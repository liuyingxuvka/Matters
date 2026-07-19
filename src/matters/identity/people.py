"""C4: conservative person identity and matter-scoped role decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256


@dataclass(frozen=True)
class PersonCandidate:
    person_id: str
    display_name: str
    source_mention_id: str
    resolved: bool = False


@dataclass(frozen=True)
class MatterRole:
    person_id: str
    matter_id: str
    role: str
    source_evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class IdentityRevision:
    revision: int
    action: str
    person_ids: tuple[str, ...]
    reason: str


@dataclass
class PersonRegistry:
    _candidates: list[PersonCandidate] = field(default_factory=list)
    _revisions: list[IdentityRevision] = field(default_factory=list)

    def candidate(self, display_name: str, source_mention_id: str) -> PersonCandidate:
        digest = sha256(
            f"{source_mention_id}\0{display_name}".encode("utf-8")
        ).hexdigest()[:20]
        candidate = PersonCandidate(
            person_id=f"person:{digest}",
            display_name=display_name,
            source_mention_id=source_mention_id,
        )
        if candidate not in self._candidates:
            self._candidates.append(candidate)
        return candidate

    def assert_identity(
        self,
        candidate: PersonCandidate,
        *,
        strong_link_evidence: bool,
    ) -> PersonCandidate:
        if not strong_link_evidence:
            return candidate
        return PersonCandidate(
            person_id=candidate.person_id,
            display_name=candidate.display_name,
            source_mention_id=candidate.source_mention_id,
            resolved=True,
        )

    def matter_role(
        self,
        candidate: PersonCandidate,
        matter_id: str,
        role: str,
        evidence_ids: tuple[str, ...] = (),
    ) -> MatterRole:
        return MatterRole(candidate.person_id, matter_id, role, evidence_ids)

    def split(
        self,
        person_ids: tuple[str, ...],
        *,
        reason: str,
    ) -> IdentityRevision:
        revision = IdentityRevision(
            len(self._revisions) + 1,
            "split",
            person_ids,
            reason,
        )
        self._revisions.append(revision)
        return revision


__all__ = [
    "IdentityRevision",
    "MatterRole",
    "PersonCandidate",
    "PersonRegistry",
]
