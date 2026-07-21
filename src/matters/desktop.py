"""Windows desktop shell for the local Matters object browser."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from typing import Sequence
from urllib.request import urlopen
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server
from socketserver import ThreadingMixIn

from matters._version import VERSION
from matters.api.http.static import create_local_application
from matters.assets import asset_path
from matters.runtime import create_service, repository_root


class DesktopShellUnavailable(RuntimeError):
    """Raised when no supported installed desktop web shell is available."""


def _native_webview():
    try:
        import webview  # type: ignore[import-not-found]
    except ImportError as exc:
        raise DesktopShellUnavailable(
            "the packaged Windows WebView shell is not installed"
        ) from exc
    return webview


class _ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class _QuietRequestHandler(WSGIRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        del format, args


def default_private_root() -> Path:
    configured = os.environ.get("MATTERS_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        return (Path(user_profile) / ".matters").resolve()
    return (Path.home() / ".matters").resolve()


def application_icon_path() -> Path:
    """Return the canonical icon used by installed Matters launch surfaces."""

    return asset_path("matters.ico")


def _window_state_path(private_root: Path) -> Path:
    return private_root / "desktop" / "window-state.json"


def _read_window_state(private_root: Path) -> tuple[int, int]:
    path = _window_state_path(private_root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        width = int(payload["width"])
        height = int(payload["height"])
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return 1600, 1000
    return max(width, 1024), max(height, 720)


def _write_window_state(private_root: Path, *, width: int, height: int) -> None:
    path = _window_state_path(private_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate = path.with_suffix(".json.tmp")
    candidate.write_text(
        json.dumps(
            {"height": max(int(height), 720), "width": max(int(width), 1024)},
            ensure_ascii=True,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    candidate.replace(path)


def browser_candidates() -> tuple[Path, ...]:
    override = os.environ.get("MATTERS_DESKTOP_BROWSER")
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override).expanduser())
    local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    program_files = Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
    program_files_x86 = Path(
        os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")
    )
    candidates.extend(
        [
            program_files_x86 / "Microsoft/Edge/Application/msedge.exe",
            program_files / "Microsoft/Edge/Application/msedge.exe",
            local_app_data / "Microsoft/Edge/Application/msedge.exe",
            program_files / "Google/Chrome/Application/chrome.exe",
            program_files_x86 / "Google/Chrome/Application/chrome.exe",
            local_app_data / "Google/Chrome/Application/chrome.exe",
        ]
    )
    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in unique:
            unique.append(resolved)
    return tuple(unique)


def resolve_browser(explicit: Path | None = None) -> Path:
    candidates = (explicit.expanduser().resolve(),) if explicit else browser_candidates()
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise DesktopShellUnavailable(
        "Microsoft Edge or Google Chrome is required for the Matters desktop window"
    )


def desktop_launch_command(
    *,
    browser: Path,
    url: str,
    private_root: Path,
) -> tuple[str, ...]:
    profile = private_root / "desktop" / "browser-profile"
    profile.mkdir(parents=True, exist_ok=True)
    return (
        str(browser),
        f"--app={url}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--disable-default-apps",
        "--window-size=1600,1000",
    )


def _port_ready(url: str, *, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{url}health", timeout=0.5) as response:
                if response.status == 200:
                    return True
        except (OSError, TimeoutError):
            time.sleep(0.05)
    return False


def _create_server() -> tuple[object, _ThreadingWSGIServer, str]:
    private_root = default_private_root()
    private_root.mkdir(parents=True, exist_ok=True)
    os.environ["MATTERS_HOME"] = str(private_root)
    service = create_service()
    application = create_local_application(
        service,
        ui_root=repository_root() / "ui",
    )
    server = make_server(
        "127.0.0.1",
        0,
        application,
        server_class=_ThreadingWSGIServer,
        handler_class=_QuietRequestHandler,
    )
    host, port = server.server_address[:2]
    return service, server, f"http://{host}:{port}/"


def check_desktop(*, browser: Path | None = None) -> dict[str, object]:
    private_root = default_private_root()
    if browser is not None:
        selected = resolve_browser(browser)
        shell_kind = "browser_development"
        renderer = str(selected)
    else:
        webview = _native_webview()
        shell_kind = "packaged_windows_webview"
        renderer = f"pywebview:{getattr(webview, '__version__', 'current')}"
    return {
        "desktop_shell": "available",
        "shell_kind": shell_kind,
        "renderer": renderer,
        "application_icon": str(application_icon_path()),
        "private_root": str(private_root),
        "loopback_only": True,
        "owns_application_window": browser is None,
        "packaged_ui": browser is None,
        "default_locale": "en",
        "available_locales": ["en", "zh-CN"],
    }


def self_test_desktop(*, startup_timeout: float = 10.0) -> dict[str, object]:
    """Exercise the packaged local service without opening a user window."""

    webview = _native_webview()
    webview_contract = callable(getattr(webview, "create_window", None)) and callable(
        getattr(webview, "start", None)
    )
    if not webview_contract:
        raise DesktopShellUnavailable(
            "the packaged Windows WebView window contract is unavailable"
        )
    previous_home = os.environ.get("MATTERS_HOME")
    server: _ThreadingWSGIServer | None = None
    thread: threading.Thread | None = None
    health_current = False
    recovery_surface = False
    private_profile = False
    state_persistence = False
    shutdown_current = False
    try:
        with tempfile.TemporaryDirectory(prefix="matters-desktop-self-test-") as root:
            os.environ["MATTERS_HOME"] = root
            _service, server, url = _create_server()
            thread = threading.Thread(
                target=server.serve_forever,
                name="matters-desktop-self-test-http",
                daemon=True,
            )
            thread.start()
            if not _port_ready(url, timeout=startup_timeout):
                raise DesktopShellUnavailable(
                    "the packaged local Matters service did not become healthy"
                )
            with urlopen(f"{url}health", timeout=2.0) as response:
                health_payload = json.loads(response.read().decode("utf-8"))
                health_result = (
                    health_payload.get("result", {})
                    if isinstance(health_payload, dict)
                    else {}
                )
                health_current = (
                    response.status == 200
                    and isinstance(health_payload, dict)
                    and health_payload.get("ok") is True
                    and isinstance(health_result, dict)
                    and health_result.get("package_status") == "active"
                    and int(health_result.get("bundled_skill_count", -1)) == 11
                )
            if not health_current:
                raise DesktopShellUnavailable(
                    "the packaged local Matters health contract is unavailable"
                )
            with urlopen(url, timeout=2.0) as response:
                document = response.read().decode("utf-8")
                document_status = response.status
            with urlopen(f"{url}app.js", timeout=2.0) as response:
                javascript = response.read().decode("utf-8")
                response_status = response.status
            recovery_surface = (
                document_status == 200
                and "app.js" in document
                and response_status == 200
                and "data-retry" in javascript
                and "ready_stale" in javascript
                and "transport_error" in javascript
            )
            if not recovery_surface:
                raise DesktopShellUnavailable(
                    "the packaged UI recovery surface is unavailable"
                )
            private_root = default_private_root()
            profile_root = private_root / "desktop" / "webview-profile"
            profile_root.mkdir(parents=True, exist_ok=True)
            private_profile = profile_root.resolve().is_relative_to(
                private_root.resolve()
            )
            _write_window_state(private_root, width=1420, height=860)
            state_persistence = (
                _read_window_state(private_root) == (1420, 860)
                and 'density: "matters-card-density"' in javascript
                and 'locale: "matters-locale"' in javascript
                and "localStorage.getItem" in javascript
                and "localStorage.setItem" in javascript
            )
            if not state_persistence:
                raise DesktopShellUnavailable(
                    "the packaged desktop state persistence contract is unavailable"
                )
            server.shutdown()
            server.server_close()
            server = None
            thread.join(timeout=5)
            shutdown_current = not thread.is_alive()
            if not shutdown_current:
                raise DesktopShellUnavailable(
                    "the packaged local service did not shut down cleanly"
                )
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)
        if previous_home is None:
            os.environ.pop("MATTERS_HOME", None)
        else:
            os.environ["MATTERS_HOME"] = previous_home
    return {
        "desktop_shell": "available",
        "matters_version": VERSION,
        "shell_kind": "packaged_windows_webview",
        "renderer": f"pywebview:{getattr(webview, '__version__', 'current')}",
        "application_icon": str(application_icon_path()),
        "loopback_only": True,
        "owns_application_window": webview_contract,
        "packaged_ui": True,
        "private_shell_profile": private_profile,
        "persists_locale_density_window_state": state_persistence,
        "default_locale": "en",
        "available_locales": ["en", "zh-CN"],
        "startup_health_gate": health_current,
        "in_shell_recovery_surface": recovery_surface,
        "clean_owned_process_shutdown": shutdown_current,
    }


def run_desktop(
    *,
    browser: Path | None = None,
    startup_timeout: float = 10.0,
) -> int:
    selected = resolve_browser(browser) if browser is not None else None
    native_webview = _native_webview() if selected is None else None
    private_root = default_private_root()
    service, server, url = _create_server()
    thread = threading.Thread(
        target=server.serve_forever,
        name="matters-desktop-http",
        daemon=True,
    )
    child: subprocess.Popen[bytes] | None = None
    service.start_autonomous_maintenance()
    thread.start()
    try:
        if not _port_ready(url, timeout=startup_timeout):
            raise DesktopShellUnavailable("the local Matters service did not start")
        if selected is not None:
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            child = subprocess.Popen(
                desktop_launch_command(
                    browser=selected,
                    url=url,
                    private_root=private_root,
                ),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
            return int(child.wait())
        storage_path = private_root / "desktop" / "webview-profile"
        storage_path.mkdir(parents=True, exist_ok=True)
        window_width, window_height = _read_window_state(private_root)
        window = native_webview.create_window(
            "Matters",
            url,
            width=window_width,
            height=window_height,
            min_size=(1024, 720),
            resizable=True,
            zoomable=True,
            text_select=True,
        )
        native_webview.start(
            gui="edgechromium",
            debug=False,
            private_mode=False,
            storage_path=str(storage_path),
            icon=str(application_icon_path()),
        )
        _write_window_state(
            private_root,
            width=int(getattr(window, "width", window_width)),
            height=int(getattr(window, "height", window_height)),
        )
        return 0
    except KeyboardInterrupt:
        return 130
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        service.stop_autonomous_maintenance()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="matters-desktop",
        description="Open the private local Matters desktop object browser.",
    )
    parser.add_argument("--browser", type=Path)
    parser.add_argument("--startup-timeout", type=float, default=10.0)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.check or args.self_test:
            json.dump(
                {
                    "ok": True,
                    "result": (
                        self_test_desktop(
                            startup_timeout=args.startup_timeout,
                        )
                        if args.self_test
                        else check_desktop(browser=args.browser)
                    ),
                },
                sys.stdout,
                ensure_ascii=False,
                sort_keys=True,
            )
            sys.stdout.write("\n")
            return 0
        return run_desktop(
            browser=args.browser,
            startup_timeout=args.startup_timeout,
        )
    except (DesktopShellUnavailable, OSError, ValueError) as exc:
        json.dump(
            {
                "ok": False,
                "error": {
                    "code": "desktop_shell_unavailable",
                    "message": str(exc),
                },
            },
            sys.stderr,
            ensure_ascii=False,
            sort_keys=True,
        )
        sys.stderr.write("\n")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DesktopShellUnavailable",
    "application_icon_path",
    "browser_candidates",
    "build_parser",
    "check_desktop",
    "default_private_root",
    "desktop_launch_command",
    "main",
    "resolve_browser",
    "run_desktop",
    "self_test_desktop",
]
