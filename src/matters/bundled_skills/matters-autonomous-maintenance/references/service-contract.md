# MatterService autonomous-maintenance contract

## Input

MatterService returns a bounded page from the `object_coverage_ledger`. Each
row contains:

- `coverage_row_id` and current revision
- source/Matter target ids
- ordered required stage ids
- current/stale/non-applicable/blocked stage dispositions
- exact dependency fingerprints and owner ids
- current lease or dispatch token
- retry count, retry budget, and next eligible time
- current hard blockers
- exact capability-role and dependency-package identities when AI work applies
- private spatial-provenance fingerprint and hierarchy-audit currentness

## Output

For each claimed row, return one proposed action:

- `coverage_row_id`
- `next_stage`
- exact `owner_id`
- current dispatch token
- `dispatch`, `retry`, `no_work`, or `hard_block`
- bounded rationale and dependency fingerprint

MatterService validates the token, enqueues one owner task, and returns the
durable work id. The owner result, not this skill, advances the ledger.

The normal ordered dependencies are:

1. `deterministic_hard_exclusion`
2. admitted extraction
3. `deterministic_preprocessor`
4. `low_cost_annotator`
5. conditional `ambiguity_resolver`
6. `matter_modeler`
7. original-owner Matter/person/event/lifecycle/outcome dispatch
8. parent-child Matter/WorkItem `hierarchy_audit`
9. applicable `consistency_reviewer`
10. presentation-only `generated_hero`
11. bilingual English/Chinese title, summary, topic type, and Hero alt projection
12. AI supplemental information
13. UI reachability

`research_operation`/ResearchGuard is a separate applicable advisory lane only
for declared research. Neither separate operation lane can write canonical
state. Private `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, `path_depth`, and
`file_kind` remain bounded dependency context; absolute paths, labels, and
spatial context never become public output or UI paths.

## Terminal and retry rules

A row is terminal only as `ui_ready`, explicitly non-applicable for every
remaining stage, or blocked by a current declared `hard_block`. Retry uses the
service budget and exact failed execution identity. An unchanged terminal
failure cannot be retried indefinitely, and a stale lease cannot dispatch.

## Ownership and hard boundaries

This coordinator owns no source, evidence, Matter, person, event, lifecycle,
open-loop, outcome, correction, localization, visual, or projection field. It
cannot mark another owner current, broaden authorization, mutate product code
or models, or own final verification. Ordinary inferred/conflicted owner
results may be terminal; per-item human confirmation is not a stage.

## Shared capability and Matter schema

The seven roles are `deterministic_preprocessor`, `low_cost_annotator`,
`ambiguity_resolver`, `matter_modeler`, `hero_image_generator`,
`consistency_reviewer`, and `maintenance_orchestrator`. The
preprocessor and annotator cannot create a Matter, and ambiguity resolution
cannot write canonical state. Only `matter_modeler` may propose parent-child
Matters, WorkItems, and localized title, summary, and topic type; the original
owner validates them and emits the hierarchy audit.
Program/cache/internal-application records terminate at
`deterministic_hard_exclusion`. No role binds a named model or price tier. No
skill requests an API key, calls a provider API directly, or uses a direct API
fallback.

Shared handoff vocabulary: `deterministic_hard_exclusion`,
`deterministic_preprocessor`, `low_cost_annotator`, `ambiguity_resolver`,
`matter_modeler`, `hero_image_generator`, `consistency_reviewer`,
`maintenance_orchestrator`, `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, parent, child,
WorkItem hierarchy audit, English/Chinese title, summary, topic type,
`generated_hero`, and `research_operation`. Canonical state never exposes an
absolute path publicly and never binds a named model, API key, direct API, or
fallback.

Contract applicability: storage_pointer=applicable_dispatch_only_no_retention_ownership;
source_group=applicable_dispatch_only_no_domain_ownership;
situation_graph=applicable_dispatch_only_no_domain_ownership;
world_model=applicable_dispatch_only_no_domain_ownership;
hero=applicable_root_dispatch_child_not_applicable;
unattended=applicable_bounded_maintenance_no_final_verification.
