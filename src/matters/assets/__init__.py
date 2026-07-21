"""Canonical packaged visual assets for Matters."""

from __future__ import annotations

from pathlib import Path


_ASSET_NAMES = frozenset({"matters-icon.png", "matters.ico"})


def asset_path(name: str) -> Path:
    """Return one allowlisted packaged asset as a concrete filesystem path."""

    if name not in _ASSET_NAMES:
        raise ValueError(f"unknown Matters asset: {name}")
    candidate = Path(__file__).resolve().parent / name
    if not candidate.is_file():
        raise FileNotFoundError(f"Matters asset is unavailable: {name}")
    return candidate


__all__ = ["asset_path"]
