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
