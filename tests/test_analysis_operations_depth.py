from pathlib import Path

import pytest

from matters.analysis.operations import (
    AgentOperationOwner,
    AnalysisWorkPackage,
    DeterministicFakeRunner,
)
from matters.application.orchestrator import MatterService


class LegacyRunner:
    provider_id = "sourceguard"
    provider_version = "old"

    def execute(self, package):
        return {"status": "passed", "findings": []}


class EscapingRunner:
    provider_id = "fake_researchguard"
    provider_version = "synthetic-v1"

    def execute(self, package):
        return {
            "status": "passed",
            "findings": [
                {
                    "statement": "unsupported",
                    "evidence_ids": ["evidence:outside"],
                }
            ],
        }


def _package(*, synthetic=False):
    return AnalysisWorkPackage.create(
        operation_type="research_operation",
        task_kind="bounded_research",
        source_revision_ids=("source:v1",),
        model_revision="model:v1",
        allowed_evidence_ids=("evidence:1",),
        private_evidence={
            "statement": "Contact a.person@example.com at https://private.test/123456",
            "message_id": "private-id",
        },
        disclosure_policy="external_pseudonymized",
        synthetic=synthetic,
    )


def test_work_package_minimizes_private_identifiers():
    package = _package(synthetic=True)
    assert package.package_version == 2
    assert package.human_confirmation_required is False
    assert package.auto_apply_policy == "validate_then_dispatch_original_owner"
    assert "example.com" not in str(package.untrusted_evidence)
    assert "private.test" not in str(package.untrusted_evidence)
    assert "private-id" not in str(package.untrusted_evidence)
    assert package.disclosure_disposition


def test_pending_researchguard_fake_and_legacy_boundaries():
    owner = AgentOperationOwner()
    pending = owner.run(_package(), runner=DeterministicFakeRunner())
    synthetic = owner.run(
        _package(synthetic=True),
        runner=DeterministicFakeRunner(),
    )
    legacy = owner.run(_package(synthetic=True), runner=LegacyRunner())
    escaping = owner.run(_package(synthetic=True), runner=EscapingRunner())
    assert pending.status == "blocked"
    assert pending.failure_class == "researchguard_currentness_missing"
    assert synthetic.status == "passed"
    assert synthetic.advisory_only
    assert synthetic.receipt_current
    assert legacy.failure_class == "legacy_parallel_guard_binding_rejected"
    assert escaping.failure_class == "invalid_agent_operation_output"
    with pytest.raises(PermissionError):
        owner.write_canonical("matter", "completed")


def test_semantic_depth_exact_states_and_persistence(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    service = MatterService(private_root=home, repository_root=repo)
    partial = service.assess_depth(
        occurrence_id="occurrence:1",
        inventory_revision=1,
        criteria={"coverage_terminal": True},
    )
    sufficient = service.assess_depth(
        occurrence_id="occurrence:1",
        inventory_revision=1,
        criteria={
            "coverage_terminal": True,
            "extraction_current": True,
            "analysis_terminal": True,
            "evidence_anchored": True,
            "owner_dispatch_terminal": True,
        },
    )
    stale = service.assess_depth(
        occurrence_id="occurrence:1",
        inventory_revision=2,
        criteria={},
        stale_dependencies=("analysis",),
    )
    assert partial.state == "partial"
    assert sufficient.state == "sufficient"
    assert stale.state == "stale"
    assert len(service.store.history("semantic_depth", "occurrence:1")) == 3


def test_model_miss_is_a_bounded_development_handoff_not_live_edit(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    service = MatterService(private_root=home, repository_root=repo)
    miss = service.report_model_miss(
        failure_class="unrepresented_source_shape",
        expected_behavior="preserve parent child provenance",
        observed_behavior="extractor cannot represent nested part",
        model_path="C3_evidence_qualification",
        private_evidence_handle="private-evidence:opaque-1",
        current_runtime_disposition="partial",
    )
    assert "review" not in miss.status
    queued = service.work_queue.status(f"development:{miss.miss_id}")
    assert queued.status == "queued"
    with pytest.raises(PermissionError):
        service.model_misses.edit_runtime("flowguard model")
