"""Local composition root for installed Matters entrypoints."""

from __future__ import annotations

import os
from pathlib import Path

from matters.application.orchestrator import MatterService
from matters.integrations.researchguard import probe_researchguard


def repository_root() -> Path:
    configured = os.environ.get("MATTERS_REPOSITORY_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "src" / "matters"
        ).is_dir():
            return candidate
    # An installed wheel has no source checkout to discover. Treat the
    # installed package directory as the public code boundary instead of the
    # caller's working directory; otherwise a MATTERS_HOME below the working
    # directory could be incorrectly classified as living inside the public
    # repository.
    return Path(__file__).resolve().parent


def create_service() -> MatterService:
    """Compose exactly one canonical service for a local process."""

    return MatterService(
        repository_root=repository_root(),
        research_status=probe_researchguard(),
    )


__all__ = ["create_service", "repository_root"]
