"""M0 autonomous end-to-end authority and coverage-ledger model."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="M0_matters_end_to_end_authority",
    title="M0 Autonomous Matters End-to-End Authority",
    modeled_boundary=(
        "one orchestration snapshot over current C1-C12 source-universe, "
        "ObjectCoverageLedger, freshness, semantic depth, automatic original-owner "
        "dispatch, source-in-place storage migration and transient cleanup, "
        "SourceGroup, SituationGraph, advisory Situation/World Model, "
        "material-clue/summary/activity ordering, root-only photoreal Hero and "
        "eight-section bilingual UI readiness, retry/restart recovery, one strongest "
        "compatible Codex maintenance orchestrator with bounded cheaper delegation, "
        "model-agnostic capability routing, shared-path Codex daily maintenance, "
        "ResearchGuard release gating, and unconsumed-output obligations"
        ", including the ordered hierarchy stage chain from decision through "
        "containment, child state, ancestor rollup, projection, and UI reachability"
    ),
    state_fields=(
        "orchestration.child_receipt_set",
        "orchestration.integration_status",
        "orchestration.object_coverage_ledger_revision",
        "orchestration.object_stage_terminal_index",
        "orchestration.coverage_first_gap_index",
        "orchestration.coverage_contract_rebase_status",
        "orchestration.coverage_orphan_reconciliation_status",
        "orchestration.canonicalization_join_status",
        "orchestration.catalog_query_shape_status",
        "orchestration.parent_narrative_status",
        "orchestration.human_narrative_status",
        "orchestration.logical_event_projection_status",
        "orchestration.people_relation_status",
        "orchestration.matter_hierarchy_projection_status",
        "orchestration.codex_source_coverage_status",
        "orchestration.registered_object_count",
        "orchestration.ui_ready_object_count",
        "orchestration.blocked_object_count",
        "orchestration.worker_checkpoint",
        "orchestration.worker_health",
        "orchestration.owner_redispatch_count",
        "orchestration.worker_poll_due_at",
        "orchestration.foreground_availability",
        "orchestration.filesystem_claim_lease",
        "orchestration.filesystem_stage_checkpoint",
        "orchestration.source_analysis_expansion_cursor",
        "orchestration.source_analysis_expansion_status",
        "orchestration.maintenance_rebase_cursor",
        "orchestration.maintenance_rebase_status",
        "orchestration.evidence_pointer_rebase_cursor",
        "orchestration.evidence_pointer_rebase_status",
        "orchestration.coverage_history_archive_cursor",
        "orchestration.coverage_history_archive_status",
        "orchestration.coverage_history_archive_verification",
        "orchestration.storage_migration_order_status",
        "orchestration.physical_compaction_status",
        "orchestration.work_item_registry",
        "orchestration.coverage_status",
        "orchestration.depth_status",
        "orchestration.research_status",
        "orchestration.analysis_status",
        "orchestration.capability_route_status",
        "orchestration.maintenance_orchestrator_status",
        "orchestration.delegated_result_join_status",
        "orchestration.material_clue_projection_status",
        "orchestration.generated_hero_status",
        "orchestration.supplemental_information_status",
        "orchestration.surface_evidence_status",
        "orchestration.hierarchy_stage_terminal_index",
        "orchestration.hierarchy_freshness_status",
        "orchestration.gmail_metadata_owner_reconciliation_status",
        "orchestration.gmail_content_receipt_rebase_status",
        "orchestration.gmail_current_scope_reconciliation_status",
        "orchestration.gmail_body_continuation_status",
        "orchestration.annotation_followup_reconciliation_status",
        "orchestration.source_revision_analysis_status",
        "orchestration.source_revision_reconciliation_status",
        "orchestration.source_in_place_migration_cursor",
        "orchestration.source_in_place_migration_status",
        "orchestration.transient_cleanup_cursor",
        "orchestration.transient_cleanup_status",
        "orchestration.cache_reference_gc_status",
        "orchestration.source_group_coverage_status",
        "orchestration.situation_graph_status",
        "orchestration.world_model_status",
    ),
    owned_write_fields=(
        "orchestration.child_receipt_set",
        "orchestration.integration_status",
        "orchestration.object_coverage_ledger_revision",
        "orchestration.object_stage_terminal_index",
        "orchestration.coverage_first_gap_index",
        "orchestration.coverage_contract_rebase_status",
        "orchestration.coverage_orphan_reconciliation_status",
        "orchestration.canonicalization_join_status",
        "orchestration.catalog_query_shape_status",
        "orchestration.parent_narrative_status",
        "orchestration.human_narrative_status",
        "orchestration.logical_event_projection_status",
        "orchestration.people_relation_status",
        "orchestration.matter_hierarchy_projection_status",
        "orchestration.codex_source_coverage_status",
        "orchestration.registered_object_count",
        "orchestration.ui_ready_object_count",
        "orchestration.blocked_object_count",
        "orchestration.worker_checkpoint",
        "orchestration.worker_health",
        "orchestration.owner_redispatch_count",
        "orchestration.worker_poll_due_at",
        "orchestration.foreground_availability",
        "orchestration.filesystem_claim_lease",
        "orchestration.filesystem_stage_checkpoint",
        "orchestration.source_analysis_expansion_cursor",
        "orchestration.source_analysis_expansion_status",
        "orchestration.maintenance_rebase_cursor",
        "orchestration.maintenance_rebase_status",
        "orchestration.evidence_pointer_rebase_cursor",
        "orchestration.evidence_pointer_rebase_status",
        "orchestration.coverage_history_archive_cursor",
        "orchestration.coverage_history_archive_status",
        "orchestration.coverage_history_archive_verification",
        "orchestration.storage_migration_order_status",
        "orchestration.physical_compaction_status",
        "orchestration.work_item_registry",
        "orchestration.coverage_status",
        "orchestration.depth_status",
        "orchestration.research_status",
        "orchestration.analysis_status",
        "orchestration.capability_route_status",
        "orchestration.maintenance_orchestrator_status",
        "orchestration.delegated_result_join_status",
        "orchestration.material_clue_projection_status",
        "orchestration.generated_hero_status",
        "orchestration.supplemental_information_status",
        "orchestration.surface_evidence_status",
        "orchestration.hierarchy_stage_terminal_index",
        "orchestration.hierarchy_freshness_status",
        "orchestration.gmail_metadata_owner_reconciliation_status",
        "orchestration.gmail_content_receipt_rebase_status",
        "orchestration.gmail_current_scope_reconciliation_status",
        "orchestration.gmail_body_continuation_status",
        "orchestration.annotation_followup_reconciliation_status",
        "orchestration.source_revision_analysis_status",
        "orchestration.source_revision_reconciliation_status",
        "orchestration.source_in_place_migration_cursor",
        "orchestration.source_in_place_migration_status",
        "orchestration.transient_cleanup_cursor",
        "orchestration.transient_cleanup_status",
        "orchestration.cache_reference_gc_status",
        "orchestration.source_group_coverage_status",
        "orchestration.situation_graph_status",
        "orchestration.world_model_status",
    ),
    side_effect_classes=(
        "orchestration_receipt_write",
        "coverage_ledger_write",
        "work_dispatch_write",
        "worker_checkpoint_write",
    ),
    completion_evidence=(
        "CurrentChildReceiptSet",
        "ConsumedOutputInventory",
        "ObjectCoverageLedgerCurrent",
        "CoverageContractRebaseCurrent",
        "CoverageOrphanReconciliationCurrent",
        "MatterCanonicalizationCurrent",
        "CatalogQueryShapeCurrent",
        "ParentNarrativeCurrent",
        "AllRegisteredObjectsTerminal",
        "AllAdmittedMattersUIReady",
        "M0IntegrationReceipt",
        "SourceUniverseTerminal",
        "DepthCurrent",
        "ResearchCurrent",
        "AnalysisTerminal",
        "CapabilityRouteTerminal",
        "MaintenanceOrchestratorCurrent",
        "DelegatedResultJoinCurrent",
        "MaterialClueProjectionCurrent",
        "GeneratedHeroCurrent",
        "SupplementalInformationTerminal",
        "SurfaceEvidenceCurrent",
        "OriginalOwnerTerminalSet",
        "WorkerCheckpoint",
        "OwnerRedispatchIsolated",
        "ForegroundResponsive",
        "FilesystemClaimLease",
        "FilesystemStageCheckpoint",
        "SourceAnalysisExpansionCursor",
        "SourceAnalysisExpansionTerminal",
        "MaintenanceRebaseCursor",
        "MaintenanceRebaseTerminal",
        "EvidencePointerRebaseCursor",
        "EvidencePointerRebaseTerminal",
        "CoverageHistoryArchiveCursor",
        "CoverageHistoryArchiveTerminal",
        "CoverageHistoryArchiveVerified",
        "StorageMigrationOrderCurrent",
        "PhysicalCompactionNotRun",
        "GmailMetadataOwnerReconciliationCurrent",
        "GmailContentReceiptRebaseCurrent",
        "GmailCurrentScopeReconciliationTerminal",
        "GmailBodyContinuationPrefixCurrent",
        "GmailNoTextBodyTerminal",
        "AnnotationFollowupReconciliationCurrent",
        "SourceRevisionAnalysisTerminal",
        "SourceRevisionSuccessorSetCurrent",
        "SourceRevisionReconciliationCurrent",
        "SourceInPlaceMigrationTerminal",
        "TransientCleanupTerminal",
        "CacheReferenceGCTerminal",
        "SourceGroupCoverageCurrent",
        "SituationGraphCurrent",
        "WorldModelCurrent",
        "hierarchy_decision",
        "containment_current",
        "child_state_current",
        "ancestor_rollup_current",
        "hierarchy_projection_current",
        "ui_reachable",
        "CoverageFirstGapIndexCurrent",
        "MatterOnlyHierarchyProjectionCurrent",
        "LogicalEventProjectionCurrent",
        "PeopleRelationsCurrent",
        "HumanNarrativeCurrent",
        "CodexSourceCoverageCurrent",
    ),
    rules=(
        CaseRule(
            case_id="source_in_place_migration_and_retention_current",
            decision="source_in_place_storage_pipeline_terminal",
            label="source_in_place_storage_pipeline_terminal",
            writes=(
                "orchestration.source_in_place_migration_cursor",
                "orchestration.source_in_place_migration_status",
                "orchestration.transient_cleanup_cursor",
                "orchestration.transient_cleanup_status",
                "orchestration.cache_reference_gc_status",
                "orchestration.storage_migration_order_status",
                "orchestration.physical_compaction_status",
            ),
            side_effects=(
                "orchestration_receipt_write",
                "coverage_ledger_write",
                "work_dispatch_write",
            ),
            emitted_tokens=(
                "SourceInPlaceMigrationTerminal",
                "TransientCleanupTerminal",
                "CacheReferenceGCTerminal",
                "StorageMigrationOrderCurrent",
                "PhysicalCompactionNotRun",
            ),
            reason=(
                "after writers freeze and a separate restorable backup is "
                "verified, M0 coordinates direct current pointer/derived-state "
                "migration, raw and staging removal, and reference-safe cache GC; "
                "physical compaction remains a separate explicit terminal and is "
                "never implied by logical migration"
            ),
        ),
        CaseRule(
            case_id="source_groups_graph_world_model_and_ui_current",
            decision="situation_object_browser_pipeline_current",
            label="situation_object_browser_pipeline_current",
            writes=(
                "orchestration.source_group_coverage_status",
                "orchestration.situation_graph_status",
                "orchestration.world_model_status",
                "orchestration.matter_hierarchy_projection_status",
                "orchestration.logical_event_projection_status",
                "orchestration.people_relation_status",
                "orchestration.human_narrative_status",
                "orchestration.object_stage_terminal_index",
                "orchestration.ui_ready_object_count",
            ),
            side_effects=(
                "orchestration_receipt_write",
                "coverage_ledger_write",
            ),
            emitted_tokens=(
                "SourceGroupCoverageCurrent",
                "SituationGraphCurrent",
                "WorldModelCurrent",
                "AllAdmittedMattersUIReady",
                "MatterOnlyHierarchyProjectionCurrent",
                "LogicalEventProjectionCurrent",
                "PeopleRelationsCurrent",
                "HumanNarrativeCurrent",
            ),
            reason=(
                "every admitted root reaches current grouped source locations, "
                "a bounded Matter-only descendant graph, logical-event-deduplicated "
                "timeline, current people/relationship projection, human parent "
                "and child narrative, advisory inference disposition, "
                "root-only Hero or not-applicable descendant Hero stage, exactly "
                "eight bilingual sections, and real UI reachability"
            ),
        ),
        CaseRule(
            case_id="coverage_ledger_and_first_gap_index_current",
            decision="coverage_first_gap_projection_current",
            label="coverage_first_gap_projection_current",
            writes=(
                "orchestration.object_coverage_ledger_revision",
                "orchestration.object_stage_terminal_index",
                "orchestration.coverage_first_gap_index",
                "orchestration.coverage_status",
            ),
            side_effects=("coverage_ledger_write",),
            emitted_tokens=(
                "ObjectCoverageLedgerCurrent",
                "CoverageFirstGapIndexCurrent",
            ),
            reason=(
                "each registered object has one current earliest nonterminal or "
                "terminal stage pointer materialized alongside the ledger; the "
                "one-click audit reads this bounded index to report exactly where "
                "each object stopped, and a complete claim requires every admitted "
                "Matter to be UI reachable, not merely registered or excluded"
            ),
        ),
        CaseRule(
            case_id="codex_project_source_inventory_current",
            decision="codex_source_objects_registered_grouped_and_modeled",
            label="codex_source_objects_registered_grouped_and_modeled",
            writes=(
                "orchestration.codex_source_coverage_status",
                "orchestration.object_stage_terminal_index",
                "orchestration.source_group_coverage_status",
            ),
            side_effects=("coverage_ledger_write",),
            emitted_tokens=(
                "CodexSourceCoverageCurrent",
                "SourceGroupCoverageCurrent",
                "ObjectCoverageLedgerCurrent",
            ),
            reason=(
                "authorized Codex projects/workspaces are registered as in-place "
                "source groups with project identity, bounded metadata, current "
                "semantic disposition, Matter relations, and UI reachability; "
                "their repositories are not copied into Matters storage"
            ),
        ),
        CaseRule(
            case_id="current_contract_repair_owners_terminal",
            decision="coverage_and_canonicalization_repairs_current",
            label="coverage_and_canonicalization_repairs_current",
            writes=(
                "orchestration.coverage_contract_rebase_status",
                "orchestration.coverage_orphan_reconciliation_status",
                "orchestration.canonicalization_join_status",
                "orchestration.object_coverage_ledger_revision",
            ),
            side_effects=("orchestration_receipt_write", "coverage_ledger_write"),
            emitted_tokens=(
                "CoverageContractRebaseCurrent",
                "CoverageOrphanReconciliationCurrent",
                "MatterCanonicalizationCurrent",
                "ObjectCoverageLedgerCurrent",
            ),
            reason=(
                "M0 consumes current bounded C1 tracked-only rebase and orphan "
                "retirement plus C6 atomic parent/canonicalization terminal "
                "receipts without becoming their product-state writer"
            ),
        ),
        CaseRule(
            case_id="gmail_metadata_owner_reconciliation_current",
            decision="gmail_metadata_owner_coverage_join_current",
            label="gmail_metadata_owner_coverage_join_current",
            writes=(
                "orchestration.gmail_metadata_owner_reconciliation_status",
                "orchestration.object_coverage_ledger_revision",
                "orchestration.coverage_status",
            ),
            side_effects=("coverage_ledger_write",),
            emitted_tokens=(
                "GmailMetadataOwnerReconciliationCurrent",
                "ObjectCoverageLedgerCurrent",
            ),
            reason=(
                "M0 joins C1 exact current-owner admission with C2 bounded "
                "minimal SourceVersion and cursor evidence while leaving "
                "extraction, evidence, analysis, Matter, and UI owners untouched"
            ),
        ),
        CaseRule(
            case_id="gmail_legacy_content_receipts_and_current_scope_terminal",
            decision="gmail_content_receipt_and_scope_join_current",
            label="gmail_content_receipt_and_scope_join_current",
            writes=(
                "orchestration.gmail_content_receipt_rebase_status",
                "orchestration.gmail_current_scope_reconciliation_status",
                "orchestration.object_coverage_ledger_revision",
                "orchestration.coverage_status",
            ),
            side_effects=("coverage_ledger_write",),
            emitted_tokens=(
                "GmailContentReceiptRebaseCurrent",
                "GmailCurrentScopeReconciliationTerminal",
                "ObjectCoverageLedgerCurrent",
            ),
            reason=(
                "M0 joins C1's bounded provider-read-free digest/length/evidence "
                "receipt rebase and one current-scope terminal page; switched "
                "rows become current while ambiguous rows remain explicitly "
                "blocked and no provider read or body copy is hidden"
            ),
        ),
        CaseRule(
            case_id="annotation_followups_and_source_revisions_terminal",
            decision="exact_semantic_revision_repair_join_current",
            label="exact_semantic_revision_repair_join_current",
            writes=(
                "orchestration.annotation_followup_reconciliation_status",
                "orchestration.source_revision_analysis_status",
                "orchestration.source_revision_reconciliation_status",
                "orchestration.object_coverage_ledger_revision",
                "orchestration.analysis_status",
            ),
            side_effects=(
                "orchestration_receipt_write",
                "coverage_ledger_write",
            ),
            emitted_tokens=(
                "AnnotationFollowupReconciliationCurrent",
                "SourceRevisionAnalysisTerminal",
                "SourceRevisionSuccessorSetCurrent",
                "SourceRevisionReconciliationCurrent",
                "ObjectCoverageLedgerCurrent",
            ),
            reason=(
                "M0 consumes one stable annotation-to-semantic relation, exact "
                "target-bound C6 revision adoption, exactly one current "
                "successor for every stale same-Matter sibling refresh, and "
                "the subsequent source plus old-evidence membership "
                "reconciliation without becoming a second semantic or Matter "
                "writer"
            ),
        ),
        CaseRule(
            case_id="gmail_body_continuation_prefix_current",
            decision="gmail_body_continuation_coverage_join_current",
            label="gmail_body_continuation_coverage_join_current",
            writes=(
                "orchestration.gmail_body_continuation_status",
                "orchestration.object_coverage_ledger_revision",
                "orchestration.coverage_status",
            ),
            side_effects=("coverage_ledger_write",),
            emitted_tokens=(
                "GmailBodyContinuationPrefixCurrent",
                "ObjectCoverageLedgerCurrent",
            ),
            reason=(
                "M0 joins either C1 exact-batch admission plus C2 current body "
                "SourceVersion/receipt and C3 exact anchors, or C1 proof-bound "
                "no-text admission plus C2 disposition and C3 not-applicable "
                "evidence; an interrupted completed prefix stays current while "
                "the remaining batch is visibly pending and no semantic owner "
                "is invoked"
            ),
        ),
        CaseRule(
            case_id="gmail_no_text_body_terminal",
            decision="gmail_no_text_body_coverage_terminal",
            label="gmail_no_text_body_coverage_terminal",
            writes=(
                "orchestration.gmail_body_continuation_status",
                "orchestration.object_coverage_ledger_revision",
                "orchestration.coverage_status",
            ),
            side_effects=("coverage_ledger_write",),
            emitted_tokens=(
                "GmailNoTextBodyTerminal",
                "ObjectCoverageLedgerCurrent",
            ),
            reason=(
                "M0 points source_version to the unchanged metadata version and "
                "marks extraction, evidence, and analysis not_applicable under "
                "their declared owners after C1/C2/C3 proof-bound completion"
            ),
        ),
        CaseRule(
            case_id="catalog_indexed_page_and_visible_hydration_current",
            decision="catalog_query_shape_current",
            label="catalog_query_shape_current",
            writes=(
                "orchestration.catalog_query_shape_status",
                "orchestration.integration_status",
            ),
            side_effects=("orchestration_receipt_write",),
            emitted_tokens=("CatalogQueryShapeCurrent",),
            reason=(
                "C12 current evidence proves indexed filter/order/page "
                "selection before visible-id hydration and bounded aggregate "
                "facets; bounded HTTP output alone is insufficient"
            ),
        ),
        CaseRule(
            case_id="parent_narrative_complete_scope_current",
            decision="parent_narrative_join_current",
            label="parent_narrative_join_current",
            writes=(
                "orchestration.parent_narrative_status",
                "orchestration.integration_status",
            ),
            side_effects=("orchestration_receipt_write",),
            emitted_tokens=("ParentNarrativeCurrent",),
            reason=(
                "M0 joins the C5 refresh trigger, C6 complete current "
                "child/projection/evidence scope, and C12 narrow bilingual "
                "overview publication without becoming a narrative or product-state writer"
            ),
        ),
        CaseRule(
            case_id="registered_filesystem_batch_claimed",
            decision="exclusive_bounded_claim_active",
            label="exclusive_bounded_claim_active",
            writes=(
                "orchestration.filesystem_claim_lease",
                "orchestration.filesystem_stage_checkpoint",
                "orchestration.worker_checkpoint",
            ),
            side_effects=("worker_checkpoint_write",),
            emitted_tokens=("FilesystemClaimLease", "FilesystemStageCheckpoint"),
            reason=(
                "small atomic claim pages give one worker exclusive bounded "
                "ownership; each source/extraction/evidence/package/coverage "
                "stage is checkpointed, ordinary interruption releases the "
                "page immediately, and crash recovery preserves the checkpoint"
            ),
        ),
        CaseRule(
            case_id="source_analysis_expansion_pending",
            decision="bounded_analysis_page_materialized",
            label="bounded_analysis_page_materialized",
            writes=(
                "orchestration.source_analysis_expansion_cursor",
                "orchestration.source_analysis_expansion_status",
                "orchestration.worker_checkpoint",
            ),
            side_effects=(
                "work_dispatch_write",
                "worker_checkpoint_write",
            ),
            emitted_tokens=(
                "SourceAnalysisExpansionCursor",
            ),
            reason=(
                "all qualified anchors remain registered while one maintenance "
                "step materializes only a bounded WorkPackage page and advances "
                "a durable cursor until the exact anchor set is exhausted"
            ),
        ),
        CaseRule(
            case_id="source_analysis_expansion_complete",
            decision="analysis_expansion_terminal",
            label="analysis_expansion_terminal",
            writes=(
                "orchestration.source_analysis_expansion_cursor",
                "orchestration.source_analysis_expansion_status",
            ),
            side_effects=("orchestration_receipt_write",),
            emitted_tokens=(
                "SourceAnalysisExpansionCursor",
                "SourceAnalysisExpansionTerminal",
            ),
            reason=(
                "the terminal cursor equals the registered exact anchor count "
                "and no evidence was truncated to satisfy a runtime budget"
            ),
        ),
        CaseRule(
            case_id="interactive_service_started_with_legacy_rows",
            decision="foreground_started_rebase_deferred",
            label="foreground_started_rebase_deferred",
            writes=(
                "orchestration.foreground_availability",
                "orchestration.maintenance_rebase_cursor",
                "orchestration.maintenance_rebase_status",
            ),
            side_effects=("worker_checkpoint_write",),
            emitted_tokens=("ForegroundResponsive", "MaintenanceRebaseCursor"),
            reason=(
                "opening the desktop or service exposes current readable state "
                "without enumerating or rewriting the private catalog; legacy "
                "coverage, projection, hierarchy, activity, and hero rows are "
                "advanced only by explicit bounded resumable maintenance"
            ),
        ),
        CaseRule(
            case_id="explicit_maintenance_rebase_terminal",
            decision="maintenance_rebase_terminal",
            label="maintenance_rebase_terminal",
            writes=(
                "orchestration.maintenance_rebase_cursor",
                "orchestration.maintenance_rebase_status",
                "orchestration.worker_checkpoint",
            ),
            side_effects=(
                "orchestration_receipt_write",
                "worker_checkpoint_write",
            ),
            emitted_tokens=(
                "MaintenanceRebaseCursor",
                "MaintenanceRebaseTerminal",
                "WorkerCheckpoint",
            ),
            reason=(
                "one explicit owner advances bounded keyset pages until the "
                "terminal receipt matches the frozen migration contract"
            ),
        ),
        CaseRule(
            case_id="explicit_storage_migrations_terminal_in_safe_order",
            decision="storage_migrations_terminal_without_compaction",
            label="storage_migrations_terminal_without_compaction",
            writes=(
                "orchestration.evidence_pointer_rebase_cursor",
                "orchestration.evidence_pointer_rebase_status",
                "orchestration.coverage_history_archive_cursor",
                "orchestration.coverage_history_archive_status",
                "orchestration.coverage_history_archive_verification",
                "orchestration.storage_migration_order_status",
                "orchestration.physical_compaction_status",
                "orchestration.worker_checkpoint",
            ),
            side_effects=(
                "orchestration_receipt_write",
                "worker_checkpoint_write",
            ),
            emitted_tokens=(
                "EvidencePointerRebaseCursor",
                "EvidencePointerRebaseTerminal",
                "CoverageHistoryArchiveCursor",
                "CoverageHistoryArchiveTerminal",
                "CoverageHistoryArchiveVerified",
                "StorageMigrationOrderCurrent",
                "PhysicalCompactionNotRun",
            ),
            reason=(
                "after a verified restorable copy and stopped writers, explicit "
                "bounded pointer-rebase pages finish before exact coverage-history "
                "archive pages; integrity/count/history samples close recovery, "
                "while VACUUM and physical shrink remain separate not-run work"
            ),
        ),
        CaseRule(
            case_id="all_registered_objects_terminal_and_ui_ready",
            decision="end_to_end_current",
            label="end_to_end_current",
            writes=(
                "orchestration.child_receipt_set",
                "orchestration.integration_status",
                "orchestration.object_coverage_ledger_revision",
                "orchestration.object_stage_terminal_index",
                "orchestration.registered_object_count",
                "orchestration.ui_ready_object_count",
                "orchestration.blocked_object_count",
                "orchestration.worker_checkpoint",
                "orchestration.worker_health",
                "orchestration.worker_poll_due_at",
                "orchestration.foreground_availability",
                "orchestration.work_item_registry",
                "orchestration.coverage_status",
                "orchestration.depth_status",
                "orchestration.research_status",
                "orchestration.analysis_status",
                "orchestration.capability_route_status",
                "orchestration.maintenance_orchestrator_status",
                "orchestration.delegated_result_join_status",
                "orchestration.material_clue_projection_status",
                "orchestration.generated_hero_status",
                "orchestration.supplemental_information_status",
                "orchestration.surface_evidence_status",
                "orchestration.hierarchy_stage_terminal_index",
                "orchestration.hierarchy_freshness_status",
            ),
            side_effects=(
                "orchestration_receipt_write",
                "coverage_ledger_write",
                "worker_checkpoint_write",
            ),
            emitted_tokens=(
                "CurrentChildReceiptSet",
                "ConsumedOutputInventory",
                "ObjectCoverageLedgerCurrent",
                "AllRegisteredObjectsTerminal",
                "AllAdmittedMattersUIReady",
                "M0IntegrationReceipt",
                "SourceUniverseTerminal",
                "DepthCurrent",
                "ResearchCurrent",
                "AnalysisTerminal",
                "CapabilityRouteTerminal",
                "MaintenanceOrchestratorCurrent",
                "DelegatedResultJoinCurrent",
                "MaterialClueProjectionCurrent",
                "GeneratedHeroCurrent",
                "SupplementalInformationTerminal",
                "SurfaceEvidenceCurrent",
                "OriginalOwnerTerminalSet",
                "WorkerCheckpoint",
                "ForegroundResponsive",
                "hierarchy_decision",
                "containment_current",
                "child_state_current",
                "ancestor_rollup_current",
                "hierarchy_projection_current",
                "ui_reachable",
            ),
            reason=(
                "every registered occurrence has a current terminal pointer for "
                "required stages, every admitted root/child Matter has owner decisions, "
                "en/zh-CN values, atomic material-clue/summary/activity projection, "
                "current generated hero, "
                "terminal AI supplemental-information state, exact eight-section "
                "openable C12 projection, and current 8766 surface evidence; every "
                "admitted Matter hierarchy "
                "also has the ordered current stages hierarchy_decision -> "
                "containment_current -> child_state_current -> "
                "ancestor_rollup_current -> hierarchy_projection_current -> ui_reachable"
            ),
        ),
        CaseRule(
            case_id="hierarchy_stage_chain_current",
            decision="hierarchy_pipeline_current",
            label="hierarchy_pipeline_current",
            writes=(
                "orchestration.hierarchy_stage_terminal_index",
                "orchestration.hierarchy_freshness_status",
                "orchestration.object_stage_terminal_index",
            ),
            side_effects=("coverage_ledger_write",),
            emitted_tokens=(
                "hierarchy_decision",
                "containment_current",
                "child_state_current",
                "ancestor_rollup_current",
                "hierarchy_projection_current",
                "ui_reachable",
            ),
            reason=(
                "each registered root/child Matter points to one current terminal "
                "owner receipt at every ordered hierarchy stage and every pointer "
                "shares the same containment dependency revision"
            ),
        ),
        CaseRule(
            case_id="hierarchy_stage_missing_or_stale",
            decision="hierarchy_work_scheduled",
            label="hierarchy_work_scheduled",
            writes=(
                "orchestration.integration_status",
                "orchestration.hierarchy_stage_terminal_index",
                "orchestration.hierarchy_freshness_status",
                "orchestration.work_item_registry",
            ),
            side_effects=("coverage_ledger_write", "work_dispatch_write"),
            emitted_tokens=("HierarchyWorkScheduled", "WorkScheduled"),
            reason=(
                "a missing, out-of-order, stale, or revision-mismatched hierarchy "
                "stage blocks per-Matter completion and schedules the exact owner"
            ),
        ),
        CaseRule(
            case_id="hierarchy_depth_pending",
            decision="bounded_hierarchy_work_scheduled",
            label="bounded_hierarchy_work_scheduled",
            writes=(
                "orchestration.integration_status",
                "orchestration.depth_status",
                "orchestration.hierarchy_freshness_status",
                "orchestration.work_item_registry",
            ),
            side_effects=("work_dispatch_write",),
            emitted_tokens=("HierarchyDepthPending", "DepthWorkScheduled"),
            reason=(
                "known branches may remain usable, but a budget-exhausted deeper "
                "branch remains pending and prevents exhaustive hierarchy completion"
            ),
        ),
        CaseRule(
            case_id="old_or_new_ancestor_chain_stale",
            decision="ancestor_recompute_scheduled",
            label="ancestor_recompute_scheduled",
            writes=(
                "orchestration.integration_status",
                "orchestration.hierarchy_freshness_status",
                "orchestration.work_item_registry",
            ),
            side_effects=("work_dispatch_write",),
            emitted_tokens=("AncestorRecomputeRequired", "WorkScheduled"),
            reason=(
                "a child or containment revision cannot reach projection until C10 "
                "and original owners terminate for both old and new ancestor chains"
            ),
        ),
        CaseRule(
            case_id="missing_or_stale_stage_work",
            decision="work_scheduled",
            label="work_scheduled",
            writes=(
                "orchestration.integration_status",
                "orchestration.object_stage_terminal_index",
                "orchestration.work_item_registry",
                "orchestration.worker_checkpoint",
            ),
            side_effects=("coverage_ledger_write", "work_dispatch_write", "worker_checkpoint_write"),
            emitted_tokens=("ObjectCoverageLedgerCurrent", "WorkScheduled", "WorkerCheckpoint"),
            reason="missing or stale owner stages are deterministically scheduled without user confirmation",
        ),
        CaseRule(
            case_id="typed_finding_owner_join_pending",
            decision="original_owner_join_required",
            label="original_owner_join_required",
            writes=(
                "orchestration.child_receipt_set",
                "orchestration.integration_status",
                "orchestration.work_item_registry",
            ),
            side_effects=("work_dispatch_write", "orchestration_receipt_write"),
            emitted_tokens=("OriginalOwnerDispatch", "RecomputeRequired"),
            reason="a validated finding cannot reach C12 until its declared owner returns one terminal result",
        ),
        CaseRule(
            case_id="owner_result_coverage_join_mismatch",
            decision="exact_owner_result_rejoined_or_pending",
            label="exact_owner_result_rejoined_or_pending",
            writes=(
                "orchestration.child_receipt_set",
                "orchestration.object_stage_terminal_index",
                "orchestration.depth_status",
                "orchestration.hierarchy_stage_terminal_index",
                "orchestration.hierarchy_freshness_status",
            ),
            side_effects=("coverage_ledger_write",),
            emitted_tokens=(
                "ObjectCoverageLedgerCurrent",
                "RecomputeRequired",
            ),
            reason=(
                "M0 maps the exact persisted semantic-depth and hierarchy-owner "
                "results into their coverage pointers, propagates stale/recomputed "
                "owner revisions, and leaves every missing owner result pending; "
                "it never fabricates a current stage from registration alone"
            ),
        ),
        CaseRule(
            case_id="matter_semantic_depth_rollup_current",
            decision="aggregate_matter_depth_current",
            label="aggregate_matter_depth_current",
            writes=(
                "orchestration.object_stage_terminal_index",
                "orchestration.depth_status",
            ),
            side_effects=("coverage_ledger_write",),
            emitted_tokens=(
                "ObjectCoverageLedgerCurrent",
                "DepthCurrent",
            ),
            reason=(
                "M0 accepts Matter depth only from the exact canonical C6 "
                "admission, strictly parsed source revision references, and "
                "current descendant source-depth, exact-version evidence, "
                "explicitly terminal original-owner, human bilingual C12 projection, logical-event "
                "timeline, people/relations, supplemental disposition, material-activity, "
                "and Matter-only hierarchy-owner results; occurrence-only not-applicable "
                "processing stages are never treated as Matter evidence, while an "
                "explicit not-applicable original-owner disposition remains terminal"
            ),
        ),
        CaseRule(
            case_id="one_object_blocked_others_progress",
            decision="object_blocked_progress_continues",
            label="object_blocked_progress_continues",
            writes=(
                "orchestration.object_stage_terminal_index",
                "orchestration.blocked_object_count",
                "orchestration.integration_status",
            ),
            side_effects=("coverage_ledger_write",),
            emitted_tokens=("ObjectBlocked", "ObjectCoverageLedgerCurrent"),
            reason="one blocked object is terminally visible while unrelated work keeps advancing",
        ),
        CaseRule(
            case_id="progressive_inventory_partial",
            decision="inventory_progress_visible_not_complete",
            label="inventory_progress_visible_not_complete",
            writes=(
                "orchestration.integration_status",
                "orchestration.coverage_status",
                "orchestration.object_coverage_ledger_revision",
            ),
            side_effects=("coverage_ledger_write",),
            emitted_tokens=("CoveragePartial", "ObjectCoverageLedgerCurrent"),
            reason="current partial inventory is visible but cannot support a complete coverage claim",
        ),
        CaseRule(
            case_id="semantic_depth_partial",
            decision="depth_work_scheduled",
            label="depth_work_scheduled",
            writes=(
                "orchestration.integration_status",
                "orchestration.depth_status",
                "orchestration.work_item_registry",
            ),
            side_effects=("work_dispatch_write",),
            emitted_tokens=("DepthWorkScheduled",),
            reason=(
                "missing, blocked, or stale occurrence or aggregate-Matter "
                "depth obligations schedule bounded owner work"
            ),
        ),
        CaseRule(
            case_id="hero_localization_supplemental_or_ui_gap",
            decision="projection_work_scheduled",
            label="projection_work_scheduled",
            writes=(
                "orchestration.integration_status",
                "orchestration.object_stage_terminal_index",
                "orchestration.generated_hero_status",
                "orchestration.supplemental_information_status",
                "orchestration.surface_evidence_status",
                "orchestration.work_item_registry",
            ),
            side_effects=("coverage_ledger_write", "work_dispatch_write"),
            emitted_tokens=("ProjectionWorkScheduled",),
            reason=(
                "an admitted Matter lacks a generated hero terminal, bilingual "
                "localization, supplemental-information terminal, exact eight-section "
                "UI reachability, or current 8766 surface evidence"
            ),
        ),
        CaseRule(
            case_id="material_clue_summary_or_activity_gap",
            decision="activity_projection_work_scheduled",
            label="activity_projection_work_scheduled",
            writes=(
                "orchestration.integration_status",
                "orchestration.object_stage_terminal_index",
                "orchestration.material_clue_projection_status",
                "orchestration.work_item_registry",
            ),
            side_effects=("coverage_ledger_write", "work_dispatch_write"),
            emitted_tokens=("MaterialClueProjectionWorkScheduled",),
            reason=(
                "a new material clue is not complete until the same current revision "
                "has bilingual Matter/ancestor summaries, latest-clue timestamps, "
                "stable activity ordering, and a published catalog projection"
            ),
        ),
        CaseRule(
            case_id="daily_orchestrator_or_delegated_join_gap",
            decision="orchestration_join_work_scheduled",
            label="orchestration_join_work_scheduled",
            writes=(
                "orchestration.integration_status",
                "orchestration.maintenance_orchestrator_status",
                "orchestration.delegated_result_join_status",
                "orchestration.work_item_registry",
            ),
            side_effects=("coverage_ledger_write", "work_dispatch_write"),
            emitted_tokens=("OrchestrationJoinWorkScheduled",),
            reason=(
                "one strongest compatible primary Codex profile owns the daily plan "
                "and terminal claim; delegated cheaper work remains incomplete until "
                "its typed result is validated and joined by that owner"
            ),
        ),
        CaseRule(
            case_id="researchguard_pending",
            decision="research_release_blocked_nonresearch_continues",
            label="research_release_blocked_nonresearch_continues",
            writes=("orchestration.integration_status", "orchestration.research_status"),
            side_effects=("orchestration_receipt_write",),
            emitted_tokens=("ResearchGuardPending", "ReleaseBlocked"),
            reason="non-research autonomous work continues but complete v0.1 release cannot claim research",
        ),
        CaseRule(
            case_id="stale_child_receipt",
            decision="freshness_blocked",
            label="freshness_blocked",
            writes=("orchestration.integration_status", "orchestration.work_item_registry"),
            side_effects=("work_dispatch_write",),
            emitted_tokens=("StaleChildReceipt", "WorkScheduled"),
            reason="a stale child receipt invalidates the parent snapshot and schedules its owner",
        ),
        CaseRule(
            case_id="unconsumed_child_output",
            decision="integration_gap_blocked",
            label="integration_gap_blocked",
            writes=("orchestration.integration_status",),
            side_effects=("orchestration_receipt_write",),
            emitted_tokens=("UnconsumedOutput", "M0BlockedReceipt"),
            reason="every declared child output must have one downstream consumer or typed terminal",
        ),
        CaseRule(
            case_id="correction_invalidates_downstream",
            decision="recompute_scheduled",
            label="recompute_scheduled",
            writes=(
                "orchestration.child_receipt_set",
                "orchestration.integration_status",
                "orchestration.object_stage_terminal_index",
                "orchestration.work_item_registry",
            ),
            side_effects=("coverage_ledger_write", "work_dispatch_write"),
            emitted_tokens=("InvalidatedChildReceipts", "RecomputeRequired"),
            reason="optional correction or revocation invalidates and schedules exact affected owners",
        ),
        CaseRule(
            case_id="restart_from_checkpoint",
            decision="worker_resumed_missing_only",
            label="worker_resumed_missing_only",
            writes=(
                "orchestration.worker_checkpoint",
                "orchestration.worker_health",
                "orchestration.work_item_registry",
            ),
            side_effects=("work_dispatch_write", "worker_checkpoint_write"),
            emitted_tokens=("WorkerCheckpoint", "WorkScheduled"),
            reason="restart revalidates authorization/freshness and resumes only nonterminal work",
        ),
        CaseRule(
            case_id="unchanged_rescan",
            decision="no_delta",
            label="no_delta",
            writes=("orchestration.worker_checkpoint",),
            side_effects=("worker_checkpoint_write",),
            emitted_tokens=("NoDelta", "WorkerCheckpoint"),
            reason="an unchanged inventory and policy creates no duplicate analysis or projection work",
        ),
        CaseRule(
            case_id="capability_route_pending_or_unavailable",
            decision="capability_work_pending_visible",
            label="capability_work_pending_visible",
            writes=(
                "orchestration.analysis_status",
                "orchestration.capability_route_status",
                "orchestration.work_item_registry",
            ),
            side_effects=("coverage_ledger_write", "work_dispatch_write"),
            emitted_tokens=("CapabilityPending", "WorkScheduled"),
            reason=(
                "an unavailable or underpowered Codex mapping preserves the exact "
                "capability gap and may schedule compatible escalation without "
                "fabricating terminal semantic work"
            ),
        ),
        CaseRule(
            case_id="shared_invocation_no_delta",
            decision="shared_invocation_no_delta_current",
            label="shared_invocation_no_delta_current",
            writes=(
                "orchestration.worker_checkpoint",
            ),
            side_effects=("orchestration_receipt_write", "worker_checkpoint_write"),
            emitted_tokens=("NoDelta", "WorkerCheckpoint"),
            reason=(
                "an interactive or scheduled adapter calls the same shared service "
                "path and records no-delta without duplicate work; schedule evidence "
                "remains owned by DevelopmentProcessFlow"
            ),
        ),
        CaseRule(
            case_id="shared_invocation_interrupted",
            decision="shared_invocation_checkpoint_preserved",
            label="shared_invocation_checkpoint_preserved",
            writes=(
                "orchestration.worker_checkpoint",
                "orchestration.worker_health",
            ),
            side_effects=("orchestration_receipt_write", "worker_checkpoint_write"),
            emitted_tokens=("WorkerCheckpoint",),
            reason=(
                "an interrupted shared invocation remains non-pass and resumes from "
                "durable current authorization on the next invocation"
            ),
        ),
        CaseRule(
            case_id="owner_redispatch_without_codex",
            decision="passed_result_redispatched_to_original_owner",
            label="passed_result_redispatched_to_original_owner",
            writes=(
                "orchestration.worker_checkpoint",
                "orchestration.worker_health",
                "orchestration.owner_redispatch_count",
            ),
            side_effects=("worker_checkpoint_write",),
            emitted_tokens=(
                "WorkerCheckpoint",
                "OriginalOwnerDispatch",
                "OwnerRedispatchIsolated",
            ),
            reason=(
                "a passed current AI result whose original-owner dispatch was "
                "blocked is resumable from an indexed result page without a "
                "Codex runner or broad pending-package enumeration; source "
                "analysis expansion, projection-repair/hero preparation, and "
                "supplemental research are deferred to the next cycle so the "
                "recovery cannot fan out new AI work"
            ),
        ),
        CaseRule(
            case_id="codex_runner_unavailable",
            decision="waiting_for_codex_with_bounded_backoff",
            label="waiting_for_codex_with_bounded_backoff",
            writes=(
                "orchestration.worker_checkpoint",
                "orchestration.worker_health",
                "orchestration.worker_poll_due_at",
                "orchestration.foreground_availability",
            ),
            side_effects=("worker_checkpoint_write",),
            emitted_tokens=("WorkerCheckpoint", "ForegroundResponsive"),
            reason=(
                "when the desktop process has no Codex execution owner, it "
                "records waiting work from the indexed coverage ledger without "
                "re-enumerating private AI packages in a tight loop; bounded "
                "polling leaves the object browser responsive"
            ),
        ),
        CaseRule(
            case_id="codex_pending_page_requested",
            decision="bounded_current_package_page_returned",
            label="bounded_current_package_page_returned",
            writes=(
                "orchestration.worker_checkpoint",
                "orchestration.foreground_availability",
            ),
            side_effects=("worker_checkpoint_write",),
            emitted_tokens=("WorkScheduled", "ForegroundResponsive"),
            reason=(
                "the Codex worker resolves current package, result, migration, "
                "source, dependency, and coverage rows in bounded owner-indexed "
                "sets; it never asks SQLite to correlate the full snapshot "
                "history once per package"
            ),
        ),
        CaseRule(
            case_id="scheduled_adapter_attempts_forbidden_action_or_final_gate",
            decision="scheduled_scope_escape_rejected",
            label="scheduled_scope_escape_rejected",
            writes=("orchestration.worker_health",),
            side_effects=("orchestration_receipt_write",),
            emitted_tokens=("M0BlockedReceipt",),
            reason=(
                "routine scheduling cannot mutate files or Gmail, send outbound "
                "actions, expand grants, edit product code/models, or own final "
                "model, test, install, Git, tag, or release gates"
            ),
        ),
        CaseRule(
            case_id="parent_attempts_child_write",
            decision="foreign_write_rejected",
            label="foreign_write_rejected",
            emitted_tokens=("OwnershipViolation", "M0BlockedReceipt"),
            reason="M0 coordinates pointers and work but never copies or writes a C1-C12 fact",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-M0-043-ledger-current-without-first-gap-index",
            protected_error_class="coverage_diagnostic_index_missing",
            description=(
                "the ledger is marked current without a matching first-gap "
                "index for every registered object"
            ),
            protected_harm=(
                "the one-click audit cannot explain where objects stopped and "
                "falls back to a full-ledger scan"
            ),
            case_id="coverage_ledger_and_first_gap_index_current",
            broken_decision="coverage_ledger_current_without_gap_index",
            broken_writes=(
                "orchestration.object_coverage_ledger_revision",
                "orchestration.coverage_first_gap_index",
            ),
            broken_side_effects=("coverage_ledger_write",),
            broken_tokens=("ObjectCoverageLedgerCurrent",),
        ),
        HazardSpec(
            failure_id="H-M0-044-registered-or-excluded-counted-ui-ready",
            protected_error_class="coverage_terminal_ui_readiness_conflation",
            description=(
                "registered, excluded, or source-only terminal objects are "
                "counted as admitted Matter UI readiness"
            ),
            protected_harm=(
                "coverage appears green although real modeled Matters have not "
                "reached the object browser"
            ),
            case_id="coverage_ledger_and_first_gap_index_current",
            broken_decision="all_registered_objects_counted_ui_ready",
            broken_writes=(
                "orchestration.ui_ready_object_count",
                "orchestration.coverage_status",
            ),
            broken_side_effects=("coverage_ledger_write",),
            broken_tokens=("AllAdmittedMattersUIReady",),
        ),
        HazardSpec(
            failure_id="H-M0-045-codex-project-source-lane-missing",
            protected_error_class="codex_source_universe_omission",
            description=(
                "authorized Codex projects are absent from the source registry, "
                "source groups, semantic stages, or UI relations"
            ),
            protected_harm=(
                "software work is fragmented or invisible despite being part of "
                "the user's authorized source universe"
            ),
            case_id="codex_project_source_inventory_current",
            broken_decision="codex_sources_not_registered",
            broken_writes=(
                "orchestration.codex_source_coverage_status",
                "orchestration.object_stage_terminal_index",
            ),
            broken_side_effects=("coverage_ledger_write",),
            broken_tokens=("SourceUniverseTerminal",),
        ),
        HazardSpec(
            failure_id="H-M0-046-mixed-graph-or-duplicate-timeline-counted-ready",
            protected_error_class="semantic_ui_stage_false_terminal",
            description=(
                "a mixed-type hierarchy graph or duplicate logical-event timeline "
                "is accepted as current UI readiness"
            ),
            protected_harm=(
                "the pipeline reports complete while the visible Matter model is "
                "still structurally wrong"
            ),
            case_id="source_groups_graph_world_model_and_ui_current",
            broken_decision="situation_object_browser_pipeline_current",
            broken_writes=(
                "orchestration.matter_hierarchy_projection_status",
                "orchestration.logical_event_projection_status",
                "orchestration.ui_ready_object_count",
            ),
            broken_side_effects=("coverage_ledger_write",),
            broken_tokens=("AllAdmittedMattersUIReady",),
        ),
        HazardSpec(
            failure_id="H-M0-047-empty-people-or-supplemental-counted-depth-current",
            protected_error_class="matter_depth_empty_lane_false_current",
            description=(
                "empty people/relationship or supplemental lanes are treated as "
                "current without a supported terminal unavailable disposition"
            ),
            protected_harm=(
                "semantic depth looks complete while important human context is "
                "missing and no work is scheduled"
            ),
            case_id="matter_semantic_depth_rollup_current",
            broken_decision="aggregate_matter_depth_current",
            broken_writes=(
                "orchestration.people_relation_status",
                "orchestration.supplemental_information_status",
                "orchestration.depth_status",
            ),
            broken_side_effects=("coverage_ledger_write",),
            broken_tokens=("DepthCurrent",),
        ),
        HazardSpec(
            failure_id="H-M0-048-versioned-source-ref-false-stale",
            protected_error_class="matter_semantic_depth_source_ref_mismatch",
            description=(
                "a versioned Matter source reference is queried as a source "
                "object id, so valid exact-version evidence is reported stale "
                "and an explicit not-applicable owner terminal is reported open"
            ),
            protected_harm=(
                "all canonical Matters can be falsely classified as stale, "
                "hiding the smaller set of real source, activity, and hierarchy gaps"
            ),
            case_id="matter_semantic_depth_rollup_current",
            broken_decision="versioned_source_ref_false_stale",
            broken_writes=(
                "orchestration.object_stage_terminal_index",
                "orchestration.depth_status",
            ),
            broken_side_effects=("coverage_ledger_write",),
            broken_tokens=("RecomputeRequired",),
        ),
        HazardSpec(
            failure_id="H-M0-042-gmail-metadata-reconciliation-dispatches-semantics",
            protected_error_class="gmail_metadata_reconciliation_owner_expansion",
            description=(
                "the metadata-owner repair is reported current after it "
                "downgrades body content, accepts a noncurrent owner, or "
                "dispatches extraction, evidence, analysis, Matter, or projection"
            ),
            protected_harm=(
                "M0 hides a source completeness gap behind fabricated semantic "
                "progress and can overwrite deeper provider truth"
            ),
            case_id="gmail_metadata_owner_reconciliation_current",
            broken_decision="gmail_metadata_owner_semantic_dispatch",
            broken_writes=(
                "orchestration.gmail_metadata_owner_reconciliation_status",
                "orchestration.object_coverage_ledger_revision",
                "orchestration.analysis_status",
            ),
            broken_side_effects=(
                "coverage_ledger_write",
                "work_dispatch_write",
            ),
            broken_tokens=(
                "GmailMetadataOwnerReconciliationCurrent",
                "AnalysisTerminal",
            ),
        ),
        HazardSpec(
            failure_id="H-M0-043-gmail-receipt-or-scope-repair-false-current",
            protected_error_class="gmail_receipt_scope_join_false_current",
            description=(
                "M0 reports current after a receipt was fabricated without "
                "exact digest/length/evidence, after a provider read/body copy, "
                "or after ambiguous current scope was silently selected"
            ),
            protected_harm=(
                "the one-click audit hides an authorization or content-proof "
                "gap and exposes downstream semantic work as licensed"
            ),
            case_id="gmail_legacy_content_receipts_and_current_scope_terminal",
            broken_decision="gmail_receipt_and_scope_false_current",
            broken_writes=(
                "orchestration.gmail_content_receipt_rebase_status",
                "orchestration.gmail_current_scope_reconciliation_status",
                "orchestration.coverage_status",
            ),
            broken_side_effects=("coverage_ledger_write",),
            broken_tokens=("GmailCurrentScopeReconciliationTerminal",),
        ),
        HazardSpec(
            failure_id="H-M0-044-source-revision-repair-joins-wrong-matter",
            protected_error_class="source_revision_target_join_false_current",
            description=(
                "M0 reports source revision repair current after a duplicate "
                "semantic follow-up, title-similarity Matter selection, duplicate "
                "root creation, retained old-revision evidence membership, a "
                "retried stale sibling, or a missing or duplicate current "
                "successor"
            ),
            protected_harm=(
                "the original Matter remains stale or semantically mixed while "
                "coverage and UI are marked current"
            ),
            case_id="annotation_followups_and_source_revisions_terminal",
            broken_decision="source_revision_repair_false_current",
            broken_writes=(
                "orchestration.annotation_followup_reconciliation_status",
                "orchestration.source_revision_analysis_status",
                "orchestration.source_revision_reconciliation_status",
                "orchestration.coverage_status",
            ),
            broken_side_effects=("coverage_ledger_write",),
            broken_tokens=(
                "SourceRevisionSuccessorSetCurrent",
                "SourceRevisionReconciliationCurrent",
            ),
        ),
        HazardSpec(
            failure_id="H-M0-040-gmail-continuation-invokes-semantic-owner",
            protected_error_class="gmail_continuation_owner_expansion",
            description=(
                "the deterministic Gmail body continuation directly creates "
                "or changes Matter, person, event, analysis, or projection state"
            ),
            protected_harm=(
                "a narrow transport/provenance leaf becomes a second semantic "
                "success path and model/API availability changes import behavior"
            ),
            case_id="gmail_body_continuation_prefix_current",
            broken_decision="gmail_body_continuation_semantic_dispatch",
            broken_writes=(
                "orchestration.gmail_body_continuation_status",
                "orchestration.object_coverage_ledger_revision",
                "orchestration.analysis_status",
            ),
            broken_side_effects=(
                "coverage_ledger_write",
                "work_dispatch_write",
            ),
            broken_tokens=(
                "GmailBodyContinuationPrefixCurrent",
                "AnalysisTerminal",
            ),
        ),
        HazardSpec(
            failure_id="H-M0-041-gmail-no-text-remains-open-or-fabricated",
            protected_error_class="gmail_no_text_coverage_false_state",
            description=(
                "a proven no_text_body remains pending forever, is marked "
                "available, or reaches a semantic work package"
            ),
            protected_harm=(
                "coverage never closes or falsely claims textual evidence and "
                "semantic modeling for absent MIME text"
            ),
            case_id="gmail_no_text_body_terminal",
            broken_decision="gmail_no_text_body_semantic_dispatch",
            broken_writes=(
                "orchestration.gmail_body_continuation_status",
                "orchestration.object_coverage_ledger_revision",
                "orchestration.analysis_status",
            ),
            broken_side_effects=(
                "coverage_ledger_write",
                "work_dispatch_write",
            ),
            broken_tokens=(
                "GmailNoTextBodyTerminal",
                "AnalysisTerminal",
            ),
        ),
        HazardSpec(
            failure_id="H-M0-034-storage-migration-order-or-recovery-bypassed",
            protected_error_class="storage_migration_recovery_false_complete",
            description=(
                "coverage history is archived before anchor-pointer rebase, "
                "originals are retired before verification, or a partial page "
                "is reported as the completed migration"
            ),
            protected_harm=(
                "private evidence references or exact coverage history become "
                "unrecoverable while M0 claims the store current"
            ),
            case_id="explicit_storage_migrations_terminal_in_safe_order",
            broken_decision="storage_migrations_terminal",
            broken_writes=(
                "orchestration.coverage_history_archive_status",
                "orchestration.coverage_history_archive_verification",
                "orchestration.storage_migration_order_status",
            ),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("CoverageHistoryArchiveTerminal",),
        ),
        HazardSpec(
            failure_id="H-M0-035-migration-runs-vacuum-or-claims-shrink",
            protected_error_class="storage_migration_physical_compaction_escape",
            description=(
                "logical pointer/archive maintenance runs VACUUM, VACUUM INTO, "
                "or claims physical database shrink"
            ),
            protected_harm=(
                "an offline high-disk rewrite is hidden inside routine startup "
                "or maintenance without backup, capacity, integrity, or activation evidence"
            ),
            case_id="explicit_storage_migrations_terminal_in_safe_order",
            broken_decision="storage_migrations_compacted_database",
            broken_writes=("orchestration.physical_compaction_status",),
            broken_side_effects=("coverage_ledger_write",),
            broken_tokens=("MaintenanceRebaseTerminal",),
        ),
        HazardSpec(
            failure_id="H-M0-033-parent-narrative-false-join",
            protected_error_class="parent_narrative_scope_false_complete",
            description=(
                "M0 marks a parent overview current when it is merely the latest "
                "child summary or lacks current complete child/evidence bindings"
            ),
            protected_harm=(
                "the UI displays an incomplete subtask summary as the project overview"
            ),
            case_id="parent_narrative_complete_scope_current",
            broken_decision="latest_child_summary_joined_as_parent_narrative",
            broken_writes=("orchestration.parent_narrative_status",),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("ParentNarrativeCurrent",),
        ),
        HazardSpec(
            failure_id="H-M0-028-current-contract-repair-owner-missing",
            protected_error_class="current_contract_reconciliation_false_join",
            description=(
                "M0 reports current coverage while tracked-only rebase, orphan "
                "reconciliation, parent composition, or canonicalization lacks "
                "a current owner receipt"
            ),
            protected_harm=(
                "ghost or duplicate objects appear complete and reach the UI"
            ),
            case_id="current_contract_repair_owners_terminal",
            broken_decision="coverage_and_canonicalization_repairs_current",
            broken_writes=(
                "orchestration.coverage_contract_rebase_status",
                "orchestration.coverage_orphan_reconciliation_status",
                "orchestration.canonicalization_join_status",
            ),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("ObjectCoverageLedgerCurrent",),
        ),
        HazardSpec(
            failure_id="H-M0-029-bounded-payload-masks-unbounded-catalog-query",
            protected_error_class="catalog_query_shape_false_complete",
            description=(
                "M0 accepts a bounded HTTP/DOM page even though C12 constructs "
                "every private card before slicing"
            ),
            protected_harm=(
                "release confidence hides catalog cost that grows with the "
                "entire private inventory"
            ),
            case_id="catalog_indexed_page_and_visible_hydration_current",
            broken_decision="catalog_query_shape_current",
            broken_writes=("orchestration.catalog_query_shape_status",),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("CatalogQueryShapeCurrent",),
        ),
        HazardSpec(
            failure_id="H-M0-031-service-startup-runs-catalog-migrations",
            protected_error_class="foreground_startup_catalog_amplification",
            description=(
                "constructing the service enumerates current projections or "
                "coverage and rewrites hierarchy, activity, locale, or hero rows"
            ),
            protected_harm=(
                "the desktop and 8766 browser time out while memory and CPU are "
                "consumed by hidden full-catalog maintenance"
            ),
            case_id="interactive_service_started_with_legacy_rows",
            broken_decision="startup_full_catalog_rebase_started",
            broken_writes=(
                "orchestration.foreground_availability",
                "orchestration.maintenance_rebase_status",
            ),
            broken_side_effects=("worker_checkpoint_write",),
            broken_tokens=("ForegroundResponsive",),
        ),
        HazardSpec(
            failure_id="H-M0-032-maintenance-rebase-loses-continuation",
            protected_error_class="maintenance_rebase_continuation_loss",
            description=(
                "a bounded legacy-row page is treated as the completed migration"
            ),
            protected_harm=(
                "unvisited private rows remain stale while a current receipt "
                "claims full schema and UI readiness"
            ),
            case_id="explicit_maintenance_rebase_terminal",
            broken_decision="maintenance_rebase_terminal",
            broken_writes=(
                "orchestration.maintenance_rebase_cursor",
                "orchestration.maintenance_rebase_status",
            ),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("MaintenanceRebaseTerminal",),
        ),
        HazardSpec(
            failure_id="H-M0-023-unclaimed-filesystem-workers-overlap",
            protected_error_class="filesystem_batch_execution_overlap",
            description=(
                "two workers select the same registered files without a claim token"
            ),
            protected_harm=(
                "duplicate extraction and revision races corrupt restart evidence"
            ),
            case_id="registered_filesystem_batch_claimed",
            broken_decision="overlapping_filesystem_batches_started",
            broken_writes=("orchestration.filesystem_stage_checkpoint",),
            broken_side_effects=("worker_checkpoint_write",),
            broken_tokens=("FilesystemStageCheckpoint",),
        ),
        HazardSpec(
            failure_id="H-M0-024-expired-claim-loses-interrupted-stage",
            protected_error_class="filesystem_stage_resume_gap",
            description=(
                "a crash after source registration advances coverage but leaves "
                "no recoverable claim stage"
            ),
            protected_harm=(
                "a registered file permanently disappears between source and UI"
            ),
            case_id="registered_filesystem_batch_claimed",
            broken_decision="interrupted_file_not_reselected",
            broken_writes=("orchestration.filesystem_claim_lease",),
            broken_tokens=("FilesystemClaimLease",),
        ),
        HazardSpec(
            failure_id="H-M0-025-unbounded-source-package-fanout",
            protected_error_class="source_analysis_derivative_unbounded",
            description=(
                "one large source synchronously materializes every derived AI "
                "package before the filesystem worker can checkpoint progress"
            ),
            protected_harm=(
                "one document monopolizes the worker, strands a large lease, "
                "and prevents other registered user files from advancing"
            ),
            case_id="source_analysis_expansion_pending",
            broken_decision="unbounded_analysis_fanout_started",
            broken_writes=(
                "orchestration.source_analysis_expansion_cursor",
                "orchestration.worker_checkpoint",
            ),
            broken_side_effects=("work_dispatch_write",),
            broken_tokens=("SourceAnalysisExpansionCursor",),
        ),
        HazardSpec(
            failure_id="H-M0-026-bounded-expansion-truncates-anchors",
            protected_error_class="source_analysis_anchor_loss",
            description=(
                "a bounded package page is treated as the complete source "
                "instead of retaining a resumable cursor"
            ),
            protected_harm=(
                "later anchors silently disappear from AI consideration"
            ),
            case_id="source_analysis_expansion_complete",
            broken_decision="analysis_expansion_terminal",
            broken_writes=(
                "orchestration.source_analysis_expansion_status",
            ),
            broken_tokens=("SourceAnalysisExpansionTerminal",),
        ),
        HazardSpec(
            failure_id="H-M0-001-incomplete-ledger-claimed-current",
            protected_error_class="object_coverage_false_complete",
            description="M0 claims current while a required object stage is missing or stale",
            protected_harm="registered user content disappears behind a complete claim",
            case_id="missing_or_stale_stage_work",
            broken_decision="end_to_end_current",
            broken_writes=("orchestration.integration_status",),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt",),
        ),
        HazardSpec(
            failure_id="H-M0-002-stale-child-accepted",
            protected_error_class="stale_child_false_green",
            description="M0 commits using a stale child receipt",
            protected_harm="parent evidence no longer describes the integrated snapshot",
            case_id="stale_child_receipt",
            broken_decision="end_to_end_current",
            broken_writes=("orchestration.integration_status",),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt",),
        ),
        HazardSpec(
            failure_id="H-M0-003-unconsumed-output-ignored",
            protected_error_class="integration_output_loss",
            description="M0 commits with an unconsumed child output",
            protected_harm="a modeled obligation silently disappears between owners",
            case_id="unconsumed_child_output",
            broken_decision="end_to_end_current",
            broken_writes=("orchestration.integration_status",),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt",),
        ),
        HazardSpec(
            failure_id="H-M0-004-parent-writes-child-state",
            protected_error_class="parent_child_ownership_violation",
            description="M0 directly writes a field owned by a child",
            protected_harm="the coordinator becomes a competing canonical authority",
            case_id="parent_attempts_child_write",
            broken_decision="child_state_written",
            broken_writes=("matter.lifecycle_axes",),
            broken_tokens=("LifecycleState",),
        ),
        HazardSpec(
            failure_id="H-M0-005-correction-keeps-stale-receipts",
            protected_error_class="correction_invalidation_failure",
            description="affected child receipts remain current after correction",
            protected_harm="withdrawn evidence still supports downstream conclusions",
            case_id="correction_invalidates_downstream",
            broken_decision="end_to_end_current",
            broken_writes=("orchestration.integration_status",),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt",),
        ),
        HazardSpec(
            failure_id="H-M0-006-partial-inventory-claimed-complete",
            protected_error_class="source_universe_false_complete",
            description="M0 commits while inventory pages or items are nonterminal",
            protected_harm="unprocessed user content is hidden",
            case_id="progressive_inventory_partial",
            broken_decision="end_to_end_current",
            broken_writes=("orchestration.integration_status", "orchestration.coverage_status"),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt", "SourceUniverseTerminal"),
        ),
        HazardSpec(
            failure_id="H-M0-007-shallow-depth-claimed-complete",
            protected_error_class="semantic_depth_false_complete",
            description="M0 commits while semantic depth work remains",
            protected_harm="missing evidence or contradictions are hidden",
            case_id="semantic_depth_partial",
            broken_decision="end_to_end_current",
            broken_writes=("orchestration.integration_status", "orchestration.depth_status"),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt", "DepthCurrent"),
        ),
        HazardSpec(
            failure_id="H-M0-008-researchguard-pending-release",
            protected_error_class="research_integration_false_release",
            description="M0 declares complete v0.1 while ResearchGuard is pending",
            protected_harm="the release claims a research capability that is unavailable",
            case_id="researchguard_pending",
            broken_decision="end_to_end_current",
            broken_writes=("orchestration.integration_status", "orchestration.research_status"),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt", "ResearchCurrent"),
        ),
        HazardSpec(
            failure_id="H-M0-009-original-owner-join-bypassed",
            protected_error_class="original_owner_join_bypass",
            description="a validated AI finding reaches C12 before its owner terminates",
            protected_harm="AI output becomes canonical through a shadow path",
            case_id="typed_finding_owner_join_pending",
            broken_decision="end_to_end_current",
            broken_writes=("orchestration.integration_status",),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt",),
        ),
        HazardSpec(
            failure_id="H-M0-030-owner-result-not-joined-to-coverage",
            protected_error_class="owner_result_coverage_code_boundary_mismatch",
            description=(
                "a current semantic-depth or hierarchy owner result is durable "
                "but its ObjectCoverageLedger pointer remains missing or stale"
            ),
            protected_harm=(
                "registered objects can never honestly reach UI-ready even though "
                "the original owner completed, while direct green writes could "
                "hide a genuinely missing owner result"
            ),
            case_id="owner_result_coverage_join_mismatch",
            broken_decision="owner_result_ignored_or_stage_fabricated_current",
            broken_writes=(
                "orchestration.object_stage_terminal_index",
                "orchestration.depth_status",
                "orchestration.hierarchy_stage_terminal_index",
            ),
            broken_side_effects=("coverage_ledger_write",),
            broken_tokens=("M0IntegrationReceipt",),
        ),
        HazardSpec(
            failure_id="H-M0-036-matter-depth-borrows-occurrence-not-applicable",
            protected_error_class="matter_semantic_depth_false_complete",
            description=(
                "a canonical Matter is assessed with occurrence criteria, so "
                "its not-applicable extraction and analysis stages falsely "
                "license semantic sufficiency"
            ),
            protected_harm=(
                "the object browser can present a large Matter as understood "
                "without current descendant sources, evidence, activity, "
                "hierarchy, or bilingual semantic projection"
            ),
            case_id="matter_semantic_depth_rollup_current",
            broken_decision="occurrence_not_applicable_false_green",
            broken_writes=(
                "orchestration.object_stage_terminal_index",
                "orchestration.depth_status",
            ),
            broken_side_effects=("coverage_ledger_write",),
            broken_tokens=("DepthCurrent",),
        ),
        HazardSpec(
            failure_id="H-M0-010-blocked-object-stops-all-progress",
            protected_error_class="global_progress_starvation",
            description="one blocked object prevents unrelated objects from advancing",
            protected_harm="the first run never converges despite independent work",
            case_id="one_object_blocked_others_progress",
            broken_decision="global_worker_blocked",
            broken_writes=("orchestration.worker_health",),
            broken_tokens=("M0BlockedReceipt",),
        ),
        HazardSpec(
            failure_id="H-M0-011-restart-duplicates-work",
            protected_error_class="worker_restart_duplication",
            description="restart redispatches terminal work and duplicates state",
            protected_harm="coverage counts and Matter revisions diverge after recovery",
            case_id="restart_from_checkpoint",
            broken_decision="worker_resumed_all_work",
            broken_writes=("orchestration.work_item_registry",),
            broken_side_effects=("work_dispatch_write",),
            broken_tokens=("WorkScheduled",),
            ignore_idempotency=True,
        ),
        HazardSpec(
            failure_id="H-M0-012-no-delta-rescan-duplicates-analysis",
            protected_error_class="unchanged_rescan_duplication",
            description="unchanged rescan schedules duplicate AI or projection work",
            protected_harm="background maintenance creates duplicate findings and unstable cards",
            case_id="unchanged_rescan",
            broken_decision="work_scheduled",
            broken_writes=("orchestration.work_item_registry",),
            broken_side_effects=("work_dispatch_write",),
            broken_tokens=("WorkScheduled",),
        ),
        HazardSpec(
            failure_id="H-M0-013-ui-ready-gap-claimed-complete",
            protected_error_class="ui_reachability_false_complete",
            description=(
                "an admitted Matter without generated hero terminal, localization, "
                "supplemental-information terminal, eight-section UI, or current "
                "surface evidence is counted complete"
            ),
            protected_harm="modeled content exists but cannot be reviewed by its first user",
            case_id="hero_localization_supplemental_or_ui_gap",
            broken_decision="end_to_end_current",
            broken_writes=("orchestration.integration_status",),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("AllAdmittedMattersUIReady",),
        ),
        HazardSpec(
            failure_id="H-M0-028-material-clue-projection-gap-claimed-complete",
            protected_error_class="material_clue_end_to_end_false_complete",
            description="a material clue reaches only some of summary, ancestor rollup, order, or UI",
            protected_harm="the ledger looks complete while the object browser remains stale or contradictory",
            case_id="material_clue_summary_or_activity_gap",
            broken_decision="end_to_end_current",
            broken_writes=(
                "orchestration.integration_status",
                "orchestration.material_clue_projection_status",
            ),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt", "MaterialClueProjectionCurrent"),
        ),
        HazardSpec(
            failure_id="H-M0-029-unjoined-delegated-result-claimed-complete",
            protected_error_class="maintenance_orchestrator_join_false_complete",
            description="a cheaper delegated result becomes terminal without primary-orchestrator validation",
            protected_harm="low-cost classification or generation can bypass semantic and safety review",
            case_id="daily_orchestrator_or_delegated_join_gap",
            broken_decision="end_to_end_current",
            broken_writes=(
                "orchestration.integration_status",
                "orchestration.delegated_result_join_status",
            ),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt", "DelegatedResultJoinCurrent"),
        ),
        HazardSpec(
            failure_id="H-M0-014-hierarchy-stage-gap-claimed-complete",
            protected_error_class="hierarchy_pipeline_false_complete",
            description="M0 claims a Matter current while a required hierarchy stage is missing, stale, or out of order",
            protected_harm="registered hierarchy work disappears before reaching the reviewable UI",
            case_id="hierarchy_stage_missing_or_stale",
            broken_decision="end_to_end_current",
            broken_writes=(
                "orchestration.integration_status",
                "orchestration.hierarchy_freshness_status",
            ),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt", "ui_reachable"),
        ),
        HazardSpec(
            failure_id="H-M0-015-hierarchy-depth-pending-claimed-complete",
            protected_error_class="hierarchy_depth_false_complete",
            description="M0 reports exhaustive hierarchy completion while deeper branches remain pending",
            protected_harm="bounded first-pass modeling is misrepresented as complete coverage",
            case_id="hierarchy_depth_pending",
            broken_decision="end_to_end_current",
            broken_writes=("orchestration.integration_status", "orchestration.depth_status"),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt", "DepthCurrent"),
        ),
        HazardSpec(
            failure_id="H-M0-016-old-ancestor-chain-stays-current",
            protected_error_class="ancestor_invalidation_false_current",
            description="a reparent or child-state revision leaves an old or new ancestor chain current",
            protected_harm="root cards, child tables, and rollups disagree after hierarchy change",
            case_id="old_or_new_ancestor_chain_stale",
            broken_decision="end_to_end_current",
            broken_writes=(
                "orchestration.integration_status",
                "orchestration.hierarchy_freshness_status",
            ),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt", "hierarchy_projection_current"),
        ),
        HazardSpec(
            failure_id="H-M0-017-capability-gap-claimed-terminal",
            protected_error_class="capability_route_false_complete",
            description="M0 marks semantic work current while its required capability is unavailable",
            protected_harm="unexecuted or underpowered AI work disappears from the coverage ledger",
            case_id="capability_route_pending_or_unavailable",
            broken_decision="end_to_end_current",
            broken_writes=("orchestration.integration_status", "orchestration.capability_route_status"),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt", "CapabilityRouteTerminal"),
        ),
        HazardSpec(
            failure_id="H-M0-018-shared-no-delta-duplicates-work",
            protected_error_class="shared_invocation_no_delta_duplication",
            description="a no-delta shared invocation creates duplicate analysis or Matter revisions",
            protected_harm="interactive or scheduled maintenance destabilizes the user's object browser",
            case_id="shared_invocation_no_delta",
            broken_decision="work_scheduled",
            broken_writes=("orchestration.work_item_registry",),
            broken_side_effects=("work_dispatch_write",),
            broken_tokens=("WorkScheduled",),
        ),
        HazardSpec(
            failure_id="H-M0-019-interrupted-shared-invocation-claimed-pass",
            protected_error_class="shared_invocation_false_success",
            description="an interrupted shared invocation is recorded current",
            protected_harm="stale files and mail appear fully reconciled",
            case_id="shared_invocation_interrupted",
            broken_decision="shared_invocation_no_delta_current",
            broken_writes=("orchestration.integration_status",),
            broken_side_effects=("orchestration_receipt_write",),
            broken_tokens=("M0IntegrationReceipt",),
        ),
        HazardSpec(
            failure_id="H-M0-022-no-runner-skips-owner-redispatch",
            protected_error_class="owner_dispatch_recovery_lost",
            description=(
                "no-runner optimization skips a passed result that only needs "
                "original-owner redispatch"
            ),
            protected_harm=(
                "validated semantic work stays blocked even after its owner prerequisite recovers"
            ),
            case_id="owner_redispatch_without_codex",
            broken_decision="waiting_for_codex_with_bounded_backoff",
            broken_writes=("orchestration.worker_health",),
            broken_tokens=("WorkerCheckpoint",),
        ),
        HazardSpec(
            failure_id="H-M0-028-owner-recovery-fans-out-new-ai-work",
            protected_error_class="owner_dispatch_recovery_fanout",
            description=(
                "an owner-redispatch cycle also expands source analysis, "
                "projection repair, hero generation, or supplemental research"
            ),
            protected_harm=(
                "restart recovery creates unrelated AI work before the exact "
                "original-owner disposition reaches a terminal state"
            ),
            case_id="owner_redispatch_without_codex",
            broken_decision="passed_result_redispatched_and_new_ai_work_scheduled",
            broken_writes=(
                "orchestration.owner_redispatch_count",
                "orchestration.work_item_registry",
            ),
            broken_side_effects=("work_dispatch_write",),
            broken_tokens=("OwnerRedispatchIsolated",),
        ),
        HazardSpec(
            failure_id="H-M0-021-no-runner-busy-loop-starves-ui",
            protected_error_class="foreground_starvation",
            description=(
                "a desktop worker with no Codex runner repeatedly enumerates "
                "private analysis packages without bounded backoff"
            ),
            protected_harm=(
                "background bookkeeping monopolizes CPU and memory until the "
                "local object browser times out"
            ),
            case_id="codex_runner_unavailable",
            broken_decision="waiting_for_codex_busy_loop",
            broken_writes=(
                "orchestration.worker_health",
                "orchestration.foreground_availability",
            ),
            broken_side_effects=("worker_checkpoint_write",),
            broken_tokens=("ForegroundResponsive",),
        ),
        HazardSpec(
            failure_id="H-M0-027-pending-package-history-query-starves-worker",
            protected_error_class="analysis_pending_page_unbounded",
            description=(
                "one pending-package page uses correlated JSON subqueries over "
                "the historical snapshot table for every current package"
            ),
            protected_harm=(
                "a small Codex batch waits minutes merely to discover work, "
                "preventing autonomous annotation and timely UI updates"
            ),
            case_id="codex_pending_page_requested",
            broken_decision="historical_package_query_started",
            broken_writes=("orchestration.foreground_availability",),
            broken_side_effects=("worker_checkpoint_write",),
            broken_tokens=("ForegroundResponsive",),
        ),
        HazardSpec(
            failure_id="H-M0-020-daily-task-owns-final-or-mutation",
            protected_error_class="scheduled_scope_authority_escape",
            description="the routine task mutates source/mailbox state or executes final release verification",
            protected_harm="a background helper becomes an unreviewed external-action or release authority",
            case_id="scheduled_adapter_attempts_forbidden_action_or_final_gate",
            broken_decision="scheduled_action_executed",
            broken_writes=("release.status",),
            broken_side_effects=("external_mutation",),
            broken_tokens=("ReleaseCurrent",),
        ),
    ),
    risk_classes=(
        "state_transition",
        "ownership",
        "freshness",
        "integration",
        "coverage",
        "semantic_depth",
        "hierarchy",
        "capability_routing",
        "scheduled_maintenance",
        "liveness",
        "recovery",
        "side_effect",
    ),
    template_no_match_reason=(
        "No template owns the exact C1-C12 autonomous ObjectCoverageLedger, "
        "durable worker, material-clue activity projection, generated-hero/"
        "localization/eight-section UI readiness, and current-receipt mesh."
    ),
    blindspots=(
        "portable child refinement and exact producer-consumer schemas require current ModelMesh",
        "production conformance and private first-run usefulness require runtime and TestMesh evidence",
    ),
    claim_boundary=(
        "This model establishes abstract M0 orchestration, ObjectCoverageLedger "
        "terminality, automatic owner scheduling, object-isolated blocking, restart/"
        "no-delta liveness, ResearchGuard release gating, ordered hierarchy-stage "
        "terminality, ancestor freshness, model-agnostic capability gaps, "
        "shared-path daily orchestration/delegation/no-delta/interruption/authority "
        "boundaries, foreground startup without hidden catalog migration, explicit "
        "bounded pointer-rebase-before-history-archive migration continuation with "
        "backup, stopped-writer, verification, and recovery gates, exact semantic-"
        "depth/hierarchy owner-result joins, aggregate Matter depth separated "
        "from occurrence-only not-applicable stages, with "
        "missing-owner pending preservation, material-clue atomic projection, "
        "generated-hero and exact "
        "eight-section UI readiness, "
        "output consumption, and ownership hazards. It does not prove child "
        "refinement, concrete model availability, real provider coverage, installed "
        "desktop behavior, automation installation, private-run usefulness, a real "
        "private migration, physical compaction, or VACUUM safety."
    ),
)
