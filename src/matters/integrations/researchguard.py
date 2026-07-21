"""Validate one frozen ResearchGuard installation without mutating it."""

from __future__ import annotations

from hashlib import sha256
import importlib.metadata
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from matters._version import VERSION
from matters.analysis.operations import ResearchProviderStatus


MEMBERS = ("researchguard", "logicguard", "sourceguard", "traceguard")
RETIRED_SKILLS = (
    "logicguard-source-library",
    "logicguard-structured-artifact",
    "logicguard-model-deepening",
    "logicguard-artifact-synthesis",
    "logicguard-project-library-viewer",
    "traceguard-library",
)
RECEIPT_PATH = Path(__file__).with_name("researchguard_currentness.json")


def _json_digest(value: object, *, prefix: bool = True) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = sha256(encoded).hexdigest()
    return f"sha256:{digest}" if prefix else digest


def _inventory(root: Path) -> dict[str, str]:
    if not root.is_dir():
        raise FileNotFoundError(root)
    rows: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        rows[relative.as_posix()] = sha256(path.read_bytes()).hexdigest()
    return rows


def _receipt_identity(receipt: Mapping[str, Any]) -> str:
    compatibility = receipt.get("compatibility", {})
    return _json_digest(
        {
            "schema_version": receipt.get("schema_version"),
            "source_commit": receipt.get("source", {}).get("commit"),
            "source_fingerprint": receipt.get("source", {}).get("fingerprint"),
            "distribution_version": receipt.get("distribution", {}).get("version"),
            "console_entrypoint": receipt.get("distribution", {}).get(
                "console_entrypoint"
            ),
            "manifest_fingerprint": receipt.get("manifest", {}).get("fingerprint"),
            "matters_specifier": compatibility.get("matters_specifier"),
            "researchguard_specifier": compatibility.get(
                "researchguard_specifier"
            ),
            "researchguard_version": compatibility.get("researchguard_version"),
            "compatibility_status": compatibility.get("status"),
            "native_checks_fingerprint": receipt.get("native_validation", {}).get(
                "checks_fingerprint"
            ),
            "installed_currentness_fingerprint": receipt.get(
                "installed_currentness", {}
            ).get("fingerprint"),
        }
    )


def load_researchguard_receipt(path: Path | None = None) -> dict[str, Any]:
    selected = path or RECEIPT_PATH
    return json.loads(selected.read_text(encoding="utf-8"))


def validate_researchguard_state(
    *,
    receipt: Mapping[str, Any],
    manifest: Mapping[str, Any],
    distribution_version: str,
    console_entrypoints: tuple[str, ...],
    package_fingerprint: str,
    skill_fingerprints: Mapping[str, str],
    retired_residuals: tuple[str, ...],
) -> tuple[str, ...]:
    """Compare exact installed identities with one portable frozen receipt."""

    findings: list[str] = []
    compatibility = receipt.get("compatibility", {})
    if receipt.get("schema_version") != (
        "matters.researchguard-currentness-receipt.v1"
    ):
        findings.append("receipt_schema_mismatch")
    if receipt.get("receipt_id") != _receipt_identity(receipt):
        findings.append("receipt_identity_mismatch")
    if receipt.get("terminal_disposition") != "current":
        findings.append("receipt_not_current")
    if receipt.get("source", {}).get("clean") is not True:
        findings.append("source_not_clean")
    if compatibility.get("status") != "compatible":
        findings.append("compatibility_not_current")
    if receipt.get("native_validation", {}).get("status") != "pass":
        findings.append("native_validation_not_current")
    if receipt.get("installed_currentness", {}).get("status") != "pass":
        findings.append("installed_currentness_not_current")

    expected_version = str(receipt.get("distribution", {}).get("version", ""))
    if compatibility.get("researchguard_version") != expected_version:
        findings.append("researchguard_compatibility_version_mismatch")
    try:
        matters_specifier = SpecifierSet(
            str(compatibility.get("matters_specifier", ""))
        )
        if not matters_specifier.contains(Version(VERSION), prereleases=True):
            findings.append("matters_version_incompatible")
        researchguard_specifier = SpecifierSet(
            str(compatibility.get("researchguard_specifier", ""))
        )
        if not researchguard_specifier.contains(
            Version(expected_version),
            prereleases=True,
        ):
            findings.append("researchguard_version_incompatible")
    except (InvalidSpecifier, InvalidVersion):
        findings.append("compatibility_specifier_invalid")
    if distribution_version != expected_version:
        findings.append("distribution_version_mismatch")
    expected_entrypoint = str(
        receipt.get("distribution", {}).get("console_entrypoint", "")
    )
    if console_entrypoints != (expected_entrypoint,):
        findings.append("console_entrypoint_mismatch")
    if package_fingerprint != receipt.get("distribution", {}).get(
        "package_fingerprint"
    ):
        findings.append("installed_package_mismatch")

    expected_manifest_fingerprint = str(
        receipt.get("manifest", {}).get("fingerprint", "")
    )
    if _json_digest(dict(manifest)) != expected_manifest_fingerprint:
        findings.append("install_manifest_mismatch")
    if manifest.get("schema_version") != receipt.get("manifest", {}).get(
        "schema_version"
    ):
        findings.append("install_manifest_schema_mismatch")
    if manifest.get("source_fingerprint") != receipt.get("source", {}).get(
        "fingerprint"
    ):
        findings.append("source_fingerprint_mismatch")
    if manifest.get("package_fingerprint") != package_fingerprint:
        findings.append("manifest_package_fingerprint_mismatch")

    expected_skill_ids = tuple(receipt.get("skills", {}).get("installed_skill_ids", ()))
    if tuple(sorted(skill_fingerprints)) != tuple(sorted(expected_skill_ids)):
        findings.append("installed_skill_inventory_mismatch")
    expected_skill_fingerprints = receipt.get("skills", {}).get(
        "skill_fingerprints", {}
    )
    if dict(skill_fingerprints) != dict(expected_skill_fingerprints):
        findings.append("installed_skill_fingerprint_mismatch")
    if manifest.get("skill_fingerprints") != dict(skill_fingerprints):
        findings.append("manifest_skill_fingerprint_mismatch")
    if tuple(sorted(retired_residuals)):
        findings.append("retired_skill_residual")
    if tuple(receipt.get("residual_state", {}).get("present", ())) != ():
        findings.append("receipt_residual_state_not_clean")
    return tuple(dict.fromkeys(findings))


def probe_researchguard(
    *,
    codex_home: Path | None = None,
    receipt_path: Path | None = None,
) -> ResearchProviderStatus:
    """Return current only when every frozen and installed identity agrees."""

    try:
        receipt = load_researchguard_receipt(receipt_path)
    except (OSError, ValueError, TypeError):
        return ResearchProviderStatus("researchguard_pending_integration")

    home = (codex_home or (Path.home() / ".codex")).resolve()
    manifest_path = home / "researchguard" / "install-manifest.json"
    active_skill_root = home / "skills"
    if not manifest_path.is_file():
        return ResearchProviderStatus("researchguard_pending_integration")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        distribution = importlib.metadata.distribution("researchguard")
        distribution_version = distribution.version
        console_entrypoints = tuple(
            sorted(
                entry.value
                for entry in distribution.entry_points
                if entry.group == "console_scripts" and entry.name == "researchguard"
            )
        )
        spec = importlib.util.find_spec("researchguard")
        if spec is None or spec.submodule_search_locations is None:
            raise LookupError("researchguard_package_missing")
        package_roots = tuple(Path(item).resolve() for item in spec.submodule_search_locations)
        if len(package_roots) != 1:
            raise LookupError("researchguard_package_ambiguous")
        package_fingerprint = _json_digest(
            _inventory(package_roots[0]),
            prefix=False,
        )
        skill_fingerprints: dict[str, str] = {}
        for member in MEMBERS:
            member_root = active_skill_root / member
            if (member_root / ".skillguard").exists():
                raise LookupError("author_control_residual")
            skill_fingerprints[member] = _json_digest(
                _inventory(member_root),
                prefix=False,
            )
        retired_residuals = tuple(
            skill_id
            for skill_id in RETIRED_SKILLS
            if (active_skill_root / skill_id).exists()
        )
    except (
        FileNotFoundError,
        ImportError,
        importlib.metadata.PackageNotFoundError,
        json.JSONDecodeError,
        LookupError,
        OSError,
        TypeError,
        ValueError,
    ):
        return ResearchProviderStatus("researchguard_blocked")

    findings = validate_researchguard_state(
        receipt=receipt,
        manifest=manifest,
        distribution_version=distribution_version,
        console_entrypoints=console_entrypoints,
        package_fingerprint=package_fingerprint,
        skill_fingerprints=skill_fingerprints,
        retired_residuals=retired_residuals,
    )
    if findings:
        return ResearchProviderStatus("researchguard_blocked")
    return ResearchProviderStatus(
        "current",
        provider_version=distribution_version,
        source_commit=str(receipt["source"]["commit"]),
        portable_receipt_id=str(receipt["receipt_id"]),
    )


__all__ = [
    "load_researchguard_receipt",
    "probe_researchguard",
    "validate_researchguard_state",
]
