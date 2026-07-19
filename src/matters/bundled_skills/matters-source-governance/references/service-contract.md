# MatterService source-governance contract

## Input

The service supplies one current package containing:

- `authorization_id`
- `candidate_scope_revision`
- `tracking_policy_revision`
- `hard_exclusion_policy_revision`
- bounded `candidate_ids`
- policy evidence and prior dispositions

Private paths, mailbox identifiers, and policy evidence remain under the
external runtime and are represented outside the package by opaque ids.

## Output

Return exactly one proposed row for every `candidate_id`:

- `candidate_id`
- `disposition`: `tracked`, `not_tracked`, `hard_excluded`, or `blocked`
- `confidence`: `high`, `medium`, or `low`
- `reason_code`
- `evidence_ids`
- `prior_disposition`

Use `authorization_missing` for an undeclared or stale grant. A successful
MatterService response returns the new `tracking_policy_revision`,
`affected_stage_ids`, and any hard blockers.

## Ownership and hard boundaries

The C1 owner validates and writes authorization, scope, and tracking policy.
The skill cannot enumerate adjacent roots, enlarge authorization, mutate a
mailbox, or write grants, sources, Matters, evidence, lifecycle, outcomes, or
projections. Ordinary uncertainty remains in confidence and rationale; it does
not create a normal review queue.
