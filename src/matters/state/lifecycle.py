"""C7: lifecycle and board placement from explicit proof packets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("lifecycle inference timestamps require a timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class StateProofPacket:
    coverage: str
    explicit_start: bool = False
    work_recorded: bool = False
    scheduled: bool = False
    provider_status: str = ""
    completion_licensed: bool = False
    evidence_ids: tuple[str, ...] = ()
    basis_modality: str = "reported"
    basis_scope: str = "source_record"
    temporal_assertion: str = "unknown"
    current_phase_requested: bool = False
    prerequisite_evidence_ids: tuple[str, ...] = ()
    remaining_obligation_ids: tuple[str, ...] = ()
    analysis_as_of: str = ""
    active_window_start: str = ""
    active_window_end: str = ""
    contradiction_checked: bool = False
    counter_signals: tuple[str, ...] = ()
    confidence: str = "unknown"
    alternatives: tuple[str, ...] = ()
    coverage_boundary: str = ""
    expires_at: str = ""
    contradiction_triggers: tuple[str, ...] = ()


@dataclass(frozen=True)
class LifecycleDecision:
    state: str
    board_column: str
    rationale: str
    evidence_ids: tuple[str, ...] = ()
    provider_conflict: bool = False
    basis_modality: str = "unknown"
    basis_scope: str = ""
    temporal_assertion: str = "unknown"
    terminality: str = "confirmed"
    confidence: str = "unknown"
    alternatives: tuple[str, ...] = ()
    coverage_boundary: str = ""
    expires_at: str = ""
    contradiction_triggers: tuple[str, ...] = ()
    counter_signals: tuple[str, ...] = ()


class LifecycleOwner:
    def decide(self, packet: StateProofPacket) -> LifecycleDecision:
        if packet.current_phase_requested:
            current_phase_complete = (
                packet.basis_modality in {"inferred", "ai_inferred"}
                and packet.basis_scope == "current_phase"
                and packet.temporal_assertion == "ongoing"
                and bool(packet.prerequisite_evidence_ids)
                and set(packet.prerequisite_evidence_ids).issubset(
                    packet.evidence_ids
                )
                and bool(packet.remaining_obligation_ids)
                and bool(packet.analysis_as_of)
                and bool(packet.active_window_start)
                and bool(packet.active_window_end)
                and packet.contradiction_checked
                and not packet.counter_signals
                and packet.confidence not in {"", "unknown"}
                and bool(packet.alternatives)
                and bool(packet.coverage_boundary)
                and bool(packet.expires_at)
                and bool(packet.contradiction_triggers)
            )
            if current_phase_complete:
                analysis_time = _aware(packet.analysis_as_of)
                if (
                    _aware(packet.active_window_start)
                    <= analysis_time
                    <= _aware(packet.active_window_end)
                    and analysis_time <= _aware(packet.expires_at)
                ):
                    return LifecycleDecision(
                        "in_progress",
                        "In Progress",
                        (
                            "completed prerequisite, remaining required work, "
                            "and the active window license a provisional current-phase estimate"
                        ),
                        packet.evidence_ids,
                        basis_modality="ai_inferred",
                        basis_scope="current_phase",
                        temporal_assertion="ongoing",
                        terminality="provisional",
                        confidence=packet.confidence,
                        alternatives=packet.alternatives,
                        coverage_boundary=packet.coverage_boundary,
                        expires_at=packet.expires_at,
                        contradiction_triggers=packet.contradiction_triggers,
                    )
            return LifecycleDecision(
                "uncertain",
                "Uncertain",
                "current-phase inference contract is incomplete or outside its active window",
                packet.evidence_ids,
                basis_modality="ai_inferred",
                basis_scope="current_phase",
                temporal_assertion="unknown",
                terminality="provisional",
                confidence=packet.confidence,
                alternatives=packet.alternatives,
                coverage_boundary=packet.coverage_boundary,
                expires_at=packet.expires_at,
                contradiction_triggers=packet.contradiction_triggers,
                counter_signals=packet.counter_signals,
            )
        if packet.explicit_start or packet.work_recorded:
            return LifecycleDecision(
                "in_progress",
                "In Progress",
                "current evidence records actual work",
                packet.evidence_ids,
                basis_modality=(
                    packet.basis_modality
                    if packet.basis_modality in {"observed", "reported"}
                    else "reported"
                ),
                basis_scope=packet.basis_scope or "source_record",
                temporal_assertion="ongoing",
            )
        if packet.scheduled:
            return LifecycleDecision(
                "planned",
                "Planned",
                "scheduling is present without actual-start evidence",
                packet.evidence_ids,
                basis_modality=(
                    packet.basis_modality
                    if packet.basis_modality in {"reported", "planned"}
                    else "planned"
                ),
                basis_scope=packet.basis_scope or "source_record",
                temporal_assertion="planned",
            )
        if packet.provider_status.lower() == "done" and not packet.completion_licensed:
            return LifecycleDecision(
                "completion_unproven",
                "Uncertain",
                "provider Done does not prove Matters completion",
                packet.evidence_ids,
                provider_conflict=True,
                basis_modality=packet.basis_modality,
                basis_scope=packet.basis_scope,
            )
        if packet.coverage != "complete":
            return LifecycleDecision(
                "uncertain",
                "Uncertain",
                "partial or unknown coverage leaves the start state uncertain",
                packet.evidence_ids,
                basis_modality=packet.basis_modality,
                basis_scope=packet.basis_scope,
            )
        return LifecycleDecision(
            "not_started",
            "Not Started",
            "complete coverage contains no actual-start evidence",
            packet.evidence_ids,
            basis_modality=packet.basis_modality,
            basis_scope=packet.basis_scope,
        )

    @staticmethod
    def write_from_ui(*_args, **_kwargs) -> None:
        raise PermissionError("UI cannot write canonical lifecycle state")


__all__ = ["LifecycleDecision", "LifecycleOwner", "StateProofPacket"]
