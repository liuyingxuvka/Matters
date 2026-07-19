## ADDED Requirements

### Requirement: English and Chinese share one semantic revision
The system SHALL persist every user-visible AI-authored value as locale-keyed
text with non-empty `en` and `zh-CN` entries bound to the same canonical
revision, evidence references, and semantic labels.

#### Scenario: Both projections are current
- **WHEN** every required user-visible AI-authored value has current `en` and `zh-CN` entries that reference the same semantic revision and pass equivalence checks
- **THEN** the system SHALL make both available to the UI

#### Scenario: Language projections conflict
- **WHEN** one projection says blocked and the other says waiting for the same revision
- **THEN** publication SHALL be blocked and the conflict SHALL be visible for repair

#### Scenario: A required localized value is missing
- **WHEN** a user-visible AI-authored value has an empty, missing, stale, or unregistered required locale entry
- **THEN** publication for that locale SHALL be blocked with a visible localization gap and SHALL NOT silently substitute another language

### Requirement: English is the default selectable locale
The first local launch SHALL use `en`. The UI SHALL allow the user to select
`zh-CN`, SHALL persist that preference locally, and SHALL apply the selection
without changing semantic revision, task state, selected evidence, or focus
ownership.

#### Scenario: First launch has no language preference
- **WHEN** the application starts without a previously stored valid locale
- **THEN** the UI SHALL render the current English projection and mark English as selected

#### Scenario: User selects Chinese
- **WHEN** the user activates the `zh-CN` language control
- **THEN** the UI SHALL render the `zh-CN` values from the same semantic revision, persist the preference locally, and preserve the current task and focus context

### Requirement: The locale registry is extensible
The system SHALL expose one locale registry with default locale `en`, required
v0.2 locales `en` and `zh-CN`, BCP 47 identifiers, display names, direction,
and publication status. CLI, HTTP, MCP, and UI projections SHALL consume that
registry rather than define independent language lists.

#### Scenario: A future locale is registered
- **WHEN** a later release registers a new BCP 47 locale and supplies complete validated localized values
- **THEN** the locale SHALL become selectable without changing canonical semantic meaning or creating a new state writer

#### Scenario: An unsupported locale is requested
- **WHEN** a caller requests a locale that is not current in the registry
- **THEN** the request SHALL fail visibly with the available locales and SHALL NOT silently fall back

### Requirement: Static interface copy is localized
Every visible static UI label, instruction, action, empty state, loading state,
error, and recovery message SHALL have current `en` and `zh-CN` catalog entries.

#### Scenario: The UI changes language during an error
- **WHEN** the user changes language while an error or recovery state is visible
- **THEN** the interface copy SHALL switch language while the underlying error identity, retry owner, and recovery state remain unchanged

### Requirement: UI is a projection
The UI SHALL consume canonical projections and SHALL NOT infer or write Matter,
lifecycle, OpenLoop, outcome, identity, evidence, or admission state.

#### Scenario: Card renders lifecycle state
- **WHEN** a board card is shown
- **THEN** its state, rationale, and evidence link SHALL come from one current projection revision

### Requirement: Every action has an owned behavior chain
Every reachable UI control SHALL map to an event, owner, function, resulting UI
update, and evidence.

#### Scenario: User submits a correction
- **WHEN** the correction control is activated with valid input
- **THEN** the UI SHALL send the correction to C10 and render only the resulting current projection

### Requirement: Large catalogs render incrementally
The UI SHALL keep every current source and Matter/history item reachable while limiting
both the HTTP payload and each DOM render to a bounded window. The private
runtime SHALL maintain a paged catalog projection outside Git so the ordinary
UI never has to materialize the full private inventory. Moving to the next or
previous window SHALL preserve the semantic revision, selected locale, user
task, and keyboard focus.

#### Scenario: A private first run contains thousands of rows
- **WHEN** the current projection contains more rows than one UI render window
- **THEN** the HTTP projection and UI SHALL return and render only the first bounded window, show the total and remaining counts, provide accessible next/previous controls, and SHALL NOT serialize or insert the entire catalog at once

#### Scenario: Matter cards resolve coverage relations in a large private ledger
- **WHEN** catalog cards or one detail view need source counts, related Matters, visuals, or coverage-backed status after a large first-run inventory
- **THEN** the private runtime SHALL resolve all visible Matter-to-coverage relations through one current indexed batch and SHALL NOT transfer or parse the full ObjectCoverageLedger once per card or related candidate

#### Scenario: The user moves between catalog windows
- **WHEN** the user requests the next or previous bounded window
- **THEN** every current row SHALL remain reachable, the prior window SHALL remain recoverable, no stale response SHALL replace a newer projection, and focus SHALL move to a stable visible target rather than a control that became hidden

### Requirement: Conflicts and gaps are explainable
The UI SHALL expose evidence, uncertainty, conflicts, and correction entry at
an appropriate on-demand level without revealing internal or private
identifiers by default.

#### Scenario: Matter contains an uncertain inference
- **WHEN** a current decision preserves low confidence, alternatives, or conflicting evidence
- **THEN** the object view SHALL show the best current result and SHALL let the user reveal the bounded reason and referenced evidence without requiring approval

### Requirement: The local v0.2 workflow is operable
The UI SHALL provide reachable controls and visible feedback for pasted input,
exact file selection, authorization status, automatic analysis, unavailable or
failed analysis, object browsing, evidence inspection, optional correction,
revocation, deletion, recomputation waiting, retry, and English-default/
`zh-CN` projection switching through the shared locale registry. It SHALL NOT
present per-item confirmation, rejection, or defer controls as a prerequisite
for first modeling.

#### Scenario: User analyzes pasted text
- **WHEN** a user submits non-empty pasted text under the active authorization
- **THEN** the UI SHALL register the source, automatically continue analysis and original-owner dispatch, and render the resulting object, source-only result, or bounded failure state

#### Scenario: User selects a local file
- **WHEN** a user selects one supported TXT or Markdown file
- **THEN** the UI SHALL show the exact file authorization before reading and SHALL NOT display or inspect sibling files

#### Scenario: First-run roots and Gmail scope are active
- **WHEN** the current authorization supplies user-content roots or Gmail read scope
- **THEN** the UI SHALL show the frozen scope, hard exclusions, metadata inventory progress, and automatic `tracked`/`not_tracked`/`hard_excluded`/`metadata_only`/`blocked` counts while broad analysis continues

#### Scenario: AI triage is uncertain
- **WHEN** a scope-triage result is uncertain, stale, or conflicts with a user override
- **THEN** the UI SHALL display the current reversible disposition, uncertainty, and automatic recomputation status and MAY expose optional `track`, `do_not_track`, and `restore` corrections without revealing internal paths by default

#### Scenario: User changes a source tracking disposition
- **WHEN** a user activates `track`, `do_not_track`, or `restore` for one occurrence
- **THEN** the UI SHALL send that source-level intent to C1, preserve the previous revision, and render the resulting current disposition and affected-work status

#### Scenario: A later scan detects changes
- **WHEN** an inventory revision contains added, modified, moved, or deleted occurrences
- **THEN** the UI SHALL show changed-item freshness and incremental reprocessing status without presenting stale classifications as current

#### Scenario: Analysis is unavailable
- **WHEN** no configured agent-operation runner can satisfy the requested analysis
- **THEN** the UI SHALL show an actionable unavailable or retrying state, preserve the source and completed stages, and SHALL NOT ask the user to approve a fabricated substitute

#### Scenario: Automatic owner dispatch completes
- **WHEN** a current typed understanding result passes validation
- **THEN** the service SHALL dispatch it to the declared original owner without a user action and the UI SHALL render only the resulting current owner decision

#### Scenario: Object page advances
- **WHEN** the user requests the next or previous bounded Matter or history page
- **THEN** the UI SHALL show a loading state, accept only a response with the current projection revision, preserve locale and focus, and make every object reachable without unbounded DOM growth

#### Scenario: Object page becomes stale or fails
- **WHEN** a source change, owner update, correction, or older response changes the active projection revision
- **THEN** the UI SHALL discard stale output, preserve the current visible window on failure, expose retry, and SHALL NOT apply an action token or payload from an older revision

#### Scenario: Correction recomputation is pending
- **WHEN** a submitted correction has outstanding owner recomputation
- **THEN** the UI SHALL show pending owner status and SHALL NOT present the old or provisional state as a new canonical revision

### Requirement: Evidence detail is user-on-demand
Machine-local paths, internal ids, raw receipts, and debug metadata SHALL remain
internal, while user-relevant evidence excerpts, uncertainty, conflicts, and
revision history SHALL be revealed through accessible on-demand controls.

#### Scenario: User reveals evidence
- **WHEN** a keyboard or pointer user activates the evidence control
- **THEN** the UI SHALL reveal the admitted evidence detail and provide an operable close or collapse path

#### Scenario: Private Gmail evidence is revealed
- **WHEN** a user opens evidence originating from the progressive Gmail first run
- **THEN** the UI SHALL show only the minimized excerpt required for the current claim and SHALL keep addresses, transport links, private codes, and internal connector identifiers hidden

### Requirement: Semantic depth meaning is visible
The UI SHALL display `not_assessed`, `partial`, `sufficient`, `blocked`, or
`stale` semantic depth for the exact occurrence and revision together with
unmet criteria, freshness identity, and the next permitted action. It SHALL NOT
present `partial`, `blocked`, or `stale` as complete modeling.

#### Scenario: Semantic depth is partial
- **WHEN** an occurrence has current useful analysis but one or more required criteria remain unresolved
- **THEN** the UI SHALL show `partial`, the unmet criteria, and the automatic analysis or owner stage that can advance it

#### Scenario: Semantic depth is stale
- **WHEN** a source, policy, anchor, provider, operation, dependency, validator, or user decision changes after the depth assessment
- **THEN** the UI SHALL show `stale` and SHALL NOT display the prior depth result as current

#### Scenario: ResearchGuard is not current
- **WHEN** semantic depth requires ResearchGuard but its portable currentness gate is not current
- **THEN** the UI SHALL show `blocked`, preserve inventory and optional evidence/correction access, and state that final v0.2 complete-release remains blocked

### Requirement: UI state is recoverable and accessible
The local UI SHALL define initial, loading, success, empty, validation-error,
analysis-unavailable, analysis-failed, recompute-pending, blocked, and recovery
states with keyboard focus behavior.

#### Scenario: Input validation fails
- **WHEN** a user submits empty text or an unsupported file
- **THEN** the UI SHALL focus the bounded error, preserve recoverable input, and keep unrelated controls operable

#### Scenario: User closes an on-demand panel
- **WHEN** evidence detail is open and the user presses Escape or activates close
- **THEN** the panel SHALL close and focus SHALL return to its reveal control

### Requirement: The desktop UI is a Matter object browser
The primary v0.2 desktop surface SHALL reuse the frozen Databank handoff's
color, typography, spacing, left navigation, card, and detail-dialog design,
with only the Matters brand/logo substituted. The left region SHALL filter the
right Matter-card catalog by lifecycle state, time, people, modeled
topic/type, and source type. Matter detail SHALL expose Overview, Timeline,
People, Actions and open loops, Related Matters, Images, Files and messages,
and Evidence and change history with internal identities hidden.

#### Scenario: User opens the application
- **WHEN** the Windows desktop application launches with a current projection
- **THEN** it SHALL open the object browser in English by default, render the left filters and right card catalog using the frozen design language, and SHALL NOT open an AI review queue

#### Scenario: User opens one Matter
- **WHEN** the user activates a Matter card
- **THEN** the detail dialog SHALL open the current Matter revision, preserve the browser filters and scroll state, and provide an accessible return path

#### Scenario: Matter card content is projected
- **WHEN** a Matter card is visible in either density
- **THEN** it SHALL show the current representative hero or neutral placeholder, primary lifecycle status, localized title, localized one-line summary, last-or-next significant time, and key people from one current projection revision
- **AND** standard density SHALL also show exactly the current event count, people count, and source count as its three secondary metrics
- **AND** compact density MAY hide only those three secondary metrics while retaining the same hero or placeholder, primary status, title, summary, significant time, and key people
- **AND** changing density SHALL NOT request modeling, change canonical state, or substitute content from another projection revision

#### Scenario: User searches the Matter catalog
- **WHEN** the user enters or clears a catalog search
- **THEN** the UI SHALL search the current localized Matter projection and update only the bounded result window without changing the persisted density, active filters, locale, selected Matter, or pre-search focus and scroll anchor
- **AND** a stale search response SHALL NOT replace a newer query result or projection revision
- **AND** clearing or leaving search SHALL restore the exact pre-search density, filters, locale, selected Matter, focus target, and scroll anchor rather than resetting the object browser
- **AND** entering, updating, clearing, or leaving search SHALL perform no canonical write and SHALL NOT request modeling or user confirmation

#### Scenario: Timeline is rendered for people
- **WHEN** the Timeline section is visible
- **THEN** each event SHALL be expressed as a localized human-readable sentence from the current semantic revision rather than an internal state label
- **AND** the source-record time SHALL be labeled separately from the claimed, planned, or observed occurrence time whenever either is known, and the UI SHALL NOT coalesce one into the other
- **AND** every event SHALL visibly distinguish exactly one current modality of `planned`, `reported`, `observed`, or `inferred`, and planned or reported content SHALL NOT be worded as an observed occurrence
- **AND** the current best-supported interpretation SHALL be stated while conflicting claims, alternative times or meanings, material uncertainty, and their source relationships remain visible without requiring user confirmation

### Requirement: Standard and compact are independent display densities
The object browser SHALL provide a persisted `standard`/`compact` density
preference independent of responsive viewport mode. Both densities SHALL use
the same Matter order, filter, semantic revision, status, representative
visual, selected object, and locale. Compact MAY hide only declared
low-priority metrics.

#### Scenario: User selects compact density
- **WHEN** the user activates the compact switch
- **THEN** the grid SHALL render the handoff's smaller compact cards, retain hero/title/status, preserve focus/filter/scroll/locale, and SHALL perform no canonical write or modeling request

#### Scenario: Window size changes
- **WHEN** the desktop viewport crosses a responsive breakpoint
- **THEN** responsive columns MAY change but the persisted standard/compact preference SHALL remain unchanged

#### Scenario: Catalog has one item
- **WHEN** only one Matter card is current
- **THEN** the card SHALL remain aligned to the top of the content region and SHALL NOT stretch or move to the vertical center

### Requirement: Every Matter has one current representative-visual disposition
Each admitted Matter SHALL expose exactly one current representative-visual
disposition: a current authorized related visual asset or a neutral
placeholder. Eligible visual assets SHALL be current photos, existing images,
attachments, embedded images, or offline deterministic document/page/slide/
sheet previews tied to an exact SourceVersion and anchor. The system SHALL
filter safety and permission before AI selection, SHALL select automatically
when eligible candidates exist, and SHALL use a stable deterministic selector
when AI output is unavailable, invalid, or tied.

#### Scenario: Eligible related images exist
- **WHEN** the current Matter has one or more authorized, safe, current, precisely anchored visual candidates
- **THEN** the system SHALL automatically select one, publish bilingual alt text and a bounded reason, and render the same visual decision in standard, compact, and detail views without user confirmation

#### Scenario: No eligible visual exists
- **WHEN** every candidate is absent, stale, unrelated, unsafe, denied, unreadable, or unsupported
- **THEN** the system SHALL render a neutral placeholder and SHALL NOT search the Internet or generate a decorative image that could be mistaken for evidence

#### Scenario: User later pins a cover
- **WHEN** the user optionally chooses an eligible visual through `Change cover`
- **THEN** the user-pinned decision SHALL remain current until it is unpinned or becomes unsafe, unauthorized, deleted, or stale

### Requirement: Desktop launch starts bounded autonomous maintenance
The Windows desktop application SHALL start the local service and one durable,
bounded worker that resumes authorized discovery, reconciliation, analysis,
original-owner dispatch, localization, visual selection, and projection while
the application is running. Normal completion SHALL NOT require user
intervention. Routine work SHALL stop cleanly on application shutdown and
resume from durable checkpoints on the next launch.

#### Scenario: Application resumes pending work
- **WHEN** the desktop application starts with current authorization and pending or stale coverage-ledger stages
- **THEN** the worker SHALL resume the next valid stage without duplicating completed work or asking the user to approve ordinary AI decisions

#### Scenario: One item is genuinely blocked
- **WHEN** an occurrence cannot progress because of revoked authorization, hard safety policy, corruption, encryption, unsupported rendering, or an exhausted required runtime retry
- **THEN** the worker SHALL record the exact blocked stage, continue unrelated items, and expose the exception without converting it into a global confirmation queue
