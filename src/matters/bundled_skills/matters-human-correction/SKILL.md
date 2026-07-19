---
name: matters-human-correction
description: Apply an optional user correction, revocation, deletion, or tracking override after Matters has already produced a usable automatic result. Use only when the user chooses to inspect or correct a published result, never as a first-modeling review gate.
---

# Matters Human Correction

Read `references/service-contract.md`. Use MatterService to load one current
published projection and only the on-demand evidence the user explicitly asks
to inspect.

1. Require a current projection revision and a current opaque correction token.
2. Show the user-visible value, bounded rationale, uncertainty, and requested
   evidence without internal paths, receipts, routing ids, or debug metadata.
3. Accept only an explicit correction, tracking override, revocation, restore,
   or deletion request supplied by the user.
4. Submit the intent through MatterService so C10 records the correction and
   dispatches every affected original owner.
5. Keep the corrected projection pending until required recomputation is
   terminal; expose failed, blocked, stale, or superseded work honestly.
6. Return the new correction revision, recompute status, and resulting
   projection revision.

This skill is `optional_after_publication`. It never asks the user to confirm
ordinary AI findings, never creates a review queue, and never treats silence
as a correction. It cannot write canonical state or erase prior revision
history directly.
