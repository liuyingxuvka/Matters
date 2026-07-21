## Why

The first Matters user has authorized the product to organize all user-owned
content that it can legitimately reach, including local files, documents,
photos, Gmail, and cloud-backed user folders. The current plan covers only
pasted text, individually selected text files, and a small Gmail sample, so it
cannot perform or honestly report the requested first private run.

The next Matters release therefore needs a source-in-place, AI-autonomous
source-universe workflow
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
- **BREAKING** Keep user originals in their existing filesystem, Gmail, and
  provider locations instead of copying complete files, mail bodies, or source
  images into Matters by default. Persist stable provider locators, occurrence
  identity, content/metadata fingerprints, exact anchor coordinates, and
  derived understanding. Raw bytes or text used during extraction are
  short-lived private work material with explicit commit cleanup, TTL, quota,
  and garbage-collection ownership. If an original later moves, is deleted, or
  becomes unreachable, preserve the derived model and provenance but mark the
  source unavailable rather than pretending it can still be inspected.
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
  semantic depth, localization, meaningful-clue/summary freshness, generated
  hero disposition when applicable, supplemental-information freshness, UI
  projection, retry, and terminal reason so one scan can report the exact gap
  between registration and current UI-ready completion.
- Model useful work at several semantic scales instead of flattening every
  source or small event into a top-level card. A large root Matter such as a
  trip or job search MAY contain child Matters with independent goals, state,
  outcome criteria, and next steps; child Matters MAY contain further child
  Matters, lightweight WorkItems/Actions, Events, OpenLoops, and exact
  Source/Evidence support. Each Matter has at most one current primary
  containment parent, containment is acyclic, and ordinary cross-links remain
  Related Matters rather than becoming a second parent.
- Give Matter identity a stable semantic key independent from the changing set
  of supporting SourceVersions. Reparent, split, merge, correction, or new
  evidence SHALL preserve revision history, invalidate both old and new
  ancestor chains, and recompute hierarchy summaries before a fresh projection
  is published.
- Keep credentials, secrets, browser/session stores, operating-system and
  application internals, caches, dependency/build outputs, VCS internals,
  executable launch, unsafe serialized models, uncontrolled archive expansion,
  and unbounded link/junction traversal outside the content-reading boundary.
- Support local user-authored text and declared safe exports/downloads,
  document/page anchors, spreadsheet cell/range anchors, image metadata and
  region/OCR anchors, and Gmail message/thread/attachment anchors. Program
  source and scripts, software-tree configuration, application databases/logs/
  state, caches, dependency/build outputs, executables, unsafe serialized
  models, and unknown machine formats terminate under deterministic policy
  before content analysis or AI. Unsupported or unavailable user-content
  formats remain visible gaps; the product never fabricates equivalent
  analysis.
- Cover the authorized Gmail account through a read-only product source path.
  Inbox, Sent, and archived non-Spam/non-Trash mail are progressively paged and
  dispositioned; Spam and Trash are `hard_excluded` or `metadata_only` by
  policy.
  Reading never implies permission to send, delete, archive, or change labels.
- Establish physically separate public source, private runtime, and private
  evaluation domains. Raw content, paths, private metadata, excerpts, hashes,
  embeddings, screenshots, logs, and derived user models remain private and
  cannot cross the publication gate.
- Register immutable source observations and precise locator-bound evidence
  anchors before deriving people, events, matters, open loops, or outcomes.
  Source versions preserve what was observed and where it was observed without
  default retention of the complete original body. Cloud placeholders, missing
  originals, and files that change during reads receive explicit non-success
  dispositions.
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
- Keep product execution model-agnostic. Matters declares capability roles
  (`maintenance_orchestrator`, `deterministic_preprocessor`,
  `low_cost_annotator`, `ambiguity_resolver`, `matter_modeler`,
  `hero_image_generator`, and `consistency_reviewer`) and
  validates their input/output contracts; a machine-local Codex execution
  profile maps those roles to currently available models and reasoning levels.
  The first-user profile may map low-cost annotation to `gpt-5.6-luna` at low
  reasoning, but neither that model name nor any provider becomes canonical
  product state or a release dependency. Matters owns no OpenAI API key and
  has no direct-API fallback.
- Allow one Codex-hosted daily maintenance schedule to invoke the same bounded,
  resumable service path. Its primary task uses the strongest compatible
  reasoning profile available to plan, reconcile, and judge the run, and may
  delegate deterministic or low-cost annotation batches to cheaper replaceable
  background profiles. Every delegation remains bounded by a typed work
  package and returns through the same original-owner path. The schedule
  records private execution-profile and run receipts, performs no mailbox
  mutation or outbound action, and never owns unattended final model,
  full-test, install, Git, tag, or release verification.
- Ship a versioned app-local consumer Skill Pack with Matters so its own
  ingestion, inventory reconciliation, freshness, model-depth,
  human-correction, model-miss, skill-runtime, research-orchestration,
  semantic-understanding, autonomous-maintenance, and hero-image-generation
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
- Persist private catalog locators, immutable observation/fingerprint
  revisions, derived understanding, dependency edges, analysis receipts,
  checkpoints, reclaimable presentation caches, and recomputation work under
  the external `MATTERS_HOME` root so discovery and analysis resume safely
  after restart without duplicating the user's originals.
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
  for the product logo and the explicitly approved tighter brand-to-search and
  search-to-navigation spacing. Render a left-filter/right-card object browser with
  user-selectable, persisted `standard` and `compact` card densities that share
  one semantic and visual revision. Density changes presentation only.
- Show only root Matters in the ordinary card catalog. The Sub-matters section
  renders only the complete bounded Matter containment hierarchy plus typed
  Matter-to-Matter relations as an operable graph with pan, zoom, reset,
  minimap, keyboard focus, and bounded continuation. WorkItems, Events,
  sources, and inferences remain itemized facts inside the owning Matter's
  quick view instead of becoming graph boxes. The graph has no per-node
  collapse/expand button. Selecting a Matter node opens one reusable,
  single-layer quick-view dialog over the current root detail. The quick view
  contains a human summary/current-state region, an itemized fact/event/work
  region, and one flat files/information region; it never navigates to another
  Matter detail, opens a second modal, or recursively nests card pages. Search
  MAY find a descendant but SHALL open the owning root and focus that Matter
  node. Parent timelines summarize only current important descendant
  milestones and deduplicate logical events across source revisions.
- Give the detail reader exactly eight ordinary top-level sections: Overview,
  Sub-matters, Timeline, People, Related Matters, Files & information, Images,
  and AI supplemental information. Overview contains only the generated hero,
  a human-readable project narrative, lifecycle state, and Start date; it does
  not repeat source/evidence counters, Actions, or OpenLoops. WorkItems,
  events, waits, and outcomes are itemized in the relevant Matter quick view
  and Timeline rather than promoted to peer panels. Real related photos or
  already-existing meaningful visual images remain in Images as
  evidence-linked gallery content; mail, text, office/PDF, code, terminal, and
  generic document screenshots do not. AI supplemental information is clearly
  labeled, refreshable background context rather than source evidence.
- Make lifecycle state a single human state vocabulary independent from
  evidence modality or processing status. In the Sub-matters graph, planned
  uses green, in progress uses red, and completed uses blue together with text
  or icons; internal values such as `current` or `reported` never appear as a
  second lifecycle label.
- Keep the catalog coverage control visually single-level: one small status
  dot and one label. Its on-demand view drills from SourceGroup to first
  incomplete stage, object, owner, failure reason, freshness, and UI
  reachability. Green requires current inventory, terminal dispositions,
  source-group reconciliation, admitted-Matter semantic/hierarchy/summary/UI
  currentness, and no blockers; blue requires measured forward progress; red
  covers stale, blocked, missing-registration, inconsistent, or unreachable
  states.
- Order every filtered, searched, localized, or density-adjusted root catalog
  by the latest meaningful clue. A material child clue propagates to its
  ancestors; background scans, retries, technical receipts, and wording-only
  refreshes do not. Start time remains a separate explicit filter and is never
  substituted for this dynamic ordering.
- Automatically generate one presentation-only hero image for every root
  Matter after its semantic identity, merge, and current hierarchy are stable
  enough. Heroes use a photorealistic documentary/editorial photographic
  style with Matter-specific physical setting, objects, equipment, or activity
  that remains recognizable without a caption, not interchangeable
  people-at-computer scenes, abstract diagrams,
  collage art, mail/document screenshots, or symbolic illustrations. The
  generated hero is never evidence, never replaces the real Images gallery,
  uses one shared image with bilingual alt text, and defaults to no literal
  text, logos, private identifiers, or identifiable real users. A failed or
  pending generation produces a temporary neutral placeholder and bounded
  retry, not a real-image fallback or second cover authority. Descendant
  Matters, WorkItems, Events, sources, and quick-view nodes do not receive
  independent heroes.
- Maintain one derived personal Situation/World Model projection across current
  sources, people, times, goals, Matters, WorkItems, Events, expected
  trajectories, and gaps. It SHALL distinguish confirmed observations,
  reported/planned facts, and AI-inferred best-current interpretations. AI may
  infer likely outcomes such as a past trip leg having occurred when the
  licensed evidence and expected trajectory support that reading, but the UI
  labels the inference, confidence, alternatives, and contradictory or missing
  evidence; inference never masquerades as a confirmed observation.
- Start a bounded durable background worker with the desktop application so
  discovery, reconciliation, analysis, original-owner dispatch, localization,
  material-clue/summary refresh, generated-hero work, supplemental information,
  and projection continue without user intervention while
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
  and cloud observation identities; source-in-place locators and fingerprints;
  transient content lifecycle; derived-state persistence; bounded caches and
  garbage collection; inventory snapshots, freshness invalidation, incremental
  change sets, supersession, deletion, tombstones, and restart recovery.
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
  admission outcomes without a normal confirmation gate; stable semantic
  Matter identity; root/child containment; WorkItem/Event boundaries; reparent,
  split, merge, and cycle prevention.
- `lifecycle-board-state`: Evidence-licensed multi-axis lifecycle state and
  canonical board placement under partial source coverage, with independent
  child state and evidence-bounded parent summaries rather than mechanical
  rollup.
- `open-loop-blocking`: Requests, dependencies, waiting targets, closure
  conditions, partial versus full blocking across source types, and explicit
  critical-child propagation.
- `outcomes-reopen`: Completion, cancellation, abandonment, conflict, and
  reopening based on explicit criteria, required versus optional children, and
  later source or descendant revisions.
- `correction-invalidation`: Durable append-only correction, revocation,
  deletion, dependent invalidation, original-owner recomputation, revision
  graphs, old/new ancestor-chain invalidation, hierarchy recomputation, and
  restart recovery.
- `guard-prediction-boundary`: Versioned text and multimodal AI/local-skill work
  packages, scope-triage decisions, findings, gaps, proposals, receipts,
  failures, forecasts, typed automatic original-owner dispatch, and exact input
  disposition accounting; model-agnostic capability roles; a replaceable local
  Codex execution profile; a derived personal Situation/World Model with
  explicit observed/reported/planned/inferred modalities; and bounded daily
  maintenance that cannot expand authorization, require an app-owned API key,
  or silently mutate unrelated canonical state.
- `bundled-skill-runtime-and-maintenance`: Immutable app-local consumer Skill
  Pack inventory, ResearchGuard integration gate, compatibility-aware active
  view resolution, Matters-managed installed projection synchronization,
  hero-generation procedure, rollback, native validation, self-maintenance
  procedures, and explicit
  separation from canonical Matter state and author-side SkillGuard control
  artifacts.
- `bilingual-projection-ui`: Runnable English-default and Chinese-selectable
  desktop object browser, source catalog, coverage progress, standard/compact
  root cards ordered by latest meaningful clue, generated presentation-only
  photorealistic root heroes, summary-free cards, a multi-depth interactive
  Sub-matters graph, one reusable single-layer node quick view, grouped
  files/information locations, eight-section Matter detail, real-image gallery,
  AI supplemental information, evidence, explanation, recovery, optional
  correction, and privacy interactions.
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
private catalog/SQLite pointer-and-derived-state persistence under
`MATTERS_HOME`, filesystem and
Gmail discovery adapters, scope inventory/triage and incremental freshness,
 document/image extraction and safe evidence derivatives, private generated
 Matter heroes, an injectable
 agent-operation runner, a model-agnostic Codex role router, a Codex-hosted
 daily-maintenance schedule, autonomous dispatcher and background worker, the
abstract ResearchOperation boundary, an app-local consumer Skill Pack and
active skill view, the shared CLI/HTTP/MCP/desktop-UI service path, privacy
controls, local package and managed skill-projection installation, and local
release gates.

The existing generic Jira adapter remains source-only and disabled. Gmail and
private local data are required for the user's private first-run acceptance,
but never for clean-clone, package, installation, or public release
verification. No Jira login, Rovo installation, or automatic external action
is required for the generic release. The user has now authorized a public
GitHub software release before the private first run completes. The remote is
frozen as `liuyingxuvka/Matters`, visibility is public, the license is MIT, and
only the approved generic public-safe inventory may be published. The license
change does not include private data or authorize disclosure of user material.

The release sequence therefore has three ordered acceptance domains. First,
v0.3.1 carries the current generic hierarchy, people, timeline, summary,
inference/correction, bilingual object browser, desktop shell, MCP, bundled
skills, privacy, candidate package, and isolated anonymous-install behavior
without private content; this generic candidate is published before replacing
the user's active local installation. Second, the published wheel and Windows
desktop ZIP are downloaded and installed as an ordinary consumer to verify the
real release path. Third, the private Gmail/local/Codex first run continues against that
released contract. Any reusable product defects found there are reproduced
with public-safe synthetic evidence and may be accumulated into a later patch
release; private data and private completion claims never enter the generic
release.

The hierarchy change affects C5-C12/M0, stable Matter identity and persistence,
ancestor indexes, coverage-ledger stages, autonomous-maintenance work packages,
object-browser APIs, search/filter projections, detail navigation, bilingual
copy, bundled skills, synthetic hierarchy families, private first-run
acceptance, candidate-package identities, post-release consumer-install
identities, and the next public Git release.

## Superseding AI Access and Guard Distribution Decision

This section records a deliberate change from the earlier plan. Matters SHALL
NOT vendor, copy, or privately fork FlowGuard, WorldGuard, ResearchGuard,
SourceGuard, TraceGuard, LogicGuard, SkillGuard, or another Guard-family skill.
Those projects remain independently installed, versioned, validated, and
maintained by their own authorities. Matters depends on the external
ResearchGuard contract as the sole real research provider, but ordinary Matter
catalog, history, graph, World Model, correction, and feedback access remains
available when ResearchGuard is unavailable; only the research-dependent part
and any completeness claim stay visibly blocked.

The exactly eleven Matters-owned maintenance skills remain an immutable
app-local implementation pack. They are not Guard-family distributions and do
not become machine-global Codex skills. One separate public `matters` gateway
skill/plugin MAY be installed into Codex so an AI has one stable entrypoint for
the bounded model map, current situation, history, prediction feedback, user
observations, explicit corrections, and model-miss reporting. That gateway is
an adapter over MatterService/MCP, not a twelfth maintenance skill and not a
canonical writer.

The earlier compatible machine-global overlay plan for the eleven internal
skills is superseded. Internal execution uses the exact hash-bound app-bundled
pack for the running Matters release. A separate external Guard dependency is
resolved and checked only through its own portable identity/currentness
contract; it never overlays or replaces a Matters-owned internal skill.

Routine maintenance has one service path. When a user asks a compatible AI
host to install and use Matters, that installing AI SHALL connect the public
gateway, verify the package and internal Skill Pack, create or repair exactly
one daily schedule, run the initial bounded maintenance cycle, and open the
desktop view. The schedule is a host-owned adapter over the shared A2 path and
never a second workflow or truth owner. Installation permission does not widen
source-read authorization. If the host cannot manage schedules, setup remains
visibly blocked rather than silently omitting recurrence or delegating the
task back to the human user. During setup, the user supplies the allowed
folders, mailboxes, and other information-source scopes to the installing AI;
no personal investigation scope is hard-coded into the software or release.
