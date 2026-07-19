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
    assert first == retry
    assert not first.terminal
    assert first.coverage == "partial"
    assert [item.external_id for item in second.items] == ["z.txt"]
    assert second.terminal
    assert second.coverage == "complete"
    assert content_reads == []


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
