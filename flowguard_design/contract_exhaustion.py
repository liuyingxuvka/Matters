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
    ),
    CHILD_IDS[1]: (
        ("source_occurrence", ("added", "modified", "moved", "deleted", "newly_reachable", "unchanged")),
        ("content_relation", ("same", "changed")),
        ("dependent_freshness", ("current", "stale")),
        ("visual_derivative", ("eligible", "unsafe", "stale", "absent")),
    ),
    CHILD_IDS[2]: (
        ("anchor_quality", ("precise", "missing", "stale")),
        ("evidence_modality", ("reported", "observed", "inferred")),
        ("visual_eligibility", ("eligible", "denied", "unrelated", "absent")),
    ),
    CHILD_IDS[3]: (
        ("mention_resolution", ("unique", "same_name", "conflicting")),
        ("role_scope", ("matter_scoped", "global_assumption")),
    ),
    CHILD_IDS[4]: (
        ("temporal_modality", ("planned", "reported", "observed", "inferred")),
        ("conflict_strength", ("none", "weak", "strong")),
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
    ),
    CHILD_IDS[6]: (
        ("start_evidence", ("explicit", "indirect", "none")),
        ("schedule_state", ("unscheduled", "scheduled")),
        ("provider_state", ("open", "done")),
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
                "visual_recommendation",
                "forecast",
            ),
        ),
        ("research_provider", ("current", "pending", "legacy_parallel")),
        ("scope_relation", ("inside", "escape")),
        ("input_accounting", ("complete", "missing", "foreign")),
        ("dispatch_state", ("queued", "terminal", "retry", "blocked")),
        ("write_request", ("owner_dispatch", "canonical")),
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
                "open_detail",
                "optional_correction",
                "infer",
                "write",
            ),
        ),
        ("visual_state", ("selected", "placeholder", "stale", "denied")),
        ("content_class", ("user_visible", "user_on_demand", "internal")),
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
        group_id = f"CG-{_safe_id(model_id)}-local-cartesian"
        group_ids.append(group_id)
        groups.append(
            ContractInteractionGroup(
                group_id=group_id,
                model_id=model_id,
                axis_ids=tuple(model_axes),
                required_routes=("model_test_alignment", "test_mesh"),
                max_combinations=prod(
                    len(values) for _, values in AXIS_UNIVERSES[model_id]
                ),
                oracle_id=oracle_id,
                oracle_status="model_owned_disposition",
                description=(
                    "Exhaust only this child model's bounded axes; do not form "
                    "a whole-product global Cartesian."
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
        inventory_revision="g4-autonomous-object-browser-universes-v2",
        inventory_current=True,
        model_id=PARENT_ID,
        model_level="parent",
        metadata={"whole_product_cartesian": "forbidden"},
    )


def run_review():
    plan = build_plan()
    return plan, review_contract_exhaustion(plan)


__all__ = ["AXIS_UNIVERSES", "build_plan", "run_review"]
