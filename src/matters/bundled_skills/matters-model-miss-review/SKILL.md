---
name: matters-model-miss-review
description: Capture a bounded runtime behavior that the current Matters requirements or FlowGuard models cannot represent correctly. Use after tests, logs, real review, or provider behavior exposes a model miss.
---

# Matters Model Miss Review

Read `references/service-contract.md`. Use MatterService only for the bounded handoff.

1. Preserve the failing private example only under `MATTERS_HOME` using an opaque public handle.
2. Describe the `expected_behavior`, `observed_behavior`, current model/owner
   path, exact inputs, and claim boundary.
3. Classify whether the miss concerns automatic dispatch, prompt isolation,
   original-owner validation, bilingual equivalence, coverage progression,
   card density, representative-visual selection, or another declared path.
4. Keep the current product result partial or blocked.
5. Create one development-pipeline work item; do not edit requirements,
   FlowGuard models, validators, skills, prompts, or product code at runtime.
6. Require explicit model revision, native validation, focused regression, and
   rollback before any later product change.

Do not teach a permanent online rule from one private occurrence, retry an
unchanged failing path indefinitely, or place private evidence in the
repository.
