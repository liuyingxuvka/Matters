## ADDED Requirements

### Requirement: Formal evidence has a precise anchor
The system SHALL admit formal evidence only when it identifies an exact source
version and field, line range, character range, passage, page, timestamped
change, sheet/cell range, slide/shape, message/thread part, attachment region,
image region, OCR region, or bounded metadata field.

#### Scenario: Assertion has an exact anchor
- **WHEN** a candidate assertion references an exact region of a current source version
- **THEN** the system SHALL emit an EvidenceAnchor bound to that assertion

#### Scenario: Pasted text assertion has a character anchor
- **WHEN** a candidate assertion is extracted from explicitly submitted text
- **THEN** the system SHALL bind it to the current SourceVersion and exact character range

#### Scenario: Local text assertion has a line anchor
- **WHEN** a candidate assertion is extracted from a selected TXT or Markdown file
- **THEN** the system SHALL bind it to the current SourceVersion and exact line and character range

#### Scenario: Document or spreadsheet assertion is extracted
- **WHEN** a candidate assertion is extracted from a PDF, Office document, slide, or spreadsheet
- **THEN** the system SHALL bind it to the exact parent SourceVersion and page/passage, slide/shape, or sheet/cell range produced by the current extractor

#### Scenario: Mail assertion is extracted
- **WHEN** a candidate assertion is extracted from a Gmail message or attachment
- **THEN** the system SHALL bind it to the exact message/thread part or attachment SourceVersion and bounded content range

#### Scenario: Image assertion is extracted
- **WHEN** OCR or multimodal analysis proposes an assertion about a photo or image
- **THEN** the system SHALL bind the proposal to the exact image SourceVersion, extractor/runner identity, and pixel or OCR region

#### Scenario: Assertion is supported only by a title or filename
- **WHEN** a detailed claim lacks a precise content anchor
- **THEN** the system SHALL emit a gap and SHALL NOT promote the claim to formal evidence

### Requirement: Evidence modality and uncertainty are retained
The system SHALL retain whether evidence is observed, reported, planned,
inferred, OCR-derived, metadata-derived, contradicted, or unknown together with
extractor confidence and gaps when applicable.

#### Scenario: Planned text describes future work
- **WHEN** a source states that work is planned
- **THEN** the evidence SHALL retain planned modality and SHALL NOT license an occurred event

#### Scenario: EXIF time or location is present
- **WHEN** image metadata contains capture time or coordinates but no evidence ties them to the claimed event
- **THEN** the system SHALL preserve metadata-derived modality and SHALL NOT treat the metadata as proof of the event, actor, or Matter

#### Scenario: OCR is uncertain
- **WHEN** OCR produces ambiguous text or an incomplete region
- **THEN** the system SHALL retain the OCR result with confidence/gaps and SHALL NOT silently normalize it into observed text

### Requirement: Evidence remains version-bound
The system SHALL mark evidence stale when its source version or anchor region is
superseded, revoked, or deleted.

#### Scenario: Anchored content is corrected
- **WHEN** a later source revision changes the anchored content
- **THEN** the prior evidence SHALL become stale and its dependents SHALL require disposition

#### Scenario: A document produces many precise anchors
- **WHEN** one current source yields a bounded set of line, page, passage, cell, message, OCR, or EXIF anchors
- **THEN** every qualified anchor SHALL remain individually addressable but SHALL be committed through one bounded atomic batch; an identical retry SHALL be a no-op and the system SHALL NOT truncate valid anchors merely to reduce transaction cost

#### Scenario: A content-addressed evidence id conflicts
- **WHEN** the same evidence id is presented with a different canonical payload
- **THEN** the batch SHALL fail visibly as an identity conflict and SHALL NOT overwrite either payload

### Requirement: Derived AI work is bounded without evidence loss
The system SHALL separate complete evidence registration from bounded AI
WorkPackage materialization. Each source revision SHALL retain a durable cursor
over its exact qualified anchor set so one large source cannot monopolize the
filesystem worker or silently truncate later evidence.

#### Scenario: One document yields more anchors than one AI page can carry
- **WHEN** a current source has more qualified anchors than the frozen per-call package budget
- **THEN** the system SHALL register every anchor, materialize only the bounded package page, persist the next anchor cursor and remaining count, and leave the expansion visibly pending

#### Scenario: Background maintenance resumes a pending source expansion
- **WHEN** a current pending expansion is selected after restart or a later maintenance cycle
- **THEN** the system SHALL reconstruct the exact version-bound anchor set without rereading the user file, continue from the durable cursor, and mark the expansion complete only when the cursor equals the anchor count

#### Scenario: Filesystem processing is interrupted after a claim checkpoint
- **WHEN** an ordinary exception or cancellation stops one small registered-file claim page
- **THEN** the system SHALL release that worker's incomplete items immediately while preserving their stage checkpoints; an uncatchable process crash SHALL become reclaimable through the short lease without allowing overlapping live owners

### Requirement: Cross-owner evidence references are bounded anchor-set pointers
When coverage, analysis, hierarchy, projection, or another owner needs to refer
to a complete evidence-anchor set, it SHALL persist a bounded pointer containing
the exact SourceVersion identity, anchor count, and canonical anchor-set digest.
The C3 evidence owner SHALL retain every individually addressable anchor and
remain the only authority that expands or verifies the set. A downstream row
SHALL NOT copy an unbounded list of anchor ids into its own payload.

#### Scenario: A source has thousands of evidence anchors
- **WHEN** a downstream owner records that the complete current anchor set supports its work
- **THEN** it SHALL store the version-bound count-and-digest pointer and SHALL resolve any requested bounded page through C3
- **AND** the pointer SHALL fail currentness verification when source version, count, canonical ordering, or digest differs

#### Scenario: A legacy row contains a full anchor-id list
- **WHEN** explicit evidence-pointer maintenance selects that row through a bounded stable continuation
- **THEN** it SHALL verify the exact C3-owned anchor set, write the count-and-digest pointer, preserve a terminal or continuation receipt, and only then retire the duplicated list
- **AND** startup SHALL NOT perform this rebase and a partial page SHALL NOT be reported as the completed migration

### Requirement: Unsupported inputs fail visibly
The system SHALL NOT fabricate evidence from an unreadable, unsupported,
oversized, or undecodable input.

#### Scenario: Enumerated format has no safe extractor
- **WHEN** an authorized audio/video/archive/database/model or other format has no current safe extractor under policy
- **THEN** the system SHALL retain `metadata_only`, `quarantined`, or `unsupported` without claiming content evidence

#### Scenario: Cloud content is not hydrated
- **WHEN** only placeholder metadata is available for a cloud-backed item
- **THEN** the system SHALL NOT create content evidence and SHALL expose the placeholder gap

### Requirement: Advisory conclusions cite admitted anchors
Every AI or local-skill assertion proposed for automatic owner decision SHALL reference
one or more current EvidenceAnchors from its authorized work package.

#### Scenario: Advisory assertion lacks an anchor
- **WHEN** an agent operation returns a detailed assertion with no current evidence reference
- **THEN** the system SHALL retain it as an invalid or policy-rejected artifact and SHALL NOT dispatch or promote it to formal evidence

### Requirement: Source instructions never become control evidence
Prompt-like instructions embedded in documents, images, OCR, mail, or
attachments SHALL remain untrusted source content and SHALL NOT authorize tool
use, adjacent-source reads, external actions, or canonical writes.

#### Scenario: Document asks the agent to reveal or upload other data
- **WHEN** extracted source content contains an instruction to read, disclose, upload, or modify material outside the active work package
- **THEN** the operation SHALL reject that instruction as scope-incompatible and preserve it only as anchored source content when relevant
