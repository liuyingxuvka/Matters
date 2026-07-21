from __future__ import annotations

from dataclasses import asdict
from types import SimpleNamespace

import pytest

from matters.analysis.operations import AdvisoryFinding
from matters.application.reconciliation import MatterReconciliationOwner
from matters.domain.admission import MatterAdmission
from matters.domain.context import (
    ContextSignal,
    GranularityAssessment,
    MatterPlacementCandidate,
    MatterReconciliationRequest,
    MatterRelationshipHint,
    ProjectContext,
)
from matters.presentation.browser import project_matter_only_graph
from matters.timeline.events import Event, EventRegistry


def _signal(kind: str, value: str, evidence_id: str) -> ContextSignal:
    return ContextSignal(kind, value, (evidence_id,))


def _context(*signals: ContextSignal) -> ProjectContext:
    return ProjectContext(signals=tuple(signals))


def _candidate(
    matter_id: str,
    *signals: ContextSignal,
    broad_scope: bool = False,
) -> MatterPlacementCandidate:
    return MatterPlacementCandidate(
        matter_id=matter_id,
        semantic_identity_key=matter_id,
        context=_context(*signals),
        broad_scope=broad_scope,
    )


def _request(
    *signals: ContextSignal,
    candidates: tuple[MatterPlacementCandidate, ...],
    semantic_identity_key: str,
    relationship_hints: tuple[MatterRelationshipHint, ...] = (),
) -> MatterReconciliationRequest:
    return MatterReconciliationRequest(
        source_ids=("source:incoming:v1",),
        evidence_ids=("evidence:incoming",),
        semantic_identity_key=semantic_identity_key,
        context=_context(*signals),
        candidates=candidates,
        relationship_hints=relationship_hints,
        granularity=GranularityAssessment(independently_useful_goal=True),
    )


def _seed_projection(
    service,
    matter_id: str,
    *,
    summary_en: str,
    summary_zh: str,
    source_ids: tuple[str, ...] = (),
    evidence_ids: tuple[str, ...] = (),
    state: str = "in_progress",
) -> None:
    service.store.append(
        "admission_decision",
        matter_id,
        1,
        {
            "status": "admitted",
            "matter": {
                "matter_id": matter_id,
                "source_ids": source_ids,
                "rationale": "Current semantic admission",
                "evidence_ids": evidence_ids,
                "admitted": True,
                "semantic_identity_id": f"semantic:{matter_id}",
                "object_kind": "matter",
            },
            "candidate": None,
        },
    )
    projection = service.projections.publish(
        matter_id=matter_id,
        semantic_revision=f"semantic:{matter_id}:1",
        state=state,
        rationale=summary_en,
        evidence_ids=evidence_ids,
        localized_values={
            "en": f"{matter_id} title",
            "zh-CN": f"{matter_id} 标题",
        },
        localized_rationale={"en": summary_en, "zh-CN": summary_zh},
    )
    service.store.append("projection", matter_id, 1, asdict(projection))


def _seed_source(
    service,
    *,
    suffix: str,
    label: str,
) -> tuple[str, str]:
    source_id = f"source:{suffix}"
    evidence_id = f"evidence:{suffix}"
    service.store.append(
        "source_version",
        source_id,
        1,
        {
            "source_id": source_id,
            "version": 1,
            "provider": "filesystem",
            "external_reference": {
                "provider": "filesystem",
                "external_id": f"occurrence:{suffix}",
                "object_type": "document",
            },
            "content": {"file_name": label},
            "content_hash": f"sha256:{suffix}:content",
            "metadata_hash": f"sha256:{suffix}:metadata",
            "tombstone": False,
        },
    )
    service.store.append(
        "evidence_anchor",
        evidence_id,
        1,
        {
            "evidence_id": evidence_id,
            "source_id": source_id,
            "source_version": 1,
            "location": {"field": "body"},
            "text": f"Information from {label}",
            "modality": "reported",
            "current": True,
        },
    )
    return f"{source_id}:v1", evidence_id


def test_event_revision_has_stable_logical_identity_and_exact_supersession():
    registry = EventRegistry()
    first = registry.from_understanding(
        kind="ticket_purchase",
        source_revision="source:ticket:v1",
        claimed_time="2026-06-28T08:00:00+00:00",
        record_time="2026-06-28T08:05:00+00:00",
        object_ref="matter:japan",
        evidence_ids=("evidence:ticket:v1",),
        modality="reported",
        logical_event_key="japan-trip:universal-ticket-purchase",
    )
    corrected = registry.from_understanding(
        kind="ticket_purchase",
        source_revision="source:ticket:v2",
        claimed_time="2026-06-28T09:00:00+00:00",
        record_time="2026-06-29T08:05:00+00:00",
        object_ref="matter:japan",
        evidence_ids=("evidence:ticket:v2",),
        modality="reported",
        logical_event_key="japan-trip:universal-ticket-purchase",
        supersedes_event_id=first.event_id,
    )

    assert corrected.logical_event_key == first.logical_event_key
    assert corrected.event_id != first.event_id
    assert corrected.supersedes_event_id == first.event_id
    assert [item.current_revision for item in registry._events] == [False, True]


def test_event_registry_restores_durable_supersession_and_revises_existing():
    old = Event(
        event_id="event:deadline:old",
        kind="deadline",
        modality="reported",
        claimed_time="2026-07-20T17:00:00-07:00",
        object_ref="matter:build-week",
        evidence_ids=("evidence:old",),
        logical_event_key="logical-event:legacy-old",
    )
    corrected = Event(
        event_id="event:deadline:corrected",
        kind="deadline",
        modality="reported",
        claimed_time="2026-07-21T17:00:00-07:00",
        object_ref="matter:build-week",
        evidence_ids=("evidence:corrected",),
        logical_event_key="logical-event:legacy-corrected",
    )
    registry = EventRegistry()
    registry.restore((old, corrected))

    revised = registry.revise_existing(
        event_id=corrected.event_id,
        kind="deadline",
        claimed_time=corrected.claimed_time,
        record_time="2026-07-18T15:34:06+00:00",
        actor="",
        object_ref=corrected.object_ref,
        evidence_ids=corrected.evidence_ids,
        modality="reported",
        logical_event_key="build-week:submission-deadline",
        supersedes_event_id=old.event_id,
    )

    assert revised.event_id == corrected.event_id
    assert revised.logical_event_key.startswith("logical-event:")
    assert revised.supersedes_event_id == old.event_id
    assert [item.current_revision for item in registry._events] == [False, True]


def test_service_restart_restores_durable_temporal_event_supersession(service):
    old = {
        "event_id": "event:deadline:old",
        "kind": "deadline",
        "modality": "reported",
        "claimed_time": "2026-07-20T17:00:00-07:00",
        "object_ref": "matter:build-week",
        "evidence_ids": ("evidence:old",),
        "logical_event_key": "logical-event:build-week-deadline",
        "current_revision": True,
        "supersedes_event_id": "",
    }
    corrected = {
        **old,
        "event_id": "event:deadline:corrected",
        "claimed_time": "2026-07-21T17:00:00-07:00",
        "evidence_ids": ("evidence:corrected",),
        "supersedes_event_id": old["event_id"],
    }
    service.store.append("temporal_event", old["event_id"], 1, old)
    service.store.append(
        "temporal_event",
        corrected["event_id"],
        1,
        corrected,
    )

    restarted = type(service)(
        private_root=service.config.private_root,
        repository_root=service.config.repository_root,
    )

    assert {
        event.event_id: event.current_revision
        for event in restarted.events._events
    } == {
        old["event_id"]: False,
        corrected["event_id"]: True,
    }


def test_c5_can_append_a_correction_to_an_existing_event_id(service):
    old = Event(
        event_id="event:deadline:old",
        kind="deadline",
        modality="reported",
        claimed_time="2026-07-20T17:00:00-07:00",
        object_ref="matter:build-week",
        evidence_ids=("evidence:old",),
        logical_event_key="logical-event:legacy-old",
    )
    corrected = Event(
        event_id="event:deadline:corrected",
        kind="deadline",
        modality="reported",
        claimed_time="2026-07-21T17:00:00-07:00",
        object_ref="matter:build-week",
        evidence_ids=("evidence:corrected",),
        logical_event_key="logical-event:legacy-corrected",
    )
    for event in (old, corrected):
        service.store.append(
            "temporal_event",
            event.event_id,
            1,
            asdict(event),
        )
    service.events.restore((old, corrected))
    finding = AdvisoryFinding(
        finding_id="finding:deadline-correction",
        finding_type="deadline_candidate",
        owner_model_id="C5_event_temporal_trace",
        statement="The corrected deadline is July 21 at 5 PM PT.",
        localized_statement={
            "en": "The corrected deadline is July 21 at 5 PM PT.",
            "zh-CN": "更正后的截止时间是太平洋时间 7 月 21 日下午 5 点。",
        },
        semantic_revision="source:corrected:v2",
        evidence_ids=corrected.evidence_ids,
        confidence="high",
        modality="reported",
        attributes={
            "object_ref": corrected.object_ref,
            "revision_event_id": corrected.event_id,
            "logical_event_key": "build-week:submission-deadline",
            "supersedes_event_id": old.event_id,
            "deadline": corrected.claimed_time,
        },
    )

    outcome = service.dispatcher._c5(SimpleNamespace(), finding)
    durable = service.store.current("temporal_event", corrected.event_id)

    assert outcome.owner_output_ref == (
        f"temporal_event:{corrected.event_id}"
    )
    assert durable["event_id"] == corrected.event_id
    assert durable["supersedes_event_id"] == old.event_id
    assert durable["logical_event_key"].startswith("logical-event:")
    assert len(
        service.store.history("temporal_event", corrected.event_id)
    ) == 2


def test_inferred_canonical_event_is_only_a_revisable_past_gap_fill():
    registry = EventRegistry()
    event = registry.from_understanding(
        kind="likely_trip_completed",
        source_revision="source:ticket:v1",
        object_ref="matter:japan",
        evidence_ids=("evidence:ticket",),
        modality="inferred",
        logical_event_key="japan-trip:likely-completion",
        temporal_direction="past",
        inference_purpose="historical_gap_fill",
        inference_as_of="2026-07-20T12:00:00+00:00",
        target_time="2026-06-30T12:00:00+00:00",
        revisable=True,
        contradiction_triggers=("cancellation or refund evidence",),
    )

    assert event.inference_purpose == "historical_gap_fill"
    assert event.revisable is True
    with pytest.raises(ValueError, match="future predictions"):
        registry.from_understanding(
            kind="future_boarding",
            source_revision="source:flight:v1",
            object_ref="matter:australia",
            evidence_ids=("evidence:flight",),
            modality="inferred",
            logical_event_key="australia-trip:future-boarding",
            temporal_direction="past",
            inference_purpose="historical_gap_fill",
            inference_as_of="2026-07-20T12:00:00+00:00",
            target_time="2026-09-30T12:00:00+00:00",
            revisable=True,
            contradiction_triggers=("flight cancellation",),
        )


def test_travel_intermediate_matters_are_children_not_flat_or_fact_nodes():
    travel_root = _candidate(
        "matter:travel-2026",
        _signal(
            "containment_scope",
            "personal travel in 2026",
            "evidence:root-scope",
        ),
        _signal("subject", "travel", "evidence:root-subject"),
        broad_scope=True,
    )
    owner = MatterReconciliationOwner(MatterAdmission())

    japan = owner.reconcile(
        _request(
            _signal(
                "containment_scope",
                "personal travel in 2026",
                "evidence:incoming",
            ),
            _signal("subject", "travel", "evidence:incoming"),
            candidates=(travel_root,),
            semantic_identity_key="Japan journey",
        )
    )
    australia = owner.reconcile(
        _request(
            _signal(
                "containment_scope",
                "personal travel in 2026",
                "evidence:incoming",
            ),
            _signal("subject", "travel", "evidence:incoming"),
            candidates=(travel_root,),
            semantic_identity_key="Australia journey",
        )
    )

    assert japan.status == australia.status == "admit_child"
    assert japan.parent_matter_id == australia.parent_matter_id == (
        "matter:travel-2026"
    )
    assert japan.granularity == australia.granularity == "matter"


def test_cross_domain_support_is_typed_related_not_primary_containment():
    job_search = _candidate(
        "matter:job-search",
        _signal("subject", "job search", "evidence:job-old"),
    )
    request = _request(
        _signal("subject", "job search", "evidence:incoming"),
        candidates=(job_search,),
        semantic_identity_key="Job-search software project",
        relationship_hints=(
            MatterRelationshipHint(
                target_matter_id="matter:job-search",
                relation_type="supports",
                evidence_ids=("evidence:incoming",),
            ),
        ),
    )

    decision = MatterReconciliationOwner(MatterAdmission()).reconcile(request)

    assert decision.status == "admit_related"
    assert decision.parent_matter_id == ""
    assert decision.related_matter_types == (
        ("matter:job-search", "supports"),
    )


def test_matter_only_graph_keeps_matter_relations_and_hides_fact_nodes():
    projected = project_matter_only_graph(
        {
            "root_matter_id": "matter:travel",
            "nodes": (
                {"node_id": "matter:travel", "node_type": "matter"},
                {"node_id": "matter:japan", "node_type": "matter"},
                {"node_id": "event:ticket", "node_type": "event"},
                {"node_id": "work:check-in", "node_type": "work_item"},
            ),
            "edges": (
                {
                    "edge_id": "edge:contains",
                    "source_node_id": "matter:travel",
                    "target_node_id": "matter:japan",
                    "relation_type": "contains",
                    "primary_containment": True,
                },
                {
                    "edge_id": "edge:event",
                    "source_node_id": "matter:japan",
                    "target_node_id": "event:ticket",
                    "relation_type": "has_event",
                    "primary_containment": False,
                },
                {
                    "edge_id": "edge:related",
                    "source_node_id": "matter:travel",
                    "target_node_id": "matter:japan",
                    "relation_type": "supports",
                    "primary_containment": False,
                },
            ),
        }
    )

    assert [item["node_id"] for item in projected["nodes"]] == [
        "matter:travel",
        "matter:japan",
    ]
    assert {item["edge_id"] for item in projected["edges"]} == {
        "edge:contains",
        "edge:related",
    }
    assert projected["per_node_collapse_allowed"] is False


def test_timeline_dedupes_one_logical_event_and_labels_historical_inference(
    service,
):
    matter_id = "matter:timeline-dedupe"
    evidence_ids = ("evidence:old", "evidence:new")
    _seed_projection(
        service,
        matter_id,
        summary_en="The trip has finished.",
        summary_zh="这次旅行已经结束。",
        evidence_ids=evidence_ids,
    )
    old = {
        "event_id": "event:old",
        "logical_event_key": "logical-event:trip-complete",
        "kind": "trip_completed",
        "modality": "inferred",
        "object_ref": matter_id,
        "claimed_time": "2026-06-30T12:00:00+00:00",
        "record_time": "2026-07-01T12:00:00+00:00",
        "evidence_ids": ("evidence:old",),
        "current_revision": True,
        "temporal_direction": "past",
        "inference_purpose": "historical_gap_fill",
        "revisable": True,
        "localized_sentence": {
            "en": "The trip likely finished.",
            "zh-CN": "这次旅行很可能已经结束。",
        },
    }
    current = {
        **old,
        "event_id": "event:new",
        "record_time": "2026-07-02T12:00:00+00:00",
        "evidence_ids": ("evidence:new",),
        "supersedes_event_id": "event:old",
    }
    service.store.append("temporal_event", "event:old", 1, old)
    service.store.append("temporal_event", "event:new", 1, current)

    detail = service.matter_detail(matter_id=matter_id, locale="en")

    assert len(detail["timeline"]) == 1
    row = detail["timeline"][0]
    assert row["record_time"] == "2026-07-02T12:00:00+00:00"
    assert row["basis_label"] == {
        "en": "AI historical inference",
        "zh-CN": "AI 历史推断",
    }
    assert row["has_history"] is True
    assert row["revision_count"] == 2
    assert row["conflict"] is False


def test_timeline_hides_explicitly_superseded_legacy_identity(service):
    matter_id = "matter:deadline-correction"
    _seed_projection(
        service,
        matter_id,
        summary_en="The corrected deadline is current.",
        summary_zh="修正后的截止时间为当前版本。",
        evidence_ids=("evidence:old", "evidence:new"),
    )
    service.store.append(
        "temporal_event",
        "event:legacy-deadline",
        1,
        {
            "event_id": "event:legacy-deadline",
            "kind": "deadline",
            "modality": "inferred",
            "object_ref": matter_id,
            "claimed_time": "2026-07-20T17:00:00-07:00",
            "evidence_ids": ("evidence:old",),
            "localized_sentence": {
                "en": "The earlier deadline was Monday.",
                "zh-CN": "旧截止时间为星期一。",
            },
        },
    )
    service.store.append(
        "temporal_event",
        "event:corrected-deadline",
        1,
        {
            "event_id": "event:corrected-deadline",
            "logical_event_key": "logical-event:corrected-deadline",
            "kind": "deadline",
            "modality": "reported",
            "object_ref": matter_id,
            "claimed_time": "2026-07-21T17:00:00-07:00",
            "evidence_ids": ("evidence:new",),
            "supersedes_event_id": "event:legacy-deadline",
            "localized_sentence": {
                "en": "The corrected deadline is Tuesday.",
                "zh-CN": "修正后的截止时间为星期二。",
            },
        },
    )

    detail = service.matter_detail(matter_id=matter_id, locale="en")

    assert len(detail["timeline"]) == 1
    assert detail["timeline"][0]["sentence"]["en"] == (
        "The corrected deadline is Tuesday."
    )


def test_internal_audit_summary_is_pending_and_empty_supplement_is_not_current(
    service,
):
    matter_id = "matter:human-summary"
    _seed_projection(
        service,
        matter_id,
        summary_en="The evidence shows this was included in understanding.",
        summary_zh="证据显示这件事已经纳入事项理解。",
    )
    service.store.append(
        "matter_supplemental_information",
        matter_id,
        1,
        {"matter_id": matter_id, "items": (), "status": "current"},
    )

    detail = service.matter_detail(matter_id=matter_id, locale="zh-CN")

    assert detail["matter"]["summary"] == {"en": "", "zh-CN": ""}
    assert detail["matter"]["summary_status"] == "pending"
    assert detail["ai_supplemental_information"]["status"] == "pending"


def test_lifecycle_projection_keeps_historical_inference_separate_from_state(
    service,
):
    matter_id = "matter:historical-outcome"
    _seed_projection(
        service,
        matter_id,
        summary_en="The past journey likely finished as planned.",
        summary_zh="过去的旅程很可能已按计划结束。",
        state="completed",
    )
    service.store.append(
        "outcome_decision",
        f"{matter_id}:outcome",
        1,
        {
            "matter_id": matter_id,
            "status": "completed",
            "basis_modality": "inferred",
            "basis_scope": "historical_inference",
            "evidence_ids": ("evidence:past-booking",),
        },
    )

    quick_view = service.browser.node_quick_view(matter_id, locale="en")
    current = quick_view["summary_current_state"]

    assert current["state"] == "completed"
    assert current["state_basis_modality"] == "inferred"
    assert current["state_basis_scope"] == "historical_inference"
    assert current["state_basis_label"] == {
        "en": "AI historical inference",
        "zh-CN": "AI 历史推断",
    }
    assert "future" not in str(current).casefold()


def test_people_and_typed_relations_project_without_shared_evidence(service):
    _seed_projection(
        service,
        "matter:software",
        summary_en="The software project is in progress.",
        summary_zh="这个软件项目正在进行。",
    )
    _seed_projection(
        service,
        "matter:job-search",
        summary_en="The job search is in progress.",
        summary_zh="求职正在进行。",
    )
    service.store.append(
        "person_candidate",
        "person:alex",
        1,
        {
            "person_id": "person:alex",
            "display_name": "Alex",
            "matter_id": "matter:software",
            "evidence_ids": (),
            "resolved": True,
        },
    )
    service.store.append(
        "relation_candidate",
        "relation:software-job",
        1,
        {
            "relation_id": "relation:software-job",
            "source_matter_id": "matter:software",
            "target_matter_id": "matter:job-search",
            "relation_type": "supports",
            "rationale": "The application supports job-search preparation.",
            "evidence_ids": ("evidence:relationship",),
            "freshness": "current",
        },
    )

    detail = service.matter_detail(matter_id="matter:software", locale="en")

    assert detail["people"][0]["name"] == "Alex"
    related = detail["related_matters"][0]
    assert related["matter_id"] == "matter:job-search"
    assert related["relation_types"] == ("supports",)


def test_node_quick_view_uses_only_the_selected_matter_sources(service):
    root_source, root_evidence = _seed_source(
        service,
        suffix="root",
        label="root-itinerary.txt",
    )
    child_source, child_evidence = _seed_source(
        service,
        suffix="child",
        label="japan-ticket.txt",
    )
    _seed_projection(
        service,
        "matter:travel",
        summary_en="The 2026 travel plan is in progress.",
        summary_zh="2026 年旅行计划正在进行。",
        source_ids=(root_source,),
        evidence_ids=(root_evidence,),
    )
    _seed_projection(
        service,
        "matter:japan",
        summary_en="The Japan journey has finished.",
        summary_zh="日本之旅已经结束。",
        source_ids=(child_source,),
        evidence_ids=(child_evidence,),
    )

    quick_view = service.browser.node_quick_view(
        "matter:japan",
        locale="zh-CN",
    )

    assert [item["region_id"] for item in quick_view["regions"]] == [
        "summary_current_state",
        "files_and_information",
    ]
    files = quick_view["files_and_information"]
    assert files["groups"] == ()
    assert files["total_count"] == 1
    assert files["items"][0]["label"]["en"] == "japan-ticket.txt"
    assert "root-itinerary.txt" not in str(files)
    assert quick_view["recursive_navigation_allowed"] is False


def test_temporal_event_rebase_backfills_logical_identity_without_rewording(
    service,
):
    service.store.append(
        "temporal_event",
        "event:legacy",
        1,
        {
            "event_id": "event:legacy",
            "object_ref": "matter:travel",
            "kind": "ticket_purchase",
            "actor": "traveler",
            "claimed_time": "2026-06-28T00:58:51+09:00",
            "record_time": "2026-06-28T01:02:00+09:00",
            "localized_sentence": {
                "en": "The ticket was purchased.",
                "zh-CN": "门票已经购买。",
            },
        },
    )

    result = service.rebase_temporal_event_logical_identity(limit=10)
    current = service.store.current("temporal_event", "event:legacy")

    assert result["migrated_count"] == 1
    assert current["logical_event_key"].startswith("sha256:")
    assert current["current_revision"] is True
    assert current["supersedes_event_id"] == ""
    assert current["localized_sentence"]["en"] == "The ticket was purchased."
