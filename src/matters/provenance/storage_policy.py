"""Pure source-in-place storage policy values.

This module deliberately does not perform I/O.  It separates the private
locator required to revisit an external original from the path-free projection
that is safe to hand to presentation code.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from hashlib import sha256
import re
from typing import Any, Mapping

from matters.inventory.owners import InventoryOccurrence


_SHA256_PATTERN = re.compile(r"^(?:sha256:)?([0-9a-fA-F]{64})$")


class StorageClass(str, Enum):
    """The five singular storage owners used by source-in-place."""

    EXTERNAL_ORIGINAL = "external_original"
    DURABLE_DERIVED = "durable_derived"
    REBUILDABLE_CACHE = "rebuildable_cache"
    TRANSIENT_STAGING = "transient_staging"
    RECOVERY_BACKUP = "recovery_backup"


class SourceAvailability(str, Enum):
    """Current ability to revisit an external source."""

    AVAILABLE = "available"
    SOURCE_UNAVAILABLE = "source_unavailable"
    REVOKED = "revoked"
    DELETED = "deleted"


class CleanupAction(str, Enum):
    """An explicit, reviewable cleanup outcome."""

    RETAIN = "retain"
    DELETE = "delete"
    DEFER = "defer"


class SourceUnavailableError(RuntimeError):
    """Raised when a caller requires an external original that is unavailable."""


def _required_text(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _required_provider(value: str) -> str:
    provider = _required_text(value, "provider")
    if "/" in provider or "\\" in provider:
        raise ValueError("provider must be a canonical identifier, not a path")
    return provider


def _normalize_fingerprint(value: str, *, required: bool) -> str:
    normalized = str(value).strip()
    if not normalized:
        if required:
            raise ValueError("a sha256 fingerprint is required")
        return ""
    match = _SHA256_PATTERN.fullmatch(normalized)
    if match is None:
        raise ValueError("fingerprint must be sha256:<64 hex characters>")
    return f"sha256:{match.group(1).lower()}"


def _aware_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _opaque_reference_id(
    *,
    provider: str,
    scope_id: str,
    occurrence_id: str,
) -> str:
    payload = "\0".join((provider, scope_id, occurrence_id)).encode("utf-8")
    return f"source-ref:{sha256(payload).hexdigest()[:32]}"


@dataclass(frozen=True)
class ExternalOriginalReference:
    """Private pointer plus fingerprints for an original owned by a provider.

    ``private_root_locator`` and ``private_locator`` may contain an absolute
    filesystem path or a provider-specific opaque locator.  Both are excluded
    from ``repr`` and from :meth:`to_public_mapping`.
    """

    provider: str
    scope_id: str
    occurrence_id: str
    private_root_locator: str = field(repr=False)
    private_locator: str = field(repr=False)
    metadata_fingerprint: str
    content_fingerprint: str = ""
    availability: SourceAvailability = SourceAvailability.AVAILABLE
    unavailable_reason: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        provider = _required_provider(self.provider)
        scope_id = _required_text(self.scope_id, "scope_id")
        occurrence_id = _required_text(self.occurrence_id, "occurrence_id")
        private_root = _required_text(
            self.private_root_locator,
            "private_root_locator",
        )
        private_locator = _required_text(self.private_locator, "private_locator")
        availability = SourceAvailability(self.availability)
        unavailable_reason = str(self.unavailable_reason).strip()
        if availability is SourceAvailability.AVAILABLE and unavailable_reason:
            raise ValueError(
                "an available source cannot have an unavailable_reason"
            )
        if (
            availability is not SourceAvailability.AVAILABLE
            and not unavailable_reason
        ):
            raise ValueError(
                "an unavailable source requires an unavailable_reason"
            )
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "scope_id", scope_id)
        object.__setattr__(self, "occurrence_id", occurrence_id)
        object.__setattr__(self, "private_root_locator", private_root)
        object.__setattr__(self, "private_locator", private_locator)
        object.__setattr__(
            self,
            "metadata_fingerprint",
            _normalize_fingerprint(self.metadata_fingerprint, required=True),
        )
        object.__setattr__(
            self,
            "content_fingerprint",
            _normalize_fingerprint(self.content_fingerprint, required=False),
        )
        object.__setattr__(self, "availability", availability)
        object.__setattr__(self, "unavailable_reason", unavailable_reason)

    @classmethod
    def from_occurrence(
        cls,
        *,
        scope_id: str,
        private_root_locator: str,
        occurrence: InventoryOccurrence,
        availability: SourceAvailability = SourceAvailability.AVAILABLE,
        unavailable_reason: str = "",
    ) -> ExternalOriginalReference:
        """Create a reference without copying source bytes."""

        return cls(
            provider=occurrence.provider,
            scope_id=scope_id,
            occurrence_id=occurrence.occurrence_id,
            private_root_locator=private_root_locator,
            private_locator=occurrence.locator,
            metadata_fingerprint=occurrence.metadata_identity,
            content_fingerprint=occurrence.content_identity,
            availability=availability,
            unavailable_reason=unavailable_reason,
        )

    @property
    def storage_class(self) -> StorageClass:
        return StorageClass.EXTERNAL_ORIGINAL

    @property
    def reference_id(self) -> str:
        """Stable identity that does not encode either private locator."""

        return _opaque_reference_id(
            provider=self.provider,
            scope_id=self.scope_id,
            occurrence_id=self.occurrence_id,
        )

    @property
    def readable(self) -> bool:
        return self.availability is SourceAvailability.AVAILABLE

    def require_readable(self) -> ExternalOriginalReference:
        if not self.readable:
            raise SourceUnavailableError(
                f"external original {self.reference_id} is "
                f"{self.availability.value}"
            )
        return self

    def mark_unavailable(
        self,
        *,
        reason: str,
        availability: SourceAvailability = SourceAvailability.SOURCE_UNAVAILABLE,
    ) -> ExternalOriginalReference:
        if availability is SourceAvailability.AVAILABLE:
            raise ValueError("mark_unavailable requires an unavailable status")
        return replace(
            self,
            availability=availability,
            unavailable_reason=_required_text(reason, "reason"),
        )

    def to_public_mapping(self) -> Mapping[str, Any]:
        """Return a path-free projection safe for user-facing output."""

        return {
            "reference_id": self.reference_id,
            "provider": self.provider,
            "storage_class": self.storage_class.value,
            "availability": self.availability.value,
            "content_fingerprint_present": bool(self.content_fingerprint),
            "metadata_fingerprint_present": True,
        }


@dataclass(frozen=True)
class StoredArtifact:
    """A local artifact considered by retention policy."""

    artifact_id: str
    storage_class: StorageClass
    byte_count: int
    created_at: datetime
    last_accessed_at: datetime | None = None
    terminal_committed: bool = False
    reference_count: int = 0
    pinned: bool = False
    offline_recovery_owner_id: str = ""

    def __post_init__(self) -> None:
        artifact_id = _required_text(self.artifact_id, "artifact_id")
        storage_class = StorageClass(self.storage_class)
        if self.byte_count < 0:
            raise ValueError("byte_count cannot be negative")
        if self.reference_count < 0:
            raise ValueError("reference_count cannot be negative")
        if (
            storage_class is StorageClass.EXTERNAL_ORIGINAL
            and self.byte_count != 0
        ):
            raise ValueError("external originals cannot own local bytes")
        offline_recovery_owner_id = str(
            self.offline_recovery_owner_id
        ).strip()
        if (
            storage_class is StorageClass.RECOVERY_BACKUP
            and not offline_recovery_owner_id
        ):
            raise ValueError(
                "recovery backups require an explicit offline recovery owner"
            )
        if (
            storage_class is not StorageClass.RECOVERY_BACKUP
            and offline_recovery_owner_id
        ):
            raise ValueError(
                "only recovery backups may declare an offline recovery owner"
            )
        created_at = _aware_utc(self.created_at, "created_at")
        last_accessed_at = (
            _aware_utc(self.last_accessed_at, "last_accessed_at")
            if self.last_accessed_at is not None
            else None
        )
        if last_accessed_at is not None and last_accessed_at < created_at:
            raise ValueError("last_accessed_at cannot precede created_at")
        object.__setattr__(self, "artifact_id", artifact_id)
        object.__setattr__(self, "storage_class", storage_class)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "last_accessed_at", last_accessed_at)
        object.__setattr__(
            self,
            "offline_recovery_owner_id",
            offline_recovery_owner_id,
        )

    @property
    def retention_age_anchor(self) -> datetime:
        return self.last_accessed_at or self.created_at


@dataclass(frozen=True)
class RetentionLimits:
    """TTL and quota limits for reclaimable local storage classes."""

    transient_ttl: timedelta = timedelta(hours=24)
    transient_quota_bytes: int = 512 * 1024 * 1024
    cache_ttl: timedelta = timedelta(days=30)
    cache_quota_bytes: int = 2 * 1024 * 1024 * 1024
    cleanup_transient_after_terminal_commit: bool = True

    def __post_init__(self) -> None:
        if self.transient_ttl <= timedelta(0):
            raise ValueError("transient_ttl must be positive")
        if self.cache_ttl <= timedelta(0):
            raise ValueError("cache_ttl must be positive")
        if self.transient_quota_bytes < 0:
            raise ValueError("transient_quota_bytes cannot be negative")
        if self.cache_quota_bytes < 0:
            raise ValueError("cache_quota_bytes cannot be negative")


@dataclass(frozen=True)
class CleanupDecision:
    """Why a local artifact should be retained, deleted, or deferred."""

    action: CleanupAction
    reason: str
    evaluated_at: datetime
    reclaimable_bytes: int = 0
    eligible_at: datetime | None = None

    def __post_init__(self) -> None:
        action = CleanupAction(self.action)
        reason = _required_text(self.reason, "reason")
        evaluated_at = _aware_utc(self.evaluated_at, "evaluated_at")
        eligible_at = (
            _aware_utc(self.eligible_at, "eligible_at")
            if self.eligible_at is not None
            else None
        )
        if self.reclaimable_bytes < 0:
            raise ValueError("reclaimable_bytes cannot be negative")
        if action is not CleanupAction.DELETE and self.reclaimable_bytes:
            raise ValueError(
                "only delete decisions may declare reclaimable bytes"
            )
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "evaluated_at", evaluated_at)
        object.__setattr__(self, "eligible_at", eligible_at)


def decide_cleanup(
    artifact: StoredArtifact,
    *,
    limits: RetentionLimits,
    evaluated_at: datetime,
    class_usage_bytes: int,
) -> CleanupDecision:
    """Evaluate one artifact against its class-specific lifecycle policy."""

    now = _aware_utc(evaluated_at, "evaluated_at")
    if class_usage_bytes < 0:
        raise ValueError("class_usage_bytes cannot be negative")
    storage_class = artifact.storage_class

    if storage_class in {
        StorageClass.EXTERNAL_ORIGINAL,
        StorageClass.DURABLE_DERIVED,
    }:
        return CleanupDecision(
            action=CleanupAction.RETAIN,
            reason="storage_class_not_reclaimable",
            evaluated_at=now,
        )
    if storage_class is StorageClass.RECOVERY_BACKUP:
        return CleanupDecision(
            action=CleanupAction.DEFER,
            reason="offline_recovery_owner",
            evaluated_at=now,
        )

    if artifact.pinned or artifact.reference_count:
        return CleanupDecision(
            action=CleanupAction.DEFER,
            reason=(
                "pinned"
                if artifact.pinned
                else "active_reference"
            ),
            evaluated_at=now,
        )

    if (
        storage_class is StorageClass.TRANSIENT_STAGING
        and artifact.terminal_committed
        and limits.cleanup_transient_after_terminal_commit
    ):
        return CleanupDecision(
            action=CleanupAction.DELETE,
            reason="terminal_commit",
            evaluated_at=now,
            reclaimable_bytes=artifact.byte_count,
        )

    if storage_class is StorageClass.TRANSIENT_STAGING:
        ttl = limits.transient_ttl
        quota = limits.transient_quota_bytes
    else:
        ttl = limits.cache_ttl
        quota = limits.cache_quota_bytes

    eligible_at = artifact.retention_age_anchor + ttl
    if now >= eligible_at:
        return CleanupDecision(
            action=CleanupAction.DELETE,
            reason="ttl_expired",
            evaluated_at=now,
            reclaimable_bytes=artifact.byte_count,
            eligible_at=eligible_at,
        )
    if class_usage_bytes > quota:
        return CleanupDecision(
            action=CleanupAction.DELETE,
            reason="quota_pressure",
            evaluated_at=now,
            reclaimable_bytes=artifact.byte_count,
            eligible_at=eligible_at,
        )
    return CleanupDecision(
        action=CleanupAction.RETAIN,
        reason="within_retention_limits",
        evaluated_at=now,
        eligible_at=eligible_at,
    )
