## flowguard-project-adopt - FlowGuard project adopt record update

- Project: matters
- Trigger reason: target project requires current semantic adoption and version records
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-07-18T08:51:08+00:00
- Ended: 2026-07-18T08:51:08+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- none recorded

### Commands
- OK (0.000s): `managed adoption rule-set preflight` - generated block contains every required stable rule
- OK (0.000s): `canonical FlowGuard skill-suite validation` - blocked
- OK (0.000s): `post-write project adoption audit` - semantic and version parity after write

### Findings
- suite_inventory_unresolved: Canonical FlowGuard skill-suite validation is unresolved.
- adoption_record_written: FlowGuard project AGENTS block and manifest were written or refreshed.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- Project adoption does not replace executable model checks, tests, replay, or closure evidence.

### Risk Evidence Summary
- none recorded

### Next Actions
- python -m flowguard project-audit --root . --json
- python scripts/verify_skill_suite_markers.py --root . --json
- Rerun affected FlowGuard model checks and focused tests before broad confidence.


## flowguard-project-upgrade - FlowGuard project upgrade record update

- Project: matters
- Trigger reason: target project requires current semantic adoption and version records
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-07-18T15:48:44+00:00
- Ended: 2026-07-18T15:48:44+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- none recorded

### Commands
- OK (0.000s): `managed adoption rule-set preflight` - generated block contains every required stable rule
- OK (0.000s): `canonical FlowGuard skill-suite validation` - pass
- OK (0.000s): `post-write project adoption audit` - semantic and version parity after write

### Findings
- adoption_record_written: FlowGuard project AGENTS block and manifest were written or refreshed.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- Project adoption does not replace executable model checks, tests, replay, or closure evidence.

### Risk Evidence Summary
- none recorded

### Next Actions
- python -m flowguard project-audit --root . --json
- python scripts/verify_skill_suite_markers.py --root . --json
- Rerun affected FlowGuard model checks and focused tests before broad confidence.


## flowguard-project-upgrade - FlowGuard project upgrade record update

- Project: matters
- Trigger reason: target project requires current semantic adoption and version records
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-07-18T21:09:44+00:00
- Ended: 2026-07-18T21:09:44+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- none recorded

### Commands
- OK (0.000s): `managed adoption rule-set preflight` - generated block contains every required stable rule
- OK (0.000s): `canonical FlowGuard skill-suite validation` - pass
- OK (0.000s): `post-write project adoption audit` - semantic and version parity after write

### Findings
- adoption_record_written: FlowGuard project AGENTS block and manifest were written or refreshed.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- Project adoption does not replace executable model checks, tests, replay, or closure evidence.

### Risk Evidence Summary
- none recorded

### Next Actions
- python -m flowguard project-audit --root . --json
- Rerun affected FlowGuard model checks and focused tests before broad confidence.


## matters-testmesh-release-state-miss - Repair TestMesh release-state and G8 acceptance semantics

- Project: matters
- Trigger reason: the first full clean-clone release owner passed every suite
  but the parent validator retained a routine-only status
- Status: completed
- Skill decision: used_flowguard_model_miss_review

### Model Files

- `flowguard_design/run_test_mesh.py`
- `flowguard_design/run_g8_review.py`

### Commands

- OK (95.900s): full TM01-TM23 owner - exposed an incorrect routine-only
  parent state after every suite had passed
- OK (1.050s): focused release/routine parent-status regression

### Findings

- The parent receipt now emits `release_green` only when no suite is deferred.
- The release claim boundary covers TM01-TM23 and preserves the incomplete
  private semantic-coverage boundary.
- G8 accepts the exact routine or exact release TestMesh shape while still
  requiring native-green evidence.

### Counterexamples

- A full release run must not claim that TM19 remains deferred.
- G8 must not reject a current release TestMesh solely because it is no longer
  the routine deferred shape.

### Next Actions

- Commit the validator repair.
- Run one accepted final TM01-TM23 owner in a new clean clone.
- Freeze release evidence only after G8 and public boundaries consume it.


## matters-ui-revision-line-ending-miss - Canonicalize UI revision identity across Git projections

- Project: matters
- Trigger reason: clean-clone release validation found an LF versus CRLF-only
  UI revision mismatch
- Status: completed
- Skill decision: used_flowguard_model_miss_review

### Model Files

- `flowguard_design/ui_flow_structure.py`

### Findings

- UI authority fingerprinting canonicalizes CRLF and CR to LF before hashing.
- A focused regression requires equivalent LF and CRLF authority text to
  produce the same revision.

### Counterexamples

- Git may change line endings without changing UI behavior; raw text bytes
  therefore cannot define a portable installed-currentness identity.

### Next Actions

- Commit the canonical revision repair.
- Rerun installed UI validation against the frozen package.
- Rerun the accepted final release owner after source identity is frozen.


## matters-v0.2-model-miss-and-release-routing

- Project: matters
- Trigger reason: real Gmail canary, large private ledger, installed UI, and release closure exposed post-green misses
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-07-19T05:31:00+00:00
- Ended: 2026-07-19T05:31:00+00:00

### Repaired model-miss classes

- Authorized Gmail bodies now receive priority within the exact content budget.
- Coverage summaries refresh once at the terminal batch join.
- Matter-to-coverage lookup uses a durable transactionally maintained index.
- Installed UI verification has bounded phases and guaranteed browser cleanup.
- DevelopmentProcessFlow consumes minimized G9 private evidence, current G10 installed UI evidence, G11 clean-clone/package evidence, and G12 frozen local-release identities.

### Claim boundary

This record contains only public failure classes, repairs, and evidence routes. It contains no private source values, paths, identifiers, excerpts, hashes, screenshots, or model payloads. Complete private semantic coverage, Figma evidence, Linux CI, license authorization, and GitHub publication are not claimed.

### Next actions

- Run one frozen M0/C1-C12 model owner and one frozen S0-S5 model owner.
- Run the full tests and TM19 in a clean clone.
- Build, install, tag, and rerun G12 against exact synchronized identities.


## flowguard-project-upgrade - FlowGuard project upgrade record update

- Project: matters
- Trigger reason: target project requires current semantic adoption and version records
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-07-18T23:22:44+00:00
- Ended: 2026-07-18T23:22:44+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- none recorded

### Commands
- OK (0.000s): `managed adoption rule-set preflight` - generated block contains every required stable rule
- OK (0.000s): `package-authority/global-consumer validation` - pass
- OK (0.000s): `post-write project adoption audit` - semantic and version parity after write

### Findings
- adoption_record_written: FlowGuard project AGENTS block and manifest were written or refreshed.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- Project adoption does not replace executable model checks, tests, replay, or closure evidence.

### Risk Evidence Summary
- none recorded

### Next Actions
- python -m flowguard project-audit --root . --json
- Rerun affected FlowGuard model checks and focused tests before broad confidence.


## flowguard-project-upgrade - FlowGuard project upgrade record update

- Project: matters
- Trigger reason: target project requires current semantic adoption and version records
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-07-19T05:42:01+00:00
- Ended: 2026-07-19T05:42:01+00:00
- Duration seconds: 0.000
- Commands OK: True

### Model Files
- none recorded

### Commands
- OK (0.000s): `managed adoption rule-set preflight` - generated block contains every required stable rule
- OK (0.000s): `package-authority/global-consumer validation` - pass
- OK (0.000s): `post-write project adoption audit` - semantic and version parity after write

### Findings
- adoption_record_written: FlowGuard project AGENTS block and manifest were written or refreshed.

### Counterexamples
- none recorded

### Friction Points
- none recorded

### Skipped Steps
- Project adoption does not replace executable model checks, tests, replay, or closure evidence.

### Risk Evidence Summary
- none recorded

### Next Actions
- python -m flowguard project-audit --root . --json
- Rerun affected FlowGuard model checks and focused tests before broad confidence.
