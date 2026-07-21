from __future__ import annotations

from dataclasses import asdict
import json
import os

import pytest

import matters.providers.codex.adapter as codex_adapter
from matters.application.orchestrator import MatterService
from matters.application.source_workflows import SourceWorkflow
from matters.application.source_group_projection import SourceGroupProjection
from matters.providers.codex import (
    CodexProjectReference,
    CodexReadOnlyProvider,
    CodexRegistrationAdapter,
    CodexSourceManifest,
    refresh_codex_project_reference,
)


PRIVATE_WORKSPACE = r"C:\Synthetic\Private\CodexWorkspace"
PRIVATE_PROJECT_A = r"C:\Synthetic\Private\CodexWorkspace\ProjectA"
PRIVATE_PROJECT_B = r"C:\Synthetic\Private\CodexWorkspace\ProjectB"


def _registration(*, page_size: int = 2) -> CodexRegistrationAdapter:
    return CodexRegistrationAdapter(
        CodexSourceManifest(
            scope_id="scope:codex:synthetic",
            authorization_revision=3,
            workspace_id=PRIVATE_WORKSPACE,
            workspace_name="Personal software projects",
            workspace_locator=PRIVATE_WORKSPACE,
        ),
        (
            CodexProjectReference(
                project_id=PRIVATE_PROJECT_B,
                project_name="Project Beta",
                source_locator=PRIVATE_PROJECT_B,
                source_fingerprint="sha256:beta",
                first_recorded_at="2026-07-19",
            ),
            CodexProjectReference(
                project_id=PRIVATE_PROJECT_A,
                project_name="Project Alpha",
                source_locator=PRIVATE_PROJECT_A,
                source_fingerprint="sha256:alpha",
                first_recorded_at="2026-07-18",
            ),
        ),
        page_size=page_size,
    )


def test_codex_registration_is_bounded_resumable_and_source_in_place() -> None:
    registration = _registration()

    scope = registration.candidate_scope()
    first = registration.discover()
    second = registration.discover(cursor=first.next_cursor)

    assert scope.provider == "codex"
    assert scope.root_locator == PRIVATE_WORKSPACE
    assert scope.object_types == ("codex_workspace", "codex_project")
    assert first.coverage == "partial"
    assert first.total_count == 3
    assert len(first.occurrences) == 2
    assert first.next_cursor
    assert second.coverage == "complete"
    assert second.total_count == 3
    assert len(second.occurrences) == 1
    assert second.next_cursor == ""

    occurrences = (*first.occurrences, *second.occurrences)
    assert [item.object_type for item in occurrences] == [
        "codex_workspace",
        "codex_project",
        "codex_project",
    ]
    assert {item.locator for item in occurrences} == {
        PRIVATE_WORKSPACE,
        PRIVATE_PROJECT_A,
        PRIVATE_PROJECT_B,
    }
    for occurrence in occurrences:
        assert occurrence.metadata["source_in_place"] is True
        assert occurrence.metadata["storage_class"] == "external_original"
        assert (
            occurrence.metadata["recommended_disposition"]
            == "metadata_only"
        )
        assert "content" not in occurrence.metadata
        assert "body" not in occurrence.metadata


def test_codex_registration_rejects_foreign_cursor_and_duplicate_projects() -> None:
    registration = _registration()
    cursor = registration.discover().next_cursor

    with pytest.raises(ValueError, match="cursor"):
        registration.discover(cursor="foreign:2")
    changed_registration = CodexRegistrationAdapter(
        registration.manifest,
        (
            CodexProjectReference(
                project_id=PRIVATE_PROJECT_A,
                project_name="Changed project set",
                source_locator=PRIVATE_PROJECT_A,
            ),
        ),
    )
    with pytest.raises(ValueError, match="cursor"):
        changed_registration.discover(cursor=cursor)
    with pytest.raises(ValueError, match="unique"):
        CodexRegistrationAdapter(
            registration.manifest,
            (
                CodexProjectReference(
                    project_id="same",
                    project_name="First",
                    source_locator=r"C:\Synthetic\First",
                ),
                CodexProjectReference(
                    project_id=" same ",
                    project_name="Second",
                    source_locator=r"C:\Synthetic\Second",
                ),
            ),
        )


def test_codex_source_groups_hide_private_locators_from_projection() -> None:
    registration = _registration(page_size=10)
    occurrences = registration.registered_occurrences()

    projection = SourceGroupProjection.from_occurrences(occurrences)
    page = projection.page(limit=20)
    details = tuple(
        asdict(projection.detail(item.group_id))
        for item in page.items
    )
    rendered = json.dumps(
        {"page": asdict(page), "details": details},
        ensure_ascii=False,
        sort_keys=True,
    )

    assert page.total_count == 3
    assert {item.title for item in page.items} == {
        "Personal software projects",
        "Project Alpha",
        "Project Beta",
    }
    assert PRIVATE_WORKSPACE not in rendered
    assert PRIVATE_PROJECT_A not in rendered
    assert PRIVATE_PROJECT_B not in rendered


def test_codex_read_provider_returns_only_registered_metadata() -> None:
    registration = _registration(page_size=10)
    occurrences = registration.registered_occurrences()
    project = next(
        item for item in occurrences if item.object_type == "codex_project"
    )
    provider = CodexReadOnlyProvider(registration)

    envelope = provider.read(
        object_ids=(project.occurrence_id, project.occurrence_id)
    )[0]

    assert envelope.provider == "codex"
    assert envelope.external_id == project.occurrence_id
    assert envelope.object_type == "codex_project"
    assert envelope.coverage == "complete"
    assert envelope.payload == {
        "source_in_place": True,
        "storage_class": "external_original",
        "source_fingerprint": project.content_identity,
        "availability": "available",
    }
    assert envelope.denied_fields == (
        "content",
        "credentials",
        "session_state",
    )
    assert envelope.references[0].locator == project.locator
    assert "content" not in envelope.payload
    assert "body" not in envelope.payload

    with pytest.raises(KeyError, match="not registered"):
        provider.read(object_ids=("codex:project:unknown",))
    with pytest.raises(ValueError, match="cursor"):
        provider.read(object_ids=(project.occurrence_id,), cursor="1")


def test_inactive_codex_manifest_has_complete_empty_coverage() -> None:
    active = _registration()
    manifest = CodexSourceManifest(
        scope_id=active.manifest.scope_id,
        authorization_revision=active.manifest.authorization_revision + 1,
        workspace_id=active.manifest.workspace_id,
        workspace_name=active.manifest.workspace_name,
        workspace_locator=active.manifest.workspace_locator,
        active=False,
    )
    registration = CodexRegistrationAdapter(
        manifest,
        (
            CodexProjectReference(
                project_id=PRIVATE_PROJECT_A,
                project_name="Project Alpha",
                source_locator=PRIVATE_PROJECT_A,
            ),
        ),
    )

    page = registration.discover()

    assert registration.candidate_scope().active is False
    assert page.coverage == "complete"
    assert page.total_count == 0
    assert page.occurrences == ()
    assert page.next_cursor == ""
    assert registration.registered_occurrences() == ()
    with pytest.raises(PermissionError, match="inactive"):
        CodexReadOnlyProvider(registration).read(
            object_ids=("codex:project:any",)
        )


def test_codex_workflow_registers_metadata_only_without_copying_sources(
    tmp_path,
) -> None:
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    repository.mkdir()
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )
    registration = _registration(page_size=2)

    result = SourceWorkflow(service).run_codex(registration)

    assert result.summary.provider == "codex"
    assert result.summary.discovered == 3
    assert result.summary.metadata_only == 3
    assert result.summary.metadata_registered == 3
    assert result.summary.content_ingested == 0
    assert result.summary.evidence_anchors == 2
    assert result.summary.terminal is True
    source_versions = service.store.list_current("source_version")
    assert len(source_versions) == 3
    assert {item["provider"] for item in source_versions} == {"codex"}
    assert all(
        item["storage_class"] == "external_original"
        for item in source_versions
    )
    assert all(
        "content" not in item["content"] for item in source_versions
    )
    for occurrence in registration.registered_occurrences():
        coverage = service.store.current(
            "object_coverage",
            occurrence.occurrence_id,
        )
        assert coverage["stages"]["source_version"]["status"] == "current"
        assert coverage["stages"]["extraction"]["status"] == "current"
        expected_evidence = (
            "current"
            if occurrence.object_type == "codex_project"
            else "no_finding"
        )
        expected_analysis = (
            "pending"
            if occurrence.object_type == "codex_project"
            else "no_finding"
        )
        assert (
            coverage["stages"]["evidence"]["status"]
            == expected_evidence
        )
        assert (
            coverage["stages"]["analysis"]["status"]
            == expected_analysis
        )


def test_codex_registration_configuration_is_restart_safe(tmp_path) -> None:
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    repository.mkdir()
    registration = _registration(page_size=10)
    first = MatterService(
        repository_root=repository,
        private_root=private,
    )

    initial = first.register_codex_sources(
        manifest=registration.manifest,
        projects=registration.projects,
    )
    restarted = MatterService(
        repository_root=repository,
        private_root=private,
    )
    refreshed = restarted.refresh_registered_codex_sources(
        scope_id=registration.manifest.scope_id,
    )

    assert initial.summary.metadata_registered == 3
    assert initial.summary.evidence_anchors == 2
    assert refreshed.summary.metadata_registered == 3
    assert refreshed.summary.content_ingested == 0
    assert refreshed.summary.evidence_anchors == 2
    config = restarted.store.current(
        "codex_source_configuration",
        registration.manifest.scope_id,
    )
    assert config["storage_policy"] == "source_in_place_metadata_only"
    assert config["content_copied"] is False


def test_codex_refresh_updates_bounded_project_fingerprint_and_keeps_first_seen(
    tmp_path,
) -> None:
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    project_root = tmp_path / "project-a"
    repository.mkdir()
    project_root.mkdir()
    marker = project_root / "pyproject.toml"
    marker.write_text("[project]\nname = 'example'\n", encoding="utf-8")
    body = project_root / "private-notes.txt"
    body.write_text("private body version one", encoding="utf-8")
    manifest = CodexSourceManifest(
        scope_id="scope:codex:fingerprint-refresh",
        authorization_revision=1,
        workspace_id="workspace:test",
        workspace_name="Test projects",
        workspace_locator=str(tmp_path),
    )
    first_seen = "2026-07-18T09:30:00+00:00"
    reference = CodexProjectReference(
        project_id="project:test-a",
        project_name="Project A",
        source_locator=str(project_root),
        source_fingerprint="sha256:stale",
        first_recorded_at=first_seen,
    )
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )
    service.register_codex_sources(
        manifest=manifest,
        projects=(reference,),
    )

    service.refresh_registered_codex_sources(scope_id=manifest.scope_id)
    first_config = service.store.current(
        "codex_source_configuration",
        manifest.scope_id,
    )
    first_project = first_config["projects"][0]
    first_fingerprint = first_project["source_fingerprint"]

    assert first_fingerprint.startswith("sha256:")
    assert len(first_fingerprint) == 71
    assert str(project_root) not in first_fingerprint
    assert first_project["first_recorded_at"] == first_seen
    assert first_project["availability"] == "available"

    # Editing an arbitrary project body is intentionally outside this bounded
    # metadata probe and therefore does not cause content inspection.
    body.write_text("private body version two", encoding="utf-8")
    service.refresh_registered_codex_sources(scope_id=manifest.scope_id)
    unchanged_config = service.store.current(
        "codex_source_configuration",
        manifest.scope_id,
    )
    assert (
        unchanged_config["projects"][0]["source_fingerprint"]
        == first_fingerprint
    )
    assert unchanged_config["projects"][0]["first_recorded_at"] == first_seen

    # Marker metadata is an allowed project-change signal.
    marker_stat = marker.stat()
    os.utime(
        marker,
        ns=(marker_stat.st_atime_ns, marker_stat.st_mtime_ns + 1_000_000_000),
    )
    service.refresh_registered_codex_sources(scope_id=manifest.scope_id)
    changed_config = service.store.current(
        "codex_source_configuration",
        manifest.scope_id,
    )
    assert (
        changed_config["projects"][0]["source_fingerprint"]
        != first_fingerprint
    )
    assert changed_config["projects"][0]["first_recorded_at"] == first_seen


def test_codex_project_fingerprint_marks_missing_source_without_exposing_path(
    tmp_path,
) -> None:
    missing = tmp_path / "missing-private-project"
    first_seen = "2026-07-18"
    refreshed = refresh_codex_project_reference(
        CodexProjectReference(
            project_id="project:missing",
            project_name="Missing project",
            source_locator=str(missing),
            source_fingerprint="sha256:old",
            first_recorded_at=first_seen,
        )
    )

    assert refreshed.availability == "source_unavailable"
    assert refreshed.first_recorded_at == first_seen
    assert refreshed.source_fingerprint.startswith("sha256:")
    assert len(refreshed.source_fingerprint) == 71
    assert str(missing) not in refreshed.source_fingerprint


def test_codex_project_fingerprint_includes_opaque_git_head(
    tmp_path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "git-project"
    project_root.mkdir()
    reference = CodexProjectReference(
        project_id="project:git",
        project_name="Git project",
        source_locator=str(project_root),
        first_recorded_at="2026-07-18",
    )
    monkeypatch.setattr(codex_adapter, "_git_head", lambda _root: "a" * 40)
    first = refresh_codex_project_reference(reference)
    monkeypatch.setattr(codex_adapter, "_git_head", lambda _root: "b" * 40)
    second = refresh_codex_project_reference(reference)

    assert first.source_fingerprint != second.source_fingerprint
    assert first.first_recorded_at == second.first_recorded_at
