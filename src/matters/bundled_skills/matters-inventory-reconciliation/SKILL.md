---
name: matters-inventory-reconciliation
description: Reconcile authorized filesystem or Gmail metadata inventories into added, modified, moved, deleted, unchanged, newly-reachable, and policy-changed sets. Use after a scan, policy revision, restart, or scope expansion.
---

# Matters Inventory Reconciliation

Read `references/service-contract.md`. Use one current authorization,
candidate scope, tracking policy, and provider cursor through MatterService.

1. Request metadata-first discovery through the declared provider adapter.
2. Send the complete bounded occurrence page set to MatterService.
3. Consume the prior `deterministic_hard_exclusion` result; never enqueue
   excluded program source, dependency/build output, cache, log, temporary
   file, internal application database/state, credential, or system record.
4. Preserve opaque `source_neighborhood_id`, `source_group_chain`,
   `path_depth`, and `file_kind` for admitted files and moves so physical
   folder relationships remain usable without revealing raw paths.
5. Require exactly one terminal disposition for every current occurrence and
   one reconciliation disposition for every prior occurrence.
6. Reconcile against the last durable inventory snapshot and account for
   added, modified, moved, deleted, unchanged, newly reachable, duplicate, and
   policy-changed items.
7. Emit one exact change set and request staleness only for changed
   occurrences and declared dependents.
8. Preserve interrupted pages, scope escapes, permission failures, link loops,
   change-during-read, and unavailable cloud placeholders as explicit gaps.
9. Return counts, snapshot identity, change-set identity, and private opaque
   handles. Never expose paths, message/thread identifiers, subjects, private
   hashes, or excerpts in public output.

Do not turn every discovered item into a Matter, infer importance from a
filename, or read content during metadata reconciliation. Inventory is source
coverage, not semantic admission.

## Shared Matters product contract

The seven model-independent capability roles are `deterministic_preprocessor`,
`low_cost_annotator`, `ambiguity_resolver`, `matter_modeler`,
`hero_image_generator`, `consistency_reviewer`, and
`maintenance_orchestrator`. Inventory dispatches admitted content toward these
roles but performs no semantic modeling. `deterministic_preprocessor` and
`low_cost_annotator` cannot create a Matter. `ambiguity_resolver` compares
bounded alternatives without canonical writes. Only `matter_modeler` may
propose parent-child Matters, WorkItems, and bilingual English/Chinese title,
summary, and topic type; the original owner produces the hierarchy audit.

`source_group_labels` and `source_spatial_context_revision` join
`source_neighborhood_id`, `source_group_chain`, `path_depth`, and `file_kind`
as private bounded context. Never disclose absolute paths, private labels, or
spatial context publicly.

Never bind a role to a named model or price tier, request an API key, call a
provider API directly, or use a direct API fallback.

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
