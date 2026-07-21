from dataclasses import asdict
from io import StringIO
import json

import pytest

from matters.application.orchestrator import MatterService
from matters.analysis.operations import ResearchProviderStatus
from matters.cli.main import run


def _service(tmp_path) -> MatterService:
    repository = tmp_path / "repository"
    repository.mkdir()
    return MatterService(
        repository_root=repository,
        private_root=tmp_path / "private",
    )


def _seed_admitted_matter(
    service: MatterService,
    matter_id: str,
    *,
    text: str = "Plan the evidence-backed launch.",
) -> str:
    source_id = f"source:{matter_id}"
    evidence_id = f"evidence:{matter_id}"
    service.store.append(
        "evidence_anchor",
        evidence_id,
        1,
        {
            "evidence_id": evidence_id,
            "source_id": source_id,
            "source_version": 1,
            "location": {"field": "body"},
            "text": text,
            "modality": "reported",
            "current": True,
        },
    )
    service.store.append(
        "admission_decision",
        matter_id,
        1,
        {
            "status": "admitted",
            "matter": {
                "matter_id": matter_id,
                "source_ids": [f"{source_id}:v1"],
                "rationale": "The source describes a durable user goal.",
                "evidence_ids": [evidence_id],
                "admitted": True,
                "semantic_identity_id": f"semantic:{matter_id}",
                "object_kind": "matter",
            },
            "candidate": None,
            "reason": "admitted",
        },
    )
    return evidence_id


def _repair_result(package: dict, *, title: str, title_zh: str) -> dict:
    evidence_id = package["allowed_evidence_ids"][0]
    semantic_revision = package["source_revision_ids"][0]
    semantic_identity_key = package["untrusted_evidence"][
        "matter_projection_repair"
    ]["semantic_identity_key"]
    return {
        "status": "passed",
        "input_dispositions": [
            {
                "input_id": item,
                "disposition": "used",
                "reason": "Supports the bounded title and summary.",
            }
            for item in (
                *package["allowed_evidence_ids"],
                *package["allowed_asset_ids"],
            )
        ],
        "findings": [
            {
                "finding_type": "matter_candidate",
                "owner_model_id": "C6_matter_admission",
                "statement": title,
                "localized_statement": {
                    "en": title,
                    "zh-CN": title_zh,
                },
                "semantic_revision": semantic_revision,
                "evidence_ids": [evidence_id],
                "confidence": "high",
                "modality": "inferred",
                "attributes": {
                    "semantic_identity_key": semantic_identity_key,
                },
            },
            {
                "finding_type": "bounded_summary",
                "owner_model_id": "C12_projection_bilingual_ui",
                "statement": "The launch is being planned.",
                "localized_statement": {
                    "en": "The launch is being planned.",
                    "zh-CN": "发布工作正在规划中。",
                },
                "semantic_revision": semantic_revision,
                "evidence_ids": [evidence_id],
                "confidence": "high",
                "modality": "inferred",
                "attributes": {"state": "planned"},
            },
        ],
    }


def _seed_equivalent_projection(
    service: MatterService,
    matter_id: str,
    *,
    title: str,
) -> None:
    projection = service.projections.publish(
        matter_id=matter_id,
        semantic_revision=f"semantic:{matter_id}:1",
        state="planned",
        rationale=f"{title} is ready for presentation.",
        evidence_ids=(f"evidence:{matter_id}",),
        localized_values={"en": title, "zh-CN": f"{title}（中文）"},
        localized_rationale={
            "en": f"{title} is ready for presentation.",
            "zh-CN": f"{title} 已可以展示。",
        },
    )
    service.store.append(
        "projection",
        matter_id,
        1,
        asdict(projection),
    )


def test_reconciliation_is_bounded_restart_safe_and_does_not_replay_admission(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_admitted_matter(service, "matter:a")
    _seed_admitted_matter(service, "matter:b")

    first = service.reconcile_admitted_matter_presentation(limit=1)

    assert first["scanned_matter_count"] == 1
    assert first["projection_repair_queued_count"] == 1
    assert first["has_more"] is True
    assert first["next_cursor"] == "matter:a"
    item = first["items"][0]
    package_id = item["projection_repair_package_id"]
    package = service.store.current("analysis_work_package", package_id)
    assert package["task_kind"] == "matter_projection_repair"
    assert package["capability_role"] == "matter_modeler"
    assert package["requested_output_types"] == [
        "matter_candidate",
        "bounded_summary",
    ]
    assert package["matter_id"] == "matter:a"
    assert "openai" not in str(package).casefold()
    assert "luna" not in str(package).casefold()
    assert "terra" not in str(package).casefold()
    admission_before = service.store.current(
        "admission_decision",
        "matter:a",
    )

    imported = service.import_autonomous_result(
        package_id=package_id,
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result=_repair_result(
            package,
            title="Travel planning launch",
            title_zh="旅行计划启动",
        ),
    )

    assert imported["auto_apply_status"] == "auto_applied"
    assert service.store.current(
        "admission_decision",
        "matter:a",
    ) == admission_before
    assert service.store.next_revision(
        "admission_decision",
        "matter:a",
    ) == 2

    resumed = service.reconcile_admitted_matter_presentation(limit=1)

    assert resumed["projection_current_count"] == 1
    assert resumed["hero_prepared_count"] == 1
    assert resumed["hero_pending_count"] == 1
    assert resumed["items"][0]["projection_repair_status"] == "not_required"
    hero = service.store.current("generated_hero_record", "matter:a")
    assert hero["status"] == "generation_pending_placeholder"
    assert hero["private_asset_token"] == ""
    service.store.iter_current = lambda _owner: (_ for _ in ()).throw(
        AssertionError("hero package paging must not scan a complete owner")
    )
    hero_page = service.pending_generated_heroes(offset=0, limit=1)
    assert hero_page["total_count"] == 1
    assert hero_page["items"][0]["matter_id"] == "matter:a"

    second = service.reconcile_admitted_matter_presentation(
        after_matter_id=first["next_cursor"],
        limit=1,
    )
    assert second["scanned_matter_count"] == 1
    assert second["items"][0]["matter_id"] == "matter:b"
    assert second["has_more"] is False
    assert second["next_cursor"] == ""


def test_child_matter_never_queues_a_generated_hero(tmp_path):
    service = _service(tmp_path)
    _seed_admitted_matter(service, "matter:root")
    _seed_admitted_matter(service, "matter:child")
    _seed_equivalent_projection(
        service,
        "matter:root",
        title="Representative parent Matter",
    )
    _seed_equivalent_projection(
        service,
        "matter:child",
        title="Contained child Matter",
    )
    service.attach_matter_child(
        parent_matter_id="matter:root",
        child_matter_id="matter:child",
        role="required",
        confidence="high",
        rationale="The child is part of the parent Matter.",
        evidence_ids=("evidence:matter:child",),
    )

    prepared = service.prepare_generated_heroes(
        matter_ids=("matter:root", "matter:child"),
    )

    assert prepared["prepared_count"] == 1
    assert prepared["prepared_matter_ids"] == ("matter:root",)
    assert prepared["skipped_matter_ids"] == ("matter:child",)
    assert service.store.current(
        "generated_hero_record",
        "matter:root",
    )["status"] == "generation_pending_placeholder"
    assert service.store.current(
        "generated_hero_record",
        "matter:child",
    ) is None

    reconciled = service.reconcile_admitted_matter_presentation(limit=10)
    by_id = {
        item["matter_id"]: item
        for item in reconciled["items"]
    }
    assert by_id["matter:root"]["generated_hero_status"] == (
        "generation_pending_placeholder"
    )
    assert by_id["matter:child"]["generated_hero_status"] == "not_applicable"
    assert reconciled["hero_pending_count"] == 1
    assert reconciled["hero_prepared_count"] == 0


def test_supplemental_research_queue_is_bounded_restart_safe_and_truthful(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_admitted_matter(service, "matter:root")
    _seed_equivalent_projection(
        service,
        "matter:root",
        title="Representative root Matter",
    )

    first = service.queue_eligible_supplemental_research(limit=1)
    second = service.queue_eligible_supplemental_research(limit=1)

    assert first["scanned_matter_count"] == 1
    assert first["unavailable_count"] == 1
    assert first["queued_count"] == 0
    assert first["items"][0]["status"] == "unavailable"
    assert first["items"][0]["disposition"] == "researchguard_unavailable"
    assert first["items"][0]["research_package_id"]
    assert second["items"] == first["items"]
    assert second["changed"] is False
    assert second["unchanged_count"] == 1
    supplemental = service.store.current(
        "matter_supplemental_information",
        "matter:root",
    )
    assert supplemental["items"] == []
    assert supplemental["status"] == "unavailable"
    assert supplemental["provider_gate"]["provider_id"] == "researchguard"
    pending = service.pending_analysis_packages(limit=100)["items"]
    research = tuple(
        item
        for item in pending
        if item["task_kind"] == "supplemental_information_research"
    )
    assert len(research) == 1


def test_supplemental_research_queues_current_provider_for_roots_only(
    tmp_path,
):
    service = _service(tmp_path)
    service.research_status = ResearchProviderStatus(
        status="current",
        provider_id="researchguard",
        provider_version="0.1.2",
        source_commit="current-researchguard-source",
        portable_receipt_id="sha256:" + ("a" * 64),
    )
    for matter_id, title in (
        ("matter:root", "Representative root Matter"),
        ("matter:child", "Contained child Matter"),
    ):
        _seed_admitted_matter(service, matter_id)
        _seed_equivalent_projection(
            service,
            matter_id,
            title=title,
        )
    service.attach_matter_child(
        parent_matter_id="matter:root",
        child_matter_id="matter:child",
        role="required",
        confidence="high",
        rationale="The child is part of the parent Matter.",
        evidence_ids=("evidence:matter:child",),
    )
    service.store.append(
        "matter_supplemental_information",
        "matter:root",
        1,
        {
            "matter_id": "matter:root",
            "semantic_revision": "semantic:matter:root:old",
            "items": [
                {
                    "kind": "background",
                    "localized_title": {
                        "en": "Old background",
                        "zh-CN": "旧背景",
                    },
                    "localized_body": {
                        "en": "This background needs refreshing.",
                        "zh-CN": "这条背景信息需要刷新。",
                    },
                    "freshness": "stale",
                },
            ],
            "status": "stale",
        },
    )

    queued = service.queue_eligible_supplemental_research(limit=10)

    by_id = {
        item["matter_id"]: item
        for item in queued["items"]
    }
    assert queued["queued_count"] == 1
    assert queued["not_applicable_count"] == 1
    assert by_id["matter:root"]["status"] == "pending"
    assert by_id["matter:root"]["disposition"] == "research_queued"
    assert by_id["matter:root"]["research_package_id"]
    root_supplemental = service.store.current(
        "matter_supplemental_information",
        "matter:root",
    )
    assert root_supplemental["status"] == "pending"
    assert root_supplemental["items"][0]["freshness"] == "stale"
    root_detail = service.matter_detail(
        matter_id="matter:root",
        locale="en",
    )
    assert root_detail["ai_supplemental_information"] == {
        "items": (),
        "total_count": 0,
        "status": "pending",
    }
    assert by_id["matter:child"] == {
        "matter_id": "matter:child",
        "status": "not_applicable",
        "disposition": "descendant_not_applicable",
        "research_package_id": "",
    }
    child_supplemental = service.store.current(
        "matter_supplemental_information",
        "matter:child",
    )
    assert child_supplemental["items"] == []
    assert child_supplemental["status"] == "not_applicable"
    pending = service.pending_analysis_packages(limit=100)["items"]
    research = tuple(
        item
        for item in pending
        if item["task_kind"] == "supplemental_information_research"
    )
    assert len(research) == 1
    assert research[0]["matter_id"] == "matter:root"


def test_empty_supplemental_rebase_preserves_explicit_dispositions(tmp_path):
    service = _service(tmp_path)
    _seed_admitted_matter(service, "matter:child")
    service.store.append(
        "matter_supplemental_information",
        "matter:child",
        1,
        {
            "matter_id": "matter:child",
            "semantic_revision": "semantic:matter:child:1",
            "items": (),
            "status": "not_applicable",
        },
    )

    result = service.rebase_empty_supplemental_information(limit=10)

    assert result["repaired_count"] == 0
    assert result["explicit_disposition_count"] == 1
    assert result["items"] == (
        {
            "matter_id": "matter:child",
            "disposition": "explicit_not_applicable_unchanged",
        },
    )
    assert service.store.next_revision(
        "matter_supplemental_information",
        "matter:child",
    ) == 2


def test_reconciliation_reports_missing_current_evidence_without_fabrication(
    tmp_path,
):
    service = _service(tmp_path)
    _seed_admitted_matter(service, "matter:no-evidence")
    anchor = service.store.current(
        "evidence_anchor",
        "evidence:matter:no-evidence",
    )
    service.store.append(
        "evidence_anchor",
        "evidence:matter:no-evidence",
        2,
        {**anchor, "current": False},
    )

    result = service.reconcile_admitted_matter_presentation(limit=10)

    assert result["projection_repair_blocked_count"] == 1
    assert result["status"] == "current_with_gaps"
    assert result["items"][0]["projection_repair_package_id"] == ""
    assert "no current admitted evidence" in result["items"][0]["blocker"]
    assert service.pending_analysis_packages()["total_count"] == 0


def test_object_browser_rejects_projection_only_and_uncertain_objects(tmp_path):
    service = _service(tmp_path)
    for matter_id in ("matter:projection-only", "matter:uncertain"):
        projection = service.projections.publish(
            matter_id=matter_id,
            semantic_revision="source:test:v1",
            state="planned",
            rationale="A projected object.",
            evidence_ids=(),
            localized_values={"en": "Projected", "zh-CN": "投影对象"},
            localized_rationale={
                "en": "A projected object.",
                "zh-CN": "一个投影对象。",
            },
        )
        service.store.append(
            "projection",
            matter_id,
            1,
            asdict(projection),
        )
    service.store.append(
        "admission_decision",
        "matter:uncertain",
        1,
        {
            "status": "uncertain",
            "matter": None,
            "candidate": {"candidate_id": "matter:uncertain"},
        },
    )

    assert service.object_catalog_page()["total_count"] == 0
    assert service.browser.cards(
        ("matter:projection-only", "matter:uncertain")
    ) == ()
    with pytest.raises(KeyError, match="matter is unavailable"):
        service.matter_detail(
            matter_id="matter:projection-only",
            locale="en",
        )


def test_cli_exposes_the_bounded_presentation_reconciliation(tmp_path):
    service = _service(tmp_path)
    _seed_admitted_matter(service, "matter:cli")
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        ["matter-presentation-reconcile", "--limit", "1"],
        service=service,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert stderr.getvalue() == ""
    result = json.loads(stdout.getvalue())["result"]
    assert result["scanned_matter_count"] == 1
    assert result["items"][0]["matter_id"] == "matter:cli"
    assert result["items"][0]["projection_repair_package_id"].startswith(
        "work:"
    )


def test_daily_maintenance_includes_the_same_bounded_reconciliation(tmp_path):
    service = _service(tmp_path)
    _seed_admitted_matter(service, "matter:maintenance")

    result = service.run_maintenance_cycle(limit=1)

    presentation = result["matter_presentation_reconciliation"]
    assert presentation["scanned_matter_count"] == 1
    assert presentation["projection_repair_queued_count"] == 1
    assert presentation["items"][0]["matter_id"] == "matter:maintenance"
