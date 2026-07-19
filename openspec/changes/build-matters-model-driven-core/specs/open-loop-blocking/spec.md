## ADDED Requirements

### Requirement: Waiting has an object and closure condition
The system SHALL create a waiting OpenLoop only when it records what is awaited,
from whom or what, and the condition that closes the wait.

#### Scenario: Response is requested
- **WHEN** anchored evidence shows a request awaiting a named response
- **THEN** the system SHALL create an OpenLoop with target and closure condition

#### Scenario: Text only says waiting
- **WHEN** no waiting object or closure condition can be identified
- **THEN** the system SHALL emit an `open_loop_gap` or `not_applicable` owner disposition instead of a canonical wait or user-confirmation request

### Requirement: Blocking is scoped
The system SHALL distinguish partial impediment from full Matter blocking.

#### Scenario: Noncritical subtask fails
- **WHEN** one noncritical action fails while a valid primary path can continue
- **THEN** the system SHALL mark the affected action or loop and SHALL NOT mark the whole Matter fully blocked

### Requirement: Loop closure requires evidence
The system SHALL close an OpenLoop only from its declared closure evidence or
an explicit user decision scoped to that loop.

#### Scenario: Matter is marked complete
- **WHEN** a Matter completion decision is recorded but an independent OpenLoop remains unmet
- **THEN** the system SHALL preserve the OpenLoop unless its own closure condition is satisfied

### Requirement: AI waiting suggestions remain candidates
The system SHALL require an anchored waiting object, target, and closure
condition before an AI or local-skill suggestion becomes a canonical OpenLoop.

#### Scenario: AI finds vague waiting language
- **WHEN** an advisory result reports waiting but cannot cite a target and closure condition
- **THEN** the system SHALL automatically emit an `open_loop_gap` or policy rejection and SHALL NOT create a canonical OpenLoop or confirmation queue
