from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import pytest

from matters.application.orchestrator import MatterService
from matters.application.source_workflows import SourceWorkflow
from matters.inventory.owners import (
    CandidateScope,
    InventoryOccurrence,
    TrackingPolicy,
)
from matters.providers.gmail import (
    GmailAuthorizedPage,
    GmailMessageMetadata,
    GmailReadManifest,
    GmailReadOnlyAdapter,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = REPOSITORY_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


audit_module = _load_script("audit_gmail_page_chain")
ingest_export_module = _load_script("ingest_gmail_export")
ingest_pages_module = _load_script("ingest_gmail_pages")
runtime_audit_module = _load_script("audit_gmail_runtime")
retire_module = _load_script("retire_gmail_pseudo_thread")


def _page(
    messages: list[dict[str, Any]],
    *,
    requested: object = "",
    next_cursor: object = "",
    terminal: bool = True,
    include_requested: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "query": "synthetic-query",
        "account": "synthetic-account@example.invalid",
        "authorization_revision": "authorization:synthetic",
        "policy_revision": "policy:synthetic",
        "next_page_token": next_cursor,
        "terminal": terminal,
        "coverage": "complete" if terminal else "partial",
        "messages": messages,
    }
    if include_requested:
        payload["requested_page_token"] = requested
    return payload


def _message(
    message_id: str,
    *,
    thread_id: object = "thread-1",
    email_ts: object = "2026-01-01T00:00:00Z",
    labels: object = None,
    body: object = None,
    subject: str = "Synthetic",
) -> dict[str, Any]:
    return {
        "id": message_id,
        "thread_id": thread_id,
        "email_ts": email_ts,
        "labels": ["INBOX"] if labels is None else labels,
        "body": body,
        "subject": subject,
        "from_": "sender@example.invalid",
        "to": ["recipient@example.invalid"],
        "snippet": "synthetic snippet",
        "attachments": [],
    }


def test_identity_only_row_never_creates_synthetic_none_thread(tmp_path):
    payload = _page(
        [
            _message(
                "identity-only",
                thread_id=None,
                email_ts=None,
                labels=[],
            )
        ]
    )
    repository = tmp_path / "repository"
    repository.mkdir()
    result = ingest_export_module.ingest(
        payload,
        private_root=tmp_path / "private",
        repository_root=repository,
        content_limit=10,
    )
    service = MatterService(
        repository_root=repository,
        private_root=tmp_path / "private",
    )
    manifest = ingest_export_module.manifest_from_payload(payload)
    snapshot = service.inventory.latest_snapshot(manifest.scope_id)

    assert result["discovered"] == 1
    assert result["metadata_only"] == 1
    assert snapshot is not None
    assert {item.object_type for item in snapshot.occurrences} == {
        "message"
    }
    serialized = repr(snapshot.occurrences)
    assert "gmail:thread:9bd5f49a0ce96dfea10c2007" not in serialized
    assert "'provider_thread_id': 'None'" not in serialized
    assert "'internal_date': 'None'" not in serialized


def test_identity_only_adapter_projection_has_no_parent_thread():
    from hashlib import sha256

    opaque = lambda value: "sha256:" + sha256(value.encode()).hexdigest()
    manifest = GmailReadManifest(
        scope_id="gmail-scope:synthetic",
        account_ref=opaque("account"),
        authorization_revision="authorization:1",
        query_fingerprint=opaque("query"),
        policy_revision="policy:1",
    )
    message = GmailMessageMetadata(
        "message-id",
        "",
        "unknown",
        (),
        "",
        identity_only=True,
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
        messages=(message,),
    )
    adapter = GmailReadOnlyAdapter(manifest)
    discovery = adapter.accept_page(page)

    assert len(discovery.items) == 1
    item = discovery.items[0]
    assert item.recommended_disposition == "metadata_only"
    assert item.reason == "pending_metadata"
    assert "parent_external_id" not in item.envelope.metadata
    assert len(item.envelope.references) == 1


def test_missing_labels_remains_identity_only_after_page_normalization():
    row = _message("missing-labels")
    row["labels"] = None
    chain = audit_module.audit_page_payloads([_page([row])])
    manifest = ingest_export_module.manifest_from_payload(chain.pages[0])
    page = ingest_export_module.authorized_page_from_payload(
        chain.pages[0],
        manifest,
    )

    assert chain.report["identity_only_count"] == 1
    assert page.messages[0].identity_only is True
    assert page.messages[0].category == "unknown"


def test_connector_manifest_preserves_optional_fixed_authorized_from():
    payload = _page([_message("message-1")])
    payload["authorized_from"] = "2025-07-20"

    manifest = ingest_export_module.manifest_from_payload(payload)

    assert manifest.authorized_from == "2025-07-20"


def test_page_chain_rejects_authorized_from_narrowing_between_pages():
    first = _page(
        [_message("message-1")],
        next_cursor="cursor-2",
        terminal=False,
    )
    first["authorized_from"] = "2025-07-20"
    second = _page(
        [_message("message-2")],
        requested="cursor-2",
    )
    second["authorized_from"] = "2025-07-21"

    with pytest.raises(
        audit_module.GmailPageChainError,
        match="gmail_page_manifest_conflict",
    ):
        audit_module.audit_page_payloads([first, second])


def test_metadata_only_refresh_does_not_replace_current_message_body(
    tmp_path,
):
    full = _page([_message("message-1", body="preserved body")])
    shallow = _page([_message("message-1", body=None)])
    private_root = tmp_path / "private"
    repository = tmp_path / "repository"
    repository.mkdir()

    ingest_export_module.ingest(
        full,
        private_root=private_root,
        repository_root=repository,
        content_limit=10,
    )
    service = MatterService(
        repository_root=repository,
        private_root=private_root,
    )
    before = service.current_records("source_version")
    assert len(before) == 1
    before_content = dict(before[0]["content"])
    assert before_content["body_text_byte_length"] == len("preserved body")
    assert before_content["body_text_fingerprint"]
    assert "body_text" not in before_content

    ingest_export_module.ingest(
        shallow,
        private_root=private_root,
        repository_root=repository,
        content_limit=10,
    )
    service = MatterService(
        repository_root=repository,
        private_root=private_root,
    )
    sources = service.current_records("source_version")

    assert len(sources) == 1
    assert sources[0]["content"] == before_content


def test_verified_terminal_chain_and_richer_duplicate_merge():
    first = _page(
        [_message("message-1", body="body")],
        next_cursor="cursor-2",
        terminal=False,
    )
    second = _page(
        [_message("message-1", body=None)],
        requested="cursor-2",
    )

    chain = audit_module.audit_page_payloads([first, second])

    assert chain.report["status"] == "complete"
    assert chain.report["safe_terminal_coverage"] is True
    assert chain.report["duplicate_message_count"] == 1
    assert chain.report["unique_message_count"] == 1
    assert chain.report["content_bearing_count"] == 1
    assert chain.pages[0]["messages"][0]["body"] == "body"
    assert chain.pages[1]["messages"] == []


def test_terminal_chain_without_requested_cursors_is_blocked():
    chain = audit_module.audit_page_payloads(
        [
            _page(
                [_message("message-1")],
                include_requested=False,
                next_cursor="cursor-2",
                terminal=False,
            ),
            _page(
                [_message("message-2")],
                include_requested=False,
            ),
        ]
    )

    assert chain.report["status"] == "blocked"
    assert chain.report["cursor_chain_verified"] is False
    with pytest.raises(
        audit_module.GmailPageChainError,
        match="coverage_blocked",
    ):
        ingest_pages_module.ingest_page_chain(
            chain,
            private_root=Path("not-used"),
            repository_root=REPOSITORY_ROOT,
            content_limit=0,
        )


def test_terminal_page_before_end_is_rejected():
    with pytest.raises(
        audit_module.GmailPageChainError,
        match="terminal_page_not_last",
    ):
        audit_module.audit_page_payloads(
            [
                _page([_message("message-1")]),
                _page([_message("message-2")]),
            ]
        )


def test_conflicting_duplicate_blocks_without_exposing_message_id():
    secret_id = "private-message-id-never-report"
    first = _page(
        [_message(secret_id, body="first")],
        next_cursor="cursor-2",
        terminal=False,
    )
    second = _page(
        [_message(secret_id, body="different")],
        requested="cursor-2",
    )

    with pytest.raises(audit_module.GmailPageChainError) as captured:
        audit_module.audit_page_payloads([first, second])

    assert "gmail_message_field_conflict" in str(captured.value)
    assert secret_id not in str(captured.value)


def test_equivalent_naive_and_utc_timestamps_merge_without_conflict():
    first = _page(
        [_message("message-1", email_ts="2026-07-14T10:45:46+00:00")],
        next_cursor="cursor-2",
        terminal=False,
    )
    second = _page(
        [_message("message-1", email_ts="2026-07-14T10:45:46")],
        requested="cursor-2",
    )

    chain = audit_module.audit_page_payloads([first, second])

    assert chain.report["unique_message_count"] == 1
    assert (
        chain.pages[0]["messages"][0]["email_ts"]
        == "2026-07-14T10:45:46+00:00"
    )


def test_verified_pages_are_ingested_in_one_snapshot_without_false_deletion(
    tmp_path,
):
    chain = audit_module.audit_page_payloads(
        [
            _page(
                [_message("message-1", thread_id="thread-1")],
                next_cursor="cursor-2",
                terminal=False,
            ),
            _page(
                [_message("message-2", thread_id="thread-2")],
                requested="cursor-2",
            ),
        ]
    )

    repository = tmp_path / "repository"
    repository.mkdir()
    first_page_chain = audit_module.audit_page_payloads([chain.pages[0]])
    assert first_page_chain.report["cursor_chain_verified"] is True
    with pytest.raises(
        audit_module.GmailPageChainError,
        match="cursor_chain_unverified",
    ):
        ingest_pages_module.ingest_page_chain(
            first_page_chain,
            private_root=tmp_path / "blocked",
            repository_root=repository,
            content_limit=10,
        )
    first_output = ingest_pages_module.ingest_page_chain(
        first_page_chain,
        private_root=tmp_path / "private",
        repository_root=repository,
        content_limit=10,
        allow_unverified_partial=True,
    )
    assert first_output["claim"] == "explicit_bounded_partial_chain"

    output = ingest_pages_module.ingest_page_chain(
        chain,
        private_root=tmp_path / "private",
        repository_root=repository,
        content_limit=10,
    )
    service = MatterService(
        repository_root=repository,
        private_root=tmp_path / "private",
    )
    manifest = ingest_export_module.manifest_from_payload(chain.pages[0])
    snapshot = service.inventory.latest_snapshot(manifest.scope_id)
    assert snapshot is not None
    occurrence_types = [
        item.object_type for item in snapshot.occurrences
    ]

    assert output["claim"] == "verified_terminal_chain"
    assert output["result"]["discovered"] == 4
    assert output["inventory_delta"]["deleted_count"] == 0
    assert occurrence_types.count("message") == 2
    assert occurrence_types.count("thread") == 2


def test_terminal_page_chain_reconciles_metadata_owners_in_bounded_pages(
    tmp_path,
):
    chain = audit_module.audit_page_payloads(
        [
            _page(
                [
                    _message(
                        "metadata-message-1",
                        thread_id=None,
                        email_ts=None,
                        labels=[],
                    ),
                    _message(
                        "metadata-message-2",
                        thread_id=None,
                        email_ts=None,
                        labels=[],
                    ),
                ]
            )
        ]
    )
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    repository.mkdir()
    adapter = ingest_pages_module._build_adapter(
        chain,
        allow_unverified_partial=False,
    )
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )
    SourceWorkflow(service).run_gmail(
        adapter,
        metadata_limit=0,
    )
    assert service.current_records("source_version") == ()

    first = ingest_pages_module.reconcile_page_chain_metadata(
        chain,
        private_root=private,
        repository_root=repository,
        metadata_limit=1,
    )

    assert first["claim"] == "verified_terminal_chain"
    first_result = first["metadata_reconciliation"]
    assert first_result["registered_count"] == 1
    assert first_result["remaining_count"] == 1
    assert first_result["next_after_object_id"]
    assert len(service.current_records("source_version")) == 1
    assert service.current_records("evidence_anchor") == ()
    assert service.current_records("matter") == ()

    second = ingest_pages_module.reconcile_page_chain_metadata(
        chain,
        private_root=private,
        repository_root=repository,
        after_object_id=first_result["next_after_object_id"],
        metadata_limit=1,
    )
    assert second["metadata_reconciliation"]["registered_count"] == 1
    assert second["metadata_reconciliation"]["remaining_count"] == 0
    assert second["metadata_reconciliation"]["next_after_object_id"] == ""
    assert len(service.current_records("source_version")) == 2

    retry = ingest_pages_module.reconcile_page_chain_metadata(
        chain,
        private_root=private,
        repository_root=repository,
        metadata_limit=1,
    )
    assert retry["metadata_reconciliation"]["already_current_count"] == 1
    assert retry["metadata_reconciliation"]["coverage_updated_count"] == 0
    assert len(service.current_records("source_version")) == 2


def test_metadata_owner_reconciliation_rejects_partial_page_chain(tmp_path):
    chain = audit_module.audit_page_payloads(
        [
            _page(
                [_message("metadata-message")],
                include_requested=False,
                next_cursor="cursor-2",
                terminal=False,
            )
        ]
    )
    assert chain.report["safe_terminal_coverage"] is False

    with pytest.raises(
        audit_module.GmailPageChainError,
        match="cursor_chain_unverified",
    ):
        ingest_pages_module.reconcile_page_chain_metadata(
            chain,
            private_root=tmp_path / "private",
            repository_root=tmp_path / "repository",
        )


def test_metadata_owner_reconciliation_cli_uses_exact_terminal_chain(
    tmp_path,
    monkeypatch,
    capsys,
):
    payload = _page(
        [
            _message(
                "metadata-cli-message",
                thread_id=None,
                email_ts=None,
                labels=[],
            )
        ]
    )
    chain = audit_module.audit_page_payloads([payload])
    private = tmp_path / "private"
    service = MatterService(
        repository_root=REPOSITORY_ROOT,
        private_root=private,
    )
    SourceWorkflow(service).run_gmail(
        ingest_pages_module._build_adapter(
            chain,
            allow_unverified_partial=False,
        ),
        metadata_limit=0,
    )
    page_path = tmp_path / "terminal-page.json"
    page_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ingest_gmail_pages.py",
            "--page",
            str(page_path),
            "--private-root",
            str(private),
            "--metadata-reconcile-only",
            "--metadata-limit",
            "1",
        ],
    )

    assert ingest_pages_module.main() == 0

    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert output["claim"] == "verified_terminal_chain"
    result = output["metadata_reconciliation"]
    assert result["registered_count"] == 1
    assert result["remaining_count"] == 0


def test_nonterminal_legacy_pages_require_explicit_partial_flag(tmp_path):
    chain = audit_module.audit_page_payloads(
        [
            _page(
                [_message("message-1")],
                include_requested=False,
                next_cursor="cursor-2",
                terminal=False,
            ),
            _page(
                [_message("message-2")],
                include_requested=False,
                next_cursor="cursor-3",
                terminal=False,
            ),
        ]
    )
    assert chain.report["status"] == "partial"

    with pytest.raises(
        audit_module.GmailPageChainError,
        match="cursor_chain_unverified",
    ):
        ingest_pages_module.ingest_page_chain(
            chain,
            private_root=tmp_path / "blocked",
            repository_root=REPOSITORY_ROOT,
            content_limit=0,
        )

    repository = tmp_path / "repository"
    repository.mkdir()
    output = ingest_pages_module.ingest_page_chain(
        chain,
        private_root=tmp_path / "allowed",
        repository_root=repository,
        content_limit=0,
        allow_unverified_partial=True,
    )
    assert output["claim"] == "explicit_bounded_partial_chain"
    assert output["result"]["terminal"] is False
    assert "gmail_partial_inventory_page" in output["result"]["gaps"]


def test_audit_only_partial_chain_is_explicit_failure(
    tmp_path,
    monkeypatch,
    capsys,
):
    page_path = tmp_path / "partial-page.json"
    page_path.write_text(
        json.dumps(
            _page(
                [_message("message-1")],
                next_cursor="cursor-2",
                terminal=False,
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ingest_gmail_pages.py",
            "--page",
            str(page_path),
            "--private-root",
            str(tmp_path / "private"),
            "--audit-only",
        ],
    )

    assert ingest_pages_module.main() == 2

    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is False
    assert output["status"] == "partial"
    assert output["reason"] == "gmail_page_chain_not_terminal_or_verified"


def test_runtime_audit_counts_body_fingerprints_not_retired_body_text(
    tmp_path,
):
    payload = _page([_message("message-1", body="private body")])
    repository = tmp_path / "repository"
    private_root = tmp_path / "private"
    repository.mkdir()
    ingest_export_module.ingest(
        payload,
        private_root=private_root,
        repository_root=repository,
        content_limit=10,
    )
    page_path = tmp_path / "scope-page.json"
    page_path.write_text(json.dumps(payload), encoding="utf-8")

    report = runtime_audit_module.audit_runtime(
        repository_root=repository,
        private_root=private_root,
        scope_pages=(page_path,),
    )

    assert report["gmail_current_message_source_count"] == 1
    assert report["gmail_current_body_source_count"] == 1


def test_pseudo_thread_retirement_requires_zero_refs_and_is_isolated(
    tmp_path,
):
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    repository.mkdir()
    page_payload = _page([])
    page_path = tmp_path / "scope-page.json"
    page_path.write_text(
        json.dumps(page_payload),
        encoding="utf-8",
    )
    manifest = ingest_export_module.manifest_from_payload(page_payload)
    pseudo_id = retire_module._pseudo_thread_id(manifest.account_ref)
    message = InventoryOccurrence(
        occurrence_id="gmail:message:synthetic",
        provider="gmail",
        object_type="message",
        locator="gmail:message:synthetic",
        metadata={"coverage": "partial"},
        parent_occurrence_id=pseudo_id,
    )
    pseudo = InventoryOccurrence(
        occurrence_id=pseudo_id,
        provider="gmail",
        object_type="thread",
        locator=pseudo_id,
        metadata={"coverage": "partial"},
    )
    scope = CandidateScope(
        scope_id=manifest.scope_id,
        revision=1,
        provider="gmail",
        root_locator=manifest.account_ref,
        object_types=("message", "thread"),
    )
    policy = TrackingPolicy("tracking-policy:default", 1)
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )
    service.reconcile_inventory(
        scope=scope,
        policy=policy,
        occurrences=(message, pseudo),
    )

    with pytest.raises(RuntimeError, match="still_referenced"):
        retire_module.retire_pseudo_thread(
            repository_root=repository,
            private_root=private,
            scope_page=page_path,
        )

    service.reconcile_inventory(
        scope=scope,
        policy=policy,
        occurrences=(
            InventoryOccurrence(
                occurrence_id=message.occurrence_id,
                provider=message.provider,
                object_type=message.object_type,
                locator=message.locator,
                metadata=message.metadata,
            ),
            pseudo,
        ),
    )
    result = retire_module.retire_pseudo_thread(
        repository_root=repository,
        private_root=private,
        scope_page=page_path,
    )
    current = MatterService(
        repository_root=repository,
        private_root=private,
    ).inventory.latest_snapshot(manifest.scope_id)

    assert result["status"] == "retired"
    assert result["retired_count"] == 1
    assert current is not None
    assert {item.occurrence_id for item in current.occurrences} == {
        message.occurrence_id
    }
