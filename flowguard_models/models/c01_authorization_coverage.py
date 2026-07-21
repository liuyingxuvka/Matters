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
        "candidate_scope.active",
        "tracking_policy.revision",
        "tracking.policy_path_context",
        "tracking.deterministic_content_class",
        "tracking.disposition",
        "tracking.user_intent",
        "tracking.source_catalog",
        "coverage.status",
        "coverage.terminal_counts",
        "coverage.active_object_count",
        "coverage.partition_manifest_revision",
        "coverage.partition_state",
        "coverage.stage_schema_revision",
        "coverage.stage_schema_rebase_cursor",
        "coverage.orphan_reconciliation_cursor",
        "coverage.current_full_payload_revision",
        "coverage.noncurrent_history_archive",
        "coverage.noncurrent_history_archive_count",
        "coverage.noncurrent_history_archive_digest",
        "coverage.history_archive_cursor",
        "coverage.history_archive_verification",
        "coverage.gmail_metadata_owner_reconciliation_gate",
        "coverage.gmail_current_scope_reconciliation_status",
        "coverage.gmail_current_scope_reconciliation_cursor",
        "coverage.gmail_content_receipt_rebase_status",
        "coverage.gmail_content_receipt_rebase_cursor",
        "coverage.gmail_body_manifest_identity",
        "coverage.gmail_body_batch_number",
        "connector.cursor",
        "capability_status.private_root",
    ),
    owned_write_fields=(
        "authorization.status",
        "candidate_scope.revision",
        "candidate_scope.active",
        "tracking_policy.revision",
        "tracking.policy_path_context",
        "tracking.deterministic_content_class",
        "tracking.disposition",
        "tracking.user_intent",
        "tracking.source_catalog",
        "coverage.status",
        "coverage.terminal_counts",
        "coverage.active_object_count",
        "coverage.partition_manifest_revision",
        "coverage.partition_state",
        "coverage.stage_schema_revision",
        "coverage.stage_schema_rebase_cursor",
        "coverage.orphan_reconciliation_cursor",
        "coverage.current_full_payload_revision",
        "coverage.noncurrent_history_archive",
        "coverage.noncurrent_history_archive_count",
        "coverage.noncurrent_history_archive_digest",
        "coverage.history_archive_cursor",
        "coverage.history_archive_verification",
        "coverage.gmail_metadata_owner_reconciliation_gate",
        "coverage.gmail_current_scope_reconciliation_status",
        "coverage.gmail_current_scope_reconciliation_cursor",
        "coverage.gmail_content_receipt_rebase_status",
        "coverage.gmail_content_receipt_rebase_cursor",
        "coverage.gmail_body_manifest_identity",
        "coverage.gmail_body_batch_number",
        "connector.cursor",
        "capability_status.private_root",
    ),
    side_effect_classes=(
        "provider_metadata_read",
        "partition_manifest_write",
        "tracking_disposition_write",
        "tracking_catalog_write",
        "coverage_contract_rebase_write",
        "coverage_orphan_retirement_write",
        "coverage_history_archive_write",
        "gmail_metadata_reconciliation_admission",
        "gmail_current_scope_reconciliation",
        "gmail_content_receipt_rebase",
        "gmail_body_continuation_admission",
        "private_root_activation",
    ),
    completion_evidence=(
        "CandidateScopeFrozen",
        "TrackingDisposition",
        "PolicyPathContext",
        "DeterministicContentClass",
        "UserTrackingIntent",
        "SourceCatalogDisposition",
        "Tracked",
        "NotTracked",
        "HardExcluded",
        "MetadataOnly",
        "Unavailable",
        "ClassificationStale",
        "WorkScheduled",
        "CoverageComplete",
        "CoveragePartial",
        "PartitionManifest",
        "PartitionBoundary",
        "PolicyCurrentManifest",
        "ScopeRetired",
        "CoverageObjectRetired",
        "TrackedOnlyCoverageRebase",
        "CoverageOrphanReconciled",
        "CoverageCurrentPayloadFull",
        "CoverageHistoryArchiveExact",
        "CoverageHistoryArchiveCursor",
        "CoverageHistoryArchiveVerified",
        "GmailMetadataOwnerReconciliationAuthorized",
        "GmailCurrentScopeReconciled",
        "GmailCurrentScopePending",
        "GmailCurrentScopeBlocked",
        "GmailContentReceiptRebased",
        "GmailContentReceiptRebasePending",
        "GmailBodyContinuationAuthorized",
        "GmailNoTextBodyAuthorized",
        "GmailBodyContinuationRejected",
        "AccessGap",
        "Revoked",
        "PrivateRootStatus",
    ),
    rules=(
        CaseRule(
            case_id="active_tracked_legacy_coverage_rebased",
            decision="tracked_coverage_contract_current",
            label="tracked_coverage_contract_current",
            writes=(
                "coverage.stage_schema_revision",
                "coverage.stage_schema_rebase_cursor",
                "coverage.status",
            ),
            side_effects=("coverage_contract_rebase_write",),
            emitted_tokens=("TrackedOnlyCoverageRebase", "CoveragePartial"),
            reason=(
                "one bounded stable page adds the current content-selection "
                "stage only to active tracked occurrences and checkpoints the "
                "next continuation"
            ),
        ),
        CaseRule(
            case_id="retired_or_nontracked_legacy_coverage_seen",
            decision="historical_coverage_preserved_without_reopen",
            label="historical_coverage_preserved_without_reopen",
            writes=("coverage.stage_schema_rebase_cursor",),
            side_effects=("coverage_contract_rebase_write",),
            emitted_tokens=("TrackedOnlyCoverageRebase",),
            reason=(
                "retired, inactive, not-tracked, and hard-excluded rows remain "
                "historical and receive no new pending stage"
            ),
        ),
        CaseRule(
            case_id="active_source_coverage_missing_inventory",
            decision="coverage_orphan_retired",
            label="coverage_orphan_retired",
            writes=(
                "coverage.active_object_count",
                "coverage.orphan_reconciliation_cursor",
                "coverage.status",
            ),
            side_effects=("coverage_orphan_retirement_write",),
            emitted_tokens=("CoverageObjectRetired", "CoverageOrphanReconciled"),
            reason=(
                "an active source coverage row without one current inventory "
                "occurrence is append-only retired from counts, queues, and UI "
                "reachability while its history remains available"
            ),
        ),
        CaseRule(
            case_id="current_coverage_full_noncurrent_history_archived",
            decision="coverage_current_and_history_shape_current",
            label="coverage_current_and_history_shape_current",
            writes=(
                "coverage.current_full_payload_revision",
                "coverage.noncurrent_history_archive",
                "coverage.noncurrent_history_archive_count",
                "coverage.noncurrent_history_archive_digest",
                "coverage.history_archive_cursor",
                "coverage.history_archive_verification",
            ),
            side_effects=("coverage_history_archive_write",),
            emitted_tokens=(
                "CoverageCurrentPayloadFull",
                "CoverageHistoryArchiveExact",
                "CoverageHistoryArchiveCursor",
                "CoverageHistoryArchiveVerified",
            ),
            reason=(
                "one full current coverage payload remains directly queryable; "
                "a bounded page of replaced revisions is compressed in exact "
                "order and the archive is decompressed and verified for object, "
                "count, bytes, digest, and logical equality before originals "
                "may be retired"
            ),
        ),
        CaseRule(
            case_id="software_artifact_deterministically_excluded",
            decision="hard_excluded_before_ai",
            label="hard_excluded_before_ai",
            writes=(
                "tracking.deterministic_content_class",
                "tracking.disposition",
            ),
            side_effects=("tracking_disposition_write",),
            emitted_tokens=(
                "DeterministicContentClass",
                "TrackingDisposition",
                "HardExcluded",
            ),
            reason=(
                "software source, dependency manifest, runtime database, log, "
                "cache, generated state, executable, or unsafe model receives "
                "a terminal machine reason before any AI operation"
            ),
        ),
        CaseRule(
            case_id="ordinary_user_content_deterministically_admitted",
            decision="content_analysis_eligible",
            label="content_analysis_eligible",
            writes=(
                "tracking.deterministic_content_class",
                "tracking.disposition",
            ),
            side_effects=("tracking_disposition_write",),
            emitted_tokens=(
                "DeterministicContentClass",
                "TrackingDisposition",
                "Tracked",
            ),
            reason=(
                "supported documents, images, spreadsheets, presentations, "
                "user-authored text, and declared safe application exports or "
                "downloads may enter bounded extraction while application "
                "databases, logs, caches, sessions, and runtime state remain "
                "terminal"
            ),
        ),
        CaseRule(
            case_id="unknown_machine_format_deterministically_excluded",
            decision="hard_excluded_unknown_machine_format",
            label="hard_excluded_unknown_machine_format",
            writes=(
                "tracking.deterministic_content_class",
                "tracking.disposition",
            ),
            side_effects=("tracking_disposition_write",),
            emitted_tokens=(
                "DeterministicContentClass",
                "TrackingDisposition",
                "HardExcluded",
            ),
            reason=(
                "an unknown, extensionless, or machine-only format receives a "
                "terminal reason without execution, deserialization, content "
                "read, or AI submission"
            ),
        ),
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
            case_id="gmail_metadata_owner_exact_current_gate",
            decision="gmail_metadata_owner_reconciliation_authorized",
            label="gmail_metadata_owner_reconciliation_authorized",
            writes=(
                "coverage.gmail_metadata_owner_reconciliation_gate",
                "coverage.status",
            ),
            side_effects=("gmail_metadata_reconciliation_admission",),
            emitted_tokens=(
                "GmailMetadataOwnerReconciliationAuthorized",
                "CoveragePartial",
            ),
            reason=(
                "a verified terminal progressing Gmail page chain plus exactly "
                "one active current same-scope metadata-only message occurrence "
                "and ObjectCoverage row authorizes one bounded metadata owner "
                "repair; stale, foreign, ambiguous, or nonterminal input cannot write"
            ),
        ),
        CaseRule(
            case_id="gmail_single_newer_tracked_scope_current",
            decision="gmail_current_scope_atomically_reconciled",
            label="gmail_current_scope_atomically_reconciled",
            writes=(
                "coverage.gmail_current_scope_reconciliation_status",
                "coverage.gmail_current_scope_reconciliation_cursor",
                "coverage.status",
            ),
            side_effects=("gmail_current_scope_reconciliation",),
            emitted_tokens=(
                "GmailCurrentScopeReconciled",
                "CoveragePartial",
            ),
            reason=(
                "one exact bound metadata-only occurrence, one newer current "
                "same-account tracked occurrence, current policy, current "
                "SourceVersion, and current body or no-text disposition are "
                "rechecked in one CAS before the coverage scope switches"
            ),
        ),
        CaseRule(
            case_id="gmail_tracked_content_successor_after_policy_rebase",
            decision="gmail_current_scope_atomically_reconciled",
            label="gmail_current_scope_atomically_reconciled",
            writes=(
                "coverage.gmail_current_scope_reconciliation_status",
                "coverage.gmail_current_scope_reconciliation_cursor",
                "coverage.status",
            ),
            side_effects=("gmail_current_scope_reconciliation",),
            emitted_tokens=(
                "GmailCurrentScopeReconciled",
                "CoveragePartial",
            ),
            reason=(
                "one exact current tracked content successor remains eligible "
                "when a provider-read-free policy rebase wrote the bound "
                "metadata-only inventory later; exact body/no-text authority "
                "and the atomic CAS, not maintenance write time, license the switch"
            ),
        ),
        CaseRule(
            case_id="gmail_tracked_scope_ambiguous",
            decision="gmail_current_scope_blocked",
            label="gmail_current_scope_blocked",
            writes=(
                "coverage.gmail_current_scope_reconciliation_status",
                "coverage.gmail_current_scope_reconciliation_cursor",
            ),
            side_effects=("gmail_current_scope_reconciliation",),
            emitted_tokens=("GmailCurrentScopeBlocked",),
            reason=(
                "multiple current tracked scopes cannot be ranked by unrelated "
                "per-scope revisions, so existing coverage is preserved"
            ),
        ),
        CaseRule(
            case_id="gmail_current_body_disposition_missing",
            decision="gmail_current_scope_pending",
            label="gmail_current_scope_pending",
            writes=(
                "coverage.gmail_current_scope_reconciliation_status",
                "coverage.gmail_current_scope_reconciliation_cursor",
            ),
            side_effects=("gmail_current_scope_reconciliation",),
            emitted_tokens=("GmailCurrentScopePending",),
            reason=(
                "the tracked scope exists but no exact current body or "
                "no-text disposition licenses the scope switch; no provider "
                "read or partial coverage rewrite occurs"
            ),
        ),
        CaseRule(
            case_id="gmail_legacy_current_digest_and_evidence_exact",
            decision="gmail_content_receipt_rebased_without_provider_read",
            label="gmail_content_receipt_rebased_without_provider_read",
            writes=(
                "coverage.gmail_content_receipt_rebase_status",
                "coverage.gmail_content_receipt_rebase_cursor",
            ),
            side_effects=("gmail_content_receipt_rebase",),
            emitted_tokens=("GmailContentReceiptRebased",),
            reason=(
                "one registry-current tracked Gmail SourceVersion with an exact "
                "SHA-256 content fingerprint, positive derived byte count, and "
                "current evidence anchors for that same revision receives one "
                "minimized digest/length/evidence receipt with no provider read "
                "and no body copy"
            ),
        ),
        CaseRule(
            case_id="gmail_legacy_content_proof_incomplete",
            decision="gmail_content_receipt_rebase_pending",
            label="gmail_content_receipt_rebase_pending",
            writes=(
                "coverage.gmail_content_receipt_rebase_status",
                "coverage.gmail_content_receipt_rebase_cursor",
            ),
            side_effects=("gmail_content_receipt_rebase",),
            emitted_tokens=("GmailContentReceiptRebasePending",),
            reason=(
                "metadata, an invalid digest, a zero byte count, missing anchors, "
                "or evidence from another revision cannot manufacture content "
                "authority; the row remains visible without a provider read"
            ),
        ),
        CaseRule(
            case_id="gmail_body_continuation_exact_batch",
            decision="gmail_body_continuation_authorized",
            label="gmail_body_continuation_authorized",
            writes=(
                "coverage.gmail_body_manifest_identity",
                "coverage.gmail_body_batch_number",
                "coverage.status",
            ),
            side_effects=("gmail_body_continuation_admission",),
            emitted_tokens=(
                "GmailBodyContinuationAuthorized",
                "CoveragePartial",
            ),
            reason=(
                "the raw private manifest hash, exact 1-based batch membership, "
                "at-most-20 budget, minimal status-specific result projection, "
                "available bodies or proof-bound no-text dispositions, and "
                "current Gmail metadata owners are all validated before the "
                "continuation leaf may write"
            ),
        ),
        CaseRule(
            case_id="gmail_no_text_body_exact_disposition",
            decision="gmail_no_text_body_authorized",
            label="gmail_no_text_body_authorized",
            writes=(
                "coverage.gmail_body_manifest_identity",
                "coverage.gmail_body_batch_number",
                "coverage.status",
            ),
            side_effects=("gmail_body_continuation_admission",),
            emitted_tokens=(
                "GmailBodyContinuationAuthorized",
                "GmailNoTextBodyAuthorized",
                "CoveragePartial",
            ),
            reason=(
                "the exact manifest member contains body='', "
                "content_status=no_text_body, one domain-separated canonical-row "
                "sha256 connector raw-MIME recovery proof identity that the "
                "importer recomputes, and no current non-empty body"
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
            case_id="stale_partition_manifest_replaced",
            decision="policy_current_manifest_rebuilt",
            label="policy_current_manifest_rebuilt",
            writes=(
                "candidate_scope.revision",
                "candidate_scope.active",
                "coverage.partition_manifest_revision",
                "coverage.partition_state",
                "coverage.active_object_count",
            ),
            side_effects=(
                "partition_manifest_write",
                "tracking_catalog_write",
            ),
            emitted_tokens=(
                "PolicyCurrentManifest",
                "ScopeRetired",
                "CoverageObjectRetired",
                "CoveragePartial",
            ),
            reason=(
                "an obsolete manifest is directly replaced; omitted former "
                "child scopes and objects retain history but leave active work, "
                "Matter reachability, and UI counts"
            ),
        ),
        CaseRule(
            case_id="retired_occurrence_rediscovered",
            decision="active_coverage_reentered",
            label="active_coverage_reentered",
            writes=(
                "candidate_scope.active",
                "tracking.disposition",
                "coverage.active_object_count",
                "coverage.status",
            ),
            side_effects=(
                "tracking_disposition_write",
                "tracking_catalog_write",
            ),
            emitted_tokens=(
                "TrackingDisposition",
                "WorkScheduled",
                "CoveragePartial",
            ),
            reason=(
                "a current allowed rediscovery appends an active revision, "
                "clears obsolete non-applicable stages, and schedules the "
                "first required incomplete stage"
            ),
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
            failure_id="H-C1-024-coverage-archive-deletes-before-verification",
            protected_error_class="coverage_history_archive_recovery_loss",
            description=(
                "original noncurrent coverage rows are deleted before the "
                "compressed archive is reread and verified"
            ),
            protected_harm=(
                "interruption or corruption irreversibly removes exact private "
                "coverage history"
            ),
            case_id="current_coverage_full_noncurrent_history_archived",
            broken_decision="coverage_history_originals_deleted_unverified",
            broken_writes=(
                "coverage.noncurrent_history_archive",
                "coverage.history_archive_verification",
            ),
            broken_side_effects=("coverage_history_archive_write",),
            broken_tokens=("CoverageHistoryArchiveExact",),
        ),
        HazardSpec(
            failure_id="H-C1-022-coverage-rebase-reopens-retired-row",
            protected_error_class="tracked_only_coverage_rebase_escape",
            description=(
                "the current coverage schema rebase adds pending stages to an "
                "inactive, retired, not-tracked, or hard-excluded row"
            ),
            protected_harm=(
                "historical or excluded private objects re-enter work and "
                "prevent honest completion"
            ),
            case_id="retired_or_nontracked_legacy_coverage_seen",
            broken_decision="tracked_coverage_contract_current",
            broken_writes=("coverage.status",),
            broken_side_effects=("coverage_contract_rebase_write",),
            broken_tokens=("CoveragePartial",),
        ),
        HazardSpec(
            failure_id="H-C1-023-coverage-orphan-remains-active",
            protected_error_class="coverage_inventory_orphan_ghost",
            description=(
                "an active source coverage row with no current inventory "
                "occurrence remains in counts, queues, relationships, or UI"
            ),
            protected_harm=(
                "ghost work is permanently unfinished and can keep stale "
                "Matter reachability alive"
            ),
            case_id="active_source_coverage_missing_inventory",
            broken_decision="coverage_orphan_retained",
            broken_writes=(
                "coverage.active_object_count",
                "coverage.orphan_reconciliation_cursor",
            ),
            broken_side_effects=("coverage_orphan_retirement_write",),
            broken_tokens=("CoverageObjectRetired",),
        ),
        HazardSpec(
            failure_id="H-C1-013-software-artifact-sent-to-ai",
            protected_error_class="deterministic_admission_bypass",
            description="a policy-known software artifact is submitted to AI",
            protected_harm="tokens and private application state leave the intended user-content path",
            case_id="software_artifact_deterministically_excluded",
            broken_decision="tracked",
            broken_writes=("tracking.disposition",),
            broken_side_effects=("tracking_disposition_write",),
            broken_tokens=("TrackingDisposition", "Tracked"),
        ),
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
        HazardSpec(
            failure_id="H-C1-023-gmail-metadata-owner-gate-bypassed",
            protected_error_class="gmail_metadata_owner_scope_escape",
            description=(
                "metadata reconciliation accepts a nonterminal page chain or "
                "a stale, inactive, ambiguous, foreign-scope, non-message, or "
                "non-metadata-only inventory/coverage owner"
            ),
            protected_harm=(
                "the source registry fabricates current Gmail provenance from "
                "an incomplete or unauthorized ownership view"
            ),
            case_id="gmail_metadata_owner_exact_current_gate",
            broken_decision="gmail_metadata_owner_reconciliation_authorized",
            broken_writes=(
                "coverage.gmail_metadata_owner_reconciliation_gate",
                "coverage.status",
            ),
            broken_side_effects=("gmail_metadata_reconciliation_admission",),
            broken_tokens=("GmailMetadataOwnerReconciliationAuthorized",),
        ),
        HazardSpec(
            failure_id="H-C1-025-gmail-current-scope-ambiguity-guessed",
            protected_error_class="gmail_current_scope_ambiguity_bypass",
            description=(
                "two or more tracked Gmail scopes are ranked by scope id or "
                "unrelated per-scope revision and one is selected"
            ),
            protected_harm=(
                "coverage can be rebound to an unlicensed or semantically "
                "different mailbox view while the ambiguity is hidden"
            ),
            case_id="gmail_tracked_scope_ambiguous",
            broken_decision="gmail_current_scope_atomically_reconciled",
            broken_writes=(
                "coverage.gmail_current_scope_reconciliation_status",
                "coverage.gmail_current_scope_reconciliation_cursor",
                "coverage.status",
            ),
            broken_side_effects=("gmail_current_scope_reconciliation",),
            broken_tokens=("GmailCurrentScopeReconciled",),
        ),
        HazardSpec(
            failure_id="H-C1-026-gmail-current-scope-stale-partial-commit",
            protected_error_class="gmail_current_scope_cas_bypass",
            description=(
                "a bound scope, target inventory, policy, source, content "
                "receipt, or coverage input changes after selection but the "
                "coverage switch still partially commits"
            ),
            protected_harm=(
                "authorization and downstream coverage can point at different "
                "durable snapshots and falsely appear current"
            ),
            case_id="gmail_single_newer_tracked_scope_current",
            broken_decision="gmail_current_scope_partially_reconciled",
            broken_writes=(
                "coverage.gmail_current_scope_reconciliation_status",
                "coverage.status",
            ),
            broken_side_effects=("gmail_current_scope_reconciliation",),
            broken_tokens=("GmailCurrentScopeReconciled",),
        ),
        HazardSpec(
            failure_id="H-C1-027-policy-rebase-time-hides-content-successor",
            protected_error_class="gmail_current_scope_maintenance_time_ordering",
            description=(
                "a later policy-rebase write time on the bound metadata-only "
                "inventory incorrectly blocks the exact current tracked content "
                "successor"
            ),
            protected_harm=(
                "durable message bodies remain stranded outside current "
                "coverage solely because maintenance order was mistaken for "
                "provider-world recency"
            ),
            case_id="gmail_tracked_content_successor_after_policy_rebase",
            broken_decision="gmail_current_scope_blocked",
            broken_writes=(
                "coverage.gmail_current_scope_reconciliation_status",
                "coverage.gmail_current_scope_reconciliation_cursor",
            ),
            broken_side_effects=("gmail_current_scope_reconciliation",),
            broken_tokens=("GmailCurrentScopeBlocked",),
        ),
        HazardSpec(
            failure_id="H-C1-028-gmail-content-receipt-fabricated-from-metadata",
            protected_error_class="gmail_content_receipt_proof_bypass",
            description=(
                "metadata, a stale or foreign-revision anchor, an invalid "
                "digest, or a zero byte count is treated as enough proof to "
                "mint a current Gmail content receipt"
            ),
            protected_harm=(
                "current-scope coverage can claim licensed message content that "
                "was never durably and exactly evidenced"
            ),
            case_id="gmail_legacy_content_proof_incomplete",
            broken_decision="gmail_content_receipt_rebased_without_provider_read",
            broken_writes=(
                "coverage.gmail_content_receipt_rebase_status",
                "coverage.gmail_content_receipt_rebase_cursor",
            ),
            broken_side_effects=("gmail_content_receipt_rebase",),
            broken_tokens=("GmailContentReceiptRebased",),
        ),
        HazardSpec(
            failure_id="H-C1-029-gmail-content-receipt-rebase-copies-or-refetches",
            protected_error_class="gmail_content_receipt_rebase_privacy_escape",
            description=(
                "the legacy receipt repair rereads Gmail or stores message body "
                "text instead of deriving a minimized receipt from exact current proof"
            ),
            protected_harm=(
                "a provider-read-free repair becomes an unnecessary private "
                "content copy or connector access path"
            ),
            case_id="gmail_legacy_current_digest_and_evidence_exact",
            broken_decision="gmail_content_receipt_rebased_with_body_copy",
            broken_writes=(
                "coverage.gmail_content_receipt_rebase_status",
                "coverage.gmail_content_receipt_rebase_cursor",
            ),
            broken_side_effects=(
                "gmail_content_receipt_rebase",
                "provider_metadata_read",
            ),
            broken_tokens=("GmailContentReceiptRebased",),
        ),
        HazardSpec(
            failure_id="H-C1-021-gmail-continuation-expands-manifest",
            protected_error_class="gmail_continuation_scope_expansion",
            description=(
                "a foreign, missing, duplicated, oversized, hash-mismatched, "
                "or extra-field Gmail body result is accepted"
            ),
            protected_harm=(
                "private mail outside the frozen continuation batch can enter "
                "source/evidence state or connector transport fields can be retained"
            ),
            case_id="gmail_body_continuation_exact_batch",
            broken_decision="gmail_body_continuation_authorized",
            broken_writes=(
                "coverage.gmail_body_manifest_identity",
                "coverage.gmail_body_batch_number",
                "coverage.status",
            ),
            broken_side_effects=("gmail_body_continuation_admission",),
            broken_tokens=("GmailBodyContinuationAuthorized",),
        ),
        HazardSpec(
            failure_id="H-C1-022-gmail-no-text-body-unproven",
            protected_error_class="gmail_no_text_admission_bypass",
            description=(
                "an empty, blocked, or foreign result is accepted as "
                "no_text_body without exact empty body and one recomputable "
                "domain-separated canonical-row sha256 raw-MIME recovery proof"
            ),
            protected_harm=(
                "missing connector content is falsely reported as a proven "
                "terminal absence and the frozen manifest boundary is bypassed"
            ),
            case_id="gmail_no_text_body_exact_disposition",
            broken_decision="gmail_no_text_body_authorized",
            broken_writes=(
                "coverage.gmail_body_manifest_identity",
                "coverage.gmail_body_batch_number",
                "coverage.status",
            ),
            broken_side_effects=("gmail_body_continuation_admission",),
            broken_tokens=("GmailNoTextBodyAuthorized",),
        ),
        HazardSpec(
            failure_id="H-C1-019-unknown-machine-file-sent-to-ai",
            protected_error_class="unknown_machine_admission_bypass",
            description=(
                "an unknown or machine-only file is treated as useful content "
                "and submitted to AI"
            ),
            protected_harm=(
                "private binary/application state consumes analysis and can be "
                "misrepresented as user-authored evidence"
            ),
            case_id="unknown_machine_format_deterministically_excluded",
            broken_decision="tracked",
            broken_writes=(
                "tracking.deterministic_content_class",
                "tracking.disposition",
            ),
            broken_side_effects=("tracking_disposition_write",),
            broken_tokens=("TrackingDisposition", "Tracked"),
        ),
        HazardSpec(
            failure_id="H-C1-020-pruned-scope-remains-active",
            protected_error_class="retired_coverage_ghost_work",
            description=(
                "a child scope omitted by a current policy manifest remains in "
                "coverage, next-work, relation, or UI counts"
            ),
            protected_harm=(
                "deleted software state appears as permanent unfinished user "
                "work and prevents honest first-run closure"
            ),
            case_id="stale_partition_manifest_replaced",
            broken_decision="coverage_partial_partition_open",
            broken_writes=(
                "coverage.partition_manifest_revision",
                "coverage.partition_state",
                "coverage.active_object_count",
            ),
            broken_side_effects=("partition_manifest_write",),
            broken_tokens=("PartitionManifest", "CoveragePartial"),
        ),
        HazardSpec(
            failure_id="H-C1-021-retired-rediscovery-stays-terminal",
            protected_error_class="coverage_reactivation_loss",
            description=(
                "an eligible rediscovered occurrence keeps its retired "
                "not-applicable stages and never re-enters work"
            ),
            protected_harm=(
                "real user content remains silently absent after becoming "
                "authorized and trackable again"
            ),
            case_id="retired_occurrence_rediscovered",
            broken_decision="coverage_complete",
            broken_writes=(
                "candidate_scope.active",
                "coverage.active_object_count",
                "coverage.status",
            ),
            broken_tokens=("CoverageComplete",),
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
        "tracking, durable bounded partitioning, terminal-coverage, exact "
        "compressed noncurrent-history archival only after decompression-equivalence "
        "verification, and privacy transitions. It does not prove live source "
        "completeness, AI classification quality, private first-run coverage, a "
        "real private migration, physical SQLite shrinkage, or VACUUM safety."
    ),
)
