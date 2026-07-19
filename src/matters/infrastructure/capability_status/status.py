"""Visible private-root and provider capability decisions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CapabilityStatus:
    capability: str
    status: str
    reason: str = ""


def validate_private_root(root: Path, repository_root: Path) -> CapabilityStatus:
    root = root.resolve()
    repository_root = repository_root.resolve()
    if root == repository_root or repository_root in root.parents:
        return CapabilityStatus(
            "private_root",
            "blocked",
            "private root must be outside the public repository",
        )
    if root == repository_root.parent:
        return CapabilityStatus(
            "private_root",
            "blocked",
            "private root cannot contain the public repository",
        )
    return CapabilityStatus("private_root", "active")


__all__ = ["CapabilityStatus", "validate_private_root"]
