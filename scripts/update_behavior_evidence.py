"""Bind current G8 product evidence into the canonical BCL JSON."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from flowguard import (
    BehaviorCommitmentLedger,
    behavior_commitment_ledger_to_mapping,
    load_behavior_commitment_ledger,
    review_behavior_commitment_ledger,
)

from flowguard_design.inventory import (
    AGENT_OPERATION_TEST_SUITES,
    MODEL_CODE_CONTRACTS,
    MODEL_TEST_SUITES,
    PARENT_ID,
)
from flowguard_design.transition_coverage import PARENT_CODE_CONTRACT_ID


LEDGER_PATH = Path(".flowguard/behavior_commitment_ledger/ledger.json")
ALIGNMENT_PATH = Path(".flowguard/evidence/alignment/model_code_test.json")
G8_PATH = Path(
    ".flowguard/evidence/synthetic/G8_fully_synthetic_end_to_end.json"
)
TEST_ROOT = Path(".flowguard/evidence/tests")
MODEL_ROOT = Path(".flowguard/evidence/models")


def _hash(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _unique(values):
    return list(dict.fromkeys(value for value in values if value))


def _model_for_commitment(commitment_id: str, row: dict) -> str:
    if commitment_id == "BC-PR-000":
        return PARENT_ID
    return str(row["primary_owner_model_id"])


def _suite_for_commitment(commitment_id: str, model_id: str) -> str:
    if commitment_id == "BC-PR-000":
        return "TM14_end_to_end_conformance"
    if commitment_id == "BC-PR-013":
        return "TM18_privacy_public_boundary"
    if commitment_id.startswith("BC-AO-"):
        return AGENT_OPERATION_TEST_SUITES[model_id]
    return MODEL_TEST_SUITES[model_id]


def _contract_for_model(model_id: str) -> str:
    return (
        PARENT_CODE_CONTRACT_ID
        if model_id == PARENT_ID
        else MODEL_CODE_CONTRACTS[model_id]
    )


def _model_evidence_id(model_id: str) -> str:
    path = (
        Path(".flowguard/evidence/agent_operations/models")
        if model_id.startswith("A")
        else MODEL_ROOT
    ) / f"{model_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    evidence_id = str(payload.get("evidence_id", ""))
    if not evidence_id:
        raise RuntimeError(f"{model_id} has no current model evidence id")
    return evidence_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--through-g8", action="store_true", required=True)
    args = parser.parse_args()
    if not args.through_g8:
        return 2

    g8 = json.loads(G8_PATH.read_text(encoding="utf-8"))
    alignment = json.loads(ALIGNMENT_PATH.read_text(encoding="utf-8"))
    if g8.get("status") != "g8_synthetic_green":
        raise RuntimeError("G8 receipt is not current-green")
    if alignment.get("status") != "alignment_green":
        raise RuntimeError("alignment receipt is not current-green")
    alignment_by_model = {
        row["model_id"]: row for row in alignment["models"]
    }
    payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    ledger = payload["ledger"]
    updated = []
    for row in ledger["commitments"]:
        commitment_id = str(row["commitment_id"])
        if not commitment_id.startswith(("BC-PR-", "BC-AO-")):
            continue
        model_id = _model_for_commitment(commitment_id, row)
        suite_id = _suite_for_commitment(commitment_id, model_id)
        suite_path = TEST_ROOT / f"{suite_id}.json"
        suite = json.loads(suite_path.read_text(encoding="utf-8"))
        suite_evidence = suite["test_suite_evidence"]
        if suite_evidence.get("result_status") != "passed":
            raise RuntimeError(f"{suite_id} is not passing")
        model_alignment = alignment_by_model[model_id]
        if model_alignment["report"].get("ok") is not True:
            raise RuntimeError(f"{model_id} alignment is not green")
        proof = suite_evidence["proof_artifact"]
        cells = list(suite_evidence.get("owned_leaf_cell_ids", ()))
        observations = [
            item["observation_id"]
            for item in model_alignment["plan"].get(
                "boundary_observations", ()
            )
        ]
        contract_ids = tuple(model_alignment["plan"]["code_contract_ids"])
        if len(contract_ids) != 1:
            raise RuntimeError(
                f"{model_id} must bind exactly one primary code contract"
            )
        contract_id = contract_ids[0]
        model_evidence_id = _model_evidence_id(model_id)
        evidence = row.setdefault("evidence", {})
        evidence["code_contract_ids"] = [contract_id]
        evidence["test_evidence_ids"] = [suite_evidence["run_id"]]
        evidence["proof_artifact_ids"] = [
            model_evidence_id,
            proof["artifact_id"],
            alignment["evidence_id"],
            g8["evidence_id"],
        ]
        evidence["risk_gate_ids"] = _unique(
            (*evidence.get("risk_gate_ids", ()), "G8-fully-synthetic")
        )
        evidence["coverage_case_ids"] = cells
        evidence["coverage_shard_ids"] = [suite_id]
        evidence["coverage_receipt_ids"] = [suite_evidence["run_id"]]
        evidence["evidence_state"] = "current_pass"
        evidence["test_mesh_state"] = "shard_current"
        evidence["current"] = True
        evidence["metadata"] = {
            **dict(evidence.get("metadata", {})),
            "through_gate": "G8",
            "test_receipt_path": suite_path.as_posix(),
            "test_receipt_fingerprint": _hash(suite_path),
            "alignment_evidence_id": alignment["evidence_id"],
            "g8_evidence_id": g8["evidence_id"],
            "live_provider_evidence": False,
        }
        authority = row["path_authority"]
        authority.update(
            {
                "ppa_report_id": f"PPA-{commitment_id}-G8",
                "ppa_decision": "primary_path_authority_green",
                "ppa_confidence": "full",
                "ppa_ok": True,
                "fallback_candidate_ids": [],
                "ppa_coverage_receipt_ids": [suite_evidence["run_id"]],
                "ppa_coverage_shard_ids": [suite_id],
                "ppa_risk_gate_ids": _unique(
                    (
                        *authority.get("ppa_risk_gate_ids", ()),
                        "authority",
                        "cartesian_coverage",
                        "G8-fully-synthetic",
                    )
                ),
                "evidence_refs": [
                    suite_path.as_posix(),
                    ALIGNMENT_PATH.as_posix(),
                    G8_PATH.as_posix(),
                ],
                "runtime_observation_ids": observations
                or [suite_evidence["run_id"]],
                "proof_artifact_ids": [
                    model_evidence_id,
                    proof["artifact_id"],
                    alignment["evidence_id"],
                    g8["evidence_id"],
                ],
                "evidence_current": True,
            }
        )
        updated.append(commitment_id)
    payload = behavior_commitment_ledger_to_mapping(
        BehaviorCommitmentLedger(**ledger)
    )
    LEDGER_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    loaded = load_behavior_commitment_ledger(LEDGER_PATH)
    report = review_behavior_commitment_ledger(loaded)
    print(
        json.dumps(
            {
                "updated": updated,
                "updated_count": len(updated),
                "native_ok": report.ok,
                "native_decision": report.decision,
                "finding_count": len(report.findings),
                "finding_codes": sorted({item.code for item in report.findings}),
                "expected_deferred_process_commitments": [
                    "BC-DP-001",
                    "BC-DP-002",
                    "BC-DP-003",
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
