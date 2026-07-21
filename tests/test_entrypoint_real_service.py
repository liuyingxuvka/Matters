from io import BytesIO, StringIO
import json

from PIL import Image

from matters import runtime
from matters.api.http.app import create_application
from matters.api.mcp.server import MattersMCP
from matters.application.orchestrator import MatterService
from matters.application.source_workflows import SourceWorkflow
from matters.analysis.operations import ResearchProviderStatus
from matters.cli.main import run
from matters.providers.filesystem import FilesystemReadOnlyAdapter


def _service(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    source_root = tmp_path / "private-documents"
    repo.mkdir()
    source_root.mkdir()
    (source_root / "plan.txt").write_text(
        "Prepare the launch plan\nWait for design approval\n",
        encoding="utf-8",
    )
    service = MatterService(private_root=home, repository_root=repo)
    SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
        content_limit=20,
    )
    package = service.pending_analysis_packages()["items"][0]
    annotation_imported = service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result={
            "status": "passed",
            "input_dispositions": [
                {
                    "input_id": item,
                    "disposition": "used",
                    "reason": "bounded annotation",
                }
                for item in (
                    *package["allowed_evidence_ids"],
                    *package["allowed_asset_ids"],
                )
            ],
            "findings": [
                {
                    "finding_type": "source_annotation",
                    "owner_model_id": "A0_matters_source_analysis_operation",
                    "statement": "A launch plan with a pending design dependency",
                    "localized_statement": {
                        "en": "A launch plan with a pending design dependency",
                        "zh-CN": "一项等待设计审批的发布计划",
                    },
                    "semantic_revision": package["source_revision_ids"][0],
                    "evidence_ids": [package["allowed_evidence_ids"][0]],
                    "confidence": "bounded",
                    "modality": "observed",
                    "attributes": {
                        "content_kind": "user_plan",
                        "user_relevance": "likely_relevant",
                    },
                },
            ],
        },
    )
    assert annotation_imported["auto_apply_status"] == "auto_applied"
    package = service.pending_analysis_packages()["items"][0]
    assert package["capability_role"] == "matter_modeler"
    evidence_id = package["allowed_evidence_ids"][0]
    source_revision = package["source_revision_ids"][0]
    input_dispositions = [
        {"input_id": item, "disposition": "used", "reason": "bounded result"}
        for item in (
            *package["allowed_evidence_ids"],
            *package["allowed_asset_ids"],
        )
    ]
    imported = service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result={
            "status": "passed",
            "input_dispositions": input_dispositions,
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
                    "attributes": {"explicit_goal_or_obligation": True},
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
                {
                    "finding_type": "generated_hero_candidate",
                    "owner_model_id": "C12_projection_bilingual_ui",
                    "statement": (
                        "Photorealistic launch planning workshop"
                    ),
                    "localized_statement": {
                        "en": "Photorealistic launch planning workshop",
                        "zh-CN": "真实照片风格的发布规划工作室",
                    },
                    "semantic_revision": source_revision,
                    "evidence_ids": [evidence_id],
                    "confidence": "bounded",
                    "modality": "inferred",
                    "attributes": {
                        "topic_concepts": ["product launch"],
                        "theme_concepts": [
                            "launch team in a workshop",
                            "physical project boards",
                            "natural window light",
                        ],
                    },
                },
            ],
        },
    )
    assert imported["auto_apply_status"] == "auto_applied", imported
    return service, source_root


def _request(app, *, method="GET", path="/", query="", body=None):
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": BytesIO(raw),
    }
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)

    response = b"".join(app(environ, start_response))
    return captured["status"], json.loads(response)


def _request_binary(app, *, path, query=""):
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": "0",
        "wsgi.input": BytesIO(),
    }
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)

    response = b"".join(app(environ, start_response))
    return captured["status"], captured["headers"], response


def _image_bytes():
    output = BytesIO()
    Image.new("RGB", (64, 40), "#476d89").save(output, format="PNG")
    return output.getvalue()


def test_service_startup_does_not_run_private_catalog_migrations(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    first = MatterService(private_root=home, repository_root=repo)
    assert first.store is not None
    first.store.append(
        "projection",
        "matter:legacy",
        1,
        {
            "matter_id": "matter:legacy",
            "semantic_revision": "semantic:legacy",
            "state": "planned",
            "rationale": "legacy projection",
            "english": "Legacy projection",
            "zh_cn": "旧投影",
            "evidence_ids": [],
            "equivalence_status": "equivalent",
        },
    )

    restarted = MatterService(private_root=home, repository_root=repo)

    assert restarted.migrated_analysis_package_count == 0
    assert restarted.migrated_root_hierarchy_count == 0
    assert restarted.migrated_distinct_title_summary_count == 0
    assert restarted.migrated_matter_activity_count == 0
    assert restarted.prepared_generated_hero_count == 0
    assert restarted.store.current(
        "schema_migration",
        "projection-locale-map-v1",
    ) is None


def test_real_service_cli_rebases_existing_matter_coverage_in_one_bounded_page(
    tmp_path,
):
    service, _source_root = _service(tmp_path)
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        ["matter-coverage-rebase", "--limit", "1"],
        service=service,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert stderr.getvalue() == ""
    result = json.loads(stdout.getvalue())["result"]
    assert set(result) == {
        "scanned_matter_count",
        "registered_matter_count",
        "next_cursor",
        "has_more",
        "status",
    }
    assert result["scanned_matter_count"] <= 1
    assert result["status"] in {"partial", "current"}


def test_real_service_browser_detail_evidence_and_correction_flow_through_http(
    tmp_path,
):
    service, private_source_root = _service(tmp_path)
    app = create_application(service)

    status, payload = _request(app, path="/api/browser")
    assert status == "200 OK"
    browser = payload["result"]
    assert browser["surface"] == "object_browser"
    assert browser["default_locale"] == "en"
    assert browser["available_locales"] == ["en", "zh-CN"]
    assert browser["catalog"]["total_count"] == 1
    card = browser["catalog"]["items"][0]
    assert card["title"] == {
        "en": "Prepare the launch plan",
        "zh-CN": "准备发布计划",
    }
    assert card["hero"]["status"] == "generation_pending_placeholder"
    assert card["hero"]["preview_token"] == ""
    assert "visual" not in card
    assert str(private_source_root) not in json.dumps(browser)

    matter_id = card["matter_id"]
    pending = service.pending_generated_heroes()
    assert pending["total_count"] == 1
    generated = service.register_generated_hero(
        matter_id=matter_id,
        brief_fingerprint=pending["items"][0]["brief_fingerprint"],
        content=_image_bytes(),
        media_type="image/png",
        localized_alt={
            "en": (
                "A launch team reviewing a project plan "
                "in a naturally lit workshop"
            ),
            "zh-CN": "发布团队在自然光照亮的工作室审阅项目计划",
        },
        runner_contract_id="hero-runner-contract:v1",
        execution_identity="test-private-execution",
    )
    status, refreshed_payload = _request(app, path="/api/browser")
    assert status == "200 OK"
    refreshed_card = refreshed_payload["result"]["catalog"]["items"][0]
    assert refreshed_card["hero"]["status"] == "generated_current"
    assert refreshed_card["hero"]["preview_token"] == generated["preview_token"]
    status, headers, hero_bytes = _request_binary(
        app,
        path=f"/api/heroes/{generated['preview_token']}",
    )
    assert status == "200 OK"
    assert headers["Content-Type"] == "image/png"
    assert hero_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    status, detail = _request(
        app,
        path=f"/api/matters/{matter_id}",
        query="locale=zh-CN",
    )
    assert status == "200 OK"
    assert detail["result"]["selected_locale"] == "zh-CN"

    status, evidence = _request(
        app,
        path=f"/api/matters/{matter_id}/evidence",
        query="limit=20",
    )
    assert status == "200 OK"
    assert evidence["result"]["total_count"] == 1
    assert "Prepare the launch plan" in evidence["result"]["items"][0]["excerpt"]
    assert str(private_source_root) not in json.dumps(evidence)

    status, correction = _request(
        app,
        method="POST",
        path=f"/api/matters/{matter_id}/corrections",
        body={
            "rationale": "This Matter is completed.",
            "field_name": "state",
            "corrected_value": "completed",
        },
    )
    assert status == "200 OK"
    assert correction["result"]["status"] == "auto_applied"
    assert service.matter_detail(matter_id=matter_id)["matter"][
        "status_group"
    ] == "completed"


def test_real_service_object_browser_contract_flows_through_mcp(tmp_path):
    service, _private_source_root = _service(tmp_path)
    mcp = MattersMCP(service)

    browser = mcp.call_tool("get_browser", {"locale": "en"})
    matters = mcp.call_tool("list_matters", {"status": "in_progress"})
    matter_id = matters["result"]["items"][0]["matter_id"]
    detail = mcp.call_tool(
        "get_matter",
        {"matter_id": matter_id, "locale": "zh-CN"},
    )
    evidence = mcp.call_tool(
        "get_evidence",
        {"matter_id": matter_id, "limit": 20},
    )
    coverage = mcp.call_tool("get_coverage")

    assert browser["ok"] is True
    assert browser["result"]["surface"] == "object_browser"
    assert matters["result"]["total_count"] == 1
    assert detail["result"]["selected_locale"] == "zh-CN"
    assert evidence["result"]["total_count"] == 1
    assert coverage["result"]["registered_object_count"] == 2


def test_real_service_coverage_exposes_only_aggregate_progress(tmp_path):
    service, private_source_root = _service(tmp_path)

    coverage = service.object_coverage_summary()
    serialized = json.dumps(coverage)

    assert coverage["registered_object_count"] == 2
    assert coverage["ui_ready_object_count"] == 0
    assert coverage["coverage_status"] == "partial"
    assert str(private_source_root) not in serialized
    assert "plan.txt" not in serialized
    assert "occurrence:" not in serialized


def test_real_service_queues_minimized_idempotent_research_request(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("MATTERS_HOME", str(tmp_path / "home"))
    service, private_source_root = _service(tmp_path)
    matter_id = service.object_catalog_page()["items"][0]["matter_id"]

    first = service.queue_research_operation(
        matter_id,
        "What public context is relevant for person@example.com?",
    )
    second = service.queue_research_operation(
        matter_id,
        "What public context is relevant for person@example.com?",
    )

    assert first == second
    assert first["status"] == "queued"
    assert first["provider_gate"] == {
        "provider_id": "researchguard",
        "status": "pending",
        "provider_status": "researchguard_pending_integration",
        "execution_deferred": True,
    }
    package = first["package"]
    assert package["operation_type"] == "research_operation"
    assert package["task_kind"] == "supplemental_information_research"
    assert package["capability_role"] == "ambiguity_resolver"
    assert package["requested_output_types"] == (
        "supplemental_information_candidate",
    )
    assert package["required_skill_id"] == "matters-research-orchestration"
    assert package["allowed_tool_ids"] == ("researchguard",)
    assert package["auto_apply_policy"] == (
        "validate_then_dispatch_original_owner"
    )
    assert package["untrusted_evidence"]["provider_gate"]["status"] == "pending"
    assert package["untrusted_evidence"]["required_output"][
        "canonical_write_allowed"
    ] is False

    serialized = json.dumps(first)
    assert str(private_source_root) not in serialized
    assert "person@example.com" not in serialized
    assert "Wait for design approval" not in serialized
    assert "occurrence:" not in serialized

    pending = service.pending_analysis_packages(limit=100)["items"]
    research_packages = tuple(
        item
        for item in pending
        if item["operation_type"] == "research_operation"
    )
    assert len(research_packages) == 1
    assert research_packages[0]["package_id"] == package["package_id"]


def test_real_service_imports_current_researchguard_result_through_original_owner(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("MATTERS_HOME", str(tmp_path / "home"))
    service, _private_source_root = _service(tmp_path)
    service.research_status = ResearchProviderStatus(
        status="current",
        provider_id="researchguard",
        provider_version="0.1.2",
        source_commit="current-researchguard-source",
        portable_receipt_id="sha256:" + ("a" * 64),
    )
    matter_id = service.object_catalog_page()["items"][0]["matter_id"]
    queued = service.queue_research_operation(
        matter_id,
        "What public background would help the user understand this matter?",
    )
    package = queued["package"]

    imported = service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id="researchguard",
        provider_version="0.1.2",
        result={
            "status": "passed",
            "input_dispositions": [
                {
                    "input_id": input_id,
                    "disposition": "used",
                    "reason": "Bounded public-context research",
                }
                for input_id in (
                    *package["allowed_evidence_ids"],
                    *package["allowed_asset_ids"],
                )
            ],
            "findings": [
                {
                    "finding_type": "supplemental_information_candidate",
                    "owner_model_id": "C12_projection_bilingual_ui",
                    "statement": (
                        "A concise public background note that helps explain "
                        "the current matter."
                    ),
                    "localized_statement": {
                        "en": (
                            "A concise public background note that helps "
                            "explain the current matter."
                        ),
                        "zh-CN": "一条帮助理解当前事项的简明公开背景信息。",
                    },
                    "semantic_revision": package["source_revision_ids"][0],
                    "evidence_ids": [package["allowed_evidence_ids"][0]],
                    "confidence": "bounded",
                    "modality": "reported",
                    "attributes": {
                        "kind": "background",
                        "localized_title": {
                            "en": "Helpful background",
                            "zh-CN": "补充背景",
                        },
                    },
                },
            ],
        },
    )

    assert imported["status"] == "passed"
    assert imported["auto_apply_status"] == "auto_applied"
    supplemental = service.matter_detail(
        matter_id=matter_id,
        locale="zh-CN",
    )["ai_supplemental_information"]
    assert supplemental["status"] == "current"
    assert supplemental["items"][0]["title"] == {
        "en": "Helpful background",
        "zh-CN": "补充背景",
    }


def test_installed_runtime_does_not_treat_caller_directory_as_public_root(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv("MATTERS_REPOSITORY_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)

    assert runtime.repository_root() == runtime.Path(runtime.__file__).resolve().parent
