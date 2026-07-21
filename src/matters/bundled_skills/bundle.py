"""Load and validate the immutable app-local consumer Skill Pack."""

from __future__ import annotations

from pathlib import Path
import re

from packaging.version import Version

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
    "matters-hero-image-generation",
)
RETIRED_SKILL_IDS = frozenset(
    {
        "matters-card-visual-curation",
        "matters-generated-hero",
    }
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
        "source_annotation",
        "semantic_understanding",
        "model_independent_capability_routing",
        "matter_hierarchy_and_work_items",
        "typed_bilingual_findings",
        "owner_dispatch_advisory",
    ),
    "matters-autonomous-maintenance": (
        "coverage_ledger_coordination",
        "next_stage_dispatch",
        "bounded_retry",
    ),
    "matters-hero-image-generation": (
        "private_minimized_hero_brief",
        "generated_hero_registration",
        "bounded_generation_retry",
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
    "matters-hero-image-generation": "private_minimized_abstract_brief_only",
}
_CONTRACT_PROFILES = {
    "matters-source-governance": {
        "storage_pointer": "applicable_locator_fingerprint_only",
        "source_group": "applicable_scope_context_only",
        "situation_graph": "not_applicable",
        "world_model": "not_applicable",
        "hero": "not_applicable",
        "unattended": "applicable_bounded_service_no_final_verification",
    },
    "matters-inventory-reconciliation": {
        "storage_pointer": "applicable_locator_fingerprint_reconciliation_only",
        "source_group": "applicable_membership_reconciliation_only",
        "situation_graph": "not_applicable",
        "world_model": "not_applicable",
        "hero": "not_applicable",
        "unattended": "applicable_bounded_service_no_final_verification",
    },
    "matters-freshness-maintenance": {
        "storage_pointer": "applicable_dependency_freshness_only",
        "source_group": "applicable_dependency_freshness_only",
        "situation_graph": "applicable_dependency_freshness_only",
        "world_model": "applicable_dependency_freshness_only",
        "hero": "applicable_root_stage_freshness_only",
        "unattended": "applicable_bounded_service_no_final_verification",
    },
    "matters-model-depth-maintenance": {
        "storage_pointer": "applicable_depth_input_only",
        "source_group": "applicable_depth_input_only",
        "situation_graph": "applicable_depth_assessment_only",
        "world_model": "applicable_depth_assessment_only",
        "hero": "applicable_root_terminal_assessment_only",
        "unattended": "applicable_bounded_service_no_final_verification",
    },
    "matters-human-correction": {
        "storage_pointer": "applicable_correction_locator_only",
        "source_group": "applicable_correction_dispatch_only",
        "situation_graph": "applicable_correction_dispatch_only",
        "world_model": "applicable_correction_dispatch_only",
        "hero": "applicable_root_correction_dispatch_only",
        "unattended": "not_applicable_human_initiated_only",
    },
    "matters-model-miss-review": {
        "storage_pointer": "applicable_diagnostic_handoff_only",
        "source_group": "applicable_diagnostic_handoff_only",
        "situation_graph": "applicable_diagnostic_handoff_only",
        "world_model": "applicable_diagnostic_handoff_only",
        "hero": "applicable_root_child_boundary_diagnostic_only",
        "unattended": "not_applicable_no_runtime_repair",
    },
    "matters-skill-runtime": {
        "storage_pointer": "not_applicable_no_user_source_access",
        "source_group": "not_applicable_no_domain_data_access",
        "situation_graph": "not_applicable_no_domain_data_access",
        "world_model": "not_applicable_no_domain_data_access",
        "hero": "not_applicable_resolves_skill_identity_only",
        "unattended": "applicable_managed_sync_only_no_final_verification",
    },
    "matters-research-orchestration": {
        "storage_pointer": "applicable_minimized_pointer_input_only",
        "source_group": "applicable_advisory_context_only",
        "situation_graph": "applicable_advisory_snapshot_input_only",
        "world_model": "applicable_supplemental_research_only_no_truth_write",
        "hero": "not_applicable_research_never_generates_hero",
        "unattended": "applicable_bounded_if_current_no_final_verification",
    },
    "matters-semantic-understanding": {
        "storage_pointer": "applicable_locator_bound_transient_read_only",
        "source_group": "applicable_context_input_only",
        "situation_graph": "applicable_advisory_candidate_output_only",
        "world_model": "applicable_advisory_inference_output_only",
        "hero": "applicable_root_brief_handoff_only_no_generation",
        "unattended": "applicable_bounded_work_package_no_final_verification",
    },
    "matters-autonomous-maintenance": {
        "storage_pointer": "applicable_dispatch_only_no_retention_ownership",
        "source_group": "applicable_dispatch_only_no_domain_ownership",
        "situation_graph": "applicable_dispatch_only_no_domain_ownership",
        "world_model": "applicable_dispatch_only_no_domain_ownership",
        "hero": "applicable_root_dispatch_child_not_applicable",
        "unattended": "applicable_bounded_maintenance_no_final_verification",
    },
    "matters-hero-image-generation": {
        "storage_pointer": "not_applicable_no_source_original_access",
        "source_group": "not_applicable_opaque_gate_only",
        "situation_graph": "not_applicable_no_graph_node_access",
        "world_model": "not_applicable_no_inference_access",
        "hero": "applicable_root_only_generation_child_not_applicable",
        "unattended": "applicable_bounded_generation_no_final_verification",
    },
}
_CONTRACT_PROFILE_ORDER = (
    "storage_pointer",
    "source_group",
    "situation_graph",
    "world_model",
    "hero",
    "unattended",
)
_CONTRACT_LINE = re.compile(
    r"contract applicability:\s*"
    r"storage_pointer=([a-z0-9_]+);\s*"
    r"source_group=([a-z0-9_]+);\s*"
    r"situation_graph=([a-z0-9_]+);\s*"
    r"world_model=([a-z0-9_]+);\s*"
    r"hero=([a-z0-9_]+);\s*"
    r"unattended=([a-z0-9_]+)\.",
    re.IGNORECASE,
)
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
_SHARED_PRODUCT_MARKERS = (
    "deterministic_preprocessor",
    "low_cost_annotator",
    "ambiguity_resolver",
    "matter_modeler",
    "consistency_reviewer",
    "hero_image_generator",
    "maintenance_orchestrator",
    "deterministic_hard_exclusion",
    "source_neighborhood_id",
    "source_group_chain",
    "source_group_labels",
    "source_spatial_context_revision",
    "parent",
    "child",
    "work",
    "item",
    "hierarchy",
    "audit",
    "english",
    "chinese",
    "title",
    "summary",
    "topic",
    "type",
    "named",
    "model",
    "api",
    "key",
    "direct",
    "fallback",
    "absolute",
    "public",
    "generated_hero",
    "research_operation",
    "canonical",
    "state",
)
_RETIRED_CAPABILITY_ROLE_MARKERS = (
    "visual_selector",
    "researcher",
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
        "generated_hero_terminal",
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
        "low_cost_annotator",
        "matter_modeler",
        "requested_output_types",
        "dependency_package_ids",
        "input_dispositions",
        "untrusted_evidence",
        "automatic_owner_dispatch",
        "matter_hierarchy_candidate",
        "work_item_candidate",
        "bounded_summary",
        "material_clue_candidate",
        "generated_hero_candidate",
        "supplemental_information_candidate",
        "direct api fallback",
    ),
    "matters-autonomous-maintenance": (
        "object_coverage_ledger",
        "next_stage",
        "hard_block",
    ),
    "matters-hero-image-generation": (
        "brief_fingerprint",
        "generation_pending_placeholder",
        "generation_blocked_placeholder",
    ),
}
_FRONTMATTER_NAME = re.compile(r"(?m)^name:\s*([a-z0-9-]+)\s*$")
_FRONTMATTER_DESCRIPTION = re.compile(r"(?m)^description:\s*(.+?)\s*$")


def _frontmatter_description_is_yaml_safe(value: str) -> bool:
    match = _FRONTMATTER_DESCRIPTION.search(value)
    if match is None:
        return False
    description = match.group(1).strip()
    if not description:
        return False
    if description[0] in {'"', "'"}:
        return len(description) >= 2 and description[-1] == description[0]
    return ": " not in description


def _matters_version() -> str:
    return VERSION


def _matters_compatibility() -> str:
    current = Version(VERSION)
    return (
        f">={current.major}.{current.minor},"
        f"<{current.major}.{current.minor + 1}"
    )


def _normalized_contract_text(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", " ", value.casefold())


def _contract_permissions(skill_id: str) -> tuple[str, ...]:
    profile = _CONTRACT_PROFILES[skill_id]
    return tuple(
        f"contract.{field}.{profile[field]}"
        for field in _CONTRACT_PROFILE_ORDER
    )


def _contract_profile_from_text(value: str) -> dict[str, str] | None:
    match = _CONTRACT_LINE.search(value)
    if match is None:
        return None
    return dict(zip(_CONTRACT_PROFILE_ORDER, match.groups(), strict=True))


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
            matters_compatibility=_matters_compatibility(),
            origin=SkillOrigin.BUNDLED,
            content_hash=projection_content_hash(files),
            required=True,
            installation_policy=InstallationPolicy.BUNDLED_INTERNAL,
            capabilities=_CAPABILITIES[skill_id],
            permissions=(
                *_PERMISSIONS[skill_id],
                *_contract_permissions(skill_id),
            ),
            data_disclosure_policy=_DISCLOSURE_POLICIES[skill_id],
            dependencies=(),
            runtime_identity=f"matters-runtime:{_matters_version()}",
            validator_identity="matters-bundled-skill-validator:v6",
        )
        rows.append(SkillProjection(manifest, files))
    return tuple(rows)


def build_bundle(root: Path | None = None) -> BundleManifest:
    projections = load_projections(root)
    bundle = BundleManifest.build(
        pack_id="matters-consumer-skill-pack",
        pack_version=_matters_version(),
        matters_compatibility=_matters_compatibility(),
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
    for skill_id in sorted(RETIRED_SKILL_IDS):
        retired_root = pack_root / skill_id
        if retired_root.is_dir() and any(
            path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix not in {".pyc", ".pyo", ".log"}
            for path in retired_root.rglob("*")
        ):
            findings.append(f"{skill_id}:retired_skill_authority_present")
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
            for retired_skill_id in RETIRED_SKILL_IDS:
                if retired_skill_id in consumer_text:
                    findings.append(
                        f"{skill_id}:retired_skill_authority_reference:"
                        f"{item.path}:{retired_skill_id}"
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
        if not _frontmatter_description_is_yaml_safe(text):
            findings.append(f"{skill_id}:frontmatter_yaml_unsafe")
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
        for surface_name, surface_text in (
            ("skill", text),
            ("prompt", prompt_text),
            ("contract", contract_text),
        ):
            profile = _contract_profile_from_text(surface_text)
            if profile is None and surface_name == "contract":
                findings.append(
                    f"{skill_id}:contract_applicability_missing:"
                    f"{surface_name}"
                )
            elif (
                profile is not None
                and profile != _CONTRACT_PROFILES[skill_id]
            ):
                findings.append(
                    f"{skill_id}:contract_applicability_mismatch:"
                    f"{surface_name}"
                )
            normalized_surface = _normalized_contract_text(surface_text)
            for marker in _RETIRED_CAPABILITY_ROLE_MARKERS:
                if marker in normalized_surface:
                    findings.append(
                        f"{skill_id}:retired_capability_role:"
                        f"{surface_name}:{marker}"
                    )
            for marker in _SHARED_PRODUCT_MARKERS:
                if marker not in normalized_surface:
                    findings.append(
                        f"{skill_id}:shared_product_marker_missing:"
                        f"{surface_name}:{marker}"
                    )
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
        if manifest.validator_identity != "matters-bundled-skill-validator:v6":
            findings.append(f"{skill_id}:validator_identity_mismatch")
        if manifest.installation_policy != InstallationPolicy.BUNDLED_INTERNAL:
            findings.append(f"{skill_id}:installation_policy_mismatch")
        for permission in _contract_permissions(skill_id):
            if permission not in manifest.permissions:
                findings.append(
                    f"{skill_id}:manifest_contract_permission_missing:"
                    f"{permission}"
                )
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
    "RETIRED_SKILL_IDS",
    "build_bundle",
    "load_projections",
    "validate_bundle",
]
