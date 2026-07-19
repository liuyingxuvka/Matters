---
name: matters-research-orchestration
description: Build and run a scope-bound advisory ResearchOperation through the single ResearchGuard provider, or report pending integration. Use for evidence discovery, temporal trace, source reasoning, or argument analysis that needs the unified research boundary.
---

# Matters Research Orchestration

Read `references/service-contract.md`. Use MatterService for work-package
submission, result validation, and automatic original-owner dispatch.

1. Build one versioned, minimized work package with allowed evidence identifiers and disclosure disposition.
2. Check the portable frozen ResearchGuard currentness identity.
3. If it is missing, return `researchguard_pending_integration`; non-research
   autonomous processing, optional human correction, and synthetic conformance
   may continue.
4. If it is current, run exactly that ResearchGuard provider and validate typed, evidence-bound findings.
5. Store results as advisory findings and ask MatterService to dispatch each
   one to its declared original C4-C9/C12 owner.
6. Reject separate LogicGuard, SourceGuard, or TraceGuard runtime bindings and fallbacks.
7. Never let a research result write canonical Matter state.

Ordinary uncertainty remains typed advisory evidence and does not require user
confirmation. An unavailable or stale ResearchGuard identity remains a visible
hard boundary for real research claims.
