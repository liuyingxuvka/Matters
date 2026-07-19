import json
from dataclasses import asdict

import pytest

from flowguard import (
    review_ui_content_visibility,
    review_ui_interaction_model,
    review_ui_journey_coverage,
    review_ui_responsiveness_contract,
    review_ui_visible_surface,
    ui_interaction_model_to_transition_coverage,
)
from flowguard_design.ui_flow_structure import (
    current_revision,
    interaction_model,
    journey_coverage,
    responsiveness_contract,
    visibility_plan,
    visible_surface,
)
from matters.presentation.localization import LocalizationGap
from matters.presentation.projections import ProjectionConflict, ProjectionOwner


def _persist_projection(
    service,
    *,
    matter_id: str,
    semantic_revision: str,
    state: str,
    en: str,
    zh_cn: str,
    evidence_ids: tuple[str, ...] = (),
) -> None:
    projection = service.projections.publish(
        matter_id=matter_id,
        semantic_revision=semantic_revision,
        state=state,
        rationale="dependency is open",
        evidence_ids=evidence_ids,
        localized_values={"en": en, "zh-CN": zh_cn},
        localized_rationale={
            "en": "dependency is open",
            "zh-CN": "依赖项仍未关闭",
        },
    )
    service.store.append(
        "projection",
        matter_id,
        service.store.next_revision("projection", matter_id),
        asdict(projection),
    )


def test_same_revision_bilingual_projection_and_conflict_blocking():
    owner = ProjectionOwner()
    projection = owner.publish(
        matter_id="m",
        semantic_revision="r1",
        state="blocked",
        rationale="dependency is open",
        evidence_ids=("e:1",),
    )
    assert projection.equivalence_status == "equivalent"
    assert projection.semantic_revision == "r1"
    assert projection.default_locale == "en"
    assert projection.available_locales == ("en", "zh-CN")
    assert set(projection.localized_values) == {"en", "zh-CN"}
    assert "Blocked" in projection.localized_values["en"]
    assert "受阻" in projection.localized_values["zh-CN"]
    assert set(projection.locale_revisions.values()) == {"r1"}
    with pytest.raises(ProjectionConflict):
        owner.publish(
            matter_id="m",
            semantic_revision="r1",
            state="blocked",
            rationale="x",
            locale_semantics={"en": "blocked", "zh-CN": "waiting"},
        )
    with pytest.raises(ProjectionConflict):
        owner.publish_pair(
            matter_id="m",
            english_revision="r1",
            zh_cn_revision="r0",
            state="blocked",
            rationale="x",
        )
    with pytest.raises(LocalizationGap):
        owner.publish(
            matter_id="m",
            semantic_revision="r1",
            state="blocked",
            rationale="dependency is open",
            localized_rationale={"en": "dependency is open"},
        )
    with pytest.raises(PermissionError):
        owner.infer_canonical_state("blocked")
    assert owner.submit_correction(lambda **row: row, target="state") == {
        "target": "state"
    }


def test_native_ui_flow_structure_owns_visibility_journeys_and_transitions():
    revision = current_revision()
    model = interaction_model()
    visibility = visibility_plan(revision)
    surface = visible_surface()
    journey = journey_coverage()

    reports = (
        review_ui_content_visibility(
            visibility,
            interaction_model=model,
            visible_surface=surface,
        ),
        review_ui_interaction_model(
            model,
            content_visibility_plan=visibility,
        ),
        review_ui_visible_surface(
            surface,
            interaction_model=model,
            content_visibility_plan=visibility,
        ),
        review_ui_journey_coverage(journey, interaction_model=model),
        review_ui_responsiveness_contract(
            responsiveness_contract(),
            interaction_model=model,
        ),
    )
    matrix = ui_interaction_model_to_transition_coverage(model)

    assert all(report.ok for report in reports)
    assert matrix.required_cell_ids()


def test_large_object_catalog_is_bounded_stable_and_bilingual(service):
    states = ("planned", "in_progress", "completed")
    for index in range(121):
        _persist_projection(
            service,
            matter_id=f"matter:{index:03d}",
            semantic_revision=f"semantic:{index:03d}",
            state=states[index % len(states)],
            en=f"Matter {index:03d}\nCurrent English summary",
            zh_cn=f"事项 {index:03d}\n当前中文摘要",
        )

    first = service.object_catalog_page(locale="en", offset=0, limit=50)
    second = service.object_catalog_page(locale="en", offset=50, limit=50)
    final = service.object_catalog_page(locale="zh-CN", offset=100, limit=50)
    repeated = service.object_catalog_page(locale="en", offset=50, limit=50)

    assert first["total_count"] == 121
    assert first["catalog_revision"] == second["catalog_revision"]
    assert first["catalog_revision"] == final["catalog_revision"]
    assert len(first["items"]) == 50
    assert first["next_offset"] == 50
    assert len(second["items"]) == 50
    assert second["next_offset"] == 100
    assert len(final["items"]) == 21
    assert final["next_offset"] is None
    assert repeated["items"] == second["items"]
    assert set(first["items"][0]["title"]) == {"en", "zh-CN"}
    assert len(json.dumps(first)) < 1_000_000


def test_object_browser_search_filter_and_locale_are_projection_only(service):
    _persist_projection(
        service,
        matter_id="matter:planned",
        semantic_revision="semantic:planned",
        state="planned",
        en="Quarterly research plan\nA bounded English summary",
        zh_cn="季度研究计划\n一段有边界的中文摘要",
    )
    _persist_projection(
        service,
        matter_id="matter:active",
        semantic_revision="semantic:active",
        state="in_progress",
        en="Adapter implementation\nWork is under way",
        zh_cn="适配器实现\n工作正在进行",
    )

    english = service.object_browser_projection(
        locale="en",
        query="research",
        status="planned",
    )
    chinese = service.object_browser_projection(
        locale="zh-CN",
        query="适配器",
        status="in_progress",
    )

    assert english["surface"] == "object_browser"
    assert english["default_locale"] == "en"
    assert english["catalog"]["total_count"] == 1
    assert english["catalog"]["items"][0]["matter_id"] == "matter:planned"
    assert chinese["selected_locale"] == "zh-CN"
    assert chinese["catalog"]["total_count"] == 1
    assert chinese["catalog"]["items"][0]["matter_id"] == "matter:active"
    assert service.store.current("projection", "matter:active")["state"] == "in_progress"


def test_detail_keeps_claimed_record_time_modality_and_conflict(service):
    evidence_id = "evidence:timeline:1"
    matter_id = "matter:timeline"
    _persist_projection(
        service,
        matter_id=matter_id,
        semantic_revision="semantic:timeline",
        state="uncertain",
        en="Timeline conflict\nLatest transition is the current best interpretation",
        zh_cn="时间线冲突\n最新转换是当前最佳解释",
        evidence_ids=(evidence_id,),
    )
    service.store.append(
        "temporal_event",
        "event:timeline:1",
        1,
        {
            "event_id": "event:timeline:1",
            "kind": "milestone",
            "object_ref": matter_id,
            "claimed_time": "2031-03-04T10:00:00Z",
            "record_time": "2031-03-04T12:00:00Z",
            "modality": "reported",
            "confidence": 0.75,
            "conflict": True,
            "evidence_ids": (evidence_id,),
        },
    )

    detail = service.matter_detail(matter_id=matter_id, locale="zh-CN")
    event = detail["timeline"][0]

    assert event["sentence"]["en"]
    assert event["sentence"]["zh-CN"]
    assert event["claimed_time"] == "2031-03-04T10:00:00Z"
    assert event["record_time"] == "2031-03-04T12:00:00Z"
    assert event["modality"] == "reported"
    assert event["confidence"] == 0.75
    assert event["conflict"] is True


def test_evidence_is_private_on_demand_and_uses_an_opaque_reference(service):
    matter_id = "matter:evidence"
    evidence_id = "private-evidence:opaque-1"
    _persist_projection(
        service,
        matter_id=matter_id,
        semantic_revision="semantic:evidence",
        state="uncertain",
        en="Private evidence\nEvidence is available on demand",
        zh_cn="私有证据\n证据可按需查看",
        evidence_ids=(evidence_id,),
    )
    service.store.append(
        "evidence_anchor",
        evidence_id,
        1,
        {
            "evidence_id": evidence_id,
            "text": "A real private excerpt kept outside the repository.",
            "modality": "reported",
            "location": {"page": 2, "region": [10, 20, 300, 180]},
            "current": True,
        },
    )

    catalog = service.object_catalog_page(locale="en")
    evidence = service.matter_evidence(matter_id=matter_id)
    item = evidence["items"][0]

    assert "excerpt" not in json.dumps(catalog)
    assert item["excerpt"] == "A real private excerpt kept outside the repository."
    assert item["location"] == {"page": 2, "region": [10, 20, 300, 180]}
    assert evidence_id not in json.dumps(item)
