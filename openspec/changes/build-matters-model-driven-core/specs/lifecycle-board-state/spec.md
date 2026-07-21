## ADDED Requirements

### Requirement: Lifecycle state requires a proof packet
The system SHALL derive lifecycle axes and board placement only from a current
StateProofPacket containing licensed evidence and policy.

The packet and decision SHALL keep the lifecycle display key, evidence-basis
modality, temporal assertion, and terminality separate. `reported`,
`observed`, `planned`, and `ai_inferred` SHALL NOT be accepted as lifecycle
states. `planned`, `in_progress`, and `completed` SHALL NOT imply how the state
was learned.

#### Scenario: Work has explicit start evidence
- **WHEN** current evidence records actual work beginning under the active policy
- **THEN** the system MAY emit an in-progress lifecycle decision with its explanation

#### Scenario: Only scheduling evidence exists
- **WHEN** evidence shows assignment, due date, or sprint placement but no actual start
- **THEN** the system SHALL NOT classify the Matter as in progress

#### Scenario: Required current phase is inferred from a completed prerequisite
- **WHEN** one prerequisite is currently completed, a required next WorkItem remains open, the analysis time lies in its bounded active window, and no completion/cancellation/postponement contradiction is current
- **THEN** the lifecycle owner MAY classify that WorkItem or Matter as `in_progress`
- **AND** it SHALL publish `basis_modality=ai_inferred`, `temporal_assertion=ongoing`, `terminality=provisional`, confidence, alternatives, coverage, expiry, and contradiction triggers
- **AND** the rationale SHALL NOT claim that user activity was directly observed

#### Scenario: A deadline alone is the only current signal
- **WHEN** a future deadline exists but no completed prerequisite or bounded current-phase policy licenses preparation
- **THEN** the lifecycle owner SHALL keep the item `planned`

#### Scenario: Current cancellation or postponement contradicts preparation
- **WHEN** a bounded current-phase inference otherwise qualifies but current covered evidence records cancellation, postponement, withdrawal, or another material counter-signal
- **THEN** the lifecycle owner SHALL NOT classify the item as `in_progress`
- **AND** it SHALL preserve `uncertain`, the counter-signal, alternatives, coverage boundary, expiry, and contradiction triggers for later recomputation

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

### Requirement: Legacy lifecycle rows remain readable without semantic invention
An installed upgrade SHALL keep previously registered Matter and WorkItem
records visible while the current semantic owners recompute them. When an old
record lacks one or more current orthogonal fields such as evidence-basis
modality, basis scope, temporal assertion, or terminality, the reader SHALL
publish `semantic_contract_status=legacy_pending_recompute`, use `unknown` for
the missing semantic axis, and use `terminality=provisional`. It SHALL NOT
derive evidence modality from lifecycle state, reinterpret the old row as a
current fully modeled revision, delete it, or rewrite its historical record in
place. The original owners SHALL publish a new append-only current revision
after recomputation.

#### Scenario: Old in-progress WorkItem has no evidence-basis fields
- **WHEN** an installed private store restores an older WorkItem whose lifecycle state is `in_progress` but whose basis modality, basis scope, temporal assertion, and terminality are absent
- **THEN** the WorkItem SHALL remain readable and retain its historical lifecycle value
- **AND** its missing basis SHALL be projected as `unknown`, terminality as `provisional`, and semantic contract status as `legacy_pending_recompute`
- **AND** the reader SHALL NOT claim that the state was reported, observed, planned, or AI-inferred

#### Scenario: Original owner recomputes a legacy row
- **WHEN** the responsible semantic owners complete the current contract from authorized evidence
- **THEN** they SHALL append a new current revision with explicit lifecycle, temporal assertion, basis modality, basis scope, and terminality
- **AND** the previous row SHALL remain in append-only history rather than being silently mutated or deleted

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

### Requirement: Provisional completion remains revisable and non-propagating
The lifecycle owner MAY display an elapsed, evidence-supported phase as
`completed` with `basis_modality=ai_inferred` only when C9 licenses a
historical-gap completion disposition. Such a decision SHALL remain
`terminality=provisional`, SHALL be visibly labeled, and SHALL NOT mechanically
complete a parent, close an independent OpenLoop, or authorize an irreversible
side effect.

#### Scenario: A past attraction visit lacks an exit observation
- **WHEN** a dated admission record is in the past, covered evidence supports the visit, and no current cancellation or contrary record is found
- **THEN** C9 MAY license `completed` with `basis_modality=ai_inferred`, `basis_scope=historical_gap`, and `terminality=provisional`
- **AND** C12 SHALL display `Completed · AI historical inference` and a revisable human explanation

#### Scenario: Later evidence contradicts inferred completion
- **WHEN** a later current source proves cancellation, non-attendance, or a different outcome
- **THEN** the prior provisional decision SHALL remain in append-only history, become superseded, and trigger C10/C11 recomputation
