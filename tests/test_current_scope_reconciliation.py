from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from matters.application.coverage_ledger import (
    STAGE_ORDER,
    ObjectCoverageLedger,
)
from matters.application.current_scope_reconciliation import (
    GmailCurrentScopeReconciliationOwner,
    RECONCILIATION_RECEIPT_OWNER,
)
from matters.infrastructure.sqlite.store import SQLiteStore
from matters.inventory.owners import (
    CURRENT_TRACKING_POLICY_REVISION,
    CandidateScope,
    InventoryOccurrence,
    InventoryOwner,
    TrackingPolicy,
)
from matters.provenance.source_registry import SourceRegistry
from matters.providers.base import ExternalReference, ProviderEnvelope


def _opaque(value: str) -> str:
    return "sha256:" + sha256(value.encode("utf-8")).hexdigest()


def _owners(tmp_path: Path):
    repository = tmp_path / "repository"
    repository.mkdir()
    store = SQLiteStore(tmp_path / "private", repository)
    inventory = InventoryOwner(store)
    ledger = ObjectCoverageLedger(store)
    owner = GmailCurrentScopeReconciliationOwner(store)
    return store, inventory, ledger, owner


def _scope(scope_id: str, *, root: str, active: bool = True) -> CandidateScope:
    return CandidateScope(
        scope_id=scope_id,
        revision=1,
        provider="gmail",
        root_locator=root,
        object_types=("message",),
        active=active,
    )


def _occurrence(object_id: str, disposition: str) -> InventoryOccurrence:
    return InventoryOccurrence(
        occurrence_id=object_id,
        provider="gmail",
        object_type="message",
        locator=object_id,
        metadata={
            "recommended_disposition": disposition,
            "disposition_reason": f"synthetic {disposition}",
        },
        content_identity=_opaque(f"content:{object_id}:{disposition}"),
    )


def _seed_mismatch(
    inventory: InventoryOwner,
    ledger: ObjectCoverageLedger,
    *,
    object_id: str = "gmail-message:opaque-1",
    target_scope_ids: tuple[str, ...] = ("scope:gmail:tracked",),
    target_root: str | None = None,
    policy: TrackingPolicy | None = None,
):
    root = _opaque("same-private-mailbox")
    policy = policy or TrackingPolicy(
        policy_id="tracking-policy:default",
        revision=CURRENT_TRACKING_POLICY_REVISION,
    )
    old_scope = _scope("scope:gmail:metadata", root=root)
    old_occurrence = _occurrence(object_id, "metadata_only")
    old_snapshot, _ = inventory.reconcile(
        scope=old_scope,
        policy=policy,
        occurrences=(old_occurrence,),
    )
    ledger.reconcile_inventory(
        scope_id=old_scope.scope_id,
        inventory_revision=old_snapshot.revision,
        occurrences=(asdict(old_occurrence),),
        dispositions=(asdict(old_snapshot.dispositions[0]),),
        refresh_summary=False,
    )
    targets = []
    for scope_id in target_scope_ids:
        target_scope = _scope(
            scope_id,
            root=target_root or root,
        )
        target_occurrence = _occurrence(object_id, "tracked")
        target_snapshot, _ = inventory.reconcile(
            scope=target_scope,
            policy=policy,
            occurrences=(target_occurrence,),
        )
        targets.append((target_scope, target_snapshot))
    return object_id, old_scope, old_snapshot, tuple(targets)


def _seed_current_body(
    store: SQLiteStore,
    ledger: ObjectCoverageLedger,
    *,
    object_id: str,
    body: str = "synthetic private message body",
):
    registry = SourceRegistry(store=store)
    envelope = ProviderEnvelope(
        provider="gmail",
        external_id=object_id,
        object_type="gmail_message",
        payload={
            "provider_message_id": "provider-message:opaque",
            "body_text": body,
        },
        references=(
            ExternalReference("gmail", object_id, "gmail_message"),
        ),
        metadata={
            "scope_id": "scope:gmail:metadata",
            "authorization_revision": "authorization:synthetic",
            "query_fingerprint": _opaque("synthetic-query"),
        },
    )
    result = registry.register(envelope, idempotency_key=f"seed:{object_id}")
    source = result.source_version
    assert source is not None
    source_ref = f"{source.source_id}:v{source.version}"
    body_fingerprint = str(source.content["body_text_fingerprint"])
    evidence_ref = f"evidence_anchor_set:{source_ref}:synthetic"
    store.append(
        "gmail_message_body",
        source.source_id,
        1,
        {
            "artifact_type": "gmail_message_body",
            "source_id": source.source_id,
            "source_version_ref": source_ref,
            "manifest_identity": "gmail-body-manifest:synthetic",
            "manifest_sha256": _opaque("manifest"),
            "batch_number": 1,
            "source_page_identity_digest": _opaque("page"),
            "body_digest": body_fingerprint,
            "body_byte_count": len(body.encode("utf-8")),
            "content_status": "available",
            "evidence_set_ref": evidence_ref,
        },
    )
    for stage_id, status, output_ref in (
        ("source_version", "current", source_ref),
        ("extraction", "current", f"gmail_body_extraction:{source_ref}"),
        ("evidence", "current", evidence_ref),
        ("analysis", "pending", f"analysis:{source_ref}"),
    ):
        ledger.mark_stage(
            object_id=object_id,
            stage_id=stage_id,
            status=status,
            input_fingerprint=_opaque(f"stage:{stage_id}"),
            output_ref=output_ref,
            refresh_summary=False,
        )
    return source


def _seed_no_text_disposition(
    store: SQLiteStore,
    *,
    object_id: str,
):
    registry = SourceRegistry(store=store)
    envelope = ProviderEnvelope(
        provider="gmail",
        external_id=object_id,
        object_type="gmail_message",
        payload={"provider_message_id": "provider-message:no-text"},
        references=(
            ExternalReference("gmail", object_id, "gmail_message"),
        ),
        metadata={"scope_id": "scope:gmail:metadata"},
    )
    source = registry.register(
        envelope,
        idempotency_key=f"seed-no-text:{object_id}",
    ).source_version
    assert source is not None
    source_ref = f"{source.source_id}:v{source.version}"
    store.append(
        "gmail_message_content_disposition",
        source.source_id,
        1,
        {
            "artifact_type": "gmail_message_content_disposition",
            "source_id": source.source_id,
            "source_version_ref": source_ref,
            "manifest_identity": "gmail-body-manifest:synthetic-no-text",
            "manifest_sha256": _opaque("manifest-no-text"),
            "batch_number": 1,
            "source_page_identity_digest": _opaque("page-no-text"),
            "content_status": "no_text_body",
            "body_present": False,
            "raw_recovery_proof_identity": _opaque("raw-proof"),
            "extraction_disposition": "not_applicable",
            "evidence_disposition": "not_applicable",
        },
    )
    return source


def test_reconciles_one_newer_tracked_scope_and_preserves_history(
    tmp_path: Path,
) -> None:
    store, inventory, ledger, owner = _owners(tmp_path)
    object_id, _old_scope, _old_snapshot, targets = _seed_mismatch(
        inventory,
        ledger,
    )
    source = _seed_current_body(store, ledger, object_id=object_id)
    prior_history_count = len(store.history("object_coverage", object_id))

    result = owner.reconcile_page(limit=20)

    current = ledger.current(object_id)
    assert current is not None
    assert result.status == "complete"
    assert result.switched_count == 1
    assert current.scope_id == targets[0][0].scope_id
    assert current.inventory_revision == targets[0][1].revision
    assert current.disposition == "tracked"
    assert current.required_stages == STAGE_ORDER
    assert current.next_stage == "content_selection"
    assert current.stages["source_version"].output_ref == (
        f"{source.source_id}:v{source.version}"
    )
    assert "matter" not in current.stages
    assert len(store.history("object_coverage", object_id)) == (
        prior_history_count + 1
    )
    receipt = store.current(RECONCILIATION_RECEIPT_OWNER, object_id)
    assert receipt is not None
    assert receipt["status"] == "current"
    assert receipt["provider_read_performed"] is False

    retried = owner.reconcile_page(limit=20)
    assert retried.status == "no_delta"
    assert retried.inspected_count == 0
    assert len(store.history("object_coverage", object_id)) == (
        prior_history_count + 1
    )


def test_policy_rebase_time_cannot_hide_exact_tracked_content_successor(
    tmp_path: Path,
) -> None:
    store, inventory, ledger, owner = _owners(tmp_path)
    old_policy = TrackingPolicy(
        policy_id="tracking-policy:default",
        revision=CURRENT_TRACKING_POLICY_REVISION - 1,
    )
    object_id, old_scope, _old_snapshot, targets = _seed_mismatch(
        inventory,
        ledger,
        policy=old_policy,
    )
    source = _seed_current_body(store, ledger, object_id=object_id)
    current_policy = TrackingPolicy(
        policy_id="tracking-policy:default",
        revision=CURRENT_TRACKING_POLICY_REVISION,
    )
    target_occurrence = _occurrence(object_id, "tracked")
    target_snapshot, _ = inventory.reconcile(
        scope=targets[0][0],
        policy=current_policy,
        occurrences=(target_occurrence,),
    )
    bound_occurrence = _occurrence(object_id, "metadata_only")
    bound_snapshot, _ = inventory.reconcile(
        scope=old_scope,
        policy=current_policy,
        occurrences=(bound_occurrence,),
    )
    ledger.reconcile_inventory(
        scope_id=old_scope.scope_id,
        inventory_revision=bound_snapshot.revision,
        occurrences=(asdict(bound_occurrence),),
        dispositions=(asdict(bound_snapshot.dispositions[0]),),
        refresh_summary=False,
    )
    records, _ = store.gmail_current_scope_reconciliation_page(limit=20)
    assert records[0]["bound_inventory"]["created_at"] > (
        records[0]["tracked_candidates"][0]["inventory"]["created_at"]
    )

    result = owner.reconcile_page(limit=20)

    current = ledger.current(object_id)
    assert current is not None
    assert result.switched_count == 1
    assert current.scope_id == targets[0][0].scope_id
    assert current.inventory_revision == target_snapshot.revision
    assert current.stages["source_version"].output_ref == (
        f"{source.source_id}:v{source.version}"
    )


def test_missing_body_is_explicit_pending_without_coverage_switch(
    tmp_path: Path,
) -> None:
    store, inventory, ledger, owner = _owners(tmp_path)
    object_id, old_scope, old_snapshot, _targets = _seed_mismatch(
        inventory,
        ledger,
    )
    registry = SourceRegistry(store=store)
    registry.register(
        ProviderEnvelope(
            provider="gmail",
            external_id=object_id,
            object_type="gmail_message",
            payload={"provider_message_id": "provider-message:metadata-only"},
            references=(
                ExternalReference("gmail", object_id, "gmail_message"),
            ),
            metadata={"scope_id": old_scope.scope_id},
        ),
        idempotency_key="metadata-only-source",
    )

    result = owner.reconcile_page(limit=20)

    current = ledger.current(object_id)
    assert current is not None
    assert result.status == "complete_with_gaps"
    assert result.pending_count == 1
    assert current.scope_id == old_scope.scope_id
    assert current.inventory_revision == old_snapshot.revision
    assert current.disposition == "metadata_only"
    receipt = store.current(RECONCILIATION_RECEIPT_OWNER, object_id)
    assert receipt is not None
    assert receipt["status"] == "pending"
    assert receipt["failure_class"] == "gmail_body_not_current"
    assert receipt["provider_read_performed"] is False


def test_current_digest_and_evidence_rebase_exact_body_receipt_without_copy(
    tmp_path: Path,
) -> None:
    store, inventory, ledger, owner = _owners(tmp_path)
    object_id, _old_scope, _old_snapshot, targets = _seed_mismatch(
        inventory,
        ledger,
    )
    registry = SourceRegistry(store=store)
    source = registry.register(
        ProviderEnvelope(
            provider="gmail",
            external_id=object_id,
            object_type="gmail_message",
            payload={
                "provider_message_id": "provider-message:opaque",
                "body_text": "synthetic private message body",
            },
            references=(
                ExternalReference("gmail", object_id, "gmail_message"),
            ),
            metadata={"scope_id": "scope:gmail:metadata"},
        ),
        idempotency_key=f"receipt-rebase:{object_id}",
    ).source_version
    assert source is not None
    evidence_id = (
        f"evidence:{source.source_id}:{source.version}:synthetic"
    )
    store.append(
        "evidence_anchor",
        evidence_id,
        1,
        {
            "evidence_id": evidence_id,
            "source_id": source.source_id,
            "source_version": source.version,
            "location": {"field": "body"},
            "text": "synthetic evidence",
            "modality": "reported",
            "current": True,
        },
    )

    rebased = owner.rebase_content_receipts_page(limit=20)

    assert rebased.status == "current"
    assert rebased.rebased_count == 1
    receipt = store.current("gmail_message_body", source.source_id)
    assert receipt is not None
    assert receipt["source_version_ref"] == (
        f"{source.source_id}:v{source.version}"
    )
    assert receipt["body_digest"] == source.content[
        "body_text_fingerprint"
    ]
    assert receipt["provider_read_performed"] is False
    assert receipt["proof_basis"] == (
        "registry_current_digest_length_and_current_evidence"
    )
    assert "body_text" not in receipt

    result = owner.reconcile_page(limit=20)
    current = ledger.current(object_id)
    assert current is not None
    assert result.switched_count == 1
    assert current.scope_id == targets[0][0].scope_id


def test_multiple_current_tracked_scopes_block_as_ambiguous(
    tmp_path: Path,
) -> None:
    store, inventory, ledger, owner = _owners(tmp_path)
    object_id, old_scope, _old_snapshot, _targets = _seed_mismatch(
        inventory,
        ledger,
        target_scope_ids=("scope:gmail:tracked-a", "scope:gmail:tracked-b"),
    )
    _seed_current_body(store, ledger, object_id=object_id)

    result = owner.reconcile_page(limit=20)

    current = ledger.current(object_id)
    assert current is not None
    assert result.blocked_count == 1
    assert current.scope_id == old_scope.scope_id
    receipt = store.current(RECONCILIATION_RECEIPT_OWNER, object_id)
    assert receipt is not None
    assert receipt["status"] == "blocked"
    assert receipt["failure_class"] == "tracked_scope_ambiguous"


def test_different_mailbox_scope_blocks_authorization_conflict(
    tmp_path: Path,
) -> None:
    store, inventory, ledger, owner = _owners(tmp_path)
    object_id, old_scope, _old_snapshot, _targets = _seed_mismatch(
        inventory,
        ledger,
        target_root=_opaque("different-private-mailbox"),
    )
    _seed_current_body(store, ledger, object_id=object_id)

    result = owner.reconcile_page(limit=20)

    current = ledger.current(object_id)
    assert current is not None
    assert result.blocked_count == 1
    assert current.scope_id == old_scope.scope_id
    receipt = store.current(RECONCILIATION_RECEIPT_OWNER, object_id)
    assert receipt is not None
    assert receipt["failure_class"] == "authorization_scope_conflict"


def test_proven_no_text_body_is_terminal_content_not_missing_body(
    tmp_path: Path,
) -> None:
    store, inventory, ledger, owner = _owners(tmp_path)
    object_id, _old_scope, _old_snapshot, targets = _seed_mismatch(
        inventory,
        ledger,
    )
    _seed_no_text_disposition(store, object_id=object_id)

    result = owner.reconcile_page(limit=20)

    current = ledger.current(object_id)
    assert current is not None
    assert result.switched_count == 1
    assert current.scope_id == targets[0][0].scope_id
    assert current.stages["extraction"].status == "not_applicable"
    assert current.stages["evidence"].status == "not_applicable"
    receipt = store.current(RECONCILIATION_RECEIPT_OWNER, object_id)
    assert receipt is not None
    assert receipt["content_status"] == "no_text_body"


def test_stale_context_cas_never_overwrites_newer_authority(
    tmp_path: Path,
) -> None:
    store, inventory, ledger, owner = _owners(tmp_path)
    object_id, old_scope, _old_snapshot, targets = _seed_mismatch(
        inventory,
        ledger,
    )
    _seed_current_body(store, ledger, object_id=object_id)
    records, _ = store.gmail_current_scope_reconciliation_page(limit=20)
    assert len(records) == 1
    decision = owner._decide(records[0])
    assert decision.coverage is not None

    target = targets[0][0]
    store.append(
        "candidate_scope",
        target.scope_id,
        2,
        {
            **asdict(target),
            "revision": 2,
        },
    )
    committed = store.commit_gmail_current_scope_reconciliation(
        object_id=object_id,
        expected_context_fingerprint=records[0]["context_fingerprint"],
        receipt_payload=decision.receipt,
        coverage_payload=decision.coverage,
    )

    current = ledger.current(object_id)
    assert current is not None
    assert committed["status"] == "stale"
    assert current.scope_id == old_scope.scope_id
    assert store.current(RECONCILIATION_RECEIPT_OWNER, object_id) is None


def test_keyset_page_can_be_resumed_without_reprocessing_prior_object(
    tmp_path: Path,
) -> None:
    store, inventory, ledger, owner = _owners(tmp_path)
    policy = TrackingPolicy(
        policy_id="tracking-policy:default",
        revision=CURRENT_TRACKING_POLICY_REVISION,
    )
    first_id, *_ = _seed_mismatch(
        inventory,
        ledger,
        object_id="gmail-message:opaque-1",
        target_scope_ids=("scope:gmail:tracked-1",),
        policy=policy,
    )
    second_id, *_ = _seed_mismatch(
        inventory,
        ledger,
        object_id="gmail-message:opaque-2",
        target_scope_ids=("scope:gmail:tracked-2",),
        policy=policy,
    )
    _seed_current_body(store, ledger, object_id=first_id, body="first body")
    _seed_current_body(store, ledger, object_id=second_id, body="second body")

    first_page = owner.reconcile_page(limit=1)
    second_page = owner.reconcile_page(
        after_object_id=first_page.next_after_object_id,
        limit=1,
    )

    assert first_page.status == "partial"
    assert first_page.switched_count == 1
    assert first_page.next_after_object_id == first_id
    assert second_page.status == "complete"
    assert second_page.switched_count == 1
    assert second_page.next_after_object_id == ""
    assert ledger.current(first_id).disposition == "tracked"  # type: ignore[union-attr]
    assert ledger.current(second_id).disposition == "tracked"  # type: ignore[union-attr]
