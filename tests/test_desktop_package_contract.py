from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

import scripts.build_desktop_release_archive as release_archive
from flowguard_models.delivery_flow import VERSION, _desktop_install_gate

from matters.desktop_package import (
    BROWSER_DEVELOPMENT_SHELL,
    DesktopInstallTransactionPlan,
    DesktopPackageManifest,
    INSTALL_STAGES,
    PACKAGED_WINDOWS_WEBVIEW_SHELL,
    ROLLBACK_STAGES,
)


def _sha(character: str) -> str:
    return "sha256:" + character * 64


def _manifest(
    *,
    shell_kind: str = PACKAGED_WINDOWS_WEBVIEW_SHELL,
    startup_health_gate: bool = True,
    in_shell_recovery_surface: bool = True,
    clean_owned_process_shutdown: bool = True,
) -> DesktopPackageManifest:
    return DesktopPackageManifest.create(
        application_id="matters.desktop",
        matters_version="0.3.0",
        shell_kind=shell_kind,
        package_sha256=_sha("1"),
        executable_sha256=_sha("2"),
        build_toolchain_sha256=_sha("3"),
        ui_bundle_sha256=_sha("4"),
        icon_sha256=_sha("5"),
        service_contract_identity="matters.service.v1",
        worker_contract_identity="matters.worker.v1",
        skill_pack_identity="matters.skill-pack.v1",
        startup_health_gate=startup_health_gate,
        in_shell_recovery_surface=in_shell_recovery_surface,
        clean_owned_process_shutdown=clean_owned_process_shutdown,
    )


def test_true_packaged_shell_contract_closes_the_pure_release_gate():
    manifest = _manifest()

    assert manifest.release_gate_findings() == ()
    assert manifest.release_ready is True
    assert manifest.available_locales == ("en", "zh-CN")
    assert manifest.manifest_fingerprint.startswith("sha256:")


def test_browser_development_wrapper_can_never_close_the_desktop_gate():
    manifest = _manifest(shell_kind=BROWSER_DEVELOPMENT_SHELL)

    assert manifest.release_ready is False
    assert manifest.release_gate_findings() == (
        "browser_development_surface_only",
    )
    with pytest.raises(ValueError, match="not release-ready"):
        DesktopInstallTransactionPlan.create(
            transaction_id="desktop-install-1",
            candidate=manifest,
            prior_install_identity="",
        )


def test_packaged_shell_gate_names_each_missing_owned_behavior():
    manifest = _manifest(
        startup_health_gate=False,
        in_shell_recovery_surface=False,
        clean_owned_process_shutdown=False,
    )

    assert manifest.release_gate_findings() == (
        "startup_health_gate_missing",
        "in_shell_recovery_surface_missing",
        "clean_owned_process_shutdown_missing",
    )


def test_transaction_plan_freezes_activation_and_complete_rollback_order():
    plan = DesktopInstallTransactionPlan.create(
        transaction_id="desktop-install-1",
        candidate=_manifest(),
        prior_install_identity=_sha("6"),
    )

    assert plan.stages == INSTALL_STAGES
    assert plan.rollback_stages == ROLLBACK_STAGES
    assert plan.stages.index("verify_staged_package") < plan.stages.index(
        "activate_candidate"
    )
    assert plan.stages.index("verify_installed_currentness") < plan.stages.index(
        "publish_install_receipt"
    )
    assert plan.rollback_required_after_activation is True
    assert plan.plan_fingerprint.startswith("sha256:")


def test_transaction_plan_accepts_only_portable_opaque_locators():
    with pytest.raises(ValueError, match="opaque portable identity"):
        DesktopInstallTransactionPlan.create(
            transaction_id=r"P:\private-install\transaction",
            candidate=_manifest(),
            prior_install_identity="",
        )


def test_desktop_manifest_round_trips_through_public_mapping():
    manifest = _manifest()

    restored = DesktopPackageManifest.from_mapping(manifest.canonical())

    assert restored == manifest
    assert restored.release_ready is True


def test_desktop_manifest_rejects_non_boolean_gate_values():
    payload = dict(_manifest().canonical())
    payload["startup_health_gate"] = "true"

    with pytest.raises(ValueError, match="must be a boolean"):
        DesktopPackageManifest.from_mapping(payload)


def test_transaction_plan_round_trips_and_rejects_changed_stage_contract():
    plan = DesktopInstallTransactionPlan.create(
        transaction_id="desktop-install-1",
        candidate=_manifest(),
        prior_install_identity="",
    )

    assert DesktopInstallTransactionPlan.from_mapping(plan.canonical()) == plan

    changed = dict(plan.canonical())
    changed["stages"] = list(reversed(INSTALL_STAGES))
    with pytest.raises(ValueError, match="stages are invalid"):
        DesktopInstallTransactionPlan.from_mapping(changed)


def test_desktop_build_keeps_manifest_and_self_test_outside_package_tree():
    script = Path("scripts/build_desktop_package.ps1").read_text(encoding="utf-8")

    assert 'Join-Path $OutputPath "desktop-self-test.json"' in script
    assert 'Join-Path $OutputPath "desktop-manifest.json"' in script
    assert 'Join-Path $OutputPath "Matters"' in script
    assert "[System.IO.Path]::IsPathRooted($OutputRoot)" in script
    assert "-FilePath $Executable" in script
    assert '-ArgumentList "--self-test"' in script
    assert "-RedirectStandardOutput $SelfTestStdoutPath" in script
    assert "-RedirectStandardError $SelfTestStderrPath" in script
    assert "$SelfTestProcess.ExitCode" in script
    assert "desktop-build-toolchain.json" in script
    assert "--toolchain $ToolchainPath" in script
    assert '$IconPath = Join-Path $RepositoryRoot "src\\matters\\assets\\matters.ico"' in script
    assert '$SourcePath = Join-Path $RepositoryRoot "src"' in script
    assert '$BundledSkillsPath = Join-Path $SourcePath "matters\\bundled_skills"' in script
    assert '$UiPath = Join-Path $RepositoryRoot "ui"' in script
    assert '$EntryPath = Join-Path $RepositoryRoot "scripts\\matters_desktop_entry.py"' in script
    assert "--icon $IconPath" in script
    assert "--paths $SourcePath" in script
    assert '--collect-all "webview"' not in script
    assert '--hidden-import "webview.platforms.winforms"' in script
    assert '--hidden-import "webview.platforms.edgechromium"' in script
    for excluded in (
        "webview.platforms.android",
        "webview.platforms.cef",
        "webview.platforms.cocoa",
        "webview.platforms.gtk",
        "webview.platforms.qt",
        "torch",
        "pandas",
        "scipy",
        "matplotlib",
        "pytest",
    ):
        assert f'--exclude-module "{excluded}"' in script
    assert '--add-data "$BundledSkillsPath;matters\\bundled_skills"' in script
    assert '--add-data "$UiPath;ui"' in script
    assert "$EntryPath" in script
    assert '--add-data "ui;ui"' not in script
    assert '-Filter "direct_url.json"' in script
    assert "build_desktop_release_archive.py" in script
    assert '"Matters-{0}-windows-x64.zip" -f $MattersVersion' in script
    assert 'Copy-Item -LiteralPath $ReadmePath' in script
    assert 'Copy-Item -LiteralPath $AiSetupPath' in script


def test_desktop_release_archive_excludes_private_build_evidence(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "desktop"
    package = root / "Matters"
    package.mkdir(parents=True)
    (package / "Matters.exe").write_bytes(b"synthetic-executable")
    (root / "desktop-manifest.json").write_text("{}", encoding="utf-8")
    (root / "desktop-build-toolchain.json").write_text("{}", encoding="utf-8")
    (root / "README.md").write_text("# Matters\n", encoding="utf-8")
    (root / "AI-SETUP.md").write_text("# AI setup\n", encoding="utf-8")
    private_icon = (
        "C:" + "\\\\" + "Users" + "\\\\private\\\\icon.ico"
    )
    (root / "desktop-self-test.json").write_text(
        json.dumps({"application_icon": private_icon}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        release_archive,
        "verify_manifest",
        lambda package_root, manifest_path: SimpleNamespace(
            build_toolchain_sha256=(
                "sha256:" + sha256(b"{}").hexdigest()
            )
        ),
    )

    output = tmp_path / "Matters-0.3.0-windows-x64.zip"
    release_archive.build_release_archive(root, output)

    with zipfile.ZipFile(output) as archive:
        names = {
            row.filename
            for row in archive.infolist()
            if not row.is_dir()
        }
    assert names == {
        "AI-SETUP.md",
        "Matters/Matters.exe",
        "README.md",
        "desktop-build-toolchain.json",
        "desktop-manifest.json",
    }
    assert "desktop-self-test.json" not in names


def test_desktop_release_archive_rejects_direct_url_receipt(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "desktop"
    package = root / "Matters"
    direct_url = package / "_internal" / "matters-0.3.0.dist-info"
    direct_url.mkdir(parents=True)
    (package / "Matters.exe").write_bytes(b"synthetic-executable")
    private_wheel = (
        "file:///C:/" + "Users" + "/private/wheel.whl"
    )
    (direct_url / "direct_url.json").write_text(
        json.dumps({"url": private_wheel}),
        encoding="utf-8",
    )
    for name in (
        "AI-SETUP.md",
        "README.md",
        "desktop-manifest.json",
        "desktop-build-toolchain.json",
        "desktop-self-test.json",
    ):
        (root / name).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        release_archive,
        "verify_manifest",
        lambda package_root, manifest_path: SimpleNamespace(
            build_toolchain_sha256=(
                "sha256:" + sha256(b"{}").hexdigest()
            )
        ),
    )

    with pytest.raises(ValueError, match="direct_url"):
        release_archive.build_release_archive(
            root,
            tmp_path / "Matters-0.3.0-windows-x64.zip",
        )


def test_desktop_release_archive_rejects_stale_toolchain_receipt(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "desktop"
    package = root / "Matters"
    package.mkdir(parents=True)
    (package / "Matters.exe").write_bytes(b"synthetic-executable")
    for name in (
        "AI-SETUP.md",
        "README.md",
        "desktop-manifest.json",
        "desktop-build-toolchain.json",
        "desktop-self-test.json",
    ):
        (root / name).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        release_archive,
        "verify_manifest",
        lambda package_root, manifest_path: SimpleNamespace(
            build_toolchain_sha256="sha256:" + "0" * 64
        ),
    )

    with pytest.raises(ValueError, match="toolchain receipt is stale"):
        release_archive.build_release_archive(
            root,
            tmp_path / "Matters-0.3.0-windows-x64.zip",
        )


def test_desktop_installer_has_verified_unique_snapshots_and_atomic_receipt():
    script = Path("scripts/install_desktop_package.ps1").read_text(
        encoding="utf-8"
    )

    assert '"shortcut-{0}.lnk" -f $Index' in script
    assert "function Save-FileState" in script
    assert "function Restore-FileState" in script
    assert "Assert-ShortcutCurrent" in script
    assert "rollback was incomplete" in script
    assert (
        '$ReceiptReplaceBackupPath = Join-Path $TransactionRoot '
        '"active-install.replace-backup.json"'
    ) in script
    assert "$ReceiptReplaceBackupPath" in script
    assert "[System.IO.File]::Replace(" in script
    assert "[System.IO.File]::Replace($ReceiptCandidatePath, $ReceiptPath, $null)" not in script
    assert "transaction_plan_fingerprint" in script
    assert "executable_sha256" in script
    assert "-FilePath $InstalledExecutable" in script
    assert "-RedirectStandardOutput $InstalledSelfTestStdoutPath" in script
    assert "-RedirectStandardError $InstalledSelfTestStderrPath" in script
    assert "$InstalledSelfTestProcess.ExitCode" in script
    assert "function Stop-PriorInstalledMattersProcesses" in script
    assert "The prior Matters process owner is outside the managed desktop installation." in script
    assert "The prior Matters desktop process tree did not stop cleanly." in script
    assert "-Launcher ([string]$ExistingReceipt.launcher)" in script
    assert "-InstalledRoot ([string]$ExistingReceipt.installed_root)" in script
    assert "prior_process_shutdown_verified = $PriorProcessShutdownVerified" in script


def test_desktop_release_gate_requires_prior_process_shutdown_receipt(
    tmp_path: Path,
    monkeypatch,
):
    package = tmp_path / "package"
    package.mkdir()
    launcher = package / "Matters.exe"
    launcher.write_bytes(b"desktop")
    executable_hash = "sha256:" + sha256(b"desktop").hexdigest()
    toolchain = tmp_path / "desktop-build-toolchain.json"
    toolchain.write_text(
        json.dumps({"schema": "matters.desktop-build-toolchain.v1"}),
        encoding="utf-8",
    )
    toolchain_hash = "sha256:" + sha256(toolchain.read_bytes()).hexdigest()
    manifest = {
        "matters_version": VERSION,
        "manifest_fingerprint": _sha("a"),
        "executable_sha256": executable_hash,
        "package_sha256": _sha("b"),
        "build_toolchain_sha256": toolchain_hash,
    }
    manifest_path = tmp_path / "desktop-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    receipt = {
        "schema": "matters.desktop-install-receipt.v1",
        "matters_version": VERSION,
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "executable_sha256": executable_hash,
        "package_sha256": manifest["package_sha256"],
        "build_toolchain_sha256": toolchain_hash,
        "launcher": str(launcher),
        "prior_process_shutdown_verified": False,
    }
    receipt_path = tmp_path / "active-install.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    archive_path = tmp_path / "Matters.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("desktop-manifest.json", json.dumps(manifest))
    monkeypatch.setenv("MATTERS_DESKTOP_MANIFEST", str(manifest_path))
    monkeypatch.setenv("MATTERS_DESKTOP_INSTALL_RECEIPT", str(receipt_path))
    monkeypatch.setenv("MATTERS_DESKTOP_TOOLCHAIN_RECEIPT", str(toolchain))
    monkeypatch.setenv("MATTERS_RELEASE_DESKTOP", str(archive_path))

    blocked = _desktop_install_gate(tmp_path)
    assert blocked["ok"] is False
    assert blocked["checks"]["prior_process_shutdown"] is False

    receipt["prior_process_shutdown_verified"] = True
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    current = _desktop_install_gate(tmp_path)
    assert current["ok"] is True
    assert current["checks"]["prior_process_shutdown"] is True
