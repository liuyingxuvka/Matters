## ADDED Requirements

### Requirement: Private data remains outside public Git
The system SHALL store live private source content, metadata, paths, private
content identities, excerpts, derived understanding, embeddings, OCR, image
analysis, screenshots, logs, runtime receipts, user models, and private
evaluation material in physical roots outside the public repository.

#### Scenario: Runtime starts without a private root
- **WHEN** no valid external `MATTERS_HOME` is configured
- **THEN** private provider activation SHALL fail visibly without creating a data root inside Git

#### Scenario: Runtime is started from a clean clone
- **WHEN** the package starts without a configured external private root
- **THEN** it SHALL remain in a non-writing capability state and SHALL NOT fall back to a repository, current-directory, or implicit temporary data root

#### Scenario: Configured private root is inside Git
- **WHEN** `MATTERS_HOME` or `MATTERS_EVAL_VAULT` resolves inside a Git worktree, package staging root, or public build context
- **THEN** private activation SHALL fail visibly before source discovery or content writes

#### Scenario: Windows installed runtime selects its default private root
- **WHEN** the desktop installer configures `MATTERS_HOME` on a Windows machine whose Python runtime may apply LocalAppData virtualization
- **THEN** the installer SHALL select one non-virtualized directory directly under the user profile and every database, manifest, receipt, managed skill, blob, and desktop profile SHALL resolve beneath that same physical root

### Requirement: Public evidence is synthetic
The public repository SHALL contain only fully synthetic fixtures, receipts,
screenshots, and examples or non-reconstructable aggregate dispositions whose
public fields are explicitly allowlisted.

#### Scenario: Renamed real material is proposed
- **WHEN** a candidate fixture is derived from real content by renaming identifiers
- **THEN** the publication gate SHALL reject it as private material

#### Scenario: Derived private representation is proposed
- **WHEN** a candidate public file contains a real-source path, content hash, excerpt, summary, embedding, OCR text, image label/region, screenshot, user model, or runtime receipt
- **THEN** the publication gate SHALL reject it even if direct identifiers were removed

### Requirement: Real first-run evidence remains private
Raw or derived local-file, document, spreadsheet, image/photo, Gmail,
attachment, `cloud_placeholder`, audio/video/archive metadata, and other
user-content material SHALL remain under the external private runtime or
evaluation roots.

#### Scenario: A private first-run result is summarized publicly
- **WHEN** the repository records completion of a private source-type canary or first-run stage
- **THEN** it SHALL contain only fully synthetic case details or allowlisted aggregate outcomes, bounded failure classes, and an opaque private evidence handle that cannot reconstruct source or derived content

#### Scenario: Private material appears in a candidate file
- **WHEN** a tracked, staged, packaged, documented, logged, screenshot, model, receipt, cache, or build file contains private source or derived material
- **THEN** the publication gate SHALL block and identify the contaminated public artifact

#### Scenario: Private visual derivative is created
- **WHEN** the application generates a thumbnail, document preview, OCR overlay, Matter generation brief, generated Matter hero, or desktop screenshot from real private content or derived understanding
- **THEN** the derivative and every reconstructable identity SHALL remain under `MATTERS_HOME` or an explicitly private evaluation root and SHALL NOT enter Git, package data, public UI fixtures, release receipts, or public design captures

#### Scenario: A Matter hero is sent for generation
- **WHEN** the current private execution profile invokes a declared image-generation capability
- **THEN** the package SHALL contain only the minimized Matter theme permitted by the current policy, exclude source excerpts, paths, names, addresses, private identifiers, logos, literal text, and identifiable real people by default, and record the provider/tool disclosure disposition privately

### Requirement: Discovery and analysis cannot export private data implicitly
Filesystem, Gmail, document, image, AI, Guard, UI, logging, telemetry, and
error paths SHALL NOT copy private material to Git, public build roots, public
remote services, or undeclared model/tool providers.

#### Scenario: Agent work package uses an external model
- **WHEN** an authorized analysis operation requires a declared external model provider
- **THEN** the system SHALL send only the minimized, scope-bound private payload permitted by the operation and SHALL record the provider and disclosure disposition privately

#### Scenario: Error occurs while processing a private path
- **WHEN** discovery or extraction fails for a private source
- **THEN** public logs and receipts SHALL use an opaque case handle and bounded failure class rather than the private path, filename, content, or identifier

### Requirement: Publication uses a frozen clean candidate
The system SHALL freeze commit, version, public inventory, model/test
inventory, toolchain, dependencies, verifier, candidate packages, isolated
anonymous-install evidence, and asset list before publication. The user's
active installed projection SHALL be synchronized and verified from the
published assets after publication and SHALL NOT block an otherwise current
generic candidate.

#### Scenario: Candidate file changes after a scan
- **WHEN** any candidate file changes after privacy, build, or test evidence is created
- **THEN** all downstream evidence that consumed the older candidate SHALL become stale

### Requirement: Release is independently rechecked
The system SHALL build from a clean clone, use fake providers without private
roots, scan tracked files, history, staging, and final packages, and recheck the
published or locally tagged source as an anonymous consumer.

#### Scenario: Final source package is downloaded
- **WHEN** a release candidate has been published
- **THEN** an anonymous download SHALL be unpacked, scanned, and started without access to private data

### Requirement: Required public source cannot be ignored
The public-boundary gate SHALL compare the required-public inventory with Git
ignore, tracked, package, and clean-clone inventories.

#### Scenario: Required blob-store source matches a broad ignore pattern
- **WHEN** a required product source file is excluded by an ignore or packaging rule
- **THEN** the gate SHALL fail with the exact required file and rule before Git or package freeze

### Requirement: Public evidence is portable
Public receipts and evidence SHALL use repository-relative paths and
machine-independent tool identities and SHALL exclude caches, bytecode, logs,
private roots, user profiles, hostnames, and local interpreter paths.

#### Scenario: JSON contains an escaped Windows user path
- **WHEN** a public candidate contains a decoded or escaped absolute user-profile path
- **THEN** the public-boundary gate SHALL fail even when the raw byte sequence differs from the normalized path

#### Scenario: Evidence fingerprint includes bytecode
- **WHEN** a public evidence fingerprint inventory contains ignored cache or `.pyc` input
- **THEN** the evidence SHALL be rejected as non-portable and regenerated from the declared source inventory

### Requirement: Source, candidate, post-release installation, and Git identities remain distinct
The publication gate SHALL keep source checkout, built package, isolated
anonymous-install environment, immutable bundled Skill Pack, candidate active
skill view, ResearchGuard provider, packaged desktop assets, and local Git
identities distinct and SHALL prove their declared version, compatibility,
content, and synchronization. After publication, the consumer-install gate
SHALL separately bind the downloaded GitHub assets, installed package,
machine-installed skill inventory, resolved active skill view, and desktop
installation to the published tag and checksums. A Matters-managed installed projection SHALL be represented as
a managed ownership subtype inside the machine-installed layer, not as a
fourth skill-runtime layer.

#### Scenario: Active local installation is older than the publishable candidate
- **WHEN** the frozen candidate and isolated anonymous-install evidence are current but the user's active package or desktop is an older released version
- **THEN** publication SHALL remain allowed and the local difference SHALL become a required post-publication consumer-synchronization action

#### Scenario: Published asset fails consumer synchronization
- **WHEN** a downloaded published package, bundled pack, active skill view, managed skill fingerprint, or desktop installation differs from the published tag or checksums
- **THEN** consumer-install confidence SHALL remain blocked until that installation is repaired and rechecked, without rewriting the already published release identity

#### Scenario: ResearchGuard currentness is absent
- **WHEN** no portable terminal-success ResearchGuard currentness receipt binds the frozen source commit, distribution, command, top-level skill, member projections, manifest, residual state, compatibility, native validation, and installed identity
- **THEN** Matters MAY preserve a blocked local candidate but SHALL NOT claim final v0.2 complete-release

### Requirement: Package verification is private-source independent
The generic package, clean-clone tests, install checks, and release candidate SHALL
start in non-writing capability mode without Jira, Rovo, Gmail, cloud, or real
private source access. The user's private first run SHALL remain a separate
acceptance domain and SHALL NOT be copied into clean-clone evidence.

#### Scenario: Jira and Rovo are unavailable
- **WHEN** no Atlassian account, token, host, plugin, Rovo installation, Gmail connection, cloud hydration, or private root exists
- **THEN** package health, synthetic tests, and capability reporting SHALL remain installable and runnable without pretending the private first run occurred

### Requirement: Release artifacts teach the installing AI the complete setup
The source distribution, wheel public plugin, and Windows desktop archive SHALL
ship one current AI-readable installation contract that explains package and
MCP verification, external private-root setup, internal-versus-external skill
boundaries, separate source authorization, exactly one AI-managed daily
schedule, initial bounded maintenance, honest empty desktop behavior, and
visible setup blockers. The public README SHALL summarize and link that same
contract.

#### Scenario: AI installs from the Python wheel
- **WHEN** a compatible AI installs the frozen wheel and public Matters plugin
- **THEN** it SHALL discover the installation contract beside the public skill and SHALL be able to execute setup without inventing a second workflow or asking the user to create the schedule manually

#### Scenario: AI installs from the Windows desktop archive
- **WHEN** a compatible AI unpacks the frozen Windows release
- **THEN** the archive root SHALL contain `README.md` and `AI-SETUP.md`, and neither document SHALL contain private paths, source content, local receipts, or machine-specific provenance

### Requirement: A generic GitHub release may precede the private first run
Matters MAY publish a generic GitHub release before the user's private Gmail,
local-file, and Codex first run is complete only when every generic product
capability promised by the release—including hierarchy, people, timeline,
summary, inference/correction, bilingual object browser, desktop shell, MCP,
and bundled-skill behavior—has current model, test, privacy, candidate-package,
isolated anonymous-install, and desktop-archive evidence on one frozen candidate. The release SHALL describe the
private first run as separate and not yet completed, and SHALL NOT use private
coverage progress as generic product proof.

#### Scenario: Generic v0.3.1 is frozen while the private first run remains pending
- **WHEN** the generic candidate, anonymous install, public inventory, privacy scan, model owners, TestMesh, desktop shell, MCP, and bundled skills are current, but private Gmail/local/Codex modeling remains incomplete
- **THEN** the system MAY publish v0.3.1 without private artifacts or a private-completion claim, SHALL synchronize the user's active installation from the published assets before continuing the private first run against the released contract, and MAY aggregate later generic defects into a separately verified patch release

#### Scenario: A private first run exposes a generic product defect
- **WHEN** real private operation reveals a reusable implementation defect after v0.3.0
- **THEN** the defect SHALL be reproduced with public-safe synthetic evidence, fixed and verified as generic behavior, and MAY be published in a later patch release without exporting the private triggering content

### Requirement: Remote publication requires a separate frozen decision
Candidate-package verification, local Git commit, and local tag SHALL NOT imply
authorization to create or push a public remote, choose a license, or publish a
GitHub release.

#### Scenario: Local release candidate is green
- **WHEN** the frozen candidate package, isolated anonymous-install, model, test, privacy, and Git identities agree
- **THEN** remote publication SHALL remain blocked until a separate explicit publication decision supplies the remote, license, and public inventory

#### Scenario: Publication intent is explicit but remote identity is not frozen
- **WHEN** the user authorizes GitHub publication but the exact repository, visibility, license disposition, or public inventory is not current
- **THEN** the generic release work SHALL continue through the local frozen-candidate gate, but push, tag publication, and GitHub Release creation SHALL remain blocked until those publication identities are explicit and mutually consistent

#### Scenario: Current v0.3.1 public GitHub identity is frozen
- **WHEN** the authorized owner selects `liuyingxuvka/Matters` as a public repository, selects the MIT License and approved generic public-safe inventory, preserves historical tag `v0.3.0`, and requests source, corrective tag `v0.3.1`, and GitHub Release publication
- **THEN** the publication owner MAY create and push that public remote only after the frozen candidate passes its generic model, test, UI, privacy, package, anonymous-install, desktop, MCP, bundled-skill, README, and public-rendering gates
- **AND** the MIT software license SHALL NOT authorize private-data upload or a private-first-run completion claim
