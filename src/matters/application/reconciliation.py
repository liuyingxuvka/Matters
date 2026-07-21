"""C6 bounded Matter reconciliation and original-owner dispatch.

This owner selects a placement from a finite current candidate window.  It
delegates Matter admission and hierarchy/relationship writes to injected
canonical owners; it does not create a second Matter or containment store.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from matters.domain.admission import AdmissionPacket
from matters.domain.context import (
    MAX_RECONCILIATION_CANDIDATES,
    MatterPlacementCandidate,
    MatterPlacementDecision,
    MatterReconciliationRequest,
)
from matters.domain.matters import AdmissionDecision


_SIGNAL_WEIGHTS = {
    "goal": 8,
    "outcome": 8,
    "repository_project": 6,
    "codex_workspace": 5,
    "provider_thread": 4,
    "subject": 3,
    "source_neighborhood": 2,
    "containment_scope": 7,
    "person": 1,
    "time": 1,
}
_SAME_MATTER_IDENTITY_KINDS = frozenset({"goal", "outcome"})
_CHILD_SCOPE_KINDS = frozenset(
    {
        "repository_project",
        "codex_workspace",
        "provider_thread",
        "containment_scope",
    }
)
_HOST_LICENSING_KINDS = _SAME_MATTER_IDENTITY_KINDS | _CHILD_SCOPE_KINDS


class AdmissionDecider(Protocol):
    def decide(self, packet: AdmissionPacket) -> AdmissionDecision: ...


RegisterMatter = Callable[..., Any]
AttachChild = Callable[..., Any]
RelateMatters = Callable[..., Any]


@dataclass(frozen=True)
class ReconciliationExecution:
    decision: MatterPlacementDecision
    admission: AdmissionDecision | None = None
    hierarchy_result: Any = None
    relation_result: Any = None


@dataclass(frozen=True)
class _CandidateMatch:
    candidate: MatterPlacementCandidate
    signal_kinds: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    score: int

    @property
    def supports_same_matter(self) -> bool:
        return (
            len(self.signal_kinds) >= 2
            and bool(_SAME_MATTER_IDENTITY_KINDS.intersection(self.signal_kinds))
        )

    @property
    def supports_child(self) -> bool:
        return (
            self.candidate.broad_scope
            and len(self.signal_kinds) >= 2
            and bool(_CHILD_SCOPE_KINDS.intersection(self.signal_kinds))
            and not _SAME_MATTER_IDENTITY_KINDS.intersection(self.signal_kinds)
        )

    @property
    def supports_host(self) -> bool:
        return (
            len(self.signal_kinds) >= 2
            and bool(_HOST_LICENSING_KINDS.intersection(self.signal_kinds))
        )


class MatterReconciliationOwner:
    """Choose one C6 placement and dispatch through existing canonical owners."""

    def __init__(
        self,
        admission_owner: AdmissionDecider,
        *,
        register_matter: RegisterMatter | None = None,
        attach_child: AttachChild | None = None,
        relate_matters: RelateMatters | None = None,
    ) -> None:
        self._admission_owner = admission_owner
        self._register_matter = register_matter
        self._attach_child = attach_child
        self._relate_matters = relate_matters

    @staticmethod
    def _decision(
        request: MatterReconciliationRequest,
        status: str,
        rationale: str,
        *,
        matches: tuple[_CandidateMatch, ...] = (),
        target_matter_id: str = "",
        parent_matter_id: str = "",
        related_matter_ids: tuple[str, ...] = (),
        related_matter_types: tuple[tuple[str, str], ...] = (),
        freshness: str = "current",
    ) -> MatterPlacementDecision:
        evidence_ids = tuple(
            dict.fromkeys(
                (
                    *request.evidence_ids,
                    *(
                        evidence_id
                        for match in matches
                        for evidence_id in match.evidence_ids
                    ),
                )
            )
        )
        matched_signal_kinds = tuple(
            sorted(
                {
                    signal_kind
                    for match in matches
                    for signal_kind in match.signal_kinds
                }
            )
        )
        return MatterPlacementDecision(
            status=status,
            granularity=request.granularity.object_kind,
            candidate_matter_ids=tuple(
                candidate.matter_id for candidate in request.candidates
            ),
            rationale=rationale,
            evidence_ids=evidence_ids,
            matched_signal_kinds=matched_signal_kinds,
            target_matter_id=target_matter_id,
            parent_matter_id=parent_matter_id,
            related_matter_ids=related_matter_ids,
            related_matter_types=related_matter_types,
            revision=request.revision,
            freshness=freshness,
        )

    @staticmethod
    def _matches(
        request: MatterReconciliationRequest,
    ) -> tuple[_CandidateMatch, ...]:
        incoming_by_key = {
            signal.match_key: signal
            for signal in request.context.current_signals
        }
        matches: list[_CandidateMatch] = []
        for candidate in request.candidates:
            candidate_by_key = {
                signal.match_key: signal
                for signal in candidate.context.current_signals
            }
            shared_keys = tuple(sorted(set(incoming_by_key) & set(candidate_by_key)))
            if not shared_keys:
                continue
            kinds = tuple(sorted({kind for kind, _value in shared_keys}))
            evidence_ids = tuple(
                dict.fromkeys(
                    evidence_id
                    for key in shared_keys
                    for signal in (incoming_by_key[key], candidate_by_key[key])
                    for evidence_id in signal.evidence_ids
                )
            )
            matches.append(
                _CandidateMatch(
                    candidate=candidate,
                    signal_kinds=kinds,
                    evidence_ids=evidence_ids,
                    score=sum(_SIGNAL_WEIGHTS[kind] for kind in kinds),
                )
            )
        return tuple(
            sorted(matches, key=lambda item: (-item.score, item.candidate.matter_id))
        )

    @staticmethod
    def _unique_best(
        matches: tuple[_CandidateMatch, ...],
    ) -> _CandidateMatch | None:
        if not matches:
            return None
        if len(matches) > 1 and matches[0].score == matches[1].score:
            return None
        return matches[0]

    @staticmethod
    def _related_type(
        request: MatterReconciliationRequest,
        match: _CandidateMatch,
    ) -> str:
        explicit = next(
            (
                hint.relation_type
                for hint in request.relationship_hints
                if hint.target_matter_id == match.candidate.matter_id
            ),
            "",
        )
        if explicit:
            return explicit
        kinds = set(match.signal_kinds)
        if kinds.intersection({"repository_project", "codex_workspace"}):
            return "same_project_context"
        if kinds.intersection({"provider_thread", "source_neighborhood"}):
            return "same_source_context"
        if kinds.intersection({"goal", "outcome"}):
            return "overlapping_goal"
        if "subject" in kinds:
            return "same_context"
        if "person" in kinds:
            return "shares_person"
        if "time" in kinds:
            return "temporal_context"
        return "related"

    def reconcile(
        self,
        request: MatterReconciliationRequest,
    ) -> MatterPlacementDecision:
        """Return a terminal placement without writing canonical state."""

        if request.access_blocked:
            return self._decision(
                request,
                "blocked",
                "source access or coverage blocks current reconciliation",
                freshness="blocked",
            )
        if len(request.candidates) > MAX_RECONCILIATION_CANDIDATES:
            bounded_request = MatterReconciliationRequest(
                source_ids=request.source_ids,
                evidence_ids=request.evidence_ids,
                semantic_identity_key=request.semantic_identity_key,
                context=request.context,
                candidates=request.candidates[:MAX_RECONCILIATION_CANDIDATES],
                granularity=request.granularity,
                conflict=request.conflict,
                revision=request.revision,
            )
            return self._decision(
                bounded_request,
                "blocked",
                "candidate window exceeds the C6 reconciliation bound",
                freshness="blocked",
            )
        if request.context.freshness != "current" or any(
            candidate.context.freshness != "current"
            for candidate in request.candidates
        ):
            return self._decision(
                request,
                "blocked",
                "reconciliation requires a current candidate-context window",
                freshness="blocked",
            )
        if request.conflict:
            return self._decision(
                request,
                "preserve_uncertain_alternative",
                "materially conflicting placement evidence is preserved",
            )

        matches = self._matches(request)
        same_matches = tuple(match for match in matches if match.supports_same_matter)
        same = self._unique_best(same_matches)
        if same is not None:
            return self._decision(
                request,
                "append_to_current",
                "multiple evidence-bound signals license the same current Matter",
                matches=(same,),
                target_matter_id=same.candidate.matter_id,
            )
        if len(same_matches) > 1 and same_matches[0].score == same_matches[1].score:
            return self._decision(
                request,
                "preserve_uncertain_alternative",
                "equally supported current Matters prevent a unique append target",
                matches=same_matches,
            )

        object_kind = request.granularity.object_kind
        if object_kind != "matter":
            host_matches = tuple(match for match in matches if match.supports_host)
            host = self._unique_best(host_matches)
            if host is not None:
                return self._decision(
                    request,
                    "append_to_current",
                    f"the {object_kind} belongs inside one licensed current Matter",
                    matches=(host,),
                    target_matter_id=host.candidate.matter_id,
                )
            return self._decision(
                request,
                "preserve_uncertain_alternative",
                f"the {object_kind} remains below Matter granularity without a unique host",
                matches=host_matches or matches,
            )

        if not request.semantic_identity_key:
            return self._decision(
                request,
                "preserve_uncertain_alternative",
                "new Matter admission requires a stable semantic identity",
                matches=matches,
            )

        child_matches = tuple(match for match in matches if match.supports_child)
        child = self._unique_best(child_matches)
        if child is not None:
            return self._decision(
                request,
                "admit_child",
                "independent goal/outcome is bounded by a broader current Matter",
                matches=(child,),
                parent_matter_id=child.candidate.matter_id,
            )
        if len(child_matches) > 1 and child_matches[0].score == child_matches[1].score:
            return self._decision(
                request,
                "preserve_uncertain_alternative",
                "equally supported broader Matters prevent a unique parent",
                matches=child_matches,
            )

        if matches:
            related_matter_ids = tuple(
                match.candidate.matter_id for match in matches
            )
            return self._decision(
                request,
                "admit_related",
                "context licenses relations but not merge or primary containment",
                matches=matches,
                related_matter_ids=related_matter_ids,
                related_matter_types=tuple(
                    (
                        match.candidate.matter_id,
                        self._related_type(request, match),
                    )
                    for match in matches
                ),
            )
        return self._decision(
            request,
            "admit_root",
            "an independent goal/outcome has no licensed current parent or merge target",
        )

    @staticmethod
    def _candidate(
        request: MatterReconciliationRequest,
        matter_id: str,
    ) -> MatterPlacementCandidate:
        return next(
            candidate
            for candidate in request.candidates
            if candidate.matter_id == matter_id
        )

    @staticmethod
    def _require_admitted(admission: AdmissionDecision) -> str:
        if admission.status != "admitted" or admission.matter is None:
            raise RuntimeError(
                "C6 reconciliation dispatch did not produce an admitted Matter"
            )
        return admission.matter.matter_id

    def execute(
        self,
        request: MatterReconciliationRequest,
    ) -> ReconciliationExecution:
        """Apply a placement through injected existing-owner boundaries."""

        decision = self.reconcile(request)
        if decision.status in {"blocked", "preserve_uncertain_alternative"}:
            return ReconciliationExecution(decision)
        if decision.status == "admit_child" and self._attach_child is None:
            raise RuntimeError("child placement requires the hierarchy owner callback")
        if decision.status == "admit_related" and self._relate_matters is None:
            raise RuntimeError("related placement requires the relation owner callback")

        semantic_identity_key = request.semantic_identity_key
        existing_matter_id = ""
        if decision.status == "append_to_current":
            existing_matter_id = decision.target_matter_id
            semantic_identity_key = self._candidate(
                request,
                existing_matter_id,
            ).semantic_identity_key
        admission = self._admission_owner.decide(
            AdmissionPacket(
                source_ids=request.source_ids,
                evidence_ids=request.evidence_ids,
                explicit_goal_or_obligation=True,
                conflict=request.conflict,
                semantic_identity_key=semantic_identity_key,
                existing_matter_id=existing_matter_id,
            )
        )
        matter_id = self._require_admitted(admission)

        if decision.status == "append_to_current":
            return ReconciliationExecution(decision, admission=admission)

        if self._register_matter is not None:
            self._register_matter(
                matter_id,
                change_ref=f"reconciliation:{request.revision}:{decision.status}",
            )

        hierarchy_result = None
        if decision.status == "admit_child":
            hierarchy_result = self._attach_child(
                parent_matter_id=decision.parent_matter_id,
                child_matter_id=matter_id,
                role="optional",
                confidence="bounded",
                rationale=decision.rationale,
                evidence_ids=decision.evidence_ids,
            )

        relation_result = None
        if decision.status == "admit_related":
            relation_result = self._relate_matters(
                matter_id=matter_id,
                related_matter_ids=decision.related_matter_ids,
                related_matter_types=dict(decision.related_matter_types),
                rationale=decision.rationale,
                evidence_ids=decision.evidence_ids,
            )
        return ReconciliationExecution(
            decision,
            admission=admission,
            hierarchy_result=hierarchy_result,
            relation_result=relation_result,
        )


__all__ = [
    "AdmissionDecider",
    "AttachChild",
    "MatterReconciliationOwner",
    "ReconciliationExecution",
    "RegisterMatter",
    "RelateMatters",
]
