from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from matters.application.coverage_ledger import ObjectCoverageLedger
from matters.application.gmail_coverage_audit import (
    GmailManifestCoverageAuditService,
)
from matters.infrastructure.sqlite.store import SQLiteStore
from matters.providers.gmail.adapter import (
    gmail_account_ref,
    gmail_message_object_id,
    gmail_scope_id,
)


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _page(
    *,
    query: str,
    account: str,
    message_ids: tuple[str, ...],
) -> dict[str, object]:
    return {
        "query": query,
        "account": account,
        "authorization_revision": "authorization:test",
        "policy_revision": "policy:test",
        "authorized_from": "2025-07-20",
        "coverage": "complete",
        "terminal": True,
        "requested_page_token": "",
        "next_page_token": "",
        "messages": [
            {
                "id": message_id,
                "subject": "private subject must never be projected",
                "body": None,
                "from_": "private-address@example.invalid",
                "content_status": "identity_only",
                "identity_only": True,
            }
            for message_id in message_ids
        ],
    }


def _write_verified_input(
    root: Path,
    *,
    query: str = "after:fixed",
    account: str = "private-account@example.invalid",
    message_ids: tuple[str, ...] = ("private-message-a", "private-message-b"),
) -> tuple[Path, tuple[Path, ...], tuple[str, ...], str]:
    folder = root / "verified"
    folder.mkdir()
    page_path = folder / "gmail-fixed-page-001.json"
    page_path.write_text(
        json.dumps(_page(query=query, account=account, message_ids=message_ids)),
        encoding="utf-8",
    )
    receipt_path = folder / "gmail-fixed-coverage-receipt.json"
    receipt_path.write_text(
        json.dumps(
            {
                "artifact_type": "matters.gmail-search-chain-receipt.v1",
                "status": "complete",
                "page_count": 1,
                "unique_message_count": len(message_ids),
                "cursor_chain_verified": True,
                "terminal": True,
                "message_set_fingerprint": _fingerprint(sorted(message_ids)),
            }
        ),
        encoding="utf-8",
    )
    account_ref = gmail_account_ref(account)
    object_ids = tuple(
        gmail_message_object_id(account_ref, message_id)
        for message_id in message_ids
    )
    return receipt_path, (page_path,), object_ids, gmail_scope_id(query)


def _inventory(
    store: SQLiteStore,
    *,
    scope_id: str,
    object_ids: tuple[str, ...],
    disposition: str,
) -> None:
    occurrences = tuple(
        {
            "occurrence_id": object_id,
            "provider": "gmail",
            "object_type": "message",
        }
        for object_id in object_ids
    )
    dispositions = tuple(
        {"occurrence_id": object_id, "status": disposition}
        for object_id in object_ids
    )
    inventory_revision = store.next_revision("inventory_snapshot", scope_id)
    store.append(
        "inventory_snapshot",
        scope_id,
        inventory_revision,
        {
            "scope_id": scope_id,
            "occurrences": occurrences,
            "dispositions": dispositions,
        },
    )
    ObjectCoverageLedger(store).reconcile_inventory(
        scope_id=scope_id,
        inventory_revision=inventory_revision,
        occurrences=occurrences,
        dispositions=dispositions,
    )


def test_manifest_audit_proves_exact_scope_membership_without_private_projection(
    tmp_path: Path,
) -> None:
    receipt, _pages, object_ids, scope_id = _write_verified_input(tmp_path)
    store = SQLiteStore(tmp_path / "private", tmp_path / "repo")
    _inventory(
        store,
        scope_id=scope_id,
        object_ids=object_ids,
        disposition="metadata_only",
    )

    result = GmailManifestCoverageAuditService(store).audit(
        receipt_path=str(receipt)
    )

    assert result["verified_input"]["unique_identity_count"] == 2
    assert result["fixed_scope"] == {
        "scope_count": 1,
        "inventory_identity_count": 2,
        "inventory_occurrence_count": 2,
        "missing_identity_count": 0,
        "set_equal": True,
    }
    assert result["cross_scope"]["ambiguous_identity_count"] == 0
    assert result["coverage"]["identity_count"] == 2
    assert result["coverage"]["disposition_counts"] == {"metadata_only": 2}
    assert result["stage_counts"]["source_version"] == {"missing": 2}
    assert result["stage_counts"]["content_selection"] == {"not_required": 2}
    serialized = json.dumps(result, sort_keys=True)
    for private_value in (
        "private-message-a",
        "private-message-b",
        "private subject",
        "private-address",
        "private-account",
        str(receipt),
    ):
        assert private_value not in serialized


def test_manifest_audit_separates_fixed_scope_from_cross_scope_identity_hits(
    tmp_path: Path,
) -> None:
    receipt, pages, object_ids, _scope_id = _write_verified_input(
        tmp_path,
        message_ids=("private-message-a", "private-message-b", "private-message-c"),
    )
    store = SQLiteStore(tmp_path / "private", tmp_path / "repo")
    _inventory(
        store,
        scope_id="gmail-scope:other-one",
        object_ids=object_ids[:2],
        disposition="tracked",
    )
    _inventory(
        store,
        scope_id="gmail-scope:other-two",
        object_ids=object_ids[:1],
        disposition="metadata_only",
    )

    result = GmailManifestCoverageAuditService(store).audit(
        receipt_path=str(receipt),
        page_paths=tuple(str(path) for path in pages),
    )

    assert result["status"] == "partial"
    assert result["fixed_scope"]["inventory_identity_count"] == 0
    assert result["fixed_scope"]["missing_identity_count"] == 3
    assert result["fixed_scope"]["set_equal"] is False
    assert result["cross_scope"]["inventory_identity_count"] == 2
    assert result["cross_scope"]["cross_scope_only_identity_count"] == 2
    assert result["cross_scope"]["missing_identity_count"] == 1
    assert result["cross_scope"]["ambiguous_identity_count"] == 1
    assert result["cross_scope"]["conflicting_disposition_identity_count"] == 1
    assert result["coverage"]["identity_count"] == 2
    assert result["coverage"]["missing_identity_count"] == 1
    assert result["stage_counts"]["authorization"]["manifest_only"] == 1
    assert result["set_equality"] == {
        "fixed_scope_inventory": False,
        "cross_scope_inventory": False,
        "coverage": False,
    }


def test_manifest_audit_rejects_receipt_membership_mismatch(tmp_path: Path) -> None:
    receipt, _pages, _object_ids, _scope_id = _write_verified_input(tmp_path)
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["unique_message_count"] = 99
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    store = SQLiteStore(tmp_path / "private", tmp_path / "repo")

    with pytest.raises(ValueError, match="count does not match"):
        GmailManifestCoverageAuditService(store).audit(
            receipt_path=str(receipt)
        )


def test_manifest_audit_queries_are_supported_by_exact_indexes(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "private", tmp_path / "repo")
    with store.connection() as connection:
        plans = {
            "fixed": connection.execute(
                "EXPLAIN QUERY PLAN SELECT object_id "
                "FROM inventory_occurrence_current "
                "WHERE scope_id=? AND object_id IN (?, ?)",
                ("gmail-scope:test", "gmail:message:a", "gmail:message:b"),
            ).fetchall(),
            "cross_scope": connection.execute(
                "EXPLAIN QUERY PLAN SELECT object_id, scope_id, disposition "
                "FROM inventory_occurrence_current WHERE object_id IN (?, ?)",
                ("gmail:message:a", "gmail:message:b"),
            ).fetchall(),
            "coverage": connection.execute(
                "EXPLAIN QUERY PLAN SELECT object_id FROM coverage_stage_index "
                "WHERE object_id IN (?, ?)",
                ("gmail:message:a", "gmail:message:b"),
            ).fetchall(),
            "stage": connection.execute(
                "EXPLAIN QUERY PLAN SELECT object_id FROM "
                "coverage_stage_status_index WHERE object_id IN (?, ?)",
                ("gmail:message:a", "gmail:message:b"),
            ).fetchall(),
        }
    details = {
        key: " ".join(str(row[3]) for row in rows)
        for key, rows in plans.items()
    }
    assert "sqlite_autoindex_inventory_occurrence_current_1" in details["fixed"]
    assert "inventory_occurrence_object_idx" in details["cross_scope"]
    assert "sqlite_autoindex_coverage_stage_index_1" in details["coverage"]
    assert "coverage_stage_status_object_idx" in details["stage"]
    assert all("SCAN snapshots" not in detail for detail in details.values())
