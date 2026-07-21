"""Validate and normalize private Gmail connector pages without writing them.

The report contains only counts and opaque fingerprints. Raw message ids,
cursor tokens, account identifiers, and message content are never printed.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class GmailPageChainError(ValueError):
    """A page chain cannot be ingested without risking false coverage."""


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _text(value: object) -> str:
    return "" if value is None else str(value)


def _cursor(payload: Mapping[str, Any], *, requested: bool) -> tuple[bool, str]:
    keys = (
        ("requested_page_token", "requested_cursor")
        if requested
        else ("next_page_token", "next_cursor")
    )
    for key in keys:
        if key in payload:
            return True, _text(payload.get(key))
    return False, ""


def _present(value: object) -> bool:
    return value is not None and value != "" and value != [] and value != ()


def _row_ref(message_id: str) -> str:
    return "gmail-message:" + sha256(message_id.encode("utf-8")).hexdigest()[:16]


def _normalized_email_ts(value: object) -> str | None:
    raw = _text(value).strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _normalized_attachment(item: Mapping[str, Any]) -> dict[str, Any]:
    attachment_id = _text(item.get("attachment_id") or item.get("id"))
    if not attachment_id:
        raise GmailPageChainError("gmail_attachment_identity_missing")
    return {
        "id": attachment_id,
        "attachment_id": attachment_id,
        "filename": _text(item.get("filename")),
        "mime_type": _text(item.get("mime_type") or item.get("media_type")),
        "size_bytes": int(item.get("size_bytes", item.get("size", 0)) or 0),
    }


def _normalized_row(item: Mapping[str, Any]) -> dict[str, Any]:
    message_id = _text(item.get("id"))
    if not message_id:
        raise GmailPageChainError("gmail_message_identity_missing")
    raw_labels = item.get("labels")
    labels = [
        _text(value)
        for value in (raw_labels if isinstance(raw_labels, (list, tuple)) else ())
        if _text(value)
    ]
    thread_id = _text(item.get("thread_id"))
    email_ts = _normalized_email_ts(item.get("email_ts"))
    labels_present = bool(
        item.get("labels_present")
        if "labels_present" in item
        else raw_labels is not None
    )
    identity_only = (
        bool(item.get("identity_only"))
        or _text(item.get("content_status")) == "identity_only"
        or not thread_id
        or not email_ts
        or not labels_present
    )
    if identity_only and item.get("body") is not None:
        raise GmailPageChainError(
            f"gmail_identity_only_body_conflict:{_row_ref(message_id)}"
        )
    return {
        "id": message_id,
        "thread_id": thread_id or None,
        "from_": _text(item.get("from_") or item.get("from")) or None,
        "to": [
            _text(value)
            for value in item.get("to", ())
            if _text(value)
        ],
        "subject": _text(item.get("subject")) or None,
        "snippet": _text(item.get("snippet")) or None,
        "body": item.get("body"),
        "labels": labels,
        "labels_present": labels_present,
        "email_ts": email_ts,
        "attachments": [
            _normalized_attachment(value)
            for value in item.get("attachments", ())
        ],
        "content_status": (
            "identity_only"
            if identity_only
            else ("full" if item.get("body") is not None else "metadata_only")
        ),
        "identity_only": identity_only,
    }


def _richness(row: Mapping[str, Any]) -> tuple[int, ...]:
    return (
        int(row.get("body") is not None),
        int(bool(row.get("thread_id") and row.get("email_ts"))),
        len(row.get("labels", ())),
        sum(
            bool(row.get(key))
            for key in ("subject", "from_", "snippet")
        ),
        len(row.get("attachments", ())),
    )


def _merge_attachments(
    left: Iterable[Mapping[str, Any]],
    right: Iterable[Mapping[str, Any]],
    *,
    message_id: str,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in (*tuple(left), *tuple(right)):
        normalized = _normalized_attachment(item)
        attachment_id = normalized["attachment_id"]
        prior = merged.get(attachment_id)
        if prior is None:
            merged[attachment_id] = normalized
            continue
        for key in ("filename", "mime_type", "size_bytes"):
            if (
                _present(prior.get(key))
                and _present(normalized.get(key))
                and prior[key] != normalized[key]
            ):
                raise GmailPageChainError(
                    "gmail_attachment_metadata_conflict:"
                    + _row_ref(message_id)
                    + ":"
                    + _digest(attachment_id).removeprefix("sha256:")[:12]
                )
            if not _present(prior.get(key)) and _present(normalized.get(key)):
                prior[key] = normalized[key]
    return [merged[key] for key in sorted(merged)]


def merge_message_rows(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge duplicate observations, retaining the richer compatible row."""

    a = _normalized_row(left)
    b = _normalized_row(right)
    if a["id"] != b["id"]:
        raise GmailPageChainError("gmail_merge_identity_mismatch")
    message_ref = _row_ref(a["id"])
    for key in ("thread_id", "email_ts", "body", "subject", "from_"):
        if (
            _present(a.get(key))
            and _present(b.get(key))
            and a[key] != b[key]
        ):
            raise GmailPageChainError(
                f"gmail_message_field_conflict:{message_ref}:{key}"
            )
    richer, other = (a, b) if _richness(a) >= _richness(b) else (b, a)
    merged = dict(richer)
    for key in ("thread_id", "email_ts", "body", "subject", "from_", "snippet"):
        if not _present(merged.get(key)) and _present(other.get(key)):
            merged[key] = other[key]
    merged["labels"] = sorted(
        set(str(item) for item in a.get("labels", ()))
        | set(str(item) for item in b.get("labels", ()))
    )
    merged["labels_present"] = bool(
        a.get("labels_present") or b.get("labels_present")
    )
    merged["to"] = sorted(
        set(str(item) for item in a.get("to", ()))
        | set(str(item) for item in b.get("to", ()))
    )
    merged["attachments"] = _merge_attachments(
        a.get("attachments", ()),
        b.get("attachments", ()),
        message_id=a["id"],
    )
    identity_only = (
        not merged.get("thread_id")
        or not merged.get("email_ts")
        or not merged["labels_present"]
    )
    merged["content_status"] = (
        "identity_only"
        if identity_only
        else ("full" if merged.get("body") is not None else "metadata_only")
    )
    merged["identity_only"] = identity_only
    return merged


@dataclass(frozen=True)
class GmailPageChain:
    pages: tuple[dict[str, Any], ...]
    report: Mapping[str, Any]


def audit_page_payloads(
    payloads: Sequence[Mapping[str, Any]],
) -> GmailPageChain:
    if not payloads:
        raise GmailPageChainError("gmail_page_chain_empty")
    pages = [dict(payload) for payload in payloads]
    manifest_fields = (
        "query",
        "account",
        "authorization_revision",
        "policy_revision",
        "authorized_from",
    )
    expected_manifest = tuple(_text(pages[0].get(key)) for key in manifest_fields)
    if not expected_manifest[0] or not expected_manifest[1]:
        raise GmailPageChainError("gmail_page_manifest_incomplete")
    for payload in pages[1:]:
        observed = tuple(_text(payload.get(key)) for key in manifest_fields)
        if observed != expected_manifest:
            raise GmailPageChainError("gmail_page_manifest_conflict")

    cursor_fields_complete = True
    prior_next = ""
    seen_next: set[str] = set()
    terminal_indexes: list[int] = []
    for index, payload in enumerate(pages):
        requested_present, requested = _cursor(payload, requested=True)
        next_present, next_cursor = _cursor(payload, requested=False)
        terminal = bool(payload.get("terminal", False))
        if not requested_present:
            cursor_fields_complete = False
        if index == 0:
            if requested_present and requested:
                raise GmailPageChainError("gmail_first_page_cursor_not_empty")
        elif not requested_present or requested != prior_next:
            cursor_fields_complete = False
        if terminal:
            terminal_indexes.append(index)
            if next_cursor:
                raise GmailPageChainError("gmail_terminal_page_has_next_cursor")
        elif index < len(pages) - 1 and (not next_present or not next_cursor):
            raise GmailPageChainError("gmail_nonterminal_page_missing_next_cursor")
        if next_cursor:
            if next_cursor in seen_next:
                raise GmailPageChainError("gmail_cursor_cycle_detected")
            seen_next.add(next_cursor)
        prior_next = next_cursor
    if terminal_indexes and terminal_indexes != [len(pages) - 1]:
        raise GmailPageChainError("gmail_terminal_page_not_last")

    merged_by_id: dict[str, dict[str, Any]] = {}
    first_page_by_id: dict[str, int] = {}
    raw_count = duplicate_count = 0
    denied: set[str] = set()
    for index, payload in enumerate(pages):
        for item in payload.get("messages", ()):
            row = _normalized_row(item)
            raw_count += 1
            message_id = row["id"]
            if message_id in merged_by_id:
                duplicate_count += 1
                merged_by_id[message_id] = merge_message_rows(
                    merged_by_id[message_id],
                    row,
                )
            else:
                merged_by_id[message_id] = row
                first_page_by_id[message_id] = index
        denied.update(
            _text(item)
            for item in payload.get("denied_object_ids", ())
            if _text(item)
        )

    normalized_pages: list[dict[str, Any]] = []
    for index, payload in enumerate(pages):
        projected = dict(payload)
        projected["messages"] = [
            merged_by_id[message_id]
            for message_id in sorted(merged_by_id)
            if first_page_by_id[message_id] == index
        ]
        projected["denied_object_ids"] = sorted(denied)
        normalized_pages.append(projected)

    last_terminal = bool(pages[-1].get("terminal", False))
    complete = last_terminal and cursor_fields_complete
    identity_only_count = sum(
        row.get("content_status") == "identity_only"
        for row in merged_by_id.values()
    )
    body_count = sum(
        row.get("body") is not None for row in merged_by_id.values()
    )
    report = {
        "artifact_type": "matters.gmail-page-chain-audit.v1",
        "status": (
            "complete"
            if complete
            else ("blocked" if last_terminal else "partial")
        ),
        "safe_terminal_coverage": complete,
        "cursor_chain_verified": cursor_fields_complete,
        "page_count": len(pages),
        "raw_message_count": raw_count,
        "unique_message_count": len(merged_by_id),
        "duplicate_message_count": duplicate_count,
        "identity_only_count": identity_only_count,
        "content_bearing_count": body_count,
        "denied_id_count": len(denied),
        "last_page_terminal": last_terminal,
        "continuation_cursor_present": bool(_cursor(pages[-1], requested=False)[1]),
        "query_fingerprint": _digest(expected_manifest[0]),
        "account_ref": _digest(expected_manifest[1]),
        "authorized_from": expected_manifest[4],
        "page_set_fingerprint": _digest(
            {
                "message_refs": sorted(_row_ref(item) for item in merged_by_id),
                "cursor_hashes": [
                    _digest(_cursor(payload, requested=False)[1])
                    for payload in pages
                ],
                "terminal": last_terminal,
            }
        ),
        "claim_boundary": (
            "Complete means the supplied page set has one verified cursor chain "
            "and its last page is terminal. It does not claim that an omitted "
            "query or account scope was searched."
        ),
    }
    return GmailPageChain(tuple(normalized_pages), report)


def audit_page_paths(paths: Sequence[Path]) -> GmailPageChain:
    return audit_page_payloads(
        tuple(
            json.loads(path.resolve().read_text(encoding="utf-8"))
            for path in paths
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", action="append", type=Path, required=True)
    args = parser.parse_args()
    try:
        chain = audit_page_paths(tuple(args.page))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "status": "blocked",
                    "reason": str(error),
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps({"ok": True, **dict(chain.report)}, sort_keys=True))
    return 0 if chain.report["status"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
