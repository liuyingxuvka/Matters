"""C6 Matter Formation & Admission finite FlowGuard model declaration."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C6_matter_formation_admission",
    title="C6 Matter Formation & Admission",
    modeled_boundary=(
        "source-first Matter formation, autonomous admitted/source-only/"
        "not-applicable/uncertain/blocked outcomes, Matter-source visual "
        "relations, and admitted statistics"
    ),
    state_fields=(
        "matter.identity",
        "matter.admission_status",
        "matter.rationale",
        "matter.membership",
        "matter.source_relation",
    ),
    owned_write_fields=(
        "matter.identity",
        "matter.admission_status",
        "matter.rationale",
        "matter.membership",
        "matter.source_relation",
    ),
    side_effect_classes=("matter_registry_write",),
    completion_evidence=(
        "SourceOnly",
        "MatterCandidate",
        "AdmittedMatter",
        "MatterUncertain",
        "NotApplicable",
        "MatterSourceRelation",
        "AccessBlocked",
    ),
    rules=(
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
            reason="current evidence licenses a bounded Matter-to-source relation for visual ranking",
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
    ),
    hazards=(
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
            protected_harm="the object browser presents a misleading representative image",
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
    ),
    risk_classes=("decision", "state_transition", "evidence", "side_effect"),
    template_no_match_reason=(
        "The Phase A template search returned no source-first Matter-admission template."
    ),
    blindspots=(
        "the exact admission policy remains subject to private canaries and later model deepening",
        "candidate exclusion from real statistics requires implementation-level alignment",
    ),
    claim_boundary=(
        "This receipt can establish C6 abstract source-first admission and "
        "rejection hazards. It does not prove the substantive admission policy, "
        "statistics implementation, production persistence, or parent closure."
    ),
)
