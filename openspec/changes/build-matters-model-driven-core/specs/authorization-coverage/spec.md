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
- **THEN** classification SHALL retain the original-root policy context, record reversible `not_tracked` dispositions for generated clutter, and SHALL NOT reinterpret the child as ordinary user content merely because its local relative path lost the ancestor token

#### Scenario: Known generated state is pruned before partition descent
- **WHEN** a safe-boundary scan encounters a directory named by the current hard-exclusion policy, including software-control, dependency, cache, build, test, or temporary state
- **THEN** the system SHALL record a terminal policy disposition for that directory and SHALL NOT schedule, enumerate, or read descendant partitions beneath it

#### Scenario: A partition manifest was created under an older policy
- **WHEN** the current tracking-policy revision differs from the revision bound into a durable partition manifest
- **THEN** the system SHALL treat the manifest as stale, prevent a current or complete claim, and require a new policy-current inventory rather than resuming obsolete descendant work

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
- **WHEN** selected canary items or one imported AI result persist source, extraction, evidence, analysis, original-owner, Matter, localization, visual, or projection stage updates
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

### Requirement: Object coverage is machine-auditable through UI readiness
The system SHALL maintain one durable `ObjectCoverageLedger` row for every
registered occurrence and admitted Matter. Each row SHALL record the current
authorization, discovery, tracking disposition, source/version, extraction,
analysis, original-owner decision, semantic-depth, required localization,
representative-visual, UI-projection, freshness, retry, and terminal-reason
dispositions without becoming the owner of those component states.

#### Scenario: One occurrence is not yet UI-ready
- **WHEN** any required extraction, analysis, owner, localization, visual, or projection stage is missing, stale, retrying, or blocked
- **THEN** the coverage ledger SHALL name that exact stage and SHALL NOT report the occurrence or aggregate run as UI-ready

#### Scenario: Registered universe is current
- **WHEN** every registered occurrence has a terminal source disposition and every admitted Matter has current owner, locale, visual-or-placeholder, and reachable UI projections
- **THEN** the coverage audit MAY report the exact inventory revision as current and complete
