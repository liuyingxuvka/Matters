"""Run one agent-operation-plane model and write its native receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from flowguard_models.agent_operation_models import AGENT_OPERATION_MODELS
from flowguard_models.harness import run_current
from flowguard_models.run_model import _receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_id", choices=tuple(AGENT_OPERATION_MODELS))
    parser.add_argument(
        "--receipt-root",
        default=".flowguard/evidence/agent_operations/models",
    )
    args = parser.parse_args()
    spec = AGENT_OPERATION_MODELS[args.model_id]
    report, proofs = run_current(spec)
    receipt = _receipt(spec, report, proofs)
    root = Path(args.receipt_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{spec.model_id}.json"
    path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(report.format_text())
    print(json.dumps({"receipt": str(path), **receipt}, indent=2))
    return 0 if receipt["pass_for_g2"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
