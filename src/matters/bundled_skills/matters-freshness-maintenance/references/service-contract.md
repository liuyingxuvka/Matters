# MatterService freshness-maintenance contract

## Input

Each row supplies:

- `coverage_row_id`
- current `dependency_fingerprint`
- exact upstream identity map
- prior accepted identity map
- declared dependency edges
- current stage and owner receipts

Upstream identities include source/inventory, policy, anchors, prompt and
result schemas, provider, validator, active skill, correction, locale,
representative visual, and original-owner output.

## Output

Return:

- `stale_dependency_ids`
- `affected_stage_ids`
- `unaffected_stage_ids`
- proposed durable work items with the exact original owner
- terminal join requirements

`card_density_preference` is explicitly presentation-only and cannot appear in
`stale_dependency_ids` for semantic or visual authority.

## Ownership and hard boundaries

MatterService validates dependency edges and owns ChangeSet, SemanticDepth,
work-item, and currentness writes. The skill may enqueue or inspect work but
cannot impersonate an owner, mark evidence current, or turn a running/skipped
result into terminal success.
