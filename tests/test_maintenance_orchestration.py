import pytest

from matters.application.maintenance_orchestration import (
    DelegatedTaskReceipt,
    MaintenanceOrchestrationOwner,
    MaintenanceOrchestrationService,
    MaintenanceRunRequest,
)


class FakeStore:
    def __init__(self):
        self.rows = {}
        self.revisions = {}

    def current(self, owner, object_id):
        return self.rows.get((owner, object_id))

    def current_page(self, owner, *, offset, limit):
        rows = tuple(
            payload
            for (row_owner, _), payload in sorted(self.rows.items())
            if row_owner == owner
        )
        return rows[offset : offset + limit], len(rows)

    def next_revision(self, owner, object_id):
        return self.revisions.get((owner, object_id), 0) + 1

    def append(self, owner, object_id, revision, payload):
        self.rows[(owner, object_id)] = dict(payload)
        self.revisions[(owner, object_id)] = revision


def _request():
    return MaintenanceRunRequest.create(
        run_id="maintenance:test",
        authorization_identity="authorization:current",
        inventory_identity="inventory:current",
        coverage_identity="coverage:current",
        changed_object_ids=("occurrence:1",),
        resource_budget={
            "max_tasks": 4,
            "max_retries_per_task": 1,
            "max_concurrency": 1,
        },
    )


def test_primary_plan_delegates_bounded_tasks_and_joins_receipts():
    attempts = []

    def planner(_request):
        return {
            "tasks": [
                {
                    "task_id": "annotate",
                    "capability_role": "low_cost_annotator",
                    "input_object_ids": ("occurrence:1",),
                    "requested_output_types": ("source_annotation",),
                },
                {
                    "task_id": "model",
                    "capability_role": "matter_modeler",
                    "input_object_ids": ("occurrence:1",),
                    "dependency_task_ids": ("annotate",),
                    "requested_output_types": ("matter_candidate",),
                },
            ]
        }

    def execute(task, attempt):
        attempts.append((task.task_id, attempt))
        return DelegatedTaskReceipt(
            task_id=task.task_id,
            capability_role=task.capability_role,
            input_fingerprint=task.input_fingerprint,
            status="passed",
            attempt=attempt,
            output_refs=(f"result:{task.task_id}",),
        )

    receipt = MaintenanceOrchestrationOwner().run(
        _request(), planner=planner, executor=execute
    )

    assert receipt.status == "current"
    assert receipt.gap_task_ids == ()
    assert attempts == [("annotate", 1), ("model", 1)]


def test_product_service_entry_is_model_independent_and_hides_host_adapters():
    def planner(_request):
        return {"no_change": True, "tasks": ()}

    def executor(_task, _attempt):
        raise AssertionError("a no-change plan must not execute a task")

    service = MaintenanceOrchestrationService(
        planner=planner,
        executor=executor,
    )

    receipt = service.run(_request())
    report = service.capability_report()

    assert receipt.status == "no_change"
    assert report == {
        "contract_id": "matters.maintenance-orchestration-service.v1",
        "status": "available",
        "delegatable_roles": tuple(
            sorted(
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
        ),
        "accepts_provider_configuration": False,
        "accepts_api_credentials": False,
    }
    assert "planner" not in report
    assert "executor" not in report


def test_tampered_request_cannot_reach_the_host_planner():
    request = _request()
    tampered = MaintenanceRunRequest(
        run_id=request.run_id,
        authorization_identity=request.authorization_identity,
        inventory_identity=request.inventory_identity,
        coverage_identity="coverage:stale",
        changed_object_ids=request.changed_object_ids,
        resource_budget=request.resource_budget,
        request_fingerprint=request.request_fingerprint,
    )
    called = False

    def planner(_request):
        nonlocal called
        called = True
        return {"no_change": True, "tasks": ()}

    with pytest.raises(ValueError, match="fingerprint is stale or invalid"):
        MaintenanceOrchestrationService(
            planner=planner,
            executor=lambda _task, _attempt: None,
        ).run(tampered)

    assert called is False


def test_product_service_rejects_missing_host_adapters():
    with pytest.raises(ValueError, match="host adapters must be callable"):
        MaintenanceOrchestrationService(
            planner=None,
            executor=lambda _task, _attempt: None,
        )


def test_identical_failure_stops_retry_loop_and_blocks_dependents():
    def planner(_request):
        return {
            "tasks": [
                {
                    "task_id": "hero",
                    "capability_role": "hero_image_generator",
                    "input_object_ids": ("matter:1",),
                    "requested_output_types": ("generated_hero",),
                    "retry_budget": 3,
                },
                {
                    "task_id": "review",
                    "capability_role": "consistency_reviewer",
                    "input_object_ids": ("matter:1",),
                    "dependency_task_ids": ("hero",),
                },
            ]
        }

    attempts = []

    def execute(task, attempt):
        attempts.append(attempt)
        return DelegatedTaskReceipt(
            task_id=task.task_id,
            capability_role=task.capability_role,
            input_fingerprint=task.input_fingerprint,
            status="blocked",
            attempt=attempt,
            failure_class="capability_unavailable",
        )

    receipt = MaintenanceOrchestrationOwner().run(
        MaintenanceRunRequest.create(
            run_id="maintenance:retry-test",
            authorization_identity="authorization:current",
            inventory_identity="inventory:current",
            coverage_identity="coverage:current",
            changed_object_ids=("matter:1",),
            resource_budget={
                "max_tasks": 4,
                "max_retries_per_task": 3,
                "max_concurrency": 1,
            },
        ),
        planner=planner,
        executor=execute,
    )

    assert receipt.status == "blocked"
    assert receipt.gap_task_ids == ("hero", "review")
    assert attempts == [1, 2]


def test_public_plan_rejects_named_model_or_provider_binding():
    with pytest.raises(ValueError, match="provider or named model"):
        MaintenanceOrchestrationOwner().run(
            _request(),
            planner=lambda _request: {
                "model_id": "cheap-model",
                "tasks": (),
            },
            executor=lambda _task, _attempt: None,
        )


@pytest.mark.parametrize(
    "forbidden_payload",
    (
        {"execution_target": "gpt-5.6-luna"},
        {"model_slug": "gpt-5.6-luna"},
        {"provider_url": "https://api.openai.com"},
        {"reasoning_level": "low"},
    ),
)
def test_task_payload_cannot_smuggle_private_profile_configuration(
    forbidden_payload,
):
    with pytest.raises(ValueError, match="provider or named model"):
        MaintenanceOrchestrationOwner().run(
            _request(),
            planner=lambda _request: {
                "tasks": [
                    {
                        "task_id": "annotate",
                        "capability_role": "low_cost_annotator",
                        "input_object_ids": ("occurrence:1",),
                        "task_payload": forbidden_payload,
                    }
                ]
            },
            executor=lambda _task, _attempt: None,
        )


def test_plan_cannot_exceed_the_run_level_retry_budget():
    with pytest.raises(ValueError, match="exceeds retry budget"):
        MaintenanceOrchestrationOwner().run(
            _request(),
            planner=lambda _request: {
                "tasks": [
                    {
                        "task_id": "annotate",
                        "capability_role": "low_cost_annotator",
                        "input_object_ids": ("occurrence:1",),
                        "retry_budget": 2,
                    }
                ]
            },
            executor=lambda _task, _attempt: None,
        )


@pytest.mark.parametrize(
    ("budget", "message"),
    [
        (
            {
                "max_tasks": 0,
                "max_retries_per_task": 1,
                "max_concurrency": 1,
            },
            "task budget",
        ),
        (
            {
                "max_tasks": 1,
                "max_retries_per_task": 4,
                "max_concurrency": 1,
            },
            "retry budget",
        ),
        (
            {
                "max_tasks": 1,
                "max_retries_per_task": 1,
                "max_concurrency": 0,
            },
            "concurrency budget",
        ),
    ],
)
def test_run_request_rejects_unbounded_resource_budgets(budget, message):
    with pytest.raises(ValueError, match=message):
        MaintenanceRunRequest.create(
            run_id="maintenance:invalid-budget",
            authorization_identity="authorization:current",
            inventory_identity="inventory:current",
            coverage_identity="coverage:current",
            changed_object_ids=("occurrence:1",),
            resource_budget=budget,
        )


@pytest.mark.parametrize(
    ("child_status", "expected_disposition", "expected_run_status"),
    (
        ("passed", "processed", "current"),
        ("no_change", "rejected", "current"),
        ("blocked", "blocked", "blocked"),
    ),
)
def test_pending_a3_feedback_reaches_one_a2_terminal_receipt(
    child_status,
    expected_disposition,
    expected_run_status,
):
    store = FakeStore()
    observation_id = "ai-observation:bounded"
    store.rows[("ai_user_observation", observation_id)] = {
        "artifact_type": "matters.ai-user-observation.v1",
        "observation_id": observation_id,
        "matter_id": "matter:1",
        "observation_kind": "event",
        "statement": "The appointment happened.",
        "observed_at": "2026-07-20T12:00:00+00:00",
        "source_ref": "conversation:opaque",
        "modality": "reported",
        "dispatch_owner_id": "C5_event_temporal_trace",
        "status": "pending_owner",
        "canonical_write": False,
    }
    executed = []

    def execute(task, attempt):
        executed.append(task)
        return DelegatedTaskReceipt(
            task_id=task.task_id,
            capability_role=task.capability_role,
            input_fingerprint=task.input_fingerprint,
            status=child_status,
            attempt=attempt,
            output_refs=("owner-result:1",) if child_status == "passed" else (),
            failure_class=(
                "owner_validation_blocked" if child_status == "blocked" else ""
            ),
        )

    owner = MaintenanceOrchestrationOwner(store=store)
    receipt = owner.run(
        _request(),
        planner=lambda _request: {"no_change": True, "tasks": ()},
        executor=execute,
    )

    terminal = store.current("maintenance_ai_feedback_receipt", observation_id)
    assert receipt.status == expected_run_status
    assert len(executed) == 1
    assert executed[0].capability_role == "original_owner_feedback_validator"
    assert executed[0].task_payload["dispatch_owner_id"] == (
        "C5_event_temporal_trace"
    )
    assert terminal["disposition"] == expected_disposition
    assert terminal["canonical_write"] is False

    replay = owner.run(
        _request(),
        planner=lambda _request: {"no_change": True, "tasks": ()},
        executor=lambda _task, _attempt: pytest.fail(
            "terminal feedback must not be dispatched twice"
        ),
    )
    assert replay.status == "no_change"
