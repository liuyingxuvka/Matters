---
name: matters-source-governance
description: Govern declared source roots, mailbox policies, authorization boundaries, and automatic tracking-policy decisions. Use when Matters must add, change, or re-evaluate what it may discover without enlarging the user's grant.
---

# Matters Source Governance

Read `references/service-contract.md`. Use only the installed Matters CLI or
injected MatterService. This skill proposes bounded owner actions; it never
writes grants, source state, or Matter state directly.

1. Load the current capability report, authorization identity, candidate-scope
   revision, tracking-policy revision, and hard-exclusion policy.
2. Refuse any undeclared root, mailbox scope, connector, or adjacent source as
   `authorization_missing`; never enlarge the grant.
3. Within the authorized scope, give every proposed source target exactly one
   evidence-bound disposition: `tracked`, `not_tracked`, `hard_excluded`, or
   `blocked`.
4. Preserve confidence, reason codes, policy evidence, and the prior
   disposition so a later user correction remains possible.
5. Submit the proposed intents through MatterService for the C1 owner to
   validate and apply.
6. Return the resulting authorization, scope, and tracking-policy revisions
   plus affected freshness stages and any hard blocker.

Ordinary uncertainty is not a per-item human-review gate. Make the best bounded
decision and retain its uncertainty. Credentials, system/application
internals, repositories, dependency/build output, caches, private runtime
state, and out-of-scope links remain hard excluded.

If `MATTERS_HOME` is absent or invalid, stop with the visible capability
result. Do not create a fallback directory, scan the user's home directory, or
mutate Gmail.
