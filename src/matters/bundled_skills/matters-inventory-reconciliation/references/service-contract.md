# MatterService inventory-reconciliation contract

## Input

The service supplies:

- `authorization_id`
- `candidate_scope_revision`
- `tracking_policy_revision`
- `provider_id` and `provider_cursor`
- `prior_inventory_snapshot_id`
- complete bounded current `occurrence_rows`
- explicit page-completion and provider-gap rows

Every occurrence is referenced by an opaque stable id. Private locators and
content remain in the provider/runtime boundary.

Every file occurrence also carries its terminal
`deterministic_hard_exclusion` disposition. Eligible private files retain
opaque `source_neighborhood_id`, `source_group_chain`, `source_group_labels`,
`source_spatial_context_revision`, `path_depth`, and `file_kind`; excluded
program/cache/internal-application records never enter content-analysis work.
Absolute paths, group labels, and spatial context never enter public output.

## Output

Return:

- `occurrence_dispositions`, with exactly one row per current occurrence
- prior-row dispositions for deleted, moved, or superseded occurrences
- one proposed `inventory_snapshot`
- one proposed `change_set`
- `added`, `modified`, `moved`, `deleted`, `unchanged`,
  `newly_reachable`, `duplicate`, and `policy_changed` id sets
- bounded gaps and affected dependency ids

MatterService validates the complete-universe equality before the C2 owner
writes the authoritative InventorySnapshot and ChangeSet.

Moves update the private spatial context without erasing prior provenance.
Files in one declared folder neighborhood are not flattened into unrelated
sources, but folder proximity alone never creates a Matter or parent-child
edge.

## Shared capability and Matter schema

The seven model-independent capability roles are `deterministic_preprocessor`,
`low_cost_annotator`, `ambiguity_resolver`, `matter_modeler`,
`hero_image_generator`, `consistency_reviewer`, and
`maintenance_orchestrator`. The preprocessor and annotator cannot create a
Matter, and the ambiguity resolver cannot write canonical state. Only
`matter_modeler` may propose Matter admission, parent-child Matter edges,
WorkItems, and English/Chinese localized title, summary, and topic type; the
original owner validates them and emits the hierarchy audit. No role binds a
named model or price tier. No skill requests an API key, calls a provider API
directly, or uses a direct API fallback.

`hero_image_generator` is presentation-only and `research_operation`/
ResearchGuard is an advisory research lane. Neither may write canonical Matter
state or evidence.

## Ownership and hard boundaries

The skill cannot create an alternate inventory, read content during a
metadata-only pass, infer canonical Matter state from names, or omit a prior
or current occurrence. It cannot expose private locators or write source,
evidence, Matter, lifecycle, outcome, or projection state directly.

Shared handoff vocabulary: `deterministic_hard_exclusion`,
`deterministic_preprocessor`, `low_cost_annotator`, `ambiguity_resolver`,
`matter_modeler`, `hero_image_generator`, `consistency_reviewer`,
`maintenance_orchestrator`, `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, parent, child,
WorkItem hierarchy audit, English/Chinese title, summary, topic type,
`generated_hero`, and `research_operation`. Canonical state never exposes an
absolute path publicly and never binds a named model, API key, direct API, or
fallback.

Contract applicability: storage_pointer=applicable_locator_fingerprint_reconciliation_only;
source_group=applicable_membership_reconciliation_only;
situation_graph=not_applicable;
world_model=not_applicable;
hero=not_applicable;
unattended=applicable_bounded_service_no_final_verification.
