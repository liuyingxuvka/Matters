"""Finite, model-local bad-case Cartesian universes for C1-C12."""

from __future__ import annotations

from math import prod

from flowguard.contract_exhaustion import (
    ContractAxis,
    ContractCoverageUniverse,
    ContractExhaustionPlan,
    ContractInteractionGroup,
    ContractOracle,
    review_contract_exhaustion,
)

from flowguard_design.inventory import CHILD_IDS, PARENT_ID


AXIS_UNIVERSES: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    CHILD_IDS[0]: (
        ("authorization_state", ("active", "revoked")),
        (
            "tracking_state",
            (
                "tracked",
                "not_tracked",
                "hard_excluded",
                "metadata_only",
                "blocked",
                "unavailable",
            ),
        ),
        ("coverage_state", ("complete", "partial", "unknown")),
        ("policy_freshness", ("current", "stale")),
        ("coverage_rebase_scope", ("active_tracked", "retired_or_nontracked")),
        ("coverage_inventory_binding", ("current", "orphan")),
        (
            "coverage_storage_shape",
            ("current_full_history_exact_archive", "inline_hot_history", "archive_unverified"),
        ),
        ("storage_migration_execution", ("explicit_bounded", "startup", "vacuum")),
    ),
    CHILD_IDS[1]: (
        ("source_occurrence", ("added", "modified", "moved", "deleted", "newly_reachable", "unchanged")),
        ("content_relation", ("same", "changed")),
        ("dependent_freshness", ("current", "stale")),
        ("gallery_derivative", ("eligible", "unsafe", "stale", "absent")),
        ("scope_overlap", ("single", "parent_and_nested_same_occurrence")),
        ("selection_semantic_change", ("unchanged", "changed")),
        ("inventory_scan_revision", ("same", "advanced")),
        (
            "gmail_metadata_owner_state",
            (
                "missing_exact_current_owner",
                "already_current",
                "existing_body_preserved",
                "stale_or_foreign_owner",
                "exact_retry",
            ),
        ),
    ),
    CHILD_IDS[2]: (
        ("anchor_quality", ("precise", "missing", "stale")),
        ("evidence_modality", ("reported", "observed", "inferred")),
        ("gallery_display_eligibility", ("eligible", "denied", "unrelated", "absent")),
        (
            "anchor_reference_shape",
            ("bounded_version_count_digest", "full_anchor_id_list", "missing"),
        ),
    ),
    CHILD_IDS[3]: (
        ("mention_resolution", ("unique", "same_name", "conflicting")),
        ("role_scope", ("matter_scoped", "global_assumption")),
    ),
    CHILD_IDS[4]: (
        ("temporal_modality", ("planned", "reported", "observed", "inferred")),
        ("conflict_strength", ("none", "weak", "strong")),
        ("materiality", ("material", "nonmaterial", "uncertain")),
        ("ancestor_rollup", ("root", "child", "deep_child")),
        ("observation_time", ("exact_historical", "current_event", "missing", "future_due")),
        ("logical_event_revision", ("single_current", "superseded_revision", "conflicting_current")),
    ),
    CHILD_IDS[5]: (
        (
            "admission_state",
            (
                "source_only",
                "candidate",
                "admitted",
                "not_applicable",
                "uncertain",
                "blocked",
            ),
        ),
        ("membership_shape", ("one", "many")),
        ("placement", ("append_current", "admit_child", "admit_related", "admit_root", "uncertain")),
        ("context_strength", ("multi_signal", "single_weak", "conflicting")),
        ("parent_composition", ("atomic_success", "attachment_failure")),
        ("canonicalization", ("merge", "append", "source_only", "conflicting_retry")),
        (
            "canonical_identity_input",
            ("exact_admitted_matter_id", "projection_only", "source_or_candidate"),
        ),
        ("ui_hierarchy_node_kind", ("matter", "work_event_fact_source")),
        ("known_root_family", ("travel", "software_portfolio", "other")),
        ("cross_domain_relation", ("none", "typed_secondary", "second_primary_parent")),
    ),
    CHILD_IDS[6]: (
        ("start_evidence", ("explicit", "indirect", "none")),
        ("schedule_state", ("unscheduled", "scheduled")),
        ("provider_state", ("open", "done")),
        ("display_semantics", ("lifecycle_plus_modality", "modality_as_lifecycle")),
    ),
    CHILD_IDS[7]: (
        ("dependency_criticality", ("critical", "noncritical")),
        ("wait_target", ("present", "missing")),
        ("response_state", ("open", "closed")),
    ),
    CHILD_IDS[8]: (
        ("completion_criteria", ("explicit", "missing")),
        ("provider_state", ("open", "done")),
        ("later_obligation", ("none", "new")),
    ),
    CHILD_IDS[9]: (
        ("revision_kind", ("correction", "revocation", "deletion", "supersession")),
        ("dependent_disposition", ("complete", "partial", "blocked", "missing")),
        ("recovery_state", ("initial", "retry", "restart")),
        ("hero_invalidation", ("identity_or_theme", "ordinary_clue", "safety_or_policy")),
        ("activity_scope", ("self", "ancestor_chain", "unrelated")),
        ("observation_correction_scope", ("source", "ancestors", "late_bound_canonical")),
    ),
    CHILD_IDS[10]: (
        ("operation_freshness", ("current", "stale", "progress_only")),
        (
            "analysis_mode",
            (
                "ai",
                "researchguard",
                "scope_triage",
                "depth",
                "hero_image_generator",
                "summary_candidate",
                "human_matter_narrative",
                "supplemental_information",
                "forecast",
            ),
        ),
        ("research_provider", ("current", "pending", "legacy_parallel")),
        ("scope_relation", ("inside", "escape")),
        ("input_accounting", ("complete", "missing", "foreign")),
        ("dispatch_state", ("queued", "terminal", "retry", "blocked")),
        ("write_request", ("owner_dispatch", "canonical")),
        ("supplemental_item_count", ("nonzero", "zero")),
        ("narrative_language", ("human", "internal_audit")),
    ),
    CHILD_IDS[11]: (
        ("localization_state", ("fresh", "stale", "conflict")),
        ("revision_relation", ("same", "different")),
        ("recompute_state", ("current", "pending", "blocked")),
        (
            "ui_action",
            (
                "render",
                "search",
                "filter",
                "density",
                "background_refresh_unchanged",
                "background_refresh_changed",
                "background_refresh_failure",
                "open_detail",
                "optional_correction",
                "infer",
                "write",
            ),
        ),
        ("hero_state", ("generated_current", "generation_pending_placeholder", "generation_blocked_placeholder")),
        ("hero_evidence_relation", ("presentation_only", "gallery_leak", "source_leak")),
        ("activity_order", ("current", "stale", "nonmaterial_bubble")),
        ("detail_section_count", ("eight", "missing", "extra")),
        ("catalog_query_shape", ("indexed_page_then_hydrate", "all_cards_then_slice")),
        ("content_class", ("user_visible", "user_on_demand", "internal")),
        ("overview_shape", ("minimal_human", "internal_panels")),
        ("hierarchy_graph_node_kind", ("matter_only", "mixed_internal_types")),
        ("node_quick_view_scope", ("selected_matter_only", "root_wide_or_recursive")),
        ("timeline_revision_shape", ("logical_current_only", "superseded_duplicates")),
        ("supplemental_projection", ("nonempty_current", "empty_pending", "empty_current")),
        ("coverage_projection", ("bounded_first_gap", "false_green", "full_ledger_scan")),
        ("files_typography", ("wrapped_subordinate", "oversized_overflow")),
        ("lifecycle_visual_semantics", ("status_plus_modality", "modality_conflated")),
    ),
}

SPLIT_AXIS_GROUPS: dict[str, tuple[tuple[str, ...], ...]] = {
    CHILD_IDS[5]: (
        (
            "admission_state",
            "membership_shape",
            "placement",
            "context_strength",
            "parent_composition",
            "canonicalization",
            "canonical_identity_input",
        ),
        (
            "ui_hierarchy_node_kind",
            "known_root_family",
            "cross_domain_relation",
        ),
    ),
    CHILD_IDS[10]: (
        (
            "operation_freshness",
            "analysis_mode",
            "research_provider",
            "scope_relation",
            "input_accounting",
            "dispatch_state",
            "write_request",
        ),
        (
            "analysis_mode",
            "supplemental_item_count",
            "narrative_language",
        ),
    ),
    CHILD_IDS[11]: (
        ("localization_state", "revision_relation", "recompute_state"),
        ("ui_action", "content_class"),
        ("hero_state", "hero_evidence_relation"),
        ("activity_order", "catalog_query_shape"),
        ("detail_section_count", "overview_shape"),
        ("hierarchy_graph_node_kind", "node_quick_view_scope"),
        ("timeline_revision_shape", "lifecycle_visual_semantics"),
        ("supplemental_projection", "coverage_projection"),
        ("files_typography",),
    ),
}


def _safe_id(value: str) -> str:
    return value.replace("_", "-")


def build_plan() -> ContractExhaustionPlan:
    axes: list[ContractAxis] = []
    groups: list[ContractInteractionGroup] = []
    oracles: list[ContractOracle] = []
    axis_ids: list[str] = []
    group_ids: list[str] = []
    for model_id in CHILD_IDS:
        model_axes: list[str] = []
        for name, values in AXIS_UNIVERSES[model_id]:
            axis_id = f"AX-{_safe_id(model_id)}-{name}"
            axis_ids.append(axis_id)
            model_axes.append(axis_id)
            axes.append(
                ContractAxis(
                    axis_id=axis_id,
                    model_id=model_id,
                    values=values,
                    source_route="flowguard-model",
                    description=f"Finite {name} axis for {model_id}",
                )
            )
        oracle_id = f"OR-{_safe_id(model_id)}-owned-disposition"
        oracles.append(
            ContractOracle(
                oracle_id=oracle_id,
                expected_status="model_owned_disposition",
                expected_message_fields=("decision", "reason"),
                forbidden_downstream_steps=("foreign_canonical_write",),
                required_repair_fields=("owner_model_id",),
                description=(
                    "Every local Cartesian case must terminate in the owning "
                    "model with an explicit autonomous decision or visible blocker."
                ),
            )
        )
        values_by_name = dict(AXIS_UNIVERSES[model_id])
        axis_id_by_name = {
            name: f"AX-{_safe_id(model_id)}-{name}"
            for name, _ in AXIS_UNIVERSES[model_id]
        }
        interaction_groups = SPLIT_AXIS_GROUPS.get(
            model_id,
            (tuple(values_by_name),),
        )
        for index, axis_names in enumerate(interaction_groups, start=1):
            group_id = (
                f"CG-{_safe_id(model_id)}-local-cartesian-{index}"
                if len(interaction_groups) > 1
                else f"CG-{_safe_id(model_id)}-local-cartesian"
            )
            group_ids.append(group_id)
            groups.append(
                ContractInteractionGroup(
                    group_id=group_id,
                    model_id=model_id,
                    axis_ids=tuple(axis_id_by_name[name] for name in axis_names),
                    required_routes=("model_test_alignment", "test_mesh"),
                    max_combinations=prod(
                        len(values_by_name[name]) for name in axis_names
                    ),
                    oracle_id=oracle_id,
                    oracle_status="model_owned_disposition",
                    description=(
                        "Exhaust one explicitly related bounded axis cluster for "
                        "this child model; independent clusters and the whole "
                        "product are not multiplied together."
                    ),
                )
            )
    universe = ContractCoverageUniverse(
        universe_id="CU-Matters-C1-C12-model-local",
        claim_scope="model_local_finite_universes",
        source_refs=("flowguard_models/models", "flowguard_design/contract_exhaustion.py"),
        required_axis_ids=tuple(axis_ids),
        required_interaction_group_ids=tuple(group_ids),
        require_full_product=False,
        metadata={
            "global_cartesian_forbidden": True,
            "model_count": len(CHILD_IDS),
        },
    )
    return ContractExhaustionPlan(
        plan_id="CE-Matters-C1-C12",
        claim_scope="model_local_matrix",
        source_model_ids=CHILD_IDS,
        generation_policy="bounded",
        allow_unbounded_scoped=False,
        required_route_ids=("model_test_alignment", "test_mesh"),
        require_composite_handoff_acceptance=False,
        axes=tuple(axes),
        interaction_groups=tuple(groups),
        oracles=tuple(oracles),
        cartesian_case_limit=5000,
        coverage_universe=universe,
        require_coverage_universe=True,
        require_actionable_oracle_feedback=True,
        inventory_revision="g4-matter-browser-semantic-reset-universes-v8",
        inventory_current=True,
        model_id=PARENT_ID,
        model_level="parent",
        metadata={"whole_product_cartesian": "forbidden"},
    )


def run_review():
    plan = build_plan()
    return plan, review_contract_exhaustion(plan)


__all__ = ["AXIS_UNIVERSES", "build_plan", "run_review"]
