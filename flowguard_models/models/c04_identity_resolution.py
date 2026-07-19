"""C4 Person & Entity Resolution finite FlowGuard model declaration."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C4_person_entity_resolution",
    title="C4 Person & Entity Resolution",
    modeled_boundary="evidence-scoped identity candidates, merge/split decisions, and Matter roles",
    state_fields=(
        "person.identity_assertion",
        "person.merge_split_history",
        "matter.role",
    ),
    owned_write_fields=(
        "person.identity_assertion",
        "person.merge_split_history",
        "matter.role",
    ),
    side_effect_classes=("identity_registry_write",),
    completion_evidence=(
        "PersonCandidate",
        "IdentityAssertion",
        "MatterRole",
        "IdentityUncertainty",
    ),
    rules=(
        CaseRule(
            case_id="same_name_no_link",
            decision="distinct_person_candidates",
            label="distinct_person_candidates",
            writes=("person.identity_assertion",),
            side_effects=("identity_registry_write",),
            emitted_tokens=("PersonCandidate", "IdentityUncertainty"),
            reason=(
                "same display name lacks identity-linking evidence, so separate "
                "identities are retained automatically with explicit uncertainty"
            ),
        ),
        CaseRule(
            case_id="assignee_role",
            decision="matter_role_candidate",
            label="matter_role_candidate",
            writes=("matter.role",),
            side_effects=("identity_registry_write",),
            emitted_tokens=("MatterRole",),
            reason="provider assignee supports only a Matter-scoped role candidate",
        ),
        CaseRule(
            case_id="strong_identity_link",
            decision="identity_assertion",
            label="identity_assertion",
            writes=("person.identity_assertion",),
            side_effects=("identity_registry_write",),
            emitted_tokens=("IdentityAssertion",),
            reason="current evidence licenses identity equivalence",
        ),
        CaseRule(
            case_id="user_split_correction",
            decision="identity_split_revision",
            label="identity_split_revision",
            writes=("person.identity_assertion", "person.merge_split_history"),
            side_effects=("identity_registry_write",),
            emitted_tokens=("IdentityAssertion", "RecomputeRequest"),
            reason="user correction appends a split and invalidates dependents",
        ),
        CaseRule(
            case_id="researchguard_identity_proposal",
            decision="identity_uncertain_separate",
            label="identity_uncertain_separate",
            writes=("person.identity_assertion",),
            side_effects=("identity_registry_write",),
            emitted_tokens=("PersonCandidate", "IdentityUncertainty"),
            reason=(
                "ResearchGuard or AI similarity remains an evidence-scoped "
                "uncertain relation and cannot merge identities"
            ),
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-C4-001-same-name-auto-merge",
            protected_error_class="unsafe_identity_merge",
            description="two same-name mentions are merged without evidence",
            protected_harm="events, roles, and matters are assigned to the wrong person",
            case_id="same_name_no_link",
            broken_decision="identity_assertion",
            broken_writes=("person.identity_assertion",),
            broken_side_effects=("identity_registry_write",),
            broken_tokens=("IdentityAssertion",),
        ),
        HazardSpec(
            failure_id="H-C4-002-assignee-becomes-global-relationship",
            protected_error_class="role_scope_expansion",
            description="a provider assignee becomes a global friend or responsible-person relationship",
            protected_harm="transaction metadata is misrepresented as a stable human relationship",
            case_id="assignee_role",
            broken_decision="global_relationship_created",
            broken_writes=("person.identity_assertion", "matter.role"),
            broken_side_effects=("identity_registry_write",),
            broken_tokens=("GlobalRelationship",),
        ),
        HazardSpec(
            failure_id="H-C4-003-split-without-dependent-recompute",
            protected_error_class="identity_correction_propagation_loss",
            description="an incorrect merge is split without recomputing dependents",
            protected_harm="old events, roles, and matters remain assigned to the wrong identity",
            case_id="user_split_correction",
            broken_decision="identity_split_without_recompute",
            broken_writes=("person.identity_assertion", "person.merge_split_history"),
            broken_side_effects=("identity_registry_write",),
            broken_tokens=("IdentityAssertion",),
        ),
        HazardSpec(
            failure_id="H-C4-004-ai-similarity-auto-merge",
            protected_error_class="advisory_identity_authority_escape",
            description="AI name, address, or visual similarity directly merges identities",
            protected_harm="private events and roles are assigned to the wrong person",
            case_id="researchguard_identity_proposal",
            broken_decision="identity_assertion",
            broken_writes=("person.identity_assertion",),
            broken_side_effects=("identity_registry_write",),
            broken_tokens=("IdentityAssertion",),
        ),
    ),
    risk_classes=("identity", "ownership", "side_effect"),
    template_no_match_reason=(
        "The Phase A template search returned no identity-resolution or scoped-role template."
    ),
    blindspots=(
        "real directory identifiers and provider account linking require live evidence",
        "human identity policy and AI-similarity ambiguity remain explicit and optionally correctable",
    ),
    claim_boundary=(
        "This receipt can establish C4 abstract same-name, role-scope, and "
        "correction behavior. It does not prove a real person's identity or "
        "the completeness of dependent recomputation."
    ),
)
