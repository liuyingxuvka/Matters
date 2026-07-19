"""Immutable consumer Skill Pack manifests and payload identities.

This module owns only auxiliary skill-runtime identity.  It deliberately has
no dependency on Matter, evidence, lifecycle, outcome, or projection owners.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import PurePosixPath
import re
from typing import Iterable, Mapping

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version


_SKILL_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_AUTHOR_CONTROL_NAMES = frozenset(
    {
        ".skillguard",
        "contract-source.json",
        "compiled-contract.json",
        "check-manifest.json",
        "global_registry.json",
        "portfolio.json",
        "receipts",
        "run-store",
        "router-state",
    }
)


class SkillOrigin(StrEnum):
    BUNDLED = "bundled"
    MACHINE_INSTALLED = "machine_installed"


class InstallationPolicy(StrEnum):
    BUNDLED_INTERNAL = "bundled_internal"
    EXTERNALLY_MANAGED = "externally_managed"
    MATTERS_MANAGED = "matters_managed"


def _version(value: str | Version, *, field_name: str) -> Version:
    try:
        return value if isinstance(value, Version) else Version(value)
    except InvalidVersion as exc:
        raise ValueError(f"{field_name} must be a valid PEP 440 version") from exc


def _specifier(value: str | SpecifierSet, *, field_name: str) -> SpecifierSet:
    try:
        return value if isinstance(value, SpecifierSet) else SpecifierSet(value)
    except InvalidSpecifier as exc:
        raise ValueError(f"{field_name} must be a valid PEP 440 specifier set") from exc


def _hash(value: str, *, field_name: str) -> str:
    normalized = value.lower()
    if not _SHA256.fullmatch(normalized):
        raise ValueError(f"{field_name} must be sha256:<64 lowercase hex characters>")
    return normalized


def _identifier(value: str, *, field_name: str) -> str:
    if not value or any(character.isspace() for character in value):
        raise ValueError(f"{field_name} must be a non-empty whitespace-free identity")
    return value


def _string_tuple(values: Iterable[str], *, field_name: str) -> tuple[str, ...]:
    result = tuple(values)
    if any(not item or not isinstance(item, str) for item in result):
        raise ValueError(f"{field_name} must contain non-empty strings")
    if len(set(result)) != len(result):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


@dataclass(frozen=True, order=True)
class ProjectionFile:
    """One immutable relative file in a consumer projection."""

    path: str
    content: bytes

    def __post_init__(self) -> None:
        path = PurePosixPath(self.path)
        if path.is_absolute() or not path.parts or ".." in path.parts or "." in path.parts:
            raise ValueError("projection file paths must be normalized relative POSIX paths")
        if "\\" in self.path or str(path) != self.path:
            raise ValueError("projection file paths must use normalized POSIX separators")
        if any(part.casefold() in _AUTHOR_CONTROL_NAMES for part in path.parts):
            raise ValueError(f"author-side SkillGuard control artifact is forbidden: {self.path}")
        object.__setattr__(self, "content", bytes(self.content))


def projection_content_hash(files: Iterable[ProjectionFile]) -> str:
    """Return the deterministic content identity for a consumer projection."""

    rows = tuple(sorted(files, key=lambda item: item.path))
    if len({row.path for row in rows}) != len(rows):
        raise ValueError("projection file paths must be unique")
    digest = sha256()
    for row in rows:
        digest.update(row.path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(row.content).to_bytes(8, "big"))
        digest.update(row.content)
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


@dataclass(frozen=True)
class SkillDependency:
    skill_id: str
    version_compatibility: SpecifierSet | str
    content_hash: str = ""
    runtime_identity: str = ""

    def __post_init__(self) -> None:
        if not _SKILL_ID.fullmatch(self.skill_id):
            raise ValueError("dependency skill_id must use lowercase kebab-case")
        object.__setattr__(
            self,
            "version_compatibility",
            _specifier(self.version_compatibility, field_name="version_compatibility"),
        )
        if self.content_hash:
            object.__setattr__(
                self,
                "content_hash",
                _hash(self.content_hash, field_name="dependency content_hash"),
            )
        if self.runtime_identity:
            _identifier(self.runtime_identity, field_name="dependency runtime_identity")

    def canonical(self) -> dict[str, object]:
        return {
            "skill_id": self.skill_id,
            "version_compatibility": str(self.version_compatibility),
            "content_hash": self.content_hash,
            "runtime_identity": self.runtime_identity,
        }


@dataclass(frozen=True)
class SkillIdentity:
    skill_id: str
    version: Version
    content_hash: str
    origin: SkillOrigin
    runtime_identity: str
    validator_identity: str
    dependency_fingerprint: str
    researchguard_identity: str = ""

    @property
    def exact_content_key(self) -> tuple[str, Version, str]:
        return self.skill_id, self.version, self.content_hash

    @property
    def fingerprint(self) -> str:
        return _json_hash(
            {
                "skill_id": self.skill_id,
                "version": str(self.version),
                "content_hash": self.content_hash,
                "origin": self.origin.value,
                "runtime_identity": self.runtime_identity,
                "validator_identity": self.validator_identity,
                "dependency_fingerprint": self.dependency_fingerprint,
                "researchguard_identity": self.researchguard_identity,
            }
        )


@dataclass(frozen=True)
class SkillManifest:
    """Exact immutable manifest for one consumer skill candidate."""

    skill_id: str
    version: Version | str
    skill_schema_compatibility: SpecifierSet | str
    matters_compatibility: SpecifierSet | str
    origin: SkillOrigin
    content_hash: str
    required: bool
    installation_policy: InstallationPolicy
    capabilities: tuple[str, ...]
    permissions: tuple[str, ...]
    data_disclosure_policy: str
    dependencies: tuple[SkillDependency, ...]
    runtime_identity: str
    validator_identity: str
    accepts_prereleases: bool = False
    researchguard_identity: str = ""
    manifest_schema: str = "matters.consumer-skill-manifest.v1"

    def __post_init__(self) -> None:
        if not _SKILL_ID.fullmatch(self.skill_id):
            raise ValueError("skill_id must use lowercase kebab-case")
        object.__setattr__(self, "version", _version(self.version, field_name="version"))
        object.__setattr__(
            self,
            "skill_schema_compatibility",
            _specifier(
                self.skill_schema_compatibility,
                field_name="skill_schema_compatibility",
            ),
        )
        object.__setattr__(
            self,
            "matters_compatibility",
            _specifier(self.matters_compatibility, field_name="matters_compatibility"),
        )
        object.__setattr__(self, "content_hash", _hash(self.content_hash, field_name="content_hash"))
        object.__setattr__(
            self,
            "capabilities",
            _string_tuple(self.capabilities, field_name="capabilities"),
        )
        object.__setattr__(
            self,
            "permissions",
            _string_tuple(self.permissions, field_name="permissions"),
        )
        object.__setattr__(self, "dependencies", tuple(self.dependencies))
        if len({dependency.skill_id for dependency in self.dependencies}) != len(self.dependencies):
            raise ValueError("dependencies must contain at most one row per skill_id")
        _identifier(self.data_disclosure_policy, field_name="data_disclosure_policy")
        _identifier(self.runtime_identity, field_name="runtime_identity")
        _identifier(self.validator_identity, field_name="validator_identity")
        if self.researchguard_identity:
            _identifier(self.researchguard_identity, field_name="researchguard_identity")
        if self.origin == SkillOrigin.BUNDLED:
            if self.installation_policy != InstallationPolicy.BUNDLED_INTERNAL:
                raise ValueError("bundled manifests must use bundled_internal installation policy")
        elif self.installation_policy == InstallationPolicy.BUNDLED_INTERNAL:
            raise ValueError("machine-installed manifests cannot use bundled_internal policy")

    @property
    def dependency_fingerprint(self) -> str:
        return _json_hash([dependency.canonical() for dependency in self.dependencies])

    @property
    def identity(self) -> SkillIdentity:
        return SkillIdentity(
            skill_id=self.skill_id,
            version=self.version,
            content_hash=self.content_hash,
            origin=self.origin,
            runtime_identity=self.runtime_identity,
            validator_identity=self.validator_identity,
            dependency_fingerprint=self.dependency_fingerprint,
            researchguard_identity=self.researchguard_identity,
        )

    @property
    def manifest_fingerprint(self) -> str:
        return _json_hash(self.canonical())

    def compatibility_failures(
        self,
        *,
        matters_version: str | Version,
        skill_schema_version: str | Version,
    ) -> tuple[str, ...]:
        matters = _version(matters_version, field_name="matters_version")
        schema = _version(skill_schema_version, field_name="skill_schema_version")
        failures: list[str] = []
        if self.version.is_prerelease and not self.accepts_prereleases:
            failures.append("candidate_prerelease_not_accepted")
        if not self.matters_compatibility.contains(matters, prereleases=True):
            failures.append("matters_version_incompatible")
        if not self.skill_schema_compatibility.contains(schema, prereleases=True):
            failures.append("skill_schema_version_incompatible")
        return tuple(failures)

    def canonical(self) -> dict[str, object]:
        return {
            "manifest_schema": self.manifest_schema,
            "skill_id": self.skill_id,
            "version": str(self.version),
            "skill_schema_compatibility": str(self.skill_schema_compatibility),
            "matters_compatibility": str(self.matters_compatibility),
            "origin": self.origin.value,
            "content_hash": self.content_hash,
            "required": self.required,
            "installation_policy": self.installation_policy.value,
            "capabilities": list(self.capabilities),
            "permissions": list(self.permissions),
            "data_disclosure_policy": self.data_disclosure_policy,
            "dependencies": [dependency.canonical() for dependency in self.dependencies],
            "runtime_identity": self.runtime_identity,
            "validator_identity": self.validator_identity,
            "accepts_prereleases": self.accepts_prereleases,
            "researchguard_identity": self.researchguard_identity,
        }


@dataclass(frozen=True)
class SkillProjection:
    manifest: SkillManifest
    files: tuple[ProjectionFile, ...]

    def __post_init__(self) -> None:
        rows = tuple(sorted(self.files, key=lambda item: item.path))
        if not rows:
            raise ValueError("a skill projection must contain at least one consumer file")
        if len({row.path for row in rows}) != len(rows):
            raise ValueError("projection file paths must be unique")
        if projection_content_hash(rows) != self.manifest.content_hash:
            raise ValueError("manifest content_hash does not match consumer projection bytes")
        object.__setattr__(self, "files", rows)


@dataclass(frozen=True)
class BundleManifest:
    """Immutable identity for the complete app-local consumer Skill Pack."""

    pack_id: str
    pack_version: Version | str
    matters_compatibility: SpecifierSet | str
    skill_schema_version: Version | str
    skills: tuple[SkillManifest, ...]
    bundle_hash: str
    manifest_schema: str = "matters.consumer-skill-pack-manifest.v1"

    def __post_init__(self) -> None:
        _identifier(self.pack_id, field_name="pack_id")
        object.__setattr__(
            self,
            "pack_version",
            _version(self.pack_version, field_name="pack_version"),
        )
        object.__setattr__(
            self,
            "matters_compatibility",
            _specifier(self.matters_compatibility, field_name="matters_compatibility"),
        )
        object.__setattr__(
            self,
            "skill_schema_version",
            _version(self.skill_schema_version, field_name="skill_schema_version"),
        )
        rows = tuple(sorted(self.skills, key=lambda item: item.skill_id))
        if not rows:
            raise ValueError("bundle must contain at least one skill")
        if len({row.skill_id for row in rows}) != len(rows):
            raise ValueError("bundle must contain exactly one manifest per skill_id")
        if any(row.origin != SkillOrigin.BUNDLED for row in rows):
            raise ValueError("bundle manifests must all have bundled origin")
        object.__setattr__(self, "skills", rows)
        object.__setattr__(self, "bundle_hash", _hash(self.bundle_hash, field_name="bundle_hash"))
        if self.bundle_hash != self.calculated_hash:
            raise ValueError("bundle_hash does not match the immutable manifest inventory")

    @classmethod
    def build(
        cls,
        *,
        pack_id: str,
        pack_version: str | Version,
        matters_compatibility: str | SpecifierSet,
        skill_schema_version: str | Version,
        skills: Iterable[SkillManifest],
    ) -> "BundleManifest":
        rows = tuple(skills)
        canonical = cls._canonical_inventory(
            pack_id=pack_id,
            pack_version=_version(pack_version, field_name="pack_version"),
            matters_compatibility=_specifier(
                matters_compatibility,
                field_name="matters_compatibility",
            ),
            skill_schema_version=_version(
                skill_schema_version,
                field_name="skill_schema_version",
            ),
            skills=rows,
        )
        return cls(
            pack_id=pack_id,
            pack_version=pack_version,
            matters_compatibility=matters_compatibility,
            skill_schema_version=skill_schema_version,
            skills=rows,
            bundle_hash=_json_hash(canonical),
        )

    @property
    def calculated_hash(self) -> str:
        return _json_hash(
            self._canonical_inventory(
                pack_id=self.pack_id,
                pack_version=self.pack_version,
                matters_compatibility=self.matters_compatibility,
                skill_schema_version=self.skill_schema_version,
                skills=self.skills,
            )
        )

    @property
    def required_skill_ids(self) -> tuple[str, ...]:
        return tuple(row.skill_id for row in self.skills if row.required)

    def manifest_for(self, skill_id: str) -> SkillManifest:
        for manifest in self.skills:
            if manifest.skill_id == skill_id:
                return manifest
        raise KeyError(skill_id)

    def validate_required_inventory(
        self,
        required_skill_ids: Iterable[str],
    ) -> None:
        expected = frozenset(required_skill_ids)
        actual_required = frozenset(self.required_skill_ids)
        missing = sorted(expected - actual_required)
        unexpected = sorted(actual_required - expected)
        if missing or unexpected:
            raise ValueError(
                "required bundle inventory mismatch:"
                f"missing={','.join(missing) or '-'};"
                f"unexpected={','.join(unexpected) or '-'}"
            )

    @staticmethod
    def _canonical_inventory(
        *,
        pack_id: str,
        pack_version: Version,
        matters_compatibility: SpecifierSet,
        skill_schema_version: Version,
        skills: Iterable[SkillManifest],
    ) -> dict[str, object]:
        return {
            "manifest_schema": "matters.consumer-skill-pack-manifest.v1",
            "pack_id": pack_id,
            "pack_version": str(pack_version),
            "matters_compatibility": str(matters_compatibility),
            "skill_schema_version": str(skill_schema_version),
            "skills": [
                row.canonical()
                for row in sorted(skills, key=lambda item: item.skill_id)
            ],
        }


def _json_hash(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def projection_from_mapping(
    manifest: SkillManifest,
    files: Mapping[str, bytes],
) -> SkillProjection:
    return SkillProjection(
        manifest=manifest,
        files=tuple(ProjectionFile(path=path, content=content) for path, content in files.items()),
    )


__all__ = [
    "BundleManifest",
    "InstallationPolicy",
    "ProjectionFile",
    "SkillDependency",
    "SkillIdentity",
    "SkillManifest",
    "SkillOrigin",
    "SkillProjection",
    "projection_content_hash",
    "projection_from_mapping",
]
