from dataclasses import FrozenInstanceError

import pytest

from matters.skills import (
    BundleManifest,
    InstallationPolicy,
    InstalledSkill,
    MachineSkillInventory,
    ProjectionFile,
    REQUIRED_INITIAL_SKILL_IDS,
    SkillManifest,
    SkillOrigin,
    SkillProjection,
    projection_content_hash,
)


def _manifest(
    *,
    skill_id: str = "matters-source-governance",
    version: str = "1.0",
    content: bytes = b"consumer",
    origin: SkillOrigin = SkillOrigin.BUNDLED,
    policy: InstallationPolicy = InstallationPolicy.BUNDLED_INTERNAL,
) -> tuple[SkillManifest, tuple[ProjectionFile, ...]]:
    files = (ProjectionFile("SKILL.md", content),)
    manifest = SkillManifest(
        skill_id=skill_id,
        version=version,
        skill_schema_compatibility=">=1,<2",
        matters_compatibility=">=0.1,<0.2",
        origin=origin,
        content_hash=projection_content_hash(files),
        required=True,
        installation_policy=policy,
        capabilities=("source_governance",),
        permissions=("matter_service:read",),
        data_disclosure_policy="local_minimized_only",
        dependencies=(),
        runtime_identity="matters-runtime:0.1",
        validator_identity="validator:consumer-v1",
    )
    return manifest, files


def test_manifest_bundle_and_inventory_are_exact_immutable_identities():
    bundled, files = _manifest()
    projection = SkillProjection(manifest=bundled, files=files)
    bundle = BundleManifest.build(
        pack_id="matters-consumer-pack",
        pack_version="0.1",
        matters_compatibility=">=0.1,<0.2",
        skill_schema_version="1",
        skills=(bundled,),
    )
    installed, _ = _manifest(
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.EXTERNALLY_MANAGED,
    )
    inventory = MachineSkillInventory.build((InstalledSkill(installed),))

    assert projection.manifest.content_hash == projection_content_hash(files)
    assert bundle.bundle_hash == bundle.calculated_hash
    assert bundle.required_skill_ids == ("matters-source-governance",)
    assert inventory.revision == inventory.calculated_revision
    with pytest.raises(FrozenInstanceError):
        bundled.skill_id = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        inventory.revision = "changed"  # type: ignore[misc]


def test_bundle_hash_inventory_revision_and_projection_hash_reject_drift():
    bundled, files = _manifest()
    bundle = BundleManifest.build(
        pack_id="matters-consumer-pack",
        pack_version="0.1",
        matters_compatibility=">=0.1,<0.2",
        skill_schema_version="1",
        skills=(bundled,),
    )
    with pytest.raises(ValueError, match="bundle_hash"):
        BundleManifest(
            pack_id=bundle.pack_id,
            pack_version=bundle.pack_version,
            matters_compatibility=bundle.matters_compatibility,
            skill_schema_version=bundle.skill_schema_version,
            skills=bundle.skills,
            bundle_hash="sha256:" + "0" * 64,
        )
    with pytest.raises(ValueError, match="content_hash"):
        SkillProjection(
            manifest=bundled,
            files=(ProjectionFile("SKILL.md", b"different"),),
        )
    installed, _ = _manifest(
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.EXTERNALLY_MANAGED,
    )
    with pytest.raises(ValueError, match="inventory revision"):
        MachineSkillInventory(
            entries=(InstalledSkill(installed),),
            revision="sha256:" + "0" * 64,
        )
    assert projection_content_hash(files).startswith("sha256:")


@pytest.mark.parametrize(
    "path",
    (
        ".skillguard/contract-source.json",
        "receipts/run.json",
        "../escape.txt",
        "nested\\windows.txt",
    ),
)
def test_author_control_and_unsafe_paths_are_rejected(path):
    with pytest.raises(ValueError):
        ProjectionFile(path, b"forbidden")


def test_inventory_preserves_collision_candidates_for_visible_resolution():
    first, _ = _manifest(
        content=b"first",
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.EXTERNALLY_MANAGED,
    )
    second, _ = _manifest(
        content=b"second",
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.EXTERNALLY_MANAGED,
    )
    inventory = MachineSkillInventory.build(
        (InstalledSkill(first), InstalledSkill(second))
    )
    assert len(inventory.for_skill(first.skill_id)) == 2
    assert {
        row.manifest.content_hash for row in inventory.entries
    } == {first.content_hash, second.content_hash}


def test_initial_bundle_inventory_requires_all_declared_consumer_skills():
    manifests = tuple(
        _manifest(skill_id=skill_id, content=skill_id.encode("utf-8"))[0]
        for skill_id in REQUIRED_INITIAL_SKILL_IDS
    )
    bundle = BundleManifest.build(
        pack_id="matters-consumer-pack",
        pack_version="0.1",
        matters_compatibility=">=0.1,<0.2",
        skill_schema_version="1",
        skills=manifests,
    )
    bundle.validate_required_inventory(REQUIRED_INITIAL_SKILL_IDS)
    with pytest.raises(ValueError, match="required bundle inventory mismatch"):
        bundle.validate_required_inventory(REQUIRED_INITIAL_SKILL_IDS[:-1])
