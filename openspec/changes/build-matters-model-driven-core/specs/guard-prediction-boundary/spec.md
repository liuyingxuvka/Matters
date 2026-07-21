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

### Requirement: Future predictions use the unique World Model owner
The system SHALL preserve future predictions separately from current facts,
events, and lifecycle decisions. The lightweight `Forecast` value and
`GuardBridge.register_forecast` SHALL be retired as successful registration
paths. They SHALL explicitly reject use and direct callers to the unique C11
`PersistentAdvisoryWorldModel.publish` owner, which freezes the prediction's
evidence, verification condition, contradiction condition, observation horizon,
expiry, uncertainty, and alternatives before it is retained.

#### Scenario: Retired forecast shortcut is invoked
- **WHEN** a caller constructs `Forecast` or calls `GuardBridge.register_forecast`
- **THEN** the call SHALL fail visibly with `forecast_entrypoint_retired` and identify `PersistentAdvisoryWorldModel.publish` as the only prediction owner
- **AND** no forecast, current lifecycle state, Event, or canonical field SHALL be written

#### Scenario: World Model predicts delay
- **WHEN** `PersistentAdvisoryWorldModel.publish` receives a complete frozen prediction contract that indicates a future delay
- **THEN** the system SHALL display it only on the World Model or AI supplemental-information surface and SHALL NOT mark the Matter currently blocked

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
- **WHEN** a current evidence-bound Matter, person, event, deadline, open-loop, outcome-gap, material-clue, summary, supplemental-information, or hero-generation-brief finding passes the frozen package contract
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

### Requirement: Product execution is model-agnostic and capability-routed
Every AI work package SHALL request a declared capability role rather than a
required named model. The product SHALL support
`maintenance_orchestrator`, `deterministic_preprocessor`,
`low_cost_annotator`, `ambiguity_resolver`, `matter_modeler`,
`hero_image_generator`, and `consistency_reviewer`. Concrete model, provider,
reasoning, concurrency, budget, escalation, and substitution choices SHALL
live in a private machine-local Codex execution profile and SHALL NOT become
canonical Matter state, a public schema dependency, or a release identity.
The bounded pending-package response SHALL publish the active private
`execution_profile_identity` beside the immutable packages because result
admission requires that identity. This runtime envelope field SHALL NOT enter
the package fingerprint or expose the concrete model mapping.

#### Scenario: A Codex worker fetches pending packages
- **WHEN** the local service returns one or more immutable pending work packages
- **THEN** the response SHALL include the current `execution_profile_identity`, the worker SHALL copy it into each result, and changing the active mapping SHALL change only this runtime identity and its receipts

#### Scenario: The runtime identity is absent or stale
- **WHEN** a worker cannot bind its result to the active `execution_profile_identity`
- **THEN** admission SHALL keep the package pending with `execution_profile_identity_mismatch` and SHALL NOT discard, fabricate, or auto-apply semantic output

#### Scenario: High-volume annotation uses the current low-cost mapping
- **WHEN** an authorized low-reasoning package requests `low_cost_annotator` and the current machine profile maps that role to `gpt-5.6-luna` at low reasoning
- **THEN** Codex MAY execute that package with the mapped model, SHALL record the concrete private execution identity, and SHALL validate the same model-independent result contract

#### Scenario: Complex modeling escalates
- **WHEN** a package requires hierarchy synthesis, conflict resolution, or another declared complex capability
- **THEN** the router SHALL select the current compatible higher-capability mapping or terminate `pending_capability` without pretending that cheap annotation completed the complex work

#### Scenario: A daily run needs bounded delegation
- **WHEN** current work includes high-volume annotation plus merge, hierarchy, summary, or consistency judgment
- **THEN** `maintenance_orchestrator` SHALL use the strongest compatible current reasoning profile to plan the run, delegate only typed bounded low-cost packages, validate their structured results, and join them through the same original-owner path
- **AND** concrete primary or delegated model names SHALL remain only in private execution receipts

#### Scenario: A stable Matter needs a hero
- **WHEN** a root Matter requests `hero_image_generator` with a current privacy-minimized photographic theme brief
- **THEN** the active profile MAY invoke an available Codex image-generation capability and SHALL return a typed private generated asset or bounded unavailable/failed disposition without requesting an application-owned API key

#### Scenario: The machine changes its model mapping
- **WHEN** Luna, Terra, or another concrete model is added, removed, upgraded, or remapped
- **THEN** unchanged product work-package schemas and canonical Matter revisions SHALL remain valid and only affected private execution-profile receipts SHALL change

#### Scenario: No compatible Codex model is available
- **WHEN** no current profile mapping satisfies the requested capability contract
- **THEN** the operation SHALL remain `analysis_unavailable` or `pending_capability`, SHALL preserve completed work, and SHALL NOT request an application-owned API key or silently call a provider API

#### Scenario: A passed result only needs original-owner redispatch
- **WHEN** the desktop has no Codex runner but a current passed result was previously blocked by a missing owner prerequisite that has now recovered
- **THEN** maintenance SHALL select that result through a bounded indexed redispatch route and SHALL NOT rerun AI or perform a broad pending-package scan

### Requirement: Codex daily maintenance reuses the bounded product path
A compatible AI host SHALL create or repair exactly one daily scheduled task
during Matters setup. The task SHALL invoke the same CLI/MCP service path used
by interactive work after the installing AI verifies package, MCP, private
runtime, Skill Pack, authorization, and schedule identity. It SHALL resume only
authorized changed-item discovery, annotation, escalation, hierarchy repair,
material-clue/summary refresh, localization, generated-hero work, supplemental
information, and projection. It SHALL start with a
`maintenance_orchestrator`, MAY delegate typed low-cost packages to cheaper
current mappings, SHALL record private run and execution-profile receipts, and
SHALL NOT become a second canonical workflow.

#### Scenario: Installing AI chooses the schedule time
- **WHEN** the installing AI has user-context evidence for a low-activity local time
- **THEN** it SHALL use that time; otherwise it SHALL use 21:00 local, preserve the host timezone, and maintain exactly one schedule identity

#### Scenario: Setup authorization and read authorization differ
- **WHEN** the user asks the AI to install Matters but grants no new source-read scope
- **THEN** the AI SHALL configure the software and schedule without widening discovery, and the scheduled path SHALL remain blocked or no-delta for unauthorized sources

#### Scenario: Daily maintenance has current changed items
- **WHEN** the scheduled Codex task runs with current authorization and pending or stale ledger stages
- **THEN** it SHALL execute the next bounded idempotent work packages through the shared service path and leave every item at an exact terminal, pending, or blocked stage

#### Scenario: Daily maintenance has no delta
- **WHEN** the scheduled task finds no new, changed, moved, deleted, stale, or policy-affected input
- **THEN** it SHALL record a successful no-delta receipt without duplicating analysis, Matter revisions, projections, or notifications

#### Scenario: A scheduled run is missed or interrupted
- **WHEN** Codex, the computer, or the local service is unavailable, or a run stops before completion
- **THEN** no source or mailbox mutation SHALL occur and the next authorized run SHALL resume from durable checkpoints without claiming the missed run passed

#### Scenario: Final verification is due
- **WHEN** a release, install, Git, tag, final model, or full-test gate becomes pending
- **THEN** the routine scheduled task SHALL leave that gate not run for its explicit foreground owner rather than executing an unattended final verification

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

### Requirement: Personal Situation/World Model inference is persistent and advisory
The system SHALL maintain a versioned personal Situation/World Model read
projection that joins current source observations, people, times, Matters,
WorkItems, Events, open loops, outcomes, source groups, expected trajectories,
and gaps. C11 MAY add typed advisory hypotheses, forecasts, expected events,
and alternatives. M0 coordinates currentness and C12 publishes the projection;
the model SHALL NOT become a second canonical owner.

Every inference SHALL bind the exact SituationGraph/source/evidence snapshot,
statement, `ai_inferred` modality, confidence, supporting signals,
counter-signals, coverage boundary, alternatives, horizon, freshness/expiry,
and original-owner disposition. It SHALL survive restart, become stale when
any bound dependency changes, and remain visibly distinct from confirmed,
reported, or planned state.

Historical-gap inference and future prediction SHALL remain different
artifacts. Historical-gap inference MAY describe a necessary, already elapsed
activity as likely occurred. A future prediction SHALL remain a deliberately
fuzzy, testable model expectation and SHALL bind a verification condition,
contradiction condition, observation horizon, expiry, declared weakening
conditions, and a retrospective-review-on-conflict flag. It SHALL appear only
in AI supplemental information or the World Model surface and SHALL NOT be
written into the occurred timeline, lifecycle, outcome, or primary graph as a
fact.

A current-phase inference is a third, narrowly bounded advisory basis. It MAY
support `in_progress` only when a completed prerequisite, a still-required
next obligation, a current active window, and no current
completion/cancellation/postponement contradiction are all present. It
describes the most likely current workflow phase and SHALL NOT claim observed
activity or predict that the future outcome will succeed. C7 remains the only
lifecycle owner and SHALL preserve the inference as provisional.

#### Scenario: Expected event time has passed
- **WHEN** current evidence supports an expected event and its time has passed but no licensed observed-completion evidence exists
- **THEN** C11 MAY return `likely_occurred`, `likely_not_occurred`,
  `conflict_preserved`, or `insufficient` with confidence and alternatives
- **AND** the original lifecycle/outcome owners SHALL NOT convert that result into confirmed completion without their declared evidence

#### Scenario: Registration is complete and preparation is now the active phase
- **WHEN** a confirmed registration precedes a future required submission and the current-phase policy is satisfied
- **THEN** C11 MAY propose `current_phase_in_progress` with confidence, alternatives, coverage, expiry, and contradiction triggers
- **AND** C7 MAY accept it only as a provisional `in_progress` basis while submission remains planned and future success remains a separate prediction

#### Scenario: Inference depends on no contrary message
- **WHEN** the inference uses current covered mail or file scope and finds no cancellation, refund, or contrary record
- **THEN** it SHALL describe that condition as coverage-bounded missing contradiction, not as proof that no contrary event exists

#### Scenario: Inference dependency changes
- **WHEN** a source, graph edge, event, hierarchy, policy, coverage, or model identity bound to the inference changes
- **THEN** the inference and every dependent summary/graph/UI projection SHALL become stale until the same advisory owner recomputes or returns an explicit terminal disposition

#### Scenario: Daily maintenance refreshes world inference
- **WHEN** the Codex-hosted maintenance run selects stale or missing Situation/World Model inference work
- **THEN** it SHALL execute bounded model-agnostic advisory packages and dispatch results through the same C11/M0/C12 path without creating a new scheduler-owned truth route

#### Scenario: Future prediction is registered
- **WHEN** C11 predicts that a future application, trip, submission, payment, or project milestone may reach an outcome
- **THEN** it SHALL freeze the prediction before the observation, record how and by when it can be verified or contradicted, preserve uncertainty and alternatives, and prohibit canonical writes
- **AND** C12 SHALL label it as a future AI prediction rather than an occurred Event or current lifecycle state

#### Scenario: Later evidence agrees with the prediction
- **WHEN** a strictly later, licensed observation satisfies the frozen verification condition
- **THEN** the World Model SHALL append a confirmed feedback record while the original C5-C9 owner independently records any newly licensed fact
- **AND** the prediction itself SHALL remain historical advisory evidence rather than becoming the fact owner

#### Scenario: Later evidence contradicts the prediction
- **WHEN** a strictly later, licensed observation satisfies the frozen contradiction condition
- **THEN** the World Model SHALL preserve the prediction and contradictory observation, append a `contradicted` feedback record, and enqueue one idempotent model-miss review
- **AND** that review SHALL re-examine the original evidence sufficiency, source grouping, Matter merge/split, temporal interpretation, and model boundary that licensed the prediction
- **AND** runtime SHALL NOT silently rewrite the prediction, the observation, or a past canonical state

#### Scenario: Prediction reaches its horizon without decisive evidence
- **WHEN** the verification horizon or expiry passes without satisfying either condition
- **THEN** the prediction SHALL become `expired` or `unresolved`, remain visible as non-confirming model history, and SHALL NOT be counted as predictive success

### Requirement: AI receives a bounded model map and situation packet
The system SHALL expose one model-agnostic AI gateway over MatterService/MCP.
It SHALL provide a bounded functional map of M0, C1-C12, S0, and A0-A3 and one
revision-bound `SituationContextPacket` for a selected Matter. The packet SHALL
contain only current permitted projections, distinguish confirmed, reported,
planned, and `ai_inferred` modalities, include coverage/freshness and gaps, and
use bounded continuation handles for additional history.

A3 SHALL own only gateway query and feedback receipts. It SHALL NOT become C13,
write a C1-C12 canonical field, inspect raw private storage, or claim that a
missing ResearchGuard result is equivalent to completed research.

#### Scenario: AI asks what is happening now
- **WHEN** an authorized AI requests current context for one Matter
- **THEN** the gateway SHALL return the exact Matter revision, relevant current situation and World Model projections, current gaps, and `as_of` identity without returning an unbounded history or raw private path

#### Scenario: AI asks where to find a kind of information
- **WHEN** an AI traverses the functional model map by purpose or relation
- **THEN** the gateway SHALL return the existing owner and supported operation, not a database table or a new write route

### Requirement: AI feedback is typed, append-only, and owner-dispatched
The gateway SHALL distinguish `user_observation`, explicit `correction`,
`prediction_feedback`, and `model_miss`. Every accepted item SHALL receive an
idempotent durable receipt with Matter identity, type, bounded source
attribution, freshness, status, and required owner disposition.

A user observation SHALL remain reported candidate evidence until an original
owner validates it. An explicit correction SHALL route through C10. Prediction
feedback SHALL evaluate a frozen C11 prediction without rewriting either
record. A model miss SHALL enter the development-maintenance queue and SHALL
NOT edit code, OpenSpec, FlowGuard, or runtime rules automatically.

#### Scenario: AI learns a new fact from the user
- **WHEN** the user states a new bounded observation in a Codex conversation
- **THEN** A3 SHALL append a minimized `user_observation` receipt, omit the full conversation by default, and expose the pending original-owner disposition for later maintenance

#### Scenario: AI identifies a factual correction
- **WHEN** the user explicitly says a current Matter fact is wrong and supplies replacement scope
- **THEN** the gateway SHALL call the existing C10 correction contract and SHALL NOT disguise the change as an ordinary observation

#### Scenario: AI compares prediction with reality
- **WHEN** a strictly later licensed observation verifies, contradicts, or leaves a frozen prediction unresolved
- **THEN** the gateway SHALL call the existing C11 feedback contract, preserve prediction and observation history, and return the resulting feedback/model-miss disposition

#### Scenario: AI notices a software or model gap
- **WHEN** runtime use exposes a missing owner, invalid model assumption, unsafe route, or non-representable case
- **THEN** A3 SHALL append a bounded model-miss clue for the development pipeline and SHALL keep the current product result partial, blocked, or stale rather than self-editing

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

### Requirement: Background workers can consume only their exact assigned package set
The private pending-work facade and CLI SHALL support exact package-id,
source-revision, and task-kind selectors in addition to the existing bounded
local-operator page. Selectors SHALL be conjunctive, single-line, and evaluated
before pagination so the returned total and continuation describe only the
assigned set. A selector SHALL NOT expose raw source content, private paths, or
unrelated pending packages.

#### Scenario: A capability worker receives one exact source-revision refresh
- **WHEN** the orchestrator supplies an exact package id, source revision, and task kind to a background worker
- **THEN** the pending-work facade SHALL return only a pending current package matching all three selectors or an empty page, and SHALL preserve the normalized selectors in the private response receipt

#### Scenario: The local operator requests the existing bounded pending page
- **WHEN** no exact selector is supplied
- **THEN** the facade SHALL retain the existing capability-role filtering, bounds, ordering, pagination, and disclosure boundary without converting the worker selector into a new public data API

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

### Requirement: Hierarchy findings remain advisory and typed
AI and ResearchGuard hierarchy work SHALL use typed
`matter_structure_candidate`, `containment_candidate`, `reparent_candidate`,
`split_candidate`, `merge_candidate`, `work_item_candidate`, and
`event_assignment_candidate` findings. Each finding SHALL cite current allowed
evidence and SHALL enter the existing C5/C6/C7-C10 owners rather than writing
containment, lifecycle, outcome, or projection state.

#### Scenario: AI proposes parent and child structure
- **WHEN** a current bounded work package proposes a root Matter and several children
- **THEN** the dispatcher SHALL route each typed finding exactly once to its declared owner and SHALL preserve unsupported or conflicting alternatives without creating a second hierarchy authority
