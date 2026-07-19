"""Provider-neutral read envelope and read-only adapter contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class ExternalReference:
    provider: str
    external_id: str
    object_type: str
    locator: str = ""


@dataclass(frozen=True)
class ProviderEnvelope:
    provider: str
    external_id: str
    object_type: str
    payload: Mapping[str, Any]
    coverage: str = "complete"
    cursor: str = ""
    denied_fields: tuple[str, ...] = ()
    references: tuple[ExternalReference, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.provider or not self.external_id or not self.object_type:
            raise ValueError("provider, external_id, and object_type are required")
        if self.coverage not in {"complete", "partial", "unknown"}:
            raise ValueError("coverage must be complete, partial, or unknown")
        object.__setattr__(self, "payload", dict(self.payload))
        object.__setattr__(self, "metadata", dict(self.metadata))
        object.__setattr__(self, "denied_fields", tuple(self.denied_fields))
        if not self.references:
            object.__setattr__(
                self,
                "references",
                (
                    ExternalReference(
                        provider=self.provider,
                        external_id=self.external_id,
                        object_type=self.object_type,
                    ),
                ),
            )


class ReadOnlyProvider(Protocol):
    provider_id: str

    def read(
        self,
        *,
        object_ids: Sequence[str],
        cursor: str = "",
    ) -> tuple[ProviderEnvelope, ...]:
        """Return bounded envelopes without mutating the provider."""


class ProviderWriteForbidden(PermissionError):
    """Raised when a caller requests a provider mutation."""


__all__ = [
    "ExternalReference",
    "ProviderEnvelope",
    "ProviderWriteForbidden",
    "ReadOnlyProvider",
]
