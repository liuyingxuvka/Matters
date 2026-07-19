"""Agent-operation-plane FlowGuard models for bounded AI execution."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


A0 = FiniteModelSpec(
    model_id="A0_matters_source_analysis_operation",
    title="A0 Bounded Source Analysis Operation",
    modeled_boundary=(
        "execute one WorkPackageV2 using only declared evidence, tools, prompt, "
        "schema, policy, owner, locale, model and skill identities; account every "
        "input and emit one terminal receipt without product-runtime writes"
    ),
    state_fields=(
        "analysis_operation.execution_status",
        "analysis_operation.input_dispositions",
        "analysis_operation.raw_result_handle",
        "analysis_operation.resource_usage",
        "analysis_operation.terminal_receipt",
    ),
    owned_write_fields=(
        "analysis_operation.execution_status",
        "analysis_operation.input_dispositions",
        "analysis_operation.raw_result_handle",
        "analysis_operation.resource_usage",
        "analysis_operation.terminal_receipt",
    ),
    side_effect_classes=("analysis_operation_receipt_write",),
    completion_evidence=(
        "WorkPackageV2Accepted",
        "InputDispositionSet",
        "AnalysisOperationTerminalReceipt",
        "OperationBlocked",
    ),
    rules=(
        CaseRule(
            case_id="valid_work_package_v2",
            decision="analysis_operation_current",
            label="analysis_operation_current",
            writes=(
                "analysis_operation.execution_status",
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
    ),
    risk_classes=("authorization", "privacy", "ownership", "side_effect"),
    template_no_match_reason=(
        "No template owns the exact Matters WorkPackageV2 input-accounting and "
        "cross-plane receipt boundary."
    ),
    blindspots=(
        "model quality requires synthetic regressions and private canaries",
        "external-provider disclosure requires separate runtime evidence",
    ),
    claim_boundary=(
        "This model establishes bounded A0 WorkPackageV2 execution, complete input "
        "accounting, terminal receipts, scope rejection, and zero product writes. "
        "It does not prove model quality or provider privacy."
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


AGENT_OPERATION_MODELS = {A0.model_id: A0, A1.model_id: A1}
