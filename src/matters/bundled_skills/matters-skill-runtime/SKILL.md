---
name: matters-skill-runtime
description: Inspect and resolve the immutable bundled Skill Pack, machine-installed inventory, singular active view, compatibility, and Matters-managed synchronization. Use when skill availability, version, currentness, collision, or rollback matters.
---

# Matters Skill Runtime

Read `references/service-contract.md`. Expose decisions through MatterService
and never create a second product path.

1. Inventory exactly the eleven bundle-declared ids in the immutable bundled
   layer and machine-installed layer without enumerating unrelated skills.
2. Validate exact manifests, projection content hashes, PEP 440 versions and
   intervals, prerelease policy, dependencies, runtime identity, native
   validator, the seven capability-role contracts, and ResearchGuard identity
   when applicable.
3. Resolve exactly one active compatible candidate per required skill.
4. Prefer a valid newer machine copy as a non-mutating overlay.
5. Prefer a newer bundled copy internally when an older external copy is unmanaged, and report update available.
6. Block `same_version_different_hash`, invalid manifests, incompatible
   candidates, prereleases without opt-in, dependency drift, validator drift,
   and author-maintenance residuals.
7. Synchronize only the Matters-managed installed subtype using stage, native
   validation, atomic activation, installed-currentness check, and rollback.

The resolver has exactly three layers: immutable bundled pack,
machine-installed inventory, and resolved active view. Never install a
bundled-only skill globally merely because it is absent, overwrite an
externally managed copy, or treat the managed subtype as a fourth layer.

## Shared Matters product contract

Every active projection must preserve the same model-independent roles:
`deterministic_preprocessor`, `low_cost_annotator`, `ambiguity_resolver`,
`matter_modeler`, `hero_image_generator`, `consistency_reviewer`, and
`maintenance_orchestrator`. The preprocessor and annotator cannot create a
Matter, and the ambiguity resolver cannot write canonical state. Only
`matter_modeler` may propose parent-child Matters, WorkItems, and bilingual
English/Chinese title, summary, and topic type; the original owner emits the
hierarchy audit.

The projection must also preserve `deterministic_hard_exclusion` before AI and
private `source_neighborhood_id`, `source_group_chain`, `source_group_labels`,
`source_spatial_context_revision`, `path_depth`, and `file_kind` provenance.
It must forbid absolute paths and public leakage. Reject any projection that
binds a named model or price tier, requests an API key, calls a provider API
directly, or adds a direct API fallback.

`hero_image_generator` is presentation-only and `research_operation`/
ResearchGuard is advisory. Neither may write canonical Matter state or
evidence.

Shared handoff vocabulary: `deterministic_hard_exclusion`,
`deterministic_preprocessor`, `low_cost_annotator`, `ambiguity_resolver`,
`matter_modeler`, `hero_image_generator`, `consistency_reviewer`,
`maintenance_orchestrator`, `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, parent, child,
WorkItem hierarchy audit, English/Chinese title, summary, topic type,
`generated_hero`, and `research_operation`. Canonical state never exposes an
absolute path publicly and never binds a named model, API key, direct API, or
fallback.
