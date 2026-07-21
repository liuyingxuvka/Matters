"""Local-only static UI wrapper around the canonical JSON WSGI app."""

from __future__ import annotations

import importlib.metadata
from html.parser import HTMLParser
from pathlib import Path
import sys
from typing import Mapping
from urllib.parse import urlsplit

from matters.api.http.app import MattersHTTP, StartResponse
from matters.assets import asset_path


ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}

PACKAGE_ASSETS = {
    "/matters-icon.png": ("matters-icon.png", "image/png"),
    "/favicon.ico": ("matters.ico", "image/x-icon"),
}


class StaticAssetContractError(RuntimeError):
    """Raised before startup when the document references an unavailable asset."""


class _DocumentAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paths: set[str] = set()

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name not in {"href", "src"} or not value:
                continue
            path = urlsplit(value).path
            if path.startswith("/") and not path.startswith("//"):
                self.paths.add(path)


def validate_static_asset_contract(ui_root: Path) -> tuple[str, ...]:
    """Require every local document asset to have a registered, present owner."""

    selected = ui_root.resolve()
    index = selected / "index.html"
    if not index.is_file():
        raise StaticAssetContractError("Matters UI index is unavailable")
    parser = _DocumentAssetParser()
    parser.feed(index.read_text(encoding="utf-8"))
    failures: list[str] = []
    for path in sorted(parser.paths):
        if path in ASSETS:
            filename, _media_type = ASSETS[path]
            candidate = (selected / filename).resolve()
            if candidate.parent != selected or not candidate.is_file():
                failures.append(f"{path}:ui_file_unavailable")
        elif path in PACKAGE_ASSETS:
            filename, _media_type = PACKAGE_ASSETS[path]
            try:
                asset_path(filename)
            except FileNotFoundError:
                failures.append(f"{path}:package_asset_unavailable")
        else:
            failures.append(f"{path}:route_unregistered")
    if failures:
        raise StaticAssetContractError(
            "Matters UI static asset contract failed: " + ", ".join(failures)
        )
    return tuple(sorted(parser.paths))


def _installed_ui_root() -> Path | None:
    """Resolve wheel data files from the installed distribution record."""

    try:
        distribution = importlib.metadata.distribution("matters")
    except importlib.metadata.PackageNotFoundError:
        return None
    for entry in distribution.files or ():
        normalized = str(entry).replace("\\", "/")
        if normalized.endswith("share/matters/ui/index.html"):
            candidate = Path(distribution.locate_file(entry)).resolve().parent
            if (candidate / "index.html").is_file():
                return candidate
    return None


class LocalUI:
    """Serve a fixed asset allowlist and delegate all API paths."""

    def __init__(self, service: object, ui_root: Path):
        self._api = MattersHTTP(service)
        self._ui_root = ui_root.resolve()
        self._required_asset_paths = validate_static_asset_contract(self._ui_root)

    def __call__(
        self,
        environ: Mapping[str, object],
        start_response: StartResponse,
    ) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/"))
        asset = ASSETS.get(path)
        package_asset = PACKAGE_ASSETS.get(path)
        if method == "GET" and (asset is not None or package_asset is not None):
            if package_asset is not None:
                filename, media_type = package_asset
                candidate = asset_path(filename)
            else:
                assert asset is not None
                filename, media_type = asset
                candidate = (self._ui_root / filename).resolve()
                if candidate.parent != self._ui_root:
                    candidate = self._ui_root / "__unavailable__"
            if not candidate.is_file():
                body = b"Matters UI assets are unavailable."
                start_response(
                    "503 Service Unavailable",
                    [
                        ("Content-Type", "text/plain; charset=utf-8"),
                        ("Content-Length", str(len(body))),
                        ("Cache-Control", "no-store"),
                    ],
                )
                return [body]
            body = candidate.read_bytes()
            start_response(
                "200 OK",
                [
                    ("Content-Type", media_type),
                    ("Content-Length", str(len(body))),
                    ("Cache-Control", "no-store"),
                    ("X-Content-Type-Options", "nosniff"),
                    (
                        "Content-Security-Policy",
                        "default-src 'self'; script-src 'self'; "
                        "style-src 'self'; connect-src 'self'; "
                        "img-src 'self' data:; object-src 'none'; "
                        "base-uri 'none'; frame-ancestors 'none'",
                    ),
                ],
            )
            return [body]
        return self._api(environ, start_response)


def create_local_application(
    service: object,
    *,
    ui_root: Path,
) -> LocalUI:
    selected = ui_root
    if not (selected / "index.html").is_file():
        installed = _installed_ui_root()
        if installed is None:
            prefix_candidate = Path(sys.prefix) / "share" / "matters" / "ui"
            if (prefix_candidate / "index.html").is_file():
                installed = prefix_candidate
        if installed is not None:
            selected = installed
    return LocalUI(service, selected)


__all__ = [
    "ASSETS",
    "PACKAGE_ASSETS",
    "LocalUI",
    "StaticAssetContractError",
    "_installed_ui_root",
    "create_local_application",
    "validate_static_asset_contract",
]
