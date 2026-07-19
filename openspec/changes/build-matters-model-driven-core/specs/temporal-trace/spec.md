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

#### Scenario: Trace analysis proposes an ordering
- **WHEN** an agent operation proposes an event order that lacks a current anchor for one event
- **THEN** the system SHALL retain the proposed order with a TemporalGap and SHALL NOT publish it as canonical chronology
