from pathlib import Path
import shutil

from matters.bundled_skills import (
    REQUIRED_SKILL_IDS,
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


def test_visual_curation_is_allowlist_only_and_density_independent():
    skill_text = _projection_text(
        "matters-card-visual-curation",
        "SKILL.md",
    ).casefold()
    contract_text = _projection_text(
        "matters-card-visual-curation",
        "references/service-contract.md",
    ).casefold()

    assert "eligible_asset_ids" in skill_text
    assert "never return a local path or arbitrary url" in skill_text
    assert "fetch from" in skill_text and "internet" in skill_text
    assert "standard and compact card density share the same selected asset" in (
        skill_text
    )
    assert "deterministic_fallback_policy_id" in contract_text
    assert "selected_asset_id" in contract_text


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
