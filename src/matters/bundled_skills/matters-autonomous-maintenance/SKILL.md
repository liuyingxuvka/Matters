---
name: matters-autonomous-maintenance
description: Advance the durable Matters coverage ledger by dispatching the next missing or stale stage to its existing owner. Use while the app is running or during a bounded maintenance pass; never use it as a new canonical owner or final-release verifier.
---

# Matters Autonomous Maintenance

Read `references/service-contract.md`. Use MatterService to inspect the current
ObjectCoverageLedger and execute only service-authorized dispatch actions.

1. Load a bounded page of current ledger rows plus their dependency,
   freshness, lease, retry, and blocker state.
2. Select one eligible `next_stage` for each claimed row according to the
   declared stage order and service-provided priority.
3. Acquire the current opaque lease or dispatch token before requesting work.
4. Dispatch exactly one task to the existing C1-C12 or infrastructure owner;
   never execute the owner's write itself.
5. Observe the terminal owner result, refresh the row, and continue with the
   next missing or stale stage within the declared concurrency and retry
   budget.
6. Stop a row only when it is `ui_ready`, no required work is applicable, or a
   declared `hard_block` is current.
7. Preserve pending, retryable, failed, stale, blocked, superseded, and not-run
   states without claiming completion.

Ordinary uncertainty does not stop the workflow when the original owner has a
valid uncertainty-preserved terminal disposition. The skill cannot enlarge
authorization, read undeclared source content, write canonical state, change
product rules, create a second scheduler path, or run final release
verification in the background.
