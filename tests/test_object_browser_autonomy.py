from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image

from matters.application.orchestrator import MatterService


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
            "required_stages": (
                "inventory",
                "analysis",
                "matter",
                "localization",
                "visual",
                "ui_projection",
            ),
            "stages": {
                stage_id: {
                    "stage_id": stage_id,
                    "status": "current",
                    "owner_id": f"owner:{stage_id}",
                    "input_fingerprint": "sha256:test",
                    "output_ref": f"{stage_id}:launch",
                }
                for stage_id in (
                    "inventory",
                    "analysis",
                    "matter",
                    "localization",
                    "visual",
                    "ui_projection",
                )
            },
            "revision": 1,
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
    assert detail["timeline"][0]["sentence"]["zh-CN"].startswith("产品计划")
    assert detail["timeline"][0]["claimed_time"] == "2026-08-05"
    assert detail["timeline"][0]["record_time"].startswith("2026-07-18")
    assert detail["timeline"][0]["modality"] == "planned"
    assert detail["sources"][0]["disposition_label"]["zh-CN"] == "已跟踪"
    assert detail["open_loops"] == ()
    assert detail["related_matters"] == ()
    assert evidence["items"][0]["excerpt"].startswith("Launch is planned")
    assert "private_path" not in evidence["items"][0]["location"]


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


def test_visual_authority_prefers_ai_then_user_override_and_resolves_bytes(
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

    automatic = service.visuals.decide(
        matter_id="matter:launch",
        semantic_revision="semantic:launch:v1",
        occurrence_ids=("occurrence:launch",),
        recommended_asset_id=second.asset_id,
    )
    override = service.set_matter_cover(
        matter_id="matter:launch",
        asset_id=first.asset_id,
        active=True,
        rationale="The photo is easier to recognize.",
    )
    body, media_type = service.resolve_visual_preview(
        preview_token=override.preview_token,
        hero=True,
    )

    assert automatic.asset_id == second.asset_id
    assert automatic.selection_mode == "ai_recommendation"
    assert override.asset_id == first.asset_id
    assert override.selection_mode == "user_override"
    assert body.startswith(b"\xff\xd8")
    assert media_type == "image/jpeg"


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
