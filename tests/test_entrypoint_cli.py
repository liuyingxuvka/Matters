from __future__ import annotations

from io import StringIO
import json

from matters.cli.main import build_parser, run


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

    def source_groups(self, **kwargs):
        return self._record(
            "source_groups",
            kwargs,
            {"items": (), "offset": kwargs["offset"], "limit": kwargs["limit"]},
        )

    def source_group_detail(self, **kwargs):
        return self._record(
            "source_group_detail",
            kwargs,
            {"summary": {"group_id": kwargs["group_id"]}, "members": ()},
        )

    def rebase_source_group_index(self, **kwargs):
        return self._record(
            "rebase_source_group_index",
            kwargs,
            {
                "status": "partial",
                "scanned_occurrence_count": kwargs["limit"],
                "has_more": True,
            },
        )

    def matter_situation_graph(self, **kwargs):
        return self._record(
            "matter_situation_graph",
            kwargs,
            {"matter_id": kwargs["matter_id"], "nodes": ()},
        )

    def matter_node_quick_view(self, **kwargs):
        return self._record(
            "matter_node_quick_view",
            kwargs,
            {"node_id": kwargs["node_id"], "sources": ()},
        )

    def matter_world_model(self, **kwargs):
        return self._record(
            "matter_world_model",
            kwargs,
            {"matter_id": kwargs["matter_id"], "items": ()},
        )

    def object_coverage_page(self, **kwargs):
        return self._record(
            "object_coverage_page",
            kwargs,
            ((), 0),
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
                        "first_gap_stage": "ui_reachable",
                    },
                ),
                "offset": kwargs["offset"],
                "limit": kwargs["limit"],
                "total_matching": 1,
            },
        )

    def rebase_coverage_stage_schema(
        self,
        *,
        after_object_id: str,
        limit: int,
    ):
        return self._record(
            "rebase_coverage_stage_schema",
            {
                "after_object_id": after_object_id,
                "limit": limit,
            },
            {
                "scanned_object_count": 50,
                "migrated_object_count": 50,
                "next_cursor": "filesystem:50",
                "has_more": True,
                "status": "partial",
            },
        )

    def rebase_existing_matter_coverage(
        self,
        *,
        after_matter_id: str,
        limit: int,
    ):
        return self._record(
            "rebase_existing_matter_coverage",
            {
                "after_matter_id": after_matter_id,
                "limit": limit,
            },
            {
                "scanned_matter_count": 50,
                "registered_matter_count": 50,
                "next_cursor": "matter:50",
                "has_more": True,
                "status": "partial",
            },
        )

    def reconcile_matter_source_revisions(
        self,
        *,
        after_matter_id: str,
        limit: int,
    ):
        return self._record(
            "reconcile_matter_source_revisions",
            {
                "after_matter_id": after_matter_id,
                "limit": limit,
            },
            {
                "scanned_matter_count": limit,
                "analysis_required_count": 2,
                "next_cursor": "matter:100",
                "has_more": True,
                "status": "partial",
            },
        )

    def reconcile_gmail_current_scope(
        self,
        *,
        after_object_id: str,
        limit: int,
    ):
        return self._record(
            "reconcile_gmail_current_scope",
            {
                "after_object_id": after_object_id,
                "limit": limit,
            },
            {
                "status": "partial",
                "inspected_count": limit,
                "switched_count": limit - 2,
                "pending_count": 1,
                "blocked_count": 1,
                "stale_count": 0,
                "next_after_object_id": "gmail:next",
            },
        )

    def reconcile_noncanonical_matter_hierarchy(
        self,
        *,
        after_matter_id: str,
        limit: int,
        dry_run: bool,
    ):
        return self._record(
            "reconcile_noncanonical_matter_hierarchy",
            {
                "after_matter_id": after_matter_id,
                "limit": limit,
                "dry_run": dry_run,
            },
            {
                "scanned_matter_count": 50,
                "retired_matter_count": 0 if dry_run else 50,
                "retired_pointer_count": 0 if dry_run else 150,
                "blocked_matter_ids": (),
                "next_cursor": "candidate:050",
                "has_more": True,
                "status": "partial",
                "dry_run": dry_run,
            },
        )

    def reconcile_noncanonical_matter_coverage(
        self,
        *,
        after_object_id: str,
        limit: int,
        dry_run: bool,
    ):
        return self._record(
            "reconcile_noncanonical_matter_coverage",
            {
                "after_object_id": after_object_id,
                "limit": limit,
                "dry_run": dry_run,
            },
            {
                "scanned_object_count": 2,
                "retired_object_count": 0,
                "dry_run": dry_run,
                "next_cursor": "candidate:1",
                "has_more": True,
                "status": "partial",
            },
        )

    def archive_object_coverage_history(
        self,
        *,
        after_object_id: str,
        after_revision: int,
        limit: int,
    ):
        return self._record(
            "archive_object_coverage_history",
            {
                "after_object_id": after_object_id,
                "after_revision": after_revision,
                "limit": limit,
            },
            {
                "scanned_count": 50,
                "archived_count": 50,
                "raw_bytes": 500_000,
                "compressed_bytes": 50_000,
                "freed_page_candidate_bytes": 450_000,
                "next_object_id": "occurrence:50",
                "next_revision": 7,
                "has_more": True,
                "status": "partial",
            },
        )

    def rebase_legacy_evidence_pointers(
        self,
        *,
        after_object_id: str,
        limit: int,
    ):
        return self._record(
            "rebase_legacy_evidence_pointers",
            {
                "after_object_id": after_object_id,
                "limit": limit,
            },
            {
                "scanned_object_count": 20,
                "migrated_object_count": 20,
                "next_cursor": "occurrence:20",
                "has_more": True,
                "status": "partial",
            },
        )

    def reconcile_coverage_inventory_orphans(self, *, limit: int):
        return self._record(
            "reconcile_coverage_inventory_orphans",
            {"limit": limit},
            {
                "scanned_object_count": 4,
                "retired_object_count": 4,
                "has_more": False,
                "status": "current",
            },
        )

    def rebase_current_inventory_policy(
        self,
        *,
        provider: str,
        offset: int,
        limit: int,
    ):
        return self._record(
            "rebase_current_inventory_policy",
            {
                "provider": provider,
                "offset": offset,
                "limit": limit,
            },
            {
                "provider": provider,
                "scanned_scope_count": 2,
                "rebased_scope_count": 2,
                "already_current_scope_count": 0,
                "missing_snapshot_scope_count": 0,
                "next_offset": 0,
                "has_more": False,
                "status": "current",
            },
        )

    def reconcile_current_matter_activity(self):
        return self._record(
            "reconcile_current_matter_activity",
            {},
            {
                "eligible_matter_count": 44,
                "current_activity_count": 44,
                "missing_activity_count": 0,
                "migrated_activity_count": 34,
                "checked_clue_count": 44,
                "repaired_clue_count": 2,
                "skipped_clue_count": 42,
                "status": "current",
            },
        )

    def matter_hierarchy_coverage_page(self, **kwargs):
        return self._record(
            "matter_hierarchy_coverage_page",
            kwargs,
            {"items": (), "total_count": 0},
        )

    def pending_analysis_packages(
        self,
        *,
        offset: int,
        limit: int,
        package_id: str,
        source_revision: str,
        task_kind: str,
    ):
        return self._record(
            "pending_analysis_packages",
            {
                "offset": offset,
                "limit": limit,
                "package_id": package_id,
                "source_revision": source_revision,
                "task_kind": task_kind,
            },
            {"items": [], "offset": offset, "limit": limit},
        )

    def rebase_analysis_contracts(
        self,
        *,
        after_package_id: str,
        limit: int,
    ):
        return self._record(
            "rebase_analysis_contracts",
            {
                "after_package_id": after_package_id,
                "limit": limit,
            },
            {
                "scanned_package_count": 7,
                "rebased_package_count": 2,
                "next_cursor": "work:7",
                "has_more": True,
                "rescan_required": True,
            },
        )

    def queue_research_operation(
        self,
        matter_id: str,
        question: str = "",
    ):
        return self._record(
            "queue_research_operation",
            {"matter_id": matter_id, "question": question},
            {
                "status": "queued",
                "provider_gate": {
                    "provider_id": "researchguard",
                    "status": "pending",
                },
                "package": {
                    "operation_type": "research_operation",
                    "matter_id": matter_id,
                    "untrusted_evidence": {
                        "research_question": question,
                    },
                },
            },
        )

    def import_autonomous_result(self, **kwargs):
        return self._record(
            "import_autonomous_result",
            kwargs,
            {"status": "passed", "auto_apply_status": "auto_applied"},
        )

    def pending_generated_heroes(self, *, offset: int, limit: int):
        return self._record(
            "pending_generated_heroes",
            {"offset": offset, "limit": limit},
            {
                "items": (),
                "offset": offset,
                "limit": limit,
                "total_count": 0,
            },
        )

    def register_generated_hero(self, **kwargs):
        return self._record(
            "register_generated_hero",
            kwargs,
            {"matter_id": kwargs["matter_id"], "status": "generated_current"},
        )

    def refresh_generated_hero(self, *, matter_id: str):
        return self._record(
            "refresh_generated_hero",
            {"matter_id": matter_id},
            {
                "matter_id": matter_id,
                "status": "generation_pending_placeholder",
            },
        )

    def record_generated_hero_failure(
        self,
        *,
        matter_id: str,
        failure_kind: str,
    ):
        return self._record(
            "record_generated_hero_failure",
            {"matter_id": matter_id, "failure_kind": failure_kind},
            {
                "matter_id": matter_id,
                "status": "generation_pending_placeholder",
            },
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

    def activate_codex_execution_profile(self, entries):
        return self._record(
            "activate_codex_execution_profile",
            {"entries": entries},
            {"status": "current", "profile_revision": 1},
        )

    def codex_execution_profile_receipt(self):
        return self._record(
            "codex_execution_profile_receipt",
            {},
            {
                "status": "current",
                "profile_identity": "execution-profile:test",
                "profile_revision": 1,
            },
        )

    def process_registered_filesystem_batch(self, *, limit: int):
        return self._record(
            "process_registered_filesystem_batch",
            {"limit": limit},
            {
                "status": "processed",
                "selected_count": limit,
                "remaining_count": 3,
            },
        )

    def import_gmail_body_continuation(
        self,
        *,
        manifest_bytes: bytes,
        connector_result,
    ):
        return self._record(
            "import_gmail_body_continuation",
            {
                "manifest_bytes": manifest_bytes,
                "connector_result": connector_result,
            },
            {
                "status": "current",
                "batch_number": connector_result["batch_number"],
                "expected_count": len(connector_result["messages"]),
            },
        )

    def submit_matter_correction(self, **kwargs):
        return self._record(
            "submit_matter_correction",
            kwargs,
            {"status": "auto_applied"},
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
                    "sort": "activity",
                    "start_year": "all",
                    "people": (),
                    "relationships": (),
                    "topic_types": (),
                    "source_types": (),
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
            "all",
            "--sort",
            "activity",
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


def test_entrypoint_cli_advances_one_bounded_coverage_schema_rebase_page():
    service = FakeService()

    rebased = invoke(
        [
            "coverage-rebase",
            "--after-object-id",
            "filesystem:prior",
            "--limit",
            "50",
        ],
        service,
    )

    assert rebased[0] == 0
    assert rebased[2] == ""
    assert json.loads(rebased[1])["result"]["status"] == "partial"
    assert service.calls == [
        (
            "rebase_coverage_stage_schema",
            {
                "after_object_id": "filesystem:prior",
                "limit": 50,
            },
        )
    ]


def test_entrypoint_cli_advances_one_bounded_existing_matter_coverage_page():
    service = FakeService()

    rebased = invoke(
        [
            "matter-coverage-rebase",
            "--after-matter-id",
            "matter:prior",
            "--limit",
            "50",
        ],
        service,
    )

    assert rebased[0] == 0
    assert rebased[2] == ""
    assert json.loads(rebased[1])["result"] == {
        "scanned_matter_count": 50,
        "registered_matter_count": 50,
        "next_cursor": "matter:50",
        "has_more": True,
        "status": "partial",
    }
    assert service.calls == [
        (
            "rebase_existing_matter_coverage",
            {
                "after_matter_id": "matter:prior",
                "limit": 50,
            },
        )
    ]


def test_entrypoint_cli_reconciles_one_bounded_matter_source_page():
    service = FakeService()

    reconciled = invoke(
        [
            "matter-source-reconcile",
            "--after-matter-id",
            "matter:prior",
            "--limit",
            "50",
        ],
        service,
    )

    assert reconciled[0] == 0
    assert json.loads(reconciled[1])["result"]["status"] == "partial"
    assert service.calls == [
        (
            "reconcile_matter_source_revisions",
            {
                "after_matter_id": "matter:prior",
                "limit": 50,
            },
        )
    ]


def test_entrypoint_cli_reconciles_one_bounded_gmail_current_scope_page():
    service = FakeService()

    reconciled = invoke(
        [
            "gmail-current-scope-reconcile",
            "--after-object-id",
            "gmail:prior",
            "--limit",
            "50",
        ],
        service,
    )

    assert reconciled[0] == 0
    result = json.loads(reconciled[1])["result"]
    assert result["status"] == "partial"
    assert result["switched_count"] == 48
    assert service.calls == [
        (
            "reconcile_gmail_current_scope",
            {
                "after_object_id": "gmail:prior",
                "limit": 50,
            },
        )
    ]


def test_entrypoint_cli_rebases_one_bounded_inventory_policy_page():
    service = FakeService()

    rebased = invoke(
        [
            "inventory-policy-rebase",
            "--provider",
            "gmail",
            "--offset",
            "4",
            "--limit",
            "2",
        ],
        service,
    )

    assert rebased[0] == 0
    assert json.loads(rebased[1])["result"]["status"] == "current"
    assert service.calls == [
        (
            "rebase_current_inventory_policy",
            {
                "provider": "gmail",
                "offset": 4,
                "limit": 2,
            },
        )
    ]


def test_entrypoint_cli_reconciles_current_matter_activity():
    service = FakeService()

    reconciled = invoke(["matter-activity-reconcile"], service)

    assert reconciled[0] == 0
    result = json.loads(reconciled[1])["result"]
    assert result["status"] == "current"
    assert result["missing_activity_count"] == 0
    assert service.calls == [
        ("reconcile_current_matter_activity", {})
    ]


def test_entrypoint_cli_previews_noncanonical_matter_coverage_reconciliation():
    service = FakeService()

    reconciled = invoke(
        [
            "noncanonical-matter-coverage-reconcile",
            "--after-object-id",
            "candidate:prior",
            "--limit",
            "50",
            "--dry-run",
        ],
        service,
    )

    assert reconciled[0] == 0
    assert json.loads(reconciled[1])["result"]["dry_run"] is True
    assert service.calls == [
        (
            "reconcile_noncanonical_matter_coverage",
            {
                "after_object_id": "candidate:prior",
                "limit": 50,
                "dry_run": True,
            },
        )
    ]


def test_entrypoint_cli_previews_noncanonical_matter_hierarchy_reconciliation():
    service = FakeService()

    reconciled = invoke(
        [
            "noncanonical-matter-hierarchy-reconcile",
            "--after-matter-id",
            "candidate:prior",
            "--limit",
            "50",
            "--dry-run",
        ],
        service,
    )

    assert reconciled[0] == 0
    assert json.loads(reconciled[1])["result"]["dry_run"] is True
    assert service.calls == [
        (
            "reconcile_noncanonical_matter_hierarchy",
            {
                "after_matter_id": "candidate:prior",
                "limit": 50,
                "dry_run": True,
            },
        )
    ]


def test_entrypoint_cli_describes_matter_coverage_rebase_as_bounded():
    parser = build_parser()

    command_group = parser._subparsers._group_actions[0]
    assert (
        "Register one bounded page of existing Matters in coverage."
        in command_group.choices["matter-coverage-rebase"].format_help()
    )
    parsed = parser.parse_args(["matter-coverage-rebase"])
    assert parsed.after_matter_id == ""
    assert parsed.limit == 200


def test_entrypoint_cli_advances_bounded_coverage_history_archive():
    service = FakeService()

    archived = invoke(
        [
            "coverage-history-archive",
            "--after-object-id",
            "occurrence:prior",
            "--after-revision",
            "4",
            "--limit",
            "50",
        ],
        service,
    )

    assert archived[0] == 0
    assert json.loads(archived[1])["result"]["status"] == "partial"
    assert service.calls == [
        (
            "archive_object_coverage_history",
            {
                "after_object_id": "occurrence:prior",
                "after_revision": 4,
                "limit": 50,
            },
        )
    ]


def test_entrypoint_cli_advances_bounded_evidence_pointer_rebase():
    service = FakeService()

    rebased = invoke(
        [
            "evidence-pointer-rebase",
            "--after-object-id",
            "occurrence:prior",
            "--limit",
            "20",
        ],
        service,
    )

    assert rebased[0] == 0
    assert json.loads(rebased[1])["result"]["status"] == "partial"
    assert service.calls == [
        (
            "rebase_legacy_evidence_pointers",
            {
                "after_object_id": "occurrence:prior",
                "limit": 20,
            },
        )
    ]


def test_entrypoint_cli_rebuilds_one_bounded_source_group_page():
    service = FakeService()

    rebased = invoke(
        [
            "source-group-rebase",
            "--after-object-id",
            "occurrence:prior",
            "--after-scope-id",
            "scope:prior",
            "--limit",
            "250",
        ],
        service,
    )

    assert rebased[0] == 0
    assert json.loads(rebased[1])["result"]["status"] == "partial"
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


def test_entrypoint_cli_reconciles_one_bounded_coverage_orphan_page():
    service = FakeService()

    reconciled = invoke(
        ["coverage-reconcile", "--limit", "50"],
        service,
    )

    assert reconciled[0] == 0
    assert reconciled[2] == ""
    assert json.loads(reconciled[1])["result"]["status"] == "current"
    assert service.calls == [
        (
            "reconcile_coverage_inventory_orphans",
            {"limit": 50},
        )
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
                "provider_id": "codex-hosted-capability-router",
                "provider_version": "capability-contract-v1",
                "result": {"status": "passed", "findings": []},
            },
        ),
        ("run_maintenance_cycle", {"limit": 7}),
    ]


def test_entrypoint_cli_runs_model_independent_planned_maintenance(tmp_path):
    request_file = tmp_path / "maintenance-request.json"
    request_file.write_text(
        json.dumps(
            {
                "run_id": "maintenance:cli",
                "authorization_identity": "authorization:current",
                "inventory_identity": "inventory:current",
                "coverage_identity": "coverage:current",
                "changed_object_ids": ["occurrence:2", "occurrence:1"],
                "resource_budget": {
                    "max_tasks": 8,
                    "max_retries_per_task": 1,
                    "max_concurrency": 2,
                },
            }
        ),
        encoding="utf-8",
    )
    service = FakeService()

    result = invoke(
        [
            "maintenance-orchestration",
            "--request-file",
            str(request_file),
        ],
        service,
    )

    assert result[0] == 0
    assert result[2] == ""
    assert json.loads(result[1])["result"] == {
        "status": "no_change",
        "run_id": "maintenance:cli",
    }
    request = service.calls[0][1]["request"]
    assert request.changed_object_ids == ("occurrence:1", "occurrence:2")
    assert request.resource_budget == {
        "max_tasks": 8,
        "max_retries_per_task": 1,
        "max_concurrency": 2,
    }


def test_entrypoint_cli_queues_research_request_without_running_it(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("MATTERS_HOME", str(tmp_path / "private"))
    service = FakeService()

    queued = invoke(
        [
            "research-request",
            "matter:1",
            "--question",
            "What public context should be added?",
        ],
        service,
    )

    assert queued[0] == 0
    assert queued[2] == ""
    result = json.loads(queued[1])["result"]
    assert result["status"] == "queued"
    assert result["provider_gate"] == {
        "provider_id": "researchguard",
        "status": "pending",
    }
    assert result["package"]["operation_type"] == "research_operation"
    assert service.calls == [
        (
            "queue_research_operation",
            {
                "matter_id": "matter:1",
                "question": "What public context should be added?",
            },
        )
    ]


def test_entrypoint_cli_advances_one_explicit_bounded_contract_rebase_page():
    service = FakeService()

    rebased = invoke(
        [
            "analysis-rebase",
            "--after-package-id",
            "work:prior",
            "--limit",
            "7",
        ],
        service,
    )

    assert rebased[0] == 0
    assert rebased[2] == ""
    result = json.loads(rebased[1])["result"]
    assert result["rebased_package_count"] == 2
    assert result["next_cursor"] == "work:7"
    assert result["has_more"] is True
    assert service.calls == [
        (
            "rebase_analysis_contracts",
            {
                "after_package_id": "work:prior",
                "limit": 7,
            },
        )
    ]


def test_entrypoint_cli_filters_analysis_packages_by_exact_private_selectors():
    service = FakeService()

    result = invoke(
        [
            "analysis-packages",
            "--package-id",
            "analysis-package:target",
            "--source-revision",
            "source:target:v2",
            "--task-kind",
            "source_revision_matter_refresh",
            "--limit",
            "1",
        ],
        service,
    )

    assert result[0] == 0
    assert result[2] == ""
    assert service.calls == [
        (
            "pending_analysis_packages",
            {
                "offset": 0,
                "limit": 1,
                "package_id": "analysis-package:target",
                "source_revision": "source:target:v2",
                "task_kind": "source_revision_matter_refresh",
            },
        )
    ]


def test_entrypoint_cli_exposes_bounded_codex_generated_hero_handoff(tmp_path):
    image_file = tmp_path / "hero.png"
    image_file.write_bytes(b"\x89PNG\r\n\x1a\nprivate-test-image")
    service = FakeService()

    pending = invoke(
        ["hero-packages", "--offset", "2", "--limit", "3"],
        service,
    )
    refreshed = invoke(["hero-refresh", "matter:1"], service)
    imported = invoke(
        [
            "hero-import",
            "matter:1",
            "sha256:brief",
            str(image_file),
            "--alt-en",
            "Conceptual project journey",
            "--alt-zh-cn",
            "项目旅程概念图",
        ],
        service,
    )
    failed = invoke(
        ["hero-fail", "matter:2", "generation_failed"],
        service,
    )

    assert pending[0] == refreshed[0] == imported[0] == failed[0] == 0
    assert json.loads(refreshed[1])["result"]["status"] == (
        "generation_pending_placeholder"
    )
    assert json.loads(imported[1])["result"]["status"] == "generated_current"
    assert service.calls == [
        ("pending_generated_heroes", {"offset": 2, "limit": 3}),
        ("refresh_generated_hero", {"matter_id": "matter:1"}),
        (
            "register_generated_hero",
            {
                "matter_id": "matter:1",
                "brief_fingerprint": "sha256:brief",
                "content": b"\x89PNG\r\n\x1a\nprivate-test-image",
                "media_type": "image/png",
                "localized_alt": {
                    "en": "Conceptual project journey",
                    "zh-CN": "项目旅程概念图",
                },
                "runner_contract_id": "codex-imagegen-tool:v1",
                "execution_identity": "codex-hosted-imagegen:current",
            },
        ),
        (
            "record_generated_hero_failure",
            {
                "matter_id": "matter:2",
                "failure_kind": "generation_failed",
            },
        ),
    ]

    rejected = invoke(["hero-packages", "--limit", "101"], service)
    assert rejected[0] == 4
    assert json.loads(rejected[2])["error"]["code"] == "invalid_request"


def test_entrypoint_cli_profiles_and_indexed_coverage_are_private_and_bounded(
    tmp_path,
):
    profile_file = tmp_path / "profile.json"
    profile_file.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "capability_role": "low_cost_annotator",
                        "execution_target": "economy-local",
                        "reasoning_level": "low",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    service = FakeService()

    activated = invoke(
        ["execution-profile-activate", str(profile_file)],
        service,
    )
    status = invoke(["execution-profile-status"], service)
    source_page = invoke(
        ["coverage-page", "--limit", "25", "--next-stage", "analysis"],
        service,
    )
    hierarchy_page = invoke(
        [
            "hierarchy-coverage",
            "--limit",
            "30",
            "--next-stage",
            "ui_reachable",
        ],
        service,
    )

    assert activated[0] == status[0] == source_page[0] == hierarchy_page[0] == 0
    assert service.calls == [
        (
            "activate_codex_execution_profile",
            {
                "entries": (
                    {
                        "capability_role": "low_cost_annotator",
                        "execution_target": "economy-local",
                        "reasoning_level": "low",
                    },
                )
            },
        ),
        ("codex_execution_profile_receipt", {}),
        (
            "object_coverage_page",
            {"offset": 0, "limit": 25, "next_stage": "analysis"},
        ),
        (
            "matter_hierarchy_coverage_page",
            {"offset": 0, "limit": 30, "next_stage": "ui_reachable"},
        ),
    ]


def test_entrypoint_cli_exposes_bounded_read_only_stage_audit():
    service = FakeService()

    result = invoke(
        [
            "coverage-audit",
            "--offset",
            "5",
            "--limit",
            "25",
            "--object-kind",
            "matter",
        ],
        service,
    )

    assert result[0] == 0
    assert result[2] == ""
    assert json.loads(result[1])["result"]["objects"][0][
        "first_gap_stage"
    ] == "ui_reachable"
    assert service.calls == [
        (
            "object_stage_audit",
            {"offset": 5, "limit": 25, "object_kind": "matter"},
        )
    ]

    rejected = invoke(["coverage-audit", "--limit", "201"], service)
    assert rejected[0] == 4
    assert json.loads(rejected[2])["error"]["code"] == "invalid_request"
    assert len(service.calls) == 1


def test_entrypoint_cli_forwards_indexed_surface_drilldown_filters():
    service = FakeService()

    result = invoke(
        [
            "coverage-audit",
            "--surface-id",
            "world_model",
            "--surface-status",
            "stale",
            "--owner-id",
            "C11_guard_prediction",
            "--failure-class",
            "world_model_expired",
            "--freshness",
            "stale",
            "--ui-ready",
            "false",
        ],
        service,
    )

    assert result[0] == 0
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


def test_entrypoint_cli_processes_only_a_bounded_registered_filesystem_page():
    service = FakeService()

    result = invoke(["extract-files", "--limit", "17"], service)

    assert result[0] == 0
    assert result[2] == ""
    assert json.loads(result[1])["result"] == {
        "remaining_count": 3,
        "selected_count": 17,
        "status": "processed",
    }
    assert service.calls == [
        ("process_registered_filesystem_batch", {"limit": 17})
    ]

    rejected = invoke(["extract-files", "--limit", "501"], service)
    assert rejected[0] == 4
    assert rejected[1] == ""
    assert json.loads(rejected[2])["error"]["code"] == "invalid_request"
    assert service.calls == [
        ("process_registered_filesystem_batch", {"limit": 17})
    ]


def test_entrypoint_cli_imports_one_exact_gmail_body_batch(
    tmp_path: Path,
):
    service = FakeService()
    manifest_bytes = b'[{"message_id":"m1"}]'
    manifest_file = tmp_path / "private-manifest.json"
    result_file = tmp_path / "connector-result.json"
    manifest_file.write_bytes(manifest_bytes)
    connector_result = {
        "artifact_type": "gmail_body_continuation",
        "manifest_sha256": "0" * 64,
        "batch_number": 7,
        "messages": [
            {
                "message_id": "m1",
                "body": "private",
                "content_status": "available",
            }
        ],
    }
    result_file.write_text(
        json.dumps(connector_result),
        encoding="utf-8",
    )

    result = invoke(
        [
            "gmail-body-import",
            str(manifest_file),
            str(result_file),
        ],
        service,
    )

    assert result[0] == 0
    assert result[2] == ""
    assert json.loads(result[1])["result"] == {
        "status": "current",
        "batch_number": 7,
        "expected_count": 1,
    }
    assert service.calls == [
        (
            "import_gmail_body_continuation",
            {
                "manifest_bytes": manifest_bytes,
                "connector_result": connector_result,
            },
        )
    ]


def test_entrypoint_cli_accepts_optional_post_result_correction_only():
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

    assert corrected[0] == 0
    assert json.loads(corrected[1])["result"]["status"] == "auto_applied"
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


def test_entrypoint_cli_exposes_groups_graph_quick_view_and_world_model():
    service = FakeService()

    groups = invoke(
        ["source-groups", "--query", "trip", "--offset", "5", "--limit", "25"],
        service,
    )
    detail = invoke(
        [
            "source-group",
            "source-group:trip",
            "--member-offset",
            "10",
            "--member-limit",
            "20",
        ],
        service,
    )
    graph = invoke(
        [
            "graph",
            "matter:1",
            "--locale",
            "zh-CN",
            "--continuation",
            "next:1",
            "--limit",
            "80",
        ],
        service,
    )
    quick_view = invoke(
        ["node-quick-view", "matter:1", "event:1", "--locale", "zh-CN"],
        service,
    )
    world_model = invoke(
        ["world-model", "matter:1", "--continuation", "next:2", "--limit", "30"],
        service,
    )

    assert all(result[0] == 0 for result in (
        groups,
        detail,
        graph,
        quick_view,
        world_model,
    ))
    assert service.calls == [
        (
            "source_groups",
            {"offset": 5, "limit": 25, "query": "trip"},
        ),
        (
            "source_group_detail",
            {
                "group_id": "source-group:trip",
                "member_offset": 10,
                "member_limit": 20,
            },
        ),
        (
            "matter_situation_graph",
            {
                "matter_id": "matter:1",
                "locale": "zh-CN",
                "continuation": "next:1",
                "limit": 80,
            },
        ),
        (
            "matter_node_quick_view",
            {
                "matter_id": "matter:1",
                "node_id": "event:1",
                "locale": "zh-CN",
            },
        ),
        (
            "matter_world_model",
            {
                "matter_id": "matter:1",
                "locale": "en",
                "continuation": "next:2",
                "limit": 30,
            },
        ),
    ]


def test_entrypoint_cli_has_no_ordinary_cover_command():
    command_group = build_parser()._subparsers._group_actions[0]

    assert "cover" not in command_group.choices


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
