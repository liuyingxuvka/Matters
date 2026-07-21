# MatterService skill-runtime contract

## Required inventory

The immutable pack contains exactly eleven ids:

1. `matters-source-governance`
2. `matters-inventory-reconciliation`
3. `matters-freshness-maintenance`
4. `matters-model-depth-maintenance`
5. `matters-human-correction`
6. `matters-model-miss-review`
7. `matters-skill-runtime`
8. `matters-research-orchestration`
9. `matters-semantic-understanding`
10. `matters-autonomous-maintenance`
11. `matters-hero-image-generation`

## Exact manifest and output

Every candidate binds skill id, PEP 440 version, skill-schema and Matters
compatibility, origin, exact projection `content_hash`, required flag,
installation policy, capabilities, permissions, disclosure policy,
dependencies, runtime identity, validator identity, prerelease policy, and
ResearchGuard identity when applicable.

Every current projection also binds the model-independent capability contract
for `deterministic_preprocessor`, `low_cost_annotator`,
`ambiguity_resolver`, `matter_modeler`, `hero_image_generator`,
`consistency_reviewer`, and `maintenance_orchestrator`;
deterministic-hard-exclusion policy; and the private spatial-provenance schema
`source_neighborhood_id`, `source_group_chain`, `source_group_labels`,
`source_spatial_context_revision`, `path_depth`, and `file_kind`. Absolute
paths, private labels, and spatial context are forbidden from public output.

MatterService returns one decision per required id and one bundle identity.
Valid dispositions include `bundled_internal`, exact match, newer validated
machine overlay, `bundled_update_available`,
`bundled_managed_sync_required`, or blocked.
`same_version_different_hash` is always blocked.

## Ownership and hard boundaries

The three layers are immutable bundle, machine-installed inventory, and
resolved active view. Matters-managed is an ownership subtype inside the
second layer. Absence uses the bundled skill internally and never triggers
global installation. Only an explicitly Matters-managed projection may be
staged and activated transactionally. Auxiliary S0-S5 skill-runtime state
cannot write Matter, evidence, lifecycle, outcome, or projection fields.

## Shared capability and Matter schema

The preprocessor and annotator cannot create a Matter, and the ambiguity
resolver cannot write canonical state. Only `matter_modeler` may propose
parent-child Matters, WorkItems, and English/Chinese title, summary, and topic
type; original owners validate and emit the hierarchy audit.
`deterministic_hard_exclusion` blocks program/cache/internal-application
records before AI.

An active skill is invalid if it binds a role to a named model or price tier,
requests an API key, calls a provider API directly, or uses a direct API
fallback.

`hero_image_generator` is presentation-only and `research_operation`/
ResearchGuard is an advisory research lane; neither may write canonical Matter
state or evidence.

Shared handoff vocabulary: `deterministic_hard_exclusion`,
`deterministic_preprocessor`, `low_cost_annotator`, `ambiguity_resolver`,
`matter_modeler`, `hero_image_generator`, `consistency_reviewer`,
`maintenance_orchestrator`, `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, parent, child,
WorkItem hierarchy audit, English/Chinese title, summary, topic type,
`generated_hero`, and `research_operation`. Canonical state never exposes an
absolute path publicly and never binds a named model, API key, direct API, or
fallback.

Contract applicability: storage_pointer=not_applicable_no_user_source_access;
source_group=not_applicable_no_domain_data_access;
situation_graph=not_applicable_no_domain_data_access;
world_model=not_applicable_no_domain_data_access;
hero=not_applicable_resolves_skill_identity_only;
unattended=applicable_managed_sync_only_no_final_verification.
