"""Core Matter values. Admission authority lives in C6."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatterCandidate:
    candidate_id: str
    source_ids: tuple[str, ...]
    rationale: str
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Matter:
    matter_id: str
    source_ids: tuple[str, ...]
    rationale: str
    evidence_ids: tuple[str, ...]
    admitted: bool = True


@dataclass(frozen=True)
class AdmissionDecision:
    status: str
    rationale: str
    candidate: MatterCandidate | None = None
    matter: Matter | None = None


__all__ = ["AdmissionDecision", "Matter", "MatterCandidate"]
