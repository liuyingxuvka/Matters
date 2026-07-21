import json
from pathlib import Path
import tomllib

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from matters._version import VERSION


@pytest.mark.release
def test_frozen_release_identity_and_sbom_exist():
    assert Path("LICENSE").is_file()
    assert Path("SECURITY.md").is_file()
    assert Path("CHANGELOG.md").is_file()
    sbom = json.loads(Path("sbom.json").read_text(encoding="utf-8"))
    assert sbom["bomFormat"] == "CycloneDX"


def test_release_version_plugin_security_and_sbom_are_consistent():
    plugin = json.loads(
        Path("plugin/matters-plugin.json").read_text(encoding="utf-8")
    )
    sbom = json.loads(Path("sbom.json").read_text(encoding="utf-8"))
    component = sbom["metadata"]["component"]
    security = Path("SECURITY.md").read_text(encoding="utf-8")

    assert VERSION == "0.3.1"
    assert plugin["version"] == VERSION
    assert plugin["ai_setup_guide"].endswith("references/installation.md")
    assert plugin["maintenance_triggers"] == {
        "default": [
            "installed_ui_launch",
            "first_run",
            "explicit_cli_mcp_or_codex_request",
            "registered_source_or_project_change",
        ],
        "daily_schedule": "ai_host_managed_during_install",
        "daily_default_local_time": "21:00",
        "daily_schedule_count": 1,
    }
    assert Path(plugin["ai_setup_guide"]).is_file()
    assert component["version"] == VERSION
    assert component["purl"] == f"pkg:pypi/matters@{VERSION}"
    assert component["bom-ref"] == component["purl"]
    assert f"{VERSION.rsplit('.', 1)[0]}.x release line" in security


def test_public_ai_setup_contract_is_packaged_and_user_does_not_own_schedule():
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    references = project["tool"]["setuptools"]["data-files"][
        "share/matters/plugins/matters/skills/matters/references"
    ]
    guide_path = Path(
        "plugins/matters/skills/matters/references/installation.md"
    )
    guide = guide_path.read_text(encoding="utf-8")
    public_skill = Path("plugins/matters/skills/matters/SKILL.md").read_text(
        encoding="utf-8"
    )
    readme = Path("README.md").read_text(encoding="utf-8")

    assert guide_path.as_posix() in references
    assert "exactly one host-owned daily Matters maintenance schedule" in guide
    assert "The installing AI—not the human user—creates" in guide
    assert "automation_capability_unavailable" in guide
    assert "It is not hard-coded into Matters" in guide
    assert "installation.md" in public_skill
    assert "The user does not create" in readme
    assert "this task manually" in readme


def test_sbom_dependency_inventory_matches_pyproject_runtime_requirements():
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    sbom = json.loads(Path("sbom.json").read_text(encoding="utf-8"))
    declared = {
        canonicalize_name(requirement.name): str(requirement.specifier)
        for requirement in map(Requirement, project["project"]["dependencies"])
    }
    components = {
        canonicalize_name(component["name"]): component["version"]
        for component in sbom["components"]
        if component.get("scope") == "required"
    }

    assert components == declared


def test_install_receipt_uses_strict_utf8_without_bom():
    installer = Path("scripts/install_local.ps1").read_text(encoding="utf-8")

    assert "[System.IO.File]::WriteAllText(" in installer
    assert "[System.Text.UTF8Encoding]::new($false)" in installer
    assert "Set-Content -LiteralPath" not in installer


def test_install_shortcuts_use_the_packaged_matters_icon():
    installer = Path("scripts/install_local.ps1").read_text(encoding="utf-8")

    assert "from matters.desktop import application_icon_path" in installer
    assert '$Shortcut.IconLocation = "$IconPath,0"' in installer
    assert "application_icon = $IconPath" in installer


def test_install_activation_is_guarded_by_recoverable_prior_state():
    installer = Path("scripts/install_local.ps1").read_text(encoding="utf-8")

    snapshot = installer.index(
        "$PriorDistribution = New-DistributionSnapshot"
    )
    activation = installer.index("$ActivationStarted = $true")
    install = installer.index(
        "-m pip install --upgrade --force-reinstall --no-deps"
    )
    assert snapshot < activation < install
    assert "has no recoverable RECORD inventory" in installer
    assert "has no recoverable files" in installer
    assert "staging copy is not byte-identical" in installer


def test_install_failure_restores_package_shortcuts_receipt_and_candidate_archive():
    installer = Path("scripts/install_local.ps1").read_text(encoding="utf-8")

    assert "Restore-DistributionSnapshot -Snapshot $PriorDistribution" in installer
    assert "Restore-FileState -State $ShortcutState" in installer
    assert "Restore-FileState -State $ReceiptState" in installer
    assert "$WheelArchiveCreated" in installer
    assert "rollback is incomplete" in installer
    assert "Recovery staging remains at $TransactionRoot" in installer


def test_install_honors_explicit_private_root_without_persisting_it_for_tests():
    installer = Path("scripts/install_local.ps1").read_text(encoding="utf-8")

    assert "$PrivateRootWasExplicit" in installer
    assert "[System.IO.Path]::GetFullPath($env:MATTERS_HOME)" in installer
    assert "if (-not $PrivateRootWasExplicit)" in installer


def test_install_version_authority_remains_dynamic():
    installer = Path("scripts/install_local.ps1").read_text(encoding="utf-8")

    assert '$VersionSource = Join-Path $RepositoryRoot "src\\matters\\_version.py"' in installer
    assert '$ExpectedWheelPattern = "matters-$ExpectedVersion-*.whl"' in installer
    assert 'matters_version = $ExpectedVersion' in installer
    assert "matters-0.3.0-*.whl" not in installer
    assert '$ExpectedVersionScript | & $PythonPath - $VersionSource' in installer
    assert '$WheelIdentityScript | & $PythonPath - ([string]$Wheel.FullName) $ExpectedVersion' in installer
    assert '$McpValidationScript | & $PythonPath - $McpLauncher $ExpectedVersion' in installer
    assert '$DistributionIdentityScript | & $PythonPath -' in installer
    assert '$PythonPath -c @"' not in installer


def test_install_build_removes_exact_repository_build_residue_first():
    installer = Path("scripts/install_local.ps1").read_text(encoding="utf-8")

    cleanup = installer.index("Remove-RepositoryBuildResidue\n    New-Item")
    build = installer.index(
        "-m pip wheel $RepositoryRoot --no-deps --wheel-dir $DistRoot"
    )
    assert cleanup < build
    assert '(Join-Path $RepositoryRoot "build")' in installer
    assert '(Join-Path $RepositoryRoot "src\\matters.egg-info")' in installer
    assert "A Matters build-residue path escapes the repository" in installer
    assert "[System.IO.FileAttributes]::ReparsePoint" in installer


def test_install_preflights_the_exact_mcp_and_skill_pack_contract():
    installer = Path("scripts/install_local.ps1").read_text(encoding="utf-8")

    preflight = installer.index("# matters-wheel-identity-v2")
    activation = installer.index("$ActivationStarted = $true")
    assert preflight < activation
    assert '"matters-mcp": "matters.api.mcp.stdio:main"' in installer
    assert '"matters/api/mcp/stdio.py"' in installer
    assert "The wheel bundled-skill authority is not the exact required eleven-skill pack" in installer
    assert "The wheel contains retired Matters skill authority" in installer
    assert '"matters-card-visual-curation"' in installer
    assert '"matters-generated-hero"' in installer
    assert "The installed skill pack is not byte-identical to the candidate wheel" in installer
    assert "The installed Matters MCP currentness check failed" in installer
    assert '"protocolVersion": "2025-11-25"' in installer


def test_install_receipt_freezes_mcp_wheel_and_skill_pack_identities():
    installer = Path("scripts/install_local.ps1").read_text(encoding="utf-8")

    assert "mcp_launcher = $McpLauncher" in installer
    assert "wheel_contents_fingerprint = $WheelIdentity.wheel_contents_fingerprint" in installer
    assert "skill_pack_identity = $WheelIdentity.skill_pack_identity" in installer
    assert "$PublishedReceipt.mcp_launcher -ne $McpLauncher" in installer
    assert "$PublishedReceipt.wheel_contents_fingerprint -ne $WheelIdentity.wheel_contents_fingerprint" in installer
    assert "$PublishedReceipt.skill_pack_identity -ne $WheelIdentity.skill_pack_identity" in installer
