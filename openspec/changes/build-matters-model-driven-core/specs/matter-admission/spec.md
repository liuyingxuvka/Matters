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

### Requirement: Matter identity is stable and source-independent
An admitted Matter SHALL use a stable semantic identity that remains unchanged
when supporting SourceVersions or EvidenceAnchors are added, removed,
superseded, or reordered. The system SHALL preserve identity and revision
history across reparent, split, merge, and correction decisions.

#### Scenario: New evidence supports an existing Matter
- **WHEN** a current SourceVersion adds evidence to an already admitted semantic Matter
- **THEN** the system SHALL append a Matter revision and SHALL NOT create a new Matter merely because the source-id set changed

#### Scenario: One source supports a parent and child
- **WHEN** one current SourceVersion supports both a root Matter and a child Matter
- **THEN** both Matters SHALL retain distinct stable semantic identities and SHALL reference the source without deriving identity from source membership

### Requirement: Canonical Matter identity requires the exact admitted matter id
C6 SHALL be the only owner that creates or selects a canonical Matter identity.
Hierarchy, coverage, lifecycle, activity, relation, localization, hero, and UI
owners SHALL accept Matter authority only through the exact current
`matter_id` of a C6 `admitted` disposition. Projection ids, source ids,
candidate ids, package ids, titles, source overlap, and inferred nearest-Matter
matches SHALL remain non-authoritative.

#### Scenario: C6 admits a Matter
- **WHEN** the current admission transaction returns `admitted` with an exact `matter_id`
- **THEN** downstream owners MAY bind their revisions to that exact id and SHALL preserve it across later source-membership changes

#### Scenario: A projection-only object resembles an existing Matter
- **WHEN** a projection, source-only result, or MatterCandidate lacks an exact current admitted `matter_id`
- **THEN** the system SHALL reject canonical hierarchy, coverage, lifecycle, activity, and root-catalog writes for that object
- **AND** source overlap, title similarity, or package-local projection identity SHALL NOT choose a Matter on its behalf

#### Scenario: A package contains zero or multiple possible admitted owners
- **WHEN** an advisory result cannot name exactly one current C6-admitted `matter_id`
- **THEN** downstream publication SHALL remain pending or blocked until C6 returns an unambiguous disposition
- **AND** no projection or candidate identity SHALL be promoted as a temporary canonical Matter id

### Requirement: Matter merge decisions use bounded semantic and project context
Before admitting a new root or independently openable child, C6 SHALL compare
it with current candidate Matters using evidence-bound goal, subject, outcome,
people, time, source-neighborhood, provider-thread, repository/project, and
declared Codex-workspace context. No one contextual signal SHALL prove a merge.
The decision SHALL terminate as append-to-current, admit-child, admit-related,
admit-root, preserve-uncertain-alternative, or blocked and SHALL record the
current candidates, rationale, evidence, revision, and freshness.

#### Scenario: Several records concern one hackathon
- **WHEN** submission deadline mail, project files, and a participation record share a licensed goal and event identity
- **THEN** the system SHALL append them to one hackathon Matter and its useful child Matters rather than creating separate root cards for each record

#### Scenario: Several coding records belong to one repository project
- **WHEN** skill, FlowGuard, Codex-task, and source records are licensed to the same current repository/project goal
- **THEN** the system SHALL model the repository/project as the broader Matter and keep independently useful features or releases as children, WorkItems, or Events according to their own boundaries

#### Scenario: Folder or person similarity is weak
- **WHEN** two sources share a folder, person, broad topic, or date but not a licensed common goal/outcome identity
- **THEN** the system SHALL preserve the contextual relation without forcing a merge or containment edge

### Requirement: Root Matters represent broad independently useful situations
The ordinary root catalog SHALL prefer broad situations such as a trip, job
search, event participation, subscription relationship, or software project.
A receipt, single email, isolated deadline, one code edit, boarding step, or
refund message SHALL become an Event, WorkItem, source link, or child Matter
unless evidence licenses an independently useful root goal and outcome
boundary.

#### Scenario: Travel records describe one trip
- **WHEN** booking, authorization, flight, hotel, boarding, and itinerary records belong to one licensed trip identity
- **THEN** the trip SHALL be the root Matter and the independently trackable bookings or legs MAY be child Matters while routine occurrences remain Events or WorkItems

### Requirement: Matter containment is evidence-backed and acyclic
Each Matter SHALL have zero or one current primary containment parent. A
containment decision SHALL record parent and child identities, `required`,
`optional`, or `critical` child role, confidence, rationale, evidence,
revision, and freshness. Self-parenting, cycles, and simultaneous multiple
primary parents SHALL be rejected. Other links SHALL remain Related Matters.

#### Scenario: AI proposes a useful child Matter
- **WHEN** current evidence supports an independent child goal, lifecycle, outcome criterion, or next step inside a broader Matter
- **THEN** C6 MAY admit the child and one evidence-bound primary containment edge without requiring user confirmation

#### Scenario: Shared person is the only relationship
- **WHEN** two Matters share a person but no evidence licenses containment
- **THEN** the system SHALL keep an ordinary related link and SHALL NOT create a primary parent

#### Scenario: Proposed edge creates a cycle
- **WHEN** a new or reparented containment edge would make a Matter its own ancestor
- **THEN** the system SHALL reject the edge, preserve the proposal in history, and keep the current hierarchy unchanged

### Requirement: Matter, WorkItem, and Event are distinct levels
A candidate SHALL become a Matter only when it has a stable independent
identity and at least two independent dimensions: an independently useful
goal/obligation plus at least one independently useful lifecycle, outcome
boundary, or next-step surface. A single bounded next step SHALL become a
WorkItem/Action, not a Matter. A one-time occurrence SHALL remain an Event.
Sources and evidence SHALL never become Matters solely because they exist.
Contradictory granularity flags SHALL preserve uncertainty rather than choose
the highest apparent type. Every recursive level SHALL pass the same admission
threshold; deeper placement never lowers the threshold.

#### Scenario: A reply email is received
- **WHEN** an email only records that a reply arrived for a current child Matter
- **THEN** the system SHALL create or link an Event and SHALL NOT create another child Matter solely for that message

#### Scenario: Company application is independently trackable
- **WHEN** a job-search source set supports a company-specific goal, state, next step, and outcome boundary
- **THEN** the system MAY admit a company-application child Matter under the broader job-search Matter

#### Scenario: One upload action has a name and deadline
- **WHEN** an upload advances a parent project but has no independent goal or outcome world
- **THEN** it SHALL remain a WorkItem even if it has its own title, status, and deadline

#### Scenario: Candidate claims to be both one occurrence and a Matter
- **WHEN** a granularity proposal marks the same identity as a one-time occurrence and an independently trackable Matter without resolving the contradiction
- **THEN** C6 SHALL preserve `granularity_uncertain` and SHALL NOT admit or attach the candidate

### Requirement: All production admission uses one C6 reconciliation boundary
Every production path that may retain a Matter candidate, admit or append a
Matter, or select its placement SHALL call the same C6 reconciliation owner.
The dispatcher and direct source-processing facade SHALL NOT independently
call a lower-level admission decider with a different granularity
interpretation. A registered source with no current qualified evidence SHALL
enter the same owner through the pre-evidence retention operation, remain a
source or uncertain candidate, and SHALL NOT create, merge, or attach a Matter
until a later qualified request returns through the ordinary reconciliation
operation.

#### Scenario: Qualified AI result proposes a Matter
- **WHEN** an accepted analysis result contains current evidence, semantic identity, granularity, and candidate context
- **THEN** the single C6 owner SHALL produce both the placement decision and canonical admission decision before any admission, hierarchy, relation, coverage, or projection write

#### Scenario: Newly registered source has no qualified evidence
- **WHEN** source registration succeeds but evidence qualification produces no current anchor
- **THEN** the same C6 boundary SHALL retain the source as source-only or uncertain according to its bounded disposition
- **AND** it SHALL NOT infer a Matter, merge target, parent, relation, or current semantic state from source metadata alone

### Requirement: Root catalog admission follows current containment
The ordinary Matter catalog SHALL contain only Matters with no current primary
containment parent. Child Matters SHALL remain independently searchable and
reachable through their hierarchy path without being duplicated as root cards.

#### Scenario: Child is reparented
- **WHEN** a root Matter receives a current primary parent
- **THEN** it SHALL leave the root catalog only after the new hierarchy projection is current and SHALL remain reachable through search and its parent detail

### Requirement: Situation graph is a bounded projection of existing owners
For one admitted root Matter the system SHALL expose a versioned bounded graph
projection containing current descendant Matters, WorkItems, Events, primary
containment edges, typed secondary relationships, and explicitly advisory
inference nodes/edges. Every node and edge SHALL retain its owning C4-C9/C11
revision, modality, freshness, and evidence or advisory identity. The graph
SHALL NOT become another admission, hierarchy, relationship, event, lifecycle,
or outcome owner.

#### Scenario: A child Matter has events and a related Matter
- **WHEN** the current owners publish one primary child edge, two current events, and one typed related-Matter edge
- **THEN** the root graph SHALL render the same owned objects once, style the primary and secondary edges distinctly, and SHALL NOT create duplicate Matter or Event identities

#### Scenario: AI proposes a missing likely event
- **WHEN** a current C11 result proposes an evidence-bound likely event or outcome hypothesis that no C5/C9 owner has confirmed
- **THEN** the graph MAY include an `ai_inferred` advisory node or edge with confidence, alternatives, expiry, and gaps, but SHALL NOT add it to confirmed Event, lifecycle, or outcome counts

#### Scenario: Current records disagree about one graph identity
- **WHEN** two current owner records for the same node disagree on certainty or a material attribute
- **THEN** the graph SHALL preserve both evidence sets and alternatives, mark the node certainty `unknown`, expose the conflicting values, and lower confidence to the weaker current record
- **AND** it SHALL NOT select the apparently stronger certainty or higher confidence as the winner

#### Scenario: A graph page is incomplete
- **WHEN** the requested descendant/edge set exceeds the bounded payload
- **THEN** the system SHALL return a stable continuation plus exact pending branch/edge counts and SHALL NOT serialize the entire private catalog or claim graph completeness

### Requirement: The ordinary Sub-matters projection separates Matters and material stages
The internal SituationGraph MAY retain owned WorkItems, Events, sources, and
advisory inferences. C12 SHALL project admitted Matter nodes, containment
edges, and typed Matter-to-Matter relations as the large hierarchy boxes. It
MAY additionally project a bounded set of material WorkItems as visually
smaller stage nodes when they are required, stage-changing, and carry a
distinct status plus time/result boundary. These stage nodes SHALL retain
`node_type=work_item`, SHALL NOT enter Matter counts/search paths as Matters,
and SHALL NOT accept child containment. Events, sources, ordinary actions, and
inference details SHALL remain itemized under their owning Matter's quick view.
This projection boundary SHALL NOT change C5/C6/C7-C11 ownership or delete
internal objects.

#### Scenario: Travel contains two journeys and several records
- **WHEN** one 2026 travel root contains an independently useful Japan journey, an independently useful Australia journey, outbound and return travel children, plus ticket, authorization, boarding, entry, and inferred-completion facts
- **THEN** the graph SHALL show the travel, Japan, Australia, outbound, and return Matters at their licensed levels
- **AND** outbound and return SHALL be siblings when neither contains the other
- **AND** ticket, authorization, boarding, entry, and inferred-completion records SHALL remain itemized facts rather than deeper graph nodes

#### Scenario: Build Week has no independent project child yet
- **WHEN** the current evidence supports registration confirmation, a required preparation phase, and a future submission deadline but does not yet support an independent project Matter
- **THEN** the Sub-matters surface SHALL show material stage nodes for registration, preparation, and submission under the Build Week Matter
- **AND** registration MAY be completed/reported, preparation MAY be in-progress/AI-inferred under the current-phase policy, and submission SHALL remain planned
- **AND** none of those stage nodes SHALL be counted or opened as a child Matter

#### Scenario: Two independent competition projects are later evidenced
- **WHEN** current local/Codex evidence establishes two stable project identities with their own goals, lifecycle, results, and next steps
- **THEN** C6 SHALL admit them as sibling child Matters under Build Week while retaining registration/preparation/submission as the appropriate WorkItems or Events

#### Scenario: Software projects also support human-domain Matters
- **WHEN** SkillGuard, FlowPilot, FlowGuard, a heating-assessment application, and a job-search application are current software projects, and the last two also support heating and job-search situations
- **THEN** the software projects MAY be children of one broad Software Development root while the heating and job-search Matters retain typed cross-domain relationships
- **AND** the shared relationship SHALL NOT duplicate cards or force the human-domain Matters under Software Development

### Requirement: Matter-internal semantic members have one stable identity
Every cross-source WorkItem and open loop SHALL declare one stable,
language-neutral semantic role within its owning Matter. The C6/C8 owner SHALL
reuse the current identity for that role or require an exact supersession list.
Title similarity, translation similarity, chronology alone, and finding ids
SHALL NOT authorize automatic replacement.

#### Scenario: Reanalysis emits the same preparation stage
- **WHEN** a later semantic refresh emits the same `preparation` role for the same Matter
- **THEN** the owner SHALL revise or reuse the one current preparation WorkItem and SHALL NOT create a second peer stage

#### Scenario: Legacy analysis created two submission stages
- **WHEN** a current refresh names one surviving submission identity and the exact current duplicate ids in `supersedes_item_ids`
- **THEN** the owner SHALL append retired revisions for those exact duplicates, preserve their evidence and history, and expose only the survivor in WorkItem indexes and UI

#### Scenario: A same-role collision is not fully named
- **WHEN** a proposed WorkItem or open loop collides with another active object carrying the same semantic role but the proposal does not explicitly supersede it
- **THEN** the complete write SHALL fail without retiring or adding any object

#### Scenario: Semantic state changes after one analysis pass
- **WHEN** a cross-source result changes current WorkItems, open loops, lifecycle, or outcome state
- **THEN** the previous semantic-state fingerprint SHALL become stale and one successor refresh SHALL receive the complete bounded current semantic state so the pipeline can converge without duplicate revisions

### Requirement: Bounded containment batches are atomic and recoverable
The system SHALL support one evidence-bound containment batch for one parent
and at most 500 child Matters. It SHALL validate the complete batch before
writing, commit edges plus one hierarchy revision and pending publication
request atomically, and compute the parent summary and projection once.

#### Scenario: One child in the batch violates containment
- **WHEN** any proposed child is duplicated, already has another primary parent, would create a cycle, or lacks the required role/evidence/freshness contract
- **THEN** the entire batch SHALL be rejected with zero partial edge, revision, summary, or projection writes

#### Scenario: Publication is interrupted after the batch commit
- **WHEN** the atomic edge/revision commit succeeds but summary publication is interrupted
- **THEN** startup SHALL recover the pending publication request, publish the current summary once, and make an identical batch retry return the same hierarchy revision

### Requirement: Parent composition is atomic across all canonical owners
A composed parent request SHALL validate the parent identity, localized
projection, child set, edge roles, evidence, cycle/multi-parent constraints,
coverage bindings, activity rollup, and supplemental-information disposition
before any row becomes current. Admission, projection, classification,
coverage, containment, activity, and supplemental-information writes SHALL
commit in one private transaction.

#### Scenario: One child attachment fails
- **WHEN** any child is missing, invalid, cyclic, already owned without explicit reparent, or the containment write fails
- **THEN** no parent admission, projection, classification, coverage, hierarchy, activity, hero request, or supplemental row SHALL survive and all children SHALL retain their previous current state

#### Scenario: Parent composition succeeds
- **WHEN** every parent and child invariant passes
- **THEN** exactly one parent revision and one containment batch SHALL become current, child activity SHALL bubble to the parent, and generated-hero work MAY be requested only for a root Matter after the canonical transaction commits

### Requirement: Parent narrative scope is derived from the complete current child set
C6 SHALL expose one evidence-bound parent-narrative scope containing the
current parent id, hierarchy revision, complete current child id/projection
revision set, and licensed evidence revision set. It SHALL NOT select only the
latest child as the parent overview authority.

#### Scenario: Five children form one broader Matter
- **WHEN** C6 has a current parent with five current child Matters
- **THEN** the narrative scope SHALL bind all five current child/projection revisions and licensed evidence even if only one child supplied the latest clue

#### Scenario: Child membership changes during narrative generation
- **WHEN** a child is added, removed, merged, or reparented after a narrative request was queued
- **THEN** the stale request SHALL NOT publish and C6 SHALL expose a new scope revision for reprocessing

### Requirement: Same-Matter canonicalization is singular and append-only
Merge, append-to-Matter, and source-only retirement SHALL share one
`matter_canonicalization` owner. Each disposition SHALL preserve evidence,
name the canonical Matter when one exists, update coverage references in the
same transaction, and prevent the superseded candidate or duplicate from
remaining in the catalog.

#### Scenario: Two cards describe the same Matter
- **WHEN** evidence licenses an exact same-goal/outcome identity and C6 selects one canonical Matter
- **THEN** the system SHALL move source membership and coverage references to the canonical Matter, append a `merged` disposition for the duplicate, preserve both histories, and publish only the canonical projection

#### Scenario: A candidate is one bounded action
- **WHEN** it lacks an independent Matter outcome but belongs to one current Matter
- **THEN** the system SHALL append it exactly once as a WorkItem or Event, preserve its evidence, record the canonical Matter id, and remove its candidate projection from the ordinary catalog

#### Scenario: A candidate has no trackable goal
- **WHEN** it remains useful only as source evidence
- **THEN** the system SHALL append a `retired_to_source_only` disposition, preserve evidence and source links, remove its Matter coverage reference, and SHALL NOT delete source history

#### Scenario: Canonicalization is retried
- **WHEN** the exact disposition, target, materialization, rationale, and evidence are already current
- **THEN** the operation SHALL be idempotent; a conflicting retry SHALL fail without partial writes

### Requirement: Admitted source revisions reconcile without semantic bypass
Every canonical Matter SHALL bind the exact admitted SourceVersion revision.
When the source registry publishes a newer current revision, one bounded
`source_revision_reconciliation` owner SHALL compare that current registry
revision with the Matter's admitted references before downstream freshness,
depth, localization, supplemental-information, or UI completeness can become
current. A source revision SHALL NOT be promoted mechanically merely because
its extracted body or selected metadata currently compares equal: the new
revision still requires the original semantic owners to establish current
anchors and decisions.

#### Scenario: The same Matter already admits the current revision
- **WHEN** a Matter references an older SourceVersion and also already references the registry-current revision of that same source
- **THEN** the owner SHALL remove only the redundant old reference and the old-revision evidence membership from the current admission, preserve append-only admission and reconciliation history, retain the exact current anchors, and make an exact retry idempotent

#### Scenario: The registry has a newer revision not yet admitted
- **WHEN** a Matter references an older SourceVersion and does not yet reference the registry-current revision
- **THEN** the owner SHALL return `analysis_required`, preserve the old evidence link, and keep downstream freshness visibly non-current until the original source, evidence, semantic, and Matter owners process the new revision

#### Scenario: The registry-current revision is processed for one exact existing Matter
- **WHEN** one target-bound semantic package names the exact existing Matter id, registry-current SourceVersion, current admission fingerprint, and exact current evidence anchors
- **THEN** C6 SHALL preserve that Matter's identity and semantic identity, append the current source and anchors to that Matter, and SHALL NOT use title similarity, choose another Matter, or create a duplicate root

#### Scenario: One Matter semantic refresh needs multiple current sources
- **WHEN** one exact existing Matter cites multiple source ids and each has one registry-current non-tombstoned SourceVersion, a current source-annotation WorkPackage/Result, and current EvidenceAnchor coverage
- **THEN** the system SHALL issue exactly one `matter_semantic_refresh` package bound to the complete sorted current-source set, complete current annotation dependency set, exact allowed evidence and assets, current admission fingerprint, and semantic identity; it SHALL append-only supersede an older package when any bound input changes and SHALL NOT silently fall back to per-source packages

#### Scenario: A cross-source semantic candidate preserves Matter identity
- **WHEN** a current `matter_semantic_refresh` result emits a `matter_candidate` for its exact existing Matter
- **THEN** C6 SHALL treat that candidate as an identity-preservation no-op after validating the exact Matter id, semantic identity, admission fingerprint, registry-current source set, and anchor whitelist; it SHALL NOT create a root, select a similar Matter, or mutate source membership

#### Scenario: Cross-source semantic output distinguishes time axes
- **WHEN** a `matter_semantic_refresh` package returns historical gaps, a current phase, or future planned obligations
- **THEN** its required output SHALL preserve the `historical_gap`, `current_phase`, and `future_planned` axes separately; a future obligation SHALL remain planned and SHALL NOT be emitted as completed merely because a prerequisite or registration is completed

#### Scenario: A source-revision result also contains another C6 finding type
- **WHEN** one `source_revision_matter_refresh` result contains a `work_item_candidate`, `matter_hierarchy_candidate`, or another declared C6 finding in addition to its `matter_candidate`
- **THEN** only the `matter_candidate` SHALL use the exact target-bound source-revision admission branch; every other finding SHALL continue through its own canonical finding-type owner, and SHALL NOT be consumed, discarded, or rewritten as a Matter source-membership refresh

#### Scenario: A same-Matter sibling package becomes stale after an earlier refresh commits
- **WHEN** one source-revision package changes the exact Matter admission fingerprint and a sibling package still binds the prior fingerprint
- **THEN** the stale sibling SHALL be rejected and append-only superseded, exactly one successor SHALL bind the same Matter, registry-current SourceVersion, current admission fingerprint, and current evidence anchors, and an exact retry SHALL reuse that successor without retrying the stale package, loosening its fingerprint, or creating a duplicate successor

#### Scenario: A passed annotation is recovered or imported again
- **WHEN** the exact current annotation result already has one persisted semantic follow-up relation
- **THEN** the system SHALL return that same follow-up without rewriting the annotation or generating a time-varying package identity; any additional unexecuted follow-up SHALL be append-only invalidated in favor of the persisted relation while completed or uncertain history remains intact

#### Scenario: The admitted reference cannot be reconciled safely
- **WHEN** the reference is malformed, the source or current revision is unavailable, or the current occurrence is tombstoned or outside the authorized tracked scope
- **THEN** the owner SHALL return a typed blocked disposition and SHALL NOT rewrite Matter source membership
