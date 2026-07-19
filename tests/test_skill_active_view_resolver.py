from matters.skills import (
    ActiveSkillResolver,
    BundleManifest,
    CandidateValidation,
    DependencyIdentity,
    InstallationPolicy,
    InstalledSkill,
    MachineSkillInventory,
    ProjectionFile,
    ResearchGuardGate,
    ResearchGuardStatus,
    ResolutionEnvironment,
    SkillManifest,
    SkillDependency,
    SkillOrigin,
    ValidationStatus,
    projection_content_hash,
)


def _manifest(
    *,
    version: str,
    content: bytes,
    origin: SkillOrigin,
    policy: InstallationPolicy,
    matters: str = ">=0.1,<0.2",
    schema: str = ">=1,<2",
    accepts_prereleases: bool = False,
    runtime: str = "matters-runtime:0.1",
    validator: str = "validator:consumer-v1",
    researchguard_identity: str = "",
    dependencies: tuple[SkillDependency, ...] = (),
) -> SkillManifest:
    files = (ProjectionFile("SKILL.md", content),)
    return SkillManifest(
        skill_id="matters-research-orchestration",
        version=version,
        skill_schema_compatibility=schema,
        matters_compatibility=matters,
        origin=origin,
        content_hash=projection_content_hash(files),
        required=True,
        installation_policy=policy,
        capabilities=("research_operation",),
        permissions=("matter_service:advisory",),
        data_disclosure_policy="local_minimized_only",
        dependencies=dependencies,
        runtime_identity=runtime,
        validator_identity=validator,
        accepts_prereleases=accepts_prereleases,
        researchguard_identity=researchguard_identity,
    )


def _bundle(bundled: SkillManifest) -> BundleManifest:
    return BundleManifest.build(
        pack_id="matters-consumer-pack",
        pack_version="0.1",
        matters_compatibility=">=0.1,<0.2",
        skill_schema_version="1",
        skills=(bundled,),
    )


def _environment(
    manifests: tuple[SkillManifest, ...],
    *,
    gate: ResearchGuardGate | None = None,
    statuses: dict[str, ValidationStatus] | None = None,
    runtimes: tuple[str, ...] = ("matters-runtime:0.1",),
    dependencies: tuple[DependencyIdentity, ...] = (),
) -> ResolutionEnvironment:
    statuses = statuses or {}
    return ResolutionEnvironment(
        matters_version="0.1",
        skill_schema_version="1",
        available_runtime_identities=runtimes,
        dependency_identities=dependencies,
        validations=tuple(
            CandidateValidation(
                candidate_manifest_fingerprint=row.manifest_fingerprint,
                validator_identity=row.validator_identity,
                status=statuses.get(
                    row.manifest_fingerprint,
                    ValidationStatus.CURRENT,
                ),
            )
            for row in manifests
        ),
        researchguard=gate
        or ResearchGuardGate(status=ResearchGuardStatus.PENDING),
    )


def _resolve(
    bundled: SkillManifest,
    *installed: SkillManifest,
    environment: ResolutionEnvironment | None = None,
):
    manifests = (bundled,) + installed
    return ActiveSkillResolver().resolve(
        bundle=_bundle(bundled),
        inventory=MachineSkillInventory.build(
            tuple(InstalledSkill(row) for row in installed)
        ),
        environment=environment or _environment(manifests),
    )


def test_bundled_only_uses_internal_view_without_global_install():
    bundled = _manifest(
        version="1.0",
        content=b"bundle",
        origin=SkillOrigin.BUNDLED,
        policy=InstallationPolicy.BUNDLED_INTERNAL,
    )
    view = _resolve(bundled)
    decision = view.decision_for(bundled.skill_id)

    assert view.status == "partial"
    assert decision.disposition == "bundled_internal"
    assert decision.usable
    assert not decision.update_available
    assert not decision.sync_required
    assert view.research_provider.status == ResearchGuardStatus.PENDING


def test_exact_match_and_newer_pep440_machine_overlay_are_deterministic():
    bundled = _manifest(
        version="1.0",
        content=b"same",
        origin=SkillOrigin.BUNDLED,
        policy=InstallationPolicy.BUNDLED_INTERNAL,
    )
    exact = _manifest(
        version="1.0",
        content=b"same",
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.EXTERNALLY_MANAGED,
    )
    exact_view = _resolve(bundled, exact)
    assert exact_view.decision_for(bundled.skill_id).disposition == "exact_match"

    newer = _manifest(
        version="1.0.post1",
        content=b"newer",
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.EXTERNALLY_MANAGED,
    )
    overlay = _resolve(bundled, newer).decision_for(bundled.skill_id)
    assert overlay.disposition == "machine_overlay"
    assert str(overlay.selected_identity.version) == "1.0.post1"


def test_newer_bundle_never_overwrites_unmanaged_and_flags_managed_sync():
    bundled = _manifest(
        version="2.0",
        content=b"bundle-new",
        origin=SkillOrigin.BUNDLED,
        policy=InstallationPolicy.BUNDLED_INTERNAL,
    )
    external = _manifest(
        version="1.0",
        content=b"external-old",
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.EXTERNALLY_MANAGED,
    )
    external_decision = _resolve(bundled, external).decision_for(bundled.skill_id)
    assert external_decision.disposition == "bundled_update_available"
    assert external_decision.update_available
    assert not external_decision.sync_required

    managed = _manifest(
        version="1.0",
        content=b"managed-old",
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.MATTERS_MANAGED,
    )
    managed_decision = _resolve(bundled, managed).decision_for(bundled.skill_id)
    assert managed_decision.disposition == "bundled_managed_sync_required"
    assert managed_decision.sync_required
    assert not managed_decision.update_available


def test_hash_collision_blocks_without_guessing_a_winner():
    bundled = _manifest(
        version="1.0",
        content=b"bundle",
        origin=SkillOrigin.BUNDLED,
        policy=InstallationPolicy.BUNDLED_INTERNAL,
    )
    installed = _manifest(
        version="1.0",
        content=b"different",
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.EXTERNALLY_MANAGED,
    )
    view = _resolve(bundled, installed)
    decision = view.decision_for(bundled.skill_id)
    assert view.status == "blocked"
    assert decision.disposition == "identity_collision"
    assert decision.selected_identity is None
    assert any(
        "same_version_hash_collision" in reason
        for row in decision.candidate_dispositions
        for reason in row.reasons
    )


def test_invalid_incompatible_and_unaccepted_prerelease_do_not_win():
    bundled = _manifest(
        version="1.0",
        content=b"bundle",
        origin=SkillOrigin.BUNDLED,
        policy=InstallationPolicy.BUNDLED_INTERNAL,
    )
    prerelease = _manifest(
        version="2.0rc1",
        content=b"pre",
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.EXTERNALLY_MANAGED,
    )
    incompatible = _manifest(
        version="3.0",
        content=b"incompatible",
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.EXTERNALLY_MANAGED,
        matters=">=1,<2",
    )
    environment = _environment(
        (bundled, prerelease, incompatible),
        statuses={
            incompatible.manifest_fingerprint: ValidationStatus.FAILED,
        },
    )
    decision = _resolve(
        bundled,
        prerelease,
        incompatible,
        environment=environment,
    ).decision_for(bundled.skill_id)
    assert decision.disposition == "bundled_internal"
    reasons = {
        reason
        for row in decision.candidate_dispositions
        for reason in row.reasons
    }
    assert "candidate_prerelease_not_accepted" in reasons
    assert "matters_version_incompatible" in reasons
    assert "native_validation_failed" in reasons


def test_explicitly_accepted_compatible_prerelease_can_be_the_newer_overlay():
    bundled = _manifest(
        version="1.0",
        content=b"bundle",
        origin=SkillOrigin.BUNDLED,
        policy=InstallationPolicy.BUNDLED_INTERNAL,
    )
    accepted = _manifest(
        version="2.0rc1",
        content=b"accepted-pre",
        origin=SkillOrigin.MACHINE_INSTALLED,
        policy=InstallationPolicy.EXTERNALLY_MANAGED,
        accepts_prereleases=True,
    )
    decision = _resolve(bundled, accepted).decision_for(bundled.skill_id)
    assert decision.disposition == "machine_overlay"
    assert str(decision.selected_identity.version) == "2.0rc1"


def test_zero_compatible_candidates_blocks_and_input_change_stales_view():
    bundled = _manifest(
        version="1.0",
        content=b"bundle",
        origin=SkillOrigin.BUNDLED,
        policy=InstallationPolicy.BUNDLED_INTERNAL,
        runtime="runtime:missing",
    )
    environment = _environment((bundled,))
    view = _resolve(bundled, environment=environment)
    assert view.status == "blocked"
    assert (
        view.decision_for(bundled.skill_id).disposition
        == "no_validated_compatible_candidate"
    )

    valid = _manifest(
        version="1.0",
        content=b"valid",
        origin=SkillOrigin.BUNDLED,
        policy=InstallationPolicy.BUNDLED_INTERNAL,
    )
    current_environment = _environment((valid,))
    current_view = _resolve(valid, environment=current_environment)
    changed_environment = _environment(
        (valid,),
        runtimes=("matters-runtime:0.1", "runtime:new"),
    )
    assert current_view.is_current_for(
        bundle=_bundle(valid),
        inventory=MachineSkillInventory.empty(),
        environment=current_environment,
    )
    assert not current_view.is_current_for(
        bundle=_bundle(valid),
        inventory=MachineSkillInventory.empty(),
        environment=changed_environment,
    )


def test_dependency_identity_is_exact_and_dependency_change_invalidates_view():
    dependency = SkillDependency(
        skill_id="matters-source-governance",
        version_compatibility=">=2,<3",
        content_hash="sha256:" + "a" * 64,
        runtime_identity="dependency-runtime:2",
    )
    bundled = _manifest(
        version="1.0",
        content=b"bundle",
        origin=SkillOrigin.BUNDLED,
        policy=InstallationPolicy.BUNDLED_INTERNAL,
        dependencies=(dependency,),
    )
    missing = _environment((bundled,))
    assert _resolve(
        bundled,
        environment=missing,
    ).decision_for(bundled.skill_id).status == "blocked"

    exact_dependency = DependencyIdentity(
        skill_id="matters-source-governance",
        version="2.1",
        content_hash="sha256:" + "a" * 64,
        runtime_identity="dependency-runtime:2",
    )
    current_environment = _environment(
        (bundled,),
        dependencies=(exact_dependency,),
    )
    view = _resolve(bundled, environment=current_environment)
    assert view.decision_for(bundled.skill_id).usable

    changed_environment = _environment(
        (bundled,),
        dependencies=(
            DependencyIdentity(
                skill_id="matters-source-governance",
                version="3.0",
                content_hash="sha256:" + "a" * 64,
                runtime_identity="dependency-runtime:2",
            ),
        ),
    )
    assert not view.is_current_for(
        bundle=_bundle(bundled),
        inventory=MachineSkillInventory.empty(),
        environment=changed_environment,
    )
    changed = _resolve(bundled, environment=changed_environment)
    assert changed.decision_for(bundled.skill_id).status == "blocked"


def test_researchguard_current_is_exact_and_legacy_parallel_fallback_is_rejected():
    bundled = _manifest(
        version="1.0",
        content=b"bundle",
        origin=SkillOrigin.BUNDLED,
        policy=InstallationPolicy.BUNDLED_INTERNAL,
        researchguard_identity="researchguard:commit-1",
    )
    current_gate = ResearchGuardGate(
        status=ResearchGuardStatus.CURRENT,
        identity="researchguard:commit-1",
        currentness_receipt_identity="receipt:portable-1",
        requested_provider_ids=("researchguard",),
    )
    current = _resolve(
        bundled,
        environment=_environment((bundled,), gate=current_gate),
    )
    assert current.status == "current"
    assert current.research_provider.provider_identity == "researchguard:commit-1"

    legacy_gate = ResearchGuardGate(
        status=ResearchGuardStatus.PENDING,
        requested_provider_ids=("logicguard", "sourceguard", "traceguard"),
    )
    legacy = _resolve(
        _manifest(
            version="1.0",
            content=b"synthetic-only",
            origin=SkillOrigin.BUNDLED,
            policy=InstallationPolicy.BUNDLED_INTERNAL,
        ),
        environment=_environment(
            (
                _manifest(
                    version="1.0",
                    content=b"synthetic-only",
                    origin=SkillOrigin.BUNDLED,
                    policy=InstallationPolicy.BUNDLED_INTERNAL,
                ),
            ),
            gate=legacy_gate,
        ),
    )
    assert legacy.status == "blocked"
    assert legacy.research_provider.reason.startswith(
        "legacy_parallel_fallback_rejected"
    )
    assert {
        disposition
        for _, disposition in legacy.research_provider.legacy_dispositions
    } == {"stale_source_only"}
