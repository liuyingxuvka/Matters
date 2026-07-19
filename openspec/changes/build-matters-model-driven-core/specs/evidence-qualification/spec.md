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
