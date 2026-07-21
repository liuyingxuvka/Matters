"""C2 Source Registry, Inventory Snapshot, and Freshness model."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C2_source_registry",
    title="C2 Source Registry, Inventory & Freshness",
    modeled_boundary=(
        "immutable occurrence/source identity, inventory snapshots, change "
        "sets, source-in-place locator/fingerprint registration, storage-class "
        "and retention policy, versioning, content-selection semantic identity separated from "
        "inventory scan revision, safe real Images-gallery derivatives, "
        "stable SourceGroup projection, transient cleanup, source-unavailable "
        "preservation, freshness invalidation, no-delta, and tombstones"
    ),
    state_fields=(
        "source.identity",
        "source.version",
        "source.content_hash",
        "source.metadata_hash",
        "source.locator",
        "source.content_fingerprint",
        "source.metadata_fingerprint",
        "source.storage_class",
        "source.transient_cleanup_status",
        "source.cache_retention_policy",
        "source.cache_reference_status",
        "source.unavailable_status",
        "source.source_group_identity",
        "source.source_group_membership_revision",
        "source.neighborhood_identity",
        "source.group_chain",
        "source.group_labels_private",
        "source.spatial_context_revision",
        "source.gmail_content_resume",
        "source.gmail_inventory_cursor",
        "source.gmail_metadata_owner_status",
        "source.gmail_metadata_reconciliation_cursor",
        "source.gmail_body_receipt_identity",
        "source.gmail_body_predecessor_fingerprint",
        "source.gmail_content_disposition_identity",
        "source.content_depth",
        "source.content_selection_mode",
        "source.content_selection_reason",
        "source.content_selection_priority",
        "source.content_selection_continuation",
        "source.content_selection_scope_memberships",
        "source.content_selection_semantic_identity",
        "source.content_selection_inventory_revision_context",
        "source.tombstone",
        "source.atomic_registration",
        "gallery_asset.identity",
        "gallery_asset.derivative_revision",
        "gallery_asset.renderer_identity",
        "gallery_asset.safety_disposition",
        "inventory.snapshot_revision",
        "inventory.occurrence_current_index",
        "inventory.change_set",
        "dependency.freshness",
    ),
    owned_write_fields=(
        "source.identity",
        "source.version",
        "source.content_hash",
        "source.metadata_hash",
        "source.locator",
        "source.content_fingerprint",
        "source.metadata_fingerprint",
        "source.storage_class",
        "source.transient_cleanup_status",
        "source.cache_retention_policy",
        "source.cache_reference_status",
        "source.unavailable_status",
        "source.source_group_identity",
        "source.source_group_membership_revision",
        "source.neighborhood_identity",
        "source.group_chain",
        "source.group_labels_private",
        "source.spatial_context_revision",
        "source.gmail_content_resume",
        "source.gmail_inventory_cursor",
        "source.gmail_metadata_owner_status",
        "source.gmail_metadata_reconciliation_cursor",
        "source.gmail_body_receipt_identity",
        "source.gmail_body_predecessor_fingerprint",
        "source.gmail_content_disposition_identity",
        "source.content_depth",
        "source.content_selection_mode",
        "source.content_selection_reason",
        "source.content_selection_priority",
        "source.content_selection_continuation",
        "source.content_selection_scope_memberships",
        "source.content_selection_semantic_identity",
        "source.content_selection_inventory_revision_context",
        "source.tombstone",
        "source.atomic_registration",
        "gallery_asset.identity",
        "gallery_asset.derivative_revision",
        "gallery_asset.renderer_identity",
        "gallery_asset.safety_disposition",
        "inventory.snapshot_revision",
        "inventory.occurrence_current_index",
        "inventory.change_set",
        "dependency.freshness",
    ),
    side_effect_classes=(
        "source_registry_write",
        "gmail_body_receipt_write",
        "gmail_content_disposition_write",
        "content_selection_write",
        "inventory_snapshot_write",
        "freshness_invalidation_write",
        "transient_cleanup_write",
        "source_group_projection_write",
    ),
    completion_evidence=(
        "SourceVersion",
        "MetadataRevision",
        "SourceNeighborhood",
        "GmailContentResume",
        "GmailMetadataOwnerCurrent",
        "GmailMetadataReconciliationCursor",
        "GmailBodyContinuationReceipt",
        "GmailBodyRefresh",
        "GmailNoTextContentDisposition",
        "GmailPartialInventory",
        "ContentSelectionPlan",
        "ContentSelectionDeferred",
        "ContentSelectionBounded",
        "ContentSelectionContinuation",
        "ContentSelectionOverlapDeduplicated",
        "ContentSelectionSemanticIdentity",
        "ContentSelectionSemanticNoDelta",
        "ContentSelectionInventoryContext",
        "InventorySnapshot",
        "OccurrenceCurrentIndex",
        "AtomicSourceRegistration",
        "ChangeSet",
        "Added",
        "Modified",
        "Moved",
        "Deleted",
        "NewlyReachable",
        "NoDelta",
        "Tombstone",
        "InvalidationRequest",
        "GalleryDerivative",
        "GallerySafetyDisposition",
        "ExternalOriginalPointer",
        "DurableDerivedRecord",
        "RebuildableCache",
        "TransientStaging",
        "TransientCleanupTerminal",
        "SourceUnavailable",
        "SourceGroup",
        "SourceGroupMembership",
    ),
    rules=(
        CaseRule(
            case_id="authorized_original_registered_in_place",
            decision="source_in_place_registration_current",
            label="source_in_place_registration_current",
            writes=(
                "source.locator",
                "source.content_fingerprint",
                "source.metadata_fingerprint",
                "source.storage_class",
                "source.unavailable_status",
            ),
            side_effects=("source_registry_write",),
            emitted_tokens=("SourceVersion", "ExternalOriginalPointer"),
            reason=(
                "an authorized file, Gmail message, or provider object keeps its "
                "original bytes at the provider while C2 persists a private "
                "locator, stable fingerprints, observation metadata, and the "
                "external_original storage class"
            ),
        ),
        CaseRule(
            case_id="derived_understanding_persisted_without_original_copy",
            decision="durable_derived_record_current",
            label="durable_derived_record_current",
            writes=(
                "source.storage_class",
                "source.cache_retention_policy",
                "source.cache_reference_status",
            ),
            side_effects=("source_registry_write",),
            emitted_tokens=("DurableDerivedRecord", "RebuildableCache"),
            reason=(
                "summaries, anchors, facts, and models are durable derived state "
                "while thumbnails, previews, and extraction caches remain "
                "rebuildable and reference-audited"
            ),
        ),
        CaseRule(
            case_id="transient_connector_body_committed_or_expired",
            decision="transient_cleanup_terminal",
            label="transient_cleanup_terminal",
            writes=(
                "source.storage_class",
                "source.transient_cleanup_status",
                "source.cache_reference_status",
            ),
            side_effects=("transient_cleanup_write",),
            emitted_tokens=("TransientStaging", "TransientCleanupTerminal"),
            reason=(
                "complete Gmail bodies, extraction payloads, and generation "
                "staging are bounded transient inputs and reach deleted, "
                "retained-under-explicit-recovery-policy, or visibly blocked "
                "terminal state after their derived commit"
            ),
        ),
        CaseRule(
            case_id="original_source_temporarily_or_permanently_unavailable",
            decision="source_unavailable_derived_state_preserved",
            label="source_unavailable_derived_state_preserved",
            writes=("source.unavailable_status", "dependency.freshness"),
            side_effects=("freshness_invalidation_write",),
            emitted_tokens=("SourceUnavailable", "InvalidationRequest"),
            reason=(
                "an offline, moved, deleted, or revoked original keeps its prior "
                "derived history and locator trace while C2 refuses to claim "
                "that the original is currently readable"
            ),
        ),
        CaseRule(
            case_id="stable_private_source_group_projected",
            decision="source_group_membership_current",
            label="source_group_membership_current",
            writes=(
                "source.source_group_identity",
                "source.source_group_membership_revision",
                "source.neighborhood_identity",
                "source.group_chain",
            ),
            side_effects=("source_group_projection_write",),
            emitted_tokens=("SourceGroup", "SourceGroupMembership"),
            reason=(
                "contained filesystem neighborhoods, Gmail threads, Codex "
                "projects or workspaces, and provider groups receive stable "
                "private group identity without exposing an absolute local path"
            ),
        ),
        CaseRule(
            case_id="overlapping_registered_scopes_same_occurrence",
            decision="one_current_selection_plan_per_occurrence",
            label="one_current_selection_plan_per_occurrence",
            writes=(
                "source.content_selection_mode",
                "source.content_selection_reason",
                "source.content_selection_priority",
                "source.content_selection_continuation",
                "source.content_selection_scope_memberships",
                "source.neighborhood_identity",
                "source.group_chain",
            ),
            side_effects=("content_selection_write",),
            emitted_tokens=(
                "ContentSelectionPlan",
                "ContentSelectionOverlapDeduplicated",
                "SourceNeighborhood",
            ),
            reason=(
                "parent and nested authorized roots may contribute licensed "
                "scope context, but stable occurrence identity receives one "
                "selection plan, one Source identity, and no duplicate work"
            ),
        ),
        CaseRule(
            case_id="unchanged_selection_semantics_new_inventory_scan_revision",
            decision="content_selection_semantic_no_delta",
            label="content_selection_semantic_no_delta",
            writes=(
                "source.content_selection_inventory_revision_context",
                "inventory.snapshot_revision",
                "inventory.occurrence_current_index",
            ),
            side_effects=("inventory_snapshot_write",),
            emitted_tokens=(
                "InventorySnapshot",
                "OccurrenceCurrentIndex",
                "ContentSelectionSemanticIdentity",
                "ContentSelectionSemanticNoDelta",
                "ContentSelectionInventoryContext",
            ),
            reason=(
                "a new scan revision is retained as audit and freshness context "
                "but unchanged occurrence, policy, content-relevant metadata, "
                "neighborhood, mode, reason, priority, and continuation retain "
                "one semantic plan identity and enqueue no duplicate content work"
            ),
        ),
        CaseRule(
            case_id="registered_occurrence_exact_index_current",
            decision="occurrence_current_index_projected",
            label="occurrence_current_index_projected",
            writes=(
                "inventory.occurrence_current_index",
            ),
            side_effects=("inventory_snapshot_write",),
            emitted_tokens=("InventorySnapshot", "OccurrenceCurrentIndex"),
            reason=(
                "the immutable inventory snapshot remains authority while a "
                "rebuildable exact current occurrence index serves bounded "
                "content batches without decoding whole scope snapshots"
            ),
        ),
        CaseRule(
            case_id="concurrent_identical_source_registration",
            decision="single_atomic_source_version",
            label="single_atomic_source_version",
            writes=(
                "source.identity",
                "source.version",
                "source.content_hash",
                "source.metadata_hash",
                "source.atomic_registration",
            ),
            side_effects=("source_registry_write",),
            emitted_tokens=("SourceVersion", "AtomicSourceRegistration", "NoDelta"),
            reason=(
                "concurrent identical registration resolves inside one atomic "
                "owner transaction to one version and one idempotent no-delta"
            ),
        ),
        CaseRule(
            case_id="filesystem_source_neighborhood_registered",
            decision="source_neighborhood_current",
            label="source_neighborhood_current",
            writes=(
                "source.neighborhood_identity",
                "source.group_chain",
                "source.group_labels_private",
                "source.spatial_context_revision",
                "source.metadata_hash",
            ),
            side_effects=("source_registry_write",),
            emitted_tokens=("MetadataRevision", "SourceNeighborhood"),
            reason=(
                "each contained filesystem occurrence preserves one "
                "partition-stable opaque parent-neighborhood identity, ordered "
                "authorized-root group chain, private contained labels, and "
                "spatial-context revision without an absolute path or any "
                "occurrence/content identity merge"
            ),
        ),
        CaseRule(
            case_id="inventory_first_snapshot",
            decision="inventory_snapshot_created",
            label="inventory_snapshot_created",
            writes=("inventory.snapshot_revision", "inventory.change_set"),
            side_effects=("inventory_snapshot_write",),
            emitted_tokens=("InventorySnapshot", "ChangeSet", "Added"),
            reason="the first bounded enumeration records stable occurrences without claiming content ingestion",
        ),
        CaseRule(
            case_id="registered_occurrence_content_deferred",
            decision="content_selection_terminal_deferred",
            label="content_selection_terminal_deferred",
            writes=(
                "source.content_selection_mode",
                "source.content_selection_reason",
                "source.content_selection_priority",
                "source.content_selection_continuation",
            ),
            side_effects=("content_selection_write",),
            emitted_tokens=(
                "ContentSelectionPlan",
                "ContentSelectionDeferred",
            ),
            reason=(
                "registration remains complete while software-tree prose, "
                "machine-oriented records, unsupported media, or low-value "
                "content receives an honest terminal no-read disposition"
            ),
        ),
        CaseRule(
            case_id="registered_occurrence_content_admitted",
            decision="content_selection_bounded_read_admitted",
            label="content_selection_bounded_read_admitted",
            writes=(
                "source.content_selection_mode",
                "source.content_selection_reason",
                "source.content_selection_priority",
                "source.content_selection_continuation",
            ),
            side_effects=("content_selection_write",),
            emitted_tokens=(
                "ContentSelectionPlan",
                "ContentSelectionBounded",
                "ContentSelectionContinuation",
            ),
            reason=(
                "value, freshness, neighborhood, and human-content signals "
                "select one bounded read; any deeper read remains an explicit "
                "resumable continuation rather than automatic full expansion"
            ),
        ),
        CaseRule(
            case_id="new_content",
            decision="source_version_created",
            label="source_version_created",
            writes=(
                "source.identity",
                "source.version",
                "source.content_hash",
                "source.metadata_hash",
            ),
            side_effects=("source_registry_write",),
            emitted_tokens=("SourceVersion",),
            reason="new stable content creates an immutable version",
        ),
        CaseRule(
            case_id="gmail_partial_inventory_page",
            decision="gmail_partial_inventory_accumulated",
            label="gmail_partial_inventory_accumulated",
            writes=(
                "inventory.snapshot_revision",
                "inventory.change_set",
                "source.gmail_inventory_cursor",
            ),
            side_effects=("inventory_snapshot_write",),
            emitted_tokens=(
                "InventorySnapshot",
                "ChangeSet",
                "Added",
                "GmailPartialInventory",
            ),
            reason=(
                "a non-terminal authorized Gmail page is merged with the "
                "current query inventory; absence from that page is not "
                "deletion evidence and only a terminal complete inventory may "
                "retire previously seen messages or threads"
            ),
        ),
        CaseRule(
            case_id="gmail_metadata_owner_bounded_reconciliation",
            decision="gmail_metadata_source_owner_current",
            label="gmail_metadata_source_owner_current",
            writes=(
                "source.identity",
                "source.version",
                "source.metadata_hash",
                "source.gmail_metadata_owner_status",
                "source.gmail_metadata_reconciliation_cursor",
            ),
            side_effects=("source_registry_write",),
            emitted_tokens=(
                "SourceVersion",
                "GmailMetadataOwnerCurrent",
                "GmailMetadataReconciliationCursor",
            ),
            reason=(
                "one deterministic at-most-500 prefix of exact C1-authorized "
                "metadata-only or identity-only messages receives only a minimal "
                "metadata SourceVersion and source-version coverage pointer; "
                "existing bodies are preserved and exact replay is no-delta"
            ),
        ),
        CaseRule(
            case_id="gmail_bounded_content_resume",
            decision="gmail_content_batch_current_without_regression",
            label="gmail_content_batch_current_without_regression",
            writes=(
                "source.version",
                "source.content_hash",
                "source.metadata_hash",
                "source.gmail_content_resume",
                "source.content_depth",
                "dependency.freshness",
            ),
            side_effects=(
                "source_registry_write",
                "freshness_invalidation_write",
            ),
            emitted_tokens=(
                "SourceVersion",
                "GmailContentResume",
                "InvalidationRequest",
            ),
            reason=(
                "a stable offset/limit selects the next authorized bodies; the "
                "content-bearing envelope is authoritative and earlier current "
                "content/evidence never regresses to metadata-only"
            ),
        ),
        CaseRule(
            case_id="gmail_manifest_body_continuation",
            decision="gmail_body_source_version_current",
            label="gmail_body_source_version_current",
            writes=(
                "source.version",
                "source.content_hash",
                "source.metadata_hash",
                "source.gmail_content_resume",
                "source.gmail_body_receipt_identity",
                "source.gmail_body_predecessor_fingerprint",
                "source.content_depth",
            ),
            side_effects=(
                "source_registry_write",
                "gmail_body_receipt_write",
            ),
            emitted_tokens=(
                "SourceVersion",
                "GmailContentResume",
                "GmailBodyContinuationReceipt",
                "GmailBodyRefresh",
            ),
            reason=(
                "one exact connector body deepens its already-current Gmail "
                "metadata SourceVersion and writes only a digest/pointer receipt; "
                "identical replay is no-delta, while a differing complete body "
                "appends a replacement version only when the manifest binds the "
                "exact current predecessor body fingerprint"
            ),
        ),
        CaseRule(
            case_id="gmail_no_text_body_disposition",
            decision="gmail_no_text_content_disposition_current",
            label="gmail_no_text_content_disposition_current",
            writes=("source.gmail_content_disposition_identity",),
            side_effects=("gmail_content_disposition_write",),
            emitted_tokens=("GmailNoTextContentDisposition",),
            reason=(
                "one proof-bound no-text result records only a minimized "
                "content-disposition owner over the already-current metadata "
                "SourceVersion; it never creates a body SourceVersion and "
                "identical replay is no-delta"
            ),
        ),
        CaseRule(
            case_id="metadata_only_change",
            decision="metadata_revision_created",
            label="metadata_revision_created",
            writes=("source.version", "source.metadata_hash"),
            side_effects=("source_registry_write",),
            emitted_tokens=("MetadataRevision", "Modified"),
            reason="metadata identity changes without pretending content changed",
        ),
        CaseRule(
            case_id="occurrence_moved_same_content",
            decision="move_recorded_dependents_reviewed",
            label="move_recorded_dependents_reviewed",
            writes=("inventory.snapshot_revision", "inventory.change_set", "dependency.freshness"),
            side_effects=("inventory_snapshot_write", "freshness_invalidation_write"),
            emitted_tokens=("InventorySnapshot", "ChangeSet", "Moved", "InvalidationRequest"),
            reason="move preserves content identity while location/policy dependents are re-evaluated",
        ),
        CaseRule(
            case_id="occurrence_newly_reachable",
            decision="newly_reachable_recorded",
            label="newly_reachable_recorded",
            writes=("inventory.snapshot_revision", "inventory.change_set", "dependency.freshness"),
            side_effects=("inventory_snapshot_write", "freshness_invalidation_write"),
            emitted_tokens=("InventorySnapshot", "ChangeSet", "NewlyReachable", "InvalidationRequest"),
            reason="hydration or permission change creates a new bounded processing candidate",
        ),
        CaseRule(
            case_id="identical_rescan",
            decision="no_delta",
            label="identical_no_delta",
            emitted_tokens=("NoDelta",),
            reason="an unchanged occurrence and policy produces no duplicate work",
        ),
        CaseRule(
            case_id="source_modified",
            decision="source_version_and_invalidation_created",
            label="source_modified",
            writes=(
                "source.version",
                "source.content_hash",
                "source.metadata_hash",
                "inventory.snapshot_revision",
                "inventory.change_set",
                "dependency.freshness",
            ),
            side_effects=(
                "source_registry_write",
                "inventory_snapshot_write",
                "freshness_invalidation_write",
            ),
            emitted_tokens=("SourceVersion", "ChangeSet", "Modified", "InvalidationRequest"),
            reason="content change stales only the occurrence and declared dependents",
        ),
        CaseRule(
            case_id="source_deleted",
            decision="tombstone_and_invalidation_created",
            label="tombstone_created",
            writes=(
                "source.version",
                "source.tombstone",
                "inventory.snapshot_revision",
                "inventory.change_set",
                "dependency.freshness",
            ),
            side_effects=(
                "source_registry_write",
                "inventory_snapshot_write",
                "freshness_invalidation_write",
            ),
            emitted_tokens=("Tombstone", "Deleted", "ChangeSet", "InvalidationRequest"),
            reason="confirmed deletion creates a tombstone and stales declared dependents",
        ),
        CaseRule(
            case_id="eligible_gallery_derivative",
            decision="safe_gallery_derivative_created",
            label="safe_gallery_derivative_created",
            writes=(
                "gallery_asset.identity",
                "gallery_asset.derivative_revision",
                "gallery_asset.renderer_identity",
                "gallery_asset.safety_disposition",
                "dependency.freshness",
            ),
            side_effects=("source_registry_write", "freshness_invalidation_write"),
            emitted_tokens=("GalleryDerivative", "GallerySafetyDisposition"),
            reason=(
                "an allowlisted real image or supported document region is rendered "
                "locally for the Images evidence gallery with macros, network, and "
                "external content disabled and no generated-hero authority"
            ),
        ),
        CaseRule(
            case_id="unsafe_or_stale_gallery_asset",
            decision="gallery_derivative_unavailable",
            label="gallery_derivative_unavailable",
            writes=("gallery_asset.safety_disposition", "dependency.freshness"),
            side_effects=("freshness_invalidation_write",),
            emitted_tokens=("GallerySafetyDisposition", "InvalidationRequest"),
            reason=(
                "unsafe, denied, unreadable, unsupported, or stale visual content "
                "is terminally unavailable for the Images evidence gallery"
            ),
        ),
        CaseRule(
            case_id="ai_rewrite_attempt",
            decision="source_mutation_rejected",
            label="source_mutation_rejected",
            emitted_tokens=("SourceMutationRejected",),
            reason="AI-authored replacement cannot mutate original source content",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-C2-017-inventory-revision-rewrites-content-selection",
            protected_error_class="content_selection_scan_revision_identity_conflation",
            description=(
                "a no-delta inventory scan revision is included in the "
                "content-selection semantic fingerprint"
            ),
            protected_harm=(
                "every scan rewrites unchanged plans and amplifies extraction, "
                "anchors, AI packages, coverage history, and UI refresh"
            ),
            case_id="unchanged_selection_semantics_new_inventory_scan_revision",
            broken_decision="content_selection_plan_rewritten",
            broken_writes=(
                "source.content_selection_semantic_identity",
                "source.content_selection_inventory_revision_context",
            ),
            broken_side_effects=("content_selection_write",),
            broken_tokens=("ContentSelectionPlan", "ContentSelectionBounded"),
        ),
        HazardSpec(
            failure_id="H-C2-016-overlapping-root-duplicates-content-plan",
            protected_error_class="content_selection_overlap_amplification",
            description=(
                "one physical occurrence registered through overlapping roots "
                "receives multiple current selection plans or analysis packages"
            ),
            protected_harm=(
                "scope topology duplicates private reads, evidence, AI work, "
                "and downstream Matters"
            ),
            case_id="overlapping_registered_scopes_same_occurrence",
            broken_decision="selection_plan_created_per_scope_membership",
            broken_writes=(
                "source.content_selection_mode",
                "source.content_selection_scope_memberships",
            ),
            broken_side_effects=("content_selection_write",),
            broken_tokens=("ContentSelectionPlan",),
        ),
        HazardSpec(
            failure_id="H-C2-014-registration-implies-full-content-read",
            protected_error_class="inventory_content_admission_conflation",
            description=(
                "every registered occurrence immediately creates a full "
                "SourceVersion and all downstream anchors"
            ),
            protected_harm=(
                "large user roots amplify into unbounded private reads and "
                "analysis packages before value or neighborhood is considered"
            ),
            case_id="registered_occurrence_content_deferred",
            broken_decision="source_version_created",
            broken_writes=("source.version", "source.content_hash"),
            broken_side_effects=("source_registry_write",),
            broken_tokens=("SourceVersion",),
        ),
        HazardSpec(
            failure_id="H-C2-015-bounded-selection-silently-truncates-content",
            protected_error_class="content_selection_continuation_loss",
            description=(
                "a sampled or bounded read is recorded as the complete source "
                "without a continuation state"
            ),
            protected_harm=(
                "later relevant content becomes invisible while coverage "
                "incorrectly appears complete"
            ),
            case_id="registered_occurrence_content_admitted",
            broken_decision="source_version_created_complete",
            broken_writes=(
                "source.content_selection_mode",
                "source.content_selection_continuation",
            ),
            broken_side_effects=("content_selection_write",),
            broken_tokens=("ContentSelectionBounded",),
        ),
        HazardSpec(
            failure_id="H-C2-012-whole-snapshot-read-per-object",
            protected_error_class="registered_batch_snapshot_amplification",
            description=(
                "each registered file reloads and decodes its whole inventory snapshot"
            ),
            protected_harm=(
                "first-run cost grows with snapshot size times object count and stalls coverage"
            ),
            case_id="registered_occurrence_exact_index_current",
            broken_decision="whole_snapshot_rehydrated_per_object",
            broken_writes=(),
            broken_tokens=("InventorySnapshot",),
        ),
        HazardSpec(
            failure_id="H-C2-013-nonatomic-source-revision-race",
            protected_error_class="source_revision_allocation_race",
            description=(
                "source revision is read and written in separate transactions"
            ),
            protected_harm=(
                "concurrent workers collide or duplicate the same immutable source version"
            ),
            case_id="concurrent_identical_source_registration",
            broken_decision="duplicate_source_revision_attempted",
            broken_writes=("source.version",),
            broken_side_effects=("source_registry_write",),
            broken_tokens=("SourceVersion",),
        ),
        HazardSpec(
            failure_id="H-C2-008-folder-proximity-collapses-source-identity",
            protected_error_class="source_neighborhood_identity_collapse",
            description="neighboring files are merged into one source identity",
            protected_harm="independent content/version history is lost because files share a folder",
            case_id="filesystem_source_neighborhood_registered",
            broken_decision="source_identity_merged",
            broken_writes=("source.identity", "source.content_hash"),
            broken_side_effects=("source_registry_write",),
            broken_tokens=("SourceVersion",),
        ),
        HazardSpec(
            failure_id="H-C2-009-partition-boundary-changes-neighborhood",
            protected_error_class="partition_relative_spatial_identity_drift",
            description=(
                "the same physical parent receives different neighborhood or "
                "group identities when scanned from a child partition"
            ),
            protected_harm=(
                "related user sources become isolated or spuriously regrouped "
                "only because the inventory boundary changed"
            ),
            case_id="filesystem_source_neighborhood_registered",
            broken_decision="source_neighborhood_partition_local",
            broken_writes=(
                "source.neighborhood_identity",
                "source.group_chain",
                "source.metadata_hash",
            ),
            broken_side_effects=("source_registry_write",),
            broken_tokens=("MetadataRevision", "SourceNeighborhood"),
        ),
        HazardSpec(
            failure_id="H-C2-011-gmail-partial-page-deletes-prior-page",
            protected_error_class="partial_inventory_false_deletion",
            description=(
                "a later non-terminal Gmail page replaces the current query "
                "snapshot and treats prior-page messages as deleted"
            ),
            protected_harm=(
                "real mail disappears from coverage and its evidence becomes "
                "stale merely because connector pagination advanced"
            ),
            case_id="gmail_partial_inventory_page",
            broken_decision="inventory_snapshot_replaced",
            broken_writes=(
                "inventory.snapshot_revision",
                "inventory.change_set",
                "source.gmail_inventory_cursor",
            ),
            broken_side_effects=("inventory_snapshot_write",),
            broken_tokens=("Deleted",),
        ),
        HazardSpec(
            failure_id="H-C2-020-gmail-metadata-owner-creates-semantic-depth",
            protected_error_class="gmail_metadata_owner_depth_or_retry_escape",
            description=(
                "metadata-owner reconciliation replaces a current body, "
                "creates evidence or semantic work, exceeds its bounded prefix, "
                "or amplifies source/coverage revisions on exact retry"
            ),
            protected_harm=(
                "minimal provenance repair loses real content or becomes a "
                "second unbounded semantic ingestion path"
            ),
            case_id="gmail_metadata_owner_bounded_reconciliation",
            broken_decision="gmail_metadata_source_and_semantic_state_created",
            broken_writes=(
                "source.version",
                "source.content_hash",
                "source.gmail_metadata_owner_status",
                "source.gmail_metadata_reconciliation_cursor",
            ),
            broken_side_effects=("source_registry_write",),
            broken_tokens=(
                "SourceVersion",
                "GmailMetadataOwnerCurrent",
            ),
        ),
        HazardSpec(
            failure_id="H-C2-010-gmail-metadata-regresses-content",
            protected_error_class="gmail_content_depth_regression",
            description=(
                "a later bounded Gmail batch registers metadata-only before "
                "content and replaces a previously extracted body version"
            ),
            protected_harm=(
                "earlier evidence and analysis become stale or no-finding even "
                "though the authorized message body is unchanged"
            ),
            case_id="gmail_bounded_content_resume",
            broken_decision="metadata_revision_created",
            broken_writes=(
                "source.version",
                "source.metadata_hash",
                "source.content_depth",
            ),
            broken_side_effects=("source_registry_write",),
            broken_tokens=("MetadataRevision",),
        ),
        HazardSpec(
            failure_id="H-C2-018-gmail-continuation-rewrites-unbound-body",
            protected_error_class="gmail_continuation_predecessor_mismatch",
            description=(
                "a continuation replaces an existing different Gmail body "
                "without the exact current prior-body fingerprint or creates "
                "duplicate versions and receipts on exact replay"
            ),
            protected_harm=(
                "a stale or arbitrary connector result becomes current provider "
                "truth, or resumable import amplifies source and receipt history"
            ),
            case_id="gmail_manifest_body_continuation",
            broken_decision="gmail_body_source_version_rewritten_without_predecessor",
            broken_writes=(
                "source.version",
                "source.content_hash",
                "source.gmail_body_receipt_identity",
                "source.gmail_body_predecessor_fingerprint",
            ),
            broken_side_effects=(
                "source_registry_write",
                "gmail_body_receipt_write",
            ),
            broken_tokens=("SourceVersion", "GmailBodyContinuationReceipt"),
        ),
        HazardSpec(
            failure_id="H-C2-019-gmail-no-text-creates-fake-source",
            protected_error_class="gmail_no_text_fake_content",
            description=(
                "a proof-bound no_text_body disposition writes an empty "
                "body-bearing SourceVersion or changes current provider content"
            ),
            protected_harm=(
                "the registry fabricates source content and loses the distinction "
                "between metadata provenance and a recovered textual body"
            ),
            case_id="gmail_no_text_body_disposition",
            broken_decision="gmail_no_text_source_version_created",
            broken_writes=(
                "source.version",
                "source.content_hash",
                "source.gmail_content_disposition_identity",
            ),
            broken_side_effects=(
                "source_registry_write",
                "gmail_content_disposition_write",
            ),
            broken_tokens=(
                "SourceVersion",
                "GmailNoTextContentDisposition",
            ),
        ),
        HazardSpec(
            failure_id="H-C2-001-ai-rewrites-original",
            protected_error_class="source_truth_mutation",
            description="AI-authored text replaces provider source content",
            protected_harm="the provenance record no longer represents the source",
            case_id="ai_rewrite_attempt",
            broken_decision="source_version_created",
            broken_writes=("source.version", "source.content_hash", "source.metadata_hash"),
            broken_side_effects=("source_registry_write",),
            broken_tokens=("SourceVersion",),
        ),
        HazardSpec(
            failure_id="H-C2-002-rescan-duplicates-work",
            protected_error_class="duplicate_side_effect",
            description="an unchanged rescan writes another snapshot or source version",
            protected_harm="background scanning creates duplicate analysis and unstable counts",
            case_id="inventory_first_snapshot",
            broken_decision="inventory_snapshot_created",
            broken_writes=("inventory.snapshot_revision", "inventory.change_set"),
            broken_side_effects=("inventory_snapshot_write",),
            broken_tokens=("InventorySnapshot", "ChangeSet", "Added"),
            ignore_idempotency=True,
        ),
        HazardSpec(
            failure_id="H-C2-003-metadata-becomes-content",
            protected_error_class="hash_identity_conflation",
            description="a metadata-only change is recorded as a content change",
            protected_harm="downstream evidence is invalidated against the wrong identity",
            case_id="metadata_only_change",
            broken_decision="source_version_created",
            broken_writes=("source.version", "source.content_hash", "source.metadata_hash"),
            broken_side_effects=("source_registry_write",),
            broken_tokens=("SourceVersion",),
        ),
        HazardSpec(
            failure_id="H-C2-004-change-keeps-dependents-current",
            protected_error_class="freshness_propagation_loss",
            description="modified content does not stale declared dependents",
            protected_harm="old triage, anchors, analysis, and projections look current",
            case_id="source_modified",
            broken_decision="source_version_created",
            broken_writes=("source.version", "source.content_hash", "source.metadata_hash"),
            broken_side_effects=("source_registry_write",),
            broken_tokens=("SourceVersion",),
        ),
        HazardSpec(
            failure_id="H-C2-005-deletion-without-tombstone",
            protected_error_class="deletion_propagation_loss",
            description="a deleted source disappears without a tombstone or invalidation",
            protected_harm="dependents remain current after their source was deleted",
            case_id="source_deleted",
            broken_decision="no_delta",
            broken_tokens=("NoDelta",),
        ),
        HazardSpec(
            failure_id="H-C2-007-unsafe-gallery-asset-rendered",
            protected_error_class="gallery_derivative_safety_escape",
            description="an unsafe or stale source is rendered as a current gallery derivative",
            protected_harm="active or unrelated private content becomes visible evidence",
            case_id="unsafe_or_stale_gallery_asset",
            broken_decision="safe_gallery_derivative_created",
            broken_writes=(
                "gallery_asset.identity",
                "gallery_asset.derivative_revision",
                "gallery_asset.safety_disposition",
            ),
            broken_tokens=("GalleryDerivative",),
        ),
        HazardSpec(
            failure_id="H-C2-006-move-creates-unrelated-content",
            protected_error_class="occurrence_content_identity_collapse",
            description="a move is treated as unrelated new content without identity reconciliation",
            protected_harm="duplicates and broken history replace a continuous source occurrence",
            case_id="occurrence_moved_same_content",
            broken_decision="source_version_created",
            broken_writes=("source.identity", "source.version", "source.content_hash"),
            broken_side_effects=("source_registry_write",),
            broken_tokens=("SourceVersion",),
        ),
    ),
    risk_classes=(
        "deduplication",
        "idempotency",
        "freshness",
        "side_effect",
        "provenance",
    ),
    template_ids=("side_effect_at_most_once",),
    blindspots=(
        "real provider occurrence stability requires adapter conformance",
        "rename identity thresholds and cloud hydration require source-type tests",
        "durable transaction and restart behavior require runtime evidence",
    ),
    claim_boundary=(
        "This model establishes bounded C2 inventory, value/neighborhood-aware "
        "content-selection plans whose semantic identity is independent from "
        "inventory scan revision, explicit deferred/bounded/continuation states, "
        "change-set, source-version, freshness, safe Images-gallery derivative, "
        "no-delta, and tombstone behavior. It does not prove durable storage, "
        "provider enumeration completeness, or real dependency execution."
    ),
)
