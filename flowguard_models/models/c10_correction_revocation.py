"""C10 Correction, Invalidation, Original-Owner Recompute, and Recovery model."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C10_correction_revocation",
    title="C10 Correction, Invalidation & Recompute",
    modeled_boundary=(
        "append-only correction/revocation/deletion, dependency-graph "
        "invalidation, original-owner dispatch, terminal join, retry, restart, "
        "material-clue/summary/activity/supplemental-information invalidation, "
        "source-locator and derived-understanding repair, SourceGroup, "
        "SituationGraph, Situation/World Model and generated-hero invalidation, "
        "and old and new ancestor-"
        "chain invalidation for containment, child-state, split, merge, and "
        "reparent revisions"
    ),
    state_fields=(
        "revision_graph",
        "invalidation_plan",
        "recompute_request",
        "recompute.owner_dispositions",
        "recompute.join_status",
        "recompute.checkpoint",
        "invalidation.ancestor_chain_dispositions",
        "revision.hierarchy_dispositions",
        "invalidation.material_clue_dispositions",
        "invalidation.observation_time_dispositions",
        "invalidation.hero_disposition",
        "invalidation.supplemental_information_disposition",
        "correction.source_locator_invalidation",
        "correction.derived_understanding_invalidation",
        "correction.source_group_invalidation",
        "correction.situation_graph_invalidation",
        "correction.world_model_invalidation",
        "correction.generated_hero_invalidation",
    ),
    owned_write_fields=(
        "revision_graph",
        "invalidation_plan",
        "recompute_request",
        "recompute.owner_dispositions",
        "recompute.join_status",
        "recompute.checkpoint",
        "invalidation.ancestor_chain_dispositions",
        "revision.hierarchy_dispositions",
        "invalidation.material_clue_dispositions",
        "invalidation.observation_time_dispositions",
        "invalidation.hero_disposition",
        "invalidation.supplemental_information_disposition",
        "correction.source_locator_invalidation",
        "correction.derived_understanding_invalidation",
        "correction.source_group_invalidation",
        "correction.situation_graph_invalidation",
        "correction.world_model_invalidation",
        "correction.generated_hero_invalidation",
    ),
    side_effect_classes=(
        "append_revision",
        "dispatch_recompute_request",
        "append_owner_disposition",
        "append_recompute_checkpoint",
    ),
    completion_evidence=(
        "RevisionGraph",
        "InvalidationPlan",
        "RecomputeRequest",
        "DependentDisposition",
        "OwnerTerminalSet",
        "RecomputeJoinCurrent",
        "RecomputeBlocked",
        "RecoveryCheckpoint",
        "AncestorInvalidationPlan",
        "OldAncestorChainInvalidated",
        "NewAncestorChainInvalidated",
        "HierarchyRecomputeRequest",
        "HierarchyRevisionDisposition",
        "MaterialClueInvalidationPlan",
        "ObservationTimeCorrectionPlan",
        "HeroRetained",
        "HeroInvalidated",
        "SupplementalInformationInvalidated",
        "SourceLocatorRevalidated",
        "DerivedUnderstandingInvalidated",
        "SourceGroupInvalidated",
        "SituationGraphInvalidated",
        "WorldModelInvalidated",
    ),
    rules=(
        CaseRule(
            case_id="source_locator_or_fingerprint_changed",
            decision="source_derived_graph_and_world_dependents_invalidated",
            label="source_derived_graph_and_world_dependents_invalidated",
            writes=(
                "revision_graph",
                "invalidation_plan",
                "recompute_request",
                "correction.source_locator_invalidation",
                "correction.derived_understanding_invalidation",
                "correction.source_group_invalidation",
                "correction.situation_graph_invalidation",
                "correction.world_model_invalidation",
                "correction.generated_hero_invalidation",
            ),
            side_effects=("append_revision", "dispatch_recompute_request"),
            emitted_tokens=(
                "SourceLocatorRevalidated",
                "DerivedUnderstandingInvalidated",
                "SourceGroupInvalidated",
                "SituationGraphInvalidated",
                "WorldModelInvalidated",
            ),
            reason=(
                "a moved, modified, deleted, revoked, or reauthorized original "
                "invalidates only the exact dependent derived understanding, "
                "group membership, graph nodes and edges, advisory inference, "
                "and root Hero brief before original owners recompute them"
            ),
        ),
        CaseRule(
            case_id="future_due_activity_observation_corrected",
            decision="exact_activity_dependents_invalidated_and_recomputed",
            label="exact_activity_dependents_invalidated_and_recomputed",
            writes=(
                "revision_graph",
                "invalidation_plan",
                "recompute_request",
                "recompute.checkpoint",
                "invalidation.ancestor_chain_dispositions",
                "invalidation.material_clue_dispositions",
                "invalidation.observation_time_dispositions",
            ),
            side_effects=(
                "append_revision",
                "dispatch_recompute_request",
                "append_owner_disposition",
                "append_recompute_checkpoint",
            ),
            emitted_tokens=(
                "RevisionGraph",
                "ObservationTimeCorrectionPlan",
                "MaterialClueInvalidationPlan",
                "OldAncestorChainInvalidated",
                "NewAncestorChainInvalidated",
                "RecoveryCheckpoint",
            ),
            reason=(
                "C5's exact historical observation-time correction supersedes "
                "only the erroneous activity clue, invalidates its Matter, old "
                "and current ancestor activity projections, and any late-bound "
                "canonical Matter before original-owner recompute"
            ),
        ),
        CaseRule(
            case_id="user_correction",
            decision="correction_appended_and_recompute_requested",
            label="correction_appended",
            writes=("revision_graph", "invalidation_plan", "recompute_request", "recompute.checkpoint"),
            side_effects=("append_revision", "dispatch_recompute_request", "append_recompute_checkpoint"),
            emitted_tokens=("RevisionGraph", "InvalidationPlan", "RecomputeRequest", "RecoveryCheckpoint"),
            reason="correction preserves history and dispatches affected original owners",
        ),
        CaseRule(
            case_id="source_or_tracking_stale",
            decision="all_dependents_disposed",
            label="all_dependents_disposed",
            writes=("invalidation_plan", "recompute_request", "recompute.owner_dispositions"),
            side_effects=("dispatch_recompute_request", "append_owner_disposition"),
            emitted_tokens=("InvalidationPlan", "DependentDisposition", "RecomputeRequest"),
            reason="every exact dependent receives recompute, remove, retain, review, or blocked disposition",
        ),
        CaseRule(
            case_id="all_required_owners_terminal",
            decision="recompute_join_current",
            label="recompute_join_current",
            writes=("recompute.owner_dispositions", "recompute.join_status", "recompute.checkpoint"),
            side_effects=("append_owner_disposition", "append_recompute_checkpoint"),
            emitted_tokens=("OwnerTerminalSet", "RecomputeJoinCurrent", "RecoveryCheckpoint"),
            reason="every dependency-graph owner is terminal for the same input revision",
        ),
        CaseRule(
            case_id="required_owner_failed_or_missing",
            decision="recompute_join_blocked",
            label="recompute_join_blocked",
            writes=("recompute.owner_dispositions", "recompute.join_status", "recompute.checkpoint"),
            side_effects=("append_owner_disposition", "append_recompute_checkpoint"),
            emitted_tokens=("RecomputeBlocked", "RecoveryCheckpoint"),
            reason="failed, stale, or missing owner disposition blocks fresh projection",
        ),
        CaseRule(
            case_id="restart_with_current_checkpoint",
            decision="recompute_resumed",
            label="recompute_resumed",
            writes=("recompute_request", "recompute.checkpoint"),
            side_effects=("dispatch_recompute_request", "append_recompute_checkpoint"),
            emitted_tokens=("RecomputeRequest", "RecoveryCheckpoint"),
            reason="restart resumes only missing owners after authorization and freshness revalidation",
        ),
        CaseRule(
            case_id="authorization_revoked",
            decision="revocation_appended_and_dependents_invalidated",
            label="revocation_appended",
            writes=("revision_graph", "invalidation_plan", "recompute_request", "recompute.checkpoint"),
            side_effects=("append_revision", "dispatch_recompute_request", "append_recompute_checkpoint"),
            emitted_tokens=("Revoked", "InvalidationPlan", "RecomputeRequest", "RecoveryCheckpoint"),
            reason="revocation stops reads and invalidates derived state",
        ),
        CaseRule(
            case_id="ui_only_patch_request",
            decision="ui_only_patch_rejected",
            label="ui_only_patch_rejected",
            emitted_tokens=("CorrectionRejected",),
            reason="correction cannot change only the projection",
        ),
        CaseRule(
            case_id="direct_foreign_state_write",
            decision="foreign_state_write_rejected",
            label="foreign_state_write_rejected",
            emitted_tokens=("OwnerWriteRejected",),
            reason="C10 requests recompute and never writes another owner field",
        ),
        CaseRule(
            case_id="child_state_or_containment_changed",
            decision="both_ancestor_chains_invalidated",
            label="both_ancestor_chains_invalidated",
            writes=(
                "invalidation_plan",
                "recompute_request",
                "recompute.checkpoint",
                "invalidation.ancestor_chain_dispositions",
            ),
            side_effects=(
                "dispatch_recompute_request",
                "append_owner_disposition",
                "append_recompute_checkpoint",
            ),
            emitted_tokens=(
                "InvalidationPlan",
                "AncestorInvalidationPlan",
                "OldAncestorChainInvalidated",
                "NewAncestorChainInvalidated",
                "HierarchyRecomputeRequest",
                "RecoveryCheckpoint",
            ),
            reason=(
                "a child state, outcome, blocker, role, or containment revision "
                "invalidates the child, every old ancestor, every new ancestor, "
                "their rollups, and C12 hierarchy projections before owner recompute"
            ),
        ),
        CaseRule(
            case_id="material_clue_or_nonmaterial_processing_changed",
            decision="clue_summary_activity_dependents_disposed",
            label="clue_summary_activity_dependents_disposed",
            writes=(
                "invalidation_plan",
                "recompute_request",
                "recompute.checkpoint",
                "invalidation.ancestor_chain_dispositions",
                "invalidation.material_clue_dispositions",
                "invalidation.hero_disposition",
                "invalidation.supplemental_information_disposition",
            ),
            side_effects=(
                "dispatch_recompute_request",
                "append_owner_disposition",
                "append_recompute_checkpoint",
            ),
            emitted_tokens=(
                "InvalidationPlan",
                "MaterialClueInvalidationPlan",
                "HierarchyRecomputeRequest",
                "HeroRetained",
                "SupplementalInformationInvalidated",
                "RecoveryCheckpoint",
            ),
            reason=(
                "material clues invalidate bilingual summary and activity order "
                "for the Matter and ancestors plus dependent AI supplemental "
                "information; nonmaterial processing does not; "
                "a stable hero remains current unless identity, theme, merge/"
                "split/reparent, permission, safety, or explicit correction changes"
            ),
        ),
        CaseRule(
            case_id="hero_identity_theme_or_policy_dependency_changed",
            decision="generated_hero_invalidated_for_exact_dependency",
            label="generated_hero_invalidated_for_exact_dependency",
            writes=(
                "invalidation_plan",
                "recompute_request",
                "recompute.checkpoint",
                "invalidation.hero_disposition",
            ),
            side_effects=(
                "dispatch_recompute_request",
                "append_owner_disposition",
                "append_recompute_checkpoint",
            ),
            emitted_tokens=(
                "InvalidationPlan",
                "HeroInvalidated",
                "RecomputeRequest",
                "RecoveryCheckpoint",
            ),
            reason=(
                "only Matter identity, topic/theme, merge, split, reparent, "
                "permission, safety, policy, or explicit correction invalidates "
                "the current generated hero and schedules one replacement; an "
                "ordinary clue, summary, locale, density, scan, or retry does not"
            ),
        ),
        CaseRule(
            case_id="hierarchy_split_revision",
            decision="split_dispositions_appended",
            label="split_dispositions_appended",
            writes=(
                "revision_graph",
                "invalidation_plan",
                "recompute_request",
                "revision.hierarchy_dispositions",
            ),
            side_effects=("append_revision", "dispatch_recompute_request"),
            emitted_tokens=(
                "RevisionGraph",
                "InvalidationPlan",
                "HierarchyRecomputeRequest",
                "HierarchyRevisionDisposition",
            ),
            reason=(
                "a split preserves original identity and records one explicit "
                "retain/move/copy-with-provenance/review disposition for every "
                "source, Event, WorkItem, child, and open loop"
            ),
        ),
        CaseRule(
            case_id="hierarchy_merge_revision",
            decision="merge_dispositions_appended",
            label="merge_dispositions_appended",
            writes=(
                "revision_graph",
                "invalidation_plan",
                "recompute_request",
                "revision.hierarchy_dispositions",
            ),
            side_effects=("append_revision", "dispatch_recompute_request"),
            emitted_tokens=(
                "RevisionGraph",
                "InvalidationPlan",
                "HierarchyRecomputeRequest",
                "HierarchyRevisionDisposition",
            ),
            reason=(
                "a merge preserves both prior Matter identities, evidence, and "
                "history while appending a current canonical disposition and redirects"
            ),
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-C10-017-observation-correction-leaves-canonical-stale",
            protected_error_class="observation_time_correction_propagation_gap",
            description=(
                "the source Matter is corrected but one ancestor or late-bound "
                "canonical Matter retains the superseded future due activity"
            ),
            protected_harm=(
                "catalog ordering remains contradictory after a successful "
                "correction"
            ),
            case_id="future_due_activity_observation_corrected",
            broken_decision="source_activity_only_recomputed",
            broken_writes=(
                "invalidation.ancestor_chain_dispositions",
                "invalidation.observation_time_dispositions",
            ),
            broken_side_effects=("append_owner_disposition",),
            broken_tokens=("ObservationTimeCorrectionPlan",),
        ),
        HazardSpec(
            failure_id="H-C10-001-correction-overwrites-history",
            protected_error_class="revision_history_loss",
            description="a correction overwrites the prior canonical revision",
            protected_harm="the user cannot reconstruct why an earlier decision was visible",
            case_id="user_correction",
            broken_decision="correction_overwritten",
            broken_writes=("revision_graph",),
            broken_side_effects=("append_revision",),
            broken_tokens=("CurrentRevisionOnly",),
        ),
        HazardSpec(
            failure_id="H-C10-002-dependent-omitted",
            protected_error_class="invalidation_propagation_gap",
            description="one dependency-graph owner receives no disposition",
            protected_harm="stale evidence or projections remain current",
            case_id="source_or_tracking_stale",
            broken_decision="partial_dependents_disposed",
            broken_writes=("invalidation_plan", "recompute.owner_dispositions"),
            broken_side_effects=("append_owner_disposition",),
            broken_tokens=("DependentDisposition",),
        ),
        HazardSpec(
            failure_id="H-C10-003-early-join",
            protected_error_class="nonterminal_owner_join",
            description="recompute is declared current with a missing or failed owner",
            protected_harm="C12 publishes a fresh-looking projection over stale dependencies",
            case_id="required_owner_failed_or_missing",
            broken_decision="recompute_join_current",
            broken_writes=("recompute.join_status",),
            broken_tokens=("RecomputeJoinCurrent",),
        ),
        HazardSpec(
            failure_id="H-C10-004-restart-duplicates-owner-work",
            protected_error_class="recompute_retry_duplication",
            description="restart redispatches already terminal owners and duplicates revisions",
            protected_harm="correction history and projections diverge after recovery",
            case_id="restart_with_current_checkpoint",
            broken_decision="recompute_resumed",
            broken_writes=("recompute_request", "recompute.checkpoint"),
            broken_side_effects=("dispatch_recompute_request", "append_recompute_checkpoint"),
            broken_tokens=("RecomputeRequest", "RecoveryCheckpoint"),
            ignore_idempotency=True,
        ),
        HazardSpec(
            failure_id="H-C10-005-ui-only-correction",
            protected_error_class="projection_only_correction",
            description="a user correction changes only the UI",
            protected_harm="the canonical decision and other projections remain wrong",
            case_id="ui_only_patch_request",
            broken_decision="ui_projection_patched",
            broken_tokens=("ProjectionUpdated",),
        ),
        HazardSpec(
            failure_id="H-C10-007-material-clue-omits-ancestor-summary",
            protected_error_class="material_clue_ancestor_invalidation_gap",
            description="a material child clue updates only the child projection",
            protected_harm="parent summaries and activity order stay stale despite real progress",
            case_id="material_clue_or_nonmaterial_processing_changed",
            broken_decision="child_only_clue_invalidated",
            broken_writes=(
                "invalidation.material_clue_dispositions",
                "invalidation.ancestor_chain_dispositions",
            ),
            broken_side_effects=("dispatch_recompute_request",),
            broken_tokens=("MaterialClueInvalidationPlan",),
        ),
        HazardSpec(
            failure_id="H-C10-006-c10-writes-child-state",
            protected_error_class="foreign_writer_escape",
            description="C10 directly writes another owner canonical field",
            protected_harm="correction coordination becomes a second authority",
            case_id="direct_foreign_state_write",
            broken_decision="lifecycle_state_written",
            broken_writes=("matter.lifecycle_axes",),
            broken_tokens=("LifecycleState",),
        ),
        HazardSpec(
            failure_id="H-C10-008-old-parent-chain-remains-current",
            protected_error_class="reparent_old_ancestor_invalidation_gap",
            description="reparent invalidates the new chain but leaves the old parent chain current",
            protected_harm="the child continues to affect two ancestor projections after reparenting",
            case_id="child_state_or_containment_changed",
            broken_decision="new_ancestor_chain_only_invalidated",
            broken_writes=(
                "invalidation_plan",
                "invalidation.ancestor_chain_dispositions",
            ),
            broken_side_effects=("dispatch_recompute_request",),
            broken_tokens=("NewAncestorChainInvalidated",),
        ),
        HazardSpec(
            failure_id="H-C10-009-split-duplicates-membership-silently",
            protected_error_class="split_membership_duplication",
            description="split duplicates source, Event, or WorkItem membership without dispositions",
            protected_harm="evidence and activity appear twice without auditable provenance",
            case_id="hierarchy_split_revision",
            broken_decision="split_membership_copied",
            broken_writes=("revision_graph", "revision.hierarchy_dispositions"),
            broken_side_effects=("append_revision",),
            broken_tokens=("HierarchyRevisionDisposition",),
        ),
        HazardSpec(
            failure_id="H-C10-010-merge-erases-history",
            protected_error_class="merge_identity_history_loss",
            description="merge deletes prior Matter identities, evidence, or revision history",
            protected_harm="the user cannot reconstruct earlier cards or why they were merged",
            case_id="hierarchy_merge_revision",
            broken_decision="merged_history_overwritten",
            broken_writes=("revision_graph", "revision.hierarchy_dispositions"),
            broken_side_effects=("append_revision",),
            broken_tokens=("CurrentRevisionOnly",),
        ),
        HazardSpec(
            failure_id="H-C10-011-ordinary-clue-invalidates-generated-hero",
            protected_error_class="generated_hero_overinvalidation",
            description="an ordinary material clue, summary, locale, density, scan, or retry invalidates the hero",
            protected_harm="stable Matter recognition churns and unnecessary image generation repeats",
            case_id="material_clue_or_nonmaterial_processing_changed",
            broken_decision="generated_hero_invalidated_for_exact_dependency",
            broken_writes=("invalidation.hero_disposition",),
            broken_side_effects=("dispatch_recompute_request",),
            broken_tokens=("HeroInvalidated",),
        ),
        HazardSpec(
            failure_id="H-C10-012-hero-dependency-change-retains-stale-artifact",
            protected_error_class="generated_hero_underinvalidation",
            description="identity, theme, hierarchy, permission, safety, policy, or correction changes but the hero remains current",
            protected_harm="the card keeps art for the wrong or no-longer-authorized Matter meaning",
            case_id="hero_identity_theme_or_policy_dependency_changed",
            broken_decision="hero_retained",
            broken_writes=("invalidation.hero_disposition",),
            broken_tokens=("HeroRetained",),
        ),
    ),
    risk_classes=(
        "state_transition",
        "ownership",
        "idempotency",
        "freshness",
        "recovery",
        "side_effect",
    ),
    template_ids=("side_effect_at_most_once",),
    blindspots=(
        "dependency and ancestor-chain graph construction requires implementation conformance",
        "real owner executors and durable restart require runtime evidence",
        "physical deletion and retention policy remain separate",
    ),
    claim_boundary=(
        "This model establishes bounded C10 append-only history, exact "
        "invalidation, old/new ancestor-chain propagation, split/merge disposition, "
        "original-owner terminal joins, retry, restart, and foreign-writer "
        "rejection. It does not prove the production dependency graph, durable "
        "execution, or C12 publication conformance."
    ),
)
