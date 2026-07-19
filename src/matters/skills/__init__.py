"""Auxiliary bundled consumer-skill runtime.

The package resolves and maintains executable skill identities only.  It owns
no canonical Matter, evidence, lifecycle, outcome, or presentation state.
"""

from .inventory import InstalledSkill, MachineSkillInventory
from .discovery import (
    MachineSkillDiscovery,
    default_codex_skill_root,
    discover_machine_skills,
)
from .manifest import (
    BundleManifest,
    InstallationPolicy,
    ProjectionFile,
    SkillDependency,
    SkillIdentity,
    SkillManifest,
    SkillOrigin,
    SkillProjection,
    projection_content_hash,
    projection_from_mapping,
)
from .projection import (
    FilesystemManagedProjectionStore,
    ManagedProjectionError,
    ManagedProjectionReceipt,
    ManagedProjectionSynchronizer,
    UnmanagedProjectionError,
    VerificationResult,
    matters_managed_projection,
)
from .research import (
    LEGACY_RESEARCH_PROVIDER_IDS,
    ResearchGuardGate,
    ResearchGuardStatus,
    ResearchProviderDecision,
    resolve_research_provider,
)
from .resolver import (
    ActiveSkillDecision,
    ActiveSkillResolver,
    ActiveSkillView,
    CandidateDisposition,
    CandidateValidation,
    DependencyIdentity,
    ResolutionEnvironment,
    ValidationStatus,
    active_view_input_fingerprint,
)


REQUIRED_INITIAL_SKILL_IDS = (
    "matters-source-governance",
    "matters-inventory-reconciliation",
    "matters-freshness-maintenance",
    "matters-model-depth-maintenance",
    "matters-human-correction",
    "matters-model-miss-review",
    "matters-skill-runtime",
    "matters-research-orchestration",
    "matters-semantic-understanding",
    "matters-autonomous-maintenance",
    "matters-card-visual-curation",
)


__all__ = [
    "ActiveSkillDecision",
    "ActiveSkillResolver",
    "ActiveSkillView",
    "BundleManifest",
    "CandidateDisposition",
    "CandidateValidation",
    "DependencyIdentity",
    "FilesystemManagedProjectionStore",
    "InstallationPolicy",
    "InstalledSkill",
    "LEGACY_RESEARCH_PROVIDER_IDS",
    "MachineSkillInventory",
    "MachineSkillDiscovery",
    "ManagedProjectionError",
    "ManagedProjectionReceipt",
    "ManagedProjectionSynchronizer",
    "ProjectionFile",
    "REQUIRED_INITIAL_SKILL_IDS",
    "ResearchGuardGate",
    "ResearchGuardStatus",
    "ResearchProviderDecision",
    "ResolutionEnvironment",
    "SkillDependency",
    "SkillIdentity",
    "SkillManifest",
    "SkillOrigin",
    "SkillProjection",
    "UnmanagedProjectionError",
    "ValidationStatus",
    "VerificationResult",
    "active_view_input_fingerprint",
    "default_codex_skill_root",
    "discover_machine_skills",
    "projection_content_hash",
    "projection_from_mapping",
    "matters_managed_projection",
    "resolve_research_provider",
]
