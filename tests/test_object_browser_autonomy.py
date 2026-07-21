from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from matters.application.orchestrator import MatterService
from matters.application.coverage_ledger import STAGE_ORDER
from matters.presentation.heroes import HeroSubject


def _service(tmp_path: Path) -> MatterService:
    repository = tmp_path / "repository"
    repository.mkdir()
    return MatterService(
        repository_root=repository,
        private_root=tmp_path / "private",
    )


def _append_current(
    service: MatterService,
    owner: str,
    key: str,
    payload: dict[str, object],
) -> None:
    assert service.store is not None
    service.store.append(
        owner,
        key,
        service.store.next_revision(owner, key),
        payload,
    )


def _seed_matter(
    service: MatterService,
    *,
    matter_id: str = "matter:launch",
    state: str = "in_progress",
) -> None:
    evidence_id = "evidence:launch"
    _append_current(
        service,
        "evidence_anchor",
        evidence_id,
        {
            "evidence_id": evidence_id,
            "text": "Launch is planned for 5 August.",
            "modality": "reported",
            "location": {"line_start": 4, "line_end": 4, "private_path": "hidden"},
        },
    )
    _append_current(
        service,
        "projection",
        matter_id,
        {
            "matter_id": matter_id,
            "semantic_revision": "semantic:launch:v1",
            "state": state,
            "rationale": "Current evidence records launch work.",
            "evidence_ids": (evidence_id,),
            "localized_values": {
                "en": "Prepare the product launch",
                "zh-CN": "准备产品发布",
            },
            "localized_rationale": {
                "en": "The launch work is active.",
                "zh-CN": "发布工作正在进行。",
            },
            "equivalence_status": "equivalent",
        },
    )
    _append_current(
        service,
        "admission_decision",
        matter_id,
        {
            "matter_id": matter_id,
            "status": "admitted",
            "rationale": "current evidence licenses admission",
            "matter": {"matter_id": matter_id},
        },
    )
    _append_current(
        service,
        "matter_classification",
        matter_id,
        {
            "matter_id": matter_id,
            "semantic_revision": "semantic:launch:v1",
            "topic_types": (
                {
                    "value": "product_launch",
                    "label": {
                        "en": "Product launch",
                        "zh-CN": "产品发布",
                    },
                },
            ),
            "freshness": "current",
        },
    )
    _append_current(
        service,
        "relation_candidate",
        f"{matter_id}:depends_on:matter:design",
        {
            "source_matter_id": matter_id,
            "relation_type": "depends_on",
            "target_matter_id": "matter:design",
        },
    )
    _append_current(
        service,
        "temporal_event",
        "event:launch",
        {
            "event_id": "event:launch",
            "kind": "milestone",
            "modality": "planned",
            "record_time": "2026-07-18T12:00:00Z",
            "claimed_time": "2026-08-05",
            "actor": "Matters AI",
            "object_ref": matter_id,
            "evidence_ids": (evidence_id,),
            "localized_sentence": {
                "en": "The product launch is planned for 5 August.",
                "zh-CN": "产品计划于 8 月 5 日发布。",
            },
            "confidence": 0.82,
            "conflict": False,
        },
    )
    _append_current(
        service,
        "object_coverage",
        "occurrence:launch",
        {
            "object_id": "occurrence:launch",
            "provider": "filesystem",
            "object_type": "document",
            "scope_id": "scope:documents",
            "inventory_revision": 1,
            "disposition": "tracked",
            "matter_ids": (matter_id,),
            "required_stages": STAGE_ORDER,
            "stages": {
                stage_id: {
                    "stage_id": stage_id,
                    "status": "current",
                    "owner_id": f"owner:{stage_id}",
                    "input_fingerprint": "sha256:test",
                    "output_ref": f"{stage_id}:launch",
                }
                for stage_id in STAGE_ORDER
            },
            "revision": 1,
        },
    )
    _append_current(
        service,
        "source_catalog",
        "occurrence:launch",
        {
            "occurrence_id": "occurrence:launch",
            "object_type": "document",
            "display_name": "Launch plan.docx",
            "disposition": "tracked",
            "active": True,
            "private_path": "synthetic://private/Launch plan.docx",
        },
    )


def _image_bytes(color: str) -> bytes:
    image = Image.new("RGB", (640, 400), color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_browser_is_bilingual_filterable_and_evidence_bound(tmp_path: Path) -> None:
    service = _service(tmp_path)
    _seed_matter(service)

    browser = service.object_browser_projection(locale="zh-CN")
    card = browser["catalog"]["items"][0]
    detail = service.matter_detail(matter_id="matter:launch", locale="zh-CN")
    evidence = service.matter_evidence(matter_id="matter:launch")

    assert browser["surface"] == "object_browser"
    assert browser["default_locale"] == "en"
    assert browser["available_locales"] == ("en", "zh-CN")
    assert card["title"] == {
        "en": "Prepare the product launch",
        "zh-CN": "准备产品发布",
    }
    assert card["status_group"] == "in_progress"
    assert card["event_count"] == 1
    assert card["people_count"] == 0
    assert card["source_count"] == 1
    assert service.object_catalog_page(
        locale="zh-CN",
        query="产品",
        status="in_progress",
    )["total_count"] == 1
    grouped = service.object_catalog_page(
        start_year="2026",
        relationships=("depends_on",),
        topic_types=("product_launch",),
        source_types=("document",),
    )
    assert grouped["total_count"] == 1
    assert grouped["facets"]["start_year"][0]["value"] == "2026"
    assert grouped["facets"]["relationships"][0]["value"] == "depends_on"
    assert grouped["facets"]["topic_types"][0]["label"]["zh-CN"] == "产品发布"
    assert grouped["facets"]["source_types"][0]["label"]["zh-CN"] == "文档"
    assert grouped["filters"]["sort"] == "activity"
    for retired_sort in ("recent", "title", "state"):
        with pytest.raises(ValueError, match="unsupported catalog sort"):
            service.object_catalog_page(sort=retired_sort)
    assert service.object_catalog_page(source_types=("image",))["total_count"] == 0
    assert detail["timeline"][0]["sentence"]["zh-CN"].startswith("产品计划")
    assert detail["timeline"][0]["claimed_time"] == "2026-08-05"
    assert detail["timeline"][0]["record_time"].startswith("2026-07-18")
    assert detail["timeline"][0]["modality"] == "planned"


    assert detail["primary_sections"] == (
        "overview",
        "sub_matters",
        "timeline",
        "people",
        "related_matters",
        "files_and_information",
        "images",
        "ai_supplemental_information",
    )
    assert tuple(detail["sections"]) == detail["primary_sections"]
    file_row = detail["files_and_information"]["items"][0]
    assert file_row["label"]["en"] == "Launch plan.docx"
    assert file_row["type"]["zh-CN"] == "文档"
    assert file_row["availability"]["label"]["zh-CN"] == "可用"
    assert set(file_row) == {
        "record_ref",
        "label",
        "type",
            "kind",
            "provider",
            "privacy_safe_location",
            "location_group",
        "observed_time",
        "relevant_time",
        "summary",
        "availability",
        "modalities",
        "evidence_available",
        "history_available",
        }
    assert file_row["privacy_safe_location"]["en"]
    assert "private" not in file_row["privacy_safe_location"]["en"].casefold()
    assert file_row["modalities"] == ("reported",)
    serialized_detail = str(detail)
    assert "occurrence:launch" not in serialized_detail
    assert "filesystem" not in serialized_detail
    assert "owner:" not in serialized_detail
    assert "next_stage" not in serialized_detail
    assert "private_path" not in serialized_detail
    assert detail["open_loops"] == ()
    assert detail["related_matters"] == ()
    assert evidence["items"][0]["excerpt"].startswith("Launch is planned")
    assert "private_path" not in evidence["items"][0]["location"]


def test_browser_uses_published_coverage_checkpoint_for_first_paint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    _seed_matter(service)
    assert service.coverage_ledger is not None
    assert service.store is not None
    service.coverage_ledger.refresh_summary()

    def reject_exact_whole_ledger_scan() -> dict[str, object]:
        raise AssertionError(
            "the catalog shell must not run the exact whole-ledger contract"
        )

    monkeypatch.setattr(
        service.store,
        "coverage_contract_status",
        reject_exact_whole_ledger_scan,
    )

    browser = service.object_browser_projection(locale="en")

    assert browser["catalog"]["total_count"] == 1
    assert (
        browser["coverage"]["summary_freshness"]
        == "persisted_background_checkpoint"
    )


def test_files_table_collapses_historical_versions_of_one_source(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    _seed_matter(service)
    matter_id = "matter:launch"
    source_id = "source:launch-plan"
    external_id = "occurrence:launch"
    for version, summary in (
        (1, "Earlier launch plan"),
        (2, "Current launch plan"),
    ):
        _append_current(
            service,
            "source_version",
            source_id,
            {
                "source_id": source_id,
                "version": version,
                "provider": "filesystem",
                "external_reference": {
                    "external_id": external_id,
                    "object_type": "document",
                    "provider": "filesystem",
                },
                "content": {
                    "title": "Launch plan.docx",
                    "summary": summary,
                },
            },
        )
    admission = service.store.current("admission_decision", matter_id)
    assert admission is not None
    _append_current(
        service,
        "admission_decision",
        matter_id,
        {
            **admission,
            "matter": {
                **dict(admission["matter"]),
                "source_ids": (
                    f"{source_id}:v1",
                    f"{source_id}:v2",
                ),
            },
        },
    )

    files = service.matter_detail(
        matter_id=matter_id,
        locale="en",
    )["files_and_information"]

    assert files["total_count"] == 1
    assert len(files["items"]) == 1
    assert files["items"][0]["summary"]["en"] == "Current launch plan"
    assert files["items"][0]["history_available"] is True


def test_superseded_analysis_event_is_preserved_but_hidden_until_rebuilt(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    _seed_matter(service)
    assert service.store is not None
    output_ref = "temporal_event:event:launch"
    _append_current(
        service,
        "autonomous_finding",
        "finding:legacy-launch",
        {
            "finding_id": "finding:legacy-launch",
            "package_id": "work:legacy-launch",
            "status": "auto_applied",
            "owner_output_ref": output_ref,
        },
    )
    _append_current(
        service,
        "analysis_result_invalidation",
        "work:legacy-launch",
        {
            "package_id": "work:legacy-launch",
            "status": "superseded",
            "replacement_package_id": "work:current-launch",
        },
    )
    _append_current(
        service,
        "analysis_output_invalidation",
        "analysis-output-invalidation:legacy-launch",
        {
            "invalidation_id": "analysis-output-invalidation:legacy-launch",
            "output_ref": output_ref,
            "old_package_id": "work:legacy-launch",
            "replacement_package_id": "work:current-launch",
            "status": "superseded",
        },
    )

    card = service.object_browser_projection(locale="en")["catalog"]["items"][0]
    detail = service.matter_detail(matter_id="matter:launch", locale="en")
    graph = service.matter_situation_graph(
        matter_id="matter:launch",
        locale="en",
    )

    assert service.store.current("temporal_event", "event:launch") is not None
    assert card["event_count"] == 0
    assert detail["timeline"] == ()
    assert graph["coverage"] == "partial"
    assert "analysis_output_replacement_pending" in graph["coverage_gaps"]
    assert all(
        item["node_id"] != "event:launch"
        for item in graph["nodes"]
    )


def test_superseded_matter_outputs_are_pending_until_current_owner_rebuilds(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    _seed_matter(service)
    assert service.store is not None
    output_refs = (
        "projection:matter:launch",
        "admission_decision:matter:launch",
    )
    for index, output_ref in enumerate(output_refs):
        _append_current(
            service,
            "autonomous_finding",
            f"finding:legacy-launch:{index}",
            {
                "finding_id": f"finding:legacy-launch:{index}",
                "package_id": "work:legacy-launch",
                "status": "auto_applied",
                "owner_output_ref": output_ref,
            },
        )
        _append_current(
            service,
            "analysis_output_invalidation",
            f"analysis-output-invalidation:legacy-launch:{index}",
            {
                "invalidation_id": (
                    f"analysis-output-invalidation:legacy-launch:{index}"
                ),
                "output_ref": output_ref,
                "old_package_id": "work:legacy-launch",
                "replacement_package_id": "work:current-launch",
                "status": "superseded",
            },
        )
    _append_current(
        service,
        "analysis_result_invalidation",
        "work:legacy-launch",
        {
            "package_id": "work:legacy-launch",
            "status": "superseded",
            "replacement_package_id": "work:current-launch",
        },
    )

    assert service.object_catalog_page()["total_count"] == 0
    with pytest.raises(KeyError, match="matter is unavailable"):
        service.matter_detail(matter_id="matter:launch")
    with pytest.raises(KeyError, match="matter is unavailable"):
        service.matter_evidence(matter_id="matter:launch")
    assert service.store.current("projection", "matter:launch") is not None
    assert service.store.current(
        "admission_decision",
        "matter:launch",
    ) is not None

    for index, output_ref in enumerate(output_refs):
        _append_current(
            service,
            "autonomous_finding",
            f"finding:current-launch:{index}",
            {
                "finding_id": f"finding:current-launch:{index}",
                "package_id": "work:current-launch",
                "status": "auto_applied",
                "owner_output_ref": output_ref,
            },
        )

    assert service.object_catalog_page()["total_count"] == 1
    assert service.matter_detail(
        matter_id="matter:launch"
    )["matter"]["matter_id"] == "matter:launch"


def test_related_matters_require_shared_current_evidence_link(tmp_path: Path) -> None:
    service = _service(tmp_path)
    _seed_matter(service)
    _append_current(
        service,
        "projection",
        "matter:follow-up",
        {
            "matter_id": "matter:follow-up",
            "semantic_revision": "semantic:follow-up:v1",
            "state": "planned",
            "evidence_ids": ("evidence:launch",),
            "localized_values": {
                "en": "Prepare the launch follow-up",
                "zh-CN": "准备发布后续工作",
            },
            "localized_rationale": {
                "en": "The follow-up uses the same launch evidence.",
                "zh-CN": "后续工作使用同一份发布证据。",
            },
            "equivalence_status": "equivalent",
        },
    )
    _append_current(
        service,
        "admission_decision",
        "matter:follow-up",
        {
            "matter_id": "matter:follow-up",
            "status": "admitted",
            "rationale": "current evidence licenses admission",
            "matter": {"matter_id": "matter:follow-up"},
        },
    )
    _append_current(
        service,
        "object_coverage",
        "occurrence:follow-up",
        {
            "object_id": "occurrence:follow-up",
            "provider": "filesystem",
            "object_type": "document",
            "disposition": "tracked",
            "matter_ids": ("matter:follow-up",),
        },
    )

    detail = service.matter_detail(matter_id="matter:launch", locale="en")

    assert detail["related_matters"][0]["matter_id"] == "matter:follow-up"
    assert detail["related_matters"][0]["shared_people_count"] == 0
    assert detail["related_matters"][0]["shared_source_count"] == 0
    assert detail["related_matters"][0]["shared_evidence_count"] == 1


def test_generated_hero_is_separate_from_real_images_gallery(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    _seed_matter(service)
    assert service.visuals is not None
    first = service.visuals.register_image(
        source_revision_id="source:launch:v1",
        occurrence_id="occurrence:launch",
        content=_image_bytes("#1b4d6b"),
        media_type="image/png",
        evidence_ids=("evidence:launch",),
        photo=True,
    )
    second = service.visuals.register_image(
        source_revision_id="source:launch:v1",
        occurrence_id="occurrence:launch",
        content=_image_bytes("#c8102e"),
        media_type="image/png",
        evidence_ids=("evidence:launch",),
        photo=False,
    )

    assert service.heroes is not None
    pending = service.heroes.prepare(
        HeroSubject(
            object_id="matter:launch",
            object_kind="matter",
            semantic_identity_id="semantic-identity:launch",
            topic_concepts=("product launch",),
            theme_concepts=("software release demonstration workspace",),
            hierarchy_revision="hierarchy:launch:v1",
            is_root=True,
            independently_openable=True,
        )
    )
    generated = service.register_generated_hero(
        matter_id="matter:launch",
        brief_fingerprint=pending.brief_fingerprint,
        content=_image_bytes("#476d89"),
        media_type="image/png",
        localized_alt={
            "en": "Documentary photograph of a product launch workspace",
            "zh-CN": "产品发布工作现场的纪实照片",
        },
        runner_contract_id="hero-runner-contract:v1",
        execution_identity="test-private-execution",
    )
    body, media_type = service.resolve_generated_hero(
        preview_token=generated["preview_token"],
    )
    card = service.object_catalog_page()["items"][0]
    detail = service.matter_detail(matter_id="matter:launch", locale="en")
    gallery = detail["images"]

    assert card["hero"] == {
        "status": "generated_current",
        "preview_token": generated["preview_token"],
        "alt": {
            "en": "Documentary photograph of a product launch workspace",
            "zh-CN": "产品发布工作现场的纪实照片",
        },
        "generation_revision": 2,
    }
    assert body.startswith(b"\x89PNG\r\n\x1a\n")
    assert media_type == "image/png"
    assert gallery["selected_preview_token"] == first.preview_token
    assert gallery["items"][0]["preview_token"] == first.preview_token
    assert gallery["items"][0]["thumbnail_preview_token"] == first.preview_token
    assert gallery["items"][0]["localized_alt"] == gallery["items"][0]["alt"]
    assert {
        item["preview_token"] for item in gallery["items"]
    } == {first.preview_token, second.preview_token}
    assert generated["preview_token"] not in str(gallery)
    assert "asset_id" not in str(gallery)
    assert "occurrence_id" not in str(gallery)


def test_real_visual_asset_never_gains_generated_hero_authority(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    _seed_matter(service)
    assert service.visuals is not None
    asset = service.visuals.register_image(
        source_revision_id="source:launch:v1",
        occurrence_id="occurrence:launch",
        content=_image_bytes("#1b4d6b"),
        media_type="image/png",
        evidence_ids=("evidence:launch",),
        photo=True,
    )
    card = service.object_catalog_page()["items"][0]
    gallery = service.matter_detail(
        matter_id="matter:launch",
        locale="en",
    )["images"]

    assert card["hero"]["status"] == "generation_pending_placeholder"
    assert card["hero"]["preview_token"] == ""
    assert "visual" not in card
    assert gallery["items"][0]["preview_token"] == asset.preview_token


def test_optional_correction_is_auto_applied_without_approval_queue(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    _seed_matter(service)

    result = service.submit_matter_correction(
        matter_id="matter:launch",
        field_name="state",
        corrected_value="completed",
        rationale="The launch work has now finished.",
    )
    card = service.object_catalog_page(status="completed")["items"][0]

    assert result["status"] == "auto_applied"
    assert result["recompute_status"] == "passed"
    assert card["state"] == "completed"
    assert not hasattr(service, "submit_understanding_intent")
    assert not hasattr(service, "review_catalog_page")
    assert not hasattr(service, "set_matter_cover")
