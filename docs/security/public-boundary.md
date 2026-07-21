# Public, private, and evaluation boundary

Matters uses three physically separate security domains:

```text
matters/              generic public-safe source Git repository
MATTERS_HOME/         private live user workspace outside the repository
MATTERS_EVAL_VAULT/   private frozen evaluation workspace outside the repository
```

The source repository may consume only synthetic fixtures during normal
tests, even while repository access is private. Here, `public-safe` describes
the data boundary; it does not imply public GitHub visibility or an
open-source license.
The private workspace may read explicitly authorized real sources but must
never copy them automatically into Git or the evaluation vault. Transfer from
the private workspace to the vault requires explicit user selection. Transfer
from the vault to a public export candidate additionally requires
deidentification, aggregation where relevant, human review, and the complete
public-boundary gate.

## Initial public allowlist

- Product source, schemas, and migrations
- Generic provider contracts and fake providers
- OpenSpec and FlowGuard model sources
- Fully synthetic known-good and known-bad fixtures
- i18n resources and synthetic UI screenshots
- Tests, CI, documentation, threat model, license, SBOM, and security policy

The allowlist is an admission policy, not a claim that those files already
exist or have passed publication review.

## Authoritative public inventory

`docs/security/required-public-inventory.json` is the source authority for
which physical workspace files must remain public. Its singleton and tree
selectors are evaluated from the filesystem so an accidentally ignored source
file cannot disappear from the check. Cache, bytecode, log, and other declared
runtime exclusions are removed before the public-source fingerprint is built.

`scripts/check_public_boundary.py` compares that authority with five separate
views: the physical workspace, Git-ignored files, the committed tree, an
explicit clean clone, and supplied package artifacts. Before the first commit,
the committed and clean-clone views report `not_available`; before packaging,
the package view reports `not_run`. Those states are visible gaps, not passes.
Package checks fail on both missing required projections and unexpected
runtime or data payload, so a deleted source file cannot silently return from
stale build output.
All paths written to the report use `repo://`, `private://`, `clone://`, or
`package://` identifiers rather than machine-local paths.

The scanner decodes JSON and YAML strings and common percent, HTML, Unicode,
and separator escape variants before looking for private roots, user-home
paths, host/interpreter identity, non-synthetic email addresses, structured
opaque Gmail message/thread identifiers, and high-confidence secrets. Public
symlinks and Windows junctions fail closed.

## Private-root dispositions

The public check proves only that the configured symbolic private roots
resolve outside the repository. ACL, encryption, and cloud-sync disposition
remain `user_review_required` until the user or an authorized machine audit
records them. The scanner does not enumerate or read either private root.

## Publication invalidation rule

Any change to a release candidate file invalidates every later privacy scan,
build, test, package, and release receipt that consumed the older candidate.
Release verification starts only after source, toolchain, dependency,
inventory, version, and execution ownership are frozen.
