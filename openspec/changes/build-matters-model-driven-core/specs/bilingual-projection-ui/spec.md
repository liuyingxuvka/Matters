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

#### Scenario: A catalog row lacks exact admitted Matter identity
- **WHEN** C12 receives a projection-only, source-only, or candidate row without the exact current C6-admitted `matter_id`
- **THEN** it SHALL exclude the row from the canonical root/child catalog and admitted-Matter coverage
- **AND** it MAY expose only the separately licensed source/candidate history surface without inventing a hierarchy path or canonical id

#### Scenario: A current admitted Matter projection is published
- **WHEN** C12 receives one exact current C6-admitted `matter_id` with the matching semantic and hierarchy revision
- **THEN** every card, child row, breadcrumb, coverage relation, detail request, and locale/density projection SHALL retain that exact identity

### Requirement: Every action has an owned behavior chain
Every reachable UI control SHALL map to an event, owner, function, resulting UI
update, and evidence.

#### Scenario: Ordinary first-version browser remains autonomous
- **WHEN** the user opens any catalog card or any of the eight ordinary detail sections
- **THEN** the object browser SHALL expose no correction, confirmation, rejection, tracking, cover-edit, or other canonical-write control, while the append-only C10 correction capability remains available through its separate API, CLI, MCP, or maintenance path

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
The UI SHALL expose evidence, uncertainty, and conflicts at an appropriate
on-demand level without revealing internal or private identifiers by default.
The ordinary first-version object browser SHALL NOT expose correction entry;
append-only correction remains a separate, non-primary capability.

#### Scenario: Matter contains an uncertain inference
- **WHEN** a current decision preserves low confidence, alternatives, or conflicting evidence
- **THEN** the object view SHALL show the best current result and SHALL let the user reveal the bounded reason and referenced evidence without requiring approval

### Requirement: The local v0.2 workflow is operable
The product SHALL provide owned paths and visible feedback for pasted input,
exact file selection, authorization status, automatic analysis, unavailable or
failed analysis, object browsing, evidence inspection, optional correction,
revocation, deletion, recomputation waiting, retry, and English-default/
`zh-CN` projection switching through the shared locale registry. The ordinary
first-version object browser SHALL remain read-only and SHALL NOT present
per-item confirmation, rejection, correction, defer, or other canonical-write
controls.

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
- **WHEN** a scope-triage result is uncertain, stale, or conflicts with a prior correction
- **THEN** the UI SHALL display the current reversible disposition, uncertainty, and automatic recomputation status without turning `track`, `do_not_track`, or `restore` into ordinary first-version controls

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
- **THEN** the UI SHALL discard stale output, preserve the current visible window on failure, expose retry, and SHALL NOT apply a payload from an older revision or expose a retired review/tracking action

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
color, typography, left navigation, card, and detail-dialog design, with the
Matters brand/logo substituted plus two bounded presentation exceptions
explicitly approved by the user on 2026-07-19. The left-sidebar brand region
SHALL use the selected red/yellow/blue Matters icon and MAY proportionally
enlarge only that icon and the adjacent `Matters` wordmark for legibility. The
search box and navigation SHALL move upward so the brand-to-search and
search-to-navigation gaps are both smaller than the space above the brand; the
brand region's upper and lower whitespace SHALL NOT be forced to equality. The
same approved icon SHALL be used for the browser window, Windows shortcuts,
and packaged application. No other typography, card, detail-dialog, or
interaction geometry changes are authorized by these exceptions. The left
region SHALL filter the right Matter-card catalog by lifecycle state, Start
time, people, relationships, modeled topic/type, and source type. Matter detail
SHALL expose exactly Overview, Sub-matters, Timeline, People, Related Matters,
Files & information, Images, and AI supplemental information as its ordinary
primary sections. Overview SHALL contain only the generated root Hero, one
human-readable project narrative, lifecycle state, and Start date. Actions,
open loops, source/evidence counters, and internal review state SHALL NOT
appear as Overview panels. Facts, work, waits, and outcomes SHALL remain
reachable inside the owning Matter quick view or Timeline. Evidence and change
history SHALL remain on-demand inside Files & information; internal identities
SHALL remain hidden.

#### Scenario: User opens the application
- **WHEN** the Windows desktop application launches with a current projection
- **THEN** it SHALL open the object browser in English by default, render the left filters and right card catalog using the frozen design language, and SHALL NOT open an AI review queue

#### Scenario: User launches the installed desktop product
- **WHEN** the user starts Matters from its installed Windows application or desktop shortcut
- **THEN** one owned desktop window SHALL open the packaged Web UI inside an application shell rather than requiring the user to visit a development URL in a normal browser
- **AND** that shell SHALL start and health-check the same loopback-only local MatterService and bounded durable worker used by the verified browser surface, preserve locale/density/window state, and expose startup or recovery failure inside the shell
- **AND** closing or restarting the shell SHALL checkpoint resumable work and stop only its owned service, worker, and window processes without moving, copying, or mutating registered source originals
- **AND** a browser-development launch by itself SHALL NOT satisfy the installed-desktop delivery gate

#### Scenario: User-approved Matters branding is rendered
- **WHEN** the desktop object browser, browser window, installed application, or Windows shortcut renders Matters branding
- **THEN** it SHALL use the same user-selected red/yellow/blue Matters icon
- **AND** the icon's external canvas SHALL be transparent, the stacked-card symbol SHALL render directly on its owning surface without an additional white frame or container, and white or cream regions intrinsic to the cards SHALL remain visible
- **AND** the left-sidebar brand icon and adjacent `Matters` wordmark SHALL retain their approved size while the search and navigation move upward under the bounded asymmetric-spacing rule
- **AND** the icon and wordmark SHALL align vertically as one left-aligned group whose visual center line remains at the same height as the catalog heading rather than floating in the sidebar center
- **AND** the visible non-transparent center of the icon, the typographic center of the `Matters` wordmark, and the typographic center of the catalog heading SHALL share one horizontal line; transparent padding inside the icon asset SHALL be compensated rather than treating image-box alignment as sufficient
- **AND** the top edge of the search control SHALL share one horizontal line with the top edge of the first visible Matter-card row

#### Scenario: User opens one Matter
- **WHEN** the user activates a Matter card
- **THEN** the detail dialog SHALL open the current Matter revision, preserve the browser filters and scroll state, and provide an accessible return path
- **AND** while that bounded detail request is pending, the catalog SHALL remain visible, the activated card SHALL expose a subtle busy state, and the UI SHALL NOT open an empty or generic `working in background` dialog
- **AND** autonomous background-maintenance status SHALL remain owned by the compact catalog-level coverage indicator rather than interrupting the user with a modal

#### Scenario: Matter card content is projected
- **WHEN** a Matter card is visible in either density
- **THEN** it SHALL show the current generated root hero or temporary neutral generation placeholder, primary lifecycle status, localized title, and one clearly labeled Start date when known
- **AND** the visible Start value SHALL use day precision only (`YYYY-MM-DD`) without an hour, minute, second, timezone, or truncated timestamp suffix, while the canonical source time MAY retain its full internal precision
- **AND** lifecycle status and Start date SHALL use the same calm card-metadata typography; lifecycle status SHALL NOT render inside a capsule, pill, chip, filled background, or rounded status container
- **AND** Standard density SHALL show exactly the current event count, people count, and source count from that same current projection revision while Compact density SHALL omit all three secondary metrics
- **AND** neither density SHALL render the Matter summary, key-person row, duplicate date, or another narrative sentence inside the catalog card
- **AND** compact density SHALL retain a clearly visible, recognizable crop of the same hero or placeholder rather than reducing the image to a decorative line or hiding it behind text
- **AND** date and secondary metrics SHALL NOT be repeated or overlaid across the hero and text regions
- **AND** changing density SHALL NOT request modeling, change canonical state, or substitute content from another projection revision

#### Scenario: Localized title and summary remain distinct
- **WHEN** the current semantic owners provide a localized human-readable Matter title and a localized bounded summary
- **THEN** C12 SHALL project the title value only into the card/detail title field and the bounded summary value only into the detail Overview and other explicitly summary-owning surfaces
- **AND** the catalog card SHALL omit the summary without making it unavailable to the root detail or accessibility projection
- **AND** it SHALL NOT promote the summary into the title, ignore the current short title, or keep a second successful title fallback path
- **AND** a missing current required-locale title SHALL keep the projection pending or blocked rather than silently substituting the summary

#### Scenario: Title and summary bind to the same accepted Matter owner
- **WHEN** one accepted autonomous result contains a C6 Matter candidate and a C12 bounded summary without an explicit Matter id
- **THEN** C12 SHALL bind both values only to the unique current C6 admission owner from that same package and semantic revision
- **AND** source-version overlap with an older Matter SHALL NOT select, overwrite, or revive that older Matter's projection
- **AND** zero or multiple same-result Matter owners SHALL block projection until the finding declares an unambiguous current Matter id

### Requirement: Material clues atomically refresh summary and catalog activity
Each current Matter SHALL expose one `latest_meaningful_clue_at`, a stable clue
identity, materiality rationale, and current bilingual bounded summary. A
material clue is current evidence that changes state, outcome, next step,
important time, involved person, relationship, hierarchy, or the useful
bounded summary. Inventory scans, retries, technical receipts, read times,
unchanged content, wording-only changes, localization-only changes, and hero
generation SHALL NOT count as material clues. A material child clue SHALL
propagate activity to every current ancestor without mechanically changing
their lifecycle state.

#### Scenario: A current material clue arrives
- **WHEN** a current source or descendant supplies a material clue for a Matter
- **THEN** C12 SHALL publish the clue identity, `latest_meaningful_clue_at`, and non-empty `en`/`zh-CN` summaries in one semantic revision
- **AND** until that revision is complete, the last current summary and order SHALL remain visible with a stale/recomputing indication rather than mixing locale or clue revisions

#### Scenario: A scan produces no semantic change
- **WHEN** discovery, extraction, analysis retry, localization, or hero generation completes without a material semantic change
- **THEN** the current activity time, summary revision, and catalog order SHALL remain unchanged

### Requirement: Root catalog order bubbles by latest meaningful clue
After applying the current search and filters, the root catalog SHALL sort by
`latest_meaningful_clue_at` descending with one stable deterministic tie-break.
The order SHALL remain identical across Standard/Compact density and `en`/
`zh-CN`. Start time SHALL remain an independent Matter occurrence-start filter
and SHALL NOT become the activity-order key.

#### Scenario: A filtered Matter receives a new child clue
- **WHEN** a current child supplies a material clue and its root ancestor remains inside the active filter
- **THEN** the ancestor SHALL move to the position licensed by the propagated clue time without changing the active filters, locale, density, focus owner, or lifecycle state

#### Scenario: Presentation state changes
- **WHEN** the user changes density or locale, or clears and re-applies an equivalent search/filter
- **THEN** all retained Matters SHALL preserve the same relative latest-clue order

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
- **AND** all current revisions and SourceVersions of one logical event SHALL project as one current timeline row; superseded wording and conflicting alternatives SHALL remain on demand inside that row rather than appearing as duplicate peer events
- **AND** a parent SHALL project an important descendant milestone once with its owning Matter path, while routine child facts remain in the node quick view
- **AND** the current best-supported interpretation SHALL be stated while conflicting claims, alternative times or meanings, material uncertainty, and their source relationships remain visible without requiring user confirmation

### Requirement: Situation-model inferences are useful and visibly distinct
The root Overview, Sub-matters graph, Timeline, and node quick view SHALL render
the current best-supported personal Situation/World Model projection while
distinguishing `confirmed_observed`, `reported`, `planned`, and `ai_inferred`
values. An inferred current state or outcome SHALL show confidence,
inference-time freshness, important supporting signals, missing expected
evidence, and material alternatives or contradictions on demand. The display
SHALL NOT imply that an AI-generated hero depicts a real occurrence.

#### Scenario: A booked trip leg is in the past without explicit completion mail
- **WHEN** the current model has licensed booking and departure-time evidence, the expected event time has passed, current coverage has no material cancellation/refund contradiction, but no observed completion evidence exists
- **THEN** the UI MAY show a localized “likely occurred” or equivalent current-best inference with an `AI inferred` label and confidence
- **AND** it SHALL NOT render the leg as confirmed completed or treat absence of a refund message alone as proof

#### Scenario: Contrary evidence arrives
- **WHEN** a cancellation, refund, missed-flight, or conflicting-time source becomes current
- **THEN** the affected inference SHALL become stale, conflict-preserved, or replaced through its original owner before the root summary, graph, or timeline claims a current interpretation

### Requirement: Standard and compact are independent display densities
The object browser SHALL provide a persisted `standard`/`compact` density
preference independent of responsive viewport mode. Both densities SHALL use
the same Matter order, filter, semantic revision, status, generated root hero,
selected object, and locale. Standard SHALL retain the three secondary metrics.
Compact SHALL reduce geometry, omit both the catalog summary and the three
secondary metrics, and give the remaining card body to a recognizable,
edge-to-edge hero rather than compressing it into a decorative strip.

#### Scenario: User selects compact density
- **WHEN** the user activates the compact switch
- **THEN** the grid SHALL render equal-width and equal-height compact cards, retain a visible hero, title, status, and Start date, omit event/people/source metrics, let the hero fill the remaining card body, preserve focus/filter/scroll/locale, and SHALL perform no canonical write or modeling request

#### Scenario: Window size changes
- **WHEN** the desktop viewport crosses a responsive breakpoint
- **THEN** responsive columns MAY change but the persisted standard/compact preference SHALL remain unchanged

#### Scenario: Catalog has one item
- **WHEN** only one Matter card is current
- **THEN** the card SHALL remain aligned to the top of the content region and SHALL NOT stretch or move to the vertical center

### Requirement: Every root Matter has one generated photorealistic hero disposition
Every admitted root Matter SHALL expose
exactly one current hero disposition:
`generated_current`, `generation_pending_placeholder`, or
`generation_blocked_placeholder`. Generation SHALL start only after the
Matter's semantic identity, merge disposition, current hierarchy, and
localized title/summary theme are current. Child Matters, WorkItems, Events,
sources, and graph quick-view nodes SHALL NOT receive independent heroes. The
generated image SHALL be a presentation artifact, SHALL NOT be SourceVersion
or Evidence, and SHALL NOT be chosen from real photos, mail/TXT/document
screenshots, attachments, embedded images, or document previews.

#### Scenario: A Matter becomes generation-ready
- **WHEN** one root Matter has a current semantic identity, merge, hierarchy, localized theme, and permission-safe generation brief
- **THEN** the system SHALL automatically request one privacy-minimized photorealistic documentary/editorial photograph, publish the same image in Standard, Compact, and detail surfaces, and store non-empty equivalent `en` and `zh-CN` alt text without user confirmation
- **AND** the brief SHALL require Matter-specific physical place, objects, equipment, or activity so the topic is recognizable without a caption; SHALL reject interchangeable people-at-computer or generic office scenes as well as abstract diagrams, symbolic collage art, screenshots, illustrations, and 3D-render language; and SHALL default to no literal text, logos, private identifiers, or identifiable real users
- **AND** at least two independently recognizable Matter-specific physical cues SHALL dominate the visible frame; a depicted person MAY support the scene but SHALL NOT be its sole distinguishing cue

#### Scenario: A current Hero fails the visual-specificity review
- **WHEN** an automated or browser visual review finds that a current Hero could represent an unrelated Matter, defaults to a generic person working at a computer, makes the person the only distinguishing cue, or omits two dominant Matter-specific place, equipment, object, or activity cues
- **THEN** C12 SHALL retire the current private token with the typed non-blocking `quality` invalidation, return the root Matter to `generation_pending_placeholder`, prepare exactly one current replacement brief, and preserve the prior asset only in private revision history
- **AND** the replacement SHALL pass the same privacy, bilingual-alt, presentation-only, and root-only gates before publication

#### Scenario: Hero generation is pending or fails
- **WHEN** generation has not completed, returns invalid output, violates safety, or exhausts a bounded attempt
- **THEN** C12 SHALL publish the typed temporary pending or blocked neutral placeholder, preserve the retry disposition, and SHALL NOT fall back to a real source image or second cover owner

#### Scenario: An ordinary clue changes
- **WHEN** a material clue updates state, outcome, next step, people, time, relationship, or summary without changing semantic identity, topic/theme, merge/split/reparent disposition, permission, or safety policy
- **THEN** the current generated hero SHALL remain stable while the summary and catalog order update

### Requirement: Matter detail has eight ordinary sections
The ordinary Matter detail reader SHALL expose exactly Overview, Sub-matters,
Timeline, People, Related Matters, Files & information, Images, and AI
supplemental information as its primary sections. Overview SHALL contain only
the generated root Hero, one bounded human-readable project narrative,
lifecycle state, and Start date, positioned as the useful visual center of the
section. Source/evidence counters, Actions, and OpenLoops SHALL NOT appear as
Overview panels. Facts, work, waits, and outcomes SHALL remain reachable in the
owning Matter quick view or Timeline. Evidence and change history SHALL remain
on-demand inside Files & information. Internal sources, evidence, corrections,
hero generation state, and execution-profile state SHALL NOT appear as
same-level ordinary navigation.

#### Scenario: User opens Matter detail
- **WHEN** a current Matter detail is shown
- **THEN** the eight primary section labels SHALL be localized through the shared locale registry and SHALL preserve the same semantic revision, breadcrumb, focus, and scroll state
- **AND** Overview SHALL NOT repeat a source count, evidence count, Action panel, OpenLoop panel, or internal model-review explanation

### Requirement: Images use an operable gallery
The Images section SHALL render only authorized current Matter-related real
photos or already-existing meaningful visual images as a thumbnail strip plus
one selected large image. Mail, TXT, office-document, PDF-page, source-code,
terminal, and generic application screenshots or document previews SHALL NOT
be admitted merely because they can be rendered. It SHALL support 0.5x-5x
zoom, reset, mouse-wheel zoom, panning when enlarged, keyboard
selection/navigation, and localized empty/unavailable states without exposing
private identifiers. Generated heroes SHALL NOT appear as evidence-gallery
assets.

#### Scenario: User inspects a related image
- **WHEN** the user selects a thumbnail, zooms, pans, resets, or uses the keyboard
- **THEN** the gallery SHALL update only view state, retain the current Matter and semantic revision, and perform no canonical write

### Requirement: Files and information use a bounded human-readable table
The Files & information section SHALL use a bounded table for related files,
Gmail-derived information, Codex projects/tasks, and other source-backed
records. It SHALL render one flat row set with `Source group` as an ordinary
column; contained folder, Gmail thread, Codex project/workspace, or declared
provider group SHALL NOT create repeated group-heading rows or a second nested
table. Each row SHALL show a localized human label, source type, privacy-safe
location, Source group label, source-observed/received/modified time, content
summary, and current availability. It SHALL NOT replace those values with
generic relationship text, processing time, internal ids, or “included in
understanding” status. Evidence and change history MAY expand on demand inside
the row and SHALL NOT require a separate primary section. Table body text SHALL
remain visually subordinate to the table and section headings, wrap within
bounded columns, and avoid horizontal overflow caused by oversized row
typography.

#### Scenario: User inspects one related record
- **WHEN** the user expands a row in Files & information
- **THEN** only the bounded minimized evidence/history for that row SHALL appear, ordinary labels SHALL remain human-readable, and internal paths, connector ids, receipts, and execution profiles SHALL remain hidden

### Requirement: AI supplemental information is advisory and freshness-bound
The AI supplemental information section SHALL show bilingual background
context, official rules, deadline or timezone interpretation, and practical
preparation suggestions that are useful for the current Matter. Each item SHALL
show its source relationship and freshness, SHALL be clearly labeled as
supplemental/advisory, and SHALL NOT assert that the user performed an action or
write canonical Matter state.

#### Scenario: Supplemental context is current
- **WHEN** a current research or semantic operation returns a scoped, supported supplemental item
- **THEN** the eighth section SHALL render its `en` and `zh-CN` projections with source and freshness information distinct from user evidence

#### Scenario: Research context is unavailable or stale
- **WHEN** the required research provider is unavailable, blocked, or its result is stale
- **THEN** the section SHALL show a localized bounded unavailable/stale state and SHALL NOT fabricate background facts or hide the rest of the Matter

#### Scenario: No supplemental item has been produced
- **WHEN** the current Matter has zero accepted supplemental items
- **THEN** the section SHALL show `pending`, `not_applicable`, or `unavailable` with its owner and reason
- **AND** it SHALL NOT label an empty result as current supplemental information

#### Scenario: Eligible root automatically enters bounded research
- **WHEN** an admitted root Matter has one current equivalent bilingual projection and zero accepted supplemental items
- **THEN** the system SHALL queue exactly one idempotent A1 package for the current ResearchGuard boundary and SHALL retain its opaque package identity with `pending`, `blocked`, or `unavailable`
- **AND** a repeated maintenance pass over unchanged inputs SHALL reuse the same package and SHALL NOT create another research request

#### Scenario: Descendant does not duplicate root research
- **WHEN** an admitted Matter has a current primary parent
- **THEN** its supplemental-information owner SHALL record `not_applicable` and SHALL NOT queue a descendant ResearchGuard package
- **AND** a later reparent or promotion to root SHALL recompute the disposition from the current hierarchy rather than preserving the former child status

### Requirement: Lifecycle state has one user-facing visual language
The object browser SHALL render exactly one human lifecycle state for a Matter,
independent from evidence modality, inference status, record currentness, or
background processing. In the Sub-matters graph, planned SHALL use green, in
progress SHALL use red, and completed SHALL use blue, together with text or an
icon so color is not the sole signal. Values such as `current`, `reported`,
`observed`, `inferred`, and `已报告` SHALL remain basis/modality metadata and
SHALL NOT appear as peer lifecycle states.

#### Scenario: A reported fact supports a planned Matter
- **WHEN** a reported source fact supports a Matter whose lifecycle owner says planned
- **THEN** the graph node SHALL show the localized planned state in green and SHALL retain reported only inside the relevant fact basis

### Requirement: Coverage status is compact, truthful, and drillable
The catalog SHALL render one slim single-line coverage control containing one
small status dot and one localized status label. It SHALL NOT render a nested
two-row card, a numerator/denominator under the label, or a second capsule as
thick as the density switch. Activating the control SHALL open a bounded
indexed drilldown from SourceGroup to first incomplete stage, object, owner,
failure reason, freshness, and actual UI reachability without exposing private
paths.

Green SHALL require current inventory, a terminal disposition for every
enumerated object, current SourceGroup reconciliation, current semantic depth,
hierarchy, narrative and UI reachability for every admitted Matter, and zero
blockers. Blue SHALL require measured forward progress in a required stage.
Red SHALL cover stale, blocked, missing-registration, inconsistent, or
UI-unreachable state. A recent aggregate checkpoint alone SHALL NOT produce
blue, and hard-excluded/unavailable objects SHALL NOT be counted as modeled.

#### Scenario: Terminal dispositions exist but no source object is UI-ready
- **WHEN** many objects are terminally hard-excluded or unavailable but one or more required tracked objects or admitted Matters have not reached their UI stage
- **THEN** coverage SHALL remain red or blue according to measured progress and SHALL NOT become green

#### Scenario: User opens coverage details
- **WHEN** the user activates the single-line coverage control
- **THEN** the UI SHALL fetch only bounded indexed summary/page data and SHALL NOT parse the entire private coverage ledger before returning the first page

### Requirement: Desktop launch starts bounded autonomous maintenance
The Windows desktop application SHALL start the local service and one durable,
bounded worker that resumes authorized discovery, reconciliation, analysis,
original-owner dispatch, localization, meaningful-clue/summary refresh,
generated-hero work, AI supplemental information, and projection while the
application is running. Normal completion SHALL NOT require user intervention.
Routine work SHALL stop cleanly on application shutdown and resume from durable
checkpoints on the next launch.

#### Scenario: Application resumes pending work
- **WHEN** the desktop application starts with current authorization and pending or stale coverage-ledger stages
- **THEN** the worker SHALL resume the next valid stage without duplicating completed work or asking the user to approve ordinary AI decisions

#### Scenario: One item is genuinely blocked
- **WHEN** an occurrence cannot progress because of revoked authorization, hard safety policy, corruption, encryption, unsupported rendering, or an exhausted required runtime retry
- **THEN** the worker SHALL record the exact blocked stage, continue unrelated items, and expose the exception without converting it into a global confirmation queue

#### Scenario: Desktop process has no Codex execution owner
- **WHEN** the local desktop process can see pending AI work but no Codex-hosted execution owner is attached
- **THEN** the worker SHALL report `waiting_for_codex`, use indexed coverage state and a bounded polling interval, SHALL NOT repeatedly enumerate private analysis packages, and SHALL leave the object browser responsive

### Requirement: Object-browser filters preserve the Databank navigation language
The left navigation SHALL expose one `All matters` entry and collapsible
Status, Start time, People, Relationships, Topic/Type, and Source type groups.
Start time SHALL use occurrence-start years or an explicit range. Flat
Recent/Upcoming/Updated buckets and duplicate All entries SHALL NOT replace the
grouped filter model.

#### Scenario: User filters by status and year
- **WHEN** the user selects one lifecycle state and one start year
- **THEN** the bounded root catalog SHALL apply both filters, keep each group and active filter visible, and preserve density, locale, search, and scroll context

### Requirement: Sub-matters use one multi-depth graph and one reusable quick view
Matter detail SHALL include a Sub-matters graph whose primary edges show the
current single-parent containment tree across every current bounded depth and
whose secondary styled edges show typed Matter-to-Matter relations without
changing primary parentage. Only current admitted Matters SHALL render as
graph nodes. WorkItems, Events, facts, sources, and advisory inferences SHALL
remain itemized under their owning Matter's quick view rather than becoming
graph boxes. The graph SHALL support pan, 0.5x-5x zoom, reset, minimap,
keyboard traversal, bounded continuation, and stable focus restoration. It
SHALL expose no per-node collapse/expand button and SHALL NOT navigate a node
to another full Matter detail page.

#### Scenario: User selects any graph node
- **WHEN** the user activates a current admitted Matter node at any visible depth
- **THEN** the UI SHALL open or update exactly one reusable single-layer quick-view dialog over the current root detail
- **AND** the quick view SHALL contain exactly two stacked primary regions: a localized human summary/current-state region containing itemized facts/events/work/waits with time and basis, and one flat files/information list with a Source group field
- **AND** current state SHALL use the exact current lifecycle/outcome basis, label a past-gap completion as localized `AI historical inference`, and omit internal `unknown` coverage vocabulary
- **AND** the files/information region SHALL include only material directly bound to the selected Matter node rather than copying every source from the owning root or parent
- **AND** it SHALL NOT render another hero, another eight-section Matter reader, another graph, another modal layer, or a recursive card/detail page
- **AND** technical record-currentness values such as `current`, `reported`, `observed`, or `inferred` SHALL NOT appear as a second user-facing lifecycle state on graph nodes; the node SHALL show a human lifecycle state only when one exists and retain modality/certainty in its separately owned label

#### Scenario: User selects a different node
- **WHEN** the quick view is open and the user activates another graph node
- **THEN** the same dialog instance SHALL replace its node projection, preserve the graph pan/zoom state, and keep only one overlay layer

#### Scenario: User closes the quick view
- **WHEN** the user presses Escape or activates close while the node quick view is open
- **THEN** only the quick view SHALL close and focus SHALL return to the originating graph node; a subsequent Escape MAY close the root detail and return focus to the original root card

#### Scenario: Search returns a descendant Matter or attached fact
- **WHEN** a localized search matches a descendant Matter or an attached fact that is not a root card
- **THEN** the result SHALL show its full primary path, open the owning root detail at Sub-matters, focus the matching node, and SHALL NOT duplicate it in the root catalog or open a descendant as another root detail

#### Scenario: Graph data is incomplete or too large for one page
- **WHEN** additional descendants or secondary edges remain beyond the bounded graph payload
- **THEN** the graph SHALL expose exact pending branch counts and load bounded continuation pages without fabricating a complete tree, hiding a branch behind a collapse control, or materializing the whole private catalog

### Requirement: Node quick view uses one flat source list rather than nesting sources
The node quick view's files/information region SHALL render one flat supporting
material list with Source group as an ordinary field. Each item SHALL show
human label, source type, privacy-safe location, Source group, source time,
concise content summary, availability, and confirmed/reported/planned/inferred
modality when relevant. It SHALL NOT insert repeated folder/thread/project
group headers, nested source tables, or another Matter page merely to display
those fields. Ordinary source-time cells and quick-view source metadata SHALL
display day precision only while the private canonical record retains its
complete timestamp.

#### Scenario: A node is supported by several source types
- **WHEN** one child or event has a local folder, Gmail thread, and Codex project in its current source set
- **THEN** the quick view SHALL show their bounded rows in one flat list with three human Source group values and SHALL NOT flatten them into generic “Information” records or create one nested detail per source

### Requirement: Transport errors never become fake empty state
Loading, processing, ready, honest-empty, no-filter-results, ready-stale, and
transport-error states SHALL remain distinct. Counts unavailable because of a
fetch failure SHALL render as unknown and SHALL NOT become zero.

#### Scenario: Browser API times out
- **WHEN** the current object-browser or coverage request times out
- **THEN** the UI SHALL retain recoverable prior content when available, show a localized retry state with unknown counts, and SHALL NOT claim that no Matters were found

### Requirement: Every meaningful UI batch has current desktop evidence
Each meaningful UI implementation batch SHALL be validated against the current
source service on port 8766 with desktop captures and DOM geometry at
1880x900 and 1440x900. The evidence set SHALL cover `en` and `zh-CN`,
Standard and Compact, and every changed loaded/processing/empty/error/detail/
filter/gallery state. It SHALL explicitly test text overlap, image overlap,
metrics over images, clipping, duplicate dates/summaries/people, section
overflow, and incoherent empty space. A failed observation SHALL be fixed and
recaptured on the same implementation/model revision before the UI batch is
current.

#### Scenario: A card or detail layout changes
- **WHEN** typography, spacing, card content, hero, navigation, section, or responsive behavior changes
- **THEN** the current 8766 surface SHALL produce the required screenshots and DOM geometry for the affected state matrix
- **AND** a Figma design, source inspection, unit test, or older screenshot SHALL NOT substitute for current runnable evidence

#### Scenario: A capture reveals overlap or repetition
- **WHEN** any required viewport shows text/image overlap, clipping, hidden labels, metrics covering the hero, repeated semantic information, or unusable whitespace
- **THEN** the batch SHALL remain blocked until the implementation is repaired and the failed cells are recaptured without the defect

### Requirement: Catalog paging is selected before card hydration
The private store SHALL apply root/child scope, admission status, locale-neutral
search keys, lifecycle status, Start year, people, relationships, topic/source
filters, `latest_meaningful_clue_at DESC`, deterministic tie-break, offset, and
limit through indexed queries before hydrating card context. Counts and facets
MAY use separate bounded aggregate queries. Only visible page ids and bounded
path/facet ids SHALL be hydrated into projections, hierarchy, coverage, people,
relationships, images, files, and supplemental information.

#### Scenario: A large catalog requests its first page
- **WHEN** thousands of current projections exist and the user requests at most 200 cards
- **THEN** the store SHALL return the selected ids, total, facets, and stable page guard without iterating or constructing every card, and the service SHALL hydrate only those visible ids plus bounded display dependencies

#### Scenario: Search or a filter is active
- **WHEN** one or more filters narrow the catalog
- **THEN** filtering SHALL precede activity ordering and paging, every matching object SHALL remain reachable across pages, and density or locale SHALL NOT change the relative order

#### Scenario: The implementation builds every card before slicing
- **WHEN** request handling iterates all current projections, hydrates all relations, constructs all cards, and only then applies `offset` and `limit`
- **THEN** the catalog scalability gate SHALL fail even if the returned payload and DOM are bounded

### Requirement: A parent overview is a bounded bilingual project narrative
C12 SHALL publish a parent Matter overview from a current evidence-bound
narrative result that covers the complete current child scope. The result SHALL
bind the parent id, hierarchy revision, child projection revision set, and
evidence revision set. It SHALL update the English and Chinese overview
together, without copying the latest child summary as the whole parent
overview. Every Matter summary SHALL tell the user what the Matter is, what has
finished or is happening now, and the next important thing when one exists.
It SHALL NOT expose internal review language such as “the evidence shows,”
“semantic revision,” “included in understanding,” routing, coverage stage, or
model confidence vocabulary. Important uncertainty MAY be stated in ordinary
language while its technical basis remains on demand.

#### Scenario: Current AI narrative covers all current children
- **WHEN** the result binds the current parent, hierarchy, complete child/projection set, and licensed evidence set
- **THEN** C12 SHALL atomically publish one bilingual parent overview revision while preserving the existing title, lifecycle state, activity recency/order, and generated-hero identity

#### Scenario: New child evidence arrives after narrative generation
- **WHEN** a material clue, child projection, canonicalization, or containment revision changes any bound input
- **THEN** C12 SHALL keep the last current overview visible as stale, enqueue a refresh through the original AI owner, and SHALL NOT relabel the latest child summary as a current project overview

#### Scenario: Narrative result attempts unrelated mutation
- **WHEN** the result proposes a title, lifecycle, activity-time/order, or generated-hero identity change
- **THEN** C12 SHALL reject those writes and admit only the evidence-licensed bilingual overview when its complete bindings are current

#### Scenario: Narrative reads like an internal audit
- **WHEN** a proposed summary describes evidence counts, model processing, route state, or what was included in semantic understanding instead of the user's situation
- **THEN** C12 SHALL reject it as non-human-readable and keep the prior current narrative or a visible pending state
