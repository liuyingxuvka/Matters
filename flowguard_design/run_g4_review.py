"""Run the complete G4 design review and write bounded design receipts."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
from typing import Any

import flowguard

from flowguard_design.architecture import run_review as run_architecture
from flowguard_design.contract_exhaustion import run_review as run_contracts
from flowguard_design.field_lifecycle import run_review as run_fields
from flowguard_design.inventory import (
    AGENT_OPERATION_ORDER,
    ALL_TEST_SUITES,
    MODEL_ORDER,
)
from flowguard_design.model_test_alignment import run_reviews as run_alignment
from flowguard_design.synthetic_sources import (
    FIXTURE_PATH,
    review_fixture_inventory,
)
from flowguard_design.test_mesh import run_review as run_test_mesh
from flowguard_design.transition_coverage import build_matrices


RECEIPT_ROOT = Path(".flowguard/evidence/design")
SOURCE_PATHS = (
    Path(".flowguard/behavior_commitment_ledger/ledger.json"),
    Path("flowguard_models/agent_operation_models.py"),
    Path("flowguard_models/model_mesh.py"),
    *tuple(sorted(Path("flowguard_models/models").glob("*.py"))),
    Path("flowguard_design/architecture.py"),
    Path("flowguard_design/commitments.py"),
    Path("flowguard_design/contract_exhaustion.py"),
    Path("flowguard_design/field_lifecycle.py"),
    Path("flowguard_design/inventory.py"),
    Path("flowguard_design/model_test_alignment.py"),
    Path("flowguard_design/run_g4_review.py"),
    Path("flowguard_design/synthetic_sources.py"),
    Path("flowguard_design/test_mesh.py"),
    Path("flowguard_design/transition_coverage.py"),
    Path("flowguard_design/ui_flow_structure.py"),
    Path("flowguard_design/run_ui_flow_structure.py"),
    Path("flowguard_design/ui_runtime_contract.py"),
    Path("flowguard_design/ui_runtime_required_checks.json"),
    Path("scripts/verify_live_ui.js"),
    *tuple(
        sorted(
            path
            for path in Path("plugins/matters").rglob("*")
            if path.is_file()
        )
    ),
    FIXTURE_PATH,
)

ALIGNMENT_EXECUTION_FINDINGS = {
    "boundary_missing_runtime_evidence",
    "missing_code_contract_test_evidence",
    "missing_test_evidence",
    "test_evidence_not_passing",
}
TEST_MESH_EXECUTION_FINDINGS = {
    "final_receipt_artifact_version_missing",
    "final_receipt_coverage_incomplete",
    "final_receipt_exit_code_missing",
    "final_receipt_result_artifact_missing",
    "final_receipt_result_fingerprint_missing",
    "final_receipt_run_id_missing",
    "final_receipt_terminal_status_missing",
    "final_receipt_verifier_version_missing",
    "insufficient_evidence_tier",
    "leaf_matrix_cell_evidence_missing",
    "release_suite_deferred",
    "required_inventory_item_owner_missing",
    "suite_not_current",
}


def _fingerprint() -> str:
    digest = sha256()
    for path in SOURCE_PATHS:
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()


def _write(name: str, payload: dict) -> str:
    RECEIPT_ROOT.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_ROOT / name
    path.write_text(
        json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path.as_posix()


def _canonical_fingerprint(value: Any) -> str:
    canonical = json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + sha256(canonical).hexdigest()


def _sequence_summary(value: list[Any]) -> dict[str, Any]:
    return {
        "count": len(value),
        "fingerprint": _canonical_fingerprint(value),
    }


def _compact_contract_exhaustion(plan, report) -> dict:
    """Persist review authority without copying every derived Cartesian row."""

    plan_payload = plan.to_dict()
    report_payload = report.to_dict()
    return {
        "artifact_type": "matters.contract-exhaustion-design.v2",
        "canonical_review_fingerprint": _canonical_fingerprint(
            {"plan": plan_payload, "report": report_payload}
        ),
        "plan": {
            key: plan_payload[key]
            for key in (
                "plan_id",
                "model_id",
                "model_level",
                "source_model_ids",
                "generation_policy",
                "required_route_ids",
                "cartesian_case_limit",
                "axes",
                "interaction_groups",
                "oracles",
                "coverage_universe",
                "inventory_revision",
                "inventory_current",
            )
        },
        "report": {
            "ok": report_payload["ok"],
            "decision": report_payload["decision"],
            "confidence": report_payload["confidence"],
            "summary": report_payload["summary"],
            "inventory_revision": report_payload["inventory_revision"],
            "finding_codes": sorted(
                {item["code"] for item in report_payload["findings"]}
            ),
            "generated_case_count": len(report_payload["generated_cases"]),
            "combination_case_count": len(report_payload["combination_cases"]),
            "fault_profile_count": len(report_payload["contract_fault_profiles"]),
            "composite_handoff_acceptance_count": len(
                report_payload["composite_handoff_acceptances"]
            ),
            "coverage_shards": _sequence_summary(
                report_payload["coverage_shards"]
            ),
            "coverage_receipts": _sequence_summary(
                report_payload["coverage_receipts"]
            ),
            "required_route_case_ids": _sequence_summary(
                report_payload["required_route_case_ids"]
            ),
            "missing_oracle_case_ids": report_payload[
                "missing_oracle_case_ids"
            ],
            "model_gap_dimension_ids": report_payload[
                "model_gap_dimension_ids"
            ],
        },
        "claim_boundary": (
            "The canonical executable review produced every Cartesian case. "
            "This public receipt stores its fingerprint, authority, coverage, "
            "counts, and findings without duplicating thousands of derived rows."
        ),
    }


def _compact_test_mesh(plan, report) -> dict:
    """Persist exact TestMesh authority without repeated leaf/finding payloads."""

    plan_payload = plan.to_dict()
    report_payload = report.to_dict()
    suite_scalar_keys = (
        "suite_id",
        "layer",
        "command",
        "diagnostic_boundary",
        "planned_count",
        "executed_count",
        "failed_count",
        "not_run_count",
        "not_run_reason",
        "result_status",
        "terminal_status",
        "evidence_tier",
        "evidence_current",
        "release_required",
    )
    suite_sequence_keys = (
        "covered_obligation_ids",
        "owned_coverage_shard_ids",
        "owned_inventory_item_ids",
        "owned_leaf_cell_ids",
        "owns_side_effects",
        "owns_state",
    )
    suites = []
    for row in plan_payload["child_suites"]:
        suites.append(
            {
                **{key: row[key] for key in suite_scalar_keys},
                **{
                    key: _sequence_summary(row[key])
                    for key in suite_sequence_keys
                },
            }
        )
    finding_codes = sorted(
        {item["code"] for item in report_payload["findings"]}
    )
    return {
        "artifact_type": "matters.test-mesh-design.v2",
        "canonical_review_fingerprint": _canonical_fingerprint(
            {"plan": plan_payload, "report": report_payload}
        ),
        "plan": {
            key: plan_payload[key]
            for key in (
                "parent_suite_id",
                "decision_scope",
                "inventory_revision",
                "release_deferred_allowed",
                "require_complete_inventory",
                "require_final_receipts",
                "require_proof_artifacts",
                "required_evidence_tier",
                "partition_items",
                "target_split_derivation",
            )
        }
        | {
            "child_suites": suites,
            "required_coverage_shard_ids": _sequence_summary(
                plan_payload["required_coverage_shard_ids"]
            ),
            "required_inventory_item_ids": _sequence_summary(
                plan_payload["required_inventory_item_ids"]
            ),
            "required_leaf_cell_ids": _sequence_summary(
                plan_payload["required_leaf_cell_ids"]
            ),
        },
        "native_report": {
            key: report_payload[key]
            for key in (
                "ok",
                "decision",
                "decision_scope",
                "inventory_revision",
                "summary",
                "release_obligations",
            )
        }
        | {
            "finding_count": len(report_payload["findings"]),
            "finding_codes": finding_codes,
            "findings_fingerprint": _canonical_fingerprint(
                report_payload["findings"]
            ),
            "covered_inventory_item_ids": _sequence_summary(
                report_payload["covered_inventory_item_ids"]
            ),
            "missing_inventory_item_ids": _sequence_summary(
                report_payload["missing_inventory_item_ids"]
            ),
            "scoped_inventory_item_ids": _sequence_summary(
                report_payload["scoped_inventory_item_ids"]
            ),
        },
        "claim_boundary": (
            "The native TestMesh review consumed the complete child-suite, "
            "leaf-cell, inventory, and finding payloads. This public receipt "
            "stores exact fingerprints, counts, suite authority, and findings "
            "without repeating derived rows or embedding full owner payloads."
        ),
    }


def _test_mesh_invariants(plan) -> dict:
    suites = plan.child_suites
    suite_ids = tuple(suite.suite_id for suite in suites)
    leaf_owners: dict[str, list[str]] = {}
    inventory_owners: dict[str, list[str]] = {}
    state_owners: dict[str, list[str]] = {}
    effect_owners: dict[str, list[str]] = {}
    accounting_ok = True
    for suite in suites:
        accounting_ok &= suite.planned_count == (
            suite.executed_count + suite.not_run_count
        )
        accounting_ok &= suite.failed_count <= suite.executed_count
        for item in suite.owned_leaf_cell_ids:
            leaf_owners.setdefault(item, []).append(suite.suite_id)
        for item in suite.owned_inventory_item_ids:
            inventory_owners.setdefault(item, []).append(suite.suite_id)
        for item in suite.owns_state:
            state_owners.setdefault(item, []).append(suite.suite_id)
        for item in suite.owns_side_effects:
            effect_owners.setdefault(item, []).append(suite.suite_id)
    required_leaf = set(plan.required_leaf_cell_ids)
    required_inventory = set(plan.required_inventory_item_ids)
    return {
        "suite_ids_exact": suite_ids == ALL_TEST_SUITES,
        "suite_count": len(suites),
        "accounting_ok": bool(accounting_ok),
        "all_tests_not_run": all(suite.result_status == "not_run" for suite in suites),
        "planned_count": sum(suite.planned_count for suite in suites),
        "executed_count": sum(suite.executed_count for suite in suites),
        "failed_count": sum(suite.failed_count for suite in suites),
        "not_run_count": sum(suite.not_run_count for suite in suites),
        "leaf_ownership_exact": (
            set(leaf_owners) == required_leaf
            and all(len(owners) == 1 for owners in leaf_owners.values())
        ),
        "inventory_ownership_exact": (
            set(inventory_owners) == required_inventory
            and all(len(owners) == 1 for owners in inventory_owners.values())
        ),
        "state_ownership_unique": all(
            len(owners) == 1 for owners in state_owners.values()
        ),
        "side_effect_ownership_unique": all(
            len(owners) == 1 for owners in effect_owners.values()
        ),
    }


def main() -> int:
    fingerprint = _fingerprint()
    generated_at = datetime.now(timezone.utc).isoformat()

    architecture, architecture_report = run_architecture()
    fields, field_report = run_fields()
    matrices = build_matrices()
    contract_plan, contract_report = run_contracts()
    alignment_rows = run_alignment()
    test_mesh_plan, test_mesh_report = run_test_mesh()
    fixture_report = review_fixture_inventory()

    alignment_codes = {
        finding.code
        for _, report in alignment_rows
        for finding in report.findings
    }
    alignment_structural_ok = alignment_codes <= ALIGNMENT_EXECUTION_FINDINGS
    test_mesh_codes = {finding.code for finding in test_mesh_report.findings}
    test_mesh_structural_ok = test_mesh_codes <= TEST_MESH_EXECUTION_FINDINGS
    test_mesh_invariants = _test_mesh_invariants(test_mesh_plan)
    transition_ids = [
        cell.cell_id for matrix in matrices for cell in matrix.required_cells()
    ]
    transition_structural_ok = (
        len(matrices) == len(MODEL_ORDER) + len(AGENT_OPERATION_ORDER)
        and len(transition_ids) == len(set(transition_ids))
        and all(matrix.cells for matrix in matrices)
    )

    _write(
        "G4_transition_coverage.json",
        {
            "artifact_type": "matters.transition-coverage-design.v1",
            "design_fingerprint": fingerprint,
            "generated_at": generated_at,
            "matrices": [matrix.to_dict() for matrix in matrices],
            "structural_ok": transition_structural_ok,
            "execution_status": "not_run",
        },
    )
    _write(
        "G4_contract_exhaustion.json",
        {
            "design_fingerprint": fingerprint,
            "generated_at": generated_at,
            "execution_status": "matrix_generated_not_executed",
            **_compact_contract_exhaustion(contract_plan, contract_report),
        },
    )
    _write(
        "G4_model_test_alignment.json",
        {
            "artifact_type": "matters.model-code-test-alignment-design.v1",
            "design_fingerprint": fingerprint,
            "generated_at": generated_at,
            "plans": [plan.to_dict() for plan, _ in alignment_rows],
            "reports": [
                {
                    "model_id": plan.model_id,
                    "ok": report.ok,
                    "finding_count": len(report.findings),
                    "finding_codes": sorted(
                        {finding.code for finding in report.findings}
                    ),
                }
                for plan, report in alignment_rows
            ],
            "structural_ok": alignment_structural_ok,
            "execution_status": "not_run",
            "allowed_not_run_findings": sorted(ALIGNMENT_EXECUTION_FINDINGS),
        },
    )
    _write(
        "G4_test_mesh.json",
        {
            "design_fingerprint": fingerprint,
            "generated_at": generated_at,
            **_compact_test_mesh(test_mesh_plan, test_mesh_report),
            "structural_ok": test_mesh_structural_ok
            and all(
                value
                for key, value in test_mesh_invariants.items()
                if key.endswith(("_ok", "_exact", "_unique"))
            ),
            "invariants": test_mesh_invariants,
            "execution_status": "not_run",
            "allowed_not_run_findings": sorted(TEST_MESH_EXECUTION_FINDINGS),
        },
    )

    overall_ok = all(
        (
            architecture_report.ok,
            field_report.ok,
            transition_structural_ok,
            contract_report.ok,
            alignment_structural_ok,
            test_mesh_structural_ok,
            all(
                value
                for key, value in test_mesh_invariants.items()
                if key.endswith(("_ok", "_exact", "_unique"))
            ),
            fixture_report["ok"],
        )
    )
    receipt = {
        "artifact_type": "matters.g4-model-derived-design-receipt.v1",
        "gate_id": "G4",
        "evidence_id": (
            "evidence:G4-model-derived-design:"
            + fingerprint.removeprefix("sha256:")[:16]
        ),
        "design_fingerprint": fingerprint,
        "generated_at": generated_at,
        "toolchain": {
            "flowguard_package_version": importlib.metadata.version("flowguard"),
            "flowguard_schema_version": flowguard.SCHEMA_VERSION,
        },
        "structural_status": "g4_design_green" if overall_ok else "blocked",
        "execution_status": "not_run",
        "claim_boundary": (
            "G4 proves design inventory, unique ownership, finite universes, "
            "and exact planned evidence ownership. It does not prove code, "
        "tests, provider conformance, synthetic E2E, live private sources, UI, or release."
        ),
        "checks": {
            "architecture_native_ok": architecture_report.ok,
            "field_lifecycle_native_ok": field_report.ok,
            "transition_matrix_structural_ok": transition_structural_ok,
            "transition_matrix_count": len(matrices),
            "transition_cell_count": len(transition_ids),
            "contract_exhaustion_native_ok": contract_report.ok,
            "contract_combination_count": len(contract_report.combination_cases),
            "alignment_structural_ok": alignment_structural_ok,
            "alignment_native_execution_ok": all(
                report.ok for _, report in alignment_rows
            ),
            "test_mesh_structural_ok": test_mesh_structural_ok,
            "test_mesh_native_execution_ok": test_mesh_report.ok,
            "test_mesh_invariants": test_mesh_invariants,
            "synthetic_source_inventory": fixture_report,
        },
        "artifacts": {
            "architecture": architecture.to_dict(),
            "field_lifecycle": fields.to_dict(),
            "transition_coverage": ".flowguard/evidence/design/G4_transition_coverage.json",
            "contract_exhaustion": ".flowguard/evidence/design/G4_contract_exhaustion.json",
            "model_test_alignment": ".flowguard/evidence/design/G4_model_test_alignment.json",
            "test_mesh": ".flowguard/evidence/design/G4_test_mesh.json",
            "synthetic_sources": FIXTURE_PATH.as_posix(),
        },
    }
    path = _write("G4_model_derived_design.json", receipt)
    print(
        json.dumps(
            {
                "ok": overall_ok,
                "receipt": path,
                "evidence_id": receipt["evidence_id"],
                "structural_status": receipt["structural_status"],
                "execution_status": receipt["execution_status"],
                "transition_cells": len(transition_ids),
                "contract_combinations": len(contract_report.combination_cases),
                "test_mesh": test_mesh_invariants,
            },
            indent=2,
        )
    )
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
