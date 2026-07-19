from io import BytesIO
import json

from matters import runtime
from matters.api.http.app import create_application
from matters.api.mcp.server import MattersMCP
from matters.application.orchestrator import MatterService
from matters.application.source_workflows import SourceWorkflow
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
    )
    package = service.pending_analysis_packages()["items"][0]
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
            ],
        },
    )
    assert imported["auto_apply_status"] == "auto_applied"
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
    assert card["visual"]["status"] == "current"
    assert card["visual"]["preview_token"]
    assert str(private_source_root) not in json.dumps(browser)

    matter_id = card["matter_id"]
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
    assert coverage["result"]["registered_object_count"] == 1


def test_real_service_coverage_exposes_only_aggregate_progress(tmp_path):
    service, private_source_root = _service(tmp_path)

    coverage = service.object_coverage_summary()
    serialized = json.dumps(coverage)

    assert coverage["registered_object_count"] == 1
    assert coverage["ui_ready_object_count"] == 1
    assert coverage["coverage_status"] == "complete"
    assert str(private_source_root) not in serialized
    assert "plan.txt" not in serialized
    assert "occurrence:" not in serialized


def test_installed_runtime_does_not_treat_caller_directory_as_public_root(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv("MATTERS_REPOSITORY_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)

    assert runtime.repository_root() == runtime.Path(runtime.__file__).resolve().parent
