"""Build and verify the external manifest for one frozen desktop package."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from matters._version import VERSION
from matters.bundled_skills.bundle import build_bundle, validate_bundle
from matters.desktop_package import (
    DesktopInstallTransactionPlan,
    DesktopPackageManifest,
    PACKAGED_WINDOWS_WEBVIEW_SHELL,
)

_EXTERNAL_CONTROL_ARTIFACTS = frozenset(
    {
        "desktop-install-plan.json",
        "desktop-manifest.json",
        "desktop-self-test.json",
    }
)


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _is_link_or_junction(path: Path) -> bool:
    return path.is_symlink() or (
        hasattr(os.path, "isjunction") and os.path.isjunction(path)
    )


def _safe_package_root(package_root: Path) -> Path:
    candidate = package_root.absolute()
    if _is_link_or_junction(candidate):
        raise ValueError("desktop package root must not be a link or junction")
    root = candidate.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("desktop package root must be a directory")
    for path in root.rglob("*"):
        if _is_link_or_junction(path):
            raise ValueError("desktop package must not contain links or junctions")
        try:
            path.resolve(strict=True).relative_to(root)
        except ValueError as exc:
            raise ValueError("desktop package path escapes its package root") from exc
    return root


def _require_external_path(
    path: Path,
    *,
    package_root: Path,
    label: str,
    must_exist: bool,
) -> Path:
    resolved = path.resolve(strict=must_exist)
    root = package_root.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError:
        return resolved
    raise ValueError(f"desktop {label} must be external to the package root")


def _tree_sha256(root: Path) -> str:
    rows: list[str] = []
    for path in sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: PurePosixPath(item.relative_to(root).as_posix()).as_posix(),
    ):
        relative = PurePosixPath(path.relative_to(root).as_posix())
        rows.append(f"{relative}\t{_sha256_file(path)[7:]}")
    if not rows:
        raise ValueError("desktop package contains no files")
    return _sha256_bytes("\n".join(rows).encode("utf-8"))


def _unique_file(root: Path, suffix: str) -> Path:
    normalized = PurePosixPath(suffix).as_posix().lower()
    matches = tuple(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.relative_to(root).as_posix().lower().endswith(normalized)
    )
    if len(matches) != 1:
        raise ValueError(
            f"desktop package must contain exactly one {suffix}: {len(matches)}"
        )
    return matches[0]


def _unique_directory(root: Path, suffix: str) -> Path:
    normalized = PurePosixPath(suffix).as_posix().lower()
    matches = tuple(
        path
        for path in root.rglob("*")
        if path.is_dir()
        and path.relative_to(root).as_posix().lower().endswith(normalized)
    )
    if len(matches) != 1:
        raise ValueError(
            f"desktop package must contain exactly one {suffix}: {len(matches)}"
        )
    return matches[0]


def _file_set_sha256(paths: Iterable[Path]) -> str:
    rows = tuple(
        f"{path.name}\t{_sha256_file(path)[7:]}"
        for path in sorted(paths, key=lambda item: item.name)
    )
    if not rows:
        raise ValueError("desktop package file set is empty")
    return _sha256_bytes("\n".join(rows).encode("utf-8"))


def _read_self_test(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload.get("result", {})
    if payload.get("ok") is not True or not isinstance(result, dict):
        raise ValueError("desktop packaged self-test did not pass")
    required_true = (
        "loopback_only",
        "owns_application_window",
        "packaged_ui",
        "private_shell_profile",
        "persists_locale_density_window_state",
        "startup_health_gate",
        "in_shell_recovery_surface",
        "clean_owned_process_shutdown",
    )
    if any(result.get(item) is not True for item in required_true):
        raise ValueError("desktop packaged self-test gates are incomplete")
    if result.get("matters_version") != VERSION:
        raise ValueError("desktop packaged self-test version is stale")
    if result.get("shell_kind") != PACKAGED_WINDOWS_WEBVIEW_SHELL:
        raise ValueError("desktop packaged self-test used the wrong shell")
    locales = result.get("available_locales")
    if (
        not isinstance(locales, list)
        or any(not isinstance(item, str) for item in locales)
        or "en" not in locales
        or "zh-CN" not in locales
    ):
        raise ValueError("desktop packaged self-test locales are incomplete")
    return result


def package_observations(package_root: Path) -> dict[str, str]:
    root = _safe_package_root(package_root)
    embedded_controls = tuple(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name.lower() in _EXTERNAL_CONTROL_ARTIFACTS
    )
    if embedded_controls:
        raise ValueError(
            "desktop package contains an external control artifact"
        )
    executable = root / "Matters.exe"
    if not executable.is_file():
        raise ValueError("desktop package does not contain Matters.exe")
    ui_files = tuple(
        _unique_file(root, suffix)
        for suffix in ("ui/index.html", "ui/styles.css", "ui/app.js")
    )
    icon = _unique_file(root, "matters/assets/matters.ico")
    skill_root = _unique_directory(root, "matters/bundled_skills")
    findings = validate_bundle(skill_root)
    if findings:
        raise ValueError(
            "desktop bundled skill pack is invalid: " + ",".join(findings)
        )
    return {
        "package_sha256": _tree_sha256(root),
        "executable_sha256": _sha256_file(executable),
        "ui_bundle_sha256": _file_set_sha256(ui_files),
        "icon_sha256": _sha256_file(icon),
        "skill_pack_identity": build_bundle(skill_root).bundle_hash,
    }


def build_manifest(
    package_root: Path,
    *,
    self_test: Path,
    toolchain: Path,
) -> DesktopPackageManifest:
    _require_external_path(
        self_test,
        package_root=package_root,
        label="self-test receipt",
        must_exist=True,
    )
    _require_external_path(
        toolchain,
        package_root=package_root,
        label="toolchain receipt",
        must_exist=True,
    )
    observations = package_observations(package_root)
    self_test_result = _read_self_test(self_test)
    manifest = DesktopPackageManifest.create(
        application_id="matters.desktop",
        matters_version=VERSION,
        shell_kind=PACKAGED_WINDOWS_WEBVIEW_SHELL,
        package_sha256=observations["package_sha256"],
        executable_sha256=observations["executable_sha256"],
        build_toolchain_sha256=_sha256_file(toolchain),
        ui_bundle_sha256=observations["ui_bundle_sha256"],
        icon_sha256=observations["icon_sha256"],
        service_contract_identity=f"matters.service.contract:{VERSION}",
        worker_contract_identity=f"matters.worker.contract:{VERSION}",
        skill_pack_identity=observations["skill_pack_identity"],
        available_locales=tuple(self_test_result["available_locales"]),
        loopback_only=self_test_result["loopback_only"],
        owns_application_window=self_test_result["owns_application_window"],
        packaged_ui=self_test_result["packaged_ui"],
        private_shell_profile=self_test_result["private_shell_profile"],
        persists_locale_density_window_state=(
            self_test_result["persists_locale_density_window_state"]
        ),
        startup_health_gate=self_test_result["startup_health_gate"],
        in_shell_recovery_surface=self_test_result["in_shell_recovery_surface"],
        clean_owned_process_shutdown=(
            self_test_result["clean_owned_process_shutdown"]
        ),
    )
    if not manifest.release_ready:
        raise ValueError(
            "desktop manifest release gate is blocked: "
            + ",".join(manifest.release_gate_findings())
        )
    return manifest


def verify_manifest(
    package_root: Path,
    manifest_path: Path,
) -> DesktopPackageManifest:
    _require_external_path(
        manifest_path,
        package_root=package_root,
        label="manifest",
        must_exist=True,
    )
    manifest = DesktopPackageManifest.from_mapping(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )
    observations = package_observations(package_root)
    if manifest.matters_version != VERSION:
        raise ValueError("desktop manifest version is stale")
    for field in (
        "package_sha256",
        "executable_sha256",
        "ui_bundle_sha256",
        "icon_sha256",
        "skill_pack_identity",
    ):
        if getattr(manifest, field) != observations[field]:
            raise ValueError(f"desktop manifest {field} is stale")
    if not manifest.release_ready:
        raise ValueError(
            "desktop manifest release gate is blocked: "
            + ",".join(manifest.release_gate_findings())
        )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--self-test", type=Path)
    parser.add_argument("--toolchain", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--transaction-id", default="")
    parser.add_argument("--prior-install-identity", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    _require_external_path(
        args.manifest,
        package_root=args.package_root,
        label="manifest",
        must_exist=args.verify,
    )
    if args.plan is not None:
        _require_external_path(
            args.plan,
            package_root=args.package_root,
            label="transaction plan",
            must_exist=False,
        )
    if args.verify:
        manifest = verify_manifest(args.package_root, args.manifest)
    else:
        if args.self_test is None:
            raise ValueError("--self-test is required when building a manifest")
        if args.toolchain is None:
            raise ValueError("--toolchain is required when building a manifest")
        manifest = build_manifest(
            args.package_root,
            self_test=args.self_test,
            toolchain=args.toolchain,
        )
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(
                manifest.canonical(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        manifest = verify_manifest(args.package_root, args.manifest)
    result: dict[str, Any] = {
        "manifest": manifest.canonical(),
        "release_ready": manifest.release_ready,
    }
    if args.plan is not None:
        plan = DesktopInstallTransactionPlan.create(
            transaction_id=args.transaction_id,
            candidate=manifest,
            prior_install_identity=args.prior_install_identity,
        )
        args.plan.parent.mkdir(parents=True, exist_ok=True)
        args.plan.write_text(
            json.dumps(
                plan.canonical(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        DesktopInstallTransactionPlan.from_mapping(
            json.loads(args.plan.read_text(encoding="utf-8"))
        )
        result["plan"] = plan.canonical()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
