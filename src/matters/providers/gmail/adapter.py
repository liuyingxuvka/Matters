"""Read-only Gmail projection for already-authorized external read results.

This module contains no OAuth client, token field, browser control, or mailbox
mutation.  A connected app may inject a page source, or pass an already-read
``GmailAuthorizedPage`` directly.  Raw message content remains an immutable
private-runtime payload and is exposed only for currently tracked occurrences.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from hashlib import sha256
import json
from typing import Any

from matters.providers.base import (
    ExternalReference,
    ProviderEnvelope,
    ProviderWriteForbidden,
)


GMAIL_COVERAGE = frozenset({"complete", "partial", "unknown"})


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def gmail_account_ref(account: str) -> str:
    """Return the private-runtime opaque identity for one Gmail account."""

    normalized = str(account)
    if not normalized:
        raise ValueError("Gmail account identity is required")
    return "sha256:" + sha256(normalized.encode("utf-8")).hexdigest()


def gmail_scope_id(query: str) -> str:
    """Return the deterministic scope identity for one exact Gmail query."""

    normalized = str(query)
    if not normalized:
        raise ValueError("Gmail query is required")
    return "gmail-scope:" + sha256(normalized.encode("utf-8")).hexdigest()[:24]


def gmail_message_object_id(account_ref: str, message_id: str) -> str:
    """Project a provider message id into the canonical opaque object id."""

    normalized_account = str(account_ref)
    normalized_message = str(message_id)
    if not normalized_account.startswith("sha256:") or not normalized_message:
        raise ValueError("Gmail opaque account and message identities are required")
    value = f"{normalized_account}\0message\0{normalized_message}"
    return (
        "gmail:message:"
        + sha256(value.encode("utf-8")).hexdigest()[:24]
    )


@dataclass(frozen=True)
class GmailReadManifest:
    scope_id: str
    account_ref: str
    authorization_revision: str
    query_fingerprint: str
    policy_revision: str
    included_categories: frozenset[str] = frozenset(
        {"inbox", "sent", "archived"}
    )
    excluded_categories: frozenset[str] = frozenset({"spam", "trash"})
    attachment_metadata_allowed: bool = True
    attachment_content_allowed: bool = False
    # Empty deliberately means all history.  A non-empty value is a fixed
    # lower date boundary, never a rolling "last N days" window.
    authorized_from: str = ""
    active: bool = True
    operations: frozenset[str] = frozenset({"read"})

    def __post_init__(self) -> None:
        if (
            not self.scope_id
            or not self.authorization_revision
            or not self.policy_revision
        ):
            raise ValueError("Gmail scope and revision identities are required")
        if not self.account_ref.startswith("sha256:"):
            raise ValueError("Gmail account_ref must be opaque")
        if not self.query_fingerprint.startswith("sha256:"):
            raise ValueError("Gmail query_fingerprint must be opaque")
        if self.operations != frozenset({"read"}):
            raise ValueError("Gmail v0.1 authorization must be read-only")
        if self.authorized_from:
            try:
                date.fromisoformat(self.authorized_from)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "Gmail authorized_from must be a fixed YYYY-MM-DD date"
                ) from error
        object.__setattr__(
            self,
            "included_categories",
            frozenset(item.casefold() for item in self.included_categories),
        )
        object.__setattr__(
            self,
            "excluded_categories",
            frozenset(item.casefold() for item in self.excluded_categories),
        )

    def assert_not_narrower_than(self, earlier: "GmailReadManifest") -> None:
        """Reject a successor that would drop already-authorized history.

        The caller supplies the predecessor because this adapter deliberately
        owns no private state.  Empty means all history, so it can never be
        replaced by a date; a date may only stay fixed or move earlier.
        """

        if self.account_ref != earlier.account_ref:
            raise ValueError("Gmail authorization successor account mismatch")
        if not earlier.authorized_from:
            if self.authorized_from:
                raise ValueError("Gmail authorized_from cannot narrow full history")
            return
        if not self.authorized_from:
            return
        if date.fromisoformat(self.authorized_from) > date.fromisoformat(
            earlier.authorized_from
        ):
            raise ValueError("Gmail authorized_from cannot move later")


@dataclass(frozen=True)
class GmailAttachmentMetadata:
    attachment_id: str
    filename: str
    media_type: str
    size: int

    def __post_init__(self) -> None:
        if not self.attachment_id or not self.media_type or self.size < 0:
            raise ValueError("valid Gmail attachment metadata is required")


@dataclass(frozen=True)
class GmailMessageMetadata:
    message_id: str
    thread_id: str
    category: str
    label_ids: tuple[str, ...]
    internal_date: str
    attachments: tuple[GmailAttachmentMetadata, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)
    identity_only: bool = False

    def __post_init__(self) -> None:
        if not self.message_id:
            raise ValueError("Gmail message identity is required")
        if not self.identity_only and (
            not self.thread_id or not self.internal_date
        ):
            raise ValueError(
                "Gmail thread identity and date are required for full metadata"
            )
        if self.identity_only and self.attachments:
            raise ValueError(
                "identity-only Gmail messages cannot carry attachment metadata"
            )
        object.__setattr__(
            self,
            "category",
            "unknown" if self.identity_only else self.category.casefold(),
        )
        object.__setattr__(
            self,
            "label_ids",
            tuple(str(item).casefold() for item in self.label_ids),
        )
        object.__setattr__(self, "attachments", tuple(self.attachments))
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True)
class GmailMessageContent:
    message_id: str
    body_text: str
    headers: Mapping[str, str] = field(default_factory=dict)
    attachment_content: Mapping[str, bytes] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.message_id:
            raise ValueError("Gmail message content requires a message id")
        object.__setattr__(
            self,
            "headers",
            {str(key): str(value) for key, value in self.headers.items()},
        )
        object.__setattr__(
            self,
            "attachment_content",
            {
                str(key): bytes(value)
                for key, value in self.attachment_content.items()
            },
        )


@dataclass(frozen=True)
class GmailAuthorizedPage:
    scope_id: str
    account_ref: str
    authorization_revision: str
    query_fingerprint: str
    policy_revision: str
    requested_cursor: str
    next_cursor: str
    terminal: bool
    messages: tuple[GmailMessageMetadata, ...]
    contents: tuple[GmailMessageContent, ...] = ()
    coverage: str = "complete"
    denied_object_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.coverage not in GMAIL_COVERAGE:
            raise ValueError("invalid Gmail page coverage")
        if self.terminal and self.next_cursor:
            raise ValueError("terminal Gmail page cannot have a next cursor")
        message_ids = tuple(item.message_id for item in self.messages)
        content_ids = tuple(item.message_id for item in self.contents)
        if len(message_ids) != len(set(message_ids)):
            raise ValueError("Gmail page message ids must be unique")
        if len(content_ids) != len(set(content_ids)):
            raise ValueError("Gmail page content ids must be unique")
        if not set(content_ids).issubset(message_ids):
            raise ValueError("Gmail content must belong to a page message")
        identity_only_ids = {
            item.message_id for item in self.messages if item.identity_only
        }
        if identity_only_ids.intersection(content_ids):
            raise ValueError(
                "identity-only Gmail messages cannot carry message content"
            )
        object.__setattr__(self, "messages", tuple(self.messages))
        object.__setattr__(self, "contents", tuple(self.contents))
        object.__setattr__(
            self,
            "denied_object_ids",
            tuple(str(item) for item in self.denied_object_ids),
        )


@dataclass(frozen=True)
class GmailDiscoveryItem:
    envelope: ProviderEnvelope
    recommended_disposition: str
    reason: str


@dataclass(frozen=True)
class GmailDiscoveryPage:
    items: tuple[GmailDiscoveryItem, ...]
    page_fingerprint: str
    next_cursor: str
    terminal: bool
    coverage: str
    gaps: tuple[str, ...] = ()


@dataclass(frozen=True)
class GmailReadResult:
    external_id: str
    disposition: str
    envelope: ProviderEnvelope | None = None
    reason: str = ""

    @property
    def ingested(self) -> bool:
        return self.disposition == "ingested" and self.envelope is not None


class GmailPageRejected(ValueError):
    """An injected page does not match the frozen read manifest/cursor."""


class GmailSourceUnavailable(RuntimeError):
    """No already-authorized Gmail page source was configured."""


GmailPageSource = Callable[[str], GmailAuthorizedPage]


class GmailReadOnlyAdapter:
    """Validate and project already-authorized Gmail pages deterministically."""

    provider_id = "gmail"

    def __init__(
        self,
        manifest: GmailReadManifest,
        *,
        page_source: GmailPageSource | None = None,
        max_messages_per_page: int = 500,
        max_attachment_bytes: int = 32 * 1024 * 1024,
    ):
        if max_messages_per_page < 1 or max_attachment_bytes < 1:
            raise ValueError("Gmail resource budgets must be positive")
        self._manifest = manifest
        self._page_source = page_source
        self._max_messages_per_page = max_messages_per_page
        self._max_attachment_bytes = max_attachment_bytes

    @property
    def manifest(self) -> GmailReadManifest:
        """Expose the frozen, credential-free read boundary."""

        return self._manifest

    def authorized_page(self, *, cursor: str = "") -> GmailAuthorizedPage:
        """Fetch and validate one already-authorized page without projecting it."""

        if self._page_source is None:
            raise GmailSourceUnavailable(
                "already_authorized_gmail_page_source_unconfigured"
            )
        page = self._page_source(cursor)
        self._validate_page(page, cursor=cursor)
        return page

    def _opaque_id(self, object_type: str, provider_id: str) -> str:
        if object_type == "message":
            return gmail_message_object_id(
                self._manifest.account_ref,
                provider_id,
            )
        value = (
            f"{self._manifest.account_ref}\0{object_type}\0{provider_id}"
        )
        return f"gmail:{object_type}:{sha256(value.encode('utf-8')).hexdigest()[:24]}"

    def _validate_page(
        self,
        page: GmailAuthorizedPage,
        *,
        cursor: str,
    ) -> None:
        if not self._manifest.active:
            raise GmailPageRejected("gmail_authorization_revoked")
        expected = (
            self._manifest.scope_id,
            self._manifest.account_ref,
            self._manifest.authorization_revision,
            self._manifest.query_fingerprint,
            self._manifest.policy_revision,
        )
        observed = (
            page.scope_id,
            page.account_ref,
            page.authorization_revision,
            page.query_fingerprint,
            page.policy_revision,
        )
        if expected != observed:
            raise GmailPageRejected("gmail_page_outside_frozen_manifest")
        if page.requested_cursor != cursor:
            raise GmailPageRejected("gmail_page_cursor_mismatch")
        if len(page.messages) > self._max_messages_per_page:
            raise GmailPageRejected("gmail_page_message_budget_exceeded")

    def _message_disposition(
        self,
        message: GmailMessageMetadata,
    ) -> tuple[str, str]:
        if message.identity_only:
            return "metadata_only", "pending_metadata"
        if self._manifest.authorized_from:
            try:
                message_date = date.fromisoformat(message.internal_date[:10])
            except ValueError:
                return (
                    "not_tracked",
                    "gmail_internal_date_invalid_for_authorized_from",
                )
            if message_date < date.fromisoformat(self._manifest.authorized_from):
                return "not_tracked", "gmail_before_authorized_from"
        labels = set(message.label_ids)
        labels.add(message.category)
        if labels.intersection(self._manifest.excluded_categories):
            return "hard_excluded", "gmail_spam_or_trash_policy"
        if message.category == "promotions":
            return "not_tracked", "gmail_promotions_excluded_by_signal_policy"
        if not labels.intersection(self._manifest.included_categories):
            return "metadata_only", "mailbox_category_outside_current_inclusion"
        return "tracked", "authorized_included_mailbox_category"

    def _metadata_envelopes(
        self,
        page: GmailAuthorizedPage,
    ) -> tuple[GmailDiscoveryItem, ...]:
        items: list[GmailDiscoveryItem] = []
        thread_messages: dict[str, list[GmailMessageMetadata]] = {}
        for message in page.messages:
            if not message.identity_only:
                thread_messages.setdefault(message.thread_id, []).append(
                    message
                )
        for thread_id in sorted(thread_messages):
            external_id = self._opaque_id("thread", thread_id)
            items.append(
                GmailDiscoveryItem(
                    ProviderEnvelope(
                        provider=self.provider_id,
                        external_id=external_id,
                        object_type="gmail_thread",
                        payload={
                            "message_count": len(thread_messages[thread_id]),
                        },
                        coverage=page.coverage,
                        cursor=page.next_cursor,
                        references=(
                            ExternalReference(
                                self.provider_id,
                                external_id,
                                "gmail_thread",
                            ),
                        ),
                        metadata={
                            "scope_id": self._manifest.scope_id,
                            "authorization_revision": (
                                self._manifest.authorization_revision
                            ),
                            "query_fingerprint": (
                                self._manifest.query_fingerprint
                            ),
                            "metadata_only": True,
                            "authorized_from": self._manifest.authorized_from,
                        },
                    ),
                    "metadata_only",
                    "thread_metadata_inventory_only",
                )
            )

        for message in sorted(page.messages, key=lambda item: item.message_id):
            disposition, reason = self._message_disposition(message)
            message_external_id = self._opaque_id(
                "message",
                message.message_id,
            )
            thread_external_id = (
                self._opaque_id("thread", message.thread_id)
                if not message.identity_only
                else ""
            )
            message_payload: dict[str, object] = {
                "provider_message_id": message.message_id,
                "identity_only": message.identity_only,
                "authorized_from": self._manifest.authorized_from,
            }
            if not message.identity_only:
                message_payload.update(
                    {
                        "provider_thread_id": message.thread_id,
                        "category": message.category,
                        "label_ids": message.label_ids,
                        "internal_date": message.internal_date,
                        **dict(message.metadata),
                    }
                )
            references = [
                ExternalReference(
                    self.provider_id,
                    message_external_id,
                    "gmail_message",
                ),
            ]
            if thread_external_id:
                references.append(
                    ExternalReference(
                        self.provider_id,
                        thread_external_id,
                        "gmail_thread",
                    )
                )
            message_metadata: dict[str, object] = {
                "scope_id": self._manifest.scope_id,
                "authorization_revision": self._manifest.authorization_revision,
                "query_fingerprint": self._manifest.query_fingerprint,
                "metadata_only": True,
                "identity_only": message.identity_only,
            }
            if thread_external_id:
                message_metadata["parent_external_id"] = thread_external_id
            items.append(
                GmailDiscoveryItem(
                    ProviderEnvelope(
                        provider=self.provider_id,
                        external_id=message_external_id,
                        object_type="gmail_message",
                        payload=message_payload,
                        coverage=page.coverage,
                        cursor=page.next_cursor,
                        denied_fields=(
                            ("content",)
                            if message.message_id in page.denied_object_ids
                            else ()
                        ),
                        references=tuple(references),
                        metadata=message_metadata,
                    ),
                    disposition,
                    reason,
                )
            )
            if not self._manifest.attachment_metadata_allowed:
                continue
            for attachment in sorted(
                message.attachments,
                key=lambda item: item.attachment_id,
            ):
                attachment_external_id = self._opaque_id(
                    "attachment",
                    f"{message.message_id}\0{attachment.attachment_id}",
                )
                items.append(
                    GmailDiscoveryItem(
                        ProviderEnvelope(
                            provider=self.provider_id,
                            external_id=attachment_external_id,
                            object_type="gmail_attachment",
                            payload={
                                "provider_attachment_id": (
                                    attachment.attachment_id
                                ),
                                "filename": attachment.filename,
                                "media_type": attachment.media_type,
                                "size": attachment.size,
                            },
                            coverage=page.coverage,
                            cursor=page.next_cursor,
                            references=(
                                ExternalReference(
                                    self.provider_id,
                                    attachment_external_id,
                                    "gmail_attachment",
                                ),
                                ExternalReference(
                                    self.provider_id,
                                    message_external_id,
                                    "gmail_message",
                                ),
                                ExternalReference(
                                    self.provider_id,
                                    thread_external_id,
                                    "gmail_thread",
                                ),
                            ),
                            metadata={
                                "parent_external_id": message_external_id,
                                "thread_external_id": thread_external_id,
                                "scope_id": self._manifest.scope_id,
                                "authorized_from": self._manifest.authorized_from,
                                "metadata_only": True,
                            },
                        ),
                        (
                            "hard_excluded"
                            if disposition == "hard_excluded"
                            else (
                                "tracked"
                                if disposition == "tracked"
                                else "not_tracked"
                            )
                        ),
                        (
                            reason
                            if disposition == "hard_excluded"
                            else (
                                "authorized_attachment_metadata"
                                if disposition == "tracked"
                                else reason
                            )
                        ),
                    )
                )
        return tuple(items)

    def accept_page(
        self,
        page: GmailAuthorizedPage,
        *,
        cursor: str = "",
    ) -> GmailDiscoveryPage:
        """Validate an external page and return metadata-only inventory items."""

        self._validate_page(page, cursor=cursor)
        items = self._metadata_envelopes(page)
        page_fingerprint = _digest(
            {
                "manifest": {
                    "scope": page.scope_id,
                    "account": page.account_ref,
                    "authorization": page.authorization_revision,
                    "query": page.query_fingerprint,
                    "policy": page.policy_revision,
                    "authorized_from": self._manifest.authorized_from,
                },
                "cursor": page.requested_cursor,
                "next_cursor": page.next_cursor,
                "messages": [
                    {
                        "message_id": item.message_id,
                        "thread_id": item.thread_id,
                        "category": item.category,
                        "labels": item.label_ids,
                        "date": item.internal_date,
                        "identity_only": item.identity_only,
                        "attachments": [
                            (
                                attachment.attachment_id,
                                attachment.media_type,
                                attachment.size,
                            )
                            for attachment in item.attachments
                        ],
                    }
                    for item in page.messages
                ],
                "denied": page.denied_object_ids,
            }
        )
        coverage = page.coverage
        gaps: list[str] = []
        if page.denied_object_ids:
            coverage = "partial"
            gaps.append("gmail_objects_denied")
        if not page.terminal:
            coverage = "partial"
        return GmailDiscoveryPage(
            items=items,
            page_fingerprint=page_fingerprint,
            next_cursor=page.next_cursor,
            terminal=page.terminal,
            coverage=coverage,
            gaps=tuple(gaps),
        )

    def discover(self, *, cursor: str = "") -> GmailDiscoveryPage:
        page = self.authorized_page(cursor=cursor)
        return self.accept_page(page, cursor=cursor)

    def read_page(
        self,
        page: GmailAuthorizedPage,
        *,
        tracking_dispositions: Mapping[str, str],
        cursor: str = "",
    ) -> tuple[GmailReadResult, ...]:
        """Project tracked message/attachment content; never mutate mail."""

        self._validate_page(page, cursor=cursor)
        contents = {item.message_id: item for item in page.contents}
        results: list[GmailReadResult] = []
        for message in sorted(page.messages, key=lambda item: item.message_id):
            disposition, reason = self._message_disposition(message)
            message_external_id = self._opaque_id(
                "message",
                message.message_id,
            )
            if message.identity_only:
                results.append(
                    GmailReadResult(
                        message_external_id,
                        "metadata_only",
                        reason="pending_metadata",
                    )
                )
                continue
            thread_external_id = self._opaque_id("thread", message.thread_id)
            if disposition == "hard_excluded":
                results.append(
                    GmailReadResult(
                        message_external_id,
                        "hard_excluded",
                        reason="gmail_spam_or_trash_content_not_read",
                    )
                )
                continue
            if disposition == "not_tracked":
                results.append(
                    GmailReadResult(
                        message_external_id,
                        "not_tracked",
                        reason=reason,
                    )
                )
                continue
            if tracking_dispositions.get(message_external_id) != "tracked":
                results.append(
                    GmailReadResult(
                        message_external_id,
                        "deferred",
                        reason="current_tracked_disposition_required",
                    )
                )
                continue
            content = contents.get(message.message_id)
            if content is None:
                results.append(
                    GmailReadResult(
                        message_external_id,
                        (
                            "inaccessible"
                            if message.message_id in page.denied_object_ids
                            else "metadata_only"
                        ),
                        reason=(
                            "message_content_denied"
                            if message.message_id in page.denied_object_ids
                            else "message_content_not_supplied"
                        ),
                    )
                )
                continue
            message_envelope = ProviderEnvelope(
                provider=self.provider_id,
                external_id=message_external_id,
                object_type="gmail_message",
                payload={
                    "provider_message_id": message.message_id,
                    "provider_thread_id": message.thread_id,
                    "headers": dict(content.headers),
                    "body_text": content.body_text,
                    "category": message.category,
                    "label_ids": message.label_ids,
                    "internal_date": message.internal_date,
                },
                coverage=page.coverage,
                cursor=page.next_cursor,
                references=(
                    ExternalReference(
                        self.provider_id,
                        message_external_id,
                        "gmail_message",
                    ),
                    ExternalReference(
                        self.provider_id,
                        thread_external_id,
                        "gmail_thread",
                    ),
                ),
                metadata={
                    "parent_external_id": thread_external_id,
                    "scope_id": self._manifest.scope_id,
                    "authorization_revision": (
                        self._manifest.authorization_revision
                    ),
                    "query_fingerprint": self._manifest.query_fingerprint,
                    "tracking_disposition": "tracked",
                    "disposition": "ingested",
                    "private_payload": True,
                },
            )
            results.append(
                GmailReadResult(
                    message_external_id,
                    "ingested",
                    envelope=message_envelope,
                )
            )
            if not self._manifest.attachment_content_allowed:
                continue
            attachment_by_id = {
                item.attachment_id: item for item in message.attachments
            }
            for attachment_id in sorted(content.attachment_content):
                metadata = attachment_by_id.get(attachment_id)
                if metadata is None:
                    raise GmailPageRejected(
                        "gmail_attachment_content_without_metadata"
                    )
                attachment_external_id = self._opaque_id(
                    "attachment",
                    f"{message.message_id}\0{attachment_id}",
                )
                if (
                    tracking_dispositions.get(attachment_external_id)
                    != "tracked"
                ):
                    results.append(
                        GmailReadResult(
                            attachment_external_id,
                            "deferred",
                            reason="current_tracked_disposition_required",
                        )
                    )
                    continue
                attachment_bytes = content.attachment_content[attachment_id]
                if len(attachment_bytes) > self._max_attachment_bytes:
                    results.append(
                        GmailReadResult(
                            attachment_external_id,
                            "metadata_only",
                            reason="attachment_content_budget_exceeded",
                        )
                    )
                    continue
                attachment_envelope = ProviderEnvelope(
                    provider=self.provider_id,
                    external_id=attachment_external_id,
                    object_type="gmail_attachment",
                    payload={
                        "provider_attachment_id": attachment_id,
                        "filename": metadata.filename,
                        "media_type": metadata.media_type,
                        "content": attachment_bytes,
                    },
                    coverage=page.coverage,
                    cursor=page.next_cursor,
                    references=(
                        ExternalReference(
                            self.provider_id,
                            attachment_external_id,
                            "gmail_attachment",
                        ),
                        ExternalReference(
                            self.provider_id,
                            message_external_id,
                            "gmail_message",
                        ),
                        ExternalReference(
                            self.provider_id,
                            thread_external_id,
                            "gmail_thread",
                        ),
                    ),
                    metadata={
                        "parent_external_id": message_external_id,
                        "thread_external_id": thread_external_id,
                        "scope_id": self._manifest.scope_id,
                        "tracking_disposition": "tracked",
                        "disposition": "ingested",
                        "private_payload": True,
                    },
                )
                results.append(
                    GmailReadResult(
                        attachment_external_id,
                        "ingested",
                        envelope=attachment_envelope,
                    )
                )
        return tuple(results)

    def read(
        self,
        *,
        object_ids: Sequence[str],
        cursor: str = "",
        tracking_dispositions: Mapping[str, str] | None = None,
    ) -> tuple[ProviderEnvelope, ...]:
        if self._page_source is None:
            raise GmailSourceUnavailable(
                "already_authorized_gmail_page_source_unconfigured"
            )
        if tracking_dispositions is None:
            raise PermissionError("current_tracked_disposition_required")
        page = self._page_source(cursor)
        requested = set(str(item) for item in object_ids)
        results = tuple(
            item
            for item in self.read_page(
                page,
                tracking_dispositions=tracking_dispositions,
                cursor=cursor,
            )
            if item.external_id in requested
        )
        observed = {item.external_id for item in results}
        missing = requested - observed
        if missing:
            raise GmailPageRejected("requested_gmail_object_not_in_page")
        blocked = tuple(item for item in results if not item.ingested)
        if blocked:
            raise PermissionError(
                "gmail_read_not_ingested:"
                + ",".join(
                    f"{item.external_id}:{item.disposition}"
                    for item in blocked
                )
            )
        return tuple(
            item.envelope for item in results if item.envelope is not None
        )

    @staticmethod
    def write(*_args: object, **_kwargs: object) -> None:
        raise ProviderWriteForbidden("Gmail mailbox writes are forbidden")


__all__ = [
    "GMAIL_COVERAGE",
    "GmailAttachmentMetadata",
    "GmailAuthorizedPage",
    "GmailDiscoveryItem",
    "GmailDiscoveryPage",
    "GmailMessageContent",
    "GmailMessageMetadata",
    "GmailPageRejected",
    "GmailPageSource",
    "GmailReadManifest",
    "GmailReadOnlyAdapter",
    "GmailReadResult",
    "GmailSourceUnavailable",
    "gmail_account_ref",
    "gmail_message_object_id",
    "gmail_scope_id",
]
