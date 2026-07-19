"""C8 Open Loop / Waiting / Blocking finite FlowGuard model declaration."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C8_open_loop_waiting_blocking",
    title="C8 Open Loop / Waiting / Blocking",
    modeled_boundary="requests, wait targets, closure conditions, and partial/full blocking",
    state_fields=(
        "open_loop.identity",
        "open_loop.wait_target",
        "open_loop.closure_condition",
        "matter.blocking_axis",
    ),
    owned_write_fields=(
        "open_loop.identity",
        "open_loop.wait_target",
        "open_loop.closure_condition",
        "matter.blocking_axis",
    ),
    side_effect_classes=("open_loop_registry_write",),
    completion_evidence=("OpenLoop", "Waiting", "PartialBlock", "FullBlock", "LoopClosed", "OpenLoopGap"),
    rules=(
        CaseRule(
            case_id="request_with_target_and_condition",
            decision="waiting_open_loop",
            label="waiting_open_loop",
            writes=(
                "open_loop.identity",
                "open_loop.wait_target",
                "open_loop.closure_condition",
            ),
            side_effects=("open_loop_registry_write",),
            emitted_tokens=("OpenLoop", "Waiting"),
            reason="request names what is awaited and how it closes",
        ),
        CaseRule(
            case_id="vague_waiting_text",
            decision="open_loop_gap",
            label="open_loop_gap",
            emitted_tokens=("OpenLoopGap",),
            reason="waiting lacks a target or closure condition",
        ),
        CaseRule(
            case_id="researchguard_blocker_without_closure",
            decision="open_loop_gap",
            label="researchguard_open_loop_gap",
            emitted_tokens=("OpenLoopGap",),
            reason="an advisory blocker without anchored target and closure condition cannot create a canonical loop",
        ),
        CaseRule(
            case_id="noncritical_subtask_failure",
            decision="partial_block",
            label="partial_block",
            writes=("matter.blocking_axis",),
            side_effects=("open_loop_registry_write",),
            emitted_tokens=("PartialBlock",),
            reason="the affected branch is blocked while the primary path can continue",
        ),
        CaseRule(
            case_id="critical_dependency_failure",
            decision="full_block",
            label="full_block",
            writes=("matter.blocking_axis",),
            side_effects=("open_loop_registry_write",),
            emitted_tokens=("FullBlock",),
            reason="all valid progress paths depend on the failed dependency",
        ),
        CaseRule(
            case_id="matter_complete_loop_unmet",
            decision="preserve_open_loop",
            label="preserve_open_loop",
            writes=("matter.blocking_axis",),
            side_effects=("open_loop_registry_write",),
            emitted_tokens=("OpenLoop",),
            reason="Matter completion does not silently close an independent loop",
        ),
        CaseRule(
            case_id="declared_closure_evidence",
            decision="open_loop_closed",
            label="open_loop_closed",
            writes=(
                "open_loop.identity",
                "open_loop.wait_target",
                "open_loop.closure_condition",
            ),
            side_effects=("open_loop_registry_write",),
            emitted_tokens=("LoopClosed",),
            reason="the declared closure condition is satisfied",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-C8-001-wait-without-closure-condition",
            protected_error_class="unclosable_wait",
            description="vague waiting text creates a canonical OpenLoop",
            protected_harm="the system creates a wait that cannot be objectively closed",
            case_id="vague_waiting_text",
            broken_decision="waiting_open_loop",
            broken_writes=(
                "open_loop.identity",
                "open_loop.wait_target",
                "open_loop.closure_condition",
            ),
            broken_side_effects=("open_loop_registry_write",),
            broken_tokens=("OpenLoop", "Waiting"),
        ),
        HazardSpec(
            failure_id="H-C8-002-noncritical-failure-fully-blocks",
            protected_error_class="blocking_scope_expansion",
            description="a noncritical subtask failure marks the whole Matter fully blocked",
            protected_harm="valid remaining progress is hidden and the board overstates the blocker",
            case_id="noncritical_subtask_failure",
            broken_decision="full_block",
            broken_writes=("matter.blocking_axis",),
            broken_side_effects=("open_loop_registry_write",),
            broken_tokens=("FullBlock",),
        ),
        HazardSpec(
            failure_id="H-C8-003-matter-completion-closes-loop",
            protected_error_class="independent_loop_silent_closure",
            description="Matter completion silently closes an unmet independent OpenLoop",
            protected_harm="a real outstanding request disappears from the user's view",
            case_id="matter_complete_loop_unmet",
            broken_decision="open_loop_closed",
            broken_writes=(
                "open_loop.identity",
                "open_loop.wait_target",
                "open_loop.closure_condition",
            ),
            broken_side_effects=("open_loop_registry_write",),
            broken_tokens=("LoopClosed",),
        ),
        HazardSpec(
            failure_id="H-C8-004-advisory-blocker-becomes-loop",
            protected_error_class="advisory_open_loop_authority_escape",
            description="a ResearchGuard blocker proposal creates a canonical loop without closure evidence",
            protected_harm="the user receives an unclosable inferred obligation",
            case_id="researchguard_blocker_without_closure",
            broken_decision="waiting_open_loop",
            broken_writes=(
                "open_loop.identity",
                "open_loop.wait_target",
                "open_loop.closure_condition",
            ),
            broken_side_effects=("open_loop_registry_write",),
            broken_tokens=("OpenLoop", "Waiting"),
        ),
    ),
    risk_classes=("state_transition", "liveness", "ownership", "side_effect"),
    template_no_match_reason=(
        "The Phase A template search returned no wait-target and partial/full blocking template."
    ),
    blindspots=(
        "criticality policy and valid progress-path calculation require later design evidence",
        "human follow-up timing and notification behavior are outside this child",
    ),
    claim_boundary=(
        "This receipt can establish C8 abstract wait, closure, and blocking-scope "
        "hazards. It does not establish real dependency criticality, notification "
        "delivery, or parent liveness."
    ),
)
