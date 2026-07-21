from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json

import pytest

from matters.api.http.app import create_application
from matters.application.coverage_ledger import STAGE_ORDER
from matters.application.orchestrator import MatterService
from matters.domain.admission import AdmissionPacket, MatterAdmission
from matters.domain.activity import MaterialClue
from matters.domain.hierarchy import (
    HierarchyMemberDisposition,
    MatterWorkItem,
)
from matters.domain.matters import Matter


def _service(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    return MatterService(private_root=home, repository_root=repo)


def _seed_matter(
    service,
    matter_id,
    title,
    *,
    state="planned",
    source_id=None,
    outcome_status="completion_unproven",
):
    source_id = source_id or f"source:{matter_id}"
    matter = Matter(
        matter_id=matter_id,
        source_ids=(source_id,),
        rationale=f"{title} is independently trackable",
        evidence_ids=(f"evidence:{matter_id}",),
        semantic_identity_id=f"semantic:{matter_id}",
    )
    service.store.append(
        "admission_decision",
        matter_id,
        1,
        {
            "status": "admitted",
            "rationale": matter.rationale,
            "candidate": None,
            "matter": asdict(matter),
        },
    )
    service.store.append(
        "projection",
        matter_id,
        1,
        {
            "matter_id": matter_id,
            "semantic_revision": f"semantic:{matter_id}:1",
            "state": state,
            "evidence_ids": matter.evidence_ids,
            "localized_values": {
                "en": title,
                "zh-CN": f"{title}（中文）",
            },
            "localized_rationale": {
                "en": f"Current status for {title}",
                "zh-CN": f"{title} 的当前状态",
            },
            "locale_revisions": {
                "en": f"semantic:{matter_id}:1",
                "zh-CN": f"semantic:{matter_id}:1",
            },
            "locales": ("en", "zh-CN"),
            "equivalence_status": "equivalent",
        },
    )
    service.store.append(
        "lifecycle_decision",
        f"{matter_id}:lifecycle",
        1,
        {
            "state": state,
            "rationale": f"{state} evidence",
            "evidence_ids": matter.evidence_ids,
        },
    )
    service.store.append(
        "outcome_decision",
        f"{matter_id}:outcome",
        1,
        {
            "status": outcome_status,
            "rationale": outcome_status,
            "criterion_ids": (),
            "revision": 1,
            "open_loop_dispositions": (),
        },
    )


def _request(app, path, query=""):
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    body = b"".join(
        app(
            {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": path,
                "QUERY_STRING": query,
                "CONTENT_LENGTH": "0",
                "wsgi.input": BytesIO(),
            },
            start_response,
        )
    )
    return captured["status"], json.loads(body)


def _seed_noncanonical_hierarchy_projection(
    service,
    matter_id,
    *,
    revision=1,
):
    audit = {
        "matter_id": matter_id,
        "revision": revision,
        "status": "current",
        "change_ref": f"legacy:{matter_id}",
        "stages": {
            "hierarchy_decision": "current",
            "containment_current": "current",
            "child_state_current": "current",
            "ancestor_rollup_current": "current",
            "hierarchy_projection_current": "current",
            "ui_reachable": "current",
        },
    }
    service.store.append(
        "matter_hierarchy_summary",
        matter_id,
        revision,
        {
            "matter_id": matter_id,
            "revision": revision,
            "child_count": 0,
        },
    )
    service.store.append(
        "matter_hierarchy_projection",
        matter_id,
        revision,
        {
            "matter_id": matter_id,
            "revision": revision,
            "path": (matter_id,),
            "freshness": "current",
        },
    )
    service.store.append(
        "matter_hierarchy_audit",
        matter_id,
        revision,
        audit,
    )


def test_parent_people_include_named_contacts_from_descendant_matters(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_matter(service, "matter:subscriptions", "Subscriptions")
    _seed_matter(service, "matter:vpn-refund", "VPN refund")
    service.hierarchy.attach_child(
        parent_matter_id="matter:subscriptions",
        child_matter_id="matter:vpn-refund",
        role="optional",
        confidence="high",
        rationale="The refund is one subscription workstream.",
        evidence_ids=("evidence:matter:vpn-refund",),
    )
    service.store.append(
        "person_candidate",
        "person:jenna",
        1,
        {
            "person_id": "person:jenna",
            "display_name": "Jenna",
            "matter_id": "matter:vpn-refund",
            "matter_ids": ("matter:vpn-refund",),
            "role": "customer_support_contact",
            "evidence_ids": ("evidence:jenna",),
            "resolved": False,
        },
    )

    child = service.matter_detail(
        matter_id="matter:vpn-refund",
        locale="en",
    )
    parent = service.matter_detail(
        matter_id="matter:subscriptions",
        locale="en",
    )

    assert [item["name"] for item in child["people"]] == ["Jenna"]
    assert [item["name"] for item in parent["people"]] == ["Jenna"]
    assert child["people"][0]["role"] == "customer_support_contact"
    assert child["people"][0]["role_label"] == {
        "en": "Customer support contact",
        "zh-CN": "客户支持联系人",
    }
    assert parent["people"][0]["resolved"] is False


def test_matter_identity_is_stable_when_source_membership_changes():
    owner = MatterAdmission()
    first = owner.decide(
        AdmissionPacket(
            source_ids=("source:a",),
            evidence_ids=("evidence:a",),
            explicit_goal_or_obligation=True,
            semantic_identity_key="Find a new job",
        )
    ).matter
    second = owner.decide(
        AdmissionPacket(
            source_ids=("source:b", "source:a"),
            evidence_ids=("evidence:b",),
            explicit_goal_or_obligation=True,
            semantic_identity_key="  FIND   A NEW JOB ",
        )
    ).matter

    assert first is not None and second is not None
    assert second.matter_id == first.matter_id
    assert second.semantic_identity_id == first.semantic_identity_id
    assert second.source_ids == ("source:a", "source:b")


def test_compose_parent_matter_attaches_children_and_bubbles_latest_activity(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_matter(service, "matter:child-a", "Child A")
    _seed_matter(service, "matter:child-b", "Child B")
    service.activity.record(
        MaterialClue(
            clue_id="clue:child-a",
            matter_id="matter:child-a",
            clue_kind="progress",
            user_world_at="2026-07-18T10:00:00+00:00",
            disposition="material",
            rationale="Child A progressed",
            localized_summary={
                "en": "Child A progressed",
                "zh-CN": "子事项 A 有了进展",
            },
            semantic_revision="semantic:child-a:1",
            evidence_ids=("evidence:matter:child-a",),
        )
    )
    service.activity.record(
        MaterialClue(
            clue_id="clue:child-b",
            matter_id="matter:child-b",
            clue_kind="progress",
            user_world_at="2026-07-19T10:00:00+00:00",
            disposition="material",
            rationale="Child B progressed",
            localized_summary={
                "en": "Child B progressed",
                "zh-CN": "子事项 B 有了进展",
            },
            semantic_revision="semantic:child-b:1",
            evidence_ids=("evidence:matter:child-b",),
        )
    )

    composed = service.compose_parent_matter(
        semantic_identity_key="Parent project",
        localized_title={
            "en": "Parent project",
            "zh-CN": "父项目",
        },
        localized_summary={
            "en": "Two current workstreams form one project.",
            "zh-CN": "两个当前工作流组成同一个项目。",
        },
        state="in_progress",
        topic_type="software project",
        localized_topic_type={
            "en": "Software project",
            "zh-CN": "软件项目",
        },
        attachments=(
            {
                "child_matter_id": "matter:child-a",
                "role": "required",
                "confidence": "high",
                "rationale": "Child A is one project workstream.",
                "evidence_ids": ("evidence:matter:child-a",),
            },
            {
                "child_matter_id": "matter:child-b",
                "role": "required",
                "confidence": "high",
                "rationale": "Child B is one project workstream.",
                "evidence_ids": ("evidence:matter:child-b",),
            },
        ),
        rationale="Both children are independent workstreams of one project.",
    )

    parent_id = composed["matter_id"]
    children = service.matter_children(matter_id=parent_id)
    activity = service.store.current("matter_activity", parent_id)
    assert children["total_count"] == 2
    assert {
        item["matter_id"] for item in children["items"]
    } == {"matter:child-a", "matter:child-b"}
    assert activity["source_matter_id"] == "matter:child-b"
    assert (
        activity["latest_meaningful_clue_at"]
        == "2026-07-19T10:00:00+00:00"
    )
    assert activity["ancestor_propagated"] is True
    assert composed["hero_status"] == "generation_pending_placeholder"
    parent_hero = service.heroes.current(parent_id)
    assert parent_hero is not None
    assert parent_hero.brief_fingerprint.startswith("sha256:")
    assert parent_hero.failure_kind == ""
    supplemental = service.store.current(
        "matter_supplemental_information",
        parent_id,
    )
    assert supplemental is not None
    assert supplemental["items"] == []
    assert supplemental["status"] == "pending"
    parent_coverage = service.store.current("object_coverage", parent_id)
    assert parent_coverage is not None
    assert (
        parent_coverage["stages"]["supplemental_information"]["status"]
        == "pending"
    )
    assert service.hierarchy.parent_edge(
        "matter:child-a",
        current_only=True,
    ).parent_matter_id == parent_id


def test_parent_summary_refresh_preserves_title_activity_state_and_hero(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_matter(service, "matter:child-a", "Child A")
    _seed_matter(service, "matter:child-b", "Child B")
    service.activity.record(
        MaterialClue(
            clue_id="clue:child-b",
            matter_id="matter:child-b",
            clue_kind="progress",
            user_world_at="2026-07-19T10:00:00+00:00",
            disposition="material",
            rationale="Child B progressed",
            localized_summary={
                "en": "Child B progressed",
                "zh-CN": "子事项 B 有了进展",
            },
            semantic_revision="semantic:child-b:1",
            evidence_ids=("evidence:matter:child-b",),
        )
    )
    composed = service.compose_parent_matter(
        semantic_identity_key="Parent overview refresh",
        localized_title={
            "en": "Parent project",
            "zh-CN": "父项目",
        },
        localized_summary={
            "en": "Initial child-specific summary.",
            "zh-CN": "最初的子事项摘要。",
        },
        state="in_progress",
        topic_type="software project",
        localized_topic_type={
            "en": "Software project",
            "zh-CN": "软件项目",
        },
        attachments=(
            {
                "child_matter_id": "matter:child-a",
                "role": "required",
                "confidence": "high",
                "rationale": "Child A belongs to the project.",
                "evidence_ids": ("evidence:matter:child-a",),
            },
            {
                "child_matter_id": "matter:child-b",
                "role": "required",
                "confidence": "high",
                "rationale": "Child B belongs to the project.",
                "evidence_ids": ("evidence:matter:child-b",),
            },
        ),
        rationale="Both children form one project.",
    )
    parent_id = composed["matter_id"]
    before_projection = service.store.current("projection", parent_id)
    before_activity = service.store.current("matter_activity", parent_id)
    before_hero = service.store.current("generated_hero_record", parent_id)
    child_projection = service.store.current("projection", "matter:child-a")
    child_projection = {
        **child_projection,
        "evidence_ids": tuple(
            (
                *child_projection["evidence_ids"],
                "evidence:child-a:new-material-clue",
            )
        ),
    }
    service.store.append(
        "projection",
        "matter:child-a",
        service.store.next_revision("projection", "matter:child-a"),
        child_projection,
    )
    selected_evidence = tuple(
        (
            *before_projection["evidence_ids"],
            "evidence:child-a:new-material-clue",
        )
    )

    refreshed = service.refresh_parent_matter_summary(
        matter_id=parent_id,
        localized_summary={
            "en": "Child A and Child B are two active workstreams in one project.",
            "zh-CN": "子事项 A 与子事项 B 是同一项目中的两个当前工作流。",
        },
        evidence_ids=selected_evidence,
    )
    after_projection = service.store.current("projection", parent_id)

    assert refreshed["updated"] is True
    assert after_projection["localized_values"] == (
        before_projection["localized_values"]
    )
    assert after_projection["state"] == before_projection["state"]
    assert after_projection["localized_rationale"]["en"].startswith(
        "Child A and Child B"
    )
    assert service.store.current("matter_activity", parent_id) == before_activity
    assert service.store.current("generated_hero_record", parent_id) == before_hero
    assert (
        service.refresh_parent_matter_summary(
            matter_id=parent_id,
            localized_summary=dict(after_projection["localized_rationale"]),
            evidence_ids=tuple(after_projection["evidence_ids"]),
        )["updated"]
        is False
    )


def test_parent_composition_rolls_back_all_parent_rows_on_attach_failure(
    tmp_path,
    monkeypatch,
):
    service = _service(tmp_path)
    _seed_matter(service, "matter:child-a", "Child A")
    _seed_matter(service, "matter:child-b", "Child B")
    monkeypatch.setattr(
        service.hierarchy,
        "attach_children_batch",
        lambda **_kwargs: (_ for _ in ()).throw(
            RuntimeError("simulated attachment failure")
        ),
    )

    with pytest.raises(RuntimeError, match="simulated attachment failure"):
        service.compose_parent_matter(
            semantic_identity_key="Atomic parent project",
            localized_title={
                "en": "Atomic parent project",
                "zh-CN": "原子父项目",
            },
            localized_summary={
                "en": "Two workstreams form one project.",
                "zh-CN": "两个工作流组成一个项目。",
            },
            state="in_progress",
            topic_type="software project",
            localized_topic_type={
                "en": "Software project",
                "zh-CN": "软件项目",
            },
            attachments=(
                {
                    "child_matter_id": "matter:child-a",
                    "role": "required",
                    "confidence": "high",
                    "rationale": "Child A belongs to the project.",
                    "evidence_ids": ("evidence:matter:child-a",),
                },
                {
                    "child_matter_id": "matter:child-b",
                    "role": "required",
                    "confidence": "high",
                    "rationale": "Child B belongs to the project.",
                    "evidence_ids": ("evidence:matter:child-b",),
                },
            ),
            rationale="Both children are required.",
        )

    admissions = tuple(service.store.iter_current("admission_decision"))
    assert {
        item["matter"]["matter_id"]
        for item in admissions
        if item.get("matter")
    } == {"matter:child-a", "matter:child-b"}
    assert service.object_catalog_page(root_only=True)["total_count"] == 2


def test_same_matter_merge_moves_members_and_hides_duplicate_projection(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_matter(
        service,
        "matter:duplicate",
        "Duplicate",
        source_id="source:duplicate",
    )
    _seed_matter(
        service,
        "matter:canonical",
        "Canonical",
        source_id="source:canonical",
    )

    merged = service.merge_same_matter(
        source_matter_id="matter:duplicate",
        target_matter_id="matter:canonical",
        rationale="Both cards describe the same independently useful goal.",
        evidence_ids=(
            "evidence:matter:duplicate",
            "evidence:matter:canonical",
        ),
    )

    duplicate = service.store.current(
        "admission_decision",
        "matter:duplicate",
    )
    canonical = service.store.current(
        "admission_decision",
        "matter:canonical",
    )
    catalog = service.object_catalog_page(locale="en", root_only=True)
    assert duplicate["status"] == "merged"
    assert duplicate["canonical_matter_id"] == "matter:canonical"
    assert set(canonical["matter"]["source_ids"]) == {
        "source:duplicate",
        "source:canonical",
    }
    assert {
        item["matter_id"] for item in catalog["items"]
    } == {"matter:canonical"}
    assert merged["disposition_count"] == 2
    retry = service.merge_same_matter(
        source_matter_id="matter:duplicate",
        target_matter_id="matter:canonical",
        rationale="Both cards describe the same independently useful goal.",
        evidence_ids=(
            "evidence:matter:duplicate",
            "evidence:matter:canonical",
        ),
    )
    assert retry["idempotent"] is True


def test_candidate_append_materializes_work_item_and_hides_candidate(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_matter(service, "matter:canonical", "Canonical")
    candidate_id = "candidate:step"
    service.store.append(
        "admission_decision",
        candidate_id,
        1,
        {
            "status": "uncertain",
            "rationale": "This may be a bounded step.",
            "matter": None,
            "candidate": {
                "candidate_id": candidate_id,
                "source_ids": ("source:step",),
                "rationale": "This may be a bounded step.",
                "evidence_ids": ("evidence:step",),
                "semantic_identity_id": "semantic:step",
            },
        },
    )
    service.store.append(
        "projection",
        candidate_id,
        1,
        {
            "matter_id": candidate_id,
            "semantic_revision": "semantic:step:1",
            "state": "planned",
            "evidence_ids": ("evidence:step",),
            "localized_values": {
                "en": "Review the next step",
                "zh-CN": "检查下一步",
            },
            "localized_rationale": {
                "en": "This is one bounded action.",
                "zh-CN": "这是一个有限动作。",
            },
            "locale_revisions": {
                "en": "semantic:step:1",
                "zh-CN": "semantic:step:1",
            },
            "available_locales": ("en", "zh-CN"),
            "default_locale": "en",
            "equivalence_status": "equivalent",
        },
    )

    appended = service.append_candidate_to_matter(
        candidate_id=candidate_id,
        target_matter_id="matter:canonical",
        materialization="work_item",
        rationale="The candidate is one bounded action of the canonical Matter.",
        evidence_ids=("evidence:step",),
    )

    candidate = service.store.current("admission_decision", candidate_id)
    catalog = service.object_catalog_page(locale="en", root_only=True)
    work_items = service.matter_work_items(matter_id="matter:canonical")
    assert candidate["status"] == "appended"
    assert candidate["canonical_matter_id"] == "matter:canonical"
    assert {
        item["matter_id"] for item in catalog["items"]
    } == {"matter:canonical"}
    assert work_items["total_count"] == 1
    assert work_items["items"][0]["localized_title"]["en"] == (
        "Review the next step"
    )
    assert appended["materialization"] == "work_item"
    retry = service.append_candidate_to_matter(
        candidate_id=candidate_id,
        target_matter_id="matter:canonical",
        materialization="work_item",
        rationale="The candidate is one bounded action of the canonical Matter.",
        evidence_ids=("evidence:step",),
    )
    assert retry["idempotent"] is True


def test_same_matter_merge_rolls_back_if_coverage_rewrite_fails(
    tmp_path,
    monkeypatch,
):
    service = _service(tmp_path)
    _seed_matter(service, "matter:duplicate", "Duplicate")
    _seed_matter(service, "matter:canonical", "Canonical")
    monkeypatch.setattr(
        service.coverage_ledger,
        "replace_matter_reference",
        lambda **_kwargs: (_ for _ in ()).throw(
            RuntimeError("simulated coverage failure")
        ),
    )

    with pytest.raises(RuntimeError, match="simulated coverage failure"):
        service.merge_same_matter(
            source_matter_id="matter:duplicate",
            target_matter_id="matter:canonical",
            rationale="Both cards are the same Matter.",
            evidence_ids=(
                "evidence:matter:duplicate",
                "evidence:matter:canonical",
            ),
        )

    duplicate = service.store.current(
        "admission_decision",
        "matter:duplicate",
    )
    assert duplicate["status"] == "admitted"
    assert service.store.current(
        "matter_canonicalization",
        "matter:duplicate",
    ) is None


def test_candidate_without_trackable_goal_retires_to_source_only(tmp_path):
    service = _service(tmp_path)
    candidate_id = "candidate:no-goal"
    service.store.append(
        "admission_decision",
        candidate_id,
        1,
        {
            "status": "uncertain",
            "rationale": "The source may be useful.",
            "matter": None,
            "candidate": {
                "candidate_id": candidate_id,
                "source_ids": ("source:no-goal",),
                "rationale": "The source may be useful.",
                "evidence_ids": ("evidence:no-goal",),
                "semantic_identity_id": "semantic:no-goal",
            },
        },
    )
    service.store.append(
        "projection",
        candidate_id,
        1,
        {
            "matter_id": candidate_id,
            "semantic_revision": "semantic:no-goal:1",
            "state": "uncertain",
            "evidence_ids": ("evidence:no-goal",),
            "localized_values": {
                "en": "State: uncertain",
                "zh-CN": "状态：不确定",
            },
            "localized_rationale": {
                "en": "No trackable goal is established.",
                "zh-CN": "尚未建立可跟踪目标。",
            },
            "locale_revisions": {
                "en": "semantic:no-goal:1",
                "zh-CN": "semantic:no-goal:1",
            },
            "available_locales": ("en", "zh-CN"),
            "default_locale": "en",
            "equivalence_status": "equivalent",
        },
    )

    result = service.retire_candidate_to_source_only(
        candidate_id=candidate_id,
        rationale="No independent goal, obligation, or outcome is evidenced.",
        evidence_ids=("evidence:no-goal",),
    )

    decision = service.store.current("admission_decision", candidate_id)
    catalog = service.object_catalog_page(locale="en", root_only=True)
    canonicalization = service.store.current(
        "matter_canonicalization",
        candidate_id,
    )
    assert result["evidence_preserved"] is True
    assert decision["status"] == "source_only"
    assert catalog["items"] == ()
    assert canonicalization["disposition"] == "retired_to_source_only"


def test_hierarchy_rejects_self_cycle_and_unintentional_second_parent(tmp_path):
    service = _service(tmp_path)
    for matter_id in ("matter:root-a", "matter:root-b", "matter:child"):
        _seed_matter(service, matter_id, matter_id)

    service.attach_matter_child(
        parent_matter_id="matter:root-a",
        child_matter_id="matter:child",
        role="required",
        confidence="bounded",
        rationale="child has an independent goal inside root A",
        evidence_ids=("evidence:edge-a",),
    )

    with pytest.raises(ValueError, match="explicit reparent"):
        service.attach_matter_child(
            parent_matter_id="matter:root-b",
            child_matter_id="matter:child",
            role="optional",
            confidence="bounded",
            rationale="a second parent is not implicit",
            evidence_ids=("evidence:edge-b",),
        )
    with pytest.raises(ValueError, match="own parent"):
        service.attach_matter_child(
            parent_matter_id="matter:child",
            child_matter_id="matter:child",
            role="required",
            confidence="bounded",
            rationale="invalid self edge",
            evidence_ids=("evidence:self",),
        )
    with pytest.raises(ValueError, match="cycle"):
        service.attach_matter_child(
            parent_matter_id="matter:child",
            child_matter_id="matter:root-a",
            role="required",
            confidence="bounded",
            rationale="invalid ancestor cycle",
            evidence_ids=("evidence:cycle",),
        )


def test_reparent_invalidates_old_and_new_ancestor_chains(tmp_path):
    service = _service(tmp_path)
    for matter_id in ("matter:old", "matter:new", "matter:child"):
        _seed_matter(service, matter_id, matter_id)
    service.attach_matter_child(
        parent_matter_id="matter:old",
        child_matter_id="matter:child",
        role="required",
        confidence="bounded",
        rationale="initial evidence-backed parent",
        evidence_ids=("evidence:old",),
    )

    revision = service.reparent_matter_child(
        child_matter_id="matter:child",
        expected_parent_matter_id="matter:old",
        new_parent_matter_id="matter:new",
        role="critical",
        confidence="bounded",
        rationale="new evidence changes the primary boundary",
        evidence_ids=("evidence:new",),
    )

    assert set(revision["invalidated_matter_ids"]) == {
        "matter:old",
        "matter:new",
        "matter:child",
    }
    edge = service.store.hierarchy_parent_edge(
        "matter:child",
        current_only=True,
    )
    assert edge["parent_matter_id"] == "matter:new"
    assert edge["role"] == "critical"
    old_history = service.store.history(
        "matter_containment_edge",
        service.hierarchy._edge_id("matter:old", "matter:child"),
    )
    assert old_history[-1]["active"] is False
    for matter_id in ("matter:old", "matter:new", "matter:child"):
        history = service.store.history("matter_hierarchy_audit", matter_id)
        assert any(row["status"] == "stale" for row in history)
        assert set(history[-1]["stages"]) == {
            "hierarchy_decision",
            "containment_current",
            "child_state_current",
            "ancestor_rollup_current",
            "hierarchy_projection_current",
            "ui_reachable",
        }


def test_parent_summary_does_not_mechanically_copy_child_state(tmp_path):
    service = _service(tmp_path)
    _seed_matter(
        service,
        "matter:trip",
        "Trip",
        state="planned",
        outcome_status="completed",
    )
    _seed_matter(
        service,
        "matter:flight",
        "Flight",
        state="completed",
        outcome_status="completion_unproven",
    )
    _seed_matter(
        service,
        "matter:hotel",
        "Hotel preference",
        state="blocked",
        outcome_status="completion_unproven",
    )
    service.attach_matter_child(
        parent_matter_id="matter:trip",
        child_matter_id="matter:flight",
        role="required",
        confidence="bounded",
        rationale="flight is a required component",
        evidence_ids=("evidence:flight-edge",),
    )
    service.attach_matter_child(
        parent_matter_id="matter:trip",
        child_matter_id="matter:hotel",
        role="optional",
        confidence="bounded",
        rationale="hotel preference is optional",
        evidence_ids=("evidence:hotel-edge",),
    )

    detail = service.matter_detail(matter_id="matter:trip")
    assert detail["matter"]["state"] == "planned"
    assert detail["children_summary"]["required_incomplete_count"] == 1
    assert detail["children_summary"]["critical_attention_count"] == 0
    assert detail["children_summary"]["completion_coherent"] is False
    assert "completion_barrier_ids" not in detail["children_summary"]
    private_summary = service.store.current(
        "matter_hierarchy_summary",
        "matter:trip",
    )
    assert "matter:hotel" not in private_summary["completion_barrier_ids"]

    service.store.append(
        "outcome_decision",
        "matter:flight:outcome",
        2,
        {
            "status": "completed",
            "rationale": "flight criteria are complete",
            "criterion_ids": ("ticket",),
            "revision": 2,
            "open_loop_dispositions": (),
        },
    )
    service.hierarchy.mark_dependency_changed(
        "matter:flight",
        change_ref="outcome:matter:flight:2",
        refresh=True,
    )
    refreshed = service.matter_detail(matter_id="matter:trip")
    assert refreshed["children_summary"]["completion_coherent"] is True
    assert refreshed["matter"]["state"] == "planned"


def test_root_catalog_child_page_breadcrumb_work_items_and_http(tmp_path):
    service = _service(tmp_path)
    _seed_matter(service, "matter:jobs", "Job search", state="in_progress")
    _seed_matter(service, "matter:company-a", "Company A", state="planned")
    service.attach_matter_child(
        parent_matter_id="matter:jobs",
        child_matter_id="matter:company-a",
        role="required",
        confidence="bounded",
        rationale="the application has its own state and outcome",
        evidence_ids=("evidence:application",),
    )
    service.hierarchy.save_work_item(
        MatterWorkItem(
            item_id="work-item:submit-cv",
            matter_id="matter:company-a",
            kind="application_step",
            status="completed",
            localized_title={
                "en": "Submit CV",
                "zh-CN": "提交简历",
            },
            localized_result={
                "en": "CV submitted",
                "zh-CN": "简历已提交",
            },
            evidence_ids=("evidence:cv",),
            actual_end="2026-07-19T09:00:00+00:00",
            required_for_parent=True,
        )
    )

    catalog = service.object_catalog_page()
    assert [item["matter_id"] for item in catalog["items"]] == ["matter:jobs"]
    assert catalog["facets"]["hierarchy"] == {"root": 1, "nested": 1}
    search = service.object_catalog_page(
        locale="zh-CN",
        query="Company A",
        root_only=False,
    )
    assert [item["matter_id"] for item in search["items"]] == [
        "matter:company-a"
    ]
    assert search["items"][0]["search_result_kind"] == "child"
    assert [
        item["title"]["en"]
        for item in search["items"][0]["hierarchy_path"]
    ] == ["Job search", "Company A"]
    assert [
        item["title"]["zh-CN"]
        for item in search["items"][0]["hierarchy_path"]
    ] == ["Job search（中文）", "Company A（中文）"]
    child_page = service.matter_children(matter_id="matter:jobs")
    assert child_page["total_count"] == 1
    assert child_page["items"][0]["matter_id"] == "matter:company-a"
    assert child_page["items"][0]["role"] == "required"
    detail = service.matter_detail(matter_id="matter:company-a")
    assert [item["matter_id"] for item in detail["breadcrumb"]] == [
        "matter:jobs",
        "matter:company-a",
    ]
    assert detail["parent"]["matter_id"] == "matter:jobs"
    assert detail["work_items"]["items"][0]["title"]["zh-CN"] == "提交简历"
    root_detail = service.matter_detail(matter_id="matter:jobs")
    descendant_milestones = [
        item
        for item in root_detail["timeline"]
        if item.get("source_level") == "descendant_matter"
    ]
    assert descendant_milestones[0]["sentence"]["en"] == "Submit CV"
    assert descendant_milestones[0]["sub_matter"]["en"] == "Company A"
    assert root_detail["timeline_summary"]["descendant_count"] == 1
    status, payload = _request(
        create_application(service),
        "/api/matters/matter:jobs/children",
        "locale=zh-CN&offset=0&limit=50",
    )
    assert status == "200 OK"
    assert payload["result"]["items"][0]["title"]["zh-CN"] == "Company A（中文）"


def test_build_week_projects_material_stages_without_inventing_child_matters(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_matter(
        service,
        "matter:build-week",
        "OpenAI Build Week participation",
        state="in_progress",
    )
    service.hierarchy.save_work_item(
        MatterWorkItem(
            item_id="work-item:build-week-preparation",
            matter_id="matter:build-week",
            kind="milestone",
            status="in_progress",
            localized_title={
                "en": "Prepare the competition project",
                "zh-CN": "准备参赛项目",
            },
            localized_result={
                "en": "Registration is confirmed and submission work remains.",
                "zh-CN": "报名已确认，仍需完成并提交参赛项目。",
            },
            evidence_ids=("evidence:registration-confirmed",),
            planned_start="2026-07-16T00:00:00+00:00",
            planned_end="2026-07-21T23:59:59+00:00",
            required_for_parent=True,
            material_stage=True,
            basis_modality="ai_inferred",
            basis_scope="current_phase",
            temporal_assertion="ongoing",
            terminality="provisional",
            confidence="bounded",
            inference_as_of="2026-07-20T12:00:00+00:00",
            prerequisite_evidence_ids=("evidence:registration-confirmed",),
            remaining_obligation_ids=("submit-project",),
            active_window_start="2026-07-16T00:00:00+00:00",
            active_window_end="2026-07-21T23:59:59+00:00",
            contradiction_checked=True,
            coverage_boundary="No direct editor activity is available.",
            supporting_signals=(
                "registration is confirmed and the submission deadline is open",
            ),
            alternative_explanations=("Preparation may be paused.",),
            contradiction_triggers=(
                "withdrawal, submitted result, or postponement",
            ),
            expires_at="2026-07-21T23:59:59+00:00",
        )
    )
    service.hierarchy.save_work_item(
        MatterWorkItem(
            item_id="work-item:build-week-submit",
            matter_id="matter:build-week",
            kind="milestone",
            status="planned",
            localized_title={
                "en": "Submit the competition result",
                "zh-CN": "提交参赛成果",
            },
            localized_result={
                "en": "The deadline is confirmed but submission has not occurred.",
                "zh-CN": "截止时间已确认，但尚未提交。",
            },
            evidence_ids=("evidence:submission-deadline",),
            planned_end="2026-07-21T17:00:00-07:00",
            required_for_parent=True,
            material_stage=True,
            basis_modality="reported",
            basis_scope="source_record",
            temporal_assertion="planned",
        )
    )

    graph = service.matter_situation_graph(matter_id="matter:build-week")
    quick_view = service.matter_node_quick_view(
        matter_id="matter:build-week",
        node_id="work-item:build-week-preparation",
    )

    assert {node["node_id"] for node in graph["nodes"]} == {
        "matter:build-week",
        "work-item:build-week-preparation",
        "work-item:build-week-submit",
    }
    assert all(
        node["node_type"] != "matter"
        for node in graph["nodes"]
        if node["node_id"].startswith("work-item:")
    )
    assert quick_view["node_type"] == "work_item"
    assert quick_view["summary_current_state"]["state"] == "in_progress"
    assert quick_view["summary_current_state"]["state_basis_modality"] == (
        "ai_inferred"
    )
    assert quick_view["recursive_navigation_allowed"] is False


def test_legacy_work_item_without_semantic_basis_remains_readable_after_restart(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_matter(
        service,
        "matter:legacy-project",
        "Legacy project",
        state="in_progress",
    )
    service.store.append(
        "matter_work_item",
        "work-item:legacy-required-stage",
        1,
        {
            "item_id": "work-item:legacy-required-stage",
            "matter_id": "matter:legacy-project",
            "kind": "milestone",
            "status": "planned",
            "localized_title": {
                "en": "Legacy required stage",
                "zh-CN": "旧版必要阶段",
            },
            "localized_result": {
                "en": "The old record predates semantic-basis fields.",
                "zh-CN": "这条旧记录早于语义依据字段。",
            },
            "evidence_ids": ("evidence:legacy-stage",),
            "source_ids": (),
            "planned_start": "",
            "planned_end": "2026-08-01T00:00:00+00:00",
            "actual_start": "",
            "actual_end": "",
            "required_for_parent": True,
            "freshness": "current",
            "revision": 1,
            "updated_at": "2026-07-01T00:00:00+00:00",
        },
    )

    restarted = MatterService(
        private_root=service.config.private_root,
        repository_root=service.config.repository_root,
    )
    graph = restarted.matter_situation_graph(
        matter_id="matter:legacy-project"
    )
    quick_view = restarted.matter_node_quick_view(
        matter_id="matter:legacy-project",
        node_id="work-item:legacy-required-stage",
    )

    assert {node["node_id"] for node in graph["nodes"]} == {
        "matter:legacy-project",
        "work-item:legacy-required-stage",
    }
    assert quick_view["summary_current_state"]["state"] == "planned"
    assert quick_view["summary_current_state"]["state_basis_modality"] == (
        "unknown"
    )
    assert quick_view["summary_current_state"]["state_terminality"] == (
        "provisional"
    )
    assert quick_view["summary_current_state"]["semantic_contract_status"] == (
        "legacy_pending_recompute"
    )


def test_travel_leg_is_a_supported_material_work_item_kind():
    item = MatterWorkItem(
        item_id="work-item:flight-leg",
        matter_id="matter:trip",
        kind="travel_leg",
        status="planned",
        localized_title={
            "en": "Planned flight leg",
            "zh-CN": "计划航段",
        },
        localized_result={
            "en": "The flight leg remains planned.",
            "zh-CN": "该航段仍处于计划中。",
        },
        evidence_ids=("evidence:flight-plan",),
        source_ids=("source:flight-plan:v1",),
        planned_start="2026-09-30",
        required_for_parent=True,
        material_stage=True,
        basis_modality="planned",
        basis_scope="source_record",
        temporal_assertion="planned",
        terminality="provisional",
    )

    assert item.kind == "travel_leg"
    assert item.status == "planned"
    assert item.material_stage is True


def test_semantic_role_reconciliation_retires_exact_work_item_duplicates(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_matter(
        service,
        "matter:build-week",
        "Build Week",
        state="in_progress",
    )
    common = {
        "matter_id": "matter:build-week",
        "kind": "milestone",
        "status": "planned",
        "localized_title": {
            "en": "Submit the project",
            "zh-CN": "提交参赛项目",
        },
        "localized_result": {
            "en": "Submission remains planned.",
            "zh-CN": "参赛作品仍待提交。",
        },
        "evidence_ids": ("evidence:submission",),
        "basis_modality": "planned",
        "basis_scope": "",
        "temporal_assertion": "planned",
        "terminality": "provisional",
    }
    service.hierarchy.save_work_item(
        MatterWorkItem(
            **common,
            item_id="work-item:legacy-submission-a",
        )
    )
    service.hierarchy.save_work_item(
        MatterWorkItem(
            **common,
            item_id="work-item:legacy-submission-b",
        )
    )

    canonical = MatterWorkItem(
        **common,
        item_id="work-item:submission",
        semantic_role_key="submission",
    )
    service.hierarchy.save_work_item(
        canonical,
        supersedes_item_ids=(
            "work-item:legacy-submission-a",
            "work-item:legacy-submission-b",
        ),
    )
    page = service.matter_work_items(
        matter_id="matter:build-week"
    )
    assert [item["item_id"] for item in page["items"]] == [
        "work-item:submission"
    ]
    for retired_id in (
        "work-item:legacy-submission-a",
        "work-item:legacy-submission-b",
    ):
        retired = service.store.current(
            "matter_work_item",
            retired_id,
        )
        assert retired["deleted"] is True
        assert retired["superseded_by"] == "work-item:submission"
        assert retired["retirement_reason"] == (
            "semantic_identity_reconciliation"
        )

    history_count = len(
        service.store.history(
            "matter_work_item",
            "work-item:submission",
        )
    )
    service.hierarchy.save_work_item(
        canonical,
        supersedes_item_ids=(
            "work-item:legacy-submission-a",
            "work-item:legacy-submission-b",
        ),
    )
    assert len(
        service.store.history(
            "matter_work_item",
            "work-item:submission",
        )
    ) == history_count


def test_same_semantic_role_requires_exact_work_item_supersession(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_matter(service, "matter:project", "Project")
    common = {
        "matter_id": "matter:project",
        "kind": "action",
        "status": "planned",
        "localized_title": {
            "en": "Prepare",
            "zh-CN": "准备",
        },
        "localized_result": {
            "en": "Preparation is planned.",
            "zh-CN": "准备工作处于计划中。",
        },
        "evidence_ids": ("evidence:prepare",),
        "semantic_role_key": "preparation",
    }
    service.hierarchy.save_work_item(
        MatterWorkItem(
            **common,
            item_id="work-item:preparation-a",
        )
    )

    with pytest.raises(
        ValueError,
        match="same semantic role",
    ):
        service.hierarchy.save_work_item(
            MatterWorkItem(
                **common,
                item_id="work-item:preparation-b",
            )
        )

    page = service.matter_work_items(matter_id="matter:project")
    assert [item["item_id"] for item in page["items"]] == [
        "work-item:preparation-a"
    ]


def test_ai_inferred_work_item_status_must_match_its_inference_scope():
    common = {
        "item_id": "work-item:inference-scope",
        "matter_id": "matter:scope",
        "kind": "milestone",
        "localized_title": {
            "en": "Inferred stage",
            "zh-CN": "推断阶段",
        },
        "localized_result": {
            "en": "A bounded inference.",
            "zh-CN": "一项有边界的推断。",
        },
        "evidence_ids": ("evidence:scope",),
        "basis_modality": "ai_inferred",
        "terminality": "provisional",
        "confidence": "bounded",
        "inference_as_of": "2026-07-20T12:00:00+00:00",
        "coverage_boundary": "Only the authorized evidence was checked.",
        "supporting_signals": ("one current support",),
        "alternative_explanations": ("the activity may be paused",),
        "contradiction_triggers": ("a cancellation or completion record",),
        "expires_at": "2026-07-21T23:59:59+00:00",
    }

    with pytest.raises(
        ValueError,
        match="complete revisable inference contract",
    ):
        MatterWorkItem(
            **common,
            status="planned",
            basis_scope="current_phase",
            temporal_assertion="ongoing",
            prerequisite_evidence_ids=("evidence:scope",),
            remaining_obligation_ids=("submit-result",),
            active_window_start="2026-07-16T00:00:00+00:00",
            active_window_end="2026-07-21T23:59:59+00:00",
            contradiction_checked=True,
        )

    with pytest.raises(
        ValueError,
        match="complete revisable inference contract",
    ):
        MatterWorkItem(
            **common,
            status="in_progress",
            basis_scope="current_phase",
            temporal_assertion="ongoing",
            prerequisite_evidence_ids=("evidence:scope",),
            remaining_obligation_ids=("submit-result",),
            active_window_start="2026-07-16T00:00:00+00:00",
            active_window_end="2026-07-21T23:59:59+00:00",
            contradiction_checked=True,
            counter_signals=("current cancellation evidence",),
        )

    with pytest.raises(
        ValueError,
        match="complete revisable inference contract",
    ):
        MatterWorkItem(
            **common,
            status="in_progress",
            basis_scope="historical_gap",
            temporal_assertion="occurred",
            target_time="2026-07-19T12:00:00+00:00",
        )


def test_hierarchy_timeline_projects_one_child_logical_event_once(tmp_path):
    service = _service(tmp_path)
    _seed_matter(service, "matter:trip", "Trip", state="in_progress")
    _seed_matter(service, "matter:visit", "Park visit", state="completed")
    service.attach_matter_child(
        parent_matter_id="matter:trip",
        child_matter_id="matter:visit",
        role="required",
        confidence="bounded",
        rationale="the visit belongs to the trip",
        evidence_ids=("evidence:visit-edge",),
    )
    event = {
        "event_id": "event:park-complete",
        "logical_event_key": "logical-event:park-complete",
        "kind": "visit_completed",
        "object_ref": "matter:visit",
        "modality": "inferred",
        "temporal_direction": "past",
        "inference_purpose": "historical_gap_fill",
        "revisable": True,
        "claimed_time": "2026-06-30T16:59:59+02:00",
        "record_time": "2026-07-01T09:00:00+02:00",
        "evidence_ids": ("evidence:matter:visit",),
        "localized_sentence": {
            "en": "The park visit likely finished.",
            "zh-CN": "主题公园行程很可能已经结束。",
        },
    }
    service.store.append("temporal_event", event["event_id"], 1, event)

    timeline, summary = service._hierarchy_timeline(
        "matter:trip",
        (
            {
                "sentence": dict(event["localized_sentence"]),
                "claimed_time": event["claimed_time"],
                "record_time": event["record_time"],
                "modality": "inferred",
            },
        ),
    )

    assert len(timeline) == 1
    assert timeline[0]["sentence"] == event["localized_sentence"]
    assert timeline[0]["source_level"] == "descendant_matter"
    assert timeline[0]["sub_matter"]["en"] == "Park visit"
    assert timeline[0]["basis_label"] == {
        "en": "AI historical inference",
        "zh-CN": "AI 历史推断",
    }
    assert summary["total_count"] == 1
    assert summary["analysis_output_replacement_pending"] is False


def test_situation_graph_excludes_work_owned_by_superseded_child_projection(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_matter(service, "matter:parent", "Parent", state="in_progress")
    _seed_matter(service, "matter:child", "Child", state="planned")
    service.attach_matter_child(
        parent_matter_id="matter:parent",
        child_matter_id="matter:child",
        role="required",
        confidence="bounded",
        rationale="the child is independently trackable",
        evidence_ids=("evidence:child-edge",),
    )
    service.hierarchy.save_work_item(
        MatterWorkItem(
            item_id="work-item:child-step",
            matter_id="matter:child",
            kind="action",
            status="planned",
            localized_title={
                "en": "Complete child step",
                "zh-CN": "完成子步骤",
            },
            localized_result={
                "en": "Not started",
                "zh-CN": "尚未开始",
            },
            evidence_ids=("evidence:child-step",),
        )
    )
    output_ref = "projection:matter:child"
    service.store.append(
        "autonomous_finding",
        "finding:legacy-child",
        1,
        {
            "finding_id": "finding:legacy-child",
            "package_id": "work:legacy-child",
            "status": "auto_applied",
            "owner_output_ref": output_ref,
        },
    )
    service.store.append(
        "analysis_result_invalidation",
        "work:legacy-child",
        1,
        {
            "package_id": "work:legacy-child",
            "status": "superseded",
            "replacement_package_id": "work:current-child",
        },
    )
    service.store.append(
        "analysis_output_invalidation",
        "analysis-output-invalidation:legacy-child",
        1,
        {
            "invalidation_id": "analysis-output-invalidation:legacy-child",
            "output_ref": output_ref,
            "old_package_id": "work:legacy-child",
            "replacement_package_id": "work:current-child",
            "status": "superseded",
        },
    )

    child_page = service.matter_children(matter_id="matter:parent")
    graph = service.matter_situation_graph(matter_id="matter:parent")

    assert child_page["items"][0]["title"]["en"] == "Projection pending"
    assert graph["coverage"] == "partial"
    assert "analysis_output_replacement_pending" in graph["coverage_gaps"]
    assert all(
        node["node_id"] not in {"matter:child", "work-item:child-step"}
        for node in graph["nodes"]
    )

    service.store.append(
        "autonomous_finding",
        "finding:current-child",
        1,
        {
            "finding_id": "finding:current-child",
            "package_id": "work:current-child",
            "status": "auto_applied",
            "owner_output_ref": output_ref,
        },
    )
    rebuilt = service.matter_situation_graph(matter_id="matter:parent")

    assert "analysis_output_replacement_pending" not in (
        rebuilt["coverage_gaps"]
    )
    assert rebuilt["projection_kind"] == "matter_and_material_stages"
    assert {node["node_id"] for node in rebuilt["nodes"]} == {
        "matter:parent",
        "matter:child",
    }
    quick_view = service.matter_node_quick_view(
        matter_id="matter:parent",
        node_id="matter:child",
    )
    assert any(
        item.get("kind") == "work_item"
        for item in quick_view["summary_current_state"]["facts"]
    )


def test_child_material_clue_updates_parent_activity_order_not_overview(tmp_path):
    service = _service(tmp_path)
    _seed_matter(service, "matter:trip", "Japan trip", state="in_progress")
    _seed_matter(service, "matter:flight", "Book flight", state="planned")
    _seed_matter(service, "matter:other", "Older project", state="in_progress")
    service.attach_matter_child(
        parent_matter_id="matter:trip",
        child_matter_id="matter:flight",
        role="required",
        confidence="bounded",
        rationale="the flight is an independently trackable part of the trip",
        evidence_ids=("evidence:flight-edge",),
    )

    service.activity.record(
        MaterialClue(
            clue_id="clue:other-old",
            matter_id="matter:other",
            clue_kind="progress",
            user_world_at="2026-07-18T08:00:00+00:00",
            disposition="material",
            rationale="The older project changed yesterday.",
            localized_summary={
                "en": "The older project changed yesterday.",
                "zh-CN": "较早的项目昨天有了变化。",
            },
            semantic_revision="semantic:matter:other:1",
            evidence_ids=("evidence:other-progress",),
        )
    )
    service.activity.record(
        MaterialClue(
            clue_id="clue:flight-confirmed",
            matter_id="matter:flight",
            clue_kind="booking_confirmation",
            user_world_at="2026-07-19T09:30:00+00:00",
            disposition="material",
            rationale="The flight confirmation changes the trip's current state.",
            localized_summary={
                "en": "The flight has been confirmed.",
                "zh-CN": "航班已经确认。",
            },
            semantic_revision="semantic:matter:flight:1",
            evidence_ids=("evidence:flight-confirmed",),
        )
    )

    catalog = service.object_catalog_page()

    parent_projection = service.store.current("projection", "matter:trip")
    parent_activity = service.store.current("matter_activity", "matter:trip")
    assert parent_projection is not None and parent_activity is not None
    assert parent_activity["matter_id"] == "matter:trip"
    assert parent_activity["source_matter_id"] == "matter:flight"
    assert parent_activity["ancestor_propagated"] is True
    assert parent_activity["semantic_revision"] == "semantic:matter:flight:1"
    assert (
        parent_activity["semantic_revision"]
        != parent_projection["semantic_revision"]
    )
    assert [item["matter_id"] for item in catalog["items"]] == [
        "matter:trip",
        "matter:other",
    ]
    parent = catalog["items"][0]
    assert parent["activity_status"] == "current"
    assert parent["latest_meaningful_clue_at"] == "2026-07-19T09:30:00+00:00"
    assert parent["summary"] == parent_projection["localized_rationale"]


def test_indexed_hierarchy_audit_names_first_stale_stage_and_ui_reachability(
    tmp_path,
):
    service = _service(tmp_path)
    matter_id = "matter:indexed"
    object_id = "filesystem:indexed"
    _seed_matter(service, matter_id, "Indexed Matter")
    service.coverage_ledger.reconcile_inventory(
        scope_id="scope:indexed",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": object_id,
                "provider": "filesystem",
                "object_type": "file",
                "metadata": {"size": 10},
            },
        ),
        dispositions=(
            {"occurrence_id": object_id, "status": "tracked"},
        ),
    )
    for stage_id in STAGE_ORDER[2:]:
        service.coverage_ledger.mark_stage(
            object_id=object_id,
            stage_id=stage_id,
            status="current",
            input_fingerprint=f"test:{stage_id}",
            output_ref=f"output:{stage_id}",
            matter_ids=(matter_id,) if stage_id == "matter" else None,
            refresh_summary=stage_id == "ui_reachable",
        )
    service.hierarchy.register_matter(
        matter_id,
        change_ref="test:hierarchy-current",
    )

    current = service.matter_hierarchy_coverage_page()
    summary = service.object_coverage_summary()
    assert current["total_count"] == 1
    assert current["items"][0]["next_stage"] == ""
    assert current["items"][0]["ui_reachable"] is True
    assert set(current["items"][0]["stages"]) == {
        "hierarchy_decision",
        "containment_current",
        "child_state_current",
        "ancestor_rollup_current",
        "hierarchy_projection_current",
        "ui_reachable",
    }
    assert summary["registered_matter_count"] == 1
    assert summary["ui_reachable_matter_count"] == 1
    # Hierarchy reachability is current, but strict v2 coverage does not turn
    # green until SourceGroup, admitted-Matter coverage, semantic presentation,
    # and every other owned projection are current as well.
    assert summary["coverage_status"] == "partial"
    assert summary["coverage_reasons"]

    service.hierarchy.mark_dependency_changed(
        matter_id,
        change_ref="test:source-changed",
        refresh=False,
    )
    stale = service.matter_hierarchy_coverage_page()
    stale_summary = service.object_coverage_summary()
    assert stale["items"][0]["next_stage"] == "containment_current"
    assert stale["items"][0]["ui_reachable"] is False
    assert stale_summary["coverage_status"] == "partial"


def test_split_dispositions_move_sources_once_and_resume_idempotently(tmp_path):
    service = _service(tmp_path)
    _seed_matter(
        service,
        "matter:original",
        "Original",
        source_id="source:move",
    )
    original = service.store.current(
        "admission_decision",
        "matter:original",
    )
    original["matter"]["source_ids"] = ("source:move", "source:retain")
    service.store.append(
        "admission_decision",
        "matter:original",
        2,
        original,
    )
    _seed_matter(
        service,
        "matter:target",
        "Target",
        source_id="source:target",
    )
    dispositions = (
        {
            "member_kind": "source",
            "member_id": "source:move",
            "action": "move",
            "target_matter_ids": ("matter:target",),
            "evidence_ids": ("evidence:split",),
        },
        {
            "member_kind": "source",
            "member_id": "source:retain",
            "action": "retain",
            "target_matter_ids": ("matter:original",),
            "evidence_ids": ("evidence:split",),
        },
    )

    first = service.record_matter_split_or_merge(
        change_kind="split",
        subject_matter_ids=("matter:original",),
        rationale="Move one source to the independently trackable target",
        evidence_ids=("evidence:split",),
        dispositions=dispositions,
    )
    second = service.record_matter_split_or_merge(
        change_kind="split",
        subject_matter_ids=("matter:original",),
        rationale="Move one source to the independently trackable target",
        evidence_ids=("evidence:split",),
        dispositions=dispositions,
    )

    original_current = service.store.current(
        "admission_decision",
        "matter:original",
    )["matter"]
    target_current = service.store.current(
        "admission_decision",
        "matter:target",
    )["matter"]
    assert first["revision_id"] == second["revision_id"]
    assert original_current["source_ids"] == ["source:retain"]
    assert set(target_current["source_ids"]) == {
        "source:target",
        "source:move",
    }
    requests = service.hierarchy.disposition_requests(first["revision_id"])
    assert len(requests) == 2
    assert {item["status"] for item in requests} == {"current"}


def test_restart_resumes_pending_original_owner_disposition(tmp_path):
    service = _service(tmp_path)
    _seed_matter(
        service,
        "matter:before",
        "Before",
        source_id="source:move-after-restart",
    )
    _seed_matter(
        service,
        "matter:after",
        "After",
        source_id="source:existing",
    )
    revision = service.hierarchy.record_split_or_merge(
        change_kind="split",
        subject_matter_ids=("matter:before",),
        rationale="Resume the original owner after a process interruption",
        evidence_ids=("evidence:restart",),
        dispositions=(
            HierarchyMemberDisposition(
                member_kind="source",
                member_id="source:move-after-restart",
                action="move",
                target_matter_ids=("matter:after",),
                evidence_ids=("evidence:restart",),
            ),
        ),
    )
    assert service.hierarchy.disposition_requests(revision.revision_id)[0][
        "status"
    ] == "pending"

    restarted = MatterService(
        private_root=service.config.private_root,
        repository_root=service.config.repository_root,
    )
    cycle = restarted.run_maintenance_cycle(limit=20)
    request = restarted.hierarchy.disposition_requests(
        revision.revision_id
    )[0]
    after = restarted.store.current(
        "admission_decision",
        "matter:after",
    )["matter"]

    assert cycle["hierarchy_recovered_count"] == 1
    assert request["status"] == "current"
    assert "source:move-after-restart" in after["source_ids"]


def test_legacy_matter_explicitly_migrates_as_root_without_related_edge(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_matter(
        service,
        "matter:legacy-root",
        "Legacy root",
    )
    service.store.append(
        "matter_relation_candidate",
        "relation:legacy",
        1,
        {
            "left_matter_id": "matter:legacy-root",
            "right_matter_id": "matter:other",
            "relation": "related",
        },
    )

    restarted = MatterService(
        private_root=service.config.private_root,
        repository_root=service.config.repository_root,
    )
    second_restart = MatterService(
        private_root=service.config.private_root,
        repository_root=service.config.repository_root,
    )

    assert restarted.migrated_root_hierarchy_count == 0
    assert second_restart.migrated_root_hierarchy_count == 0
    assert restarted._migrate_root_hierarchy_audits() == 1
    assert second_restart._migrate_root_hierarchy_audits() == 0
    assert restarted.hierarchy.parent_edge(
        "matter:legacy-root",
        current_only=False,
    ) is None
    assert restarted.object_catalog_page()["items"][0]["matter_id"] == (
        "matter:legacy-root"
    )


@pytest.mark.parametrize("object_id", ("source:projected", "candidate:projected"))
def test_projected_noncanonical_object_is_not_accepted_as_matter(
    tmp_path,
    object_id,
):
    service = _service(tmp_path)
    service.store.append(
        "projection",
        object_id,
        1,
        {"matter_id": object_id, "state": "planned"},
    )

    with pytest.raises(KeyError, match="admitted Matter is unavailable"):
        service.hierarchy.register_matter(
            object_id,
            change_ref="test:reject-projection-only",
        )


def test_root_migration_ignores_projected_noncanonical_objects(tmp_path):
    service = _service(tmp_path)
    _seed_matter(service, "matter:canonical-root", "Canonical root")
    for object_id in ("source:projected", "candidate:projected"):
        service.store.append(
            "projection",
            object_id,
            1,
            {"matter_id": object_id, "state": "planned"},
        )

    assert service._migrate_root_hierarchy_audits() == 1
    assert service.store.current(
        "matter_hierarchy_audit",
        "matter:canonical-root",
    ) is not None
    for object_id in ("source:projected", "candidate:projected"):
        assert service.store.current("matter_hierarchy_audit", object_id) is None


def test_concurrent_startup_root_migration_converges_without_unique_failure(
    tmp_path,
):
    service = _service(tmp_path)
    peer = MatterService(
        private_root=service.config.private_root,
        repository_root=service.config.repository_root,
    )
    _seed_matter(
        service,
        "matter:concurrent-legacy-root",
        "Concurrent legacy root",
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        migrated_counts = tuple(
            executor.map(
                lambda candidate: candidate._migrate_root_hierarchy_audits(),
                (service, peer),
            )
        )

    audits = tuple(
        item.store.current(
            "matter_hierarchy_audit",
            "matter:concurrent-legacy-root",
        )
        for item in (service, peer)
    )
    assert all(
        set(dict(audit["stages"])) == {
            "hierarchy_decision",
            "containment_current",
            "child_state_current",
            "ancestor_rollup_current",
            "hierarchy_projection_current",
            "ui_reachable",
        }
        for audit in audits
    )
    assert sum(migrated_counts) == 1


def test_root_migration_rolls_back_partial_registration_and_can_retry(
    tmp_path,
    monkeypatch,
):
    service = _service(tmp_path)
    peer = MatterService(
        private_root=service.config.private_root,
        repository_root=service.config.repository_root,
    )
    _seed_matter(
        service,
        "matter:retry-legacy-root",
        "Retry legacy root",
    )

    with monkeypatch.context() as patch:
        patch.setattr(
            service.hierarchy,
            "_publish",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("simulated migration interruption")
            ),
        )
        with pytest.raises(
            RuntimeError,
            match="simulated migration interruption",
        ):
            service._migrate_root_hierarchy_audits()

    assert service.store.current(
        "matter_hierarchy_audit",
        "matter:retry-legacy-root",
    ) is None
    assert service.store.current(
        "matter_hierarchy_summary",
        "matter:retry-legacy-root",
    ) is None

    assert peer._migrate_root_hierarchy_audits() == 1
    assert peer.store.current(
        "matter_hierarchy_audit",
        "matter:retry-legacy-root",
    ) is not None


def test_hierarchy_coverage_pages_require_exact_current_c6_admission(tmp_path):
    service = _service(tmp_path)
    _seed_matter(service, "matter:canonical", "Canonical")
    service.hierarchy.register_matter(
        "matter:canonical",
        change_ref="admission:matter:canonical:1",
    )
    _seed_noncanonical_hierarchy_projection(
        service,
        "candidate:projection-only",
    )
    service.store.append(
        "admission_decision",
        "candidate:mismatched",
        1,
        {
            "status": "admitted",
            "matter": {
                "matter_id": "matter:different",
                "admitted": True,
            },
        },
    )
    _seed_noncanonical_hierarchy_projection(
        service,
        "candidate:mismatched",
    )

    counts = service.store.matter_hierarchy_summary_counts()
    page = service.matter_hierarchy_coverage_page(offset=0, limit=100)

    assert counts["registered_matter_count"] == 1
    assert counts["hierarchy_terminal_matter_count"] == 1
    assert page["total_count"] == 1
    assert tuple(item["matter_id"] for item in page["items"]) == (
        "matter:canonical",
    )


def test_noncanonical_hierarchy_reconcile_is_bounded_cursor_safe_and_keeps_history(
    tmp_path,
):
    service = _service(tmp_path)
    for matter_id in (
        "candidate:001",
        "candidate:002",
        "candidate:003",
    ):
        _seed_noncanonical_hierarchy_projection(service, matter_id)
        _seed_noncanonical_hierarchy_projection(
            service,
            matter_id,
            revision=2,
        )

    first = service.reconcile_noncanonical_matter_hierarchy(limit=2)
    assert first["status"] == "partial"
    assert first["retired_matter_count"] == 2
    assert first["retired_pointer_count"] == 6
    assert first["next_cursor"] == "candidate:002"
    assert first["has_more"] is True
    assert service.store.current(
        "matter_hierarchy_audit",
        "candidate:001",
    ) is None
    assert len(
        service.store.history(
            "matter_hierarchy_audit",
            "candidate:001",
        )
    ) == 2

    final = service.reconcile_noncanonical_matter_hierarchy(
        after_matter_id=first["next_cursor"],
        limit=2,
    )
    exact_retry = service.reconcile_noncanonical_matter_hierarchy(
        after_matter_id=first["next_cursor"],
        limit=2,
    )
    assert final["status"] == "current"
    assert final["retired_matter_count"] == 1
    assert exact_retry["retired_matter_count"] == 0
    assert exact_retry["retired_pointer_count"] == 0
    assert exact_retry["has_more"] is False
    assert service.store.history(
        "matter_hierarchy_summary",
        "candidate:003",
    )
    catalog = service.object_catalog_page(locale="en", root_only=True)
    assert catalog["items"] == ()


def test_noncanonical_hierarchy_page_blocks_atomically_on_any_active_edge(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_matter(service, "matter:canonical-parent", "Canonical parent")
    for matter_id in ("candidate:free", "candidate:linked"):
        _seed_noncanonical_hierarchy_projection(service, matter_id)
    edge_id = "edge:legacy-linked"
    service.store.append(
        "matter_containment_edge",
        edge_id,
        1,
        {
            "edge_id": edge_id,
            "child_matter_id": "candidate:linked",
            "parent_matter_id": "matter:canonical-parent",
            "role": "optional",
            "ordinal": 0,
            "freshness": "current",
            "active": True,
        },
    )

    blocked = service.reconcile_noncanonical_matter_hierarchy(limit=10)
    assert blocked["status"] == "blocked"
    assert blocked["blocked_matter_ids"] == ("candidate:linked",)
    assert blocked["retired_pointer_count"] == 0
    assert service.store.current(
        "matter_hierarchy_audit",
        "candidate:free",
    ) is not None

    service.store.append(
        "matter_containment_edge",
        edge_id,
        2,
        {
            "edge_id": edge_id,
            "child_matter_id": "candidate:linked",
            "parent_matter_id": "matter:canonical-parent",
            "role": "optional",
            "ordinal": 0,
            "freshness": "current",
            "active": False,
        },
    )
    repaired = service.reconcile_noncanonical_matter_hierarchy(limit=10)
    assert repaired["status"] == "current"
    assert repaired["retired_matter_count"] == 2
    assert len(
        service.store.history(
            "matter_hierarchy_audit",
            "candidate:linked",
        )
    ) == 1


def test_noncanonical_hierarchy_reconcile_covers_real_residual_family_scale(
    tmp_path,
):
    service = _service(tmp_path)
    residual_count = 11_647
    rows = (
        (
            "matter_hierarchy_audit",
            f"legacy-source:{index:05d}",
            1,
            {
                "matter_id": f"legacy-source:{index:05d}",
                "revision": 1,
                "status": "current",
                "change_ref": "legacy-unbounded-root-migration",
                "stages": {
                    "hierarchy_decision": "current",
                    "containment_current": "current",
                    "child_state_current": "current",
                    "ancestor_rollup_current": "current",
                    "hierarchy_projection_current": "current",
                    "ui_reachable": "current",
                },
            },
        )
        for index in range(residual_count)
    )
    service.store.append_many(rows)

    cursor = ""
    retired = 0
    page_count = 0
    while True:
        result = service.reconcile_noncanonical_matter_hierarchy(
            after_matter_id=cursor,
            limit=500,
        )
        retired += result["retired_matter_count"]
        page_count += 1
        if not result["has_more"]:
            break
        cursor = result["next_cursor"]

    assert retired == residual_count
    assert page_count == 24
    assert service.store.count_current("matter_hierarchy_audit") == 0
    assert service.store.matter_hierarchy_summary_counts()[
        "registered_matter_count"
    ] == 0
    assert len(
        service.store.history(
            "matter_hierarchy_audit",
            "legacy-source:00000",
        )
    ) == 1


def test_empty_current_supplemental_information_rebases_to_pending(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_matter(service, "matter:legacy", "Legacy Matter")
    service.store.append(
        "matter_supplemental_information",
        "matter:legacy",
        1,
        {
            "matter_id": "matter:legacy",
            "semantic_revision": "semantic:matter:legacy:1",
            "items": (),
            "status": "current",
        },
    )
    service.coverage_ledger.register_matters(
        matters=(
            {
                "matter_id": "matter:legacy",
                "matter_kind": "root_matter",
                "semantic_revision": "semantic:matter:legacy:1",
                "hierarchy_revision": "hierarchy:matter:legacy:1",
            },
        )
    )
    service.coverage_ledger.mark_stage(
        object_id="matter:legacy",
        stage_id="supplemental_information",
        status="current",
        input_fingerprint="semantic:matter:legacy:1",
        output_ref=(
            "matter_supplemental_information:matter:legacy"
        ),
    )

    receipt = service.rebase_empty_supplemental_information(limit=1)

    assert receipt["status"] == "current"
    assert receipt["repaired_count"] == 1
    assert (
        service.store.current(
            "matter_supplemental_information",
            "matter:legacy",
        )["status"]
        == "pending"
    )
    assert (
        service.store.current(
            "object_coverage",
            "matter:legacy",
        )["stages"]["supplemental_information"]["status"]
        == "pending"
    )

    repeated = service.rebase_empty_supplemental_information(limit=1)

    assert repeated["repaired_count"] == 0
    assert repeated["already_pending_count"] == 1


def test_supplemental_projection_shows_only_current_fresh_items(tmp_path):
    service = _service(tmp_path)
    _seed_matter(service, "matter:context", "Context Matter")
    service.store.append(
        "matter_supplemental_information",
        "matter:context",
        1,
        {
            "matter_id": "matter:context",
            "status": "current",
            "items": (
                {
                    "localized_title": {
                        "en": "Current context",
                        "zh-CN": "当前背景",
                    },
                    "localized_body": {
                        "en": "This remains useful.",
                        "zh-CN": "这条信息仍然有用。",
                    },
                    "freshness": "current",
                },
                {
                    "localized_title": {
                        "en": "Old context",
                        "zh-CN": "旧背景",
                    },
                    "localized_body": {
                        "en": "This is stale.",
                        "zh-CN": "这条信息已经过期。",
                    },
                    "freshness": "stale",
                },
            ),
        },
    )

    current = service.matter_detail(
        matter_id="matter:context",
        locale="en",
    )["ai_supplemental_information"]

    assert current["status"] == "current"
    assert current["total_count"] == 1
    assert current["items"][0]["title"]["en"] == "Current context"

    service.store.append(
        "matter_supplemental_information",
        "matter:context",
        2,
        {
            "matter_id": "matter:context",
            "status": "stale",
            "items": (
                {
                    "localized_title": {
                        "en": "Old context",
                        "zh-CN": "旧背景",
                    },
                    "localized_body": {
                        "en": "This is stale.",
                        "zh-CN": "这条信息已经过期。",
                    },
                    "freshness": "stale",
                },
            ),
        },
    )
    stale = service.matter_detail(
        matter_id="matter:context",
        locale="zh-CN",
    )["ai_supplemental_information"]

    assert stale == {"items": (), "total_count": 0, "status": "stale"}
