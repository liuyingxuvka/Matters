## ADDED Requirements

### Requirement: Matters ships an app-local consumer Skill Pack
The system SHALL package Matters-owned consumer skills and their matching
runtime assets as an immutable, versioned app-local Skill Pack that can operate
without installing skills into a machine-global Codex skill directory.

The required initial inventory SHALL contain exactly eleven required consumer
skills: source governance, inventory reconciliation, freshness maintenance,
model-depth maintenance, human correction, model-miss review, skill-runtime
management, research orchestration, semantic understanding, autonomous
maintenance, and card-visual curation. Each skill SHALL call the shared
MatterService/CLI/API boundary and SHALL NOT read undeclared sources, expand
authorization, or write canonical owner state. Human correction SHALL be
optional after publication and SHALL NOT become a normal first-modeling gate.
Autonomous maintenance SHALL coordinate ledger stages without becoming a new
canonical owner. Card-visual curation SHALL select only from an eligible
allowlist and SHALL NOT fetch or invent evidence.

#### Scenario: Machine has no matching skill installed
- **WHEN** Matters starts with a valid bundled required skill and no machine-installed copy
- **THEN** it SHALL use the bundled copy internally without creating a global skill installation

#### Scenario: Machine inventory is discovered at runtime
- **WHEN** Matters resolves the active Skill Pack on a real machine
- **THEN** it SHALL inspect only the exact bundle-declared skill ids, require an exact versioned machine manifest and verified bytes for any overlay, preserve unverifiable same-named candidates as visible findings, and SHALL NOT enumerate or ingest unrelated local skills

#### Scenario: Consumer skill attempts direct canonical write
- **WHEN** a bundled skill asks to write a Matter, lifecycle, outcome, evidence, or projection field directly
- **THEN** the operation SHALL be rejected and SHALL re-enter through the declared MatterService owner path

### Requirement: Every bundled skill has an exact consumer manifest
Each bundled skill SHALL declare skill id, version, schema compatibility,
Matters compatibility, origin, content hash, required or optional status,
installation policy, capabilities, permissions, data-disclosure policy,
dependencies, matching runtime identity, and native validator.
Versions and compatible intervals SHALL use PEP 440. A prerelease SHALL be
eligible only when the manifest explicitly declares prerelease acceptance for
the current Matters and skill-schema intervals.

The bundled consumer projection SHALL exclude author-side `.skillguard`
contracts, receipts, execution-owner state, router state, and maintenance
control artifacts.

#### Scenario: Manifest and bytes disagree
- **WHEN** a declared content hash or runtime identity does not match the packaged bytes
- **THEN** the skill SHALL be blocked before activation and no alternate implementation SHALL be selected silently

#### Scenario: Author control artifact enters the bundle
- **WHEN** a bundled consumer skill contains author-side SkillGuard control state
- **THEN** packaging and installation verification SHALL fail with the exact residual

### Requirement: Active skill resolution is compatibility-aware and singular
The system SHALL model exactly three layers: immutable bundled pack,
machine-installed inventory, and resolved active view. A Matters-managed
installed projection SHALL be a managed ownership subtype within the
machine-installed layer and SHALL NOT become a fourth layer. The system SHALL
select exactly one highest current validated compatible candidate for every
required skill after validating PEP 440 version/interval eligibility, explicit
prerelease acceptance, schema compatibility, content hash, runtime,
dependencies, native validator, and ResearchGuard identity when applicable.

#### Scenario: Local and bundled identities match
- **WHEN** machine-installed and bundled copies have the same version and content hash and both validate
- **THEN** the active view SHALL bind that exact identity deterministically

#### Scenario: Compatible local copy is newer
- **WHEN** the machine-installed copy is newer, validates, and declares
  compatibility with the current Matters and skill schema versions
- **THEN** the active view SHALL use it as a non-mutating local overlay and SHALL leave the bundled bytes unchanged

#### Scenario: Newer candidate is a prerelease
- **WHEN** PEP 440 ordering identifies a newer prerelease but its manifest does not explicitly allow prerelease use for the current compatibility intervals
- **THEN** the resolver SHALL exclude that candidate and SHALL NOT treat numerical ordering alone as compatibility

#### Scenario: Bundled copy is newer than an externally managed local copy
- **WHEN** the bundled copy is newer and valid but the older machine-installed copy is not marked Matters-managed
- **THEN** Matters SHALL use the bundled copy internally, leave the external installation unchanged, and expose an update-available disposition

#### Scenario: Same version has different content
- **WHEN** bundled and machine-installed copies declare the same version but different content hashes
- **THEN** the required skill SHALL be blocked as an identity collision until one validated authority is selected

#### Scenario: No compatible candidate exists
- **WHEN** every discovered candidate is invalid, incompatible, stale, or unavailable
- **THEN** the required skill SHALL remain visibly blocked without fallback, guessed compatibility, or silent downgrade

#### Scenario: Selected dependency identity changes
- **WHEN** a selected manifest, runtime, dependency, validator, or ResearchGuard identity changes after active-view resolution
- **THEN** the active view SHALL become stale and SHALL be resolved and natively validated again before the skill is used

### Requirement: Matters-managed skill synchronization is transactional
Only the Matters-managed ownership subtype inside the machine-installed layer
MAY be updated automatically. The updater SHALL stage
the selected consumer projection, validate inventory and native checks,
activate it atomically, run installed-currentness checks, and restore the prior
projection if any required post-activation check fails.

#### Scenario: Bundled copy supersedes a Matters-managed install
- **WHEN** the bundled copy is newer, current, compatible, and the installed projection is Matters-managed
- **THEN** the updater SHALL synchronize it transactionally and record separate source, bundle, active-view, and installed-projection identities

#### Scenario: Post-activation validation fails
- **WHEN** a required installed-currentness or native smoke check fails after activation
- **THEN** the updater SHALL restore the prior projection and report the failed candidate without claiming synchronization

### Requirement: ResearchGuard is the sole research-analysis provider
Matters SHALL define one versioned `ResearchOperation` boundary. The final real
provider SHALL be one frozen, validated ResearchGuard consumer pack and matching
engine that incorporates source discovery, temporal/evidence trace, and
argument reasoning.

Separate SourceGuard, TraceGuard, and LogicGuard runtime bindings SHALL NOT be
final parallel success paths or fallbacks.

#### Scenario: ResearchGuard integration is not frozen
- **WHEN** the ResearchGuard package, top-level consumer skill, member
  projections, manifest, compatibility declaration, native validation, and
  installed-currentness evidence are incomplete
- **THEN** real research work SHALL terminate as
  `researchguard_pending_integration` while deterministic synthetic
  `ResearchOperation` conformance remains runnable; inventory, autonomous
  non-research processing, optional inspection/correction, synthetic
  verification, and a blocked local candidate MAY continue, but the
  system SHALL NOT claim ResearchGuard-complete analysis or final v0.2
  complete-release

#### Scenario: Frozen ResearchGuard is current
- **WHEN** one compatible ResearchGuard package and consumer pack passes the
  declared integration and installed-currentness gates
- **THEN** Matters SHALL bind the real ResearchOperation provider to that exact
  identity and record its result as advisory evidence

#### Scenario: Legacy separate Guard artifact is discovered
- **WHEN** an old SourceGuard, TraceGuard, or LogicGuard receipt or binding is
  encountered during migration
- **THEN** it SHALL be classified as stale or source-only migration evidence
  and SHALL NOT become a parallel runtime provider

### Requirement: ResearchGuard currentness evidence is portable and complete
The external ResearchGuard gate SHALL consume one portable currentness receipt
that records `checked_at`, source commit, distribution state, command state,
top-level consumer-skill state, member-projection state, manifest state,
legacy/residual state, compatibility, native validation, installed currentness,
and terminal disposition. It SHALL NOT contain machine-local paths.

#### Scenario: Receipt is missing one required currentness field
- **WHEN** the ResearchGuard receipt omits a required field or binds a different source commit, distribution, command, skill, member, manifest, residual, compatibility, validator, or installed identity
- **THEN** ResearchGuard activation and the final v0.2 complete-release claim SHALL remain blocked

#### Scenario: Receipt contains a machine-local path
- **WHEN** a ResearchGuard currentness receipt contains a user-profile, repository, interpreter, or installation absolute path
- **THEN** the receipt SHALL be rejected as non-portable and SHALL NOT close the gate

### Requirement: Skill self-maintenance cannot self-edit product behavior
The system SHALL allow bundled skills to inventory sources, reconcile changes,
assess semantic freshness and depth, request bounded work, automatically
advance coverage-ledger stages, and present optional correction or exception
views through current product contracts. It SHALL NOT let runtime skills edit
production code, OpenSpec requirements, FlowGuard models, native validators,
or canonical core rules.

#### Scenario: Runtime evidence exposes a model miss
- **WHEN** a skill detects behavior that the current product or model cannot
  represent correctly
- **THEN** it SHALL emit a bounded Model Miss work item for the explicit
  development pipeline and SHALL keep the current runtime result partial or
  blocked

### Requirement: Semantic depth is explicit and freshness-bound
For every applicable tracked occurrence the system SHALL record one
revision-bound semantic-depth state: `not_assessed`, `partial`, `sufficient`,
`blocked`, or `stale`. `sufficient` SHALL require every policy-required
analysis class to have current anchored evidence or an explicit non-applicable
disposition and no unresolved blocking gap. `partial` SHALL mean useful current
analysis exists but sufficient criteria are unmet. `blocked` SHALL identify a
required source, extractor, ResearchGuard operation, original-owner dispatch,
localization, visual, or projection stage that cannot terminate.

#### Scenario: Required analysis is incomplete
- **WHEN** at least one current anchored result exists but another policy-required analysis class or owner stage remains unresolved
- **THEN** semantic depth SHALL be `partial`, the unmet criteria SHALL be visible, and the system SHALL NOT claim complete modeling

#### Scenario: Required operation cannot terminate
- **WHEN** a required source, extractor, current ResearchGuard operation, owner dispatch, localization, visual, or projection stage is unavailable or blocked
- **THEN** semantic depth SHALL be `blocked` with the exact blocking criterion

#### Scenario: A depth dependency changes
- **WHEN** source/inventory, tracking policy, anchor, model/provider, operation schema, dependency, validator, or user-decision identity changes
- **THEN** the affected semantic-depth assessment SHALL become `stale` until recomputed

#### Scenario: Semantic depth is sufficient
- **WHEN** every required analysis class has current anchored evidence or an explicit non-applicable disposition and no blocking gap remains
- **THEN** semantic depth MAY be `sufficient` for that exact occurrence, policy, provider, and revision scope

### Requirement: Skill runtime has a separate auxiliary FlowGuard owner
The system SHALL model bundled inventory, compatibility, active resolution,
managed synchronization, and validation/rollback under
`S0_matters_skill_runtime` with S1-S5 children. This auxiliary model SHALL own
skill-runtime infrastructure only and SHALL NOT become C13 or own any canonical
Matter field.

#### Scenario: Skill activation succeeds
- **WHEN** S1 inventory, S2 compatibility, S3 resolution, S4 synchronization
  if required, and S5 validation all terminate successfully
- **THEN** the active skill identity MAY be published without changing M0 or
  C1-C12 canonical ownership

#### Scenario: Skill activation is blocked
- **WHEN** any required S1-S5 owner is non-terminal, incompatible, failed, or stale
- **THEN** skill activation SHALL remain blocked while unaffected M0/C1-C12 capabilities report their own status independently
