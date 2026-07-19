## Why

The first Matters user has authorized the product to organize all user-owned
content that it can legitimately reach, including local files, documents,
photos, Gmail, and cloud-backed user folders. The current plan covers only
pasted text, individually selected text files, and a small Gmail sample, so it
cannot perform or honestly report the requested first private run.

Matters v0.2 therefore needs a local-first, AI-autonomous source-universe workflow
that first freezes candidate folders and mailbox policy, separates useful
tracking candidates from system material, generated clutter, junk, and
irrelevant content, and then makes every discovered item end in an explicit
disposition. It must preserve exact provenance and uncertainty, invalidate
stale scope decisions when sources change, survive interruption, and prevent
private source or derived understanding from entering public Git or becoming
unsupported canonical truth.

## What Changes

- Treat all authorized user-content sources as the v0.2 coverage target:
  pasted text; user-content roots such as Documents, Desktop, Downloads,
  Pictures, Music, Videos, and configured user data roots; PDF and Office
  documents; photos and images; Gmail messages, threads, and attachments; and
  reachable cloud-backed user content.
- Add a metadata-first scope-organization gate before broad content analysis.
  Freeze candidate roots, mailbox categories/query policy, hard exclusions,
  and a versioned tracking policy; automatically classify each discovered item
  as `tracked`, `not_tracked` with reason, `hard_excluded`, `metadata_only`,
  `blocked`, `unavailable`, or another declared disposition. Hard
  system/credential/cache exclusions are policy-owned. AI makes reversible
  relevance/junk dispositions under the frozen policy and records model
  identity, confidence, uncertainty, evidence features, and reason. Ordinary
  uncertainty does not wait for user approval; AI selects the best supported
  current disposition while preserving alternatives. AI may never enlarge
  authorization, delete content, or hide an item without a disposition.
- Make folder and mailbox freshness explicit. Persist inventory snapshot
  revisions and occurrence fingerprints, detect added, modified, moved,
  deleted, and newly reachable items, mark affected classification/extraction/
  analysis results stale, and incrementally re-triage only the changed
  occurrence and declared dependents. A no-change scan produces no duplicate
  work. User overrides and policy revisions remain append-only and can return
  an item to tracking.
- Make coverage progressive and truthful. Discovery, metadata inventory,
  per-type canaries, staged extraction, and later expansion use durable cursors
  and checkpoints. Every enumerated item must end as `ingested`, `not_tracked`,
  `hard_excluded`, policy-authorized `metadata_only`, `unsupported`,
  `excluded_sensitive`, `inaccessible`, `changed_during_read`,
  `cloud_placeholder`, `quarantined`, `revoked`, `deleted`, or another
  explicitly declared terminal disposition before the system claims complete
  coverage.
- Maintain one durable `ObjectCoverageLedger` row for every registered
  occurrence and admitted Matter. The row records authorization, discovery,
  disposition, source/version, extraction, analysis, original-owner decision,
  semantic depth, localization, representative visual, UI projection,
  freshness, retry, and terminal reason so one scan can report the exact gap
  between registration and current UI-ready completion.
- Keep credentials, secrets, browser/session stores, operating-system and
  application internals, caches, dependency/build outputs, VCS internals,
  executable launch, unsafe serialized models, uncontrolled archive expansion,
  and unbounded link/junction traversal outside the content-reading boundary.
- Support local text/code/config extraction, document/page anchors, spreadsheet
  cell/range anchors, image metadata and region/OCR anchors, and Gmail
  message/thread/attachment anchors. Unsupported or unavailable formats remain
  visible gaps; the product never fabricates equivalent analysis.
- Cover the authorized Gmail account through a read-only product source path.
  Inbox, Sent, and archived non-Spam/non-Trash mail are progressively paged and
  dispositioned; Spam and Trash are `hard_excluded` or `metadata_only` by
  policy.
  Reading never implies permission to send, delete, archive, or change labels.
- Establish physically separate public source, private runtime, and private
  evaluation domains. Raw content, paths, private metadata, excerpts, hashes,
  embeddings, screenshots, logs, and derived user models remain private and
  cannot cross the publication gate.
- Register immutable source versions and precise evidence anchors before
  deriving people, events, matters, open loops, or outcomes. Cloud placeholders
  and files that change during reads receive explicit non-success dispositions.
- Run AI, multimodal analysis, and the single local ResearchGuard research
  entrypoint through versioned `agent_operation` work packages. ResearchGuard
  is the in-progress successor to the separate SourceGuard, TraceGuard, and
  LogicGuard runtime routes. Until that external merger is frozen and
  validated, Matters targets an abstract `ResearchOperation` contract and a
  deterministic synthetic runner; it does not create three final parallel
  bindings or claim that ResearchGuard is available. Every result remains
  advisory, anchored, scoped, freshness-bound, and unable to write canonical
  product state. A current frozen ResearchGuard is required for the final v0.2
  complete-release claim; without it Matters may complete inventory,
  autonomous non-research processing, optional inspection/correction,
  synthetic verification, and a blocked local candidate only.
- Ship a versioned app-local consumer Skill Pack with Matters so its own
  ingestion, inventory reconciliation, freshness, model-depth,
  human-correction, model-miss, skill-runtime, research-orchestration,
  semantic-understanding, autonomous-maintenance, and card-visual-curation
  procedures travel with
  the software without requiring global skill installation. Resolve the active
  skill view through three layers: the immutable bundled pack,
  machine-installed inventory, and one resolved active view. A Matters-managed
  installed projection is a managed ownership subtype inside the
  machine-installed layer, not a fourth layer. Resolve candidates with PEP 440
  ordering, declared compatible intervals, explicit prerelease acceptance,
  exact version plus content-hash identity, schema, origin, dependencies,
  native validator, and ResearchGuard identity. Use a newer compatible local
  skill as an overlay, use a newer bundled skill internally, update only a
  Matters-managed installed projection transactionally, leave externally
  managed installs unchanged, and visibly block same-version hash conflicts or
  the absence of any validated compatible version. Any manifest, runtime,
  dependency, validator, or ResearchGuard identity change invalidates the
  resolved active view.
- **BREAKING** Replace the normal human-review success path with autonomous
  typed AI findings, deterministic validation, and automatic dispatch to the
  unique original C4-C9/C12 owner. Keep source-only, candidate,
  uncertainty-preserved, not-applicable, blocked, admitted,
  insufficient-evidence, and no-delta outcomes distinct. Users may inspect and
  correct results after publication, but confirmation is not a prerequisite
  for first modeling.
- Persist private catalog, immutable source content, revisions, dependency
  edges, analysis runs, checkpoints, and recomputation work under the external
  `MATTERS_HOME` root so discovery and analysis resume safely after restart.
- Make correction, supersession, deletion, and authorization revocation append
  history, invalidate dependents, and require terminal original-owner
  recomputation before a fresh projection is published.
- Provide one runnable CLI/API/MCP/desktop-UI path for source-universe
  authorization, inventory progress, autonomous analysis, object browsing,
  evidence inspection, optional correction, revocation, deletion, recovery,
  and English-default, Chinese-selectable, locale-extensible revision-aware
  status. Persist every user-visible AI-authored value in the required English
  and `zh-CN` forms before publication.
- Reuse the frozen Databank UI handoff as the Matters visual authority except
  for the product logo. Render a left-filter/right-card object browser with
  user-selectable, persisted `standard` and `compact` card densities that share
  one semantic and visual revision. Density changes presentation only.
- Automatically select one representative visual for every admitted Matter
  from current allowlisted photos, existing images, attachments, embedded
  images, or safely rendered document pages. AI must select when an eligible
  candidate exists; a deterministic stable selector handles AI failure or
  ties; zero eligible candidates produce an honest neutral placeholder.
  Internet image search and fabricated decorative evidence images are
  prohibited.
- Start a bounded durable background worker with the desktop application so
  discovery, reconciliation, analysis, original-owner dispatch, localization,
  visual selection, and projection continue without user intervention while
  the application is running.
- Use fully synthetic safety and conformance cases first, then source-type
  private canaries, and finally a progressive full first run over the
  authorized source universe. Real data proves usefulness but never replaces
  synthetic reproducibility and privacy tests.
- Keep the generic Jira adapter dormant as an optional future connector. Jira
  and Atlassian Rovo are not v0.2 runtime, installation, first-run, acceptance,
  or release dependencies.
- Require frozen model, code, test, privacy, package, three-layer Skill Pack,
  portable ResearchGuard currentness, installed-package, and local-Git evidence
  before the final v0.2 complete-release claim is accepted. Missing
  ResearchGuard currentness leaves a blocked local candidate. Remote GitHub
  publication remains a separate decision and can contain only approved public
  source and synthetic materials.

## Capabilities

### New Capabilities

- `authorization-coverage`: Explicit source-universe grants, hard exclusions,
  candidate-scope freeze, versioned tracking policy, staged discovery, durable
  coverage cursors, AI-autonomous reversible triage, per-item terminal
  dispositions, `ObjectCoverageLedger`, access gaps, `cloud_placeholder`
  handling, and revocation.
- `source-provenance`: Immutable local-file, document, image, Gmail, attachment,
  and cloud-occurrence identities, versions, persistence, deduplication,
  inventory snapshots, freshness invalidation, incremental change sets,
  supersession, deletion, tombstones, and restart recovery.
- `evidence-qualification`: Precise field, passage, line, character, page,
  sheet/cell, message/thread, attachment, image-region, OCR, and metadata
  anchors with bounded assertion candidates.
- `identity-resolution`: Evidence-scoped person/entity candidates, identity
  assertions, and Matter roles without unsafe same-name, same-address, or
  same-face merging.
- `temporal-trace`: Typed events, modality, record/event/file/EXIF/mail time,
  supersession, contradiction, and temporal gaps.
- `matter-admission`: Source-only, candidate, admitted Matter,
  uncertainty-preserved, not-applicable, no-delta, blocked, and unsupported
  admission outcomes without a normal confirmation gate.
- `lifecycle-board-state`: Evidence-licensed multi-axis lifecycle state and
  canonical board placement under partial source coverage.
- `open-loop-blocking`: Requests, dependencies, waiting targets, closure
  conditions, and partial versus full blocking across source types.
- `outcomes-reopen`: Completion, cancellation, abandonment, conflict, and
  reopening based on explicit criteria and later source revisions.
- `correction-invalidation`: Durable append-only correction, revocation,
  deletion, dependent invalidation, original-owner recomputation, revision
  graphs, and restart recovery.
- `guard-prediction-boundary`: Versioned text and multimodal AI/local-skill work
  packages, scope-triage decisions, findings, gaps, proposals, receipts,
  failures, forecasts, typed automatic original-owner dispatch, and exact input
  disposition accounting that cannot expand authorization or silently mutate
  unrelated canonical state.
- `bundled-skill-runtime-and-maintenance`: Immutable app-local consumer Skill
  Pack inventory, ResearchGuard integration gate, compatibility-aware active
  view resolution, Matters-managed installed projection synchronization,
  rollback, native validation, self-maintenance procedures, and explicit
  separation from canonical Matter state and author-side SkillGuard control
  artifacts.
- `bilingual-projection-ui`: Runnable English-default and Chinese-selectable
  desktop object browser, source catalog, coverage progress, standard/compact
  cards, automatic representative visuals, Matter detail, evidence,
  explanation, recovery, optional correction, and privacy interactions.
  User-visible AI-authored values are stored as locale-keyed text bound to one
  semantic revision; required English and `zh-CN` values are validated now and
  the locale registry permits later languages without creating another fact
  authority.
- `privacy-release-boundary`: Public/private/vault separation, private-derived
  artifact controls, portable public evidence, clean packaging,
  source/install/Git identity synchronization, and frozen release verification.

### Modified Capabilities

None. The change remains the initial unarchived specification authority for
the repository; its fourteen capability files form one initial change.

## Impact

The change governs the initial OpenSpec authority, plane-partitioned Behavior
Commitment Ledger, M0 plus C1-C12 FlowGuard owners and nested source/extractor
leaves, model-derived code and test contracts, source-type synthetic fixtures,
private catalog/SQLite/blob persistence under `MATTERS_HOME`, filesystem and
Gmail discovery adapters, scope inventory/triage and incremental freshness,
document/image extraction and safe visual derivatives, an injectable
agent-operation runner, autonomous dispatcher and background worker, the
abstract ResearchOperation boundary, an app-local consumer Skill Pack and
active skill view, the shared CLI/HTTP/MCP/desktop-UI service path, privacy
controls, local package and managed skill-projection installation, and local
release gates.

The existing generic Jira adapter remains source-only and disabled. Gmail and
private local data are required for the user's private first-run acceptance,
but never for clean-clone, package, installation, or public release
verification. No Jira login, Rovo installation, automatic external action,
public license choice, or remote GitHub publication is required for v0.2.
