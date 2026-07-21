---
name: matters-autonomous-maintenance
description: Advance the durable Matters coverage ledger by dispatching the next missing or stale stage to its existing owner. Use while the app is running or during a bounded maintenance pass; never use it as a new canonical owner or final-release verifier.
---

# Matters Autonomous Maintenance

Read `references/service-contract.md`. Use MatterService to inspect the current
ObjectCoverageLedger and execute only service-authorized dispatch actions.

1. Load a bounded page of current ledger rows plus their dependency,
   freshness, lease, retry, and blocker state.
2. Select one eligible `next_stage` for each claimed row according to the
   declared stage order and service-provided priority.
3. Acquire the current opaque lease or dispatch token before requesting work.
4. Dispatch exactly one task to the existing C1-C12 or infrastructure owner;
   never execute the owner's write itself.
5. Observe the terminal owner result, refresh the row, and continue with the
   next missing or stale stage within the declared concurrency and retry
   budget.
6. Stop a row only when it is `ui_ready`, no required work is applicable, or a
   declared `hard_block` is current.
7. Preserve pending, retryable, failed, stale, blocked, superseded, and not-run
   states without claiming completion.

The normal stage dependency is deterministic hard exclusion, admitted
extraction, `deterministic_preprocessor`, `low_cost_annotator`, conditional
`ambiguity_resolver`, `matter_modeler`, original-owner validation,
parent-child/WorkItem hierarchy audit, applicable `consistency_reviewer`,
presentation-only `hero_image_generator`, localization/projection,
supplemental information, and UI reachability. `research_operation`/
ResearchGuard is separately applicable only for declared research. Neither
presentation nor research output can write canonical state. Never dispatch a
downstream stage before its dependencies are current.

Ordinary uncertainty does not stop the workflow when the original owner has a
valid uncertainty-preserved terminal disposition. The skill cannot enlarge
authorization, read undeclared source content, write canonical state, change
product rules, create a second scheduler path, or run final release
verification in the background.

## Shared Matters product contract

The seven model-independent capability roles are `deterministic_preprocessor`,
`low_cost_annotator`, `ambiguity_resolver`, `matter_modeler`,
`hero_image_generator`, `consistency_reviewer`, and
`maintenance_orchestrator`. The preprocessor and annotator cannot create a Matter;
the ambiguity resolver cannot write canonical state. Only `matter_modeler` may
propose parent-child Matters, WorkItems, and bilingual English/Chinese title,
summary, and topic type; original owners validate and emit the hierarchy audit.

Preserve private `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, `path_depth`, and
`file_kind` through dispatch. `deterministic_hard_exclusion` makes
program/cache/internal-application records terminal without AI. Never expose
absolute paths or private context publicly. Never bind a role to a named model
or price tier, request an API key, call a provider API directly, or use a
direct API fallback.

Shared handoff vocabulary: `deterministic_hard_exclusion`,
`deterministic_preprocessor`, `low_cost_annotator`, `ambiguity_resolver`,
`matter_modeler`, `hero_image_generator`, `consistency_reviewer`,
`maintenance_orchestrator`, `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, parent, child,
WorkItem hierarchy audit, English/Chinese title, summary, topic type,
`generated_hero`, and `research_operation`. Canonical state never exposes an
absolute path publicly and never binds a named model, API key, direct API, or
fallback.
