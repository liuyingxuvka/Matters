"""Run one declared Matters model and write its bounded native receipt."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path

import flowguard

from flowguard_models.harness import FiniteModelSpec, run_current
from flowguard_models.models.m00_end_to_end_authority import SPEC as M0
from flowguard_models.models.c01_authorization_coverage import SPEC as C1
from flowguard_models.models.c02_source_registry import SPEC as C2
from flowguard_models.models.c03_evidence_qualification import SPEC as C3
from flowguard_models.models.c04_identity_resolution import SPEC as C4
from flowguard_models.models.c05_event_temporal_trace import SPEC as C5
from flowguard_models.models.c06_matter_admission import SPEC as C6
from flowguard_models.models.c07_lifecycle_board_state import SPEC as C7
from flowguard_models.models.c08_open_loop_blocking import SPEC as C8
from flowguard_models.models.c09_outcomes_reopen import SPEC as C9
from flowguard_models.models.c10_correction_revocation import SPEC as C10
from flowguard_models.models.c11_guard_prediction import SPEC as C11
from flowguard_models.models.c12_projection_bilingual_ui import SPEC as C12


MODELS: dict[str, FiniteModelSpec] = {
    M0.model_id: M0,
    C1.model_id: C1,
    C2.model_id: C2,
    C3.model_id: C3,
    C4.model_id: C4,
    C5.model_id: C5,
    C6.model_id: C6,
    C7.model_id: C7,
    C8.model_id: C8,
    C9.model_id: C9,
    C10.model_id: C10,
    C11.model_id: C11,
    C12.model_id: C12,
}


def _receipt(spec: FiniteModelSpec, report, proofs) -> dict:
    sections = {section.name: section.status for section in report.sections}
    hazards_green = all(proof.observed_status == "failed" for proof in proofs)
    abstract_green = sections.get("model_check") == "pass"
    known_bad_green = sections.get("known_bad_proof") == "pass" and hazards_green
    evidence_tiers = []
    if abstract_green:
        evidence_tiers.append("abstract_green")
    if known_bad_green:
        evidence_tiers.append("hazard_green")
    fingerprint = spec.fingerprint()
    return {
        "artifact_type": "matters.flowguard-model-receipt.v1",
        "model_id": spec.model_id,
        "model_title": spec.title,
        "model_fingerprint": fingerprint,
        "evidence_id": f"evidence:{spec.model_id}:{fingerprint.removeprefix('sha256:')[:16]}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
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
        "evidence_tiers": evidence_tiers,
        "claim_boundary": spec.claim_boundary,
        "skipped_checks": {
            "conformance_replay": (
                "not_run_in_this_owner: production conformance belongs to "
                "the revision-bound TestMesh receipts"
            ),
            "live_current": (
                "not_run_in_this_owner: real private and installed-runtime "
                "evidence belong to separate delivery gates"
            ),
            "model_mesh": (
                "not_run_in_this_owner: cross-model topology belongs to the "
                "separate ModelMesh owner"
            ),
        },
        "pass_for_g2": (
            abstract_green
            and known_bad_green
            and sections.get("minimum_model_review") == "pass"
            and sections.get("template_harvest_review") == "pass"
            and sections.get("scenario_review") == "pass"
            and sections.get("state_closure") == "pass"
            and report.overall_status in {"pass", "pass_with_gaps"}
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_id", choices=tuple(MODELS))
    parser.add_argument(
        "--receipt-root",
        default=".flowguard/evidence/models",
    )
    args = parser.parse_args()
    spec = MODELS[args.model_id]
    report, proofs = run_current(spec)
    receipt = _receipt(spec, report, proofs)
    receipt_root = Path(args.receipt_root)
    receipt_root.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_root / f"{spec.model_id}.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(report.format_text())
    print(json.dumps({"receipt": str(receipt_path), **receipt}, indent=2))
    return 0 if receipt["pass_for_g2"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
