## ADDED Requirements

### Requirement: Every read is covered by a finite source grant
The system SHALL read or analyze content only when an active authorization
names an exact source occurrence, selected file, declared user-content root,
Gmail account/read scope, or configured cloud-backed content root together
with allowed operations, exclusions, and the applicable policy revision.

#### Scenario: Authorized pasted text is registered
- **WHEN** a user explicitly submits pasted text for declared analysis operations
- **THEN** the system SHALL register one source occurrence bound to that authorization

#### Scenario: Declared user-content root is enumerated
- **WHEN** an active source-universe grant names a user-content root and permits discovery
- **THEN** the filesystem adapter SHALL enumerate only occurrences contained by that resolved root under the current exclusion and traversal policy

#### Scenario: Object or operation is outside scope
- **WHEN** a requested source, path, account, or operation is not covered by the active authorization
- **THEN** the system SHALL reject it and record an access gap without fetching content or expanding scope

### Requirement: Narrow grants and root grants remain distinct
The system SHALL NOT derive directory, sibling-file, mailbox, cloud-account, or
connector authorization from a pasted input or single-file grant. A root grant
SHALL NOT expand across a symbolic link, junction, reparse point, mount, or
provider reference outside the declared root.

#### Scenario: Selected file has sibling files
- **WHEN** a user authorizes one file in a directory containing other files
- **THEN** the system SHALL NOT enumerate, inspect, watch, or read the sibling files

#### Scenario: Root contains a link to an external path
- **WHEN** discovery encounters a link or junction whose resolved target is outside the declared root
- **THEN** the system SHALL record `hard_excluded` and SHALL NOT follow the target

### Requirement: Candidate scope is frozen before broad analysis
The system SHALL freeze a versioned candidate-scope manifest containing the
authorized roots or mailbox scope, discovery policy, hard exclusions, tracking
policy, inventory revision, and allowed analysis operations before broad
content extraction or analysis.

#### Scenario: Authorized first-run roots are available
- **WHEN** the current product authorization names one or more user-content roots for organization
- **THEN** the system SHALL persist the resolved contained roots and policy revision before enumeration and SHALL begin bounded discovery without requiring per-root content confirmation

#### Scenario: Candidate scope changes
- **WHEN** a root, Gmail query/category policy, exclusion, or tracking rule changes
- **THEN** the system SHALL append a new scope revision and mark affected inventory and triage decisions stale

### Requirement: Authorized does not mean tracked
Every discovered item SHALL receive a current tracking disposition such as
`tracked`, `not_tracked`, `hard_excluded`, `metadata_only`, `blocked`, or
`unavailable` before broad analysis. An authorized but irrelevant, junk, or
generated item MAY remain outside tracking with a recorded reversible reason.
`tracked` is an actionable classification. Ordinary uncertainty SHALL be
stored with confidence, alternatives, and uncertainty codes on the best
supported current disposition and SHALL NOT create a user-confirmation gate.

#### Scenario: Generated clutter is not tracked
- **WHEN** an authorized occurrence matches the frozen generated-output or cache policy
- **THEN** the system SHALL record `hard_excluded` for policy-excluded cache material or `not_tracked` for reversible generated clutter and SHALL NOT submit it for content analysis

#### Scenario: A partition begins below a generated-state directory
- **WHEN** bounded partitioning creates a child scope below a directory token governed by the original-root tracking policy
- **THEN** classification SHALL retain the original-root policy context, record terminal `hard_excluded` for a current hard-rule ancestor or reversible `not_tracked` only for declared reversible clutter, and SHALL NOT reinterpret the child as ordinary user content merely because its local relative path lost the ancestor token

#### Scenario: Known generated state is pruned before partition descent
- **WHEN** a safe-boundary scan encounters a directory named by the current hard-exclusion policy, including software-control, dependency, cache, build, test, or temporary state
- **THEN** the system SHALL record a terminal policy disposition for that directory and SHALL NOT schedule, enumerate, or read descendant partitions beneath it

#### Scenario: A partition manifest was created under an older policy
- **WHEN** the current tracking-policy revision differs from the revision bound into a durable partition manifest
- **THEN** the system SHALL directly replace it with a new policy-current inventory, SHALL NOT resume obsolete descendant work, and SHALL retire omitted former child scopes and their objects from active work and UI counts while preserving append-only history

#### Scenario: Potentially valuable item is uncertain
- **WHEN** relevance classification is below the frozen confidence threshold or would exclude a potentially valuable source
- **THEN** the system SHALL conservatively choose the current reversible disposition declared by policy, preserve alternatives and uncertainty, and SHALL NOT silently omit the item or wait for user approval

#### Scenario: User overrides a not_tracked decision
- **WHEN** a user elects to track an item previously classified `not_tracked`
- **THEN** the system SHALL append the override, preserve prior history, and schedule current extraction or analysis under the unchanged authorization boundary

#### Scenario: Policy revision changes after a user override
- **WHEN** the tracking policy is revised and a previously overridden occurrence remains reachable
- **THEN** reconciliation SHALL preserve the current explicit user intent unless the user appends a replacement intent or authorization is revoked

### Requirement: Sensitive system material is hard_excluded
The system SHALL exclude credential and secret stores, browser/session data,
operating-system and application internals, caches, dependency/build outputs,
VCS internals, executable launch, unsafe serialized models, and uncontrolled
archive expansion even when they are physically nested below a broad root.

#### Scenario: Discovery encounters a credential or VCS path
- **WHEN** an enumerated occurrence matches the current hard-exclusion policy
- **THEN** the system SHALL record an `excluded_sensitive` disposition without reading its content

#### Scenario: Discovery encounters an executable or unsafe model
- **WHEN** an in-scope occurrence is executable or requires unsafe deserialization
- **THEN** the system SHALL NOT execute or deserialize it and SHALL record the declared `metadata_only`, `quarantined`, or `unsupported` disposition

### Requirement: Deterministic user-content admission precedes AI
Before any AI content task, the system SHALL classify each filesystem
occurrence using current path, directory, suffix, filename, file-kind, safety,
and source-neighborhood rules. Software source code, dependency manifests,
runtime databases, logs, caches, generated state, executables, and unsafe
serialized objects that match a hard rule SHALL receive a terminal non-content
disposition without spending an AI operation. Ordinary documents, images,
spreadsheets, presentations, and readable user-authored text MAY proceed to
bounded content analysis. Ambiguous safe files SHALL remain visibly
`metadata_only` or on a bounded reversible classification path; they SHALL NOT
be silently treated as useful content.

#### Scenario: User root contains a software project
- **WHEN** deterministic discovery finds program source files, dependency manifests, runtime databases, logs, or generated state inside an authorized user-content root
- **THEN** those occurrences SHALL be registered and terminally `hard_excluded` or `metadata_only` with a machine-readable reason before any AI task, while neighboring ordinary user documents remain independently eligible

#### Scenario: Application download folder contains ordinary documents
- **WHEN** a WeChat or other application download area contains an ordinary document or image but not an internal database, cache, executable, or log
- **THEN** the ordinary file MAY follow the normal user-content path while application-internal records remain hard-blocked

#### Scenario: Deterministic classifier cannot safely decide
- **WHEN** a safe unknown file does not match a hard exclusion or supported user-content rule
- **THEN** the system SHALL record terminal `hard_excluded` for unknown or machine formats, or `metadata_only` for a declared known unsupported media/archive class, with a machine reason and without executing, deserializing, or automatically submitting arbitrary bytes to AI

### Requirement: Active coverage excludes retired objects
Coverage summaries, next-work queues, indexed pages, Matter reachability, and UI
counts SHALL consume only current active occurrences. A deleted occurrence or
former partition scope removed by a current policy SHALL retain append-only
history but SHALL not remain active, pending, blocked, UI-ready, or attached to
a current Matter projection. Rediscovery under a current allowed policy SHALL
append a new active revision and re-enter the appropriate first incomplete
stage.

#### Scenario: A policy-current rebuild prunes an old software-state subtree
- **WHEN** an earlier partition scope is absent from the new current manifest because the subtree is now hard-excluded or no longer exists
- **THEN** the system SHALL deactivate the scope, retire its former occurrences from active coverage and UI indexes, preserve their history, and report only aggregate retirement counts outside the private runtime

#### Scenario: A retired occurrence becomes eligible again
- **WHEN** a previously retired occurrence is rediscovered under a current authorized and trackable policy
- **THEN** the system SHALL append an active coverage revision, clear obsolete terminal non-applicable stages, and schedule the first required current stage without duplicating source history

### Requirement: Gmail coverage is progressive and read-only
The system SHALL freeze the Gmail account identity, inclusion/exclusion query
policy, mailbox categories, allowed operations, pagination cursor, attachment
policy, and authorization revision before body reads. Inbox, Sent, and archived
non-Spam/non-Trash mail SHALL be progressively dispositioned; Spam and Trash
SHALL be `hard_excluded` or `metadata_only` by policy.

#### Scenario: Gmail page is read
- **WHEN** the next authorized Gmail page is available
- **THEN** the system SHALL register or disposition every returned message and persist the next cursor before advancing

#### Scenario: Gmail mutation is requested under a read grant
- **WHEN** an operation attempts to send, delete, archive, or change a label using the first-run read authorization
- **THEN** the system SHALL reject the operation without changing the mailbox

#### Scenario: Gmail is unavailable
- **WHEN** the connected Gmail app is disconnected or cannot read an authorized page, message, thread, or attachment
- **THEN** coverage SHALL remain partial or blocked at the durable cursor without silently substituting synthetic success

#### Scenario: Promotions category is encountered
- **WHEN** an authorized message is categorized as Promotions but not Spam or Trash
- **THEN** the system SHALL apply the current relevance policy rather than treating the category alone as proof that the message is junk

### Requirement: Coverage claims require per-item terminal dispositions
The system SHALL distinguish metadata inventory, canary extraction, incremental
coverage, complete terminal coverage, partial coverage, and unknown coverage.
It SHALL claim complete coverage only when every enumerated occurrence and
required discovery page has a current terminal disposition. The canonical
terminal occurrence dispositions are `ingested`, `not_tracked`,
`hard_excluded`, policy-authorized `metadata_only`, `unsupported`,
`excluded_sensitive`, `inaccessible`, `changed_during_read`,
`cloud_placeholder`, `quarantined`, `revoked`, and `deleted`.

#### Scenario: A small content canary uses a completed partition manifest
- **WHEN** a bounded filesystem content canary needs fewer items than the current inventory contains
- **THEN** the system SHALL first select the smallest current tracked complete partition that can fill the remaining sample, or the largest useful partial partition when none can, and SHALL NOT begin with an arbitrary giant subtree or cross many single-item scopes solely to obtain the sample

#### Scenario: Canary items update several coverage stages
- **WHEN** selected canary items or one imported AI result persist source, extraction, evidence, analysis, original-owner, Matter, localization, meaningful-clue/summary, generated-hero, supplemental-information, or projection stage updates
- **THEN** those item updates SHALL defer global coverage aggregation and the bounded canary or AI-result dispatch SHALL refresh the summary once at its terminal batch join rather than once per item, finding, owner, or stage

#### Scenario: A Gmail content canary has fewer supplied bodies than tracked messages
- **WHEN** a bounded authorized Gmail page contains tracked messages but only a subset has connector-supplied body content
- **THEN** the system SHALL select the supplied authorized bodies before metadata-only messages, SHALL enforce the exact content budget, and SHALL NOT report those supplied bodies as metadata-only merely because opaque message identifiers sort later

#### Scenario: Pagination or permission is incomplete
- **WHEN** any required page or occurrence is denied, missing, skipped, deferred, or unresolved
- **THEN** coverage SHALL be partial or unknown and SHALL NOT be described as complete

#### Scenario: Item is unsupported or changes during read
- **WHEN** an enumerated item is unsupported, quarantined, or changes before a stable version is registered
- **THEN** the system SHALL preserve `unsupported`, `quarantined`, or `changed_during_read` as the terminal disposition for the current inventory revision instead of counting the item as ingested

#### Scenario: Item is deliberately not tracked
- **WHEN** an enumerated item has a current `not_tracked` or `hard_excluded` disposition
- **THEN** terminal-coverage accounting MAY count its disposition but SHALL NOT count the item as ingested, analyzed, or useful evidence

### Requirement: Large roots are covered through durable bounded partitions
When a declared filesystem root cannot be inventoried within the frozen
per-scope resource budget, the system SHALL replace that attempted whole-root
inventory with a durable partition manifest. The manifest SHALL keep the
original authorization, policy revision, parent scope, child scope, partition
state, retry state, and terminal evidence distinct. A parent scan SHALL
inventory its direct files and SHALL record each safe child directory as a
declared partition boundary without recursively loading that child. Each child
scope SHALL then be scanned as one bounded recursive subtree. A child SHALL be
partitioned again only when that bounded subtree scan exceeds the frozen
per-scope resource budget; an ordinary nested directory that fits the budget
SHALL NOT become a separate partition node. Links, junctions,
reparse points, excluded directories, and inaccessible boundaries SHALL NOT
become child scopes.

#### Scenario: Whole-root inventory exceeds its resource budget
- **WHEN** bounded discovery reports `filesystem_discovery_entry_budget_exhausted` or an equivalent resource failure for an authorized directory
- **THEN** coverage SHALL remain partial and the system SHALL checkpoint a parent partition plus its safe immediate child scopes instead of increasing the budget until the entire tree is held in memory

#### Scenario: Parent boundary delegates to a child scope
- **WHEN** a bounded parent scan encounters a safe immediate child directory selected for partitioning
- **THEN** the parent occurrence SHALL receive terminal `not_tracked` with reason `covered_by_declared_child_scope`, while the child scope SHALL retain independent pending/current/failed coverage state

#### Scenario: A child subtree fits the frozen budget
- **WHEN** a declared child scope and all of its allowed descendants can be inventoried within the frozen per-scope resource budget
- **THEN** the system SHALL complete that child as one bounded subtree and SHALL NOT create partition-manifest nodes for its ordinary nested directories

#### Scenario: A child subtree exceeds the frozen budget
- **WHEN** a bounded recursive child scan exhausts the frozen per-scope resource budget
- **THEN** the system SHALL replace only that child attempt with safe immediate child partitions and SHALL keep aggregate root coverage partial until those new scopes are terminal

#### Scenario: Every partition is terminal
- **WHEN** every required partition has a current terminal inventory and every occurrence within those partitions has a current terminal disposition
- **THEN** the aggregate root coverage MAY become complete and SHALL cite the exact partition-manifest revision

#### Scenario: A partition is missing, failed, or stale
- **WHEN** any required child partition is pending, inaccessible without a terminal disposition, resource-failed, interrupted, or stale under a newer source or policy revision
- **THEN** aggregate root coverage SHALL remain partial or blocked and SHALL expose the unfinished partition without treating its parent boundary row as content coverage

### Requirement: Cloud placeholders do not imply content coverage
The system SHALL distinguish enumerated cloud metadata from hydrated readable
content.

#### Scenario: Cloud-backed file is an unhydrated placeholder
- **WHEN** discovery can see a cloud occurrence but cannot obtain stable content under the active grant
- **THEN** the system SHALL record `metadata_only`, `cloud_placeholder`, or `inaccessible` according to policy and SHALL NOT claim content ingestion

### Requirement: Revocation stops future access
The system SHALL stop reads under a revoked authorization and invalidate
dependent current evidence.

#### Scenario: Authorization is revoked
- **WHEN** a previously active authorization is revoked
- **THEN** later reads SHALL fail and a recomputation or removal disposition SHALL be issued for every dependent

### Requirement: Agent operations inherit source authorization
AI and local-skill operations SHALL receive only current SourceVersions and
EvidenceAnchors covered by the active authorization and SHALL NOT enlarge the
read boundary or activate undeclared tools.

#### Scenario: Agent operation requests an unregistered source
- **WHEN** an agent operation requests content outside its authorized work package
- **THEN** the system SHALL reject the operation as scope-incompatible without reading that content

#### Scenario: Source text contains instructions to expand scope
- **WHEN** a document, image, or message attempts to direct the runner to read another source or perform an external action
- **THEN** the runner SHALL treat the instruction as untrusted source content and SHALL preserve the original authorization boundary

#### Scenario: A queued source becomes excluded or inactive
- **WHEN** a current policy revision changes a registered source occurrence to non-`tracked` or inactive after an AI package was created
- **THEN** the package SHALL leave the runnable queue without erasing history and SHALL NOT be submitted to a model

#### Scenario: A queued package uses a retired capability role
- **WHEN** a durable package uses a pre-current capability name while its inputs remain authorized and tracked
- **THEN** the system SHALL direct-migrate it to exactly one current seven-role package, hide the retired package from runnable work, and SHALL NOT add a compatibility runner or named-model dependency

#### Scenario: A Codex worker requests one pending analysis page
- **WHEN** thousands of current and historical WorkPackages, results, source revisions, migrations, and coverage rows exist
- **THEN** the system SHALL join only current owner-indexed sets, apply authorization, dependency, migration, and terminal-result filters once, return the bounded page plus exact current total, and SHALL NOT execute a correlated full-history query per package

### Requirement: Object coverage is machine-auditable through UI readiness
The system SHALL maintain one durable `ObjectCoverageLedger` row for every
registered occurrence and admitted Matter. Each row SHALL record the current
authorization, discovery, tracking disposition, source/version, extraction,
analysis, original-owner decision, semantic-depth, required localization,
meaningful-clue/summary freshness, generated-hero disposition for independently
openable Matters, supplemental-information freshness, UI-projection,
freshness, retry, and terminal-reason dispositions without becoming the owner
of those component states.

#### Scenario: One occurrence is not yet UI-ready
- **WHEN** any required extraction, analysis, owner, localization, meaningful-clue/summary, generated-hero, supplemental-information, or projection stage is missing, stale, retrying, or blocked
- **THEN** the coverage ledger SHALL name that exact stage and SHALL NOT report the occurrence or aggregate run as UI-ready

#### Scenario: Registered universe is current
- **WHEN** every registered occurrence has a terminal source disposition, every root Matter has current owner, locale, clue/summary, generated-hero-or-typed-temporary-placeholder, every descendant has an explicit hero `not_applicable` disposition, and every admitted Matter has supplemental-information disposition and reachable UI projections
- **THEN** the coverage audit MAY report the exact inventory revision as current and complete

### Requirement: Coverage keeps one full current payload and an exact compressed noncurrent archive
Each `ObjectCoverageLedger` object SHALL keep its complete current stage payload
directly queryable. Replaced noncurrent revisions SHALL move to an exact,
versioned compressed archive with object id, revision order, uncompressed byte
count, record count, canonical digest, compression identity, and verification
state. Reading history SHALL reconstruct the exact logical revision sequence;
compression SHALL NOT discard, summarize, or reorder prior dispositions.

#### Scenario: A current coverage payload is replaced
- **WHEN** a new full current payload commits for the same object
- **THEN** the prior current revision SHALL become noncurrent and MAY enter the compressed archive through an explicit bounded owner
- **AND** the new current payload SHALL remain fully and directly queryable without decompressing the object's history

#### Scenario: A noncurrent history page is archived
- **WHEN** the explicit coverage-history archive owner selects a bounded stable page
- **THEN** it SHALL create and reread the compressed archive, verify record count, uncompressed byte count, canonical digest, object identity, revision order, and decompressed logical equality before deleting the original duplicated history rows
- **AND** interruption before verification SHALL preserve the original rows and make the page safely retryable

#### Scenario: Historical coverage is requested
- **WHEN** an audit asks for current plus earlier revisions
- **THEN** the store SHALL merge the full current payload with the exact verified archive in revision order and SHALL expose corruption or missing archive data rather than silently returning partial history

### Requirement: Storage repair is explicit, ordered, bounded, and non-compacting
Legacy evidence references SHALL be rebased to bounded C3 anchor-set pointers
before dependent coverage history is archived. Both maintenance owners SHALL
use stable continuation cursors, finite page limits, idempotent retries, and
terminal receipts. Foreground startup SHALL run neither repair. Logical
migration completion SHALL not imply physical file shrink, and the migration
owner SHALL not run `VACUUM` or `VACUUM INTO`.

#### Scenario: A large legacy database requires both repairs
- **WHEN** explicit private maintenance begins after a verified restorable backup and all other writers are stopped
- **THEN** it SHALL finish and validate bounded evidence-pointer rebase pages before bounded coverage-history archive pages
- **AND** it SHALL run integrity, count, and sampled historical-equivalence checks before either migration is terminal

#### Scenario: A migration page is interrupted
- **WHEN** the process stops after any nonterminal pointer or archive page
- **THEN** the next explicit run SHALL resume from the durable continuation, reverify the affected page, and SHALL NOT restart from the beginning or claim the whole database current

#### Scenario: Logical migration completes
- **WHEN** both explicit migrations and their verification receipts are terminal
- **THEN** freed SQLite pages MAY remain available for reuse and the runtime SHALL NOT claim that the database file shrank
- **AND** any later physical compaction SHALL be a separate offline operation with separate disk-capacity, backup, integrity, and activation evidence

### Requirement: Matter hierarchy coverage is machine-auditable
Every admitted Matter SHALL have current, independently queryable
`hierarchy_decision`, `containment_current`, `child_state_current`,
`ancestor_rollup_current`, `hierarchy_projection_current`, and `ui_reachable`
stage dispositions for the exact semantic and hierarchy revision. Occurrence
rows that cannot be Matters SHALL receive an explicit not-applicable hierarchy
disposition.

#### Scenario: Child hierarchy is stale
- **WHEN** a child Matter, containment edge, role, outcome, source, or parent changes after an ancestor summary was produced
- **THEN** the ledger SHALL name the first stale hierarchy stage for the child and every affected ancestor and SHALL NOT count those Matter projections as current

#### Scenario: Browser transport fails
- **WHEN** a coverage or object-browser request times out or cannot reach the current private projection
- **THEN** the UI SHALL report unknown transport state and retry ownership and SHALL NOT replace current counts with zero or claim an honest empty catalog

#### Scenario: A projection, source, or candidate has no exact admitted Matter id
- **WHEN** coverage receives only a projection id, SourceVersion id, MatterCandidate id, or inferred source-overlap match
- **THEN** it SHALL NOT create or update admitted-Matter hierarchy stages or admitted-Matter totals
- **AND** it SHALL retain the source/candidate disposition until C6 supplies the exact current admitted `matter_id`

### Requirement: Current coverage schema repair is tracked-only and resumable
The coverage-stage schema rebase SHALL visit only active occurrences whose
current disposition is `tracked`. It SHALL add missing current stages through
a bounded stable continuation and SHALL preserve inactive, retired,
`not_tracked`, and `hard_excluded` history without reopening work.

#### Scenario: One active legacy tracked row lacks content selection
- **WHEN** a bounded coverage-schema rebase page reaches that row
- **THEN** the system SHALL add a pending `content_selection` stage, replace the required-stage inventory with the current tracked contract, and checkpoint the next stable continuation

#### Scenario: One legacy row is already retired
- **WHEN** the same coverage-schema rebase runs
- **THEN** the row SHALL remain byte-for-byte historical, SHALL receive no new pending stage, and SHALL NOT re-enter aggregate active counts or runnable work

### Requirement: Coverage orphans are retired explicitly
An active source `ObjectCoverageLedger` row SHALL have one current inventory
occurrence owner. A bounded orphan-reconciliation owner SHALL retire any row
whose current inventory occurrence no longer exists, without deleting its
history or touching admitted Matter coverage.

#### Scenario: Active source coverage has no current inventory occurrence
- **WHEN** the bounded orphan page selects that object id
- **THEN** the system SHALL append an inactive `not_tracked` disposition, remove it from active counts and runnable work, preserve all prior stages, and return a resumable terminal reconciliation status

#### Scenario: The orphan repair is retried
- **WHEN** no additional active orphan row matches the same object id
- **THEN** the retry SHALL write no duplicate retirement and SHALL report current
