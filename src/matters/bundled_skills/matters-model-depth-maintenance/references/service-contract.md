# MatterService model-depth contract

## Input

The service supplies one revision-bound `criteria_map` containing:

- `coverage_terminal`
- `extraction_current`
- `analysis_terminal`
- `evidence_anchored`
- `original_owner_terminal`
- `localization_terminal`
- `generated_hero_terminal`
- `projection_terminal`
- `ui_reachability_terminal`

Each criterion includes applicability, owner, dependency identities, and the
current terminal receipt when one exists. `coverage_terminal` distinguishes a
terminal deterministic hard exclusion from admitted content.
`analysis_terminal` requires current `deterministic_preprocessor`, followed by
`low_cost_annotator`, conditional `ambiguity_resolver`, `matter_modeler`, and
`consistency_reviewer` only when applicable.
`original_owner_terminal` includes parent-child/WorkItem hierarchy audit, and
`localization_terminal` includes English/Chinese title, summary, and topic type.

## Output

Return one state:

- `not_assessed`
- `partial`
- `sufficient`
- `blocked`
- `stale`

Also return exact `missing_criteria`, `non_applicable_criteria`,
`blocking_criteria`, `dependency_fingerprint`, and proposed owner work items.
`sufficient` requires every applicable criterion to be current and terminal.

The criteria bind private `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, `path_depth`, and
`file_kind` as provenance identities without exposing absolute paths, group
labels, or spatial context publicly. Program/cache/internal-application
records are sufficient only through a terminal
`deterministic_hard_exclusion` disposition; they never require AI content work.

## Shared capability and Matter schema

The seven model-independent capability roles are `deterministic_preprocessor`,
`low_cost_annotator`, `ambiguity_resolver`, `matter_modeler`,
`hero_image_generator`, `consistency_reviewer`, and
`maintenance_orchestrator`. The preprocessor and annotator cannot create a Matter,
and the ambiguity resolver cannot write canonical state. Only
`matter_modeler` may propose parent-child Matters, WorkItems, and
English/Chinese localized title, summary, and topic type; the original owner
emits the hierarchy audit. No role binds a named model or price tier. No skill
requests an API key, calls a provider API directly, or uses a direct API
fallback.

`hero_image_generator` is presentation-only and `research_operation`/
ResearchGuard is an advisory research lane. Neither may write canonical Matter
state or evidence.

## Ownership and hard boundaries

Depth is a product assessment, not an AI confidence score. MatterService owns
the assessment and work queue. The skill cannot declare evidence anchored,
original-owner work terminal, a generated Hero current, or UI
reachability complete on another owner's behalf.

The explicit presentation-stage check is `generated_hero_terminal`.

Shared handoff vocabulary: `deterministic_hard_exclusion`,
`deterministic_preprocessor`, `low_cost_annotator`, `ambiguity_resolver`,
`matter_modeler`, `hero_image_generator`, `consistency_reviewer`,
`maintenance_orchestrator`, `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, parent, child,
WorkItem hierarchy audit, English/Chinese title, summary, topic type,
`generated_hero`, and `research_operation`. Canonical state never exposes an
absolute path publicly and never binds a named model, API key, direct API, or
fallback.

Contract applicability: storage_pointer=applicable_depth_input_only;
source_group=applicable_depth_input_only;
situation_graph=applicable_depth_assessment_only;
world_model=applicable_depth_assessment_only;
hero=applicable_root_terminal_assessment_only;
unattended=applicable_bounded_service_no_final_verification.
