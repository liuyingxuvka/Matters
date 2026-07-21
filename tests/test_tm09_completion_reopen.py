from matters.application.orchestrator import MatterService
from matters.state.outcomes import CompletionCriterion, OutcomeOwner


def test_completion_criteria_false_proof_cancel_and_reopen():
    owner = OutcomeOwner()
    false = owner.decide_completion("m", (), provider_done=True)
    assert false.status == "completion_unproven"
    complete = owner.decide_completion(
        "m",
        (
            CompletionCriterion(
                "one",
                True,
                ("e:1",),
                owner_evidence_licensed=True,
            ),
            CompletionCriterion(
                "two",
                True,
                ("e:2",),
                owner_evidence_licensed=True,
            ),
        ),
    )
    assert complete.status == "completed"
    reopened = owner.reopen("m", new_obligation_id="o:2")
    assert reopened.status == "reopened"
    assert [item.status for item in owner.history("m")] == [
        "completion_unproven",
        "completed",
        "reopened",
    ]
    cancelled = owner.cancel("other", rationale="user decision", loop_dispositions=("closed:x",))
    assert cancelled.open_loop_dispositions == ("closed:x",)
    conflict = owner.record_conflict("m", rationale="contradictory termination evidence")
    assert conflict.status == "outcome_conflict"


def test_historical_inference_is_visible_but_provisional_and_revisable():
    owner = OutcomeOwner()

    inferred = owner.decide_completion(
        "japan-trip",
        (
            CompletionCriterion(
                "elapsed-entry-window",
                True,
                ("e:dated-ticket",),
                basis_modality="ai_inferred",
                temporal_direction="past",
                completion_licensed=True,
                owner_evidence_licensed=True,
                terminality="provisional",
                inference_contract_valid=True,
            ),
        ),
    )
    future = owner.decide_completion(
        "future-flight",
        (
            CompletionCriterion(
                "ticket-issued",
                True,
                ("e:future-ticket",),
                basis_modality="reported",
                temporal_direction="future",
                owner_evidence_licensed=True,
            ),
        ),
    )
    unlicensed_ai = owner.decide_completion(
        "unsupported-completion",
        (
            CompletionCriterion(
                "model-says-done",
                True,
                ("e:summary",),
                basis_modality="ai_inferred",
                temporal_direction="past",
                owner_evidence_licensed=True,
                terminality="provisional",
                inference_contract_valid=False,
            ),
        ),
    )

    assert inferred.status == "completed"
    assert inferred.basis_modality == "ai_inferred"
    assert inferred.terminality == "provisional"
    assert future.status == "completion_unproven"
    assert unlicensed_ai.status == "completion_unproven"


def test_ai_satisfied_boolean_cannot_self_license_completion_evidence():
    owner = OutcomeOwner()

    unlicensed = owner.decide_completion(
        "matter:self-asserted",
        (
            CompletionCriterion(
                "model-says-done",
                True,
                ("evidence:summary",),
                basis_modality="reported",
                temporal_direction="past",
                completion_licensed=True,
                owner_evidence_licensed=False,
                terminality="confirmed",
            ),
        ),
    )

    assert unlicensed.status == "completion_unproven"


def test_c9_matches_completion_and_cancellation_to_current_c5_events(
    tmp_path,
):
    repository = tmp_path / "repository"
    repository.mkdir()
    service = MatterService(
        repository_root=repository,
        private_root=tmp_path / "private",
    )
    assert service.store is not None
    assert service.dispatcher is not None
    matter_id = "matter:evidence-owner"
    service.store.append(
        "temporal_event",
        "event:registered",
        1,
        {
            "event_id": "event:registered",
            "kind": "registration_confirmed",
            "modality": "reported",
            "object_ref": matter_id,
            "evidence_ids": ("evidence:registration",),
            "current_revision": True,
            "temporal_direction": "past",
        },
    )
    service.store.append(
        "temporal_event",
        "event:cancelled",
        1,
        {
            "event_id": "event:cancelled",
            "kind": "event_cancelled",
            "modality": "reported",
            "object_ref": matter_id,
            "evidence_ids": ("evidence:cancellation",),
            "current_revision": True,
            "temporal_direction": "past",
        },
    )

    assert service.dispatcher._criterion_owner_evidence_licensed(
        matter_id=matter_id,
        evidence_ids=("evidence:registration",),
        basis_modality="reported",
        temporal_direction="past",
    )
    assert not service.dispatcher._criterion_owner_evidence_licensed(
        matter_id=matter_id,
        evidence_ids=("evidence:generic-summary",),
        basis_modality="reported",
        temporal_direction="past",
    )
    assert service.dispatcher._reported_termination_evidence_licensed(
        matter_id=matter_id,
        evidence_ids=("evidence:cancellation",),
    )
    assert not service.dispatcher._reported_termination_evidence_licensed(
        matter_id=matter_id,
        evidence_ids=("evidence:registration",),
    )
