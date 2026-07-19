"""Freeze the existing-owner decision for the candidate source universe."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

from flowguard import (
    BehaviorCommitmentHit,
    ExistingIntentSurface,
    ExistingModelPreflight,
    ExistingOwnershipSnapshot,
    ModelContextHit,
    review_existing_model_preflight,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flowguard_models.run_model import MODELS


LEDGER_PATH = ROOT / ".flowguard" / "behavior_commitment_ledger" / "ledger.json"
OUTPUT_PATH = (
    ROOT
    / ".flowguard"
    / "evidence"
    / "preflight"
    / "candidate_universe_existing_model_preflight.json"
)
CHANGE_ROOT = (
    ROOT / "openspec" / "changes" / "build-matters-model-driven-core"
)
PARENT_ID = "M0_matters_end_to_end_authority"
PROCESS_OWNER_ID = "DPF_matters_delivery_gate"
SKILL_RUNTIME_OWNER_ID = "S0_matters_skill_runtime"
SOURCE_ANALYSIS_OWNER_ID = "A0_matters_source_analysis_operation"
RESEARCH_OWNER_ID = "A1_matters_research_operation"
SCOPE_REVISION = "autonomous-object-browser-v2"
REUSE_MAP = {
    "M0_matters_end_to_end_authority": "extend_with_object_coverage_ledger_worker_and_ui_readiness",
    "C1_authorization_coverage": "replace_review_with_automatic_reversible_terminal_dispositions",
    "C2_source_registry": "extend_with_safe_visual_derivatives_and_freshness",
    "C3_evidence_qualification": "extend_with_visual_anchors_display_permission_and_eligibility",
    "C4_person_entity_resolution": "preserve_separate_uncertain_identities_without_confirmation",
    "C5_event_temporal_trace": "preserve_conflict_and_publish_best_supported_human_readable_time",
    "C6_matter_formation_admission": "replace_review_with_autonomous_terminal_admission_and_visual_relations",
    "C7_lifecycle_board_state": "replace_review_with_uncertainty_preserved_lifecycle_projection",
    "C8_open_loop_waiting_blocking": "replace_review_with_gap_and_not_applicable_terminals",
    "C9_completion_cancellation_reopen": "replace_review_with_completion_gap_and_outcome_conflict_terminals",
    "C10_correction_revocation": "extend_with_optional_visual_correction_and_original_owner_recompute",
    "C11_guard_artifact_prediction": "replace_confirmation_with_workpackage_v2_input_accounting_and_auto_dispatch",
    "C12_projection_bilingual_ui": "replace_review_workspace_with_bilingual_desktop_object_browser",
    "DPF_matters_delivery_gate": "extend_progressive_autonomous_first_run_skill_pack_desktop_and_release_gates",
    "S0_matters_skill_runtime": "add_auxiliary_non_product_skill_runtime_boundary",
    "A0_matters_source_analysis_operation": "add_agent_operation_boundary",
    "A1_matters_research_operation": "add_abstract_researchoperation_boundary",
}


def _sha256(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _aggregate_hash(paths: tuple[Path, ...]) -> str:
    digest = sha256()
    for path in sorted(paths, key=lambda item: item.as_posix()):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _openspec_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            (
                path
                for path in CHANGE_ROOT.rglob("*")
                if path.is_file()
                and (
                    path.name in {"proposal.md", "design.md", "tasks.md"}
                    or path.name == "spec.md"
                )
            ),
            key=lambda item: item.as_posix(),
        )
    )


def _model_path(model_id: str) -> str:
    for path in (ROOT / "flowguard_models" / "models").glob("*.py"):
        if path.name == "__init__.py":
            continue
        if f'model_id="{model_id}"' in path.read_text(encoding="utf-8"):
            return path.relative_to(ROOT).as_posix()
    raise RuntimeError(f"model source not found for {model_id}")


def _optional_owner_source(model_id: str) -> str:
    for path in (ROOT / "flowguard_models").rglob("*.py"):
        if model_id in path.read_text(encoding="utf-8"):
            return path.relative_to(ROOT).as_posix()
    return ""


def _commitments() -> dict[str, dict]:
    payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    return {
        str(row["commitment_id"]): row
        for row in payload["ledger"]["commitments"]
    }


def _product_model_hits() -> tuple[ModelContextHit, ...]:
    children = tuple(model_id for model_id in MODELS if model_id != PARENT_ID)
    hits = []
    for model_id, spec in MODELS.items():
        is_parent = model_id == PARENT_ID
        model_path = _model_path(model_id)
        hits.append(
            ModelContextHit(
                model_id=model_id,
                model_path=model_path,
                evidence_id=f"source:{_sha256(ROOT / model_path)}",
                evidence_tier="candidate_only",
                evidence_current=False,
                responsibilities=(spec.modeled_boundary,),
                function_blocks=tuple(rule.case_id for rule in spec.rules),
                state_owned=spec.state_fields,
                side_effects_owned=spec.side_effect_classes,
                fields_owned=spec.owned_write_fields,
                parent_model_id="" if is_parent else PARENT_ID,
                child_model_ids=children if is_parent else (),
                layered_proof_evidence_id=(
                    "stale:.flowguard/evidence/model_mesh/MM0_matters_parent_child_mesh.json"
                    if is_parent
                    else ""
                ),
                parent_coverage_status=(
                    "stale_requires_candidate_universe_revalidation"
                    if is_parent
                    else ""
                ),
                child_disjointness_status=(
                    "stale_requires_candidate_universe_revalidation"
                    if is_parent
                    else ""
                ),
                child_reattachment_status=(
                    "stale_requires_candidate_universe_revalidation"
                    if is_parent
                    else ""
                ),
                leaf_boundary_matrix_status=(
                    "stale_requires_candidate_universe_revalidation"
                    if is_parent
                    else ""
                ),
                validation_evidence=(
                    "prior Jira-shaped model and mesh receipts are stale",
                    "this hit proves source discovery and ownership context only",
                ),
                rationale=REUSE_MAP[model_id],
            )
        )
    return tuple(hits)


def _process_hit() -> ModelContextHit:
    path = ROOT / "flowguard_models" / "delivery_flow.py"
    return ModelContextHit(
        model_id=PROCESS_OWNER_ID,
        model_path=path.relative_to(ROOT).as_posix(),
        evidence_id=f"source:{_sha256(path)}",
        evidence_tier="candidate_only",
        evidence_current=False,
        responsibilities=(
            "development gate order and evidence freshness",
            "progressive private first-run sequencing",
            "Model Miss handoff into ordinary development",
        ),
        function_blocks=(
            "capture_delivery_snapshot",
            "build_plan",
            "build_receipt",
        ),
        state_owned=(
            "development_gate.status",
            "validation_evidence.freshness",
            "private_first_run.status",
            "maintenance.model_miss_work_item",
        ),
        side_effects_owned=(
            "authorize only current descendants",
            "emit typed blocked next actions",
        ),
        fields_owned=(
            "development_gate.status",
            "validation_evidence.freshness",
            "private_first_run.status",
            "maintenance.model_miss_work_item",
        ),
        validation_evidence=(
            "prior G8/Jira delivery-flow receipt is stale",
            "source is retained only as the existing process-owner context",
        ),
        rationale=REUSE_MAP[PROCESS_OWNER_ID],
    )


def _optional_auxiliary_hits() -> tuple[ModelContextHit, ...]:
    rows = []
    for model_id, responsibilities, states in (
        (
            SKILL_RUNTIME_OWNER_ID,
            (
                "app-local Skill Pack inventory",
                "compatible active-view resolution",
                "Matters-managed synchronization and rollback",
                "external ResearchGuard integration currentness",
            ),
            (
                "skill_runtime.bundle_identity",
                "skill_runtime.active_view_identity",
                "skill_runtime.managed_projection_identity",
                "skill_runtime.researchguard_integration_identity",
            ),
        ),
        (
            SOURCE_ANALYSIS_OWNER_ID,
            ("bounded text, multimodal, and OCR agent operations",),
            (
                "agent_operation.analysis_status",
                "agent_operation.source_analysis_terminal_receipt",
            ),
        ),
        (
            RESEARCH_OWNER_ID,
            ("abstract ResearchOperation and single ResearchGuard provider",),
            (
                "agent_operation.research_status",
                "agent_operation.researchguard_identity",
                "agent_operation.research_terminal_receipt",
            ),
        ),
    ):
        source = _optional_owner_source(model_id)
        if not source:
            continue
        rows.append(
            ModelContextHit(
                model_id=model_id,
                model_path=source,
                evidence_id=f"source:{_sha256(ROOT / source)}",
                evidence_tier="candidate_only",
                evidence_current=False,
                responsibilities=responsibilities,
                state_owned=states,
                fields_owned=states,
                validation_evidence=(
                    "source boundary discovered; native execution evidence is not claimed",
                ),
                rationale=REUSE_MAP[model_id],
            )
        )
    return tuple(rows)


def _ownership_snapshot(
    product_hits: tuple[ModelContextHit, ...],
    auxiliary_hits: tuple[ModelContextHit, ...],
) -> ExistingOwnershipSnapshot:
    return ExistingOwnershipSnapshot(
        function_block_owners=tuple(
            (rule.case_id, model_id)
            for model_id, spec in MODELS.items()
            for rule in spec.rules
        )
        + (
            ("capture_delivery_snapshot", PROCESS_OWNER_ID),
            ("build_plan", PROCESS_OWNER_ID),
            ("build_receipt", PROCESS_OWNER_ID),
        ),
        state_owners=tuple(
            (field_id, model_id)
            for model_id, spec in MODELS.items()
            for field_id in spec.state_fields
        )
        + tuple(
            (field_id, hit.model_id)
            for hit in auxiliary_hits
            for field_id in hit.state_owned
        ),
        side_effect_owners=tuple(
            (effect_id, model_id)
            for model_id, spec in MODELS.items()
            for effect_id in spec.side_effect_classes
        )
        + (
            ("authorize only current descendants", PROCESS_OWNER_ID),
            ("emit typed blocked next actions", PROCESS_OWNER_ID),
        ),
        field_owners=tuple(
            (field_id, model_id)
            for model_id, spec in MODELS.items()
            for field_id in spec.owned_write_fields
        )
        + tuple(
            (field_id, hit.model_id)
            for hit in auxiliary_hits
            for field_id in hit.fields_owned
        ),
        responsibility_owners=tuple(
            (responsibility, hit.model_id)
            for hit in product_hits + (_process_hit(),) + auxiliary_hits
            for responsibility in hit.responsibilities
        ),
    )


def _intent_surfaces(ledger_fingerprint: str) -> tuple[ExistingIntentSurface, ...]:
    intent_id = "BI-DP-004-progressive-private-first-run"
    commitment_id = "BC-DP-004"
    path_id = "path:dpf-progressive-private-first-run"
    terminal = (
        "complete, researchguard_pending_integration, or blocked with typed next actions"
    )
    tasks = CHANGE_ROOT / "tasks.md"
    proposal = CHANGE_ROOT / "proposal.md"
    dpf = ROOT / "flowguard_models" / "delivery_flow.py"
    jira = ROOT / "docs" / "providers" / "jira-discovery-plan.md"
    return (
        ExistingIntentSurface(
            surface_id="surface:openspec:tasks-private-first-run",
            surface_kind="adapter",
            business_intent_id=intent_id,
            behavior_commitment_id=commitment_id,
            business_path_id=path_id,
            primary_path_id=path_id,
            expected_terminal=terminal,
            state_writes=(
                "private_first_run.status",
                "private_first_run.coverage_revision",
            ),
            owner_id=PROCESS_OWNER_ID,
            source_ref=tasks.relative_to(ROOT).as_posix(),
            evidence_ids=(_sha256(tasks), ledger_fingerprint),
            evidence_current=True,
            validation_boundary="strict OpenSpec validation and BCL mapping",
            rationale="The task provider delegates execution order to DPF.",
        ),
        ExistingIntentSurface(
            surface_id="surface:proposal:private-first-run",
            surface_kind="adapter",
            business_intent_id=intent_id,
            behavior_commitment_id=commitment_id,
            business_path_id=path_id,
            primary_path_id=path_id,
            expected_terminal=terminal,
            owner_id=PROCESS_OWNER_ID,
            source_ref=proposal.relative_to(ROOT).as_posix(),
            evidence_ids=(_sha256(proposal), ledger_fingerprint),
            evidence_current=True,
            validation_boundary="proposal/design/spec/task consistency",
            rationale="The proposal promises the process but does not own product state.",
        ),
        ExistingIntentSurface(
            surface_id="surface:dpf:progressive-private-first-run",
            surface_kind="helper",
            business_intent_id=intent_id,
            behavior_commitment_id=commitment_id,
            business_path_id=path_id,
            primary_path_id=path_id,
            expected_terminal=terminal,
            state_writes=(
                "private_first_run.status",
                "private_first_run.receipt_ids",
            ),
            owner_id=PROCESS_OWNER_ID,
            source_ref=dpf.relative_to(ROOT).as_posix(),
            evidence_ids=(_sha256(dpf), ledger_fingerprint),
            evidence_current=True,
            validation_boundary=(
                "DPF source ownership discovery; execution evidence remains stale"
            ),
            rationale="The existing DPF is extended rather than duplicated.",
        ),
        ExistingIntentSurface(
            surface_id="surface:legacy:jira-slice",
            surface_kind="compatibility",
            business_intent_id=intent_id,
            owner_id=PROCESS_OWNER_ID,
            source_ref=jira.relative_to(ROOT).as_posix(),
            evidence_ids=(_sha256(jira), ledger_fingerprint),
            evidence_current=True,
            in_scope=False,
            disposition="replaced",
            scoped_out_reason=(
                "Jira/Rovo are deferred and cannot close a v0.1 first-run gate."
            ),
            validation_boundary=(
                "source-only dormant adapter with zero required runtime, install, "
                "acceptance, or release authority"
            ),
            rationale="BC-DP-004 replaces the historical Jira-specific path.",
        ),
    )


def _spec_provider_context(
    ledger_fingerprint: str,
) -> dict:
    files = _openspec_files()
    artifact_ids = {
        path.relative_to(ROOT).as_posix(): _sha256(path) for path in files
    }
    text = "\n".join(path.read_text(encoding="utf-8") for path in files)
    required_markers = (
        "candidate",
        "ResearchOperation",
        "ResearchGuard",
        "Skill Pack",
        "tracked",
        "freshness",
        "depth",
    )
    provider_current = bool(files) and all(marker in text for marker in required_markers)
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))["ledger"]
    reconciliation_current = bool(
        ledger.get("current_revision") == "autonomous-object-browser-v2"
        and all(
            commitment_id in set(ledger.get("expected_commitment_ids", ()))
            for commitment_id in (
                "BC-DP-004",
                "BC-DP-005",
                "BC-DP-006",
                "BC-DP-007",
                "BC-DP-008",
                "BC-DP-009",
                "BC-AO-001",
                "BC-AO-002",
            )
        )
    )
    package_fingerprint = _aggregate_hash(files)
    reconciliation_fingerprint = _aggregate_hash(files + (LEDGER_PATH,))
    return {
        "context_id": (
            "openspec:build-matters-model-driven-core:"
            "autonomous-object-browser-v2"
        ),
        "provider_id": "openspec",
        "work_package_id": (
            "openspec:build-matters-model-driven-core:"
            "autonomous-object-browser-v2"
        ),
        "change_id": "build-matters-model-driven-core",
        "behavior_plane": "development_process",
        "read_only": True,
        "provider_owns_product_behavior": False,
        "current": provider_current and reconciliation_current,
        "reconciliation_current": reconciliation_current,
        "context_hash": package_fingerprint,
        "reconciliation_fingerprint": reconciliation_fingerprint,
        "ledger_fingerprint": ledger_fingerprint,
        "artifact_ids": artifact_ids,
        "target_commitment_ids": [
            "BC-DP-004",
            "BC-DP-005",
            "BC-DP-006",
            "BC-DP-007",
            "BC-DP-008",
            "BC-DP-009",
            "BC-AO-001",
            "BC-AO-002",
            "BC-PR-001",
            "BC-PR-002",
            "BC-PR-010",
            "BC-PR-011",
            "BC-PR-012",
        ],
        "typed_relation_ids": [
            "BC-DP-004:governs:BC-AO-001",
            "BC-DP-004:governs:BC-AO-002",
            "BC-DP-008:validates:BC-AO-002",
            "BC-DP-004:requires_evidence_from:BC-PR-001",
            "BC-DP-009:requires_evidence_from:BC-PR-010",
        ],
        "execution_bridge": False,
        "receipt_bridge": False,
    }


def build_preflight() -> ExistingModelPreflight:
    commitments = _commitments()
    primary = commitments["BC-DP-004"]
    ledger_fingerprint = _sha256(LEDGER_PATH)
    product_hits = _product_model_hits()
    auxiliary_hits = _optional_auxiliary_hits()
    relevant_models = (
        (_process_hit(),) + product_hits + auxiliary_hits
    )
    path_id = str(primary["path_authority"]["primary_path_id"])
    intent_id = str(primary["business_intent_id"])
    surfaces = _intent_surfaces(ledger_fingerprint)
    surface_inventory_revision = _aggregate_hash(
        (
            CHANGE_ROOT / "proposal.md",
            CHANGE_ROOT / "tasks.md",
            ROOT / "flowguard_models" / "delivery_flow.py",
            ROOT / "docs" / "providers" / "jira-discovery-plan.md",
            LEDGER_PATH,
        )
    )
    return ExistingModelPreflight(
        preflight_id=(
            "matters-autonomous-object-browser-existing-model-preflight"
        ),
        task_summary=(
            "Extend Matters for a frozen candidate source universe, automatic "
            "reversible terminal dispositions, durable inventory and ObjectCoverageLedger "
            "freshness/depth, WorkPackageV2 input accounting and automatic owner "
            "dispatch, representative visuals, the Databank-authority bilingual "
            "desktop object browser, one abstract ResearchOperation with the single "
            "ResearchGuard provider, an exact eleven-skill app-local pack, managed "
            "sync/rollback, autonomous progressive private first run, and bounded "
            "Model Miss self-maintenance without Jira/Rovo or legacy Guard fallbacks."
        ),
        mode="full",
        existing_modeled_system=True,
        model_search_performed=True,
        search_paths=(
            "flowguard_models/models",
            "flowguard_models/model_mesh.py",
            "flowguard_models/delivery_flow.py",
            ".flowguard/behavior_commitment_ledger/ledger.json",
            "flowguard_design",
            "openspec/changes/build-matters-model-driven-core",
            "docs/providers/jira-discovery-plan.md",
        ),
        behavior_lookup_required=True,
        behavior_lookup_status="performed",
        primary_behavior_plane="development_process",
        primary_commitment_hits=(
            BehaviorCommitmentHit(
                commitment_id="BC-DP-004",
                behavior_plane="development_process",
                primary_owner_model_id=PROCESS_OWNER_ID,
                score=100,
                match_reasons=(
                    "same progressive private-first-run process intent",
                    "existing DPF owns order and evidence freshness",
                    "Jira-specific predecessor is explicitly replaced",
                ),
            ),
        ),
        related_commitment_hits=(
            BehaviorCommitmentHit(
                commitment_id="BC-PR-001",
                behavior_plane="product_runtime",
                primary_owner_model_id="C1_authorization_coverage",
                score=95,
                match_reasons=("candidate scope and disposition evidence target",),
                hit_role="validation_target",
                relation_type="requires_evidence_from",
                relation_path=("BC-DP-004", "BC-PR-001"),
            ),
            BehaviorCommitmentHit(
                commitment_id="BC-PR-002",
                behavior_plane="product_runtime",
                primary_owner_model_id="C2_source_registry",
                score=94,
                match_reasons=("inventory snapshot and change-set evidence target",),
                hit_role="validation_target",
                relation_type="requires_evidence_from",
                relation_path=("BC-DP-004", "BC-PR-002"),
            ),
            BehaviorCommitmentHit(
                commitment_id="BC-PR-012",
                behavior_plane="product_runtime",
                primary_owner_model_id="C12_projection_bilingual_ui",
                score=92,
                match_reasons=("freshness, depth, and human-review evidence target",),
                hit_role="validation_target",
                relation_type="requires_evidence_from",
                relation_path=("BC-DP-004", "BC-PR-012"),
            ),
            BehaviorCommitmentHit(
                commitment_id="BC-AO-001",
                behavior_plane="agent_operation",
                primary_owner_model_id=SOURCE_ANALYSIS_OWNER_ID,
                score=90,
                match_reasons=("governed source-analysis operation",),
                hit_role="validation_target",
                relation_type="governs",
                relation_path=("BC-DP-004", "BC-AO-001"),
            ),
            BehaviorCommitmentHit(
                commitment_id="BC-AO-002",
                behavior_plane="agent_operation",
                primary_owner_model_id=RESEARCH_OWNER_ID,
                score=90,
                match_reasons=(
                    "governed ResearchOperation with visible pending integration",
                ),
                hit_role="validation_target",
                relation_type="governs",
                relation_path=("BC-DP-004", "BC-AO-002"),
            ),
        ),
        ledger_fingerprint=ledger_fingerprint,
        behavior_lookup_reason=(
            "The change is primarily a development lifecycle and integration "
            "rebase. DPF remains the single process owner; C1-C12 and agent "
            "operations are typed evidence targets and never merge into the "
            "development-process plane."
        ),
        relevant_models=relevant_models,
        ownership_snapshot=_ownership_snapshot(product_hits, auxiliary_hits),
        reuse_decision="extend_existing",
        downstream_routes=(
            "behavior_commitment_ledger",
            "model_first_function_flow",
            "model_mesh_maintenance",
            "field_lifecycle_mesh",
            "model_test_alignment",
            "test_mesh_maintenance",
            "development_process_flow",
            "agent_workflow_rehearsal",
            "ui_flow_structure",
            "model_miss_review",
        ),
        rationale=(
            "M0/C1-C12 retain product ownership and DPF retains process order. "
            "S0 is an auxiliary non-product skill-runtime boundary, while A0/A1 "
            "are agent-operation owners. No C13, Jira/Rovo gate, or three-Guard "
            "parallel runtime authority is introduced."
        ),
        proposed_new_boundaries=tuple(
            model_id
            for model_id in (
                SKILL_RUNTIME_OWNER_ID,
                SOURCE_ANALYSIS_OWNER_ID,
                RESEARCH_OWNER_ID,
            )
            if not _optional_owner_source(model_id)
        ),
        behavior_field_ids=tuple(
            field_id
            for spec in MODELS.values()
            for field_id in spec.owned_write_fields
        )
        + (
            "skill_runtime.bundle_identity",
            "skill_runtime.active_view_identity",
            "skill_runtime.managed_projection_identity",
            "skill_runtime.researchguard_integration_identity",
            "agent_operation.analysis_status",
            "agent_operation.research_status",
            "agent_operation.source_analysis_terminal_receipt",
            "agent_operation.research_terminal_receipt",
        ),
        field_lifecycle_required=True,
        field_lifecycle_model_ids=tuple(MODELS)
        + (
            SKILL_RUNTIME_OWNER_ID,
            SOURCE_ANALYSIS_OWNER_ID,
            RESEARCH_OWNER_ID,
        ),
        model_angle_review_required=False,
        similarity_review_required=False,
        affected_business_intent_id=intent_id,
        selected_commitment_id="BC-DP-004",
        selected_primary_path_id=path_id,
        expected_surface_ids=tuple(surface.surface_id for surface in surfaces),
        intent_surfaces=surfaces,
        surface_inventory_revision=surface_inventory_revision,
        surface_inventory_evidence_ids=(
            surface_inventory_revision,
            ledger_fingerprint,
        ),
        require_complete_surface_inventory=True,
        spec_context=_spec_provider_context(ledger_fingerprint),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    preflight = build_preflight()
    report = review_existing_model_preflight(preflight)
    core = {
        "reuse_map": REUSE_MAP,
        "preflight": preflight.to_dict(),
        "native_report": report.to_dict(),
    }
    fingerprint = "sha256:" + sha256(
        json.dumps(
            core,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    blockers = [
        finding.to_dict()
        for finding in report.findings
        if finding.severity == "blocker"
    ]
    payload = {
        "artifact_type": "matters.existing-model-preflight.v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "preflight_green" if report.ok else "blocked",
        "evidence_id": (
            "evidence:existing-model-preflight:"
            + fingerprint.removeprefix("sha256:")[:16]
        ),
        "preflight_fingerprint": fingerprint,
        **core,
        "blockers": blockers,
        "researchguard_status": "researchguard_pending_integration",
        "retired_runtime_bindings": {
            "SourceGuard": "stale_source_only",
            "TraceGuard": "stale_source_only",
            "LogicGuard": "stale_source_only",
        },
        "claim_boundary": (
            "This current receipt proves plane-first lookup, source/model "
            "discovery, ownership, reuse/extension, same-intent surface inventory, "
            "OpenSpec read-only context, and explicit legacy disposition only. "
            "It does not prove model execution, mesh closure, field lifecycle, "
            "agent operations, ResearchGuard availability, Skill Pack validation, "
            "TestMesh, runtime, private first run, install, or release. Model source "
            "edits after this fingerprint stale this receipt."
        ),
    }
    output = args.output
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
