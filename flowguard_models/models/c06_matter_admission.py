"""C6 Matter Formation & Admission finite FlowGuard model declaration."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C6_matter_formation_admission",
    title="C6 Matter Formation & Admission",
    modeled_boundary=(
        "source-first Matter formation, autonomous admitted/source-only/"
        "not-applicable/uncertain/blocked outcomes, context-aware semantic "
        "reconciliation, Matter-source gallery relations, admitted statistics, "
        "and recursive broad-root/child-Matter/WorkItem/Event/Source "
        "classification with one acyclic primary-parent containment edge and "
        "required/optional/critical role semantics, plus one bounded internal "
        "SituationGraph and one ordinary UI MatterHierarchyProjection whose "
        "nodes are admitted Matters only, with primary containment and typed "
        "Matter-to-Matter secondary edges"
    ),
    state_fields=(
        "matter.identity",
        "matter.admitted_matter_id_authority",
        "matter.admission_status",
        "matter.rationale",
        "matter.membership",
        "matter.source_revision_reconciliation_status",
        "matter.source_revision_target_identity",
        "matter.current_evidence_membership",
        "matter.source_relation",
        "matter.object_kind",
        "matter.primary_parent",
        "matter.containment_role",
        "matter.hierarchy_revision",
        "matter.hierarchy_depth_status",
        "matter.hierarchy_batch_status",
        "matter.hierarchy_publication_request",
        "matter.reconciliation_context",
        "matter.merge_disposition",
        "matter.canonicalization_disposition",
        "matter.canonical_matter_id",
        "matter.canonicalization_materialization",
        "matter.canonicalization_evidence",
        "matter.parent_composition_transaction_status",
        "matter.parent_narrative_scope_revision",
        "matter.parent_narrative_child_projection_revisions",
        "matter.parent_narrative_evidence_revisions",
        "matter.root_granularity",
        "work_item.membership",
        "matter.situation_graph_revision",
        "matter.situation_graph_primary_edges",
        "matter.situation_graph_secondary_edges",
        "matter.situation_graph_continuation",
        "matter.ui_hierarchy_projection_revision",
        "matter.ui_hierarchy_matter_ids",
        "matter.ui_hierarchy_secondary_edges",
    ),
    owned_write_fields=(
        "matter.identity",
        "matter.admitted_matter_id_authority",
        "matter.admission_status",
        "matter.rationale",
        "matter.membership",
        "matter.source_revision_reconciliation_status",
        "matter.source_revision_target_identity",
        "matter.current_evidence_membership",
        "matter.source_relation",
        "matter.object_kind",
        "matter.primary_parent",
        "matter.containment_role",
        "matter.hierarchy_revision",
        "matter.hierarchy_depth_status",
        "matter.hierarchy_batch_status",
        "matter.hierarchy_publication_request",
        "matter.reconciliation_context",
        "matter.merge_disposition",
        "matter.canonicalization_disposition",
        "matter.canonical_matter_id",
        "matter.canonicalization_materialization",
        "matter.canonicalization_evidence",
        "matter.parent_composition_transaction_status",
        "matter.parent_narrative_scope_revision",
        "matter.parent_narrative_child_projection_revisions",
        "matter.parent_narrative_evidence_revisions",
        "matter.root_granularity",
        "work_item.membership",
        "matter.situation_graph_revision",
        "matter.situation_graph_primary_edges",
        "matter.situation_graph_secondary_edges",
        "matter.situation_graph_continuation",
        "matter.ui_hierarchy_projection_revision",
        "matter.ui_hierarchy_matter_ids",
        "matter.ui_hierarchy_secondary_edges",
    ),
    side_effect_classes=(
        "matter_registry_write",
        "hierarchy_batch_write",
        "parent_composition_transaction_write",
        "canonicalization_transaction_write",
        "situation_graph_projection_write",
    ),
    completion_evidence=(
        "SourceOnly",
        "MatterCandidate",
        "AdmittedMatter",
        "MatterUncertain",
        "NotApplicable",
        "MatterSourceRelation",
        "AccessBlocked",
        "HierarchyDecision",
        "RootMatter",
        "ChildMatter",
        "WorkItem",
        "EventOnly",
        "ContainmentCurrent",
        "RelatedMatterOnly",
        "HierarchyConflict",
        "HierarchyDepthPending",
        "HierarchyRevision",
        "HierarchyBatchCommitted",
        "HierarchyPublicationRecovered",
        "SplitMergeDisposition",
        "ContextReconciliationDecision",
        "GlobalCandidateRecallComplete",
        "BroadRootMatter",
        "WeakContextNoMerge",
        "ParentCompositionAtomic",
        "MatterCanonicalization",
        "CanonicalMatterProjectionOnly",
        "CandidateSourceOnlyRetained",
        "SituationGraph",
        "SituationGraphPrimaryEdge",
        "SituationGraphSecondaryEdge",
        "SituationGraphContinuation",
        "ParentNarrativeScopeCurrent",
        "CanonicalMatterIdentityCurrent",
        "CanonicalMatterIdentityRejected",
        "MatterOnlyHierarchyProjection",
        "CrossDomainMatterRelation",
        "TravelHierarchyReconciled",
        "SoftwarePortfolioHierarchyReconciled",
        "MatterSourceRevisionCurrent",
        "MatterSourceRevisionAnalysisRequired",
        "MatterSourceRevisionTargetAdopted",
        "SourceRevisionStalePackageRejected",
        "SourceRevisionCurrentSuccessorRequired",
        "OldRevisionEvidenceRetired",
    ),
    rules=(
        CaseRule(
            case_id="root_matter_situation_graph_requested",
            decision="bounded_situation_graph_current",
            label="bounded_situation_graph_current",
            writes=(
                "matter.situation_graph_revision",
                "matter.situation_graph_primary_edges",
                "matter.situation_graph_secondary_edges",
                "matter.situation_graph_continuation",
            ),
            side_effects=("situation_graph_projection_write",),
            emitted_tokens=(
                "SituationGraph",
                "SituationGraphPrimaryEdge",
                "SituationGraphSecondaryEdge",
                "SituationGraphContinuation",
            ),
            reason=(
                "the admitted root Matter projects its current descendant "
                "Matter, WorkItem, Event, and inferred-node neighborhood as a "
                "bounded graph; the existing single acyclic primary parent "
                "remains authoritative while related, precedes, depends-on, "
                "supports, contradicts, and inferred edges remain typed secondary edges"
            ),
        ),
        CaseRule(
            case_id="ordinary_submatters_projection_requested",
            decision="matter_only_hierarchy_projection_current",
            label="matter_only_hierarchy_projection_current",
            writes=(
                "matter.ui_hierarchy_projection_revision",
                "matter.ui_hierarchy_matter_ids",
                "matter.ui_hierarchy_secondary_edges",
            ),
            side_effects=("situation_graph_projection_write",),
            emitted_tokens=(
                "MatterOnlyHierarchyProjection",
                "SituationGraphPrimaryEdge",
                "SituationGraphSecondaryEdge",
            ),
            reason=(
                "the ordinary Sub-matters UI projects only exact current admitted "
                "Matter ids; WorkItems, Events, facts, waits, sources, and "
                "inferences remain internal contents of their owning Matter, "
                "while typed related/depends-on/supports Matter relations stay visible"
            ),
        ),
        CaseRule(
            case_id="travel_and_software_fragments_reconciled",
            decision="broad_roots_and_peer_children_reconciled",
            label="broad_roots_and_peer_children_reconciled",
            writes=(
                "matter.reconciliation_context",
                "matter.merge_disposition",
                "matter.primary_parent",
                "matter.hierarchy_revision",
                "matter.root_granularity",
            ),
            side_effects=("matter_registry_write",),
            emitted_tokens=(
                "BroadRootMatter",
                "ContainmentCurrent",
                "TravelHierarchyReconciled",
                "SoftwarePortfolioHierarchyReconciled",
            ),
            reason=(
                "one 2026 travel program owns peer trip Matters such as Japan and "
                "Australia, with outbound and return legs kept as peer contents "
                "or children at the same licensed level; one software-development "
                "portfolio owns project Matters such as FlowGuard, SkillGuard, "
                "FlowPilot, PhysicsGuard, heating evaluation, and job-search "
                "software rather than emitting each clue as an unrelated root"
            ),
        ),
        CaseRule(
            case_id="same_matter_already_admits_current_source_revision",
            decision="older_duplicate_source_revision_removed",
            label="older_duplicate_source_revision_removed",
            writes=(
                "matter.membership",
                "matter.current_evidence_membership",
                "matter.source_revision_reconciliation_status",
            ),
            side_effects=("matter_registry_write",),
            emitted_tokens=("MatterSourceRevisionCurrent",),
            reason=(
                "when the same admitted Matter already cites the exact current "
                "SourceVersion, its older duplicate source and evidence "
                "memberships are removed from the current admission while the "
                "current evidence anchors and append-only history remain"
            ),
        ),
        CaseRule(
            case_id="exact_existing_matter_current_revision_processed",
            decision="current_revision_adopted_into_exact_existing_matter",
            label="current_revision_adopted_into_exact_existing_matter",
            writes=(
                "matter.membership",
                "matter.source_revision_target_identity",
                "matter.current_evidence_membership",
                "matter.source_revision_reconciliation_status",
            ),
            side_effects=("matter_registry_write",),
            emitted_tokens=(
                "MatterSourceRevisionTargetAdopted",
                "MatterSourceRevisionCurrent",
                "OldRevisionEvidenceRetired",
            ),
            reason=(
                "a target-bound semantic result matches the exact existing "
                "Matter id, registry-current SourceVersion, current admission "
                "fingerprint, and current evidence anchors; C6 preserves Matter "
                "and semantic identity, admits the current revision, and never "
                "uses title similarity or creates a duplicate root"
            ),
        ),
        CaseRule(
            case_id="admitted_source_revision_is_behind_registry_current",
            decision="current_source_revision_analysis_required",
            label="current_source_revision_analysis_required",
            writes=("matter.source_revision_reconciliation_status",),
            emitted_tokens=("MatterSourceRevisionAnalysisRequired",),
            reason=(
                "a newer registry revision cannot replace the admitted revision "
                "until current evidence anchors and semantic owner results exist, "
                "even when content fingerprints appear equivalent"
            ),
        ),
        CaseRule(
            case_id="same_matter_sibling_refresh_stales_after_prior_admission",
            decision="stale_refresh_superseded_by_one_exact_current_successor",
            label="stale_refresh_superseded_by_one_exact_current_successor",
            writes=("matter.source_revision_reconciliation_status",),
            emitted_tokens=(
                "SourceRevisionStalePackageRejected",
                "SourceRevisionCurrentSuccessorRequired",
            ),
            reason=(
                "when one source revision refresh changes the exact Matter "
                "admission fingerprint, a sibling package bound to the prior "
                "fingerprint is append-only superseded; exactly one successor "
                "is required for the same Matter, registry-current source, "
                "current admission fingerprint, and current evidence anchors; "
                "the stale package is never retried and its fingerprint is "
                "never relaxed"
            ),
        ),
        CaseRule(
            case_id="matter_participates_in_multiple_domains",
            decision="one_primary_parent_plus_typed_cross_domain_relation",
            label="one_primary_parent_plus_typed_cross_domain_relation",
            writes=(
                "matter.primary_parent",
                "matter.situation_graph_secondary_edges",
                "matter.ui_hierarchy_secondary_edges",
                "matter.hierarchy_revision",
            ),
            side_effects=("matter_registry_write", "situation_graph_projection_write"),
            emitted_tokens=(
                "ContainmentCurrent",
                "RelatedMatterOnly",
                "CrossDomainMatterRelation",
            ),
            reason=(
                "a project such as job-search software retains exactly one "
                "primary parent while a typed related/supports edge links it to "
                "the job-search Matter; the cross-domain relation never creates "
                "a second containment parent or a duplicate Matter"
            ),
        ),
        CaseRule(
            case_id="situation_graph_has_more_descendants",
            decision="situation_graph_continuation_visible",
            label="situation_graph_continuation_visible",
            writes=(
                "matter.situation_graph_revision",
                "matter.situation_graph_continuation",
            ),
            side_effects=("situation_graph_projection_write",),
            emitted_tokens=("SituationGraph", "SituationGraphContinuation"),
            reason=(
                "large or deep hierarchies return a stable bounded continuation "
                "instead of pretending the currently rendered graph is exhaustive"
            ),
        ),
        CaseRule(
            case_id="composed_parent_and_children_valid",
            decision="parent_composition_committed_atomically",
            label="parent_composition_committed_atomically",
            writes=(
                "matter.identity",
                "matter.admission_status",
                "matter.rationale",
                "matter.membership",
                "matter.primary_parent",
                "matter.containment_role",
                "matter.hierarchy_revision",
                "matter.hierarchy_batch_status",
                "matter.parent_composition_transaction_status",
            ),
            side_effects=("parent_composition_transaction_write",),
            emitted_tokens=(
                "AdmittedMatter",
                "ContainmentCurrent",
                "HierarchyBatchCommitted",
                "ParentCompositionAtomic",
            ),
            reason=(
                "the parent and complete attachment set validate before one "
                "transaction commits admission, projection delegation, "
                "classification, coverage references, containment, activity "
                "rollup, and supplemental disposition; hero generation starts "
                "only after commit"
            ),
        ),
        CaseRule(
            case_id="exact_admitted_matter_id_enters_canonical_owners",
            decision="canonical_matter_identity_current",
            label="canonical_matter_identity_current",
            writes=(
                "matter.identity",
                "matter.admitted_matter_id_authority",
                "matter.admission_status",
                "matter.canonical_matter_id",
            ),
            side_effects=("matter_registry_write",),
            emitted_tokens=(
                "AdmittedMatter",
                "CanonicalMatterIdentityCurrent",
            ),
            reason=(
                "hierarchy, coverage, lifecycle, activity, relation, "
                "localization, hero, and UI owners may bind only the exact "
                "current matter_id returned by a C6 admitted disposition"
            ),
        ),
        CaseRule(
            case_id="projection_source_or_candidate_without_admitted_matter_id",
            decision="canonical_matter_identity_rejected",
            label="canonical_matter_identity_rejected",
            writes=("matter.admission_status", "matter.rationale"),
            side_effects=("matter_registry_write",),
            emitted_tokens=(
                "SourceOnly",
                "MatterCandidate",
                "CanonicalMatterIdentityRejected",
            ),
            reason=(
                "projection ids, SourceVersion ids, candidate ids, package ids, "
                "titles, and source overlap remain non-authoritative and cannot "
                "enter canonical hierarchy, coverage, or admitted totals"
            ),
        ),
        CaseRule(
            case_id="complete_current_child_scope_for_parent_narrative",
            decision="parent_narrative_scope_published",
            label="parent_narrative_scope_published",
            writes=(
                "matter.parent_narrative_scope_revision",
                "matter.parent_narrative_child_projection_revisions",
                "matter.parent_narrative_evidence_revisions",
            ),
            side_effects=("matter_registry_write",),
            emitted_tokens=("ParentNarrativeScopeCurrent",),
            reason=(
                "the narrative scope binds the parent, current hierarchy, "
                "complete current child/projection revision set, and licensed "
                "evidence revisions; the latest child is not the parent summary authority"
            ),
        ),
        CaseRule(
            case_id="same_matter_duplicate_licensed",
            decision="duplicate_merged_to_canonical_matter",
            label="duplicate_merged_to_canonical_matter",
            writes=(
                "matter.membership",
                "matter.merge_disposition",
                "matter.canonicalization_disposition",
                "matter.canonical_matter_id",
                "matter.canonicalization_evidence",
            ),
            side_effects=("canonicalization_transaction_write",),
            emitted_tokens=(
                "MatterCanonicalization",
                "CanonicalMatterProjectionOnly",
                "SplitMergeDisposition",
            ),
            reason=(
                "evidence-licensed same-goal identity moves source membership "
                "and coverage references to one canonical Matter in one "
                "transaction while preserving both histories"
            ),
        ),
        CaseRule(
            case_id="candidate_belongs_as_work_item_or_event",
            decision="candidate_appended_to_canonical_matter",
            label="candidate_appended_to_canonical_matter",
            writes=(
                "matter.canonicalization_disposition",
                "matter.canonical_matter_id",
                "matter.canonicalization_materialization",
                "matter.canonicalization_evidence",
                "work_item.membership",
            ),
            side_effects=("canonicalization_transaction_write",),
            emitted_tokens=(
                "MatterCanonicalization",
                "CanonicalMatterProjectionOnly",
                "WorkItem",
            ),
            reason=(
                "a bounded candidate without an independent outcome is "
                "materialized exactly once under the canonical Matter and its "
                "candidate projection is retired"
            ),
        ),
        CaseRule(
            case_id="candidate_has_no_trackable_goal",
            decision="candidate_retired_to_source_only",
            label="candidate_retired_to_source_only",
            writes=(
                "matter.admission_status",
                "matter.canonicalization_disposition",
                "matter.canonicalization_evidence",
            ),
            side_effects=("canonicalization_transaction_write",),
            emitted_tokens=(
                "MatterCanonicalization",
                "CandidateSourceOnlyRetained",
                "SourceOnly",
            ),
            reason=(
                "the candidate leaves Matter reachability but retains evidence "
                "and source history through one append-only source-only disposition"
            ),
        ),
        CaseRule(
            case_id="provider_item_basic",
            decision="matter_candidate",
            label="matter_candidate",
            writes=("matter.admission_status", "matter.rationale"),
            side_effects=("matter_registry_write",),
            emitted_tokens=("MatterCandidate",),
            reason="one file, message, document part, or provider item may form a candidate but is not mechanically admitted",
        ),
        CaseRule(
            case_id="future_maybe_research",
            decision="source_only",
            label="source_only",
            writes=("matter.admission_status", "matter.rationale"),
            side_effects=("matter_registry_write",),
            emitted_tokens=("SourceOnly",),
            reason="weak future interest does not form a Matter",
        ),
        CaseRule(
            case_id="fully_evidenced_obligation",
            decision="matter_admitted",
            label="matter_admitted",
            writes=(
                "matter.identity",
                "matter.admission_status",
                "matter.rationale",
                "matter.membership",
            ),
            side_effects=("matter_registry_write",),
            emitted_tokens=("AdmittedMatter",),
            reason="current person/event/obligation evidence satisfies admission policy",
        ),
        CaseRule(
            case_id="conflicting_or_insufficient",
            decision="matter_uncertain",
            label="matter_uncertain",
            writes=("matter.admission_status", "matter.rationale"),
            side_effects=("matter_registry_write",),
            emitted_tokens=("MatterUncertain",),
            reason=(
                "material conflict is preserved as an autonomous uncertain "
                "disposition rather than waiting for user confirmation"
            ),
        ),
        CaseRule(
            case_id="irrelevant_or_non_actionable",
            decision="not_applicable",
            label="not_applicable",
            writes=("matter.admission_status", "matter.rationale"),
            side_effects=("matter_registry_write",),
            emitted_tokens=("NotApplicable",),
            reason="current evidence is terminally unrelated to a user situation",
        ),
        CaseRule(
            case_id="visual_related_to_matter",
            decision="matter_source_relation_recorded",
            label="matter_source_relation_recorded",
            writes=("matter.source_relation",),
            side_effects=("matter_registry_write",),
            emitted_tokens=("MatterSourceRelation",),
            reason="current evidence licenses a bounded Matter-to-source relation for the real Images gallery",
        ),
        CaseRule(
            case_id="visual_unrelated_to_matter",
            decision="matter_source_relation_absent",
            label="matter_source_relation_absent",
            writes=("matter.source_relation",),
            side_effects=("matter_registry_write",),
            emitted_tokens=("NotApplicable",),
            reason="an unrelated eligible visual remains excluded from this Matter",
        ),
        CaseRule(
            case_id="access_blocked",
            decision="admission_blocked",
            label="admission_blocked",
            writes=("matter.admission_status", "matter.rationale"),
            emitted_tokens=("AccessBlocked",),
            reason="required evidence is inaccessible",
        ),
        CaseRule(
            case_id="licensed_project_or_situation_context",
            decision="context_reconciled_to_current_structure",
            label="context_reconciled_to_current_structure",
            writes=(
                "matter.reconciliation_context",
                "matter.merge_disposition",
                "matter.membership",
                "matter.primary_parent",
                "matter.hierarchy_revision",
            ),
            side_effects=("matter_registry_write",),
            emitted_tokens=(
                "ContextReconciliationDecision",
                "HierarchyDecision",
                "ContainmentCurrent",
            ),
            reason=(
                "goal, subject, outcome, people, time, source neighborhood, "
                "provider thread, repository/project, and Codex workspace context "
                "are compared together before append/root/child/related decisions"
            ),
        ),
        CaseRule(
            case_id="licensed_match_beyond_initial_context_page",
            decision="global_context_candidate_recalled",
            label="global_context_candidate_recalled",
            writes=(
                "matter.reconciliation_context",
                "matter.merge_disposition",
            ),
            side_effects=("matter_registry_write",),
            emitted_tokens=(
                "GlobalCandidateRecallComplete",
                "ContextReconciliationDecision",
                "ContainmentCurrent",
            ),
            reason=(
                "the exact-signal index is searched across every current Matter "
                "before a deterministic top candidate window is supplied to "
                "bounded reconciliation"
            ),
        ),
        CaseRule(
            case_id="weak_single_context_signal",
            decision="weak_context_preserved_without_merge",
            label="weak_context_preserved_without_merge",
            writes=(
                "matter.reconciliation_context",
                "matter.merge_disposition",
                "matter.rationale",
            ),
            side_effects=("matter_registry_write",),
            emitted_tokens=(
                "ContextReconciliationDecision",
                "WeakContextNoMerge",
                "RelatedMatterOnly",
            ),
            reason=(
                "one shared folder, person, broad topic, title, or date is "
                "contextual evidence only and cannot force merge or containment"
            ),
        ),
        CaseRule(
            case_id="large_goal_root_matter",
            decision="root_matter_admitted",
            label="root_matter_admitted",
            writes=(
                "matter.identity",
                "matter.admission_status",
                "matter.rationale",
                "matter.membership",
                "matter.object_kind",
                "matter.primary_parent",
                "matter.hierarchy_revision",
                "matter.root_granularity",
            ),
            side_effects=("matter_registry_write",),
            emitted_tokens=(
                "AdmittedMatter",
                "HierarchyDecision",
                "RootMatter",
                "BroadRootMatter",
                "ContainmentCurrent",
            ),
            reason=(
                "an independently meaningful broad situation such as one trip, "
                "job search, event participation, subscription relationship, or "
                "software project is admitted as a root Matter with no primary parent"
            ),
        ),
        CaseRule(
            case_id="independent_child_goal",
            decision="child_matter_admitted",
            label="child_matter_admitted",
            writes=(
                "matter.identity",
                "matter.admission_status",
                "matter.rationale",
                "matter.membership",
                "matter.object_kind",
                "matter.primary_parent",
                "matter.containment_role",
                "matter.hierarchy_revision",
            ),
            side_effects=("matter_registry_write",),
            emitted_tokens=(
                "AdmittedMatter",
                "HierarchyDecision",
                "ChildMatter",
                "ContainmentCurrent",
            ),
            reason=(
                "a bounded sub-goal with its own evidence, lifecycle, and outcome "
                "is admitted below exactly one current primary parent; the "
                "evidence-backed edge is classified required, optional, or critical"
            ),
        ),
        CaseRule(
            case_id="bounded_action_without_independent_outcome",
            decision="work_item_attached",
            label="work_item_attached",
            writes=(
                "matter.rationale",
                "matter.hierarchy_revision",
                "work_item.membership",
            ),
            side_effects=("matter_registry_write",),
            emitted_tokens=("HierarchyDecision", "WorkItem", "ContainmentCurrent"),
            reason=(
                "a smaller actionable step without an independent Matter outcome "
                "remains a WorkItem under its owning Matter"
            ),
        ),
        CaseRule(
            case_id="bounded_event_or_source",
            decision="event_or_source_not_promoted",
            label="event_or_source_not_promoted",
            writes=("matter.rationale",),
            side_effects=("matter_registry_write",),
            emitted_tokens=("HierarchyDecision", "EventOnly", "SourceOnly"),
            reason=(
                "an occurrence or evidence origin remains Event or Source unless "
                "independent Matter admission criteria are separately satisfied"
            ),
        ),
        CaseRule(
            case_id="shared_person_or_source_only",
            decision="related_without_containment",
            label="related_without_containment",
            writes=("matter.rationale", "matter.hierarchy_revision"),
            side_effects=("matter_registry_write",),
            emitted_tokens=("HierarchyDecision", "RelatedMatterOnly"),
            reason=(
                "shared people, sources, titles, dates, or evidence create at most "
                "a related-Matter candidate and never a parent-child edge"
            ),
        ),
        CaseRule(
            case_id="cycle_or_self_parent_proposed",
            decision="hierarchy_conflict",
            label="hierarchy_conflict",
            writes=("matter.rationale", "matter.hierarchy_depth_status"),
            side_effects=("matter_registry_write",),
            emitted_tokens=("HierarchyDecision", "HierarchyConflict"),
            reason=(
                "self-parent and any edge whose ancestor walk reaches the child "
                "are rejected without replacing the last current containment"
            ),
        ),
        CaseRule(
            case_id="multiple_primary_parents_proposed",
            decision="hierarchy_conflict",
            label="hierarchy_conflict",
            writes=("matter.rationale", "matter.hierarchy_depth_status"),
            side_effects=("matter_registry_write",),
            emitted_tokens=("HierarchyDecision", "HierarchyConflict"),
            reason=(
                "a child has at most one current primary parent; additional "
                "relationships remain non-hierarchical until an explicit reparent revision"
            ),
        ),
        CaseRule(
            case_id="reparent_split_or_merge",
            decision="hierarchy_revision_appended",
            label="hierarchy_revision_appended",
            writes=(
                "matter.membership",
                "matter.primary_parent",
                "matter.containment_role",
                "matter.hierarchy_revision",
                "work_item.membership",
            ),
            side_effects=("matter_registry_write",),
            emitted_tokens=(
                "HierarchyDecision",
                "HierarchyRevision",
                "ContainmentCurrent",
                "SplitMergeDisposition",
            ),
            reason=(
                "reparent, split, and merge append identity-preserving revisions "
                "with explicit source, event, WorkItem, old-parent, and new-parent dispositions"
            ),
        ),
        CaseRule(
            case_id="hierarchy_depth_budget_exhausted",
            decision="hierarchy_depth_pending",
            label="hierarchy_depth_pending",
            writes=("matter.hierarchy_depth_status",),
            side_effects=("matter_registry_write",),
            emitted_tokens=("HierarchyDecision", "HierarchyDepthPending"),
            reason=(
                "recursive discovery may continue in later bounded runs; an "
                "unmodeled deeper branch remains explicitly pending, never complete"
            ),
        ),
        CaseRule(
            case_id="bounded_containment_batch_valid",
            decision="hierarchy_batch_committed_then_published_once",
            label="hierarchy_batch_committed_then_published_once",
            writes=(
                "matter.primary_parent",
                "matter.containment_role",
                "matter.hierarchy_revision",
                "matter.hierarchy_batch_status",
                "matter.hierarchy_publication_request",
            ),
            side_effects=("hierarchy_batch_write",),
            emitted_tokens=(
                "HierarchyRevision",
                "ContainmentCurrent",
                "HierarchyBatchCommitted",
            ),
            reason=(
                "one parent and at most 500 children are validated as a whole; "
                "edges, one revision, stale audits, and pending publication "
                "commit atomically before one summary/projection publication"
            ),
        ),
        CaseRule(
            case_id="batch_publication_interrupted",
            decision="pending_hierarchy_publication_recovered",
            label="pending_hierarchy_publication_recovered",
            writes=(
                "matter.hierarchy_batch_status",
                "matter.hierarchy_publication_request",
            ),
            side_effects=("hierarchy_batch_write",),
            emitted_tokens=(
                "HierarchyBatchCommitted",
                "HierarchyPublicationRecovered",
            ),
            reason=(
                "startup resumes a committed pending publication exactly once; "
                "an identical batch retry reuses the same hierarchy revision"
            ),
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-C6-024-new-source-revision-bypasses-analysis",
            protected_error_class="source_revision_semantic_owner_bypass",
            description=(
                "a newer SourceVersion mechanically replaces an admitted "
                "revision without current evidence anchors and semantic results"
            ),
            protected_harm=(
                "the Matter appears fresh while its claims still depend on an "
                "older or materially different source revision"
            ),
            case_id="admitted_source_revision_is_behind_registry_current",
            broken_decision="newer_source_revision_auto_promoted",
            broken_writes=(
                "matter.membership",
                "matter.source_revision_reconciliation_status",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("MatterSourceRevisionCurrent",),
        ),
        HazardSpec(
            failure_id="H-C6-025-target-bound-revision-escapes-to-similar-matter",
            protected_error_class="source_revision_exact_target_bypass",
            description=(
                "a target-bound current revision is applied to a title-similar "
                "Matter or creates a new root instead of updating the exact "
                "existing Matter named by the current admission fingerprint"
            ),
            protected_harm=(
                "one real situation forks into duplicate or incorrect Matters "
                "and the original Matter remains stale"
            ),
            case_id="exact_existing_matter_current_revision_processed",
            broken_decision="similarity_selected_or_duplicate_root_created",
            broken_writes=(
                "matter.identity",
                "matter.membership",
                "matter.source_revision_target_identity",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("AdmittedMatter",),
        ),
        HazardSpec(
            failure_id="H-C6-026-old-revision-evidence-remains-current",
            protected_error_class="source_revision_evidence_membership_stale",
            description=(
                "the current SourceVersion is admitted but the current admission "
                "still contains evidence anchors from the replaced revision"
            ),
            protected_harm=(
                "depth, summaries, localization, supplemental information, and "
                "the UI can claim current while reading stale evidence"
            ),
            case_id="same_matter_already_admits_current_source_revision",
            broken_decision="old_source_removed_old_evidence_retained",
            broken_writes=(
                "matter.membership",
                "matter.source_revision_reconciliation_status",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("MatterSourceRevisionCurrent",),
        ),
        HazardSpec(
            failure_id="H-C6-027-stale-sibling-retried-or-duplicate-successor",
            protected_error_class="source_revision_stale_successor_cardinality",
            description=(
                "a stale same-Matter sibling package is retried with a weaker "
                "admission fingerprint or produces multiple current successors"
            ),
            protected_harm=(
                "stale evidence can overwrite current Matter semantics or "
                "duplicate divergent successor work can enter the queue"
            ),
            case_id="same_matter_sibling_refresh_stales_after_prior_admission",
            broken_decision="stale_package_retried_or_duplicate_successors_queued",
            broken_writes=("matter.source_revision_reconciliation_status",),
            broken_tokens=("MatterSourceRevisionCurrent",),
        ),
        HazardSpec(
            failure_id="H-C6-021-nonmatter-node-enters-ui-hierarchy",
            protected_error_class="ui_hierarchy_object_kind_escape",
            description=(
                "a WorkItem, Event, fact, wait, source, or inference is emitted "
                "as a peer node in the ordinary Sub-matters projection"
            ),
            protected_harm=(
                "the user-visible Matter hierarchy becomes a recursive internal trace graph"
            ),
            case_id="ordinary_submatters_projection_requested",
            broken_decision="mixed_object_kind_hierarchy_projection",
            broken_writes=(
                "matter.ui_hierarchy_projection_revision",
                "matter.ui_hierarchy_matter_ids",
            ),
            broken_side_effects=("situation_graph_projection_write",),
            broken_tokens=("MatterOnlyHierarchyProjection",),
        ),
        HazardSpec(
            failure_id="H-C6-022-travel-or-software-fragments-remain-roots",
            protected_error_class="known_portfolio_hierarchy_undermerge",
            description=(
                "licensed Japan/Australia travel or Guard-family software "
                "fragments remain unrelated root cards after reconciliation"
            ),
            protected_harm=(
                "the catalog shows implementation clues instead of the broad "
                "situations the user asked to browse"
            ),
            case_id="travel_and_software_fragments_reconciled",
            broken_decision="root_matter_admitted_per_fragment",
            broken_writes=(
                "matter.primary_parent",
                "matter.hierarchy_revision",
                "matter.root_granularity",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("RootMatter",),
        ),
        HazardSpec(
            failure_id="H-C6-023-cross-domain-relation-creates-second-parent",
            protected_error_class="cross_domain_multi_parent_escape",
            description=(
                "a Matter that supports two domains is duplicated or receives "
                "two current primary parents"
            ),
            protected_harm=(
                "one project acquires contradictory hierarchy identity and state"
            ),
            case_id="matter_participates_in_multiple_domains",
            broken_decision="second_primary_parent_added",
            broken_writes=(
                "matter.primary_parent",
                "matter.ui_hierarchy_secondary_edges",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("ContainmentCurrent",),
        ),
        HazardSpec(
            failure_id="H-C6-020-projection-or-candidate-id-enters-hierarchy",
            protected_error_class="canonical_matter_identity_authority_escape",
            description=(
                "a projection-only, source-only, or candidate id is accepted "
                "as a canonical Matter id without one exact C6 admission"
            ),
            protected_harm=(
                "phantom Matters enter hierarchy, coverage, lifecycle, and UI "
                "or overwrite an unrelated Matter selected by source overlap"
            ),
            case_id="projection_source_or_candidate_without_admitted_matter_id",
            broken_decision="canonical_matter_identity_current",
            broken_writes=(
                "matter.identity",
                "matter.admitted_matter_id_authority",
                "matter.canonical_matter_id",
                "matter.primary_parent",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("AdmittedMatter", "ContainmentCurrent"),
        ),
        HazardSpec(
            failure_id="H-C6-019-parent-narrative-scope-truncated-to-latest-child",
            protected_error_class="parent_narrative_scope_undercoverage",
            description=(
                "the parent overview scope includes only the latest child or a "
                "stale subset of the current child projection set"
            ),
            protected_harm=(
                "the parent project overview describes one subtask instead of "
                "the complete broader Matter"
            ),
            case_id="complete_current_child_scope_for_parent_narrative",
            broken_decision="latest_child_selected_as_parent_scope",
            broken_writes=(
                "matter.parent_narrative_scope_revision",
                "matter.parent_narrative_child_projection_revisions",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("ParentNarrativeScopeCurrent",),
        ),
        HazardSpec(
            failure_id="H-C6-016-parent-composition-leaves-partial-parent",
            protected_error_class="parent_composition_transaction_escape",
            description=(
                "a child attachment fails after parent admission, projection, "
                "coverage, activity, or supplemental rows already became current"
            ),
            protected_harm=(
                "a phantom parent survives with incomplete children and "
                "non-idempotent downstream work"
            ),
            case_id="composed_parent_and_children_valid",
            broken_decision="parent_composition_partially_committed",
            broken_writes=(
                "matter.identity",
                "matter.admission_status",
                "matter.parent_composition_transaction_status",
            ),
            broken_side_effects=("parent_composition_transaction_write",),
            broken_tokens=("AdmittedMatter",),
        ),
        HazardSpec(
            failure_id="H-C6-017-canonicalization-splits-transaction",
            protected_error_class="matter_canonicalization_partial_commit",
            description=(
                "same-Matter merge or candidate append changes admission before "
                "coverage references, materialization, and projection retirement"
            ),
            protected_harm=(
                "duplicate cards, lost evidence, or coverage rows point to "
                "different Matter authorities"
            ),
            case_id="same_matter_duplicate_licensed",
            broken_decision="duplicate_partially_merged",
            broken_writes=(
                "matter.merge_disposition",
                "matter.canonical_matter_id",
            ),
            broken_side_effects=("canonicalization_transaction_write",),
            broken_tokens=("MatterCanonicalization",),
        ),
        HazardSpec(
            failure_id="H-C6-018-canonicalization-retry-changes-materialization",
            protected_error_class="matter_canonicalization_retry_conflict",
            description=(
                "a retry silently changes canonical target, WorkItem/Event "
                "materialization, rationale, or evidence"
            ),
            protected_harm=(
                "one candidate acquires incompatible current dispositions"
            ),
            case_id="candidate_belongs_as_work_item_or_event",
            broken_decision="candidate_appended_with_new_materialization",
            broken_writes=(
                "matter.canonicalization_materialization",
                "matter.canonicalization_evidence",
            ),
            broken_side_effects=("canonicalization_transaction_write",),
            broken_tokens=("MatterCanonicalization",),
        ),
        HazardSpec(
            failure_id="H-C6-001-one-source-item-one-matter",
            protected_error_class="provider_item_mechanical_admission",
            description="one file, message, document part, or provider item is mechanically admitted as one Matter",
            protected_harm="provider structure replaces product semantics",
            case_id="provider_item_basic",
            broken_decision="matter_admitted",
            broken_writes=(
                "matter.identity",
                "matter.admission_status",
                "matter.rationale",
                "matter.membership",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("AdmittedMatter",),
        ),
        HazardSpec(
            failure_id="H-C6-002-source-only-overmodeled",
            protected_error_class="matter_overformation",
            description="a speculative future interest is admitted as a Matter",
            protected_harm="the system creates noise and false commitments",
            case_id="future_maybe_research",
            broken_decision="matter_admitted",
            broken_writes=(
                "matter.identity",
                "matter.admission_status",
                "matter.rationale",
                "matter.membership",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("AdmittedMatter",),
        ),
        HazardSpec(
            failure_id="H-C6-003-conflict-silently-admitted",
            protected_error_class="admission_conflict_bypass",
            description="material contrary evidence is ignored during admission",
            protected_harm="a disputed Matter enters canonical state and statistics",
            case_id="conflicting_or_insufficient",
            broken_decision="matter_admitted",
            broken_writes=(
                "matter.identity",
                "matter.admission_status",
                "matter.rationale",
                "matter.membership",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("AdmittedMatter",),
        ),
        HazardSpec(
            failure_id="H-C6-005-unrelated-visual-linked",
            protected_error_class="matter_visual_relation_overclaim",
            description="an unrelated visual is linked to the Matter",
            protected_harm="the Images gallery presents unrelated private evidence",
            case_id="visual_unrelated_to_matter",
            broken_decision="matter_source_relation_recorded",
            broken_writes=("matter.source_relation",),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("MatterSourceRelation",),
        ),
        HazardSpec(
            failure_id="H-C6-004-access-gap-admitted",
            protected_error_class="access_gap_overclaim",
            description="an access-blocked packet is admitted despite missing required evidence",
            protected_harm="absence caused by permissions is treated as complete support",
            case_id="access_blocked",
            broken_decision="matter_admitted",
            broken_writes=(
                "matter.identity",
                "matter.admission_status",
                "matter.rationale",
                "matter.membership",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("AdmittedMatter",),
        ),
        HazardSpec(
            failure_id="H-C6-006-event-promoted-to-matter",
            protected_error_class="event_matter_identity_conflation",
            description="one event or source item is promoted to a child Matter",
            protected_harm="fine-grained evidence floods the root catalog with duplicate objects",
            case_id="bounded_event_or_source",
            broken_decision="child_matter_admitted",
            broken_writes=(
                "matter.identity",
                "matter.admission_status",
                "matter.object_kind",
                "matter.primary_parent",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("AdmittedMatter", "ChildMatter"),
        ),
        HazardSpec(
            failure_id="H-C6-007-shared-person-implies-parent",
            protected_error_class="relation_containment_conflation",
            description="shared person, source, title, date, or evidence implies parent-child containment",
            protected_harm="coincidental similarity changes semantic ownership and rollup",
            case_id="shared_person_or_source_only",
            broken_decision="child_matter_admitted",
            broken_writes=("matter.primary_parent", "matter.containment_role"),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("ChildMatter", "ContainmentCurrent"),
        ),
        HazardSpec(
            failure_id="H-C6-008-cycle-or-self-parent-accepted",
            protected_error_class="hierarchy_cycle",
            description="a self-parent or cyclic primary containment edge becomes current",
            protected_harm="ancestor traversal, invalidation, and UI navigation cannot terminate",
            case_id="cycle_or_self_parent_proposed",
            broken_decision="hierarchy_revision_appended",
            broken_writes=("matter.primary_parent", "matter.hierarchy_revision"),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("ContainmentCurrent",),
        ),
        HazardSpec(
            failure_id="H-C6-009-multiple-primary-parents",
            protected_error_class="hierarchy_multi_parent",
            description="one child has multiple current primary parents",
            protected_harm="state rollup and correction propagation have competing ancestor paths",
            case_id="multiple_primary_parents_proposed",
            broken_decision="hierarchy_revision_appended",
            broken_writes=("matter.primary_parent", "matter.hierarchy_revision"),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("ContainmentCurrent",),
        ),
        HazardSpec(
            failure_id="H-C6-010-depth-pending-claimed-complete",
            protected_error_class="hierarchy_depth_false_complete",
            description="a budget-exhausted descendant branch is recorded as fully modeled",
            protected_harm="the user and M0 cannot see that deeper objects remain unclassified",
            case_id="hierarchy_depth_budget_exhausted",
            broken_decision="hierarchy_current_complete",
            broken_writes=("matter.hierarchy_depth_status",),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("ContainmentCurrent",),
        ),
        HazardSpec(
            failure_id="H-C6-011-partial-containment-batch",
            protected_error_class="hierarchy_batch_partial_commit",
            description=(
                "one invalid child is discovered after earlier batch edges "
                "already became current"
            ),
            protected_harm=(
                "a rejected batch leaves partial parents, stale summaries, and "
                "non-idempotent retry history"
            ),
            case_id="bounded_containment_batch_valid",
            broken_decision="hierarchy_batch_partially_committed",
            broken_writes=(
                "matter.primary_parent",
                "matter.hierarchy_revision",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("ContainmentCurrent",),
        ),
        HazardSpec(
            failure_id="H-C6-012-pending-publication-lost",
            protected_error_class="hierarchy_batch_publication_loss",
            description=(
                "a committed containment batch is left permanently pending "
                "after interruption"
            ),
            protected_harm=(
                "current edges exist without a current parent summary or UI "
                "projection and retries may duplicate work"
            ),
            case_id="batch_publication_interrupted",
            broken_decision="pending_publication_abandoned",
            broken_writes=("matter.hierarchy_batch_status",),
            broken_side_effects=("hierarchy_batch_write",),
            broken_tokens=("HierarchyBatchCommitted",),
        ),
        HazardSpec(
            failure_id="H-C6-013-single-context-signal-forces-merge",
            protected_error_class="matter_context_overmerge",
            description="a shared folder, person, broad topic, title, or date alone merges two Matters",
            protected_harm="distinct user goals and outcomes lose independent identity and state",
            case_id="weak_single_context_signal",
            broken_decision="context_reconciled_to_current_structure",
            broken_writes=(
                "matter.merge_disposition",
                "matter.membership",
                "matter.primary_parent",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("ContextReconciliationDecision", "ContainmentCurrent"),
        ),
        HazardSpec(
            failure_id="H-C6-014-one-situation-fragmented-into-root-cards",
            protected_error_class="matter_context_undermerge",
            description="one licensed trip, job search, event, or software project becomes several root cards",
            protected_harm="records and small steps replace the broad situation the user needs to browse",
            case_id="licensed_project_or_situation_context",
            broken_decision="root_matter_admitted_per_source",
            broken_writes=(
                "matter.identity",
                "matter.membership",
                "matter.root_granularity",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("RootMatter",),
        ),
        HazardSpec(
            failure_id="H-C6-015-global-context-recall-truncated",
            protected_error_class="matter_context_candidate_window_truncation",
            description=(
                "a licensed same-Matter match beyond the first 50 stored "
                "contexts is never considered"
            ),
            protected_harm=(
                "storage order creates a duplicate root Matter even though "
                "current evidence licenses append-to-current"
            ),
            case_id="licensed_match_beyond_initial_context_page",
            broken_decision="root_matter_admitted_per_storage_window",
            broken_writes=(
                "matter.identity",
                "matter.admission_status",
                "matter.merge_disposition",
            ),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("AdmittedMatter", "RootMatter"),
        ),
    ),
    risk_classes=("decision", "state_transition", "evidence", "side_effect"),
    template_no_match_reason=(
        "The Phase A template search returned no source-first Matter-admission template."
    ),
    blindspots=(
        "the exact admission and hierarchy-edge policies remain subject to private canaries and later model deepening",
        "candidate exclusion from real statistics requires implementation-level alignment",
    ),
    claim_boundary=(
        "This receipt can establish C6 abstract source-first admission, bounded "
        "multi-signal context reconciliation, full-library indexed candidate "
        "recall before bounded AI context, broad-root/object-kind "
        "classification, single-parent acyclic containment, role, revision, and "
        "bounded-depth hazards, atomic parent composition, and singular "
        "append-only same-Matter canonicalization whose downstream identity is the "
        "exact admitted matter_id. It rejects source, candidate, package, title, "
        "or projection identities as canonical substitutes. It does not prove the "
        "substantive admission or merge policy, statistics implementation, "
        "production persistence, ancestor rollup, or parent closure."
    ),
)
