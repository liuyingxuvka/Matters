from pathlib import Path
import re
import shutil

from matters.analysis.operations import CAPABILITY_ROLES
from matters.bundled_skills import (
    REQUIRED_SKILL_IDS,
    RETIRED_SKILL_IDS,
    load_projections,
    validate_bundle,
)
from matters.bundled_skills import bundle as bundle_module
from matters.skills.manifest import ProjectionFile, projection_content_hash


REQUIRED_FILES = {
    "SKILL.md",
    "agents/openai.yaml",
    "references/service-contract.md",
    "scripts/invoke.py",
}


def _projection_text(skill_id: str, path: str) -> str:
    projection = next(
        item
        for item in load_projections()
        if item.manifest.skill_id == skill_id
    )
    return next(
        item.content.decode("utf-8")
        for item in projection.files
        if item.path == path
    )


def _copy_pack(tmp_path: Path) -> Path:
    source = Path(bundle_module.__file__).resolve().parent
    target = tmp_path / "bundled_skills"
    target.mkdir()
    for skill_id in REQUIRED_SKILL_IDS:
        shutil.copytree(source / skill_id, target / skill_id)
    return target


def test_each_skill_is_a_clean_standalone_consumer_projection():
    for projection in load_projections():
        paths = {item.path for item in projection.files}
        assert REQUIRED_FILES <= paths
        assert all(
            path.split("/", 1)[0]
            in {"SKILL.md", "agents", "references", "scripts", "assets"}
            for path in paths
        )
        assert all(".skillguard" not in path.casefold() for path in paths)
        skill_text = _projection_text(projection.manifest.skill_id, "SKILL.md")
        prompt_text = _projection_text(
            projection.manifest.skill_id,
            "agents/openai.yaml",
        )
        script_text = _projection_text(
            projection.manifest.skill_id,
            "scripts/invoke.py",
        )
        assert "MatterService" in skill_text
        assert f"${projection.manifest.skill_id}" in prompt_text
        assert "MatterService" in prompt_text
        assert "from matters.cli.main import main" in script_text
        assert "raise SystemExit(main())" in script_text


def test_every_skill_surface_shares_the_model_independent_product_contract():
    required_markers = {
        "deterministic_preprocessor",
        "low_cost_annotator",
        "ambiguity_resolver",
        "matter_modeler",
        "hero_image_generator",
        "consistency_reviewer",
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
    }
    assert CAPABILITY_ROLES == frozenset(
        {
            "deterministic_preprocessor",
            "low_cost_annotator",
            "ambiguity_resolver",
            "matter_modeler",
            "hero_image_generator",
            "consistency_reviewer",
            "maintenance_orchestrator",
        }
    )
    for projection in load_projections():
        for path in (
            "SKILL.md",
            "agents/openai.yaml",
            "references/service-contract.md",
        ):
            text = _projection_text(projection.manifest.skill_id, path)
            normalized = re.sub(
                r"[^a-z0-9_]+",
                " ",
                text.casefold(),
            )
            missing = {
                marker for marker in required_markers if marker not in normalized
            }
            assert not missing, (
                projection.manifest.skill_id,
                path,
                missing,
            )
            assert "visual_selector" not in normalized
            assert "researcher" not in normalized

        skill_and_contract = "\n".join(
            (
                _projection_text(projection.manifest.skill_id, "SKILL.md"),
                _projection_text(
                    projection.manifest.skill_id,
                    "references/service-contract.md",
                ),
            )
        ).casefold()
        assert "cannot create a matter" in re.sub(
            r"\s+",
            " ",
            skill_and_contract,
        )
        assert "program" in skill_and_contract
        assert "cache" in skill_and_contract
        assert "internal" in skill_and_contract
        for forbidden_model_binding in ("luna", "terra", "gpt-"):
            assert forbidden_model_binding not in skill_and_contract


def test_no_skill_declares_a_five_role_set_after_hero_and_orchestrator_adoption():
    declaration_start = re.compile(
        r"(?:only|complete|exact|same|every)\s+(?:[a-z-]+\s+)*"
        r"model-independent\s+(?:capability\s+)?"
        r"(?:roles?|role\s+set|capability\s+contract)",
    )
    for projection in load_projections():
        for path in ("SKILL.md", "references/service-contract.md"):
            text = _projection_text(projection.manifest.skill_id, path).casefold()
            for match in declaration_start.finditer(text):
                declaration = text[match.start() : match.start() + 420]
                assert "hero_image_generator" in declaration
                assert "maintenance_orchestrator" in declaration


def test_automatic_modeling_skills_do_not_restore_a_review_queue():
    source = _projection_text("matters-source-governance", "SKILL.md").casefold()
    semantic = _projection_text(
        "matters-semantic-understanding",
        "SKILL.md",
    ).casefold()
    correction = _projection_text(
        "matters-human-correction",
        "SKILL.md",
    ).casefold()
    autonomous = _projection_text(
        "matters-autonomous-maintenance",
        "SKILL.md",
    ).casefold()
    autonomous_contract = _projection_text(
        "matters-autonomous-maintenance",
        "references/service-contract.md",
    ).casefold()

    assert "ordinary uncertainty is not a per-item human-review gate" in source
    assert "automatic_owner_dispatch" in semantic
    assert "never ask the user to confirm ordinary findings" in semantic
    assert "optional_after_publication" in correction
    assert "never creates a review queue" in correction
    assert "per-item human confirmation is not a stage" in autonomous_contract
    assert "matters-human-review" not in REQUIRED_SKILL_IDS


def test_semantic_understanding_is_two_stage_model_independent_and_complete():
    projection = next(
        item
        for item in load_projections()
        if item.manifest.skill_id == "matters-semantic-understanding"
    )
    skill_text = _projection_text(
        "matters-semantic-understanding",
        "SKILL.md",
    ).casefold()
    contract_text = _projection_text(
        "matters-semantic-understanding",
        "references/service-contract.md",
    ).casefold()
    prompt_text = _projection_text(
        "matters-semantic-understanding",
        "agents/openai.yaml",
    ).casefold()
    combined = "\n".join((skill_text, contract_text, prompt_text))

    assert projection.manifest.validator_identity == (
        "matters-bundled-skill-validator:v6"
    )
    assert {
        "source_annotation",
        "semantic_understanding",
        "model_independent_capability_routing",
        "matter_hierarchy_and_work_items",
    } <= set(projection.manifest.capabilities)
    assert projection.manifest.content_hash == projection_content_hash(
        projection.files
    )
    assert "low_cost_annotator" in combined
    assert "matter_modeler" in combined
    assert "source_annotation" in combined
    assert "dependency_package_ids" in contract_text
    assert "execution_profile_contract_id" in contract_text
    assert "requested_output_types" in contract_text
    assert "returns only `source_annotation`" in skill_text
    assert "direct api fallback" in combined
    assert "never request or store an api key" in skill_text
    assert "named model" in skill_text
    assert "concrete execution identity" in contract_text

    for finding_type in (
        "matter_candidate",
        "matter_hierarchy_candidate",
        "work_item_candidate",
        "person_candidate",
        "event_candidate",
        "material_clue_candidate",
        "deadline_candidate",
        "open_loop_candidate",
        "lifecycle_candidate",
        "outcome_candidate",
        "completion_gap",
        "conflict",
        "bounded_summary",
        "summary_candidate",
        "generated_hero_candidate",
        "supplemental_information_candidate",
    ):
        assert finding_type in contract_text

    assert "parent-child" in combined
    assert "human-readable matter title" in contract_text
    assert "one-line" in contract_text
    assert "semantically equivalent english and chinese" in contract_text
    assert "semantic_revision" in contract_text
    assert "allowed_evidence_ids" in contract_text
    assert "allowed_asset_ids" in contract_text
    assert "input_dispositions" in contract_text
    assert "raw filename" in contract_text

    for forbidden_model_binding in ("luna", "terra", "gpt-"):
        assert forbidden_model_binding not in combined


def test_generated_hero_is_private_minimized_and_density_independent():
    skill_text = _projection_text(
        "matters-hero-image-generation",
        "SKILL.md",
    ).casefold()
    contract_text = _projection_text(
        "matters-hero-image-generation",
        "references/service-contract.md",
    ).casefold()

    assert "minimized hero brief" in skill_text
    assert "never source excerpts or user records" in skill_text
    assert "literal text, logos, brands" in skill_text
    assert "real photos, screenshots" in skill_text
    assert "images evidence gallery" in skill_text
    assert "standard and compact cards share the same generated hero" in (
        skill_text
    )
    assert "generation_pending_placeholder" in contract_text
    assert "generation_blocked_placeholder" in contract_text
    assert "presentation-only" in contract_text
    assert "sourceversion" in contract_text
    assert "images-gallery item" in contract_text


def test_hero_skill_is_a_direct_replacement_with_no_retired_authority():
    assert RETIRED_SKILL_IDS == frozenset(
        {
            "matters-card-visual-curation",
            "matters-generated-hero",
        }
    )
    assert "matters-hero-image-generation" in REQUIRED_SKILL_IDS
    assert not RETIRED_SKILL_IDS.intersection(REQUIRED_SKILL_IDS)
    for projection in load_projections():
        combined = b"\n".join(item.content for item in projection.files).decode(
            "utf-8"
        )
        assert not any(
            retired in combined for retired in RETIRED_SKILL_IDS
        )


def test_validator_rejects_any_retired_skill_authority_residual(tmp_path):
    root = _copy_pack(tmp_path)
    retired = root / "matters-card-visual-curation"
    retired.mkdir()
    (retired / "README.md").write_text(
        "retired authority",
        encoding="utf-8",
    )

    assert validate_bundle(root) == (
        "matters-card-visual-curation:retired_skill_authority_present",
    )


def test_validator_rejects_unquoted_frontmatter_colon(tmp_path):
    root = _copy_pack(tmp_path)
    skill_md = root / "matters-semantic-understanding" / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    skill_md.write_text(
        text.replace(
            'description: "Process a frozen private Matters work package through '
            'a model-independent two-stage capability contract: bounded low-cost '
            'source annotation followed by semantic Matter modeling. Use for queued '
            'file, mail, document, or image evidence and stale semantic analysis; '
            'never use it to scan adjacent sources, choose a named model, request an '
            'API key, or write canonical state."',
            'description: Process a frozen private Matters work package through a '
            'model-independent two-stage capability contract: bounded low-cost '
            'source annotation followed by semantic Matter modeling.',
        ),
        encoding="utf-8",
    )

    assert validate_bundle(root) == (
        "matters-semantic-understanding:frontmatter_yaml_unsafe",
    )


def test_projection_content_hash_changes_for_any_consumer_byte_change():
    projection = load_projections()[0]
    original = projection_content_hash(projection.files)
    changed = tuple(
        ProjectionFile(
            item.path,
            item.content + (b"\n" if item.path == "SKILL.md" else b""),
        )
        for item in projection.files
    )
    assert projection_content_hash(changed) != original


def test_validator_reports_author_control_residual_without_project_adoption(
    tmp_path,
):
    root = _copy_pack(tmp_path)
    residual = (
        root
        / "matters-source-governance"
        / ".skillguard"
        / "compiled-contract.json"
    )
    residual.parent.mkdir()
    residual.write_text("{}", encoding="utf-8")

    assert validate_bundle(root) == (
        "matters-source-governance:author_control_residual:"
        ".skillguard/compiled-contract.json",
    )


def test_validator_reports_missing_consumer_file(tmp_path):
    root = _copy_pack(tmp_path)
    (
        root
        / "matters-autonomous-maintenance"
        / "references"
        / "service-contract.md"
    ).unlink()

    assert validate_bundle(root) == (
        "matters-autonomous-maintenance:consumer_file_missing:"
        "references/service-contract.md",
    )


def test_validator_rejects_author_side_command_instruction(tmp_path):
    root = _copy_pack(tmp_path)
    contract = (
        root
        / "matters-skill-runtime"
        / "references"
        / "service-contract.md"
    )
    contract.write_text(
        contract.read_text(encoding="utf-8")
        + "\nRun skillguard_supervise.py from the consumer.\n",
        encoding="utf-8",
    )

    assert validate_bundle(root) == (
        "matters-skill-runtime:author_control_instruction:"
        "references/service-contract.md:skillguard_supervise.py",
    )


def test_validator_rejects_unexpected_consumer_skill(tmp_path):
    root = _copy_pack(tmp_path)
    unexpected = root / "matters-human-review"
    unexpected.mkdir()
    (unexpected / "SKILL.md").write_text(
        "---\nname: matters-human-review\n---\n",
        encoding="utf-8",
    )

    assert validate_bundle(root) == (
        "matters-human-review:unexpected_skill",
    )
