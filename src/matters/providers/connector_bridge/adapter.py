"""Projection bridge for already-authorized connector payloads."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from matters.providers.base import ProviderEnvelope


class ConnectorBridgeAdapter:
    provider_id = "connector_bridge"

    def __init__(self, rows: Mapping[str, Mapping[str, Any]]):
        self._rows = {str(key): dict(value) for key, value in rows.items()}

    def read(
        self,
        *,
        object_ids: Sequence[str],
        cursor: str = "",
    ) -> tuple[ProviderEnvelope, ...]:
        return tuple(
            ProviderEnvelope(
                provider="connector_bridge",
                external_id=object_id,
                object_type=str(self._rows[object_id].get("object_type", "object")),
                payload=self._rows[object_id],
            )
            for object_id in object_ids
            if object_id in self._rows
        )


__all__ = ["ConnectorBridgeAdapter"]
