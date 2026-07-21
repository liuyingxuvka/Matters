## ADDED Requirements

### Requirement: Completion and termination use explicit criteria
The system SHALL distinguish completed, cancelled, abandoned, conflicted, and
`completion_unproven` outcomes using declared criteria and evidence. Conflict
and insufficient evidence SHALL be current automatic outcomes with preserved
uncertainty rather than user-confirmation gates.

#### Scenario: File named final is present
- **WHEN** the only completion signal is a filename, meeting end, or provider `Done` state
- **THEN** the system SHALL NOT classify the Matter as completed

#### Scenario: Completion criteria are evidenced
- **WHEN** every required completion criterion has current licensed evidence
- **THEN** the system SHALL emit a completed outcome with the criterion evidence
- **AND** C9 SHALL independently match every criterion evidence identifier to a current C5 event for the same Matter

### Requirement: New obligations can reopen an outcome
The system SHALL evaluate reopening when new licensed obligations, contrary
evidence, or source revisions arrive after termination.

#### Scenario: Completed Matter receives a new required action
- **WHEN** current evidence introduces an obligation that falls within the Matter boundary
- **THEN** the system SHALL automatically reopen or preserve an `outcome_conflict` while retaining the earlier completion revision

### Requirement: User decisions are scoped and auditable
The system SHALL retain the scope, rationale, and revision of a user outcome
decision without allowing it to silently mutate independent loops or evidence.

#### Scenario: User cancels a Matter
- **WHEN** a user explicitly cancels a Matter
- **THEN** the system SHALL record cancellation and separately dispose every dependent OpenLoop

#### Scenario: A current source reports cancellation
- **WHEN** a current observed or reported C5 termination event supports a cancellation finding for the same Matter and every current OpenLoop has an explicit disposition
- **THEN** C9 MAY record confirmed cancellation with the source modality and exact evidence
- **AND** a generic AI statement, unrelated event, inferred future outcome, or missing OpenLoop disposition SHALL preserve `outcome_conflict` rather than cancel the Matter

### Requirement: AI outcome suggestions are not terminal decisions
The system SHALL NOT complete, cancel, abandon, or reopen a Matter solely from
an AI or local-skill suggestion.

#### Scenario: AI proposes completion
- **WHEN** an advisory result proposes completion without current evidence for every required criterion
- **THEN** the outcome owner SHALL automatically reject the completion proposal or emit `completion_unproven`/`outcome_conflict` while preserving the advisory artifact

### Requirement: Completion evidence carries modality, license, and terminality
Every completion criterion SHALL retain its evidence modality, temporal
direction, freshness, completion license, and terminality. Planned, future,
stale, or unlicensed evidence SHALL NOT satisfy a completion criterion. A
historical-gap inference MAY satisfy a criterion only under the explicit
provisional-completion policy and SHALL NOT be treated as confirmed evidence.

#### Scenario: Historical inference supports a bounded elapsed phase
- **WHEN** every required criterion for an elapsed bounded phase has current supporting evidence, current covered evidence contains no material contradiction, and the historical-gap policy licenses a revisable inference
- **THEN** C9 MAY emit `completed` with `basis_modality=ai_inferred` and `terminality=provisional`
- **AND** it SHALL preserve confidence, alternatives, counter-signals, coverage boundary, expiry, and contradiction triggers
- **AND** the decision SHALL NOT close a parent criterion, an independent loop, or an irreversible action

#### Scenario: AI returns satisfied without a completion license
- **WHEN** an AI finding sets `satisfied=true` but its evidence is planned, future, stale, unlicensed, or a generic summary
- **THEN** C9 SHALL emit `completion_unproven` and preserve the rejected proposal for audit

#### Scenario: AI declares its own evidence licensed
- **WHEN** an AI result sets `completion_licensed=true` or `inference_contract_valid=true` but C9 cannot match every criterion evidence identifier to a compatible current C5 event for the same Matter
- **THEN** C9 SHALL ignore the self-declared license and emit `completion_unproven`

### Requirement: Parent completion includes required children and parent criteria
A parent Matter SHALL be completed only when its own declared completion
criteria and every current required child criterion are satisfied. Optional
children SHALL NOT block parent completion. Child completion alone SHALL NOT
complete the parent.

#### Scenario: All required bookings are complete
- **WHEN** every required booking child is complete but the root trip criterion requires the trip to occur
- **THEN** the root SHALL remain incomplete until current evidence satisfies the root criterion

#### Scenario: Required child reopens
- **WHEN** a current required child receives a new unresolved obligation after the parent was completed
- **THEN** the parent outcome SHALL be invalidated and automatically reopened or preserved as an outcome conflict while retaining the prior completion revision
