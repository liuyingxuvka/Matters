"""C7 Lifecycle & Board State finite FlowGuard model declaration."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C7_lifecycle_board_state",
    title="C7 Lifecycle & Board State",
    modeled_boundary=(
        "evidence-licensed lifecycle axes, canonical board placement, current "
        "child-state snapshots, visible certainty class, advisory inference "
        "basis and alternatives, non-mechanical ancestor lifecycle rollup, and "
        "a stable lifecycle display key kept separate from evidence modality"
    ),
    state_fields=(
        "matter.lifecycle_axes",
        "matter.board_placement",
        "matter.state_rationale",
        "matter.child_state_snapshot",
        "matter.ancestor_lifecycle_rollup",
        "matter.lifecycle_certainty",
        "matter.lifecycle_inference_basis",
        "matter.lifecycle_inference_alternatives",
        "matter.lifecycle_inference_expiry",
        "matter.lifecycle_display_key",
        "matter.lifecycle_basis_modality",
    ),
    owned_write_fields=(
        "matter.lifecycle_axes",
        "matter.board_placement",
        "matter.state_rationale",
        "matter.child_state_snapshot",
        "matter.ancestor_lifecycle_rollup",
        "matter.lifecycle_certainty",
        "matter.lifecycle_inference_basis",
        "matter.lifecycle_inference_alternatives",
        "matter.lifecycle_inference_expiry",
        "matter.lifecycle_display_key",
        "matter.lifecycle_basis_modality",
    ),
    side_effect_classes=("lifecycle_registry_write",),
    completion_evidence=(
        "LifecycleState",
        "BoardPlacement",
        "StateRationale",
        "LifecycleUncertainty",
        "CoverageGap",
        "CompletionUnproven",
        "ChildStateCurrent",
        "AncestorRollupCurrent",
        "HierarchyProgressSummary",
        "RollupUncertainty",
        "LifecycleCertainty",
        "AIInferredLifecycle",
        "InferenceAlternatives",
        "LifecycleDisplayContract",
        "LifecycleModalitySeparated",
    ),
    rules=(
        CaseRule(
            case_id="elapsed_planned_activity_with_supporting_trace_but_no_confirmation",
            decision="provisional_lifecycle_ai_inferred",
            label="provisional_lifecycle_ai_inferred",
            writes=(
                "matter.lifecycle_axes",
                "matter.board_placement",
                "matter.state_rationale",
                "matter.lifecycle_certainty",
                "matter.lifecycle_inference_basis",
                "matter.lifecycle_inference_alternatives",
                "matter.lifecycle_inference_expiry",
            ),
            side_effects=("lifecycle_registry_write",),
            emitted_tokens=(
                "LifecycleState",
                "BoardPlacement",
                "StateRationale",
                "LifecycleCertainty",
                "AIInferredLifecycle",
                "InferenceAlternatives",
            ),
            reason=(
                "elapsed travel, booking, application, or scheduled work may be "
                "projected to the most likely current lifecycle when supporting "
                "trace and world context exist, but it remains visibly "
                "ai_inferred with confidence, alternatives, and expiry rather "
                "than confirmed_observed"
            ),
        ),
        CaseRule(
            case_id="lifecycle_state_projected_for_human_display",
            decision="stable_lifecycle_key_and_modality_published_separately",
            label="stable_lifecycle_key_and_modality_published_separately",
            writes=(
                "matter.lifecycle_display_key",
                "matter.lifecycle_basis_modality",
            ),
            side_effects=("lifecycle_registry_write",),
            emitted_tokens=(
                "LifecycleDisplayContract",
                "LifecycleModalitySeparated",
            ),
            reason=(
                "planned, in_progress, and completed are the stable human "
                "lifecycle display keys; reported, observed, and inferred remain "
                "a separate evidence-basis modality and cannot replace lifecycle"
            ),
        ),
        CaseRule(
            case_id="explicit_start_evidence",
            decision="in_progress",
            label="in_progress",
            writes=(
                "matter.lifecycle_axes",
                "matter.board_placement",
                "matter.state_rationale",
            ),
            side_effects=("lifecycle_registry_write",),
            emitted_tokens=("LifecycleState", "BoardPlacement", "StateRationale"),
            reason="current evidence records actual work beginning",
        ),
        CaseRule(
            case_id="scheduled_only",
            decision="planned",
            label="planned",
            writes=(
                "matter.lifecycle_axes",
                "matter.board_placement",
                "matter.state_rationale",
            ),
            side_effects=("lifecycle_registry_write",),
            emitted_tokens=("LifecycleState", "BoardPlacement", "StateRationale"),
            reason="assignment, sprint, or due date licenses planned but not active",
        ),
        CaseRule(
            case_id="partial_coverage_no_start",
            decision="state_uncertain",
            label="state_uncertain",
            writes=(
                "matter.lifecycle_axes",
                "matter.board_placement",
                "matter.state_rationale",
            ),
            side_effects=("lifecycle_registry_write",),
            emitted_tokens=(
                "LifecycleState",
                "BoardPlacement",
                "StateRationale",
                "LifecycleUncertainty",
                "CoverageGap",
            ),
            reason=(
                "absence under partial coverage cannot prove not-started, so the "
                "best current state is marked uncertain and remains automatically projected"
            ),
        ),
        CaseRule(
            case_id="provider_done_without_completion",
            decision="provider_done_completion_unproven",
            label="provider_done_completion_unproven",
            writes=("matter.lifecycle_axes", "matter.state_rationale"),
            side_effects=("lifecycle_registry_write",),
            emitted_tokens=("ProviderStateEvidence", "CompletionUnproven", "LifecycleUncertainty"),
            reason="provider Done is evidence, not canonical completion",
        ),
        CaseRule(
            case_id="ui_direct_state_write",
            decision="ui_write_rejected",
            label="ui_write_rejected",
            emitted_tokens=("ProjectionWriteRejected",),
            reason="UI cannot infer or write canonical lifecycle state",
        ),
        CaseRule(
            case_id="required_children_mixed_state",
            decision="child_state_and_ancestor_rollup_current",
            label="child_state_and_ancestor_rollup_current",
            writes=(
                "matter.child_state_snapshot",
                "matter.ancestor_lifecycle_rollup",
                "matter.state_rationale",
            ),
            side_effects=("lifecycle_registry_write",),
            emitted_tokens=(
                "ChildStateCurrent",
                "AncestorRollupCurrent",
                "HierarchyProgressSummary",
                "StateRationale",
            ),
            reason=(
                "the parent summary reports counts and named required/critical "
                "children while preserving direct parent evidence; child state "
                "alone does not select the parent's lifecycle axis"
            ),
        ),
        CaseRule(
            case_id="completed_child_parent_evidence_unchanged",
            decision="child_completion_recorded_without_parent_transition",
            label="child_completion_recorded_without_parent_transition",
            writes=(
                "matter.child_state_snapshot",
                "matter.ancestor_lifecycle_rollup",
                "matter.state_rationale",
            ),
            side_effects=("lifecycle_registry_write",),
            emitted_tokens=(
                "ChildStateCurrent",
                "AncestorRollupCurrent",
                "HierarchyProgressSummary",
            ),
            reason=(
                "a completed booking or application branch updates the parent's "
                "summary but does not mechanically complete, start, or move the parent"
            ),
        ),
        CaseRule(
            case_id="related_matter_state_changed",
            decision="nonhierarchical_relation_excluded_from_rollup",
            label="nonhierarchical_relation_excluded_from_rollup",
            writes=("matter.ancestor_lifecycle_rollup", "matter.state_rationale"),
            side_effects=("lifecycle_registry_write",),
            emitted_tokens=("AncestorRollupCurrent", "StateRationale"),
            reason=(
                "related, shared-person, and shared-source edges never participate "
                "in lifecycle rollup"
            ),
        ),
        CaseRule(
            case_id="known_children_with_depth_pending",
            decision="bounded_progress_summary_uncertain",
            label="bounded_progress_summary_uncertain",
            writes=(
                "matter.child_state_snapshot",
                "matter.ancestor_lifecycle_rollup",
                "matter.state_rationale",
            ),
            side_effects=("lifecycle_registry_write",),
            emitted_tokens=(
                "ChildStateCurrent",
                "AncestorRollupCurrent",
                "HierarchyProgressSummary",
                "RollupUncertainty",
            ),
            reason=(
                "known-child counts remain useful but an unknown denominator is "
                "labeled bounded and never converted into an authoritative percentage"
            ),
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-C7-008-modality-replaces-lifecycle-state",
            protected_error_class="lifecycle_modality_conflation",
            description=(
                "reported, observed, inferred, or current is published as the "
                "human lifecycle state"
            ),
            protected_harm=(
                "the UI cannot consistently distinguish planned, in-progress, "
                "and completed Matters"
            ),
            case_id="lifecycle_state_projected_for_human_display",
            broken_decision="basis_modality_published_as_lifecycle",
            broken_writes=(
                "matter.lifecycle_display_key",
                "matter.lifecycle_basis_modality",
            ),
            broken_side_effects=("lifecycle_registry_write",),
            broken_tokens=("LifecycleState",),
        ),
        HazardSpec(
            failure_id="H-C7-001-scheduled-becomes-active",
            protected_error_class="planned_active_conflation",
            description="scheduled or assigned work is classified in progress",
            protected_harm="the board reports activity without occurrence evidence",
            case_id="scheduled_only",
            broken_decision="in_progress",
            broken_writes=(
                "matter.lifecycle_axes",
                "matter.board_placement",
                "matter.state_rationale",
            ),
            broken_side_effects=("lifecycle_registry_write",),
            broken_tokens=("LifecycleState", "BoardPlacement", "StateRationale"),
        ),
        HazardSpec(
            failure_id="H-C7-002-partial-absence-becomes-not-started",
            protected_error_class="absence_as_negative_evidence",
            description="no start evidence under partial coverage becomes a not-started conclusion",
            protected_harm="missing provider access is misrepresented as a real-world fact",
            case_id="partial_coverage_no_start",
            broken_decision="not_started",
            broken_writes=(
                "matter.lifecycle_axes",
                "matter.board_placement",
                "matter.state_rationale",
            ),
            broken_side_effects=("lifecycle_registry_write",),
            broken_tokens=("LifecycleState", "BoardPlacement"),
        ),
        HazardSpec(
            failure_id="H-C7-003-provider-done-becomes-completed",
            protected_error_class="provider_status_authority_escape",
            description="a provider Done label or AI completion statement directly determines canonical completed state",
            protected_harm="provider workflow state replaces real-world completion criteria",
            case_id="provider_done_without_completion",
            broken_decision="completed",
            broken_writes=(
                "matter.lifecycle_axes",
                "matter.board_placement",
                "matter.state_rationale",
            ),
            broken_side_effects=("lifecycle_registry_write",),
            broken_tokens=("LifecycleState", "BoardPlacement"),
        ),
        HazardSpec(
            failure_id="H-C7-004-ui-writes-state",
            protected_error_class="projection_writer_escape",
            description="UI code writes canonical lifecycle state",
            protected_harm="a second truth path bypasses evidence and the lifecycle owner",
            case_id="ui_direct_state_write",
            broken_decision="in_progress",
            broken_writes=(
                "matter.lifecycle_axes",
                "matter.board_placement",
                "matter.state_rationale",
            ),
            broken_side_effects=("lifecycle_registry_write",),
            broken_tokens=("LifecycleState", "BoardPlacement"),
        ),
        HazardSpec(
            failure_id="H-C7-005-active-child-mechanically-activates-parent",
            protected_error_class="child_parent_state_conflation",
            description="one active child mechanically marks its parent in progress",
            protected_harm="child evidence replaces the parent's own lifecycle policy",
            case_id="required_children_mixed_state",
            broken_decision="in_progress",
            broken_writes=(
                "matter.lifecycle_axes",
                "matter.board_placement",
                "matter.state_rationale",
            ),
            broken_side_effects=("lifecycle_registry_write",),
            broken_tokens=("LifecycleState", "BoardPlacement"),
        ),
        HazardSpec(
            failure_id="H-C7-006-related-relation-rolls-up-state",
            protected_error_class="related_edge_rollup_escape",
            description="a related Matter changes the current Matter's lifecycle state",
            protected_harm="non-containment similarity becomes a hidden state dependency",
            case_id="related_matter_state_changed",
            broken_decision="in_progress",
            broken_writes=("matter.lifecycle_axes", "matter.board_placement"),
            broken_side_effects=("lifecycle_registry_write",),
            broken_tokens=("LifecycleState", "BoardPlacement"),
        ),
        HazardSpec(
            failure_id="H-C7-007-partial-depth-fake-percentage",
            protected_error_class="unknown_denominator_false_precision",
            description="partially modeled descendants produce an authoritative completion percentage",
            protected_harm="unknown hierarchy depth is hidden behind false numerical precision",
            case_id="known_children_with_depth_pending",
            broken_decision="progress_percentage_current",
            broken_writes=("matter.ancestor_lifecycle_rollup",),
            broken_side_effects=("lifecycle_registry_write",),
            broken_tokens=("HierarchyProgressSummary",),
        ),
    ),
    risk_classes=("state_transition", "evidence", "ownership", "side_effect"),
    template_no_match_reason=(
        "The Phase A template search returned no evidence-licensed lifecycle and board template."
    ),
    blindspots=(
        "the substantive lifecycle and ancestor-rollup policies require private canaries and optional correction",
        "real UI rendering and provider state conformance remain untested",
    ),
    claim_boundary=(
        "This receipt can establish C7 abstract planned/active, partial-coverage, "
        "provider-status, hierarchy-rollup, false-percentage, and UI-writer "
        "hazards. It does not prove the final lifecycle policy, real board "
        "behavior, hierarchy completeness, or outcome completion."
    ),
)
