"""Read stable plane-partitioned bindings from the canonical project ledger."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


LEDGER_PATH = Path(".flowguard/behavior_commitment_ledger/ledger.json")
ALL_SOURCE_SCOPE_REVISION = "candidate-source-universe-v1"


def commitment_bindings(
    behavior_plane: str = "product_runtime",
) -> dict[str, dict[str, str]]:
    """Return owner model -> stable binding for one exact behavior plane.

    Product-runtime remains the default for existing model/test callers.  Agent
    operations and development-process owners must be requested explicitly so
    a shared owner label or keyword cannot merge responsibility planes.
    """

    payload: dict[str, Any] = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    bindings: dict[str, dict[str, str]] = {}
    for row in payload["ledger"]["commitments"]:
        if row.get("behavior_plane") != behavior_plane:
            continue
        if row.get("in_scope", True) is not True:
            continue
        if row.get("replacement_state", "active") != "active":
            continue
        model_id = str(row.get("primary_owner_model_id", ""))
        if not model_id:
            continue
        authority = row.get("path_authority", {})
        # Some owners intentionally carry more than one distinct external
        # intent.  Existing single-binding callers receive the first canonical
        # row while plane-aware callers can query the complete inventory below.
        bindings.setdefault(
            model_id,
            {
                "behavior_plane": behavior_plane,
                "business_intent_id": str(row.get("business_intent_id", "")),
                "behavior_commitment_id": str(row.get("commitment_id", "")),
                "primary_path_id": str(authority.get("primary_path_id", "")),
            },
        )
    return bindings


def commitment_inventory() -> tuple[dict[str, str], ...]:
    """Return every active commitment without collapsing same-owner intents."""

    payload: dict[str, Any] = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    rows = []
    for row in payload["ledger"]["commitments"]:
        if row.get("in_scope", True) is not True:
            continue
        if row.get("replacement_state", "active") != "active":
            continue
        authority = row.get("path_authority", {})
        rows.append(
            {
                "behavior_plane": str(row.get("behavior_plane", "")),
                "business_intent_id": str(row.get("business_intent_id", "")),
                "behavior_commitment_id": str(row.get("commitment_id", "")),
                "primary_owner_model_id": str(
                    row.get("primary_owner_model_id", "")
                ),
                "primary_path_id": str(authority.get("primary_path_id", "")),
            }
        )
    return tuple(rows)


__all__ = [
    "ALL_SOURCE_SCOPE_REVISION",
    "LEDGER_PATH",
    "commitment_bindings",
    "commitment_inventory",
]
