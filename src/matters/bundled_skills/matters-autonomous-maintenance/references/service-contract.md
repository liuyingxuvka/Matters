# MatterService autonomous-maintenance contract

## Input

MatterService returns a bounded page from the `object_coverage_ledger`. Each
row contains:

- `coverage_row_id` and current revision
- source/Matter target ids
- ordered required stage ids
- current/stale/non-applicable/blocked stage dispositions
- exact dependency fingerprints and owner ids
- current lease or dispatch token
- retry count, retry budget, and next eligible time
- current hard blockers

## Output

For each claimed row, return one proposed action:

- `coverage_row_id`
- `next_stage`
- exact `owner_id`
- current dispatch token
- `dispatch`, `retry`, `no_work`, or `hard_block`
- bounded rationale and dependency fingerprint

MatterService validates the token, enqueues one owner task, and returns the
durable work id. The owner result, not this skill, advances the ledger.

## Terminal and retry rules

A row is terminal only as `ui_ready`, explicitly non-applicable for every
remaining stage, or blocked by a current declared `hard_block`. Retry uses the
service budget and exact failed execution identity. An unchanged terminal
failure cannot be retried indefinitely, and a stale lease cannot dispatch.

## Ownership and hard boundaries

This coordinator owns no source, evidence, Matter, person, event, lifecycle,
open-loop, outcome, correction, localization, visual, or projection field. It
cannot mark another owner current, broaden authorization, mutate product code
or models, or own final verification. Ordinary inferred/conflicted owner
results may be terminal; per-item human confirmation is not a stage.
