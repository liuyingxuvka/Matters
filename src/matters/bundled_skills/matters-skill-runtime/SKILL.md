---
name: matters-skill-runtime
description: Inspect and resolve the immutable bundled Skill Pack, machine-installed inventory, singular active view, compatibility, and Matters-managed synchronization. Use when skill availability, version, currentness, collision, or rollback matters.
---

# Matters Skill Runtime

Read `references/service-contract.md`. Expose decisions through MatterService
and never create a second product path.

1. Inventory exactly the eleven bundle-declared ids in the immutable bundled
   layer and machine-installed layer without enumerating unrelated skills.
2. Validate exact manifests, projection content hashes, PEP 440 versions and
   intervals, prerelease policy, dependencies, runtime identity, native
   validator, and ResearchGuard identity when applicable.
3. Resolve exactly one active compatible candidate per required skill.
4. Prefer a valid newer machine copy as a non-mutating overlay.
5. Prefer a newer bundled copy internally when an older external copy is unmanaged, and report update available.
6. Block `same_version_different_hash`, invalid manifests, incompatible
   candidates, prereleases without opt-in, dependency drift, validator drift,
   and author-maintenance residuals.
7. Synchronize only the Matters-managed installed subtype using stage, native
   validation, atomic activation, installed-currentness check, and rollback.

The resolver has exactly three layers: immutable bundled pack,
machine-installed inventory, and resolved active view. Never install a
bundled-only skill globally merely because it is absent, overwrite an
externally managed copy, or treat the managed subtype as a fourth layer.
