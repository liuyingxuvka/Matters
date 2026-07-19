"""Optional cloud-source boundary with explicit unconfigured capability."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256

from matters.providers.base import (
    ExternalReference,
    ProviderEnvelope,
    ProviderWriteForbidden,
)


@dataclass(frozen=True)
class CloudReadManifest:
    scope_id: str
    provider_id: str
    account_ref: str
    root_ref: str
    authorization_revision: str
    policy_revision: str
    configured: bool = False
    operations: frozenset[str] = frozenset({"read"})

    def __post_init__(self) -> None:
        if not self.scope_id or not self.provider_id:
            raise ValueError("cloud scope and provider identities are required")
        if self.operations != frozenset({"read"}):
            raise ValueError("cloud source authorization must be read-only")
        if self.configured and (
            not self.account_ref.startswith("sha256:")
            or not self.root_ref.startswith("sha256:")
            or not self.authorization_revision
            or not self.policy_revision
        ):
            raise ValueError(
                "configured cloud source requires opaque account/root "
                "and revision identities"
            )


@dataclass(frozen=True)
class CloudOccurrence:
    provider_object_id: str
    object_type: str
    metadata: Mapping[str, object] = field(default_factory=dict)
    hydrated: bool = False
    content: bytes | None = None
    parent_provider_object_id: str = ""

    def __post_init__(self) -> None:
        if not self.provider_object_id or not self.object_type:
            raise ValueError("cloud occurrence identity and type are required")
        object.__setattr__(self, "metadata", dict(self.metadata))
        if self.content is not None:
            object.__setattr__(self, "content", bytes(self.content))
        if not self.hydrated and self.content is not None:
            raise ValueError("cloud placeholder cannot contain content")


@dataclass(frozen=True)
class CloudAuthorizedPage:
    scope_id: str
    provider_id: str
    authorization_revision: str
    policy_revision: str
    requested_cursor: str
    next_cursor: str
    terminal: bool
    occurrences: tuple[CloudOccurrence, ...]
    coverage: str = "complete"

    def __post_init__(self) -> None:
        if self.coverage not in {"complete", "partial", "unknown"}:
            raise ValueError("invalid cloud page coverage")
        if self.terminal and self.next_cursor:
            raise ValueError("terminal cloud page cannot have a next cursor")
        object.__setattr__(self, "occurrences", tuple(self.occurrences))


@dataclass(frozen=True)
class CloudCapability:
    provider_id: str
    status: str
    reason: str
    read_only: bool = True
    content_coverage: str = "unknown"


@dataclass(frozen=True)
class CloudDiscoveryItem:
    envelope: ProviderEnvelope
    disposition: str
    reason: str


@dataclass(frozen=True)
class CloudDiscoveryPage:
    status: str
    items: tuple[CloudDiscoveryItem, ...]
    next_cursor: str
    terminal: bool
    coverage: str
    reason: str = ""


class CloudPageRejected(ValueError):
    """An injected cloud page does not match the configured read manifest."""


CloudPageSource = Callable[[str], CloudAuthorizedPage]


class CloudReadOnlyAdapter:
    """Project configured pages or report optional cloud support unconfigured."""

    def __init__(
        self,
        manifest: CloudReadManifest | None = None,
        *,
        page_source: CloudPageSource | None = None,
    ):
        self._manifest = manifest
        self._page_source = page_source
        self.provider_id = (
            manifest.provider_id if manifest is not None else "cloud"
        )

    def capability(self) -> CloudCapability:
        if self._manifest is None or not self._manifest.configured:
            return CloudCapability(
                self.provider_id,
                "unconfigured",
                "optional_cloud_source_unconfigured",
            )
        if self._page_source is None:
            return CloudCapability(
                self.provider_id,
                "unavailable",
                "already_authorized_cloud_page_source_unavailable",
            )
        return CloudCapability(
            self.provider_id,
            "configured",
            "already_authorized_page_source_configured",
            content_coverage="partial",
        )

    def _opaque_id(self, object_type: str, provider_object_id: str) -> str:
        manifest = self._manifest
        account_ref = manifest.account_ref if manifest is not None else ""
        raw = (
            f"{self.provider_id}\0{account_ref}\0"
            f"{object_type}\0{provider_object_id}"
        )
        return (
            f"cloud:{object_type}:"
            + sha256(raw.encode("utf-8")).hexdigest()[:24]
        )

    def _validate_page(
        self,
        page: CloudAuthorizedPage,
        *,
        cursor: str,
    ) -> None:
        if self._manifest is None or not self._manifest.configured:
            raise CloudPageRejected("optional_cloud_source_unconfigured")
        expected = (
            self._manifest.scope_id,
            self._manifest.provider_id,
            self._manifest.authorization_revision,
            self._manifest.policy_revision,
            cursor,
        )
        observed = (
            page.scope_id,
            page.provider_id,
            page.authorization_revision,
            page.policy_revision,
            page.requested_cursor,
        )
        if expected != observed:
            raise CloudPageRejected("cloud_page_outside_frozen_manifest")

    def accept_page(
        self,
        page: CloudAuthorizedPage,
        *,
        cursor: str = "",
    ) -> CloudDiscoveryPage:
        self._validate_page(page, cursor=cursor)
        items: list[CloudDiscoveryItem] = []
        for occurrence in sorted(
            page.occurrences,
            key=lambda item: item.provider_object_id,
        ):
            external_id = self._opaque_id(
                occurrence.object_type,
                occurrence.provider_object_id,
            )
            parent_external_id = (
                self._opaque_id(
                    "parent",
                    occurrence.parent_provider_object_id,
                )
                if occurrence.parent_provider_object_id
                else ""
            )
            references = [
                ExternalReference(
                    self.provider_id,
                    external_id,
                    occurrence.object_type,
                )
            ]
            if parent_external_id:
                references.append(
                    ExternalReference(
                        self.provider_id,
                        parent_external_id,
                        "parent",
                    )
                )
            disposition = (
                "tracked"
                if occurrence.hydrated and occurrence.content is not None
                else "metadata_only"
            )
            reason = (
                "authorized_hydrated_content"
                if disposition == "tracked"
                else "stable_content_unavailable"
            )
            items.append(
                CloudDiscoveryItem(
                    ProviderEnvelope(
                        provider=self.provider_id,
                        external_id=external_id,
                        object_type=occurrence.object_type,
                        payload={
                            "provider_object_id": (
                                occurrence.provider_object_id
                            ),
                            **dict(occurrence.metadata),
                        },
                        coverage=page.coverage,
                        cursor=page.next_cursor,
                        references=tuple(references),
                        metadata={
                            "scope_id": self._manifest.scope_id,
                            "authorization_revision": (
                                self._manifest.authorization_revision
                            ),
                            "policy_revision": (
                                self._manifest.policy_revision
                            ),
                            "parent_external_id": parent_external_id,
                            "hydrated": occurrence.hydrated,
                            "metadata_only": True,
                        },
                    ),
                    disposition,
                    reason,
                )
            )
        coverage = page.coverage
        if not page.terminal or any(
            item.disposition == "cloud_placeholder" for item in items
        ):
            coverage = "partial"
        return CloudDiscoveryPage(
            "configured",
            tuple(items),
            page.next_cursor,
            page.terminal,
            coverage,
        )

    def discover(self, *, cursor: str = "") -> CloudDiscoveryPage:
        capability = self.capability()
        if capability.status != "configured":
            return CloudDiscoveryPage(
                capability.status,
                (),
                "",
                False,
                "unknown",
                capability.reason,
            )
        assert self._page_source is not None
        return self.accept_page(self._page_source(cursor), cursor=cursor)

    def read(
        self,
        *,
        object_ids: Sequence[str],
        cursor: str = "",
        tracking_dispositions: Mapping[str, str] | None = None,
    ) -> tuple[ProviderEnvelope, ...]:
        capability = self.capability()
        if capability.status != "configured":
            raise RuntimeError(capability.reason)
        if tracking_dispositions is None:
            raise PermissionError("current_tracked_disposition_required")
        assert self._page_source is not None
        page = self._page_source(cursor)
        self._validate_page(page, cursor=cursor)
        requested = set(str(item) for item in object_ids)
        envelopes: list[ProviderEnvelope] = []
        observed: set[str] = set()
        for occurrence in page.occurrences:
            external_id = self._opaque_id(
                occurrence.object_type,
                occurrence.provider_object_id,
            )
            if external_id not in requested:
                continue
            observed.add(external_id)
            if tracking_dispositions.get(external_id) != "tracked":
                raise PermissionError("current_tracked_disposition_required")
            if not occurrence.hydrated or occurrence.content is None:
                raise PermissionError("cloud_placeholder_content_unavailable")
            parent_external_id = (
                self._opaque_id(
                    "parent",
                    occurrence.parent_provider_object_id,
                )
                if occurrence.parent_provider_object_id
                else ""
            )
            references = [
                ExternalReference(
                    self.provider_id,
                    external_id,
                    occurrence.object_type,
                )
            ]
            if parent_external_id:
                references.append(
                    ExternalReference(
                        self.provider_id,
                        parent_external_id,
                        "parent",
                    )
                )
            envelopes.append(
                ProviderEnvelope(
                    provider=self.provider_id,
                    external_id=external_id,
                    object_type=occurrence.object_type,
                    payload={
                        "provider_object_id": occurrence.provider_object_id,
                        "content": occurrence.content,
                        **dict(occurrence.metadata),
                    },
                    coverage=page.coverage,
                    cursor=page.next_cursor,
                    references=tuple(references),
                    metadata={
                        "scope_id": self._manifest.scope_id,
                        "parent_external_id": parent_external_id,
                        "tracking_disposition": "tracked",
                        "disposition": "ingested",
                        "private_payload": True,
                    },
                )
            )
        if requested - observed:
            raise CloudPageRejected("requested_cloud_object_not_in_page")
        return tuple(envelopes)

    @staticmethod
    def write(*_args: object, **_kwargs: object) -> None:
        raise ProviderWriteForbidden("Cloud source writes are forbidden")


__all__ = [
    "CloudAuthorizedPage",
    "CloudCapability",
    "CloudDiscoveryItem",
    "CloudDiscoveryPage",
    "CloudOccurrence",
    "CloudPageRejected",
    "CloudPageSource",
    "CloudReadManifest",
    "CloudReadOnlyAdapter",
]
