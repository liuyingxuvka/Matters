---
name: matters-human-correction
description: Apply an optional user correction, revocation, deletion, or tracking override after Matters has already produced a usable automatic result. Use only when the user chooses to inspect or correct a published result, never as a first-modeling review gate.
---

# Matters Human Correction

Read `references/service-contract.md`. Use MatterService to load one current
published projection and only the on-demand evidence the user explicitly asks
to inspect.

1. Require a current projection revision and a current opaque correction token.
2. Show the user-visible value, bounded rationale, uncertainty, and requested
   evidence without internal paths, receipts, routing ids, or debug metadata.
3. Accept only an explicit correction, tracking override, revocation, restore,
   or deletion request supplied by the user.
4. Submit the intent through MatterService so C10 records the correction and
   dispatches every affected original owner, including parent-child Matter,
   WorkItem, hierarchy audit, bilingual title/summary/topic type, source
   neighborhood, or visual owners when applicable.
5. Keep the corrected projection pending until required recomputation is
   terminal; expose failed, blocked, stale, or superseded work honestly.
6. Return the new correction revision, recompute status, and resulting
   projection revision.

This skill is `optional_after_publication`. It never asks the user to confirm
ordinary AI findings, never creates a review queue, and never treats silence
as a correction. It cannot write canonical state or erase prior revision
history directly.

## Shared Matters product contract

The seven model-independent capability roles are `deterministic_preprocessor`,
`low_cost_annotator`, `ambiguity_resolver`, `matter_modeler`,
`hero_image_generator`, `consistency_reviewer`, and
`maintenance_orchestrator`. A correction may stale their prior results but never
changes role ownership. The preprocessor and annotator cannot create a Matter,
the ambiguity resolver cannot write canonical state, and only
`matter_modeler` may propose parent-child Matters, WorkItems, and bilingual
English/Chinese title, summary, and topic type. Original owners validate and
emit the hierarchy audit.

Private `source_neighborhood_id`, `source_group_chain`, `source_group_labels`,
`source_spatial_context_revision`, `path_depth`, and `file_kind` remain bounded
provenance; `deterministic_hard_exclusion` remains ahead of AI. Never expose
absolute paths, private group labels, or spatial context publicly. Never bind
a role to a named model or price tier, request an API key, call a provider API
directly, or use a direct API fallback.

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
