from conftest import process_source


def test_correction_disposes_all_declared_dependents_and_refreshes_projection(
    synthetic_rows,
    service,
):
    original = process_source(service, synthetic_rows["J3"])
    matter_id = original.admission.candidate.candidate_id
    prior_revision = original.projections[0].semantic_revision

    corrected = service.submit_matter_correction(
        matter_id=matter_id,
        rationale="user corrected the start interpretation",
        field_name="state",
        corrected_value="planned",
    )

    revision = corrected["revision"]
    dispositions = corrected["invalidation_plan"]["dispositions"]
    assert revision["prior_revision_id"] == prior_revision
    assert corrected["status"] == "auto_applied"
    assert corrected["recompute_status"] == "passed"
    assert len(dispositions) == 5
    assert {item["owner_model_id"] for item in dispositions} == {
        "C6_matter_admission",
        "C7_lifecycle_board_state",
        "C8_open_loop_waiting_blocking",
        "C9_completion_cancellation_reopen",
        "C12_projection_bilingual_ui",
    }
    projection = service.store.current("projection", matter_id)
    assert projection["semantic_revision"] == revision["revision_id"]
    assert projection["state"] == "planned"
    assert set(projection["localized_values"]) == {"en", "zh-CN"}
