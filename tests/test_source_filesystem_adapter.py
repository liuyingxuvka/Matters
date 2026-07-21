from __future__ import annotations

from pathlib import Path

import pytest

from matters.providers.filesystem import (
    FilesystemCursorError,
    FilesystemReadOnlyAdapter,
)


def test_filesystem_discovery_is_metadata_only_deterministic_and_paged(
    tmp_path: Path,
):
    (tmp_path / "z.txt").write_text("z", encoding="utf-8")
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.py").write_text("b", encoding="utf-8")
    content_reads: list[Path] = []

    def forbidden_read(path: Path) -> bytes:
        content_reads.append(path)
        raise AssertionError("metadata discovery read file content")

    adapter = FilesystemReadOnlyAdapter(
        tmp_path,
        page_size=2,
        read_bytes=forbidden_read,
    )
    first = adapter.discover()
    retry = adapter.discover()
    second = adapter.discover(cursor=first.next_cursor)

    assert [item.external_id for item in first.items] == ["a.md", "nested/b.py"]
    assert first.items[0].outcome == "candidate"
    assert first.items[1].outcome == "hard_excluded"
    assert first.items[1].reason == "software_source_not_user_content"
    assert first == retry
    assert not first.terminal
    assert first.coverage == "partial"
    assert [item.external_id for item in second.items] == ["z.txt"]
    assert second.terminal
    assert second.coverage == "complete"
    assert content_reads == []


def test_filesystem_classifies_software_artifacts_before_content_ai_and_groups_files(
    tmp_path: Path,
):
    user_folder = tmp_path / "Trip" / "Bookings"
    user_folder.mkdir(parents=True)
    (user_folder / "hotel.docx").write_bytes(b"synthetic")
    (user_folder / "notes.md").write_text("Travel notes", encoding="utf-8")
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("print('x')", encoding="utf-8")
    (project / "pyproject.toml").write_text("[project]", encoding="utf-8")
    (project / "runtime.sqlite3").write_bytes(b"synthetic")

    page = FilesystemReadOnlyAdapter(tmp_path).discover()
    by_id = {item.external_id: item for item in page.items}

    assert by_id["Trip/Bookings/hotel.docx"].outcome == "candidate"
    assert by_id["Trip/Bookings/notes.md"].outcome == "candidate"
    assert by_id["project/main.py"].reason == "software_source_not_user_content"
    assert by_id["project/pyproject.toml"].reason == (
        "software_manifest_not_user_content"
    )
    assert by_id["project/runtime.sqlite3"].reason == (
        "software_internal_record_not_user_content"
    )
    hotel = by_id["Trip/Bookings/hotel.docx"].metadata
    notes = by_id["Trip/Bookings/notes.md"].metadata
    assert hotel["source_neighborhood_id"] == notes["source_neighborhood_id"]
    assert hotel["parent_relative_path"] == "Trip/Bookings"
    assert hotel["source_group_chain"]
    assert hotel["source_group_labels"] == ("Trip", "Bookings")


def test_filesystem_hard_blocks_unknown_files_and_software_config_without_ai(
    tmp_path: Path,
):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    (project / "settings.json").write_text("{}", encoding="utf-8")
    (project / "notes.md").write_text("Human plan", encoding="utf-8")
    (tmp_path / "opaque.bin").write_bytes(b"\x00\x01")
    (tmp_path / "video.mp4").write_bytes(b"synthetic")
    reads: list[Path] = []

    def forbidden_read(path: Path) -> bytes:
        reads.append(path)
        raise AssertionError("deterministic admission read content")

    page = FilesystemReadOnlyAdapter(
        tmp_path,
        read_bytes=forbidden_read,
    ).discover()
    by_id = {item.external_id: item for item in page.items}

    assert by_id["project/settings.json"].outcome == "hard_excluded"
    assert by_id["project/settings.json"].reason == (
        "software_config_not_user_content"
    )
    assert by_id["project/notes.md"].outcome == "candidate"
    assert by_id["project/notes.md"].metadata["software_tree"] is True
    assert by_id["opaque.bin"].outcome == "hard_excluded"
    assert by_id["opaque.bin"].reason == (
        "unknown_or_machine_file_format_not_read"
    )
    assert by_id["video.mp4"].outcome == "unsupported"
    assert reads == []


def test_filesystem_keeps_safe_message_exports_but_blocks_application_state(
    tmp_path: Path,
):
    downloads = tmp_path / "Messaging Downloads"
    downloads.mkdir()
    (downloads / "trip-plan.docx").write_bytes(b"synthetic")
    (downloads / "chat-export.json").write_text(
        '{"messages": [{"text": "Book the hotel"}]}',
        encoding="utf-8",
    )
    application_state = tmp_path / "Messaging App"
    application_state.mkdir()
    (application_state / "messages.sqlite3").write_bytes(b"synthetic")
    (application_state / "runtime.log").write_text(
        "internal",
        encoding="utf-8",
    )

    page = FilesystemReadOnlyAdapter(tmp_path).discover()
    by_id = {item.external_id: item for item in page.items}

    assert by_id["Messaging Downloads/trip-plan.docx"].outcome == "candidate"
    assert by_id["Messaging Downloads/chat-export.json"].outcome == "candidate"
    assert by_id["Messaging App/messages.sqlite3"].outcome == "hard_excluded"
    assert by_id["Messaging App/messages.sqlite3"].reason == (
        "software_internal_record_not_user_content"
    )
    assert by_id["Messaging App/runtime.log"].outcome == "hard_excluded"
    assert by_id["Messaging App/runtime.log"].reason == (
        "software_internal_record_not_user_content"
    )


def test_filesystem_spatial_context_is_stable_across_partition_boundaries(
    tmp_path: Path,
):
    bookings = tmp_path / "Trip" / "Bookings"
    bookings.mkdir(parents=True)
    (bookings / "hotel.txt").write_text("Hotel", encoding="utf-8")

    whole = FilesystemReadOnlyAdapter(tmp_path).discover()
    whole_item = next(
        item for item in whole.items if item.external_id == "Trip/Bookings/hotel.txt"
    )
    partition = FilesystemReadOnlyAdapter(
        bookings,
        policy_path_prefix=("Trip", "Bookings"),
    ).discover()
    partition_item = next(
        item for item in partition.items if item.external_id == "hotel.txt"
    )

    assert (
        whole_item.metadata["source_neighborhood_id"]
        == partition_item.metadata["source_neighborhood_id"]
    )
    assert (
        whole_item.metadata["source_group_chain"]
        == partition_item.metadata["source_group_chain"]
    )
    assert partition_item.metadata["source_group_labels"] == (
        "Trip",
        "Bookings",
    )


def test_filesystem_cursor_stales_when_inventory_changes(tmp_path: Path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    adapter = FilesystemReadOnlyAdapter(tmp_path, page_size=1)
    first = adapter.discover()

    (tmp_path / "c.txt").write_text("c", encoding="utf-8")

    with pytest.raises(FilesystemCursorError, match="cursor_stale"):
        adapter.discover(cursor=first.next_cursor)


def test_filesystem_hard_exclusions_and_scope_escape_never_read_content(
    tmp_path: Path,
):
    vcs = tmp_path / ".git"
    vcs.mkdir()
    (vcs / "config").write_text("synthetic", encoding="utf-8")
    (tmp_path / ".env").write_text("SYNTHETIC=1", encoding="utf-8")
    (tmp_path / "run.exe").write_bytes(b"synthetic")
    reads: list[Path] = []

    def record_read(path: Path) -> bytes:
        reads.append(path)
        return path.read_bytes()

    adapter = FilesystemReadOnlyAdapter(tmp_path, read_bytes=record_read)
    page = adapter.discover()
    outcomes = {item.external_id: item.outcome for item in page.items}

    assert outcomes[".git"] == "hard_excluded"
    assert outcomes[".env"] == "excluded_sensitive"
    assert outcomes["run.exe"] == "quarantined"
    escaped = adapter.read_tracked(
        object_ids=("../outside.txt",),
        tracking_dispositions={"../outside.txt": "tracked"},
    )
    assert escaped[0].disposition == "inaccessible"
    assert reads == []


def test_filesystem_content_requires_tracking_and_detects_read_time_change(
    tmp_path: Path,
):
    source = tmp_path / "note.txt"
    source.write_text("before", encoding="utf-8")

    def changing_read(path: Path) -> bytes:
        original = path.read_bytes()
        path.write_text("after and longer", encoding="utf-8")
        return original

    adapter = FilesystemReadOnlyAdapter(tmp_path, read_bytes=changing_read)
    not_read = adapter.read_tracked(
        object_ids=("note.txt",),
        tracking_dispositions={"note.txt": "metadata_only"},
    )
    changed = adapter.read_tracked(
        object_ids=("note.txt",),
        tracking_dispositions={"note.txt": "tracked"},
    )

    assert not_read[0].disposition == "not_read"
    assert not_read[0].reason == "current_tracked_disposition_required"
    assert not_read[0].envelope is None
    assert changed[0].disposition == "changed_during_read"
    assert changed[0].envelope is None


def test_filesystem_stable_tracked_text_returns_private_relative_envelope(
    tmp_path: Path,
):
    (tmp_path / "note.md").write_text("synthetic note", encoding="utf-8")
    adapter = FilesystemReadOnlyAdapter(tmp_path)
    result = adapter.read_tracked(
        object_ids=("note.md",),
        tracking_dispositions={"note.md": "tracked"},
    )[0]

    assert result.ingested
    assert result.envelope is not None
    assert result.envelope.payload["relative_path"] == "note.md"
    assert result.envelope.payload["content"] == "synthetic note"
    assert str(tmp_path) not in repr(result.envelope)


def test_filesystem_depth_partition_records_safe_child_boundaries(tmp_path: Path):
    (tmp_path / "direct.txt").write_text("direct", encoding="utf-8")
    included = tmp_path / "included"
    included.mkdir()
    (included / "nested.txt").write_text("nested", encoding="utf-8")
    excluded = tmp_path / ".git"
    excluded.mkdir()
    (excluded / "config").write_text("synthetic", encoding="utf-8")

    adapter = FilesystemReadOnlyAdapter(
        tmp_path,
        page_size=10,
        max_entries=10,
        max_depth=0,
    )
    page = adapter.discover()
    by_id = {item.external_id: item for item in page.items}

    assert page.terminal
    assert by_id["direct.txt"].outcome == "candidate"
    assert by_id["included"].outcome == "partition_boundary"
    assert by_id["included"].reason == "covered_by_declared_child_scope"
    assert by_id[".git"].outcome == "hard_excluded"
    assert adapter.partition_children() == (included,)


def test_filesystem_partition_prunes_generated_software_state_before_descent(
    tmp_path: Path,
):
    included = tmp_path / "user-work"
    included.mkdir()
    (included / "note.md").write_text("synthetic note", encoding="utf-8")
    generated_names = (
        ".flowpilot",
        ".skillguard",
        ".playwright-mcp",
        "tmp",
        "site-packages",
    )
    for name in generated_names:
        generated = tmp_path / name
        generated.mkdir()
        nested = generated / "nested"
        nested.mkdir()
        (nested / "state.json").write_text("{}", encoding="utf-8")

    adapter = FilesystemReadOnlyAdapter(
        tmp_path,
        page_size=20,
        max_entries=20,
        max_depth=0,
    )
    page = adapter.discover()
    by_id = {item.external_id: item for item in page.items}

    assert adapter.partition_children() == (included,)
    assert all(by_id[name].outcome == "hard_excluded" for name in generated_names)
    excluded_prefixes = tuple(f"{name}/" for name in generated_names)
    assert all(
        not item.external_id.startswith(excluded_prefixes)
        for item in page.items
    )


def test_filesystem_prunes_hidden_application_state_before_descent(
    tmp_path: Path,
):
    hidden_state = tmp_path / ".job-application-browser"
    extension = hidden_state / "Default" / "Extensions"
    extension.mkdir(parents=True)
    (extension / "filter.txt").write_text("machine filter", encoding="utf-8")
    (tmp_path / "cover-letter.txt").write_text(
        "Human-authored application letter",
        encoding="utf-8",
    )

    page = FilesystemReadOnlyAdapter(tmp_path).discover()
    by_id = {item.external_id: item for item in page.items}

    assert by_id[".job-application-browser"].outcome == "hard_excluded"
    assert by_id[".job-application-browser"].reason == (
        "hidden_application_state_not_user_content"
    )
    assert ".job-application-browser/Default/Extensions/filter.txt" not in by_id
    assert by_id["cover-letter.txt"].outcome == "candidate"


def test_filesystem_prunes_generated_directories_only_inside_software_trees(
    tmp_path: Path,
):
    project = tmp_path / "ProjectRadar"
    project.mkdir()
    (project / ".flowpilot").mkdir()
    processed = project / "data" / "processed"
    processed.mkdir(parents=True)
    (processed / "job.json").write_text("{}", encoding="utf-8")
    exports = project / "data" / "exports"
    exports.mkdir(parents=True)
    (exports / "job.json").write_text("{}", encoding="utf-8")
    reports = project / "reports"
    reports.mkdir()
    (reports / "release-validation.txt").write_text(
        "machine report",
        encoding="utf-8",
    )
    (project / "README.md").write_text("Human project context", encoding="utf-8")

    user_reports = tmp_path / "Reports"
    user_reports.mkdir()
    (user_reports / "travel.txt").write_text(
        "Human travel report",
        encoding="utf-8",
    )

    page = FilesystemReadOnlyAdapter(tmp_path).discover()
    by_id = {item.external_id: item for item in page.items}

    assert by_id["ProjectRadar/.flowpilot"].outcome == "hard_excluded"
    assert by_id["ProjectRadar/data/processed"].reason == (
        "generated_software_state_not_user_content"
    )
    assert by_id["ProjectRadar/data/exports"].reason == (
        "generated_software_state_not_user_content"
    )
    assert by_id["ProjectRadar/reports"].reason == (
        "generated_software_state_not_user_content"
    )
    assert by_id["ProjectRadar/README.md"].outcome == "candidate"
    assert by_id["ProjectRadar/README.md"].metadata["software_tree"] is True
    assert by_id["Reports/travel.txt"].outcome == "candidate"
    assert by_id["Reports/travel.txt"].metadata["software_tree"] is False


def test_filesystem_partition_children_reject_links(tmp_path: Path):
    included = tmp_path / "included"
    included.mkdir()
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    link = tmp_path / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")

    adapter = FilesystemReadOnlyAdapter(tmp_path, max_depth=0)
    page = adapter.discover()
    by_id = {item.external_id: item for item in page.items}

    assert by_id["linked"].outcome == "hard_excluded"
    assert adapter.partition_children() == (included,)
