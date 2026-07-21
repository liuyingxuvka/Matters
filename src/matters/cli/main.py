"""Canonical local CLI for the autonomous Matter object browser."""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
from enum import Enum
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Protocol, Sequence, TextIO

from matters.application.maintenance_orchestration import MaintenanceRunRequest
from matters.presentation.localization import UnsupportedLocale


class EntrypointService(Protocol):
    def capabilities(self) -> object: ...
    def locale_registry(self) -> object: ...
    def object_browser_projection(self, **kwargs: object) -> object: ...
    def object_catalog_page(self, **kwargs: object) -> object: ...
    def matter_detail(self, *, matter_id: str, locale: str) -> object: ...
    def matter_evidence(self, *, matter_id: str, offset: int, limit: int) -> object: ...
    def source_groups(self, **kwargs: object) -> object: ...
    def source_group_detail(self, **kwargs: object) -> object: ...
    def rebase_source_group_index(self, **kwargs: object) -> object: ...
    def matter_situation_graph(self, **kwargs: object) -> object: ...
    def matter_node_quick_view(self, **kwargs: object) -> object: ...
    def matter_world_model(self, **kwargs: object) -> object: ...
    def object_coverage_summary(self) -> object: ...
    def object_stage_audit(self, **kwargs: object) -> object: ...
    def gmail_manifest_coverage_audit(self, **kwargs: object) -> object: ...
    def object_coverage_page(self, **kwargs: object) -> object: ...
    def matter_hierarchy_coverage_page(self, **kwargs: object) -> object: ...
    def rebase_coverage_stage_schema(
        self,
        *,
        after_object_id: str,
        limit: int,
    ) -> object: ...
    def rebase_existing_matter_coverage(
        self,
        *,
        after_matter_id: str,
        limit: int,
    ) -> object: ...
    def rebase_matter_semantic_depth(
        self,
        *,
        after_matter_id: str,
        limit: int,
        max_descendants: int,
        max_sources: int,
    ) -> object: ...
    def reconcile_matter_source_revisions(
        self,
        *,
        after_matter_id: str,
        limit: int,
    ) -> object: ...
    def source_revision_analysis_plan(
        self,
        *,
        matter_id: str,
        after_matter_id: str,
        limit: int,
        queue: bool,
    ) -> object: ...
    def matter_semantic_analysis_plan(
        self,
        *,
        matter_id: str,
        after_matter_id: str,
        limit: int,
        queue: bool,
    ) -> object: ...
    def reconcile_gmail_current_scope(
        self,
        *,
        after_object_id: str,
        limit: int,
    ) -> object: ...
    def rebase_gmail_content_receipts(
        self,
        *,
        after_object_id: str,
        limit: int,
    ) -> object: ...
    def reconcile_noncanonical_matter_coverage(
        self,
        *,
        after_object_id: str,
        limit: int,
        dry_run: bool,
    ) -> object: ...
    def reconcile_noncanonical_matter_hierarchy(
        self,
        *,
        after_matter_id: str,
        limit: int,
        dry_run: bool,
    ) -> object: ...
    def reconcile_admitted_matter_presentation(
        self,
        *,
        after_matter_id: str,
        limit: int,
    ) -> object: ...
    def archive_object_coverage_history(
        self,
        *,
        after_object_id: str,
        after_revision: int,
        limit: int,
    ) -> object: ...
    def rebase_legacy_evidence_pointers(
        self,
        *,
        after_object_id: str,
        limit: int,
    ) -> object: ...
    def rebase_content_selection(
        self,
        *,
        after_object_id: str,
        limit: int,
    ) -> object: ...
    def reconcile_coverage_inventory_orphans(
        self,
        *,
        limit: int,
    ) -> object: ...
    def rebase_current_inventory_policy(
        self,
        *,
        provider: str,
        offset: int,
        limit: int,
    ) -> object: ...
    def content_selection_page(self, *, offset: int, limit: int) -> object: ...
    def pending_analysis_packages(
        self,
        *,
        offset: int,
        limit: int,
        package_id: str,
        source_revision: str,
        task_kind: str,
    ) -> object: ...
    def rebase_analysis_contracts(
        self,
        *,
        after_package_id: str,
        limit: int,
    ) -> object: ...
    def reconcile_annotation_semantic_followups(
        self,
        *,
        after_package_id: str,
        limit: int,
    ) -> object: ...
    def rebase_temporal_event_logical_identity(
        self,
        *,
        offset: int,
        limit: int,
    ) -> object: ...
    def reconcile_current_matter_activity(self) -> object: ...
    def queue_research_operation(
        self,
        matter_id: str,
        question: str = "",
    ) -> object: ...
    def import_autonomous_result(self, **kwargs: object) -> object: ...
    def pending_generated_heroes(self, *, offset: int, limit: int) -> object: ...
    def register_generated_hero(self, **kwargs: object) -> object: ...
    def refresh_generated_hero(self, *, matter_id: str) -> object: ...
    def source_in_place_migration_plan(self) -> object: ...
    def create_source_in_place_backup(self, *, backup_root: str) -> object: ...
    def verify_source_in_place_backup(self, *, backup_root: str) -> object: ...
    def apply_source_in_place_migration_batch(
        self,
        *,
        backup_root: str,
        limit: int,
    ) -> object: ...
    def clean_source_in_place_storage(
        self,
        *,
        backup_root: str,
        blob_limit: int,
    ) -> object: ...
    def verify_source_in_place_migration(
        self,
        *,
        backup_root: str,
    ) -> object: ...
    def record_generated_hero_failure(
        self,
        *,
        matter_id: str,
        failure_kind: str,
    ) -> object: ...
    def activate_codex_execution_profile(self, entries: object) -> object: ...
    def codex_execution_profile_receipt(self) -> object: ...
    def run_maintenance_cycle(self, *, limit: int) -> object: ...
    def run_planned_maintenance(
        self,
        request: MaintenanceRunRequest,
    ) -> object: ...
    def submit_matter_correction(self, **kwargs: object) -> object: ...
    def version(self) -> object: ...
    def work_status(self) -> object: ...
    def pause_work(self, *, job_id: str) -> object: ...
    def resume_work(self, *, job_id: str) -> object: ...
    def scan_filesystem(self, *, root: str, content_limit: int | None) -> object: ...
    def process_registered_filesystem_batch(self, *, limit: int) -> object: ...
    def import_gmail_body_continuation(
        self,
        *,
        manifest_bytes: bytes,
        connector_result: Mapping[str, Any],
    ) -> object: ...
    def synchronize_managed_skill_projections(
        self,
        *,
        transaction_id_prefix: str,
    ) -> object: ...


class CapabilityUnavailable(RuntimeError):
    pass


def _jsonable(value: object) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Enum):
        return _jsonable(value.value)
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    raise TypeError(f"unsupported service result type: {type(value).__name__}")


def _invoke(service: object, method_name: str, /, **kwargs: object) -> Any:
    method = getattr(service, method_name, None)
    if not callable(method):
        raise CapabilityUnavailable(method_name)
    return _jsonable(method(**kwargs))


def _planned_maintenance_request(payload: object) -> MaintenanceRunRequest:
    if not isinstance(payload, Mapping):
        raise ValueError("maintenance_request_object_required")
    allowed = {
        "run_id",
        "authorization_identity",
        "inventory_identity",
        "coverage_identity",
        "changed_object_ids",
        "resource_budget",
    }
    extras = sorted(str(key) for key in payload if str(key) not in allowed)
    if extras:
        raise ValueError(
            "maintenance_request_unknown_fields:" + ",".join(extras)
        )
    changed = payload.get("changed_object_ids", ())
    budget = payload.get("resource_budget")
    if not isinstance(changed, list) or (
        budget is not None and not isinstance(budget, Mapping)
    ):
        raise ValueError("maintenance_request_schema_invalid")
    return MaintenanceRunRequest.create(
        run_id=str(payload.get("run_id", "")),
        authorization_identity=str(
            payload.get("authorization_identity", "")
        ),
        inventory_identity=str(payload.get("inventory_identity", "")),
        coverage_identity=str(payload.get("coverage_identity", "")),
        changed_object_ids=tuple(str(item) for item in changed),
        resource_budget=(
            {str(key): int(value) for key, value in budget.items()}
            if isinstance(budget, Mapping)
            else None
        ),
    )


def _catalog_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--locale", default="en", choices=("en", "zh-CN"))
    parser.add_argument("--query", default="")
    parser.add_argument(
        "--status",
        default="all",
        choices=("all", "planned", "in_progress", "completed"),
    )
    parser.add_argument(
        "--time",
        default="all",
        choices=("all",),
    )
    parser.add_argument("--sort", default="activity", choices=("activity",))
    parser.add_argument("--start-year", default="all")
    parser.add_argument("--person", action="append", default=[])
    parser.add_argument("--relationship", action="append", default=[])
    parser.add_argument("--topic-type", action="append", default=[])
    parser.add_argument("--source-type", action="append", default=[])
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=60)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="matters",
        description="Operate the local autonomous Matters object browser.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("capabilities")
    commands.add_parser("locales")
    commands.add_parser("coverage")
    coverage_audit = commands.add_parser("coverage-audit")
    coverage_audit.add_argument("--offset", type=int, default=0)
    coverage_audit.add_argument("--limit", type=int, default=100)
    coverage_audit.add_argument(
        "--object-kind",
        default="",
        choices=("", "occurrence", "matter"),
    )
    coverage_audit.add_argument("--surface-id", default="")
    coverage_audit.add_argument("--surface-status", default="")
    coverage_audit.add_argument("--owner-id", default="")
    coverage_audit.add_argument("--failure-class", default="")
    coverage_audit.add_argument("--freshness", default="")
    coverage_audit.add_argument(
        "--ui-ready",
        default="",
        choices=("", "true", "false"),
    )
    gmail_manifest_audit = commands.add_parser(
        "gmail-manifest-coverage-audit",
        help=(
            "Read one verified Gmail page set through private coverage indexes "
            "without provider access or state writes."
        ),
    )
    gmail_manifest_audit.add_argument("--receipt", type=Path)
    gmail_manifest_audit.add_argument(
        "--page",
        action="append",
        type=Path,
        default=[],
    )
    coverage_page = commands.add_parser("coverage-page")
    coverage_page.add_argument("--offset", type=int, default=0)
    coverage_page.add_argument("--limit", type=int, default=100)
    coverage_page.add_argument("--next-stage", default="")
    coverage_rebase = commands.add_parser("coverage-rebase")
    coverage_rebase.add_argument("--after-object-id", default="")
    coverage_rebase.add_argument("--limit", type=int, default=200)
    matter_coverage_rebase = commands.add_parser(
        "matter-coverage-rebase",
        help="Register one bounded page of existing Matters in coverage.",
        description="Register one bounded page of existing Matters in coverage.",
    )
    matter_coverage_rebase.add_argument("--after-matter-id", default="")
    matter_coverage_rebase.add_argument("--limit", type=int, default=200)
    matter_depth_rebase = commands.add_parser(
        "matter-depth-rebase",
        help="Assess one bounded page of canonical Matter semantic depth.",
        description=(
            "Assess one bounded page of canonical Matter semantic depth."
        ),
    )
    matter_depth_rebase.add_argument("--after-matter-id", default="")
    matter_depth_rebase.add_argument("--limit", type=int, default=100)
    matter_depth_rebase.add_argument(
        "--max-descendants",
        type=int,
        default=1000,
    )
    matter_depth_rebase.add_argument(
        "--max-sources",
        type=int,
        default=10000,
    )
    matter_source_reconcile = commands.add_parser(
        "matter-source-reconcile",
        help=(
            "Reconcile one bounded page of admitted source revisions without "
            "bypassing current evidence analysis."
        ),
        description=(
            "Reconcile one bounded page of admitted source revisions without "
            "bypassing current evidence analysis."
        ),
    )
    matter_source_reconcile.add_argument("--after-matter-id", default="")
    matter_source_reconcile.add_argument("--limit", type=int, default=100)
    source_revision_analysis = commands.add_parser(
        "source-revision-analysis-plan",
        help=(
            "Plan or queue exact target-bound semantic refreshes for "
            "registry-current Matter source revisions."
        ),
        description=(
            "Plan or queue exact target-bound semantic refreshes for "
            "registry-current Matter source revisions."
        ),
    )
    source_revision_analysis.add_argument("--matter-id", default="")
    source_revision_analysis.add_argument("--after-matter-id", default="")
    source_revision_analysis.add_argument("--limit", type=int, default=100)
    source_revision_analysis.add_argument("--queue", action="store_true")
    matter_semantic_analysis = commands.add_parser(
        "matter-semantic-analysis-plan",
        help=(
            "Plan or queue one exact cross-source semantic refresh for each "
            "admitted Matter."
        ),
        description=(
            "Plan or queue one exact cross-source semantic refresh for each "
            "admitted Matter."
        ),
    )
    matter_semantic_analysis.add_argument("--matter-id", default="")
    matter_semantic_analysis.add_argument("--after-matter-id", default="")
    matter_semantic_analysis.add_argument("--limit", type=int, default=100)
    matter_semantic_analysis.add_argument("--queue", action="store_true")
    gmail_scope_reconcile = commands.add_parser(
        "gmail-current-scope-reconcile",
        help=(
            "Rebind one bounded Gmail metadata-only coverage page to its "
            "single newer tracked scope without provider reads."
        ),
        description=(
            "Rebind one bounded Gmail metadata-only coverage page to its "
            "single newer tracked scope without provider reads."
        ),
    )
    gmail_scope_reconcile.add_argument("--after-object-id", default="")
    gmail_scope_reconcile.add_argument("--limit", type=int, default=200)
    gmail_content_receipt_rebase = commands.add_parser(
        "gmail-content-receipt-rebase",
        help=(
            "Backfill exact Gmail body receipts from registry-current digest, "
            "length, and evidence without copying or reading body content."
        ),
        description=(
            "Backfill exact Gmail body receipts from registry-current digest, "
            "length, and evidence without copying or reading body content."
        ),
    )
    gmail_content_receipt_rebase.add_argument(
        "--after-object-id",
        default="",
    )
    gmail_content_receipt_rebase.add_argument("--limit", type=int, default=100)
    noncanonical_coverage = commands.add_parser(
        "noncanonical-matter-coverage-reconcile",
        help="Retire one bounded page of noncanonical Matter coverage.",
        description="Retire one bounded page of noncanonical Matter coverage.",
    )
    noncanonical_coverage.add_argument("--after-object-id", default="")
    noncanonical_coverage.add_argument("--limit", type=int, default=200)
    noncanonical_coverage.add_argument("--dry-run", action="store_true")
    noncanonical_hierarchy = commands.add_parser(
        "noncanonical-matter-hierarchy-reconcile",
        help=(
            "Retire one bounded page of noncanonical Matter hierarchy "
            "pointers while preserving history."
        ),
        description=(
            "Retire one bounded page of noncanonical Matter hierarchy "
            "pointers while preserving history."
        ),
    )
    noncanonical_hierarchy.add_argument("--after-matter-id", default="")
    noncanonical_hierarchy.add_argument("--limit", type=int, default=200)
    noncanonical_hierarchy.add_argument("--dry-run", action="store_true")
    presentation_reconcile = commands.add_parser(
        "matter-presentation-reconcile",
        help=(
            "Advance one bounded exact-admission page through bilingual "
            "projection and generated-hero preparation."
        ),
        description=(
            "Advance one bounded exact-admission page through bilingual "
            "projection and generated-hero preparation."
        ),
    )
    presentation_reconcile.add_argument("--after-matter-id", default="")
    presentation_reconcile.add_argument("--limit", type=int, default=50)
    coverage_history_archive = commands.add_parser(
        "coverage-history-archive",
        help="Compress one bounded page of non-current coverage history.",
        description="Compress one bounded page of non-current coverage history.",
    )
    coverage_history_archive.add_argument("--after-object-id", default="")
    coverage_history_archive.add_argument("--after-revision", type=int, default=0)
    coverage_history_archive.add_argument("--limit", type=int, default=200)
    evidence_pointer_rebase = commands.add_parser(
        "evidence-pointer-rebase",
        help="Compact one bounded page of current legacy evidence pointers.",
        description="Compact one bounded page of current legacy evidence pointers.",
    )
    evidence_pointer_rebase.add_argument("--after-object-id", default="")
    evidence_pointer_rebase.add_argument("--limit", type=int, default=20)
    coverage_reconcile = commands.add_parser("coverage-reconcile")
    coverage_reconcile.add_argument("--limit", type=int, default=200)
    inventory_policy_rebase = commands.add_parser(
        "inventory-policy-rebase",
        help=(
            "Reclassify one bounded current inventory-scope page under the "
            "current tracking policy without provider reads."
        ),
        description=(
            "Reclassify one bounded current inventory-scope page under the "
            "current tracking policy without provider reads."
        ),
    )
    inventory_policy_rebase.add_argument("--provider", required=True)
    inventory_policy_rebase.add_argument("--offset", type=int, default=0)
    inventory_policy_rebase.add_argument("--limit", type=int, default=20)
    selection_page = commands.add_parser("selection-page")
    selection_page.add_argument("--offset", type=int, default=0)
    selection_page.add_argument("--limit", type=int, default=100)
    selection_rebase = commands.add_parser("selection-rebase")
    selection_rebase.add_argument("--after-object-id", default="")
    selection_rebase.add_argument("--limit", type=int, default=200)
    hierarchy_coverage = commands.add_parser("hierarchy-coverage")
    hierarchy_coverage.add_argument("--offset", type=int, default=0)
    hierarchy_coverage.add_argument("--limit", type=int, default=100)
    hierarchy_coverage.add_argument("--next-stage", default="")
    commands.add_parser("version")
    commands.add_parser("status")
    browser = commands.add_parser("browser")
    _catalog_arguments(browser)
    catalog = commands.add_parser("catalog")
    _catalog_arguments(catalog)
    detail = commands.add_parser("detail")
    detail.add_argument("matter_id")
    detail.add_argument("--locale", default="en", choices=("en", "zh-CN"))
    evidence = commands.add_parser("evidence")
    evidence.add_argument("matter_id")
    evidence.add_argument("--offset", type=int, default=0)
    evidence.add_argument("--limit", type=int, default=50)
    source_groups = commands.add_parser("source-groups")
    source_groups.add_argument("--query", default="")
    source_groups.add_argument("--offset", type=int, default=0)
    source_groups.add_argument("--limit", type=int, default=50)
    source_group = commands.add_parser("source-group")
    source_group.add_argument("group_id")
    source_group.add_argument("--member-offset", type=int, default=0)
    source_group.add_argument("--member-limit", type=int, default=100)
    source_group_rebase = commands.add_parser("source-group-rebase")
    source_group_rebase.add_argument("--after-object-id", default="")
    source_group_rebase.add_argument("--after-scope-id", default="")
    source_group_rebase.add_argument("--limit", type=int, default=500)
    graph = commands.add_parser("graph")
    graph.add_argument("matter_id")
    graph.add_argument("--locale", default="en", choices=("en", "zh-CN"))
    graph.add_argument("--continuation", default="")
    graph.add_argument("--limit", type=int, default=120)
    node_quick_view = commands.add_parser("node-quick-view")
    node_quick_view.add_argument("matter_id")
    node_quick_view.add_argument("node_id")
    node_quick_view.add_argument(
        "--locale",
        default="en",
        choices=("en", "zh-CN"),
    )
    world_model = commands.add_parser("world-model")
    world_model.add_argument("matter_id")
    world_model.add_argument("--locale", default="en", choices=("en", "zh-CN"))
    world_model.add_argument("--continuation", default="")
    world_model.add_argument("--limit", type=int, default=50)
    packages = commands.add_parser("analysis-packages")
    packages.add_argument("--offset", type=int, default=0)
    packages.add_argument("--limit", type=int, default=20)
    packages.add_argument("--package-id", default="")
    packages.add_argument("--source-revision", default="")
    packages.add_argument("--task-kind", default="")
    rebase = commands.add_parser("analysis-rebase")
    rebase.add_argument("--after-package-id", default="")
    rebase.add_argument("--limit", type=int, default=200)
    followup_reconcile = commands.add_parser(
        "analysis-followup-reconcile",
        help=(
            "Retire duplicate unexecuted semantic follow-ups while preserving "
            "one exact A0 relation."
        ),
    )
    followup_reconcile.add_argument("--after-package-id", default="")
    followup_reconcile.add_argument("--limit", type=int, default=200)
    research_request = commands.add_parser("research-request")
    research_request.add_argument("matter_id")
    research_request.add_argument("--question", default="")
    imported = commands.add_parser("analysis-import")
    imported.add_argument("package_id")
    imported.add_argument("result_file", type=Path)
    imported.add_argument(
        "--provider-id",
        default="codex-hosted-capability-router",
    )
    imported.add_argument(
        "--provider-version",
        default="capability-contract-v1",
    )
    hero_packages = commands.add_parser("hero-packages")
    hero_packages.add_argument("--offset", type=int, default=0)
    hero_packages.add_argument("--limit", type=int, default=20)
    hero_refresh = commands.add_parser("hero-refresh")
    hero_refresh.add_argument("matter_id")
    hero_import = commands.add_parser("hero-import")
    hero_import.add_argument("matter_id")
    hero_import.add_argument("brief_fingerprint")
    hero_import.add_argument("image_file", type=Path)
    hero_import.add_argument(
        "--media-type",
        default="image/png",
        choices=("image/jpeg", "image/png", "image/webp"),
    )
    hero_import.add_argument("--alt-en", required=True)
    hero_import.add_argument("--alt-zh-cn", required=True)
    hero_import.add_argument(
        "--runner-contract-id",
        default="codex-imagegen-tool:v1",
    )
    hero_import.add_argument(
        "--execution-identity",
        default="codex-hosted-imagegen:current",
    )
    hero_failure = commands.add_parser("hero-fail")
    hero_failure.add_argument("matter_id")
    hero_failure.add_argument(
        "failure_kind",
        choices=(
            "capability_unavailable",
            "generation_failed",
            "runner_interrupted",
            "permission_denied",
            "policy_blocked",
            "retry_exhausted",
            "schema_invalid",
            "unsafe_output",
        ),
    )
    commands.add_parser("storage-migration-plan")
    storage_backup = commands.add_parser("storage-migration-backup")
    storage_backup.add_argument("backup_root")
    storage_backup_verify = commands.add_parser(
        "storage-migration-backup-verify"
    )
    storage_backup_verify.add_argument("backup_root")
    storage_apply = commands.add_parser("storage-migration-apply")
    storage_apply.add_argument("backup_root")
    storage_apply.add_argument("--limit", type=int, default=200)
    storage_clean = commands.add_parser("storage-migration-clean")
    storage_clean.add_argument("backup_root")
    storage_clean.add_argument("--blob-limit", type=int, default=2000)
    storage_verify = commands.add_parser("storage-migration-verify")
    storage_verify.add_argument("backup_root")
    commands.add_parser("execution-profile-status")
    profile_activate = commands.add_parser("execution-profile-activate")
    profile_activate.add_argument("profile_file", type=Path)
    maintenance = commands.add_parser("maintenance")
    maintenance.add_argument("--limit", type=int, default=20)
    maintenance_orchestration = commands.add_parser(
        "maintenance-orchestration"
    )
    maintenance_orchestration.add_argument(
        "--request-file",
        type=Path,
        required=True,
    )
    temporal_event_rebase = commands.add_parser("temporal-event-rebase")
    temporal_event_rebase.add_argument("--offset", type=int, default=0)
    temporal_event_rebase.add_argument("--limit", type=int, default=200)
    commands.add_parser(
        "matter-activity-reconcile",
        help=(
            "Fill missing canonical Matter activity and correct scheduled-time "
            "regressions from exact source observation time."
        ),
        description=(
            "Fill missing canonical Matter activity and correct scheduled-time "
            "regressions from exact source observation time."
        ),
    )
    correction = commands.add_parser("correct")
    correction.add_argument("matter_id")
    correction.add_argument("rationale")
    correction.add_argument("--field", default="")
    correction.add_argument("--value", default="")
    skill_sync = commands.add_parser("skill-sync")
    skill_sync.add_argument("transaction_id_prefix")
    pause = commands.add_parser("pause")
    pause.add_argument("job_id")
    resume = commands.add_parser("resume")
    resume.add_argument("job_id")
    for name, help_text, default_limit in (
        ("inventory", "Inventory one authorized root without content reads.", 0),
        ("canary", "Run a small private source-modeling pass.", 20),
        ("expand", "Expand bounded private source modeling.", 1000),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("root", type=Path)
        if default_limit:
            command.add_argument("--limit", type=int, default=default_limit)
    extract_files = commands.add_parser(
        "extract-files",
        help="Process one bounded page of already-inventoried filesystem content.",
    )
    extract_files.add_argument("--limit", type=int, default=100)
    gmail_bodies = commands.add_parser(
        "gmail-body-import",
        help="Import one exact private-manifest Gmail body continuation batch.",
    )
    gmail_bodies.add_argument("manifest_file", type=Path)
    gmail_bodies.add_argument("connector_result_file", type=Path)
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    return parser


def _catalog_kwargs(args: argparse.Namespace) -> dict[str, object]:
    if args.offset < 0 or args.limit < 1 or args.limit > 200:
        raise ValueError("invalid_page_bounds")
    return {
        "locale": args.locale,
        "query": args.query,
        "status": args.status,
        "time_filter": args.time,
        "sort": args.sort,
        "start_year": args.start_year,
        "people": tuple(args.person),
        "relationships": tuple(args.relationship),
        "topic_types": tuple(args.topic_type),
        "source_types": tuple(args.source_type),
        "offset": args.offset,
        "limit": args.limit,
    }


_OFFLINE_STORAGE_COMMANDS = frozenset(
    {
        "storage-migration-plan",
        "storage-migration-backup",
        "storage-migration-backup-verify",
        "storage-migration-apply",
        "storage-migration-clean",
        "storage-migration-verify",
    }
)


def _offline_storage_result(args: argparse.Namespace) -> object:
    """Run storage migration without constructing the normal runtime service."""

    from matters.provenance.source_in_place_migration import (
        apply_database_batch,
        clean_staging,
        create_verified_backup,
        reclaim_orphan_blobs,
        residual_report,
        verify_backup,
        verify_migration,
    )

    configured = str(os.environ.get("MATTERS_HOME", "")).strip()
    if not configured:
        raise RuntimeError("MATTERS_HOME is required for storage migration")
    private_root = Path(configured).expanduser().resolve()
    database_path = private_root / "matters.sqlite3"
    if not database_path.is_file():
        raise RuntimeError("MATTERS_HOME database is unavailable")
    command = str(args.command)
    if command == "storage-migration-plan":
        return residual_report(database_path)
    backup_root = Path(str(args.backup_root)).expanduser().resolve()
    if command == "storage-migration-backup":
        return create_verified_backup(
            private_root=private_root,
            backup_root=backup_root,
        )
    if command == "storage-migration-backup-verify":
        return verify_backup(backup_root)
    if command == "storage-migration-apply":
        return apply_database_batch(
            private_root=private_root,
            backup_root=backup_root,
            limit=int(args.limit),
        )
    if command == "storage-migration-clean":
        blobs = reclaim_orphan_blobs(
            database_path=database_path,
            blob_root=private_root / "blobs",
            limit=int(args.blob_limit),
        )
        staging = (
            clean_staging(
                private_root=private_root,
                backup_root=backup_root,
            )
            if not int(blobs["remaining_orphan_count"])
            else {
                "status": "pending_blob_cleanup",
                "deleted_file_count": 0,
                "deleted_bytes": 0,
            }
        )
        result = {
            "status": (
                "current"
                if staging["status"] == "staging_current"
                else "pending"
            ),
            "blobs": blobs,
            "staging": staging,
        }
        from matters.infrastructure.sqlite.store import SQLiteStore

        cleanup_store = SQLiteStore(
            private_root,
            Path(__file__).resolve().parents[3],
        )
        cleanup_identity = (
            f"storage-cleanup:{blobs['remaining_orphan_count']}:"
            f"{staging['status']}"
        )
        cleanup_store.record_coverage_surface_status(
            surface_id="raw_cleanup",
            status=(
                "current"
                if not int(blobs["remaining_orphan_count"])
                else "pending"
            ),
            input_fingerprint=cleanup_identity,
            failure_class=(
                ""
                if not int(blobs["remaining_orphan_count"])
                else "orphan_blob_cleanup_pending"
            ),
        )
        cleanup_store.record_coverage_surface_status(
            surface_id="staging_cleanup",
            status=(
                "current"
                if staging["status"] == "staging_current"
                else "pending"
            ),
            input_fingerprint=cleanup_identity,
            failure_class=(
                ""
                if staging["status"] == "staging_current"
                else "staging_cleanup_pending"
            ),
        )
        return result
    if command == "storage-migration-verify":
        return verify_migration(
            private_root=private_root,
            backup_root=backup_root,
        )
    raise ValueError("unsupported offline storage command")


def _run_offline_storage_command(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    try:
        result = _jsonable(_offline_storage_result(args))
    except (OSError, RuntimeError, ValueError) as exc:
        json.dump(
            {
                "ok": False,
                "error": {
                    "code": "storage_migration_blocked",
                    "operation": str(exc),
                },
            },
            stderr,
            ensure_ascii=False,
            sort_keys=True,
        )
        stderr.write("\n")
        return 5
    json.dump(
        {"ok": True, "result": result},
        stdout,
        ensure_ascii=False,
        sort_keys=True,
    )
    stdout.write("\n")
    return 0


def run(
    argv: Sequence[str] | None = None,
    *,
    service: EntrypointService,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    errors = stderr or sys.stderr
    args = build_parser().parse_args(argv)
    try:
        command = args.command
        if command in {"capabilities", "locales", "coverage", "version", "status"}:
            method = {
                "capabilities": "capabilities",
                "locales": "locale_registry",
                "coverage": "object_coverage_summary",
                "version": "version",
                "status": "work_status",
            }[command]
            result = _invoke(service, method)
        elif command in {"browser", "catalog"}:
            result = _invoke(
                service,
                (
                    "object_browser_projection"
                    if command == "browser"
                    else "object_catalog_page"
                ),
                **_catalog_kwargs(args),
            )
        elif command == "detail":
            result = _invoke(
                service,
                "matter_detail",
                matter_id=args.matter_id,
                locale=args.locale,
            )
        elif command == "evidence":
            result = _invoke(
                service,
                "matter_evidence",
                matter_id=args.matter_id,
                offset=args.offset,
                limit=args.limit,
            )
        elif command == "source-groups":
            result = _invoke(
                service,
                "source_groups",
                offset=args.offset,
                limit=args.limit,
                query=args.query,
            )
        elif command == "source-group":
            result = _invoke(
                service,
                "source_group_detail",
                group_id=args.group_id,
                member_offset=args.member_offset,
                member_limit=args.member_limit,
            )
        elif command == "graph":
            result = _invoke(
                service,
                "matter_situation_graph",
                matter_id=args.matter_id,
                locale=args.locale,
                continuation=args.continuation,
                limit=args.limit,
            )
        elif command == "node-quick-view":
            result = _invoke(
                service,
                "matter_node_quick_view",
                matter_id=args.matter_id,
                node_id=args.node_id,
                locale=args.locale,
            )
        elif command == "world-model":
            result = _invoke(
                service,
                "matter_world_model",
                matter_id=args.matter_id,
                locale=args.locale,
                continuation=args.continuation,
                limit=args.limit,
            )
        elif command == "coverage-page":
            result = _invoke(
                service,
                "object_coverage_page",
                offset=args.offset,
                limit=args.limit,
                next_stage=args.next_stage,
            )
        elif command == "coverage-rebase":
            result = _invoke(
                service,
                "rebase_coverage_stage_schema",
                after_object_id=args.after_object_id,
                limit=args.limit,
            )
        elif command == "matter-coverage-rebase":
            result = _invoke(
                service,
                "rebase_existing_matter_coverage",
                after_matter_id=args.after_matter_id,
                limit=args.limit,
            )
        elif command == "matter-depth-rebase":
            result = _invoke(
                service,
                "rebase_matter_semantic_depth",
                after_matter_id=args.after_matter_id,
                limit=args.limit,
                max_descendants=args.max_descendants,
                max_sources=args.max_sources,
            )
        elif command == "matter-source-reconcile":
            result = _invoke(
                service,
                "reconcile_matter_source_revisions",
                after_matter_id=args.after_matter_id,
                limit=args.limit,
            )
        elif command == "source-revision-analysis-plan":
            result = _invoke(
                service,
                "source_revision_analysis_plan",
                matter_id=args.matter_id,
                after_matter_id=args.after_matter_id,
                limit=args.limit,
                queue=args.queue,
            )
        elif command == "matter-semantic-analysis-plan":
            result = _invoke(
                service,
                "matter_semantic_analysis_plan",
                matter_id=args.matter_id,
                after_matter_id=args.after_matter_id,
                limit=args.limit,
                queue=args.queue,
            )
        elif command == "gmail-current-scope-reconcile":
            result = _invoke(
                service,
                "reconcile_gmail_current_scope",
                after_object_id=args.after_object_id,
                limit=args.limit,
            )
        elif command == "gmail-content-receipt-rebase":
            result = _invoke(
                service,
                "rebase_gmail_content_receipts",
                after_object_id=args.after_object_id,
                limit=args.limit,
            )
        elif command == "noncanonical-matter-coverage-reconcile":
            result = _invoke(
                service,
                "reconcile_noncanonical_matter_coverage",
                after_object_id=args.after_object_id,
                limit=args.limit,
                dry_run=args.dry_run,
            )
        elif command == "noncanonical-matter-hierarchy-reconcile":
            result = _invoke(
                service,
                "reconcile_noncanonical_matter_hierarchy",
                after_matter_id=args.after_matter_id,
                limit=args.limit,
                dry_run=args.dry_run,
            )
        elif command == "matter-presentation-reconcile":
            result = _invoke(
                service,
                "reconcile_admitted_matter_presentation",
                after_matter_id=args.after_matter_id,
                limit=args.limit,
            )
        elif command == "coverage-history-archive":
            result = _invoke(
                service,
                "archive_object_coverage_history",
                after_object_id=args.after_object_id,
                after_revision=args.after_revision,
                limit=args.limit,
            )
        elif command == "evidence-pointer-rebase":
            result = _invoke(
                service,
                "rebase_legacy_evidence_pointers",
                after_object_id=args.after_object_id,
                limit=args.limit,
            )
        elif command == "source-group-rebase":
            result = _invoke(
                service,
                "rebase_source_group_index",
                after_object_id=args.after_object_id,
                after_scope_id=args.after_scope_id,
                limit=args.limit,
            )
        elif command == "coverage-reconcile":
            result = _invoke(
                service,
                "reconcile_coverage_inventory_orphans",
                limit=args.limit,
            )
        elif command == "inventory-policy-rebase":
            result = _invoke(
                service,
                "rebase_current_inventory_policy",
                provider=args.provider,
                offset=args.offset,
                limit=args.limit,
            )
        elif command == "selection-page":
            result = _invoke(
                service,
                "content_selection_page",
                offset=args.offset,
                limit=args.limit,
            )
        elif command == "selection-rebase":
            result = _invoke(
                service,
                "rebase_content_selection",
                after_object_id=args.after_object_id,
                limit=args.limit,
            )
        elif command == "coverage-audit":
            if args.offset < 0 or args.limit < 1 or args.limit > 200:
                raise ValueError("invalid_page_bounds")
            audit_kwargs: dict[str, object] = {
                "offset": args.offset,
                "limit": args.limit,
                "object_kind": args.object_kind,
            }
            for key in (
                "surface_id",
                "surface_status",
                "owner_id",
                "failure_class",
                "freshness",
            ):
                if value := str(getattr(args, key, "")):
                    audit_kwargs[key] = value
            if args.ui_ready != "":
                audit_kwargs["ui_ready"] = args.ui_ready == "true"
            result = _invoke(
                service,
                "object_stage_audit",
                **audit_kwargs,
            )
        elif command == "gmail-manifest-coverage-audit":
            if args.receipt is None and not args.page:
                raise ValueError("gmail_manifest_coverage_input_required")
            result = _invoke(
                service,
                "gmail_manifest_coverage_audit",
                receipt_path=(str(args.receipt) if args.receipt else ""),
                page_paths=tuple(str(path) for path in args.page),
            )
        elif command == "hierarchy-coverage":
            result = _invoke(
                service,
                "matter_hierarchy_coverage_page",
                offset=args.offset,
                limit=args.limit,
                next_stage=args.next_stage,
            )
        elif command == "analysis-packages":
            result = _invoke(
                service,
                "pending_analysis_packages",
                offset=args.offset,
                limit=args.limit,
                package_id=args.package_id,
                source_revision=args.source_revision,
                task_kind=args.task_kind,
            )
        elif command == "analysis-rebase":
            result = _invoke(
                service,
                "rebase_analysis_contracts",
                after_package_id=args.after_package_id,
                limit=args.limit,
            )
        elif command == "analysis-followup-reconcile":
            result = _invoke(
                service,
                "reconcile_annotation_semantic_followups",
                after_package_id=args.after_package_id,
                limit=args.limit,
            )
        elif command == "research-request":
            result = _invoke(
                service,
                "queue_research_operation",
                matter_id=args.matter_id,
                question=args.question,
            )
        elif command == "analysis-import":
            payload = json.loads(args.result_file.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError("result_object_required")
            result = _invoke(
                service,
                "import_autonomous_result",
                package_id=args.package_id,
                provider_id=args.provider_id,
                provider_version=args.provider_version,
                result=payload,
            )
        elif command == "hero-packages":
            if args.offset < 0 or args.limit < 1 or args.limit > 100:
                raise ValueError("invalid_page_bounds")
            result = _invoke(
                service,
                "pending_generated_heroes",
                offset=args.offset,
                limit=args.limit,
            )
        elif command == "hero-refresh":
            result = _invoke(
                service,
                "refresh_generated_hero",
                matter_id=args.matter_id,
            )
        elif command == "hero-import":
            content = args.image_file.read_bytes()
            if not content or len(content) > 20 * 1024 * 1024:
                raise ValueError("invalid_generated_hero_size")
            result = _invoke(
                service,
                "register_generated_hero",
                matter_id=args.matter_id,
                brief_fingerprint=args.brief_fingerprint,
                content=content,
                media_type=args.media_type,
                localized_alt={
                    "en": args.alt_en,
                    "zh-CN": args.alt_zh_cn,
                },
                runner_contract_id=args.runner_contract_id,
                execution_identity=args.execution_identity,
            )
        elif command == "hero-fail":
            result = _invoke(
                service,
                "record_generated_hero_failure",
                matter_id=args.matter_id,
                failure_kind=args.failure_kind,
            )
        elif command == "storage-migration-plan":
            result = _invoke(
                service,
                "source_in_place_migration_plan",
            )
        elif command == "storage-migration-backup":
            result = _invoke(
                service,
                "create_source_in_place_backup",
                backup_root=args.backup_root,
            )
        elif command == "storage-migration-backup-verify":
            result = _invoke(
                service,
                "verify_source_in_place_backup",
                backup_root=args.backup_root,
            )
        elif command == "storage-migration-apply":
            result = _invoke(
                service,
                "apply_source_in_place_migration_batch",
                backup_root=args.backup_root,
                limit=args.limit,
            )
        elif command == "storage-migration-clean":
            result = _invoke(
                service,
                "clean_source_in_place_storage",
                backup_root=args.backup_root,
                blob_limit=args.blob_limit,
            )
        elif command == "storage-migration-verify":
            result = _invoke(
                service,
                "verify_source_in_place_migration",
                backup_root=args.backup_root,
            )
        elif command == "execution-profile-status":
            result = _invoke(
                service,
                "codex_execution_profile_receipt",
            )
        elif command == "execution-profile-activate":
            payload = json.loads(
                args.profile_file.read_text(encoding="utf-8")
            )
            entries = (
                payload.get("entries")
                if isinstance(payload, Mapping)
                else payload
            )
            if not isinstance(entries, list):
                raise ValueError("profile_entries_required")
            result = _invoke(
                service,
                "activate_codex_execution_profile",
                entries=tuple(entries),
            )
        elif command == "maintenance":
            result = _invoke(
                service,
                "run_maintenance_cycle",
                limit=args.limit,
            )
        elif command == "maintenance-orchestration":
            request_payload = json.loads(
                args.request_file.read_text(encoding="utf-8")
            )
            result = _invoke(
                service,
                "run_planned_maintenance",
                request=_planned_maintenance_request(request_payload),
            )
        elif command == "temporal-event-rebase":
            result = _invoke(
                service,
                "rebase_temporal_event_logical_identity",
                offset=args.offset,
                limit=args.limit,
            )
        elif command == "matter-activity-reconcile":
            result = _invoke(
                service,
                "reconcile_current_matter_activity",
            )
        elif command == "correct":
            result = _invoke(
                service,
                "submit_matter_correction",
                matter_id=args.matter_id,
                rationale=args.rationale,
                field_name=args.field,
                corrected_value=args.value,
            )
        elif command == "skill-sync":
            result = _invoke(
                service,
                "synchronize_managed_skill_projections",
                transaction_id_prefix=args.transaction_id_prefix,
            )
        elif command == "pause":
            result = _invoke(service, "pause_work", job_id=args.job_id)
        elif command == "resume":
            result = _invoke(service, "resume_work", job_id=args.job_id)
        elif command in {"inventory", "canary", "expand"}:
            result = _invoke(
                service,
                "scan_filesystem",
                root=str(args.root),
                content_limit=0 if command == "inventory" else args.limit,
            )
        elif command == "extract-files":
            if args.limit < 1 or args.limit > 500:
                raise ValueError("invalid_registered_filesystem_batch_limit")
            result = _invoke(
                service,
                "process_registered_filesystem_batch",
                limit=args.limit,
            )
        elif command == "gmail-body-import":
            connector_result = json.loads(
                args.connector_result_file.read_text(encoding="utf-8")
            )
            if not isinstance(connector_result, Mapping):
                raise ValueError("gmail_body_result_mapping_required")
            result = _invoke(
                service,
                "import_gmail_body_continuation",
                manifest_bytes=args.manifest_file.read_bytes(),
                connector_result=connector_result,
            )
        else:
            raise CapabilityUnavailable("serve_requires_local_composition")
    except CapabilityUnavailable as exc:
        error = {"code": "capability_unavailable", "operation": str(exc)}
        exit_code = 3
    except RuntimeError:
        error = {"code": "runtime_unavailable"}
        exit_code = 5
    except UnsupportedLocale:
        error = {"code": "unsupported_locale"}
        exit_code = 4
    except (KeyError, TypeError, ValueError):
        error = {"code": "invalid_request"}
        exit_code = 4
    else:
        json.dump({"ok": True, "result": result}, output, ensure_ascii=False, sort_keys=True)
        output.write("\n")
        return 0
    json.dump({"ok": False, "error": error}, errors, ensure_ascii=False, sort_keys=True)
    errors.write("\n")
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    parsed = build_parser().parse_args(arguments)
    if parsed.command in _OFFLINE_STORAGE_COMMANDS:
        return _run_offline_storage_command(
            parsed,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    from matters.runtime import create_service, repository_root

    if arguments and arguments[0] == "serve":
        from wsgiref.simple_server import make_server

        from matters.api.http.static import create_local_application
        from matters.desktop import _QuietRequestHandler, _ThreadingWSGIServer

        service = create_service()
        service.start_autonomous_maintenance()
        application = create_local_application(
            service,
            ui_root=repository_root() / "ui",
        )
        try:
            with make_server(
                parsed.host,
                parsed.port,
                application,
                server_class=_ThreadingWSGIServer,
                handler_class=_QuietRequestHandler,
            ) as server:
                print(
                    f"Matters is available at http://{parsed.host}:{parsed.port}/",
                    flush=True,
                )
                server.serve_forever()
        finally:
            service.stop_autonomous_maintenance()
        return 0
    return run(arguments, service=create_service())


__all__ = [
    "CapabilityUnavailable",
    "EntrypointService",
    "build_parser",
    "main",
    "run",
]


if __name__ == "__main__":
    raise SystemExit(main())
