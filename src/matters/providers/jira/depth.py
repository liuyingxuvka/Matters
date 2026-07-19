"""Per-case and per-Matter depth accounting for bounded Jira evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


DEPTH_LAYERS = (
    "Authorization",
    "Coverage",
    "Source",
    "Evidence",
    "Person",
    "Event",
    "Matter",
    "Action/OpenLoop",
    "State",
    "Guard",
    "Localization",
    "UI",
    "Freshness",
    "Audit",
)
DEPTH_STATUSES = frozenset(
    {
        "not_run",
        "candidate",
        "bounded",
        "licensed",
        "blocked",
        "stale",
        "user_confirmed",
    }
)
INCOMPLETE_CRITICAL_STATUSES = frozenset({"blocked", "stale", "not_run"})


@dataclass(frozen=True)
class DepthLayer:
    layer: str
    status: str
    details: Mapping[str, Any] = field(default_factory=dict)
    critical: bool = True

    def __post_init__(self) -> None:
        if self.layer not in DEPTH_LAYERS:
            raise ValueError(f"unknown depth layer: {self.layer}")
        if self.status not in DEPTH_STATUSES:
            raise ValueError(f"invalid depth status: {self.status}")
        object.__setattr__(
            self,
            "details",
            MappingProxyType(dict(self.details)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "critical": self.critical,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class MatterDepthReport:
    case_ref_hash: str
    matter_ref_hash: str
    semantic_revision: str
    layers: tuple[DepthLayer, ...]
    claim_boundary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "layers", tuple(self.layers))
        layer_names = tuple(row.layer for row in self.layers)
        if len(set(layer_names)) != len(layer_names):
            raise ValueError("depth layers must be unique")
        if set(layer_names) != set(DEPTH_LAYERS):
            missing = sorted(set(DEPTH_LAYERS) - set(layer_names))
            extra = sorted(set(layer_names) - set(DEPTH_LAYERS))
            raise ValueError(
                f"depth report must cover all layers; missing={missing}; extra={extra}"
            )

    @property
    def blocking_layers(self) -> tuple[str, ...]:
        return tuple(
            row.layer
            for row in self.layers
            if row.critical and row.status in INCOMPLETE_CRITICAL_STATUSES
        )

    @property
    def analysis_complete(self) -> bool:
        return not self.blocking_layers

    def to_dict(self) -> dict[str, Any]:
        rows = {row.layer: row.to_dict() for row in self.layers}
        return {
            "case_ref_hash": self.case_ref_hash,
            "matter_ref_hash": self.matter_ref_hash,
            "semantic_revision": self.semantic_revision,
            "layers": {layer: rows[layer] for layer in DEPTH_LAYERS},
            "analysis_complete": self.analysis_complete,
            "blocking_layers": list(self.blocking_layers),
            "claim_boundary": self.claim_boundary,
        }


__all__ = [
    "DEPTH_LAYERS",
    "DEPTH_STATUSES",
    "DepthLayer",
    "MatterDepthReport",
]
