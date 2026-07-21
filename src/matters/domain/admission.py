"""C6: conservative source-first Matter formation and admission."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import unicodedata

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
    semantic_identity_key: str = ""
    existing_matter_id: str = ""


@dataclass
class MatterAdmission:
    _admitted: dict[str, Matter] = field(default_factory=dict)
    _candidates: dict[str, MatterCandidate] = field(default_factory=dict)
    _matter_id_by_semantic_identity: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def _id(prefix: str, identity: str) -> str:
        digest = sha256(identity.encode("utf-8")).hexdigest()[:24]
        return f"{prefix}:{digest}"

    @staticmethod
    def _semantic_identity(packet: AdmissionPacket) -> str:
        key = unicodedata.normalize(
            "NFKC",
            packet.semantic_identity_key,
        ).casefold()
        key = " ".join(key.split())
        if not key and packet.evidence_ids:
            # Legacy callers without an explicit semantic key receive a stable
            # evidence-anchor identity.  Source membership is never the key.
            key = f"evidence-anchor:{packet.evidence_ids[0]}"
        if not key:
            return ""
        return "semantic:" + sha256(key.encode("utf-8")).hexdigest()

    @classmethod
    def _candidate_id(cls, packet: AdmissionPacket) -> str:
        identity = cls._semantic_identity(packet)
        if not identity:
            identity = "candidate-sources:" + "\0".join(packet.source_ids)
        return cls._id("candidate", identity)

    def restore(self, matter: Matter) -> None:
        """Restore a durable admitted Matter without re-deriving its identity."""

        self._admitted[matter.matter_id] = matter
        if matter.semantic_identity_id:
            self._matter_id_by_semantic_identity[
                matter.semantic_identity_id
            ] = matter.matter_id

    def decide(self, packet: AdmissionPacket) -> AdmissionDecision:
        if packet.access_blocked:
            return AdmissionDecision("blocked", "source access or coverage blocked")
        if packet.conflict:
            candidate_id = self._candidate_id(packet)
            candidate = MatterCandidate(
                candidate_id=candidate_id,
                source_ids=packet.source_ids,
                rationale="material conflict is preserved as an uncertain Matter",
                evidence_ids=packet.evidence_ids,
                semantic_identity_id=self._semantic_identity(packet),
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
            semantic_identity = self._semantic_identity(packet)
            if not semantic_identity:
                candidate = MatterCandidate(
                    candidate_id=self._candidate_id(packet),
                    source_ids=packet.source_ids,
                    rationale="stable semantic identity is missing",
                    evidence_ids=packet.evidence_ids,
                )
                self._candidates[candidate.candidate_id] = candidate
                return AdmissionDecision(
                    "uncertain",
                    "admission requires a stable semantic identity",
                    candidate=candidate,
                )
            matter_id = (
                packet.existing_matter_id.strip()
                or self._matter_id_by_semantic_identity.get(
                    semantic_identity,
                    "",
                )
                or self._id("matter", semantic_identity)
            )
            prior = self._admitted.get(matter_id)
            matter = Matter(
                matter_id=matter_id,
                source_ids=tuple(
                    dict.fromkeys(
                        (
                            *(prior.source_ids if prior is not None else ()),
                            *packet.source_ids,
                        )
                    )
                ),
                rationale="current evidence licenses admission",
                evidence_ids=tuple(
                    dict.fromkeys(
                        (
                            *(prior.evidence_ids if prior is not None else ()),
                            *packet.evidence_ids,
                        )
                    )
                ),
                semantic_identity_id=semantic_identity,
            )
            self._admitted[matter_id] = matter
            self._matter_id_by_semantic_identity[semantic_identity] = matter_id
            return AdmissionDecision("admitted", matter.rationale, matter=matter)
        candidate_id = self._candidate_id(packet)
        candidate = MatterCandidate(
            candidate_id=candidate_id,
            source_ids=packet.source_ids,
            rationale="useful source is retained as an uncertain Matter",
            evidence_ids=packet.evidence_ids,
            semantic_identity_id=self._semantic_identity(packet),
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
