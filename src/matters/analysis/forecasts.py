"""Forecast values remain separate from current state."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Forecast:
    forecast_id: str
    matter_id: str
    statement: str
    horizon: str
    evidence_ids: tuple[str, ...] = ()


__all__ = ["Forecast"]
