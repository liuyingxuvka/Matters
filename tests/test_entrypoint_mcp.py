from __future__ import annotations

from dataclasses import dataclass

import pytest

from matters.api.mcp.server import MattersMCP
from matters.application.orchestrator import MatterService
from matters.presentation.localization import UnsupportedLocale


EXPECTED_TOOLS = {
    "capabilities",
    "locales",
    "get_browser",
    "list_matters",
    "get_matter",
    "get_evidence",
    "get_coverage",
    "list_pending_analysis",
    "import_autonomous_result",
    "run_maintenance",
    "submit_correction",
    "set_cover",
    "sync_skills",
}

RETIRED_TOOL_NAMES = {
    "matters_get_projection",
    "matters_list_sources",
    "matters_list_review_queue",
    "matters_submit_tracking_intent",
    "matters_list_understanding_candidates",
    "matters_submit_understanding_intent",
    "matters_import_understanding_result",
}


@dataclass(frozen=True)
class FakeCoverDecision:
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
        if kwargs["locale"] not in {"en", "zh-CN"}:
            raise UnsupportedLocale(kwargs["locale"])
        return self._record(
            "object_browser_projection",
            kwargs,
            {"surface": "object_browser", "catalog": {"items": []}},
        )

    def object_catalog_page(self, **kwargs):
        return self._record(
            "object_catalog_page",
            kwargs,
            {
                "items": [],
                "offset": kwargs["offset"],
                "limit": kwargs["limit"],
            },
        )

    def matter_detail(self, *, matter_id: str, locale: str):
        if locale not in {"en", "zh-CN"}:
            raise UnsupportedLocale(locale)
        return self._record(
            "matter_detail",
            {"matter_id": matter_id, "locale": locale},
            {"matter_id": matter_id, "title": "Plan"},
        )

    def matter_evidence(self, *, matter_id: str, offset: int, limit: int):
        return self._record(
            "matter_evidence",
            {"matter_id": matter_id, "offset": offset, "limit": limit},
            {"items": [], "offset": offset, "limit": limit},
        )

    def object_coverage_summary(self):
        return self._record(
            "object_coverage_summary",
            {},
            {"coverage_status": "current", "ui_ready_object_count": 1},
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
            {"status": "accepted_recompute_queued"},
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
            FakeCoverDecision(matter_id, asset_id, active),
        )

    def synchronize_managed_skill_projections(
        self,
        *,
        transaction_id_prefix: str,
    ):
        return self._record(
            "synchronize_managed_skill_projections",
            {"transaction_id_prefix": transaction_id_prefix},
            {"status": "current", "default_global_install": False},
        )


def test_entrypoint_mcp_advertises_exact_autonomous_tool_contract():
    tools = MattersMCP.list_tools()
    names = {tool["name"] for tool in tools}

    assert names == EXPECTED_TOOLS
    assert len(tools) == len(EXPECTED_TOOLS)
    assert names.isdisjoint(RETIRED_TOOL_NAMES)
    assert all(
        tool["inputSchema"]["additionalProperties"] is False
        for tool in tools
    )


def test_entrypoint_mcp_reads_browser_catalog_detail_evidence_and_coverage():
    service = FakeService()
    mcp = MattersMCP(service)

    browser = mcp.call_tool(
        "get_browser",
        {
            "locale": "zh-CN",
            "query": "plan",
            "status": "in_progress",
            "time": "recent",
            "sort": "title",
            "offset": 20,
            "limit": 10,
        },
    )
    catalog = mcp.call_tool("list_matters", {})
    matter = mcp.call_tool(
        "get_matter",
        {"matter_id": "matter:1", "locale": "en"},
    )
    evidence = mcp.call_tool(
        "get_evidence",
        {"matter_id": "matter:1", "offset": 5, "limit": 25},
    )
    coverage = mcp.call_tool("get_coverage", {})

    assert browser["result"]["surface"] == "object_browser"
    assert catalog["result"]["limit"] == 60
    assert matter["result"]["matter_id"] == "matter:1"
    assert evidence["result"]["limit"] == 25
    assert coverage["result"]["coverage_status"] == "current"
    assert service.calls == [
        (
            "object_browser_projection",
            {
                "locale": "zh-CN",
                "query": "plan",
                "status": "in_progress",
                "time_filter": "recent",
                "sort": "title",
                "offset": 20,
                "limit": 10,
            },
        ),
        (
            "object_catalog_page",
            {
                "locale": "en",
                "query": "",
                "status": "all",
                "time_filter": "all",
                "sort": "recent",
                "offset": 0,
                "limit": 60,
            },
        ),
        ("matter_detail", {"matter_id": "matter:1", "locale": "en"}),
        (
            "matter_evidence",
            {"matter_id": "matter:1", "offset": 5, "limit": 25},
        ),
        ("object_coverage_summary", {}),
    ]


def test_entrypoint_mcp_runs_autonomous_analysis_and_maintenance():
    service = FakeService()
    mcp = MattersMCP(service)

    packages = mcp.call_tool(
        "list_pending_analysis",
        {"offset": 20, "limit": 10},
    )
    imported = mcp.call_tool(
        "import_autonomous_result",
        {
            "package_id": "work:1",
            "provider_id": "codex-local",
            "provider_version": "1",
            "result": {"status": "passed", "findings": []},
        },
    )
    maintenance = mcp.call_tool("run_maintenance", {})

    assert packages["result"]["limit"] == 10
    assert imported["result"]["auto_apply_status"] == "auto_applied"
    assert maintenance["result"]["status"] == "idle"
    assert service.calls == [
        ("pending_analysis_packages", {"offset": 20, "limit": 10}),
        (
            "import_autonomous_result",
            {
                "package_id": "work:1",
                "provider_id": "codex-local",
                "provider_version": "1",
                "result": {"status": "passed", "findings": []},
            },
        ),
        ("run_maintenance_cycle", {"limit": 20}),
    ]


def test_entrypoint_mcp_writes_only_optional_correction_cover_and_skill_sync():
    service = FakeService()
    mcp = MattersMCP(service)

    corrected = mcp.call_tool(
        "submit_correction",
        {
            "matter_id": "matter:1",
            "rationale": "The status is outdated.",
            "field_name": "state",
            "corrected_value": "completed",
        },
    )
    cover = mcp.call_tool(
        "set_cover",
        {
            "matter_id": "matter:1",
            "asset_id": "asset:1",
            "active": True,
            "rationale": "This image represents the Matter.",
        },
    )
    automatic_cover = mcp.call_tool(
        "set_cover",
        {
            "matter_id": "matter:1",
            "active": False,
            "rationale": "Return to automatic selection.",
        },
    )
    synced = mcp.call_tool(
        "sync_skills",
        {"transaction_id_prefix": "mcp-test"},
    )

    assert corrected["result"]["status"] == "accepted_recompute_queued"
    assert cover["result"]["asset_id"] == "asset:1"
    assert automatic_cover["result"]["active"] is False
    assert synced["result"]["status"] == "current"
    assert service.calls == [
        (
            "submit_matter_correction",
            {
                "matter_id": "matter:1",
                "rationale": "The status is outdated.",
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
                "rationale": "This image represents the Matter.",
            },
        ),
        (
            "set_matter_cover",
            {
                "matter_id": "matter:1",
                "asset_id": "",
                "active": False,
                "rationale": "Return to automatic selection.",
            },
        ),
        (
            "synchronize_managed_skill_projections",
            {"transaction_id_prefix": "mcp-test"},
        ),
    ]


@pytest.mark.parametrize(
    ("name", "arguments"),
    (
        ("get_browser", {"limit": 201}),
        ("list_matters", {"status": "blocked"}),
        ("get_matter", {}),
        ("get_evidence", {"matter_id": "matter:1", "offset": -1}),
        ("import_autonomous_result", {"result": []}),
        ("run_maintenance", {"limit": True}),
        (
            "submit_correction",
            {"matter_id": "matter:1", "rationale": ""},
        ),
        (
            "set_cover",
            {
                "matter_id": "matter:1",
                "active": True,
                "rationale": "Pin cover.",
            },
        ),
        (
            "sync_skills",
            {"transaction_id_prefix": "x" * 65},
        ),
    ),
)
def test_entrypoint_mcp_rejects_invalid_arguments(
    name: str,
    arguments: dict[str, object],
):
    assert MattersMCP(FakeService()).call_tool(name, arguments) == {
        "ok": False,
        "error": {"code": "invalid_arguments"},
    }


def test_entrypoint_mcp_rejects_unknown_retired_and_unavailable_tools():
    mcp = MattersMCP(FakeService())

    assert mcp.call_tool("unknown", {})["error"]["code"] == "tool_not_found"
    for retired in RETIRED_TOOL_NAMES:
        assert mcp.call_tool(retired, {})["error"]["code"] == "tool_not_found"
    assert MattersMCP(object()).call_tool("list_matters", {})["error"] == {
        "code": "capability_unavailable",
        "operation": "object_catalog_page",
    }


def test_entrypoint_mcp_reports_unsupported_locale_without_fallback():
    service = FakeService()
    mcp = MattersMCP(service)

    response = mcp.call_tool("get_browser", {"locale": "fr"})

    assert response == {
        "ok": False,
        "error": {
            "code": "unsupported_locale",
            "available_locales": ["en", "zh-CN"],
        },
    }


def test_entrypoint_mcp_json_serializes_dataclass_service_results():
    result = MattersMCP(FakeService()).call_tool(
        "set_cover",
        {
            "matter_id": "matter:1",
            "asset_id": "asset:1",
            "active": True,
            "rationale": "Pin cover.",
        },
    )

    assert result == {
        "ok": True,
        "result": {
            "matter_id": "matter:1",
            "asset_id": "asset:1",
            "active": True,
        },
    }


def test_entrypoint_mcp_uses_current_real_service_object_browser_methods(
    tmp_path,
):
    repository_root = tmp_path / "repository"
    repository_root.mkdir()
    service = MatterService(
        private_root=tmp_path / "private",
        repository_root=repository_root,
    )
    mcp = MattersMCP(service)

    responses = {
        "locales": mcp.call_tool("locales"),
        "browser": mcp.call_tool("get_browser"),
        "matters": mcp.call_tool("list_matters"),
        "coverage": mcp.call_tool("get_coverage"),
        "analysis": mcp.call_tool("list_pending_analysis"),
        "maintenance": mcp.call_tool("run_maintenance", {"limit": 1}),
    }

    assert all(response["ok"] is True for response in responses.values())
    assert responses["browser"]["result"]["surface"] == "object_browser"
    assert responses["matters"]["result"]["items"] == []
    assert responses["coverage"]["result"]["registered_object_count"] == 0
    assert responses["analysis"]["result"]["items"] == []
