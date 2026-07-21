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


## matters-gmail-metadata-owner-reconciliation

- Status: completed with shared parent TestMesh and rebased BCL evidence blocked
- Route: OpenSpec apply + Behavior Commitment Ledger change + FlowGuard Model Miss Review over C1/C2/M0
- Miss type: `input_branch_missing`
- Primary owner: `C2_source_registry`; C1 owns exact inventory/coverage admission and M0 owns the coverage join
- Private data access: not run

### Root-cause backpropagation

- Previous claim: current Gmail inventory and ObjectCoverage implied current
  message provenance.
- Observed failure: `SourceWorkflow` skipped every non-`tracked` disposition,
  so current `metadata_only` and identity-only message rows could lack a C2
  SourceVersion.
- Repaired branch: every exact current metadata-only Gmail message can receive
  one minimal private SourceVersion; no body, evidence, semantic work, Matter,
  person, event, or projection is created.
- Existing body-bearing SourceVersions are preserved, and stale, inactive,
  ambiguous, foreign-scope, non-message, or nonterminal inputs write nothing.
- Legacy repair accepts only a verified terminal page chain and a deterministic
  exclusive object-id cursor with a batch from 1 through 500. Exact retry is
  no-delta.
- Field lifecycle: no new persisted product schema field was introduced; the
  cursor and counters are bounded operation-result values.

### Same-class family and evidence

- The generalized family is: missing exact current owner, already current,
  existing body preserved, stale/foreign owner, and exact retry.
- C1/C2/M0 known-bad proofs reject scope escape, body downgrade, unbounded or
  semantic dispatch, and false M0 completion.
- OpenSpec strict validation passed.
- `85` focused source/Gmail/continuation/CLI regressions passed.
- TM15 executed `90` passing tests with one declared skip; the affected leaf
  receipt is current, while the shared parent remains blocked by older
  peer-owned inventory revisions.
- C1, C2, and M0 executable models passed; ModelMesh is green with zero unbound
  outputs.
- G4 structural review is green with execution explicitly not run.
- FlowGuard 0.58.5 / schema 1.0 adoption audit passed.

### Claim boundary

No private Gmail payload, real store, mailbox mutation, real reconciliation,
installation, Git, tag, or release was run. The BCL change intentionally
invalidated prior primary-path evidence; its broad coverage review remains
blocked until the integration owner refreshes current path/material/risk
evidence.

## matters-gmail-no-text-body-terminal

- Status: completed with shared parent TestMesh blocked
- Route: OpenSpec apply + FlowGuard C1/C2/C3/M0 + ModelMesh
- Private data access: not run

### Contract

- `available` still requires a non-empty body.
- `no_text_body` requires `body=""` and one importer-recomputed,
  domain-separated canonical-row SHA-256 recovery proof.
- The no-text branch writes only a minimized content disposition and owned
  terminal coverage pointers. It creates no body SourceVersion, EvidenceAnchor,
  semantic work package, Matter, person, event, or projection.
- Existing Gmail metadata remains current for relationship and chronology use.
- Exact replay is no-delta.

### Evidence

- Strict OpenSpec validation passed.
- 45 focused parser, owner, idempotency, and CLI regressions passed.
- TM15 passed 84 tests with one declared skip.
- C1, C2, C3, and M0 executable models passed; ModelMesh is green with zero
  unbound outputs.
- G4 structural review is green with execution explicitly not run.
- FlowGuard 0.58.5 / schema 1.0 adoption audit passed.

### Boundary

No private library or raw-recovery artifact was read or written, and no real
import, mailbox mutation, direct model/API call, installation, Git, tag, or
release was performed. The shared parent TestMesh remains blocked by older
peer-owned stale receipts even though the affected TM15 leaf passed.

## matters-gmail-body-continuation-import

- Project: matters
- Status: completed with an unrelated public-inventory blocker
- Skill decision: OpenSpec apply + existing-model preflight + DevelopmentProcessFlow
- Claim boundary: synthetic continuation service/CLI, C1/C2/C3/M0, mesh, G4
  structure, and focused tests only; no private runtime or real Gmail import

### Contract and model result

- The private manifest is a JSON array of exact
  `message_id`, `source_page_identity`, and positive `batch_number` rows.
- A connector result is accepted only when its raw-manifest SHA-256 and exact
  batch of at most 20 messages match; every message contains only
  `message_id`, non-empty `body`, and `content_status=available`.
- Foreign, duplicate, blocked, empty, extra-field, over-budget, stale-owner,
  and current-body-conflict cases reject before writes.
- The deterministic leaf invokes no model, provider API, connector read, or
  mailbox mutation and never writes Matter/person/event/projection owners.

### Evidence

- C1, C2, C3, and M0 executable model runs passed their abstract/hazard gates.
- ModelMesh returned `mesh_green`; G4 structural review returned
  `g4_design_green` with execution still honestly `not_run`.
- `91` focused Gmail/source/store/CLI regressions passed.
- The wider run passed `99` tests and had one unrelated failure: parallel
  retirement removed `matters-card-visual-curation` files while the required
  public inventory still named them.
- FlowGuard project audit passed on package `0.58.5`, schema `1.0`.

## matters-background-refresh-control-stability - Preserve operable controls during background refresh

- Project: matters
- Trigger reason: browser evidence showed the Standard/Compact control repeatedly detached while the processing poll rebuilt the whole shell every three seconds
- Status: completed with installed and private-runtime follow-up
- Skill decision: existing-model preflight + UI Flow Structure + Model Miss Review
- Miss type: `code_boundary_mismatch`
- Primary owner: `C12_projection_bilingual_ui`
- Claim boundary: the synthetic 8767 browser and current UI revision prove the repaired same-class control-stability behavior; installed 8766 and private usefulness remain separate gates

### Root cause backpropagation

- The existing stable-region rule already promised that background status would not disable or move the current catalog controls.
- `loadBrowser()` nevertheless called the full-shell renderer before and after every unchanged background response.
- A density click therefore encountered a detached DOM node for the full five-second browser action window.
- The repair gives scheduled refresh an explicit background path: unchanged catalog data updates only the coverage status region; changed catalog data still performs one current render.

### Generalized case and evidence

- ContractExhaustion now includes unchanged, changed, and failed background-refresh cases.
- The same-class boundary covers density, language, settings, search, filters, and Matter-open controls because all share the stable shell.
- The live verifier now freezes the density node across two processing polls, clicks it, checks compact dates for clipping, and captures English/Chinese Standard/Compact screenshots at exact `1880x900` and `1440x900` viewports.
- `20` focused UI/evidence tests passed.
- The synthetic live verifier passed all `70` required checks with no browser errors.
- UI Flow Structure returned `ui_flow_green` with a current exact runtime inventory.

### Residual risk

- The current receipt is synthetic and source-served. The exact installed build and the private 8766 catalog must consume the same UI revision before release closure.

## matters-reconciliation-query-shape-parent-narrative - Current contract and parent narrative refresh

- Project: matters
- Trigger reason: current runtime reconciliation/query-shape work and the observed latest-child-as-parent-summary defect required the existing C1/C2/C5/C6/C10/C12/M0 boundaries to be refreshed
- Status: completed_with_downstream_gates_blocked
- Skill decision: existing-model preflight + DevelopmentProcessFlow + Model-Test Alignment + TestMesh
- Ended: 2026-07-20T01:03:41Z
- Claim boundary: current OpenSpec, executable model, mesh, G4 structural, focused test, and adoption evidence only; no install, Git, release, private completeness, or live UI claim

### Evidence

- Strict OpenSpec validation passed.
- C5, C6, C12, and M0 executable model owners passed after adding the parent-narrative boundary.
- ModelMesh, existing-model preflight, and G4 structural review passed.
- `82` focused reconciliation/hierarchy/activity/catalog tests and `11` mesh/Gmail safety tests passed.
- FlowGuard project audit passed with package `0.58.5` and schema `1.0`.

### Findings

- Indexed catalog paging and visible-id hydration now have a real uniquely owned test.
- Parent overview synthesis must bind the complete current child/projection/evidence revision set; the latest child summary is not a project overview.
- Parent narrative generation may update only the bilingual overview. Title, lifecycle, activity recency/order, and generated-hero identity remain owned elsewhere.
- A material child clue queues narrative refresh but narrative processing time never becomes activity evidence.

### Blocked downstream gates

- DPF remains at `current_gate=none`, `next_gate=G0`: G0/G1 and later implementation, private-run, installed-UI, package, Git/tag, and release identities are not current on this shared changing worktree.
- OpenSpec task 10.80 remains open until the runtime owner and its focused tests prove the five affected parent Matters receive complete-scope bilingual narratives.

## 2026-07-19 — Live icon static-asset model miss

- Miss type: `boundary_missing` under `BC-PR-012` / `C12_projection_bilingual_ui`.
- Observed failure: the user-running 8766 service returned 404 for both `/matters-icon.png` and `/favicon.ico`, so the sidebar showed a broken image.
- Root cause: current UI files were hot-read by an older installed Python process whose fixed static-route map did not include the new assets.
- Generalized repair: `LocalUI` now blocks startup when `index.html` references any unregistered or missing local asset.
- Evidence: the observed PNG failure, same-class favicon failure, an unregistered-asset regression, 18 focused passing tests, all four index assets returning 200, and a live browser check with the 1254px source image rendered at 38px without overlap or console warnings.
- Legacy disposition: the old active process and its child reached zero before a source-aligned owner replaced it. The older installed package remains inactive and is not claimed current.
- Claim boundary: the active 8766 broken-asset class is closed; full installed-package, C12 hierarchy, and release evidence remains outside this focused repair.

## 2026-07-19 — User-approved Matters default icon

- Reused the existing `BC-PR-012` / `C12_projection_bilingual_ui` product-runtime owner; no new behavior path was added.
- Recorded the bounded user exception in OpenSpec: the left-sidebar icon is `38×38px` and the adjacent `Matters` wordmark is `26px`; all other frozen UI sizing remains unchanged.
- Verified the selected PNG is byte-identical to the user-provided source (`sha256:0eb2e4ea3a6268b05bbe1ef81eb22a6ed3517791f9f5eb85c59a73e71e891161`).
- Passed 16 focused tests, wheel asset inspection, strict OpenSpec validation, and a live browser inspection with no brand/search overlap or console warnings.
- Claim boundary: this proves focused icon integration, packaging, and brand-region layout only. Full C12, hierarchy, UI-flow, installed-package, and release evidence remains outside this focused change while concurrent hierarchy work is active.


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

## matters-transparent-icon-canvas - Transparent Matters icon exterior

- Project: matters
- Trigger reason: user explicitly corrected the live UI because the icon was still displayed inside an unwanted white frame
- Status: completed
- Skill decision: existing-model preflight + UI Flow Structure + DevelopmentProcessFlow
- Claim boundary: focused icon transparency, packaging, and live brand-region presentation only; broader C12, hierarchy, installed-package, and release evidence remain outside this correction

### Evidence

- FlowGuard 0.58.4 / schema 1.0 project audit passed.
- The canonical PNG is RGBA and all four corner alpha values are `0`.
- `16` focused entrypoint and desktop tests passed.
- Strict OpenSpec validation passed.
- The current wheel contains the transparent PNG and regenerated ICO.
- The live 8766 icon bytes match source SHA256 `7a7d097fc9942e3706753d4bcee74fe54f6a2185af565f0d6817a06c5e4f0612`.
- Browser inspection observed a `38px` icon on the navy sidebar with transparent computed background, `0px` radius, a `26px` wordmark, no overlap, and no console warnings.

### Counterexample and correction

- Previous: preserving the supplied opaque raster canvas byte-for-byte left the correct stacked-card artwork inside an unwanted white exterior.
- Corrected: preserve only intrinsic card whites/creams, make the external canvas transparent, remove image-element background and clipping, and verify both corner alpha and the live owning surface.

### Skipped broader evidence

- Full C12/UI Flow Structure execution remains with the concurrent hierarchy owner and was not claimed current from this focused correction.
- Live machine installation remains with the existing frozen release/install owner.

## matters-enlarge-sidebar-icon-only - Enlarge only the sidebar icon

- Project: matters
- Trigger reason: the user reported that the icon still appeared too small and explicitly approved the existing title font
- Status: completed
- Skill decision: existing-model preflight + UI Flow Structure + DevelopmentProcessFlow
- Claim boundary: focused sidebar icon sizing, live geometry, and wheel projection only

### Evidence

- The transparent icon box changed from `38×38px` to `48×48px`.
- The `Matters` title remains `700 26px/28px`.
- `16` focused tests and strict OpenSpec validation passed.
- Live 8766 geometry measured a `10px` icon/title gap and `32px` brand/search gap with no overlap or console warnings.
- The current wheel contains the exact `48px` icon rule and unchanged title typography.

### Model and scope

- Reused `BC-PR-012` and `C12_projection_bilingual_ui`; no new UI behavior or owner was introduced.
- The existing OpenSpec bounded brand-sizing exception already authorizes this implementation parameter, so no new planning artifact was required.
- Broader C12/hierarchy and installed-package evidence remains with its existing owner.

## matters-balance-brand-search-spacing - Balance the brand and search spacing

- Project: matters
- Trigger reason: the user requested equal whitespace above and below the title, then asked to shorten the title-to-search distance slightly
- Status: completed
- Skill decision: existing-model preflight + UI Flow Structure + DevelopmentProcessFlow
- Claim boundary: focused sidebar brand spacing, live geometry, and wheel projection only

### Evidence

- Sidebar top padding changed from `24px` to `20px`.
- Brand-to-search spacing changed from `32px` to `20px`.
- Live 8766 geometry measured both gaps at exactly `20px`, with no overlap.
- The transparent icon remains `48×48px`; the `Matters` title remains `700 26px/28px`.
- `16` focused tests, strict OpenSpec validation, diff checks, and wheel inspection passed.

### Model and scope

- Reused `BC-PR-012` and `C12_projection_bilingual_ui`; no new UI behavior or owner was introduced.
- The existing bounded branding exception covers this presentation-only parameter, so OpenSpec routing was `skip_with_reason`.
- Broader C12/hierarchy and installed-package evidence remains with its existing owner.


## flowguard-project-upgrade - FlowGuard project upgrade record update

- Project: matters
- Trigger reason: target project requires current semantic adoption and version records
- Status: completed
- Skill decision: used_flowguard
- Started: 2026-07-19T20:19:01+00:00
- Ended: 2026-07-19T20:19:01+00:00
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
## matters-white-dot-icon-only - Replace the three colored markers with white

- Project: matters
- Trigger reason: the user found the red-yellow-blue markers visually busy and explicitly required an icon-only replacement without changing the later UI
- Status: completed
- Skill decision: Image generation + existing-model preflight + UI Flow Structure + DevelopmentProcessFlow + Browser
- Claim boundary: white-dot PNG/ICO replacement, unchanged UI identities, focused tests, wheel contents, and active 8766 rendering only

### Evidence

- The three inner markers are now white; the stacked red, cream, and charcoal cards and all three white lines remain unchanged.
- Decoded pixel comparison found `0` changed pixels outside the three bounded marker regions and an exactly identical alpha channel.
- `ui/index.html`, `ui/app.js`, and `ui/styles.css` retained their frozen pre-edit SHA256 identities.
- The PNG remains `1254×1254` RGBA with four transparent corners.
- The desktop ICO contains `16`, `24`, `32`, `48`, `64`, `128`, and `256px` entries.
- `16` focused tests and strict OpenSpec validation passed.
- The `0.3.0` wheel contains the exact current PNG and ICO plus unchanged UI-file hashes.
- The active `127.0.0.1:8766` service serves the exact source asset hashes, and browser inspection shows the `48px` white-dot icon without overlap or console errors.

### Model and scope

- Reused `BC-PR-012` and `C12_projection_bilingual_ui`; no new behavior, interaction, visibility, content, or geometry owner was introduced.
- OpenSpec routing was `skip_with_reason` because this is a color-only replacement within the existing bounded branding exception.
- No UI layout, typography, spacing, navigation, card, or detail source was edited.
- Broader hierarchy, machine-wide installation, Git, tag, and release evidence remain outside this focused claim.

## matters-versioned-source-depth-miss - Repair false stale Matter depth

- Project: matters
- Trigger reason: the real private run classified all 44 canonical Matters as stale after the aggregate Matter-depth owner was added
- Status: focused implementation verified; private rebase and final frozen owner remain pending
- Skill decision: existing-model preflight + model-miss review + development process flow
- Claim boundary: strict source revision parsing, exact-version evidence binding, explicit owner terminal semantics, focused tests, and M0 hazard coverage only

### Finding and repair

- The Matter admission contract stores `source:<id>:vN`, while the depth owner incorrectly used that whole reference as the `source_version` object id.
- The false empty lookup made current evidence anchors appear missing and turned every Matter stale.
- The owner now strictly parses the versioned reference, reads the current base source, records a real source-version change separately, and validates each EvidenceAnchor against the exact admitted version.
- `not_applicable` is terminal only for the original-owner dispatch lane; occurrence-only processing stages still cannot license Matter sufficiency.
- Malformed or missing source revision references fail visibly instead of silently producing a green depth result.

### Evidence

- `42` focused semantic-depth, analysis-operation, and source-workflow tests passed.
- Added M0 hazard `H-M0-048-versioned-source-ref-false-stale`.
- Private database rebase, complete M0/C1-C12 replay, ModelMesh, Alignment, TestMesh, and final release evidence remain separate required owners.

### Correction lesson

- The first whole-image generative edit made the transparent exterior opaque and re-rendered nearly every pixel.
- The accepted result keeps the approved transparent source as the sole base and admits generated content only inside the three marker regions.

## matters-research-import-currentness-miss - Preserve ResearchGuard identity at import

- Project: matters
- Trigger reason: live capability inspection showed ResearchGuard current while all supplemental information remained pending
- Status: focused implementation verified; final ModelMesh/TestMesh/DPF remain pending
- Skill decision: existing-model preflight + model-miss review + development process flow
- Claim boundary: the durable result-import handoff, original-owner dispatch, focused tests, and A1 hazard coverage only

### Finding and repair

- Research work packages correctly required the single current external ResearchGuard provider.
- The durable import path reconstructed a runner but failed to pass the frozen ResearchGuard currentness identity into A1 validation.
- A valid real result was therefore rejected as `researchguard_currentness_missing` before C12 could publish supplemental information.
- The import boundary now carries the current provider identity into the same validation path used by direct execution; legacy individual Guard providers and direct API fallbacks remain rejected.

### Evidence and remaining boundary

- A real current-provider regression now queues one research package, imports one bilingual supplemental finding, and verifies original-owner auto-application.
- Added A1 hazard `H-A1-005-current-import-loses-researchguard-identity`.
- External research quality, current web evidence, complete private supplemental coverage, final ModelMesh/TestMesh/DPF, installation, and release evidence remain separate owners.
