from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path

from matters.analysis.operations import AnalysisWorkPackage
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
    project = source_root / "Project"
    project.mkdir()
    (project / "plan.txt").write_text(
        "Prepare the launch plan\nWait for design approval\n",
        encoding="utf-8",
    )
    service = _service(tmp_path)
    SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
        content_limit=20,
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
                "statement": "Launch planning is under way.",
                "localized_statement": {
                    "en": "Launch planning is under way.",
                    "zh-CN": "发布计划正在推进中。",
                },
                "semantic_revision": source_revision,
                "evidence_ids": [evidence_id],
                "confidence": "bounded",
                "modality": "inferred",
                "attributes": {"state": "in_progress"},
            },
        ],
    }


def _person_result(package: dict, *, matter_id: str) -> dict:
    evidence_id = package["allowed_evidence_ids"][0]
    source_revision = package["source_revision_ids"][0]
    return {
        "status": "passed",
        "input_dispositions": _input_dispositions(package),
        "findings": [
            {
                "finding_type": "person_candidate",
                "owner_model_id": "C4_person_entity_resolution",
                "statement": "Jenna is the named customer support contact.",
                "localized_statement": {
                    "en": "Jenna",
                    "zh-CN": "Jenna",
                },
                "semantic_revision": source_revision,
                "evidence_ids": [evidence_id],
                "confidence": "bounded",
                "modality": "reported",
                "attributes": {
                    "matter_id": matter_id,
                    "display_name": "Jenna",
                    "role": "customer_support_contact",
                    "strong_link_evidence": False,
                },
            },
        ],
    }


def _annotation_result(package: dict) -> dict:
    evidence_id = package["allowed_evidence_ids"][0]
    source_revision = package["source_revision_ids"][0]
    return {
        "status": "passed",
        "input_dispositions": _input_dispositions(package),
        "findings": [
            {
                "finding_type": "source_annotation",
                "owner_model_id": "A0_matters_source_analysis_operation",
                "statement": "A launch plan with a pending design dependency",
                "localized_statement": {
                    "en": "A launch plan with a pending design dependency",
                    "zh-CN": "一项等待设计审批的发布计划",
                },
                "semantic_revision": source_revision,
                "evidence_ids": [evidence_id],
                "confidence": "bounded",
                "modality": "observed",
                "attributes": {
                    "content_kind": "user_plan",
                    "user_relevance": "likely_relevant",
                    "key_terms": ["launch plan", "design approval"],
                },
            },
        ],
    }


def _advance_to_semantic(service: MatterService, package: dict) -> dict:
    imported = service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result=_annotation_result(package),
    )
    assert imported["status"] == "passed"
    assert imported["followup_capability_role"] == "matter_modeler"
    page = service.pending_analysis_packages(offset=0, limit=20)
    assert page["total_count"] == 1
    semantic = page["items"][0]
    assert semantic["package_id"] == imported["followup_package_id"]
    return semantic


def test_real_source_anchor_queues_bounded_private_work_package_v2(tmp_path: Path):
    service, package = _queued_service(tmp_path)

    assert package["package_version"] == 2
    assert package["operation_type"] == "text_analysis"
    assert package["task_kind"] == "source_annotation"
    assert package["capability_role"] == "low_cost_annotator"
    assert package["requested_output_types"] == ["source_annotation"]
    assert package["model_revision"] == "matters-source-annotation:v1"
    assert package["required_runner_id"] == "codex-hosted-capability-router"
    assert package["required_runner_version"] == "capability-contract-v1"
    assert package["execution_profile_contract_id"].startswith(
        "execution-profile-contract:"
    )
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
    assert "luna" not in str(package).casefold()
    assert "terra" not in str(package).casefold()
    assert "absolute_path" not in str(package)
    private_package = service.store.current(
        "analysis_work_package",
        package["package_id"],
    )
    source_context = private_package["untrusted_evidence"]["source_context"]
    assert source_context["source_group_labels"] == ["Project"]
    assert source_context["source_spatial_context_revision"] == (
        "filesystem-spatial:v2"
    )
    assert source_context["source_neighborhood_id"].startswith(
        "filesystem-neighborhood:"
    )
    assert str(tmp_path) not in str(source_context)


def test_pending_packages_support_exact_private_worker_selectors(tmp_path: Path):
    service, package = _queued_service(tmp_path)
    package_id = package["package_id"]
    source_revision = package["source_revision_ids"][0]

    by_package = service.pending_analysis_packages(package_id=package_id)
    by_source = service.pending_analysis_packages(
        source_revision=source_revision,
    )
    by_kind = service.pending_analysis_packages(task_kind="source_annotation")
    mismatch = service.pending_analysis_packages(
        package_id="analysis-package:not-this-one",
        source_revision=source_revision,
        task_kind="source_annotation",
    )

    assert [item["package_id"] for item in by_package["items"]] == [package_id]
    assert [item["package_id"] for item in by_source["items"]] == [package_id]
    assert [item["package_id"] for item in by_kind["items"]] == [package_id]
    assert mismatch["items"] == ()
    assert mismatch["total_count"] == 0
    assert by_package["exact_selectors"] == {
        "package_id": package_id,
        "source_revision": "",
        "task_kind": "",
    }


def test_bilingual_ai_result_auto_dispatches_to_original_owners(
    tmp_path: Path,
    monkeypatch,
):
    service, package = _queued_service(tmp_path)
    package = _advance_to_semantic(service, package)
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
    matter_coverage = service.coverage_ledger.current(card["matter_id"])
    assert matter_coverage is not None
    assert matter_coverage.provider == "matters"
    assert matter_coverage.stages["semantic_depth"].status == "pending"
    assert card["title"] == {
        "en": "Prepare the launch plan",
        "zh-CN": "准备发布计划",
    }
    assert card["summary"] == {
        "en": "Launch planning is under way.",
        "zh-CN": "发布计划正在推进中。",
    }
    detail = service.matter_detail(
        matter_id=card["matter_id"],
        locale="zh-CN",
    )
    assert detail["matter"]["title"] == card["title"]
    assert detail["matter"]["summary"] == card["summary"]
    assert card["status_group"] == "in_progress"
    assert card["hero"]["status"] == "generation_pending_placeholder"
    assert card["hero"]["preview_token"] == ""
    assert set(card["hero"]["alt"]) == {"en", "zh-CN"}
    assert "visual" not in card
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
    assert service.pending_analysis_packages()["total_count"] == 0
    assert summary_refreshes == 1


def test_passed_annotation_reimport_reuses_exact_semantic_followup(
    tmp_path: Path,
) -> None:
    service, annotation_package = _queued_service(tmp_path)
    semantic_package = _advance_to_semantic(
        service,
        annotation_package,
    )
    annotations = service.current_records("source_annotation")
    assert len(annotations) == 1
    finding_id = annotations[0]["finding"]["finding_id"]
    annotation_history_count = len(
        service.store.history("source_annotation", finding_id)
    )
    package_count = len(
        service.current_records("analysis_work_package")
    )

    replay = service.import_autonomous_result(
        package_id=annotation_package["package_id"],
        provider_id=annotation_package["required_runner_id"],
        provider_version=annotation_package["required_runner_version"],
        result=_annotation_result(annotation_package),
    )

    assert replay["write_status"] == "current"
    assert replay["dispatch_count"] == 0
    assert replay["followup_package_id"] == semantic_package["package_id"]
    assert len(
        service.store.history("source_annotation", finding_id)
    ) == annotation_history_count
    assert len(service.current_records("analysis_work_package")) == package_count
    assert service.pending_analysis_packages()["total_count"] == 1


def test_duplicate_unexecuted_annotation_followup_is_retired_to_exact_relation(
    tmp_path: Path,
) -> None:
    service, annotation_package = _queued_service(tmp_path)
    semantic_payload = _advance_to_semantic(service, annotation_package)
    semantic = service.operations.package(semantic_payload["package_id"])
    duplicate_evidence = dict(semantic.untrusted_evidence)
    duplicate_evidence["analysis_as_of"] = "2026-07-21T00:00:00+00:00"
    duplicate = AnalysisWorkPackage.create(
        operation_type=semantic.operation_type,
        task_kind=semantic.task_kind,
        capability_role=semantic.capability_role,
        requested_output_types=semantic.requested_output_types,
        dependency_package_ids=semantic.dependency_package_ids,
        source_revision_ids=semantic.source_revision_ids,
        model_revision=semantic.model_revision,
        allowed_evidence_ids=semantic.allowed_evidence_ids,
        allowed_asset_ids=semantic.allowed_asset_ids,
        allowed_tool_ids=semantic.allowed_tool_ids,
        private_evidence=duplicate_evidence,
        matter_id=semantic.matter_id,
        matter_revision=semantic.matter_revision,
        authorization_identity=semantic.authorization_identity,
        scope_identity=semantic.scope_identity,
        inventory_identity=semantic.inventory_identity,
        tracking_policy_identity=semantic.tracking_policy_identity,
        prompt_contract_id=semantic.prompt_contract_id,
        prompt_contract_revision=semantic.prompt_contract_revision,
        output_schema_id=semantic.output_schema_id,
        required_skill_id=semantic.required_skill_id,
        required_skill_version=semantic.required_skill_version,
        locale_registry_revision=semantic.locale_registry_revision,
        required_locales=semantic.required_locales,
        disclosure_policy=semantic.disclosure_policy,
        resource_budget=semantic.resource_budget,
        auto_apply_policy=semantic.auto_apply_policy,
        synthetic=semantic.synthetic,
    )
    assert duplicate.package_id != semantic.package_id
    service.operations.queue(duplicate)

    result = service.reconcile_annotation_semantic_followups(limit=20)

    assert result["status"] == "current"
    assert result["duplicate_group_count"] == 1
    assert result["retired_package_count"] == 1
    invalidation = service.store.current(
        "analysis_result_invalidation",
        duplicate.package_id,
    )
    assert invalidation is not None
    assert invalidation["replacement_package_id"] == semantic.package_id
    assert service.operations.current_result(duplicate.package_id) is None


def test_person_dispatch_preserves_matter_role_and_evidence_scope(
    tmp_path: Path,
):
    service, source_package = _queued_service(tmp_path)
    semantic_package = _advance_to_semantic(service, source_package)
    service.import_autonomous_result(
        package_id=semantic_package["package_id"],
        provider_id=semantic_package["required_runner_id"],
        provider_version=semantic_package["required_runner_version"],
        result=_autonomous_result(semantic_package),
    )
    matter_id = service.object_catalog_page()["items"][0]["matter_id"]
    person_package = AnalysisWorkPackage.create(
        operation_type="text_analysis",
        task_kind="person_role_repair",
        capability_role="matter_modeler",
        requested_output_types=("person_candidate",),
        source_revision_ids=tuple(
            semantic_package["source_revision_ids"]
        ),
        model_revision="C4_person_entity_resolution:role-scope-v1",
        allowed_evidence_ids=tuple(
            semantic_package["allowed_evidence_ids"]
        ),
        private_evidence={
            "purpose": "Bind a named support contact to one Matter.",
        },
        matter_id=matter_id,
    )
    service.operations.queue(person_package)

    imported = service.import_autonomous_result(
        package_id=person_package.package_id,
        provider_id=person_package.required_runner_id,
        provider_version=person_package.required_runner_version,
        result=_person_result(
            {
                **asdict(person_package),
                "allowed_evidence_ids": list(
                    person_package.allowed_evidence_ids
                ),
                "allowed_asset_ids": list(
                    person_package.allowed_asset_ids
                ),
                "source_revision_ids": list(
                    person_package.source_revision_ids
                ),
            },
            matter_id=matter_id,
        ),
    )

    assert imported["auto_apply_status"] == "auto_applied"
    person = service.current_records("person_candidate")[0]
    assert person["display_name"] == "Jenna"
    assert person["matter_id"] == matter_id
    assert person["matter_ids"] == [matter_id]
    assert person["role"] == "customer_support_contact"
    assert person["evidence_ids"] == [
        person_package.allowed_evidence_ids[0]
    ]
    role = service.current_records("matter_role")[0]
    assert role["person_id"] == person["person_id"]
    assert role["matter_id"] == matter_id
    assert role["role"] == "customer_support_contact"
    detail = service.matter_detail(matter_id=matter_id, locale="en")
    assert detail["people"][0]["name"] == "Jenna"


def test_same_result_owner_binding_prevents_cross_matter_projection(
    tmp_path: Path,
):
    service, package = _queued_service(tmp_path)
    package = _advance_to_semantic(service, package)
    service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result=_autonomous_result(package),
    )
    first_card = service.object_catalog_page()["items"][0]
    original = service.operations.package(package["package_id"])
    second = AnalysisWorkPackage.create(
        operation_type=original.operation_type,
        task_kind=original.task_kind,
        capability_role=original.capability_role,
        requested_output_types=original.requested_output_types,
        dependency_package_ids=original.dependency_package_ids,
        source_revision_ids=original.source_revision_ids,
        model_revision="matters-semantic-understanding:test-owner-binding",
        allowed_evidence_ids=original.allowed_evidence_ids,
        private_evidence=original.untrusted_evidence,
        allowed_asset_ids=original.allowed_asset_ids,
        allowed_tool_ids=original.allowed_tool_ids,
        authorization_identity=original.authorization_identity,
        scope_identity=original.scope_identity,
        inventory_identity=original.inventory_identity,
        tracking_policy_identity=original.tracking_policy_identity,
        prompt_contract_id=original.prompt_contract_id,
        prompt_contract_revision="owner-binding-test",
        output_schema_id=original.output_schema_id,
        required_skill_id=original.required_skill_id,
        required_skill_version=original.required_skill_version,
        locale_registry_revision=original.locale_registry_revision,
        required_locales=original.required_locales,
        disclosure_policy=original.disclosure_policy,
        resource_budget=original.resource_budget,
        auto_apply_policy=original.auto_apply_policy,
    )
    service.operations.queue(second)
    second_payload = asdict(second)
    second_result = _autonomous_result(second_payload)
    second_result["findings"][0].update(
        {
            "statement": "Book the launch venue",
            "localized_statement": {
                "en": "Book the launch venue",
                "zh-CN": "预订发布会场地",
            },
        }
    )
    second_result["findings"][1].update(
        {
            "statement": "Venue booking is planned.",
            "localized_statement": {
                "en": "Venue booking is planned.",
                "zh-CN": "场地预订正在计划中。",
            },
        }
    )

    imported = service.import_autonomous_result(
        package_id=second.package_id,
        provider_id=second.required_runner_id,
        provider_version=second.required_runner_version,
        result=second_result,
    )

    assert imported["auto_apply_status"] == "auto_applied"
    catalog = service.object_catalog_page(root_only=False)
    assert catalog["total_count"] == 2
    cards = {
        item["title"]["en"]: item
        for item in catalog["items"]
    }
    assert cards["Prepare the launch plan"]["matter_id"] == (
        first_card["matter_id"]
    )
    assert cards["Prepare the launch plan"]["summary"]["en"] == (
        "Launch planning is under way."
    )
    assert cards["Book the launch venue"]["matter_id"] != (
        first_card["matter_id"]
    )
    assert cards["Book the launch venue"]["summary"]["en"] == (
        "Venue booking is planned."
    )


def test_restart_migrates_legacy_summary_title_without_rerunning_ai(
    tmp_path: Path,
):
    service, package = _queued_service(tmp_path)
    package = _advance_to_semantic(service, package)
    imported = service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result=_autonomous_result(package),
    )
    assert imported["auto_apply_status"] == "auto_applied"
    card = service.object_catalog_page()["items"][0]
    matter_id = card["matter_id"]
    projection = service.store.current("projection", matter_id)
    legacy = dict(projection)
    legacy["localized_values"] = {
        "en": "Launch planning is under way.",
        "zh-CN": "发布计划正在推进中。",
    }
    service.store.append(
        "projection",
        matter_id,
        service.store.next_revision("projection", matter_id),
        legacy,
    )
    legacy_catalog_revision = service.object_catalog_page()[
        "catalog_revision"
    ]

    restarted = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    migrated_count = restarted._migrate_distinct_title_summary_projections()

    assert restarted.migrated_distinct_title_summary_count == 0
    assert migrated_count == 1
    migrated = restarted.object_catalog_page()["items"][0]
    assert migrated["title"] == {
        "en": "Prepare the launch plan",
        "zh-CN": "准备发布计划",
    }
    assert migrated["summary"] == {
        "en": "Launch planning is under way.",
        "zh-CN": "发布计划正在推进中。",
    }
    marker = restarted.store.current(
        "schema_migration",
        "projection-distinct-title-summary-v2",
    )
    assert marker["status"] == "current"
    assert marker["blocked_projection_count"] == 0
    assert marker["fallback"] == "forbidden"
    assert (
        restarted.object_catalog_page()["catalog_revision"]
        != legacy_catalog_revision
    )
    projection_history_count = len(
        restarted.store.history("projection", matter_id)
    )
    marker_history_count = len(
        restarted.store.history(
            "schema_migration",
            "projection-distinct-title-summary-v2",
        )
    )

    stable_restart = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    stable_migrated_count = (
        stable_restart._migrate_distinct_title_summary_projections()
    )

    assert stable_restart.migrated_distinct_title_summary_count == 0
    assert stable_migrated_count == 0
    assert (
        len(stable_restart.store.history("projection", matter_id))
        == projection_history_count
    )
    assert (
        len(
            stable_restart.store.history(
                "schema_migration",
                "projection-distinct-title-summary-v2",
            )
        )
        == marker_history_count
    )


def test_explicit_coverage_stage_schema_rebase_marks_stable_restart(
    tmp_path: Path,
):
    service = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    rebased = service.rebase_coverage_stage_schema(limit=10)
    assert rebased["status"] == "current"
    marker = service.store.current(
        "schema_migration",
        "coverage-stage-schema-v2",
    )
    assert marker["status"] == "current"
    assert marker["migrated_object_count"] == 0
    history_count = len(
        service.store.history(
            "schema_migration",
            "coverage-stage-schema-v2",
        )
    )

    restarted = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )

    assert (
        len(
            restarted.store.history(
                "schema_migration",
                "coverage-stage-schema-v2",
            )
        )
        == history_count
    )


def test_coverage_rebase_adds_content_selection_and_skips_retired_rows(
    tmp_path: Path,
):
    service = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    active_id = "filesystem:active-legacy"
    retired_id = "filesystem:retired-legacy"
    legacy = {
        "provider": "filesystem",
        "object_type": "file",
        "scope_id": "scope:legacy",
        "inventory_revision": 1,
        "disposition": "tracked",
        "required_stages": (
            "authorization",
            "inventory",
            "source_version",
        ),
        "stages": {
            "authorization": {
                "stage_id": "authorization",
                "status": "current",
                "owner_id": "C1_authorization_coverage",
                "input_fingerprint": "legacy",
                "output_ref": "",
                "failure_class": "",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
            "inventory": {
                "stage_id": "inventory",
                "status": "current",
                "owner_id": "C1_authorization_coverage",
                "input_fingerprint": "legacy",
                "output_ref": "",
                "failure_class": "",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
        },
        "matter_ids": (),
        "revision": 1,
        "retry_count": 0,
        "next_retry_at": "",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    for object_id, active in (
        (active_id, True),
        (retired_id, False),
    ):
        service.store.append(
            "object_coverage",
            object_id,
            1,
            {
                **legacy,
                "object_id": object_id,
                "active": active,
            },
        )

    result = service.rebase_coverage_stage_schema(limit=10)

    assert result["migrated_object_count"] == 1
    active = service.store.current("object_coverage", active_id)
    retired = service.store.current("object_coverage", retired_id)
    assert active["stages"]["content_selection"]["status"] == "pending"
    assert set(active["required_stages"]) == set(
        service.coverage_ledger.required_stages("tracked")
    )
    assert len(service.store.history("object_coverage", retired_id)) == 1
    assert "content_selection" not in retired["stages"]


def test_coverage_rebase_resumes_from_current_partial_marker(
    tmp_path: Path,
):
    service = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    for index in range(3):
        object_id = f"filesystem:legacy-{index}"
        service.store.append(
            "object_coverage",
            object_id,
            1,
            {
                "object_id": object_id,
                "provider": "filesystem",
                "object_type": "file",
                "scope_id": "scope:legacy",
                "inventory_revision": 1,
                "disposition": "tracked",
                "required_stages": (
                    "authorization",
                    "inventory",
                    "source_version",
                ),
                "stages": {},
                "matter_ids": (),
                "revision": 1,
                "retry_count": 0,
                "next_retry_at": "",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "active": True,
            },
        )

    first = service.rebase_coverage_stage_schema(limit=1)
    second = service.rebase_coverage_stage_schema(limit=1)
    third = service.rebase_coverage_stage_schema(limit=1)

    assert first["status"] == "partial"
    assert second["status"] == "partial"
    assert third["status"] == "current"
    marker = service.store.current(
        "schema_migration",
        "coverage-stage-schema-v2",
    )
    assert marker["migrated_object_count"] == 3
    for index in range(3):
        current = service.store.current(
            "object_coverage",
            f"filesystem:legacy-{index}",
        )
        assert current["stages"]["content_selection"]["status"] == "pending"


def test_content_selection_rebase_restarts_when_inventory_identity_changes(
    tmp_path: Path,
):
    service = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    scope_id = "scope:inventory-refresh"

    def occurrence(object_id: str) -> dict:
        return {
            "occurrence_id": object_id,
            "provider": "filesystem",
            "object_type": "document",
            "locator": f"private/{object_id}.txt",
            "metadata": {"size": 1, "modified_ns": 1},
            "content_identity": f"content:{object_id}",
            "discovery_reason": "enumerated",
            "parent_occurrence_id": "",
        }

    def register_revision(revision: int, object_ids: tuple[str, ...]) -> None:
        occurrences = tuple(occurrence(object_id) for object_id in object_ids)
        dispositions = tuple(
            {
                "occurrence_id": object_id,
                "status": "tracked",
                "reason": "included",
                "policy_revision": 1,
                "decided_by": "policy",
                "user_intent": "",
            }
            for object_id in object_ids
        )
        service.store.append(
            "inventory_snapshot",
            scope_id,
            revision,
            {
                "snapshot_id": f"inventory:{scope_id}:{revision}",
                "scope_id": scope_id,
                "revision": revision,
                "policy_revision": 1,
                "occurrences": occurrences,
                "dispositions": dispositions,
            },
        )
        service.coverage_ledger.reconcile_inventory(
            scope_id=scope_id,
            inventory_revision=revision,
            occurrences=occurrences,
            dispositions=dispositions,
        )

    register_revision(
        1,
        (
            "occurrence:b",
            "occurrence:c",
            "occurrence:d",
        ),
    )
    first = service.rebase_content_selection(limit=1)
    first_marker = service.store.current(
        "schema_migration",
        "content-selection-rebase-v2",
    )

    assert first["status"] == "partial"
    assert first["next_cursor"] == "occurrence:b"
    assert first_marker["inventory_identity"] == (
        service.store.current_inventory_identity()
    )

    register_revision(
        2,
        (
            "occurrence:a",
            "occurrence:b",
            "occurrence:c",
            "occurrence:d",
        ),
    )
    second = service.rebase_content_selection(limit=1)
    second_marker = service.store.current(
        "schema_migration",
        "content-selection-rebase-v2",
    )

    assert second["status"] == "partial"
    assert second["next_cursor"] == "occurrence:a"
    assert service.store.current(
        "content_selection",
        "occurrence:a",
    ) is not None
    assert second_marker["inventory_identity"] != (
        first_marker["inventory_identity"]
    )
    assert second_marker["inventory_identity"] == (
        service.store.current_inventory_identity()
    )

    completed = service.rebase_content_selection(limit=10)
    assert completed["status"] == "current"
    register_revision(
        3,
        (
            "occurrence:a",
            "occurrence:b",
            "occurrence:c",
            "occurrence:d",
        ),
    )
    refreshed = service.rebase_content_selection(limit=1)

    assert refreshed["scanned_object_count"] == 1
    assert refreshed["status"] == "partial"
    assert service.store.current(
        "schema_migration",
        "content-selection-rebase-v2",
    )["inventory_identity"] == service.store.current_inventory_identity()


def test_coverage_reconciliation_retires_active_source_missing_from_inventory(
    tmp_path: Path,
):
    service = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    object_id = "occurrence:orphaned-source"
    service.store.append(
        "object_coverage",
        object_id,
        1,
        {
            "object_id": object_id,
            "provider": "filesystem",
            "object_type": "document",
            "scope_id": "scope:retired",
            "inventory_revision": 1,
            "disposition": "tracked",
            "required_stages": ("authorization", "inventory"),
            "stages": {},
            "matter_ids": (),
            "revision": 1,
            "retry_count": 0,
            "next_retry_at": "",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "active": True,
        },
    )

    result = service.reconcile_coverage_inventory_orphans(limit=10)

    assert result == {
        "scanned_object_count": 1,
        "retired_object_count": 1,
        "has_more": False,
        "status": "current",
    }
    current = service.coverage_ledger.current(object_id)
    assert current is not None
    assert current.active is False
    assert current.disposition == "not_tracked"


def test_restart_blocks_projection_when_unique_title_owner_is_missing(
    tmp_path: Path,
):
    service, package = _queued_service(tmp_path)
    package = _advance_to_semantic(service, package)
    service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result=_autonomous_result(package),
    )
    matter_id = service.object_catalog_page()["items"][0]["matter_id"]
    result = service.operations.current_result(package["package_id"])
    title_finding = next(
        finding
        for finding in result.findings
        if finding.finding_type == "matter_candidate"
    )
    owner_record = service.store.current(
        "autonomous_finding",
        title_finding.finding_id,
    )
    invalid_owner_record = dict(owner_record)
    invalid_owner_record["owner_output_ref"] = (
        "admission_decision:foreign-matter"
    )
    service.store.append(
        "autonomous_finding",
        title_finding.finding_id,
        service.store.next_revision(
            "autonomous_finding",
            title_finding.finding_id,
        ),
        invalid_owner_record,
    )

    restarted = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    assert restarted._migrate_distinct_title_summary_projections() == 0

    assert restarted.object_catalog_page()["total_count"] == 0
    marker = restarted.store.current(
        "schema_migration",
        "projection-distinct-title-summary-v2",
    )
    assert marker["status"] == "current_with_gaps"
    assert marker["blocked_projection_count"] == 1
    assert marker["fallback"] == "forbidden"

    repaired_owner_record = dict(invalid_owner_record)
    repaired_owner_record["owner_output_ref"] = (
        f"admission_decision:{matter_id}"
    )
    restarted.store.append_next(
        "autonomous_finding",
        title_finding.finding_id,
        repaired_owner_record,
    )
    repaired = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    repaired_count = repaired._migrate_distinct_title_summary_projections()

    assert repaired.migrated_distinct_title_summary_count == 0
    assert repaired_count == 1
    assert repaired.object_catalog_page()["total_count"] == 1
    repaired_marker = repaired.store.current(
        "schema_migration",
        "projection-distinct-title-summary-v2",
    )
    assert repaired_marker["status"] == "current"
    assert repaired_marker["blocked_projection_count"] == 0


def test_projection_migration_does_not_overwrite_distinct_unknown_title(
    tmp_path: Path,
):
    service, package = _queued_service(tmp_path)
    package = _advance_to_semantic(service, package)
    service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result=_autonomous_result(package),
    )
    card = service.object_catalog_page()["items"][0]
    matter_id = card["matter_id"]
    projection = service.store.current("projection", matter_id)
    distinct = dict(projection)
    distinct["localized_values"] = {
        "en": "Curated launch title",
        "zh-CN": "经整理的发布标题",
    }
    service.store.append_next("projection", matter_id, distinct)

    restarted = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    assert restarted._migrate_distinct_title_summary_projections() == 0

    assert restarted.migrated_distinct_title_summary_count == 0
    preserved = restarted.object_catalog_page()["items"][0]
    assert preserved["title"] == distinct["localized_values"]
    assert preserved["summary"] == projection["localized_rationale"]


def test_projection_migration_uses_owner_records_without_current_ai_result(
    tmp_path: Path,
):
    service, package = _queued_service(tmp_path)
    package = _advance_to_semantic(service, package)
    service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result=_autonomous_result(package),
    )
    card = service.object_catalog_page()["items"][0]
    matter_id = card["matter_id"]
    projection = service.store.current("projection", matter_id)
    legacy = dict(projection)
    legacy["localized_values"] = dict(
        projection["localized_rationale"]
    )
    service.store.append_next("projection", matter_id, legacy)
    with service.store.connection() as connection:
        connection.execute(
            "DELETE FROM current_objects "
            "WHERE owner='agent_operation_result' AND object_id=?",
            (package["package_id"],),
        )

    restarted = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    migrated_count = restarted._migrate_distinct_title_summary_projections()

    assert restarted.migrated_distinct_title_summary_count == 0
    assert migrated_count == 1
    migrated = restarted.object_catalog_page()["items"][0]
    assert migrated["title"] == card["title"]
    assert migrated["summary"] == card["summary"]


def test_projection_migration_blocks_invalid_summary_owner_reference(
    tmp_path: Path,
):
    service, package = _queued_service(tmp_path)
    package = _advance_to_semantic(service, package)
    service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result=_autonomous_result(package),
    )
    card = service.object_catalog_page()["items"][0]
    matter_id = card["matter_id"]
    projection = service.store.current("projection", matter_id)
    legacy = dict(projection)
    legacy["localized_values"] = dict(
        projection["localized_rationale"]
    )
    service.store.append_next("projection", matter_id, legacy)
    result = service.operations.current_result(package["package_id"])
    summary_finding = next(
        finding
        for finding in result.findings
        if finding.finding_type == "bounded_summary"
    )
    summary_owner = service.store.current(
        "autonomous_finding",
        summary_finding.finding_id,
    )
    invalid_summary_owner = dict(summary_owner)
    invalid_summary_owner["owner_output_ref"] = (
        "projection:foreign-matter"
    )
    service.store.append_next(
        "autonomous_finding",
        summary_finding.finding_id,
        invalid_summary_owner,
    )

    restarted = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    assert restarted._migrate_distinct_title_summary_projections() == 0

    assert restarted.object_catalog_page()["total_count"] == 0
    marker = restarted.store.current(
        "schema_migration",
        "projection-distinct-title-summary-v2",
    )
    assert marker["blocked_projection_count"] == 1


def test_projection_migration_blocks_duplicate_current_summary_owners(
    tmp_path: Path,
):
    service, package = _queued_service(tmp_path)
    package = _advance_to_semantic(service, package)
    service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result=_autonomous_result(package),
    )
    card = service.object_catalog_page()["items"][0]
    matter_id = card["matter_id"]
    projection = service.store.current("projection", matter_id)
    legacy = dict(projection)
    legacy["localized_values"] = dict(
        projection["localized_rationale"]
    )
    service.store.append_next("projection", matter_id, legacy)
    result = service.operations.current_result(package["package_id"])
    summary_finding = next(
        finding
        for finding in result.findings
        if finding.finding_type == "bounded_summary"
    )
    summary_owner = service.store.current(
        "autonomous_finding",
        summary_finding.finding_id,
    )
    duplicate = dict(summary_owner)
    duplicate["finding_id"] = "finding:duplicate-summary"
    duplicate_finding = dict(duplicate["finding"])
    duplicate_finding["finding_id"] = "finding:duplicate-summary"
    duplicate["finding"] = duplicate_finding
    service.store.append(
        "autonomous_finding",
        "finding:duplicate-summary",
        1,
        duplicate,
    )

    restarted = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    assert restarted._migrate_distinct_title_summary_projections() == 0

    assert restarted.object_catalog_page()["total_count"] == 0
    marker = restarted.store.current(
        "schema_migration",
        "projection-distinct-title-summary-v2",
    )
    assert marker["blocked_projection_count"] == 1


def test_projection_migration_is_atomic_under_parallel_rebuilders(
    tmp_path: Path,
):
    service, package = _queued_service(tmp_path)
    package = _advance_to_semantic(service, package)
    service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result=_autonomous_result(package),
    )
    card = service.object_catalog_page()["items"][0]
    matter_id = card["matter_id"]
    projection = service.store.current("projection", matter_id)
    legacy = dict(projection)
    legacy["localized_values"] = dict(
        projection["localized_rationale"]
    )
    service.store.append_next("projection", matter_id, legacy)
    legacy_current = service.store.current("projection", matter_id)
    owner_records = tuple(
        service.store.iter_current("autonomous_finding")
    )
    history_before = len(
        service.store.history("projection", matter_id)
    )

    with ThreadPoolExecutor(max_workers=4) as executor:
        dispositions = tuple(
            executor.map(
                lambda _index: (
                    service.dispatcher
                    .rebuild_distinct_title_summary_projection(
                        legacy_current,
                        owner_records,
                    )
                ),
                range(4),
            )
        )

    assert dispositions.count("migrated") == 1
    assert set(dispositions).issubset({"migrated", "conflicted"})
    assert (
        len(service.store.history("projection", matter_id))
        == history_before + 1
    )


def test_missing_bilingual_value_is_blocked_and_creates_no_matter(
    tmp_path: Path,
):
    service, package = _queued_service(tmp_path)
    package = _advance_to_semantic(service, package)
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


def test_blocked_owner_dispatch_recovers_without_rerunning_ai(tmp_path: Path):
    service, package = _queued_service(tmp_path)
    package = _advance_to_semantic(service, package)
    matter_id = "matter:restart-safe-owner"
    result = {
        "status": "passed",
        "input_dispositions": _input_dispositions(package),
        "execution_profile_identity": (
            "execution-profile:test-owner-recovery"
        ),
        "concrete_execution_identity": "execution:test-owner-recovery",
        "findings": [
            {
                "finding_type": "work_item_candidate",
                "owner_model_id": "C6_matter_admission",
                "statement": "Submit the launch brief",
                "localized_statement": {
                    "en": "Submit the launch brief",
                    "zh-CN": "提交发布简报",
                },
                "semantic_revision": package["source_revision_ids"][0],
                "evidence_ids": [package["allowed_evidence_ids"][0]],
                "confidence": "bounded",
                "modality": "reported",
                "attributes": {
                    "matter_id": matter_id,
                    "kind": "action",
                    "status": "planned",
                    "required_for_parent": True,
                },
            }
        ],
    }
    first = service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result=result,
    )
    assert first["auto_apply_status"] == "blocked"
    assert service.pending_analysis_packages()["total_count"] == 1

    service.store.append(
        "admission_decision",
        matter_id,
        1,
        {
            "status": "admitted",
            "matter": {
                "matter_id": matter_id,
                "source_ids": package["source_revision_ids"],
                "rationale": "Restart-safe owner fixture",
                "evidence_ids": package["allowed_evidence_ids"],
                "admitted": True,
                "semantic_identity_id": "semantic:restart-safe-owner",
                "object_kind": "matter",
            },
            "candidate": None,
        },
    )
    service.store.append(
        "projection",
        matter_id,
        1,
        {
            "matter_id": matter_id,
            "semantic_revision": package["source_revision_ids"][0],
            "state": "planned",
            "evidence_ids": package["allowed_evidence_ids"],
            "localized_values": {
                "en": "Launch",
                "zh-CN": "发布",
            },
            "localized_rationale": {
                "en": "Launch",
                "zh-CN": "发布",
            },
            "locale_revisions": {
                "en": package["source_revision_ids"][0],
                "zh-CN": package["source_revision_ids"][0],
            },
            "locales": ("en", "zh-CN"),
            "equivalence_status": "equivalent",
        },
    )
    cycle = service.run_maintenance_cycle(limit=10)

    assert cycle["status"] == "progressed"
    assert cycle["package_count"] == 1
    assert cycle["owner_redispatch_count"] == 1
    assert cycle["followup_ai_expansion_status"] == (
        "deferred_owner_redispatch"
    )
    assert cycle["matter_presentation_reconciliation"]["status"] == (
        "deferred_owner_redispatch"
    )
    assert cycle["supplemental_research_queue"]["status"] == (
        "deferred_owner_redispatch"
    )
    assert service.pending_analysis_packages()["total_count"] == 0
    assert service.pending_generated_heroes()["total_count"] == 0
    items = service.matter_work_items(matter_id=matter_id)
    assert items["total_count"] == 1
    assert items["items"][0]["localized_title"]["zh-CN"] == "提交发布简报"

    next_cycle = service.run_maintenance_cycle(limit=10)
    assert next_cycle["owner_redispatch_count"] == 0
    assert next_cycle["followup_ai_expansion_status"] == "eligible"
    assert service.pending_analysis_packages()["total_count"] == 1
    assert next_cycle["matter_presentation_reconciliation"][
        "hero_prepared_count"
    ] == 1
    assert service.store.current(
        "generated_hero_record",
        matter_id,
    )["status"] == "generation_pending_placeholder"
