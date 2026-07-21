"""Explicit, source-in-place Codex workspace and project registration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Iterable, Sequence

from matters.inventory.owners import CandidateScope, InventoryOccurrence
from matters.providers.base import ExternalReference, ProviderEnvelope


def _required(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _opaque_id(kind: str, scope_id: str, private_id: str) -> str:
    value = f"codex\0{scope_id}\0{kind}\0{private_id}".encode("utf-8")
    return f"codex:{kind}:{sha256(value).hexdigest()[:24]}"


_PROJECT_MARKERS = (
    "AGENTS.md",
    "Cargo.lock",
    "Cargo.toml",
    "go.mod",
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "pyproject.toml",
    "requirements.txt",
    "setup.cfg",
    "setup.py",
    "yarn.lock",
)


def _stat_identity(path: Path) -> dict[str, int | str]:
    """Return metadata only; project or marker bytes are never opened."""

    stat = path.stat()
    return {
        "kind": "directory" if path.is_dir() else "file",
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
        "mode": int(stat.st_mode),
    }


def _git_head(root: Path) -> str:
    """Return Git's opaque commit identity without inspecting working files."""

    try:
        completed = subprocess.run(
            (
                "git",
                "-C",
                str(root),
                "rev-parse",
                "--verify",
                "HEAD",
            ),
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    candidate = completed.stdout.strip().lower()
    if completed.returncode != 0 or len(candidate) not in {40, 64}:
        return ""
    if any(character not in "0123456789abcdef" for character in candidate):
        return ""
    return candidate


def refresh_codex_project_reference(
    project: "CodexProjectReference",
) -> "CodexProjectReference":
    """Refresh one bounded source-in-place project fingerprint.

    The observation deliberately does not recurse and does not read project
    bodies.  It is derived only from root metadata, a fixed marker allow-list,
    and the repository's opaque Git HEAD when one is available.
    """

    root = Path(project.source_locator).expanduser()
    try:
        if not root.is_dir():
            raise FileNotFoundError(root)
        root_identity = _stat_identity(root)
        marker_identity = {
            marker: _stat_identity(root / marker)
            for marker in _PROJECT_MARKERS
            if (root / marker).is_file()
        }
        availability = "available"
    except OSError:
        root_identity = {"kind": "unavailable"}
        marker_identity = {}
        availability = "source_unavailable"
    payload = {
        "schema": "matters.codex.project-metadata-fingerprint.v1",
        "availability": availability,
        "root": root_identity,
        "markers": marker_identity,
        "git_head": _git_head(root) if availability == "available" else "",
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return replace(
        project,
        source_fingerprint=f"sha256:{sha256(encoded).hexdigest()}",
        first_recorded_at=project.first_recorded_at,
        availability=availability,
    )


def refresh_codex_project_references(
    projects: Iterable["CodexProjectReference"],
) -> tuple["CodexProjectReference", ...]:
    """Refresh an explicit project set without discovering adjacent paths."""

    return tuple(refresh_codex_project_reference(item) for item in projects)


@dataclass(frozen=True)
class CodexSourceManifest:
    """Frozen, credential-free authority for one local Codex workspace."""

    scope_id: str
    authorization_revision: int
    workspace_id: str
    workspace_name: str
    workspace_locator: str
    active: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "scope_id",
            _required(self.scope_id, "scope_id"),
        )
        object.__setattr__(
            self,
            "workspace_id",
            _required(self.workspace_id, "workspace_id"),
        )
        object.__setattr__(
            self,
            "workspace_name",
            _required(self.workspace_name, "workspace_name"),
        )
        object.__setattr__(
            self,
            "workspace_locator",
            _required(self.workspace_locator, "workspace_locator"),
        )
        if self.authorization_revision < 1:
            raise ValueError("authorization_revision must be positive")


@dataclass(frozen=True)
class CodexProjectReference:
    """One explicitly supplied project pointer; no project bytes are copied."""

    project_id: str
    project_name: str
    source_locator: str
    source_fingerprint: str = ""
    first_recorded_at: str = ""
    availability: str = "available"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "project_id",
            _required(self.project_id, "project_id"),
        )
        object.__setattr__(
            self,
            "project_name",
            _required(self.project_name, "project_name"),
        )
        object.__setattr__(
            self,
            "source_locator",
            _required(self.source_locator, "source_locator"),
        )
        object.__setattr__(
            self,
            "source_fingerprint",
            str(self.source_fingerprint).strip(),
        )
        object.__setattr__(
            self,
            "first_recorded_at",
            str(self.first_recorded_at).strip(),
        )
        object.__setattr__(
            self,
            "availability",
            str(self.availability).strip(),
        )
        if self.availability not in {
            "available",
            "source_unavailable",
        }:
            raise ValueError("unsupported Codex source availability")


@dataclass(frozen=True)
class CodexRegistrationPage:
    """One bounded, deterministic inventory-registration page."""

    occurrences: tuple[InventoryOccurrence, ...]
    total_count: int
    next_cursor: str
    coverage: str


class CodexRegistrationAdapter:
    """Project explicit Codex references into source-in-place inventory rows."""

    provider_id = "codex"

    def __init__(
        self,
        manifest: CodexSourceManifest,
        projects: Iterable[CodexProjectReference],
        *,
        page_size: int = 100,
    ) -> None:
        if page_size < 1 or page_size > 500:
            raise ValueError("Codex registration page size is invalid")
        project_rows = tuple(projects)
        project_ids = tuple(item.project_id for item in project_rows)
        if len(project_ids) != len(set(project_ids)):
            raise ValueError("Codex project ids must be unique")
        self._manifest = manifest
        self._projects = tuple(
            sorted(project_rows, key=lambda item: item.project_id)
        )
        self._page_size = page_size
        project_identity = "\0".join(
            "\0".join(
                (
                    item.project_id,
                    item.project_name,
                    item.source_locator,
                    item.source_fingerprint,
                    item.first_recorded_at,
                    item.availability,
                )
            )
            for item in self._projects
        )
        self._cursor_prefix = sha256(
            (
                f"{manifest.scope_id}\0"
                f"{manifest.authorization_revision}\0"
                f"{manifest.workspace_id}\0"
                f"{project_identity}"
            ).encode("utf-8")
        ).hexdigest()[:16]
        self._registered_occurrences = self._occurrences()
        self._registered_by_id = {
            item.occurrence_id: item
            for item in self._registered_occurrences
        }

    @property
    def manifest(self) -> CodexSourceManifest:
        return self._manifest

    @property
    def projects(self) -> tuple[CodexProjectReference, ...]:
        return self._projects

    def candidate_scope(self) -> CandidateScope:
        """Return the explicit private scope without probing adjacent paths."""

        return CandidateScope(
            scope_id=self._manifest.scope_id,
            revision=self._manifest.authorization_revision,
            provider=self.provider_id,
            root_locator=self._manifest.workspace_locator,
            object_types=("codex_workspace", "codex_project"),
            active=self._manifest.active,
        )

    def discover(self, *, cursor: str = "") -> CodexRegistrationPage:
        """Return a bounded metadata-only page without reading project bodies."""

        if not self._manifest.active:
            return CodexRegistrationPage(
                occurrences=(),
                total_count=0,
                next_cursor="",
                coverage="complete",
            )
        offset = self._parse_cursor(cursor)
        occurrences = self._registered_occurrences
        selected = occurrences[offset : offset + self._page_size]
        next_offset = offset + len(selected)
        return CodexRegistrationPage(
            occurrences=selected,
            total_count=len(occurrences),
            next_cursor=(
                self._cursor(next_offset)
                if next_offset < len(occurrences)
                else ""
            ),
            coverage=(
                "partial" if next_offset < len(occurrences) else "complete"
            ),
        )

    def registered_occurrences(self) -> tuple[InventoryOccurrence, ...]:
        """Return the frozen metadata-only registration set."""

        return self._registered_occurrences if self._manifest.active else ()

    def registered_occurrence(
        self,
        object_id: str,
    ) -> InventoryOccurrence | None:
        """Resolve one registered pointer without scanning all registrations."""

        if not self._manifest.active:
            return None
        return self._registered_by_id.get(str(object_id))

    def _occurrences(self) -> tuple[InventoryOccurrence, ...]:
        workspace_occurrence_id = _opaque_id(
            "workspace",
            self._manifest.scope_id,
            self._manifest.workspace_id,
        )
        workspace = InventoryOccurrence(
            occurrence_id=workspace_occurrence_id,
            provider=self.provider_id,
            object_type="codex_workspace",
            locator=self._manifest.workspace_locator,
            metadata={
                "display_name": self._manifest.workspace_name,
                "workspace_id": self._manifest.workspace_id,
                "workspace_name": self._manifest.workspace_name,
                "source_group_chain": (workspace_occurrence_id,),
                "source_group_labels": (
                    self._manifest.workspace_name,
                ),
                "source_availability": "available",
                "storage_class": "external_original",
                "source_in_place": True,
                "recommended_disposition": "metadata_only",
            },
            discovery_reason="explicit_codex_workspace_registration",
        )
        projects = tuple(
            self._project_occurrence(
                project,
                workspace_occurrence_id=workspace_occurrence_id,
            )
            for project in self._projects
        )
        return (workspace, *projects)

    def _project_occurrence(
        self,
        project: CodexProjectReference,
        *,
        workspace_occurrence_id: str,
    ) -> InventoryOccurrence:
        project_occurrence_id = _opaque_id(
            "project",
            self._manifest.scope_id,
            project.project_id,
        )
        return InventoryOccurrence(
            occurrence_id=project_occurrence_id,
            provider=self.provider_id,
            object_type="codex_project",
            locator=project.source_locator,
            metadata={
                "display_name": project.project_name,
                "project_id": project.project_id,
                "project_name": project.project_name,
                "workspace_id": self._manifest.workspace_id,
                "workspace_name": self._manifest.workspace_name,
                "source_group_chain": (
                    workspace_occurrence_id,
                    project_occurrence_id,
                ),
                "source_group_labels": (
                    self._manifest.workspace_name,
                    project.project_name,
                ),
                "source_availability": project.availability,
                "source_fingerprint": project.source_fingerprint,
                "first_recorded_at": project.first_recorded_at,
                "storage_class": "external_original",
                "source_in_place": True,
                "recommended_disposition": "metadata_only",
            },
            content_identity=project.source_fingerprint,
            discovery_reason="explicit_codex_project_registration",
            parent_occurrence_id=workspace_occurrence_id,
        )

    def _cursor(self, offset: int) -> str:
        return f"{self._cursor_prefix}:{offset}"

    def _parse_cursor(self, cursor: str) -> int:
        if not cursor:
            return 0
        prefix, separator, offset = str(cursor).partition(":")
        if (
            not separator
            or prefix != self._cursor_prefix
            or not offset.isdigit()
        ):
            raise ValueError("Codex registration cursor is invalid")
        parsed = int(offset)
        if parsed < 0 or parsed > len(self._registered_occurrences):
            raise ValueError("Codex registration cursor is outside scope")
        return parsed


class CodexReadOnlyProvider:
    """Read only the already registered Codex metadata envelopes."""

    provider_id = "codex"

    def __init__(self, registration: CodexRegistrationAdapter) -> None:
        self._registration = registration

    def read(
        self,
        *,
        object_ids: Sequence[str],
        cursor: str = "",
    ) -> tuple[ProviderEnvelope, ...]:
        if not self._registration.manifest.active:
            raise PermissionError("Codex source scope is inactive")
        if cursor:
            raise ValueError("Codex metadata reads do not use a cursor")
        requested = tuple(dict.fromkeys(str(item) for item in object_ids))
        selected = tuple(
            self._registration.registered_occurrence(object_id)
            for object_id in requested
        )
        missing = tuple(
            object_id
            for object_id, occurrence in zip(requested, selected)
            if occurrence is None
        )
        if missing:
            raise KeyError("requested Codex object is not registered")
        return tuple(
            self._envelope(occurrence)
            for occurrence in selected
            if occurrence is not None
        )

    @staticmethod
    def _envelope(
        occurrence: InventoryOccurrence,
    ) -> ProviderEnvelope:
        return ProviderEnvelope(
            provider="codex",
            external_id=occurrence.occurrence_id,
            object_type=occurrence.object_type,
            payload={
                "source_in_place": True,
                "storage_class": "external_original",
                "source_fingerprint": str(
                    occurrence.metadata.get("source_fingerprint", "")
                ),
                "availability": str(
                    occurrence.metadata.get(
                        "source_availability",
                        "available",
                    )
                ),
            },
            coverage="complete",
            denied_fields=(
                "content",
                "credentials",
                "session_state",
            ),
            references=(
                ExternalReference(
                    provider="codex",
                    external_id=occurrence.occurrence_id,
                    object_type=occurrence.object_type,
                    locator=occurrence.locator,
                ),
            ),
            metadata={
                "display_name": str(
                    occurrence.metadata.get("display_name", "")
                ),
                "source_group_chain": tuple(
                    occurrence.metadata.get("source_group_chain", ())
                ),
                "source_group_labels": tuple(
                    occurrence.metadata.get("source_group_labels", ())
                ),
            },
        )


__all__ = [
    "CodexProjectReference",
    "CodexReadOnlyProvider",
    "CodexRegistrationAdapter",
    "CodexRegistrationPage",
    "CodexSourceManifest",
    "refresh_codex_project_reference",
    "refresh_codex_project_references",
]
