## ADDED Requirements

### Requirement: Source observations are immutable while originals remain in place
The system SHALL preserve an immutable record of what source occurrence was
observed, where it is authorized, and which content/metadata fingerprint was
read without AI rewriting. By default it SHALL NOT copy a complete local file,
Gmail body, attachment, source image, or provider object into Matters durable
storage. The original remains in its existing source location and later
observations become new source versions linked to their predecessor.

#### Scenario: Source content changes
- **WHEN** pasted text, a local file, a document, an image, a Gmail item, an attachment, or hydrated cloud content differs from the current source version
- **THEN** the system SHALL create a new immutable observation/fingerprint version linked to its predecessor without overwriting the source or retaining another complete original by default

#### Scenario: AI proposes normalized wording
- **WHEN** an AI or local skill proposes a summary or normalized wording
- **THEN** the proposal SHALL be stored separately and SHALL NOT replace the immutable source content

#### Scenario: A complete source is read for extraction
- **WHEN** an authorized extractor temporarily reads a complete local file, Gmail body, attachment, or source image
- **THEN** the bytes or text SHALL remain private transient work material, SHALL NOT become a default durable SourceVersion body or original-image blob, and SHALL be removed after the atomic derived-state commit or the declared bounded failure/TTL path

### Requirement: Content and metadata identities are separate
The system SHALL calculate and retain separate identities for content and
metadata changes and SHALL keep provider occurrence identity separate from
deduplicated content identity.

#### Scenario: Only metadata changes
- **WHEN** source metadata changes while source content remains identical
- **THEN** the system SHALL record a metadata revision without claiming a content revision

#### Scenario: Identical content appears in two places
- **WHEN** two authorized local paths or mail attachments contain identical bytes
- **THEN** the system SHALL retain two occurrence identities and MAY share one content fingerprint or derived-analysis identity without copying or claiming ownership of the external original bytes

### Requirement: Files retain private source-neighborhood structure
The system SHALL retain the authorized root, contained relative parent,
source-neighborhood identity, ancestor-group chain, occurrence identity, and
relevant private metadata as provenance. Files SHALL NOT become isolated
semantic inputs merely because content extraction is item-bounded. Raw local
paths and private directory names SHALL remain outside public projections.
The machine-local private UI MAY show a contained human-readable folder/group
label that is inside the active grant, but SHALL NOT expose the absolute root,
internal locator, opaque identity, or an unauthorized adjacent path.
Opaque neighborhood and group identities SHALL remain stable when the same
occurrence is scanned from the authorized root or from a bounded child
partition. Private bounded AI work MAY receive contained folder labels and
file-kind context, but SHALL NOT receive or expose an absolute local path.
Folder proximity is contextual evidence only; it SHALL NOT by itself prove one
Matter, Event, person identity, or causal relationship.

#### Scenario: Related user files share a folder
- **WHEN** several eligible files occur under the same contained relative parent
- **THEN** each file SHALL keep its own occurrence/version identity and SHALL also reference the same opaque source-neighborhood identity for later bounded Matter and timeline synthesis

#### Scenario: File is nested in several folders
- **WHEN** an eligible occurrence has a contained ancestor chain below the authorized root
- **THEN** the system SHALL retain an ordered opaque group chain so later modeling can use spatial organization without exposing the raw path in the public UI

#### Scenario: The same folder is scanned through a child partition
- **WHEN** a bounded inventory moves the scan boundary from the authorized root to a contained child directory
- **THEN** the same physical parent SHALL produce the same opaque neighborhood and ordered group chain, while contained private folder labels remain limited to authorized work packages and the bounded machine-local source-group UI

#### Scenario: Folder proximity conflicts with content evidence
- **WHEN** files share a source neighborhood but their content, people, or times support different Matters
- **THEN** the system SHALL preserve the neighborhood relation as provenance and SHALL NOT force the files into one Matter or Event

#### Scenario: A private source group is shown in quick view
- **WHEN** the machine-local UI groups current supporting files by a contained authorized folder
- **THEN** it SHALL show only the minimum human-readable contained group label and bounded member rows required for the current Matter/node, while public artifacts and ordinary logs retain only opaque or aggregate identities

### Requirement: Deterministic user-content admission precedes content reads and AI
The system SHALL classify occurrence metadata and bounded path context before
reading content or creating AI work. Program source and scripts,
software-control and dependency manifests, software-tree configuration,
application databases/logs/runtime state, caches, generated/build outputs,
executables, unsafe serialized models, credentials, and unknown machine
formats SHALL receive a terminal non-content disposition without model use.
Ordinary user documents, photos, spreadsheets, presentations, user-authored
text, and declared safe exports/downloads SHALL remain eligible for bounded
content extraction. A hard exclusion SHALL remain accounted in coverage and
SHALL NOT silently disappear from the inventory.

#### Scenario: A folder contains program source and generated state
- **WHEN** metadata and bounded path context identify scripts, source files, dependency/build state, caches, or software runtime records
- **THEN** the system SHALL record a deterministic terminal reason and SHALL NOT read those bytes or create an AI work package

#### Scenario: A messaging application exposes both downloads and internal state
- **WHEN** an authorized user folder contains ordinary downloaded or explicitly exported documents alongside an application's database, logs, cache, session, or runtime-state files
- **THEN** the ordinary files SHALL follow normal user-content admission while the application-internal records SHALL remain terminal unless a separately authorized safe provider adapter exports them

#### Scenario: A safe user export uses a machine-readable format
- **WHEN** a declared user export such as CSV or non-software-tree JSON is inside the authorized scope and is not credential, executable, cache, build, dependency, or application-internal state
- **THEN** the system SHALL keep it eligible for the matching bounded extractor rather than excluding it solely because the format is machine-readable

#### Scenario: A hard exclusion is reported in coverage
- **WHEN** a program, cache, generated, or application-internal occurrence is deterministically excluded
- **THEN** its occurrence identity, terminal disposition, policy revision, and non-sensitive reason SHALL remain countable while no content, private path, or application payload enters AI or the public UI

### Requirement: Registration and content admission are separate
The system SHALL register every authorized occurrence before deciding whether
its bytes should be read. A `tracked` inventory disposition SHALL NOT by itself
authorize immediate full-content extraction or unbounded AI expansion.

Each active tracked occurrence SHALL have one current, private, revision-bound
content plan with an explicit mode, reason, priority, source-neighborhood
identity, freshness fingerprint, and bounded continuation state. Supported
modes SHALL distinguish metadata-only/deferred, sampled annotation, bounded
extraction, and explicitly authorized resumable deep extraction.

#### Scenario: A user folder contains many supported files
- **WHEN** inventory registers supported documents, images, and ordinary text across one or more source neighborhoods
- **THEN** every occurrence SHALL become coverage-visible at `content_selection`, while only occurrences with a current read-admitting plan MAY advance to `source_version`
- **AND** no scan, service startup, or ordinary maintenance cycle SHALL treat registration as permission to read every file

#### Scenario: A software project contains human-readable support files
- **WHEN** deterministic policy identifies a software tree after hard-excluding source, configuration, cache, dependency, build, and internal-runtime files
- **THEN** ordinary project Markdown or exports MAY remain registered as metadata-only/deferred context unless a bounded plan selects them
- **AND** folder or repository context SHALL prioritize selection without merging distinct Source identities

#### Scenario: Selection is deferred
- **WHEN** a current occurrence is safe to register but is not selected for a content read
- **THEN** coverage SHALL record the private plan and reason, terminate non-applicable downstream work honestly, and SHALL NOT create SourceVersion content, extraction anchors, or AI packages

#### Scenario: A deeper read is useful
- **WHEN** a sampled or bounded pass establishes that deeper content is useful
- **THEN** a new explicit deep-extraction plan SHALL provide a durable page, line, part, or equivalent continuation cursor and budget
- **AND** the system SHALL NOT repeatedly reread only the beginning or claim the unseen remainder complete

### Requirement: Content work is value-bounded and resumable
Content-selection and content-read claims SHALL be bounded, idempotent, and
ordered by deterministic private priority such as recent material change,
human-document type, size, and source neighborhood rather than opaque object id
alone. Low-cost replaceable AI MAY classify ambiguous metadata; only the
original content-selection owner writes the plan.

#### Scenario: A large inventory is processed over many runs
- **WHEN** tens of thousands of registered occurrences await content selection
- **THEN** each run SHALL advance a finite disjoint claim, publish a durable checkpoint, and leave all remaining occurrences visibly pending or deferred
- **AND** interruption SHALL release or expire only the affected claim without duplicating completed selection or content work

### Requirement: Inventory scan revision is not content-selection semantic identity
The current content-selection semantic identity SHALL be derived only from the
occurrence, current tracking/content policy, content-relevant metadata,
neighborhood context, selection mode/reason/priority, and continuation contract
that can change the selected read. The inventory scan revision MAY remain a
separate freshness and audit reference but SHALL NOT by itself change the plan
identity, create a new current plan, or enqueue duplicate extraction or AI
work.

#### Scenario: A no-delta scan advances the inventory revision
- **WHEN** a later authorized scan receives a new inventory revision while the occurrence, policy, content-relevant metadata, neighborhood context, and selection contract remain semantically identical
- **THEN** the system SHALL retain the current content-selection identity and return no semantic delta
- **AND** it MAY update the separate inventory audit reference without rewriting the plan or duplicating content, evidence, package, or projection work

#### Scenario: A selection-relevant input changes
- **WHEN** policy, content-relevant metadata, neighborhood context, mode, reason, priority, or continuation changes the licensed read
- **THEN** the original content-selection owner SHALL publish a new semantic plan identity and invalidate only its declared dependents

### Requirement: Foreground startup does not own private-catalog migration
Opening the desktop, HTTP service, MCP service, or CLI SHALL expose current
readable state without enumerating or rewriting the private catalog. Legacy
coverage, analysis-package, projection, hierarchy, activity, visual, or hero
records SHALL advance only through explicit, bounded, resumable maintenance
owners.

#### Scenario: Current private catalog contains legacy rows
- **GIVEN** a private runtime contains legacy rows from an earlier Matters version
- **WHEN** the user opens the desktop, HTTP service, MCP service, or an ordinary CLI command
- **THEN** foreground startup SHALL remain responsive
- **AND** it SHALL NOT retire, migrate, rebuild, or prepare catalog rows as a startup side effect
- **AND** it SHALL NOT run `VACUUM`, `VACUUM INTO`, or another whole-database physical compaction as a startup side effect
- **AND** each required migration SHALL remain visible as explicit bounded work with a continuation or terminal receipt

### Requirement: Registration is idempotent
The system SHALL deduplicate repeated registration of the same pasted,
filesystem, mail, attachment, or provider occurrence and version.

#### Scenario: Provider delivery is retried
- **WHEN** an identical occurrence and version is delivered again under the same idempotency key
- **THEN** the system SHALL return no-delta and SHALL NOT create a duplicate Source, Event, or Matter

### Requirement: Deletion is represented
The system SHALL preserve a tombstone and dependent disposition when an
authorized source is deleted or becomes unavailable.

#### Scenario: Source is deleted
- **WHEN** a previously registered source is confirmed deleted
- **THEN** the system SHALL create a tombstone revision, invalidate evidence that depended on the missing content, and retire the occurrence from active coverage, work, relation, and UI indexes without erasing history

### Requirement: Private source state survives restart without duplicating originals
The system SHALL persist source/provider locators, source/version identities,
content and metadata fingerprints, exact anchor coordinates and digests,
derived facts/summaries/relationships/models, metadata, discovery cursors,
per-item dispositions, tombstones, and current references under the configured
external `MATTERS_HOME` root. It SHALL NOT require a persisted complete source
body in order to rebuild the current UI projection.

#### Scenario: Service restarts during discovery
- **WHEN** the service restarts with the same authorized external `MATTERS_HOME` after a discovery page was committed
- **THEN** it SHALL recover SourceVersions, derived state, dispositions, and the durable cursor without reading source data from the Git repository, copying the original into Matters, or duplicating the committed page

#### Scenario: Original source is no longer reachable
- **WHEN** a previously modeled local file, Gmail message, attachment, or provider object is moved outside its grant, deleted, revoked, offline, or otherwise unavailable
- **THEN** the system SHALL preserve its prior derived understanding and provenance as historical/private state, mark the source and dependent inspection paths unavailable or stale, and SHALL NOT claim the original remains inspectable or upgrade an inference to confirmed evidence

#### Scenario: A registered filesystem batch reads current occurrences
- **WHEN** content processing selects already registered filesystem objects
- **THEN** it SHALL resolve each locator, metadata, disposition, scope, and inventory revision through a rebuildable exact current-occurrence index while the immutable inventory snapshot remains authoritative, and SHALL NOT decode a whole scope snapshot once per object

#### Scenario: Two workers request the same registered files
- **WHEN** concurrent workers request a bounded filesystem batch
- **THEN** one atomic claim lease SHALL assign disjoint objects, every completion or stage advance SHALL require the matching token, and an expired interrupted claim SHALL resume from its durable stage checkpoint

#### Scenario: Identical source registration races
- **WHEN** two authorized workers concurrently register the same unchanged occurrence and content
- **THEN** atomic source registration SHALL create exactly one immutable source version and the other attempt SHALL converge to no-delta without leaking a revision conflict

### Requirement: Private storage classes have singular retention owners
Every private artifact SHALL have exactly one current class:
`external_original`, `durable_derived`, `rebuildable_cache`,
`transient_staging`, or `recovery_backup`. `external_original` records only a
source-in-place locator and fingerprints. `durable_derived` contains the
minimal source-independent understanding required for restart and UI.
`rebuildable_cache` and `transient_staging` SHALL declare byte quota, TTL or
terminal cleanup, reference owner, and garbage-collection policy.
`recovery_backup` SHALL be created only by an explicit offline recovery owner
and SHALL NOT become normal runtime authority.

#### Scenario: A successful extraction commits
- **WHEN** derived anchors, facts, summaries, relations, and coverage pointers commit atomically
- **THEN** the transient complete body or bytes SHALL be deleted, while only the source locator/fingerprint, declared minimal derived state, and current reclaimable caches remain

#### Scenario: A cache is no longer referenced
- **WHEN** a thumbnail, document preview, connector batch, generated staging file, or another rebuildable cache has no current reference and exceeds its retention policy
- **THEN** the bounded garbage collector SHALL delete it, record aggregate private reclamation evidence, and SHALL NOT delete the external original or durable derived state

#### Scenario: A cleanup run is interrupted
- **WHEN** transient cleanup, reference reconciliation, or garbage collection stops before its terminal receipt
- **THEN** the next bounded run SHALL resume from its durable cursor, recheck every reference before deletion, and SHALL NOT restart an unbounded scan or treat the interrupted cleanup as complete

### Requirement: Legacy copied originals migrate directly to source-in-place authority
The private migration SHALL directly replace legacy complete SourceVersion
bodies and copied original-image blobs with current locator/fingerprint
SourceVersions plus current durable derived state. No normal-runtime legacy
reader, dual authority, or copied-original fallback SHALL remain.

#### Scenario: A legacy private catalog contains copied originals
- **WHEN** all writers are stopped and a separate verified restorable backup exists
- **THEN** the migration SHALL first verify source locators and all required derived evidence, append the current pointer-only authority, remove legacy raw bodies/original-image copies and stale staging through bounded resumable pages, and run integrity/count/equivalence checks before activation

#### Scenario: A source cannot be revalidated during migration
- **WHEN** the original is unavailable or the required derived state cannot be proven sufficient
- **THEN** that source SHALL remain explicitly blocked for migration with its legacy bytes protected by the verified recovery boundary, and the system SHALL NOT silently delete or claim completion

#### Scenario: Logical migration completes
- **WHEN** all bounded source-body, original-image, staging, and reference pages are terminal and verified
- **THEN** physical SQLite or backup shrink SHALL remain a separate offline compaction/retention decision with independent capacity, backup, integrity, activation, and rollback evidence

### Requirement: Gmail metadata-only messages retain minimal source ownership
Every current Gmail message occurrence with a `metadata_only` disposition,
including an identity-only connector observation, SHALL retain one minimal
private SourceVersion derived only from its authorized message envelope. The
write SHALL require an active ObjectCoverage row and exactly one matching
current inventory occurrence under the same scope, inventory revision,
provider, message type, and disposition. It SHALL NOT read or invent a body,
create EvidenceAnchors or semantic work packages, or dispatch Matter, person,
event, analysis, or projection owners. A deeper current content-fingerprint
SourceVersion with derived anchors/results SHALL never be replaced by this path.

The system SHALL expose a bounded reconciliation operation for legacy current
inventories whose metadata-only message owner is missing. Reconciliation SHALL
accept only a verified terminal, progressing Gmail page chain, order candidates
deterministically by object id, process an exclusive `after_object_id` plus a
limit from 1 through 500, and report selected, skipped, remaining, and next
cursor state. Each candidate SHALL recheck the exact current inventory and
coverage owner before writing. Exact replay SHALL be no-delta.

#### Scenario: Current metadata-only message lacks a SourceVersion
- **WHEN** a verified terminal page-chain member has one exact current metadata-only inventory and coverage owner but no current SourceVersion
- **THEN** the service SHALL register only its minimal metadata SourceVersion, mark only the source-version coverage pointer current, and leave evidence and semantic owners unchanged

#### Scenario: Metadata-owner reconciliation is paged
- **WHEN** more eligible messages remain after a bounded reconciliation batch
- **THEN** the service SHALL return the last selected object id as the next exclusive cursor and SHALL process only the requested finite prefix

#### Scenario: A deeper content observation is already current
- **WHEN** a selected metadata-only observation resolves to a current SourceVersion containing an authorized content fingerprint and derived anchors/results
- **THEN** the service SHALL preserve that SourceVersion and derived state byte-for-byte and SHALL NOT downgrade, duplicate, or invalidate its evidence

#### Scenario: Inventory or coverage ownership is not exact
- **WHEN** the occurrence is missing, stale, ambiguous, inactive, foreign-scope, non-message, or no longer metadata-only, or the supplied page chain is not terminal
- **THEN** the service SHALL skip or reject it without source, coverage, evidence, or semantic writes and SHALL expose the bounded mismatch count or terminal-chain error

#### Scenario: Metadata-owner reconciliation is retried
- **WHEN** the same terminal page chain, cursor, and limit are replayed
- **THEN** already current SourceVersions and coverage pointers SHALL remain no-delta without revision amplification

### Requirement: Gmail coverage follows one exact current tracked content scope
When a legacy current ObjectCoverage row still binds one exact Gmail
`metadata_only` occurrence but the same message is already present in one
current `tracked` inventory scope with licensed body or exact
`no_text_body` authority for the same authorized account, the
system SHALL expose a bounded, provider-read-free reconciliation owner. The
owner SHALL use stable object-id keyset pagination, recheck the bound and
target scope, inventory, policy, SourceVersion, and body or `no_text_body`
disposition inside one atomic compare-and-swap, preserve coverage history, and
write a minimized reconciliation receipt. It SHALL NOT compare revision
numbers across different scopes as though they share one counter, and SHALL
NOT treat inventory policy-rebase write time as provider-world recency.

#### Scenario: Exactly one tracked content scope is current
- **WHEN** the bound metadata-only occurrence, one same-account tracked occurrence, current policy, current SourceVersion, and current body or no-text disposition all match
- **THEN** the system SHALL switch authorization, inventory, source, extraction, evidence, and analysis coverage to that tracked scope as licensed, retain later-stage work for its original owners, and make exact replay no-delta

#### Scenario: Policy rebase wrote the metadata snapshot later
- **WHEN** a provider-read-free policy rebase created the bound metadata-only inventory record after the exact tracked content inventory record
- **THEN** the current body or no-text authority SHALL still license the tracked content successor, and maintenance write order SHALL NOT leave the message blocked

#### Scenario: More than one tracked scope can own the message
- **WHEN** two or more current tracked scopes contain the same Gmail message
- **THEN** the operation SHALL remain `blocked` with `tracked_scope_ambiguous`, preserve the existing coverage row, and SHALL NOT guess from scope ids or unrelated revision numbers

#### Scenario: The message body disposition is not current
- **WHEN** exactly one tracked scope exists but neither a current body receipt nor a current exact `no_text_body` disposition licenses the transition
- **THEN** the operation SHALL remain `pending`, preserve the current coverage row, and perform no provider read

#### Scenario: State changes during reconciliation
- **WHEN** any bound scope, target scope, inventory, policy, source, content receipt, or coverage input changes after selection
- **THEN** the atomic comparison SHALL return `stale`, commit no partial coverage switch, and permit a fresh bounded retry

### Requirement: Legacy current Gmail content proof can receive an exact minimized receipt
When a current tracked Gmail SourceVersion predates the content-receipt
contract but already retains a non-empty SHA-256 content fingerprint, a
positive derived byte count, and exact current evidence anchors for that same
source revision, one bounded provider-read-free owner MAY append the missing
`gmail_message_body` receipt. The receipt SHALL contain only the digest, byte
count, exact evidence ids, contract identity, and a declaration that no
provider read occurred. It SHALL NOT contain message body text, refetch Gmail,
create new evidence, infer content from metadata, or weaken the normal
current-scope reconciliation gates.

#### Scenario: Exact current digest and evidence prove the legacy content
- **WHEN** the registry-current tracked Gmail SourceVersion has a valid non-empty SHA-256 body fingerprint, positive byte count, and one or more current evidence anchors that bind that exact source revision
- **THEN** the owner SHALL append one minimized current content receipt, record `provider_read_performed=false`, and make exact replay no-delta

#### Scenario: Metadata or stale evidence is the only proof
- **WHEN** the SourceVersion has no valid body digest, no positive byte count, no current exact evidence anchors, or any anchor binds another revision
- **THEN** the owner SHALL leave the receipt missing with a typed pending or blocked disposition and SHALL NOT read the provider or fabricate a receipt

### Requirement: Gmail body continuation is exact, bounded, and model-independent
After a private Gmail inventory has registered current message metadata, the
system MAY import connector-read message bodies through an exact continuation
manifest. The raw manifest bytes SHALL determine the manifest SHA-256 and
private identity. Each manifest row SHALL contain exactly `message_id`,
`source_page_identity`, a positive 1-based `batch_number`, and
`prior_body_fingerprint`. The prior fingerprint SHALL be either empty when no
body has ever been retained for that current metadata owner or the exact
current `sha256:<64 lowercase hex>` body fingerprint. Each batch SHALL contain
at most 20 unique messages. The connector result SHALL contain exactly
`artifact_type`, `manifest_sha256`, `batch_number`, and `messages`. Each
available message SHALL contain exactly `message_id`, a non-empty `body`, and
`content_status=available`. Each connector raw-MIME recovery result that found
no textual MIME part SHALL contain exactly `message_id`, an exact empty
`body`, `content_status=no_text_body`, and a
`raw_recovery_proof_identity` matching `sha256:<64 lowercase hex>`. The proof
identity SHALL equal SHA-256 over the byte domain
`matters.gmail.raw-mime-recovery.no-text-body.v1\0` followed by the canonical
UTF-8 JSON row containing exactly `message_id`, `body=""`,
`content_status="no_text_body"`, and `disposition="no_text_body"`, with sorted
keys, separators `,` and `:`, no optional whitespace, and unescaped Unicode.
The importer SHALL recompute and compare that identity; syntactically valid but
mismatched proof text is not sufficient.

The importer SHALL validate the complete selected batch and all current Gmail
metadata owners before writing. It SHALL reject a hash or batch mismatch,
foreign/missing/duplicate message, empty available body, blocked/unsupported
status, no-text result with content, no-text result without the exact derived
raw-recovery proof identity, over-budget batch, or any additional title,
address, header, cursor, token, or other field.

An available result SHALL use the body only as transient extraction input and
write a minimized Gmail read receipt, pointer/fingerprint SourceVersion, exact
anchor coordinates/digests, declared durable derived outputs, and current
coverage pointers before removing the complete body from connector staging. A
`no_text_body` result SHALL write only one explicit
content-disposition owner plus owned terminal `not_applicable`
extraction/evidence/analysis coverage pointers over the already-current
metadata SourceVersion. It SHALL NOT create a durable complete-body SourceVersion,
EvidenceAnchor, semantic work package, or synthetic empty-text evidence; the
metadata SourceVersion SHALL remain available to relationship and chronology
owners. Neither branch SHALL mutate Gmail, widen authorization, create or
change a Matter/person/event/projection, invoke a model, require a model name,
or call a provider API. Exact retries SHALL be no-delta; interruption MAY leave
a completed prefix, and replaying the exact batch SHALL safely resume it.
A complete body that differs from the current body SHALL be accepted only when
the manifest's `prior_body_fingerprint` exactly equals the current stored body
fingerprint. That compare-and-replace operation SHALL append a new immutable
SourceVersion, preserve prior SourceVersion and anchor history, bind all new
anchors and derived work to the replacement revision, and never reinterpret an
arbitrary differing body as a retry.

#### Scenario: Exact continuation batch is imported
- **WHEN** one result has the exact current manifest hash and batch membership, every body is available and non-empty, and every message has one current Gmail metadata SourceVersion plus a current occurrence/coverage row
- **THEN** the system SHALL append or reuse the pointer/fingerprint SourceVersion, exact body-anchor coordinates/digests, declared derived outputs, minimized read receipt, and coverage pointers, then remove the complete body from staging without changing the mailbox or any semantic owner

#### Scenario: Continuation result contains excess private fields
- **WHEN** the top level or any message includes a title, subject, sender, recipient, header, cursor, token, or another undeclared field
- **THEN** the system SHALL reject the entire batch before writes

#### Scenario: A complete body is refreshed from an exact prior fingerprint
- **WHEN** the selected message has a current non-empty body, the connector returns a different complete body, and the manifest row binds the exact current `prior_body_fingerprint`
- **THEN** the system SHALL append one replacement SourceVersion and its exact current anchors, preserve the former SourceVersion and anchors as history, and advance only the dependents bound to the replacement revision

#### Scenario: A differing body is not bound to the exact current predecessor
- **WHEN** the connector returns a differing complete body while `prior_body_fingerprint` is empty, malformed, stale, or names another body
- **THEN** the system SHALL reject the entire batch before writes and SHALL NOT overwrite, alias, or silently accept the differing body as a retry

#### Scenario: Raw MIME recovery proves no textual body
- **WHEN** one exact manifest member has an empty body, `content_status=no_text_body`, one exact connector raw-recovery proof identity, current metadata ownership, and no current non-empty body
- **THEN** the system SHALL write one content-disposition owner, keep the metadata SourceVersion usable, mark extraction, evidence, and analysis terminal `not_applicable` under their declared owners, and create no SourceVersion or EvidenceAnchor

#### Scenario: No-text claim is unproven or contains content
- **WHEN** `content_status=no_text_body` has a non-empty body, omits or malforms its raw-recovery proof identity, conflicts with an existing non-empty body, or adds another field
- **THEN** the system SHALL reject the entire batch before writes and SHALL NOT reinterpret it as available content

#### Scenario: Continuation membership or identity differs
- **WHEN** the manifest hash, batch number, exact message-id set, uniqueness, or current metadata-owner binding differs
- **THEN** the system SHALL reject the entire batch before writes and SHALL NOT substitute a nearby message or broader Gmail query

#### Scenario: Continuation is retried or resumed
- **WHEN** an identical batch is replayed after success or after interruption
- **THEN** already current messages SHALL remain no-delta and only the unfinished exact messages SHALL advance, without duplicate SourceVersions, receipts, anchors, derived outputs, staging bodies, or coverage revisions

#### Scenario: A deployment changes AI models
- **WHEN** the local Codex execution profile changes its model or no AI capability is available
- **THEN** the deterministic Gmail body continuation contract and import result SHALL remain unchanged because this leaf invokes no model or direct provider API

### Requirement: Inventories have durable freshness revisions
The system SHALL persist directory and mailbox inventory snapshots and derive
an explicit change set containing added, modified, moved, deleted, unchanged,
and newly reachable occurrences using provider occurrence identity and
policy-approved private metadata.

#### Scenario: Previously inventoried folder changes
- **WHEN** a later authorized scan observes an added, modified, moved, or deleted occurrence
- **THEN** the system SHALL append a new inventory revision and mark the affected occurrence's prior triage, extraction, analysis, evidence, and projection dependencies stale

#### Scenario: Repeated scan has no change
- **WHEN** the occurrence identity and relevant metadata match the current inventory revision
- **THEN** the system SHALL record no-delta and SHALL NOT duplicate triage, extraction, analysis, or source versions

#### Scenario: Tracking policy changes without source change
- **WHEN** the current tracking policy changes for an otherwise unchanged occurrence
- **THEN** the system SHALL mark the affected triage decision stale and re-evaluate classification without fabricating a content change

### Requirement: Incremental refresh is dependency-bounded
After a current inventory change the system SHALL reprocess only changed
occurrences and their declared dependents unless a policy or model revision
explicitly invalidates a larger finite set.

#### Scenario: One file changes in a large root
- **WHEN** one occurrence is modified and all other occurrence fingerprints remain current
- **THEN** the system SHALL re-triage that occurrence and its dependents without resubmitting every unchanged item

#### Scenario: Deleted item was tracked
- **WHEN** a tracked occurrence is confirmed deleted
- **THEN** the system SHALL append a tombstone and invalidate its dependents without attempting to read the missing content

### Requirement: Local reads bind metadata and stable content
The system SHALL bind a local occurrence to normalized contained path identity,
file identity when available, size, modification metadata, read policy, and
content identity. It SHALL NOT register success when those stability inputs
change during the read.

#### Scenario: Local file changes during extraction
- **WHEN** file identity, size, or modification metadata differs between the validated pre-read and post-read observations
- **THEN** the system SHALL discard the unstable extraction, record `changed_during_read`, and retry only under a current authorization

#### Scenario: Renamed file retains stable content
- **WHEN** an already registered file occurrence is renamed within an authorized root without content change
- **THEN** the system SHALL preserve occurrence history, record the path metadata revision, and SHALL NOT claim a new content version

### Requirement: Compound sources preserve parent-child provenance
Documents, mail threads, messages, attachments, spreadsheets, images, and
bounded archive members SHALL retain explicit parent-child occurrence and
version relationships.

#### Scenario: Gmail attachment is registered
- **WHEN** an authorized message has an in-policy attachment
- **THEN** the system SHALL register the message and attachment as distinct private occurrences linked by an attachment relationship

#### Scenario: Document page is extracted
- **WHEN** a PDF or Office document yields page, sheet, slide, embedded-image, or text-part artifacts
- **THEN** each artifact SHALL reference the exact parent SourceVersion and extractor identity

### Requirement: Placeholder and quarantined occurrences retain provenance
The system SHALL preserve the occurrence metadata and disposition for
`cloud_placeholder`, `unsupported`, `quarantined`, `metadata_only`, and `inaccessible`
items without inventing content identity.

#### Scenario: Cloud placeholder is inventoried
- **WHEN** a cloud-backed path is visible but stable content is unavailable
- **THEN** the occurrence SHALL retain provider/path metadata and placeholder disposition without a fabricated content hash

### Requirement: Private Gmail snapshots preserve complete read provenance without durable bodies
Every Gmail message, thread relation, and attachment read under the progressive
first-run grant SHALL be registered as an immutable private source occurrence
with account-scoped connector identity, provider identity, relevant timestamps,
page/cursor authorization, content fingerprint, source locator, and
minimization disposition. Complete message bodies and raw MIME SHALL be
transient connector input and SHALL NOT remain in the durable catalog after
successful extraction.

#### Scenario: An authorized Gmail message is registered
- **WHEN** the Gmail adapter submits one authorized message from a committed page
- **THEN** the service SHALL preserve its private pointer/fingerprint SourceVersion, anchors, and derived understanding under the external private root without retaining raw mail after commit or copying any private identity into the repository

#### Scenario: A signed link or private code is present
- **WHEN** message content contains transport-only signed links, redemption codes, booking references, or similar protected values not needed for the modeled claim
- **THEN** the minimized analysis payload SHALL replace those values with explicit redaction markers while the source locator/fingerprint, bounded derived state, and minimization disposition remain in the private domain

#### Scenario: A bounded Gmail read resumes at the next content batch
- **WHEN** a frozen authorized page is processed with a stable content offset and limit
- **THEN** the selected tracked messages SHALL be deterministic, earlier completed messages SHALL retain current extraction and evidence, and the resume SHALL NOT duplicate or regress prior analysis work

#### Scenario: A later Gmail page is not a complete mailbox inventory
- **WHEN** an authorized Gmail query returns a non-terminal page after one or more earlier pages
- **THEN** the current query inventory SHALL accumulate the new page, absence from that page SHALL NOT delete or stale prior-page mail, and only a terminal complete inventory MAY confirm removals

#### Scenario: A page supplies both message metadata and body content
- **WHEN** the connector page includes the authorized complete body for a tracked message
- **THEN** the content-observation envelope SHALL be the SourceVersion authority for that pass, the complete body SHALL remain transient, and a metadata-only envelope SHALL NOT overwrite the resulting fingerprint/derived authority before or after extraction

### Requirement: Visual derivatives retain exact private lineage
Every thumbnail, embedded-image extraction, document page/slide/sheet preview,
OCR overlay, or other visual derivative SHALL reference the exact parent
SourceVersion, precise region/page anchor, renderer identity and version,
generation policy, safety disposition, private blob identity, and currentness
state. Visual derivatives SHALL remain private, rebuildable, reclaimable under
an explicit retention policy, and SHALL NOT become a second source authority.

#### Scenario: Document preview is generated
- **WHEN** a current authorized document is rendered into a real Images-gallery derivative
- **THEN** the derivative SHALL bind the exact source revision and page/slide/sheet/region and SHALL become stale when the source, renderer, policy, authorization, or anchor changes

#### Scenario: Visual source is deleted or revoked
- **WHEN** the parent image or document source is deleted, revoked, superseded, or no longer safe to display
- **THEN** every dependent gallery derivative and real-image gallery projection SHALL become stale or unavailable before another UI projection is published, while an unrelated current generated hero remains governed by its Matter theme and safety dependencies

### Requirement: Generated Matter heroes are not source derivatives
A generated Matter hero SHALL bind the current Matter semantic identity,
hierarchy/theme fingerprint, generation-policy revision, private generation
brief fingerprint, execution identity, safety disposition, and generated private
blob identity. It SHALL NOT receive a SourceVersion, EvidenceAnchor, source
assertion, or evidentiary relationship. Source images and document previews
SHALL remain available only through the real Images/evidence path and SHALL NOT
become a hero fallback.

#### Scenario: Hero generation completes
- **WHEN** a privacy-minimized generation package returns one valid photorealistic documentary-style image for a current root Matter
- **THEN** the system SHALL persist it as a private presentation asset under `MATTERS_HOME` and SHALL NOT register it as source content or evidence

#### Scenario: A real image is related to the Matter
- **WHEN** an authorized photo, attachment, embedded image, or document preview is current and relevant
- **THEN** it MAY appear in the Images gallery with exact lineage but SHALL NOT enter the generated-hero selection or fallback path

### Requirement: Overlapping registered roots produce one selection plan per occurrence
When authorized filesystem roots overlap, inventory scope membership MAY name
the same physical occurrence more than once, but current content selection and
source identity SHALL be deduplicated by the stable occurrence id. Folder,
group-chain, and source-neighborhood context SHALL be the union of current
licensed scope context and SHALL NOT become a second Source identity.

#### Scenario: A parent root and nested root both register one file
- **WHEN** the bounded content-selection rebase visits both scope memberships
- **THEN** it SHALL scan both registered memberships, publish one current selection plan and one Source identity for the occurrence, preserve the complete licensed neighborhood context, and SHALL NOT create duplicate extraction or AI work

#### Scenario: The overlapping-root rebase is repeated
- **WHEN** the same inventory, policy, and source metadata are current
- **THEN** the system SHALL return the same plan identity and SHALL write no duplicate current plan
