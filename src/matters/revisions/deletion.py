"""Deletion requests are revision inputs, never destructive commands."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeletionRequest:
    target_id: str
    rationale: str
    evidence_ids: tuple[str, ...] = ()


__all__ = ["DeletionRequest"]
