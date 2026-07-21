"""C8 Open Loop / Waiting / Blocking finite FlowGuard model declaration."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C8_open_loop_waiting_blocking",
    title="C8 Open Loop / Waiting / Blocking",
    modeled_boundary=(
        "requests, wait targets, closure conditions, partial/full blocking, and "
        "required/optional/critical child blocking rollup"
    ),
    state_fields=(
        "open_loop.identity",
        "open_loop.semantic_role_identity",
        "open_loop.supersession",
        "open_loop.wait_target",
        "open_loop.closure_condition",
        "matter.blocking_axis",
        "matter.child_blocking_summary",
        "matter.ancestor_blocking_rollup",
    ),
    owned_write_fields=(
        "open_loop.identity",
        "open_loop.semantic_role_identity",
        "open_loop.supersession",
        "open_loop.wait_target",
        "open_loop.closure_condition",
        "matter.blocking_axis",
        "matter.child_blocking_summary",
        "matter.ancestor_blocking_rollup",
    ),
    side_effect_classes=("open_loop_registry_write",),
    completion_evidence=(
        "OpenLoop",
        "Waiting",
        "PartialBlock",
        "FullBlock",
        "LoopClosed",
        "OpenLoopGap",
        "ChildBlockingCurrent",
        "AncestorBlockingRollupCurrent",
        "SemanticOpenLoopIdentityCurrent",
    ),
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
            case_id="same_semantic_open_loop_role_reanalyzed",
            decision="one_open_loop_identity_reused_or_exactly_superseded",
            label="one_open_loop_identity_reused_or_exactly_superseded",
            writes=(
                "open_loop.identity",
                "open_loop.semantic_role_identity",
                "open_loop.supersession",
            ),
            side_effects=("open_loop_registry_write",),
            emitted_tokens=("SemanticOpenLoopIdentityCurrent",),
            reason=(
                "one language-neutral waiting role is unique within its "
                "Matter; reanalysis reuses it or retires only exact named "
                "legacy duplicates while preserving append-only history"
            ),
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
            writes=(
                "matter.blocking_axis",
                "matter.child_blocking_summary",
                "matter.ancestor_blocking_rollup",
            ),
            side_effects=("open_loop_registry_write",),
            emitted_tokens=(
                "PartialBlock",
                "ChildBlockingCurrent",
                "AncestorBlockingRollupCurrent",
            ),
            reason=(
                "a required but noncritical child blocks only the affected branch "
                "while another licensed parent progress path remains"
            ),
        ),
        CaseRule(
            case_id="critical_dependency_failure",
            decision="full_block",
            label="full_block",
            writes=(
                "matter.blocking_axis",
                "matter.child_blocking_summary",
                "matter.ancestor_blocking_rollup",
            ),
            side_effects=("open_loop_registry_write",),
            emitted_tokens=(
                "FullBlock",
                "ChildBlockingCurrent",
                "AncestorBlockingRollupCurrent",
            ),
            reason=(
                "a critical child fully blocks the parent only when current "
                "evidence shows every valid parent progress path depends on it"
            ),
        ),
        CaseRule(
            case_id="optional_child_blocked",
            decision="optional_child_block_visible_parent_unblocked",
            label="optional_child_block_visible_parent_unblocked",
            writes=(
                "matter.child_blocking_summary",
                "matter.ancestor_blocking_rollup",
            ),
            side_effects=("open_loop_registry_write",),
            emitted_tokens=("ChildBlockingCurrent", "AncestorBlockingRollupCurrent"),
            reason=(
                "an optional child remains visibly blocked without changing the "
                "parent blocking axis"
            ),
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
        HazardSpec(
            failure_id="H-C8-005-optional-child-fully-blocks-parent",
            protected_error_class="optional_child_blocking_scope_expansion",
            description="an optional child marks the whole parent Matter fully blocked",
            protected_harm="nonessential work hides valid progress on the parent",
            case_id="optional_child_blocked",
            broken_decision="full_block",
            broken_writes=("matter.blocking_axis", "matter.ancestor_blocking_rollup"),
            broken_side_effects=("open_loop_registry_write",),
            broken_tokens=("FullBlock",),
        ),
        HazardSpec(
            failure_id="H-C8-006-same-semantic-role-duplicates-open-loop",
            protected_error_class="open_loop_semantic_identity_duplication",
            description=(
                "a repeated submission-receipt wait creates another active "
                "loop or retires an unlisted loop by title similarity"
            ),
            protected_harm=(
                "the user sees duplicate outstanding waits or loses a valid "
                "independent closure obligation"
            ),
            case_id="same_semantic_open_loop_role_reanalyzed",
            broken_decision="duplicate_loop_or_heuristic_replacement",
            broken_writes=(
                "open_loop.identity",
                "open_loop.semantic_role_identity",
                "open_loop.supersession",
            ),
            broken_side_effects=("open_loop_registry_write",),
            broken_tokens=("OpenLoop",),
        ),
    ),
    risk_classes=("state_transition", "liveness", "ownership", "side_effect"),
    template_no_match_reason=(
        "The Phase A template search returned no wait-target and partial/full blocking template."
    ),
    blindspots=(
        "child-role criticality policy and valid parent progress-path calculation require later design evidence",
        "human follow-up timing and notification behavior are outside this child",
    ),
    claim_boundary=(
        "This receipt can establish C8 abstract wait, closure, stable semantic "
        "open-loop identity, exact supersession, child-role, and blocking-scope "
        "rollup hazards. It does not establish real dependency "
        "criticality, notification delivery, hierarchy completeness, or parent liveness."
    ),
)
