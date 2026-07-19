"""TM0/TM01-TM23 test inventory and exact evidence ownership."""

from __future__ import annotations

import json
from pathlib import Path

from flowguard.testmesh import (
    TestMeshPlan,
    TestPartitionItem,
    TestSuiteEvidence,
    TestTargetSplitDerivation,
    review_test_mesh,
)

from flowguard_design.inventory import (
    ALL_TEST_SUITES,
    MODEL_ORDER,
    MODEL_TEST_SUITES,
    MODELS,
    PARENT_ID,
)
from flowguard_design.transition_coverage import build_matrices


PARENT_SUITE_ID = "TM0_matters_whole_flow_gate"
INVENTORY_REVISION = "g4-testmesh-v3-autonomous-object-browser"

SUITE_EXTRA_TEST_PATHS = {
    "TM01_authorization_coverage": (
        "tests/test_partitioned_filesystem_runner.py",
        "tests/test_runtime_persistence_inventory.py",
    ),
    "TM03_evidence_qualification": (
        "tests/test_source_document_adapters.py",
        "tests/test_source_image_adapters.py",
    ),
    "TM11_guard_prediction_boundary": (
        "tests/test_analysis_operations_depth.py",
        "tests/test_researchguard_installation_probe.py",
        "tests/test_understanding_workflow.py",
    ),
    "TM12_projection_bilingual_ui": (
        "tests/test_entrypoint_ui.py",
        "tests/test_localization_registry.py",
    ),
    "TM14_end_to_end_conformance": (
        "tests/test_durable_work_recompute.py",
        "tests/test_entrypoint_cli.py",
        "tests/test_entrypoint_http.py",
        "tests/test_entrypoint_mcp.py",
        "tests/test_entrypoint_real_service.py",
    ),
    "TM15_connector_pagination_retry": (
        "tests/test_source_cloud_adapter.py",
        "tests/test_source_filesystem_adapter.py",
        "tests/test_source_gmail_adapter.py",
        "tests/test_source_workflows.py",
    ),
    "TM18_privacy_public_boundary": (
        "tests/test_private_aggregate.py",
        "tests/test_public_evidence_generators.py",
    ),
    "TM19_clean_install_release": (
        "tests/test_bundled_skill_pack.py",
        "tests/test_skill_active_view_resolver.py",
        "tests/test_skill_machine_discovery.py",
        "tests/test_skill_managed_projection.py",
        "tests/test_skill_manifest_inventory.py",
        "tests/test_skill_runtime_boundary.py",
        "tests/test_tm20_skill_runtime_model.py",
    ),
    "TM20_autonomous_owner_dispatch": (
        "tests/test_analysis_operations_depth.py",
        "tests/test_durable_work_recompute.py",
    ),
    "TM21_object_coverage_worker": (
        "tests/test_source_workflows.py",
    ),
    "TM22_representative_visual": (
        "tests/test_source_image_adapters.py",
        "tests/test_localization_registry.py",
    ),
    "TM23_desktop_object_browser": (
        "tests/test_entrypoint_ui.py",
        "tests/test_entrypoint_http.py",
    ),
}

SUITE_PRIMARY_TEST_PATHS = {
    "TM20_autonomous_owner_dispatch": "tests/test_understanding_workflow.py",
    "TM21_object_coverage_worker": "tests/test_runtime_persistence_inventory.py",
    "TM22_representative_visual": "tests/test_object_browser_autonomy.py",
    "TM23_desktop_object_browser": "tests/test_desktop.py",
}

SUITE_PURPOSES = {
    **{suite: f"model contract evidence for {model}" for model, suite in MODEL_TEST_SUITES.items()},
    "TM13_model_mesh_closure": "M0/C1-C12 parent-child reattachment and closure",
    "TM14_end_to_end_conformance": "synthetic whole-flow and M0 authority",
    "TM15_connector_pagination_retry": (
        "filesystem/Gmail provider-neutral metadata inventory, paging, retry, "
        "change sets, terminal dispositions, and no-delta freshness"
    ),
    "TM16_bilingual_semantic_equivalence": "English/zh-CN same-revision equivalence",
    "TM17_revocation_full_propagation": "C10 invalidation and original-owner recompute",
    "TM18_privacy_public_boundary": "external private roots and public inventory",
    "TM19_clean_install_release": (
        "clean clone/package, immutable Skill Pack, active view, optional "
        "managed projection, ResearchGuard gate, Git, and local release proof"
    ),
    "TM20_autonomous_owner_dispatch": (
        "WorkPackageV2 input accounting, typed bilingual findings, durable "
        "idempotent automatic original-owner dispatch, retry and restart"
    ),
    "TM21_object_coverage_worker": (
        "ObjectCoverageLedger, autonomous worker, blocked-object isolation, "
        "no-delta rescan, and restart recovery"
    ),
    "TM22_representative_visual": (
        "safe visual derivatives, exact visual anchors, Matter relations, "
        "deterministic recommendation/selection, placeholders and correction"
    ),
    "TM23_desktop_object_browser": (
        "Databank-authority object browser, Standard/Compact, search/filter, "
        "detail/timeline, bilingual state, focus, responsive and desktop runtime"
    ),
}


def _suite_model(suite_id: str) -> str:
    for model_id, candidate in MODEL_TEST_SUITES.items():
        if candidate == suite_id:
            return model_id
    if suite_id == "TM14_end_to_end_conformance":
        return PARENT_ID
    return ""


def test_path(suite_id: str) -> str:
    return SUITE_PRIMARY_TEST_PATHS.get(
        suite_id,
        f"tests/test_{suite_id.lower()}.py",
    )


def test_paths(suite_id: str) -> tuple[str, ...]:
    return (test_path(suite_id), *SUITE_EXTRA_TEST_PATHS.get(suite_id, ()))


def build_plan(receipt_root: Path | None = None) -> TestMeshPlan:
    matrix_by_model = {matrix.model_id: matrix for matrix in build_matrices()}
    partition_items = tuple(
        TestPartitionItem(
            item_id=f"TI-{suite_id}",
            item_type="behavior",
            owner_suite_id=suite_id,
            ownership="child",
            description=SUITE_PURPOSES[suite_id],
            inventory_revision=INVENTORY_REVISION,
        )
        for suite_id in ALL_TEST_SUITES
    )
    suites: list[TestSuiteEvidence] = []
    for suite_id in ALL_TEST_SUITES:
        model_id = _suite_model(suite_id)
        matrix = matrix_by_model.get(model_id)
        cell_ids = matrix.required_cell_ids() if matrix else ()
        spec = MODELS.get(model_id)
        is_release = suite_id == "TM19_clean_install_release"
        planned = TestSuiteEvidence(
                suite_id=suite_id,
                command=(
                    "python -m pytest -q "
                    + " ".join(test_paths(suite_id))
                ),
                layer="release" if is_release else "child",
                result_status="not_run",
                evidence_tier="candidate_only",
                evidence_current=True,
                test_count=len(cell_ids) or 1,
                selected_count=0,
                skipped_count=0,
                planned_count=len(cell_ids) or 1,
                executed_count=0,
                failed_count=0,
                not_run_count=len(cell_ids) or 1,
                diagnostic_campaign_id=f"G4-{suite_id}-planned",
                diagnostic_boundary="targeted",
                skipped_visible=True,
                exit_code=None,
                result_path=(
                    f".flowguard/evidence/tests/{suite_id}.json"
                ),
                has_exit_artifact=False,
                has_result_artifact=False,
                release_required=is_release,
                owns_state=spec.owned_write_fields if spec else (),
                owns_side_effects=spec.side_effect_classes if spec else (),
                owned_leaf_cell_ids=cell_ids,
                not_run_reason="G4 design inventory only; implementation not started",
                inventory_revision=INVENTORY_REVISION,
                owned_inventory_item_ids=(f"TI-{suite_id}",),
                covered_obligation_ids=tuple(
                    f"transition_coverage:{cell_id}" for cell_id in cell_ids
                ),
            )
        receipt_path = (
            receipt_root / f"{suite_id}.json" if receipt_root is not None else None
        )
        if receipt_path is not None and receipt_path.is_file():
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            planned = TestSuiteEvidence(**payload["test_suite_evidence"])
        suites.append(planned)
    all_cells = tuple(
        cell_id
        for matrix in matrix_by_model.values()
        for cell_id in matrix.required_cell_ids()
    )
    release_item_id = "TI-TM19_clean_install_release"
    required_inventory_ids = tuple(item.item_id for item in partition_items)
    scoped_inventory_reasons = {}
    if receipt_root is not None:
        required_inventory_ids = tuple(
            item_id for item_id in required_inventory_ids if item_id != release_item_id
        )
        scoped_inventory_reasons = {
            release_item_id: "TM19 is owned by the frozen G12 release gate"
        }
    return TestMeshPlan(
        parent_suite_id=PARENT_SUITE_ID,
        partition_items=partition_items,
        child_suites=tuple(suites),
        target_split_derivation=TestTargetSplitDerivation(
            source_model_id=PARENT_ID,
            target_suite_ids=ALL_TEST_SUITES,
            covered_partition_item_ids=tuple(item.item_id for item in partition_items),
            state_owner_fields=tuple(
                field
                for model_id in MODEL_ORDER
                for field in MODELS[model_id].owned_write_fields
            ),
            side_effect_owner_fields=tuple(
                effect
                for model_id in MODEL_ORDER
                for effect in MODELS[model_id].side_effect_classes
            ),
            source_model_path="flowguard_models/",
            rationale=(
                "The model hierarchy determines exact state, side-effect, "
                "transition-cell, and cross-cutting suite ownership."
            ),
            derived_from_flowguard_model=True,
        ),
        required_leaf_cell_ids=all_cells,
        required_evidence_tier="abstract_green",
        require_proof_artifacts=receipt_root is not None,
        decision_scope="routine",
        release_deferred_allowed=True,
        inventory_revision=INVENTORY_REVISION,
        required_inventory_item_ids=required_inventory_ids,
        scoped_inventory_item_reasons=scoped_inventory_reasons,
        require_complete_inventory=True,
        require_final_receipts=False,
    )


def run_review(receipt_root: Path | None = None):
    plan = build_plan(receipt_root)
    return plan, review_test_mesh(plan)


__all__ = [
    "INVENTORY_REVISION",
    "PARENT_SUITE_ID",
    "SUITE_PURPOSES",
    "SUITE_EXTRA_TEST_PATHS",
    "build_plan",
    "run_review",
    "test_path",
    "test_paths",
]
