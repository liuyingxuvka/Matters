"""C9: explicit completion, cancellation, conflict, and reopening."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CompletionCriterion:
    criterion_id: str
    satisfied: bool
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class OutcomeDecision:
    status: str
    rationale: str
    criterion_ids: tuple[str, ...] = ()
    revision: int = 1
    open_loop_dispositions: tuple[str, ...] = ()


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
        if criteria and all(item.satisfied and item.evidence_ids for item in criteria):
            status = "completed"
            rationale = "all explicit completion criteria have current evidence"
        else:
            status = "completion_unproven"
            rationale = (
                "provider Done, a final file, or incomplete criteria cannot prove completion"
                if provider_done or result_attachment_only
                else "completion criteria are incomplete"
            )
        decision = OutcomeDecision(
            status,
            rationale,
            tuple(item.criterion_id for item in criteria),
            len(history) + 1,
        )
        history.append(decision)
        return decision

    def cancel(
        self,
        matter_id: str,
        *,
        rationale: str,
        loop_dispositions: tuple[str, ...],
    ) -> OutcomeDecision:
        history = self._history.setdefault(matter_id, [])
        decision = OutcomeDecision(
            "cancelled",
            rationale,
            revision=len(history) + 1,
            open_loop_dispositions=loop_dispositions,
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
