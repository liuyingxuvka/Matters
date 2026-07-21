## ADDED Requirements

### Requirement: Lifecycle state requires a proof packet
The system SHALL derive lifecycle axes and board placement only from a current
StateProofPacket containing licensed evidence and policy.

#### Scenario: Work has explicit start evidence
- **WHEN** current evidence records actual work beginning under the active policy
- **THEN** the system MAY emit an in-progress lifecycle decision with its explanation

#### Scenario: Only scheduling evidence exists
- **WHEN** evidence shows assignment, due date, or sprint placement but no actual start
- **THEN** the system SHALL NOT classify the Matter as in progress

### Requirement: Absence of evidence is not negative evidence
The system SHALL preserve `unknown`, `provisional`, or `conflict_preserved`
state with confidence and gaps when coverage does not support a positive or
negative conclusion. These states SHALL be current automatic owner decisions,
not a request for user approval.

#### Scenario: No start evidence is found in partial coverage
- **WHEN** provider coverage is partial and no start evidence is fetched
- **THEN** the system SHALL NOT classify the Matter as not started solely from that absence

#### Scenario: Expected completion is supported but not observed
- **WHEN** licensed planning/booking evidence and elapsed time support a likely completed trajectory but no observed completion evidence exists
- **THEN** the lifecycle owner MAY preserve a separate provisional or `ai_inferred` current-best interpretation with confidence and gaps
- **AND** it SHALL NOT publish the confirmed `completed` state or use absence of a cancellation/refund record alone as negative evidence

### Requirement: Board placement is a canonical projection
The system SHALL derive board placement from the canonical lifecycle revision
and SHALL prevent source adapters, AI/local skills, and UI code from writing
placement directly.

#### Scenario: Source label differs from Matters state
- **WHEN** a source label or AI proposal says `Done` but completion criteria are not licensed
- **THEN** the board SHALL reflect the Matters decision and expose the source or advisory conflict

#### Scenario: Recompute is pending
- **WHEN** a correction has invalidated the current lifecycle revision and required owners have not completed recomputation
- **THEN** the board SHALL withhold a new canonical placement and expose a pending automatic-recomputation status

### Requirement: Child and parent lifecycle decisions remain independent
Every child Matter SHALL own its lifecycle decision. Parent lifecycle summaries
SHALL treat child activity as evidence and SHALL NOT mechanically choose the
most active, latest, or majority child state. Unknown denominators SHALL use a
narrative summary and SHALL NOT fabricate a completion percentage.

#### Scenario: Flight booking is complete but travel has not begun
- **WHEN** a required flight-booking child is completed while the root trip has only planned evidence
- **THEN** the child SHALL remain completed and the root trip SHALL remain planned unless its own lifecycle proof licenses another state

#### Scenario: Several children have mixed state
- **WHEN** a parent has completed, planned, waiting, and unknown children but no declared progress denominator
- **THEN** the projection SHALL summarize those current child states without emitting a synthetic percent-complete value
