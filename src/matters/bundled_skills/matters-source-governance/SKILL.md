---
name: matters-source-governance
description: Govern declared source roots, mailbox policies, authorization boundaries, and automatic tracking-policy decisions. Use when Matters must add, change, or re-evaluate what it may discover without enlarging the user's grant.
---

# Matters Source Governance

Read `references/service-contract.md`. Use only the installed Matters CLI or
injected MatterService. This skill proposes bounded owner actions; it never
writes grants, source state, or Matter state directly.

1. Load the current capability report, authorization identity, candidate-scope
   revision, tracking-policy revision, and hard-exclusion policy.
2. Refuse any undeclared root, mailbox scope, connector, or adjacent source as
   `authorization_missing`; never enlarge the grant.
3. Apply `deterministic_hard_exclusion` before any AI package. Program source,
   dependency/build output, caches, logs, temporary files, internal
   application databases/state, credentials, and operating-system records are
   `hard_excluded`; user documents, images, mail, and declared downloads remain
   eligible for content analysis.
4. Within the authorized scope, give every proposed source target exactly one
   evidence-bound disposition: `tracked`, `not_tracked`, `hard_excluded`, or
   `blocked`.
5. Preserve confidence, reason codes, policy evidence, and the prior
   disposition so a later user correction remains possible.
6. Submit the proposed intents through MatterService for the C1 owner to
   validate and apply.
7. Return the resulting authorization, scope, and tracking-policy revisions
   plus affected freshness stages and any hard blocker.

Ordinary uncertainty is not a per-item human-review gate. Make the best bounded
decision and retain its uncertainty. Credentials, system/application
internals, repositories, dependency/build output, caches, private runtime
state, and out-of-scope links remain hard excluded.

If `MATTERS_HOME` is absent or invalid, stop with the visible capability
result. Do not create a fallback directory, scan the user's home directory, or
mutate Gmail.

## Shared Matters product contract

The seven model-independent capability roles are `deterministic_preprocessor`,
`low_cost_annotator`, `ambiguity_resolver`, `matter_modeler`,
`hero_image_generator`, `consistency_reviewer`, and
`maintenance_orchestrator`. This skill performs deterministic governance and does
not impersonate them. `deterministic_preprocessor` applies bounded mechanical
classification, `low_cost_annotator` annotates admitted content, and neither
can create a Matter. `ambiguity_resolver` may compare bounded alternatives but
cannot write canonical state. Only `matter_modeler` may propose a parent-child
Matter, WorkItem, or bilingual English/Chinese title, summary, and topic type;
the original hierarchy owner produces the hierarchy audit.

Preserve private `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, `path_depth`, and
`file_kind` as bounded spatial provenance so files are not flattened into
unrelated items. Never expose absolute paths, raw paths, group labels, or
spatial context in public output or product UI. Never bind a capability role
to a named model or price tier, request an API key, call a provider API
directly, or use a direct API fallback.

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
