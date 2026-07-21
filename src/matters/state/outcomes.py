"""C9: explicit completion, cancellation, conflict, and reopening."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CompletionCriterion:
    criterion_id: str
    satisfied: bool
    evidence_ids: tuple[str, ...] = ()
    basis_modality: str = "reported"
    temporal_direction: str = "past"
    freshness: str = "current"
    completion_licensed: bool = True
    owner_evidence_licensed: bool = False
    terminality: str = "confirmed"
    inference_contract_valid: bool = False


@dataclass(frozen=True)
class OutcomeDecision:
    status: str
    rationale: str
    criterion_ids: tuple[str, ...] = ()
    revision: int = 1
    open_loop_dispositions: tuple[str, ...] = ()
    basis_modality: str = "unknown"
    terminality: str = "confirmed"


@dataclass
class OutcomeOwner:
    _history: dict[str, list[OutcomeDecision]] = field(default_factory=dict)

    def decide_completion(
        self,
        matter_id: str,
        criteria: tuple[CompletionCriterion, ...],
        *,
        provider_done: bool = False,
        result_attachment_only: bool = False,
    ) -> OutcomeDecision:
        history = self._history.setdefault(matter_id, [])
        confirmed_complete = bool(criteria) and all(
            item.satisfied
            and item.evidence_ids
            and item.freshness == "current"
            and item.completion_licensed
            and item.owner_evidence_licensed
            and item.temporal_direction != "future"
            and item.basis_modality in {"observed", "reported"}
            and item.terminality == "confirmed"
            for item in criteria
        )
        provisional_complete = bool(criteria) and all(
            item.satisfied
            and item.evidence_ids
            and item.freshness == "current"
            and item.completion_licensed
            and item.owner_evidence_licensed
            and item.temporal_direction == "past"
            and (
                (
                    item.basis_modality in {"observed", "reported"}
                    and item.terminality == "confirmed"
                )
                or (
                    item.basis_modality in {"inferred", "ai_inferred"}
                    and item.terminality == "provisional"
                    and item.inference_contract_valid
                )
            )
            for item in criteria
        ) and any(
            item.basis_modality in {"inferred", "ai_inferred"}
            for item in criteria
        )
        if confirmed_complete:
            status = "completed"
            rationale = "all explicit completion criteria have current evidence"
            basis_modality = "reported"
            terminality = "confirmed"
        elif provisional_complete:
            status = "completed"
            rationale = (
                "all bounded elapsed-phase criteria are supported by a "
                "revisable historical inference contract"
            )
            basis_modality = "ai_inferred"
            terminality = "provisional"
        else:
            status = "completion_unproven"
            rationale = (
                "provider Done, a final file, or incomplete criteria cannot prove completion"
                if provider_done or result_attachment_only
                else "completion criteria are incomplete"
            )
            basis_modality = "unknown"
            terminality = "provisional"
        decision = OutcomeDecision(
            status,
            rationale,
            tuple(item.criterion_id for item in criteria),
            len(history) + 1,
            basis_modality=basis_modality,
            terminality=terminality,
        )
        history.append(decision)
        return decision

    def cancel(
        self,
        matter_id: str,
        *,
        rationale: str,
        loop_dispositions: tuple[str, ...],
        basis_modality: str = "reported",
        terminality: str = "confirmed",
    ) -> OutcomeDecision:
        history = self._history.setdefault(matter_id, [])
        decision = OutcomeDecision(
            "cancelled",
            rationale,
            revision=len(history) + 1,
            open_loop_dispositions=loop_dispositions,
            basis_modality=basis_modality,
            terminality=terminality,
        )
        history.append(decision)
        return decision

    def reopen(self, matter_id: str, *, new_obligation_id: str) -> OutcomeDecision:
        history = self._history.setdefault(matter_id, [])
        decision = OutcomeDecision(
            "reopened",
            f"new licensed obligation {new_obligation_id}",
            revision=len(history) + 1,
        )
        history.append(decision)
        return decision

    def record_conflict(
        self,
        matter_id: str,
        *,
        rationale: str,
    ) -> OutcomeDecision:
        history = self._history.setdefault(matter_id, [])
        decision = OutcomeDecision(
            "outcome_conflict",
            rationale,
            revision=len(history) + 1,
        )
        history.append(decision)
        return decision

    def history(self, matter_id: str) -> tuple[OutcomeDecision, ...]:
        return tuple(self._history.get(matter_id, ()))


__all__ = ["CompletionCriterion", "OutcomeDecision", "OutcomeOwner"]
