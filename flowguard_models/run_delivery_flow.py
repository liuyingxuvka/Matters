"""Run and persist the current G0-G12 DevelopmentProcessFlow receipt."""

from __future__ import annotations

import json
from pathlib import Path

from flowguard_models.delivery_flow import RECEIPT_PATH, build_receipt


def main() -> int:
    root = Path(".").resolve()
    receipt = build_receipt(root)
    path = root / RECEIPT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"receipt": str(path), **receipt}, indent=2))
    current_gate = str(receipt.get("current_gate", ""))
    current_index = (
        int(current_gate.removeprefix("G"))
        if current_gate.startswith("G")
        and current_gate.removeprefix("G").isdigit()
        else -1
    )
    return 0 if current_index >= 8 and receipt["native_report"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
