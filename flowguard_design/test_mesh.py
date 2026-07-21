"""TM0/TM01-TM27 test inventory and exact evidence ownership."""

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
    AGENT_OPERATION_MODELS,
    AGENT_OPERATION_ORDER,
    AGENT_OPERATION_TEST_SUITES,
    ALL_TEST_SUITES,
    MODEL_ORDER,
    MODEL_TEST_SUITES,
    MODELS,
    PARENT_ID,
)
from flowguard_design.transition_coverage import build_matrices


PARENT_SUITE_ID = "TM0_matters_whole_flow_gate"
INVENTORY_REVISION = "g4-testmesh-v15-exact-source-and-install-closure"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

HIERARCHY_MODEL_IDS = {
    "M0_matters_end_to_end_authority",
    "C5_event_temporal_trace",
    "C6_matter_formation_admission",
    "C7_lifecycle_board_state",
    "C8_open_loop_waiting_blocking",
    "C9_completion_cancellation_reopen",
    "C10_correction_revocation",
    "C11_guard_artifact_prediction",
    "C12_projection_bilingual_ui",
    "A2_matters_maintenance_orchestrator_operation",
    "A3_matters_ai_gateway_operation",
}

SUITE_EXTRA_TEST_PATHS = {
    "TM01_authorization_coverage": (
        "tests/test_current_scope_reconciliation.py",
        "tests/test_inventory_policy_rebase.py",
        "tests/test_partitioned_filesystem_runner.py",
    ),
    "TM03_evidence_qualification": (
        "tests/test_source_document_adapters.py",
        "tests/test_source_image_adapters.py",
    ),
    "TM02_source_registry": (
        "tests/test_source_group_service.py",
        "tests/test_source_in_place_migration.py",
        "tests/test_source_in_place_storage_policy.py",
    ),
    "TM05_event_trace": (
        "tests/test_matter_activity.py",
        "tests/test_start_boundary.py",
    ),
    "TM06_matter_admission": (
        "tests/test_matter_hierarchy.py",
        "tests/test_matter_hierarchy_stress.py",
        "tests/test_matter_reconciliation.py",
        "tests/test_situation_graph.py",
        "tests/test_source_revision_reconciliation.py",
    ),
    "TM11_guard_prediction_boundary": (
        "tests/test_matter_semantic_depth.py",
        "tests/test_world_inference.py",
    ),
    "TM12_projection_bilingual_ui": (
        "tests/test_matter_presentation_reconciliation.py",
        "tests/test_object_browser_autonomy.py",
        "tests/test_object_browser_catalog_query.py",
        "tests/test_semantic_data_layer_projection.py",
        "tests/test_source_group_projection.py",
    ),
    "TM14_end_to_end_conformance": (
        "tests/test_entrypoint_cli.py",
        "tests/test_entrypoint_http.py",
        "tests/test_entrypoint_mcp.py",
        "tests/test_entrypoint_real_service.py",
    ),
    "TM15_connector_pagination_retry": (
        "tests/test_gmail_body_continuation.py",
        "tests/test_gmail_ingest_safety.py",
        "tests/test_source_cloud_adapter.py",
        "tests/test_source_filesystem_adapter.py",
        "tests/test_source_gmail_adapter.py",
        "tests/test_source_workflows.py",
    ),
    "TM16_bilingual_semantic_equivalence": (
        "tests/test_localization_registry.py",
    ),
    "TM18_privacy_public_boundary": (
        "tests/test_private_aggregate.py",
        "tests/test_public_evidence_generators.py",
    ),
    "TM19_clean_install_release": (
        "tests/test_bundled_skill_pack.py",
        "tests/test_bundled_skill_pack_contracts.py",
        "tests/test_desktop_manifest.py",
        "tests/test_desktop_package_contract.py",
        "tests/test_install_local_transaction.py",
        "tests/test_skill_active_view_resolver.py",
        "tests/test_skill_machine_discovery.py",
        "tests/test_skill_managed_projection.py",
        "tests/test_skill_manifest_inventory.py",
        "tests/test_skill_runtime_boundary.py",
        "tests/test_tm20_skill_runtime_model.py",
    ),
    "TM20_autonomous_owner_dispatch": (
        "tests/test_analysis_operations_depth.py",
        "tests/test_codex_provider.py",
        "tests/test_contract_rebase_and_global_recall.py",
        "tests/test_durable_work_recompute.py",
        "tests/test_execution_profiles.py",
    ),
    "TM21_object_coverage_worker": (
        "tests/test_coverage_audit.py",
        "tests/test_sqlite_store_scale_kernel.py",
    ),
    "TM23_desktop_object_browser": (
        "tests/test_entrypoint_ui.py",
    ),
    "TM27_ai_gateway": (
        "tests/test_mcp_stdio.py",
    ),
}

SUITE_PRIMARY_TEST_PATHS = {
    "TM20_autonomous_owner_dispatch": "tests/test_understanding_workflow.py",
    "TM21_object_coverage_worker": "tests/test_runtime_persistence_inventory.py",
    "TM22_generated_hero": "tests/test_generated_hero.py",
    "TM23_desktop_object_browser": "tests/test_desktop.py",
    "TM24_research_operation": "tests/test_researchguard_installation_probe.py",
    "TM25_daily_codex_maintenance": "tests/test_autonomous_maintenance.py",
    "TM26_maintenance_orchestrator": "tests/test_maintenance_orchestration.py",
    "TM27_ai_gateway": "tests/test_ai_gateway.py",
}

SUITE_PURPOSES = {
    **{suite: f"model contract evidence for {model}" for model, suite in MODEL_TEST_SUITES.items()},
    "TM05_event_trace": (
        "C5 Event identity, temporal trace, MaterialClue materiality, "
        "latest meaningful clue time, ancestor activity propagation, and "
        "parent-narrative refresh triggers that never replace clue-time authority, "
        "logical-event revision/supersession deduplication, plus "
        "Event-never-mechanically-becomes-Matter contracts"
    ),
    "TM06_matter_admission": (
        "C6 root/child Matter, WorkItem/Event/Source classification; one acyclic "
        "primary parent; role; depth; complete parent-narrative scope; "
        "split/merge/reparent contracts; and rejection of projection/source/"
        "candidate identities unless C6 supplies the exact admitted matter_id; "
        "ordinary Sub-matters projects Matter nodes only, reconciles travel/software "
        "portfolio roots, and preserves typed cross-domain relations"
    ),
    "TM07_lifecycle_board_state": (
        "C7 child-state snapshots, non-mechanical lifecycle rollup, related-edge "
        "exclusion, unknown-denominator contracts, and lifecycle/modality separation"
    ),
    "TM08_open_loop_blocking": (
        "C8 required/optional/critical child blocking and ancestor rollup contracts"
    ),
    "TM09_completion_reopen": (
        "C9 child-outcome rollup and parent-completion non-mechanical contracts"
    ),
    "TM10_correction_invalidation": (
        "C10 old/new ancestor invalidation, exact observation-time correction "
        "propagation, MaterialClue/summary/activity/supplemental recompute, exact "
        "generated-hero invalidation, and identity-preserving split/merge dispositions"
    ),
    "TM11_guard_prediction_boundary": (
        "C11 seven capability roles, advisory hierarchy/human-narrative/hero-brief/"
        "nonempty-or-explicitly-unavailable supplemental packages, privacy "
        "minimization, and zero canonical containment writes"
    ),
    "TM12_projection_bilingual_ui": (
        "C12 root-only latest-meaningful-clue catalog, atomic bilingual summary/order, "
        "indexed filter/order/page selection before bounded visible-card hydration, "
        "complete-scope bilingual parent narrative with a narrow write boundary, "
        "exact C6-admitted matter_id retention with noncanonical projection exclusion, "
        "qualified exact child search, a minimal human Overview, eight exact detail sections, generated hero "
        "outside evidence, AI supplemental information, Files & information columns/"
        "wrapped subordinate typography/disclosure, Images evidence gallery zoom/reset/"
        "pan/keyboard, truthful compact indexed coverage, Matter-only hierarchy with "
        "one reusable node quick view, logical-event timeline deduplication, lifecycle/"
        "modality visual separation, and bilingual projection"
    ),
    "TM13_model_mesh_closure": (
        "M0/C1-C12 plus A0/A1/A2 reattachment, orchestration joins, hierarchy/"
        "MaterialClue/hero token consumers, finite retry, and closure"
    ),
    "TM14_end_to_end_conformance": (
        "synthetic whole-flow and ordered M0 per-object source/Matter stage authority "
        "through MaterialClue, summary/activity, generated hero, supplemental information, "
        "UI projection, and UI reachability"
    ),
    "TM15_connector_pagination_retry": (
        "filesystem/Gmail provider-neutral metadata inventory, paging, retry, "
        "change sets, terminal dispositions, no-delta freshness, and content-selection "
        "semantic identity that excludes a scan-only inventory revision, plus "
        "strict private-manifest Gmail body continuation, minimal projection, "
        "current-metadata gate, proof-bound no-text terminal without fake "
        "SourceVersion/Evidence, plus exact-owner-gated terminal-page metadata "
        "SourceVersion reconciliation with <=500 cursor batches, body-depth "
        "preservation, zero semantic writes, and exact-retry no-delta behavior"
    ),
    "TM16_bilingual_semantic_equivalence": (
        "English/zh-CN same-revision title, summary, generated-hero alt, "
        "AI supplemental information, and stable activity-order equivalence"
    ),
    "TM17_revocation_full_propagation": (
        "C10 invalidation, old/new ancestor propagation, and original-owner recompute"
    ),
    "TM18_privacy_public_boundary": (
        "external private roots, public inventory, privacy-minimized generated-hero briefs, "
        "private generated assets, and zero local/Gmail payload publication"
    ),
    "TM19_clean_install_release": (
        "clean clone/package, immutable Skill Pack, active view, optional "
        "managed projection, ResearchGuard gate, Git, and local release proof"
    ),
    "TM20_autonomous_owner_dispatch": (
        "A0 one bounded model-agnostic WorkPackageV2 capability role, replaceable private "
        "execution profile, current-contract rebasing, global reconciliation recall, "
        "input accounting, substitution, escalation, visible "
        "unavailability, no app-owned API-key fallback, typed bilingual findings, "
        "durable idempotent original-owner dispatch, retry and restart"
    ),
    "TM21_object_coverage_worker": (
        "per-occurrence and per-Matter stage coverage, materialized first exact gap, autonomous worker, "
        "blocked-object isolation, no-delta rescan, bounded anchor-set pointers, one full "
        "current coverage payload plus exact compressed noncurrent history, ordered bounded "
        "migration cursors, no startup migration/VACUUM, UI reachability, and restart recovery"
    ),
    "TM22_generated_hero": (
        "privacy-minimized generated-hero briefs, private generated assets, exact "
        "invalidation, pending/blocked placeholders, bilingual alt text, no real-image "
        "fallback, no evidence registration, and Images-gallery separation"
    ),
    "TM23_desktop_object_browser": (
        "Databank-authority root object browser, approved font and sidebar geometry, "
        "Standard/Compact, latest-meaningful-clue ordering, Start-time filter, eight exact "
        "detail sections, generated hero, AI supplemental information, Files table, "
        "Images evidence gallery with wheel/pan/keyboard, screenshot/DOM non-overlap, "
        "qualified child search, stale-card retention, retry/auto-reconnect, "
        "Matter-only graph plus one reusable node quick view, human Overview, logical "
        "timeline, compact coverage drilldown, bilingual focus/responsive desktop runtime"
    ),
    "TM24_research_operation": (
        "A1 single frozen ResearchGuard provider identity, current/pending terminal "
        "receipt, legacy separate-Guard fallback rejection, and zero product writes"
    ),
    "TM25_daily_codex_maintenance": (
        "daily Codex adapter using strongest-compatible primary planning and bounded "
        "low-cost delegation, manual rehearsal, no-delta terminal, interruption "
        "recovery, zero source/mail/outbound/grant/code/model/install/Git/tag/"
        "release mutation, and final-gate ownership remaining foreground-only"
    ),
    "TM26_maintenance_orchestrator": (
        "A2 strongest-compatible primary Codex maintenance plan, bounded A0/A1 "
        "delegation, validated joins, finite retry, no provider/model authority in "
        "public product state, pending A3 feedback original-owner terminal receipts, "
        "and no release/final-validation authority"
    ),
    "TM27_ai_gateway": (
        "A3 bounded model-map, situation/history query receipts, minimized append-only "
        "feedback, visible pending original-owner dispatch, ResearchGuard dependency "
        "status, zero canonical product writes, and zero A2 completion authority"
    ),
}


def _suite_model(suite_id: str) -> str:
    for model_id, candidate in MODEL_TEST_SUITES.items():
        if candidate == suite_id:
            return model_id
    for model_id, candidate in AGENT_OPERATION_TEST_SUITES.items():
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


def _test_file_item_id(path: str) -> str:
    return "TI-FILE-" + (
        path.removeprefix("tests/")
        .removesuffix(".py")
        .replace("/", "-")
        .replace("_", "-")
    )


def test_file_inventory() -> dict[str, object]:
    """Return the independent repository inventory and its exact suite owners."""

    discovered_paths = tuple(
        sorted(
            path.relative_to(REPOSITORY_ROOT).as_posix()
            for path in (REPOSITORY_ROOT / "tests").glob("test_*.py")
            if path.is_file()
        )
    )
    owners: dict[str, list[str]] = {}
    for suite_id in ALL_TEST_SUITES:
        for path in test_paths(suite_id):
            owners.setdefault(path, []).append(suite_id)
    referenced_paths = tuple(sorted(owners))
    return {
        "discovered_paths": discovered_paths,
        "referenced_paths": referenced_paths,
        "owners": {
            path: tuple(owner_ids)
            for path, owner_ids in sorted(owners.items())
        },
        "unowned_paths": tuple(
            path for path in discovered_paths if path not in owners
        ),
        "duplicate_owned_paths": {
            path: tuple(owner_ids)
            for path, owner_ids in sorted(owners.items())
            if len(owner_ids) != 1
        },
        "missing_referenced_paths": tuple(
            path for path in referenced_paths if path not in discovered_paths
        ),
    }


def build_plan(receipt_root: Path | None = None) -> TestMeshPlan:
    matrix_by_model = {matrix.model_id: matrix for matrix in build_matrices()}
    file_inventory = test_file_inventory()
    inventory_gaps = {
        key: file_inventory[key]
        for key in (
            "unowned_paths",
            "duplicate_owned_paths",
            "missing_referenced_paths",
        )
        if file_inventory[key]
    }
    if inventory_gaps:
        raise ValueError(
            "test-file ownership inventory is incomplete: "
            + json.dumps(inventory_gaps, sort_keys=True)
        )
    owners = file_inventory["owners"]
    suite_partition_items = tuple(
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
    file_partition_items = tuple(
        TestPartitionItem(
            item_id=_test_file_item_id(path),
            item_type="test_file",
            owner_suite_id=owners[path][0],
            ownership="child",
            description=(
                f"exact test-file evidence owned only by {owners[path][0]}"
            ),
            touched_paths=(path,),
            inventory_revision=INVENTORY_REVISION,
        )
        for path in file_inventory["discovered_paths"]
    )
    partition_items = suite_partition_items + file_partition_items
    file_item_ids_by_suite = {
        suite_id: tuple(
            _test_file_item_id(path)
            for path in test_paths(suite_id)
        )
        for suite_id in ALL_TEST_SUITES
    }
    suites: list[TestSuiteEvidence] = []
    for suite_id in ALL_TEST_SUITES:
        model_id = _suite_model(suite_id)
        matrix = matrix_by_model.get(model_id)
        cell_ids = matrix.required_cell_ids() if matrix else ()
        spec = MODELS.get(model_id) or AGENT_OPERATION_MODELS.get(model_id)
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
                not_run_reason=(
                    "model/UI/operation inventory changed; implementation, "
                    "external-contract tests, and runtime conformance are not run"
                    if model_id in HIERARCHY_MODEL_IDS
                    or model_id in AGENT_OPERATION_ORDER
                    or suite_id == "TM25_daily_codex_maintenance"
                    else "G4 design inventory only; implementation not started"
                ),
                inventory_revision=INVENTORY_REVISION,
                owned_inventory_item_ids=(
                    f"TI-{suite_id}",
                    *file_item_ids_by_suite[suite_id],
                ),
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
    release_item_ids = {
        "TI-TM19_clean_install_release",
        *file_item_ids_by_suite["TM19_clean_install_release"],
    }
    required_inventory_ids = tuple(item.item_id for item in partition_items)
    scoped_inventory_reasons = {}
    if receipt_root is not None:
        required_inventory_ids = tuple(
            item_id
            for item_id in required_inventory_ids
            if item_id not in release_item_ids
        )
        scoped_inventory_reasons = {
            item_id: "TM19 is owned by the frozen G12 release gate"
            for item_id in sorted(release_item_ids)
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
            )
            + tuple(
                field
                for model_id in AGENT_OPERATION_ORDER
                for field in AGENT_OPERATION_MODELS[model_id].owned_write_fields
            ),
            side_effect_owner_fields=tuple(
                effect
                for model_id in MODEL_ORDER
                for effect in MODELS[model_id].side_effect_classes
            )
            + tuple(
                effect
                for model_id in AGENT_OPERATION_ORDER
                for effect in AGENT_OPERATION_MODELS[model_id].side_effect_classes
            ),
            source_model_path=(
                "flowguard_models/;flowguard_models/agent_operation_models.py;"
                "flowguard_design/ui_flow_structure.py"
            ),
            rationale=(
                "The product hierarchy, agent-operation plane, UI-flow model, "
                "and development-process schedule boundary determine exact "
                "state, side-effect, transition-cell, and cross-cutting suite "
                "ownership without sharing pass evidence across planes."
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
    "test_file_inventory",
    "test_path",
    "test_paths",
]
