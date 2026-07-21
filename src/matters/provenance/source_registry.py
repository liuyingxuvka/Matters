"""C2: immutable source registration, versioning, and idempotency."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
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


_TRANSIENT_CONTENT_KEYS = frozenset(
    {
        "body",
        "body_html",
        "body_text",
        "content",
        "html",
        "mime",
        "mime_body",
        "raw",
        "raw_body",
        "raw_content",
        "raw_mime",
        "text",
    }
)

_SOURCE_TIME_KEYS = frozenset(
    {
        "authored_at",
        "created_at",
        "ctime",
        "date",
        "first_recorded_at",
        "internal_date",
        "message_date",
        "modified_at",
        "modified_ns",
        "mtime",
        "observed_at",
        "received_at",
        "sent_at",
        "source_created_at",
        "source_modified_at",
        "source_observed_at",
    }
)


def source_time_metadata(
    envelope: ProviderEnvelope,
) -> dict[str, Any]:
    """Retain only source-authored or source-observed time clues.

    This deliberately excludes scan, registration, processing, analysis,
    deadline, due, expiry, and presentation timestamps.  Values remain raw so
    C5 can normalize them with the field name and preserve provider semantics.
    """

    layers: list[tuple[str, Mapping[str, Any]]] = [
        ("payload", envelope.payload),
        ("provider_metadata", envelope.metadata),
    ]
    nested_metadata = envelope.payload.get("metadata")
    if isinstance(nested_metadata, Mapping):
        layers.append(("payload_metadata", nested_metadata))
    headers = envelope.payload.get("headers")
    if isinstance(headers, Mapping):
        layers.append(("headers", headers))

    retained: dict[str, Any] = {}
    for layer_name, values in layers:
        for raw_key, value in values.items():
            key = str(raw_key).strip()
            normalized = key.casefold().replace("-", "_")
            if layer_name == "headers" and normalized == "date":
                normalized = "message_date"
            if normalized not in _SOURCE_TIME_KEYS or value is None or value == "":
                continue
            retained[f"{layer_name}.{normalized}"] = value
    return retained


def durable_source_content(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Remove complete source bytes/text while retaining useful private metadata.

    The complete provider payload remains available to the active call through
    ``SourceVersion.transient_content`` only.  Durable state keeps per-field
    fingerprints and lengths so freshness and idempotency do not require a
    second copy of the original.
    """

    durable: dict[str, Any] = {}
    for raw_key, value in payload.items():
        key = str(raw_key)
        if key.casefold() not in _TRANSIENT_CONTENT_KEYS:
            durable[key] = value
            continue
        if value is None:
            continue
        if isinstance(value, bytes):
            encoded = value
        else:
            encoded = str(value).encode("utf-8")
        durable[f"{key}_fingerprint"] = (
            "sha256:" + sha256(encoded).hexdigest()
        )
        durable[f"{key}_byte_length"] = len(encoded)
    return durable


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
    storage_class: str = "external_original"
    locator_fingerprint: str = ""
    original_availability: str = "available"
    source_time_metadata: Mapping[str, Any] = field(default_factory=dict)
    transient_content: Mapping[str, Any] = field(
        default_factory=dict,
        repr=False,
        compare=False,
    )


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
            "storage_class": version.storage_class,
            "locator_fingerprint": version.locator_fingerprint,
            "original_availability": version.original_availability,
            "source_time_metadata": dict(version.source_time_metadata),
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
            storage_class=str(
                payload.get("storage_class", "external_original")
            ),
            locator_fingerprint=str(
                payload.get("locator_fingerprint", "")
            ),
            original_availability=str(
                payload.get("original_availability", "available")
            ),
            source_time_metadata=dict(
                payload.get("source_time_metadata", {})
            ),
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
            source_version = previous.source_version
            if source_version is not None:
                source_version = replace(
                    source_version,
                    transient_content=dict(envelope.payload),
                )
            return RegistrationResult("no_delta", source_version, "retry")
        if self.store is not None:
            durable_retry = self.store.get_idempotency(
                "source_registration", idempotency_key
            )
            if durable_retry is not None:
                previous = self._deserialize_result(durable_retry)
                self._idempotency[idempotency_key] = previous
                source_version = previous.source_version
                if source_version is not None:
                    source_version = replace(
                        source_version,
                        transient_content=dict(envelope.payload),
                    )
                return RegistrationResult(
                    "no_delta", source_version, "durable retry"
                )

        source_id = self.source_id(envelope)
        history = self._history(source_id)
        transient_content = dict(envelope.payload)
        content = durable_source_content(transient_content)
        metadata = {
            "coverage": envelope.coverage,
            "cursor": envelope.cursor,
            "denied_fields": envelope.denied_fields,
            **dict(envelope.metadata),
        }
        original_content_hash = _digest(transient_content)
        metadata_hash = _digest(metadata)
        temporal_metadata = source_time_metadata(envelope)
        locator_fingerprint = _digest(
            {
                "provider": envelope.provider,
                "object_type": envelope.object_type,
                "external_id": envelope.external_id,
                "locator": envelope.references[0].locator,
            }
        )
        if self.store is not None:
            prior_holder: dict[str, SourceVersion | None] = {"value": None}

            def is_equivalent(
                current_payload: dict[str, Any] | None,
            ) -> bool:
                if current_payload is None:
                    return False
                current_version = self._deserialize(current_payload)
                return (
                    not deleted
                    and not current_version.tombstone
                    and current_version.content_hash == original_content_hash
                    and current_version.metadata_hash == metadata_hash
                    and dict(current_version.source_time_metadata)
                    == temporal_metadata
                )

            def payload_factory(
                revision: int,
                current_payload: dict[str, Any] | None,
            ) -> dict[str, Any]:
                current_version = (
                    self._deserialize(current_payload)
                    if current_payload is not None
                    else None
                )
                prior_holder["value"] = current_version
                version = SourceVersion(
                    source_id=source_id,
                    version=revision,
                    provider=envelope.provider,
                    external_reference=envelope.references[0],
                    content=content,
                    content_hash=original_content_hash,
                    metadata_hash=metadata_hash,
                    predecessor_version=(
                        current_version.version
                        if current_version is not None
                        else None
                    ),
                    tombstone=deleted,
                    storage_class="external_original",
                    locator_fingerprint=locator_fingerprint,
                    original_availability=(
                        "deleted" if deleted else "available"
                    ),
                    source_time_metadata=temporal_metadata,
                )
                return self._serialize(version)

            stored = self.store.compare_current_and_append(
                "source_version",
                source_id,
                is_equivalent=is_equivalent,
                payload_factory=payload_factory,
            )
            version = replace(
                self._deserialize(stored["payload"]),
                transient_content=transient_content,
            )
            self._versions.pop(source_id, None)
            if stored["status"] == "current":
                result = RegistrationResult(
                    "no_delta",
                    version,
                    "identical occurrence",
                )
            else:
                prior = prior_holder["value"]
                if deleted:
                    status = "tombstone_created"
                elif (
                    prior is not None
                    and prior.content_hash == original_content_hash
                ):
                    status = "metadata_revision_created"
                else:
                    status = "source_version_created"
                result = RegistrationResult(status, version)
            self._idempotency[idempotency_key] = result
            self.store.put_idempotency(
                "source_registration",
                idempotency_key,
                self._serialize_result(result),
            )
            return result

        current = history[-1] if history else None
        if (
            current
            and not deleted
            and not current.tombstone
            and current.content_hash == original_content_hash
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
            content_hash=original_content_hash,
            metadata_hash=metadata_hash,
            predecessor_version=current.version if current else None,
            tombstone=deleted,
            storage_class="external_original",
            locator_fingerprint=locator_fingerprint,
            original_availability=("deleted" if deleted else "available"),
            source_time_metadata=temporal_metadata,
            transient_content=transient_content,
        )
        history.append(version)
        if deleted:
            status = "tombstone_created"
        elif current and current.content_hash == original_content_hash:
            status = "metadata_revision_created"
        else:
            status = "source_version_created"
        result = RegistrationResult(status, version)
        self._idempotency[idempotency_key] = result
        return result

    def history(self, source_id: str) -> tuple[SourceVersion, ...]:
        return tuple(self._history(source_id))

    def current(self, source_id: str) -> SourceVersion | None:
        """Return the one current immutable version without exposing storage."""

        if self.store is not None:
            payload = self.store.current("source_version", source_id)
            return self._deserialize(payload) if payload is not None else None
        history = self._history(source_id)
        return history[-1] if history else None


__all__ = [
    "RegistrationResult",
    "SourceRegistry",
    "SourceVersion",
    "durable_source_content",
    "source_time_metadata",
]
