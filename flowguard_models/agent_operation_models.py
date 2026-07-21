"""Agent-operation-plane FlowGuard models for bounded AI execution."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


A0 = FiniteModelSpec(
    model_id="A0_matters_source_analysis_operation",
    title="A0 Bounded Source Analysis Operation",
    modeled_boundary=(
        "route one model-agnostic WorkPackageV2 by declared capability and execute "
        "it through a replaceable private Codex profile using only declared "
        "evidence, tools, prompt, schema, policy, owner, locale and skill "
        "identities; account every input and emit one terminal receipt without "
        "product-runtime writes or an app-owned API-key fallback"
    ),
    state_fields=(
        "analysis_operation.execution_status",
        "analysis_operation.assignment_selector_identity",
        "analysis_operation.capability_role",
        "analysis_operation.execution_profile_identity",
        "analysis_operation.concrete_execution_identity",
        "analysis_operation.escalation_status",
        "analysis_operation.input_dispositions",
        "analysis_operation.raw_result_handle",
        "analysis_operation.resource_usage",
        "analysis_operation.terminal_receipt",
    ),
    owned_write_fields=(
        "analysis_operation.execution_status",
        "analysis_operation.assignment_selector_identity",
        "analysis_operation.capability_role",
        "analysis_operation.execution_profile_identity",
        "analysis_operation.concrete_execution_identity",
        "analysis_operation.escalation_status",
        "analysis_operation.input_dispositions",
        "analysis_operation.raw_result_handle",
        "analysis_operation.resource_usage",
        "analysis_operation.terminal_receipt",
    ),
    side_effect_classes=("analysis_operation_receipt_write",),
    completion_evidence=(
        "WorkPackageV2Accepted",
        "ExactAssignedPackageSet",
        "ExecutionProfilePublished",
        "CapabilityRoleResolved",
        "CapabilityEscalated",
        "CapabilityUnavailable",
        "HeroGenerationCapabilityResolved",
        "ExecutionProfileChanged",
        "InputDispositionSet",
        "AnalysisOperationTerminalReceipt",
        "OperationBlocked",
    ),
    rules=(
        CaseRule(
            case_id="pending_package_envelope_profile_current",
            decision="runtime_execution_profile_published",
            label="runtime_execution_profile_published",
            writes=(
                "analysis_operation.execution_profile_identity",
            ),
            emitted_tokens=(
                "WorkPackageV2Accepted",
                "ExecutionProfilePublished",
            ),
            reason=(
                "the bounded pending-package response publishes the current "
                "private execution-profile identity beside immutable packages "
                "so a Codex worker can bind a result without changing package identity"
            ),
        ),
        CaseRule(
            case_id="exact_worker_assignment_selected",
            decision="exact_assigned_package_set_returned",
            label="exact_assigned_package_set_returned",
            writes=(
                "analysis_operation.assignment_selector_identity",
            ),
            emitted_tokens=(
                "WorkPackageV2Accepted",
                "ExactAssignedPackageSet",
            ),
            reason=(
                "conjunctive package-id, source-revision, and task-kind "
                "selectors are applied before pagination so a background "
                "capability worker receives only its explicitly assigned "
                "pending package set"
            ),
        ),
        CaseRule(
            case_id="valid_work_package_v2",
            decision="analysis_operation_current",
            label="analysis_operation_current",
            writes=(
                "analysis_operation.execution_status",
                "analysis_operation.capability_role",
                "analysis_operation.execution_profile_identity",
                "analysis_operation.concrete_execution_identity",
                "analysis_operation.escalation_status",
                "analysis_operation.input_dispositions",
                "analysis_operation.raw_result_handle",
                "analysis_operation.resource_usage",
                "analysis_operation.terminal_receipt",
            ),
            side_effects=("analysis_operation_receipt_write",),
            emitted_tokens=(
                "WorkPackageV2Accepted",
                "InputDispositionSet",
                "AnalysisOperationTerminalReceipt",
            ),
            reason="every declared input is used, excluded-with-reason, or terminally unsupported",
        ),
        CaseRule(
            case_id="low_cost_annotation_profile_current",
            decision="low_cost_annotation_executed",
            label="low_cost_annotation_executed",
            writes=(
                "analysis_operation.execution_status",
                "analysis_operation.capability_role",
                "analysis_operation.execution_profile_identity",
                "analysis_operation.concrete_execution_identity",
                "analysis_operation.input_dispositions",
                "analysis_operation.resource_usage",
                "analysis_operation.terminal_receipt",
            ),
            side_effects=("analysis_operation_receipt_write",),
            emitted_tokens=(
                "WorkPackageV2Accepted",
                "CapabilityRoleResolved",
                "InputDispositionSet",
                "AnalysisOperationTerminalReceipt",
            ),
            reason=(
                "low_cost_annotator may use the current machine's cheap Codex "
                "mapping while the validated result contract stays model-independent"
            ),
        ),
        CaseRule(
            case_id="complex_capability_escalated",
            decision="complex_capability_routed",
            label="complex_capability_routed",
            writes=(
                "analysis_operation.execution_status",
                "analysis_operation.capability_role",
                "analysis_operation.execution_profile_identity",
                "analysis_operation.concrete_execution_identity",
                "analysis_operation.escalation_status",
                "analysis_operation.terminal_receipt",
            ),
            side_effects=("analysis_operation_receipt_write",),
            emitted_tokens=(
                "CapabilityEscalated",
                "AnalysisOperationTerminalReceipt",
            ),
            reason=(
                "ambiguity, Matter modeling, or consistency review uses a "
                "compatible stronger profile mapping instead of pretending a "
                "cheap annotation satisfied the complex contract"
            ),
        ),
        CaseRule(
            case_id="hero_generation_capability_current",
            decision="hero_generation_profile_resolved",
            label="hero_generation_profile_resolved",
            writes=(
                "analysis_operation.capability_role",
                "analysis_operation.execution_profile_identity",
                "analysis_operation.concrete_execution_identity",
                "analysis_operation.terminal_receipt",
            ),
            side_effects=("analysis_operation_receipt_write",),
            emitted_tokens=(
                "HeroGenerationCapabilityResolved",
                "AnalysisOperationTerminalReceipt",
            ),
            reason=(
                "hero_image_generator resolves through an available private "
                "image-generation capability after Matter identity stabilizes; "
                "its presentation artifact is joined separately from evidence"
            ),
        ),
        CaseRule(
            case_id="execution_profile_mapping_changed",
            decision="same_capability_contract_preserved",
            label="same_capability_contract_preserved",
            writes=(
                "analysis_operation.execution_profile_identity",
                "analysis_operation.concrete_execution_identity",
                "analysis_operation.terminal_receipt",
            ),
            side_effects=("analysis_operation_receipt_write",),
            emitted_tokens=("ExecutionProfileChanged", "AnalysisOperationTerminalReceipt"),
            reason=(
                "a concrete model or reasoning-level substitution changes only "
                "the private execution identity, not the product work-package schema"
            ),
        ),
        CaseRule(
            case_id="capability_mapping_unavailable",
            decision="analysis_operation_pending_capability",
            label="analysis_operation_pending_capability",
            writes=(
                "analysis_operation.execution_status",
                "analysis_operation.capability_role",
                "analysis_operation.execution_profile_identity",
                "analysis_operation.terminal_receipt",
            ),
            side_effects=("analysis_operation_receipt_write",),
            emitted_tokens=("CapabilityUnavailable", "AnalysisOperationTerminalReceipt"),
            reason=(
                "no compatible Codex mapping remains visible and resumable "
                "without a direct provider API fallback"
            ),
        ),
        CaseRule(
            case_id="application_api_key_fallback_attempt",
            decision="direct_api_fallback_rejected",
            label="direct_api_fallback_rejected",
            writes=(
                "analysis_operation.execution_status",
                "analysis_operation.terminal_receipt",
            ),
            side_effects=("analysis_operation_receipt_write",),
            emitted_tokens=("OperationBlocked", "AnalysisOperationTerminalReceipt"),
            reason=(
                "the application cannot request or own an OpenAI API key when "
                "the machine-local Codex capability mapping is unavailable"
            ),
        ),
        CaseRule(
            case_id="no_finding",
            decision="analysis_operation_no_finding",
            label="analysis_operation_no_finding",
            writes=(
                "analysis_operation.execution_status",
                "analysis_operation.input_dispositions",
                "analysis_operation.terminal_receipt",
            ),
            side_effects=("analysis_operation_receipt_write",),
            emitted_tokens=("InputDispositionSet", "AnalysisOperationTerminalReceipt"),
            reason="no-finding is a valid terminal only with complete input accounting",
        ),
        CaseRule(
            case_id="invalid_schema_or_scope_escape",
            decision="analysis_operation_blocked",
            label="analysis_operation_blocked",
            writes=(
                "analysis_operation.execution_status",
                "analysis_operation.terminal_receipt",
            ),
            side_effects=("analysis_operation_receipt_write",),
            emitted_tokens=("OperationBlocked", "AnalysisOperationTerminalReceipt"),
            reason="invalid output, adjacent reads, or undeclared tools fail before product dispatch",
        ),
        CaseRule(
            case_id="operation_attempts_product_write",
            decision="product_write_rejected",
            label="product_write_rejected",
            emitted_tokens=("OwnerWriteRejected",),
            reason="the operation plane emits a receipt and never writes a C1-C12 field",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-A0-007-profile-identity-not-published",
            protected_error_class="analysis_runtime_identity_projection_gap",
            description=(
                "a pending-package response omits the active execution-profile "
                "identity that result admission requires"
            ),
            protected_harm=(
                "every valid external Codex result is rejected before semantic validation"
            ),
            case_id="pending_package_envelope_profile_current",
            broken_decision="runtime_execution_profile_unknown",
            broken_writes=(),
            broken_tokens=("WorkPackageV2Accepted",),
        ),
        HazardSpec(
            failure_id="H-A0-011-worker-selector-scope-escape",
            protected_error_class="background_worker_assignment_scope_escape",
            description=(
                "an exact background-worker selector is applied after "
                "pagination or ignored, returning unrelated pending packages"
            ),
            protected_harm=(
                "the worker reads or spends capability budget on private "
                "packages outside its assigned source-revision refresh"
            ),
            case_id="exact_worker_assignment_selected",
            broken_decision="unfiltered_pending_page_returned",
            broken_writes=(
                "analysis_operation.assignment_selector_identity",
            ),
            broken_tokens=("WorkPackageV2Accepted",),
        ),
        HazardSpec(
            failure_id="H-A0-001-missing-input-accounting",
            protected_error_class="analysis_input_loss",
            description="a current operation omits one declared input disposition",
            protected_harm="registered content silently disappears from modeling",
            case_id="no_finding",
            broken_decision="analysis_operation_no_finding",
            broken_writes=(
                "analysis_operation.execution_status",
                "analysis_operation.terminal_receipt",
            ),
            broken_side_effects=("analysis_operation_receipt_write",),
            broken_tokens=("AnalysisOperationTerminalReceipt",),
        ),
        HazardSpec(
            failure_id="H-A0-002-scope-escape-accepted",
            protected_error_class="analysis_scope_escape",
            description="an adjacent-source read or undeclared tool is accepted",
            protected_harm="private data or side effects escape the work package",
            case_id="invalid_schema_or_scope_escape",
            broken_decision="analysis_operation_current",
            broken_writes=("analysis_operation.execution_status",),
            broken_tokens=("AnalysisOperationTerminalReceipt",),
        ),
        HazardSpec(
            failure_id="H-A0-003-product-write",
            protected_error_class="agent_operation_plane_escape",
            description="the operation directly writes canonical Matter state",
            protected_harm="AI execution becomes a second product authority",
            case_id="operation_attempts_product_write",
            broken_decision="canonical_state_written",
            broken_writes=("matter.lifecycle_axes",),
            broken_tokens=("LifecycleState",),
        ),
        HazardSpec(
            failure_id="H-A0-004-named-model-becomes-contract",
            protected_error_class="deployment_model_product_dependency",
            description="a concrete model slug becomes a required work-package field",
            protected_harm="changing local model availability invalidates product data and release identity",
            case_id="execution_profile_mapping_changed",
            broken_decision="product_contract_changed",
            broken_writes=("analysis_operation.capability_role",),
            broken_tokens=("WorkPackageSchemaChanged",),
        ),
        HazardSpec(
            failure_id="H-A0-005-cheap-model-satisfies-complex-role",
            protected_error_class="capability_underprovisioning",
            description="a low-cost annotation mapping is reported as completing complex Matter modeling",
            protected_harm="hierarchy or conflict synthesis is accepted without its declared capability",
            case_id="complex_capability_escalated",
            broken_decision="complex_capability_current",
            broken_writes=("analysis_operation.execution_status",),
            broken_tokens=("AnalysisOperationTerminalReceipt",),
        ),
        HazardSpec(
            failure_id="H-A0-006-direct-api-fallback",
            protected_error_class="undeclared_provider_success_path",
            description="an unavailable Codex profile silently falls back to an app-owned API key",
            protected_harm="privacy, cost, and execution ownership leave the declared product boundary",
            case_id="application_api_key_fallback_attempt",
            broken_decision="analysis_operation_current",
            broken_writes=("analysis_operation.concrete_execution_identity",),
            broken_tokens=("AnalysisOperationTerminalReceipt",),
        ),
        HazardSpec(
            failure_id="H-A0-010-generated-hero-result-enters-analysis-evidence",
            protected_error_class="hero_generation_evidence_join_escape",
            description="a hero-generation child result is joined as a factual finding",
            protected_harm="synthetic art becomes evidence for Matter state",
            case_id="hero_generation_capability_current",
            broken_decision="analysis_operation_current",
            broken_writes=("analysis_operation.input_dispositions",),
            broken_side_effects=("analysis_operation_receipt_write",),
            broken_tokens=("InputDispositionSet",),
        ),
    ),
    risk_classes=(
        "authorization",
        "privacy",
        "ownership",
        "side_effect",
        "capability_routing",
        "deployment_substitution",
        "assignment_scope",
    ),
    template_no_match_reason=(
        "No template owns the exact Matters WorkPackageV2 input-accounting and "
        "cross-plane receipt boundary."
    ),
    blindspots=(
        "model quality requires synthetic regressions and private canaries",
        "external-provider disclosure requires separate runtime evidence",
    ),
    claim_boundary=(
        "This model establishes bounded model-agnostic A0 WorkPackageV2 "
        "capability routing, exact background-worker assignment selection, "
        "hero-generation isolation, replaceable private "
        "Codex profiles, escalation, "
        "unavailability, complete input accounting, terminal receipts, scope "
        "rejection, no direct-API fallback, and zero product writes. It does not "
        "prove model quality, concrete model availability, or provider privacy."
    ),
)


A1 = FiniteModelSpec(
    model_id="A1_matters_research_operation",
    title="A1 Abstract ResearchOperation",
    modeled_boundary=(
        "execute one abstract ResearchOperation through one frozen compatible "
        "ResearchGuard provider identity or emit a visible terminal pending/non-pass result"
    ),
    state_fields=(
        "research_operation.provider_identity",
        "research_operation.execution_status",
        "research_operation.result_handle",
        "research_operation.terminal_receipt",
    ),
    owned_write_fields=(
        "research_operation.provider_identity",
        "research_operation.execution_status",
        "research_operation.result_handle",
        "research_operation.terminal_receipt",
    ),
    side_effect_classes=("research_operation_receipt_write",),
    completion_evidence=(
        "ResearchOperationTerminalReceipt",
        "ResearchGuardCurrent",
        "ResearchGuardPending",
        "OperationBlocked",
    ),
    rules=(
        CaseRule(
            case_id="researchguard_identity_current",
            decision="research_operation_current",
            label="research_operation_current",
            writes=(
                "research_operation.provider_identity",
                "research_operation.execution_status",
                "research_operation.result_handle",
                "research_operation.terminal_receipt",
            ),
            side_effects=("research_operation_receipt_write",),
            emitted_tokens=("ResearchGuardCurrent", "ResearchOperationTerminalReceipt"),
            reason="one frozen provider identity returns a current schema-valid anchored result",
        ),
        CaseRule(
            case_id="researchguard_current_result_imported",
            decision="research_operation_current",
            label="research_operation_current",
            writes=(
                "research_operation.provider_identity",
                "research_operation.execution_status",
                "research_operation.result_handle",
                "research_operation.terminal_receipt",
            ),
            side_effects=("research_operation_receipt_write",),
            emitted_tokens=(
                "ResearchGuardCurrent",
                "ResearchOperationTerminalReceipt",
            ),
            reason=(
                "the durable import boundary carries the same current "
                "ResearchGuard identity into result validation"
            ),
        ),
        CaseRule(
            case_id="researchguard_not_current",
            decision="researchguard_pending_integration",
            label="researchguard_pending_integration",
            writes=(
                "research_operation.provider_identity",
                "research_operation.execution_status",
                "research_operation.terminal_receipt",
            ),
            side_effects=("research_operation_receipt_write",),
            emitted_tokens=("ResearchGuardPending", "ResearchOperationTerminalReceipt"),
            reason="missing or incompatible package/skill/manifest/currentness is a visible terminal",
        ),
        CaseRule(
            case_id="legacy_guard_fallback_attempt",
            decision="legacy_fallback_rejected",
            label="legacy_fallback_rejected",
            writes=(
                "research_operation.execution_status",
                "research_operation.terminal_receipt",
            ),
            side_effects=("research_operation_receipt_write",),
            emitted_tokens=("OperationBlocked", "ResearchOperationTerminalReceipt"),
            reason="separate SourceGuard, TraceGuard, or LogicGuard cannot replace ResearchGuard",
        ),
        CaseRule(
            case_id="research_attempts_product_write",
            decision="product_write_rejected",
            label="product_write_rejected",
            emitted_tokens=("OwnerWriteRejected",),
            reason="ResearchOperation remains advisory and never writes C1-C12 state",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-A1-001-pending-claimed-current",
            protected_error_class="researchguard_currentness_overclaim",
            description="a missing or incompatible ResearchGuard is reported current",
            protected_harm="the release claims research execution that cannot run",
            case_id="researchguard_not_current",
            broken_decision="research_operation_current",
            broken_writes=("research_operation.execution_status",),
            broken_tokens=("ResearchGuardCurrent",),
        ),
        HazardSpec(
            failure_id="H-A1-005-current-import-loses-researchguard-identity",
            protected_error_class="researchguard_import_identity_lost",
            description=(
                "a result from the current ResearchGuard reaches the import "
                "boundary without its frozen currentness identity"
            ),
            protected_harm=(
                "valid supplemental research remains permanently pending and "
                "can never reach its original projection owner"
            ),
            case_id="researchguard_current_result_imported",
            broken_decision="researchguard_pending_integration",
            broken_writes=("research_operation.execution_status",),
            broken_tokens=("ResearchGuardCurrent",),
        ),
        HazardSpec(
            failure_id="H-A1-002-legacy-fallback",
            protected_error_class="alternate_research_success_path",
            description="legacy separate Guards silently close the ResearchGuard gap",
            protected_harm="incompatible provider identities appear as one supported route",
            case_id="legacy_guard_fallback_attempt",
            broken_decision="research_operation_current",
            broken_writes=("research_operation.execution_status",),
            broken_tokens=("ResearchGuardCurrent",),
        ),
        HazardSpec(
            failure_id="H-A1-003-product-write",
            protected_error_class="research_operation_plane_escape",
            description="research directly writes canonical Matter state",
            protected_harm="external research becomes a second product authority",
            case_id="research_attempts_product_write",
            broken_decision="canonical_state_written",
            broken_writes=("matter.lifecycle_axes",),
            broken_tokens=("LifecycleState",),
        ),
    ),
    risk_classes=("integration", "ownership", "freshness", "side_effect"),
    template_no_match_reason=(
        "No template owns the exact single-provider ResearchGuard currentness boundary."
    ),
    blindspots=(
        "ResearchGuard substantive correctness remains with its native validation",
        "real provider execution remains blocked until a portable currentness receipt exists",
    ),
    claim_boundary=(
        "This model establishes A1 single-provider currentness, visible pending, "
        "legacy-fallback rejection, terminal receipt, and zero product writes. "
        "It does not prove ResearchGuard installation or research truth."
    ),
)


A2 = FiniteModelSpec(
    model_id="A2_matters_maintenance_orchestrator_operation",
    title="A2 Model-Agnostic Maintenance Orchestrator Operation",
    modeled_boundary=(
        "one strongest-compatible private Codex maintenance_orchestrator owns "
        "a bounded maintenance plan, delegates typed WorkPackageV2 tasks to A0 "
        "and research tasks to A1, validates and joins their terminal receipts, "
        "applies bounded retry/escalation, and emits one terminal maintenance "
        "receipt without product writes, named-model product contracts, direct "
        "provider API fallback, or final release-gate authority"
    ),
    state_fields=(
        "maintenance_operation.run_identity",
        "maintenance_operation.plan_revision",
        "maintenance_operation.execution_profile_identity",
        "maintenance_operation.concrete_execution_identity",
        "maintenance_operation.delegation_registry",
        "maintenance_operation.child_terminal_receipt_set",
        "maintenance_operation.child_result_join_status",
        "maintenance_operation.retry_budget",
        "maintenance_operation.resource_budget",
        "maintenance_operation.completion_status",
        "maintenance_operation.terminal_receipt",
    ),
    owned_write_fields=(
        "maintenance_operation.run_identity",
        "maintenance_operation.plan_revision",
        "maintenance_operation.execution_profile_identity",
        "maintenance_operation.concrete_execution_identity",
        "maintenance_operation.delegation_registry",
        "maintenance_operation.child_terminal_receipt_set",
        "maintenance_operation.child_result_join_status",
        "maintenance_operation.retry_budget",
        "maintenance_operation.resource_budget",
        "maintenance_operation.completion_status",
        "maintenance_operation.terminal_receipt",
    ),
    side_effect_classes=(
        "maintenance_operation_receipt_write",
        "delegated_work_dispatch",
    ),
    completion_evidence=(
        "MaintenanceOrchestratorCurrent",
        "MaintenancePlanCurrent",
        "DelegatedWorkPackage",
        "DelegatedResultJoined",
        "AIFeedbackOwnerTerminal",
        "MaintenanceNoDelta",
        "MaintenanceGap",
        "MaintenanceOperationTerminalReceipt",
        "OwnerWriteRejected",
    ),
    rules=(
        CaseRule(
            case_id="maintenance_run_started",
            decision="strongest_compatible_orchestrator_current",
            label="strongest_compatible_orchestrator_current",
            writes=(
                "maintenance_operation.run_identity",
                "maintenance_operation.execution_profile_identity",
                "maintenance_operation.concrete_execution_identity",
                "maintenance_operation.retry_budget",
                "maintenance_operation.resource_budget",
                "maintenance_operation.completion_status",
            ),
            side_effects=("maintenance_operation_receipt_write",),
            emitted_tokens=("MaintenanceOrchestratorCurrent",),
            reason=(
                "one machine-local strongest compatible Codex profile owns plan, "
                "joins, escalation, retries, and the terminal maintenance claim; "
                "its concrete identity remains private and replaceable"
            ),
        ),
        CaseRule(
            case_id="bounded_maintenance_plan_validated",
            decision="maintenance_plan_current",
            label="maintenance_plan_current",
            writes=(
                "maintenance_operation.plan_revision",
                "maintenance_operation.delegation_registry",
                "maintenance_operation.retry_budget",
                "maintenance_operation.resource_budget",
            ),
            side_effects=(
                "maintenance_operation_receipt_write",
                "delegated_work_dispatch",
            ),
            emitted_tokens=("MaintenancePlanCurrent", "DelegatedWorkPackage"),
            reason=(
                "the plan contains bounded typed deterministic preprocessing, "
                "low-cost annotation, ambiguity resolution, Matter modeling, "
                "hero generation, consistency review, or research packages; "
                "every package has one declared A0/A1 owner and no product write"
            ),
        ),
        CaseRule(
            case_id="all_delegated_results_terminal_and_valid",
            decision="delegated_results_joined_terminal",
            label="delegated_results_joined_terminal",
            writes=(
                "maintenance_operation.child_terminal_receipt_set",
                "maintenance_operation.child_result_join_status",
                "maintenance_operation.completion_status",
                "maintenance_operation.terminal_receipt",
            ),
            side_effects=("maintenance_operation_receipt_write",),
            emitted_tokens=(
                "DelegatedResultJoined",
                "MaintenanceOperationTerminalReceipt",
            ),
            reason=(
                "the orchestrator validates every typed child receipt, requires "
                "each accepted semantic output to return through its original "
                "product owner, and alone declares the run terminal"
            ),
        ),
        CaseRule(
            case_id="pending_ai_user_observation_consumed",
            decision="ai_feedback_original_owner_terminal",
            label="ai_feedback_original_owner_terminal",
            writes=(
                "maintenance_operation.delegation_registry",
                "maintenance_operation.child_terminal_receipt_set",
                "maintenance_operation.child_result_join_status",
                "maintenance_operation.completion_status",
                "maintenance_operation.terminal_receipt",
            ),
            side_effects=(
                "delegated_work_dispatch",
                "maintenance_operation_receipt_write",
            ),
            emitted_tokens=(
                "AIFeedbackOwnerTerminal",
                "MaintenanceOperationTerminalReceipt",
            ),
            reason=(
                "A2 consumes each bounded pending A3 observation exactly once, "
                "dispatches it to the declared existing C1-C12 owner, and records "
                "processed, rejected, or blocked as an immutable terminal receipt; "
                "neither A2 nor A3 writes the owner's canonical product field"
            ),
        ),
        CaseRule(
            case_id="maintenance_no_delta",
            decision="maintenance_no_delta_terminal",
            label="maintenance_no_delta_terminal",
            writes=(
                "maintenance_operation.plan_revision",
                "maintenance_operation.child_result_join_status",
                "maintenance_operation.completion_status",
                "maintenance_operation.terminal_receipt",
            ),
            side_effects=("maintenance_operation_receipt_write",),
            emitted_tokens=(
                "MaintenanceNoDelta",
                "MaintenanceOperationTerminalReceipt",
            ),
            reason=(
                "a current source, Matter, policy, skill, and projection identity "
                "with no missing or stale stage emits a terminal no-delta receipt "
                "without creating child work"
            ),
        ),
        CaseRule(
            case_id="child_failed_blocked_or_retry_exhausted",
            decision="maintenance_gap_terminal_visible",
            label="maintenance_gap_terminal_visible",
            writes=(
                "maintenance_operation.child_terminal_receipt_set",
                "maintenance_operation.child_result_join_status",
                "maintenance_operation.retry_budget",
                "maintenance_operation.completion_status",
                "maintenance_operation.terminal_receipt",
            ),
            side_effects=("maintenance_operation_receipt_write",),
            emitted_tokens=(
                "MaintenanceGap",
                "MaintenanceOperationTerminalReceipt",
            ),
            reason=(
                "failed, blocked, stale, underpowered, or retry-exhausted child "
                "work remains an exact visible gap and cannot be reported current"
            ),
        ),
        CaseRule(
            case_id="orchestrator_attempts_product_or_final_gate_write",
            decision="orchestrator_authority_escape_rejected",
            label="orchestrator_authority_escape_rejected",
            emitted_tokens=("OwnerWriteRejected", "MaintenanceGap"),
            reason=(
                "routine maintenance may dispatch original owners but cannot "
                "write C1-C12 state or own final model, test, install, Git, tag, "
                "release, or publication gates"
            ),
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-A2-001-multiple-maintenance-completion-owners",
            protected_error_class="maintenance_orchestration_split_brain",
            description="multiple profiles independently own plan, joins, retry, or completion",
            protected_harm="work is duplicated, contradictory, or silently omitted",
            case_id="maintenance_run_started",
            broken_decision="parallel_completion_owners_current",
            broken_writes=(
                "maintenance_operation.run_identity",
                "maintenance_operation.completion_status",
            ),
            broken_side_effects=("maintenance_operation_receipt_write",),
            broken_tokens=("MaintenanceOrchestratorCurrent",),
        ),
        HazardSpec(
            failure_id="H-A2-002-cheap-child-agent-becomes-final-owner",
            protected_error_class="orchestrator_completion_authority_escape",
            description="a delegated low-cost result directly claims Matter modeling or run completion",
            protected_harm="underpowered child work bypasses strongest-profile review and typed joins",
            case_id="all_delegated_results_terminal_and_valid",
            broken_decision="maintenance_current_from_unjoined_child",
            broken_writes=(
                "maintenance_operation.child_result_join_status",
                "maintenance_operation.completion_status",
            ),
            broken_side_effects=("maintenance_operation_receipt_write",),
            broken_tokens=("MaintenanceOperationTerminalReceipt",),
        ),
        HazardSpec(
            failure_id="H-A2-003-unbounded-delegation-or-retry",
            protected_error_class="maintenance_work_fanout_liveness_failure",
            description="the plan or retry loop creates unbounded or identical repeated child packages",
            protected_harm="maintenance consumes the machine indefinitely and starves the UI",
            case_id="bounded_maintenance_plan_validated",
            broken_decision="unbounded_plan_dispatched",
            broken_writes=(
                "maintenance_operation.delegation_registry",
                "maintenance_operation.retry_budget",
            ),
            broken_side_effects=("delegated_work_dispatch",),
            broken_tokens=("DelegatedWorkPackage",),
        ),
        HazardSpec(
            failure_id="H-A2-004-child-gap-claimed-current",
            protected_error_class="maintenance_child_gap_false_complete",
            description="a failed, blocked, stale, or retry-exhausted child is omitted from completion",
            protected_harm="unprocessed files, mail, heroes, or Matter revisions disappear from the run",
            case_id="child_failed_blocked_or_retry_exhausted",
            broken_decision="delegated_results_joined_terminal",
            broken_writes=(
                "maintenance_operation.child_result_join_status",
                "maintenance_operation.completion_status",
            ),
            broken_side_effects=("maintenance_operation_receipt_write",),
            broken_tokens=("MaintenanceOperationTerminalReceipt",),
        ),
        HazardSpec(
            failure_id="H-A2-005-concrete-model-becomes-product-contract",
            protected_error_class="maintenance_model_specific_contract",
            description="the maintenance plan or product data requires a named model slug",
            protected_harm="local deployment substitution changes product semantics",
            case_id="maintenance_run_started",
            broken_decision="named_model_plan_current",
            broken_writes=("maintenance_operation.plan_revision",),
            broken_tokens=("MaintenancePlanCurrent",),
        ),
        HazardSpec(
            failure_id="H-A2-006-orchestrator-writes-product-or-release-state",
            protected_error_class="maintenance_orchestrator_authority_escape",
            description="routine maintenance writes a product field or final release gate",
            protected_harm="a background AI becomes a second product or release authority",
            case_id="orchestrator_attempts_product_or_final_gate_write",
            broken_decision="canonical_state_written",
            broken_writes=("matter.lifecycle_axes",),
            broken_tokens=("LifecycleState",),
        ),
        HazardSpec(
            failure_id="H-A2-007-ai-feedback-left-pending-after-completion",
            protected_error_class="ai_feedback_terminal_omission",
            description=(
                "accepted A3 feedback remains silently pending while A2 reports "
                "the maintenance run complete"
            ),
            protected_harm=(
                "user observations disappear from original-owner processing and "
                "cannot be distinguished from processed or rejected feedback"
            ),
            case_id="pending_ai_user_observation_consumed",
            broken_decision="maintenance_current_with_feedback_pending",
            broken_writes=(
                "maintenance_operation.child_result_join_status",
                "maintenance_operation.completion_status",
            ),
            broken_side_effects=("maintenance_operation_receipt_write",),
            broken_tokens=("MaintenanceOperationTerminalReceipt",),
        ),
    ),
    risk_classes=(
        "authorization",
        "privacy",
        "ownership",
        "liveness",
        "resource",
        "capability_routing",
        "deployment_substitution",
        "side_effect",
    ),
    template_no_match_reason=(
        "No template owns the exact strongest-profile maintenance plan, bounded "
        "A0/A1 delegation, typed child join, and terminal maintenance boundary."
    ),
    blindspots=(
        "concrete Codex orchestration quality requires private canaries",
        "desktop scheduling and crash recovery require installed-runtime evidence",
        "original C1-C12 semantic acceptance still requires each owner's native evidence",
    ),
    claim_boundary=(
        "This model establishes one model-agnostic A2 maintenance orchestrator, "
        "bounded typed delegation, validated child joins, finite retry, visible "
        "gaps/no-delta, and terminal original-owner dispositions for pending A3 "
        "feedback, with no direct product write or final release authority. "
        "It does not prove concrete model availability, child-task quality, "
        "scheduled installation, or end-to-end private usefulness."
    ),
)


A3 = FiniteModelSpec(
    model_id="A3_matters_ai_gateway_operation",
    title="A3 Bounded AI Information Map and Feedback Gateway Operation",
    modeled_boundary=(
        "serve one authorized bounded model-map, situation-context, or history "
        "query from existing M0/C1-C12 projections, or append one typed user "
        "observation, correction request, prediction-feedback request, or model-"
        "miss clue for its existing owner; emit an idempotent gateway receipt "
        "without raw-store access, full-conversation retention, Guard vendoring "
        "or fallback, canonical product writes, or maintenance-completion authority"
    ),
    state_fields=(
        "ai_gateway.contract_revision",
        "ai_gateway.request_fingerprint",
        "ai_gateway.query_receipt",
        "ai_gateway.feedback_receipt",
        "ai_gateway.owner_dispatch_disposition",
        "ai_gateway.researchguard_status",
        "ai_gateway.completion_status",
    ),
    owned_write_fields=(
        "ai_gateway.contract_revision",
        "ai_gateway.request_fingerprint",
        "ai_gateway.query_receipt",
        "ai_gateway.feedback_receipt",
        "ai_gateway.owner_dispatch_disposition",
        "ai_gateway.researchguard_status",
        "ai_gateway.completion_status",
    ),
    side_effect_classes=(
        "ai_gateway_query_receipt_write",
        "ai_gateway_feedback_receipt_write",
        "existing_owner_dispatch_request",
    ),
    completion_evidence=(
        "AIModelMapCurrent",
        "SituationContextCurrent",
        "BoundedHistoryCurrent",
        "AIFeedbackRecorded",
        "ExistingOwnerDispatchPending",
        "ResearchDependencyGap",
        "AIGatewayRequestRejected",
        "AIGatewayTerminalReceipt",
        "OwnerWriteRejected",
    ),
    rules=(
        CaseRule(
            case_id="bounded_model_map_requested",
            decision="model_map_current",
            label="model_map_current",
            writes=(
                "ai_gateway.contract_revision",
                "ai_gateway.request_fingerprint",
                "ai_gateway.query_receipt",
                "ai_gateway.completion_status",
            ),
            side_effects=("ai_gateway_query_receipt_write",),
            emitted_tokens=("AIModelMapCurrent", "AIGatewayTerminalReceipt"),
            reason=(
                "the gateway returns functional owner contracts and relations, "
                "not raw tables or a new canonical write path"
            ),
        ),
        CaseRule(
            case_id="bounded_situation_context_requested",
            decision="situation_context_current",
            label="situation_context_current",
            writes=(
                "ai_gateway.contract_revision",
                "ai_gateway.request_fingerprint",
                "ai_gateway.query_receipt",
                "ai_gateway.researchguard_status",
                "ai_gateway.completion_status",
            ),
            side_effects=("ai_gateway_query_receipt_write",),
            emitted_tokens=("SituationContextCurrent", "AIGatewayTerminalReceipt"),
            reason=(
                "the packet is revision-bound, privacy-minimized, modality-aware, "
                "and assembled only from existing bounded owner projections"
            ),
        ),
        CaseRule(
            case_id="bounded_history_requested",
            decision="bounded_history_current",
            label="bounded_history_current",
            writes=(
                "ai_gateway.request_fingerprint",
                "ai_gateway.query_receipt",
                "ai_gateway.completion_status",
            ),
            side_effects=("ai_gateway_query_receipt_write",),
            emitted_tokens=("BoundedHistoryCurrent", "AIGatewayTerminalReceipt"),
            reason=(
                "history is bounded by declared owners, limit, authorization, and "
                "opaque continuation rather than an unbounded private-store export"
            ),
        ),
        CaseRule(
            case_id="user_observation_submitted",
            decision="user_observation_recorded_pending_owner",
            label="user_observation_recorded_pending_owner",
            writes=(
                "ai_gateway.request_fingerprint",
                "ai_gateway.feedback_receipt",
                "ai_gateway.owner_dispatch_disposition",
                "ai_gateway.completion_status",
            ),
            side_effects=(
                "ai_gateway_feedback_receipt_write",
                "existing_owner_dispatch_request",
            ),
            emitted_tokens=(
                "AIFeedbackRecorded",
                "ExistingOwnerDispatchPending",
                "AIGatewayTerminalReceipt",
            ),
            reason=(
                "a minimized reported observation remains candidate evidence until "
                "its original owner validates it; the full conversation is not stored"
            ),
        ),
        CaseRule(
            case_id="correction_prediction_feedback_or_model_miss_submitted",
            decision="typed_feedback_delegated_to_existing_owner",
            label="typed_feedback_delegated_to_existing_owner",
            writes=(
                "ai_gateway.request_fingerprint",
                "ai_gateway.feedback_receipt",
                "ai_gateway.owner_dispatch_disposition",
                "ai_gateway.completion_status",
            ),
            side_effects=(
                "ai_gateway_feedback_receipt_write",
                "existing_owner_dispatch_request",
            ),
            emitted_tokens=(
                "AIFeedbackRecorded",
                "ExistingOwnerDispatchPending",
                "AIGatewayTerminalReceipt",
            ),
            reason=(
                "explicit correction remains C10-owned, prediction feedback C11-owned, "
                "and model misses development-owned; A3 records and routes only"
            ),
        ),
        CaseRule(
            case_id="researchguard_unavailable_for_mixed_context",
            decision="core_context_current_research_gap_visible",
            label="core_context_current_research_gap_visible",
            writes=(
                "ai_gateway.request_fingerprint",
                "ai_gateway.query_receipt",
                "ai_gateway.researchguard_status",
                "ai_gateway.completion_status",
            ),
            side_effects=("ai_gateway_query_receipt_write",),
            emitted_tokens=(
                "SituationContextCurrent",
                "ResearchDependencyGap",
                "AIGatewayTerminalReceipt",
            ),
            reason=(
                "ordinary Matter context remains readable while research-dependent "
                "content and completeness claims stay visibly unavailable"
            ),
        ),
        CaseRule(
            case_id="unauthorized_unbounded_or_unsupported_request",
            decision="ai_gateway_request_rejected",
            label="ai_gateway_request_rejected",
            writes=(
                "ai_gateway.request_fingerprint",
                "ai_gateway.query_receipt",
                "ai_gateway.completion_status",
            ),
            side_effects=("ai_gateway_query_receipt_write",),
            emitted_tokens=("AIGatewayRequestRejected", "AIGatewayTerminalReceipt"),
            reason=(
                "the gateway fails closed on scope escape, raw-store access, "
                "unbounded history, incompatible contracts, or unsupported writes"
            ),
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-A3-001-gateway-writes-canonical-product-state",
            protected_error_class="ai_gateway_product_authority_escape",
            description="the gateway writes a Matter, event, lifecycle, or projection field",
            protected_harm="A3 becomes an unmodeled C13 truth owner",
            case_id="correction_prediction_feedback_or_model_miss_submitted",
            broken_decision="canonical_state_written",
            broken_writes=("matter.lifecycle_axes",),
            broken_side_effects=("ai_gateway_feedback_receipt_write",),
            broken_tokens=("LifecycleState",),
        ),
        HazardSpec(
            failure_id="H-A3-002-unbounded-private-history-export",
            protected_error_class="ai_gateway_privacy_scope_escape",
            description="a history request exports raw private storage without a bound",
            protected_harm="private paths and unrelated personal history leave their owner boundary",
            case_id="bounded_history_requested",
            broken_decision="raw_private_store_exported",
            broken_writes=("ai_gateway.raw_private_export",),
            broken_side_effects=("ai_gateway_query_receipt_write",),
            broken_tokens=("BoundedHistoryCurrent",),
        ),
        HazardSpec(
            failure_id="H-A3-003-full-conversation-retained",
            protected_error_class="ai_gateway_overcollection",
            description="the feedback receipt stores the complete Codex conversation by default",
            protected_harm="unnecessary private conversation content becomes durable product state",
            case_id="user_observation_submitted",
            broken_decision="full_conversation_recorded",
            broken_writes=("ai_gateway.full_conversation",),
            broken_side_effects=("ai_gateway_feedback_receipt_write",),
            broken_tokens=("AIFeedbackRecorded",),
        ),
        HazardSpec(
            failure_id="H-A3-004-feedback-silently-dropped",
            protected_error_class="ai_gateway_feedback_loss",
            description="an accepted observation has no durable owner disposition",
            protected_harm="the AI appears to remember a clue that later maintenance cannot find",
            case_id="user_observation_submitted",
            broken_decision="feedback_accepted_without_dispatch",
            broken_writes=(
                "ai_gateway.feedback_receipt",
                "ai_gateway.completion_status",
            ),
            broken_side_effects=("ai_gateway_feedback_receipt_write",),
            broken_tokens=("AIGatewayTerminalReceipt",),
        ),
        HazardSpec(
            failure_id="H-A3-005-legacy-guard-fallback",
            protected_error_class="ai_gateway_guard_authority_split",
            description="missing ResearchGuard is silently replaced by a bundled legacy Guard",
            protected_harm="Matters distributes or trusts an unvalidated second research authority",
            case_id="researchguard_unavailable_for_mixed_context",
            broken_decision="legacy_guard_fallback_current",
            broken_writes=("ai_gateway.researchguard_status",),
            broken_tokens=("SituationContextCurrent",),
        ),
        HazardSpec(
            failure_id="H-A3-006-gateway-completes-maintenance",
            protected_error_class="ai_gateway_maintenance_authority_escape",
            description="A3 declares A2 maintenance complete from a submitted clue",
            protected_harm="unprocessed owner work is hidden behind a gateway receipt",
            case_id="correction_prediction_feedback_or_model_miss_submitted",
            broken_decision="maintenance_current",
            broken_writes=("maintenance_operation.completion_status",),
            broken_tokens=("MaintenanceOperationTerminalReceipt",),
        ),
    ),
    risk_classes=(
        "authorization",
        "privacy",
        "ownership",
        "freshness",
        "integration",
        "side_effect",
        "capability_routing",
    ),
    template_no_match_reason=(
        "No template owns the exact bounded AI information-map, typed feedback "
        "inbox, external ResearchGuard gap, and zero-product-write boundary."
    ),
    blindspots=(
        "answer usefulness and future AI tool-selection quality require runtime evaluation",
        "external ResearchGuard installation and substantive research truth remain separate evidence",
        "A2 consumption of pending feedback requires maintenance integration evidence",
    ),
    claim_boundary=(
        "This model establishes one bounded A3 query/feedback gateway with typed "
        "receipts, visible ResearchGuard gaps, privacy minimization, existing-owner "
        "dispatch, zero canonical product writes, and zero maintenance-completion "
        "authority. It does not prove service implementation, arbitrary future AI "
        "answer correctness, ResearchGuard currentness, feedback consumption, "
        "private runtime usefulness, or final release readiness."
    ),
)


AGENT_OPERATION_MODELS = {
    A0.model_id: A0,
    A1.model_id: A1,
    A2.model_id: A2,
    A3.model_id: A3,
}
