# MatterService research-orchestration contract

## Input

Use a versioned AnalysisWorkPackage containing the exact authorization,
source revisions, allowed evidence ids, disclosure disposition, prompt/result
schema identities, requested finding types, required locales, and
`original_owner_targets`. It declares operation type `research_operation` and
one of the exact seven capability roles appropriate to the bounded task; neither
the operation nor ResearchGuard is itself a capability role. It never names a
concrete model or provider API credential.

Real execution additionally requires one portable current ResearchGuard
identity covering source commit, distribution, command, top-level skill,
member projections, manifest, residual state, compatibility, native
validation, and installed currentness.

## Output

Return one typed terminal result:

- `passed` with allowlisted advisory findings and complete input dispositions
- `researchguard_pending_integration`
- `failed`
- `blocked`

Each passed finding declares one allowed original owner and is imported through
MatterService for automatic dispatch. Synthetic fake execution remains
explicitly synthetic.

## Ownership and hard boundaries

`legacy_parallel_guard_binding_rejected` is the required disposition for
separate LogicGuard, SourceGuard, or TraceGuard runtime bindings. Research
findings cannot write canonical state, cite undeclared evidence, invoke
undeclared tools, trigger user confirmation, or become a fallback for a stale
ResearchGuard identity.

## Shared capability and Matter schema

The seven roles are `deterministic_preprocessor`, `low_cost_annotator`,
`ambiguity_resolver`, `matter_modeler`, `hero_image_generator`,
`consistency_reviewer`, and `maintenance_orchestrator`. The
preprocessor and annotator cannot create a Matter, and the ambiguity resolver
cannot write canonical state. Only `matter_modeler` may propose parent-child
Matters, WorkItems, and English/Chinese title, summary, and topic type;
original owners validate them and emit the hierarchy audit.

`deterministic_hard_exclusion` blocks program/cache/internal-application
records before research or other AI work. Allowlisted private
`source_neighborhood_id`, `source_group_chain`, `source_group_labels`,
`source_spatial_context_revision`, `path_depth`, and `file_kind` may supply
spatial context but absolute paths, labels, and context remain private and
cannot leak publicly. No role binds a named model or price tier. No skill
requests an API key, calls a provider API directly, or uses a direct API
fallback.

`research_operation`/ResearchGuard is advisory and `hero_image_generator` is
presentation-only; neither can write canonical Matter state or evidence.

Shared handoff vocabulary: `deterministic_hard_exclusion`,
`deterministic_preprocessor`, `low_cost_annotator`, `ambiguity_resolver`,
`matter_modeler`, `hero_image_generator`, `consistency_reviewer`,
`maintenance_orchestrator`, `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, parent, child,
WorkItem hierarchy audit, English/Chinese title, summary, topic type,
`generated_hero`, and `research_operation`. Canonical state never exposes an
absolute path publicly and never binds a named model, API key, direct API, or
fallback.

Contract applicability: storage_pointer=applicable_minimized_pointer_input_only;
source_group=applicable_advisory_context_only;
situation_graph=applicable_advisory_snapshot_input_only;
world_model=applicable_supplemental_research_only_no_truth_write;
hero=not_applicable_research_never_generates_hero;
unattended=applicable_bounded_if_current_no_final_verification.
