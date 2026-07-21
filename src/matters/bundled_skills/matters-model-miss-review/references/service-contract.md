# MatterService model-miss contract

## Input

Submit:

- `expected_behavior`
- `observed_behavior`
- `owner_model_id` and current path id
- exact source/operation/projection revisions
- bounded `failure_class`
- opaque private evidence handle
- current product disposition
- affected `capability_role` and capability-contract identity
- affected deterministic-exclusion, spatial-provenance, hierarchy-audit, or
  localization identity when applicable

## Output

MatterService emits one immutable `development_work_item` containing the
bounded claim, affected owner/model ids, required native validation, focused
regression requirement, and rollback requirement.

## Ownership and hard boundaries

Runtime skills cannot mutate requirements, models, tests, validators, prompts,
skills, or canonical core behavior. Private examples stay under
`MATTERS_HOME`; only opaque handles and non-reconstructable failure classes may
cross into development evidence. A model-miss handoff does not prove the later
repair or release.

## Shared capability and Matter schema

The seven model-independent roles are `deterministic_preprocessor`,
`low_cost_annotator`, `ambiguity_resolver`, `matter_modeler`,
`hero_image_generator`, `consistency_reviewer`, and
`maintenance_orchestrator`. The preprocessor and annotator cannot create a Matter,
and the ambiguity resolver cannot write canonical state. Only
`matter_modeler` may propose parent-child Matters, WorkItems, and
English/Chinese title, summary, and topic type; original owners validate and
emit the hierarchy audit.
`deterministic_hard_exclusion` blocks program/cache/internal-application
records before AI, while private `source_neighborhood_id`,
`source_group_chain`, `source_group_labels`,
`source_spatial_context_revision`, `path_depth`, and `file_kind` preserve
spatial context. Absolute paths, private labels, and context cannot leak
publicly. No role binds a named model or price tier. No skill requests an API
key, calls a provider API directly, or uses a direct API fallback.

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

Contract applicability: storage_pointer=applicable_diagnostic_handoff_only;
source_group=applicable_diagnostic_handoff_only;
situation_graph=applicable_diagnostic_handoff_only;
world_model=applicable_diagnostic_handoff_only;
hero=applicable_root_child_boundary_diagnostic_only;
unattended=not_applicable_no_runtime_repair.
