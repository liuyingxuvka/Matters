"""Build current M0/C1-C12 model-code-test alignment from TestMesh receipts."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from flowguard_design.model_test_alignment import run_reviews


TEST_RECEIPT_ROOT = Path(".flowguard/evidence/tests")
OUTPUT = Path(".flowguard/evidence/alignment/model_code_test.json")
MAX_PUBLIC_ALIGNMENT_BYTES = 5 * 1024 * 1024


def _canonical_fingerprint(value) -> str:
    canonical = json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + sha256(canonical).hexdigest()


def _fingerprinted_inventory(values) -> dict:
    rows = list(values)
    return {
        "count": len(rows),
        "fingerprint": _canonical_fingerprint(rows),
    }


def _compact_proof_artifact(proof_artifact: dict) -> dict:
    full_fingerprint = _canonical_fingerprint(proof_artifact)
    artifact_id = str(proof_artifact.get("artifact_id", ""))
    artifact_ref = (
        artifact_id
        + "@"
        + full_fingerprint.removeprefix("sha256:")[:16]
    )
    metadata = proof_artifact.get("metadata") or {}
    return {
        "artifact_ref": artifact_ref,
        "artifact_id": artifact_id,
        "full_fingerprint": full_fingerprint,
        "producer_route": proof_artifact.get("producer_route", ""),
        "command": proof_artifact.get("command", ""),
        "result_path": proof_artifact.get("result_path", ""),
        "result_status": proof_artifact.get("result_status", ""),
        "exit_code": proof_artifact.get("exit_code"),
        "started_at": proof_artifact.get("started_at", ""),
        "finished_at": proof_artifact.get("finished_at", ""),
        "artifact_fingerprints": _fingerprinted_inventory(
            sorted((proof_artifact.get("artifact_fingerprints") or {}).items())
        ),
        "covered_obligation_ids": _fingerprinted_inventory(
            proof_artifact.get("covered_obligation_ids") or ()
        ),
        "assertion_scope": proof_artifact.get("assertion_scope", ""),
        "current": bool(proof_artifact.get("current", False)),
        "route_evidence_current": bool(
            proof_artifact.get("route_evidence_current", False)
        ),
        "progress_only": bool(proof_artifact.get("progress_only", False)),
        "stale_reasons": list(proof_artifact.get("stale_reasons") or ()),
        "route_gap_codes": list(proof_artifact.get("route_gap_codes") or ()),
        "metadata": {
            "keys": sorted(metadata),
            "fingerprint": _canonical_fingerprint(metadata),
        },
    }


def _compact_findings(findings: list[dict]) -> tuple[list[dict], list[dict]]:
    compact_findings: list[dict] = []
    proof_artifacts: dict[str, dict] = {}
    for finding in findings:
        compact = dict(finding)
        metadata = dict(compact.get("metadata") or {})
        proof_artifact = metadata.pop("proof_artifact", None)
        if proof_artifact:
            proof = _compact_proof_artifact(proof_artifact)
            proof_artifacts[proof["artifact_ref"]] = proof
            metadata["proof_artifact_ref"] = proof["artifact_ref"]
        compact["metadata"] = metadata
        compact_findings.append(compact)
    return (
        compact_findings,
        [proof_artifacts[key] for key in sorted(proof_artifacts)],
    )


def _compact_model_row(plan, report) -> dict:
    plan_payload = plan.to_dict()
    report_payload = report.to_dict()
    canonical = json.dumps(
        {"plan": plan_payload, "report": report_payload},
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    compact_findings, proof_artifacts = _compact_findings(
        report_payload["findings"]
    )
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
            "findings": compact_findings,
            "finding_count": len(report_payload["findings"]),
            "findings_fingerprint": _canonical_fingerprint(
                report_payload["findings"]
            ),
            "proof_artifacts": proof_artifacts,
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
        "artifact_type": "matters.model-code-test-alignment-receipt.v2",
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
            "boundary observations, authority ids, exact finding identities, "
            "failure rows, coverage counts/fingerprints, and deduplicated "
            "proof-artifact status/identity summaries without duplicating "
            "complete TestMesh receipts. Exact source receipts remain bound by "
            "input_fingerprints. It does not prove live provider behavior or "
            "release installation."
        ),
    }
    serialized = (
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    if len(serialized) > MAX_PUBLIC_ALIGNMENT_BYTES:
        raise RuntimeError(
            "public alignment receipt exceeds the 5 MiB public-file boundary: "
            f"{len(serialized)} bytes"
        )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(serialized)
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
