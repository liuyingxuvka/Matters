## ADDED Requirements

### Requirement: Research and AI artifacts are advisory
The system SHALL store AI, ResearchGuard, and forecast results as versioned
findings, gaps, proposals, or forecasts and SHALL NOT let them write canonical
fields directly. Legacy SourceGuard, TraceGuard, and LogicGuard outputs SHALL
remain explicitly stale or source-only migration evidence rather than parallel
runtime providers.

#### Scenario: ResearchGuard proposes a lifecycle state
- **WHEN** a ResearchGuard artifact proposes that a Matter is blocked
- **THEN** the lifecycle owner SHALL treat it as a candidate and require licensed evidence before any state change

### Requirement: Research receipts must be current and scoped
The system SHALL reject stale, skipped, not-run, progress-only, foreign, or
scope-incompatible ResearchGuard receipts as promotion evidence.

#### Scenario: Source revision changes after research execution
- **WHEN** a ResearchGuard receipt references an older source or model revision
- **THEN** the artifact SHALL become stale and SHALL NOT support a current canonical decision

### Requirement: Forecasts do not change current state
The system SHALL preserve forecasts separately from current facts, events, and
lifecycle decisions.

#### Scenario: Forecast predicts delay
- **WHEN** a forecast indicates a future delay
- **THEN** the system SHALL display it as a forecast and SHALL NOT mark the Matter currently blocked

### Requirement: Agent operations are versioned executable work
Every AI or local-skill operation SHALL bind an operation id, runner identity,
tool or skill identity and version, prompt-contract revision and hash, output
schema revision and hash, decision-policy revision, owner-schema revision,
locale-registry revision, autonomy mode, authorization id, exact SourceVersion
and EvidenceAnchor inputs, allowed evidence/asset/tool ids, deterministic input
fingerprint, terminal execution status, output payload, input dispositions,
gaps, and evidence references.

#### Scenario: Current local skill returns a valid result
- **WHEN** an authorized agent operation terminates successfully with a schema-valid anchored result
- **THEN** the system SHALL store the result as a current advisory artifact and automatically dispatch every typed finding exactly once to its declared canonical owner

#### Scenario: Local skill is unavailable
- **WHEN** a requested AI or local skill runner is not configured or installed
- **THEN** the operation SHALL terminate as unavailable and the UI SHALL expose that status without claiming analysis success

#### Scenario: Local skill execution fails
- **WHEN** a configured runner exits with an error or returns a schema-invalid payload
- **THEN** the operation SHALL terminate as failed with a bounded error and SHALL NOT emit promotable candidates

#### Scenario: Extracted source anchors require semantic understanding
- **WHEN** a tracked file, Gmail message, or supported image produces current precise EvidenceAnchors
- **THEN** the service SHALL queue bounded private work packages that preserve the exact SourceVersion and evidence whitelist without exposing adjacent content

#### Scenario: Understanding output is bilingual and revision-bound
- **WHEN** a semantic-understanding result is submitted for a frozen work package
- **THEN** every finding SHALL contain non-empty semantically equivalent `en` and `zh-CN` statements, cite only allowed evidence ids, and bind the exact package source revision or the result SHALL fail without creating a candidate

#### Scenario: Valid understanding output is imported
- **WHEN** a current evidence-bound Matter, person, event, deadline, open-loop, outcome-gap, summary, or card-visual finding passes the frozen package contract
- **THEN** the deterministic dispatcher SHALL route it exactly once to the declared original C4-C9/C12 owner without a confirmation token, and the operation owner SHALL NOT write canonical product state itself

#### Scenario: Ordinary uncertainty remains
- **WHEN** a valid finding is inferred, low-confidence, or has competing interpretations but does not violate authorization, schema, safety, or owner policy
- **THEN** the system SHALL preserve modality, confidence band, alternatives, uncertainty codes, and evidence ids and SHALL continue automatic owner dispatch instead of creating `review_required`

#### Scenario: No licensed fact is supported
- **WHEN** the frozen inputs support no valid finding for a requested class
- **THEN** the operation SHALL return a typed `no_finding`, `not_applicable`, `insufficient`, or `blocked` disposition for each affected input and SHALL NOT fabricate a candidate

#### Scenario: ResearchGuard merger is not current
- **WHEN** the requested research operation has no frozen compatible ResearchGuard package, consumer pack, and validation identity
- **THEN** the operation SHALL terminate as `researchguard_pending_integration` and SHALL NOT execute separate legacy Guard bindings

### Requirement: AI scope triage is bounded and auditable
An AI scope-triage operation SHALL classify only occurrences in its authorized
work package and SHALL return a reversible proposed tracking disposition,
reason, confidence, evidence-feature references, model/provider identity,
policy revision, and freshness fingerprint.

#### Scenario: AI classifies an item as irrelevant
- **WHEN** a current scope-triage result satisfies the user-approved automatic-decision policy
- **THEN** the C1 authorization/coverage owner MAY append a `not_tracked` disposition with the AI result as advisory evidence

#### Scenario: AI is uncertain or source may be valuable
- **WHEN** the result is below the policy threshold, conflicts with a prior user override, or proposes excluding a protected source type
- **THEN** the C1 policy SHALL select the conservative reversible disposition, preserve confidence and alternatives, respect the current user override, and SHALL NOT silently exclude the item or require approval

#### Scenario: AI requests broader content
- **WHEN** scope triage requests an adjacent file, another mailbox item, an undeclared tool, or more content than the work package permits
- **THEN** the operation SHALL terminate scope-incompatible without expanding authorization

#### Scenario: Inventory or policy becomes newer
- **WHEN** the occurrence fingerprint, inventory revision, or tracking-policy revision changes after triage
- **THEN** the prior triage result SHALL become stale and SHALL NOT control current tracking

### Requirement: Agent operations cannot expand read scope
An AI or local-skill runner SHALL receive only the content and anchors in its
authorized work package and SHALL NOT request or read adjacent files,
directories, mailboxes, cloud services, Jira, or Rovo.

#### Scenario: Skill attempts to read a sibling file
- **WHEN** a skill operation requests a path not present in the work package
- **THEN** the operation SHALL be rejected as scope-incompatible without reading that path

### Requirement: No silent heuristic equivalence
The system SHALL NOT substitute keyword heuristics or an unversioned parser for
an unavailable AI/local-skill operation while reporting the requested
operation as successful.

#### Scenario: Requested AI runner is absent
- **WHEN** the user requests AI-assisted analysis and no current runner is available
- **THEN** the system SHALL return `analysis_unavailable`, preserve source and completed stages, schedule retry when allowed, and SHALL NOT fabricate an AI result or create a confirmation queue

### Requirement: Every work-package input is explicitly accounted
The validator SHALL require every frozen evidence or asset input to receive
exactly one current disposition such as `used`, `duplicate`, `irrelevant`,
`insufficient`, or `conflicting`. Empty findings SHALL pass only when all
inputs are explicitly accounted and no requested class requires a supported
finding.

#### Scenario: Runner silently omits an input
- **WHEN** a result omits a frozen evidence or asset id or assigns more than one incompatible disposition
- **THEN** validation SHALL fail with the exact input id and SHALL NOT dispatch any finding

### Requirement: Automatic dispatch is durable and idempotent
The dispatcher SHALL persist the finding, source revision, owner model,
prompt/schema/policy identities, retry state, and terminal owner disposition.
It SHALL never become a canonical data owner and SHALL not publish C12 until
all required original-owner results for the active revision are terminal.

#### Scenario: Service restarts during owner dispatch
- **WHEN** the service restarts after a valid finding is stored but before its owner result is terminal
- **THEN** the dispatcher SHALL resume the exact pending owner command without creating a duplicate finding, owner revision, or projection

#### Scenario: Owner rejects an unsupported proposal
- **WHEN** the declared owner determines that a valid advisory finding lacks the evidence required for a canonical write
- **THEN** the owner SHALL return `policy_rejected`, `source_only`, `candidate`, `uncertainty_preserved`, `not_applicable`, or `blocked` as appropriate and the pipeline SHALL continue without user confirmation
