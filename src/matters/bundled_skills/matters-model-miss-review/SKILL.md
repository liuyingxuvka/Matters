---
name: matters-model-miss-review
description: Capture a bounded runtime behavior that the current Matters requirements or FlowGuard models cannot represent correctly. Use after tests, logs, real review, or provider behavior exposes a model miss.
---

# Matters Model Miss Review

Read `references/service-contract.md`. Use MatterService only for the bounded handoff.

1. Preserve the failing private example only under `MATTERS_HOME` using an opaque public handle.
2. Describe the `expected_behavior`, `observed_behavior`, current model/owner
   path, exact inputs, and claim boundary.
3. Classify whether the miss concerns automatic dispatch, prompt isolation,
   deterministic hard exclusion, private spatial provenance, capability-role
   separation, parent-child Matter/WorkItem modeling, hierarchy audit,
   bilingual title/summary/topic-type equivalence, original-owner validation,
   coverage progression, card density, representative-visual selection, or
   another declared path.
4. Keep the current product result partial or blocked.
5. Create one development-pipeline work item; do not edit requirements,
   FlowGuard models, validators, skills, prompts, or product code at runtime.
6. Require explicit model revision, native validation, focused regression, and
   rollback before any later product change.

Do not teach a permanent online rule from one private occurrence, retry an
unchanged failing path indefinitely, or place private evidence in the
repository.

## Shared Matters product contract

The seven model-independent capability roles are `deterministic_preprocessor`,
`low_cost_annotator`, `ambiguity_resolver`, `matter_modeler`,
`hero_image_generator`, `consistency_reviewer`, and
`maintenance_orchestrator`. A miss includes any case where preprocessing,
annotation, or ambiguity resolution creates canonical Matter state, a
non-modeler authors parent-child Matters or WorkItems, an owner omits hierarchy
audit, or English/Chinese title, summary, or topic type diverge.

Also capture failures of `deterministic_hard_exclusion` or loss/leakage of
private `source_neighborhood_id`, `source_group_chain`, `source_group_labels`,
`source_spatial_context_revision`, `path_depth`, and `file_kind`, including any
absolute-path or public leakage. Never repair a miss by binding a named model,
requesting an API key, calling a provider API directly, or adding a direct API
fallback.

`hero_image_generator` is presentation-only and `research_operation`/
ResearchGuard is an advisory research lane. Neither may write canonical Matter
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
