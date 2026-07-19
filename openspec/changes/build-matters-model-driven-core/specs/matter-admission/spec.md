## ADDED Requirements

### Requirement: A source is not automatically a Matter
The system SHALL treat every authorized input as a Source before considering
source-only, candidate, uncertainty-preserved, conflict-preserved,
not-applicable, blocked, or admitted Matter outcomes.

#### Scenario: Local input is registered
- **WHEN** authorized pasted text or a selected file becomes a current SourceVersion
- **THEN** the system SHALL NOT create an admitted Matter without the declared person, event, goal, obligation, or outcome evidence

### Requirement: Admission is evidence-backed and autonomous
The system SHALL record why a Matter was formed, which evidence licensed it,
which counterevidence or uncertainty remains, and one automatic terminal
admission disposition for the current packet.

#### Scenario: Evidence satisfies admission rules
- **WHEN** the admission packet satisfies the current policy and contains no blocking conflict
- **THEN** the system SHALL emit an admitted Matter with evidence references and rationale

#### Scenario: Evidence is insufficient
- **WHEN** the packet has useful source content but does not satisfy admission
- **THEN** the system SHALL terminate as `source_only`, `candidate`, `uncertainty_preserved`, `not_applicable`, or `blocked` rather than silently admitting or waiting for user confirmation

### Requirement: Candidates are excluded from canonical statistics
The system SHALL exclude MatterCandidates from admitted-Matter counts and
canonical board totals.

#### Scenario: Candidate is projected on demand
- **WHEN** a MatterCandidate appears in an on-demand candidate/history view
- **THEN** admitted totals SHALL remain unchanged

### Requirement: AI proposals do not bypass admission
AI and local-skill outputs SHALL enter admission only as anchored candidates
and SHALL NOT create an admitted Matter directly.

#### Scenario: AI proposes a Matter
- **WHEN** a current advisory artifact proposes a Matter with anchored evidence
- **THEN** the admission owner SHALL automatically validate the packet and return `source_only`, `candidate`, `uncertainty_preserved`, `conflict_preserved`, `not_applicable`, `blocked`, or `admitted` according to policy

#### Scenario: Advisory candidate remains unsupported
- **WHEN** a candidate lacks required admission evidence after automatic owner validation
- **THEN** the system SHALL preserve the advisory history and SHALL keep admission `source_only`, `candidate`, `not_applicable`, or `blocked` rather than fabricating evidence or asking the user to approve it
