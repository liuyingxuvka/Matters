"""Build a deterministic, path-safe Windows desktop release archive."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path, PurePosixPath
import zipfile

if __package__:
    from scripts.build_desktop_manifest import verify_manifest
else:  # Direct execution keeps the repository script usable on Windows.
    from build_desktop_manifest import verify_manifest


RELEASE_CONTROL_FILES = (
    "AI-SETUP.md",
    "README.md",
    "desktop-build-toolchain.json",
    "desktop-manifest.json",
)
PRIVATE_BUILD_EVIDENCE = (
    "desktop-self-test.json",
)
_FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
    except ValueError:
        return False
    return True


def _archive_file(
    archive: zipfile.ZipFile,
    path: Path,
    *,
    relative: str,
) -> None:
    info = zipfile.ZipInfo(
        PurePosixPath(relative).as_posix(),
        date_time=_FIXED_ZIP_TIMESTAMP,
    )
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, path.read_bytes())


def build_release_archive(desktop_root: Path, output: Path) -> Path:
    root = desktop_root.resolve(strict=True)
    package_root = (root / "Matters").resolve(strict=True)
    if not package_root.is_dir() or not _within(package_root, root):
        raise ValueError("desktop package root is unavailable or escapes its build root")
    manifest = root / "desktop-manifest.json"
    toolchain = root / "desktop-build-toolchain.json"
    for name in (*RELEASE_CONTROL_FILES, *PRIVATE_BUILD_EVIDENCE):
        if not (root / name).is_file():
            raise ValueError(f"desktop build is missing {name}")
    verified_manifest = verify_manifest(package_root, manifest)
    toolchain_sha256 = "sha256:" + sha256(toolchain.read_bytes()).hexdigest()
    if verified_manifest.build_toolchain_sha256 != toolchain_sha256:
        raise ValueError("desktop build toolchain receipt is stale")
    direct_urls = tuple(package_root.rglob("direct_url.json"))
    if direct_urls:
        raise ValueError("desktop package contains a machine-local direct_url receipt")
    for path in package_root.rglob("*"):
        if path.is_symlink() or (
            hasattr(path, "is_junction") and path.is_junction()
        ):
            raise ValueError("desktop release package contains a link or junction")
        if not _within(path, package_root):
            raise ValueError("desktop release package path escapes its root")

    target = output.resolve(strict=False)
    if _within(target, package_root):
        raise ValueError("desktop release archive must be outside the package tree")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(
            temporary,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for path in sorted(
                (item for item in package_root.rglob("*") if item.is_file()),
                key=lambda item: item.relative_to(package_root).as_posix(),
            ):
                relative = PurePosixPath(
                    path.relative_to(package_root).as_posix()
                )
                _archive_file(
                    archive,
                    path,
                    relative=f"Matters/{relative}",
                )
            for name in RELEASE_CONTROL_FILES:
                _archive_file(archive, root / name, relative=name)
        with zipfile.ZipFile(temporary) as archive:
            observed = {
                row.filename
                for row in archive.infolist()
                if not row.is_dir()
            }
        required = {
            "Matters/Matters.exe",
            *RELEASE_CONTROL_FILES,
        }
        if not required <= observed:
            raise ValueError("desktop release archive is missing required members")
        forbidden = {
            *PRIVATE_BUILD_EVIDENCE,
            *(
                name
                for name in observed
                if PurePosixPath(name).name.casefold() == "direct_url.json"
            ),
        }
        if observed & forbidden:
            raise ValueError("desktop release archive contains private build evidence")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--desktop-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_release_archive(args.desktop_root, args.output)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
