# MatterService two-stage semantic-understanding v4 contract

## Model-independent capability routing

The package declares a capability contract, not a concrete model:

- `capability_role`
- exact `requested_output_types`
- `execution_profile_contract_id`
- `dependency_package_ids`

MatterService selects a capability-compatible Codex-hosted execution profile.
No package, prompt, finding, or skill rule may bind a named model, vendor model
slug, or price tier. The private terminal receipt records the resolved
execution-profile identity, concrete execution identity, escalation status,
and resource use without changing the package fingerprint or semantic rules.

The pending-package response envelope supplies the current private
`execution_profile_identity` beside `items`. Copy that exact value into every
result submitted from the response. It is intentionally not part of an
immutable package: a machine-local capability remapping changes the runtime
identity and receipts without changing product work-package fingerprints. If
the field is absent or no longer current, do not guess from
`execution_profile_contract_id`; leave the package retryable and report the
runtime identity gap.

The skill never requests an API key and never calls a provider API directly.
A direct API provider or direct API fallback is invalid. An unavailable declared
capability route produces a stable blocked result rather than a second success
path.

The only normal two-stage route is:

1. `low_cost_annotator` with requested output
   `source_annotation`.
2. `matter_modeler`, dependent on the current annotation package, with any
   requested subset of the semantic outputs listed below.

The annotation stage cannot emit semantic-modeling findings. The semantic
stage cannot run while a dependency is missing, blocked, failed, stale, or
non-terminal.

The complete seven-role model-independent set is
`deterministic_preprocessor`, `low_cost_annotator`, `ambiguity_resolver`,
`matter_modeler`, `hero_image_generator`, `consistency_reviewer`, and
`maintenance_orchestrator`. Preprocessing is mechanical, annotation cannot
create a Matter, ambiguity resolution cannot write canonical state, and the
reviewer never becomes the author. Hero generation and maintenance
orchestration remain separate bounded lanes with no canonical Matter-state
write authority.

## Frozen input package

Every package binds:

- `package_id` and `package_version`
- `operation_type` and `task_kind`
- `capability_role` and exact `requested_output_types`
- `execution_profile_contract_id` and exact `dependency_package_ids`
- exact `source_revision_ids`
- optional target `matter_id` and `matter_revision`
- `authorization_identity`, `scope_identity`, `inventory_identity`, and
  `tracking_policy_identity`
- `prompt_contract_id`, `prompt_contract_revision`, and
  `prompt_contract_hash`
- `output_schema_id` and `output_schema_hash`
- required skill id, version, and content hash
- capability-router identity and `allowed_tool_ids`
- `allowed_evidence_ids` and `allowed_asset_ids`
- `locale_registry_revision` and exact `required_locales`
- disclosure policy, resource budget, and input fingerprint
- terminal `deterministic_hard_exclusion` admission
- optional opaque private `source_neighborhood_id`, `source_group_chain`,
  `source_group_labels`, `source_spatial_context_revision`, `path_depth`, and
  `file_kind`
- immutable control instructions separate from `untrusted_evidence`

No source, evidence, asset, tool, connector, path, or external action outside
that package is available to this skill.

## Typed result

Return an object with:

- exact `package_id` and `package_version`
- `status`: `passed`, `blocked`, or `failed`
- exact `execution_profile_identity` from the pending-package response envelope
- zero or more typed `findings`
- `input_dispositions`
- bounded `gaps`
- stable `failure_class` when non-passing

Every finding contains:

- `finding_type`
- one allowed `owner_model_id`
- type-specific `attributes`
- `statement`
- `localized_statement` for exactly every required locale
- one allowed `semantic_revision`
- one or more allowed `evidence_ids`
- zero or more allowed `asset_ids`
- `modality`: `observed`, `reported`, `planned`, or `inferred`
- `confidence`: `high`, `medium`, or `low`
- `uncertainty_codes`
- `alternative_explanations`

For a historical inferred `event_candidate`, `work_item_candidate`,
`lifecycle_candidate`, or `outcome_candidate`, `attributes` additionally
contains:

- `temporal_direction: past`
- `inference_purpose: historical_gap_fill`
- `inference_as_of`, exactly equal to the package `analysis_as_of`
- `target_time`, an ISO-8601 time not later than `inference_as_of`
- `revisable: true`
- one or more `contradiction_triggers`
- bounded `inference_confidence`, `supporting_signals`,
  `coverage_boundary`, `alternative_explanations`, and `expires_at`

No future target may use this inferred canonical-candidate route.

An inferred `work_item_candidate` or `lifecycle_candidate` may instead
describe the current phase, never a future occurrence or completion. It
contains:

- `temporal_direction: present`
- `temporal_assertion: ongoing`
- `inference_purpose: current_phase`
- `inference_as_of`, exactly equal to package `analysis_as_of`
- `revisable: true`
- one or more `prerequisite_evidence_ids`
- one or more `remaining_obligation_ids`
- `active_window_start` and `active_window_end` containing `inference_as_of`
- `contradiction_checked: true`
- bounded confidence, support, coverage, alternatives, expiry, and one or
  more contradiction triggers

Every finding type must be present in the package
`requested_output_types`. Allowed finding-to-owner routes are:

- `source_annotation` to A0, only for `low_cost_annotator`
- `matter_candidate` to C6
- `matter_hierarchy_candidate` to C6
- `work_item_candidate` to C6
- `person_candidate` to C4
- `event_candidate`, `material_clue_candidate`, or `deadline_candidate` to C5
- `open_loop_candidate` to C8
- `lifecycle_candidate` to C7
- `outcome_candidate` or `completion_gap` to C9
- typed identity, temporal, Matter, lifecycle, or outcome `conflict` to C4,
  C5, C6, C7, or C9
- `bounded_summary` or `summary_candidate` to C12
- `generated_hero_candidate` to C12 eligibility/preparation
- `supplemental_information_candidate` to C12

MatterService derives finding ids, result receipts, and currentness from the
frozen package. The returned `semantic_revision` must be exactly one of the
package `source_revision_ids`; output cannot invent a newer or unrelated
revision.

## Stage 1: bounded source annotation

A `low_cost_annotator` package requests exactly `source_annotation`. Its
findings may describe only bounded source-level signals such as:

- content kind and whether meaningful user content is present;
- user relevance and analysis-needed disposition;
- people, time, action, obligation, outcome, and topic clues;
- source-neighborhood or grouping clues already supplied in the private
  package; and
- likely duplicate, noise, or insufficient content.

It must not decide Matter admission, parent-child structure, work items,
identity resolution, events, material activity, deadlines, open loops,
lifecycle, outcomes, completion, conflicts, summaries, hero preparation, or
supplemental information. Those belong to original owners
after the semantic-modeling stage.

## Stage 2: semantic Matter modeling

A `matter_modeler` package may request:

- `matter_candidate`
- `matter_hierarchy_candidate`
- `work_item_candidate`
- `person_candidate`
- `event_candidate`
- `material_clue_candidate`
- `deadline_candidate`
- `open_loop_candidate`
- `lifecycle_candidate`
- `outcome_candidate`
- `completion_gap`
- `conflict`
- `bounded_summary`
- `generated_hero_candidate`
- `supplemental_information_candidate`

For every requested type, return every evidence-supported candidate needed for
the bounded input and omit unsupported candidates without fabrication.

Matter granularity follows human purpose and a strict scale contract:

- a Matter has a stable semantic identity, an independently useful goal or
  obligation, and at least one independently useful lifecycle state, outcome,
  or next step;
- an independently trackable sub-goal or obligation with its own lifecycle or
  outcome may be a child Matter;
- a smaller action or milestone that only advances a Matter is a work item;
- a single message, payment, upload, reminder, check-in, or one-time
  occurrence is a WorkItem or Event, never a Matter by itself;
- parent-child edges require evidence of containment, not mere similarity,
shared folder, shared person, shared time, shared filename, or co-occurrence.

`matter_candidate.attributes.context_signals` carries only evidence-bound
goal, subject, outcome, person, time, source-neighborhood, provider-thread,
repository/project, or Codex-workspace signals. Its `granularity` distinguishes
Matter, WorkItem, Event, source, and uncertain. It explicitly records the goal
or obligation dimension, each independent lifecycle/outcome/next-step
dimension, and why the candidate is not a WorkItem, Event, source, or the same
Matter as a current candidate. One weak signal never licenses merge or
containment; contradictory scale signals remain uncertain.

`material_clue_candidate` declares `material`, `nonmaterial`, or `uncertain`,
one user-world timestamp, a clue kind, evidence, and the bilingual summary
bound to the same revision. Scan, retry, localization, hero generation, and
summary rewording can never be material activity.

An `event_candidate` or `deadline_candidate` that corrects an already durable
event sets `attributes.revision_event_id` to that exact current event id,
provides one stable `logical_event_key`, and names the exact prior current
occurrence in `supersedes_event_id` when the new evidence replaces it. The C5
owner appends a revision to the existing event object; it does not create a
second peer Timeline row. A restart restores these supersession edges before
accepting another correction.

`matter_hierarchy_candidate` declares an evidence-supported attach, reparent,
detach, role change, split, or merge. `work_item_candidate` includes a
bilingual title, bounded status, result or next step, relevant dates,
required-for-parent flag, material-stage flag, the independent basis modality,
temporal assertion, terminality, and evidence references when supported.
During `matter_semantic_refresh`, every WorkItem and open loop also has one
stable language-neutral `semantic_role_key`. The current semantic-state
snapshot supplies existing ids and role keys. Reuse an existing id; if exact
legacy duplicates exist, name them in `supersedes_item_ids` or
`supersedes_loop_ids`. The owner rejects an unlisted same-role collision and
records accepted replacements as append-only retired revisions.
The original hierarchy owner, not the modeler, emits the current hierarchy
audit after validation.

Object kind, temporal assertion, basis modality, workflow state, and
terminality are independent fields. Temporal direction is explicit:

- evidence-recorded facts remain `observed` or `reported`;
- scheduled future facts remain `planned`;
- AI inference in the Event/outcome lanes fills only necessary historical
  gaps and remains visibly revisable;
- AI inference in the WorkItem/lifecycle lanes may also describe a bounded
  current phase when a completed prerequisite, remaining obligation, active
  window, contradiction review, and complete inference contract are present;
- a future flight, submission, or trip remains planned; a ticket,
  registration, or boarding-pass issuance may be a completed Event without
  completing the future activity;
- future expectations and predictions are emitted only by the separate C11
  Situation/World Model operation with a verification condition, contradiction
  condition, expiry, and model-miss feedback contract. They never become
  canonical Event, WorkItem, lifecycle, or outcome state.

## Human-readable bilingual projection

Every finding has non-empty, semantically equivalent English and Chinese
`localized_statement` values from the same semantic revision. The localization
map has exactly the package `required_locales`; a missing, extra, empty, or
meaningfully divergent value fails validation.

For `matter_candidate`, the localized statement supplies a short,
standalone human-readable Matter title. It names the actual situation and must
not be a raw filename, path, internal id, source fragment, date-only label,
receipt, workflow state, or unexplained system wording.

For `bounded_summary`, the localized statement supplies a one-line,
plain-language account of what the Matter is and its current
evidence-supported state. It must not expose provider, model, capability,
routing, analysis, confidence, receipt, or execution-profile jargon.

For `matter_candidate`, `attributes.topic_types` is a list of typed rows. Each
row contains a stable language-neutral `value` and a `label` map with exactly
non-empty, semantically equivalent `en` and `zh-CN` values. Topic type, title,
and summary bind the same allowed `semantic_revision`.

`generated_hero_candidate` returns only privacy-safe abstract topic and theme
concepts plus eligibility dispositions. The generated-hero owner creates and
validates the image from a separate minimized brief. The hero never enters
Source/Evidence or the Images gallery.

The Images gallery admits only useful source photos and real visual images.
Rendered email bodies, document/TXT previews, forms, or other text screenshots
remain source/evidence derivatives and are never projected as Images.

`supplemental_information_candidate` returns a bounded English/Chinese title
and body, type, relevant time when present, freshness, and supporting evidence.
It is current background/helpful context, never canonical user-world fact
without evidence.

## Complete input accounting

`input_dispositions` contains exactly one row per input in the union of
`allowed_evidence_ids` and `allowed_asset_ids`, with one of:

- `used`
- `duplicate`
- `irrelevant`
- `insufficient`
- `conflicting`

A passed result with no findings is valid only when every input still has one
complete disposition. Missing or duplicate disposition rows fail validation.
Findings may cite only whitelisted evidence and assets; input accounting never
grants permission to inspect an adjacent path, message, attachment, database,
connector, or asset.

`deterministic_hard_exclusion` blocks program source, dependency/build output,
caches, logs, temporary files, internal application databases/state,
credentials, and system records before either AI stage. Private spatial
context helps group admitted user content but never authorizes adjacent reads
or proves parent-child containment. Absolute paths, private group labels, and
spatial context cannot enter findings, public output, logs, or UI.

## Ownership and hard boundaries

Passed results remain advisory and enter `automatic_owner_dispatch`; no user
confirmation is required. The declared original owner validates and writes its
own canonical state. Ordinary uncertainty is preserved in typed fields and
does not block. Stale authorization, scope escape, privacy/safety denial,
corrupt input, unavailable required runner/schema/skill, undeclared evidence
or tools, invalid localization, and invalid schema are explicit terminal
failures. Private package content never enters the repository, Git, public
logs, or release receipts.

Generated-hero execution and `research_operation`/ResearchGuard are separate
bounded lanes. Neither may write canonical Matter state or turn the generated
hero into evidence.

Shared handoff vocabulary: `deterministic_hard_exclusion`,
`deterministic_preprocessor`, `low_cost_annotator`, `ambiguity_resolver`,
`matter_modeler`, `hero_image_generator`, `consistency_reviewer`,
`maintenance_orchestrator`, `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, parent, child,
WorkItem hierarchy audit, English/Chinese title, summary, topic type,
`generated_hero`, and `research_operation`. Canonical state never exposes an
absolute path publicly and never binds a named model, API key, direct API, or
fallback.

Contract applicability: storage_pointer=applicable_locator_bound_transient_read_only;
source_group=applicable_context_input_only;
situation_graph=applicable_advisory_candidate_output_only;
world_model=applicable_advisory_inference_output_only;
hero=applicable_root_brief_handoff_only_no_generation;
unattended=applicable_bounded_work_package_no_final_verification.
