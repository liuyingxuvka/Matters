# Matters

Matters is a local-first personal intelligence system. It turns explicitly
authorized files and read-only Gmail data into traceable sources, evidence,
people, events, matters, open loops, outcomes, and an AI-maintained object
browser.

It is designed around one rule: adapters, AI analysis, skills, and the UI may
propose and explain, but they do not become a second source of truth.

## What version 0.3.0 includes

- Durable source inventory, tracking decisions, change detection, freshness,
  background work, correction, and owner-by-owner recomputation.
- Local text/code/configuration, bounded document/spreadsheet, image metadata
  and OCR, Gmail thread/message/attachment, and declared cloud-placeholder
  adapters.
- A single current ResearchGuard 0.1.2 entrypoint whose members are
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
  reconciliation, freshness maintenance, and UI projection. Version 0.3.0
  does not require routine per-item approval.
- CLI, local HTTP UI, desktop, and MCP surfaces that delegate to one
  `MatterService`.
- FlowGuard models and tests for product behavior, UI flow, skill runtime,
  privacy, and release boundaries.

## AI access map and Guard dependency boundary

Matters now has one public Codex gateway at `plugins/matters`. Installing that
plugin gives an AI the `$matters` skill and starts the local `matters-mcp`
entrypoint. The AI can then discover the functional model map, ask for one
bounded current situation packet, inspect relevant history and World Model
predictions, record a new user observation, submit an explicit correction,
compare prediction with reality, report a model miss, or invoke the existing
bounded maintenance path.

This public gateway is not one of the eleven internal maintenance skills. The
eleven `matters-*` skills remain an exact, immutable, app-local pack for the
running Matters release; a same-named machine-global skill does not overlay or
replace them.

The earlier plan to distribute Guard-family skills inside Matters is retired.
FlowGuard, WorldGuard, ResearchGuard, SourceGuard, TraceGuard, LogicGuard,
SkillGuard, and other Guards remain independent projects with their own
installation, version, OpenSpec, validation, and maintenance authority.
Matters vendors none of them.

ResearchGuard is the sole external real research provider. If its portable
currentness receipt is missing or stale, ordinary Matter catalog, context,
history, graph, correction, feedback, and non-research maintenance remain
available; research-dependent output and the corresponding completeness claim
stay visibly blocked. Matters never falls back to separate
SourceGuard/TraceGuard/LogicGuard runtime routes.

This repository contains the Matters gateway source, but it does not contain
ResearchGuard or any other Guard source.
Consumers who need real research must install and validate ResearchGuard
separately.

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

The Codex plugin launches `matters-mcp` as a background protocol process; it is
not an interactive command that a person needs to run in a terminal.

Routine maintenance uses one path. Installed-UI launch, first run, an explicit
Codex/CLI/MCP request, or a detected registered-source/project change may
start or resume it. Matters does not enable a recurring daily task by default;
a daily schedule is a separate explicit user opt-in adapter over the same
path.

Without `MATTERS_HOME`, package health remains available in a non-writing
capability mode. No Jira, Rovo, Gmail, cloud, or private source is required to
run package and synthetic verification.

## Release boundary

Version 0.3.0 is the first generic private GitHub release. Its frozen
ResearchGuard receipt
binds the external source commit, distribution, sole console, top-level skill,
three member projections, installation manifest, compatibility, native
validation, retired-skill residual state, and installed identity. Startup
rechecks the installed bytes and blocks any drift.

The first private run is progressive: the durable ledger records every
registered object and every missing, stale, partial, blocked, localized,
visual, and UI-reachability stage. A bounded canary can therefore be useful
before full semantic coverage is complete without being mislabeled as full
coverage.

The private repository identity is `liuyingxuvka/Matters`; the release tag is
`v0.3.0`. The release contains only generic source, synthetic validation
material, and package artifacts. It does not claim that the owner's private
Gmail, local-file, or Codex first run is complete.

The included proprietary license permits private, access-controlled repository
and release storage. A public repository, public redistribution, or an
open-source license still requires a separate explicit decision.

See `docs/security/public-boundary.md`,
`docs/security/data-classification.md`, and
`openspec/changes/build-matters-model-driven-core/`.
