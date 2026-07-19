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

## Ownership and hard boundaries

The skill cannot create an alternate inventory, read content during a
metadata-only pass, infer canonical Matter state from names, or omit a prior
or current occurrence. It cannot expose private locators or write source,
evidence, Matter, lifecycle, outcome, or projection state directly.
