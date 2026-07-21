from __future__ import annotations

import inspect

import pytest

from matters.providers.base import ProviderWriteForbidden
from matters.providers.gmail import (
    GmailAttachmentMetadata,
    GmailAuthorizedPage,
    GmailMessageContent,
    GmailMessageMetadata,
    GmailPageRejected,
    GmailReadManifest,
    GmailReadOnlyAdapter,
)


def _opaque(value: str) -> str:
    from hashlib import sha256

    return "sha256:" + sha256(value.encode("utf-8")).hexdigest()


def _manifest(**changes) -> GmailReadManifest:
    values = {
        "scope_id": "scope:synthetic-gmail",
        "account_ref": _opaque("synthetic-account"),
        "authorization_revision": "authorization:1",
        "query_fingerprint": _opaque("inbox-sent-archive"),
        "policy_revision": "policy:1",
        "attachment_metadata_allowed": True,
        "attachment_content_allowed": True,
    }
    values.update(changes)
    return GmailReadManifest(**values)


def _page(**changes) -> GmailAuthorizedPage:
    values = {
        "scope_id": "scope:synthetic-gmail",
        "account_ref": _opaque("synthetic-account"),
        "authorization_revision": "authorization:1",
        "query_fingerprint": _opaque("inbox-sent-archive"),
        "policy_revision": "policy:1",
        "requested_cursor": "",
        "next_cursor": "page:2",
        "terminal": False,
        "messages": (
            GmailMessageMetadata(
                "msg-1",
                "thread-1",
                "primary",
                ("inbox",),
                "2026-01-01T00:00:00Z",
                attachments=(
                    GmailAttachmentMetadata(
                        "att-1",
                        "synthetic.txt",
                        "text/plain",
                        9,
                    ),
                ),
            ),
            GmailMessageMetadata(
                "msg-spam",
                "thread-spam",
                "spam",
                ("spam",),
                "2026-01-02T00:00:00Z",
            ),
            GmailMessageMetadata(
                "msg-promo",
                "thread-promo",
                "promotions",
                ("promotions",),
                "2026-01-03T00:00:00Z",
            ),
            GmailMessageMetadata(
                "msg-social",
                "thread-social",
                "social",
                ("social",),
                "2026-01-04T00:00:00Z",
            ),
        ),
        "contents": (
            GmailMessageContent(
                "msg-1",
                "synthetic body",
                headers={"Subject": "Synthetic"},
                attachment_content={"att-1": b"synthetic"},
            ),
            GmailMessageContent("msg-spam", "synthetic spam"),
        ),
    }
    values.update(changes)
    return GmailAuthorizedPage(**values)


def test_gmail_metadata_projection_is_deterministic_and_body_free():
    adapter = GmailReadOnlyAdapter(_manifest())
    first = adapter.accept_page(_page())
    retry = adapter.accept_page(_page())

    assert first == retry
    assert first.coverage == "partial"
    assert not first.terminal
    assert "synthetic body" not in repr(first)
    dispositions = {
        item.envelope.external_id: item.recommended_disposition
        for item in first.items
        if item.envelope.object_type == "gmail_message"
    }
    message_items = [
        item
        for item in first.items
        if item.envelope.object_type == "gmail_message"
    ]
    assert "hard_excluded" in dispositions.values()
    promotion = next(
        item
        for item in message_items
        if item.envelope.payload["category"] == "promotions"
    )
    ordinary_unincluded = next(
        item
        for item in message_items
        if item.envelope.payload["category"] == "social"
    )
    assert promotion.recommended_disposition == "not_tracked"
    assert ordinary_unincluded.recommended_disposition == "metadata_only"


def test_gmail_tracked_content_preserves_thread_and_attachment_parents():
    adapter = GmailReadOnlyAdapter(_manifest())
    discovery = adapter.accept_page(_page())
    message = next(
        item.envelope
        for item in discovery.items
        if item.envelope.object_type == "gmail_message"
        and item.envelope.payload["provider_message_id"] == "msg-1"
    )
    attachment = next(
        item.envelope
        for item in discovery.items
        if item.envelope.object_type == "gmail_attachment"
    )
    results = adapter.read_page(
        _page(),
        tracking_dispositions={
            message.external_id: "tracked",
            attachment.external_id: "tracked",
        },
    )
    ingested = [item for item in results if item.ingested]

    assert [item.envelope.object_type for item in ingested] == [
        "gmail_message",
        "gmail_attachment",
    ]
    assert ingested[0].envelope.payload["body_text"] == "synthetic body"
    assert (
        ingested[1].envelope.metadata["parent_external_id"]
        == ingested[0].external_id
    )
    assert len(ingested[1].envelope.references) == 3
    spam = next(
        item for item in results if item.disposition == "hard_excluded"
    )
    assert spam.envelope is None


def test_gmail_cursor_scope_and_zero_mailbox_mutation_are_enforced():
    adapter = GmailReadOnlyAdapter(_manifest())

    with pytest.raises(GmailPageRejected, match="cursor_mismatch"):
        adapter.accept_page(_page(), cursor="wrong")
    with pytest.raises(ProviderWriteForbidden, match="writes are forbidden"):
        adapter.write({"operation": "archive"})

    signature = str(inspect.signature(GmailReadOnlyAdapter)).casefold()
    assert "token" not in signature
    assert "credential" not in signature
    assert not hasattr(adapter, "send")
    assert not hasattr(adapter, "archive")
    assert not hasattr(adapter, "delete")
    assert not hasattr(adapter, "change_labels")


def test_gmail_injected_page_source_retries_same_cursor_idempotently():
    calls: list[str] = []

    def source(cursor: str) -> GmailAuthorizedPage:
        calls.append(cursor)
        return _page(requested_cursor=cursor)

    adapter = GmailReadOnlyAdapter(_manifest(), page_source=source)
    first = adapter.discover(cursor="")
    retry = adapter.discover(cursor="")

    assert first == retry
    assert calls == ["", ""]


def test_fixed_authorized_from_nontracks_older_rows_without_reading_bodies():
    adapter = GmailReadOnlyAdapter(_manifest(authorized_from="2025-07-20"))
    old = GmailMessageMetadata(
        "old-message",
        "old-thread",
        "inbox",
        ("inbox",),
        "2025-07-19T23:59:59Z",
    )
    current = GmailMessageMetadata(
        "current-message",
        "current-thread",
        "inbox",
        ("inbox",),
        "2025-07-20T00:00:00Z",
    )
    page = _page(
        messages=(old, current),
        contents=(
            GmailMessageContent("old-message", "old body must not be read"),
            GmailMessageContent("current-message", "current body"),
        ),
    )

    discovery = adapter.accept_page(page)
    old_item = next(
        item
        for item in discovery.items
        if item.envelope.payload.get("provider_message_id") == "old-message"
    )
    current_item = next(
        item
        for item in discovery.items
        if item.envelope.payload.get("provider_message_id") == "current-message"
    )
    assert old_item.recommended_disposition == "not_tracked"
    assert old_item.reason == "gmail_before_authorized_from"
    assert current_item.recommended_disposition == "tracked"

    results = adapter.read_page(
        page,
        tracking_dispositions={
            old_item.envelope.external_id: "tracked",
            current_item.envelope.external_id: "tracked",
        },
    )
    old_result = next(
        item for item in results if item.external_id == old_item.envelope.external_id
    )
    current_result = next(
        item
        for item in results
        if item.external_id == current_item.envelope.external_id
    )
    assert old_result.disposition == "not_tracked"
    assert old_result.reason == "gmail_before_authorized_from"
    assert old_result.envelope is None
    assert current_result.ingested
    assert current_result.envelope.payload["body_text"] == "current body"


def test_empty_authorized_from_keeps_full_history_and_rejects_rolling_values():
    adapter = GmailReadOnlyAdapter(_manifest())
    old_page = _page(
        messages=(
            GmailMessageMetadata(
                "old-message", "old-thread", "inbox", ("inbox",), "2020-01-01"
            ),
        ),
        contents=(),
    )

    item = next(
        item
        for item in adapter.accept_page(old_page).items
        if item.envelope.object_type == "gmail_message"
    )
    assert adapter.manifest.authorized_from == ""
    assert item.recommended_disposition == "tracked"
    with pytest.raises(ValueError, match="fixed YYYY-MM-DD"):
        _manifest(authorized_from="last-365-days")


def test_authorized_from_successors_can_only_keep_or_expand_history():
    prior = _manifest(authorized_from="2025-07-20")

    _manifest(authorized_from="2025-07-20").assert_not_narrower_than(prior)
    _manifest(authorized_from="2024-01-01").assert_not_narrower_than(prior)
    _manifest().assert_not_narrower_than(prior)
    with pytest.raises(ValueError, match="cannot move later"):
        _manifest(authorized_from="2025-07-21").assert_not_narrower_than(prior)
    with pytest.raises(ValueError, match="cannot narrow full history"):
        _manifest(authorized_from="2025-07-20").assert_not_narrower_than(
            _manifest()
        )
