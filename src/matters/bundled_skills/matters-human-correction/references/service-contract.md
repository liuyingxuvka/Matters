# MatterService human-correction contract

## Input

The user initiates this optional operation with:

- `target_id`
- current `projection_revision`
- current opaque `correction_token`
- one explicit `intent`: `correct`, `tracking_override`, `revoke`,
  `restore`, or `delete`
- replacement value or bounded rationale when required
- optional on-demand evidence ids already authorized by MatterService

The operation is `optional_after_publication`; no pending AI candidate or
normal model result requires it.

## Output

MatterService returns:

- `correction_revision`
- `prior_projection_revision`
- `affected_owner_ids`
- `recompute_status`: `pending`, `current`, `failed`, or `blocked`
- `resulting_projection_revision` when current
- bounded gaps and blockers

## Ownership and hard boundaries

C10 owns correction history and dependency invalidation. Each affected
original owner validates and writes its own state before C12 republishes. The
skill cannot create a review queue, infer an intent from silence, apply a stale
token, mutate canonical state, erase history, or claim current while required
recomputation is non-terminal.
