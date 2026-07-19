"""C11 AI, ResearchOperation, Semantic Depth, and Prediction boundary model."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C11_guard_artifact_prediction",
    title="C11 AI, Research & Prediction Boundary",
    modeled_boundary=(
        "versioned scope-bound AI/ResearchOperation work packages, terminal "
        "results, ResearchGuard currentness, semantic depth, typed bilingual "
        "findings, input accounting, durable automatic original-owner dispatch, "
        "representative-visual recommendation, receipt freshness, and forecast/"
        "current-state separation"
    ),
    state_fields=(
        "agent.work_package_v2_registry",
        "agent.result_registry",
        "analysis.finding_history",
        "analysis.input_disposition_registry",
        "analysis.dispatch_outbox",
        "analysis.visual_recommendation_registry",
        "research.provider_status",
        "analysis.depth_registry",
        "forecast_registry",
    ),
    owned_write_fields=(
        "agent.work_package_v2_registry",
        "agent.result_registry",
        "analysis.finding_history",
        "analysis.input_disposition_registry",
        "analysis.dispatch_outbox",
        "analysis.visual_recommendation_registry",
        "research.provider_status",
        "analysis.depth_registry",
        "forecast_registry",
    ),
    side_effect_classes=(
        "agent_work_package_write",
        "finding_history_write",
        "input_disposition_write",
        "dispatch_outbox_write",
        "visual_recommendation_write",
        "depth_assessment_write",
    ),
    completion_evidence=(
        "AnalysisWorkPackageV2",
        "AgentOperationResult",
        "BilingualFinding",
        "InputDisposition",
        "OriginalOwnerDispatch",
        "OwnerTerminalResult",
        "NoFinding",
        "VisualRecommendation",
        "Finding",
        "Proposal",
        "Gap",
        "DepthAssessment",
        "ResearchGuardPending",
        "Forecast",
        "ArtifactRejected",
    ),
    rules=(
        CaseRule(
            case_id="extracted_anchors_queued",
            decision="bounded_analysis_work_package_queued",
            label="bounded_analysis_work_package_queued",
            writes=("agent.work_package_v2_registry",),
            side_effects=("agent_work_package_write",),
            emitted_tokens=("AnalysisWorkPackageV2",),
            reason=(
                "current tracked evidence anchors are chunked into a bounded, "
                "private, evidence-whitelisted WorkPackageV2 with prompt, schema, "
                "policy, owner, locale, model, skill, and input-dependency identities"
            ),
        ),
        CaseRule(
            case_id="valid_bilingual_understanding_result",
            decision="typed_findings_validated_and_dispatched",
            label="typed_findings_validated_and_dispatched",
            writes=(
                "agent.result_registry",
                "analysis.finding_history",
                "analysis.input_disposition_registry",
                "analysis.dispatch_outbox",
            ),
            side_effects=(
                "finding_history_write",
                "input_disposition_write",
                "dispatch_outbox_write",
            ),
            emitted_tokens=(
                "AgentOperationResult",
                "BilingualFinding",
                "InputDisposition",
                "OriginalOwnerDispatch",
                "Finding",
            ),
            reason=(
                "one terminal result uses only package evidence refs and persists "
                "non-empty en and zh-CN values against the same semantic revision, "
                "accounts every input, validates the typed owner schema, and "
                "automatically appends one idempotent original-owner dispatch"
            ),
        ),
        CaseRule(
            case_id="typed_finding_auto_dispatched",
            decision="original_owner_dispatch_appended",
            label="original_owner_dispatch_appended",
            writes=(
                "analysis.finding_history",
                "analysis.dispatch_outbox",
            ),
            side_effects=("finding_history_write", "dispatch_outbox_write"),
            emitted_tokens=("OriginalOwnerDispatch",),
            reason=(
                "a current typed finding is automatically delegated exactly once "
                "to its declared C1/C4-C9/C12 owner without a confirmation token"
            ),
        ),
        CaseRule(
            case_id="no_finding_or_policy_rejected",
            decision="terminal_nonfinding_recorded",
            label="terminal_nonfinding_recorded",
            writes=(
                "analysis.finding_history",
                "analysis.input_disposition_registry",
            ),
            side_effects=("finding_history_write", "input_disposition_write"),
            emitted_tokens=("NoFinding", "InputDisposition"),
            reason=(
                "no-finding and policy-rejected outcomes are durable terminal "
                "dispositions with complete input accounting"
            ),
        ),
        CaseRule(
            case_id="analysis_operation_failed_or_blocked",
            decision="analysis_gap_visible",
            label="analysis_gap_visible",
            writes=("agent.result_registry",),
            side_effects=("finding_history_write",),
            emitted_tokens=("AgentOperationResult", "Gap"),
            reason=(
                "failed or blocked execution is terminal and visible but creates "
                "no understanding candidate and no canonical state"
            ),
        ),
        CaseRule(
            case_id="current_ai_finding",
            decision="current_finding_auto_dispatched",
            label="current_finding_auto_dispatched",
            writes=(
                "agent.work_package_v2_registry",
                "agent.result_registry",
                "analysis.finding_history",
                "analysis.dispatch_outbox",
            ),
            side_effects=(
                "agent_work_package_write",
                "finding_history_write",
                "dispatch_outbox_write",
            ),
            emitted_tokens=(
                "AnalysisWorkPackageV2",
                "AgentOperationResult",
                "Finding",
                "OriginalOwnerDispatch",
            ),
            reason="current scoped AI output is typed, recorded, and automatically owner-routed",
        ),
        CaseRule(
            case_id="current_researchguard_result",
            decision="research_advisory_registered",
            label="research_advisory_registered",
            writes=(
                "agent.work_package_v2_registry",
                "agent.result_registry",
                "research.provider_status",
            ),
            side_effects=("agent_work_package_write", "finding_history_write"),
            emitted_tokens=("AnalysisWorkPackageV2", "AgentOperationResult", "Finding", "Proposal", "Gap"),
            reason="one frozen compatible ResearchGuard identity returns schema-valid anchored advisory output",
        ),
        CaseRule(
            case_id="researchguard_not_current",
            decision="researchguard_pending_integration",
            label="researchguard_pending_integration",
            writes=("agent.work_package_v2_registry", "agent.result_registry", "research.provider_status"),
            side_effects=("agent_work_package_write", "finding_history_write"),
            emitted_tokens=("AnalysisWorkPackageV2", "AgentOperationResult", "ResearchGuardPending", "Gap"),
            reason="missing package, command, top-level skill, manifest, compatibility, or currentness blocks real research execution",
        ),
        CaseRule(
            case_id="legacy_parallel_guard_binding",
            decision="legacy_binding_rejected",
            label="legacy_binding_rejected",
            writes=("agent.result_registry", "research.provider_status"),
            side_effects=("finding_history_write",),
            emitted_tokens=("ArtifactRejected", "Gap"),
            reason="separate SourceGuard, TraceGuard, or LogicGuard paths are stale/source-only migration evidence",
        ),
        CaseRule(
            case_id="current_scope_triage",
            decision="scope_triage_auto_dispatched",
            label="scope_triage_auto_dispatched",
            writes=(
                "agent.work_package_v2_registry",
                "agent.result_registry",
                "analysis.finding_history",
                "analysis.dispatch_outbox",
            ),
            side_effects=(
                "agent_work_package_write",
                "finding_history_write",
                "dispatch_outbox_write",
            ),
            emitted_tokens=(
                "AnalysisWorkPackageV2",
                "AgentOperationResult",
                "OriginalOwnerDispatch",
            ),
            reason="triage emits a reversible C1 disposition with reason, confidence, policy, and freshness identity",
        ),
        CaseRule(
            case_id="depth_sufficient_current",
            decision="depth_assessment_current",
            label="depth_assessment_current",
            writes=("analysis.depth_registry",),
            side_effects=("depth_assessment_write",),
            emitted_tokens=("DepthAssessment",),
            reason="required source classes, anchors, contradiction checks, owner decisions, localization, visual, and projection state satisfy current depth policy",
        ),
        CaseRule(
            case_id="depth_partial_or_stale",
            decision="depth_work_required",
            label="depth_work_required",
            writes=("analysis.depth_registry",),
            side_effects=("depth_assessment_write",),
            emitted_tokens=("DepthAssessment", "Gap", "Proposal"),
            reason="missing, blocked, or stale obligations remain visible and schedule bounded work",
        ),
        CaseRule(
            case_id="visual_candidates_ranked",
            decision="visual_recommendation_registered",
            label="visual_recommendation_registered",
            writes=("analysis.visual_recommendation_registry",),
            side_effects=("visual_recommendation_write",),
            emitted_tokens=("VisualRecommendation",),
            reason=(
                "allowlisted current C2/C3/C6 candidates receive a deterministic "
                "recommendation; C12 remains the display-decision owner"
            ),
        ),
        CaseRule(
            case_id="stale_operation_result",
            decision="stale_artifact_rejected",
            label="stale_artifact_rejected",
            writes=("agent.result_registry",),
            side_effects=("finding_history_write",),
            emitted_tokens=("ArtifactRejected", "Gap"),
            reason="source, policy, model, provider, tool, schema, or active skill identity changed",
        ),
        CaseRule(
            case_id="scope_escape_attempt",
            decision="scope_incompatible",
            label="scope_incompatible",
            writes=("agent.result_registry",),
            side_effects=("finding_history_write",),
            emitted_tokens=("AgentOperationResult", "ArtifactRejected", "Gap"),
            reason="adjacent-source read, undeclared tool, or external action is rejected",
        ),
        CaseRule(
            case_id="forecast_delay",
            decision="forecast_registered_only",
            label="forecast_registered_only",
            writes=("forecast_registry",),
            side_effects=("finding_history_write",),
            emitted_tokens=("Forecast",),
            reason="future forecast remains separate from current lifecycle state",
        ),
        CaseRule(
            case_id="research_direct_canonical_write",
            decision="research_write_rejected",
            label="research_write_rejected",
            emitted_tokens=("OwnerWriteRejected",),
            reason="AI or ResearchGuard output cannot write a canonical field",
        ),
        CaseRule(
            case_id="skipped_or_progress_receipt",
            decision="nonterminal_receipt_rejected",
            label="nonterminal_receipt_rejected",
            writes=("agent.result_registry",),
            side_effects=("finding_history_write",),
            emitted_tokens=("ArtifactRejected", "Gap"),
            reason="skipped, not-run, or progress-only evidence cannot be promoted",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-C11-001-research-writes-canonical-state",
            protected_error_class="research_authority_escape",
            description="an AI or ResearchGuard finding directly changes canonical state",
            protected_harm="analysis bypasses evidence validation and the canonical owner",
            case_id="research_direct_canonical_write",
            broken_decision="canonical_state_written",
            broken_writes=("matter.lifecycle_axes",),
            broken_tokens=("LifecycleState",),
        ),
        HazardSpec(
            failure_id="H-C11-002-stale-result-promoted",
            protected_error_class="stale_research_evidence_reuse",
            description="a stale operation result supports a current decision",
            protected_harm="analysis over obsolete source, policy, tool, or skill identity looks current",
            case_id="stale_operation_result",
            broken_decision="advisory_finding_registered",
            broken_writes=("agent.result_registry",),
            broken_side_effects=("finding_history_write",),
            broken_tokens=("Finding", "Proposal"),
        ),
        HazardSpec(
            failure_id="H-C11-003-forecast-changes-current-state",
            protected_error_class="forecast_fact_conflation",
            description="a forecasted delay marks the Matter currently blocked",
            protected_harm="predicted future conditions are presented as present facts",
            case_id="forecast_delay",
            broken_decision="current_blocked",
            broken_writes=("matter.blocking_axis",),
            broken_tokens=("FullBlock",),
        ),
        HazardSpec(
            failure_id="H-C11-004-progress-receipt-promoted",
            protected_error_class="nonterminal_evidence_promotion",
            description="skipped or progress-only research evidence is promoted",
            protected_harm="absence of execution is misrepresented as analysis proof",
            case_id="skipped_or_progress_receipt",
            broken_decision="advisory_finding_registered",
            broken_writes=("agent.result_registry",),
            broken_side_effects=("finding_history_write",),
            broken_tokens=("Finding", "Proposal"),
        ),
        HazardSpec(
            failure_id="H-C11-005-legacy-three-guard-fallback",
            protected_error_class="alternate_research_success_path",
            description="ResearchGuard absence silently launches separate legacy Guards",
            protected_harm="mixed suite identity and incompatible results appear as current research",
            case_id="legacy_parallel_guard_binding",
            broken_decision="research_advisory_registered",
            broken_writes=("agent.result_registry", "research.provider_status"),
            broken_side_effects=("finding_history_write",),
            broken_tokens=("Finding", "Proposal"),
        ),
        HazardSpec(
            failure_id="H-C11-006-researchguard-pending-claimed-current",
            protected_error_class="external_integration_false_green",
            description="incomplete ResearchGuard installation is reported current",
            protected_harm="the final release claims research analysis that cannot run",
            case_id="researchguard_not_current",
            broken_decision="research_advisory_registered",
            broken_writes=("agent.result_registry", "research.provider_status"),
            broken_side_effects=("finding_history_write",),
            broken_tokens=("Finding", "Proposal"),
        ),
        HazardSpec(
            failure_id="H-C11-007-scope-escape-read",
            protected_error_class="agent_scope_escape",
            description="an operation reads adjacent sources or invokes undeclared tools",
            protected_harm="private data or side effects escape the authorized work package",
            case_id="scope_escape_attempt",
            broken_decision="advisory_finding_registered",
            broken_writes=("agent.result_registry",),
            broken_side_effects=("finding_history_write",),
            broken_tokens=("Finding",),
        ),
        HazardSpec(
            failure_id="H-C11-008-shallow-model-claimed-sufficient",
            protected_error_class="semantic_depth_overclaim",
            description="missing or stale depth obligations are reported sufficient",
            protected_harm="the UI hides unmodeled sources, gaps, contradictions, or incomplete owner stages",
            case_id="depth_partial_or_stale",
            broken_decision="depth_assessment_current",
            broken_writes=("analysis.depth_registry",),
            broken_side_effects=("depth_assessment_write",),
            broken_tokens=("DepthAssessment",),
        ),
        HazardSpec(
            failure_id="H-C11-009-anchor-dropped-before-ai",
            protected_error_class="semantic_analysis_input_loss",
            description=(
                "tracked extracted anchors reach persistence but no bounded AI "
                "work package or visible terminal disposition"
            ),
            protected_harm=(
                "the inventory appears processed although its content never "
                "entered the understanding path"
            ),
            case_id="extracted_anchors_queued",
            broken_decision="anchors_silently_dropped",
            broken_writes=("agent.work_package_v2_registry",),
            broken_tokens=("AnalysisWorkPackageV2",),
        ),
        HazardSpec(
            failure_id="H-C11-010-invalid-bilingual-result-admitted",
            protected_error_class="understanding_semantic_revision_mismatch",
            description=(
                "a missing language, mismatched revision, unsupported finding "
                "type, or non-whitelisted evidence ref becomes owner-routable"
            ),
            protected_harm=(
                "an invented or semantically divergent AI claim reaches an owner"
            ),
            case_id="valid_bilingual_understanding_result",
            broken_decision="typed_findings_validated_and_dispatched",
            broken_writes=("analysis.finding_history", "analysis.dispatch_outbox"),
            broken_side_effects=("finding_history_write", "dispatch_outbox_write"),
            broken_tokens=("BilingualFinding", "OriginalOwnerDispatch"),
        ),
        HazardSpec(
            failure_id="H-C11-011-auto-dispatch-writes-canonical-directly",
            protected_error_class="understanding_original_owner_bypass",
            description=(
                "automatic dispatch directly creates or changes a person, "
                "event, Matter, open loop, or lifecycle field"
            ),
            protected_harm=(
                "the dispatcher is mistaken for permission to bypass the canonical owner"
            ),
            case_id="typed_finding_auto_dispatched",
            broken_decision="canonical_state_written",
            broken_writes=("matter.lifecycle_axes",),
            broken_tokens=("LifecycleState",),
        ),
        HazardSpec(
            failure_id="H-C11-012-input-disposition-accounting-bypassed",
            protected_error_class="analysis_input_accounting_gap",
            description=(
                "a no-finding result reaches terminal without accounting every "
                "declared input"
            ),
            protected_harm="registered content silently disappears from semantic modeling",
            case_id="no_finding_or_policy_rejected",
            broken_decision="terminal_nonfinding_recorded",
            broken_writes=("analysis.finding_history",),
            broken_side_effects=("finding_history_write",),
            broken_tokens=("NoFinding",),
        ),
        HazardSpec(
            failure_id="H-C11-013-visual-recommendation-writes-c12",
            protected_error_class="visual_projection_owner_bypass",
            description="C11 writes the current card visual instead of recommending one",
            protected_harm="AI ranking becomes an untracked display authority",
            case_id="visual_candidates_ranked",
            broken_decision="card_visual_decision_written",
            broken_writes=("matter.card_visual_decision",),
            broken_tokens=("CardVisualDecision",),
        ),
    ),
    risk_classes=(
        "evidence",
        "ownership",
        "authorization",
        "freshness",
        "integration",
        "state_transition",
        "side_effect",
    ),
    template_no_match_reason=(
        "No existing template owns the exact Matters AI/ResearchOperation, "
        "ResearchGuard currentness, semantic-depth, and forecast boundary."
    ),
    blindspots=(
        "substantive ResearchGuard correctness remains with its frozen native suite",
        "AI relevance and depth quality require synthetic regressions plus private canaries and optional correction",
        "external provider privacy and model behavior require runtime disclosure evidence",
    ),
    claim_boundary=(
        "This model establishes the extracted-anchor to bounded work-package, "
        "terminal bilingual typed findings, full input accounting, automatic "
        "idempotent original-owner dispatch, advisory-only research output, "
        "ResearchGuard gate, legacy-fallback rejection, freshness, semantic-depth, "
        "scope, visual recommendations, and forecast transitions. It does not prove factual truth, "
        "ResearchGuard installation, model quality, or private first-run usefulness."
    ),
)
