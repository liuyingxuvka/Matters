"""Checkpointed autonomous maintenance over the ObjectCoverageLedger."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Event, Lock, Thread
from typing import Callable
from uuid import uuid4

from matters.analysis.operations import (
    AgentOperationOwner,
    AgentOperationResult,
    AgentRunner,
    AnalysisWorkPackage,
)
from matters.application.coverage_ledger import ObjectCoverageLedger
from matters.application.dispatcher import AutonomousFindingDispatcher
from matters.infrastructure.sqlite.store import SQLiteStore


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class MaintenanceCycle:
    cycle_id: str
    started_at: str
    finished_at: str
    package_count: int
    dispatched_count: int
    owner_redispatch_count: int
    blocked_count: int
    analysis_expanded_source_count: int
    analysis_queued_package_count: int
    hierarchy_recovered_count: int
    hierarchy_blocked_count: int
    pending_work_count: int
    status: str
    checkpoint: str


class AutonomousMaintenanceWorker:
    """Select missing work, run available AI, and checkpoint every cycle."""

    def __init__(
        self,
        *,
        store: SQLiteStore,
        ledger: ObjectCoverageLedger,
        operations: AgentOperationOwner,
        dispatcher: AutonomousFindingDispatcher,
        runner_provider: Callable[[], AgentRunner | None] | None = None,
        post_dispatch: Callable[
            [AnalysisWorkPackage, AgentOperationResult],
            None,
        ]
        | None = None,
        hierarchy_recovery: Callable[[int], tuple[int, int]] | None = None,
        analysis_expansion: Callable[[int], tuple[int, int]] | None = None,
        interval_seconds: float = 30.0,
        background_cycle_limit: int = 1,
    ) -> None:
        if interval_seconds < 0.1:
            raise ValueError("maintenance interval is too small")
        if background_cycle_limit < 1 or background_cycle_limit > 20:
            raise ValueError("background maintenance limit is invalid")
        self.store = store
        self.ledger = ledger
        self.operations = operations
        self.dispatcher = dispatcher
        self.runner_provider = runner_provider or (lambda: None)
        self.post_dispatch = post_dispatch or (
            lambda _package, _result: None
        )
        self.hierarchy_recovery = hierarchy_recovery or (
            lambda _limit: (0, 0)
        )
        self.analysis_expansion = analysis_expansion or (
            lambda _limit: (0, 0)
        )
        self.interval_seconds = interval_seconds
        self.background_cycle_limit = background_cycle_limit
        self._stop = Event()
        self._thread: Thread | None = None
        self._lock = Lock()

    def run_cycle(self, *, limit: int = 20) -> MaintenanceCycle:
        if limit < 1 or limit > 200:
            raise ValueError("maintenance cycle limit is invalid")
        with self._lock:
            started_at = _utc_now()
            cycle_id = f"maintenance:{uuid4().hex}"
            self.ledger.record_worker_state(
                worker_health="running",
                worker_checkpoint=f"{cycle_id}:started",
            )
            runner = self.runner_provider()
            # A normal desktop process intentionally has no embedded Codex
            # execution owner. Do not re-enumerate private WorkPackages merely
            # to rediscover that fact on every background cycle: imported
            # results dispatch synchronously, while the indexed coverage ledger
            # remains the cheap source of pending-state truth.
            packages = ()
            owner_recovery_only = False
            if runner is not None:
                expanded_sources, queued_packages = self.analysis_expansion(
                    limit
                )
                packages, _total = self.operations.pending_packages(
                    offset=0,
                    limit=limit,
                )
            else:
                packages = self.operations.redispatchable_packages(
                    limit=limit,
                )
                owner_recovery_only = bool(packages)
                if owner_recovery_only:
                    # A passed, current result is already the terminal AI
                    # output.  Recover its original-owner write as one bounded
                    # phase before scheduling any new AI package.  This keeps a
                    # restart-safe retry from fanning out unrelated analysis
                    # while its exact owner disposition is still being closed.
                    expanded_sources, queued_packages = (0, 0)
                else:
                    expanded_sources, queued_packages = (
                        self.analysis_expansion(limit)
                    )
            dispatched = 0
            owner_redispatched = 0
            blocked = 0
            processed = 0
            waiting_for_runner = 0
            for payload in packages:
                package_id = str(payload["package_id"])
                package = self.operations.package(package_id)
                current_result = self.operations.current_result(package_id)
                redispatchable = bool(
                    current_result is not None
                    and current_result.status == "passed"
                    and current_result.receipt_current
                    and current_result.package_input_fingerprint
                    == package.input_fingerprint
                    and current_result.auto_apply_status
                    not in {
                        "auto_applied",
                        "no_finding",
                        "annotation_current",
                    }
                )
                if redispatchable:
                    result = current_result
                elif runner is not None:
                    result = self.operations.run(package, runner=runner)
                else:
                    waiting_for_runner += 1
                    continue
                outcomes = self.dispatcher.dispatch(package, result)
                self.post_dispatch(package, result)
                processed += 1
                owner_redispatched += int(
                    owner_recovery_only and redispatchable
                )
                dispatched += len(outcomes)
                blocked += int(
                    result.status == "blocked"
                    or any(item.status == "blocked" for item in outcomes)
                )
            hierarchy_recovered, hierarchy_blocked = (
                self.hierarchy_recovery(limit)
            )
            pending_work = self.ledger.next_work(limit=limit)
            if runner is None and pending_work:
                waiting_for_runner = len(pending_work)
            status = (
                "progressed"
                if (
                    processed
                    or dispatched
                    or hierarchy_recovered
                    or expanded_sources
                    or queued_packages
                )
                else (
                    "waiting_for_codex"
                    if waiting_for_runner
                    else ("idle" if not pending_work else "waiting_for_owner")
                )
            )
            checkpoint = (
                f"{cycle_id}:packages={processed}:dispatch={dispatched}:"
                f"source_expand={expanded_sources}:"
                f"source_packages={queued_packages}:"
                f"hierarchy={hierarchy_recovered}:"
                f"hierarchy_blocked={hierarchy_blocked}:"
                f"owner_retry={owner_redispatched}:"
                f"pending={len(pending_work)}:waiting_ai={waiting_for_runner}"
            )
            cycle = MaintenanceCycle(
                cycle_id=cycle_id,
                started_at=started_at,
                finished_at=_utc_now(),
                package_count=processed,
                dispatched_count=dispatched,
                owner_redispatch_count=owner_redispatched,
                blocked_count=blocked,
                analysis_expanded_source_count=expanded_sources,
                analysis_queued_package_count=queued_packages,
                hierarchy_recovered_count=hierarchy_recovered,
                hierarchy_blocked_count=hierarchy_blocked,
                pending_work_count=len(pending_work),
                status=status,
                checkpoint=checkpoint,
            )
            self.store.append(
                "maintenance_cycle",
                cycle_id,
                1,
                asdict(cycle),
            )
            self.ledger.record_worker_state(
                worker_health=status,
                worker_checkpoint=checkpoint,
            )
            return cycle

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()

        def work() -> None:
            while not self._stop.is_set():
                try:
                    self.run_cycle(limit=self.background_cycle_limit)
                except Exception as exc:
                    checkpoint = f"maintenance:error:{type(exc).__name__}"
                    self.ledger.record_worker_state(
                        worker_health="blocked",
                        worker_checkpoint=checkpoint,
                    )
                self._stop.wait(self.interval_seconds)

        self._thread = Thread(
            target=work,
            name="matters-autonomous-maintenance",
            daemon=True,
        )
        self._thread.start()

    def stop(self, *, timeout: float = 5.0) -> bool:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        stopped = not (self._thread is not None and self._thread.is_alive())
        self.ledger.record_worker_state(
            worker_health="stopped" if stopped else "blocked",
            worker_checkpoint="maintenance:stopped" if stopped else "maintenance:stop-timeout",
        )
        return stopped


__all__ = ["AutonomousMaintenanceWorker", "MaintenanceCycle"]
