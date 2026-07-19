## ADDED Requirements

### Requirement: Identity merging requires evidence
The system SHALL keep mentions as separate candidates unless evidence licenses
their identity equivalence.

#### Scenario: Two people share a name
- **WHEN** mentions have the same display name but no identity-linking evidence
- **THEN** the system SHALL keep distinct PersonCandidates, preserve uncertainty, and continue modeling without requiring user confirmation

### Requirement: Roles are scoped to a matter
The system SHALL represent source-described and matter roles separately from
global social relationships.

#### Scenario: Local text names a responsible person
- **WHEN** an authorized local source says that a named person is responsible for one action
- **THEN** the system SHALL create at most a matter-scoped role candidate and SHALL NOT infer friendship or stable global responsibility

### Requirement: Identity corrections preserve history
The system SHALL append identity split, merge, or reassignment decisions and
invalidate affected roles, events, and matters.

#### Scenario: User separates an incorrect merge
- **WHEN** a user confirms that one resolved person represents two people
- **THEN** the system SHALL append a split revision and request recomputation of every dependent

### Requirement: AI identity output remains a candidate
The system SHALL NOT merge people or entities solely because an AI or local
skill reports identity equivalence.

#### Scenario: AI proposes a same-name merge
- **WHEN** an advisory result proposes that two same-name mentions are one person without identity-linking evidence
- **THEN** the system SHALL automatically reject the merge, keep separate candidates, and expose the unsupported proposal only in on-demand history
