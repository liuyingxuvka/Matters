"""Build current M0/C1-C12 model-code-test alignment from TestMesh receipts."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from flowguard_design.model_test_alignment import run_reviews


TEST_RECEIPT_ROOT = Path(".flowguard/evidence/tests")
OUTPUT = Path(".flowguard/evidence/alignment/model_code_test.json")


def _compact_model_row(plan, report) -> dict:
    plan_payload = plan.to_dict()
    report_payload = report.to_dict()
    canonical = json.dumps(
        {"plan": plan_payload, "report": report_payload},
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return {
        "model_id": plan.model_id,
        "plan_fingerprint": "sha256:" + sha256(canonical).hexdigest(),
        "plan": {
            "model_id": plan.model_id,
            "boundary_observations": plan_payload["boundary_observations"],
            "obligation_ids": [
                item["obligation_id"] for item in plan_payload["obligations"]
            ],
            "code_contract_ids": [
                item["code_contract_id"]
                for item in plan_payload["code_contracts"]
            ],
            "test_evidence_ids": [
                item["evidence_id"] for item in plan_payload["test_evidence"]
            ],
            "obligation_count": len(plan_payload["obligations"]),
            "test_evidence_count": len(plan_payload["test_evidence"]),
        },
        "report": {
            "model_id": report_payload["model_id"],
            "ok": report_payload["ok"],
            "decision": report_payload["decision"],
            "summary": report_payload["summary"],
            "findings": report_payload["findings"],
            "binding_row_count": len(report_payload["binding_rows"]),
        },
    }


def main() -> int:
    rows = run_reviews(executed=True, receipt_root=TEST_RECEIPT_ROOT)
    receipt_paths = tuple(
        sorted(
            path
            for path in TEST_RECEIPT_ROOT.glob("TM*.json")
            if path.name != "TM0_matters_whole_flow_gate.json"
        )
    )
    digest = sha256()
    input_fingerprints = {}
    for path in receipt_paths:
        fingerprint = "sha256:" + sha256(path.read_bytes()).hexdigest()
        input_fingerprints[path.as_posix()] = fingerprint
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    alignment_fingerprint = "sha256:" + digest.hexdigest()
    payload = {
        "artifact_type": "matters.model-code-test-alignment-receipt.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_id": (
            "evidence:model-code-test-alignment:"
            + alignment_fingerprint.removeprefix("sha256:")[:16]
        ),
        "alignment_fingerprint": alignment_fingerprint,
        "input_fingerprints": input_fingerprints,
        "status": "alignment_green" if all(report.ok for _, report in rows) else "blocked",
        "models": [
            _compact_model_row(plan, report) for plan, report in rows
        ],
        "claim_boundary": (
            "This receipt covers current synthetic external-contract tests. "
            "Each model row keeps its canonical plan/report fingerprint, "
            "boundary observations, authority ids, counts, and findings "
            "without duplicating complete test receipts. It does not prove "
            "live provider behavior or release installation."
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": payload["status"] == "alignment_green",
                "status": payload["status"],
                "models": {
                    plan.model_id: {
                        "ok": report.ok,
                        "finding_codes": sorted(
                            {item.code for item in report.findings}
                        ),
                    }
                    for plan, report in rows
                },
                "receipt": OUTPUT.as_posix(),
            },
            indent=2,
        )
    )
    return 0 if payload["status"] == "alignment_green" else 1


if __name__ == "__main__":
    raise SystemExit(main())
