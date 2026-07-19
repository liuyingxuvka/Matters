"""Run only the auxiliary S0-S5 skill-runtime FlowGuard owners."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path

import flowguard
from flowguard import (
    ContractCoverageUniverse,
    ContractDimension,
    ContractExhaustionPlan,
    ContractMutationCase,
    ContractOracle,
    review_contract_exhaustion,
)

from flowguard_models.harness import FiniteModelSpec, run_current
from flowguard_models.models.s00_skill_runtime import MODELS


DEFAULT_RECEIPT_ROOT = Path(".flowguard/evidence/skill_runtime/models")


def _contract_report(spec: FiniteModelSpec):
    dimension_id = f"{spec.model_id}:declared-case-inventory"
    seed_cases = tuple(
        ContractMutationCase(
            case_id=hazard.failure_id,
            dimension_id=dimension_id,
            mutation_type=hazard.protected_error_class,
            source_route="model_first_function_flow",
            source_case_id=hazard.case_id,
            oracle_id=f"oracle:{hazard.failure_id}",
            expected_status="blocked",
            model_id=spec.model_id,
            description=hazard.description,
        )
        for hazard in spec.hazards
    )
    oracles = tuple(
        ContractOracle(
            oracle_id=f"oracle:{hazard.failure_id}",
            expected_status="blocked",
            expected_message_fields=("decision", "reason"),
            required_repair_fields=("case_id", "required_disposition"),
            disallowed_side_effects=("canonical_matter_write",),
            description=(
                f"{hazard.failure_id} must be rejected by the declared model "
                "reaction without a canonical Matter write."
            ),
        )
        for hazard in spec.hazards
    )
    plan = ContractExhaustionPlan(
        plan_id=f"contract-exhaustion:{spec.model_id}",
        dimensions=(
            ContractDimension(
                dimension_id=dimension_id,
                dimension_type="declared_finite_case_inventory",
                source_route="model_first_function_flow",
                owner_model_id=spec.model_id,
                values=tuple(rule.case_id for rule in spec.rules),
                mutation_types=(),
                description="Exact finite known-good and hazard source cases.",
            ),
        ),
        seed_cases=seed_cases,
        oracles=oracles,
        claim_scope="routine",
        require_oracles_for_required_cases=False,
        source_model_ids=(spec.model_id,),
        generation_policy="bounded",
        required_route_ids=(),
        require_composite_handoff_acceptance=False,
        model_id=spec.model_id,
        parent_model_id=(
            "" if spec.model_id == "S0_matters_skill_runtime"
            else "S0_matters_skill_runtime"
        ),
        model_level=(
            "parent" if spec.model_id == "S0_matters_skill_runtime" else "child"
        ),
        coverage_universe=ContractCoverageUniverse(
            universe_id=f"coverage-universe:{spec.model_id}",
            claim_scope="routine",
            source_refs=(spec.model_id,),
            required_dimension_ids=(dimension_id,),
            required_case_ids=tuple(hazard.failure_id for hazard in spec.hazards),
            require_full_product=False,
        ),
        require_coverage_universe=True,
        require_actionable_oracle_feedback=False,
        inventory_revision=spec.fingerprint(),
        inventory_current=True,
    )
    return plan, review_contract_exhaustion(plan)


def build_receipt(spec: FiniteModelSpec) -> dict:
    report, proofs = run_current(spec)
    sections = {section.name: section.status for section in report.sections}
    contract_plan, contract_report = _contract_report(spec)
    hazards_green = all(proof.observed_status == "failed" for proof in proofs)
    abstract_green = sections.get("model_check") == "pass"
    known_bad_green = sections.get("known_bad_proof") == "pass" and hazards_green
    pass_for_skill_runtime = (
        abstract_green
        and known_bad_green
        and sections.get("minimum_model_review") == "pass"
        and sections.get("template_harvest_review") == "pass"
        and sections.get("scenario_review") == "pass"
        and sections.get("state_closure") == "pass"
        and contract_report.ok
        and report.overall_status in {"pass", "pass_with_gaps"}
    )
    fingerprint = spec.fingerprint()
    return {
        "artifact_type": "matters.skill-runtime-flowguard-receipt.v1",
        "model_id": spec.model_id,
        "model_title": spec.title,
        "model_fingerprint": fingerprint,
        "evidence_id": (
            f"evidence:skill-runtime:{spec.model_id}:"
            f"{fingerprint.removeprefix('sha256:')[:16]}"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "function_signature": (
            f"{spec.model_id}: CaseInput x ModelState -> "
            "Set(DecisionOutput x ModelState)"
        ),
        "owned_write_fields": list(spec.owned_write_fields),
        "side_effect_classes": list(spec.side_effect_classes),
        "toolchain": {
            "flowguard_package_version": importlib.metadata.version("flowguard"),
            "flowguard_schema_version": flowguard.SCHEMA_VERSION,
        },
        "overall_status": report.overall_status,
        "sections": sections,
        "known_bad_proofs": [
            {
                "failure_id": proof.case_id,
                "protected_error_class": proof.protected_error_class,
                "observed_status": proof.observed_status,
                "evidence_id": proof.evidence_id,
            }
            for proof in proofs
        ],
        "contract_exhaustion": {
            "plan": contract_plan.to_dict(),
            "report": contract_report.to_dict(),
        },
        "evidence_tiers": [
            tier
            for tier, present in (
                ("abstract_green", abstract_green),
                ("hazard_green", known_bad_green),
            )
            if present
        ],
        "claim_boundary": spec.claim_boundary,
        "skipped_checks": {
            "production_conformance": (
                "not_run: auxiliary skill runtime implementation is intentionally "
                "outside this model-only workstream"
            ),
            "live_installation": (
                "not_run: no real global or Matters-managed skill installation "
                "was attempted"
            ),
            "m0_c1_c12_integration": (
                "out_of_scope: S0 is auxiliary and cannot become C13"
            ),
        },
        "pass_for_skill_runtime": pass_for_skill_runtime,
    }


def run_one(
    spec: FiniteModelSpec,
    *,
    receipt_root: Path = DEFAULT_RECEIPT_ROOT,
) -> dict:
    receipt = build_receipt(spec)
    receipt_root.mkdir(parents=True, exist_ok=True)
    path = receipt_root / f"{spec.model_id}.json"
    path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_id", nargs="?", choices=tuple(MODELS))
    parser.add_argument("--all", action="store_true")
    parser.add_argument(
        "--receipt-root",
        default=DEFAULT_RECEIPT_ROOT.as_posix(),
    )
    args = parser.parse_args()
    if args.all == (args.model_id is not None):
        parser.error("select exactly one model_id or --all")
    selected = (
        tuple(MODELS.values())
        if args.all
        else (MODELS[args.model_id],)
    )
    receipt_root = Path(args.receipt_root)
    receipts = [
        run_one(spec, receipt_root=receipt_root)
        for spec in selected
    ]
    summary = {
        "ok": all(row["pass_for_skill_runtime"] for row in receipts),
        "models": {
            row["model_id"]: {
                "status": row["overall_status"],
                "pass_for_skill_runtime": row["pass_for_skill_runtime"],
                "evidence_id": row["evidence_id"],
            }
            for row in receipts
        },
        "receipt_root": "repo://.flowguard/evidence/skill_runtime/models",
        "claim_boundary": (
            "Only S0-S5 abstract and hazard evidence was executed. No existing "
            "model owner, product runtime, installation, or ResearchGuard "
            "provider was executed."
        ),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
