"""Immutable authorization scopes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("authorization timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _normalize_as_of(value: datetime | None) -> datetime:
    current = value or _utc_now()
    if current.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    return current.astimezone(timezone.utc)


def opaque_reference(value: str) -> str:
    """Return a stable non-reversible reference suitable for public receipts."""

    return "sha256:" + sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuthorizationScope:
    scope_id: str
    provider: str
    object_ids: frozenset[str]
    operations: frozenset[str] = frozenset({"read"})
    active: bool = True
    query_snapshot: str = ""
    instance_ref_hash: str = ""
    project_ref_hashes: frozenset[str] = frozenset()
    object_types: frozenset[str] = frozenset()
    time_start: str = ""
    time_end: str = ""
    attachment_metadata_allowed: bool = False
    attachment_content_allowed: bool = False
    permission_fingerprint: str = ""
    expires_at: str = ""

    def __post_init__(self) -> None:
        if not self.scope_id or not self.provider:
            raise ValueError("scope_id and provider are required")
        object.__setattr__(self, "object_ids", frozenset(self.object_ids))
        object.__setattr__(self, "operations", frozenset(self.operations))
        object.__setattr__(
            self,
            "project_ref_hashes",
            frozenset(self.project_ref_hashes),
        )
        object.__setattr__(self, "object_types", frozenset(self.object_types))
        if self.attachment_content_allowed and not self.attachment_metadata_allowed:
            raise ValueError(
                "attachment content authorization requires attachment metadata authorization"
            )
        if self.time_start and self.time_end:
            if _parse_timestamp(self.time_start) > _parse_timestamp(self.time_end):
                raise ValueError("authorization time_start must not follow time_end")
        if self.expires_at:
            _parse_timestamp(self.expires_at)

    def current(self, as_of: datetime | None = None) -> bool:
        if not self.active:
            return False
        if not self.expires_at:
            return True
        current_time = _normalize_as_of(as_of)
        return current_time < _parse_timestamp(self.expires_at)

    def covers(
        self,
        provider: str,
        object_id: str,
        operation: str,
        *,
        object_type: str = "",
        instance_ref_hash: str = "",
        as_of: datetime | None = None,
    ) -> bool:
        return (
            self.current(as_of)
            and provider == self.provider
            and object_id in self.object_ids
            and operation in self.operations
            and (
                not object_type
                or not self.object_types
                or object_type in self.object_types
            )
            and (
                not instance_ref_hash
                or instance_ref_hash == self.instance_ref_hash
            )
        )

    def explicit_read_boundary_gaps(self) -> tuple[str, ...]:
        """Return missing fields that make a live provider read ineligible."""

        gaps: list[str] = []
        if self.operations != frozenset({"read"}):
            gaps.append("read_only_operation_required")
        if not self.object_ids:
            gaps.append("object_scope_missing")
        if not self.instance_ref_hash.startswith("sha256:"):
            gaps.append("instance_ref_hash_missing")
        if not self.project_ref_hashes:
            gaps.append("project_scope_missing")
        if not self.object_types:
            gaps.append("object_type_scope_missing")
        if not self.time_start or not self.time_end:
            gaps.append("time_boundary_missing")
        if not self.permission_fingerprint.startswith("sha256:"):
            gaps.append("permission_fingerprint_missing")
        if not self.expires_at:
            gaps.append("authorization_expiry_missing")
        return tuple(gaps)


__all__ = ["AuthorizationScope", "opaque_reference"]
