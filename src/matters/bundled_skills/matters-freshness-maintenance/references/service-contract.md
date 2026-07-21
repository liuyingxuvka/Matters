# MatterService freshness-maintenance contract

## Input

Each row supplies:

- `coverage_row_id`
- current `dependency_fingerprint`
- exact upstream identity map
- prior accepted identity map
- declared dependency edges
- current stage and owner receipts

Upstream identities include source/inventory, `deterministic_hard_exclusion`,
private `source_neighborhood_id`, `source_group_chain`, `source_group_labels`,
`source_spatial_context_revision`, `path_depth`, `file_kind`, policy, anchors,
capability role and contract, prompt and result schemas, private execution
receipt, validator, active skill, correction, locale, parent-child/WorkItem
owner output, hierarchy audit, bilingual title, summary, topic type,
generated Hero, supplemental information, and original-owner output. Absolute paths, group labels,
and private spatial context never enter public output.

## Output

Return:

- `stale_dependency_ids`
- `affected_stage_ids`
- `unaffected_stage_ids`
- proposed durable work items with the exact original owner
- terminal join requirements

`card_density_preference` is explicitly presentation-only and cannot appear in
`stale_dependency_ids` for semantic or visual authority.

## Shared capability and Matter schema

The seven model-independent roles are `deterministic_preprocessor`,
`low_cost_annotator`, `ambiguity_resolver`, `matter_modeler`,
`hero_image_generator`, `consistency_reviewer`, and
`maintenance_orchestrator`. The preprocessor and annotator cannot create a Matter,
and the ambiguity resolver cannot write canonical state. Only
`matter_modeler` may propose parent-child Matters, WorkItems, and
English/Chinese localized title, summary, and topic type; the original owner
validates them and emits the hierarchy audit.

Program/cache/internal-application records remain terminal under
`deterministic_hard_exclusion`. No role binds a named model or price tier. No
skill requests an API key, calls a provider API directly, or uses a direct API
fallback.

`hero_image_generator` is presentation-only and `research_operation`/
ResearchGuard is an advisory research lane; neither may write canonical Matter
state or evidence.

## Ownership and hard boundaries

MatterService validates dependency edges and owns ChangeSet, SemanticDepth,
work-item, and currentness writes. The skill may enqueue or inspect work but
cannot impersonate an owner, mark evidence current, or turn a running/skipped
result into terminal success.

Shared handoff vocabulary: `deterministic_hard_exclusion`,
`deterministic_preprocessor`, `low_cost_annotator`, `ambiguity_resolver`,
`matter_modeler`, `hero_image_generator`, `consistency_reviewer`,
`maintenance_orchestrator`, `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, parent, child,
WorkItem hierarchy audit, English/Chinese title, summary, topic type,
`generated_hero`, and `research_operation`. Canonical state never exposes an
absolute path publicly and never binds a named model, API key, direct API, or
fallback.

Contract applicability: storage_pointer=applicable_dependency_freshness_only;
source_group=applicable_dependency_freshness_only;
situation_graph=applicable_dependency_freshness_only;
world_model=applicable_dependency_freshness_only;
hero=applicable_root_stage_freshness_only;
unattended=applicable_bounded_service_no_final_verification.
