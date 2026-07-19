"""Read-only discovery of explicitly declared machine skill candidates."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Iterable, Mapping

from .inventory import InstalledSkill, MachineSkillInventory
from .manifest import (
    BundleManifest,
    InstallationPolicy,
    ProjectionFile,
    SkillDependency,
    SkillManifest,
    SkillOrigin,
    projection_content_hash,
)


_EXTERNAL_MANIFEST = ".matters-consumer-skill.json"
_MANAGED_MARKER = ".matters-managed.json"


@dataclass(frozen=True)
class MachineSkillDiscovery:
    inventory: MachineSkillInventory
    status: str
    inspected_root_count: int
    findings: tuple[str, ...] = ()


def default_codex_skill_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    root = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return (root / "skills").resolve()


def discover_machine_skills(
    bundle: BundleManifest,
    *,
    external_roots: Iterable[Path] = (),
    managed_root: Path | None = None,
) -> MachineSkillDiscovery:
    """Inspect only bundle-declared ids; never enumerate unrelated skills."""

    declared = frozenset(item.skill_id for item in bundle.skills)
    entries: list[InstalledSkill] = []
    findings: list[str] = []
    inspected = 0
    roots = tuple(dict.fromkeys(path.resolve() for path in external_roots))
    for root in roots:
        inspected += 1
        if not root.is_dir():
            continue
        for skill_id in sorted(declared):
            candidate = root / skill_id
            if not candidate.exists():
                continue
            _discover_candidate(
                candidate,
                expected_skill_id=skill_id,
                expected_policy=InstallationPolicy.EXTERNALLY_MANAGED,
                metadata_name=_EXTERNAL_MANIFEST,
                entries=entries,
                findings=findings,
            )
    if managed_root is not None:
        inspected += 1
        root = managed_root.resolve()
        if root.is_dir():
            for skill_id in sorted(declared):
                candidate = root / skill_id / "active"
                if not candidate.exists():
                    continue
                _discover_candidate(
                    candidate,
                    expected_skill_id=skill_id,
                    expected_policy=InstallationPolicy.MATTERS_MANAGED,
                    metadata_name=_MANAGED_MARKER,
                    entries=entries,
                    findings=findings,
                )
    inventory = MachineSkillInventory.build(entries)
    status = "current" if not findings else "partial"
    return MachineSkillDiscovery(
        inventory=inventory,
        status=status,
        inspected_root_count=inspected,
        findings=tuple(sorted(set(findings))),
    )


def _discover_candidate(
    path: Path,
    *,
    expected_skill_id: str,
    expected_policy: InstallationPolicy,
    metadata_name: str,
    entries: list[InstalledSkill],
    findings: list[str],
) -> None:
    finding_prefix = f"{expected_skill_id}:"
    try:
        if path.is_symlink() or not path.is_dir():
            raise ValueError("candidate_root_invalid")
        metadata_path = path / metadata_name
        if not metadata_path.is_file():
            raise ValueError("machine_manifest_missing")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        manifest_payload = metadata.get("manifest")
        if not isinstance(manifest_payload, Mapping):
            raise ValueError("machine_manifest_payload_missing")
        files = _projection_files(path)
        content_hash = projection_content_hash(files)
        if str(manifest_payload.get("content_hash", "")) != content_hash:
            raise ValueError("machine_content_hash_mismatch")
        if str(manifest_payload.get("skill_id", "")) != expected_skill_id:
            raise ValueError("machine_skill_id_mismatch")
        if str(manifest_payload.get("installation_policy", "")) != (
            expected_policy.value
        ):
            raise ValueError("machine_ownership_mismatch")
        manifest = _manifest_from_payload(manifest_payload)
        entries.append(InstalledSkill(manifest))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        findings.append(finding_prefix + str(exc))


def _projection_files(path: Path) -> tuple[ProjectionFile, ...]:
    rows = []
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise ValueError("machine_projection_link_forbidden")
        if not item.is_file():
            continue
        relative = item.relative_to(path).as_posix()
        if (
            item.name in {_EXTERNAL_MANIFEST, _MANAGED_MARKER}
            or "__pycache__" in item.parts
            or item.suffix in {".pyc", ".pyo", ".log"}
            or ".skillguard" in item.parts
        ):
            continue
        rows.append(ProjectionFile(relative, item.read_bytes()))
    if not rows:
        raise ValueError("machine_projection_empty")
    return tuple(rows)


def _manifest_from_payload(payload: Mapping[str, object]) -> SkillManifest:
    dependencies = tuple(
        SkillDependency(
            skill_id=str(item["skill_id"]),
            version_compatibility=str(item["version_compatibility"]),
            content_hash=str(item.get("content_hash", "")),
            runtime_identity=str(item.get("runtime_identity", "")),
        )
        for item in payload.get("dependencies", ())
        if isinstance(item, Mapping)
    )
    return SkillManifest(
        skill_id=str(payload["skill_id"]),
        version=str(payload["version"]),
        skill_schema_compatibility=str(
            payload["skill_schema_compatibility"]
        ),
        matters_compatibility=str(payload["matters_compatibility"]),
        origin=SkillOrigin.MACHINE_INSTALLED,
        content_hash=str(payload["content_hash"]),
        required=bool(payload["required"]),
        installation_policy=InstallationPolicy(
            str(payload["installation_policy"])
        ),
        capabilities=tuple(str(item) for item in payload["capabilities"]),
        permissions=tuple(str(item) for item in payload["permissions"]),
        data_disclosure_policy=str(payload["data_disclosure_policy"]),
        dependencies=dependencies,
        runtime_identity=str(payload["runtime_identity"]),
        validator_identity=str(payload["validator_identity"]),
        accepts_prereleases=bool(payload.get("accepts_prereleases", False)),
        researchguard_identity=str(payload.get("researchguard_identity", "")),
        manifest_schema=str(
            payload.get(
                "manifest_schema",
                "matters.consumer-skill-manifest.v1",
            )
        ),
    )


__all__ = [
    "MachineSkillDiscovery",
    "default_codex_skill_root",
    "discover_machine_skills",
]
