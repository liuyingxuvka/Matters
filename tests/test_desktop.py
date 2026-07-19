from __future__ import annotations

import json
from pathlib import Path

import pytest

from matters import desktop


def test_resolve_browser_and_launch_command(tmp_path: Path) -> None:
    browser = tmp_path / "msedge.exe"
    browser.write_bytes(b"test")

    assert desktop.resolve_browser(browser) == browser.resolve()
    command = desktop.desktop_launch_command(
        browser=browser,
        url="http://127.0.0.1:4321/",
        private_root=tmp_path / "private",
    )

    assert command[0] == str(browser)
    assert command[1] == "--app=http://127.0.0.1:4321/"
    assert any(item.startswith("--user-data-dir=") for item in command)
    assert (tmp_path / "private" / "desktop" / "browser-profile").is_dir()


def test_check_desktop_is_loopback_and_bilingual(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser = tmp_path / "msedge.exe"
    browser.write_bytes(b"test")
    monkeypatch.setenv("MATTERS_HOME", str(tmp_path / "private"))

    result = desktop.check_desktop(browser=browser)

    assert result["desktop_shell"] == "available"
    assert result["loopback_only"] is True
    assert result["available_locales"] == ["en", "zh-CN"]
    assert result["private_root"] == str((tmp_path / "private").resolve())


def test_default_private_root_avoids_windows_store_virtualized_local_app_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MATTERS_HOME", raising=False)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    assert desktop.default_private_root() == (tmp_path / ".matters").resolve()


def test_main_check_emits_canonical_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    browser = tmp_path / "msedge.exe"
    browser.write_bytes(b"test")

    assert desktop.main(["--check", "--browser", str(browser)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["result"]["desktop_shell"] == "available"


def test_missing_browser_is_visible_failure(tmp_path: Path) -> None:
    with pytest.raises(desktop.DesktopShellUnavailable):
        desktop.resolve_browser(tmp_path / "missing.exe")
