from matters.state.outcomes import CompletionCriterion, OutcomeOwner


def test_completion_criteria_false_proof_cancel_and_reopen():
    owner = OutcomeOwner()
    false = owner.decide_completion("m", (), provider_done=True)
    assert false.status == "completion_unproven"
    complete = owner.decide_completion(
        "m",
        (
            CompletionCriterion("one", True, ("e:1",)),
            CompletionCriterion("two", True, ("e:2",)),
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
