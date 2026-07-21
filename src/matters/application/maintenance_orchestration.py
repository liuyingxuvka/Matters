"""A2 model-agnostic private maintenance planning, delegation, and receipt joins."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, TYPE_CHECKING, TypeAlias

from matters.application.ai_gateway import (
    MAINTENANCE_FEEDBACK_RECEIPT_OWNER,
    USER_OBSERVATION_OWNER,
)

if TYPE_CHECKING:
    from matters.infrastructure.sqlite.store import SQLiteStore


DELEGATABLE_ROLES = frozenset(
    {
        "deterministic_preprocessor",
        "low_cost_annotator",
        "ambiguity_resolver",
        "matter_modeler",
        "hero_image_generator",
        "consistency_reviewer",
        "research_operation",
        "original_owner_feedback_validator",
    }
)
TERMINAL_CHILD_STATUSES = frozenset(
    {"passed", "no_change", "failed", "blocked", "unavailable", "cancelled"}
)
FORBIDDEN_PUBLIC_PLAN_KEYS = frozenset(
    {
        "model",
        "model_id",
        "model_name",
        "provider",
        "provider_id",
        "api_key",
        "api_url",
        "credential",
        "execution_target",
        "model_slug",
        "price_tier",
        "provider_url",
        "reasoning_level",
        "token",
    }
)

MaintenancePlanner: TypeAlias = Callable[
    ["MaintenanceRunRequest"],
    Mapping[str, Any],
]
MaintenanceTaskExecutor: TypeAlias = Callable[
    ["MaintenanceTask", int],
    "DelegatedTaskReceipt",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key).casefold() in FORBIDDEN_PUBLIC_PLAN_KEYS
            or _contains_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_key(item) for item in value)
    return False


@dataclass(frozen=True)
class MaintenanceRunRequest:
    run_id: str
    authorization_identity: str
    inventory_identity: str
    coverage_identity: str
    changed_object_ids: tuple[str, ...]
    resource_budget: Mapping[str, int]
    request_fingerprint: str

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        authorization_identity: str,
        inventory_identity: str,
        coverage_identity: str,
        changed_object_ids: tuple[str, ...],
        resource_budget: Mapping[str, int] | None = None,
    ) -> "MaintenanceRunRequest":
        budget = dict(
            resource_budget
            or {"max_tasks": 100, "max_retries_per_task": 1, "max_concurrency": 4}
        )
        max_tasks = int(budget.get("max_tasks", 0))
        max_retries = int(budget.get("max_retries_per_task", 0))
        max_concurrency = int(budget.get("max_concurrency", 1))
        if max_tasks < 1 or max_tasks > 10_000:
            raise ValueError("maintenance task budget is invalid")
        if max_retries < 0 or max_retries > 3:
            raise ValueError("maintenance retry budget is invalid")
        if max_concurrency < 1 or max_concurrency > 32:
            raise ValueError("maintenance concurrency budget is invalid")
        budget = {
            "max_tasks": max_tasks,
            "max_retries_per_task": max_retries,
            "max_concurrency": max_concurrency,
        }
        payload = {
            "run_id": run_id,
            "authorization_identity": authorization_identity,
            "inventory_identity": inventory_identity,
            "coverage_identity": coverage_identity,
            "changed_object_ids": tuple(sorted(set(changed_object_ids))),
            "resource_budget": budget,
        }
        return cls(**payload, request_fingerprint=_fingerprint(payload))


@dataclass(frozen=True)
class MaintenanceTask:
    task_id: str
    capability_role: str
    input_object_ids: tuple[str, ...]
    dependency_task_ids: tuple[str, ...] = ()
    requested_output_types: tuple[str, ...] = ()
    retry_budget: int = 0
    input_fingerprint: str = ""
    task_payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_id or self.capability_role not in DELEGATABLE_ROLES:
            raise ValueError("invalid maintenance task")
        if self.retry_budget < 0 or self.retry_budget > 3:
            raise ValueError("maintenance retry budget is invalid")
        if _contains_forbidden_key(self.task_payload):
            raise ValueError("maintenance task cannot bind a provider or named model")
        object.__setattr__(self, "input_object_ids", tuple(self.input_object_ids))
        object.__setattr__(self, "dependency_task_ids", tuple(self.dependency_task_ids))
        object.__setattr__(
            self, "requested_output_types", tuple(self.requested_output_types)
        )
        object.__setattr__(self, "task_payload", dict(self.task_payload))
        if not self.input_fingerprint:
            object.__setattr__(
                self,
                "input_fingerprint",
                _fingerprint(
                    {
                        "task_id": self.task_id,
                        "capability_role": self.capability_role,
                        "input_object_ids": self.input_object_ids,
                        "dependency_task_ids": self.dependency_task_ids,
                        "requested_output_types": self.requested_output_types,
                        "task_payload": self.task_payload,
                    }
                ),
            )


@dataclass(frozen=True)
class MaintenancePlan:
    plan_id: str
    run_id: str
    request_fingerprint: str
    tasks: tuple[MaintenanceTask, ...]
    no_change: bool
    plan_fingerprint: str


@dataclass(frozen=True)
class DelegatedTaskReceipt:
    task_id: str
    capability_role: str
    input_fingerprint: str
    status: str
    attempt: int
    output_refs: tuple[str, ...] = ()
    failure_class: str = ""
    receipt_fingerprint: str = ""

    def __post_init__(self) -> None:
        if self.status not in TERMINAL_CHILD_STATUSES or self.attempt < 1:
            raise ValueError("invalid delegated task receipt")
        object.__setattr__(self, "output_refs", tuple(self.output_refs))
        if not self.receipt_fingerprint:
            object.__setattr__(
                self,
                "receipt_fingerprint",
                _fingerprint(
                    {
                        "task_id": self.task_id,
                        "capability_role": self.capability_role,
                        "input_fingerprint": self.input_fingerprint,
                        "status": self.status,
                        "attempt": self.attempt,
                        "output_refs": self.output_refs,
                        "failure_class": self.failure_class,
                    }
                ),
            )


@dataclass(frozen=True)
class MaintenanceRunReceipt:
    run_id: str
    request_fingerprint: str
    plan_fingerprint: str
    child_receipts: tuple[DelegatedTaskReceipt, ...]
    status: str
    gap_task_ids: tuple[str, ...]
    completed_at: str
    receipt_fingerprint: str


@dataclass(frozen=True)
class AIFeedbackTerminalReceipt:
    artifact_type: str
    observation_id: str
    dispatch_owner_id: str
    run_id: str
    task_id: str
    child_status: str
    disposition: str
    output_refs: tuple[str, ...]
    failure_class: str
    canonical_write: bool
    completed_at: str
    receipt_fingerprint: str


@dataclass
class MaintenanceOrchestrationOwner:
    """Own one maintenance plan and joins child receipts, never product fields."""

    store: "SQLiteStore | None" = None

    def run(
        self,
        request: MaintenanceRunRequest,
        *,
        planner: MaintenancePlanner,
        executor: MaintenanceTaskExecutor,
    ) -> MaintenanceRunReceipt:
        self._assert_current_request(request)
        raw_plan = dict(planner(request))
        feedback_tasks = self._pending_feedback_tasks(request, raw_plan)
        if feedback_tasks:
            raw_plan["tasks"] = (
                *tuple(raw_plan.get("tasks", ())),
                *feedback_tasks,
            )
            raw_plan["no_change"] = False
        plan = self._plan(request, raw_plan)
        self._persist_plan(plan)
        receipts: list[DelegatedTaskReceipt] = []
        status_by_task: dict[str, str] = {}
        if plan.no_change:
            return self._finish(request, plan, (), "no_change", ())
        for task in plan.tasks:
            if any(
                status_by_task.get(dependency) not in {"passed", "no_change"}
                for dependency in task.dependency_task_ids
            ):
                receipt = DelegatedTaskReceipt(
                    task_id=task.task_id,
                    capability_role=task.capability_role,
                    input_fingerprint=task.input_fingerprint,
                    status="blocked",
                    attempt=1,
                    failure_class="dependency_not_current",
                )
                receipts.append(receipt)
                status_by_task[task.task_id] = receipt.status
                continue
            seen_failures: set[str] = set()
            receipt = None
            for attempt in range(1, task.retry_budget + 2):
                candidate = executor(task, attempt)
                if (
                    candidate.task_id != task.task_id
                    or candidate.capability_role != task.capability_role
                    or candidate.input_fingerprint != task.input_fingerprint
                    or candidate.attempt != attempt
                ):
                    raise ValueError("delegated receipt does not match frozen task")
                receipt = candidate
                if candidate.status in {"passed", "no_change"}:
                    break
                failure_identity = _fingerprint(
                    {
                        "status": candidate.status,
                        "failure_class": candidate.failure_class,
                        "output_refs": candidate.output_refs,
                    }
                )
                if failure_identity in seen_failures:
                    break
                seen_failures.add(failure_identity)
            assert receipt is not None
            receipts.append(receipt)
            status_by_task[task.task_id] = receipt.status
        gaps = tuple(
            task.task_id
            for task in plan.tasks
            if status_by_task.get(task.task_id) not in {"passed", "no_change"}
        )
        status = (
            "current"
            if not gaps
            else (
                "partial"
                if any(
                    status in {"passed", "no_change"}
                    for status in status_by_task.values()
                )
                else "blocked"
            )
        )
        run_receipt = self._finish(
            request, plan, tuple(receipts), status, gaps
        )
        self._persist_feedback_terminal_receipts(
            request,
            plan,
            tuple(receipts),
        )
        return run_receipt

    @staticmethod
    def _assert_current_request(request: MaintenanceRunRequest) -> None:
        expected = MaintenanceRunRequest.create(
            run_id=request.run_id,
            authorization_identity=request.authorization_identity,
            inventory_identity=request.inventory_identity,
            coverage_identity=request.coverage_identity,
            changed_object_ids=tuple(request.changed_object_ids),
            resource_budget=dict(request.resource_budget),
        )
        if request != expected:
            raise ValueError("maintenance request fingerprint is stale or invalid")

    @staticmethod
    def _plan(
        request: MaintenanceRunRequest,
        raw: Mapping[str, Any],
    ) -> MaintenancePlan:
        if _contains_forbidden_key(raw):
            raise ValueError("maintenance plan cannot bind a provider or named model")
        raw_tasks = tuple(raw.get("tasks", ()))
        max_tasks = int(request.resource_budget.get("max_tasks", 100))
        if len(raw_tasks) > max_tasks:
            raise ValueError("maintenance plan exceeds task budget")
        tasks = tuple(
            item if isinstance(item, MaintenanceTask) else MaintenanceTask(**dict(item))
            for item in raw_tasks
        )
        max_retries = int(
            request.resource_budget.get("max_retries_per_task", 0)
        )
        if any(task.retry_budget > max_retries for task in tasks):
            raise ValueError("maintenance plan exceeds retry budget")
        task_ids = tuple(task.task_id for task in tasks)
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("maintenance plan task ids must be unique")
        known: set[str] = set()
        for task in tasks:
            if any(dependency not in known for dependency in task.dependency_task_ids):
                raise ValueError("maintenance plan dependencies must be acyclic and ordered")
            known.add(task.task_id)
        no_change = bool(raw.get("no_change", False))
        if no_change and tasks:
            raise ValueError("a no-change plan cannot dispatch tasks")
        fingerprint_payload = {
            "run_id": request.run_id,
            "request_fingerprint": request.request_fingerprint,
            "tasks": tuple(asdict(task) for task in tasks),
            "no_change": no_change,
        }
        fingerprint = _fingerprint(fingerprint_payload)
        return MaintenancePlan(
            plan_id="maintenance-plan:" + fingerprint.removeprefix("sha256:")[:24],
            run_id=request.run_id,
            request_fingerprint=request.request_fingerprint,
            tasks=tasks,
            no_change=no_change,
            plan_fingerprint=fingerprint,
        )

    def _finish(
        self,
        request: MaintenanceRunRequest,
        plan: MaintenancePlan,
        receipts: tuple[DelegatedTaskReceipt, ...],
        status: str,
        gaps: tuple[str, ...],
    ) -> MaintenanceRunReceipt:
        core = {
            "run_id": request.run_id,
            "request_fingerprint": request.request_fingerprint,
            "plan_fingerprint": plan.plan_fingerprint,
            "child_receipts": receipts,
            "status": status,
            "gap_task_ids": gaps,
            "completed_at": _utc_now(),
        }
        receipt = MaintenanceRunReceipt(
            **core,
            receipt_fingerprint=_fingerprint(
                {
                    **core,
                    "child_receipts": tuple(asdict(item) for item in receipts),
                }
            ),
        )
        if self.store is not None:
            self.store.append(
                "maintenance_orchestration_receipt",
                request.run_id,
                self.store.next_revision(
                    "maintenance_orchestration_receipt", request.run_id
                ),
                asdict(receipt),
            )
        return receipt

    def _pending_feedback_tasks(
        self,
        request: MaintenanceRunRequest,
        raw_plan: Mapping[str, Any],
    ) -> tuple[MaintenanceTask, ...]:
        if self.store is None:
            return ()
        planned_count = len(tuple(raw_plan.get("tasks", ())))
        remaining = max(
            0,
            int(request.resource_budget.get("max_tasks", 100)) - planned_count,
        )
        if remaining == 0:
            return ()
        tasks: list[MaintenanceTask] = []
        offset = 0
        total = 1
        while offset < total and len(tasks) < remaining:
            rows, total = self.store.current_page(
                USER_OBSERVATION_OWNER,
                offset=offset,
                limit=200,
            )
            if not rows:
                break
            for row in rows:
                if len(tasks) >= remaining:
                    break
                if str(row.get("status", "")) != "pending_owner":
                    continue
                observation_id = str(row.get("observation_id", "")).strip()
                dispatch_owner_id = str(
                    row.get("dispatch_owner_id", "")
                ).strip()
                if not observation_id or not dispatch_owner_id:
                    raise ValueError("pending AI feedback is missing owner identity")
                current_terminal = self.store.current(
                    MAINTENANCE_FEEDBACK_RECEIPT_OWNER,
                    observation_id,
                )
                if current_terminal is not None:
                    if (
                        current_terminal.get("artifact_type")
                        != "matters.ai-feedback-owner-terminal.v1"
                        or current_terminal.get("observation_id")
                        != observation_id
                        or current_terminal.get("disposition")
                        not in {"processed", "rejected", "blocked"}
                        or current_terminal.get("canonical_write") is not False
                    ):
                        raise ValueError("AI feedback terminal receipt is invalid")
                    continue
                tasks.append(
                    MaintenanceTask(
                        task_id=f"ai-feedback:{observation_id}",
                        capability_role="original_owner_feedback_validator",
                        input_object_ids=(observation_id,),
                        requested_output_types=(
                            "original_owner_feedback_disposition",
                        ),
                        retry_budget=0,
                        task_payload={
                            "observation_id": observation_id,
                            "matter_id": str(row.get("matter_id", "")),
                            "observation_kind": str(
                                row.get("observation_kind", "")
                            ),
                            "statement": str(row.get("statement", "")),
                            "observed_at": str(row.get("observed_at", "")),
                            "source_ref": str(row.get("source_ref", "")),
                            "dispatch_owner_id": dispatch_owner_id,
                            "modality": str(row.get("modality", "reported")),
                            "canonical_write": False,
                        },
                    )
                )
            offset += len(rows)
        return tuple(tasks)

    def _persist_feedback_terminal_receipts(
        self,
        request: MaintenanceRunRequest,
        plan: MaintenancePlan,
        receipts: tuple[DelegatedTaskReceipt, ...],
    ) -> None:
        if self.store is None:
            return
        receipt_by_task = {receipt.task_id: receipt for receipt in receipts}
        for task in plan.tasks:
            if task.capability_role != "original_owner_feedback_validator":
                continue
            observation_id = str(task.task_payload["observation_id"])
            if self.store.current(
                MAINTENANCE_FEEDBACK_RECEIPT_OWNER,
                observation_id,
            ) is not None:
                continue
            child = receipt_by_task.get(task.task_id)
            if child is None:
                raise ValueError("AI feedback task lacks a terminal child receipt")
            disposition = (
                "processed"
                if child.status == "passed"
                else "rejected"
                if child.status == "no_change"
                else "blocked"
            )
            core = {
                "artifact_type": "matters.ai-feedback-owner-terminal.v1",
                "observation_id": observation_id,
                "dispatch_owner_id": str(
                    task.task_payload["dispatch_owner_id"]
                ),
                "run_id": request.run_id,
                "task_id": task.task_id,
                "child_status": child.status,
                "disposition": disposition,
                "output_refs": child.output_refs,
                "failure_class": child.failure_class,
                "canonical_write": False,
                "completed_at": _utc_now(),
            }
            terminal = AIFeedbackTerminalReceipt(
                **core,
                receipt_fingerprint=_fingerprint(core),
            )
            self.store.append(
                MAINTENANCE_FEEDBACK_RECEIPT_OWNER,
                observation_id,
                1,
                asdict(terminal),
            )

    def _persist_plan(self, plan: MaintenancePlan) -> None:
        if self.store is None:
            return
        self.store.append(
            "maintenance_orchestration_plan",
            plan.run_id,
            self.store.next_revision("maintenance_orchestration_plan", plan.run_id),
            asdict(plan),
        )


@dataclass
class MaintenanceOrchestrationService:
    """Product service entry backed only by model-independent host adapters.

    The host may privately route the two adapters to any compatible Codex
    capability.  The product entry deliberately accepts no provider, model,
    credential, URL, or execution-profile configuration.
    """

    planner: MaintenancePlanner = field(repr=False)
    executor: MaintenanceTaskExecutor = field(repr=False)
    owner: MaintenanceOrchestrationOwner = field(
        default_factory=MaintenanceOrchestrationOwner,
    )

    def __post_init__(self) -> None:
        if not callable(self.planner) or not callable(self.executor):
            raise ValueError("maintenance host adapters must be callable")
        if not isinstance(self.owner, MaintenanceOrchestrationOwner):
            raise ValueError("maintenance owner is invalid")

    def run(self, request: MaintenanceRunRequest) -> MaintenanceRunReceipt:
        return self.owner.run(
            request,
            planner=self.planner,
            executor=self.executor,
        )

    def capability_report(self) -> Mapping[str, Any]:
        """Return stable public contract metadata without private routing data."""

        return {
            "contract_id": "matters.maintenance-orchestration-service.v1",
            "status": "available",
            "delegatable_roles": tuple(sorted(DELEGATABLE_ROLES)),
            "accepts_provider_configuration": False,
            "accepts_api_credentials": False,
        }


__all__ = [
    "DELEGATABLE_ROLES",
    "DelegatedTaskReceipt",
    "MaintenanceOrchestrationOwner",
    "MaintenanceOrchestrationService",
    "MaintenancePlanner",
    "MaintenancePlan",
    "MaintenanceRunReceipt",
    "MaintenanceRunRequest",
    "MaintenanceTask",
    "MaintenanceTaskExecutor",
]
