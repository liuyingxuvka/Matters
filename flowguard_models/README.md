# Matters FlowGuard models

Each model declaration in `flowguard_models/models/` is an immutable finite
case contract. `harness.py` projects that declaration into the installed
FlowGuard `Workflow`, `RiskIntent`, `MinimumModelContract`,
`KnownBadProof`, template reuse/harvest review, invariants, and
`FlowGuardCheckPlan`.

Every executable block is:

```text
CaseInput x ModelState -> Set(DecisionOutput x ModelState)
```

The correct model must pass its declared relation and ownership invariants.
Exactly one intentionally broken workflow variant is executed for each
protected failure id, and each variant must fail before the receipt can claim
`hazard_green`.

Receipts under `.flowguard/evidence/models/` are model evidence only. They do
not prove production conformance, live provider behavior, parent ModelMesh
closure, UI behavior, privacy release readiness, or Jira authorization.
