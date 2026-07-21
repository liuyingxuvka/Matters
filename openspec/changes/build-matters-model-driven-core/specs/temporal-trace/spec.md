## ADDED Requirements

### Requirement: Events retain temporal modality
The system SHALL record source record time, claimed event time, actor, object,
and modality for every event candidate.

#### Scenario: Future meeting is mentioned
- **WHEN** evidence describes a meeting scheduled in the future
- **THEN** the system SHALL create a planned event candidate and SHALL NOT describe it as occurred

#### Scenario: File modification time is available
- **WHEN** a selected file has a filesystem modification time but its content does not state an event time
- **THEN** the system SHALL retain the metadata time separately and SHALL NOT treat it as the event occurrence time

### Requirement: Start, clue, record, processing, and event times remain distinct
The system SHALL preserve Matter Start time, source-record time, claimed/
observed event time, processing time, and `latest_meaningful_clue_at` as
separate typed fields. Start time drives the explicit Start time filter.
Meaningful-clue time drives dynamic root-card order. Processing or scan time
SHALL drive neither.

#### Scenario: A message reports progress on an older Matter
- **WHEN** a new received message contains a material progress clue for a Matter whose Start time is earlier
- **THEN** the Matter SHALL retain its original Start time, use the message's user-world clue time for activity ordering, and SHALL NOT use later analysis completion time as either value

#### Scenario: A completed Matter receives a new material record
- **WHEN** a current material clue is received for a completed Matter
- **THEN** the Matter MAY bubble by clue time while its lifecycle state remains completed until the lifecycle owner licenses another state

### Requirement: Matter Start time is the earliest traceable evidence boundary
For every admitted Matter, C5 SHALL derive one current Start time from the
earliest parseable user-world timestamp across all evidence currently related
to that Matter. The candidate set SHALL include every claimed and record time
from its typed Events plus source-authored, source-created, source-modified,
message-sent, message-received, provider-observed, and Codex-project first-
recorded times retained by the exact related SourceVersions. It SHALL compare
all valid candidates rather than preferring one field and discarding an
earlier candidate from another field.

The selected boundary SHALL preserve a typed basis and provider class so its
origin remains auditable without exposing a private path or connector id.
Processing, scan, registration, extraction, analysis, migration, deadline,
due, expiry, and generated-Hero times SHALL NOT enter this candidate set.

#### Scenario: A cover letter predates the first application message
- **WHEN** a job-search Matter has no explicit “job search began” statement, a related cover-letter file was created or modified before its first application email, and both source times are current
- **THEN** the file time SHALL be the current Start time with a filesystem-source basis
- **AND** the absence of an explicit natural-language start statement SHALL NOT leave the card at an unknown Start time

#### Scenario: A message has no event date
- **WHEN** a related Gmail message contains no explicit event date but retains a valid sent, received, or provider-observed message time
- **THEN** that message time SHALL remain a Start-time candidate and a source-record time
- **AND** it SHALL NOT be relabeled as an observed occurrence inside the Timeline

#### Scenario: A later scan finds earlier evidence
- **WHEN** the current Matter already has a Start time and newly covered current evidence supplies an earlier licensed candidate
- **THEN** C5 SHALL append a new Start-boundary revision, move the Start time earlier, refresh its year/range filter projection, and retain the superseded basis in history
- **AND** catalog activity order SHALL remain governed by `latest_meaningful_clue_at`

#### Scenario: Only processing time is available
- **WHEN** no related Event or SourceVersion contains a valid user-world timestamp but registration or analysis has a current processing timestamp
- **THEN** Start time SHALL remain unknown with an explicit temporal gap
- **AND** processing time SHALL NOT be used as a fallback

### Requirement: Later records do not erase contradictions
The system SHALL consider supersession, conflicting evidence, and negative
evidence when identifying the current temporal interpretation.

#### Scenario: Done is followed by reopen
- **WHEN** a later record reopens an item and reports an unresolved blocker
- **THEN** the system SHALL preserve both events and emit a current `temporal_conflict_preserved` interpretation with confidence and alternatives, without waiting for user confirmation

### Requirement: Missing temporal support remains visible
The system SHALL emit a TemporalGap when an important ordering or occurrence
claim lacks licensed evidence.

#### Scenario: Start time is inferred from assignment
- **WHEN** assignment is the only evidence offered for work starting
- **THEN** the system SHALL retain the assignment event and emit a gap for actual start

### Requirement: AI temporal interpretations remain evidence-bound candidates
The system SHALL preserve AI and ResearchGuard temporal-trace interpretations
as advisory candidates until current evidence licenses the modality and
ordering.

Observed, reported, and planned source statements SHALL retain those exact
modalities. An `ai_inferred` Event, WorkItem, lifecycle, or outcome candidate
MAY fill only a necessary gap whose target time is not later than the frozen
analysis time. It SHALL bind the analysis time, past target time, confidence,
supporting and counter-signals, alternatives, contradiction triggers, and a
revisable disposition. A future expectation SHALL NOT enter the temporal trace
as an occurred or AI-inferred Event; it belongs only to the separate,
advisory Situation/World Model prediction lane.

#### Scenario: Trace analysis proposes an ordering
- **WHEN** an agent operation proposes an event order that lacks a current anchor for one event
- **THEN** the system SHALL retain the proposed order with a TemporalGap and SHALL NOT publish it as canonical chronology

#### Scenario: Source explicitly reports a future departure or boarding pass
- **WHEN** current source evidence reports a future departure time or records that a boarding pass was issued
- **THEN** the departure SHALL remain `planned` and the issuance SHALL remain `observed` or `reported`
- **AND** neither record SHALL be relabeled `ai_inferred`

#### Scenario: Necessary past activity lacks a final observation
- **WHEN** a booked or admitted activity is already in the past, current covered evidence supports it, and no licensed completion observation or material contradiction is current
- **THEN** C11 MAY project a localized, confidence-bearing `ai_inferred` historical-gap candidate
- **AND** it SHALL remain revisable, visibly distinct from observed completion, and bounded by the exact covered evidence scope

#### Scenario: Candidate target lies after analysis time
- **WHEN** an Event, WorkItem, lifecycle, or outcome candidate marked `ai_inferred` targets a future time
- **THEN** result validation SHALL reject the candidate from the canonical temporal lanes
- **AND** the caller MAY re-express it only as a testable Situation/World Model prediction

### Requirement: Current-contract rebase invalidates stale temporal owner outputs
When a persisted analysis package is replaced by the current analysis
contract, the system SHALL preserve the former package, result, finding, and
owner-output history but SHALL append an exact invalidation for every
non-empty former owner output. C5, the hierarchy inventory, the object browser,
and the Situation Graph SHALL exclude invalidated temporal outputs until one
active current-contract result owns the same output reference again. A
projection that filters such stale outputs SHALL expose partial coverage and
`analysis_output_replacement_pending`; it SHALL NOT present missing stale
output as proof that the underlying real-world event did not happen.

#### Scenario: A stale future inference is rebased
- **WHEN** an older semantic package emitted a temporal output that the current contract no longer licenses and the package is rebased
- **THEN** the old package, result, finding, and output SHALL remain auditable in history while the temporal event disappears from current cards, timelines, hierarchy inventory, and Situation Graph
- **AND** affected graph coverage SHALL remain partial with `analysis_output_replacement_pending`

#### Scenario: A current replacement reuses the same owner output
- **WHEN** a current-contract result passes validation and actively owns the exact formerly invalidated output reference
- **THEN** the output SHALL become current again without deleting its invalidation history
- **AND** current projections MAY consume it only under the new package and result identity

### Requirement: Parent timelines summarize descendant milestones without duplication
A parent Matter timeline SHALL include only current important descendant
milestones with the originating child path. Complete small events SHALL remain
reachable in their child Matter and SHALL NOT be copied into multiple canonical
event records.

#### Scenario: Company child receives an interview invitation
- **WHEN** the invitation is important to the root job-search chronology
- **THEN** the parent timeline MAY project the existing event once with the company child label while the authoritative event remains owned by the child

#### Scenario: Child contains routine email events
- **WHEN** several routine messages do not change a parent milestone
- **THEN** the parent timeline SHALL omit them while the child timeline retains them

### Requirement: Logical event identity and supersession prevent duplicate timelines
Every Event SHALL retain one stable `logical_event_key` independent from the
changing set of SourceVersions, EvidenceAnchors, wording, extraction runs, and
AI revisions that describe it. A replacement SHALL name the exact
`supersedes_event_id`; one current projection per logical key SHALL own the
ordinary Timeline row while prior revisions and material conflicting
interpretations remain on demand.

#### Scenario: The same ticket purchase is extracted twice
- **WHEN** two current SourceVersions or analysis revisions describe the same purchase occurrence, actor, object, and licensed event boundary
- **THEN** C5 SHALL retain both provenance histories under one logical event key and SHALL project one current purchase row

#### Scenario: A later source corrects an event time
- **WHEN** a later licensed revision corrects the time or wording of one logical event
- **THEN** the new Event revision SHALL supersede the former revision, the Timeline SHALL show the current interpretation once, and the former value SHALL remain visible only in on-demand history

#### Scenario: Two interpretations materially conflict
- **WHEN** current evidence supports incompatible times or outcomes for one logical event
- **THEN** C5 SHALL project one conflict-preserved Timeline row with alternatives rather than two unexplained duplicate peer rows

### Requirement: Observation-time correction uses exact historical provenance
When a current activity row was incorrectly derived from a future due,
deadline, or claimed time, C5 SHALL append a correction clue using the best
exact observation time from the source revision cited by the evidence anchor
or from a current typed event. It SHALL NOT substitute the latest source
revision when the evidence names an older revision.

#### Scenario: A historical source revision contains the observation time
- **WHEN** the current activity points to a future due time and its evidence anchor names an older SourceVersion with a valid provider observation timestamp
- **THEN** C5 SHALL append a superseding correction clue at that historical observation time, preserve the due time as a claimed/planned temporal field, and refresh the affected Matter and ancestors

#### Scenario: Canonicalization is completed after the first correction
- **WHEN** the same corrected clue is already current for the source Matter but a canonical Matter projection is late-bound later
- **THEN** the correction owner SHALL project that exact clue to the canonical Matter without duplicating the clue or reusing the future due time

#### Scenario: No valid observation time exists
- **WHEN** neither the exact source revision nor a current typed event supplies a parseable observation time
- **THEN** the repair SHALL leave activity unchanged, expose the unresolved temporal gap, and SHALL NOT use processing time as evidence

### Requirement: Material descendant clues invalidate the parent narrative without changing activity authority
When a material clue changes a current child Matter, C5 SHALL append a
parent-narrative refresh trigger bound to the clue, child, and current ancestor
path. The trigger SHALL reuse the clue's user-world observation time for
activity authority and SHALL NOT use later AI narrative generation time to
reorder the parent.

#### Scenario: A child receives a new material clue
- **WHEN** the clue changes the evidence-supported project-wide understanding of a current parent
- **THEN** C5 SHALL retain the clue as activity authority and enqueue one idempotent parent-narrative refresh trigger for each affected ancestor

#### Scenario: Narrative wording changes without a new clue
- **WHEN** AI produces a clearer parent overview from the same bound children, projections, and evidence
- **THEN** the overview MAY receive a new narrative revision but the Matter title, lifecycle state, latest meaningful clue time, activity order, and generated-hero identity SHALL remain unchanged

### Requirement: Current Matters receive a bounded activity-time reconciliation
C5 SHALL expose one bounded, resumable owner that revisits current canonical
Matters, resolves activity from the exact admitted SourceVersion or current
inventory occurrence, applies the existing historical observation-time repair,
and reports current versus unresolved activity without using scan, processing,
analysis, or presentation time.

#### Scenario: A current Matter lacks activity but its admitted source has user-world time
- **WHEN** the bounded reconciliation visits a current Matter whose exact admitted source or current inventory occurrence contains a licensed observed, received, created, modified, authored, or sent time
- **THEN** C5 SHALL append the current material clue at that source time, refresh affected ancestors, and report the Matter as current

#### Scenario: No licensed source activity time is available
- **WHEN** the bounded reconciliation cannot resolve a licensed user-world time from the Matter's exact current evidence
- **THEN** it SHALL preserve the missing activity gap, report the Matter as unresolved, and SHALL NOT substitute the reconciliation run time
