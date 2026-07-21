"""C11 AI, ResearchOperation, Semantic Depth, and Prediction boundary model."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C11_guard_artifact_prediction",
    title="C11 AI, Research & Prediction Boundary",
    modeled_boundary=(
        "versioned scope-bound model-agnostic capability-routed AI/"
        "ResearchOperation work packages, terminal results, ResearchGuard "
        "currentness, semantic depth, typed bilingual "
        "findings, input accounting, durable automatic original-owner dispatch, "
        "root-only photoreal generated-Hero work, AI supplemental information, "
        "persistent advisory Situation/World Model inference with alternatives "
        "and expiry, receipt freshness, and forecast/current-state separation"
    ),
    state_fields=(
        "agent.work_package_v2_registry",
        "agent.capability_role_registry",
        "agent.result_registry",
        "analysis.finding_history",
        "analysis.input_disposition_registry",
        "analysis.dispatch_outbox",
        "analysis.hero_generation_registry",
        "analysis.narrative_registry",
        "analysis.supplemental_information_registry",
        "analysis.hierarchy_proposal_registry",
        "analysis.situation_world_model_registry",
        "analysis.situation_inference_dependency_registry",
        "analysis.world_model_feedback_registry",
        "analysis.world_model_miss_outbox",
        "analysis.current_phase_inference_registry",
        "research.provider_status",
        "analysis.depth_registry",
        "forecast_registry",
    ),
    owned_write_fields=(
        "agent.work_package_v2_registry",
        "agent.capability_role_registry",
        "agent.result_registry",
        "analysis.finding_history",
        "analysis.input_disposition_registry",
        "analysis.dispatch_outbox",
        "analysis.hero_generation_registry",
        "analysis.narrative_registry",
        "analysis.supplemental_information_registry",
        "analysis.hierarchy_proposal_registry",
        "analysis.situation_world_model_registry",
        "analysis.situation_inference_dependency_registry",
        "analysis.world_model_feedback_registry",
        "analysis.world_model_miss_outbox",
        "analysis.current_phase_inference_registry",
        "research.provider_status",
        "analysis.depth_registry",
        "forecast_registry",
    ),
    side_effect_classes=(
        "agent_work_package_write",
        "finding_history_write",
        "input_disposition_write",
        "dispatch_outbox_write",
        "hero_generation_write",
        "narrative_synthesis_write",
        "supplemental_information_write",
        "hierarchy_proposal_write",
        "depth_assessment_write",
        "world_model_write",
        "world_model_feedback_write",
        "model_miss_handoff_write",
    ),
    completion_evidence=(
        "AnalysisWorkPackageV2",
        "CapabilityRole",
        "CapabilityPending",
        "AgentOperationResult",
        "BilingualFinding",
        "InputDisposition",
        "OriginalOwnerDispatch",
        "OwnerTerminalResult",
        "NoFinding",
        "GeneratedHero",
        "HeroGenerationPending",
        "AISupplementalInformation",
        "SupplementalInformationUnavailable",
        "Finding",
        "Proposal",
        "Gap",
        "DepthAssessment",
        "ResearchGuardPending",
        "Forecast",
        "ArtifactRejected",
        "HierarchyProposal",
        "SituationWorldModel",
        "AdvisoryInference",
        "InferenceAlternative",
        "InferenceExpired",
        "PredictionSnapshot",
        "PredictionFeedback",
        "PredictionContradicted",
        "PredictionUnresolved",
        "ModelMissRequest",
        "HeroNotApplicable",
        "HumanMatterNarrative",
        "NonEmptySupplementalInformation",
        "MatterScopedSemanticDepth",
        "CurrentPhaseInference",
    ),
    rules=(
        CaseRule(
            case_id="extracted_anchors_queued",
            decision="bounded_analysis_work_package_queued",
            label="bounded_analysis_work_package_queued",
            writes=(
                "agent.work_package_v2_registry",
                "agent.capability_role_registry",
            ),
            side_effects=("agent_work_package_write",),
            emitted_tokens=("AnalysisWorkPackageV2", "CapabilityRole"),
            reason=(
                "current tracked evidence anchors are chunked into a bounded, "
                "private, evidence-whitelisted WorkPackageV2 with prompt, schema, "
                "policy, owner, locale, capability role, skill, and "
                "input-dependency identities; the named model remains private "
                "A0 execution-profile state"
            ),
        ),
        CaseRule(
            case_id="capability_role_assigned",
            decision="model_agnostic_capability_contract_current",
            label="model_agnostic_capability_contract_current",
            writes=(
                "agent.work_package_v2_registry",
                "agent.capability_role_registry",
            ),
            side_effects=("agent_work_package_write",),
            emitted_tokens=("AnalysisWorkPackageV2", "CapabilityRole"),
            reason=(
                "every AI package requests exactly one declared capability role "
                "without making Luna, Terra, or another concrete model a product field"
            ),
        ),
        CaseRule(
            case_id="capability_unavailable_or_escalating",
            decision="capability_gap_visible",
            label="capability_gap_visible",
            writes=(
                "agent.capability_role_registry",
                "agent.result_registry",
            ),
            side_effects=("finding_history_write",),
            emitted_tokens=("CapabilityPending", "Gap"),
            reason=(
                "an unavailable or underpowered mapping stays pending or escalates "
                "through A0 without fabricating a current finding"
            ),
        ),
        CaseRule(
            case_id="retired_capability_package_loaded",
            decision="retired_package_direct_migrated",
            label="retired_package_direct_migrated",
            writes=(
                "agent.work_package_v2_registry",
                "agent.capability_role_registry",
            ),
            side_effects=("agent_work_package_write",),
            emitted_tokens=("AnalysisWorkPackageV2", "CapabilityRole"),
            reason=(
                "a durable package with a retired role is hidden and replaced "
                "by exactly one current seven-role package without a compatibility runner"
            ),
        ),
        CaseRule(
            case_id="queued_source_no_longer_tracked",
            decision="analysis_package_not_runnable",
            label="analysis_package_not_runnable",
            writes=("agent.work_package_v2_registry",),
            side_effects=("agent_work_package_write",),
            emitted_tokens=("Gap",),
            reason=(
                "an inactive or current non-tracked source keeps audit history "
                "but its package leaves runnable work before any model invocation"
            ),
        ),
        CaseRule(
            case_id="named_model_or_direct_api_required",
            decision="deployment_dependency_rejected",
            label="deployment_dependency_rejected",
            writes=("agent.result_registry",),
            side_effects=("finding_history_write",),
            emitted_tokens=("ArtifactRejected", "Gap"),
            reason=(
                "C11 rejects product work that requires a named model or an "
                "application-owned provider API key"
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
            reason=(
                "required source classes, anchors, contradiction checks, owner "
                "decisions, localization, Images-gallery state, generated hero, "
                "human parent/child narrative, Matter-scoped facts/events/work/"
                "waits, people, relationships, non-empty-or-explicitly-unavailable "
                "supplemental information, and projection state satisfy current depth policy"
            ),
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
            case_id="stable_matter_identity_needs_generated_hero",
            decision="generated_hero_package_current",
            label="generated_hero_package_current",
            writes=("analysis.hero_generation_registry",),
            side_effects=("hero_generation_write",),
            emitted_tokens=("GeneratedHero",),
            reason=(
                "after C6 identity, merge, split, and hierarchy are current, one "
                "presentation-only photorealistic documentary/editorial image is "
                "generated only for each root Matter from a privacy-safe topic "
                "abstraction with natural environment and generic unidentifiable "
                "people; abstract art, illustration, 3D, collage, screenshots, "
                "literal text, logos, private identifiers, real-person likeness, "
                "and source-file fallback are rejected; "
                "C12 remains the display-publication owner"
            ),
        ),
        CaseRule(
            case_id="current_generated_hero_fails_visual_specificity",
            decision="generated_hero_quality_refresh_pending",
            label="generated_hero_quality_refresh_pending",
            writes=("analysis.hero_generation_registry",),
            side_effects=("hero_generation_write",),
            emitted_tokens=("HeroGenerationPending", "Gap"),
            reason=(
                "a browser or automated visual review found that the current "
                "root Hero could represent an unrelated Matter, defaults to a "
                "generic person at a computer, or omits the Matter-specific "
                "place, equipment, objects, or activity; the typed non-blocking "
                "quality invalidation retires the old token and prepares exactly "
                "one replacement brief without admitting source imagery"
            ),
        ),
        CaseRule(
            case_id="descendant_or_non_matter_hero_requested",
            decision="generated_hero_not_applicable",
            label="generated_hero_not_applicable",
            writes=("analysis.hero_generation_registry",),
            side_effects=("hero_generation_write",),
            emitted_tokens=("HeroNotApplicable",),
            reason=(
                "child Matters, WorkItems, Events, sources, inferred nodes, and "
                "node quick views never generate or display a separate Hero"
            ),
        ),
        CaseRule(
            case_id="hero_generation_unavailable_or_invalid",
            decision="hero_generation_pending_visible",
            label="hero_generation_pending_visible",
            writes=("analysis.hero_generation_registry",),
            side_effects=("hero_generation_write",),
            emitted_tokens=("HeroGenerationPending", "Gap"),
            reason=(
                "missing capability, policy rejection, unsafe output, or stale "
                "identity leaves a visible retryable pending/blocked state and "
                "does not promote a real source image or screenshot as the hero"
            ),
        ),
        CaseRule(
            case_id="current_ai_supplemental_information",
            decision="supplemental_information_registered_and_dispatched",
            label="supplemental_information_registered_and_dispatched",
            writes=(
                "analysis.supplemental_information_registry",
                "analysis.dispatch_outbox",
            ),
            side_effects=(
                "supplemental_information_write",
                "dispatch_outbox_write",
            ),
            emitted_tokens=(
                "AISupplementalInformation",
                "NonEmptySupplementalInformation",
                "OriginalOwnerDispatch",
            ),
            reason=(
                "one or more current usable items from evidence plus bounded "
                "external research may produce "
                "clearly labeled bilingual context, implications, preparation, "
                "and jurisdiction/time-zone normalization that remains distinct "
                "from sourced facts and is dispatched to C12 for the eighth section"
            ),
        ),
        CaseRule(
            case_id="supplemental_information_unavailable",
            decision="supplemental_information_unavailable_visible",
            label="supplemental_information_unavailable_visible",
            writes=("analysis.supplemental_information_registry",),
            side_effects=("supplemental_information_write",),
            emitted_tokens=("SupplementalInformationUnavailable", "Gap"),
            reason=(
                "when authorized context or research is unavailable or yields "
                "zero usable items, the eighth "
                "section reports a bounded unavailable state instead of fabricating "
                "background information"
            ),
        ),
        CaseRule(
            case_id="human_matter_narrative_requested",
            decision="human_bilingual_narrative_registered_and_dispatched",
            label="human_bilingual_narrative_registered_and_dispatched",
            writes=(
                "analysis.narrative_registry",
                "analysis.dispatch_outbox",
            ),
            side_effects=(
                "narrative_synthesis_write",
                "dispatch_outbox_write",
            ),
            emitted_tokens=(
                "HumanMatterNarrative",
                "MatterScopedSemanticDepth",
                "OriginalOwnerDispatch",
            ),
            reason=(
                "the current Matter and its current child projections produce "
                "bilingual human-facing language that states what the Matter is, "
                "what happened, where it stands, and what is next; it omits "
                "evidence-counting, model-owner, coverage, and review vocabulary, "
                "and dispatches only to the original C12 narrative owner"
            ),
        ),
        CaseRule(
            case_id="hierarchy_trace_advisory_current",
            decision="hierarchy_proposal_registered_and_dispatched",
            label="hierarchy_proposal_registered_and_dispatched",
            writes=(
                "analysis.hierarchy_proposal_registry",
                "analysis.dispatch_outbox",
            ),
            side_effects=("hierarchy_proposal_write", "dispatch_outbox_write"),
            emitted_tokens=("HierarchyProposal", "OriginalOwnerDispatch"),
            reason=(
                "current evidence-backed ResearchGuard temporal and structural "
                "analysis may propose root/child/WorkItem distinctions, edge roles, "
                "or split/merge/reparent work, but dispatches the proposal to C6 "
                "without changing canonical containment"
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
            case_id="weak_forecast_entrypoint_requested",
            decision="weak_forecast_entrypoint_rejected",
            label="weak_forecast_entrypoint_rejected",
            writes=(),
            side_effects=(),
            emitted_tokens=("ArtifactRejected",),
            reason=(
                "the lightweight Forecast and GuardBridge.register_forecast "
                "paths are retired; only the complete PersistentAdvisoryWorldModel "
                "prediction contract may write a frozen advisory forecast"
            ),
        ),
        CaseRule(
            case_id="future_prediction_contract_current",
            decision="frozen_testable_prediction_registered",
            label="frozen_testable_prediction_registered",
            writes=(
                "analysis.situation_world_model_registry",
                "analysis.situation_inference_dependency_registry",
                "forecast_registry",
            ),
            side_effects=("world_model_write", "finding_history_write"),
            emitted_tokens=("Forecast", "PredictionSnapshot"),
            reason=(
                "a future prediction is frozen before observation with evidence, "
                "verification and contradiction conditions, uncertainty, "
                "weakening conditions, observation horizon, expiry, and an "
                "advisory-only disposition; it never writes C5-C9 state"
            ),
        ),
        CaseRule(
            case_id="later_observation_confirms_prediction",
            decision="prediction_feedback_confirmed",
            label="prediction_feedback_confirmed",
            writes=("analysis.world_model_feedback_registry",),
            side_effects=("world_model_feedback_write",),
            emitted_tokens=("PredictionFeedback",),
            reason=(
                "a strictly later licensed observation appends empirical "
                "confirmation while the original owner independently records "
                "any newly licensed fact"
            ),
        ),
        CaseRule(
            case_id="later_observation_contradicts_prediction",
            decision="prediction_feedback_contradicted_model_miss_queued",
            label="prediction_feedback_contradicted_model_miss_queued",
            writes=(
                "analysis.world_model_feedback_registry",
                "analysis.world_model_miss_outbox",
            ),
            side_effects=("world_model_feedback_write", "model_miss_handoff_write"),
            emitted_tokens=(
                "PredictionFeedback",
                "PredictionContradicted",
                "ModelMissRequest",
            ),
            reason=(
                "the frozen prediction and later contradiction are both preserved; "
                "one idempotent FlowGuard Model-Miss review reopens the original "
                "evidence sufficiency, grouping, temporal interpretation, and "
                "model boundary without rewriting runtime history"
            ),
        ),
        CaseRule(
            case_id="prediction_horizon_passed_without_decisive_observation",
            decision="prediction_feedback_unresolved",
            label="prediction_feedback_unresolved",
            writes=("analysis.world_model_feedback_registry",),
            side_effects=("world_model_feedback_write",),
            emitted_tokens=("PredictionFeedback", "PredictionUnresolved"),
            reason=(
                "an elapsed prediction without decisive licensed evidence becomes "
                "expired or unresolved and is not counted as predictive success"
            ),
        ),
        CaseRule(
            case_id="current_situation_graph_supports_advisory_inference",
            decision="situation_world_model_inference_current",
            label="situation_world_model_inference_current",
            writes=(
                "analysis.situation_world_model_registry",
                "analysis.situation_inference_dependency_registry",
            ),
            side_effects=("world_model_write", "finding_history_write"),
            emitted_tokens=(
                "SituationWorldModel",
                "AdvisoryInference",
                "InferenceAlternative",
            ),
            reason=(
                "C11 persists an advisory read model over the current C2-C9 and "
                "C11 dependency revisions; a likely occurred trip, application "
                "step, payment, or project milestone records confidence, "
                "alternatives, coverage, evidence basis, expiry, and ai_inferred "
                "certainty without writing canonical fact, lifecycle, outcome, "
                "or primary containment"
            ),
        ),
        CaseRule(
            case_id="situation_world_model_dependency_changed_or_expired",
            decision="situation_world_model_inference_expired",
            label="situation_world_model_inference_expired",
            writes=(
                "analysis.situation_world_model_registry",
                "analysis.situation_inference_dependency_registry",
            ),
            side_effects=("world_model_write",),
            emitted_tokens=("InferenceExpired", "Gap"),
            reason=(
                "source, graph, lifecycle, policy, or time-horizon change makes "
                "the inference visibly stale until recomputed from current owners"
            ),
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
        CaseRule(
            case_id="completed_prerequisite_and_future_required_obligation",
            decision="current_phase_inference_proposed",
            label="current_phase_inference_proposed",
            writes=(
                "analysis.situation_world_model_registry",
                "analysis.situation_inference_dependency_registry",
                "analysis.current_phase_inference_registry",
            ),
            side_effects=("world_model_write",),
            emitted_tokens=("AdvisoryInference", "CurrentPhaseInference"),
            reason=(
                "C11 may propose the most likely current workflow phase only "
                "with a completed prerequisite, still-required next obligation, "
                "bounded active window, coverage, alternatives, expiry, and "
                "contradiction triggers; C7 remains the lifecycle owner"
            ),
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-C11-030-current-phase-predicts-future-success",
            protected_error_class="current_phase_future_outcome_conflation",
            description=(
                "a current preparation-phase inference is rewritten as a "
                "prediction that submission or another future outcome succeeded"
            ),
            protected_harm="advisory phase reasoning becomes a false future fact",
            case_id="completed_prerequisite_and_future_required_obligation",
            broken_decision="future_outcome_completed",
            broken_writes=("analysis.situation_world_model_registry",),
            broken_side_effects=("world_model_write",),
            broken_tokens=("Completed",),
        ),
        HazardSpec(
            failure_id="H-C11-024-empty-supplemental-claimed-current",
            protected_error_class="supplemental_zero_item_false_current",
            description=(
                "a supplemental-information operation with zero usable items is "
                "published as current"
            ),
            protected_harm=(
                "the depth audit and UI report analysis complete while the "
                "section contains no background or preparation value"
            ),
            case_id="supplemental_information_unavailable",
            broken_decision="supplemental_information_registered_and_dispatched",
            broken_writes=("analysis.supplemental_information_registry",),
            broken_side_effects=("supplemental_information_write",),
            broken_tokens=("AISupplementalInformation",),
        ),
        HazardSpec(
            failure_id="H-C11-025-internal-audit-language-becomes-summary",
            protected_error_class="human_narrative_internal_language_leak",
            description=(
                "the visible parent or child narrative describes evidence counts, "
                "owner stages, coverage, or internal review conclusions"
            ),
            protected_harm=(
                "the user cannot understand the real-world Matter without "
                "decoding the system's implementation language"
            ),
            case_id="human_matter_narrative_requested",
            broken_decision="internal_review_narrative_dispatched",
            broken_writes=("analysis.narrative_registry",),
            broken_side_effects=("narrative_synthesis_write",),
            broken_tokens=("HumanMatterNarrative",),
        ),
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
            failure_id="H-C11-003-weak-forecast-entrypoint-remains-successful",
            protected_error_class="parallel_prediction_owner",
            description=(
                "the retired lightweight Forecast or GuardBridge.register_forecast "
                "path accepts a future prediction"
            ),
            protected_harm=(
                "an untestable forecast can bypass World Model evidence, "
                "verification, contradiction, expiry, and feedback obligations"
            ),
            case_id="weak_forecast_entrypoint_requested",
            broken_decision="forecast_registered_only",
            broken_writes=("forecast_registry",),
            broken_side_effects=("finding_history_write",),
            broken_tokens=("Forecast",),
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
            failure_id="H-C11-008-hierarchy-proposal-writes-parent",
            protected_error_class="hierarchy_advisory_authority_escape",
            description="a ResearchGuard hierarchy proposal directly writes a primary parent",
            protected_harm="advisory inference bypasses C6 admission, cycle, and single-parent checks",
            case_id="hierarchy_trace_advisory_current",
            broken_decision="hierarchy_revision_appended",
            broken_writes=(
                "matter.primary_parent",
                "matter.containment_role",
                "matter.hierarchy_revision",
            ),
            broken_tokens=("ContainmentCurrent",),
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
            failure_id="H-C11-013-generated-hero-writes-c12-directly",
            protected_error_class="generated_hero_projection_owner_bypass",
            description="C11 writes the visible card hero instead of registering a generated artifact",
            protected_harm="AI generation becomes an untracked display authority",
            case_id="stable_matter_identity_needs_generated_hero",
            broken_decision="visible_hero_written",
            broken_writes=("ui.catalog_window",),
            broken_tokens=("MatterCard",),
        ),
        HazardSpec(
            failure_id="H-C11-014-named-model-product-dependency",
            protected_error_class="model_specific_product_contract",
            description="a work package requires a concrete model slug instead of a capability role",
            protected_harm="machine-local deployment availability becomes canonical product meaning",
            case_id="named_model_or_direct_api_required",
            broken_decision="bounded_analysis_work_package_queued",
            broken_writes=("agent.work_package_v2_registry",),
            broken_side_effects=("agent_work_package_write",),
            broken_tokens=("AnalysisWorkPackageV2",),
        ),
        HazardSpec(
            failure_id="H-C11-015-unavailable-capability-claimed-current",
            protected_error_class="capability_gap_hidden",
            description="an unavailable or underpowered capability mapping emits a current finding",
            protected_harm="cheap or absent execution is mistaken for completed semantic modeling",
            case_id="capability_unavailable_or_escalating",
            broken_decision="current_finding_auto_dispatched",
            broken_writes=("analysis.finding_history", "analysis.dispatch_outbox"),
            broken_side_effects=("finding_history_write", "dispatch_outbox_write"),
            broken_tokens=("Finding", "OriginalOwnerDispatch"),
        ),
        HazardSpec(
            failure_id="H-C11-016-retired-role-remains-runnable",
            protected_error_class="retired_capability_runtime_authority",
            description=(
                "a retired capability role remains directly runnable through "
                "a compatibility path"
            ),
            protected_harm=(
                "two role authorities can execute the same private evidence "
                "with different contracts"
            ),
            case_id="retired_capability_package_loaded",
            broken_decision="retired_package_executed",
            broken_writes=("agent.result_registry",),
            broken_side_effects=("finding_history_write",),
            broken_tokens=("Finding",),
        ),
        HazardSpec(
            failure_id="H-C11-017-excluded-source-sent-to-model",
            protected_error_class="analysis_policy_retirement_bypass",
            description=(
                "an old package for a now excluded or inactive source is sent "
                "to the model"
            ),
            protected_harm=(
                "program files, removed sources, or policy-rejected content "
                "still consume AI and can create false Matters"
            ),
            case_id="queued_source_no_longer_tracked",
            broken_decision="bounded_analysis_work_package_queued",
            broken_writes=("agent.result_registry",),
            broken_side_effects=("finding_history_write",),
            broken_tokens=("Finding",),
        ),
        HazardSpec(
            failure_id="H-C11-018-generated-hero-treated-as-source-evidence",
            protected_error_class="presentation_artifact_evidence_pollution",
            description="a generated hero is admitted as a Source, File, Image evidence, or factual anchor",
            protected_harm="synthetic presentation art appears to support canonical facts",
            case_id="stable_matter_identity_needs_generated_hero",
            broken_decision="generated_hero_admitted_as_evidence",
            broken_writes=("analysis.finding_history",),
            broken_side_effects=("finding_history_write",),
            broken_tokens=("Finding",),
        ),
        HazardSpec(
            failure_id="H-C11-019-supplemental-information-unlabeled-as-fact",
            protected_error_class="supplemental_context_fact_conflation",
            description="AI supplemental context is published as sourced Matter fact",
            protected_harm="reader cannot distinguish evidence-backed state from AI-added context",
            case_id="current_ai_supplemental_information",
            broken_decision="canonical_state_written",
            broken_writes=("matter.lifecycle_axes",),
            broken_tokens=("LifecycleState",),
        ),
        HazardSpec(
            failure_id="H-C11-020-unfrozen-future-prediction-evaluated",
            protected_error_class="prediction_hindsight_leak",
            description="a prediction is created after or without its observation boundary",
            protected_harm="hindsight is misreported as predictive ability",
            case_id="future_prediction_contract_current",
            broken_decision="prediction_feedback_confirmed",
            broken_writes=("analysis.world_model_feedback_registry",),
            broken_side_effects=("world_model_feedback_write",),
            broken_tokens=("PredictionFeedback",),
        ),
        HazardSpec(
            failure_id="H-C11-021-prediction-contradiction-silently-rewritten",
            protected_error_class="prediction_feedback_history_erasure",
            description="a contradicted prediction is silently edited or discarded",
            protected_harm="the model cannot learn which earlier evidence or boundary was wrong",
            case_id="later_observation_contradicts_prediction",
            broken_decision="prediction_rewritten_current",
            broken_writes=("analysis.situation_world_model_registry",),
            broken_side_effects=("world_model_write",),
            broken_tokens=("PredictionContradicted",),
        ),
        HazardSpec(
            failure_id="H-C11-022-prediction-conflict-skips-model-miss",
            protected_error_class="prediction_feedback_learning_loop_broken",
            description="a later contradiction is stored but no model-miss review is queued",
            protected_harm="the same shallow evidence or merge error can keep recurring",
            case_id="later_observation_contradicts_prediction",
            broken_decision="prediction_feedback_contradicted_only",
            broken_writes=("analysis.world_model_feedback_registry",),
            broken_side_effects=("world_model_feedback_write",),
            broken_tokens=("ModelMissRequest",),
        ),
        HazardSpec(
            failure_id="H-C11-023-unrepresentative-hero-retained",
            protected_error_class="generated_hero_visual_specificity_gap",
            description=(
                "a root Hero that could represent an unrelated Matter remains "
                "current after the visual-specificity review"
            ),
            protected_harm=(
                "the object browser repeatedly shows generic people-at-computer "
                "imagery that does not help the reader recognize each Matter"
            ),
            case_id="current_generated_hero_fails_visual_specificity",
            broken_decision="generated_hero_package_current",
            broken_writes=("analysis.hero_generation_registry",),
            broken_side_effects=("hero_generation_write",),
            broken_tokens=("GeneratedHero",),
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
        "scope, generated-hero registration, labeled supplemental information, "
        "and forecast transitions. It does not prove factual truth, "
        "ResearchGuard installation, concrete Codex model availability, model "
        "quality, or private first-run usefulness."
    ),
)
