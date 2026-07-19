from matters.analysis.operations import ResearchProviderStatus
from matters.integrations.researchguard import (
    load_researchguard_receipt,
    validate_researchguard_state,
)
from matters.runtime import create_service


def _manifest(receipt):
    return {
        "schema_version": receipt["manifest"]["schema_version"],
        "version": receipt["distribution"]["version"],
        "skill_ids": [
            "researchguard",
            "logicguard",
            "sourceguard",
            "traceguard",
        ],
        "retired_skill_ids": receipt["residual_state"]["retired_skill_ids"],
        "source_fingerprint": receipt["source"]["fingerprint"],
        "package_fingerprint": receipt["distribution"]["package_fingerprint"],
        "skill_fingerprints": receipt["skills"]["skill_fingerprints"],
    }


def test_frozen_researchguard_receipt_accepts_only_exact_installed_identity():
    receipt = load_researchguard_receipt()
    manifest = _manifest(receipt)
    assert validate_researchguard_state(
        receipt=receipt,
        manifest=manifest,
        distribution_version="0.1.1",
        console_entrypoints=("researchguard.cli:main",),
        package_fingerprint=receipt["distribution"]["package_fingerprint"],
        skill_fingerprints=receipt["skills"]["skill_fingerprints"],
        retired_residuals=(),
    ) == ()

    drifted = dict(receipt["skills"]["skill_fingerprints"])
    drifted["traceguard"] = "different"
    findings = validate_researchguard_state(
        receipt=receipt,
        manifest=manifest,
        distribution_version="0.1.0",
        console_entrypoints=("researchguard.cli:main",),
        package_fingerprint=receipt["distribution"]["package_fingerprint"],
        skill_fingerprints=drifted,
        retired_residuals=("traceguard-library",),
    )
    assert "installed_skill_fingerprint_mismatch" in findings
    assert "retired_skill_residual" in findings


def test_runtime_current_researchguard_reaches_capability_and_active_view(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        "matters.runtime.probe_researchguard",
        lambda: ResearchProviderStatus(
            "current",
            provider_version="0.1.0",
            source_commit="70c0405045cbf2a44abe994a20c77c4ebf82d384",
            portable_receipt_id=(
                "sha256:"
                "bb2116c70da152b4c7891e8354f15b86bf20a3bf0cc02107f9baf7d6f4e1a336"
            ),
        ),
    )
    monkeypatch.setenv("MATTERS_REPOSITORY_ROOT", str(tmp_path / "repo"))
    monkeypatch.delenv("MATTERS_HOME", raising=False)

    service = create_service()
    report = service.capabilities()

    assert report.researchguard == "researchguard_current"
    assert report.active_skill_view == "current"
