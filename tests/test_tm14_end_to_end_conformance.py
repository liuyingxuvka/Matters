from conftest import process_source


def test_synthetic_j1_j10_contracts(synthetic_rows, service):
    results = {
        scenario_id: process_source(service, row)
        for scenario_id, row in synthetic_rows.items()
    }
    assert results["J1"].terminal_status == "uncertain"
    assert results["J1"].registration.status == "source_version_created"
    assert not results["J1"].registration.source_version.content.get("attachments")

    assert results["J2"].lifecycle.state == "planned"
    assert results["J2"].lifecycle.state != "in_progress"

    assert results["J3"].lifecycle.state == "in_progress"
    assert any(event.kind == "work_recorded" for event in results["J3"].trace.events)

    assert results["J4"].outcome.status == "completed"
    assert "completed" in results["J4"].outcome.status

    assert results["J5"].terminal_status == "source_only"

    assert results["J6"].terminal_status == "uncertain"
    assert "done_then_reopened" in results["J6"].trace.conflicts
    assert results["J6"].trace.interpretation_status == "conflicted_current_best"
    assert results["J6"].blocking.scope == "full"

    assert results["J7"].terminal_status == "uncertain"
    assert (
        "one Matter with actions versus split Matters"
        in results["J7"].uncertainty_notes
    )

    assert len(results["J8"].relations) == 3
    assert all(not relation.auto_merge for relation in results["J8"].relations)
    assert all(not relation.causal for relation in results["J8"].relations)

    assert any(
        "region" in anchor.location for anchor in results["J9"].evidence
    )
    assert results["J9"].projections[0].equivalence_status == "equivalent"
    assert results["J9"].projections[0].localized_values["en"]
    assert results["J9"].projections[0].localized_values["zh-CN"]

    assert results["J10"].terminal_status == "blocked"
    assert results["J10"].coverage.status == "partial"


def test_whole_flow_retry_is_no_delta(synthetic_rows, service):
    first = process_source(service, synthetic_rows["J1"])
    second = process_source(service, synthetic_rows["J1"])
    assert first.terminal_status == "uncertain"
    assert second.terminal_status == "no_delta"
    assert service.admission.candidate_count == 1
