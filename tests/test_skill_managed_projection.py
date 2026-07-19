from pathlib import Path

from matters.skills import (
    ActiveSkillResolver,
    BundleManifest,
    CandidateValidation,
    FilesystemManagedProjectionStore,
    InstallationPolicy,
    InstalledSkill,
    MachineSkillInventory,
    ManagedProjectionSynchronizer,
    ProjectionFile,
    ResearchGuardGate,
    ResearchGuardStatus,
    ResolutionEnvironment,
    SkillManifest,
    SkillOrigin,
    SkillProjection,
    ValidationStatus,
    VerificationResult,
    matters_managed_projection,
    projection_content_hash,
)


def _projection(
    *,
    version: str,
    content: bytes,
    origin: SkillOrigin,
    policy: InstallationPolicy,
) -> SkillProjection:
    files = (
        ProjectionFile("SKILL.md", content),
        ProjectionFile("runtime/runner.py", b"def run(): return 'advisory'\n"),
    )
    manifest = SkillManifest(
        skill_id="matters-skill-runtime",
        version=version,
        skill_schema_compatibility=">=1,<2",
        matters_compatibility=">=0.1,<0.2",
        origin=origin,
        content_hash=projection_content_hash(files),
        required=True,
        installation_policy=policy,
        capabilities=("skill_runtime",),
        permissions=("matter_service:capability",),
        data_disclosure_policy="no_source_content",
        dependencies=(),
        runtime_identity="matters-runtime:0.1",
        validator_identity="validator:consumer-v1",
    )
    return SkillProjection(manifest=manifest, files=files)


def _decision(
    bundled: SkillProjection,
    installed: SkillProjection,
):
    bundle = BundleManifest.build(
        pack_id="matters-consumer-pack",
        pack_version="0.1",
        matters_compatibility=">=0.1,<0.2",
        skill_schema_version="1",
        skills=(bundled.manifest,),
    )
    inventory = MachineSkillInventory.build((InstalledSkill(installed.manifest),))
    environment = ResolutionEnvironment(
        matters_version="0.1",
        skill_schema_version="1",
        available_runtime_identities=("matters-runtime:0.1",),
        dependency_identities=(),
        validations=tuple(
            CandidateValidation(
                candidate_manifest_fingerprint=row.manifest_fingerprint,
                validator_identity=row.validator_identity,
                status=ValidationStatus.CURRENT,
            )
            for row in (bundled.manifest, installed.manifest)
        ),
        researchguard=ResearchGuardGate(status=ResearchGuardStatus.PENDING),
    )
    return ActiveSkillResolver().resolve(
        bundle=bundle,
        inventory=inventory,
        environment=environment,
    ).decision_for(bundled.manifest.skill_id)


def _pass(identity: str):
    def verify(_path: Path, _projection: SkillProjection) -> VerificationResult:
        return VerificationResult(ok=True, verification_identity=identity)

    return verify


def _fail(identity: str, reason: str):
    def verify(_path: Path, _projection: SkillProjection) -> VerificationResult:
        return VerificationResult(
            ok=False,
            verification_identity=identity,
            reason=reason,
        )

    return verify


def test_managed_projection_stages_verifies_activates_and_commits(tmp_path):
    prior = _projection(
        version="1.0",
        content=b"prior",
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.MATTERS_MANAGED,
    )
    candidate = _projection(
        version="2.0",
        content=b"candidate",
        origin=SkillOrigin.BUNDLED,
        policy=InstallationPolicy.BUNDLED_INTERNAL,
    )
    store = FilesystemManagedProjectionStore(tmp_path / "machine-skills")
    store.initialize_managed_projection(prior)
    receipt = ManagedProjectionSynchronizer(store).synchronize(
        transaction_id="txn-success",
        decision=_decision(candidate, prior),
        installed=InstalledSkill(prior.manifest),
        projection=candidate,
        staged_validator=_pass("native:staged-current"),
        installed_currentness_validator=_pass("installed:current"),
    )

    assert receipt.status == "installed_current"
    assert receipt.synchronized
    installed_candidate = matters_managed_projection(candidate)
    assert receipt.source_identity == candidate.manifest.identity.fingerprint
    assert receipt.active_identity == installed_candidate.manifest.identity.fingerprint
    assert receipt.active_identity != receipt.source_identity
    active = store.active_path(candidate.manifest.skill_id)
    assert (active / "SKILL.md").read_bytes() == b"candidate"
    assert store.assert_current_managed(
        InstalledSkill(installed_candidate.manifest)
    ) == installed_candidate.manifest.identity.fingerprint
    assert not (active.parent / ".transactions").exists()


def test_post_activation_failure_restores_prior_projection(tmp_path):
    prior = _projection(
        version="1.0",
        content=b"prior",
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.MATTERS_MANAGED,
    )
    candidate = _projection(
        version="2.0",
        content=b"candidate",
        origin=SkillOrigin.BUNDLED,
        policy=InstallationPolicy.BUNDLED_INTERNAL,
    )
    store = FilesystemManagedProjectionStore(tmp_path / "machine-skills")
    store.initialize_managed_projection(prior)
    receipt = ManagedProjectionSynchronizer(store).synchronize(
        transaction_id="txn-rollback",
        decision=_decision(candidate, prior),
        installed=InstalledSkill(prior.manifest),
        projection=candidate,
        staged_validator=_pass("native:staged-current"),
        installed_currentness_validator=_fail(
            "installed:failed",
            "post-activation currentness failed",
        ),
    )

    assert receipt.status == "restored"
    assert receipt.rollback_identity.startswith("sha256:")
    assert receipt.active_identity == prior.manifest.identity.fingerprint
    active = store.active_path(prior.manifest.skill_id)
    assert (active / "SKILL.md").read_bytes() == b"prior"
    assert store.assert_current_managed(InstalledSkill(prior.manifest)) == (
        prior.manifest.identity.fingerprint
    )


def test_staged_failure_never_activates_candidate(tmp_path):
    prior = _projection(
        version="1.0",
        content=b"prior",
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.MATTERS_MANAGED,
    )
    candidate = _projection(
        version="2.0",
        content=b"candidate",
        origin=SkillOrigin.BUNDLED,
        policy=InstallationPolicy.BUNDLED_INTERNAL,
    )
    store = FilesystemManagedProjectionStore(tmp_path / "machine-skills")
    store.initialize_managed_projection(prior)
    receipt = ManagedProjectionSynchronizer(store).synchronize(
        transaction_id="txn-stage-fail",
        decision=_decision(candidate, prior),
        installed=InstalledSkill(prior.manifest),
        projection=candidate,
        staged_validator=_fail("native:failed", "native validator failed"),
        installed_currentness_validator=_pass("not-run"),
    )
    assert receipt.status == "blocked_before_activation"
    assert receipt.active_identity == prior.manifest.identity.fingerprint
    assert (
        store.active_path(prior.manifest.skill_id) / "SKILL.md"
    ).read_bytes() == b"prior"


def test_unmanaged_projection_is_update_available_without_any_write(tmp_path):
    external = _projection(
        version="1.0",
        content=b"external",
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.EXTERNALLY_MANAGED,
    )
    candidate = _projection(
        version="2.0",
        content=b"candidate",
        origin=SkillOrigin.BUNDLED,
        policy=InstallationPolicy.BUNDLED_INTERNAL,
    )
    root = tmp_path / "must-remain-absent"
    store = FilesystemManagedProjectionStore(root)
    receipt = ManagedProjectionSynchronizer(store).synchronize(
        transaction_id="txn-unmanaged",
        decision=_decision(candidate, external),
        installed=InstalledSkill(external.manifest),
        projection=candidate,
        staged_validator=_pass("not-run"),
        installed_currentness_validator=_pass("not-run"),
    )
    assert receipt.status == "unmanaged_unchanged"
    assert receipt.update_available
    assert not root.exists()
