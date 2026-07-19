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
        attachment_id=str(item["id"]),
        filename=str(item.get("filename", "")),
        media_type=str(item.get("media_type", "application/octet-stream")),
        size=int(item.get("size", 0)),
    )


def ingest(
    payload: Mapping[str, Any],
    *,
    private_root: Path,
    repository_root: Path,
    content_limit: int,
) -> dict[str, Any]:
    query = str(payload["query"])
    account = str(payload["account"])
    rows = tuple(dict(item) for item in payload.get("messages", ()))
    query_ref = _opaque(query)
    manifest = GmailReadManifest(
        scope_id="gmail-scope:" + query_ref.removeprefix("sha256:")[:24],
        account_ref=_opaque(account),
        authorization_revision=str(
            payload.get("authorization_revision", "connector-read:v1")
        ),
        query_fingerprint=query_ref,
        policy_revision=str(payload.get("policy_revision", "policy:v1")),
        attachment_metadata_allowed=True,
        attachment_content_allowed=False,
    )
    messages = tuple(
        GmailMessageMetadata(
            message_id=str(row["id"]),
            thread_id=str(row["thread_id"]),
            category=_category(tuple(row.get("labels", ()))),
            label_ids=tuple(row.get("labels", ())),
            internal_date=str(row["email_ts"]),
            attachments=tuple(
                _attachment(item) for item in row.get("attachments", ())
            ),
            metadata={
                "subject": str(row.get("subject", "")),
                "sender": str(row.get("from", "")),
                "snippet": str(row.get("snippet", "")),
            },
        )
        for row in rows
    )
    contents = tuple(
        GmailMessageContent(
            message_id=str(row["id"]),
            body_text=str(row["body"]),
            headers={
                "subject": str(row.get("subject", "")),
                "from": str(row.get("from", "")),
                "to": ", ".join(str(item) for item in row.get("to", ())),
            },
        )
        for row in rows
        if row.get("body") is not None
    )
    page = GmailAuthorizedPage(
        scope_id=manifest.scope_id,
        account_ref=manifest.account_ref,
        authorization_revision=manifest.authorization_revision,
        query_fingerprint=manifest.query_fingerprint,
        policy_revision=manifest.policy_revision,
        requested_cursor="",
        next_cursor="",
        terminal=bool(payload.get("terminal", True)),
        messages=messages,
        contents=contents,
        coverage=str(payload.get("coverage", "complete")),
        denied_object_ids=tuple(payload.get("denied_object_ids", ())),
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
    )
    return asdict(result.summary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--content-limit", type=int, default=20)
    args = parser.parse_args()
    if args.content_limit < 0:
        return 2
    payload = json.load(sys.stdin)
    if not isinstance(payload, Mapping):
        return 2
    summary = ingest(
        payload,
        private_root=args.private_root,
        repository_root=Path(__file__).resolve().parents[1],
        content_limit=args.content_limit,
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
