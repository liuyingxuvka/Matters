# MatterService human-correction contract

## Input

The user initiates this optional operation with:

- `target_id`
- current `projection_revision`
- current opaque `correction_token`
- one explicit `intent`: `correct`, `tracking_override`, `revoke`,
  `restore`, or `delete`
- one typed target such as source tracking, parent-child Matter edge, WorkItem,
  hierarchy audit, localized title, localized summary, localized topic type,
  lifecycle/outcome, or visual
- replacement value or bounded rationale when required
- optional on-demand evidence ids already authorized by MatterService

The operation is `optional_after_publication`; no pending AI candidate or
normal model result requires it.

## Output

MatterService returns:

- `correction_revision`
- `prior_projection_revision`
- `affected_owner_ids`
- `recompute_status`: `pending`, `current`, `failed`, or `blocked`
- `resulting_projection_revision` when current
- bounded gaps and blockers

## Ownership and hard boundaries

C10 owns correction history and dependency invalidation. Each affected
original owner validates and writes its own state before C12 republishes. The
skill cannot create a review queue, infer an intent from silence, apply a stale
token, mutate canonical state, erase history, or claim current while required
recomputation is non-terminal.

## Shared capability and Matter schema

The seven model-independent roles are `deterministic_preprocessor`,
`low_cost_annotator`, `ambiguity_resolver`, `matter_modeler`,
`hero_image_generator`, `consistency_reviewer`, and
`maintenance_orchestrator`. The preprocessor and annotator cannot create a Matter,
and the ambiguity resolver cannot write canonical state. Only
`matter_modeler` may propose parent-child Matters, WorkItems, and
English/Chinese title, summary, and topic type; original owners validate and
emit the hierarchy audit. Private `source_neighborhood_id`,
`source_group_chain`, `source_group_labels`,
`source_spatial_context_revision`, `path_depth`, and `file_kind` remain
non-public provenance, and `deterministic_hard_exclusion` remains terminal for
program/cache/internal-application records. Absolute paths, private labels,
and spatial context cannot leak publicly.

No role binds a named model or price tier. No skill requests an API key, calls
a provider API directly, or uses a direct API fallback.

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

Contract applicability: storage_pointer=applicable_correction_locator_only;
source_group=applicable_correction_dispatch_only;
situation_graph=applicable_correction_dispatch_only;
world_model=applicable_correction_dispatch_only;
hero=applicable_root_correction_dispatch_only;
unattended=not_applicable_human_initiated_only.
