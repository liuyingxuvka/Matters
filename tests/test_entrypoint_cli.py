from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import json

from matters.cli.main import run


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

    def set_matter_cover(
        self,
        *,
        matter_id: str,
        asset_id: str,
        active: bool,
        rationale: str,
    ):
        return self._record(
            "set_matter_cover",
            {
                "matter_id": matter_id,
                "asset_id": asset_id,
                "active": active,
                "rationale": rationale,
            },
            CoverDecision(matter_id, asset_id, active),
        )


def invoke(arguments: list[str], service: object):
    stdout = StringIO()
    stderr = StringIO()
    exit_code = run(
        arguments,
        service=service,
        stdout=stdout,
        stderr=stderr,
    )
    return exit_code, stdout.getvalue(), stderr.getvalue()


def test_entrypoint_cli_browser_defaults_to_english_and_filters_are_explicit():
    service = FakeService()

    exit_code, stdout, stderr = invoke(["browser"], service)

    assert exit_code == 0
    assert stderr == ""
    assert json.loads(stdout)["result"]["surface"] == "object_browser"
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

    service.calls.clear()
    exit_code, stdout, stderr = invoke(
        [
            "catalog",
            "--locale",
            "zh-CN",
            "--query",
            "计划",
            "--status",
            "in_progress",
            "--time",
            "recent",
            "--sort",
            "title",
            "--offset",
            "20",
            "--limit",
            "10",
        ],
        service,
    )
    assert exit_code == 0
    assert stderr == ""
    assert json.loads(stdout)["result"]["selected_locale"] == "zh-CN"
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
        )
    ]


def test_entrypoint_cli_exposes_locale_registry_without_a_language_fallback():
    service = FakeService()

    exit_code, stdout, stderr = invoke(["locales"], service)

    assert exit_code == 0
    assert stderr == ""
    assert service.calls == [("locale_registry", {})]
    assert json.loads(stdout)["result"] == {
        "available_locales": ["en", "zh-CN"],
        "default_locale": "en",
        "fallback_policy": "none",
    }


def test_entrypoint_cli_reads_detail_and_bounded_evidence():
    service = FakeService()

    detail = invoke(
        ["detail", "matter:1", "--locale", "zh-CN"],
        service,
    )
    evidence = invoke(
        ["evidence", "matter:1", "--offset", "5", "--limit", "25"],
        service,
    )

    assert detail[0] == evidence[0] == 0
    assert detail[2] == evidence[2] == ""
    assert json.loads(detail[1])["result"]["selected_locale"] == "zh-CN"
    assert json.loads(evidence[1])["result"]["limit"] == 25
    assert service.calls == [
        ("matter_detail", {"matter_id": "matter:1", "locale": "zh-CN"}),
        (
            "matter_evidence",
            {"matter_id": "matter:1", "offset": 5, "limit": 25},
        ),
    ]


def test_entrypoint_cli_imports_ai_result_and_runs_autonomous_maintenance(
    tmp_path,
):
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps({"status": "passed", "findings": []}),
        encoding="utf-8",
    )
    service = FakeService()

    imported = invoke(
        [
            "analysis-import",
            "work:1",
            str(result_file),
            "--provider-id",
            "codex-local",
            "--provider-version",
            "current",
        ],
        service,
    )
    maintenance = invoke(["maintenance", "--limit", "7"], service)

    assert imported[0] == maintenance[0] == 0
    assert json.loads(imported[1])["result"]["auto_apply_status"] == "auto_applied"
    assert json.loads(maintenance[1])["result"]["status"] == "idle"
    assert service.calls == [
        (
            "import_autonomous_result",
            {
                "package_id": "work:1",
                "provider_id": "codex-local",
                "provider_version": "current",
                "result": {"status": "passed", "findings": []},
            },
        ),
        ("run_maintenance_cycle", {"limit": 7}),
    ]


def test_entrypoint_cli_accepts_only_optional_post_result_correction_and_cover():
    service = FakeService()

    corrected = invoke(
        [
            "correct",
            "matter:1",
            "The state is outdated.",
            "--field",
            "state",
            "--value",
            "completed",
        ],
        service,
    )
    covered = invoke(
        ["cover", "matter:1", "asset:1", "--rationale", "Best visual"],
        service,
    )
    automatic = invoke(
        ["cover", "matter:1", "--automatic", "--rationale", "Let AI decide"],
        service,
    )

    assert corrected[0] == covered[0] == automatic[0] == 0
    assert json.loads(corrected[1])["result"]["status"] == "auto_applied"
    assert json.loads(covered[1])["result"]["asset_id"] == "asset:1"
    assert json.loads(automatic[1])["result"]["active"] is False
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
        (
            "set_matter_cover",
            {
                "matter_id": "matter:1",
                "asset_id": "",
                "active": False,
                "rationale": "Let AI decide",
            },
        ),
    ]


def test_entrypoint_cli_rejects_unbounded_catalog_and_missing_capability():
    service = FakeService()

    exit_code, stdout, stderr = invoke(["catalog", "--limit", "201"], service)
    assert exit_code == 4
    assert stdout == ""
    assert json.loads(stderr)["error"]["code"] == "invalid_request"
    assert service.calls == []

    exit_code, stdout, stderr = invoke(["browser"], object())
    assert exit_code == 3
    assert stdout == ""
    assert json.loads(stderr) == {
        "ok": False,
        "error": {
            "code": "capability_unavailable",
            "operation": "object_browser_projection",
        },
    }
