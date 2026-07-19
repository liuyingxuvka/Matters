from matters.presentation.projections import ProjectionOwner


def test_bilingual_views_bind_same_state_revision_and_evidence():
    projection = ProjectionOwner().publish(
        matter_id="m",
        semantic_revision="revision:7",
        state="uncertain",
        rationale="contradictory temporal evidence",
        evidence_ids=("e:1", "e:2"),
    )
    assert projection.semantic_revision == "revision:7"
    assert projection.evidence_ids == ("e:1", "e:2")
    assert "Uncertain" in projection.localized_values["en"]
    assert "不确定" in projection.localized_values["zh-CN"]
    assert projection.locale_revisions == {
        "en": "revision:7",
        "zh-CN": "revision:7",
    }
