from matters.bundled_skills import (
    REQUIRED_SKILL_IDS,
    build_bundle,
    load_projections,
    validate_bundle,
)
from matters.application.orchestrator import MatterService
from matters.skills import REQUIRED_INITIAL_SKILL_IDS
from matters.skills.manifest import (
    InstallationPolicy,
    projection_content_hash,
)


EXPECTED_SKILL_IDS = (
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


def test_app_local_skill_pack_has_exact_required_inventory():
    bundle = build_bundle()
    assert REQUIRED_SKILL_IDS == EXPECTED_SKILL_IDS
    assert REQUIRED_INITIAL_SKILL_IDS == EXPECTED_SKILL_IDS
    assert bundle.required_skill_ids == tuple(sorted(EXPECTED_SKILL_IDS))
    assert len(load_projections()) == 11
    assert not validate_bundle()


def test_consumer_projection_has_no_author_control_and_calls_shared_service():
    for projection in load_projections():
        paths = {item.path for item in projection.files}
        assert "SKILL.md" in paths
        assert "agents/openai.yaml" in paths
        assert "scripts/invoke.py" in paths
        assert "references/service-contract.md" in paths
        assert all(".skillguard" not in path.casefold() for path in paths)
        skill_text = next(
            item.content.decode("utf-8")
            for item in projection.files
            if item.path == "SKILL.md"
        )
        assert "MatterService" in skill_text
        contract_text = next(
            item.content.decode("utf-8")
            for item in projection.files
            if item.path == "references/service-contract.md"
        )
        assert (
            "canonical" in contract_text.lower()
            or "owner" in contract_text.lower()
        )


def test_every_bundled_manifest_binds_exact_projection_and_runtime_identity():
    bundle = build_bundle()
    capability_owners = {}
    for projection in load_projections():
        manifest = projection.manifest
        assert manifest.required
        assert manifest.installation_policy == InstallationPolicy.BUNDLED_INTERNAL
        assert manifest.content_hash == projection_content_hash(projection.files)
        assert str(manifest.version) == str(bundle.pack_version)
        assert manifest.runtime_identity == f"matters-runtime:{bundle.pack_version}"
        assert manifest.validator_identity == "matters-bundled-skill-validator:v6"
        assert manifest.permissions[:3] == (
            "matterservice_only",
            "declared_scope_only",
            "no_direct_canonical_writes",
        )
        assert len(manifest.permissions) == 9
        assert all(
            permission.startswith("contract.")
            for permission in manifest.permissions[3:]
        )
        for capability in manifest.capabilities:
            assert capability not in capability_owners
            capability_owners[capability] = manifest.skill_id
    assert bundle.bundle_hash == bundle.calculated_hash


def test_service_uses_bundle_without_global_install_and_reports_research_pending(
    tmp_path,
):
    service = MatterService(private_root=tmp_path / "private")
    view = service.resolve_skill_view()
    report = service.capabilities()
    assert view.status == "partial"
    assert all(decision.usable for decision in view.decisions)
    assert report.bundled_skill_count == 11
    assert report.active_skill_view == "partial"
    assert report.researchguard == "researchguard_pending_integration"
