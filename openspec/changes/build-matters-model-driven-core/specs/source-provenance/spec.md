## ADDED Requirements

### Requirement: Original source content is immutable
The system SHALL preserve user-supplied or provider-supplied source content
without AI rewriting and SHALL register changes as new source versions.

#### Scenario: Source content changes
- **WHEN** pasted text, a local file, a document, an image, a Gmail item, an attachment, or hydrated cloud content differs from the current source version
- **THEN** the system SHALL create a new immutable version linked to its predecessor

#### Scenario: AI proposes normalized wording
- **WHEN** an AI or local skill proposes a summary or normalized wording
- **THEN** the proposal SHALL be stored separately and SHALL NOT replace the immutable source content

### Requirement: Content and metadata identities are separate
The system SHALL calculate and retain separate identities for content and
metadata changes and SHALL keep provider occurrence identity separate from
deduplicated content identity.

#### Scenario: Only metadata changes
- **WHEN** source metadata changes while source content remains identical
- **THEN** the system SHALL record a metadata revision without claiming a content revision

#### Scenario: Identical content appears in two places
- **WHEN** two authorized local paths or mail attachments contain identical bytes
- **THEN** the system SHALL retain two occurrence identities while allowing them to reference one deduplicated immutable content object

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
- **THEN** the system SHALL create a tombstone revision and invalidate evidence that depended on the missing content

### Requirement: Private source state survives restart
The system SHALL persist immutable source bodies, source/version identities,
metadata, discovery cursors, per-item dispositions, tombstones, and current
references under the configured external `MATTERS_HOME` root.

#### Scenario: Service restarts during discovery
- **WHEN** the service restarts with the same authorized external `MATTERS_HOME` after a discovery page was committed
- **THEN** it SHALL recover SourceVersions, dispositions, and the durable cursor without reading source data from the Git repository or duplicating the committed page

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

### Requirement: Private Gmail snapshots preserve complete read provenance
Every Gmail message, thread relation, and attachment read under the progressive
first-run grant SHALL be registered as an immutable private source occurrence
with account-scoped connector identity, provider identity, relevant timestamps,
page/cursor authorization, content identity, and minimization disposition.

#### Scenario: An authorized Gmail message is registered
- **WHEN** the Gmail adapter submits one authorized message from a committed page
- **THEN** the service SHALL preserve its private SourceVersion and anchors under the external private root without copying raw mail or a private content hash into the repository

#### Scenario: A signed link or private code is present
- **WHEN** message content contains transport-only signed links, redemption codes, booking references, or similar protected values not needed for the modeled claim
- **THEN** the minimized analysis payload SHALL replace those values with explicit redaction markers while the immutable private source and minimization disposition remain in the private domain

### Requirement: Visual derivatives retain exact private lineage
Every thumbnail, embedded-image extraction, document page/slide/sheet preview,
OCR overlay, or other visual derivative SHALL reference the exact parent
SourceVersion, precise region/page anchor, renderer identity and version,
generation policy, safety disposition, private blob identity, and currentness
state. Visual derivatives SHALL remain private and SHALL NOT become a second
source authority.

#### Scenario: Document preview is generated
- **WHEN** a current authorized document is rendered into an eligible visual candidate
- **THEN** the derivative SHALL bind the exact source revision and page/slide/sheet/region and SHALL become stale when the source, renderer, policy, authorization, or anchor changes

#### Scenario: Visual source is deleted or revoked
- **WHEN** the parent image or document source is deleted, revoked, superseded, or no longer safe to display
- **THEN** every dependent visual candidate and current Matter visual decision SHALL become stale or unavailable before another UI projection is published
