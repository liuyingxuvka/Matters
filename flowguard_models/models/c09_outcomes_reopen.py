"""C9 Completion / Cancellation / Reopen finite FlowGuard model declaration."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C9_completion_cancellation_reopen",
    title="C9 Completion / Cancellation / Reopen",
    modeled_boundary=(
        "explicit completion and termination criteria, independent-loop "
        "disposition, reopening, and non-mechanical child-outcome rollup"
    ),
    state_fields=(
        "matter.outcome",
        "matter.outcome_criteria",
        "matter.reopen_revision",
        "matter.child_outcome_summary",
        "matter.ancestor_outcome_rollup",
    ),
    owned_write_fields=(
        "matter.outcome",
        "matter.outcome_criteria",
        "matter.reopen_revision",
        "matter.child_outcome_summary",
        "matter.ancestor_outcome_rollup",
    ),
    side_effect_classes=("outcome_registry_write",),
    completion_evidence=(
        "Completed",
        "Cancelled",
        "Abandoned",
        "Reopened",
        "CompletionGap",
        "CompletionUnproven",
        "OutcomeConflict",
        "OutcomeUncertainty",
        "ChildOutcomeCurrent",
        "AncestorOutcomeRollupCurrent",
        "ParentCompletionUnproven",
    ),
    rules=(
        CaseRule(
            case_id="all_completion_criteria_evidenced",
            decision="completed",
            label="completed",
            writes=("matter.outcome", "matter.outcome_criteria"),
            side_effects=("outcome_registry_write",),
            emitted_tokens=("Completed", "CompletionEvidence"),
            reason="every declared completion criterion has current licensed evidence",
        ),
        CaseRule(
            case_id="terminal_label_or_final_file_only",
            decision="completion_unproven",
            label="completion_unproven",
            writes=("matter.outcome_criteria",),
            side_effects=("outcome_registry_write",),
            emitted_tokens=("CompletionGap", "CompletionUnproven"),
            reason="filename, meeting end, provider Done, or AI language cannot alone prove completion",
        ),
        CaseRule(
            case_id="user_cancels_with_open_loop",
            decision="cancelled_with_loop_disposition",
            label="cancelled_with_loop_disposition",
            writes=("matter.outcome", "matter.outcome_criteria"),
            side_effects=("outcome_registry_write",),
            emitted_tokens=("Cancelled", "OpenLoopDispositionRequired"),
            reason="user cancellation is recorded and independent loops require separate disposition",
        ),
        CaseRule(
            case_id="new_obligation_after_completion",
            decision="reopened",
            label="reopened",
            writes=("matter.outcome", "matter.outcome_criteria", "matter.reopen_revision"),
            side_effects=("outcome_registry_write",),
            emitted_tokens=("Reopened", "NewObligation"),
            reason="a new in-boundary obligation reopens while preserving prior completion",
        ),
        CaseRule(
            case_id="source_revision_or_ai_reopen_proposal",
            decision="reopen_not_licensed",
            label="reopen_not_licensed",
            writes=("matter.outcome_criteria",),
            side_effects=("outcome_registry_write",),
            emitted_tokens=("OutcomeConflict", "CompletionUnproven"),
            reason=(
                "a source revision or AI proposal does not reopen without current "
                "obligation evidence; uncertainty remains visible"
            ),
        ),
        CaseRule(
            case_id="conflicting_termination_evidence",
            decision="outcome_conflict_preserved",
            label="outcome_conflict_preserved",
            writes=("matter.outcome_criteria",),
            side_effects=("outcome_registry_write",),
            emitted_tokens=("OutcomeConflict", "OutcomeUncertainty"),
            reason=(
                "material conflict prevents a certain terminal outcome while "
                "preserving the current best autonomous disposition"
            ),
        ),
        CaseRule(
            case_id="all_known_children_completed_parent_criteria_unmet",
            decision="parent_completion_unproven",
            label="parent_completion_unproven",
            writes=(
                "matter.outcome_criteria",
                "matter.child_outcome_summary",
                "matter.ancestor_outcome_rollup",
            ),
            side_effects=("outcome_registry_write",),
            emitted_tokens=(
                "CompletionUnproven",
                "ChildOutcomeCurrent",
                "AncestorOutcomeRollupCurrent",
                "ParentCompletionUnproven",
            ),
            reason=(
                "all currently known children may be complete while parent-level "
                "criteria, unknown depth, independent loops, or direct obligations "
                "remain; child outcomes update the summary but never complete the parent"
            ),
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-C9-001-false-completion-proof",
            protected_error_class="premature_completion",
            description="filename, meeting end, provider Done, or AI language alone marks the Matter completed",
            protected_harm="the system hides unfinished obligations and misreports the outcome",
            case_id="terminal_label_or_final_file_only",
            broken_decision="completed",
            broken_writes=("matter.outcome", "matter.outcome_criteria"),
            broken_side_effects=("outcome_registry_write",),
            broken_tokens=("Completed",),
        ),
        HazardSpec(
            failure_id="H-C9-002-cancellation-silently-closes-loops",
            protected_error_class="independent_loop_silent_closure",
            description="user cancellation silently closes independent OpenLoops",
            protected_harm="outstanding requests disappear without their own disposition",
            case_id="user_cancels_with_open_loop",
            broken_decision="cancelled_all_closed",
            broken_writes=("matter.outcome", "matter.outcome_criteria"),
            broken_side_effects=("outcome_registry_write",),
            broken_tokens=("Cancelled", "AllLoopsClosed"),
        ),
        HazardSpec(
            failure_id="H-C9-003-new-obligation-does-not-reopen",
            protected_error_class="stale_terminal_outcome",
            description="a new in-boundary obligation leaves a completed outcome unchanged",
            protected_harm="current responsibilities are hidden behind an obsolete terminal state",
            case_id="new_obligation_after_completion",
            broken_decision="completed_no_delta",
            broken_writes=("matter.outcome",),
            broken_side_effects=("outcome_registry_write",),
            broken_tokens=("Completed",),
        ),
        HazardSpec(
            failure_id="H-C9-004-conflict-silently-terminates",
            protected_error_class="outcome_conflict_bypass",
            description="conflicting termination evidence is collapsed into a certain outcome",
            protected_harm="a disputed outcome is presented as certain and contrary evidence disappears",
            case_id="conflicting_termination_evidence",
            broken_decision="completed",
            broken_writes=("matter.outcome", "matter.outcome_criteria"),
            broken_side_effects=("outcome_registry_write",),
            broken_tokens=("Completed",),
        ),
        HazardSpec(
            failure_id="H-C9-005-ai-reopens-without-obligation",
            protected_error_class="advisory_reopen_authority_escape",
            description="an advisory proposal reopens a completed Matter without current obligation evidence",
            protected_harm="forecast or interpretation is presented as a current responsibility",
            case_id="source_revision_or_ai_reopen_proposal",
            broken_decision="reopened",
            broken_writes=("matter.outcome", "matter.outcome_criteria", "matter.reopen_revision"),
            broken_side_effects=("outcome_registry_write",),
            broken_tokens=("Reopened", "NewObligation"),
        ),
        HazardSpec(
            failure_id="H-C9-006-all-children-mechanically-complete-parent",
            protected_error_class="child_parent_completion_conflation",
            description="all known child Matters completed mechanically completes the parent",
            protected_harm=(
                "parent criteria, independent obligations, and unmodeled depth "
                "are silently discarded"
            ),
            case_id="all_known_children_completed_parent_criteria_unmet",
            broken_decision="completed",
            broken_writes=("matter.outcome", "matter.outcome_criteria"),
            broken_side_effects=("outcome_registry_write",),
            broken_tokens=("Completed",),
        ),
    ),
    risk_classes=("completion", "state_transition", "evidence", "side_effect"),
    template_ids=("completion_requires_evidence", "side_effect_at_most_once"),
    blindspots=(
        "the exact parent and child completion criteria for each Matter require user or domain policy",
        "OpenLoop disposition conformance belongs to C8 and parent alignment",
    ),
    claim_boundary=(
        "This receipt can establish C9 abstract completion-evidence, cancellation, "
        "reopen, conflict, and child/parent completion-separation hazards. It does "
        "not establish Matter-specific criteria, hierarchy completeness, C8 loop "
        "closure, or production outcomes."
    ),
)
