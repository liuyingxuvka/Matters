import json
from dataclasses import replace
from pathlib import Path

from matters.application.orchestrator import MatterService
from matters.bundled_skills import build_bundle, load_projections
from matters.skills import (
    FilesystemManagedProjectionStore,
    InstallationPolicy,
    SkillManifest,
    SkillOrigin,
    SkillProjection,
    discover_machine_skills,
    matters_managed_projection,
)


def _write_external(
    root: Path,
    projection: SkillProjection,
    *,
    version: str,
) -> None:
    target = root / projection.manifest.skill_id
    target.mkdir(parents=True)
    for item in projection.files:
        path = target / item.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(item.content)
    manifest = SkillManifest(
        skill_id=projection.manifest.skill_id,
        version=version,
        skill_schema_compatibility=(
            projection.manifest.skill_schema_compatibility
        ),
        matters_compatibility=projection.manifest.matters_compatibility,
        origin=SkillOrigin.MACHINE_INSTALLED,
        content_hash=projection.manifest.content_hash,
        required=projection.manifest.required,
        installation_policy=InstallationPolicy.EXTERNALLY_MANAGED,
        capabilities=projection.manifest.capabilities,
        permissions=projection.manifest.permissions,
        data_disclosure_policy=projection.manifest.data_disclosure_policy,
        dependencies=projection.manifest.dependencies,
        runtime_identity=projection.manifest.runtime_identity,
        validator_identity=projection.manifest.validator_identity,
        accepts_prereleases=projection.manifest.accepts_prereleases,
        researchguard_identity=projection.manifest.researchguard_identity,
    )
    (target / ".matters-consumer-skill.json").write_text(
        json.dumps(
            {
                "schema": "matters.machine-skill-candidate.v1",
                "manifest": manifest.canonical(),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_machine_discovery_checks_only_declared_ids_and_preserves_newer_overlay(
    tmp_path: Path,
):
    root = tmp_path / "skills"
    root.mkdir()
    unrelated = root / "unrelated-private-skill"
    unrelated.mkdir()
    (unrelated / "SKILL.md").write_text("private", encoding="utf-8")
    projection = load_projections()[0]
    _write_external(root, projection, version="0.1.1")

    discovery = discover_machine_skills(
        build_bundle(),
        external_roots=(root,),
    )

    assert discovery.status == "current"
    assert len(discovery.inventory.entries) == 1
    installed = discovery.inventory.entries[0].manifest
    assert installed.skill_id == projection.manifest.skill_id
    assert str(installed.version) == "0.1.1"
    assert "unrelated-private-skill" not in str(discovery)


def test_unverifiable_same_named_skill_is_visible_but_not_selected(
    tmp_path: Path,
):
    root = tmp_path / "skills"
    target = root / load_projections()[0].manifest.skill_id
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("unversioned", encoding="utf-8")

    discovery = discover_machine_skills(
        build_bundle(),
        external_roots=(root,),
    )

    assert discovery.status == "partial"
    assert discovery.inventory.entries == ()
    assert discovery.findings[0].endswith("machine_manifest_missing")


def test_service_updates_existing_managed_projection_but_installs_no_absent_skill(
    tmp_path: Path,
    monkeypatch,
):
    codex_home = tmp_path / "codex-home"
    (codex_home / "skills").mkdir(parents=True)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    repository = tmp_path / "repository"
    repository.mkdir()
    private = tmp_path / "private"
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )
    source = load_projections()[0]
    older_manifest = replace(
        source.manifest,
        version="0.0.1",
    )
    older = matters_managed_projection(
        SkillProjection(older_manifest, source.files)
    )
    store = FilesystemManagedProjectionStore(private / "managed-skills")
    store.initialize_managed_projection(older)

    result = service.synchronize_managed_skill_projections(
        transaction_id_prefix="test-sync",
    )

    assert result["status"] in {"current", "partial"}
    assert result["receipt_count"] == 1
    assert result["receipts"][0]["status"] == "installed_current"
    assert result["default_global_install"] is False
    assert not any((codex_home / "skills").iterdir())
