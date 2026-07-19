from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from flowguard import review_behavior_commitment_ledger

from model import LEDGER_PATH, build_behavior_commitment_ledger


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    ROOT
    / ".flowguard"
    / "evidence"
    / "preflight"
    / "behavior_commitment_ledger_review.json"
)
EXPECTED_DEFERRED_FINDINGS = frozenset(
    {
        "commitment_primary_path_blocked",
        "commitment_primary_path_material_evidence_missing",
        "commitment_primary_path_risk_gate_missing",
    }
)


def _fingerprint(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    ledger = build_behavior_commitment_ledger()
    report = review_behavior_commitment_ledger(ledger)
    finding_codes = tuple(sorted({finding.code for finding in report.findings}))
    unexpected = tuple(
        sorted(set(finding_codes) - EXPECTED_DEFERRED_FINDINGS)
    )
    payload = {
        "artifact_type": "matters.behavior-commitment-ledger-review.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": (
            "ledger_green"
            if report.ok
            else (
                "structural_inventory_current_evidence_deferred"
                if not unexpected
                else "blocked"
            )
        ),
        "ledger_revision": ledger.current_revision,
        "ledger_fingerprint": _fingerprint(LEDGER_PATH),
        "three_plane_counts": {
            plane: sum(
                1
                for row in ledger.commitments
                if row.in_scope and row.behavior_plane == plane
            )
            for plane in (
                "product_runtime",
                "agent_operation",
                "development_process",
            )
        },
        "native_report": report.to_dict(),
        "finding_codes": list(finding_codes),
        "unexpected_finding_codes": list(unexpected),
        "expected_deferred_finding_codes": sorted(
            EXPECTED_DEFERRED_FINDINGS
        ),
        "claim_boundary": (
            "A structural_inventory_current_evidence_deferred result proves only "
            "the current bidirectional three-plane inventory has no unexpected "
            "native ownership, relation, surface, identity, or lifecycle finding. "
            "Every path-sensitive product, agent-operation, Skill Pack, "
            "ResearchGuard, first-run, install, and release claim remains blocked "
            "until its original evidence owners publish current PPA, TestMesh, "
            "runtime, and risk-gate receipts."
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
    print("flowguard behavior commitment ledger")
    print(report.format_text())
    print("receipt:", output)
    print("status:", payload["status"])
    print("unexpected_findings:", ", ".join(unexpected) or "none")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
