from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

import pytest

from matters.application.gmail_body_continuation import (
    ARTIFACT_TYPE,
    gmail_no_text_raw_recovery_proof_identity,
    parse_gmail_body_continuation,
)
from matters.application.orchestrator import MatterService
from matters.application.source_workflows import SourceWorkflow
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


def _seed_gmail_metadata(
    service: MatterService,
    message_ids: tuple[str, ...],
    *,
    bodies: dict[str, str] | None = None,
) -> None:
    account_ref = "sha256:" + sha256(b"continuation-account").hexdigest()
    query_fingerprint = (
        "sha256:" + sha256(b"continuation-query").hexdigest()
    )
    manifest = GmailReadManifest(
        scope_id="gmail-scope:continuation",
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
        messages=tuple(
            GmailMessageMetadata(
                message_id=message_id,
                thread_id=f"thread-{index}",
                category="inbox",
                label_ids=("inbox",),
                internal_date=f"2026-07-18T{index:02d}:00:00+00:00",
            )
            for index, message_id in enumerate(message_ids)
        ),
        contents=tuple(
            GmailMessageContent(message_id, body)
            for message_id, body in (bodies or {}).items()
        ),
    )
    SourceWorkflow(service).run_gmail(
        GmailReadOnlyAdapter(
            manifest,
            page_source=lambda _cursor: page,
        )
    )


def _manifest(
    batches: tuple[tuple[str, ...], ...],
    *,
    prior_body_fingerprints: dict[str, str] | None = None,
) -> tuple[bytes, list[dict[str, object]]]:
    prior_body_fingerprints = prior_body_fingerprints or {}
    rows = [
        {
            "message_id": message_id,
            "source_page_identity": f"private-page-{batch_number}",
            "batch_number": batch_number,
            "prior_body_fingerprint": prior_body_fingerprints.get(
                message_id,
                "",
            ),
        }
        for batch_number, message_ids in enumerate(batches, start=1)
        for message_id in message_ids
    ]
    return (
        json.dumps(
            rows,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8"),
        rows,
    )


def _result(
    manifest_bytes: bytes,
    *,
    batch_number: int,
    bodies: dict[str, str],
) -> dict[str, object]:
    return {
        "artifact_type": ARTIFACT_TYPE,
        "manifest_sha256": sha256(manifest_bytes).hexdigest(),
        "batch_number": batch_number,
        "messages": [
            {
                "message_id": message_id,
                "body": body,
                "content_status": "available",
            }
            for message_id, body in bodies.items()
        ],
    }


def _no_text_result(
    manifest_bytes: bytes,
    *,
    batch_number: int,
    message_ids: tuple[str, ...],
) -> dict[str, object]:
    return {
        "artifact_type": ARTIFACT_TYPE,
        "manifest_sha256": sha256(manifest_bytes).hexdigest(),
        "batch_number": batch_number,
        "messages": [
            {
                "message_id": message_id,
                "body": "",
                "content_status": "no_text_body",
                "raw_recovery_proof_identity": (
                    gmail_no_text_raw_recovery_proof_identity(message_id)
                ),
            }
            for message_id in message_ids
        ],
    }


def _history_counts(service: MatterService) -> dict[str, int]:
    assert service.store is not None
    counts: dict[str, int] = {}
    with service.store.connection() as connection:
        for table in ("snapshots", "snapshot_archive"):
            for owner, count in connection.execute(
                f"SELECT owner, COUNT(*) FROM {table} GROUP BY owner"
            ):
                counts[str(owner)] = counts.get(str(owner), 0) + int(count)
    return counts


def test_gmail_body_continuation_imports_only_narrow_owners(
    tmp_path: Path,
) -> None:
    message_ids = ("provider-message-a", "provider-message-b")
    service = _service(tmp_path)
    _seed_gmail_metadata(service, message_ids)
    manifest_bytes, _rows = _manifest((message_ids,))
    connector_result = _result(
        manifest_bytes,
        batch_number=1,
        bodies={
            message_ids[0]: "First private body\nwith two lines",
            message_ids[1]: "Second private body",
        },
    )
    before = _history_counts(service)

    imported = service.import_gmail_body_continuation(
        manifest_bytes=manifest_bytes,
        connector_result=connector_result,
    )

    assert imported.status == "current"
    assert imported.expected_count == imported.imported_count == 2
    assert imported.already_current_count == 0
    assert imported.evidence_anchor_count == 3
    assert imported.receipt_updated_count == 2
    assert imported.next_batch_number is None
    assert imported.has_more is False
    assert not any(
        message_id in json.dumps(asdict(imported))
        for message_id in message_ids
    )

    assert service.store is not None
    grouped = service.store.current_gmail_message_sources_by_provider_ids(
        message_ids
    )
    for message_id in message_ids:
        payload = grouped[message_id][0]
        body = connector_result["messages"][
            message_ids.index(message_id)
        ]["body"]
        assert "body_text" not in payload["content"]
        assert payload["content"]["body_text_fingerprint"] == (
            "sha256:" + sha256(body.encode("utf-8")).hexdigest()
        )
        assert payload["content"]["body_text_byte_length"] == len(
            body.encode("utf-8")
        )
        source_id = payload["source_id"]
        receipt = service.store.current("gmail_message_body", source_id)
        assert receipt is not None
        encoded_receipt = json.dumps(receipt, ensure_ascii=False)
        assert message_id not in encoded_receipt
        assert "private-page-1" not in encoded_receipt
        assert "First private body" not in encoded_receipt
        object_id = payload["external_reference"]["external_id"]
        coverage = service.coverage_ledger.current(object_id)
        assert coverage is not None
        assert coverage.stages["source_version"].status == "current"
        assert coverage.stages["extraction"].status == "current"
        assert coverage.stages["evidence"].status == "current"
        assert coverage.stages["analysis"].status == "pending"

    after = _history_counts(service)
    changed_owners = {
        owner
        for owner, count in after.items()
        if count != before.get(owner, 0)
    }
    assert changed_owners <= {
        "gmail_message_body",
        "source_version",
        "evidence_anchor",
        "object_coverage",
        "object_coverage_summary",
    }
    assert {
        "gmail_message_body",
        "source_version",
        "evidence_anchor",
        "object_coverage",
    } <= changed_owners


def test_gmail_body_continuation_exact_retry_is_no_delta(
    tmp_path: Path,
) -> None:
    message_ids = ("provider-message-a", "provider-message-b")
    service = _service(tmp_path)
    _seed_gmail_metadata(service, message_ids)
    manifest_bytes, _rows = _manifest((message_ids,))
    connector_result = _result(
        manifest_bytes,
        batch_number=1,
        bodies={
            message_ids[0]: "First body",
            message_ids[1]: "Second body",
        },
    )
    service.import_gmail_body_continuation(
        manifest_bytes=manifest_bytes,
        connector_result=connector_result,
    )
    before = _history_counts(service)

    retried = service.import_gmail_body_continuation(
        manifest_bytes=manifest_bytes,
        connector_result=connector_result,
    )

    assert retried.status == "no_delta"
    assert retried.imported_count == 0
    assert retried.already_current_count == 2
    assert retried.receipt_updated_count == 0
    assert _history_counts(service) == before


def test_gmail_body_continuation_resumes_exact_batches(
    tmp_path: Path,
) -> None:
    message_ids = (
        "provider-message-a",
        "provider-message-b",
        "provider-message-c",
    )
    service = _service(tmp_path)
    _seed_gmail_metadata(service, message_ids)
    manifest_bytes, _rows = _manifest(
        (message_ids[:2], message_ids[2:])
    )

    first = service.import_gmail_body_continuation(
        manifest_bytes=manifest_bytes,
        connector_result=_result(
            manifest_bytes,
            batch_number=1,
            bodies={
                message_ids[0]: "First body",
                message_ids[1]: "Second body",
            },
        ),
    )
    second = service.import_gmail_body_continuation(
        manifest_bytes=manifest_bytes,
        connector_result=_result(
            manifest_bytes,
            batch_number=2,
            bodies={message_ids[2]: "Third body"},
        ),
    )

    assert first.next_batch_number == 2
    assert first.has_more is True
    assert second.next_batch_number is None
    assert second.has_more is False
    assert second.imported_count == 1


@pytest.mark.parametrize(
    "mutation,error",
    (
        (
            lambda payload: payload.update({"cursor": "private"}),
            "gmail_body_result_projection_invalid",
        ),
        (
            lambda payload: payload["messages"][0].update(
                {"subject": "private"}
            ),
            "gmail_body_message_projection_invalid",
        ),
        (
            lambda payload: payload.update({"manifest_sha256": "0" * 64}),
            "gmail_body_manifest_hash_mismatch",
        ),
        (
            lambda payload: payload["messages"].append(
                dict(payload["messages"][0])
            ),
            "gmail_body_result_batch_membership_invalid",
        ),
        (
            lambda payload: payload["messages"][0].update({"body": "   "}),
            "gmail_body_content_empty",
        ),
        (
            lambda payload: payload["messages"][0].update(
                {"content_status": "blocked", "body": ""}
            ),
            "gmail_body_content_unavailable",
        ),
        (
            lambda payload: payload["messages"][0].update(
                {"message_id": "foreign-message"}
            ),
            "gmail_body_result_batch_membership_invalid",
        ),
    ),
)
def test_gmail_body_continuation_rejects_nonminimal_or_inexact_results(
    mutation,
    error: str,
) -> None:
    manifest_bytes, _rows = _manifest((("provider-message-a",),))
    payload = _result(
        manifest_bytes,
        batch_number=1,
        bodies={"provider-message-a": "Private body"},
    )
    mutation(payload)

    with pytest.raises(ValueError, match=error):
        parse_gmail_body_continuation(manifest_bytes, payload)


def test_gmail_body_continuation_rejects_manifest_projection_and_budget() -> None:
    manifest_bytes, rows = _manifest(
        (tuple(f"provider-message-{index}" for index in range(21)),)
    )
    with pytest.raises(ValueError, match="gmail_body_batch_budget_exceeded"):
        parse_gmail_body_continuation(
            manifest_bytes,
            _result(
                manifest_bytes,
                batch_number=1,
                bodies={
                    str(row["message_id"]): "Body"
                    for row in rows
                },
            ),
        )

    extra_row = [
        {
            "message_id": "provider-message-a",
            "source_page_identity": "private-page-1",
            "batch_number": 1,
            "cursor": "private",
        }
    ]
    extra_bytes = json.dumps(extra_row).encode("utf-8")
    with pytest.raises(
        ValueError,
        match="gmail_body_manifest_row_projection_invalid",
    ):
        parse_gmail_body_continuation(
            extra_bytes,
            _result(
                extra_bytes,
                batch_number=1,
                bodies={"provider-message-a": "Body"},
            ),
        )


def test_gmail_body_continuation_requires_current_metadata_before_writes(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    manifest_bytes, _rows = _manifest((("provider-message-a",),))
    result = _result(
        manifest_bytes,
        batch_number=1,
        bodies={"provider-message-a": "Private body"},
    )
    before = _history_counts(service)

    with pytest.raises(
        ValueError,
        match="gmail_body_metadata_owner_not_current",
    ):
        service.import_gmail_body_continuation(
            manifest_bytes=manifest_bytes,
            connector_result=result,
        )

    assert _history_counts(service) == before


def test_gmail_body_continuation_rejects_conflicting_current_body(
    tmp_path: Path,
) -> None:
    message_id = "provider-message-a"
    service = _service(tmp_path)
    _seed_gmail_metadata(
        service,
        (message_id,),
        bodies={message_id: "Original provider body"},
    )
    manifest_bytes, _rows = _manifest(((message_id,),))
    before = _history_counts(service)

    with pytest.raises(
        ValueError,
        match="gmail_body_current_content_conflict",
    ):
        service.import_gmail_body_continuation(
            manifest_bytes=manifest_bytes,
            connector_result=_result(
                manifest_bytes,
                batch_number=1,
                bodies={message_id: "Different provider body"},
            ),
        )

    assert _history_counts(service) == before


def test_gmail_body_continuation_reuses_identical_existing_body(
    tmp_path: Path,
) -> None:
    message_id = "provider-message-a"
    service = _service(tmp_path)
    _seed_gmail_metadata(
        service,
        (message_id,),
        bodies={message_id: "Original provider body"},
    )
    manifest_bytes, _rows = _manifest(
        ((message_id,),),
        prior_body_fingerprints={
            message_id: (
                "sha256:"
                + sha256(b"Original provider body").hexdigest()
            )
        },
    )

    result = service.import_gmail_body_continuation(
        manifest_bytes=manifest_bytes,
        connector_result=_result(
            manifest_bytes,
            batch_number=1,
            bodies={message_id: "Original provider body"},
        ),
    )

    assert result.imported_count == 0
    assert result.already_current_count == 1
    assert result.receipt_updated_count == 1


def test_gmail_body_continuation_refreshes_exact_manifest_bound_body(
    tmp_path: Path,
) -> None:
    message_id = "provider-message-a"
    service = _service(tmp_path)
    prior_body = "Prior bounded provider body"
    current_body = "Current complete provider body\nwith scheduled date"
    _seed_gmail_metadata(
        service,
        (message_id,),
        bodies={message_id: prior_body},
    )
    manifest_bytes, _rows = _manifest(
        ((message_id,),),
        prior_body_fingerprints={
            message_id: (
                "sha256:" + sha256(prior_body.encode("utf-8")).hexdigest()
            )
        },
    )

    result = service.import_gmail_body_continuation(
        manifest_bytes=manifest_bytes,
        connector_result=_result(
            manifest_bytes,
            batch_number=1,
            bodies={message_id: current_body},
        ),
    )

    assert result.imported_count == 1
    assert result.already_current_count == 0
    assert service.store is not None
    payload = service.store.current_gmail_message_sources_by_provider_ids(
        (message_id,)
    )[message_id][0]
    assert payload["content"]["body_text_fingerprint"] == (
        "sha256:" + sha256(current_body.encode("utf-8")).hexdigest()
    )
    assert payload["content"]["body_text_byte_length"] == len(
        current_body.encode("utf-8")
    )


def test_gmail_no_text_body_records_only_disposition_and_terminal_coverage(
    tmp_path: Path,
) -> None:
    message_ids = ("provider-message-a", "provider-message-b")
    service = _service(tmp_path)
    _seed_gmail_metadata(service, message_ids)
    manifest_bytes, _rows = _manifest((message_ids,))
    connector_result = _no_text_result(
        manifest_bytes,
        batch_number=1,
        message_ids=message_ids,
    )
    before = _history_counts(service)

    imported = service.import_gmail_body_continuation(
        manifest_bytes=manifest_bytes,
        connector_result=connector_result,
    )

    assert imported.status == "current"
    assert imported.expected_count == 2
    assert imported.imported_count == 0
    assert imported.already_current_count == 0
    assert imported.evidence_anchor_count == 0
    assert imported.receipt_updated_count == 0
    assert imported.no_text_body_count == 2
    assert imported.content_disposition_updated_count == 2

    assert service.store is not None
    grouped = service.store.current_gmail_message_sources_by_provider_ids(
        message_ids
    )
    for message_id in message_ids:
        payload = grouped[message_id][0]
        assert "body_text" not in payload["content"]
        source_id = payload["source_id"]
        assert service.store.current(
            "gmail_message_body",
            source_id,
        ) is None
        disposition = service.store.current(
            "gmail_message_content_disposition",
            source_id,
        )
        assert disposition is not None
        assert disposition["content_status"] == "no_text_body"
        assert disposition["body_present"] is False
        assert disposition["extraction_disposition"] == "not_applicable"
        assert disposition["evidence_disposition"] == "not_applicable"
        encoded = json.dumps(disposition, ensure_ascii=False)
        assert message_id not in encoded
        assert "private-page-1" not in encoded

        object_id = payload["external_reference"]["external_id"]
        coverage = service.coverage_ledger.current(object_id)
        assert coverage is not None
        assert coverage.stages["source_version"].status == "current"
        for stage_id in ("extraction", "evidence", "analysis"):
            pointer = coverage.stages[stage_id]
            assert pointer.status == "not_applicable"
            assert pointer.terminal is True
            assert pointer.owner_id

    after = _history_counts(service)
    changed_owners = {
        owner
        for owner, count in after.items()
        if count != before.get(owner, 0)
    }
    assert changed_owners <= {
        "gmail_message_content_disposition",
        "object_coverage",
        "object_coverage_summary",
    }
    assert {
        "gmail_message_content_disposition",
        "object_coverage",
    } <= changed_owners


def test_gmail_no_text_body_exact_retry_is_no_delta(
    tmp_path: Path,
) -> None:
    message_id = "provider-message-a"
    service = _service(tmp_path)
    _seed_gmail_metadata(service, (message_id,))
    manifest_bytes, _rows = _manifest(((message_id,),))
    connector_result = _no_text_result(
        manifest_bytes,
        batch_number=1,
        message_ids=(message_id,),
    )
    service.import_gmail_body_continuation(
        manifest_bytes=manifest_bytes,
        connector_result=connector_result,
    )
    before = _history_counts(service)

    retried = service.import_gmail_body_continuation(
        manifest_bytes=manifest_bytes,
        connector_result=connector_result,
    )

    assert retried.status == "no_delta"
    assert retried.no_text_body_count == 1
    assert retried.content_disposition_updated_count == 0
    assert _history_counts(service) == before


def test_gmail_body_continuation_accepts_mixed_available_and_no_text(
    tmp_path: Path,
) -> None:
    message_ids = ("provider-message-a", "provider-message-b")
    service = _service(tmp_path)
    _seed_gmail_metadata(service, message_ids)
    manifest_bytes, _rows = _manifest((message_ids,))
    connector_result = _result(
        manifest_bytes,
        batch_number=1,
        bodies={message_ids[0]: "Recovered MIME text"},
    )
    connector_result["messages"].append(
        _no_text_result(
            manifest_bytes,
            batch_number=1,
            message_ids=(message_ids[1],),
        )["messages"][0]
    )

    imported = service.import_gmail_body_continuation(
        manifest_bytes=manifest_bytes,
        connector_result=connector_result,
    )

    assert imported.expected_count == 2
    assert imported.imported_count == 1
    assert imported.evidence_anchor_count == 1
    assert imported.no_text_body_count == 1
    assert imported.content_disposition_updated_count == 1


def test_gmail_no_text_body_rejects_existing_real_body_without_writes(
    tmp_path: Path,
) -> None:
    message_id = "provider-message-a"
    service = _service(tmp_path)
    _seed_gmail_metadata(
        service,
        (message_id,),
        bodies={message_id: "Existing real body"},
    )
    manifest_bytes, _rows = _manifest(((message_id,),))
    before = _history_counts(service)

    with pytest.raises(
        ValueError,
        match="gmail_no_text_body_current_content_conflict",
    ):
        service.import_gmail_body_continuation(
            manifest_bytes=manifest_bytes,
            connector_result=_no_text_result(
                manifest_bytes,
                batch_number=1,
                message_ids=(message_id,),
            ),
        )

    assert _history_counts(service) == before


@pytest.mark.parametrize(
    "mutation,error",
    (
        (
            lambda message: message.pop(
                "raw_recovery_proof_identity"
            ),
            "gmail_no_text_raw_recovery_proof_required",
        ),
        (
            lambda message: message.update({"body": "not empty"}),
            "gmail_no_text_body_must_be_empty",
        ),
        (
            lambda message: message.update(
                {"raw_recovery_proof_identity": "connector-asserted"}
            ),
            "gmail_no_text_raw_recovery_proof_invalid",
        ),
        (
            lambda message: message.update(
                {
                    "raw_recovery_proof_identity": (
                        "sha256:" + "0" * 64
                    )
                }
            ),
            "gmail_no_text_raw_recovery_proof_mismatch",
        ),
        (
            lambda message: message.update(
                {"message_id": "foreign-message"}
            ),
            "gmail_body_result_batch_membership_invalid",
        ),
    ),
)
def test_gmail_no_text_body_rejects_unproven_or_inexact_results(
    mutation,
    error: str,
) -> None:
    message_id = "provider-message-a"
    manifest_bytes, _rows = _manifest(((message_id,),))
    payload = _no_text_result(
        manifest_bytes,
        batch_number=1,
        message_ids=(message_id,),
    )
    mutation(payload["messages"][0])

    with pytest.raises(ValueError, match=error):
        parse_gmail_body_continuation(manifest_bytes, payload)


def test_gmail_available_body_rejects_no_text_proof_field() -> None:
    message_id = "provider-message-a"
    manifest_bytes, _rows = _manifest(((message_id,),))
    payload = _result(
        manifest_bytes,
        batch_number=1,
        bodies={message_id: "Available"},
    )
    payload["messages"][0]["raw_recovery_proof_identity"] = (
        "sha256:" + sha256(b"not-needed").hexdigest()
    )

    with pytest.raises(
        ValueError,
        match="gmail_body_message_projection_invalid",
    ):
        parse_gmail_body_continuation(manifest_bytes, payload)
