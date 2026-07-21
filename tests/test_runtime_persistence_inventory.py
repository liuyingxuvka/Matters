import json
from pathlib import Path

import pytest

from matters.application.coverage_ledger import STAGE_ORDER
from matters.application.orchestrator import MatterService
from matters.config import RuntimeConfig
from matters.inventory.owners import (
    CandidateScope,
    InventoryOccurrence,
    TrackingPolicy,
    occurrence_id,
)
from matters.providers.base import ProviderEnvelope
from matters.infrastructure.sqlite.store import SQLiteStore
from conftest import scope_for


def _occurrence(
    locator: str,
    *,
    content_identity: str,
    size: int = 4,
    object_type: str = "file",
    discovery_reason: str = "enumerated",
) -> InventoryOccurrence:
    return InventoryOccurrence(
        occurrence_id=occurrence_id("filesystem", object_type, locator),
        provider="filesystem",
        object_type=object_type,
        locator=locator,
        metadata={"size": size, "modified_ns": size},
        content_identity=content_identity,
        discovery_reason=discovery_reason,
    )


def test_absent_private_root_is_visible_and_non_writing(tmp_path, monkeypatch):
    monkeypatch.delenv("MATTERS_HOME", raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    config = RuntimeConfig.resolve(repository_root=repo)
    assert config.private_status().status == "not_configured"
    assert list(tmp_path.iterdir()) == [repo]
    with pytest.raises(ValueError):
        config.activate_private_root()


def test_private_root_inside_or_containing_repository_is_blocked(tmp_path):
    repo = tmp_path / "workspace" / "repo"
    repo.mkdir(parents=True)
    inside = RuntimeConfig.resolve(
        repository_root=repo,
        private_root=repo / "private",
    )
    containing = RuntimeConfig.resolve(
        repository_root=repo,
        private_root=repo.parent,
    )
    assert inside.private_status().status == "blocked"
    assert containing.private_status().status == "blocked"


def test_source_versions_and_idempotency_survive_restart(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "private"
    repo.mkdir()
    envelope = ProviderEnvelope(
        provider="pasted_text",
        external_id="synthetic-1",
        object_type="text",
        payload={"summary": "Synthetic task", "explicit_goal_or_obligation": True},
    )
    first_service = MatterService(private_root=home, repository_root=repo)
    first = first_service.process_envelope(
        scope=scope_for(envelope),
        envelope=envelope,
        idempotency_key="stable-key",
    )
    restarted = MatterService(private_root=home, repository_root=repo)
    retry = restarted.process_envelope(
        scope=scope_for(envelope),
        envelope=envelope,
        idempotency_key="stable-key",
    )
    assert first.registration.status == "source_version_created"
    assert retry.registration.status == "no_delta"
    assert retry.registration.reason == "durable retry"
    assert len(restarted.sources.history(first.registration.source_version.source_id)) == 1


def test_source_processing_receipt_never_persists_transient_provider_body(
    tmp_path,
):
    repo = tmp_path / "repo"
    home = tmp_path / "private"
    repo.mkdir()
    secret_body = "complete private source body that must remain transient"
    envelope = ProviderEnvelope(
        provider="pasted_text",
        external_id="transient-body",
        object_type="text",
        payload={
            "summary": "Transient body storage check",
            "explicit_goal_or_obligation": True,
            "body_text": secret_body,
        },
    )
    service = MatterService(private_root=home, repository_root=repo)

    result = service.process_envelope(
        scope=scope_for(envelope),
        envelope=envelope,
        idempotency_key="transient-body",
    )

    assert result.registration is not None
    assert result.registration.source_version is not None
    assert (
        result.registration.source_version.transient_content["body_text"]
        == secret_body
    )
    durable = json.dumps(
        service.current_records("source_processing_result"),
        ensure_ascii=False,
        sort_keys=True,
    )
    assert secret_body not in durable
    assert "transient_content" not in durable
    source = service.current_records("source_version")[0]
    assert "body_text" not in source["content"]
    assert source["content"]["body_text_byte_length"] == len(
        secret_body.encode("utf-8")
    )


def test_inventory_move_policy_change_and_staleness_are_durable(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "private"
    repo.mkdir()
    service = MatterService(private_root=home, repository_root=repo)
    scope = CandidateScope(
        "scope:docs",
        1,
        "filesystem",
        str(tmp_path / "Documents"),
        ("file",),
    )
    policy_v1 = TrackingPolicy("policy:default", 1)
    original = _occurrence("Documents/plan.txt", content_identity="content:a")
    first, first_changes = service.reconcile_inventory(
        scope=scope,
        policy=policy_v1,
        occurrences=(original,),
    )
    assert first_changes.added == (original.occurrence_id,)

    moved = _occurrence("Documents/archive/plan.txt", content_identity="content:a")
    second, second_changes = service.reconcile_inventory(
        scope=scope,
        policy=policy_v1,
        occurrences=(moved,),
    )
    assert second_changes.moved == ((original.occurrence_id, moved.occurrence_id),)
    assert service.current_records("dependency_freshness")

    policy_v2 = TrackingPolicy("policy:default", 2)
    _, third_changes = service.reconcile_inventory(
        scope=scope,
        policy=policy_v2,
        occurrences=(moved,),
        user_intents={moved.occurrence_id: "do_not_track"},
    )
    assert third_changes.policy_changed == (moved.occurrence_id,)
    restarted = MatterService(private_root=home, repository_root=repo)
    snapshot = restarted.inventory.latest_snapshot(scope.scope_id)
    assert snapshot.revision == 3
    assert snapshot.dispositions[0].status == "not_tracked"


def test_duplicate_content_identities_pair_moves_one_to_one(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "private"
    repo.mkdir()
    service = MatterService(private_root=home, repository_root=repo)
    scope = CandidateScope(
        "scope:duplicate-content",
        1,
        "gmail",
        "gmail://in:anywhere",
        ("message",),
    )
    policy = TrackingPolicy("policy:default", 1)
    originals = (
        _occurrence("gmail/message/old-a", content_identity="content:same"),
        _occurrence("gmail/message/old-b", content_identity="content:same"),
    )
    service.reconcile_inventory(
        scope=scope,
        policy=policy,
        occurrences=originals,
    )

    replacements = (
        _occurrence("gmail/message/new-a", content_identity="content:same"),
        _occurrence("gmail/message/new-b", content_identity="content:same"),
    )
    _, changes = service.reconcile_inventory(
        scope=scope,
        policy=policy,
        occurrences=replacements,
    )

    assert len(changes.moved) == 2
    assert {source_id for source_id, _ in changes.moved} == {
        occurrence.occurrence_id for occurrence in originals
    }
    assert {target_id for _, target_id in changes.moved} == {
        occurrence.occurrence_id for occurrence in replacements
    }
    assert changes.added == ()
    assert changes.deleted == ()


def test_user_tracking_intent_survives_policy_only_reconciliation(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "private"
    repo.mkdir()
    service = MatterService(private_root=home, repository_root=repo)
    scope = CandidateScope(
        "scope:docs",
        1,
        "filesystem",
        str(tmp_path / "Documents"),
        ("file",),
    )
    occurrence = _occurrence(
        "Documents/note.txt",
        content_identity="content:note",
    )
    policy_v1 = TrackingPolicy("policy:default", 1)
    first, _ = service.reconcile_inventory(
        scope=scope,
        policy=policy_v1,
        occurrences=(occurrence,),
        user_intents={occurrence.occurrence_id: "do_not_track"},
    )
    assert first.dispositions[0].decided_by == "user"

    second, _ = service.reconcile_inventory(
        scope=scope,
        policy=TrackingPolicy("policy:default", 2),
        occurrences=(occurrence,),
    )
    assert second.dispositions[0].status == "not_tracked"
    assert second.dispositions[0].user_intent == "do_not_track"


def test_source_catalog_contains_only_current_inventory_fields(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "private"
    repo.mkdir()
    service = MatterService(private_root=home, repository_root=repo)
    scope = CandidateScope(
        "scope:docs",
        1,
        "filesystem",
        str(tmp_path / "Documents"),
        ("file",),
    )
    occurrence = _occurrence(
        "Documents/note.txt",
        content_identity="content:note",
    )
    service.reconcile_inventory(
        scope=scope,
        policy=TrackingPolicy("policy:default", 1),
        occurrences=(occurrence,),
    )
    assert service.store is not None
    catalog = service.store.current(
        "source_catalog",
        occurrence.occurrence_id,
    )
    assert catalog is not None
    assert set(catalog) == {
        "active",
        "display_name",
        "disposition",
        "disposition_reason",
        "object_type",
        "occurrence_id",
        "scope_id",
        "snapshot_id",
    }


def test_inventory_batch_refreshes_coverage_summary_once(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    home = tmp_path / "private"
    repo.mkdir()
    service = MatterService(private_root=home, repository_root=repo)
    scope = CandidateScope(
        "scope:batch",
        1,
        "filesystem",
        str(tmp_path / "Documents"),
        ("file",),
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
    occurrences = tuple(
        _occurrence(
            f"Documents/{index}.txt",
            content_identity=f"content:{index}",
        )
        for index in range(4)
    )

    service.reconcile_inventory(
        scope=scope,
        policy=TrackingPolicy("policy:default", 1),
        occurrences=occurrences,
    )

    assert refresh_calls == 1


def test_coverage_rows_and_stale_stages_use_one_batch_each(
    tmp_path,
    monkeypatch,
):
    repo = tmp_path / "repo"
    home = tmp_path / "private"
    repo.mkdir()
    service = MatterService(private_root=home, repository_root=repo)
    assert service.coverage_ledger is not None
    ledger = service.coverage_ledger
    append_calls = 0
    original = ledger.store.append_many

    def counted_append(rows):
        nonlocal append_calls
        append_calls += 1
        return original(rows)

    monkeypatch.setattr(ledger.store, "append_many", counted_append)
    occurrences = tuple(
        {
            "occurrence_id": f"filesystem:batch:{index}",
            "provider": "filesystem",
            "object_type": "file",
            "metadata": {"size": index},
        }
        for index in range(4)
    )
    dispositions = tuple(
        {
            "occurrence_id": item["occurrence_id"],
            "status": "tracked",
        }
        for item in occurrences
    )

    rows = ledger.reconcile_inventory(
        scope_id="scope:batch",
        inventory_revision=1,
        occurrences=occurrences,
        dispositions=dispositions,
        refresh_summary=False,
    )
    stale = ledger.mark_stale_many(
        stage_ids_by_object={
            row.object_id: ("extraction", "analysis")
            for row in rows
        },
        input_fingerprint="change:batch:1",
        refresh_summary=False,
    )

    assert append_calls == 2
    assert len(stale) == 4
    assert all(row.stages["extraction"].status == "stale" for row in stale)
    assert all(row.stages["analysis"].status == "stale" for row in stale)
    assert all(row.retry_count == 1 for row in stale)


def test_coverage_index_exposes_bounded_next_work_and_true_ui_readiness(
    tmp_path,
):
    assert "visual" not in STAGE_ORDER
    assert STAGE_ORDER[-5:] == (
        "meaningful_clue_summary",
        "generated_hero",
        "supplemental_information",
        "ui_projection",
        "ui_reachable",
    )
    repo = tmp_path / "repo"
    home = tmp_path / "private"
    repo.mkdir()
    service = MatterService(private_root=home, repository_root=repo)
    ledger = service.coverage_ledger
    object_id = "filesystem:indexed-user-document"
    ledger.reconcile_inventory(
        scope_id="scope:indexed",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": object_id,
                "provider": "filesystem",
                "object_type": "file",
                "metadata": {"size": 12},
            },
        ),
        dispositions=(
            {
                "occurrence_id": object_id,
                "status": "tracked",
            },
        ),
    )

    assert ledger.next_work(limit=10) == (
        (object_id, "content_selection"),
    )
    page, total = ledger.page(offset=0, limit=10)
    assert total == 1
    assert page[0]["next_stage"] == "content_selection"
    assert page[0]["ui_ready"] is False

    for stage_id in STAGE_ORDER[2:]:
        ledger.mark_stage(
            object_id=object_id,
            stage_id=stage_id,
            status="current",
            input_fingerprint=f"test:{stage_id}",
            output_ref=f"output:{stage_id}",
            matter_ids=(
                ("matter:indexed",)
                if stage_id == "matter"
                else None
            ),
            refresh_summary=False,
        )

    summary = ledger.summary()
    ready_page, _ = ledger.page(offset=0, limit=10)
    assert ledger.next_work(limit=10) == ()
    assert summary.terminal_object_count == 1
    assert summary.ui_ready_object_count == 1
    assert ready_page[0]["terminal"] is True
    assert ready_page[0]["ui_ready"] is True
    assert service.store.matter_coverage_ui_ready("matter:indexed") is True


def test_retired_coverage_leaves_active_counts_and_reactivation_requeues(
    tmp_path,
):
    repo = tmp_path / "repo"
    home = tmp_path / "private"
    repo.mkdir()
    service = MatterService(private_root=home, repository_root=repo)
    ledger = service.coverage_ledger
    object_id = "filesystem:retired-user-document"
    occurrence = {
        "occurrence_id": object_id,
        "provider": "filesystem",
        "object_type": "document",
        "metadata": {"size": 12},
    }
    disposition = {
        "occurrence_id": object_id,
        "status": "tracked",
    }
    ledger.reconcile_inventory(
        scope_id="scope:retirement",
        inventory_revision=1,
        occurrences=(occurrence,),
        dispositions=(disposition,),
    )

    retired = ledger.retire_objects(
        object_ids=(object_id,),
        scope_id="scope:retirement",
        inventory_revision=2,
        reason="synthetic_deleted",
    )[0]

    assert retired.active is False
    assert retired.terminal is True
    assert retired.ui_ready is False
    assert ledger.summary().registered_object_count == 0
    assert ledger.next_work(limit=10) == ()
    assert ledger.page(offset=0, limit=10) == ((), 0)

    reactivated = ledger.reconcile_inventory(
        scope_id="scope:retirement",
        inventory_revision=3,
        occurrences=(occurrence,),
        dispositions=(disposition,),
    )[0]

    assert reactivated.active is True
    assert reactivated.next_stage == "content_selection"
    assert ledger.summary().registered_object_count == 1
    assert ledger.next_work(limit=10) == (
        (object_id, "content_selection"),
    )


def test_parallel_worker_state_publication_keeps_one_current_summary(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    repo = tmp_path / "repo"
    home = tmp_path / "private"
    repo.mkdir()
    first = MatterService(private_root=home, repository_root=repo)
    second = MatterService(private_root=home, repository_root=repo)

    def publish(service, marker):
        return service.coverage_ledger.record_worker_state(
            worker_health="running",
            worker_checkpoint=marker,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(
            future.result()
            for future in (
                executor.submit(publish, first, "worker:first"),
                executor.submit(publish, second, "worker:second"),
            )
        )

    current = first.coverage_ledger.current_summary()
    assert current is not None
    assert current.worker_checkpoint in {"worker:first", "worker:second"}
    assert all(item.ledger_revision >= 1 for item in results)


def test_private_provider_requires_external_home(tmp_path, monkeypatch):
    monkeypatch.delenv("MATTERS_HOME", raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    service = MatterService(repository_root=repo)
    envelope = ProviderEnvelope(
        provider="gmail",
        external_id="private-message",
        object_type="message",
        payload={"summary": "private"},
        metadata={"requires_private_runtime": True},
    )
    result = service.process_envelope(
        scope=scope_for(envelope),
        envelope=envelope,
        idempotency_key="private",
    )
    assert result.terminal_status == "blocked"
    assert not (repo / "matters.sqlite3").exists()


def test_sqlite_batch_append_is_atomic_and_advances_current_revisions(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "private"
    repo.mkdir()
    store = SQLiteStore(home, repo)
    revisions = store.next_revisions("batch", ("a", "b"))
    store.append_many(
        (
            ("batch", "a", revisions["a"], {"value": 1}),
            ("batch", "b", revisions["b"], {"value": 2}),
        )
    )
    next_revisions = store.next_revisions("batch", ("a", "b", "c"))

    assert store.current("batch", "a") == {"value": 1}
    assert store.current("batch", "b") == {"value": 2}
    assert next_revisions == {"a": 2, "b": 2, "c": 1}


def test_sqlite_groups_current_rows_by_json_array_members(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "private"
    repo.mkdir()
    store = SQLiteStore(home, repo)
    store.append_many(
        (
            ("object_coverage", "one", 1, {"matter_ids": ["matter:a"]}),
            (
                "object_coverage",
                "two",
                1,
                {"matter_ids": ["matter:a", "matter:b"]},
            ),
            ("object_coverage", "three", 1, {"matter_ids": []}),
        )
    )

    grouped = store.current_by_json_array_members(
        "object_coverage",
        json_field="matter_ids",
        values=("matter:a", "matter:b", "matter:missing"),
    )

    assert [item["matter_ids"] for item in grouped["matter:a"]] == [
        ["matter:a"],
        ["matter:a", "matter:b"],
    ]
    assert grouped["matter:b"] == (
        {"matter_ids": ["matter:a", "matter:b"]},
    )
    assert grouped["matter:missing"] == ()

    store.append(
        "object_coverage",
        "two",
        2,
        {"matter_ids": ["matter:c"]},
    )
    updated = store.current_by_json_array_members(
        "object_coverage",
        json_field="matter_ids",
        values=("matter:a", "matter:b", "matter:c"),
    )

    assert updated["matter:a"] == ({"matter_ids": ["matter:a"]},)
    assert updated["matter:b"] == ()
    assert updated["matter:c"] == ({"matter_ids": ["matter:c"]},)


def test_empty_matter_coverage_lookup_does_not_scan_snapshot_history(
    tmp_path,
):
    repo = tmp_path / "repo"
    home = tmp_path / "private"
    repo.mkdir()
    store = SQLiteStore(home, repo)
    for revision in range(1, 301):
        store.append(
            "unrelated_history",
            "large-object",
            revision,
            {"revision": revision},
        )

    traced = []
    original_connection = store.connection

    class _TracedConnection:
        def __enter__(self):
            self._manager = original_connection()
            self._connection = self._manager.__enter__()
            self._connection.set_trace_callback(traced.append)
            return self._connection

        def __exit__(self, exc_type, exc, traceback):
            self._connection.set_trace_callback(None)
            return self._manager.__exit__(exc_type, exc, traceback)

    store.connection = _TracedConnection
    grouped = store.current_by_json_array_members(
        "object_coverage",
        json_field="matter_ids",
        values=("matter:without-coverage",),
    )

    assert grouped == {"matter:without-coverage": ()}
    statements = "\n".join(traced)
    assert "FROM coverage_matter_index" in statements
    assert "JOIN snapshots" not in statements
