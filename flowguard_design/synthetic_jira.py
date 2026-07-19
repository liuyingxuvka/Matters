"""Load and validate the fully synthetic J1-J10 fixture contract."""

from __future__ import annotations

import json
from pathlib import Path


FIXTURE_PATH = Path("tests/fixtures/jira_synthetic/J1-J10.json")
REQUIRED_SCENARIOS = tuple(f"J{number}" for number in range(1, 11))


def load_fixtures() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def review_fixture_inventory() -> dict:
    payload = load_fixtures()
    scenarios = payload.get("scenarios", [])
    ids = tuple(row.get("scenario_id") for row in scenarios)
    findings: list[dict[str, str]] = []
    if ids != REQUIRED_SCENARIOS:
        findings.append(
            {
                "code": "synthetic_jira_inventory_mismatch",
                "message": f"expected {REQUIRED_SCENARIOS!r}, observed {ids!r}",
            }
        )
    for row in scenarios:
        if row.get("synthetic") is not True:
            findings.append(
                {
                    "code": "non_synthetic_fixture",
                    "message": str(row.get("scenario_id")),
                }
            )
        if not row.get("provider_envelope"):
            findings.append(
                {
                    "code": "provider_envelope_missing",
                    "message": str(row.get("scenario_id")),
                }
            )
        if not row.get("expected"):
            findings.append(
                {
                    "code": "expected_semantics_missing",
                    "message": str(row.get("scenario_id")),
                }
            )
    return {
        "ok": not findings,
        "scenario_ids": list(ids),
        "scenario_count": len(scenarios),
        "findings": findings,
        "claim_boundary": (
            "Fixture design only. No real Jira access and no end-to-end "
            "execution occurred at G4."
        ),
    }


__all__ = [
    "FIXTURE_PATH",
    "REQUIRED_SCENARIOS",
    "load_fixtures",
    "review_fixture_inventory",
]
