"""Canonical installed-UI runtime check inventory."""

from __future__ import annotations

import json
from pathlib import Path


CONTRACT_PATH = Path(__file__).with_name("ui_runtime_required_checks.json")


def required_ui_checks() -> tuple[str, ...]:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if payload.get("artifact_type") != "matters.ui-runtime-check-contract.v1":
        raise ValueError("unsupported UI runtime check contract")
    checks = payload.get("required_checks")
    if (
        not isinstance(checks, list)
        or not checks
        or any(not isinstance(item, str) or not item for item in checks)
        or len(set(checks)) != len(checks)
    ):
        raise ValueError("invalid UI runtime check inventory")
    return tuple(checks)


REQUIRED_UI_CHECKS = required_ui_checks()


__all__ = ["CONTRACT_PATH", "REQUIRED_UI_CHECKS", "required_ui_checks"]
