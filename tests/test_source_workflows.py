from hashlib import sha256
from pathlib import Path

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


def _service(tmp_path: Path) -> MatterService:
    repository = tmp_path / "repository"
    repository.mkdir()
    return MatterService(
        repository_root=repository,
        private_root=tmp_path / "private-runtime",
    )


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
        FilesystemReadOnlyAdapter(source_root, page_size=1)
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
        FilesystemReadOnlyAdapter(source_root, page_size=1)
    )
    assert second.changes.no_delta is True
    assert second.summary.metadata_registered == 0
    assert second.summary.content_ingested == 1


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
    assert result.summary.not_tracked == 1
    disposition = result.snapshot.dispositions[0]
    assert disposition.status == "not_tracked"
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
