---
name: matters-inventory-reconciliation
description: Reconcile authorized filesystem or Gmail metadata inventories into added, modified, moved, deleted, unchanged, newly-reachable, and policy-changed sets. Use after a scan, policy revision, restart, or scope expansion.
---

# Matters Inventory Reconciliation

Read `references/service-contract.md`. Use one current authorization,
candidate scope, tracking policy, and provider cursor through MatterService.

1. Request metadata-first discovery through the declared provider adapter.
2. Send the complete bounded occurrence page set to MatterService.
3. Require exactly one terminal disposition for every current occurrence and
   one reconciliation disposition for every prior occurrence.
4. Reconcile against the last durable inventory snapshot and account for
   added, modified, moved, deleted, unchanged, newly reachable, duplicate, and
   policy-changed items.
5. Emit one exact change set and request staleness only for changed
   occurrences and declared dependents.
6. Preserve interrupted pages, scope escapes, permission failures, link loops,
   change-during-read, and unavailable cloud placeholders as explicit gaps.
7. Return counts, snapshot identity, change-set identity, and private opaque
   handles. Never expose paths, message/thread identifiers, subjects, private
   hashes, or excerpts in public output.

Do not turn every discovered item into a Matter, infer importance from a
filename, or read content during metadata reconciliation. Inventory is source
coverage, not semantic admission.
