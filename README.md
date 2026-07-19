# Matters

Matters is a local-first personal intelligence system. It turns explicitly
authorized files and read-only Gmail data into traceable sources, evidence,
people, events, matters, open loops, outcomes, and an AI-maintained object
browser.

It is designed around one rule: adapters, AI analysis, skills, and the UI may
propose and explain, but they do not become a second source of truth.

## What the 0.2.0 local candidate includes

- Durable source inventory, tracking decisions, change detection, freshness,
  background work, correction, and owner-by-owner recomputation.
- Local text/code/configuration, bounded document/spreadsheet, image metadata
  and OCR, Gmail thread/message/attachment, and declared cloud-placeholder
  adapters.
- A single current ResearchGuard 0.1.1 entrypoint whose members are
  LogicGuard, SourceGuard, and TraceGuard. The product rejects parallel or
  fallback Guard success paths.
- An immutable app-local pack of exactly eleven Matters AI skills with
  compatibility-aware local skill resolution and bounded managed
  synchronization.
- English as the default UI language, selectable Simplified Chinese, and an
  extensible locale registry. Every user-visible AI-authored value is stored
  as an `en` and `zh-CN` map on the same semantic revision.
- A desktop-first object browser with Standard and Compact cards, automatic
  representative visuals, human-readable detail and timelines, and optional
  after-the-fact correction.
- Autonomous source classification, owner dispatch, depth checks, coverage
  reconciliation, freshness maintenance, and UI projection. Version 0.2.0
  does not require routine per-item approval.
- CLI, local HTTP UI, desktop, and MCP surfaces that delegate to one
  `MatterService`.
- FlowGuard models and tests for product behavior, UI flow, skill runtime,
  privacy, and release boundaries.

## Private data boundary

Real source content must live outside this checkout:

```text
matters/              source and synthetic public evidence
MATTERS_HOME/         private live user data and runtime state
MATTERS_EVAL_VAULT/   explicitly selected private evaluation material
```

Never put real messages, subjects, addresses, file paths, excerpts,
screenshots, receipts, embeddings, or private models into Git or a built
package. Gmail access is read-only. Mailbox mutation, file deletion or
execution, outbound messaging, remote model disclosure, and public publication
are separate permissions.

## Local use

Set a private runtime root outside the checkout, then inspect the installation:

```powershell
$env:MATTERS_HOME = "C:\path\outside\the\checkout\MATTERS_HOME"
matters version
matters capabilities
matters locales
matters-desktop
```

The desktop browser starts in English and remembers a deliberate switch to
Chinese. Large catalogs render in bounded windows while keeping all rows
reachable.

Without `MATTERS_HOME`, package health remains available in a non-writing
capability mode. No Jira, Rovo, Gmail, cloud, or private source is required to
run package and synthetic verification.

## Release boundary

Version 0.2.0 is a private local candidate. Its frozen ResearchGuard receipt
binds the external source commit, distribution, sole console, top-level skill,
three member projections, installation manifest, compatibility, native
validation, retired-skill residual state, and installed identity. Startup
rechecks the installed bytes and blocks any drift.

The first private run is progressive: the durable ledger records every
registered object and every missing, stale, partial, blocked, localized,
visual, and UI-reachability stage. A bounded canary can therefore be useful
before full semantic coverage is complete without being mislabeled as full
coverage.

A public license, remote repository, push, or hosted release still requires a
separate explicit decision.

See `docs/security/public-boundary.md`,
`docs/security/data-classification.md`, and
`openspec/changes/build-matters-model-driven-core/`.
