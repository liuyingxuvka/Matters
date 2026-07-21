## ADDED Requirements

### Requirement: Corrections append history
The system SHALL append correction, revocation, supersession, deletion, and
time-expiry revisions rather than overwriting prior decisions.

User correction SHALL be an optional post-publication action and SHALL NOT be
a prerequisite for automatic initial modeling.

#### Scenario: User corrects a lifecycle state
- **WHEN** a user supplies a correction with supporting scope
- **THEN** the system SHALL preserve the prior revision and append the correction

### Requirement: Every dependent receives a disposition
The system SHALL identify all downstream dependents of an invalidated revision
and assign recompute, remove, retain-with-rationale, uncertainty-preserved, or blocked
disposition.

#### Scenario: Evidence anchor becomes stale
- **WHEN** a source change invalidates an EvidenceAnchor
- **THEN** every dependent assertion, entity, event, Matter, state, outcome, and projection SHALL receive an explicit disposition

### Requirement: Original owners recompute canonical state
The correction coordinator SHALL issue recomputation requests but SHALL NOT
write another model's canonical fields. Every required original owner SHALL
execute or return an explicit blocked disposition before a fresh canonical
projection is published.

#### Scenario: Correction affects board state
- **WHEN** invalidation reaches a lifecycle decision
- **THEN** the lifecycle owner SHALL actually recompute state before the canonical board projection is refreshed

#### Scenario: One required owner cannot recompute
- **WHEN** a required recomputation owner is unavailable, fails, or lacks current evidence
- **THEN** the system SHALL retain a visible pending or blocked recomputation state and SHALL NOT publish a fresh canonical projection

### Requirement: Recompute work survives restart
The system SHALL persist invalidation plans, owner requests, terminal
dispositions, and their input fingerprints under `MATTERS_HOME`.

#### Scenario: Service restarts during recomputation
- **WHEN** the service restarts after invalidation and before all required owners are terminal
- **THEN** it SHALL recover the pending plan, revalidate authorization and input freshness, and resume or block each outstanding owner without losing history

### Requirement: Projection freshness follows dependency freshness
A projection SHALL be current only when every required dependency and
original-owner recomputation result references the active correction revision.

#### Scenario: Projection owner receives stale recomputation evidence
- **WHEN** C12 receives an owner result for a superseded correction revision
- **THEN** C12 SHALL reject it as stale and keep the active projection pending

### Requirement: Hierarchy changes invalidate both old and new ancestor chains
Reparent, split, merge, containment-role change, child correction, child
source revision, and child outcome change SHALL invalidate the changed Matter,
its old ancestors, its new ancestors, and every affected hierarchy summary,
timeline, localization, meaningful-clue/summary revision, generated hero when
its semantic identity or theme changes, supplemental information, and UI
projection.

#### Scenario: Child is reparented
- **WHEN** a child moves from parent A to parent B
- **THEN** the system SHALL append the edge revision, preserve the old edge, invalidate both ancestor chains, and publish neither parent as current until their original owners terminate recomputation

#### Scenario: Two child Matters merge
- **WHEN** current evidence licenses a semantic merge
- **THEN** the system SHALL preserve both prior identities and evidence histories, append the merge decision, and recompute descendants and ancestors without deleting or double-counting events

### Requirement: Material clue invalidation is dependency-bounded and atomic
A new current material clue SHALL invalidate the affected Matter's bilingual
summary and activity-order projection plus every current ancestor's propagated
summary/activity dependency. It SHALL NOT invalidate a stable generated hero
unless semantic identity, topic/theme, merge/split/reparent disposition,
permission, safety policy, or explicit correction changes.

#### Scenario: Child receives a material progress clue
- **WHEN** a child obtains current evidence that changes its state, outcome, next step, important time, person, relationship, hierarchy, or useful summary
- **THEN** the system SHALL recompute the child and each current ancestor's clue/summary projection and publish each required bilingual summary with its clue identity atomically

#### Scenario: Only wording or processing metadata changes
- **WHEN** a scan, retry, read timestamp, technical receipt, localization-only refresh, or rephrasing creates no material semantic change
- **THEN** the system SHALL retain the prior clue time, summaries, generated hero, and catalog order

### Requirement: Reported observations do not silently become corrections
An AI gateway `user_observation` SHALL be an append-only reported candidate
with a durable owner-dispatch disposition. It SHALL NOT invalidate or replace a
current canonical revision unless the user explicitly requests correction or
an original owner independently licenses a new revision.

#### Scenario: User supplies additional context
- **WHEN** the user tells an AI a new relevant detail without saying that an existing Matter record is wrong
- **THEN** the system SHALL preserve the current revision, append the minimized observation, and leave its original-owner disposition visible for later maintenance

#### Scenario: User explicitly corrects the record
- **WHEN** the user identifies an existing value as wrong and provides replacement scope
- **THEN** the AI gateway SHALL use the C10 correction path with append-only invalidation and recomputation rather than the observation inbox
