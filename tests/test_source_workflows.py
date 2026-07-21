from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

import pytest

from matters.application.orchestrator import MatterService
from matters.application.source_workflows import SourceWorkflow
from matters.providers.filesystem import FilesystemReadOnlyAdapter
from matters.providers.gmail import (
    GmailAuthorizedPage,
    GmailMessageContent,
    GmailMessageMetadata,
    GmailReadManifest,
    GmailReadOnlyAdapter,
)
from matters.provenance.evidence import EvidenceAnchor
from scripts.ingest_gmail_export import ingest as ingest_gmail_export


def _service(tmp_path: Path) -> MatterService:
    repository = tmp_path / "repository"
    repository.mkdir()
    return MatterService(
        repository_root=repository,
        private_root=tmp_path / "private-runtime",
    )


def _owner_counts(service: MatterService) -> dict[str, int]:
    assert service.store is not None
    counts: dict[str, int] = {}
    with service.store.connection() as connection:
        for table in ("snapshots", "snapshot_archive"):
            for owner, count in connection.execute(
                f"SELECT owner, COUNT(*) FROM {table} GROUP BY owner"
            ):
                counts[str(owner)] = counts.get(str(owner), 0) + int(count)
    return counts


def test_filesystem_workflow_reconciles_reads_and_anchors(tmp_path: Path) -> None:
    source_root = tmp_path / "user-documents"
    source_root.mkdir()
    (source_root / "note.txt").write_text(
        "First line\nSecond line\n",
        encoding="utf-8",
    )
    (source_root / ".env").write_text("SECRET=private", encoding="utf-8")

    service = _service(tmp_path)
    workflow = SourceWorkflow(service)
    first = workflow.run_filesystem(
        FilesystemReadOnlyAdapter(source_root, page_size=1),
        content_limit=1,
    )

    assert first.summary.terminal is True
    assert first.summary.discovered == 2
    assert first.summary.tracked == 1
    assert first.summary.hard_excluded == 1
    assert first.summary.content_ingested == 1
    assert first.summary.evidence_anchors == 2
    assert first.summary.depth_partial == 1
    assert first.summary.depth_not_assessed == 1
    assert len(service.current_records("document_extraction")) == 1
    assert len(service.current_records("evidence_anchor")) == 2
    assert len(service.current_records("analysis_work_package")) == 1
    assert (
        service.current_records("agent_operation_result")[0]["status"]
        == "queued"
    )

    restarted = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private-runtime",
    )
    second = SourceWorkflow(restarted).run_filesystem(
        FilesystemReadOnlyAdapter(source_root, page_size=1),
        content_limit=1,
    )
    assert second.changes.no_delta is True
    assert second.summary.metadata_registered == 0
    assert second.summary.content_ingested == 1
    assert restarted.store is not None
    tracked_ids = {
        item.occurrence_id
        for item in second.snapshot.dispositions
        if item.status == "tracked"
    }
    occurrence_id = next(
        item.occurrence_id
        for item in second.snapshot.occurrences
        if item.occurrence_id in tracked_ids
    )
    extraction_history = tuple(
        restarted.store.history("document_extraction", occurrence_id)
    )
    assert len(extraction_history) == 1
    assert all(
        len(tuple(restarted.store.history("evidence_anchor", row["evidence_id"])))
        == 1
        for row in restarted.current_records("evidence_anchor")
    )


def test_filesystem_inventory_only_records_pending_automatic_content_work(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "user-documents"
    source_root.mkdir()
    (source_root / "note.txt").write_text("synthetic", encoding="utf-8")
    service = _service(tmp_path)

    result = SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
        content_limit=0,
    )

    assert result.summary.discovered == 1
    assert result.summary.tracked == 1
    assert result.summary.content_ingested == 0
    assert result.summary.depth_stale == 1
    assert result.summary.depth_not_assessed == 0
    assert service.current_records("source_version") == ()
    depth = service.current_records("semantic_depth")
    assert len(depth) == 1
    assert depth[0]["state"] == "stale"
    coverage = service.object_coverage_summary()
    assert coverage["registered_object_count"] == 1
    assert coverage["pending_object_count"] == 1
    assert coverage["next_stage_counts"] == {"source_version": 1}


def test_filesystem_workflow_default_is_inventory_only_not_unbounded_read(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "user-documents"
    source_root.mkdir()
    for index in range(3):
        (source_root / f"note-{index}.txt").write_text("private", encoding="utf-8")
    service = _service(tmp_path)

    result = SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
    )

    assert result.summary.content_ingested == 0
    assert service.current_records("source_version") == ()
    assert service.current_records("document_extraction") == ()
    assert service.current_records("evidence_anchor") == ()
    assert service.current_records("analysis_work_package") == ()


def test_content_selection_defers_software_tree_documents_before_any_read(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "project"
    source_root.mkdir()
    (source_root / "package.json").write_text("{}", encoding="utf-8")
    (source_root / "notes.md").write_text("private notes", encoding="utf-8")
    service = _service(tmp_path)

    result = SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
        content_limit=0,
    )

    plans = service.current_records("content_selection")
    deferred = next(item for item in plans if item["mode"] == "deferred")
    assert deferred["reason"] == "software_tree_document_deferred"
    assert service.store is not None
    queued, total = service.store.registered_filesystem_source_page(limit=10)
    assert queued == ()
    assert total == 0
    coverage = service.coverage_ledger.current(str(deferred["occurrence_id"]))
    assert coverage is not None
    assert coverage.terminal is True
    assert coverage.stages["source_version"].status == "not_applicable"
    assert result.summary.content_ingested == 0
    assert service.current_records("source_version") == ()
    assert service.current_records("document_extraction") == ()


def test_content_selection_claim_order_is_stable_within_one_neighborhood(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "user-documents"
    source_root.mkdir()
    for name in ("alpha.txt", "bravo.txt", "charlie.txt"):
        (source_root / name).write_text(name, encoding="utf-8")
    service = _service(tmp_path)
    SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
        content_limit=0,
    )
    assert service.store is not None

    plans = [
        item
        for item in service.current_records("content_selection")
        if item["mode"] == "bounded"
    ]
    expected = tuple(
        item["occurrence_id"]
        for item in sorted(
            plans,
            key=lambda item: (-int(item["priority"]), item["occurrence_id"]),
        )
    )
    selected, total = service.store.registered_filesystem_source_page(limit=10)
    assert total == 3
    assert selected == expected


def test_content_selection_rebase_deduplicates_overlapping_registered_scopes(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "user-documents"
    nested_root = source_root / "nested"
    nested_root.mkdir(parents=True)
    (nested_root / "note.txt").write_text("private note", encoding="utf-8")
    service = _service(tmp_path)
    workflow = SourceWorkflow(service)
    workflow.run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
        content_limit=0,
    )
    workflow.run_filesystem(
        FilesystemReadOnlyAdapter(nested_root),
        content_limit=0,
    )

    result = service.rebase_content_selection(limit=10)

    assert result["scanned_object_count"] == 2
    assert result["planned_object_count"] == 2
    assert result["status"] == "current"
    assert len(service.current_records("content_selection")) == 2


def test_content_selection_does_not_revise_for_inventory_counter_only(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "user-documents"
    source_root.mkdir()
    (source_root / "note.txt").write_text("private note", encoding="utf-8")
    service = _service(tmp_path)
    workflow = SourceWorkflow(service)
    first = workflow.run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
        content_limit=0,
    )
    assert service.store is not None
    occurrence_id = first.snapshot.occurrences[0].occurrence_id
    assert len(service.store.history("content_selection", occurrence_id)) == 1

    second = workflow.run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
        content_limit=0,
    )

    assert second.changes.no_delta is True
    assert second.snapshot.revision > first.snapshot.revision
    assert len(service.store.history("content_selection", occurrence_id)) == 1


def test_source_understanding_expansion_is_bounded_resumable_and_complete(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    assert service.store is not None
    source_id = "source:bounded-expansion"
    source_revision = f"{source_id}:v1"
    anchors = tuple(
        EvidenceAnchor(
            evidence_id=f"evidence:{source_id}:1:{index:04d}",
            source_id=source_id,
            source_version=1,
            location={"line": index + 1},
            text=f"Evidence line {index}",
            modality="observed",
        )
        for index in range(105)
    )
    service.store.append_content_addressed_many(
        (
            "evidence_anchor",
            anchor.evidence_id,
            asdict(anchor),
        )
        for anchor in anchors
    )

    first = service.queue_source_understanding(
        source_revision=source_revision,
        source_kind="document",
        anchors=anchors,
        chunk_size=20,
        max_packages_per_call=2,
    )
    descriptor = service.store.current(
        "source_analysis_expansion",
        source_revision,
    )
    assert len(first) == 2
    assert descriptor["status"] == "pending"
    assert descriptor["next_anchor_offset"] == 40
    assert descriptor["remaining_anchor_count"] == 65

    second = service.expand_pending_source_understanding(
        limit_sources=1,
        max_packages_per_source=3,
    )
    assert second == {
        "status": "progressed",
        "expanded_source_count": 1,
        "queued_package_count": 3,
        "remaining_source_count": 1,
    }
    final = service.expand_pending_source_understanding(
        limit_sources=1,
        max_packages_per_source=3,
    )
    assert final == {
        "status": "progressed",
        "expanded_source_count": 1,
        "queued_package_count": 1,
        "remaining_source_count": 0,
    }
    descriptor = service.store.current(
        "source_analysis_expansion",
        source_revision,
    )
    assert descriptor["status"] == "complete"
    assert descriptor["next_anchor_offset"] == 105
    package_evidence = {
        evidence_id
        for package in service.current_records("analysis_work_package")
        for evidence_id in package["allowed_evidence_ids"]
    }
    assert package_evidence == {anchor.evidence_id for anchor in anchors}
    assert (
        service.expand_pending_source_understanding(
            limit_sources=1,
            max_packages_per_source=3,
        )["status"]
        == "idle"
    )


def test_registered_filesystem_batches_use_distinct_indexed_pages_without_discover(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_root = tmp_path / "user-documents"
    source_root.mkdir()
    for name in ("alpha.txt", "bravo.txt", "charlie.txt"):
        (source_root / name).write_text(
            f"{name} first line\n{name} second line\n",
            encoding="utf-8",
        )
    (source_root / ".env").write_text(
        "SECRET=private",
        encoding="utf-8",
    )
    service = _service(tmp_path)
    workflow = SourceWorkflow(service)
    inventory = workflow.run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
        content_limit=0,
    )
    assert service.store is not None
    first_ids, total = service.store.registered_filesystem_source_page(
        limit=2
    )
    assert total == 3
    assert len(first_ids) == 2

    def fail_discover(*args, **kwargs):
        raise AssertionError("registered content processing must not rediscover")

    monkeypatch.setattr(FilesystemReadOnlyAdapter, "discover", fail_discover)
    assert service.inventory is not None
    monkeypatch.setattr(
        service.inventory,
        "latest_snapshot",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError(
                "registered content processing must use the exact occurrence index"
            )
        ),
    )
    first = service.process_registered_filesystem_batch(limit=2)
    second_ids, remaining = service.store.registered_filesystem_source_page(
        limit=2
    )
    second = service.process_registered_filesystem_batch(limit=2)
    idle = service.process_registered_filesystem_batch(limit=2)

    assert first.status == "processed"
    assert first.selected_count == 2
    assert first.processed_count == 2
    assert first.remaining_count == 1
    assert remaining == 1
    assert len(second_ids) == 1
    assert set(first_ids).isdisjoint(second_ids)
    assert second.status == "processed"
    assert second.selected_count == 1
    assert second.processed_count == 1
    assert second.remaining_count == 0
    assert idle.status == "idle"
    assert idle.selected_count == 0
    assert idle.remaining_count == 0
    assert len(service.current_records("source_version")) == 3
    assert len(service.current_records("document_extraction")) == 3
    with service.store.connection() as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM filesystem_claim_items "
                "WHERE completed=0"
            ).fetchone()[0]
            == 0
        )
    assert len(service.current_records("analysis_work_package")) == 3
    assert all(
        item.stages["source_version"].status == "current"
        for item in (
            service.coverage_ledger.current(occurrence.occurrence_id)
            for occurrence in inventory.snapshot.occurrences
            if occurrence.object_type != "file"
            or occurrence.metadata.get("display_name") != ".env"
        )
        if item is not None and item.disposition == "tracked"
    )


def test_registered_filesystem_batch_releases_claim_after_interruption(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_root = tmp_path / "user-documents"
    source_root.mkdir()
    (source_root / "note.txt").write_text(
        "One line of user content.",
        encoding="utf-8",
    )
    service = _service(tmp_path)
    SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
        content_limit=0,
    )
    assert service.store is not None

    def interrupt(*_args, **_kwargs):
        raise RuntimeError("synthetic interruption")

    monkeypatch.setattr(SourceWorkflow, "_document_evidence", interrupt)
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        service.process_registered_filesystem_batch(limit=1)

    recovered = service.store.claim_registered_filesystem(
        worker_id="worker:test-recovery",
        limit=1,
        lease_seconds=60,
    )
    assert recovered is not None
    assert recovered["items"][0]["attempt"] == 2
    assert recovered["items"][0]["recovered"] is True
    assert service.store.abandon_filesystem_worker_claim(
        worker_id="worker:test-recovery",
        reason="test_cleanup",
    )["released_item_count"] == 1


def test_registered_filesystem_batch_blocks_changed_and_unavailable_content(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_root = tmp_path / "user-documents"
    source_root.mkdir()
    changed = source_root / "changed.txt"
    missing = source_root / "missing.txt"
    changed.write_text("before\n", encoding="utf-8")
    missing.write_text("available during inventory\n", encoding="utf-8")
    service = _service(tmp_path)
    inventory = SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
        content_limit=0,
    )
    changed.write_text(
        "after inventory with a different byte length\n",
        encoding="utf-8",
    )
    missing.unlink()

    def fail_discover(*args, **kwargs):
        raise AssertionError("registered content processing must not rediscover")

    monkeypatch.setattr(FilesystemReadOnlyAdapter, "discover", fail_discover)
    result = service.process_registered_filesystem_batch(limit=2)

    assert result.status == "processed_with_blocks"
    assert result.selected_count == 2
    assert result.processed_count == 0
    assert result.changed_count == 1
    assert result.unavailable_count == 1
    assert result.blocked_count == 2
    assert result.remaining_count == 0
    assert service.current_records("source_version") == ()
    assert service.current_records("document_extraction") == ()
    assert all(
        service.coverage_ledger.current(
            occurrence.occurrence_id
        ).stages["source_version"].status
        == "blocked"
        for occurrence in inventory.snapshot.occurrences
    )
    serialized = json.dumps(asdict(result), sort_keys=True)
    assert str(source_root) not in serialized
    assert "changed.txt" not in serialized
    assert "missing.txt" not in serialized


def test_registered_filesystem_retry_preserves_content_depth(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_root = tmp_path / "user-documents"
    source_root.mkdir()
    (source_root / "note.txt").write_text(
        "First line\nSecond line\n",
        encoding="utf-8",
    )
    service = _service(tmp_path)
    inventory = SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
        content_limit=0,
    )
    occurrence_id = inventory.snapshot.occurrences[0].occurrence_id
    first = service.process_registered_filesystem_batch(limit=1)
    assert first.processed_count == 1
    assert service.coverage_ledger is not None
    evidence_before = service.coverage_ledger.current(
        occurrence_id
    ).stages["evidence"].status
    service.coverage_ledger.mark_stage(
        object_id=occurrence_id,
        stage_id="source_version",
        status="stale",
        input_fingerprint="sha256:forced-retry",
    )

    def fail_discover(*args, **kwargs):
        raise AssertionError("registered content retry must not rediscover")

    monkeypatch.setattr(FilesystemReadOnlyAdapter, "discover", fail_discover)
    retry = service.process_registered_filesystem_batch(limit=1)

    assert retry.processed_count == 1
    assert retry.remaining_count == 0
    assert len(service.current_records("source_version")) == 1
    coverage = service.coverage_ledger.current(occurrence_id)
    assert coverage.stages["source_version"].status == "current"
    assert coverage.stages["evidence"].status == evidence_before == "current"


def test_registered_filesystem_batch_processes_one_hundred_small_files(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "user-documents"
    source_root.mkdir()
    for index in range(100):
        (source_root / f"note-{index:03d}.txt").write_text(
            f"Synthetic user note {index}\n",
            encoding="utf-8",
        )
    service = _service(tmp_path)
    SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
        content_limit=0,
    )

    result = service.process_registered_filesystem_batch(limit=100)

    assert result.status == "processed"
    assert result.selected_count == 100
    assert result.processed_count == 100
    assert result.content_ingested == 100
    assert result.evidence_anchors == 100
    assert result.blocked_count == 0
    assert result.remaining_count == 0
    assert len(service.current_records("source_version")) == 100
    assert len(service.current_records("document_extraction")) == 100


def test_coverage_endpoint_reads_persisted_summary_without_rescanning_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_root = tmp_path / "user-documents"
    source_root.mkdir()
    (source_root / "note.txt").write_text("synthetic", encoding="utf-8")
    service = _service(tmp_path)
    SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(source_root),
        content_limit=0,
    )
    assert service.coverage_ledger is not None

    def fail_full_scan(*args, **kwargs):
        raise AssertionError("request path must not rescan the full ledger")

    monkeypatch.setattr(service.coverage_ledger, "summary", fail_full_scan)
    coverage = service.object_coverage_summary()

    assert coverage["registered_object_count"] == 1
    assert coverage["pending_object_count"] == 1


def test_filesystem_policy_context_reversibly_excludes_generated_state(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "Documents" / "project" / "tmp" / "partition"
    source_root.mkdir(parents=True)
    (source_root / "generated.txt").write_text("generated", encoding="utf-8")
    service = _service(tmp_path)

    result = SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(
            source_root,
            policy_path_prefix=("project", "tmp", "partition"),
        ),
        content_limit=0,
    )

    assert result.summary.tracked == 0
    assert result.summary.hard_excluded == 1
    disposition = result.snapshot.dispositions[0]
    assert disposition.status == "hard_excluded"
    assert disposition.decided_by == "policy"
    assert "tmp" in result.snapshot.occurrences[0].metadata["policy_path_tokens"]


def test_gmail_workflow_tracks_included_mail_and_hard_excludes_spam(
    tmp_path: Path,
) -> None:
    account_ref = "sha256:" + sha256(b"account").hexdigest()
    query_fingerprint = "sha256:" + sha256(b"query").hexdigest()
    manifest = GmailReadManifest(
        scope_id="gmail-scope:test",
        account_ref=account_ref,
        authorization_revision="authorization:v1",
        query_fingerprint=query_fingerprint,
        policy_revision="policy:v1",
    )
    page = GmailAuthorizedPage(
        scope_id=manifest.scope_id,
        account_ref=manifest.account_ref,
        authorization_revision=manifest.authorization_revision,
        query_fingerprint=manifest.query_fingerprint,
        policy_revision=manifest.policy_revision,
        requested_cursor="",
        next_cursor="",
        terminal=True,
        messages=(
            GmailMessageMetadata(
                message_id="message-inbox",
                thread_id="thread-inbox",
                category="inbox",
                label_ids=("inbox",),
                internal_date="2026-07-18T10:00:00+00:00",
            ),
            GmailMessageMetadata(
                message_id="message-spam",
                thread_id="thread-spam",
                category="spam",
                label_ids=("spam",),
                internal_date="2026-07-18T11:00:00+00:00",
            ),
        ),
        contents=(
            GmailMessageContent(
                message_id="message-inbox",
                body_text="A useful fact\nA second useful fact",
                headers={"subject": "Private subject"},
            ),
        ),
    )
    adapter = GmailReadOnlyAdapter(
        manifest,
        page_source=lambda cursor: page,
    )
    service = _service(tmp_path)

    result = SourceWorkflow(service).run_gmail(adapter)

    assert result.summary.terminal is True
    assert result.summary.discovered == 4
    assert result.summary.tracked == 1
    assert result.summary.hard_excluded == 1
    assert result.summary.metadata_only == 2
    assert result.summary.not_tracked == 0
    assert result.summary.content_ingested == 1
    assert result.summary.evidence_anchors == 2
    dispositions = {
        item.occurrence_id: item.status for item in result.snapshot.dispositions
    }
    message = next(
        item
        for item in result.snapshot.occurrences
        if item.object_type == "message"
        and item.metadata.get("category") == "inbox"
    )
    spam = next(
        item
        for item in result.snapshot.occurrences
        if item.object_type == "message"
        and item.metadata.get("category") == "spam"
    )
    assert dispositions[message.occurrence_id] == "tracked"
    assert dispositions[spam.occurrence_id] == "hard_excluded"
    assert message.parent_occurrence_id.startswith("gmail:thread:")
    assert len(service.current_records("document_extraction")) == 1
    assert len(service.current_records("evidence_anchor")) == 2
    assert len(service.current_records("analysis_work_package")) == 1


def test_gmail_workflow_registers_minimal_metadata_only_message_sources(
    tmp_path: Path,
) -> None:
    account_ref = "sha256:" + sha256(b"metadata-account").hexdigest()
    query_fingerprint = (
        "sha256:" + sha256(b"metadata-query").hexdigest()
    )
    manifest = GmailReadManifest(
        scope_id="gmail-scope:metadata-owner",
        account_ref=account_ref,
        authorization_revision="authorization:v1",
        query_fingerprint=query_fingerprint,
        policy_revision="policy:v1",
    )
    page = GmailAuthorizedPage(
        scope_id=manifest.scope_id,
        account_ref=manifest.account_ref,
        authorization_revision=manifest.authorization_revision,
        query_fingerprint=manifest.query_fingerprint,
        policy_revision=manifest.policy_revision,
        requested_cursor="",
        next_cursor="",
        terminal=True,
        messages=(
            GmailMessageMetadata(
                "identity-only-message",
                "",
                "unknown",
                (),
                "",
                identity_only=True,
            ),
            GmailMessageMetadata(
                "metadata-only-message",
                "thread-metadata",
                "other",
                ("other",),
                "2026-07-18T10:00:00+00:00",
            ),
        ),
    )
    service = _service(tmp_path)

    result = SourceWorkflow(service).run_gmail(
        GmailReadOnlyAdapter(
            manifest,
            page_source=lambda _cursor: page,
        )
    )

    assert result.summary.metadata_only == 3
    assert result.summary.metadata_registered == 2
    sources = service.current_records("source_version")
    message_sources = tuple(
        source
        for source in sources
        if source["external_reference"]["object_type"]
        == "gmail_message"
    )
    assert len(message_sources) == 2
    assert {
        source["content"]["provider_message_id"]
        for source in message_sources
    } == {
        "identity-only-message",
        "metadata-only-message",
    }
    assert all(
        "body_text" not in source["content"]
        for source in message_sources
    )
    assert service.current_records("evidence_anchor") == ()
    assert service.current_records("admission_decision") == ()
    assert service.current_records("projection") == ()
    assert service.current_records("source_processing_result") == ()


def test_gmail_metadata_owner_reconciliation_is_bounded_and_idempotent(
    tmp_path: Path,
) -> None:
    account_ref = "sha256:" + sha256(b"repair-account").hexdigest()
    query_fingerprint = (
        "sha256:" + sha256(b"repair-query").hexdigest()
    )
    manifest = GmailReadManifest(
        scope_id="gmail-scope:metadata-repair",
        account_ref=account_ref,
        authorization_revision="authorization:v1",
        query_fingerprint=query_fingerprint,
        policy_revision="policy:v1",
    )
    messages = tuple(
        GmailMessageMetadata(
            f"identity-only-{index}",
            "",
            "unknown",
            (),
            "",
            identity_only=True,
        )
        for index in range(3)
    )
    page = GmailAuthorizedPage(
        scope_id=manifest.scope_id,
        account_ref=manifest.account_ref,
        authorization_revision=manifest.authorization_revision,
        query_fingerprint=manifest.query_fingerprint,
        policy_revision=manifest.policy_revision,
        requested_cursor="",
        next_cursor="",
        terminal=True,
        messages=messages,
    )
    adapter = GmailReadOnlyAdapter(
        manifest,
        page_source=lambda _cursor: page,
    )
    service = _service(tmp_path)
    workflow = SourceWorkflow(service)
    inventoried = workflow.run_gmail(
        adapter,
        metadata_limit=0,
    )
    assert inventoried.summary.metadata_registered == 0
    assert service.current_records("source_version") == ()

    first = workflow.reconcile_gmail_metadata_owners(
        adapter,
        limit=1,
    )
    after_first = _owner_counts(service)
    retry = workflow.reconcile_gmail_metadata_owners(
        adapter,
        limit=1,
    )

    assert first.status == "current"
    assert first.scanned_message_count == 3
    assert first.eligible_message_count == 3
    assert first.selected_count == first.registered_count == 1
    assert first.remaining_count == 2
    assert first.next_after_object_id
    assert retry.status == "no_delta"
    assert retry.already_current_count == 1
    assert _owner_counts(service) == after_first

    second = workflow.reconcile_gmail_metadata_owners(
        adapter,
        after_object_id=first.next_after_object_id,
        limit=1,
    )
    third = workflow.reconcile_gmail_metadata_owners(
        adapter,
        after_object_id=second.next_after_object_id,
        limit=1,
    )
    assert second.registered_count == 1
    assert second.remaining_count == 1
    assert third.registered_count == 1
    assert third.remaining_count == 0
    assert third.next_after_object_id == ""

    assert len(service.current_records("source_version")) == 3
    assert service.current_records("evidence_anchor") == ()
    assert service.current_records("admission_decision") == ()
    assert service.current_records("projection") == ()
    assert service.current_records("source_processing_result") == ()


def test_gmail_metadata_reconciliation_preserves_existing_body(
    tmp_path: Path,
) -> None:
    account_ref = "sha256:" + sha256(b"preserve-account").hexdigest()
    query_fingerprint = (
        "sha256:" + sha256(b"preserve-query").hexdigest()
    )
    manifest = GmailReadManifest(
        scope_id="gmail-scope:preserve-body",
        account_ref=account_ref,
        authorization_revision="authorization:v1",
        query_fingerprint=query_fingerprint,
        policy_revision="policy:v1",
    )
    full_page = GmailAuthorizedPage(
        scope_id=manifest.scope_id,
        account_ref=manifest.account_ref,
        authorization_revision=manifest.authorization_revision,
        query_fingerprint=manifest.query_fingerprint,
        policy_revision=manifest.policy_revision,
        requested_cursor="",
        next_cursor="",
        terminal=True,
        messages=(
            GmailMessageMetadata(
                "preserved-message",
                "preserved-thread",
                "inbox",
                ("inbox",),
                "2026-07-18T10:00:00+00:00",
            ),
        ),
        contents=(
            GmailMessageContent(
                "preserved-message",
                "Existing private body",
            ),
        ),
    )
    shallow_page = GmailAuthorizedPage(
        scope_id=manifest.scope_id,
        account_ref=manifest.account_ref,
        authorization_revision=manifest.authorization_revision,
        query_fingerprint=manifest.query_fingerprint,
        policy_revision=manifest.policy_revision,
        requested_cursor="",
        next_cursor="",
        terminal=True,
        messages=(
            GmailMessageMetadata(
                "preserved-message",
                "preserved-thread",
                "other",
                ("other",),
                "2026-07-18T10:00:00+00:00",
            ),
        ),
    )
    service = _service(tmp_path)
    workflow = SourceWorkflow(service)
    workflow.run_gmail(
        GmailReadOnlyAdapter(
            manifest,
            page_source=lambda _cursor: full_page,
        )
    )
    before = service.current_records("source_version")
    shallow_adapter = GmailReadOnlyAdapter(
        manifest,
        page_source=lambda _cursor: shallow_page,
    )
    workflow.run_gmail(
        shallow_adapter,
        metadata_limit=0,
    )

    reconciled = workflow.reconcile_gmail_metadata_owners(
        shallow_adapter,
        limit=1,
    )

    assert reconciled.status == "no_delta"
    assert reconciled.preserved_body_count == 1
    assert service.current_records("source_version") == before
    durable_content = service.current_records("source_version")[0]["content"]
    assert "body_text" not in durable_content
    assert durable_content["body_text_fingerprint"] == (
        "sha256:"
        + sha256(b"Existing private body").hexdigest()
    )
    assert durable_content["body_text_byte_length"] == len(
        b"Existing private body"
    )


def test_gmail_metadata_reconciliation_skips_noncurrent_owner_without_writes(
    tmp_path: Path,
) -> None:
    account_ref = "sha256:" + sha256(b"foreign-account").hexdigest()
    query_fingerprint = (
        "sha256:" + sha256(b"foreign-query").hexdigest()
    )
    manifest = GmailReadManifest(
        scope_id="gmail-scope:no-current-owner",
        account_ref=account_ref,
        authorization_revision="authorization:v1",
        query_fingerprint=query_fingerprint,
        policy_revision="policy:v1",
    )
    page = GmailAuthorizedPage(
        scope_id=manifest.scope_id,
        account_ref=manifest.account_ref,
        authorization_revision=manifest.authorization_revision,
        query_fingerprint=manifest.query_fingerprint,
        policy_revision=manifest.policy_revision,
        requested_cursor="",
        next_cursor="",
        terminal=True,
        messages=(
            GmailMessageMetadata(
                "foreign-message",
                "",
                "unknown",
                (),
                "",
                identity_only=True,
            ),
        ),
    )
    service = _service(tmp_path)
    before = _owner_counts(service)

    result = SourceWorkflow(
        service
    ).reconcile_gmail_metadata_owners(
        GmailReadOnlyAdapter(
            manifest,
            page_source=lambda _cursor: page,
        ),
        limit=1,
    )

    assert result.status == "no_delta"
    assert result.eligible_message_count == 0
    assert result.skipped_owner_mismatch_count == 1
    assert _owner_counts(service) == before


def test_gmail_content_budget_prioritizes_supplied_authorized_bodies(
    tmp_path: Path,
) -> None:
    account_ref = "sha256:" + sha256(b"budget-account").hexdigest()
    query_fingerprint = "sha256:" + sha256(b"budget-query").hexdigest()
    manifest = GmailReadManifest(
        scope_id="gmail-scope:budget",
        account_ref=account_ref,
        authorization_revision="authorization:v1",
        query_fingerprint=query_fingerprint,
        policy_revision="policy:v1",
    )
    messages = tuple(
        GmailMessageMetadata(
            message_id=f"message-{index}",
            thread_id=f"thread-{index}",
            category="inbox",
            label_ids=("inbox",),
            internal_date=f"2026-07-18T{index:02d}:00:00+00:00",
        )
        for index in range(8)
    )
    page = GmailAuthorizedPage(
        scope_id=manifest.scope_id,
        account_ref=manifest.account_ref,
        authorization_revision=manifest.authorization_revision,
        query_fingerprint=manifest.query_fingerprint,
        policy_revision=manifest.policy_revision,
        requested_cursor="",
        next_cursor="",
        terminal=True,
        messages=messages,
        contents=(
            GmailMessageContent("message-6", "newer corrected deadline"),
            GmailMessageContent("message-7", "older superseded deadline"),
        ),
    )

    result = SourceWorkflow(_service(tmp_path)).run_gmail(
        GmailReadOnlyAdapter(manifest, page_source=lambda cursor: page),
        content_limit=2,
    )

    assert result.summary.tracked == 8
    assert result.summary.content_ingested == 2
    assert result.summary.evidence_anchors == 2
    assert "gmail_content:metadata_only" not in result.summary.gaps


def test_gmail_supplied_body_priority_still_obeys_exact_content_budget(
    tmp_path: Path,
) -> None:
    account_ref = "sha256:" + sha256(b"exact-budget-account").hexdigest()
    query_fingerprint = "sha256:" + sha256(b"exact-budget-query").hexdigest()
    manifest = GmailReadManifest(
        scope_id="gmail-scope:exact-budget",
        account_ref=account_ref,
        authorization_revision="authorization:v1",
        query_fingerprint=query_fingerprint,
        policy_revision="policy:v1",
    )
    messages = tuple(
        GmailMessageMetadata(
            message_id=f"message-{index}",
            thread_id=f"thread-{index}",
            category="inbox",
            label_ids=("inbox",),
            internal_date=f"2026-07-18T{index:02d}:00:00+00:00",
        )
        for index in range(6)
    )
    page = GmailAuthorizedPage(
        scope_id=manifest.scope_id,
        account_ref=manifest.account_ref,
        authorization_revision=manifest.authorization_revision,
        query_fingerprint=manifest.query_fingerprint,
        policy_revision=manifest.policy_revision,
        requested_cursor="",
        next_cursor="",
        terminal=True,
        messages=messages,
        contents=tuple(
            GmailMessageContent(
                f"message-{index}",
                f"authorized body {index}",
            )
            for index in (3, 4, 5)
        ),
    )
    service = _service(tmp_path)

    result = SourceWorkflow(service).run_gmail(
        GmailReadOnlyAdapter(manifest, page_source=lambda cursor: page),
        content_limit=2,
    )

    assert result.summary.content_ingested == 2
    assert len(service.current_records("document_extraction")) == 2
    assert len(service.current_records("analysis_work_package")) == 2


def test_gmail_content_offset_selects_the_next_stable_batch(
    tmp_path: Path,
) -> None:
    account_ref = "sha256:" + sha256(b"offset-account").hexdigest()
    query_fingerprint = "sha256:" + sha256(b"offset-query").hexdigest()
    manifest = GmailReadManifest(
        scope_id="gmail-scope:offset",
        account_ref=account_ref,
        authorization_revision="authorization:v1",
        query_fingerprint=query_fingerprint,
        policy_revision="policy:v1",
    )
    messages = tuple(
        GmailMessageMetadata(
            message_id=f"message-{index}",
            thread_id=f"thread-{index}",
            category="inbox",
            label_ids=("inbox",),
            internal_date=f"2026-07-18T{index:02d}:00:00+00:00",
        )
        for index in range(6)
    )
    page = GmailAuthorizedPage(
        scope_id=manifest.scope_id,
        account_ref=manifest.account_ref,
        authorization_revision=manifest.authorization_revision,
        query_fingerprint=manifest.query_fingerprint,
        policy_revision=manifest.policy_revision,
        requested_cursor="",
        next_cursor="",
        terminal=True,
        messages=messages,
        contents=tuple(
            GmailMessageContent(
                f"message-{index}",
                f"authorized body {index}",
            )
            for index in range(6)
        ),
    )
    service = _service(tmp_path)

    result = SourceWorkflow(service).run_gmail(
        GmailReadOnlyAdapter(manifest, page_source=lambda cursor: page),
        content_limit=2,
        content_offset=2,
    )

    assert result.summary.content_ingested == 2
    assert len(service.current_records("document_extraction")) == 2
    assert len(service.current_records("analysis_work_package")) == 2


def test_gmail_content_resume_does_not_regress_prior_batch_evidence(
    tmp_path: Path,
) -> None:
    account_ref = "sha256:" + sha256(b"resume-account").hexdigest()
    query_fingerprint = "sha256:" + sha256(b"resume-query").hexdigest()
    manifest = GmailReadManifest(
        scope_id="gmail-scope:resume",
        account_ref=account_ref,
        authorization_revision="authorization:v1",
        query_fingerprint=query_fingerprint,
        policy_revision="policy:v1",
    )
    messages = tuple(
        GmailMessageMetadata(
            message_id=f"message-{index}",
            thread_id=f"thread-{index}",
            category="inbox",
            label_ids=("inbox",),
            internal_date=f"2026-07-18T{index:02d}:00:00+00:00",
        )
        for index in range(4)
    )
    page = GmailAuthorizedPage(
        scope_id=manifest.scope_id,
        account_ref=manifest.account_ref,
        authorization_revision=manifest.authorization_revision,
        query_fingerprint=manifest.query_fingerprint,
        policy_revision=manifest.policy_revision,
        requested_cursor="",
        next_cursor="",
        terminal=True,
        messages=messages,
        contents=tuple(
            GmailMessageContent(
                f"message-{index}",
                f"authorized body {index}",
            )
            for index in range(4)
        ),
    )
    service = _service(tmp_path)
    adapter = GmailReadOnlyAdapter(
        manifest,
        page_source=lambda cursor: page,
    )

    SourceWorkflow(service).run_gmail(
        adapter,
        content_limit=2,
        content_offset=0,
    )
    SourceWorkflow(service).run_gmail(
        adapter,
        content_limit=2,
        content_offset=2,
    )

    discovered = adapter.accept_page(page).items
    message_ids = tuple(
        item.envelope.external_id
        for item in discovered
        if item.envelope.object_type == "gmail_message"
    )
    assert all(
        service.coverage_ledger.current(object_id).stages["evidence"].status
        == "current"
        for object_id in message_ids
    )


def test_gmail_partial_inventory_pages_accumulate_without_false_deletions(
    tmp_path: Path,
) -> None:
    account_ref = "sha256:" + sha256(b"paged-account").hexdigest()
    query_fingerprint = "sha256:" + sha256(b"paged-query").hexdigest()
    manifest = GmailReadManifest(
        scope_id="gmail-scope:paged",
        account_ref=account_ref,
        authorization_revision="authorization:v1",
        query_fingerprint=query_fingerprint,
        policy_revision="policy:v1",
    )

    def page(message_id: str, thread_id: str) -> GmailAuthorizedPage:
        return GmailAuthorizedPage(
            scope_id=manifest.scope_id,
            account_ref=manifest.account_ref,
            authorization_revision=manifest.authorization_revision,
            query_fingerprint=manifest.query_fingerprint,
            policy_revision=manifest.policy_revision,
            requested_cursor="",
            next_cursor="",
            terminal=False,
            messages=(
                GmailMessageMetadata(
                    message_id=message_id,
                    thread_id=thread_id,
                    category="inbox",
                    label_ids=("inbox",),
                    internal_date="2026-07-18T10:00:00+00:00",
                ),
            ),
            contents=(
                GmailMessageContent(
                    message_id,
                    f"authorized body for {message_id}",
                ),
            ),
            coverage="partial",
        )

    service = _service(tmp_path)
    first_page = page("message-first", "thread-first")
    first = SourceWorkflow(service).run_gmail(
        GmailReadOnlyAdapter(
            manifest,
            page_source=lambda cursor: first_page,
        )
    )
    first_ids = {
        occurrence.occurrence_id for occurrence in first.snapshot.occurrences
    }

    second_page = page("message-second", "thread-second")
    second = SourceWorkflow(service).run_gmail(
        GmailReadOnlyAdapter(
            manifest,
            page_source=lambda cursor: second_page,
        )
    )
    second_ids = {
        occurrence.occurrence_id for occurrence in second.snapshot.occurrences
    }

    assert first_ids.issubset(second_ids)
    assert len(second_ids) == 4
    assert second.changes.deleted == ()
    assert second.summary.discovered == 4
    assert second.summary.content_ingested == 1
    assert "gmail_partial_inventory_page" in second.summary.gaps


def test_gmail_connector_native_export_shape_is_ingested_privately(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    repository.mkdir()
    summary = ingest_gmail_export(
        {
            "query": "in:anywhere -in:spam -in:trash",
            "account": "user@example.test",
            "messages": [
                {
                    "id": "message-1",
                    "thread_id": "thread-1",
                    "from_": "Sender <sender@example.test>",
                    "to": ["user@example.test"],
                    "subject": "Travel update",
                    "snippet": "The flight is confirmed.",
                    "body": "The flight is confirmed for September.",
                    "labels": ["IMPORTANT", "INBOX"],
                    "email_ts": "2026-07-18T14:23:00+02:00",
                    "attachments": [
                        {
                            "attachment_id": "attachment-1",
                            "filename": "itinerary.pdf",
                            "mime_type": "application/pdf",
                            "size_bytes": 2048,
                        }
                    ],
                }
            ],
        },
        private_root=private,
        repository_root=repository,
        content_limit=1,
    )

    assert summary["discovered"] == 3
    assert summary["tracked"] == 2
    assert summary["content_ingested"] == 1
    assert not (repository / "matters.sqlite3").exists()
