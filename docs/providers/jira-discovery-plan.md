# Jira deployment and capability discovery plan

No Jira request is authorized in the current phase. This plan defines the
bounded discovery that becomes eligible only after the synthetic G8 gate is
green and the user grants an explicit read scope.

## Required discovery

1. Identify the exact Jira instance without storing its URL in the public
   repository.
2. Determine Cloud versus Data Center/Server, product version, authentication
   method, enabled API families, field schema, pagination behavior, attachment
   access, and permission limitations.
3. Freeze instance, project, issue, object-type, attachment, and time coverage.
4. Enforce read-only HTTP methods and reject any mutation-capable route.
5. Record a permission fingerprint and per-object expected/fetched/denied/
   skipped accounting.
6. Treat changing or missing totals, short pages, inaccessible objects, and
   unsupported endpoints as partial or unknown coverage.

## First eligible experiment

The first real experiment is one explicitly authorized issue matching J1:
clear text fields, no attachment, and a predeclared oracle. The issue is
registered as a `SourceItem + SourceVersion`; it may produce a reviewable
`MatterCandidate`, but it is never admitted mechanically.

## Decisions

- `GO`: current slice has terminal, current evidence and the user freezes it.
- `HOLD`: repair the current model/owner and rerun the same slice.
- `ABORT`: any attempted write, scope escape, or privacy leak.

No later Jira slice may begin while the current slice is failed, blocked,
stale, not run, or awaiting user review.

## Machine-checkable prerequisite contracts

The public source defines schemas and fail-closed validation only. Real values
and frozen receipts remain under an external `MATTERS_EVAL_VAULT` root.

- `JiraAuthorizationManifest` names a hashed instance and project scope,
  explicit issue/object/time boundaries, edition, version, capabilities,
  permission fingerprint, attachment permissions, read-only operation, and
  expiry.
- `JiraSliceCoverageReceipt` keeps `product_outcome`, `coverage_status`, and
  `test_result` independent and accounts expected/fetched/pagination/denied/
  skipped per object type.
- `MatterDepthReport` records Authorization, Coverage, Source, Evidence,
  Person, Event, Matter, Action/OpenLoop, State, Guard, Localization, UI,
  Freshness, and Audit separately. A critical `blocked`, `stale`, or
  `not_run` layer forbids an “analysis complete” claim.
- `JiraSliceGate` requires current G8 evidence, one current authorization, and
  explicit user `GO` on every preceding slice. `HOLD` and `ABORT` stop all
  descendants.

The repository preflight is read-only:

```powershell
python scripts/jira_slice_preflight.py --slice J1
```

Without an external authorization manifest it must return
`explicit_authorization_missing`, `read_allowed=false`, and
`real_jira_access=not_run`.
