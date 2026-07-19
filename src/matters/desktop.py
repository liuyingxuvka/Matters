"""Windows desktop shell for the local Matters object browser."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from typing import Sequence
from urllib.request import urlopen
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server
from socketserver import ThreadingMixIn

from matters.api.http.static import create_local_application
from matters.runtime import create_service, repository_root


class DesktopShellUnavailable(RuntimeError):
    """Raised when no supported installed desktop web shell is available."""


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
    selected = resolve_browser(browser)
    private_root = default_private_root()
    return {
        "desktop_shell": "available",
        "browser": str(selected),
        "private_root": str(private_root),
        "loopback_only": True,
        "default_locale": "en",
        "available_locales": ["en", "zh-CN"],
    }


def run_desktop(
    *,
    browser: Path | None = None,
    startup_timeout: float = 10.0,
) -> int:
    selected = resolve_browser(browser)
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.check:
            json.dump(
                {"ok": True, "result": check_desktop(browser=args.browser)},
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
    "browser_candidates",
    "build_parser",
    "check_desktop",
    "default_private_root",
    "desktop_launch_command",
    "main",
    "resolve_browser",
    "run_desktop",
]
