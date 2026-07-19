from matters.timeline.events import EventRegistry


def test_planned_is_not_occurred_and_assignment_gap_is_visible():
    trace = EventRegistry().from_provider_payload(
        "one",
        {"scheduled_event": "2031-01-01", "assignee": "person"},
    )
    assert any(event.modality == "planned" for event in trace.events)
    assert all(event.kind != "actual_start_reported" for event in trace.events)
    assert trace.gaps


def test_done_reopen_and_blocker_preserve_conflict():
    trace = EventRegistry().from_provider_payload(
        "one",
        {
            "change_items": [
                {"field": "status", "to": "Done"},
                {"field": "status", "to": "Reopened"},
            ],
            "comments": [{"body": "Still blocked by approval."}],
        },
    )
    assert trace.interpretation_status == "conflicted_current_best"
    assert "done_then_reopened" in trace.conflicts
    assert "latest reported transition" in trace.best_interpretation
    assert len(trace.events) == 3


def test_explicit_start_and_worklog_are_actual_start_evidence():
    trace = EventRegistry().from_provider_payload(
        "one",
        {
            "worklog": [{"at": "2031-01-01"}],
            "comments": [{"body": "I started the work."}],
        },
    )
    assert {item.kind for item in trace.events} == {
        "work_recorded",
        "actual_start_reported",
    }
