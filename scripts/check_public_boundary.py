"""Fail closed when a public candidate crosses the Matters privacy boundary."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
from typing import Any, Iterable
from urllib.parse import unquote
import zipfile

try:
    import yaml
except ImportError:  # pragma: no cover - JSON and raw-text scanning remain active.
    yaml = None


SECRET_PATTERNS = (
    re.compile(
        r"(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)"
        r"\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{12,}"
    ),
    re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9_./+=-]{12,}"),
)
EMAIL_ADDRESS_PATTERN = re.compile(
    r"(?i)\b[A-Z0-9._%+-]+@(?P<domain>[A-Z0-9.-]+\.[A-Z]{2,})\b"
)
RESERVED_SYNTHETIC_EMAIL_DOMAINS = (
    "example.com",
    "example.net",
    "example.org",
    "example.test",
    "example.invalid",
)
GMAIL_IDENTIFIER_KEYS = {
    "gmailmessageid",
    "gmailthreadid",
    "messageid",
    "threadid",
}
OPAQUE_GMAIL_IDENTIFIER_PATTERN = re.compile(r"(?i)^[0-9a-f]{12,32}$")
WINDOWS_HOME_PATTERN = re.compile(
    r"(?i)(?:file:(?:/{1,3})?)?[A-Z]:[\\/]+Users[\\/]+[^\\/\s\"'<>]+"
)
POSIX_HOME_PATTERN = re.compile(
    r"(?i)(?:file:(?:/{1,3})?)?/(?:home|Users)/[^/\s\"'<>]+"
)
PORTABLE_ROOT = "repo://"
DESKTOP_LARGE_BINARY_SUFFIXES = frozenset({".dll", ".exe", ".pyd"})
PYWEBVIEW_PORTABLE_HOME_EXAMPLE = "/" + "home" + "/" + "user/file.txt"
BACKSLASH_ESCAPE_PATTERN = re.compile(
    r"\\(?:u(?P<unicode>[0-9a-fA-F]{4})|x(?P<hex>[0-9a-fA-F]{2})|"
    r"(?P<simple>[\\/\"]|[bfnrt]))"
)


def _git_executable() -> str:
    path_git = shutil.which("git.exe")
    candidates = (
        Path(path_git) if path_git else None,
        Path(r"C:\Program Files\Git\cmd\git.exe"),
        Path(r"C:\Program Files\Git\bin\git.exe"),
        Path(r"C:\Program Files (x86)\Git\cmd\git.exe"),
    )
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return str(candidate)
    raise FileNotFoundError("no executable git.exe was found")


def _git_lines(root: Path, *arguments: str) -> tuple[str, ...]:
    result = subprocess.run(
        (_git_executable(), *arguments),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return tuple(
        sorted(
            line.strip().replace("\\", "/")
            for line in result.stdout.splitlines()
            if line.strip()
        )
    )


def _has_head(root: Path) -> bool:
    result = subprocess.run(
        (_git_executable(), "rev-parse", "--verify", "--quiet", "HEAD"),
        cwd=root,
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def _matches(path: str, patterns: Iterable[str]) -> bool:
    path_lower = path.casefold()
    return any(
        fnmatch.fnmatchcase(path_lower, pattern.casefold())
        for pattern in patterns
    )


def _is_link_or_junction(path: Path) -> bool:
    return path.is_symlink() or (
        hasattr(path, "is_junction") and path.is_junction()
    )


def _walk_tree(root: Path, relative_root: str) -> tuple[set[str], set[str]]:
    base = root / relative_root
    files: set[str] = set()
    links: set[str] = set()
    if not base.exists() and not _is_link_or_junction(base):
        return files, links
    if _is_link_or_junction(base):
        return files, {relative_root}
    for current, directory_names, file_names in os.walk(base, followlinks=False):
        current_path = Path(current)
        retained: list[str] = []
        for name in directory_names:
            child = current_path / name
            relative = child.relative_to(root).as_posix()
            if _is_link_or_junction(child):
                links.add(relative)
            else:
                retained.append(name)
        directory_names[:] = retained
        for name in file_names:
            child = current_path / name
            relative = child.relative_to(root).as_posix()
            if _is_link_or_junction(child):
                links.add(relative)
            else:
                files.add(relative)
    return files, links


def _required_inventory(
    root: Path,
    inventory: dict[str, Any],
    *,
    release: bool,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    required = set(inventory["required_singletons"])
    if release:
        required.update(inventory["release_required_singletons"])
    else:
        # Release metadata is optional before the frozen release gate, but once
        # present it is still an admitted public candidate. Keeping it out of
        # the routine inventory would make the same safe file fail routine
        # checks merely because the release phase has started.
        required.update(
            relative
            for relative in inventory["release_required_singletons"]
            if (root / relative).is_file()
        )
    links: set[str] = set()
    for relative_root in inventory["required_trees"]:
        files, tree_links = _walk_tree(root, relative_root)
        required.update(files)
        links.update(tree_links)
    excluded = tuple(inventory["excluded_patterns"])
    excluded_paths = {path for path in required if _matches(path, excluded)}
    required.difference_update(excluded_paths)
    return (
        tuple(sorted(required)),
        tuple(sorted(links)),
        tuple(sorted(excluded_paths)),
    )


def _portable_private_roots(
    root: Path,
    policy: dict[str, Any],
) -> tuple[tuple[str, Path], ...]:
    roots: list[tuple[str, Path]] = []
    for row in policy["external_private_roots"]:
        identifier = str(row["id"])
        private_root = (root / row["relative_path"]).resolve(strict=False)
        roots.append((identifier, private_root))
    return tuple(roots)


def _structured_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _structured_strings(key)
            yield from _structured_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _structured_strings(item)


def _decoded_structures(text: str, suffix: str) -> Iterable[Any]:
    if suffix == ".json":
        try:
            yield json.loads(text)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
    elif suffix in {".yaml", ".yml"} and yaml is not None:
        try:
            yield from yaml.safe_load_all(text)
        except yaml.YAMLError:
            return


def _structured_key_values(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key), item
            yield from _structured_key_values(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _structured_key_values(item)


def _text_variants(text: str) -> tuple[str, ...]:
    variants = {text}
    frontier = {text}
    for _ in range(3):
        expanded: set[str] = set()
        for value in frontier:
            expanded.add(unquote(value))
            expanded.add(html.unescape(value))
            if BACKSLASH_ESCAPE_PATTERN.search(value):
                simple = {
                    "\\": "\\",
                    "/": "/",
                    '"': '"',
                    "b": "\b",
                    "f": "\f",
                    "n": "\n",
                    "r": "\r",
                    "t": "\t",
                }

                def replace_escape(match: re.Match[str]) -> str:
                    if match.group("unicode") is not None:
                        return chr(int(match.group("unicode"), 16))
                    if match.group("hex") is not None:
                        return chr(int(match.group("hex"), 16))
                    return simple[match.group("simple")]

                expanded.add(BACKSLASH_ESCAPE_PATTERN.sub(replace_escape, value))
        expanded.difference_update(variants)
        if not expanded:
            break
        variants.update(expanded)
        frontier = expanded
    return tuple(sorted(variants))


def _identity_markers(private_roots: tuple[tuple[str, Path], ...]) -> tuple[str, ...]:
    markers = {
        str(Path.home()),
        sys.executable,
        *(str(path) for _, path in private_roots),
    }
    hostname = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME")
    if hostname and len(hostname) >= 4:
        markers.add(hostname)
    return tuple(sorted((marker for marker in markers if marker), key=len, reverse=True))


def _scan_text(
    relative: str,
    text: str,
    suffix: str,
    private_roots: tuple[tuple[str, Path], ...],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    variants: set[str] = set()
    documents = tuple(_decoded_structures(text, suffix))
    for candidate in (
        text,
        *(
            structured
            for document in documents
            for structured in _structured_strings(document)
        ),
    ):
        variants.update(_text_variants(candidate))
    markers = _identity_markers(private_roots)
    has_machine_marker = any(
        marker.casefold() in value.casefold()
        for value in variants
        for marker in markers
    )
    has_absolute_home = any(
        WINDOWS_HOME_PATTERN.search(value) or POSIX_HOME_PATTERN.search(value)
        for value in variants
    )
    if has_machine_marker:
        findings.append(
            {
                "code": "machine_local_identity_leak",
                "path": relative,
                "message": "file contains a machine-local identity or path",
            }
        )
    elif has_absolute_home:
        findings.append(
            {
                "code": "absolute_home_path_leak",
                "path": relative,
                "message": "file contains an absolute user-home path",
            }
        )
    if any(pattern.search(value) for pattern in SECRET_PATTERNS for value in variants):
        findings.append(
            {
                "code": "high_confidence_secret_pattern",
                "path": relative,
                "message": "file contains a high-confidence assigned secret",
            }
        )
    if any(
        match.group("domain").casefold()
        not in RESERVED_SYNTHETIC_EMAIL_DOMAINS
        for value in variants
        for match in EMAIL_ADDRESS_PATTERN.finditer(value)
    ):
        findings.append(
            {
                "code": "personal_email_identifier_leak",
                "path": relative,
                "message": "file contains a non-synthetic email address",
            }
        )
    if any(
        re.sub(r"[^a-z0-9]", "", key.casefold()) in GMAIL_IDENTIFIER_KEYS
        and isinstance(value, str)
        and OPAQUE_GMAIL_IDENTIFIER_PATTERN.fullmatch(value.strip())
        for document in documents
        for key, value in _structured_key_values(document)
    ):
        findings.append(
            {
                "code": "gmail_identifier_leak",
                "path": relative,
                "message": "file contains an opaque Gmail message or thread identifier",
            }
        )
    return findings


def _source_fingerprint(root: Path, paths: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(paths):
        path = root / relative
        if not path.is_file() or _is_link_or_junction(path):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _archive_inventory(path: Path) -> tuple[str, tuple[str, ...]]:
    suffixes = "".join(path.suffixes).casefold()
    if path.suffix.casefold() in {".whl", ".zip"}:
        with zipfile.ZipFile(path) as archive:
            links = [
                row.filename
                for row in archive.infolist()
                if ((row.external_attr >> 16) & 0o170000) == 0o120000
            ]
            if links:
                raise ValueError("package archive contains a symbolic link")
            observed = tuple(
                sorted(
                    row.filename.replace("\\", "/")
                    for row in archive.infolist()
                    if not row.is_dir()
                )
            )
            if path.suffix.casefold() == ".whl":
                return "wheel", observed
            desktop_signature = (
                path.name.startswith("Matters-")
                and path.name.endswith("-windows-x64.zip")
            ) or any(
                name == "Matters/Matters.exe"
                or name in {
                    "desktop-build-toolchain.json",
                    "desktop-manifest.json",
                }
                or name.startswith("Matters/")
                for name in observed
            )
            if desktop_signature:
                return "desktop", observed
            raise ValueError("unsupported ZIP package artifact")
    if suffixes.endswith(".tar.gz") or path.suffix.casefold() == ".tar":
        with tarfile.open(path) as archive:
            members = archive.getmembers()
            if any(row.issym() or row.islnk() for row in members):
                raise ValueError("package archive contains a link")
            names = [
                row.name.replace("\\", "/")
                for row in members
                if row.isfile()
            ]
            first_segments = {name.split("/", 1)[0] for name in names}
            if len(first_segments) == 1:
                names = [
                    name.split("/", 1)[1]
                    for name in names
                    if "/" in name
                ]
            return "sdist", tuple(sorted(names))
    raise ValueError(f"unsupported package artifact: {path.name}")


def _scan_archive_text(
    path: Path,
    *,
    kind: str,
    private_roots: tuple[tuple[str, Path], ...],
    max_bytes: int,
) -> list[dict[str, str]]:
    """Scan generated package members without extracting them to the host."""

    findings: list[dict[str, str]] = []

    def scan_member(relative: str, size: int, content: bytes) -> None:
        portable = f"package://{path.name}!/{relative}"
        name_findings = _scan_text(
            portable,
            relative,
            Path(relative).suffix.casefold(),
            private_roots,
        )
        findings.extend(name_findings)
        large_desktop_binary = (
            kind == "desktop"
            and Path(relative).suffix.casefold() in DESKTOP_LARGE_BINARY_SUFFIXES
        )
        if size > max_bytes and not large_desktop_binary:
            findings.append(
                {
                    "code": "package_file_too_large",
                    "path": portable,
                    "message": (
                        f"package member has {size} bytes; maximum is {max_bytes}"
                    ),
                }
            )
            return
        if b"\0" in content:
            return
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return
        scan_text = text
        if (
            kind == "desktop"
            and relative.startswith("Matters/_internal/")
            and relative.casefold().endswith(".dist-info/metadata")
            and not re.match(
                r"^Matters/_internal/matters-[^/]+\.dist-info/METADATA$",
                relative,
                flags=re.IGNORECASE,
            )
        ):
            # Dependency metadata owns public maintainer contact addresses.
            # Strip only those RFC822 header rows; every other path, address,
            # secret, and identifier remains inside the fail-closed scan.
            scan_text = re.sub(
                r"(?im)^(?:author-email|maintainer-email):[^\r\n]*(?:\r?\n|$)",
                "",
                scan_text,
            )
        if relative.casefold().endswith(
            "matters/_internal/webview/platforms/gtk.py"
        ):
            # pywebview documents two portable, non-identity examples. This
            # narrow literal exemption must not admit another /home path.
            scan_text = scan_text.replace(
                PYWEBVIEW_PORTABLE_HOME_EXAMPLE,
                "portable-example",
            )
        for row in _scan_text(
            portable,
            scan_text,
            Path(relative).suffix.casefold(),
            private_roots,
        ):
            findings.append(row)

    suffixes = "".join(path.suffixes).casefold()
    if path.suffix.casefold() in {".whl", ".zip"}:
        with zipfile.ZipFile(path) as archive:
            for row in archive.infolist():
                if row.is_dir():
                    continue
                relative = row.filename.replace("\\", "/")
                content = archive.read(row) if row.file_size <= max_bytes else b""
                scan_member(relative, row.file_size, content)
        return findings
    if suffixes.endswith(".tar.gz") or path.suffix.casefold() == ".tar":
        with tarfile.open(path) as archive:
            members = [row for row in archive.getmembers() if row.isfile()]
            names = [row.name.replace("\\", "/") for row in members]
            first_segments = {name.split("/", 1)[0] for name in names}
            strip_root = len(first_segments) == 1
            for row, name in zip(members, names, strict=True):
                relative = (
                    name.split("/", 1)[1]
                    if strip_root and "/" in name
                    else name
                )
                stream = archive.extractfile(row)
                content = (
                    stream.read()
                    if stream is not None and row.size <= max_bytes
                    else b""
                )
                scan_member(relative, row.size, content)
        return findings
    raise ValueError(f"unsupported package artifact: {path.name}")


def _expected_wheel_paths(
    required: Iterable[str],
    inventory: dict[str, Any],
) -> tuple[str, ...]:
    expected: set[str] = set()
    for row in inventory["package_projection"]:
        pattern = row["source_pattern"]
        source_prefix = row["source_prefix"]
        wheel_prefix = row["wheel_prefix"]
        for relative in required:
            if _matches(relative, (pattern,)) and relative.startswith(source_prefix):
                expected.add(f"{wheel_prefix}{relative[len(source_prefix):]}")
    return tuple(sorted(expected))


def _expected_wheel_data_paths(
    observed: Iterable[str],
    inventory: dict[str, Any],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    metadata_paths = sorted(
        path
        for path in observed
        if path.endswith(".dist-info/METADATA")
    )
    if len(metadata_paths) != 1:
        return (), ("wheel must contain exactly one .dist-info/METADATA file",)
    dist_info_root = metadata_paths[0].removesuffix("/METADATA")
    distribution_root = dist_info_root.removesuffix(".dist-info")
    data_root = f"{distribution_root}.data/data/"
    expected = {
        f"{data_root}{row['wheel_data_path']}"
        for row in inventory.get("wheel_data_projection", ())
    }
    return tuple(sorted(expected)), ()


def _wheel_generated_metadata_paths(observed: Iterable[str]) -> tuple[str, ...]:
    metadata_paths = sorted(
        path
        for path in observed
        if path.endswith(".dist-info/METADATA")
    )
    if len(metadata_paths) != 1:
        return ()
    dist_info_root = metadata_paths[0].removesuffix("/METADATA")
    return tuple(
        sorted(
            {
                f"{dist_info_root}/METADATA",
                f"{dist_info_root}/RECORD",
                f"{dist_info_root}/WHEEL",
                f"{dist_info_root}/entry_points.txt",
                f"{dist_info_root}/licenses/LICENSE",
                f"{dist_info_root}/top_level.txt",
            }
        )
    )


def _sha256_identity(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _desktop_archive_errors(
    artifact: Path,
    observed: Iterable[str],
) -> tuple[str, ...]:
    observed_set = set(observed)
    required = {
        "Matters/Matters.exe",
        "desktop-build-toolchain.json",
        "desktop-manifest.json",
    }
    if not required <= observed_set:
        return ()
    errors: list[str] = []
    with zipfile.ZipFile(artifact) as archive:
        try:
            manifest = json.loads(archive.read("desktop-manifest.json"))
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
            return ("desktop_manifest_invalid_json",)
        if not isinstance(manifest, dict):
            return ("desktop_manifest_invalid_shape",)
        fingerprint = manifest.get("manifest_fingerprint")
        fingerprint_payload = {
            key: value
            for key, value in manifest.items()
            if key != "manifest_fingerprint"
        }
        expected_fingerprint = _sha256_identity(
            json.dumps(
                fingerprint_payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        )
        if fingerprint != expected_fingerprint:
            errors.append("desktop_manifest_fingerprint_stale")
        if manifest.get("application_id") != "matters.desktop":
            errors.append("desktop_application_identity_invalid")
        if manifest.get("shell_kind") != "packaged_windows_webview":
            errors.append("desktop_shell_kind_invalid")
        locales = manifest.get("available_locales")
        if (
            not isinstance(locales, list)
            or any(not isinstance(item, str) for item in locales)
            or not {"en", "zh-CN"} <= set(locales)
        ):
            errors.append("desktop_required_locales_missing")
        for flag in (
            "loopback_only",
            "owns_application_window",
            "packaged_ui",
            "private_shell_profile",
            "persists_locale_density_window_state",
            "startup_health_gate",
            "in_shell_recovery_surface",
            "clean_owned_process_shutdown",
        ):
            if manifest.get(flag) is not True:
                errors.append(f"desktop_{flag}_missing")
        version = manifest.get("matters_version")
        if (
            not isinstance(version, str)
            or artifact.name != f"Matters-{version}-windows-x64.zip"
        ):
            errors.append("desktop_archive_version_identity_mismatch")

        package_rows: list[str] = []
        for name in sorted(
            path for path in observed_set if path.startswith("Matters/")
        ):
            relative = name.removeprefix("Matters/")
            package_rows.append(
                f"{relative}\t{hashlib.sha256(archive.read(name)).hexdigest()}"
            )
        package_sha256 = _sha256_identity(
            "\n".join(package_rows).encode("utf-8")
        )
        if manifest.get("package_sha256") != package_sha256:
            errors.append("desktop_package_sha256_stale")
        executable_sha256 = _sha256_identity(
            archive.read("Matters/Matters.exe")
        )
        if manifest.get("executable_sha256") != executable_sha256:
            errors.append("desktop_executable_sha256_stale")
        toolchain_sha256 = _sha256_identity(
            archive.read("desktop-build-toolchain.json")
        )
        if manifest.get("build_toolchain_sha256") != toolchain_sha256:
            errors.append("desktop_build_toolchain_sha256_stale")
    return tuple(sorted(set(errors)))


def _package_comparison(
    required: tuple[str, ...],
    inventory: dict[str, Any],
    artifacts: Iterable[Path],
    *,
    private_roots: tuple[tuple[str, Path], ...],
    max_bytes: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    package_findings: list[dict[str, str]] = []
    sdist_excluded = tuple(inventory.get("sdist_excluded_patterns", ()))
    package_forbidden = tuple(
        inventory.get("package_forbidden_patterns", ())
    )
    for artifact in artifacts:
        kind, observed = _archive_inventory(artifact)
        package_errors: tuple[str, ...] = ()
        if kind == "wheel":
            projected = _expected_wheel_paths(required, inventory)
            expected_data, package_errors = _expected_wheel_data_paths(
                observed,
                inventory,
            )
            expected = tuple(sorted({*projected, *expected_data}))
            allowed = {
                *expected,
                *_wheel_generated_metadata_paths(observed),
            }
        elif kind == "sdist":
            expected = tuple(
                path
                for path in required
                if not _matches(path, sdist_excluded)
            )
            allowed = {
                *expected,
                "PKG-INFO",
                "setup.cfg",
                "src/matters.egg-info/SOURCES.txt",
            }
        else:
            expected = (
                "Matters/Matters.exe",
                "desktop-build-toolchain.json",
                "desktop-manifest.json",
            )
            allowed = {
                path
                for path in observed
                if path.startswith("Matters/")
            } | {
                "desktop-build-toolchain.json",
                "desktop-manifest.json",
            }
            desktop_forbidden = sorted(
                path
                for path in observed
                if (
                    path == "desktop-self-test.json"
                    or Path(path).name.casefold() == "direct_url.json"
                )
            )
            if desktop_forbidden:
                package_errors = tuple(
                    f"private_desktop_build_artifact:{path}"
                    for path in desktop_forbidden
                )
            package_errors += _desktop_archive_errors(artifact, observed)
        missing = sorted(set(expected) - set(observed))
        unexpected = sorted(set(observed) - allowed)
        forbidden_payload = sorted(
            path for path in observed if _matches(path, package_forbidden)
        )
        artifact_findings = _scan_archive_text(
            artifact,
            kind=kind,
            private_roots=private_roots,
            max_bytes=max_bytes,
        )
        package_findings.extend(artifact_findings)
        rows.append(
            {
                "artifact": f"package://{artifact.name}",
                "kind": kind,
                "status": (
                    "pass"
                    if not missing
                    and not unexpected
                    and not forbidden_payload
                    and not package_errors
                    and not artifact_findings
                    else "fail"
                ),
                "expected_count": len(expected),
                "observed_count": len(observed),
                "missing_required": missing,
                "unexpected_public": unexpected,
                "forbidden_payload": forbidden_payload,
                "package_errors": list(package_errors),
                "privacy_findings": artifact_findings,
            }
        )
    return {
        "status": "not_run" if not rows else (
            "pass" if all(row["status"] == "pass" for row in rows) else "fail"
        ),
        "reason": "no_package_artifact_supplied" if not rows else "",
        "artifacts": rows,
        "privacy_findings": package_findings,
    }


def check(
    root: Path,
    policy_path: Path,
    *,
    clean_clone_root: Path | None = None,
    package_artifacts: Iterable[Path] = (),
    release: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    inventory_path = root / policy["required_public_inventory"]
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    allowed = tuple(policy["allowed_paths"])
    forbidden = tuple(policy["forbidden_paths"])
    max_bytes = int(policy["maximum_public_file_bytes"])
    findings: list[dict[str, str]] = []

    private_roots = _portable_private_roots(root, policy)
    root_dispositions: list[dict[str, str]] = []
    for row, (identifier, private_root) in zip(
        policy["external_private_roots"],
        private_roots,
        strict=True,
    ):
        external = root != private_root and root not in private_root.parents
        if not external:
            findings.append(
                {
                    "code": "private_root_inside_public_repo",
                    "path": f"private://{identifier}",
                    "message": "private root resolves inside the public repository",
                }
            )
        root_dispositions.append(
            {
                "id": identifier,
                "location": f"private://{identifier}",
                "outside_repository": "pass" if external else "fail",
                "acl": row["acl_disposition"],
                "encryption": row["encryption_disposition"],
                "cloud_sync": row["cloud_sync_disposition"],
            }
        )

    required, required_links, fingerprint_exclusions = _required_inventory(
        root,
        inventory,
        release=release,
    )
    required_set = set(required)
    candidates = _git_lines(
        root,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
    )
    candidate_set = set(candidates)
    ignored = _git_lines(root, "ls-files", "--others", "--ignored", "--exclude-standard")
    ignored_set = set(ignored)
    tracked = _git_lines(root, "ls-files", "--cached")
    has_head = _has_head(root)

    for relative in sorted(required_set & ignored_set):
        findings.append(
            {
                "code": "required_public_file_ignored",
                "path": relative,
                "message": "required public file is excluded by Git ignore rules",
            }
        )
    for relative in sorted(candidate_set - required_set):
        findings.append(
            {
                "code": "public_candidate_not_in_required_inventory",
                "path": relative,
                "message": "public candidate is absent from the authoritative inventory",
            }
        )
    for relative in required_links:
        findings.append(
            {
                "code": "required_public_link_forbidden",
                "path": relative,
                "message": "required public inventory contains a symlink or junction",
            }
        )
    for relative in sorted(required_set - candidate_set - ignored_set):
        if not (root / relative).exists():
            findings.append(
                {
                    "code": "required_public_file_missing",
                    "path": relative,
                    "message": "required public inventory entry is missing",
                }
            )

    for relative in candidates:
        path = root / relative
        if _is_link_or_junction(path):
            findings.append(
                {
                    "code": "symbolic_link_or_junction_forbidden",
                    "path": relative,
                    "message": "public candidates must be regular files, not links",
                }
            )
            continue
        try:
            resolved = path.resolve(strict=True)
        except FileNotFoundError:
            findings.append(
                {
                    "code": "candidate_missing",
                    "path": relative,
                    "message": "Git candidate no longer exists",
                }
            )
            continue
        if root != resolved and root not in resolved.parents:
            findings.append(
                {
                    "code": "candidate_escapes_repo",
                    "path": relative,
                    "message": "candidate resolves outside the public repository",
                }
            )
            continue
        if not _matches(relative, allowed):
            findings.append(
                {
                    "code": "path_not_allowlisted",
                    "path": relative,
                    "message": "candidate path is outside the public allowlist",
                }
            )
        if _matches(relative, forbidden):
            findings.append(
                {
                    "code": "forbidden_public_path",
                    "path": relative,
                    "message": "candidate path matches a private or secret class",
                }
            )
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > max_bytes:
            findings.append(
                {
                    "code": "public_file_too_large",
                    "path": relative,
                    "message": f"file has {size} bytes; maximum is {max_bytes}",
                }
            )
            continue
        content = path.read_bytes()
        if b"\0" in content:
            continue
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(
            _scan_text(relative, text, path.suffix.casefold(), private_roots)
        )

    clean_clone: dict[str, Any]
    if clean_clone_root is None:
        clean_clone = {
            "status": "not_available" if not has_head else "not_run",
            "reason": "repository_has_no_commit" if not has_head else "clean_clone_not_supplied",
            "missing_required": [],
        }
    else:
        clone_root = clean_clone_root.resolve()
        observed, clone_links, _ = _required_inventory(
            clone_root,
            inventory,
            release=release,
        )
        missing = sorted(required_set - set(observed))
        unexpected = sorted(set(observed) - required_set)
        clean_clone = {
            "status": (
                "pass"
                if not missing and not unexpected and not clone_links
                else "fail"
            ),
            "reason": "",
            "missing_required": missing,
            "unexpected_public": unexpected,
            "forbidden_links": list(clone_links),
        }
        if clean_clone["status"] == "fail":
            findings.append(
                {
                    "code": "clean_clone_inventory_mismatch",
                    "path": "clone://",
                    "message": "clean clone is missing required files or contains links",
                }
            )

    package = _package_comparison(
        required,
        inventory,
        package_artifacts,
        private_roots=private_roots,
        max_bytes=max_bytes,
    )
    findings.extend(package["privacy_findings"])
    if package["status"] == "fail":
        findings.append(
            {
                "code": "package_inventory_mismatch",
                "path": "package://",
                "message": (
                    "package artifact has missing, unexpected, forbidden, "
                    "or privacy-invalid payload"
                ),
            }
        )

    tracked_missing = sorted(required_set - set(tracked)) if has_head else []
    tracked_unexpected = sorted(set(tracked) - required_set) if has_head else []
    if tracked_missing or tracked_unexpected:
        findings.append(
            {
                "code": "tracked_inventory_missing_required",
                "path": "git://HEAD",
                "message": "committed inventory omits required public files",
            }
        )

    findings = sorted(
        {json.dumps(row, sort_keys=True): row for row in findings}.values(),
        key=lambda row: (row["code"], row["path"]),
    )
    fingerprint_excluded_patterns = tuple(
        inventory.get("fingerprint_excluded_patterns", ())
    )
    fingerprint_excluded_paths = {
        path
        for path in required_set
        if _matches(path, fingerprint_excluded_patterns)
    }
    fingerprint_paths = sorted(
        required_set
        - ignored_set
        - set(required_links)
        - fingerprint_excluded_paths
    )
    return {
        "artifact_type": "matters.public-boundary-check.v2",
        "ok": not findings,
        "root": PORTABLE_ROOT,
        "policy": f"{PORTABLE_ROOT}{policy_path.resolve().relative_to(root).as_posix()}",
        "required_public_inventory": {
            "authority": f"{PORTABLE_ROOT}{inventory_path.relative_to(root).as_posix()}",
            "required_count": len(required),
            "required_fingerprint": _source_fingerprint(root, fingerprint_paths),
            "inventory_excluded_count": len(fingerprint_exclusions),
            "fingerprint_excluded_count": len(fingerprint_excluded_paths),
        },
        "inventories": {
            "workspace": {
                "status": "pass",
                "candidate_count": len(candidates),
                "missing_required": sorted(required_set - candidate_set - ignored_set),
            },
            "ignored": {
                "status": "pass" if not required_set & ignored_set else "fail",
                "required_ignored": sorted(required_set & ignored_set),
            },
            "tracked": {
                "status": "not_available" if not has_head else (
                    "pass" if not tracked_missing else "fail"
                ),
                "reason": "repository_has_no_commit" if not has_head else "",
                "tracked_count": len(tracked),
                "missing_required": tracked_missing,
                "unexpected_public": tracked_unexpected,
            },
            "clean_clone": clean_clone,
            "package": package,
        },
        "private_root_dispositions": root_dispositions,
        "findings": findings,
        "claim_boundary": (
            "This check enforces authoritative required-public inventory "
            "reconciliation, ignored/tracked/package/clean-clone accounting, "
            "missing and unexpected package payload rejection, "
            "package member path and generated-text privacy scanning, "
            "external private-root placement, link and junction rejection, "
            "portable evidence paths, decoded JSON/YAML and encoded-path "
            "scanning, size limits, non-synthetic email and structured opaque "
            "Gmail identifier rejection, and high-confidence secret patterns. "
            "No-commit, clean-clone-not-supplied, package-not-supplied, and "
            "unreviewed ACL/encryption/cloud-sync dispositions remain visible "
            "and are not claimed as passed release evidence."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--policy",
        default="docs/security/public-file-policy.json",
    )
    parser.add_argument("--clean-clone-root")
    parser.add_argument("--package-artifact", action="append", default=[])
    parser.add_argument("--release", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    result = check(
        root,
        root / args.policy,
        clean_clone_root=(
            Path(args.clean_clone_root) if args.clean_clone_root else None
        ),
        package_artifacts=(Path(path) for path in args.package_artifact),
        release=args.release,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
