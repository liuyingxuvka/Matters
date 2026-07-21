---
name: matters-freshness-maintenance
description: Assess dependency-bound freshness and request incremental refresh work for changed sources, policies, evidence, model providers, validators, or user decisions. Use when a scan or identity change makes prior analysis potentially stale.
---

# Matters Freshness Maintenance

Read `references/service-contract.md`. Use MatterService for every request and
treat freshness as exact dependency identity, never elapsed-time guesswork.

1. Load the current inventory revision and dependency identities.
2. Compare source, scope, deterministic-hard-exclusion policy, private spatial
   context, anchor, capability contract, concrete private execution receipt,
   prompt contract, operation/result schema, validator, skill bundle,
   correction, locale, hierarchy audit, generated Hero, supplemental information, and
   owner-output identities.
3. Mark only affected classification, extraction, analysis, evidence,
   original-owner dispatch, depth, localization, visual, projection, and UI
   reachability stages stale.
4. Keep `card_density_preference` presentation-only; changing standard versus
   compact density must not stale semantic or visual authority.
5. Request work from each original owner through the bounded durable queue.
6. Wait for the affected terminal join before returning a refreshed
   projection, while keeping failed, paused, cancelled, pending, and not-run
   work visible.

Never mark another owner current, broaden staleness to an unconnected row, or
use this skill to run final release verification in the background.

## Shared Matters product contract

The seven model-independent capability roles are `deterministic_preprocessor`,
`low_cost_annotator`, `ambiguity_resolver`, `matter_modeler`,
`hero_image_generator`, `consistency_reviewer`, and
`maintenance_orchestrator`. A changed `source_neighborhood_id`,
`source_group_chain`, `source_group_labels`,
`source_spatial_context_revision`, `path_depth`, or `file_kind` can stale the
affected annotation/model relation without exposing absolute or raw paths,
private labels, or spatial context publicly. A changed
`deterministic_hard_exclusion` disposition invalidates downstream content work.

`deterministic_preprocessor` and `low_cost_annotator` cannot create a Matter.
`ambiguity_resolver` cannot write canonical state. Only `matter_modeler` may
propose parent-child Matters, WorkItems, and bilingual English/Chinese title,
summary, and topic type; the owner hierarchy audit gates currentness. Never
bind a role to a named model or price tier, request an API key, call a provider
API directly, or use a direct API fallback.

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
