"""Load and validate the provider-neutral synthetic source-universe inventory."""

from __future__ import annotations

import json
from pathlib import Path


FIXTURE_PATH = Path("tests/fixtures/source_universe_synthetic/cases.json")
REQUIRED_CASE_IDS = tuple(f"S{index}_" for index in range(1, 13))


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def review_fixture_inventory() -> dict:
    payload = load_fixture()
    cases = payload.get("cases", ())
    ids = tuple(str(case.get("case_id", "")) for case in cases)
    findings: list[dict[str, str]] = []
    if payload.get("schema_version") != "matters.synthetic-source-universe.v1":
        findings.append({"code": "synthetic_source_schema_mismatch"})
    if payload.get("synthetic_only") is not True:
        findings.append({"code": "synthetic_source_not_declared_synthetic"})
    if len(ids) != len(set(ids)):
        findings.append({"code": "synthetic_source_duplicate_case_id"})
    missing_prefixes = [
        prefix for prefix in REQUIRED_CASE_IDS if not any(value.startswith(prefix) for value in ids)
    ]
    if missing_prefixes:
        findings.append(
            {
                "code": "synthetic_source_inventory_mismatch",
                "detail": ",".join(missing_prefixes),
            }
        )
    for case in cases:
        if not case.get("provider") or not case.get("object_type"):
            findings.append(
                {
                    "code": "synthetic_source_identity_missing",
                    "detail": str(case.get("case_id", "")),
                }
            )
        if not any(
            key in case
            for key in (
                "expected_disposition",
                "expected_change",
                "expected_operation_status",
            )
        ):
            findings.append(
                {
                    "code": "synthetic_source_oracle_missing",
                    "detail": str(case.get("case_id", "")),
                }
            )
    return {
        "ok": not findings,
        "schema_version": payload.get("schema_version"),
        "case_count": len(cases),
        "case_ids": list(ids),
        "findings": findings,
        "claim_boundary": (
            "This inventory is fully synthetic and proves only declared case "
            "coverage; it does not prove provider access or runtime conformance."
        ),
    }


__all__ = ["FIXTURE_PATH", "REQUIRED_CASE_IDS", "load_fixture", "review_fixture_inventory"]
