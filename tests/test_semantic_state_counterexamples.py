from matters.state.lifecycle import LifecycleOwner, StateProofPacket
from matters.state.outcomes import CompletionCriterion, OutcomeOwner
from matters.timeline.events import EventRegistry


def _confirmed_past_outcome(
    owner: OutcomeOwner,
    matter_id: str,
    criterion_id: str,
    evidence_id: str,
):
    return owner.decide_completion(
        matter_id,
        (
            CompletionCriterion(
                criterion_id,
                True,
                (evidence_id,),
                basis_modality="reported",
                temporal_direction="past",
                owner_evidence_licensed=True,
                terminality="confirmed",
            ),
        ),
    )


def test_build_week_registration_preparation_and_submission_stay_separate():
    lifecycle = LifecycleOwner()
    outcomes = OutcomeOwner()

    registration = _confirmed_past_outcome(
        outcomes,
        "work-item:build-week-registration",
        "registration-confirmed",
        "evidence:registration-confirmed",
    )
    preparation = lifecycle.decide(
        StateProofPacket(
            "complete",
            evidence_ids=("evidence:registration-confirmed",),
            basis_modality="ai_inferred",
            basis_scope="current_phase",
            temporal_assertion="ongoing",
            current_phase_requested=True,
            prerequisite_evidence_ids=(
                "evidence:registration-confirmed",
            ),
            remaining_obligation_ids=("submit-project",),
            analysis_as_of="2026-07-20T12:00:00+00:00",
            active_window_start="2026-07-16T00:00:00+00:00",
            active_window_end="2026-07-21T23:59:59+00:00",
            contradiction_checked=True,
            confidence="bounded",
            alternatives=("Preparation may be paused.",),
            coverage_boundary="No direct editor activity is available.",
            expires_at="2026-07-21T23:59:59+00:00",
            contradiction_triggers=(
                "withdrawal, submitted result, or postponement",
            ),
        )
    )
    submission = lifecycle.decide(
        StateProofPacket(
            "complete",
            scheduled=True,
            evidence_ids=("evidence:submission-deadline",),
            basis_modality="reported",
            temporal_assertion="planned",
        )
    )
    impossible_future_completion = outcomes.decide_completion(
        "work-item:build-week-submission",
        (
            CompletionCriterion(
                "submission-deadline-known",
                True,
                ("evidence:submission-deadline",),
                basis_modality="reported",
                temporal_direction="future",
                owner_evidence_licensed=True,
            ),
        ),
    )

    assert registration.status == "completed"
    assert registration.terminality == "confirmed"
    assert preparation.state == "in_progress"
    assert preparation.basis_modality == "ai_inferred"
    assert preparation.terminality == "provisional"
    assert submission.state == "planned"
    assert impossible_future_completion.status == "completion_unproven"


def test_travel_purchase_and_boarding_records_do_not_complete_future_trip():
    lifecycle = LifecycleOwner()
    outcomes = OutcomeOwner()
    events = EventRegistry()

    ticket_purchase = _confirmed_past_outcome(
        outcomes,
        "work-item:australia-ticket-purchase",
        "ticket-purchased",
        "evidence:ticket-purchase",
    )
    boarding_pass = events.from_understanding(
        kind="boarding_pass_issued",
        source_revision="source:boarding-email:v1",
        record_time="2026-06-17T18:23:25+00:00",
        claimed_time="2026-06-18T10:00:00+02:00",
        object_ref="matter:australia-trip",
        evidence_ids=("evidence:boarding-email",),
        modality="reported",
        logical_event_key="australia-trip:boarding-pass-issued",
    )
    future_flight = lifecycle.decide(
        StateProofPacket(
            "complete",
            scheduled=True,
            evidence_ids=("evidence:future-itinerary",),
            basis_modality="reported",
            temporal_assertion="planned",
        )
    )
    future_arrival = outcomes.decide_completion(
        "matter:australia-trip",
        (
            CompletionCriterion(
                "arrival-on-itinerary",
                True,
                ("evidence:future-itinerary",),
                basis_modality="reported",
                temporal_direction="future",
                owner_evidence_licensed=True,
            ),
        ),
    )

    assert ticket_purchase.status == "completed"
    assert boarding_pass.kind == "boarding_pass_issued"
    assert boarding_pass.modality == "reported"
    assert future_flight.state == "planned"
    assert future_arrival.status == "completion_unproven"


def test_reported_past_event_keeps_temporal_direction_without_becoming_inference():
    event = EventRegistry().from_understanding(
        kind="ticket_purchase_completed",
        source_revision="source:ticket-email:v1",
        record_time="2026-06-27T17:58:51+02:00",
        claimed_time="2026-06-28T00:00:00+02:00",
        object_ref="matter:japan-trip",
        evidence_ids=("evidence:ticket-email",),
        modality="reported",
        temporal_direction="past",
    )

    assert event.modality == "reported"
    assert event.temporal_direction == "past"
    assert event.inference_purpose == ""


def test_cancellation_or_postponement_overrides_current_phase_guess():
    lifecycle = LifecycleOwner()
    outcomes = OutcomeOwner()

    contradicted_preparation = lifecycle.decide(
        StateProofPacket(
            "complete",
            evidence_ids=(
                "evidence:registration-confirmed",
                "evidence:event-postponed",
            ),
            basis_modality="ai_inferred",
            basis_scope="current_phase",
            temporal_assertion="ongoing",
            current_phase_requested=True,
            prerequisite_evidence_ids=(
                "evidence:registration-confirmed",
            ),
            remaining_obligation_ids=("submit-project",),
            analysis_as_of="2026-07-20T12:00:00+00:00",
            active_window_start="2026-07-16T00:00:00+00:00",
            active_window_end="2026-07-21T23:59:59+00:00",
            contradiction_checked=True,
            counter_signals=("The event was postponed.",),
            confidence="bounded",
            alternatives=("Preparation may resume after rescheduling.",),
            coverage_boundary="Current authorized event messages.",
            expires_at="2026-07-21T23:59:59+00:00",
            contradiction_triggers=("postponement or cancellation",),
        )
    )
    cancelled_trip = outcomes.cancel(
        "matter:japan-trip",
        rationale="current cancellation confirmation",
        loop_dispositions=("closed:travel-booking-loop",),
    )

    assert contradicted_preparation.state == "uncertain"
    assert contradicted_preparation.counter_signals == (
        "The event was postponed.",
    )
    assert cancelled_trip.status == "cancelled"
    assert cancelled_trip.open_loop_dispositions == (
        "closed:travel-booking-loop",
    )
