"""Relationship candidates never imply automatic merge or causality."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MatterRelationCandidate:
    source_matter_id: str
    relation_type: str
    target_matter_id: str
    causal: bool = False
    auto_merge: bool = False


__all__ = ["MatterRelationCandidate"]
