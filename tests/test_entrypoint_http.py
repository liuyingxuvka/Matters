from __future__ import annotations

from io import BytesIO
import json

from matters.api.http.app import application, create_application


class FakeService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def _record(self, name: str, arguments: dict[str, object], result: object):
        self.calls.append((name, arguments))
        return result

    def capabilities(self):
        return self._record(
            "capabilities",
            {},
            {"object_browser": "available", "autonomous_maintenance": True},
        )

    def locale_registry(self):
        return self._record(
            "locale_registry",
            {},
            {
                "default_locale": "en",
                "available_locales": ("en", "zh-CN"),
                "fallback_policy": "none",
            },
        )

    def object_coverage_summary(self):
        return self._record(
            "object_coverage_summary",
            {},
            {"coverage_status": "current", "ui_ready_object_count": 1},
        )

    def object_stage_audit(self, **kwargs):
        return self._record(
            "object_stage_audit",
            kwargs,
            {
                "run_identity": "sha256:test",
                "objects": (
                    {
                        "object_id": "matter:1",
                        "object_kind": "matter",
                        "first_gap_stage": "generated_hero",
                    },
                ),
                "offset": kwargs["offset"],
                "limit": kwargs["limit"],
                "total_matching": 1,
            },
        )

    def object_browser_projection(self, **kwargs):
        return self._record(
            "object_browser_projection",
            kwargs,
            {
                "surface": "object_browser",
                "selected_locale": kwargs["locale"],
                "catalog": {"items": []},
            },
        )

    def object_catalog_page(self, **kwargs):
        return self._record(
            "object_catalog_page",
            kwargs,
            {
                "items": [],
                "offset": kwargs["offset"],
                "limit": kwargs["limit"],
                "selected_locale": kwargs["locale"],
            },
        )

    def matter_detail(self, *, matter_id: str, locale: str):
        return self._record(
            "matter_detail",
            {"matter_id": matter_id, "locale": locale},
            {"matter": {"matter_id": matter_id}, "selected_locale": locale},
        )

    def matter_evidence(self, *, matter_id: str, offset: int, limit: int):
        return self._record(
            "matter_evidence",
            {"matter_id": matter_id, "offset": offset, "limit": limit},
            {"items": [], "offset": offset, "limit": limit},
        )

    def source_groups(self, **kwargs):
        return self._record(
            "source_groups",
            kwargs,
            {"items": [], "offset": kwargs["offset"], "limit": kwargs["limit"]},
        )

    def source_group_detail(self, **kwargs):
        return self._record(
            "source_group_detail",
            kwargs,
            {"summary": {"group_id": kwargs["group_id"]}, "members": []},
        )

    def rebase_source_group_index(self, **kwargs):
        return self._record(
            "rebase_source_group_index",
            kwargs,
            {"status": "partial", "has_more": True},
        )

    def pending_analysis_packages(self, *, offset: int, limit: int):
        return self._record(
            "pending_analysis_packages",
            {"offset": offset, "limit": limit},
            {
                "items": [],
                "offset": offset,
                "limit": limit,
                "execution_profile_identity": "execution-profile:test",
            },
        )

    def import_autonomous_result(self, **kwargs):
        return self._record(
            "import_autonomous_result",
            kwargs,
            {"status": "passed", "auto_apply_status": "auto_applied"},
        )

    def run_maintenance_cycle(self, *, limit: int):
        return self._record(
            "run_maintenance_cycle",
            {"limit": limit},
            {"status": "idle", "processed_count": 0},
        )

    def run_planned_maintenance(self, request):
        return self._record(
            "run_planned_maintenance",
            {"request": request},
            {"status": "no_change", "run_id": request.run_id},
        )

    def submit_matter_correction(self, **kwargs):
        return self._record(
            "submit_matter_correction",
            kwargs,
            {"status": "auto_applied"},
        )

    def resolve_visual_preview(self, *, preview_token: str, hero: bool):
        return self._record(
            "resolve_visual_preview",
            {"preview_token": preview_token, "hero": hero},
            (b"PNG", "image/png"),
        )


def request(
    app,
    *,
    method: str = "GET",
    path: str = "/",
    query: str = "",
    body: object | None = None,
):
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": BytesIO(raw),
    }
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)

    response = b"".join(app(environ, start_response))
    content_type = str(captured["headers"].get("Content-Type", ""))
    payload = json.loads(response) if content_type.startswith("application/json") else response
    return captured, payload


def test_entrypoint_http_browser_defaults_to_english_and_has_no_store_cache():
    service = FakeService()
    captured, payload = request(create_application(service), path="/api/browser")

    assert captured["status"] == "200 OK"
    assert captured["headers"]["Cache-Control"] == "no-store"
    assert payload["result"]["surface"] == "object_browser"
    assert service.calls == [
        (
            "object_browser_projection",
            {
                "locale": "en",
                "query": "",
                "status": "all",
                "time_filter": "all",
                    "sort": "activity",
                    "offset": 0,
                    "limit": 60,
                    "root_only": True,
                    "start_year": "all",
                    "people": (),
                    "relationships": (),
                    "topic_types": (),
                    "source_types": (),
                },
            )
        ]


def test_entrypoint_http_catalog_locales_health_and_coverage_are_explicit():
    service = FakeService()
    app = create_application(service)

    captured, payload = request(
        app,
        path="/api/catalog",
        query=(
            "locale=zh-CN&query=%E8%AE%A1%E5%88%92&status=in_progress"
            "&time=all&sort=activity&offset=20&limit=10"
        ),
    )
    assert captured["status"] == "200 OK"
    assert payload["result"]["selected_locale"] == "zh-CN"

    _, locales = request(app, path="/api/locales")
    _, health = request(app, path="/health")
    _, coverage = request(app, path="/api/coverage")
    assert locales["result"]["default_locale"] == "en"
    assert health["result"]["object_browser"] == "available"
    assert coverage["result"]["ui_ready_object_count"] == 1
    assert service.calls == [
        (
            "object_catalog_page",
            {
                "locale": "zh-CN",
                "query": "计划",
                "status": "in_progress",
                "time_filter": "all",
                "sort": "activity",
                "offset": 20,
                "limit": 10,
                "root_only": True,
                "start_year": "all",
                "people": (),
                "relationships": (),
                "topic_types": (),
                "source_types": (),
            },
        ),
        ("locale_registry", {}),
        ("capabilities", {}),
        ("object_coverage_summary", {}),
    ]


def test_entrypoint_http_exposes_bounded_read_only_stage_audit():
    service = FakeService()
    app = create_application(service)

    captured, payload = request(
        app,
        path="/api/coverage/audit",
        query="offset=5&limit=25&object_kind=matter",
    )

    assert captured["status"] == "200 OK"
    assert payload["result"]["run_identity"] == "sha256:test"
    assert payload["result"]["objects"][0]["first_gap_stage"] == (
        "generated_hero"
    )
    assert service.calls == [
        (
            "object_stage_audit",
            {"offset": 5, "limit": 25, "object_kind": "matter"},
        )
    ]

    invalid, invalid_payload = request(
        app,
        path="/api/coverage/audit",
        query="object_kind=unknown",
    )
    assert invalid["status"] == "400 Bad Request"
    assert invalid_payload["error"]["code"] == "invalid_object_kind"
    assert len(service.calls) == 1


def test_entrypoint_http_forwards_indexed_surface_drilldown_filters():
    service = FakeService()
    app = create_application(service)

    captured, _payload = request(
        app,
        path="/api/coverage/audit",
        query=(
            "surface_id=world_model&surface_status=stale&"
            "owner_id=C11_guard_prediction&"
            "failure_class=world_model_expired&freshness=stale&"
            "ui_ready=false&surface_only=true"
        ),
    )

    assert captured["status"] == "200 OK"
    assert service.calls[-1] == (
        "object_stage_audit",
        {
            "offset": 0,
            "limit": 100,
            "object_kind": "",
            "surface_id": "world_model",
            "surface_status": "stale",
            "owner_id": "C11_guard_prediction",
            "failure_class": "world_model_expired",
            "freshness": "stale",
            "ui_ready": False,
            "surface_only": True,
        },
    )


def test_entrypoint_http_exposes_bounded_path_free_source_groups():
    service = FakeService()
    app = create_application(service)

    _, groups = request(
        app,
        path="/api/source-groups",
        query="query=travel&offset=5&limit=25",
    )
    _, detail = request(
        app,
        path="/api/source-groups/source-group%3Atrip",
        query="member_offset=10&member_limit=20",
    )

    assert groups["result"]["limit"] == 25
    assert detail["result"]["summary"]["group_id"] == "source-group:trip"
    assert service.calls == [
        (
            "source_groups",
            {"offset": 5, "limit": 25, "query": "travel"},
        ),
        (
            "source_group_detail",
            {
                "group_id": "source-group:trip",
                "member_offset": 10,
                "member_limit": 20,
            },
        ),
    ]


def test_entrypoint_http_rebuilds_one_bounded_source_group_page():
    service = FakeService()
    app = create_application(service)

    captured, payload = request(
        app,
        method="POST",
        path="/api/source-groups/rebase",
        body={
            "after_object_id": "occurrence:prior",
            "after_scope_id": "scope:prior",
            "limit": 250,
        },
    )

    assert captured["status"] == "200 OK"
    assert payload["result"]["status"] == "partial"
    assert service.calls == [
        (
            "rebase_source_group_index",
            {
                "after_object_id": "occurrence:prior",
                "after_scope_id": "scope:prior",
                "limit": 250,
            },
        )
    ]


def test_entrypoint_http_catalog_parses_explicit_child_search_scope():
    service = FakeService()
    app = create_application(service)

    captured, _payload = request(
        app,
        path="/api/catalog",
        query="query=company&root_only=false",
    )
    assert captured["status"] == "200 OK"
    assert service.calls[0] == (
        "object_catalog_page",
        {
            "locale": "en",
            "query": "company",
            "status": "all",
            "time_filter": "all",
            "sort": "activity",
            "offset": 0,
            "limit": 60,
            "root_only": False,
            "start_year": "all",
            "people": (),
            "relationships": (),
            "topic_types": (),
            "source_types": (),
        },
    )

    invalid, payload = request(
        app,
        path="/api/catalog",
        query="root_only=sometimes",
    )
    assert invalid["status"] == "400 Bad Request"
    assert payload["error"]["code"] == "invalid_boolean_query"


def test_entrypoint_http_catalog_accepts_bounded_grouped_filters():
    service = FakeService()
    app = create_application(service)

    captured, _payload = request(
        app,
        path="/api/catalog",
        query=(
            "start_year=2026&people=Alice&people=Bob"
            "&relationships=depends_on&topic_type=travel"
            "&source_type=document"
        ),
    )

    assert captured["status"] == "200 OK"
    assert service.calls[0][1] == {
        "locale": "en",
        "query": "",
        "status": "all",
        "time_filter": "all",
        "sort": "activity",
        "offset": 0,
        "limit": 60,
        "root_only": True,
        "start_year": "2026",
        "people": ("Alice", "Bob"),
        "relationships": ("depends_on",),
        "topic_types": ("travel",),
        "source_types": ("document",),
    }


def test_entrypoint_http_detail_evidence_and_representative_visual():
    service = FakeService()
    app = create_application(service)

    _, detail = request(
        app,
        path="/api/matters/matter%3A1",
        query="locale=zh-CN",
    )
    _, evidence = request(
        app,
        path="/api/matters/matter%3A1/evidence",
        query="offset=5&limit=25",
    )
    captured, image = request(
        app,
        path="/api/visuals/preview%3A1",
        query="size=hero",
    )

    assert detail["result"]["selected_locale"] == "zh-CN"
    assert evidence["result"]["limit"] == 25
    assert captured["status"] == "200 OK"
    assert captured["headers"]["Cache-Control"] == "private, max-age=300"
    assert image == b"PNG"
    assert service.calls == [
        ("matter_detail", {"matter_id": "matter:1", "locale": "zh-CN"}),
        (
            "matter_evidence",
            {"matter_id": "matter:1", "offset": 5, "limit": 25},
        ),
        (
            "resolve_visual_preview",
            {"preview_token": "preview:1", "hero": True},
        ),
    ]


def test_entrypoint_http_pending_packages_publish_runtime_profile_identity():
    service = FakeService()
    app = create_application(service)

    captured, payload = request(
        app,
        path="/api/analysis/packages",
        query="offset=0&limit=20",
    )

    assert captured["status"] == "200 OK"
    assert payload["result"]["execution_profile_identity"] == (
        "execution-profile:test"
    )


def test_entrypoint_http_imports_ai_result_and_runs_maintenance():
    service = FakeService()
    app = create_application(service)
    result = {"status": "passed", "findings": []}

    _, imported = request(
        app,
        method="POST",
        path="/api/analysis/results",
        body={
            "package_id": "work:1",
            "provider_id": "codex-local",
            "provider_version": "current",
            "result": result,
        },
    )
    _, maintenance = request(
        app,
        method="POST",
        path="/api/maintenance/run",
        body={"limit": 7},
    )

    assert imported["result"]["auto_apply_status"] == "auto_applied"
    assert maintenance["result"]["status"] == "idle"
    assert service.calls == [
        (
            "import_autonomous_result",
            {
                "package_id": "work:1",
                "provider_id": "codex-local",
                "provider_version": "current",
                "result": result,
            },
        ),
        ("run_maintenance_cycle", {"limit": 7}),
    ]


def test_entrypoint_http_runs_model_independent_planned_maintenance():
    service = FakeService()
    app = create_application(service)

    captured, payload = request(
        app,
        method="POST",
        path="/api/maintenance/orchestration/run",
        body={
            "run_id": "maintenance:http",
            "authorization_identity": "authorization:current",
            "inventory_identity": "inventory:current",
            "coverage_identity": "coverage:current",
            "changed_object_ids": ["matter:2", "matter:1"],
            "resource_budget": {
                "max_tasks": 10,
                "max_retries_per_task": 0,
                "max_concurrency": 1,
            },
        },
    )

    assert captured["status"] == "200 OK"
    assert payload["result"] == {
        "status": "no_change",
        "run_id": "maintenance:http",
    }
    request_value = service.calls[0][1]["request"]
    assert request_value.changed_object_ids == ("matter:1", "matter:2")
    assert request_value.request_fingerprint.startswith("sha256:")


def test_entrypoint_http_accepts_correction_and_retires_ordinary_cover_write():
    service = FakeService()
    app = create_application(service)

    _, corrected = request(
        app,
        method="POST",
        path="/api/matters/matter%3A1/corrections",
        body={
            "rationale": "The state is outdated.",
            "field_name": "state",
            "corrected_value": "completed",
        },
    )
    cover_response, cover_payload = request(
        app,
        method="POST",
        path="/api/matters/matter%3A1/cover",
        body={
            "asset_id": "asset:1",
            "active": True,
            "rationale": "Best visual",
        },
    )

    assert corrected["result"]["status"] == "auto_applied"
    assert cover_response["status"] == "404 Not Found"
    assert cover_payload["error"]["code"] == "not_found"
    assert service.calls == [
        (
            "submit_matter_correction",
            {
                "matter_id": "matter:1",
                "rationale": "The state is outdated.",
                "field_name": "state",
                "corrected_value": "completed",
            },
        ),
    ]


def test_entrypoint_http_missing_injection_capability_and_bounds_fail_visibly():
    captured, payload = request(application, path="/health")
    assert captured["status"] == "503 Service Unavailable"
    assert payload["error"]["code"] == "service_not_injected"

    captured, payload = request(
        create_application(object()),
        path="/api/browser",
    )
    assert captured["status"] == "501 Not Implemented"
    assert payload["error"] == {
        "code": "capability_unavailable",
        "operation": "object_browser_projection",
    }

    service = FakeService()
    for query in (
        "offset=-1&limit=50",
        "offset=0&limit=0",
        "offset=0&limit=201",
        "offset=not-a-number&limit=50",
    ):
        captured, payload = request(
            create_application(service),
            path="/api/catalog",
            query=query,
        )
        assert captured["status"] == "400 Bad Request"
        assert payload["error"]["code"] == "invalid_page_bounds"
    assert service.calls == []
