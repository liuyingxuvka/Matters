from dataclasses import asdict
from pathlib import Path

import pytest

from matters.analysis.operations import (
    AgentOperationOwner,
    AnalysisWorkPackage,
    DeterministicFakeRunner,
)
from matters.application.orchestrator import MatterService
from matters.infrastructure.sqlite.store import SQLiteStore


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


class DirectApiRunner:
    provider_id = "openai-api"
    provider_version = "v1"

    def execute(self, package):
        return {"status": "passed", "findings": []}


class CapabilityRunner:
    provider_id = "codex-hosted-capability-router"
    provider_version = "capability-contract-v1"

    def __init__(self, profile):
        self.profile = profile

    def execute(self, package):
        return {
            "status": "passed",
            "input_dispositions": [
                {
                    "input_id": input_id,
                    "disposition": "used",
                    "reason": "bounded capability execution",
                }
                for input_id in (
                    *package.allowed_evidence_ids,
                    *package.allowed_asset_ids,
                )
            ],
            "findings": [],
            "execution_profile_identity": f"execution-profile:{self.profile}",
            "concrete_execution_identity": f"execution:{self.profile}",
            "resource_usage": {"input_count": 1},
        }


class OverreachingAnnotator(CapabilityRunner):
    def execute(self, package):
        payload = super().execute(package)
        payload["findings"] = [
            {
                "finding_type": "matter_candidate",
                "owner_model_id": "C6_matter_admission",
                "statement": "A Matter",
                "localized_statement": {
                    "en": "A Matter",
                    "zh-CN": "一个事项",
                },
                "semantic_revision": package.source_revision_ids[0],
                "evidence_ids": [package.allowed_evidence_ids[0]],
            }
        ]
        return payload


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


def test_capability_contract_is_model_agnostic_and_rejects_direct_api():
    package = AnalysisWorkPackage.create(
        operation_type="text_analysis",
        task_kind="source_annotation",
        capability_role="low_cost_annotator",
        requested_output_types=("source_annotation",),
        source_revision_ids=("source:v1",),
        model_revision="annotation:v1",
        allowed_evidence_ids=("evidence:1",),
        private_evidence={"statement": "A user document"},
    )
    owner = AgentOperationOwner()
    first = owner.run(package, runner=CapabilityRunner("economy-a"))
    second = owner.run(package, runner=CapabilityRunner("economy-b"))
    blocked = owner.run(package, runner=DirectApiRunner())

    assert first.status == second.status == "passed"
    assert first.package_id == second.package_id == package.package_id
    assert first.package_input_fingerprint == second.package_input_fingerprint
    assert first.execution_profile_identity != second.execution_profile_identity
    assert first.concrete_execution_identity != second.concrete_execution_identity
    assert blocked.status == "blocked"
    assert blocked.failure_class == "app_owned_api_fallback_rejected"


def test_low_cost_annotator_cannot_promote_a_matter():
    package = AnalysisWorkPackage.create(
        operation_type="text_analysis",
        task_kind="source_annotation",
        capability_role="low_cost_annotator",
        requested_output_types=("source_annotation",),
        source_revision_ids=("source:v1",),
        model_revision="annotation:v1",
        allowed_evidence_ids=("evidence:1",),
        private_evidence={"statement": "A user document"},
    )
    result = AgentOperationOwner().run(
        package,
        runner=OverreachingAnnotator("economy-a"),
    )
    assert result.status == "blocked"
    assert result.failure_class == "invalid_agent_operation_output"


def test_legacy_named_runner_package_is_directly_migrated(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    package = AnalysisWorkPackage.create(
        operation_type="text_analysis",
        task_kind="semantic_understanding",
        source_revision_ids=("source:v1",),
        model_revision="semantic:v2",
        allowed_evidence_ids=("evidence:1",),
        private_evidence={"statement": "A user document"},
    )
    legacy = asdict(package)
    legacy["package_id"] = "work:legacy-named-runner"
    legacy["required_runner_id"] = "codex-local"
    legacy["required_runner_version"] = "current"
    legacy.pop("capability_role")
    legacy.pop("requested_output_types")
    legacy.pop("execution_profile_contract_id")
    legacy.pop("dependency_package_ids")
    SQLiteStore(home, repo).append(
        "analysis_work_package",
        legacy["package_id"],
        1,
        legacy,
    )

    service = MatterService(private_root=home, repository_root=repo)
    rebased = service.rebase_analysis_contracts(
        after_package_id="",
        limit=200,
    )
    migration = service.store.current(
        "analysis_work_package_migration",
        legacy["package_id"],
    )
    pending = service.pending_analysis_packages()

    assert service.migrated_analysis_package_count == 0
    assert rebased["rebased_package_count"] == 1
    assert migration["migration"] == "direct_to_capability_contract_v1"
    assert pending["total_count"] == 1
    assert pending["items"][0]["required_runner_id"] == (
        "codex-hosted-capability-router"
    )
    assert pending["items"][0]["capability_role"] == "matter_modeler"
    assert "luna" not in str(pending["items"][0]).casefold()


def test_retired_capability_role_is_directly_migrated(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    package = AnalysisWorkPackage.create(
        operation_type="text_analysis",
        task_kind="semantic_understanding",
        source_revision_ids=("source:v1",),
        model_revision="semantic:v2",
        allowed_evidence_ids=("evidence:1",),
        private_evidence={"statement": "A user document"},
    )
    retired = asdict(package)
    retired["package_id"] = "work:retired-semantic-modeler"
    retired["capability_role"] = "semantic_modeler"
    retired["control_contract"]["capability_role"] = "semantic_modeler"
    SQLiteStore(home, repo).append(
        "analysis_work_package",
        retired["package_id"],
        1,
        retired,
    )

    service = MatterService(private_root=home, repository_root=repo)
    rebased = service.rebase_analysis_contracts(
        after_package_id="",
        limit=200,
    )
    migration = service.store.current(
        "analysis_work_package_migration",
        retired["package_id"],
    )
    pending = service.pending_analysis_packages()

    assert service.migrated_analysis_package_count == 0
    assert rebased["rebased_package_count"] == 1
    assert migration["migration"] == "direct_to_capability_contract_v1"
    assert pending["total_count"] == 1
    assert pending["items"][0]["capability_role"] == "matter_modeler"
    assert pending["items"][0]["package_id"] != retired["package_id"]


def test_pending_analysis_excludes_source_rejected_by_current_policy(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    service = MatterService(private_root=home, repository_root=repo)
    occurrence_id = "occurrence:program-file"
    source_id = "source:program-file"
    package = AnalysisWorkPackage.create(
        operation_type="text_analysis",
        task_kind="semantic_understanding",
        source_revision_ids=(f"{source_id}:v1",),
        model_revision="semantic:v3",
        allowed_evidence_ids=("evidence:program-file",),
        private_evidence={"statement": "Program text from an older scan"},
    )
    service.store.append(
        "source_version",
        source_id,
        1,
        {
            "source_id": source_id,
            "version": 1,
            "external_reference": {
                "external_id": occurrence_id,
            },
        },
    )
    service.store.append(
        "analysis_work_package",
        package.package_id,
        1,
        asdict(package),
    )
    service.coverage_ledger.reconcile_inventory(
        scope_id="scope:user-files",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": occurrence_id,
                "provider": "filesystem",
                "object_type": "document",
            },
        ),
        dispositions=(
            {
                "occurrence_id": occurrence_id,
                "status": "tracked",
            },
        ),
    )

    assert service.pending_analysis_packages()["total_count"] == 1

    service.coverage_ledger.reconcile_inventory(
        scope_id="scope:user-files",
        inventory_revision=2,
        occurrences=(
            {
                "occurrence_id": occurrence_id,
                "provider": "filesystem",
                "object_type": "file",
            },
        ),
        dispositions=(
            {
                "occurrence_id": occurrence_id,
                "status": "hard_excluded",
            },
        ),
    )

    assert service.pending_analysis_packages()["total_count"] == 0


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
