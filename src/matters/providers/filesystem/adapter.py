"""Bounded, metadata-first filesystem discovery and tracked content reads.

The adapter deliberately does not own source tracking decisions.  Discovery
returns privacy-sensitive runtime metadata and explicit policy outcomes; a
caller must pass a current ``tracked`` disposition before bytes are read.
"""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import stat as stat_module
from typing import Any

from matters.providers.base import ExternalReference, ProviderEnvelope


TERMINAL_DISCOVERY_OUTCOMES = frozenset(
    {
        "candidate",
        "partition_boundary",
        "hard_excluded",
        "excluded_sensitive",
        "quarantined",
        "inaccessible",
        "unsupported",
        "cloud_placeholder",
    }
)
TEXT_SUFFIXES = frozenset(
    {
        ".txt",
        ".md",
        ".markdown",
        ".rst",
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".c",
        ".cc",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".kts",
        ".scala",
        ".sh",
        ".sql",
        ".json",
        ".jsonl",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".csv",
        ".tsv",
        ".xml",
        ".html",
        ".css",
    }
)
IMAGE_SUFFIXES = frozenset(
    {
        ".bmp",
        ".gif",
        ".jpeg",
        ".jpg",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
    }
)
DOCUMENT_SUFFIXES = frozenset(
    {
        ".doc",
        ".docx",
        ".epub",
        ".odt",
        ".pdf",
        ".ppt",
        ".pptx",
        ".rtf",
        ".tex",
        ".xls",
        ".xlsx",
        *TEXT_SUFFIXES,
    }
)


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _opaque_occurrence_id(relative_path: str) -> str:
    digest = sha256(
        f"filesystem\0file\0{relative_path}".encode("utf-8")
    ).hexdigest()[:24]
    return f"filesystem:{digest}"


@dataclass(frozen=True)
class HardExclusionPolicy:
    """Deterministic exclusions that never require a content read."""

    excluded_directory_names: frozenset[str] = frozenset(
        {
            ".git",
            ".hg",
            ".svn",
            ".ssh",
            ".gnupg",
            ".flowguard",
            ".flowpilot",
            ".skillguard",
            ".playwright-mcp",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".ipynb_checkpoints",
            ".idea",
            ".vscode",
            ".vs",
            ".gradle",
            ".next",
            ".nox",
            ".nuxt",
            ".terraform",
            ".tmp",
            ".tox",
            ".eggs",
            ".venv",
            "__pycache__",
            "bower_components",
            "node_modules",
            "site-packages",
            ".cache",
            "cache",
            "caches",
            "coverage",
            "htmlcov",
            "build",
            "dist",
            "release_artifacts",
            "tmp",
            "temp",
            "matters_home",
            "matters_home_dev",
            "session storage",
            "local storage",
            "venv",
        }
    )
    sensitive_file_names: frozenset[str] = frozenset(
        {
            ".env",
            ".netrc",
            "cookies",
            "cookies.sqlite",
            "login data",
            "credentials",
            "credentials.json",
            "id_rsa",
            "id_ed25519",
        }
    )
    executable_suffixes: frozenset[str] = frozenset(
        {
            ".exe",
            ".dll",
            ".com",
            ".bat",
            ".cmd",
            ".msi",
            ".ps1",
            ".scr",
        }
    )
    unsafe_model_suffixes: frozenset[str] = frozenset(
        {
            ".pkl",
            ".pickle",
            ".joblib",
            ".pt",
            ".pth",
        }
    )

    def classify(
        self,
        relative_path: str,
        *,
        is_directory: bool,
    ) -> tuple[str, str] | None:
        parts = tuple(part.casefold() for part in PurePosixPath(relative_path).parts)
        name = parts[-1] if parts else ""
        if any(part in self.excluded_directory_names for part in parts):
            return "hard_excluded", "policy_excluded_software_or_cache_path"
        if name in self.sensitive_file_names or name.endswith(
            (".pem", ".key", ".pfx", ".p12")
        ):
            return "excluded_sensitive", "credential_or_secret_material"
        suffix = PurePosixPath(relative_path).suffix.casefold()
        if not is_directory and suffix in self.executable_suffixes:
            return "quarantined", "executable_content_not_read"
        if not is_directory and suffix in self.unsafe_model_suffixes:
            return "quarantined", "unsafe_serialized_model_not_loaded"
        return None


@dataclass(frozen=True)
class FilesystemOccurrence:
    occurrence_id: str
    external_id: str
    object_type: str
    outcome: str
    reason: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.outcome not in TERMINAL_DISCOVERY_OUTCOMES:
            raise ValueError(f"unsupported filesystem outcome: {self.outcome}")
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True)
class FilesystemDiscoveryPage:
    items: tuple[FilesystemOccurrence, ...]
    snapshot_fingerprint: str
    next_cursor: str
    terminal: bool
    coverage: str
    gaps: tuple[str, ...] = ()


@dataclass(frozen=True)
class FilesystemReadResult:
    external_id: str
    disposition: str
    envelope: ProviderEnvelope | None = None
    reason: str = ""

    @property
    def ingested(self) -> bool:
        return self.disposition == "ingested" and self.envelope is not None


@dataclass(frozen=True)
class FilesystemBinaryRead:
    external_id: str
    occurrence_id: str
    disposition: str
    content: bytes = b""
    media_type: str = "application/octet-stream"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "content", bytes(self.content))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def ingested(self) -> bool:
        return self.disposition == "ingested" and bool(self.content)


class FilesystemCursorError(ValueError):
    """Raised when a cursor is malformed, foreign, or stale."""


class FilesystemResourceLimit(RuntimeError):
    """Raised when bounded discovery cannot safely continue."""


class FilesystemReadOnlyAdapter:
    """Discover one authorized root and read only explicitly tracked text files."""

    provider_id = "filesystem"

    def __init__(
        self,
        authorized_root: Path,
        *,
        policy: HardExclusionPolicy | None = None,
        page_size: int = 100,
        max_entries: int = 100_000,
        max_depth: int | None = None,
        policy_path_prefix: Sequence[str] = (),
        max_file_bytes: int = 16 * 1024 * 1024,
        scandir: Callable[[Path], Sequence[os.DirEntry[str]]] | None = None,
        lstat: Callable[[Path], os.stat_result] | None = None,
        read_bytes: Callable[[Path], bytes] | None = None,
        resolve: Callable[[Path], Path] | None = None,
        cloud_placeholder_detector: Callable[[Path, os.stat_result], bool]
        | None = None,
    ):
        if page_size < 1 or max_entries < 1 or max_file_bytes < 1:
            raise ValueError("filesystem resource limits must be positive")
        if max_depth is not None and max_depth < 0:
            raise ValueError("max_depth cannot be negative")
        self._resolve = resolve or (lambda path: path.resolve(strict=True))
        self.root = self._resolve(Path(authorized_root))
        if not self.root.is_dir():
            raise ValueError("authorized filesystem root must be a directory")
        self._policy = policy or HardExclusionPolicy()
        self._page_size = page_size
        self._max_entries = max_entries
        self._max_depth = max_depth
        self.policy_path_prefix = tuple(
            str(part).casefold()
            for part in policy_path_prefix
            if str(part) not in {"", "."}
        )
        self._max_file_bytes = max_file_bytes
        self._scandir = scandir or (
            lambda path: tuple(os.scandir(path))
        )
        self._lstat = lstat or (
            lambda path: os.stat(path, follow_symlinks=False)
        )
        self._read_bytes = read_bytes or Path.read_bytes
        self._cloud_placeholder_detector = (
            cloud_placeholder_detector or (lambda _path, _stat: False)
        )
        self._scope_fingerprint = _stable_digest(
            {
                "provider": self.provider_id,
                "root": str(self.root),
                "max_depth": self._max_depth,
                "policy_path_prefix": self.policy_path_prefix,
                "policy": {
                    "directories": sorted(self._policy.excluded_directory_names),
                    "sensitive": sorted(self._policy.sensitive_file_names),
                    "executables": sorted(self._policy.executable_suffixes),
                    "unsafe_models": sorted(self._policy.unsafe_model_suffixes),
                },
            }
        )

    @staticmethod
    def _is_reparse(metadata: os.stat_result) -> bool:
        attributes = int(getattr(metadata, "st_file_attributes", 0))
        reparse_flag = int(
            getattr(stat_module, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        )
        return bool(attributes & reparse_flag)

    def _contained(self, path: Path) -> bool:
        try:
            path.relative_to(self.root)
        except ValueError:
            return False
        return True

    def _relative_id(self, path: Path) -> str:
        if not self._contained(path):
            raise PermissionError("filesystem_scope_escape")
        relative = path.relative_to(self.root).as_posix()
        if relative in {"", "."}:
            raise PermissionError("filesystem_root_is_not_a_file")
        return relative

    def _metadata(
        self,
        relative_id: str,
        raw: os.stat_result,
    ) -> dict[str, Any]:
        identity = {
            "device": int(getattr(raw, "st_dev", 0)),
            "inode": int(getattr(raw, "st_ino", 0)),
        }
        metadata = {
            "relative_path": relative_id,
            "size": int(raw.st_size),
            "modified_ns": int(raw.st_mtime_ns),
            "mode": int(raw.st_mode),
            "file_identity": _stable_digest(identity),
        }
        metadata["metadata_identity"] = _stable_digest(metadata)
        return metadata

    def _scan(self) -> tuple[FilesystemOccurrence, ...]:
        pending = [(self.root, 0)]
        results: list[FilesystemOccurrence] = []
        seen_directories: set[tuple[int, int]] = set()
        while pending:
            directory, depth = pending.pop()
            try:
                raw_directory = self._lstat(directory)
                directory_identity = (
                    int(getattr(raw_directory, "st_dev", 0)),
                    int(getattr(raw_directory, "st_ino", 0)),
                )
                if directory_identity in seen_directories:
                    continue
                seen_directories.add(directory_identity)
                entries = sorted(
                    self._scandir(directory),
                    key=lambda item: item.name.casefold(),
                )
            except OSError:
                if directory == self.root:
                    raise
                relative_id = self._relative_id(directory)
                results.append(
                    FilesystemOccurrence(
                        _opaque_occurrence_id(relative_id),
                        relative_id,
                        "directory",
                        "inaccessible",
                        "directory_metadata_unavailable",
                    )
                )
                continue

            for entry in entries:
                if len(results) >= self._max_entries:
                    raise FilesystemResourceLimit(
                        "filesystem_discovery_entry_budget_exhausted"
                    )
                path = Path(entry.path)
                relative_id = self._relative_id(path)
                try:
                    raw = self._lstat(path)
                except OSError:
                    results.append(
                        FilesystemOccurrence(
                            _opaque_occurrence_id(relative_id),
                            relative_id,
                            "unknown",
                            "inaccessible",
                            "metadata_unavailable",
                        )
                    )
                    continue

                is_link = stat_module.S_ISLNK(raw.st_mode) or self._is_reparse(raw)
                is_directory = stat_module.S_ISDIR(raw.st_mode)
                if is_link:
                    results.append(
                        FilesystemOccurrence(
                            _opaque_occurrence_id(relative_id),
                            relative_id,
                            "link",
                            "hard_excluded",
                            "link_junction_or_reparse_not_followed",
                            self._metadata(relative_id, raw),
                        )
                    )
                    continue

                policy_result = self._policy.classify(
                    relative_id,
                    is_directory=is_directory,
                )
                if policy_result is not None:
                    outcome, reason = policy_result
                    results.append(
                        FilesystemOccurrence(
                            _opaque_occurrence_id(relative_id),
                            relative_id,
                            "directory" if is_directory else "file",
                            outcome,
                            reason,
                            self._metadata(relative_id, raw),
                        )
                    )
                    continue

                if is_directory:
                    if self._max_depth is not None and depth >= self._max_depth:
                        results.append(
                            FilesystemOccurrence(
                                _opaque_occurrence_id(relative_id),
                                relative_id,
                                "directory",
                                "partition_boundary",
                                "covered_by_declared_child_scope",
                                self._metadata(relative_id, raw),
                            )
                        )
                    else:
                        pending.append((path, depth + 1))
                    continue
                if not stat_module.S_ISREG(raw.st_mode):
                    results.append(
                        FilesystemOccurrence(
                            _opaque_occurrence_id(relative_id),
                            relative_id,
                            "special",
                            "unsupported",
                            "non_regular_file_not_read",
                            self._metadata(relative_id, raw),
                        )
                    )
                    continue
                metadata = self._metadata(relative_id, raw)
                if self._cloud_placeholder_detector(path, raw):
                    metadata["hydrated"] = False
                    results.append(
                        FilesystemOccurrence(
                            _opaque_occurrence_id(relative_id),
                            relative_id,
                            "cloud_placeholder",
                            "cloud_placeholder",
                            "stable_content_unavailable",
                            metadata,
                        )
                    )
                else:
                    results.append(
                        FilesystemOccurrence(
                            _opaque_occurrence_id(relative_id),
                            relative_id,
                            "file",
                            "candidate",
                            "metadata_inventory_only",
                            metadata,
                        )
                    )
        return tuple(sorted(results, key=lambda item: item.external_id))

    def partition_children(self) -> tuple[Path, ...]:
        """Return safe immediate child directories for a bounded partition.

        The result never follows links, junctions, reparse points, or
        policy-excluded directories.  Callers persist these private paths in a
        private partition manifest before scanning child scopes.
        """

        children: list[Path] = []
        entries = sorted(
            self._scandir(self.root),
            key=lambda item: item.name.casefold(),
        )
        for entry in entries:
            path = Path(entry.path)
            relative_id = self._relative_id(path)
            try:
                raw = self._lstat(path)
            except OSError:
                continue
            if stat_module.S_ISLNK(raw.st_mode) or self._is_reparse(raw):
                continue
            if not stat_module.S_ISDIR(raw.st_mode):
                continue
            if self._policy.classify(relative_id, is_directory=True) is not None:
                continue
            children.append(path)
        return tuple(children)

    def _encode_cursor(self, *, offset: int, snapshot: str) -> str:
        payload = {
            "version": 1,
            "offset": offset,
            "snapshot": snapshot,
            "scope": self._scope_fingerprint,
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return urlsafe_b64encode(encoded).decode("ascii").rstrip("=")

    def _decode_cursor(self, cursor: str) -> Mapping[str, Any]:
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            payload = json.loads(urlsafe_b64decode(padded).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FilesystemCursorError("filesystem_cursor_malformed") from exc
        if (
            payload.get("version") != 1
            or payload.get("scope") != self._scope_fingerprint
            or not isinstance(payload.get("offset"), int)
            or payload["offset"] < 0
        ):
            raise FilesystemCursorError("filesystem_cursor_outside_scope")
        return payload

    def discover(
        self,
        *,
        cursor: str = "",
        page_size: int | None = None,
    ) -> FilesystemDiscoveryPage:
        """Return one deterministic metadata page without reading file bytes."""

        limit = page_size or self._page_size
        if limit < 1 or limit > self._page_size:
            raise ValueError("page_size exceeds the frozen adapter budget")
        inventory = self._scan()
        snapshot = _stable_digest(
            [
                {
                    "id": item.occurrence_id,
                    "outcome": item.outcome,
                    "metadata_identity": item.metadata.get(
                        "metadata_identity", ""
                    ),
                }
                for item in inventory
            ]
        )
        offset = 0
        if cursor:
            decoded = self._decode_cursor(cursor)
            if decoded.get("snapshot") != snapshot:
                raise FilesystemCursorError("filesystem_cursor_stale")
            offset = int(decoded["offset"])
        if offset > len(inventory):
            raise FilesystemCursorError("filesystem_cursor_offset_invalid")
        items = inventory[offset : offset + limit]
        next_offset = offset + len(items)
        terminal = next_offset >= len(inventory)
        next_cursor = (
            ""
            if terminal
            else self._encode_cursor(offset=next_offset, snapshot=snapshot)
        )
        return FilesystemDiscoveryPage(
            items=items,
            snapshot_fingerprint=snapshot,
            next_cursor=next_cursor,
            terminal=terminal,
            coverage="complete" if terminal else "partial",
        )

    def _validated_file(self, external_id: str) -> tuple[Path, os.stat_result]:
        normalized = PurePosixPath(external_id)
        if (
            not external_id
            or normalized.is_absolute()
            or any(part in {"", ".", ".."} for part in normalized.parts)
        ):
            raise PermissionError("filesystem_scope_escape")
        path = self.root.joinpath(*normalized.parts)
        current = self.root
        for part in normalized.parts:
            current = current / part
            raw = self._lstat(current)
            if stat_module.S_ISLNK(raw.st_mode) or self._is_reparse(raw):
                raise PermissionError("filesystem_link_traversal_forbidden")
        resolved = self._resolve(path)
        if not self._contained(resolved):
            raise PermissionError("filesystem_scope_escape")
        raw = self._lstat(path)
        if not stat_module.S_ISREG(raw.st_mode):
            raise PermissionError("filesystem_regular_file_required")
        return path, raw

    def read_tracked(
        self,
        *,
        object_ids: Sequence[str],
        tracking_dispositions: Mapping[str, str],
        cursor: str = "",
    ) -> tuple[FilesystemReadResult, ...]:
        """Read stable UTF-8 text for items explicitly classified ``tracked``."""

        del cursor  # content reads are object-addressed; discovery owns cursors
        results: list[FilesystemReadResult] = []
        for external_id in tuple(dict.fromkeys(str(item) for item in object_ids)):
            occurrence_id = _opaque_occurrence_id(external_id)
            if (
                tracking_dispositions.get(external_id) != "tracked"
                and tracking_dispositions.get(occurrence_id) != "tracked"
            ):
                results.append(
                    FilesystemReadResult(
                        external_id,
                        "not_read",
                        reason="current_tracked_disposition_required",
                    )
                )
                continue
            try:
                path, before = self._validated_file(external_id)
            except (OSError, PermissionError) as exc:
                results.append(
                    FilesystemReadResult(
                        external_id,
                        "inaccessible",
                        reason=str(exc) or "file_metadata_unavailable",
                    )
                )
                continue
            policy_result = self._policy.classify(
                external_id,
                is_directory=False,
            )
            if policy_result is not None:
                outcome, reason = policy_result
                results.append(
                    FilesystemReadResult(external_id, outcome, reason=reason)
                )
                continue
            if PurePosixPath(external_id).suffix.casefold() not in TEXT_SUFFIXES:
                results.append(
                    FilesystemReadResult(
                        external_id,
                        "unsupported",
                        reason="document_or_image_adapter_required",
                    )
                )
                continue
            if int(before.st_size) > self._max_file_bytes:
                results.append(
                    FilesystemReadResult(
                        external_id,
                        "metadata_only",
                        reason="content_read_budget_exceeded",
                    )
                )
                continue
            try:
                content_bytes = self._read_bytes(path)
                after = self._lstat(path)
            except OSError:
                results.append(
                    FilesystemReadResult(
                        external_id,
                        "inaccessible",
                        reason="content_read_failed",
                    )
                )
                continue
            stability_before = (
                int(getattr(before, "st_dev", 0)),
                int(getattr(before, "st_ino", 0)),
                int(before.st_size),
                int(before.st_mtime_ns),
            )
            stability_after = (
                int(getattr(after, "st_dev", 0)),
                int(getattr(after, "st_ino", 0)),
                int(after.st_size),
                int(after.st_mtime_ns),
            )
            if stability_before != stability_after:
                results.append(
                    FilesystemReadResult(
                        external_id,
                        "changed_during_read",
                        reason="pre_and_post_read_metadata_differ",
                    )
                )
                continue
            try:
                content = content_bytes.decode("utf-8-sig", errors="strict")
            except UnicodeDecodeError:
                results.append(
                    FilesystemReadResult(
                        external_id,
                        "unsupported",
                        reason="utf8_decode_failed",
                    )
                )
                continue
            envelope = ProviderEnvelope(
                provider=self.provider_id,
                external_id=occurrence_id,
                object_type="file",
                payload={
                    "relative_path": external_id,
                    "content": content,
                },
                references=(
                    ExternalReference(
                        self.provider_id,
                        occurrence_id,
                        "file",
                    ),
                ),
                metadata={
                    **self._metadata(external_id, after),
                    "disposition": "ingested",
                    "tracking_disposition": "tracked",
                },
            )
            results.append(
                FilesystemReadResult(
                    external_id,
                    "ingested",
                    envelope=envelope,
                )
            )
        return tuple(results)

    def read_tracked_binary(
        self,
        *,
        object_ids: Sequence[str],
        tracking_dispositions: Mapping[str, str],
    ) -> tuple[FilesystemBinaryRead, ...]:
        """Read stable bytes for tracked document/image adapters only."""

        import mimetypes

        results: list[FilesystemBinaryRead] = []
        for external_id in tuple(dict.fromkeys(str(item) for item in object_ids)):
            occurrence_id = _opaque_occurrence_id(external_id)
            if (
                tracking_dispositions.get(external_id) != "tracked"
                and tracking_dispositions.get(occurrence_id) != "tracked"
            ):
                results.append(
                    FilesystemBinaryRead(
                        external_id,
                        occurrence_id,
                        "not_tracked",
                        reason="current_tracked_disposition_required",
                    )
                )
                continue
            try:
                path, before = self._validated_file(external_id)
            except (OSError, PermissionError) as exc:
                results.append(
                    FilesystemBinaryRead(
                        external_id,
                        occurrence_id,
                        "inaccessible",
                        reason=str(exc) or "file_metadata_unavailable",
                    )
                )
                continue
            policy_result = self._policy.classify(
                external_id,
                is_directory=False,
            )
            if policy_result is not None:
                outcome, reason = policy_result
                results.append(
                    FilesystemBinaryRead(
                        external_id,
                        occurrence_id,
                        outcome,
                        reason=reason,
                    )
                )
                continue
            suffix = PurePosixPath(external_id).suffix.casefold()
            if suffix not in DOCUMENT_SUFFIXES | IMAGE_SUFFIXES:
                results.append(
                    FilesystemBinaryRead(
                        external_id,
                        occurrence_id,
                        "unsupported",
                        reason="document_or_image_suffix_required",
                    )
                )
                continue
            if int(before.st_size) > self._max_file_bytes:
                results.append(
                    FilesystemBinaryRead(
                        external_id,
                        occurrence_id,
                        "metadata_only",
                        reason="content_read_budget_exceeded",
                    )
                )
                continue
            try:
                content = self._read_bytes(path)
                after = self._lstat(path)
            except OSError:
                results.append(
                    FilesystemBinaryRead(
                        external_id,
                        occurrence_id,
                        "inaccessible",
                        reason="content_read_failed",
                    )
                )
                continue
            before_identity = (
                int(getattr(before, "st_dev", 0)),
                int(getattr(before, "st_ino", 0)),
                int(before.st_size),
                int(before.st_mtime_ns),
            )
            after_identity = (
                int(getattr(after, "st_dev", 0)),
                int(getattr(after, "st_ino", 0)),
                int(after.st_size),
                int(after.st_mtime_ns),
            )
            if before_identity != after_identity:
                results.append(
                    FilesystemBinaryRead(
                        external_id,
                        occurrence_id,
                        "changed_during_read",
                        reason="pre_and_post_read_metadata_differ",
                    )
                )
                continue
            media_type = mimetypes.guess_type(external_id)[0] or (
                "image/jpeg" if suffix in {".jpg", ".jpeg"} else
                "application/octet-stream"
            )
            results.append(
                FilesystemBinaryRead(
                    external_id,
                    occurrence_id,
                    "ingested",
                    content=content,
                    media_type=media_type,
                    metadata=self._metadata(external_id, after),
                )
            )
        return tuple(results)

    def read(
        self,
        *,
        object_ids: Sequence[str],
        cursor: str = "",
        tracking_dispositions: Mapping[str, str] | None = None,
    ) -> tuple[ProviderEnvelope, ...]:
        """Provider-protocol projection for callers that already own tracking."""

        if tracking_dispositions is None:
            raise PermissionError("current_tracked_disposition_required")
        results = self.read_tracked(
            object_ids=object_ids,
            tracking_dispositions=tracking_dispositions,
            cursor=cursor,
        )
        blocked = tuple(item for item in results if not item.ingested)
        if blocked:
            reasons = ",".join(
                f"{item.external_id}:{item.disposition}" for item in blocked
            )
            raise PermissionError(f"filesystem_read_not_ingested:{reasons}")
        return tuple(
            item.envelope for item in results if item.envelope is not None
        )


__all__ = [
    "FilesystemBinaryRead",
    "FilesystemCursorError",
    "FilesystemDiscoveryPage",
    "FilesystemOccurrence",
    "FilesystemReadOnlyAdapter",
    "FilesystemReadResult",
    "FilesystemResourceLimit",
    "HardExclusionPolicy",
    "TERMINAL_DISCOVERY_OUTCOMES",
    "TEXT_SUFFIXES",
]
