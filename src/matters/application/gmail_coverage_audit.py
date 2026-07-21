"""Privacy-safe, read-only coverage audit for verified Gmail manifests."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from matters.application.coverage_ledger import STAGE_ORDER
from matters.infrastructure.sqlite.store import SQLiteStore
from matters.providers.gmail.adapter import (
    gmail_account_ref,
    gmail_message_object_id,
    gmail_scope_id,
)


_SINGLE_RECEIPT_TYPES = frozenset(
    {
        "matters.gmail-search-chain-receipt.v1",
        "matters.gmail-page-chain-audit.v1",
    }
)
_COMBINED_RECEIPT_TYPE = "matters.gmail-combined-coverage-receipt.v1"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _fingerprint(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _text(value: object) -> str:
    return "" if value is None else str(value)


def _cursor(payload: Mapping[str, Any], *, requested: bool) -> str:
    keys = (
        ("requested_page_token", "requested_cursor")
        if requested
        else ("next_page_token", "next_cursor")
    )
    for key in keys:
        if key in payload:
            return _text(payload.get(key))
    raise ValueError("Gmail page cursor evidence is incomplete")


def _load_json(path: Path) -> tuple[dict[str, Any], bytes]:
    resolved = path.resolve()
    if resolved.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Gmail audit input exceeds the read-only size bound")
    encoded = resolved.read_bytes()
    payload = json.loads(encoded.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Gmail audit input must be a JSON object")
    return payload, encoded


def _receipt_pages(receipt_path: Path, receipt: Mapping[str, Any]) -> tuple[Path, ...]:
    artifact_type = _text(receipt.get("artifact_type"))
    if artifact_type == _COMBINED_RECEIPT_TYPE:
        raise ValueError("Combined Gmail coverage receipts require explicit pages")
    suffix = "coverage-receipt.json"
    if not receipt_path.name.endswith(suffix):
        raise ValueError("Gmail coverage receipt pages must be explicit")
    prefix = receipt_path.name[: -len(suffix)]
    paths = tuple(sorted(receipt_path.parent.glob(prefix + "page-*.json")))
    if not paths:
        raise ValueError("Gmail coverage receipt page set is unavailable")
    return paths


@dataclass(frozen=True)
class _ManifestMembership:
    scope_ids: tuple[str, ...]
    object_ids: tuple[str, ...]
    page_count: int
    chain_count: int
    message_set_fingerprint: str
    object_set_fingerprint: str
    manifest_fingerprint: str


def _verified_membership(
    pages: Sequence[Mapping[str, Any]],
    receipt: Mapping[str, Any] | None,
) -> _ManifestMembership:
    if not pages:
        raise ValueError("Gmail coverage audit requires verified pages")
    grouped: dict[tuple[str, str, str, str, str], list[Mapping[str, Any]]] = {}
    for payload in pages:
        manifest = (
            _text(payload.get("query")),
            _text(payload.get("account")),
            _text(payload.get("authorization_revision")),
            _text(payload.get("policy_revision")),
            _text(payload.get("authorized_from")),
        )
        if not manifest[0] or not manifest[1]:
            raise ValueError("Gmail page manifest is incomplete")
        grouped.setdefault(manifest, []).append(payload)

    raw_message_ids: set[str] = set()
    opaque_object_ids: set[str] = set()
    scope_ids: set[str] = set()
    manifest_projection: list[tuple[str, str, str, str, str]] = []
    for manifest, chain_pages in grouped.items():
        query, account, authorization_revision, policy_revision, authorized_from = manifest
        by_requested: dict[str, Mapping[str, Any]] = {}
        for payload in chain_pages:
            requested = _cursor(payload, requested=True)
            if requested in by_requested:
                raise ValueError("Gmail page chain has a duplicate cursor")
            by_requested[requested] = payload
        if "" not in by_requested:
            raise ValueError("Gmail page chain has no initial page")

        ordered: list[Mapping[str, Any]] = []
        requested = ""
        seen_cursors: set[str] = set()
        while requested in by_requested:
            if requested in seen_cursors:
                raise ValueError("Gmail page chain has a cursor cycle")
            seen_cursors.add(requested)
            page = by_requested[requested]
            ordered.append(page)
            next_cursor = _cursor(page, requested=False)
            terminal = bool(page.get("terminal", False))
            if terminal:
                if next_cursor or len(ordered) != len(chain_pages):
                    raise ValueError("Gmail page chain terminal evidence is invalid")
                break
            if not next_cursor:
                raise ValueError("Gmail page chain continuation is missing")
            requested = next_cursor
        if not ordered or not bool(ordered[-1].get("terminal", False)):
            raise ValueError("Gmail page chain is not terminal")
        if len(ordered) != len(chain_pages):
            raise ValueError("Gmail page chain contains unreachable pages")

        account_ref = gmail_account_ref(account)
        scope_id = gmail_scope_id(query)
        scope_ids.add(scope_id)
        manifest_projection.append(
            (
                scope_id,
                account_ref,
                authorization_revision,
                policy_revision,
                authorized_from,
            )
        )
        chain_ids: set[str] = set()
        for page in ordered:
            messages = page.get("messages", ())
            if not isinstance(messages, list):
                raise ValueError("Gmail page messages are invalid")
            for item in messages:
                if not isinstance(item, Mapping):
                    raise ValueError("Gmail page message projection is invalid")
                message_id = _text(item.get("id"))
                if not message_id or message_id in chain_ids:
                    raise ValueError("Gmail page message membership is invalid")
                chain_ids.add(message_id)
                raw_message_ids.add(message_id)
                opaque_object_ids.add(
                    gmail_message_object_id(account_ref, message_id)
                )

    message_set_fingerprint = _fingerprint(sorted(raw_message_ids))
    if receipt is not None:
        artifact_type = _text(receipt.get("artifact_type"))
        if artifact_type not in _SINGLE_RECEIPT_TYPES | {_COMBINED_RECEIPT_TYPE}:
            raise ValueError("Gmail coverage receipt type is unsupported")
        expected_count_key = (
            "verified_union_message_count"
            if artifact_type == _COMBINED_RECEIPT_TYPE
            else "unique_message_count"
        )
        expected_fingerprint_key = (
            "verified_union_fingerprint"
            if artifact_type == _COMBINED_RECEIPT_TYPE
            else "message_set_fingerprint"
        )
        if int(receipt.get(expected_count_key, -1)) != len(raw_message_ids):
            raise ValueError("Gmail coverage receipt count does not match pages")
        receipt_fingerprint = _text(receipt.get(expected_fingerprint_key))
        if receipt_fingerprint and receipt_fingerprint != message_set_fingerprint:
            raise ValueError("Gmail coverage receipt membership does not match pages")
        if artifact_type in _SINGLE_RECEIPT_TYPES:
            if len(grouped) != 1 or int(receipt.get("page_count", -1)) != len(pages):
                raise ValueError("Gmail coverage receipt page count does not match")
            if not (
                bool(receipt.get("cursor_chain_verified", False))
                and bool(receipt.get("terminal", receipt.get("last_page_terminal", False)))
            ):
                raise ValueError("Gmail coverage receipt is not terminal")
            if "safe_terminal_coverage" in receipt and not bool(
                receipt.get("safe_terminal_coverage")
            ):
                raise ValueError("Gmail coverage receipt is not safely terminal")
            manifest = next(iter(grouped))
            expected_refs = {
                "query_fingerprint": _fingerprint(manifest[0]),
                "account_ref": _fingerprint(manifest[1]),
            }
            for key, expected in expected_refs.items():
                if key in receipt and _text(receipt.get(key)) != expected:
                    raise ValueError("Gmail coverage receipt manifest does not match")
            if (
                "authorized_from" in receipt
                and _text(receipt.get("authorized_from")) != manifest[4]
            ):
                raise ValueError("Gmail coverage receipt boundary does not match")

    return _ManifestMembership(
        scope_ids=tuple(sorted(scope_ids)),
        object_ids=tuple(sorted(opaque_object_ids)),
        page_count=len(pages),
        chain_count=len(grouped),
        message_set_fingerprint=message_set_fingerprint,
        object_set_fingerprint=_fingerprint(sorted(opaque_object_ids)),
        manifest_fingerprint=_fingerprint(sorted(manifest_projection)),
    )


@dataclass
class GmailManifestCoverageAuditService:
    store: SQLiteStore

    def audit(
        self,
        *,
        receipt_path: str = "",
        page_paths: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Audit exact verified Gmail membership without provider or state writes."""

        receipt: dict[str, Any] | None = None
        receipt_fingerprint = ""
        normalized_receipt = Path(receipt_path) if receipt_path else None
        if normalized_receipt is not None:
            receipt, receipt_bytes = _load_json(normalized_receipt)
            receipt_fingerprint = "sha256:" + sha256(receipt_bytes).hexdigest()
        normalized_pages = tuple(Path(item) for item in page_paths if str(item))
        if not normalized_pages and normalized_receipt is not None and receipt is not None:
            normalized_pages = _receipt_pages(normalized_receipt, receipt)
        if not normalized_pages:
            raise ValueError("Gmail coverage audit requires a receipt or page set")
        if len(normalized_pages) > 1_000:
            raise ValueError("Gmail coverage audit page bound is invalid")
        page_payloads = tuple(_load_json(path)[0] for path in normalized_pages)
        membership = _verified_membership(page_payloads, receipt)
        snapshot = self.store.gmail_manifest_coverage_snapshot(
            object_ids=membership.object_ids,
            scope_ids=membership.scope_ids,
            stage_order=STAGE_ORDER,
        )
        fixed_scope_complete = bool(snapshot["fixed_scope"]["set_equal"])
        coverage_complete = bool(snapshot["coverage"]["set_equal"])
        terminal_complete = (
            int(snapshot["coverage"]["terminal_identity_count"])
            == len(membership.object_ids)
        )
        return {
            "artifact_type": "matters.gmail-manifest-coverage-audit.v1",
            "status": (
                "complete"
                if fixed_scope_complete and coverage_complete and terminal_complete
                else "partial"
            ),
            "verified_input": {
                "page_count": membership.page_count,
                "chain_count": membership.chain_count,
                "unique_identity_count": len(membership.object_ids),
                "message_set_fingerprint": membership.message_set_fingerprint,
                "opaque_object_set_fingerprint": membership.object_set_fingerprint,
                "manifest_fingerprint": membership.manifest_fingerprint,
                "receipt_fingerprint": receipt_fingerprint,
            },
            **snapshot,
            "set_equality": {
                "fixed_scope_inventory": fixed_scope_complete,
                "cross_scope_inventory": (
                    int(snapshot["cross_scope"]["inventory_identity_count"])
                    == len(membership.object_ids)
                ),
                "coverage": coverage_complete,
            },
            "claim_boundary": (
                "The audit proves only indexed membership and stage counts for "
                "the supplied verified page set. Cross-scope identity hits do "
                "not prove fixed-scope inventory, extraction, modeling, or UI "
                "completion. No provider access or runtime write is performed."
            ),
        }


__all__ = ["GmailManifestCoverageAuditService"]
