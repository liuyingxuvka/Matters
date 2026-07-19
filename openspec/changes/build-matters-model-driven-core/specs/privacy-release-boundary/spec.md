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

#### Scenario: Representative visual derivative is created
- **WHEN** the application generates a thumbnail, document preview, OCR overlay, representative visual, or desktop screenshot from real private content
- **THEN** the derivative and every reconstructable identity SHALL remain under `MATTERS_HOME` or an explicitly private evaluation root and SHALL NOT enter Git, package data, public UI fixtures, release receipts, or public design captures

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
inventory, toolchain, dependencies, verifier, package, installed projection,
and asset list before final release verification.

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

### Requirement: Source, package, skill-runtime, installation, and Git identities agree
The release gate SHALL keep source checkout, built package, installed package,
immutable bundled Skill Pack, machine-installed skill inventory, resolved
active skill view, ResearchGuard provider, packaged desktop assets, desktop
installation, and local Git identities distinct
and SHALL prove their declared version, compatibility, content, and
synchronization. A Matters-managed installed projection SHALL be represented as
a managed ownership subtype inside the machine-installed layer, not as a
fourth skill-runtime layer.

#### Scenario: Installed package differs from frozen source
- **WHEN** the installed package, bundled pack, active skill view, or managed
  skill fingerprint differs from its frozen declared projection
- **THEN** release confidence SHALL remain blocked until the installation is synchronized and rechecked

#### Scenario: ResearchGuard currentness is absent
- **WHEN** no portable terminal-success ResearchGuard currentness receipt binds the frozen source commit, distribution, command, top-level skill, member projections, manifest, residual state, compatibility, native validation, and installed identity
- **THEN** Matters MAY preserve a blocked local candidate but SHALL NOT claim final v0.2 complete-release

### Requirement: Package verification is private-source independent
The v0.2 package, clean-clone tests, install checks, and release candidate SHALL
start in non-writing capability mode without Jira, Rovo, Gmail, cloud, or real
private source access. The user's private first run SHALL remain a separate
acceptance domain and SHALL NOT be copied into clean-clone evidence.

#### Scenario: Jira and Rovo are unavailable
- **WHEN** no Atlassian account, token, host, plugin, Rovo installation, Gmail connection, cloud hydration, or private root exists
- **THEN** package health, synthetic tests, and capability reporting SHALL remain installable and runnable without pretending the private first run occurred

### Requirement: Remote publication requires a separate frozen decision
Local package installation, local Git commit, and local tag SHALL NOT imply
authorization to create or push a public remote, choose a license, or publish a
GitHub release.

#### Scenario: Local release candidate is green
- **WHEN** the frozen local package, install, model, test, privacy, and Git identities agree
- **THEN** remote publication SHALL remain blocked until a separate explicit publication decision supplies the remote, license, and public inventory
