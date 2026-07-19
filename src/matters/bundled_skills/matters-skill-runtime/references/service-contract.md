# MatterService skill-runtime contract

## Required inventory

The immutable pack contains exactly eleven ids:

1. `matters-source-governance`
2. `matters-inventory-reconciliation`
3. `matters-freshness-maintenance`
4. `matters-model-depth-maintenance`
5. `matters-human-correction`
6. `matters-model-miss-review`
7. `matters-skill-runtime`
8. `matters-research-orchestration`
9. `matters-semantic-understanding`
10. `matters-autonomous-maintenance`
11. `matters-card-visual-curation`

## Exact manifest and output

Every candidate binds skill id, PEP 440 version, skill-schema and Matters
compatibility, origin, exact projection `content_hash`, required flag,
installation policy, capabilities, permissions, disclosure policy,
dependencies, runtime identity, validator identity, prerelease policy, and
ResearchGuard identity when applicable.

MatterService returns one decision per required id and one bundle identity.
Valid dispositions include `bundled_internal`, exact match, newer validated
machine overlay, `bundled_update_available`,
`bundled_managed_sync_required`, or blocked.
`same_version_different_hash` is always blocked.

## Ownership and hard boundaries

The three layers are immutable bundle, machine-installed inventory, and
resolved active view. Matters-managed is an ownership subtype inside the
second layer. Absence uses the bundled skill internally and never triggers
global installation. Only an explicitly Matters-managed projection may be
staged and activated transactionally. Auxiliary S0-S5 skill-runtime state
cannot write Matter, evidence, lifecycle, outcome, or projection fields.
