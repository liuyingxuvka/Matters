"""Load and validate the immutable app-local consumer Skill Pack."""

from __future__ import annotations

from pathlib import Path
import re

from matters.skills.manifest import (
    BundleManifest,
    InstallationPolicy,
    ProjectionFile,
    SkillManifest,
    SkillOrigin,
    SkillProjection,
    projection_content_hash,
)
from matters._version import VERSION


REQUIRED_SKILL_IDS = (
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
_CAPABILITIES = {
    "matters-source-governance": (
        "source_scope_governance",
        "scope_preview",
        "tracking_policy_intent",
    ),
    "matters-inventory-reconciliation": (
        "source_inventory",
        "inventory_reconciliation",
        "change_set",
    ),
    "matters-freshness-maintenance": (
        "dependency_freshness",
        "affected_recompute_request",
    ),
    "matters-model-depth-maintenance": (
        "semantic_depth_assessment",
        "missing_work_request",
    ),
    "matters-human-correction": (
        "optional_post_publication_correction",
        "correction_recompute_status",
    ),
    "matters-model-miss-review": ("model_miss", "development_handoff"),
    "matters-skill-runtime": (
        "skill_inventory",
        "active_skill_resolution",
        "managed_projection_sync",
    ),
    "matters-research-orchestration": (
        "research_operation",
        "researchguard_gate",
    ),
    "matters-semantic-understanding": (
        "semantic_understanding",
        "typed_bilingual_findings",
        "owner_dispatch_advisory",
    ),
    "matters-autonomous-maintenance": (
        "coverage_ledger_coordination",
        "next_stage_dispatch",
        "bounded_retry",
    ),
    "matters-card-visual-curation": (
        "eligible_visual_curation",
        "visual_selection_advisory",
        "visual_fallback_disposition",
    ),
}
_PERMISSIONS = {
    skill_id: (
        "matterservice_only",
        "declared_scope_only",
        "no_direct_canonical_writes",
    )
    for skill_id in REQUIRED_SKILL_IDS
}
_DISCLOSURE_POLICIES = {
    "matters-source-governance": "private_scope_metadata_runtime_only",
    "matters-inventory-reconciliation": "private_inventory_metadata_runtime_only",
    "matters-freshness-maintenance": "opaque_dependency_identities_only",
    "matters-model-depth-maintenance": "opaque_coverage_status_only",
    "matters-human-correction": "current_projection_and_on_demand_evidence_only",
    "matters-model-miss-review": "opaque_private_evidence_handle_only",
    "matters-skill-runtime": "skill_identity_metadata_only",
    "matters-research-orchestration": "minimized_allowlisted_evidence_runtime_only",
    "matters-semantic-understanding": "bounded_private_evidence_runtime_only",
    "matters-autonomous-maintenance": "opaque_coverage_ledger_runtime_only",
    "matters-card-visual-curation": "allowlisted_asset_handles_and_thumbnails_only",
}
_REQUIRED_CONSUMER_FILES = frozenset(
    {
        "SKILL.md",
        "agents/openai.yaml",
        "references/service-contract.md",
        "scripts/invoke.py",
    }
)
_ALLOWED_TOP_LEVEL = frozenset(
    {"SKILL.md", "agents", "references", "scripts", "assets"}
)
_AUTHOR_CONTROL_PATH_PARTS = frozenset(
    {
        ".skillguard",
        "contract-source.json",
        "compiled-contract.json",
        "check-manifest.json",
        "global_registry.json",
        "portfolio.json",
        "receipts",
        "run-store",
        "router-state",
    }
)
_AUTHOR_CONTROL_TEXT_MARKERS = (
    "skillguard_supervise.py",
    "skillguard_test_mesh.py",
    "skillguard_consumer_install.py",
    "maintenance_unit_id",
    "owner_evidence_root",
    "run_state_root",
)
_SEMANTIC_MARKERS = {
    "matters-source-governance": (
        "authorization_missing",
        "hard_excluded",
        "tracking_policy_revision",
    ),
    "matters-inventory-reconciliation": (
        "inventory_snapshot",
        "change_set",
        "occurrence_dispositions",
    ),
    "matters-freshness-maintenance": (
        "dependency_fingerprint",
        "affected_stage_ids",
        "card_density_preference",
    ),
    "matters-model-depth-maintenance": (
        "original_owner_terminal",
        "representative_visual_terminal",
        "ui_reachability_terminal",
    ),
    "matters-human-correction": (
        "optional_after_publication",
        "correction_revision",
        "recompute_status",
    ),
    "matters-model-miss-review": (
        "expected_behavior",
        "observed_behavior",
        "development_work_item",
    ),
    "matters-skill-runtime": (
        "exactly eleven",
        "same_version_different_hash",
        "bundled_internal",
    ),
    "matters-research-orchestration": (
        "researchguard_pending_integration",
        "legacy_parallel_guard_binding_rejected",
        "original_owner_targets",
    ),
    "matters-semantic-understanding": (
        "input_dispositions",
        "untrusted_evidence",
        "automatic_owner_dispatch",
    ),
    "matters-autonomous-maintenance": (
        "object_coverage_ledger",
        "next_stage",
        "hard_block",
    ),
    "matters-card-visual-curation": (
        "eligible_asset_ids",
        "selected_asset_id",
        "deterministic_fallback_policy_id",
    ),
}
_FRONTMATTER_NAME = re.compile(r"(?m)^name:\s*([a-z0-9-]+)\s*$")


def _matters_version() -> str:
    return VERSION


def _files(skill_root: Path) -> tuple[ProjectionFile, ...]:
    rows = []
    for path in sorted(skill_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(skill_root).as_posix()
        if (
            "__pycache__" in path.parts
            or path.suffix in {".pyc", ".pyo", ".log"}
        ):
            continue
        rows.append(ProjectionFile(relative, path.read_bytes()))
    return tuple(rows)


def load_projections(root: Path | None = None) -> tuple[SkillProjection, ...]:
    pack_root = (root or Path(__file__).resolve().parent).resolve()
    rows = []
    for skill_id in REQUIRED_SKILL_IDS:
        skill_root = pack_root / skill_id
        files = _files(skill_root)
        manifest = SkillManifest(
            skill_id=skill_id,
            version=_matters_version(),
            skill_schema_compatibility=">=1,<2",
            matters_compatibility=">=0.2,<0.3",
            origin=SkillOrigin.BUNDLED,
            content_hash=projection_content_hash(files),
            required=True,
            installation_policy=InstallationPolicy.BUNDLED_INTERNAL,
            capabilities=_CAPABILITIES[skill_id],
            permissions=_PERMISSIONS[skill_id],
            data_disclosure_policy=_DISCLOSURE_POLICIES[skill_id],
            dependencies=(),
            runtime_identity=f"matters-runtime:{_matters_version()}",
            validator_identity="matters-bundled-skill-validator:v2",
        )
        rows.append(SkillProjection(manifest, files))
    return tuple(rows)


def build_bundle(root: Path | None = None) -> BundleManifest:
    projections = load_projections(root)
    bundle = BundleManifest.build(
        pack_id="matters-consumer-skill-pack",
        pack_version=_matters_version(),
        matters_compatibility=">=0.2,<0.3",
        skill_schema_version="1.0",
        skills=(item.manifest for item in projections),
    )
    bundle.validate_required_inventory(REQUIRED_SKILL_IDS)
    return bundle


def validate_bundle(root: Path | None = None) -> tuple[str, ...]:
    pack_root = (root or Path(__file__).resolve().parent).resolve()
    findings: list[str] = []
    discovered_skill_ids = {
        path.name
        for path in pack_root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    }
    for skill_id in sorted(discovered_skill_ids - set(REQUIRED_SKILL_IDS)):
        findings.append(f"{skill_id}:unexpected_skill")
    for skill_id in REQUIRED_SKILL_IDS:
        skill_root = pack_root / skill_id
        if not skill_root.is_dir():
            findings.append(f"{skill_id}:skill_root_missing")
            continue
        raw_paths = tuple(
            path
            for path in sorted(skill_root.rglob("*"))
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix not in {".pyc", ".pyo", ".log"}
        )
        relative_paths = {
            path.relative_to(skill_root).as_posix() for path in raw_paths
        }
        for missing in sorted(_REQUIRED_CONSUMER_FILES - relative_paths):
            findings.append(f"{skill_id}:consumer_file_missing:{missing}")
        for relative in sorted(relative_paths):
            parts = tuple(part.casefold() for part in Path(relative).parts)
            residual = next(
                (
                    part
                    for part in parts
                    if part in _AUTHOR_CONTROL_PATH_PARTS
                ),
                "",
            )
            if residual:
                findings.append(
                    f"{skill_id}:author_control_residual:{relative}"
                )
                continue
            top_level = relative.split("/", 1)[0]
            if top_level not in _ALLOWED_TOP_LEVEL:
                findings.append(
                    f"{skill_id}:consumer_top_level_forbidden:{relative}"
                )
    if findings:
        return tuple(findings)

    try:
        projections = load_projections(root)
    except (OSError, UnicodeError, ValueError) as exc:
        return (f"bundle:projection_invalid:{type(exc).__name__}:{exc}",)

    capability_owners: dict[str, str] = {}
    for projection in projections:
        skill_id = projection.manifest.skill_id
        for item in projection.files:
            if Path(item.path).suffix.casefold() not in {
                ".md",
                ".py",
                ".yaml",
                ".yml",
                ".json",
                ".txt",
            }:
                continue
            consumer_text = item.content.decode(
                "utf-8",
                errors="strict",
            ).casefold()
            for marker in _AUTHOR_CONTROL_TEXT_MARKERS:
                if marker.casefold() in consumer_text:
                    findings.append(
                        f"{skill_id}:author_control_instruction:"
                        f"{item.path}:{marker}"
                    )
        skill_md = next(
            (item for item in projection.files if item.path == "SKILL.md"),
            None,
        )
        if skill_md is None:
            findings.append(f"{skill_id}:skill_md_missing")
            continue
        text = skill_md.content.decode("utf-8", errors="strict")
        match = _FRONTMATTER_NAME.search(text)
        if match is None or match.group(1) != skill_id:
            findings.append(
                f"{skill_id}:frontmatter_identity_mismatch"
            )
        if "MatterService" not in text:
            findings.append(
                f"{skill_id}:shared_service_boundary_missing"
            )
        if any(".skillguard" in item.path.casefold() for item in projection.files):
            findings.append(
                f"{skill_id}:author_control_residual"
            )
        prompt_text = next(
            item.content.decode("utf-8", errors="strict")
            for item in projection.files
            if item.path == "agents/openai.yaml"
        )
        if f"${skill_id}" not in prompt_text or "MatterService" not in prompt_text:
            findings.append(f"{skill_id}:default_prompt_boundary_missing")
        contract_text = next(
            item.content.decode("utf-8", errors="strict")
            for item in projection.files
            if item.path == "references/service-contract.md"
        )
        lowered_contract = contract_text.casefold()
        for marker in _SEMANTIC_MARKERS[skill_id]:
            if marker.casefold() not in lowered_contract:
                findings.append(f"{skill_id}:semantic_marker_missing:{marker}")
        script_text = next(
            item.content.decode("utf-8", errors="strict")
            for item in projection.files
            if item.path == "scripts/invoke.py"
        )
        if (
            "from matters.cli.main import main" not in script_text
            or "raise SystemExit(main())" not in script_text
        ):
            findings.append(f"{skill_id}:canonical_cli_delegate_missing")
        manifest = projection.manifest
        if manifest.content_hash != projection_content_hash(projection.files):
            findings.append(f"{skill_id}:content_hash_mismatch")
        if manifest.validator_identity != "matters-bundled-skill-validator:v2":
            findings.append(f"{skill_id}:validator_identity_mismatch")
        if manifest.installation_policy != InstallationPolicy.BUNDLED_INTERNAL:
            findings.append(f"{skill_id}:installation_policy_mismatch")
        for capability in manifest.capabilities:
            prior_owner = capability_owners.get(capability)
            if prior_owner is not None:
                findings.append(
                    f"{skill_id}:capability_owner_duplicate:{capability}:{prior_owner}"
                )
            else:
                capability_owners[capability] = skill_id
    try:
        build_bundle(root)
    except ValueError as exc:
        findings.append(f"bundle:manifest_invalid:{exc}")
    return tuple(findings)


__all__ = [
    "REQUIRED_SKILL_IDS",
    "build_bundle",
    "load_projections",
    "validate_bundle",
]
