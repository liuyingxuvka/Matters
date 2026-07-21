from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from matters import desktop


def test_application_icon_is_packaged_and_current() -> None:
    icon = desktop.application_icon_path()

    assert icon.name == "matters.ico"
    assert icon.is_file()
    assert icon.read_bytes().startswith(b"\x00\x00\x01\x00")


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
    assert result["application_icon"] == str(desktop.application_icon_path())
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


def test_packaged_self_test_starts_recovers_and_stops_owned_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeWebview:
        @staticmethod
        def create_window(*_args: object, **_kwargs: object) -> object:
            return object()

        @staticmethod
        def start(*_args: object, **_kwargs: object) -> None:
            return None

    monkeypatch.setattr(desktop, "_native_webview", lambda: FakeWebview())
    monkeypatch.setenv("MATTERS_HOME", "original-private-root")

    result = desktop.self_test_desktop(startup_timeout=3.0)

    assert result["matters_version"]
    assert result["shell_kind"] == "packaged_windows_webview"
    assert result["private_shell_profile"] is True
    assert result["persists_locale_density_window_state"] is True
    assert result["startup_health_gate"] is True
    assert result["in_shell_recovery_surface"] is True
    assert result["clean_owned_process_shutdown"] is True
    assert result["available_locales"] == ["en", "zh-CN"]
    assert os.environ["MATTERS_HOME"] == "original-private-root"


def test_packaged_self_test_rejects_missing_window_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(desktop, "_native_webview", lambda: object())

    with pytest.raises(desktop.DesktopShellUnavailable, match="window contract"):
        desktop.self_test_desktop(startup_timeout=0.1)


def test_missing_browser_is_visible_failure(tmp_path: Path) -> None:
    with pytest.raises(desktop.DesktopShellUnavailable):
        desktop.resolve_browser(tmp_path / "missing.exe")
