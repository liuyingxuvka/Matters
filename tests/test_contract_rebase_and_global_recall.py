from dataclasses import asdict

import pytest

from matters.analysis.operations import (
    CURRENT_SEMANTIC_OUTPUT_TYPES,
    AgentOperationOwner,
    AnalysisWorkPackage,
)
from matters.application.dispatcher import AutonomousFindingDispatcher
from matters.application.reconciliation import MatterReconciliationOwner
from matters.domain.admission import MatterAdmission
from matters.domain.context import (
    ContextSignal,
    GranularityAssessment,
    MatterReconciliationRequest,
    ProjectContext,
)
from matters.infrastructure.sqlite.store import SQLiteStore


class _CurrentCapabilityRunner:
    provider_id = "codex-hosted-capability-router"
    provider_version = "capability-contract-v1"

    def execute(self, package):
        return {
            "status": "passed",
            "input_dispositions": [
                {
                    "input_id": input_id,
                    "disposition": "used",
                    "reason": "focused current-contract fixture",
                }
                for input_id in (
                    *package.allowed_evidence_ids,
                    *package.allowed_asset_ids,
                )
            ],
            "findings": [],
            "execution_profile_identity": "execution-profile:focused-test",
            "concrete_execution_identity": "execution:focused-test",
            "resource_usage": {"input_count": 1},
        }


def _store(tmp_path):
    repository_root = tmp_path / "repo"
    private_root = tmp_path / "private"
    repository_root.mkdir()
    return SQLiteStore(private_root, repository_root)


def test_current_contract_rebase_supersedes_but_preserves_old_result(tmp_path):
    store = _store(tmp_path)
    owner = AgentOperationOwner(store)
    old_package = AnalysisWorkPackage.create(
        operation_type="text_analysis",
        task_kind="semantic_understanding",
        capability_role="matter_modeler",
        requested_output_types=("bounded_summary",),
        source_revision_ids=("source:old:v1",),
        model_revision="matters-semantic-understanding:v2",
        allowed_evidence_ids=("evidence:old",),
        private_evidence={"statement": "Old frozen source evidence"},
        prompt_contract_id="matters.semantic-understanding",
        prompt_contract_revision="v2",
        output_schema_id="matters.agent-operation-result.v2",
        required_skill_version="0.2.0",
    )
    old_result = owner.run(
        old_package,
        runner=_CurrentCapabilityRunner(),
    )
    assert old_result.status == "passed"
    legacy_event_id = "event:legacy-contract-output"
    legacy_output_ref = f"temporal_event:{legacy_event_id}"
    store.append(
        "temporal_event",
        legacy_event_id,
        1,
        {
            "event_id": legacy_event_id,
            "object_ref": "matter:legacy-contract",
            "kind": "future_prediction",
            "modality": "inferred",
            "evidence_ids": ["evidence:old"],
        },
    )
    store.append(
        "autonomous_finding",
        "finding:legacy-contract-output",
        1,
        {
            "finding": {
                "finding_id": "finding:legacy-contract-output",
                "finding_type": "event_candidate",
            },
            "finding_id": "finding:legacy-contract-output",
            "package_id": old_package.package_id,
            "package_input_fingerprint": old_package.input_fingerprint,
            "owner_model_id": "C5_temporal_event_ledger",
            "status": "auto_applied",
            "owner_output_ref": legacy_output_ref,
            "failure_class": "",
        },
    )
    assert owner.migrate_work_packages() == 0

    batch = owner.rebase_work_packages_to_current_contract(limit=1)
    assert batch.rebased_package_count == 1
    assert batch.scanned_package_count == 1
    assert batch.rescan_required is True
    receipt = store.current(
        "analysis_contract_rebase",
        old_package.package_id,
    )
    assert receipt is not None
    current_package_id = receipt["current_package_id"]
    current_package = store.current(
        "analysis_work_package",
        current_package_id,
    )
    assert current_package is not None
    assert current_package["prompt_contract_revision"] == "v4"
    assert current_package["output_schema_id"] == (
        "matters.agent-operation-result.v4"
    )
    assert tuple(current_package["requested_output_types"]) == (
        CURRENT_SEMANTIC_OUTPUT_TYPES
    )
    assert current_package["package_id"] != old_package.package_id
    assert store.current(
        "agent_operation_result",
        old_package.package_id,
    )["status"] == "passed"
    assert owner.current_result(old_package.package_id) is None
    invalidation = store.current(
        "analysis_result_invalidation",
        old_package.package_id,
    )
    assert invalidation == {
        "package_id": old_package.package_id,
        "reason": "analysis_contract_rebased",
        "replacement_package_id": current_package_id,
        "result_id": old_result.result_id,
        "source_result_preserved": True,
        "status": "superseded",
    }
    assert store.current(
        "agent_operation_result",
        current_package_id,
    )["status"] == "queued"
    output_invalidations = store.current_by_json_scalar_values(
        "analysis_output_invalidation",
        json_field="output_ref",
        values=(legacy_output_ref,),
    )[legacy_output_ref]
    assert len(output_invalidations) == 1
    assert output_invalidations[0]["old_package_id"] == old_package.package_id
    assert output_invalidations[0]["replacement_package_id"] == current_package_id
    assert store.invalidated_analysis_output_refs(
        (legacy_output_ref,)
    ) == {legacy_output_ref}
    assert store.current("temporal_event", legacy_event_id) is not None
    with pytest.raises(ValueError, match="superseded"):
        owner.run(old_package, runner=_CurrentCapabilityRunner())
    second = owner.rebase_work_packages_to_current_contract(limit=1)
    assert second.rebased_package_count == 0


def test_current_owner_reactivates_a_preserved_output_after_rebase(tmp_path):
    store = _store(tmp_path)
    output_ref = "temporal_event:event:reactivated"
    store.append(
        "analysis_output_invalidation",
        "analysis-output-invalidation:legacy",
        1,
        {
            "invalidation_id": "analysis-output-invalidation:legacy",
            "output_ref": output_ref,
            "old_package_id": "work:legacy",
            "replacement_package_id": "work:current",
            "status": "superseded",
        },
    )
    store.append(
        "autonomous_finding",
        "finding:reactivated",
        1,
        {
            "finding_id": "finding:reactivated",
            "package_id": "work:current",
            "status": "auto_applied",
            "owner_output_ref": output_ref,
        },
    )

    assert store.invalidated_analysis_output_refs((output_ref,)) == set()


def test_current_contract_rebase_is_bounded_and_cursor_resumable(tmp_path):
    store = _store(tmp_path)
    owner = AgentOperationOwner(store)
    old_ids = []
    for index in range(3):
        package = AnalysisWorkPackage.create(
            operation_type="text_analysis",
            task_kind="semantic_understanding",
            capability_role="matter_modeler",
            requested_output_types=("matter_candidate",),
            source_revision_ids=(f"source:bounded:{index}:v1",),
            model_revision="semantic:legacy",
            allowed_evidence_ids=(f"evidence:bounded:{index}",),
            private_evidence={"statement": f"Bounded evidence {index}"},
            prompt_contract_revision="v2",
            output_schema_id="matters.agent-operation-result.v2",
        )
        old_ids.append(package.package_id)
        store.append(
            "analysis_work_package",
            package.package_id,
            1,
            asdict(package),
        )

    cursor = ""
    total_rebased = 0
    for _attempt in range(20):
        batch = owner.rebase_work_packages_to_current_contract(
            after_package_id=cursor,
            limit=1,
        )
        assert batch.scanned_package_count <= 1
        total_rebased += batch.rebased_package_count
        if batch.has_more:
            cursor = batch.next_cursor
        elif batch.rescan_required:
            cursor = ""
        else:
            break
    else:
        raise AssertionError("bounded current-contract rebase did not converge")

    assert total_rebased == 3
    assert all(
        store.current("analysis_contract_rebase", package_id) is not None
        for package_id in old_ids
    )


def test_current_contract_with_prior_disclosure_markers_is_not_rebased(tmp_path):
    store = _store(tmp_path)
    package = AnalysisWorkPackage.create(
        operation_type="text_analysis",
        task_kind="semantic_understanding",
        capability_role="matter_modeler",
        requested_output_types=CURRENT_SEMANTIC_OUTPUT_TYPES,
        source_revision_ids=("source:current:v1",),
        model_revision="matters-semantic-understanding:v4",
        allowed_evidence_ids=("evidence:current",),
        private_evidence={
            "statement": "Contact private@example.test",
            "analysis_as_of": "2026-07-20",
        },
        prompt_contract_revision="v4",
        output_schema_id="matters.agent-operation-result.v4",
        disclosure_policy="external_pseudonymized",
    )
    assert package.disclosure_disposition
    store.append(
        "analysis_work_package",
        package.package_id,
        1,
        asdict(package),
    )

    batch = AgentOperationOwner(
        store
    ).rebase_work_packages_to_current_contract(limit=1)

    assert batch.rebased_package_count == 0
    assert store.current(
        "analysis_contract_rebase",
        package.package_id,
    ) is None


def test_current_contract_rebase_rewrites_dependency_package_ids(tmp_path):
    store = _store(tmp_path)
    owner = AgentOperationOwner(store)
    old_annotation = AnalysisWorkPackage.create(
        operation_type="text_analysis",
        task_kind="source_annotation",
        capability_role="low_cost_annotator",
        requested_output_types=("source_annotation",),
        source_revision_ids=("source:dependency:v1",),
        model_revision="source-annotation:legacy",
        allowed_evidence_ids=("evidence:dependency",),
        private_evidence={"statement": "Dependency evidence"},
        prompt_contract_id="matters.semantic-understanding",
        prompt_contract_revision="v1",
        output_schema_id="matters.agent-operation-result.v1",
    )
    old_semantic = AnalysisWorkPackage.create(
        operation_type="text_analysis",
        task_kind="semantic_understanding",
        capability_role="matter_modeler",
        requested_output_types=("matter_candidate",),
        dependency_package_ids=(old_annotation.package_id,),
        source_revision_ids=("source:dependency:v1",),
        model_revision="semantic:legacy",
        allowed_evidence_ids=("evidence:dependency",),
        private_evidence={"statement": "Dependent semantic evidence"},
        prompt_contract_revision="v2",
        output_schema_id="matters.agent-operation-result.v2",
    )
    store.append(
        "analysis_work_package",
        old_annotation.package_id,
        1,
        asdict(old_annotation),
    )
    store.append(
        "analysis_work_package",
        old_semantic.package_id,
        1,
        asdict(old_semantic),
    )

    batch = owner.rebase_work_packages_to_current_contract(limit=2)
    assert batch.rebased_package_count == 2
    annotation_receipt = store.current(
        "analysis_contract_rebase",
        old_annotation.package_id,
    )
    semantic_receipt = store.current(
        "analysis_contract_rebase",
        old_semantic.package_id,
    )
    current_semantic = store.current(
        "analysis_work_package",
        semantic_receipt["current_package_id"],
    )
    assert current_semantic["dependency_package_ids"] == [
        annotation_receipt["current_package_id"]
    ]


def _signal(kind, value, evidence_id):
    return ContextSignal(
        kind=kind,
        value=value,
        evidence_ids=(evidence_id,),
    )


def _append_context(store, matter_id, signals):
    store.append(
        "matter_context",
        matter_id,
        1,
        {
            "matter_id": matter_id,
            "semantic_identity_key": f"semantic:{matter_id}",
            "signals": tuple(asdict(signal) for signal in signals),
            "context_revision": 1,
            "freshness": "current",
            "broad_scope": False,
            "parent_matter_id": "",
        },
    )


def test_global_recall_finds_licensed_match_after_first_fifty_contexts(tmp_path):
    store = _store(tmp_path)
    shared_subject = "OpenAI Build Week"
    for index in range(60):
        _append_context(
            store,
            f"matter:{index:03d}",
            (
                _signal(
                    "subject",
                    shared_subject,
                    f"evidence:weak:{index}",
                ),
            ),
        )
    target_id = "matter:zzz-licensed"
    target_signals = (
        _signal("subject", shared_subject, "evidence:target:subject"),
        _signal(
            "goal",
            "Submit the Build Week project",
            "evidence:target:goal",
        ),
        _signal(
            "outcome",
            "Build Week submission accepted",
            "evidence:target:outcome",
        ),
    )
    _append_context(store, target_id, target_signals)
    incoming = ProjectContext(
        signals=(
            _signal("subject", shared_subject, "evidence:new:subject"),
            _signal(
                "goal",
                "Submit the Build Week project",
                "evidence:new:goal",
            ),
            _signal(
                "outcome",
                "Build Week submission accepted",
                "evidence:new:outcome",
            ),
        )
    )
    dispatcher = AutonomousFindingDispatcher.__new__(
        AutonomousFindingDispatcher
    )
    dispatcher.store = store

    candidates = dispatcher._placement_candidates(incoming)

    assert len(candidates) == 50
    assert candidates[0].matter_id == target_id
    assert target_id in {
        candidate.matter_id for candidate in candidates
    }
    decision = MatterReconciliationOwner(MatterAdmission()).reconcile(
        MatterReconciliationRequest(
            source_ids=("source:new:v1",),
            evidence_ids=("evidence:new:goal",),
            semantic_identity_key="Build Week participation",
            context=incoming,
            candidates=candidates,
            granularity=GranularityAssessment(
                independently_useful_goal=True
            ),
        )
    )
    assert decision.status == "append_to_current"
    assert decision.target_matter_id == target_id
