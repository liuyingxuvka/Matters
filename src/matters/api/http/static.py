"""Local-only static UI wrapper around the canonical JSON WSGI app."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path
import sys
from typing import Mapping

from matters.api.http.app import MattersHTTP, StartResponse


ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


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

    def __call__(
        self,
        environ: Mapping[str, object],
        start_response: StartResponse,
    ) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/"))
        asset = ASSETS.get(path)
        if method == "GET" and asset is not None:
            filename, media_type = asset
            candidate = (self._ui_root / filename).resolve()
            if candidate.parent != self._ui_root or not candidate.is_file():
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


__all__ = ["LocalUI", "_installed_ui_root", "create_local_application"]
