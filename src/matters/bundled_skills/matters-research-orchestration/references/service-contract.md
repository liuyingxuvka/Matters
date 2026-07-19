# MatterService research-orchestration contract

## Input

Use a versioned AnalysisWorkPackage containing the exact authorization,
source revisions, allowed evidence ids, disclosure disposition, prompt/result
schema identities, requested finding types, required locales, and
`original_owner_targets`.

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
