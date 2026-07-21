from __future__ import annotations

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
    "list_source_groups",
    "get_source_group",
    "rebase_source_groups",
    "get_matter_graph",
    "get_node_quick_view",
    "get_world_model",
    "list_model_contracts",
    "get_model_contract",
    "get_situation_context",
    "get_ai_history",
    "list_pending_ai_feedback",
    "record_user_observation",
    "record_prediction_feedback",
    "report_model_miss",
    "get_coverage",
    "get_stage_audit",
    "list_pending_analysis",
    "import_autonomous_result",
    "run_maintenance",
    "run_planned_maintenance",
    "submit_correction",
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
    "set_cover",
}


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

    def matter_situation_graph(self, **kwargs):
        return self._record(
            "matter_situation_graph",
            kwargs,
            {"matter_id": kwargs["matter_id"], "nodes": []},
        )

    def matter_node_quick_view(self, **kwargs):
        return self._record(
            "matter_node_quick_view",
            kwargs,
            {"node_id": kwargs["node_id"], "sources": []},
        )

    def matter_world_model(self, **kwargs):
        return self._record(
            "matter_world_model",
            kwargs,
            {"matter_id": kwargs["matter_id"], "items": []},
        )

    def ai_model_contracts(self, **kwargs):
        return self._record(
            "ai_model_contracts",
            kwargs,
            {"items": [{"model_id": "A3_matters_ai_gateway_operation"}]},
        )

    def ai_model_contract(self, **kwargs):
        return self._record(
            "ai_model_contract",
            kwargs,
            {"contract": {"model_id": kwargs["model_id"]}},
        )

    def ai_situation_context(self, **kwargs):
        return self._record(
            "ai_situation_context",
            kwargs,
            {"matter_id": kwargs["matter_id"], "completeness": "partial"},
        )

    def ai_history(self, **kwargs):
        return self._record(
            "ai_history",
            kwargs,
            {"matter_id": kwargs["matter_id"], "timeline": []},
        )

    def pending_ai_feedback(self, **kwargs):
        return self._record(
            "pending_ai_feedback",
            kwargs,
            {"matter_id": kwargs["matter_id"], "items": []},
        )

    def record_user_observation(self, **kwargs):
        return self._record(
            "record_user_observation",
            kwargs,
            {"status": "pending_owner", "canonical_write": False},
        )

    def record_world_model_feedback(self, **kwargs):
        return self._record(
            "record_world_model_feedback",
            kwargs,
            {"disposition": kwargs["disposition"], "model_miss_required": False},
        )

    def report_model_miss(self, **kwargs):
        return self._record(
            "report_model_miss",
            kwargs,
            {"status": "development_repair_queued"},
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
                        "object_id": "source:1",
                        "object_kind": "occurrence",
                        "first_gap_stage": "analysis",
                    },
                ),
                "offset": kwargs["offset"],
                "limit": kwargs["limit"],
                "total_matching": 1,
            },
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
            {"status": "accepted_recompute_queued"},
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
            "time": "all",
            "sort": "activity",
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
    stage_audit = mcp.call_tool(
        "get_stage_audit",
        {"offset": 5, "limit": 25, "object_kind": "occurrence"},
    )

    assert browser["result"]["surface"] == "object_browser"
    assert catalog["result"]["limit"] == 60
    assert matter["result"]["matter_id"] == "matter:1"
    assert evidence["result"]["limit"] == 25
    assert coverage["result"]["coverage_status"] == "current"
    assert stage_audit["result"]["objects"][0]["first_gap_stage"] == "analysis"
    assert service.calls == [
        (
            "object_browser_projection",
            {
                "locale": "zh-CN",
                "query": "plan",
                "status": "in_progress",
                "time_filter": "all",
                "sort": "activity",
                "start_year": "all",
                "people": (),
                "relationships": (),
                "topic_types": (),
                "source_types": (),
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
                "sort": "activity",
                "start_year": "all",
                "people": (),
                "relationships": (),
                "topic_types": (),
                "source_types": (),
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
        (
            "object_stage_audit",
            {"offset": 5, "limit": 25, "object_kind": "occurrence"},
        ),
    ]


def test_entrypoint_mcp_forwards_indexed_surface_drilldown_filters():
    service = FakeService()
    mcp = MattersMCP(service)

    response = mcp.call_tool(
        "get_stage_audit",
        {
            "surface_id": "world_model",
            "surface_status": "stale",
            "owner_id": "C11_guard_prediction",
            "failure_class": "world_model_expired",
            "freshness": "stale",
            "ui_ready": False,
        },
    )

    assert response["result"]["run_identity"] == "sha256:test"
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
        },
    )


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
    assert packages["result"]["execution_profile_identity"] == (
        "execution-profile:test"
    )
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


def test_entrypoint_mcp_runs_model_independent_planned_maintenance():
    service = FakeService()
    mcp = MattersMCP(service)

    result = mcp.call_tool(
        "run_planned_maintenance",
        {
            "run_id": "maintenance:mcp",
            "authorization_identity": "authorization:current",
            "inventory_identity": "inventory:current",
            "coverage_identity": "coverage:current",
            "changed_object_ids": ["occurrence:2", "occurrence:1"],
            "resource_budget": {
                "max_tasks": 6,
                "max_retries_per_task": 1,
                "max_concurrency": 2,
            },
        },
    )

    assert result["result"] == {
        "status": "no_change",
        "run_id": "maintenance:mcp",
    }
    request = service.calls[0][1]["request"]
    assert request.changed_object_ids == ("occurrence:1", "occurrence:2")
    assert request.resource_budget == {
        "max_tasks": 6,
        "max_retries_per_task": 1,
        "max_concurrency": 2,
    }


def test_entrypoint_mcp_exposes_unified_ai_gateway_and_feedback_tools():
    service = FakeService()
    mcp = MattersMCP(service)

    model_map = mcp.call_tool(
        "list_model_contracts",
        {"purpose": "history", "related_to": "C12", "offset": 2, "limit": 10},
    )
    model = mcp.call_tool(
        "get_model_contract",
        {"model_id": "A3_matters_ai_gateway_operation"},
    )
    context = mcp.call_tool(
        "get_situation_context",
        {
            "matter_id": "matter:1",
            "locale": "zh-CN",
            "graph_limit": 70,
            "world_limit": 30,
        },
    )
    history = mcp.call_tool(
        "get_ai_history",
        {"matter_id": "matter:1", "locale": "en", "offset": 5, "limit": 20},
    )
    pending = mcp.call_tool(
        "list_pending_ai_feedback",
        {"matter_id": "matter:1", "offset": 0, "limit": 25},
    )
    observation = mcp.call_tool(
        "record_user_observation",
        {
            "matter_id": "matter:1",
            "observation_kind": "event",
            "statement": "The appointment happened.",
            "observed_at": "2026-07-20T12:00:00+00:00",
            "source_ref": "conversation:codex:test",
        },
    )
    feedback = mcp.call_tool(
        "record_prediction_feedback",
        {
            "matter_id": "matter:1",
            "advisory_id": "world-advisory:1",
            "disposition": "confirmed",
            "observed_at": "2026-07-20T12:00:00+00:00",
            "observation_statement": "The expected event happened.",
            "observation_evidence_ids": ["evidence:1"],
        },
    )
    miss = mcp.call_tool(
        "report_model_miss",
        {
            "failure_class": "missing_owner",
            "expected_behavior": "The gateway should find one owner.",
            "observed_behavior": "No owner represented the case.",
            "model_path": "flowguard_models/agent_operation_models.py",
            "private_evidence_handle": "private-evidence:ai-gateway-test",
            "current_runtime_disposition": "partial",
        },
    )

    assert all(
        result["ok"] is True
        for result in (
            model_map,
            model,
            context,
            history,
            pending,
            observation,
            feedback,
            miss,
        )
    )
    assert observation["result"]["canonical_write"] is False
    assert feedback["result"]["disposition"] == "confirmed"
    assert miss["result"]["status"] == "development_repair_queued"
    assert service.calls == [
        (
            "ai_model_contracts",
            {
                "purpose": "history",
                "related_to": "C12",
                "offset": 2,
                "limit": 10,
            },
        ),
        (
            "ai_model_contract",
            {"model_id": "A3_matters_ai_gateway_operation"},
        ),
        (
            "ai_situation_context",
            {
                "matter_id": "matter:1",
                "locale": "zh-CN",
                "graph_limit": 70,
                "world_limit": 30,
            },
        ),
        (
            "ai_history",
            {
                "matter_id": "matter:1",
                "locale": "en",
                "offset": 5,
                "limit": 20,
            },
        ),
        (
            "pending_ai_feedback",
            {"matter_id": "matter:1", "offset": 0, "limit": 25},
        ),
        (
            "record_user_observation",
            {
                "matter_id": "matter:1",
                "observation_kind": "event",
                "statement": "The appointment happened.",
                "observed_at": "2026-07-20T12:00:00+00:00",
                "source_ref": "conversation:codex:test",
            },
        ),
        (
            "record_world_model_feedback",
            {
                "matter_id": "matter:1",
                "advisory_id": "world-advisory:1",
                "disposition": "confirmed",
                "observed_at": "2026-07-20T12:00:00+00:00",
                "observation_statement": "The expected event happened.",
                "observation_evidence_ids": ("evidence:1",),
            },
        ),
        (
            "report_model_miss",
            {
                "failure_class": "missing_owner",
                "expected_behavior": "The gateway should find one owner.",
                "observed_behavior": "No owner represented the case.",
                "model_path": "flowguard_models/agent_operation_models.py",
                "private_evidence_handle": "private-evidence:ai-gateway-test",
                "current_runtime_disposition": "partial",
            },
        ),
    ]


def test_entrypoint_mcp_reads_and_rebases_source_groups():
    service = FakeService()
    mcp = MattersMCP(service)

    listed = mcp.call_tool(
        "list_source_groups",
        {"query": "travel", "offset": 5, "limit": 25},
    )
    detail = mcp.call_tool(
        "get_source_group",
        {
            "group_id": "source-group:travel",
            "member_offset": 10,
            "member_limit": 20,
        },
    )
    rebased = mcp.call_tool(
        "rebase_source_groups",
        {
            "after_object_id": "occurrence:prior",
            "after_scope_id": "scope:prior",
            "limit": 250,
        },
    )

    assert listed["ok"] is detail["ok"] is rebased["ok"] is True
    assert service.calls == [
        (
            "source_groups",
            {"offset": 5, "limit": 25, "query": "travel"},
        ),
        (
            "source_group_detail",
            {
                "group_id": "source-group:travel",
                "member_offset": 10,
                "member_limit": 20,
            },
        ),
        (
            "rebase_source_group_index",
            {
                "after_object_id": "occurrence:prior",
                "after_scope_id": "scope:prior",
                "limit": 250,
            },
        ),
    ]


def test_entrypoint_mcp_writes_only_optional_correction_and_skill_sync():
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
    synced = mcp.call_tool(
        "sync_skills",
        {"transaction_id_prefix": "mcp-test"},
    )

    assert corrected["result"]["status"] == "accepted_recompute_queued"
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
        ("get_stage_audit", {"object_kind": "unknown"}),
        ("get_situation_context", {"matter_id": "matter:1", "graph_limit": 0}),
        ("get_ai_history", {"matter_id": "matter:1", "limit": 51}),
        (
            "record_user_observation",
            {
                "matter_id": "matter:1",
                "observation_kind": "unknown",
                "statement": "Something changed.",
                "observed_at": "2026-07-20T12:00:00+00:00",
            },
        ),
        (
            "record_prediction_feedback",
            {
                "matter_id": "matter:1",
                "advisory_id": "world-advisory:1",
                "disposition": "confirmed",
                "observed_at": "2026-07-20T12:00:00+00:00",
                "observation_statement": "Observed.",
                "observation_evidence_ids": [],
            },
        ),
        (
            "report_model_miss",
            {
                "failure_class": "gap",
                "expected_behavior": "Expected.",
                "observed_behavior": "Observed.",
                "model_path": "flowguard_models/agent_operation_models.py",
                "private_evidence_handle": "not-private",
                "current_runtime_disposition": "partial",
            },
        ),
        ("import_autonomous_result", {"result": []}),
        ("run_maintenance", {"limit": True}),
        (
            "submit_correction",
            {"matter_id": "matter:1", "rationale": ""},
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
        "stage_audit": mcp.call_tool("get_stage_audit"),
        "analysis": mcp.call_tool("list_pending_analysis"),
        "maintenance": mcp.call_tool("run_maintenance", {"limit": 1}),
    }

    assert all(response["ok"] is True for response in responses.values())
    assert responses["browser"]["result"]["surface"] == "object_browser"
    assert responses["matters"]["result"]["items"] == []
    assert responses["coverage"]["result"]["registered_object_count"] == 0
    assert responses["stage_audit"]["result"]["total_objects"] == 0
    assert responses["analysis"]["result"]["items"] == []
