---
name: matters-freshness-maintenance
description: Assess dependency-bound freshness and request incremental refresh work for changed sources, policies, evidence, model providers, validators, or user decisions. Use when a scan or identity change makes prior analysis potentially stale.
---

# Matters Freshness Maintenance

Read `references/service-contract.md`. Use MatterService for every request and
treat freshness as exact dependency identity, never elapsed-time guesswork.

1. Load the current inventory revision and dependency identities.
2. Compare source, scope, policy, anchor, model/provider, prompt contract,
   operation/result schema, validator, skill bundle, correction, locale,
   representative-visual, and owner-output identities.
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
