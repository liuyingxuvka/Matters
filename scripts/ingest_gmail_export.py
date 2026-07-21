"""Ingest an already-authorized Gmail connector export from standard input.

The export is never written to the repository.  This bridge contains no OAuth
client and performs no mailbox mutation; it translates one explicitly bounded
read result into the provider-neutral private-runtime workflow.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Mapping

from matters.application.orchestrator import MatterService
from matters.application.source_workflows import SourceWorkflow
from matters.providers.gmail import (
    GmailAttachmentMetadata,
    GmailAuthorizedPage,
    GmailMessageContent,
    GmailMessageMetadata,
    GmailReadManifest,
    GmailReadOnlyAdapter,
)


def _opaque(value: str) -> str:
    return "sha256:" + sha256(value.encode("utf-8")).hexdigest()


def _text(value: object) -> str:
    """Normalize connector nulls without materializing the string ``None``."""

    return "" if value is None else str(value)


def _category(labels: tuple[str, ...]) -> str:
    values = {item.upper() for item in labels}
    if "SPAM" in values:
        return "spam"
    if "TRASH" in values:
        return "trash"
    if "CATEGORY_PROMOTIONS" in values:
        return "promotions"
    if "SENT" in values:
        return "sent"
    if "INBOX" in values:
        return "inbox"
    return "archived"


def _attachment(item: Mapping[str, Any]) -> GmailAttachmentMetadata:
    return GmailAttachmentMetadata(
        attachment_id=str(item.get("attachment_id") or item["id"]),
        filename=str(item.get("filename", "")),
        media_type=str(
            item.get("mime_type")
            or item.get("media_type", "application/octet-stream")
        ),
        size=int(item.get("size_bytes", item.get("size", 0))),
    )


def _sender(item: Mapping[str, Any]) -> str:
    return _text(item.get("from_") or item.get("from"))


def _message(row: Mapping[str, Any]) -> GmailMessageMetadata:
    message_id = _text(row.get("id"))
    if not message_id:
        raise ValueError("Gmail connector row requires a message id")
    thread_id = _text(row.get("thread_id"))
    internal_date = _text(row.get("email_ts"))
    raw_labels = row.get("labels")
    labels = tuple(
        _text(item)
        for item in (raw_labels if isinstance(raw_labels, (list, tuple)) else ())
        if _text(item)
    )
    identity_only = (
        bool(row.get("identity_only"))
        or _text(row.get("content_status")) == "identity_only"
        or not thread_id
        or not internal_date
        or raw_labels is None
    )
    if identity_only and row.get("body") is not None:
        raise ValueError(
            "identity-only Gmail connector rows cannot carry body content"
        )
    return GmailMessageMetadata(
        message_id=message_id,
        thread_id=thread_id,
        category="unknown" if identity_only else _category(labels),
        label_ids=labels,
        internal_date=internal_date,
        attachments=(
            ()
            if identity_only
            else tuple(
                _attachment(item) for item in row.get("attachments", ())
            )
        ),
        metadata={
            "subject": _text(row.get("subject")),
            "sender": _sender(row),
            "snippet": _text(row.get("snippet")),
        },
        identity_only=identity_only,
    )


def manifest_from_payload(payload: Mapping[str, Any]) -> GmailReadManifest:
    query = _text(payload.get("query"))
    account = _text(payload.get("account"))
    if not query or not account:
        raise ValueError("Gmail connector query and account are required")
    query_ref = _opaque(query)
    return GmailReadManifest(
        scope_id="gmail-scope:" + query_ref.removeprefix("sha256:")[:24],
        account_ref=_opaque(account),
        authorization_revision=_text(
            payload.get("authorization_revision", "connector-read:v1")
        ),
        query_fingerprint=query_ref,
        policy_revision=_text(payload.get("policy_revision", "policy:v1")),
        attachment_metadata_allowed=True,
        attachment_content_allowed=False,
        # This is optional and fixed.  Absence deliberately preserves the
        # product's full-history Gmail capability rather than creating a
        # moving cutoff based on the import date.
        authorized_from=_text(payload.get("authorized_from")),
    )


def authorized_page_from_payload(
    payload: Mapping[str, Any],
    manifest: GmailReadManifest,
    *,
    requested_cursor: str = "",
    next_cursor: str = "",
    terminal: bool | None = None,
    coverage: str | None = None,
) -> GmailAuthorizedPage:
    rows = tuple(dict(item) for item in payload.get("messages", ()))
    messages = tuple(_message(row) for row in rows)
    identity_only_ids = {
        message.message_id for message in messages if message.identity_only
    }
    contents = tuple(
        GmailMessageContent(
            message_id=_text(row.get("id")),
            body_text=_text(row.get("body")),
            headers={
                "subject": _text(row.get("subject")),
                "from": _sender(row),
                "to": ", ".join(
                    _text(item) for item in row.get("to", ()) if _text(item)
                ),
            },
        )
        for row in rows
        if row.get("body") is not None
        and _text(row.get("id")) not in identity_only_ids
    )
    return GmailAuthorizedPage(
        scope_id=manifest.scope_id,
        account_ref=manifest.account_ref,
        authorization_revision=manifest.authorization_revision,
        query_fingerprint=manifest.query_fingerprint,
        policy_revision=manifest.policy_revision,
        requested_cursor=requested_cursor,
        next_cursor=next_cursor,
        terminal=(
            bool(payload.get("terminal", True))
            if terminal is None
            else terminal
        ),
        messages=messages,
        contents=contents,
        coverage=_text(payload.get("coverage", "complete"))
        if coverage is None
        else coverage,
        denied_object_ids=tuple(
            _text(item)
            for item in payload.get("denied_object_ids", ())
            if _text(item)
        ),
    )


def ingest(
    payload: Mapping[str, Any],
    *,
    private_root: Path,
    repository_root: Path,
    content_limit: int,
    content_offset: int = 0,
) -> dict[str, Any]:
    manifest = manifest_from_payload(payload)
    # This legacy entry point deliberately exposes one bounded page. A real
    # cursor chain is handled by ingest_gmail_pages.py.
    page = authorized_page_from_payload(
        payload,
        manifest,
        requested_cursor="",
        next_cursor="",
    )
    adapter = GmailReadOnlyAdapter(
        manifest,
        page_source=lambda cursor: page,
    )
    service = MatterService(
        repository_root=repository_root,
        private_root=private_root,
    )
    result = SourceWorkflow(service).run_gmail(
        adapter,
        content_limit=content_limit,
        content_offset=content_offset,
    )
    return asdict(result.summary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--content-limit", type=int, default=20)
    parser.add_argument("--content-offset", type=int, default=0)
    args = parser.parse_args()
    if args.content_limit < 0 or args.content_offset < 0:
        return 2
    payload = json.load(sys.stdin)
    if not isinstance(payload, Mapping):
        return 2
    summary = ingest(
        payload,
        private_root=args.private_root,
        repository_root=Path(__file__).resolve().parents[1],
        content_limit=args.content_limit,
        content_offset=args.content_offset,
    )
    print(
        json.dumps(
            {"ok": True, "result": summary},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
