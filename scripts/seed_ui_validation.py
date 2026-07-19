"""Seed a deterministic public-data runtime for installed UI validation."""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path
import shutil

from PIL import Image

from matters.application.orchestrator import MatterService


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

    for index in range(count):
        matter_id = f"matter:ui-validation:{index:03d}"
        evidence_id = f"evidence:ui-validation:{index:03d}"
        occurrence_id = f"occurrence:ui-validation:{index:03d}"
        state = ("planned", "in_progress", "completed")[index % 3]
        claimed_time = f"2026-{(index % 12) + 1:02d}-{(index % 27) + 1:02d}"
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
                    "en": f"Deterministic public-data summary for matter {index:03d}.",
                    "zh-CN": f"事项 {index:03d} 的确定性公开测试摘要。",
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
            },
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
                "required_stages": ("inventory", "analysis", "matter", "ui_projection"),
                "stages": {
                    stage: {
                        "stage_id": stage,
                        "status": "current",
                        "owner_id": f"owner:{stage}",
                        "input_fingerprint": "sha256:public-validation",
                        "output_ref": f"{stage}:{index:03d}",
                    }
                    for stage in ("inventory", "analysis", "matter", "ui_projection")
                },
                "revision": 1,
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
    service.visuals.decide(
        matter_id="matter:ui-validation:229",
        semantic_revision="semantic:ui-validation:229:v1",
        occurrence_ids=("occurrence:ui-validation:229",),
        recommended_asset_id=asset.asset_id,
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
        "representative_visual_count": 1,
        "placeholder_count": count - 1,
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
        f"{result['representative_visual_count']} visual, "
        f"{result['blocked_object_count']} isolated blocker."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
