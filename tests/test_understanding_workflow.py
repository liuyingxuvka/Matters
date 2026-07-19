from pathlib import Path

from matters.application.orchestrator import MatterService
from matters.application.source_workflows import SourceWorkflow
from matters.providers.filesystem import FilesystemReadOnlyAdapter


def _service(tmp_path: Path) -> MatterService:
    repository = tmp_path / "repository"
    repository.mkdir()
    return MatterService(
        repository_root=repository,
        private_root=tmp_path / "private",
    )


def _queued_service(tmp_path: Path) -> tuple[MatterService, dict]:
    source_root = tmp_path / "documents"
    source_root.mkdir()
    (source_root / "plan.txt").write_text(
        "Prepare the launch plan\nWait for design approval\n",
        encoding="utf-8",
    )
    service = _service(tmp_path)
    SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
    )
    page = service.pending_analysis_packages(offset=0, limit=20)
    assert page["total_count"] == 1
    return service, page["items"][0]


def _input_dispositions(package: dict) -> list[dict[str, str]]:
    return [
        {
            "input_id": input_id,
            "disposition": "used",
            "reason": "Supports the bounded autonomous result.",
        }
        for input_id in (
            *package["allowed_evidence_ids"],
            *package["allowed_asset_ids"],
        )
    ]


def _autonomous_result(package: dict) -> dict:
    evidence_id = package["allowed_evidence_ids"][0]
    source_revision = package["source_revision_ids"][0]
    return {
        "status": "passed",
        "input_dispositions": _input_dispositions(package),
        "findings": [
            {
                "finding_type": "matter_candidate",
                "owner_model_id": "C6_matter_admission",
                "statement": "Prepare the launch plan",
                "localized_statement": {
                    "en": "Prepare the launch plan",
                    "zh-CN": "准备发布计划",
                },
                "semantic_revision": source_revision,
                "evidence_ids": [evidence_id],
                "confidence": "bounded",
                "modality": "observed",
                "attributes": {
                    "explicit_goal_or_obligation": True,
                },
            },
            {
                "finding_type": "bounded_summary",
                "owner_model_id": "C12_projection_bilingual_ui",
                "statement": "Prepare the launch plan",
                "localized_statement": {
                    "en": "Prepare the launch plan",
                    "zh-CN": "准备发布计划",
                },
                "semantic_revision": source_revision,
                "evidence_ids": [evidence_id],
                "confidence": "bounded",
                "modality": "inferred",
                "attributes": {"state": "in_progress"},
            },
        ],
    }


def test_real_source_anchor_queues_bounded_private_work_package_v2(tmp_path: Path):
    _service_value, package = _queued_service(tmp_path)

    assert package["package_version"] == 2
    assert package["operation_type"] == "text_analysis"
    assert package["model_revision"] == "matters-semantic-understanding:v2"
    assert package["allowed_evidence_ids"]
    assert package["prompt_contract_revision"] == "v2"
    assert package["required_locales"] == ["en", "zh-CN"]
    assert package["auto_apply_policy"] == (
        "validate_then_dispatch_original_owner"
    )
    assert package["human_confirmation_required"] is False
    assert package["control_contract"]["human_confirmation_required"] is False
    assert package["untrusted_evidence"]["required_output"][
        "human_confirmation_required"
    ] is False
    assert "absolute_path" not in str(package)


def test_bilingual_ai_result_auto_dispatches_to_original_owners(
    tmp_path: Path,
    monkeypatch,
):
    service, package = _queued_service(tmp_path)
    summary_refreshes = 0
    original_summary = service.coverage_ledger._save_summary

    def counted_summary():
        nonlocal summary_refreshes
        summary_refreshes += 1
        return original_summary()

    monkeypatch.setattr(
        service.coverage_ledger,
        "_save_summary",
        counted_summary,
    )

    imported = service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result=_autonomous_result(package),
    )

    assert imported == {
        "status": "passed",
        "result_id": (
            f"result:{package['package_id']}:{package['package_version']}"
        ),
        "finding_count": 2,
        "dispatch_count": 2,
        "dispatch_statuses": ("auto_applied", "auto_applied"),
        "advisory_only": True,
        "auto_apply_status": "auto_applied",
    }
    admissions = service.current_records("admission_decision")
    admitted = [row for row in admissions if row["status"] == "admitted"]
    assert len(admitted) == 1

    page = service.object_catalog_page(locale="en")
    assert page["total_count"] == 1
    card = page["items"][0]
    assert card["title"] == {
        "en": "Prepare the launch plan",
        "zh-CN": "准备发布计划",
    }
    assert card["status_group"] == "in_progress"
    assert card["visual"]["status"] == "current"
    assert card["visual"]["preview_token"]
    assert service.pending_analysis_packages()["total_count"] == 0
    assert summary_refreshes == 1


def test_missing_bilingual_value_is_blocked_and_creates_no_matter(
    tmp_path: Path,
):
    service, package = _queued_service(tmp_path)
    imported = service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result={
            "status": "passed",
            "input_dispositions": _input_dispositions(package),
            "findings": [
                {
                    "finding_type": "bounded_summary",
                    "owner_model_id": "C12_projection_bilingual_ui",
                    "statement": "One-language result",
                    "localized_statement": {"en": "One-language result"},
                    "semantic_revision": package["source_revision_ids"][0],
                    "evidence_ids": [package["allowed_evidence_ids"][0]],
                }
            ],
        },
    )

    assert imported["status"] == "blocked"
    assert imported["auto_apply_status"] == "blocked"
    assert imported["finding_count"] == 0
    assert service.object_catalog_page()["total_count"] == 0
