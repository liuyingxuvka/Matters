"""Checkpointed autonomous maintenance over the ObjectCoverageLedger."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Event, Lock, Thread
from typing import Callable

from matters.analysis.operations import AgentOperationOwner, AgentRunner
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
    blocked_count: int
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
        interval_seconds: float = 1.0,
    ) -> None:
        if interval_seconds < 0.1:
            raise ValueError("maintenance interval is too small")
        self.store = store
        self.ledger = ledger
        self.operations = operations
        self.dispatcher = dispatcher
        self.runner_provider = runner_provider or (lambda: None)
        self.interval_seconds = interval_seconds
        self._stop = Event()
        self._thread: Thread | None = None
        self._lock = Lock()

    def run_cycle(self, *, limit: int = 20) -> MaintenanceCycle:
        if limit < 1 or limit > 200:
            raise ValueError("maintenance cycle limit is invalid")
        with self._lock:
            started_at = _utc_now()
            sequence = self.store.next_revision("maintenance_cycle", "worker")
            cycle_id = f"maintenance:{sequence}"
            self.ledger.record_worker_state(
                worker_health="running",
                worker_checkpoint=f"{cycle_id}:started",
            )
            packages, _total = self.operations.pending_packages(
                offset=0,
                limit=limit,
            )
            runner = self.runner_provider()
            dispatched = 0
            blocked = 0
            processed = 0
            if runner is not None:
                for payload in packages:
                    package_id = str(payload["package_id"])
                    package = self.operations.package(package_id)
                    result = self.operations.run(package, runner=runner)
                    outcomes = self.dispatcher.dispatch(package, result)
                    processed += 1
                    dispatched += len(outcomes)
                    blocked += int(
                        result.status == "blocked"
                        or any(item.status == "blocked" for item in outcomes)
                    )
            pending_work = self.ledger.next_work(limit=limit)
            status = (
                "waiting_for_ai"
                if packages and runner is None
                else (
                    "progressed"
                    if processed or dispatched
                    else ("idle" if not pending_work else "waiting_for_owner")
                )
            )
            checkpoint = (
                f"{cycle_id}:packages={processed}:dispatch={dispatched}:"
                f"pending={len(pending_work)}"
            )
            cycle = MaintenanceCycle(
                cycle_id=cycle_id,
                started_at=started_at,
                finished_at=_utc_now(),
                package_count=processed,
                dispatched_count=dispatched,
                blocked_count=blocked,
                pending_work_count=len(pending_work),
                status=status,
                checkpoint=checkpoint,
            )
            self.store.append(
                "maintenance_cycle",
                "worker",
                sequence,
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
                    self.run_cycle()
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
