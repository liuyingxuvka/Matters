from __future__ import annotations

import json
from pathlib import Path

import pytest

from matters.application.orchestrator import MatterService
from matters.application.partitioned_filesystem import (
    MANIFEST_SCHEMA,
    PartitionManifestError,
    PartitionedFilesystemRunner,
)
from matters.application.source_workflows import SourceWorkflow
from matters.inventory.owners import CURRENT_TRACKING_POLICY_REVISION
from matters.providers.filesystem import FilesystemReadOnlyAdapter


def _service_roots(tmp_path: Path) -> tuple[Path, Path, Path]:
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    source = tmp_path / "source"
    repository.mkdir()
    source.mkdir()
    return repository, private, source


def test_partition_boundary_is_terminal_not_tracked_routing(tmp_path: Path):
    repository, private, source = _service_roots(tmp_path)
    child = source / "child"
    child.mkdir()
    (child / "nested.txt").write_text("nested", encoding="utf-8")
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )

    result = SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(
            source,
            page_size=10,
            max_entries=10,
            max_depth=0,
        ),
        content_limit=0,
    )
    dispositions = {
        item.occurrence_id: item.status
        for item in result.snapshot.dispositions
    }
    boundary = next(
        item
        for item in result.snapshot.occurrences
        if item.metadata["discovery_outcome"] == "partition_boundary"
    )

    assert dispositions[boundary.occurrence_id] == "not_tracked"
    assert boundary.metadata["disposition_reason"] == (
        "covered_by_declared_child_scope"
    )


def test_partition_runner_recursively_bounds_and_resumes_inventory(tmp_path: Path):
    repository, private, source = _service_roots(tmp_path)
    (source / "root.txt").write_text("root", encoding="utf-8")
    wide = source / "wide"
    wide.mkdir()
    (wide / "own.txt").write_text("own", encoding="utf-8")
    first = wide / "first"
    first.mkdir()
    second = wide / "second"
    second.mkdir()
    for index in range(3):
        (first / f"{index}.txt").write_text(str(index), encoding="utf-8")
    for index in range(2):
        (second / f"{index}.txt").write_text(str(index), encoding="utf-8")
    small = source / "small"
    small.mkdir()
    (small / "only.txt").write_text("only", encoding="utf-8")

    service = MatterService(
        repository_root=repository,
        private_root=private,
    )
    manifest_path = (
        private / "runs" / "filesystem-partitions" / "synthetic.json"
    )
    runner = PartitionedFilesystemRunner(
        service,
        manifest_path=manifest_path,
        max_entries=4,
        content_limit=0,
    )

    first_result = runner.run(source)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    attempt_counts = {
        key: value["attempt_count"]
        for key, value in manifest["nodes"].items()
    }
    resumed_result = runner.run(source)
    resumed = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert first_result["ok"]
    assert first_result["inventory_status"] == "complete"
    assert first_result["terminal_coverage"] == "not_claimed"
    assert first_result["delegating_partition_count"] == 2
    assert first_result["complete_partition_count"] == 3
    assert first_result["partition_count"] == 5
    assert manifest["schema"] == MANIFEST_SCHEMA
    assert manifest["policy_revision"] == CURRENT_TRACKING_POLICY_REVISION
    assert all(
        item["status"] in {"complete", "partitioned"}
        for item in manifest["nodes"].values()
    )
    assert resumed_result["ok"]
    assert {
        key: value["attempt_count"]
        for key, value in resumed["nodes"].items()
    } == attempt_counts

    canary = PartitionedFilesystemRunner(
        service,
        manifest_path=manifest_path,
        max_entries=4,
        content_limit=2,
    ).run(source)
    assert canary["ok"]
    assert canary["content_attempted"] == 2
    assert canary["content_ingested"] == 2


def test_partition_canary_uses_smallest_current_subtree_that_fills_sample(
    tmp_path: Path,
    monkeypatch,
):
    repository, private, source = _service_roots(tmp_path)
    large = source / "large"
    large.mkdir()
    for index in range(8):
        (large / f"{index}.txt").write_text(str(index), encoding="utf-8")
    small = source / "small"
    small.mkdir()
    (small / "one.txt").write_text("one", encoding="utf-8")
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )
    manifest_path = private / "runs" / "canary-priority.json"
    PartitionedFilesystemRunner(
        service,
        manifest_path=manifest_path,
        max_entries=20,
        content_limit=0,
    ).run(source)
    canary_runner = PartitionedFilesystemRunner(
        service,
        manifest_path=manifest_path,
        max_entries=20,
        content_limit=2,
    )
    extraction_paths: list[Path] = []
    assert service.coverage_ledger is not None
    summary_refreshes = 0
    original_summary = service.coverage_ledger._save_summary
    original = canary_runner._scan

    def record_summary(*args, **kwargs):
        nonlocal summary_refreshes
        summary_refreshes += 1
        return original_summary(*args, **kwargs)

    def record_extraction(path: Path, **kwargs):
        if kwargs.get("content_limit", 0):
            extraction_paths.append(path)
        return original(path, **kwargs)

    monkeypatch.setattr(
        service.coverage_ledger,
        "_save_summary",
        record_summary,
    )
    monkeypatch.setattr(canary_runner, "_scan", record_extraction)

    result = canary_runner.run(source)

    assert result["ok"]
    assert result["content_ingested"] == 2
    assert extraction_paths == [large.resolve()]
    assert summary_refreshes == 1


def test_partition_manifest_blocks_a_stale_tracking_policy(tmp_path: Path):
    repository, private, source = _service_roots(tmp_path)
    (source / "one.txt").write_text("one", encoding="utf-8")
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )
    manifest_path = private / "runs" / "stale-policy.json"
    runner = PartitionedFilesystemRunner(
        service,
        manifest_path=manifest_path,
        max_entries=10,
        content_limit=0,
    )
    manifest = runner._new_manifest(source.resolve())
    manifest["policy_revision"] = CURRENT_TRACKING_POLICY_REVISION - 1
    runner._save(manifest)

    with pytest.raises(
        PartitionManifestError,
        match="partition_manifest_policy_stale",
    ):
        runner.run(source)


def test_partition_runner_keeps_unpartitionable_flat_directory_blocked(
    tmp_path: Path,
):
    repository, private, source = _service_roots(tmp_path)
    for index in range(5):
        (source / f"{index}.txt").write_text(str(index), encoding="utf-8")
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )
    manifest_path = private / "runs" / "flat.json"
    runner = PartitionedFilesystemRunner(
        service,
        manifest_path=manifest_path,
        max_entries=3,
        content_limit=0,
    )

    result = runner.run(source)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert not result["ok"]
    assert result["inventory_status"] == "blocked"
    assert result["failed_partition_count"] == 1
    assert next(iter(manifest["nodes"].values()))["status"] == "failed"


def test_partition_runner_splits_authorized_root_before_deep_walk(
    tmp_path: Path,
):
    repository, private, source = _service_roots(tmp_path)
    (source / "root.txt").write_text("root", encoding="utf-8")
    child = source / "child"
    child.mkdir()
    (child / "nested.txt").write_text("nested", encoding="utf-8")
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )
    manifest_path = private / "runs" / "proactive-root.json"
    runner = PartitionedFilesystemRunner(
        service,
        manifest_path=manifest_path,
        max_entries=100,
        content_limit=0,
    )

    result = runner.run(source)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["ok"]
    assert result["partition_count"] == 2
    assert result["delegating_partition_count"] == 1
    assert result["complete_partition_count"] == 1
    root_node = next(
        node
        for node in manifest["nodes"].values()
        if node["relative_path"] == "."
    )
    assert root_node["status"] == "partitioned"
    assert len(root_node["child_node_ids"]) == 1


def test_partition_runner_scans_bounded_child_subtrees_before_further_split(
    tmp_path: Path,
    monkeypatch,
):
    repository, private, source = _service_roots(tmp_path)
    child = source / "child"
    child.mkdir()
    grandchild = child / "grandchild"
    grandchild.mkdir()
    (grandchild / "nested.txt").write_text("nested", encoding="utf-8")
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )
    manifest_path = private / "runs" / "nested-proactive.json"
    runner = PartitionedFilesystemRunner(
        service,
        manifest_path=manifest_path,
        max_entries=100,
        content_limit=0,
    )
    assert service.coverage_ledger is not None
    refresh_calls = 0
    original = service.coverage_ledger._save_summary

    def counted_refresh(*args, **kwargs):
        nonlocal refresh_calls
        refresh_calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(
        service.coverage_ledger,
        "_save_summary",
        counted_refresh,
    )

    result = runner.run(source)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status_by_path = {
        node["relative_path"]: node["status"]
        for node in manifest["nodes"].values()
    }

    assert result["ok"]
    assert result["partition_count"] == 2
    assert result["delegating_partition_count"] == 1
    assert result["complete_partition_count"] == 1
    assert status_by_path == {
        ".": "partitioned",
        "child": "complete",
    }
    child_node = next(
        node
        for node in manifest["nodes"].values()
        if node["relative_path"] == "child"
    )
    assert child_node["summary"]["discovered"] == 1
    assert child_node["child_node_ids"] == []
    assert refresh_calls == 1


def test_wide_inventory_batches_manifest_checkpoints(
    tmp_path: Path,
    monkeypatch,
):
    repository, private, source = _service_roots(tmp_path)
    for index in range(52):
        child = source / f"child-{index:02d}"
        child.mkdir()
        (child / "item.txt").write_text(str(index), encoding="utf-8")
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )
    manifest_path = private / "runs" / "wide-checkpoints.json"
    runner = PartitionedFilesystemRunner(
        service,
        manifest_path=manifest_path,
        max_entries=100,
        content_limit=0,
    )
    save_calls = 0
    original = runner._save

    def counted_save(manifest):
        nonlocal save_calls
        save_calls += 1
        return original(manifest)

    monkeypatch.setattr(runner, "_save", counted_save)

    result = runner.run(source)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["ok"]
    assert result["partition_count"] == 53
    assert save_calls == 4
    assert all(
        node["status"] in {"complete", "partitioned"}
        for node in manifest["nodes"].values()
    )


def test_wide_inventory_resumes_from_last_batched_checkpoint(
    tmp_path: Path,
    monkeypatch,
):
    repository, private, source = _service_roots(tmp_path)
    for index in range(52):
        child = source / f"child-{index:02d}"
        child.mkdir()
        (child / "item.txt").write_text(str(index), encoding="utf-8")
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )
    manifest_path = private / "runs" / "wide-resume.json"
    interrupted = PartitionedFilesystemRunner(
        service,
        manifest_path=manifest_path,
        max_entries=100,
        content_limit=0,
    )
    save_calls = 0
    original = interrupted._save

    def interrupt_after_first_batch(manifest):
        nonlocal save_calls
        save_calls += 1
        original(manifest)
        if save_calls == 2:
            raise RuntimeError("synthetic_process_interruption")

    monkeypatch.setattr(
        interrupted,
        "_save",
        interrupt_after_first_batch,
    )

    try:
        interrupted.run(source)
    except RuntimeError as exc:
        assert str(exc) == "synthetic_process_interruption"
    else:
        raise AssertionError("synthetic interruption was not reached")

    checkpoint = json.loads(manifest_path.read_text(encoding="utf-8"))
    checkpoint_terminal = sum(
        node["status"] in {"complete", "partitioned"}
        for node in checkpoint["nodes"].values()
    )
    assert checkpoint_terminal == 25

    resumed = PartitionedFilesystemRunner(
        service,
        manifest_path=manifest_path,
        max_entries=100,
        content_limit=0,
    ).run(source)
    final = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert resumed["ok"]
    assert resumed["partition_count"] == 53
    assert all(
        node["status"] in {"complete", "partitioned"}
        for node in final["nodes"].values()
    )


def test_service_inventory_uses_private_partition_manifest(tmp_path: Path):
    repository, private, source = _service_roots(tmp_path)
    (source / "one.txt").write_text("one", encoding="utf-8")
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )

    result = service.scan_filesystem(root=str(source), content_limit=0)

    assert result["ok"]
    assert result["inventory_status"] == "complete"
    assert result["terminal_coverage"] == "not_claimed"
    manifest_root = private / "runs" / "filesystem-partitions"
    assert len(tuple(manifest_root.glob("*.json"))) == 1


def test_multiple_authorized_roots_share_one_private_manifest_area(
    tmp_path: Path,
):
    repository, private, first_source = _service_roots(tmp_path)
    second_source = tmp_path / "second-source"
    second_source.mkdir()
    (first_source / "first.txt").write_text("first", encoding="utf-8")
    (second_source / "second.txt").write_text("second", encoding="utf-8")
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )

    first = service.scan_filesystem(root=str(first_source), content_limit=0)
    second = service.scan_filesystem(root=str(second_source), content_limit=0)

    assert first["ok"]
    assert second["ok"]
    manifest_root = private / "runs" / "filesystem-partitions"
    assert len(tuple(manifest_root.glob("*.json"))) == 2
