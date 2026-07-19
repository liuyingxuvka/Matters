"""Machine-installed consumer skill inventory.

Inventory is supplied as data.  Importing or constructing these objects never
scans, installs, updates, or removes machine skills.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable

from .manifest import InstallationPolicy, SkillManifest, SkillOrigin


@dataclass(frozen=True)
class InstalledSkill:
    manifest: SkillManifest

    def __post_init__(self) -> None:
        if self.manifest.origin != SkillOrigin.MACHINE_INSTALLED:
            raise ValueError("installed inventory entries must use machine_installed origin")
        if self.manifest.installation_policy not in {
            InstallationPolicy.EXTERNALLY_MANAGED,
            InstallationPolicy.MATTERS_MANAGED,
        }:
            raise ValueError("installed inventory entry has an invalid ownership subtype")

    @property
    def matters_managed(self) -> bool:
        return self.manifest.installation_policy == InstallationPolicy.MATTERS_MANAGED

    @property
    def fingerprint(self) -> str:
        return self.manifest.manifest_fingerprint


@dataclass(frozen=True)
class MachineSkillInventory:
    """Frozen inventory snapshot with collisions preserved for the resolver."""

    entries: tuple[InstalledSkill, ...]
    revision: str
    inventory_schema: str = "matters.machine-skill-inventory.v1"

    def __post_init__(self) -> None:
        rows = tuple(
            sorted(
                self.entries,
                key=lambda item: (
                    item.manifest.skill_id,
                    item.manifest.version,
                    item.manifest.content_hash,
                ),
            )
        )
        exact_keys = [
            (
                row.manifest.skill_id,
                row.manifest.version,
                row.manifest.content_hash,
                row.manifest.manifest_fingerprint,
            )
            for row in rows
        ]
        if len(set(exact_keys)) != len(exact_keys):
            raise ValueError("machine inventory contains a duplicate exact candidate")
        object.__setattr__(self, "entries", rows)
        if self.revision != self.calculated_revision:
            raise ValueError("inventory revision does not match its exact entries")

    @classmethod
    def build(cls, entries: Iterable[InstalledSkill]) -> "MachineSkillInventory":
        rows = tuple(entries)
        revision = cls._revision(rows)
        return cls(entries=rows, revision=revision)

    @classmethod
    def empty(cls) -> "MachineSkillInventory":
        return cls.build(())

    @property
    def calculated_revision(self) -> str:
        return self._revision(self.entries)

    def for_skill(self, skill_id: str) -> tuple[InstalledSkill, ...]:
        return tuple(row for row in self.entries if row.manifest.skill_id == skill_id)

    @staticmethod
    def _revision(entries: Iterable[InstalledSkill]) -> str:
        rows = sorted(
            (
                row.manifest.canonical()
                for row in entries
            ),
            key=lambda row: (
                str(row["skill_id"]),
                str(row["version"]),
                str(row["content_hash"]),
            ),
        )
        payload = json.dumps(
            {
                "inventory_schema": "matters.machine-skill-inventory.v1",
                "entries": rows,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + sha256(payload).hexdigest()


__all__ = ["InstalledSkill", "MachineSkillInventory"]
