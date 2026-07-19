"""C1 Authorization, Candidate Scope, Tracking, and Coverage model."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C1_authorization_coverage",
    title="C1 Authorization, Tracking & Coverage",
    modeled_boundary=(
        "bounded source authorization, candidate-scope freeze, reversible "
        "tracking disposition, durable large-root partitioning, terminal "
        "coverage, revocation, and private-root activation"
    ),
    state_fields=(
        "authorization.status",
        "candidate_scope.revision",
        "tracking_policy.revision",
        "tracking.policy_path_context",
        "tracking.disposition",
        "tracking.user_intent",
        "tracking.source_catalog",
        "tracking.action_token_index",
        "coverage.status",
        "coverage.terminal_counts",
        "coverage.partition_manifest_revision",
        "coverage.partition_state",
        "connector.cursor",
        "capability_status.private_root",
    ),
    owned_write_fields=(
        "authorization.status",
        "candidate_scope.revision",
        "tracking_policy.revision",
        "tracking.policy_path_context",
        "tracking.disposition",
        "tracking.user_intent",
        "tracking.source_catalog",
        "tracking.action_token_index",
        "coverage.status",
        "coverage.terminal_counts",
        "coverage.partition_manifest_revision",
        "coverage.partition_state",
        "connector.cursor",
        "capability_status.private_root",
    ),
    side_effect_classes=(
        "provider_metadata_read",
        "partition_manifest_write",
        "tracking_disposition_write",
        "tracking_catalog_write",
        "private_root_activation",
    ),
    completion_evidence=(
        "CandidateScopeFrozen",
        "TrackingDisposition",
        "PolicyPathContext",
        "UserTrackingIntent",
        "SourceCatalogDisposition",
        "TrackingActionToken",
        "Tracked",
        "NotTracked",
        "MetadataOnly",
        "Unavailable",
        "ClassificationStale",
        "WorkScheduled",
        "CoverageComplete",
        "CoveragePartial",
        "PartitionManifest",
        "PartitionBoundary",
        "AccessGap",
        "Revoked",
        "PrivateRootStatus",
    ),
    rules=(
        CaseRule(
            case_id="candidate_scope_frozen",
            decision="candidate_scope_current",
            label="candidate_scope_current",
            writes=(
                "authorization.status",
                "candidate_scope.revision",
                "tracking_policy.revision",
                "coverage.status",
                "connector.cursor",
            ),
            side_effects=("provider_metadata_read",),
            emitted_tokens=("CandidateScopeFrozen", "CoveragePartial"),
            reason="authorized roots and mailbox policy are frozen before broad content reads",
        ),
        CaseRule(
            case_id="tracked_current",
            decision="tracked",
            label="tracked_current",
            writes=("tracking.disposition",),
            side_effects=("tracking_disposition_write",),
            emitted_tokens=("TrackingDisposition", "Tracked"),
            reason="current policy admits the occurrence to staged extraction",
        ),
        CaseRule(
            case_id="ai_not_tracked_current",
            decision="not_tracked",
            label="not_tracked_current",
            writes=("tracking.disposition",),
            side_effects=("tracking_disposition_write",),
            emitted_tokens=("TrackingDisposition", "NotTracked"),
            reason="a current, reversible, policy-licensed AI triage result records reason and confidence",
        ),
        CaseRule(
            case_id="ai_uncertain_or_protected",
            decision="metadata_only_protected",
            label="metadata_only_protected",
            writes=("tracking.disposition",),
            side_effects=("tracking_disposition_write",),
            emitted_tokens=("TrackingDisposition", "MetadataOnly"),
            reason=(
                "uncertain or protected content receives a conservative automatic "
                "metadata-only disposition with confidence and reason"
            ),
        ),
        CaseRule(
            case_id="temporarily_unavailable_item",
            decision="unavailable_terminal",
            label="unavailable_terminal",
            writes=("tracking.disposition", "coverage.status"),
            side_effects=("tracking_disposition_write",),
            emitted_tokens=("TrackingDisposition", "Unavailable", "AccessGap"),
            reason=(
                "a placeholder, denied object, or unsupported payload receives a "
                "terminal unavailable disposition while retry policy remains explicit"
            ),
        ),
        CaseRule(
            case_id="all_items_and_pages_terminal",
            decision="coverage_complete",
            label="coverage_complete",
            writes=("coverage.status", "coverage.terminal_counts", "connector.cursor"),
            emitted_tokens=("CoverageComplete",),
            reason="every enumerated item and required page has one current terminal disposition",
        ),
        CaseRule(
            case_id="nonterminal_or_missing_page",
            decision="coverage_partial",
            label="coverage_partial",
            writes=("coverage.status", "coverage.terminal_counts", "connector.cursor"),
            emitted_tokens=("CoveragePartial", "AccessGap"),
            reason="missing page, unknown item, or nonterminal worker state prevents a complete claim",
        ),
        CaseRule(
            case_id="large_root_budget_exceeded",
            decision="coverage_partitioned_partial",
            label="coverage_partitioned_partial",
            writes=(
                "coverage.status",
                "coverage.partition_manifest_revision",
                "coverage.partition_state",
            ),
            side_effects=("partition_manifest_write",),
            emitted_tokens=("PartitionManifest", "CoveragePartial"),
            reason=(
                "a bounded resource failure checkpoints direct entries and safe "
                "child scopes instead of holding the whole tree in memory"
            ),
        ),
        CaseRule(
            case_id="parent_partition_boundary",
            decision="not_tracked_delegated_partition",
            label="not_tracked_delegated_partition",
            writes=("tracking.disposition", "coverage.partition_state"),
            side_effects=(
                "tracking_disposition_write",
                "partition_manifest_write",
            ),
            emitted_tokens=(
                "TrackingDisposition",
                "NotTracked",
                "PartitionBoundary",
            ),
            reason=(
                "the parent directory boundary is terminal routing evidence while "
                "its declared child scope owns content coverage"
            ),
        ),
        CaseRule(
            case_id="partition_child_retains_policy_context",
            decision="partition_policy_context_current",
            label="partition_policy_context_current",
            writes=(
                "tracking.policy_path_context",
                "tracking.disposition",
            ),
            side_effects=("tracking_disposition_write",),
            emitted_tokens=(
                "PolicyPathContext",
                "TrackingDisposition",
                "NotTracked",
            ),
            reason=(
                "a child scope retains original-root path policy tokens so a "
                "generated-state ancestor cannot disappear at a partition"
            ),
        ),
        CaseRule(
            case_id="generated_state_pruned_before_partition",
            decision="hard_excluded_before_descent",
            label="hard_excluded_before_descent",
            writes=(
                "tracking.policy_path_context",
                "tracking.disposition",
                "coverage.partition_state",
            ),
            side_effects=(
                "tracking_disposition_write",
                "partition_manifest_write",
            ),
            emitted_tokens=(
                "PolicyPathContext",
                "TrackingDisposition",
                "NotTracked",
                "PartitionBoundary",
            ),
            reason=(
                "known software-control, dependency, cache, build, and temporary "
                "directories receive a terminal policy disposition before the "
                "partition coordinator creates descendant work"
            ),
        ),
        CaseRule(
            case_id="partition_child_pending_failed_or_stale",
            decision="coverage_partial_partition_open",
            label="coverage_partial_partition_open",
            writes=(
                "coverage.status",
                "coverage.partition_manifest_revision",
                "coverage.partition_state",
            ),
            emitted_tokens=("PartitionManifest", "CoveragePartial", "AccessGap"),
            reason=(
                "a missing, failed, interrupted, or stale required child "
                "partition prevents aggregate completion"
            ),
        ),
        CaseRule(
            case_id="partition_checkpoint_batch_progress",
            decision="bounded_checkpoint_progress",
            label="bounded_checkpoint_progress",
            writes=(
                "coverage.partition_manifest_revision",
                "coverage.partition_state",
            ),
            side_effects=("partition_manifest_write",),
            emitted_tokens=("PartitionManifest", "CoveragePartial"),
            reason=(
                "large inventories atomically checkpoint bounded node batches; "
                "an interruption may repeat only the current idempotent batch"
            ),
        ),
        CaseRule(
            case_id="bounded_child_scanned_before_further_partition",
            decision="bounded_subtree_inventory",
            label="bounded_subtree_inventory",
            writes=(
                "coverage.partition_manifest_revision",
                "coverage.partition_state",
            ),
            side_effects=(
                "provider_metadata_read",
                "partition_manifest_write",
            ),
            emitted_tokens=("PartitionManifest", "CoveragePartial"),
            reason=(
                "a root child is scanned as one bounded subtree and creates "
                "descendant partition nodes only after the scan exhausts the "
                "frozen per-scope entry budget"
            ),
        ),
        CaseRule(
            case_id="canary_smallest_sufficient_partition_first",
            decision="bounded_canary_extraction",
            label="bounded_canary_extraction",
            writes=(
                "coverage.partition_manifest_revision",
                "coverage.partition_state",
            ),
            side_effects=("provider_metadata_read",),
            emitted_tokens=("PartitionManifest", "CoveragePartial"),
            reason=(
                "a bounded content canary first selects the smallest current "
                "tracked partition that can fill the remaining sample, or the "
                "largest useful partial partition when none can"
            ),
        ),
        CaseRule(
            case_id="canary_stage_updates_batch_summary_once",
            decision="bounded_canary_summary_refresh",
            label="bounded_canary_summary_refresh",
            writes=(
                "coverage.status",
                "coverage.terminal_counts",
                "coverage.partition_state",
            ),
            side_effects=(
                "provider_metadata_read",
                "tracking_disposition_write",
            ),
            emitted_tokens=("PartitionManifest", "CoveragePartial"),
            reason=(
                "per-item source, evidence, analysis, original-owner dispatch, "
                "Matter, localization, visual, and projection stage updates "
                "defer global coverage aggregation until the bounded canary or "
                "one AI-result dispatch reaches its terminal join"
            ),
        ),
        CaseRule(
            case_id="gmail_budget_prioritizes_supplied_authorized_content",
            decision="bounded_gmail_content_ingestion",
            label="bounded_gmail_content_ingestion",
            writes=("coverage.status", "coverage.terminal_counts"),
            side_effects=("provider_metadata_read",),
            emitted_tokens=("Tracked", "CoveragePartial"),
            reason=(
                "within a bounded Gmail content budget, tracked messages whose "
                "authorized page already supplies content are selected before "
                "tracked metadata-only messages while the exact limit remains "
                "enforced"
            ),
        ),
        CaseRule(
            case_id="all_partitions_and_items_terminal",
            decision="coverage_complete_partitioned",
            label="coverage_complete_partitioned",
            writes=(
                "coverage.status",
                "coverage.terminal_counts",
                "coverage.partition_manifest_revision",
                "coverage.partition_state",
            ),
            emitted_tokens=("PartitionManifest", "CoverageComplete"),
            reason=(
                "the exact partition manifest and every required child scope "
                "and occurrence are current and terminal"
            ),
        ),
        CaseRule(
            case_id="tracking_policy_changed",
            decision="classification_stale_work_scheduled",
            label="classification_stale_work_scheduled",
            writes=("tracking_policy.revision", "tracking.disposition", "coverage.status"),
            emitted_tokens=(
                "TrackingDisposition",
                "ClassificationStale",
                "WorkScheduled",
                "CoveragePartial",
            ),
            reason="a policy revision invalidates and automatically reschedules affected tracking decisions",
        ),
        CaseRule(
            case_id="policy_changed_after_user_override",
            decision="user_tracking_intent_preserved",
            label="user_tracking_intent_preserved",
            writes=(
                "tracking_policy.revision",
                "tracking.user_intent",
                "tracking.disposition",
                "coverage.status",
            ),
            side_effects=("tracking_disposition_write",),
            emitted_tokens=(
                "UserTrackingIntent",
                "TrackingDisposition",
                "CoveragePartial",
            ),
            reason=(
                "a policy-only reconciliation preserves an explicit user "
                "intent until the user replaces it or authorization is revoked"
            ),
        ),
        CaseRule(
            case_id="source_catalog_action_current",
            decision="source_catalog_action_token_published",
            label="source_catalog_action_token_published",
            writes=("tracking.source_catalog", "tracking.action_token_index"),
            side_effects=("tracking_catalog_write",),
            emitted_tokens=("SourceCatalogDisposition", "TrackingActionToken"),
            reason=(
                "one current source occurrence, source revision, policy revision, "
                "and disposition produce one opaque action token; supersession "
                "invalidates the prior token"
            ),
        ),
        CaseRule(
            case_id="outside_scope",
            decision="access_blocked",
            label="access_blocked",
            writes=("coverage.status",),
            emitted_tokens=("AccessGap",),
            reason="object, link target, or operation is outside authorization",
        ),
        CaseRule(
            case_id="authorization_revoked",
            decision="revoked_blocked",
            label="revoked_blocked",
            writes=("authorization.status", "coverage.status"),
            emitted_tokens=("Revoked", "RecomputeRequest"),
            reason="revocation stops reads and invalidates dependents",
        ),
        CaseRule(
            case_id="private_root_outside_git",
            decision="private_root_active",
            label="private_root_active",
            writes=("capability_status.private_root",),
            side_effects=("private_root_activation",),
            emitted_tokens=("PrivateRootStatus",),
            reason="configured private root is physically outside public build and Git roots",
        ),
        CaseRule(
            case_id="installed_private_root_single_physical_authority",
            decision="private_root_identity_current",
            label="private_root_identity_current",
            writes=("capability_status.private_root",),
            side_effects=("private_root_activation",),
            emitted_tokens=("PrivateRootStatus",),
            reason=(
                "the installed default uses one non-virtualized user-profile "
                "directory so Python files and native SQLite resolve to the "
                "same physical private authority"
            ),
        ),
        CaseRule(
            case_id="private_root_inside_git",
            decision="private_root_blocked",
            label="private_root_blocked",
            writes=("capability_status.private_root",),
            emitted_tokens=("PrivateRootStatus", "AccessGap"),
            reason="inside-Git private roots are forbidden without fallback",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-C1-001-out-of-scope-read",
            protected_error_class="authorization_scope_escape",
            description="out-of-scope content or link target is read",
            protected_harm="private content is fetched without authority",
            case_id="outside_scope",
            broken_decision="candidate_scope_current",
            broken_writes=("authorization.status", "coverage.status", "connector.cursor"),
            broken_side_effects=("provider_metadata_read",),
            broken_tokens=("CandidateScopeFrozen", "CoverageComplete"),
        ),
        HazardSpec(
            failure_id="H-C1-002-nonterminal-claimed-complete",
            protected_error_class="coverage_overclaim",
            description="a missing page or nonterminal worker state is counted as complete",
            protected_harm="downstream decisions rely on missing work as if terminal",
            case_id="nonterminal_or_missing_page",
            broken_decision="coverage_complete",
            broken_writes=("coverage.status", "coverage.terminal_counts", "connector.cursor"),
            broken_tokens=("CoverageComplete",),
        ),
        HazardSpec(
            failure_id="H-C1-003-ai-silently-excludes-protected",
            protected_error_class="triage_authority_escape",
            description="uncertain AI output silently excludes a protected source",
            protected_harm="valuable user content disappears from inventory and modeling",
            case_id="ai_uncertain_or_protected",
            broken_decision="not_tracked",
            broken_writes=("tracking.disposition",),
            broken_side_effects=("tracking_disposition_write",),
            broken_tokens=("TrackingDisposition", "NotTracked"),
        ),
        HazardSpec(
            failure_id="H-C1-004-policy-change-keeps-current-triage",
            protected_error_class="stale_tracking_decision_reuse",
            description="an old tracking decision remains current after policy change",
            protected_harm="coverage and analysis use an obsolete user policy",
            case_id="tracking_policy_changed",
            broken_decision="coverage_complete",
            broken_writes=("tracking_policy.revision", "coverage.status"),
            broken_tokens=("CoverageComplete",),
        ),
        HazardSpec(
            failure_id="H-C1-005-revoked-read-continues",
            protected_error_class="revocation_bypass",
            description="a revoked authorization continues to read",
            protected_harm="private data remains accessible after user revocation",
            case_id="authorization_revoked",
            broken_decision="candidate_scope_current",
            broken_writes=("authorization.status", "coverage.status", "connector.cursor"),
            broken_side_effects=("provider_metadata_read",),
            broken_tokens=("CandidateScopeFrozen",),
        ),
        HazardSpec(
            failure_id="H-C1-006-private-root-inside-git",
            protected_error_class="private_data_public_boundary_escape",
            description="an inside-Git private root is activated",
            protected_harm="private runtime data can enter public Git history",
            case_id="private_root_inside_git",
            broken_decision="private_root_active",
            broken_writes=("capability_status.private_root",),
            broken_side_effects=("private_root_activation",),
            broken_tokens=("PrivateRootStatus",),
        ),
        HazardSpec(
            failure_id="H-C1-007-partition-parent-overclaims-child",
            protected_error_class="partition_coverage_overclaim",
            description=(
                "a terminal parent boundary is treated as proof that a pending, "
                "failed, or stale child partition was inventoried"
            ),
            protected_harm=(
                "an authorized subtree disappears from coverage while aggregate "
                "status is reported complete"
            ),
            case_id="partition_child_pending_failed_or_stale",
            broken_decision="coverage_complete_partitioned",
            broken_writes=(
                "coverage.status",
                "coverage.terminal_counts",
                "coverage.partition_state",
            ),
            broken_tokens=("PartitionManifest", "CoverageComplete"),
        ),
        HazardSpec(
            failure_id="H-C1-008-resource-failure-amplifies-memory",
            protected_error_class="unbounded_inventory_materialization",
            description=(
                "a whole-root resource failure is retried with an unbounded "
                "entry budget instead of durable child partitioning"
            ),
            protected_harm=(
                "the first run can terminate with MemoryError before a complete "
                "or resumable inventory is recorded"
            ),
            case_id="large_root_budget_exceeded",
            broken_decision="coverage_complete",
            broken_writes=("coverage.status", "coverage.terminal_counts"),
            broken_side_effects=("provider_metadata_read",),
            broken_tokens=("CoverageComplete",),
        ),
        HazardSpec(
            failure_id="H-C1-009-partition-loses-policy-context",
            protected_error_class="partition_policy_context_loss",
            description=(
                "a child scope below generated state is reclassified as "
                "ordinary tracked content because its ancestor token vanished"
            ),
            protected_harm=(
                "software state and generated clutter overwhelm modeling and "
                "the object-browser surface"
            ),
            case_id="partition_child_retains_policy_context",
            broken_decision="tracked",
            broken_writes=(
                "tracking.policy_path_context",
                "tracking.disposition",
            ),
            broken_side_effects=("tracking_disposition_write",),
            broken_tokens=("TrackingDisposition", "Tracked"),
        ),
        HazardSpec(
            failure_id="H-C1-010-policy-erases-user-intent",
            protected_error_class="user_tracking_override_lost",
            description=(
                "a later policy revision silently replaces a current user "
                "tracking intent"
            ),
            protected_harm=(
                "the system reverses an explicit user decision without a new "
                "intent or revocation"
            ),
            case_id="policy_changed_after_user_override",
            broken_decision="policy_override_applied",
            broken_writes=(
                "tracking_policy.revision",
                "tracking.user_intent",
                "tracking.disposition",
            ),
            broken_side_effects=("tracking_disposition_write",),
            broken_tokens=("TrackingDisposition",),
        ),
        HazardSpec(
            failure_id="H-C1-011-stale-tracking-action-token",
            protected_error_class="tracking_action_revision_bypass",
            description=(
                "a token minted for an older source, policy, or catalog revision "
                "changes the current tracking disposition"
            ),
            protected_harm=(
                "a delayed UI action silently overwrites a newer classification"
            ),
            case_id="source_catalog_action_current",
            broken_decision="stale_tracking_action_applied",
            broken_writes=("tracking.disposition", "tracking.source_catalog"),
            broken_side_effects=("tracking_disposition_write",),
            broken_tokens=("TrackingDisposition",),
        ),
        HazardSpec(
            failure_id="H-C1-012-partition-checkpoint-write-amplification",
            protected_error_class="unbounded_partition_checkpoint_write_amplification",
            description=(
                "every completed directory rewrites and fsyncs the growing "
                "partition manifest instead of using bounded checkpoints"
            ),
            protected_harm=(
                "a correct large-root first run becomes operationally stuck "
                "before terminal inventory coverage is reached"
            ),
            case_id="partition_checkpoint_batch_progress",
            broken_decision="coverage_partial_partition_open",
            broken_writes=(
                "coverage.partition_manifest_revision",
                "coverage.partition_state",
            ),
            broken_side_effects=("partition_manifest_write",),
            broken_tokens=("PartitionManifest", "CoveragePartial"),
        ),
        HazardSpec(
            failure_id="H-C1-013-generated-state-descendant-expansion",
            protected_error_class="generated_state_partition_expansion",
            description=(
                "a known software-control or temporary directory is marked "
                "not tracked only after thousands of descendant partitions "
                "have already been scheduled"
            ),
            protected_harm=(
                "private first-run coverage is dominated by irrelevant runtime "
                "state and valuable user content is delayed or obscured"
            ),
            case_id="generated_state_pruned_before_partition",
            broken_decision="coverage_partial_partition_open",
            broken_writes=(
                "tracking.policy_path_context",
                "tracking.disposition",
                "coverage.partition_state",
            ),
            broken_side_effects=("partition_manifest_write",),
            broken_tokens=("PartitionManifest", "CoveragePartial"),
        ),
        HazardSpec(
            failure_id="H-C1-014-unconditional-descendant-partition-expansion",
            protected_error_class="unbounded_partition_node_expansion",
            description=(
                "every ordinary descendant directory becomes a partition node "
                "even when its complete subtree fits within the frozen budget"
            ),
            protected_harm=(
                "a finite user root expands into thousands of unnecessary "
                "checkpointed nodes and delays private first-run completion"
            ),
            case_id="bounded_child_scanned_before_further_partition",
            broken_decision="coverage_partial_partition_open",
            broken_writes=(
                "coverage.partition_manifest_revision",
                "coverage.partition_state",
            ),
            broken_side_effects=(
                "provider_metadata_read",
                "partition_manifest_write",
            ),
            broken_tokens=("PartitionManifest", "CoveragePartial"),
        ),
        HazardSpec(
            failure_id="H-C1-015-installed-private-root-alias-split",
            protected_error_class="private_runtime_path_alias_split",
            description=(
                "the installed default is placed under a Windows Store "
                "virtualized LocalAppData path where native SQLite and Python "
                "file operations can resolve different physical directories"
            ),
            protected_harm=(
                "one logical MATTERS_HOME silently splits database, manifests, "
                "receipts, and recovery evidence across two authorities"
            ),
            case_id="installed_private_root_single_physical_authority",
            broken_decision="private_root_active",
            broken_writes=("capability_status.private_root",),
            broken_side_effects=("private_root_activation",),
            broken_tokens=("PrivateRootStatus",),
        ),
        HazardSpec(
            failure_id="H-C1-016-canary-reinventories-largest-partition-first",
            protected_error_class="unbounded_canary_reinventory",
            description=(
                "a small content canary chooses an arbitrary large completed "
                "partition and fully re-inventories it before reading samples"
            ),
            protected_harm=(
                "a twenty-item private canary takes longer than the inventory "
                "stage and cannot serve as an early extraction gate"
            ),
            case_id="canary_smallest_sufficient_partition_first",
            broken_decision="coverage_partial_partition_open",
            broken_writes=(
                "coverage.partition_manifest_revision",
                "coverage.partition_state",
            ),
            broken_side_effects=("provider_metadata_read",),
            broken_tokens=("PartitionManifest", "CoveragePartial"),
        ),
        HazardSpec(
            failure_id="H-C1-017-canary-per-stage-global-summary-amplification",
            protected_error_class="per_item_global_summary_reaggregation",
            description=(
                "every source, evidence, analysis, original-owner, Matter, "
                "localization, visual, and projection stage update rescans the "
                "entire coverage ledger during one bounded canary or AI result"
            ),
            protected_harm=(
                "a small content sample or one multi-finding AI result performs "
                "dozens of full-table aggregations, repeatedly consumes "
                "gigabytes of memory, and can time out after partial dispatch"
            ),
            case_id="canary_stage_updates_batch_summary_once",
            broken_decision="coverage_partial_partition_open",
            broken_writes=(
                "coverage.status",
                "coverage.terminal_counts",
                "coverage.partition_state",
            ),
            broken_side_effects=(
                "provider_metadata_read",
                "tracking_disposition_write",
            ),
            broken_tokens=("PartitionManifest", "CoveragePartial"),
        ),
        HazardSpec(
            failure_id="H-C1-018-gmail-budget-selects-metadata-only-first",
            protected_error_class="gmail_content_budget_false_metadata_only",
            description=(
                "a bounded Gmail canary truncates tracked messages by opaque "
                "identifier before prioritizing messages whose authorized page "
                "actually supplies content"
            ),
            protected_harm=(
                "real authorized bodies are left unmodeled while the canary "
                "incorrectly reports only metadata-only content gaps"
            ),
            case_id="gmail_budget_prioritizes_supplied_authorized_content",
            broken_decision="coverage_partial",
            broken_writes=("coverage.status", "coverage.terminal_counts"),
            broken_side_effects=("provider_metadata_read",),
            broken_tokens=("Tracked", "CoveragePartial"),
        ),
    ),
    risk_classes=(
        "authorization",
        "coverage",
        "triage",
        "freshness",
        "revocation",
        "privacy",
        "resource",
        "side_effect",
    ),
    template_ids=("side_effect_at_most_once",),
    blindspots=(
        "live local and Gmail enumeration requires adapter conformance",
        "filesystem junction and cloud-placeholder behavior requires implementation tests",
        "partition-manifest crash recovery, bounded checkpoint and node amplification, and large-root completion require implementation and private-run evidence",
        "AI relevance quality requires private canaries and optional post-run correction",
    ),
    claim_boundary=(
        "This model establishes only bounded C1 authorization, candidate-scope, "
        "tracking, durable bounded partitioning, terminal-coverage, and privacy "
        "transitions. It does not prove live source completeness, AI "
        "classification quality, or private first-run coverage."
    ),
)
