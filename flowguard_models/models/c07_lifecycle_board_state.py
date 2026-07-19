"""C7 Lifecycle & Board State finite FlowGuard model declaration."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C7_lifecycle_board_state",
    title="C7 Lifecycle & Board State",
    modeled_boundary="evidence-licensed lifecycle axes and canonical board placement",
    state_fields=(
        "matter.lifecycle_axes",
        "matter.board_placement",
        "matter.state_rationale",
    ),
    owned_write_fields=(
        "matter.lifecycle_axes",
        "matter.board_placement",
        "matter.state_rationale",
    ),
    side_effect_classes=("lifecycle_registry_write",),
    completion_evidence=(
        "LifecycleState",
        "BoardPlacement",
        "StateRationale",
        "LifecycleUncertainty",
        "CoverageGap",
        "CompletionUnproven",
    ),
    rules=(
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
    ),
    hazards=(
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
    ),
    risk_classes=("state_transition", "evidence", "ownership", "side_effect"),
    template_no_match_reason=(
        "The Phase A template search returned no evidence-licensed lifecycle and board template."
    ),
    blindspots=(
        "the substantive lifecycle policy requires private canaries and optional correction",
        "real UI rendering and provider state conformance remain untested",
    ),
    claim_boundary=(
        "This receipt can establish C7 abstract planned/active, partial-coverage, "
        "provider-status, and UI-writer hazards. It does not prove the final "
        "lifecycle policy, real board behavior, or outcome completion."
    ),
)
