from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json

from matters.api.http.app import application, create_application


@dataclass(frozen=True)
class CoverDecision:
    matter_id: str
    asset_id: str
    active: bool


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

    def pending_analysis_packages(self, *, offset: int, limit: int):
        return self._record(
            "pending_analysis_packages",
            {"offset": offset, "limit": limit},
            {"items": [], "offset": offset, "limit": limit},
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

    def submit_matter_correction(self, **kwargs):
        return self._record(
            "submit_matter_correction",
            kwargs,
            {"status": "auto_applied"},
        )

    def set_matter_cover(self, **kwargs):
        return self._record(
            "set_matter_cover",
            kwargs,
            CoverDecision(
                str(kwargs["matter_id"]),
                str(kwargs["asset_id"]),
                bool(kwargs["active"]),
            ),
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
                "sort": "recent",
                "offset": 0,
                "limit": 60,
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
            "&time=recent&sort=title&offset=20&limit=10"
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
                "time_filter": "recent",
                "sort": "title",
                "offset": 20,
                "limit": 10,
            },
        ),
        ("locale_registry", {}),
        ("capabilities", {}),
        ("object_coverage_summary", {}),
    ]


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


def test_entrypoint_http_accepts_only_optional_post_result_correction_and_cover():
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
    _, covered = request(
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
    assert covered["result"]["asset_id"] == "asset:1"
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
        (
            "set_matter_cover",
            {
                "matter_id": "matter:1",
                "asset_id": "asset:1",
                "active": True,
                "rationale": "Best visual",
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
