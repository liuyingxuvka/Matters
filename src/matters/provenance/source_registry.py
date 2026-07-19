"""C2: immutable source registration, versioning, and idempotency."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping, TYPE_CHECKING

from matters.providers.base import ExternalReference, ProviderEnvelope

if TYPE_CHECKING:
    from matters.infrastructure.sqlite.store import SQLiteStore


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


@dataclass(frozen=True)
class SourceVersion:
    source_id: str
    version: int
    provider: str
    external_reference: ExternalReference
    content: Mapping[str, Any]
    content_hash: str
    metadata_hash: str
    predecessor_version: int | None = None
    tombstone: bool = False


@dataclass(frozen=True)
class RegistrationResult:
    status: str
    source_version: SourceVersion | None
    reason: str = ""


@dataclass
class SourceRegistry:
    """C2 owner with an optional external-root durable repository."""

    _versions: dict[str, list[SourceVersion]] = field(default_factory=dict)
    _idempotency: dict[str, RegistrationResult] = field(default_factory=dict)
    store: "SQLiteStore | None" = None

    @staticmethod
    def _serialize(version: SourceVersion) -> dict[str, Any]:
        return {
            "source_id": version.source_id,
            "version": version.version,
            "provider": version.provider,
            "external_reference": {
                "provider": version.external_reference.provider,
                "external_id": version.external_reference.external_id,
                "object_type": version.external_reference.object_type,
                "locator": version.external_reference.locator,
            },
            "content": dict(version.content),
            "content_hash": version.content_hash,
            "metadata_hash": version.metadata_hash,
            "predecessor_version": version.predecessor_version,
            "tombstone": version.tombstone,
        }

    @staticmethod
    def _deserialize(payload: Mapping[str, Any]) -> SourceVersion:
        reference = dict(payload["external_reference"])
        return SourceVersion(
            source_id=str(payload["source_id"]),
            version=int(payload["version"]),
            provider=str(payload["provider"]),
            external_reference=ExternalReference(
                provider=str(reference["provider"]),
                external_id=str(reference["external_id"]),
                object_type=str(reference["object_type"]),
                locator=str(reference.get("locator", "")),
            ),
            content=dict(payload.get("content", {})),
            content_hash=str(payload["content_hash"]),
            metadata_hash=str(payload["metadata_hash"]),
            predecessor_version=(
                int(payload["predecessor_version"])
                if payload.get("predecessor_version") is not None
                else None
            ),
            tombstone=bool(payload.get("tombstone", False)),
        )

    def _history(self, source_id: str) -> list[SourceVersion]:
        if source_id in self._versions:
            return self._versions[source_id]
        durable = (
            [
                self._deserialize(payload)
                for payload in self.store.history("source_version", source_id)
            ]
            if self.store is not None
            else []
        )
        self._versions[source_id] = durable
        return durable

    @classmethod
    def _serialize_result(cls, result: RegistrationResult) -> dict[str, Any]:
        return {
            "status": result.status,
            "reason": result.reason,
            "source_version": (
                cls._serialize(result.source_version)
                if result.source_version is not None
                else None
            ),
        }

    @classmethod
    def _deserialize_result(cls, payload: Mapping[str, Any]) -> RegistrationResult:
        version = payload.get("source_version")
        return RegistrationResult(
            str(payload["status"]),
            cls._deserialize(version) if isinstance(version, Mapping) else None,
            str(payload.get("reason", "")),
        )

    @staticmethod
    def source_id(envelope: ProviderEnvelope) -> str:
        raw = f"{envelope.provider}\0{envelope.object_type}\0{envelope.external_id}"
        return "source:" + sha256(raw.encode("utf-8")).hexdigest()[:24]

    def register(
        self,
        envelope: ProviderEnvelope,
        *,
        idempotency_key: str,
        deleted: bool = False,
    ) -> RegistrationResult:
        if not idempotency_key:
            raise ValueError("idempotency_key is required")
        if idempotency_key in self._idempotency:
            previous = self._idempotency[idempotency_key]
            return RegistrationResult("no_delta", previous.source_version, "retry")
        if self.store is not None:
            durable_retry = self.store.get_idempotency(
                "source_registration", idempotency_key
            )
            if durable_retry is not None:
                previous = self._deserialize_result(durable_retry)
                self._idempotency[idempotency_key] = previous
                return RegistrationResult(
                    "no_delta", previous.source_version, "durable retry"
                )

        source_id = self.source_id(envelope)
        history = self._history(source_id)
        content = dict(envelope.payload)
        metadata = {
            "coverage": envelope.coverage,
            "cursor": envelope.cursor,
            "denied_fields": envelope.denied_fields,
            **dict(envelope.metadata),
        }
        content_hash = _digest(content)
        metadata_hash = _digest(metadata)
        current = history[-1] if history else None
        if (
            current
            and not deleted
            and not current.tombstone
            and current.content_hash == content_hash
            and current.metadata_hash == metadata_hash
        ):
            result = RegistrationResult("no_delta", current, "identical occurrence")
            self._idempotency[idempotency_key] = result
            if self.store is not None:
                self.store.put_idempotency(
                    "source_registration",
                    idempotency_key,
                    self._serialize_result(result),
                )
            return result

        version = SourceVersion(
            source_id=source_id,
            version=len(history) + 1,
            provider=envelope.provider,
            external_reference=envelope.references[0],
            content=content,
            content_hash=content_hash,
            metadata_hash=metadata_hash,
            predecessor_version=current.version if current else None,
            tombstone=deleted,
        )
        history.append(version)
        if self.store is not None:
            self.store.append(
                "source_version",
                source_id,
                version.version,
                self._serialize(version),
            )
        if deleted:
            status = "tombstone_created"
        elif current and current.content_hash == content_hash:
            status = "metadata_revision_created"
        else:
            status = "source_version_created"
        result = RegistrationResult(status, version)
        self._idempotency[idempotency_key] = result
        if self.store is not None:
            self.store.put_idempotency(
                "source_registration",
                idempotency_key,
                self._serialize_result(result),
            )
        return result

    def history(self, source_id: str) -> tuple[SourceVersion, ...]:
        return tuple(self._history(source_id))


__all__ = [
    "RegistrationResult",
    "SourceRegistry",
    "SourceVersion",
]
