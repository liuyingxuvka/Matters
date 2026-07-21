from matters.state.lifecycle import LifecycleOwner, StateProofPacket
import pytest


def test_lifecycle_requires_proof_and_provider_done_is_not_authority():
    owner = LifecycleOwner()
    assert owner.decide(StateProofPacket("complete", explicit_start=True)).state == "in_progress"
    assert owner.decide(StateProofPacket("complete", scheduled=True)).state == "planned"
    assert owner.decide(StateProofPacket("partial")).state == "uncertain"
    conflict = owner.decide(StateProofPacket("complete", provider_status="Done"))
    assert conflict.state == "completion_unproven"
    assert conflict.board_column == "Uncertain"
    assert conflict.provider_conflict
    with pytest.raises(PermissionError):
        owner.write_from_ui("in_progress")


def test_current_phase_inference_requires_prerequisite_obligation_and_active_window():
    owner = LifecycleOwner()
    packet = StateProofPacket(
        "complete",
        evidence_ids=("e:registration-confirmed",),
        basis_modality="ai_inferred",
        basis_scope="current_phase",
        temporal_assertion="ongoing",
        current_phase_requested=True,
        prerequisite_evidence_ids=("e:registration-confirmed",),
        remaining_obligation_ids=("submit-project",),
        analysis_as_of="2026-07-20T12:00:00+00:00",
        active_window_start="2026-07-16T00:00:00+00:00",
        active_window_end="2026-07-21T23:59:59+00:00",
        contradiction_checked=True,
        confidence="bounded",
        alternatives=("Preparation may be paused.",),
        coverage_boundary="No direct editor activity is available.",
        expires_at="2026-07-21T23:59:59+00:00",
        contradiction_triggers=("withdrawal or submitted result",),
    )

    decision = owner.decide(packet)

    assert decision.state == "in_progress"
    assert decision.basis_modality == "ai_inferred"
    assert decision.basis_scope == "current_phase"
    assert decision.terminality == "provisional"


def test_future_ticket_is_planned_and_cannot_be_inferred_as_completed():
    owner = LifecycleOwner()
    planned = owner.decide(
        StateProofPacket(
            "complete",
            scheduled=True,
            evidence_ids=("e:future-ticket",),
            basis_modality="reported",
            temporal_assertion="planned",
        )
    )
    invalid_current_phase = owner.decide(
        StateProofPacket(
            "complete",
            evidence_ids=("e:future-ticket",),
            basis_modality="ai_inferred",
            basis_scope="current_phase",
            temporal_assertion="ongoing",
            current_phase_requested=True,
            prerequisite_evidence_ids=("e:future-ticket",),
            remaining_obligation_ids=(),
            analysis_as_of="2026-07-20T12:00:00+00:00",
            active_window_start="2026-09-30T00:00:00+00:00",
            active_window_end="2026-10-01T23:59:59+00:00",
            contradiction_checked=True,
            confidence="bounded",
            alternatives=("The itinerary may change.",),
            coverage_boundary="The flight date is still in the future.",
            expires_at="2026-09-30T00:00:00+00:00",
            contradiction_triggers=("cancellation or rebooking",),
        )
    )

    assert planned.state == "planned"
    assert invalid_current_phase.state == "uncertain"


def test_current_cancellation_or_postponement_blocks_preparation_inference():
    owner = LifecycleOwner()
    decision = owner.decide(
        StateProofPacket(
            "complete",
            evidence_ids=(
                "e:registration-confirmed",
                "e:postponed",
            ),
            basis_modality="ai_inferred",
            basis_scope="current_phase",
            temporal_assertion="ongoing",
            current_phase_requested=True,
            prerequisite_evidence_ids=("e:registration-confirmed",),
            remaining_obligation_ids=("submit-project",),
            analysis_as_of="2026-07-20T12:00:00+00:00",
            active_window_start="2026-07-16T00:00:00+00:00",
            active_window_end="2026-07-21T23:59:59+00:00",
            contradiction_checked=True,
            counter_signals=(
                "current postponement evidence e:postponed",
            ),
            confidence="bounded",
            alternatives=("The event may resume later.",),
            coverage_boundary="Authorized registration messages only.",
            expires_at="2026-07-21T23:59:59+00:00",
            contradiction_triggers=("withdrawal or submitted result",),
        )
    )

    assert decision.state == "uncertain"
    assert decision.temporal_assertion == "unknown"
    assert decision.counter_signals == (
        "current postponement evidence e:postponed",
    )
