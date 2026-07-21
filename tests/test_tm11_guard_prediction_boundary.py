from matters.analysis.forecasts import (
    Forecast,
    ForecastEntryPointRetiredError,
    WORLD_MODEL_PREDICTION_OWNER,
)
from matters.analysis.guard_bridge import GuardBridge
from matters.analysis.guard_receipts import GuardReceipt
from matters.analysis.operations import (
    AgentOperationOwner,
    AnalysisWorkPackage,
    DeterministicFakeRunner,
)
import pytest


def _receipt(**changes):
    values = {
        "receipt_id": "r",
        "result_status": "passed",
        "source_revision": "s1",
        "model_revision": "m1",
        "current_source_revision": "s1",
        "current_model_revision": "m1",
    }
    values.update(changes)
    return GuardReceipt(**values)


def test_guard_is_advisory_and_stale_is_rejected():
    bridge = GuardBridge()
    current = bridge.register(
        artifact_id="a",
        matter_id="m",
        kind="finding",
        statement="possible blocker",
        receipt=_receipt(),
    )
    stale = bridge.register(
        artifact_id="b",
        matter_id="m",
        kind="finding",
        statement="old blocker",
        receipt=_receipt(current_source_revision="s2"),
    )
    assert current.status == "accepted" and current.advisory_only
    assert stale.status == "stale_or_nonterminal"
    progress = bridge.register(
        artifact_id="c",
        matter_id="m",
        kind="finding",
        statement="unfinished",
        receipt=_receipt(progress_only=True),
    )
    assert progress.status == "stale_or_nonterminal"
    with pytest.raises(PermissionError):
        bridge.write_canonical("m", "blocked")


def test_weak_forecast_entry_points_are_retired_in_favor_of_world_model_owner():
    error = "forecast_entrypoint_retired"
    with pytest.raises(ForecastEntryPointRetiredError, match=error) as construction:
        Forecast("f", "m", "possible delay", "30d")
    assert WORLD_MODEL_PREDICTION_OWNER in str(construction.value)

    with pytest.raises(ForecastEntryPointRetiredError, match=error) as registration:
        GuardBridge().register_forecast(object())
    assert WORLD_MODEL_PREDICTION_OWNER in str(registration.value)


class LegacySourceGuardRunner:
    provider_id = "sourceguard"
    provider_version = "retired"

    def execute(self, _package):
        return {"status": "passed", "findings": []}


def _research_package(*, synthetic: bool):
    return AnalysisWorkPackage.create(
        operation_type="research_operation",
        task_kind="bounded_research",
        source_revision_ids=("source:synthetic:v1",),
        model_revision="model:synthetic:v1",
        allowed_evidence_ids=("evidence:synthetic:1",),
        private_evidence={"statement": "bounded synthetic claim"},
        disclosure_policy="external_pseudonymized",
        synthetic=synthetic,
    )


def test_research_operation_pending_fake_and_legacy_fallback_rejection():
    owner = AgentOperationOwner()
    pending = owner.run(
        _research_package(synthetic=False),
        runner=DeterministicFakeRunner(),
    )
    synthetic = owner.run(
        _research_package(synthetic=True),
        runner=DeterministicFakeRunner(),
    )
    legacy = owner.run(
        _research_package(synthetic=True),
        runner=LegacySourceGuardRunner(),
    )
    assert pending.status == "blocked"
    assert pending.failure_class == "researchguard_currentness_missing"
    assert synthetic.status == "passed"
    assert synthetic.advisory_only
    assert synthetic.receipt_current
    assert legacy.status == "blocked"
    assert legacy.failure_class == "legacy_parallel_guard_binding_rejected"
    with pytest.raises(PermissionError):
        owner.write_canonical("matter", "completed")
