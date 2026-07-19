"""Auxiliary S0-S5 bundled-skill runtime FlowGuard declarations.

These development-process models own only Skill Pack inventory, compatibility,
active-view resolution, Matters-managed synchronization, and validation /
rollback. They are deliberately outside M0/C1-C12 canonical Matter ownership.
"""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


S0 = FiniteModelSpec(
    model_id="S0_matters_skill_runtime",
    title="S0 Matters Auxiliary Skill Runtime",
    modeled_boundary=(
        "parent authority over S1-S5 receipts, singular active skill identity, "
        "ResearchGuard integration disposition, and zero canonical Matter writes"
    ),
    state_fields=(
        "skill_runtime.child_receipt_set",
        "skill_runtime.parent_status",
        "skill_runtime.published_active_identity",
    ),
    owned_write_fields=(
        "skill_runtime.child_receipt_set",
        "skill_runtime.parent_status",
        "skill_runtime.published_active_identity",
    ),
    side_effect_classes=("publish_active_skill_identity",),
    completion_evidence=(
        "CurrentSkillRuntimeChildReceiptSet",
        "SkillRuntimeTerminal",
        "NoCanonicalMatterWriteProof",
    ),
    rules=(
        CaseRule(
            case_id="all_children_current_active_identity",
            decision="active_identity_published",
            label="active_identity_published",
            writes=(
                "skill_runtime.child_receipt_set",
                "skill_runtime.parent_status",
                "skill_runtime.published_active_identity",
            ),
            side_effects=("publish_active_skill_identity",),
            emitted_tokens=(
                "CurrentSkillRuntimeChildReceiptSet",
                "SkillRuntimeTerminal",
                "NoCanonicalMatterWriteProof",
            ),
            reason="S1-S5 are current and one validated active identity is selected",
        ),
        CaseRule(
            case_id="bundled_only_internal_ready",
            decision="bundled_internal_runtime_ready",
            label="bundled_internal_runtime_ready",
            writes=("skill_runtime.child_receipt_set", "skill_runtime.parent_status"),
            emitted_tokens=("BundledInternalView", "NoGlobalInstall", "SkillRuntimeTerminal"),
            reason="the bundled consumer pack works without global installation",
        ),
        CaseRule(
            case_id="required_child_blocked",
            decision="skill_activation_blocked",
            label="skill_activation_blocked",
            writes=("skill_runtime.child_receipt_set", "skill_runtime.parent_status"),
            emitted_tokens=("ChildBlocked", "SkillRuntimeBlocked"),
            reason="a required S1-S5 disposition cannot be hidden by parent green",
        ),
        CaseRule(
            case_id="required_child_stale",
            decision="skill_activation_freshness_blocked",
            label="skill_activation_freshness_blocked",
            writes=("skill_runtime.child_receipt_set", "skill_runtime.parent_status"),
            emitted_tokens=("StaleChildEvidence", "SkillRuntimeBlocked"),
            reason="changed child identity invalidates the active-view publication",
        ),
        CaseRule(
            case_id="researchguard_pending",
            decision="researchguard_pending_integration",
            label="researchguard_pending_integration",
            writes=("skill_runtime.child_receipt_set", "skill_runtime.parent_status"),
            emitted_tokens=("ResearchGuardPending", "SkillRuntimePartial"),
            reason="ResearchGuard remains visibly pending without a legacy Guard fallback",
        ),
        CaseRule(
            case_id="legacy_three_guard_fallback_requested",
            decision="legacy_runtime_fallback_rejected",
            label="legacy_runtime_fallback_rejected",
            writes=("skill_runtime.parent_status",),
            emitted_tokens=("LegacyBindingSourceOnly", "SkillRuntimeBlocked"),
            reason="SourceGuard, TraceGuard, and LogicGuard cannot become parallel runtime providers",
        ),
        CaseRule(
            case_id="canonical_matter_write_requested",
            decision="canonical_matter_write_rejected",
            label="canonical_matter_write_rejected",
            writes=("skill_runtime.parent_status",),
            emitted_tokens=("MatterOwnerDelegationRequired", "SkillRuntimeBlocked"),
            reason="S0 may publish a skill identity but never write canonical Matter state",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-S0-001-child-blocker-hidden",
            protected_error_class="skill_runtime_child_false_green",
            description="S0 publishes an active identity while a required child is blocked",
            protected_harm="an invalid skill candidate becomes executable",
            case_id="required_child_blocked",
            broken_decision="active_identity_published",
            broken_writes=(
                "skill_runtime.parent_status",
                "skill_runtime.published_active_identity",
            ),
            broken_side_effects=("publish_active_skill_identity",),
            broken_tokens=("SkillRuntimeTerminal",),
        ),
        HazardSpec(
            failure_id="H-S0-002-legacy-fallback",
            protected_error_class="legacy_guard_parallel_success",
            description="S0 falls back to three separate legacy Guard bindings",
            protected_harm="ResearchOperation gains several competing runtime authorities",
            case_id="legacy_three_guard_fallback_requested",
            broken_decision="legacy_guard_provider_selected",
            broken_writes=("skill_runtime.published_active_identity",),
            broken_side_effects=("publish_active_skill_identity",),
            broken_tokens=("LegacyGuardProvider",),
        ),
        HazardSpec(
            failure_id="H-S0-003-canonical-matter-write",
            protected_error_class="skill_runtime_matter_owner_escape",
            description="S0 directly writes a canonical Matter field",
            protected_harm="the auxiliary runtime becomes a competing product authority",
            case_id="canonical_matter_write_requested",
            broken_decision="matter_state_written",
            broken_writes=("matter.lifecycle_axes",),
            broken_tokens=("CanonicalMatterState",),
        ),
    ),
    risk_classes=("ownership", "freshness", "integration", "side_effect"),
    template_no_match_reason=(
        "No reusable template owns the exact Matters app-local bundled/runtime/"
        "managed-projection identity partition."
    ),
    blindspots=(
        "actual installed skill bytes and filesystem activation are not exercised",
        "A1 ResearchOperation execution remains a separate agent-operation owner",
    ),
    claim_boundary=(
        "S0 abstract evidence covers auxiliary child gating, singular identity "
        "publication, pending ResearchGuard, legacy-fallback rejection, and "
        "zero canonical Matter writes. It does not prove installed currentness, "
        "filesystem activation, ResearchGuard execution, or M0/C1-C12 behavior."
    ),
)


S1 = FiniteModelSpec(
    model_id="S1_skill_bundle_inventory",
    title="S1 Bundled Skill Inventory",
    modeled_boundary=(
        "immutable app-local member inventory, exact manifests/runtime assets, "
        "and rejection of author-side control residuals"
    ),
    state_fields=(
        "skill_runtime.bundle_identity",
        "skill_runtime.member_inventory",
        "skill_runtime.inventory_residuals",
    ),
    owned_write_fields=(
        "skill_runtime.bundle_identity",
        "skill_runtime.member_inventory",
        "skill_runtime.inventory_residuals",
    ),
    side_effect_classes=("write_skill_inventory_receipt",),
    completion_evidence=("BundleIdentity", "MemberInventory", "InventoryDisposition"),
    rules=(
        CaseRule(
            case_id="required_inventory_complete",
            decision="bundle_inventory_current",
            label="bundle_inventory_current",
            writes=(
                "skill_runtime.bundle_identity",
                "skill_runtime.member_inventory",
                "skill_runtime.inventory_residuals",
            ),
            side_effects=("write_skill_inventory_receipt",),
            emitted_tokens=("BundleIdentity", "MemberInventory", "InventoryDisposition"),
            reason="all required consumer skills and matching runtime assets are exact",
        ),
        CaseRule(
            case_id="bundled_only_no_global_install",
            decision="bundled_inventory_available",
            label="bundled_inventory_available",
            writes=("skill_runtime.bundle_identity", "skill_runtime.member_inventory"),
            side_effects=("write_skill_inventory_receipt",),
            emitted_tokens=("BundledCandidate", "NoGlobalInstall", "InventoryDisposition"),
            reason="absence of a global copy does not prevent app-local bundled use",
        ),
        CaseRule(
            case_id="manifest_bytes_mismatch",
            decision="bundle_identity_blocked",
            label="bundle_identity_blocked",
            writes=("skill_runtime.inventory_residuals",),
            side_effects=("write_skill_inventory_receipt",),
            emitted_tokens=("ManifestHashMismatch", "InventoryDisposition"),
            reason="declared content hash or runtime identity disagrees with packaged bytes",
        ),
        CaseRule(
            case_id="author_control_residual_present",
            decision="author_control_residual_blocked",
            label="author_control_residual_blocked",
            writes=("skill_runtime.inventory_residuals",),
            side_effects=("write_skill_inventory_receipt",),
            emitted_tokens=("AuthorControlResidual", "InventoryDisposition"),
            reason="consumer bundles exclude SkillGuard contracts, receipts, router, and owner state",
        ),
        CaseRule(
            case_id="required_member_missing",
            decision="required_inventory_blocked",
            label="required_inventory_blocked",
            writes=("skill_runtime.inventory_residuals",),
            side_effects=("write_skill_inventory_receipt",),
            emitted_tokens=("RequiredMemberMissing", "InventoryDisposition"),
            reason="the independently required member inventory cannot be inferred from observed files",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-S1-001-global-install-required",
            protected_error_class="bundled_only_global_install_escape",
            description="bundled-only operation creates a global installation",
            protected_harm="Matters mutates machine-global skill state without need or authority",
            case_id="bundled_only_no_global_install",
            broken_decision="global_skill_installed",
            broken_writes=("skill_runtime.bundle_identity",),
            broken_side_effects=("install_global_skill",),
            broken_tokens=("GlobalInstall",),
        ),
        HazardSpec(
            failure_id="H-S1-002-author-control-accepted",
            protected_error_class="author_control_bundle_contamination",
            description="author-side SkillGuard control state is accepted in a consumer bundle",
            protected_harm="private maintainer authority enters the runtime distribution",
            case_id="author_control_residual_present",
            broken_decision="bundle_inventory_current",
            broken_writes=("skill_runtime.bundle_identity",),
            broken_side_effects=("write_skill_inventory_receipt",),
            broken_tokens=("BundleIdentity",),
        ),
    ),
    risk_classes=("inventory", "ownership", "privacy", "side_effect"),
    template_no_match_reason="No target-owned consumer inventory template is installed for this new pack.",
    blindspots=("real package byte enumeration awaits the implementation and package validator",),
    claim_boundary=(
        "S1 proves the finite inventory and residual dispositions abstractly. "
        "It does not prove a built wheel, installed projection, or real bundle bytes."
    ),
)


S2 = FiniteModelSpec(
    model_id="S2_skill_compatibility",
    title="S2 Skill Compatibility",
    modeled_boundary=(
        "version/hash/schema/Matters/native-validation compatibility and "
        "ResearchGuard integration status before selection"
    ),
    state_fields=(
        "skill_runtime.compatibility_matrix",
        "skill_runtime.identity_collisions",
        "skill_runtime.researchguard_integration_status",
    ),
    owned_write_fields=(
        "skill_runtime.compatibility_matrix",
        "skill_runtime.identity_collisions",
        "skill_runtime.researchguard_integration_status",
    ),
    side_effect_classes=("write_compatibility_receipt",),
    completion_evidence=("CompatibilityMatrix", "CompatibilityDisposition"),
    rules=(
        CaseRule(
            case_id="exact_version_hash_match",
            decision="exact_identity_compatible",
            label="exact_identity_compatible",
            writes=("skill_runtime.compatibility_matrix",),
            side_effects=("write_compatibility_receipt",),
            emitted_tokens=("ExactIdentity", "CompatibilityDisposition"),
            reason="same version and content hash validate against current schemas",
        ),
        CaseRule(
            case_id="newer_local_compatible",
            decision="local_overlay_compatible",
            label="local_overlay_compatible",
            writes=("skill_runtime.compatibility_matrix",),
            side_effects=("write_compatibility_receipt",),
            emitted_tokens=("CompatibleLocalOverlay", "CompatibilityDisposition"),
            reason="numerically newer local candidate also declares and proves compatibility",
        ),
        CaseRule(
            case_id="bundled_newer_unmanaged_local",
            decision="bundled_candidate_compatible_update_available",
            label="bundled_candidate_compatible_update_available",
            writes=("skill_runtime.compatibility_matrix",),
            side_effects=("write_compatibility_receipt",),
            emitted_tokens=("CompatibleBundledCandidate", "UpdateAvailable", "CompatibilityDisposition"),
            reason="the external unmanaged local copy remains a distinct unchanged identity",
        ),
        CaseRule(
            case_id="same_version_different_hash",
            decision="identity_collision_blocked",
            label="identity_collision_blocked",
            writes=("skill_runtime.compatibility_matrix", "skill_runtime.identity_collisions"),
            side_effects=("write_compatibility_receipt",),
            emitted_tokens=("IdentityCollision", "CompatibilityDisposition"),
            reason="same version with different bytes has no deterministic validated authority",
        ),
        CaseRule(
            case_id="invalid_candidate",
            decision="invalid_candidate_blocked",
            label="invalid_candidate_blocked",
            writes=("skill_runtime.compatibility_matrix",),
            side_effects=("write_compatibility_receipt",),
            emitted_tokens=("NativeValidationFailed", "CompatibilityDisposition"),
            reason="invalid candidate never enters selection",
        ),
        CaseRule(
            case_id="incompatible_candidate",
            decision="incompatible_candidate_blocked",
            label="incompatible_candidate_blocked",
            writes=("skill_runtime.compatibility_matrix",),
            side_effects=("write_compatibility_receipt",),
            emitted_tokens=("CompatibilityMismatch", "CompatibilityDisposition"),
            reason="version order cannot override schema or Matters incompatibility",
        ),
        CaseRule(
            case_id="prerelease_candidate",
            decision="prerelease_candidate_blocked",
            label="prerelease_candidate_blocked",
            writes=("skill_runtime.compatibility_matrix",),
            side_effects=("write_compatibility_receipt",),
            emitted_tokens=("PrereleaseNotAdmitted", "CompatibilityDisposition"),
            reason="a prerelease is blocked unless the frozen policy explicitly admits it",
        ),
        CaseRule(
            case_id="researchguard_integration_incomplete",
            decision="researchguard_pending_integration",
            label="researchguard_pending_integration",
            writes=(
                "skill_runtime.compatibility_matrix",
                "skill_runtime.researchguard_integration_status",
            ),
            side_effects=("write_compatibility_receipt",),
            emitted_tokens=("ResearchGuardPending", "CompatibilityDisposition"),
            reason="missing package, pack, manifest, command, or validation keeps integration pending",
        ),
        CaseRule(
            case_id="researchguard_integration_current",
            decision="researchguard_compatible_current",
            label="researchguard_compatible_current",
            writes=(
                "skill_runtime.compatibility_matrix",
                "skill_runtime.researchguard_integration_status",
            ),
            side_effects=("write_compatibility_receipt",),
            emitted_tokens=("ResearchGuardIdentity", "CompatibilityDisposition"),
            reason="one frozen package and consumer pack pass all compatibility gates",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-S2-001-hash-collision-accepted",
            protected_error_class="same_version_hash_collision_escape",
            description="same-version different-hash candidates are treated as one identity",
            protected_harm="unreviewed bytes gain authority under a trusted version",
            case_id="same_version_different_hash",
            broken_decision="exact_identity_compatible",
            broken_writes=("skill_runtime.compatibility_matrix",),
            broken_side_effects=("write_compatibility_receipt",),
            broken_tokens=("ExactIdentity",),
        ),
        HazardSpec(
            failure_id="H-S2-002-incompatible-accepted",
            protected_error_class="compatibility_gate_bypass",
            description="an incompatible candidate is admitted by numerical version order",
            protected_harm="runtime contracts no longer match the current Matters version",
            case_id="incompatible_candidate",
            broken_decision="candidate_compatible",
            broken_writes=("skill_runtime.compatibility_matrix",),
            broken_side_effects=("write_compatibility_receipt",),
            broken_tokens=("CompatibleCandidate",),
        ),
        HazardSpec(
            failure_id="H-S2-003-prerelease-accepted",
            protected_error_class="prerelease_policy_bypass",
            description="a prerelease candidate activates without explicit admission",
            protected_harm="unstable candidate bytes silently replace a frozen runtime",
            case_id="prerelease_candidate",
            broken_decision="candidate_compatible",
            broken_writes=("skill_runtime.compatibility_matrix",),
            broken_side_effects=("write_compatibility_receipt",),
            broken_tokens=("CompatibleCandidate",),
        ),
        HazardSpec(
            failure_id="H-S2-004-researchguard-pending-current",
            protected_error_class="researchguard_incomplete_false_current",
            description="incomplete ResearchGuard integration is marked current",
            protected_harm="real research executes without a frozen singular provider identity",
            case_id="researchguard_integration_incomplete",
            broken_decision="researchguard_compatible_current",
            broken_writes=("skill_runtime.researchguard_integration_status",),
            broken_side_effects=("write_compatibility_receipt",),
            broken_tokens=("ResearchGuardIdentity",),
        ),
    ),
    risk_classes=("compatibility", "identity", "validation", "freshness"),
    template_no_match_reason="No compatible-candidate matrix template matches Matters Skill Pack identities.",
    blindspots=("real semantic-version parsing and native validator execution await implementation",),
    claim_boundary=(
        "S2 proves declared compatibility and blocking dispositions, not the "
        "truth of real manifests, versions, validators, or ResearchGuard bytes."
    ),
)


S3 = FiniteModelSpec(
    model_id="S3_active_skill_resolution",
    title="S3 Active Skill Resolution",
    modeled_boundary=(
        "one deterministic validated active view with rejected-candidate visibility, "
        "freshness invalidation, and no legacy fallback"
    ),
    state_fields=(
        "skill_runtime.candidate_dispositions",
        "skill_runtime.active_view_identity",
        "skill_runtime.active_view_freshness",
    ),
    owned_write_fields=(
        "skill_runtime.candidate_dispositions",
        "skill_runtime.active_view_identity",
        "skill_runtime.active_view_freshness",
    ),
    side_effect_classes=("write_active_view_receipt",),
    completion_evidence=("CandidateDispositions", "ActiveViewDisposition"),
    rules=(
        CaseRule(
            case_id="exact_match_candidates",
            decision="exact_identity_selected",
            label="exact_identity_selected",
            writes=(
                "skill_runtime.candidate_dispositions",
                "skill_runtime.active_view_identity",
                "skill_runtime.active_view_freshness",
            ),
            side_effects=("write_active_view_receipt",),
            emitted_tokens=("ExactActiveIdentity", "ActiveViewDisposition"),
            reason="identical validated candidates bind one exact identity deterministically",
        ),
        CaseRule(
            case_id="newer_compatible_local_overlay",
            decision="local_overlay_selected_non_mutating",
            label="local_overlay_selected_non_mutating",
            writes=(
                "skill_runtime.candidate_dispositions",
                "skill_runtime.active_view_identity",
                "skill_runtime.active_view_freshness",
            ),
            side_effects=("write_active_view_receipt",),
            emitted_tokens=("LocalOverlayActive", "BundledBytesUnchanged", "ActiveViewDisposition"),
            reason="compatible newer local candidate overlays without modifying bundled bytes",
        ),
        CaseRule(
            case_id="bundled_newer_unmanaged_local",
            decision="bundled_selected_unmanaged_update_available",
            label="bundled_selected_unmanaged_update_available",
            writes=(
                "skill_runtime.candidate_dispositions",
                "skill_runtime.active_view_identity",
                "skill_runtime.active_view_freshness",
            ),
            side_effects=("write_active_view_receipt",),
            emitted_tokens=("BundledActive", "UnmanagedLocalUnchanged", "UpdateAvailable", "ActiveViewDisposition"),
            reason="bundled internal view wins while the external installation is untouched",
        ),
        CaseRule(
            case_id="bundled_newer_matters_managed",
            decision="bundled_selected_sync_required",
            label="bundled_selected_sync_required",
            writes=(
                "skill_runtime.candidate_dispositions",
                "skill_runtime.active_view_identity",
                "skill_runtime.active_view_freshness",
            ),
            side_effects=("write_active_view_receipt",),
            emitted_tokens=("BundledActive", "ManagedSyncRequired", "ActiveViewDisposition"),
            reason="only the separately identified Matters-managed projection may synchronize",
        ),
        CaseRule(
            case_id="same_version_hash_collision",
            decision="active_view_collision_blocked",
            label="active_view_collision_blocked",
            writes=("skill_runtime.candidate_dispositions", "skill_runtime.active_view_freshness"),
            side_effects=("write_active_view_receipt",),
            emitted_tokens=("IdentityCollision", "ActiveViewDisposition"),
            reason="collision remains visible and no candidate silently wins",
        ),
        CaseRule(
            case_id="no_compatible_candidate",
            decision="required_skill_blocked",
            label="required_skill_blocked",
            writes=("skill_runtime.candidate_dispositions", "skill_runtime.active_view_freshness"),
            side_effects=("write_active_view_receipt",),
            emitted_tokens=("NoCompatibleCandidate", "ActiveViewDisposition"),
            reason="required skill remains visibly blocked without downgrade or fallback",
        ),
        CaseRule(
            case_id="active_view_input_changed",
            decision="active_view_stale_recompute_required",
            label="active_view_stale_recompute_required",
            writes=("skill_runtime.active_view_freshness",),
            side_effects=("write_active_view_receipt",),
            emitted_tokens=("ActiveViewStale", "ResolutionRequired", "ActiveViewDisposition"),
            reason="bundle, local, compatibility, or validator identity change invalidates selection",
        ),
        CaseRule(
            case_id="legacy_three_guard_candidate",
            decision="legacy_candidate_source_only",
            label="legacy_candidate_source_only",
            writes=("skill_runtime.candidate_dispositions",),
            side_effects=("write_active_view_receipt",),
            emitted_tokens=("LegacyBindingSourceOnly", "ActiveViewDisposition"),
            reason="legacy Guard receipts cannot become an alternate runtime success path",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-S3-001-stale-view-accepted",
            protected_error_class="active_view_freshness_bypass",
            description="changed inputs retain the old active skill identity",
            protected_harm="selection evidence no longer describes executable bytes",
            case_id="active_view_input_changed",
            broken_decision="active_identity_reused",
            broken_writes=("skill_runtime.active_view_identity",),
            broken_side_effects=("write_active_view_receipt",),
            broken_tokens=("ExactActiveIdentity",),
        ),
        HazardSpec(
            failure_id="H-S3-002-legacy-provider-selected",
            protected_error_class="legacy_guard_resolution_fallback",
            description="a legacy Guard candidate becomes an active provider",
            protected_harm="ResearchGuard singular-provider authority is bypassed",
            case_id="legacy_three_guard_candidate",
            broken_decision="legacy_provider_selected",
            broken_writes=("skill_runtime.active_view_identity",),
            broken_side_effects=("write_active_view_receipt",),
            broken_tokens=("LegacyGuardProvider",),
        ),
        HazardSpec(
            failure_id="H-S3-003-collision-winner-guessed",
            protected_error_class="identity_collision_silent_selection",
            description="one same-version different-hash candidate wins by guess",
            protected_harm="ambiguous bytes become active without selected authority",
            case_id="same_version_hash_collision",
            broken_decision="candidate_selected",
            broken_writes=("skill_runtime.active_view_identity",),
            broken_side_effects=("write_active_view_receipt",),
            broken_tokens=("GuessedActiveIdentity",),
        ),
    ),
    risk_classes=("selection", "freshness", "identity", "fallback"),
    template_no_match_reason="No active-view resolver template owns this four-identity partition.",
    blindspots=("actual discovery order and filesystem overlays await implementation conformance",),
    claim_boundary=(
        "S3 proves the finite singular-selection and stale/fallback blockers. "
        "It does not prove discovery, installed bytes, or runtime loading."
    ),
)


S4 = FiniteModelSpec(
    model_id="S4_matters_managed_skill_sync",
    title="S4 Matters-Managed Skill Synchronization",
    modeled_boundary=(
        "no-install bundled use, immutable external installations, and staged "
        "transactional synchronization only for a Matters-managed projection"
    ),
    state_fields=(
        "skill_runtime.managed_projection_identity",
        "skill_runtime.sync_transaction_state",
        "skill_runtime.prior_projection_identity",
    ),
    owned_write_fields=(
        "skill_runtime.managed_projection_identity",
        "skill_runtime.sync_transaction_state",
        "skill_runtime.prior_projection_identity",
    ),
    side_effect_classes=(
        "stage_managed_projection",
        "activate_managed_projection",
        "write_sync_receipt",
    ),
    completion_evidence=("ManagedProjectionDisposition", "SyncTransactionReceipt"),
    rules=(
        CaseRule(
            case_id="bundled_only_no_global_install",
            decision="no_install_required",
            label="no_install_required",
            writes=("skill_runtime.sync_transaction_state",),
            side_effects=("write_sync_receipt",),
            emitted_tokens=("BundledInternalView", "NoGlobalInstall", "ManagedProjectionDisposition"),
            reason="app-local bundled use completes without global mutation",
        ),
        CaseRule(
            case_id="bundled_newer_unmanaged_local",
            decision="external_install_unchanged_update_available",
            label="external_install_unchanged_update_available",
            writes=("skill_runtime.sync_transaction_state",),
            side_effects=("write_sync_receipt",),
            emitted_tokens=("UnmanagedLocalUnchanged", "UpdateAvailable", "ManagedProjectionDisposition"),
            reason="Matters lacks authority to mutate an external installation",
        ),
        CaseRule(
            case_id="bundled_newer_matters_managed",
            decision="managed_projection_staged_and_activated",
            label="managed_projection_staged_and_activated",
            writes=(
                "skill_runtime.managed_projection_identity",
                "skill_runtime.sync_transaction_state",
                "skill_runtime.prior_projection_identity",
            ),
            side_effects=(
                "stage_managed_projection",
                "activate_managed_projection",
                "write_sync_receipt",
            ),
            emitted_tokens=("StagedProjection", "ActivatedProjection", "SyncTransactionReceipt", "ManagedProjectionDisposition"),
            reason="the selected consumer projection is staged, checked, then activated atomically",
        ),
        CaseRule(
            case_id="exact_or_local_overlay_no_sync",
            decision="managed_projection_unchanged",
            label="managed_projection_unchanged",
            writes=("skill_runtime.sync_transaction_state",),
            side_effects=("write_sync_receipt",),
            emitted_tokens=("NoSyncRequired", "ManagedProjectionDisposition"),
            reason="active-view selection does not imply installation synchronization",
        ),
        CaseRule(
            case_id="staging_validation_failed",
            decision="managed_sync_blocked_before_activation",
            label="managed_sync_blocked_before_activation",
            writes=("skill_runtime.sync_transaction_state",),
            side_effects=("stage_managed_projection", "write_sync_receipt"),
            emitted_tokens=("StagingValidationFailed", "ManagedProjectionDisposition"),
            reason="failed staged content never reaches activation",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-S4-001-bundled-only-global-install",
            protected_error_class="unnecessary_global_skill_mutation",
            description="bundled-only operation creates a global installation",
            protected_harm="a local application changes machine-wide behavior",
            case_id="bundled_only_no_global_install",
            broken_decision="global_skill_installed",
            broken_writes=("skill_runtime.managed_projection_identity",),
            broken_side_effects=("activate_managed_projection",),
            broken_tokens=("GlobalInstall",),
        ),
        HazardSpec(
            failure_id="H-S4-002-unmanaged-overwritten",
            protected_error_class="external_installation_authority_escape",
            description="an unmanaged external installation is overwritten",
            protected_harm="Matters mutates state it does not own",
            case_id="bundled_newer_unmanaged_local",
            broken_decision="external_install_updated",
            broken_writes=("skill_runtime.managed_projection_identity",),
            broken_side_effects=("activate_managed_projection",),
            broken_tokens=("ExternalInstallUpdated",),
        ),
        HazardSpec(
            failure_id="H-S4-003-direct-activation",
            protected_error_class="managed_sync_transaction_bypass",
            description="a Matters-managed update activates without staging",
            protected_harm="invalid bytes can replace the previous active projection",
            case_id="bundled_newer_matters_managed",
            broken_decision="managed_projection_activated_directly",
            broken_writes=(
                "skill_runtime.managed_projection_identity",
                "skill_runtime.sync_transaction_state",
            ),
            broken_side_effects=("activate_managed_projection", "write_sync_receipt"),
            broken_tokens=("ActivatedProjection",),
        ),
    ),
    risk_classes=("transaction", "ownership", "side_effect", "rollback"),
    template_ids=("side_effect_at_most_once",),
    blindspots=("real filesystem atomicity and crash recovery await implementation conformance",),
    claim_boundary=(
        "S4 proves abstract installation authority and staged transaction rules. "
        "It performs no real installation, staging, activation, or rollback."
    ),
)


S5 = FiniteModelSpec(
    model_id="S5_skill_validation_rollback",
    title="S5 Skill Validation And Rollback",
    modeled_boundary=(
        "native validation, installed-currentness, activation publication, "
        "and restoration of the prior managed projection on post-activation failure"
    ),
    state_fields=(
        "skill_runtime.validation_receipt_set",
        "skill_runtime.rollback_receipt",
        "skill_runtime.activation_status",
    ),
    owned_write_fields=(
        "skill_runtime.validation_receipt_set",
        "skill_runtime.rollback_receipt",
        "skill_runtime.activation_status",
    ),
    side_effect_classes=(
        "run_native_skill_validation",
        "restore_prior_managed_projection",
        "write_validation_receipt",
    ),
    completion_evidence=("ValidationReceiptSet", "RollbackDisposition", "ActivationDisposition"),
    rules=(
        CaseRule(
            case_id="candidate_all_checks_current",
            decision="validated_identity_activated",
            label="validated_identity_activated",
            writes=(
                "skill_runtime.validation_receipt_set",
                "skill_runtime.activation_status",
            ),
            side_effects=("run_native_skill_validation", "write_validation_receipt"),
            emitted_tokens=("ValidationReceiptSet", "ActiveSkillIdentity", "ActivationDisposition"),
            reason="inventory, native validation, and installed currentness are terminal-current",
        ),
        CaseRule(
            case_id="post_activation_check_failed",
            decision="prior_projection_restored_candidate_blocked",
            label="prior_projection_restored_candidate_blocked",
            writes=(
                "skill_runtime.validation_receipt_set",
                "skill_runtime.rollback_receipt",
                "skill_runtime.activation_status",
            ),
            side_effects=(
                "run_native_skill_validation",
                "restore_prior_managed_projection",
                "write_validation_receipt",
            ),
            emitted_tokens=("FailedCandidate", "RollbackReceipt", "ActivationDisposition"),
            reason="post-activation failure restores the prior Matters-managed projection",
        ),
        CaseRule(
            case_id="invalid_or_incompatible_candidate",
            decision="validation_blocked_before_publication",
            label="validation_blocked_before_publication",
            writes=("skill_runtime.validation_receipt_set", "skill_runtime.activation_status"),
            side_effects=("run_native_skill_validation", "write_validation_receipt"),
            emitted_tokens=("CandidateBlocked", "ActivationDisposition"),
            reason="invalid or incompatible candidate never publishes an active identity",
        ),
        CaseRule(
            case_id="author_control_residual_detected",
            decision="consumer_projection_residual_blocked",
            label="consumer_projection_residual_blocked",
            writes=("skill_runtime.validation_receipt_set", "skill_runtime.activation_status"),
            side_effects=("run_native_skill_validation", "write_validation_receipt"),
            emitted_tokens=("AuthorControlResidual", "ActivationDisposition"),
            reason="exact author-side residual remains visible and blocks activation",
        ),
        CaseRule(
            case_id="researchguard_integration_pending",
            decision="researchguard_pending_integration",
            label="researchguard_pending_integration",
            writes=("skill_runtime.validation_receipt_set", "skill_runtime.activation_status"),
            side_effects=("run_native_skill_validation", "write_validation_receipt"),
            emitted_tokens=("ResearchGuardPending", "ActivationDisposition"),
            reason="synthetic ResearchOperation remains runnable but real research does not activate",
        ),
        CaseRule(
            case_id="researchguard_integration_current",
            decision="researchguard_identity_current",
            label="researchguard_identity_current",
            writes=("skill_runtime.validation_receipt_set", "skill_runtime.activation_status"),
            side_effects=("run_native_skill_validation", "write_validation_receipt"),
            emitted_tokens=("ResearchGuardIdentity", "ActivationDisposition"),
            reason="one exact ResearchGuard package and consumer pack pass all declared checks",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-S5-001-post-failure-no-rollback",
            protected_error_class="post_activation_rollback_failure",
            description="post-activation validation fails but the candidate remains active",
            protected_harm="a failed skill projection replaces the last known-good version",
            case_id="post_activation_check_failed",
            broken_decision="failed_candidate_kept_active",
            broken_writes=("skill_runtime.activation_status",),
            broken_side_effects=("run_native_skill_validation", "write_validation_receipt"),
            broken_tokens=("ActiveSkillIdentity",),
        ),
        HazardSpec(
            failure_id="H-S5-002-invalid-published",
            protected_error_class="invalid_skill_activation",
            description="an invalid or incompatible candidate publishes an active identity",
            protected_harm="unvalidated behavior becomes executable",
            case_id="invalid_or_incompatible_candidate",
            broken_decision="validated_identity_activated",
            broken_writes=("skill_runtime.activation_status",),
            broken_side_effects=("write_validation_receipt",),
            broken_tokens=("ActiveSkillIdentity",),
        ),
        HazardSpec(
            failure_id="H-S5-003-author-control-published",
            protected_error_class="author_control_activation_escape",
            description="a consumer projection with author-control residuals activates",
            protected_harm="maintainer-only authority enters consumer runtime",
            case_id="author_control_residual_detected",
            broken_decision="validated_identity_activated",
            broken_writes=("skill_runtime.activation_status",),
            broken_side_effects=("write_validation_receipt",),
            broken_tokens=("ActiveSkillIdentity",),
        ),
        HazardSpec(
            failure_id="H-S5-004-researchguard-pending-fallback",
            protected_error_class="researchguard_pending_legacy_fallback",
            description="pending ResearchGuard falls back to separate legacy Guard runtimes",
            protected_harm="the singular research provider contract is bypassed",
            case_id="researchguard_integration_pending",
            broken_decision="legacy_guard_runtime_activated",
            broken_writes=("skill_runtime.activation_status",),
            broken_side_effects=("write_validation_receipt",),
            broken_tokens=("LegacyGuardProvider",),
        ),
    ),
    risk_classes=("validation", "rollback", "freshness", "fallback"),
    template_ids=("side_effect_at_most_once",),
    blindspots=("real native validators, installed currentness, and filesystem restore are not executed",),
    claim_boundary=(
        "S5 proves abstract validation, residual, pending/current ResearchGuard, "
        "and rollback dispositions. It performs no real skill activation or restore."
    ),
)


CHILDREN = (S1, S2, S3, S4, S5)
MODELS = {spec.model_id: spec for spec in (S0,) + CHILDREN}
