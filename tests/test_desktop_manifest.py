from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

import pytest

from matters.assets import asset_path
from matters._version import VERSION
from matters.bundled_skills import bundle as bundled
from scripts.build_desktop_manifest import (
    build_manifest,
    main as manifest_main,
    verify_manifest,
)


def _candidate(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "Matters"
    ui = root / "_internal" / "ui"
    assets = root / "_internal" / "matters" / "assets"
    skills = root / "_internal" / "matters" / "bundled_skills"
    ui.mkdir(parents=True)
    assets.mkdir(parents=True)
    (root / "Matters.exe").write_bytes(b"packaged-shell")
    source_ui = Path("ui")
    for name in ("index.html", "styles.css", "app.js"):
        shutil.copy2(source_ui / name, ui / name)
    shutil.copy2(asset_path("matters.ico"), assets / "matters.ico")
    shutil.copytree(
        Path(bundled.__file__).resolve().parent,
        skills,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    self_test = tmp_path / "self-test.json"
    self_test.write_text(
        json.dumps(
            {
                "ok": True,
                "result": {
                    "matters_version": VERSION,
                    "shell_kind": "packaged_windows_webview",
                    "available_locales": ["en", "zh-CN"],
                    "loopback_only": True,
                    "owns_application_window": True,
                    "packaged_ui": True,
                    "private_shell_profile": True,
                    "persists_locale_density_window_state": True,
                    "startup_health_gate": True,
                    "in_shell_recovery_surface": True,
                    "clean_owned_process_shutdown": True,
                },
            }
        ),
        encoding="utf-8",
    )
    toolchain = tmp_path / "desktop-build-toolchain.json"
    toolchain.write_text(
        json.dumps(
            {
                "schema": "matters.desktop-build-toolchain.v1",
                "python_version": "test",
                "pyinstaller_version": "test",
                "pywebview_version": "test",
            }
        ),
        encoding="utf-8",
    )
    return root, self_test, toolchain


def test_desktop_manifest_binds_complete_package_and_skill_pack(
    tmp_path: Path,
) -> None:
    package, self_test, toolchain = _candidate(tmp_path)
    manifest_path = tmp_path / "desktop-manifest.json"
    manifest = build_manifest(
        package,
        self_test=self_test,
        toolchain=toolchain,
    )
    manifest_path.write_text(
        json.dumps(manifest.canonical()),
        encoding="utf-8",
    )

    restored = verify_manifest(package, manifest_path)

    assert restored == manifest
    assert restored.release_ready is True
    assert restored.skill_pack_identity.startswith("sha256:")


def test_desktop_manifest_rejects_post_freeze_package_change(
    tmp_path: Path,
) -> None:
    package, self_test, toolchain = _candidate(tmp_path)
    manifest_path = tmp_path / "desktop-manifest.json"
    manifest = build_manifest(
        package,
        self_test=self_test,
        toolchain=toolchain,
    )
    manifest_path.write_text(
        json.dumps(manifest.canonical()),
        encoding="utf-8",
    )
    (package / "_internal" / "ui" / "app.js").write_text(
        "changed",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="stale"):
        verify_manifest(package, manifest_path)


def test_desktop_manifest_and_self_test_must_remain_external(
    tmp_path: Path,
) -> None:
    package, self_test, toolchain = _candidate(tmp_path)
    internal_self_test = package / "self-test.json"
    shutil.copy2(self_test, internal_self_test)

    with pytest.raises(ValueError, match="external"):
        build_manifest(
            package,
            self_test=internal_self_test,
            toolchain=toolchain,
        )

    manifest = build_manifest(
        package,
        self_test=self_test,
        toolchain=toolchain,
    )
    internal_manifest = package / "desktop-manifest.json"
    internal_manifest.write_text(json.dumps(manifest.canonical()), encoding="utf-8")

    with pytest.raises(ValueError, match="external"):
        verify_manifest(package, internal_manifest)


def test_desktop_manifest_rejects_stale_or_incomplete_self_test(
    tmp_path: Path,
) -> None:
    package, self_test, toolchain = _candidate(tmp_path)
    payload = json.loads(self_test.read_text(encoding="utf-8"))
    payload["result"]["matters_version"] = "0.0.0"
    self_test.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="self-test version is stale"):
        build_manifest(
            package,
            self_test=self_test,
            toolchain=toolchain,
        )


def test_desktop_package_rejects_embedded_control_artifacts(
    tmp_path: Path,
) -> None:
    package, self_test, toolchain = _candidate(tmp_path)
    (package / "desktop-self-test.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="external control artifact"):
        build_manifest(
            package,
            self_test=self_test,
            toolchain=toolchain,
        )


def test_desktop_package_rejects_linked_content(tmp_path: Path) -> None:
    package, self_test, toolchain = _candidate(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    linked = package / "linked.txt"
    try:
        linked.symlink_to(outside)
    except OSError:
        pytest.skip("symbolic links are unavailable in this Windows environment")

    with pytest.raises(ValueError, match="links or junctions"):
        build_manifest(
            package,
            self_test=self_test,
            toolchain=toolchain,
        )


def test_desktop_manifest_cli_writes_and_reloads_external_manifest_and_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package, self_test, toolchain = _candidate(tmp_path)
    manifest_path = tmp_path / "desktop-manifest.json"
    plan_path = tmp_path / "desktop-plan.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_desktop_manifest.py",
            "--package-root",
            str(package),
            "--manifest",
            str(manifest_path),
            "--self-test",
            str(self_test),
            "--toolchain",
            str(toolchain),
            "--plan",
            str(plan_path),
            "--transaction-id",
            "desktop-install-1",
        ],
    )

    assert manifest_main() == 0

    output = json.loads(capsys.readouterr().out)
    assert output["release_ready"] is True
    assert output["plan"]["transaction_id"] == "desktop-install-1"
    assert manifest_path.is_file()
    assert plan_path.is_file()
