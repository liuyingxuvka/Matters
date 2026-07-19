"""C7: lifecycle and board placement from explicit proof packets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StateProofPacket:
    coverage: str
    explicit_start: bool = False
    work_recorded: bool = False
    scheduled: bool = False
    provider_status: str = ""
    completion_licensed: bool = False
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class LifecycleDecision:
    state: str
    board_column: str
    rationale: str
    evidence_ids: tuple[str, ...] = ()
    provider_conflict: bool = False


class LifecycleOwner:
    def decide(self, packet: StateProofPacket) -> LifecycleDecision:
        if packet.explicit_start or packet.work_recorded:
            return LifecycleDecision(
                "in_progress",
                "In Progress",
                "current evidence records actual work",
                packet.evidence_ids,
            )
        if packet.scheduled:
            return LifecycleDecision(
                "planned",
                "Planned",
                "scheduling is present without actual-start evidence",
                packet.evidence_ids,
            )
        if packet.provider_status.lower() == "done" and not packet.completion_licensed:
            return LifecycleDecision(
                "completion_unproven",
                "Uncertain",
                "provider Done does not prove Matters completion",
                packet.evidence_ids,
                provider_conflict=True,
            )
        if packet.coverage != "complete":
            return LifecycleDecision(
                "uncertain",
                "Uncertain",
                "partial or unknown coverage leaves the start state uncertain",
                packet.evidence_ids,
            )
        return LifecycleDecision(
            "not_started",
            "Not Started",
            "complete coverage contains no actual-start evidence",
            packet.evidence_ids,
        )

    @staticmethod
    def write_from_ui(*_args, **_kwargs) -> None:
        raise PermissionError("UI cannot write canonical lifecycle state")


__all__ = ["LifecycleDecision", "LifecycleOwner", "StateProofPacket"]
