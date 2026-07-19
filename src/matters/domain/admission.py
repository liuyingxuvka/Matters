"""C6: conservative source-first Matter formation and admission."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256

from matters.domain.matters import AdmissionDecision, Matter, MatterCandidate


@dataclass(frozen=True)
class AdmissionPacket:
    source_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...] = ()
    explicit_goal_or_obligation: bool = False
    useful_content: bool = True
    conflict: bool = False
    access_blocked: bool = False
    possibility_only: bool = False
    requested_status: str = ""


@dataclass
class MatterAdmission:
    _admitted: dict[str, Matter] = field(default_factory=dict)
    _candidates: dict[str, MatterCandidate] = field(default_factory=dict)

    @staticmethod
    def _id(prefix: str, source_ids: tuple[str, ...]) -> str:
        digest = sha256("\0".join(source_ids).encode("utf-8")).hexdigest()[:24]
        return f"{prefix}:{digest}"

    def decide(self, packet: AdmissionPacket) -> AdmissionDecision:
        if packet.access_blocked:
            return AdmissionDecision("blocked", "source access or coverage blocked")
        if packet.conflict:
            candidate_id = self._id("candidate", packet.source_ids)
            candidate = MatterCandidate(
                candidate_id=candidate_id,
                source_ids=packet.source_ids,
                rationale="material conflict is preserved as an uncertain Matter",
                evidence_ids=packet.evidence_ids,
            )
            self._candidates[candidate_id] = candidate
            return AdmissionDecision(
                "uncertain",
                candidate.rationale,
                candidate=candidate,
            )
        if packet.possibility_only or not packet.useful_content:
            return AdmissionDecision("source_only", "no current goal or obligation")
        if packet.explicit_goal_or_obligation and packet.evidence_ids:
            matter_id = self._id("matter", packet.source_ids)
            matter = Matter(
                matter_id=matter_id,
                source_ids=packet.source_ids,
                rationale="current evidence licenses admission",
                evidence_ids=packet.evidence_ids,
            )
            self._admitted[matter_id] = matter
            return AdmissionDecision("admitted", matter.rationale, matter=matter)
        candidate_id = self._id("candidate", packet.source_ids)
        candidate = MatterCandidate(
            candidate_id=candidate_id,
            source_ids=packet.source_ids,
            rationale="useful source is retained as an uncertain Matter",
            evidence_ids=packet.evidence_ids,
        )
        self._candidates[candidate_id] = candidate
        return AdmissionDecision("uncertain", candidate.rationale, candidate=candidate)

    @property
    def admitted_count(self) -> int:
        return len(self._admitted)

    @property
    def candidate_count(self) -> int:
        return len(self._candidates)


__all__ = ["AdmissionPacket", "MatterAdmission"]
