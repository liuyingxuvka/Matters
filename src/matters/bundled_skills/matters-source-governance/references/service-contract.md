# MatterService source-governance contract

## Input

The service supplies one current package containing:

- `authorization_id`
- `candidate_scope_revision`
- `tracking_policy_revision`
- `hard_exclusion_policy_revision`
- deterministic file-classification evidence
- bounded `candidate_ids`
- policy evidence and prior dispositions

Private paths, mailbox identifiers, and policy evidence remain under the
external runtime and are represented outside the package by opaque ids.

## Output

Return exactly one proposed row for every `candidate_id`:

- `candidate_id`
- `disposition`: `tracked`, `not_tracked`, `hard_excluded`, or `blocked`
- `confidence`: `high`, `medium`, or `low`
- `reason_code`
- `evidence_ids`
- `prior_disposition`

Use `authorization_missing` for an undeclared or stale grant. A successful
MatterService response returns the new `tracking_policy_revision`,
`affected_stage_ids`, and any hard blockers.

`deterministic_hard_exclusion` runs before content extraction or AI work.
Program source, dependency/build output, caches, logs, temporary files,
internal application databases/state, credentials, and operating-system
records are terminal `hard_excluded`. A downloaded user document or image is
not excluded merely because an application stored it.

For admitted private files, retain bounded private `source_neighborhood_id`,
`source_group_chain`, `source_group_labels`,
`source_spatial_context_revision`, `path_depth`, and `file_kind`. These
preserve spatial and folder relationships without disclosing absolute/raw
paths, labels, or spatial context publicly.

## Shared capability and Matter schema

The seven model-independent capability roles are `deterministic_preprocessor`,
`low_cost_annotator`, `ambiguity_resolver`, `matter_modeler`,
`hero_image_generator`, `consistency_reviewer`, and
`maintenance_orchestrator`. The preprocessor and annotator cannot create a
Matter, and the ambiguity resolver cannot write canonical state. Only
`matter_modeler` may propose Matter admission, parent-child Matter edges,
WorkItems, and English/Chinese localized title, summary, and topic type; the
original owner validates those proposals and emits the hierarchy audit.
No role binds a named model or price tier. No skill requests an API key, calls
a provider API directly, or uses a direct API fallback.

`hero_image_generator` is presentation-only and `research_operation`/
ResearchGuard is an advisory research lane; neither may write canonical Matter
state or evidence.

## Ownership and hard boundaries

The C1 owner validates and writes authorization, scope, and tracking policy.
The skill cannot enumerate adjacent roots, enlarge authorization, mutate a
mailbox, or write grants, sources, Matters, evidence, lifecycle, outcomes, or
projections. Ordinary uncertainty remains in confidence and rationale; it does
not create a normal review queue.

Shared handoff vocabulary: `deterministic_hard_exclusion`,
`deterministic_preprocessor`, `low_cost_annotator`, `ambiguity_resolver`,
`matter_modeler`, `hero_image_generator`, `consistency_reviewer`,
`maintenance_orchestrator`, `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, parent, child,
WorkItem hierarchy audit, English/Chinese title, summary, topic type,
`generated_hero`, and `research_operation`. Canonical state never exposes an
absolute path publicly and never binds a named model, API key, direct API, or
fallback.

Contract applicability: storage_pointer=applicable_locator_fingerprint_only;
source_group=applicable_scope_context_only;
situation_graph=not_applicable;
world_model=not_applicable;
hero=not_applicable;
unattended=applicable_bounded_service_no_final_verification.
