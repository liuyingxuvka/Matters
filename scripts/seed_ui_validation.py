"""Seed a deterministic public-data runtime for installed UI validation."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from io import BytesIO
import json
from pathlib import Path
import shutil

from PIL import Image

from matters.application.coverage_ledger import STAGE_ORDER
from matters.application.orchestrator import MatterService
from matters.domain.activity import MaterialClue
from matters.domain.matters import Matter
from matters.presentation.heroes import HeroSubject


def _append(
    service: MatterService,
    owner: str,
    key: str,
    payload: dict[str, object],
) -> None:
    if service.store is None:
        raise RuntimeError("Matters store is unavailable")
    service.store.append(
        owner,
        key,
        service.store.next_revision(owner, key),
        payload,
    )


def _hero_bytes() -> bytes:
    image = Image.new("RGB", (1280, 720), "#274d6b")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _human_summary(index: int) -> dict[str, str]:
    if index in {228, 229}:
        return {
            "en": (
                "The latest meaningful progress in the child phase now updates "
                "the overall project view."
            ),
            "zh-CN": "子阶段出现了新的实质进展，整个项目的最新情况也已随之更新。",
        }
    return {
        "en": (
            f"Validation matter {index:03d} brings its latest known project "
            "progress into one clear view."
        ),
        "zh-CN": f"验证事项 {index:03d} 汇总了目前已知的项目进展，并会随着新线索持续更新。",
    }


def seed(target: Path, *, count: int = 230) -> dict[str, object]:
    if count < 210:
        raise ValueError("UI validation requires at least 210 Matters")
    target = target.resolve()
    if (
        len(target.parts) < 3
        or not target.name.startswith("matters-ui-validation-")
    ):
        raise ValueError(
            "validation target must be a bounded directory named "
            "'matters-ui-validation-*'"
        )
    if target.exists():
        shutil.rmtree(target)
    repository = target / "repository"
    private = target / "private"
    repository.mkdir(parents=True)
    service = MatterService(repository_root=repository, private_root=private)
    (private / ".matters-synthetic-fixture.json").write_text(
        json.dumps({"isolated": True, "synthetic": True}) + "\n",
        encoding="utf-8",
    )

    for index in range(count):
        matter_id = f"matter:ui-validation:{index:03d}"
        evidence_id = f"evidence:ui-validation:{index:03d}"
        occurrence_id = f"occurrence:ui-validation:{index:03d}"
        state = ("planned", "in_progress", "completed")[index % 3]
        claimed_time = f"2026-{(index % 12) + 1:02d}-{(index % 27) + 1:02d}"
        human_summary = _human_summary(index)
        matter = Matter(
            matter_id=matter_id,
            source_ids=(f"source:ui-validation:{index:03d}",),
            rationale="public UI validation fixture",
            evidence_ids=(evidence_id,),
            semantic_identity_id=f"semantic:ui-validation:{index}",
        )
        _append(
            service,
            "evidence_anchor",
            evidence_id,
            {
                "evidence_id": evidence_id,
                "text": f"Public UI validation evidence {index}.",
                "modality": "reported",
                "location": {"line_start": index + 1, "line_end": index + 1},
            },
        )
        _append(
            service,
            "projection",
            matter_id,
            {
                "matter_id": matter_id,
                "semantic_revision": f"semantic:ui-validation:{index}:v1",
                "state": state,
                "evidence_ids": (evidence_id,),
                "localized_values": {
                    "en": f"Validation matter {index:03d}",
                    "zh-CN": f"验证事项 {index:03d}",
                },
                "localized_rationale": {
                    "en": human_summary["en"],
                    "zh-CN": human_summary["zh-CN"],
                },
                "equivalence_status": "equivalent",
            },
        )
        _append(
            service,
            "admission_decision",
            matter_id,
            {
                "matter_id": matter_id,
                "status": "admitted",
                "rationale": "public UI validation fixture",
                "candidate": None,
                "matter": asdict(matter),
            },
        )
        service.admission.restore(matter)
        if service.hierarchy is None:
            raise RuntimeError("hierarchy owner is unavailable")
        service.hierarchy.register_matter(
            matter_id,
            change_ref="fixture:public-ui-validation",
        )
        _append(
            service,
            "temporal_event",
            f"event:ui-validation:{index:03d}",
            {
                "event_id": f"event:ui-validation:{index:03d}",
                "kind": "milestone",
                "modality": "planned" if state == "planned" else "reported",
                "record_time": "2026-07-18T12:00:00Z",
                "claimed_time": claimed_time,
                "object_ref": matter_id,
                "evidence_ids": (evidence_id,),
                "localized_sentence": {
                    "en": f"Validation matter {index:03d} is recorded for {claimed_time}.",
                    "zh-CN": f"验证事项 {index:03d} 记录于 {claimed_time}。",
                },
                "confidence": 0.9,
                "conflict": False,
            },
        )
        if service.activity is None:
            raise RuntimeError("activity owner is unavailable")
        service.activity.record(
            MaterialClue(
                clue_id=f"clue:ui-validation:{index:03d}",
                matter_id=matter_id,
                clue_kind="milestone",
                user_world_at=f"{claimed_time}T12:00:00Z",
                disposition="material",
                rationale="public UI validation fixture",
                localized_summary={
                    "en": human_summary["en"],
                    "zh-CN": human_summary["zh-CN"],
                },
                semantic_revision=f"semantic:ui-validation:{index}:v1",
                evidence_ids=(evidence_id,),
            )
        )
        _append(
            service,
            "object_coverage",
            occurrence_id,
            {
                "object_id": occurrence_id,
                "provider": "public_validation",
                "object_type": "document",
                "scope_id": "scope:public-validation",
                "inventory_revision": 1,
                "disposition": "tracked",
                "matter_ids": (matter_id,),
                "required_stages": STAGE_ORDER,
                "stages": {
                    stage: {
                        "stage_id": stage,
                        "status": (
                            "pending"
                            if stage == "generated_hero"
                            else "current"
                        ),
                        "owner_id": f"owner:{stage}",
                        "input_fingerprint": "sha256:public-validation",
                        "output_ref": (
                            ""
                            if stage == "generated_hero"
                            else f"{stage}:{index:03d}"
                        ),
                    }
                    for stage in STAGE_ORDER
                },
                "revision": 1,
            },
        )

    service.attach_matter_child(
        parent_matter_id="matter:ui-validation:229",
        child_matter_id="matter:ui-validation:228",
        role="required",
        confidence="supported",
        rationale="public UI validation hierarchy fixture",
        evidence_ids=("evidence:ui-validation:228",),
        ordinal=1,
    )
    service.upsert_matter_work_item(
        item_id="work-item:ui-validation:229:pending",
        matter_id="matter:ui-validation:229",
        kind="action",
        status="in_progress",
        localized_title={
            "en": "Complete the next project phase",
            "zh-CN": "完成下一项目阶段",
        },
        localized_result={
            "en": "The next step is still in progress.",
            "zh-CN": "下一步仍在进行中。",
        },
        evidence_ids=("evidence:ui-validation:229",),
        planned_start="2026-12-30T09:00:00Z",
        required_for_parent=True,
        freshness="current",
    )
    if service.activity is None:
        raise RuntimeError("activity owner is unavailable")
    service.activity.record(
        MaterialClue(
            clue_id="clue:ui-validation:228:child-progress",
            matter_id="matter:ui-validation:228",
            clue_kind="milestone",
            user_world_at="2026-12-31T23:00:00Z",
            disposition="material",
            rationale="public child clue must bubble to its parent",
            localized_summary={
                "en": _human_summary(228)["en"],
                "zh-CN": _human_summary(228)["zh-CN"],
            },
            semantic_revision="semantic:ui-validation:228:v1",
            evidence_ids=("evidence:ui-validation:228",),
        )
    )
    service.activity.record(
        MaterialClue(
            clue_id="clue:ui-validation:229:processing-only",
            matter_id="matter:ui-validation:229",
            clue_kind="scan",
            user_world_at="2027-01-01T12:00:00Z",
            processed_at="2027-01-01T12:00:00Z",
            disposition="nonmaterial",
            rationale="backend processing is not user-world progress",
        )
    )
    _append(
        service,
        "matter_supplemental_information",
        "matter:ui-validation:229",
        {
            "matter_id": "matter:ui-validation:229",
            "semantic_revision": "semantic:ui-validation:229:v1",
            "status": "current",
            "items": (
                {
                    "kind": "background",
                    "localized_title": {
                        "en": "Useful background",
                        "zh-CN": "有用的背景信息",
                    },
                    "localized_body": {
                        "en": "This advisory context is supplemental and is not source evidence.",
                        "zh-CN": "此内容仅为补充建议，并不是来源证据。",
                    },
                    "relevant_time": "2026-12-31T23:00:00Z",
                    "freshness": "current",
                    "evidence_ids": (),
                },
            ),
        },
    )

    if service.visuals is None:
        raise RuntimeError("visual service is unavailable")
    asset = service.visuals.register_image(
        source_revision_id="source:ui-validation:v1",
        occurrence_id="occurrence:ui-validation:229",
        content=_hero_bytes(),
        media_type="image/png",
        evidence_ids=("evidence:ui-validation:229",),
        photo=True,
    )
    if service.heroes is None:
        raise RuntimeError("generated Hero owner is unavailable")
    pending_hero = service.heroes.prepare(
        HeroSubject(
            object_id="matter:ui-validation:229",
            object_kind="matter",
            semantic_identity_id="semantic:ui-validation:229",
            topic_concepts=("product launch",),
            theme_concepts=("software release demonstration workspace",),
            hierarchy_revision="hierarchy:ui-validation:1",
            is_root=True,
            independently_openable=True,
        )
    )
    service.register_generated_hero(
        matter_id="matter:ui-validation:229",
        brief_fingerprint=pending_hero.brief_fingerprint,
        content=_hero_bytes(),
        media_type="image/png",
        localized_alt={
            "en": "Documentary photograph of a product launch workspace",
            "zh-CN": "产品发布工作现场的纪实照片",
        },
        runner_contract_id="public-ui-validation:generated-hero:v1",
        execution_identity="public-ui-validation:deterministic-image:v1",
    )
    _append(
        service,
        "object_coverage",
        "occurrence:ui-validation:blocked",
        {
            "object_id": "occurrence:ui-validation:blocked",
            "provider": "public_validation",
            "object_type": "document",
            "scope_id": "scope:public-validation",
            "inventory_revision": 1,
            "disposition": "blocked",
            "matter_ids": (),
            "required_stages": ("authorization", "inventory", "source_version"),
            "stages": {
                "authorization": {
                    "stage_id": "authorization",
                    "status": "current",
                    "owner_id": "C1_authorization_coverage",
                    "input_fingerprint": "sha256:public-validation",
                    "output_ref": "scope:public-validation",
                },
                "inventory": {
                    "stage_id": "inventory",
                    "status": "current",
                    "owner_id": "C1_authorization_coverage",
                    "input_fingerprint": "sha256:public-validation",
                    "output_ref": "inventory:public-validation:1",
                },
                "source_version": {
                    "stage_id": "source_version",
                    "status": "blocked",
                    "owner_id": "C2_source_registry",
                    "input_fingerprint": "sha256:public-validation",
                    "failure_class": "public_validation_isolated_blocker",
                },
            },
            "revision": 1,
        },
    )
    if service.coverage_ledger is None:
        raise RuntimeError("coverage ledger is unavailable")
    service.coverage_ledger.record_worker_state(
        worker_health="idle",
        worker_checkpoint="public-ui-validation-seeded",
    )
    return {
        "target": str(target),
        "matter_count": count,
        "generated_hero_count": 1,
        "gallery_image_count": 1,
        "placeholder_count": count - 1,
        "hierarchy_child_count": 1,
        "supplemental_information_count": 1,
        "blocked_object_count": 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--count", type=int, default=230)
    args = parser.parse_args()
    result = seed(args.target, count=args.count)
    print(
        "Seeded public UI validation runtime: "
        f"{result['matter_count']} Matters, "
        f"{result['generated_hero_count']} generated Hero, "
        f"{result['gallery_image_count']} gallery image, "
        f"{result['blocked_object_count']} isolated blocker."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
