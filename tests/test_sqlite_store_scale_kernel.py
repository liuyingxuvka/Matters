from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from time import perf_counter

import pytest

from matters.infrastructure.sqlite.store import SQLiteStore


def _store(tmp_path: Path) -> tuple[SQLiteStore, Path, Path]:
    repository_root = tmp_path / "repo"
    private_root = tmp_path / "private"
    repository_root.mkdir()
    return (
        SQLiteStore(private_root, repository_root),
        private_root,
        repository_root,
    )


def _occurrence(object_id: str, *, locator: str | None = None) -> dict:
    return {
        "occurrence_id": object_id,
        "provider": "filesystem",
        "object_type": "file",
        "locator": locator or f"Documents/{object_id}.txt",
        "metadata": {"size": 8, "modified_ns": 10},
        "content_identity": f"content:{object_id}",
        "discovery_reason": "enumerated",
        "parent_occurrence_id": "",
    }


def _inventory(
    scope_id: str,
    revision: int,
    object_ids: tuple[str, ...],
) -> dict:
    return {
        "snapshot_id": f"inventory:{scope_id}:{revision}",
        "scope_id": scope_id,
        "revision": revision,
        "policy_revision": 1,
        "occurrences": [_occurrence(object_id) for object_id in object_ids],
        "dispositions": [
            {
                "occurrence_id": object_id,
                "status": "tracked",
                "reason": "included",
                "policy_revision": 1,
                "decided_by": "policy",
                "user_intent": "",
            }
            for object_id in object_ids
        ],
    }


def _coverage(
    object_id: str,
    *,
    source_status: str = "pending",
) -> dict:
    return {
        "object_id": object_id,
        "provider": "filesystem",
        "object_type": "file",
        "disposition": "tracked",
        "active": True,
        "required_stages": ["source_version"],
        "stages": {"source_version": {"status": source_status}},
        "matter_ids": [],
        "updated_at": "2026-07-19T00:00:00+00:00",
    }


def _register_filesystem_work(
    store: SQLiteStore,
    *,
    scope_id: str,
    object_ids: tuple[str, ...],
) -> None:
    store.append(
        "inventory_snapshot",
        scope_id,
        1,
        _inventory(scope_id, 1, object_ids),
    )
    store.append_many(
        (
            "object_coverage",
            object_id,
            1,
            _coverage(object_id),
        )
        for object_id in object_ids
    )
    store.append_many(
        (
            "content_selection",
            object_id,
            1,
            {
                "occurrence_id": object_id,
                "inventory_revision": 1,
                "mode": "bounded",
                "status": "current",
                "priority": 1,
                "reason": "test_user_text_bounded",
                "source_neighborhood_id": scope_id,
                "source_group_chain": (scope_id,),
                "planner_revision": "content-selection:v1",
                "continuation": "",
            },
        )
        for object_id in object_ids
    )


def test_current_occurrence_index_exact_lookup_refresh_and_rebuild(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    store, private_root, repository_root = _store(tmp_path)
    store.append(
        "inventory_snapshot",
        "scope:documents",
        1,
        _inventory(
            "scope:documents",
            1,
            ("object:a", "object:b"),
        ),
    )

    monkeypatch.setattr(
        store,
        "current",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("exact index lookup decoded an inventory snapshot")
        ),
    )
    rows = store.inventory_occurrences_by_object_ids(
        ("object:b", "missing", "object:a")
    )
    assert tuple(rows) == ("object:b", "missing", "object:a")
    assert rows["missing"] == ()
    assert rows["object:a"][0]["scope_id"] == "scope:documents"
    assert rows["object:a"][0]["inventory_revision"] == 1
    assert rows["object:a"][0]["occurrence"]["locator"].endswith(
        "object:a.txt"
    )

    store.append(
        "inventory_snapshot",
        "scope:documents",
        2,
        _inventory("scope:documents", 2, ("object:b",)),
    )
    refreshed = store.inventory_occurrences_by_object_ids(
        ("object:a", "object:b")
    )
    assert refreshed["object:a"] == ()
    assert refreshed["object:b"][0]["inventory_revision"] == 2

    with store.connection() as connection:
        connection.execute("DELETE FROM inventory_occurrence_current")
        connection.execute(
            "DELETE FROM store_metadata "
            "WHERE key='inventory_occurrence_current:v1'"
        )
    rebuilt = SQLiteStore(private_root, repository_root)
    assert rebuilt.inventory_occurrences_by_object_ids(
        ("object:a", "object:b")
    ) == {
        "object:a": (),
        "object:b": (),
    }
    current_page = rebuilt.rebase_materialized_index_page(
        index_id="inventory_occurrence_current:v1",
        phase="current",
        limit=1,
    )
    assert current_page["next_phase"] == "stale"
    assert current_page["has_more"] is True
    terminal_page = rebuilt.rebase_materialized_index_page(
        index_id="inventory_occurrence_current:v1",
        phase=current_page["next_phase"],
        after_object_id=current_page["next_cursor"],
        limit=1,
    )
    assert terminal_page["status"] == "current"
    assert rebuilt.inventory_occurrences_by_object_ids(
        ("object:a", "object:b")
    ) == {
        "object:a": (),
        "object:b": (
            {
                "scope_id": "scope:documents",
                "object_id": "object:b",
                "inventory_revision": 2,
                "provider": "filesystem",
                "object_type": "file",
                "disposition": "tracked",
                "occurrence": _occurrence("object:b"),
            },
        ),
    }


def test_concurrent_filesystem_claims_are_disjoint_and_exact(tmp_path: Path):
    store, private_root, repository_root = _store(tmp_path)
    object_ids = tuple(f"object:{index:02d}" for index in range(8))
    _register_filesystem_work(
        store,
        scope_id="scope:documents",
        object_ids=object_ids,
    )
    left = SQLiteStore(private_root, repository_root)
    right = SQLiteStore(private_root, repository_root)
    now = datetime(2026, 7, 19, 10, 0, tzinfo=timezone.utc)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (
            executor.submit(
                candidate.claim_registered_filesystem,
                worker_id=worker_id,
                limit=4,
                lease_seconds=60,
                now=now,
            )
            for candidate, worker_id in (
                (left, "worker:left"),
                (right, "worker:right"),
            )
        )
        claims = tuple(future.result() for future in futures)

    claimed_sets = tuple(
        {item["object_id"] for item in claim["items"]}
        for claim in claims
    )
    assert len(claimed_sets[0]) == len(claimed_sets[1]) == 4
    assert claimed_sets[0].isdisjoint(claimed_sets[1])
    assert claimed_sets[0] | claimed_sets[1] == set(object_ids)
    for claim in claims:
        exact = store.filesystem_claim_occurrences(
            claim_id=claim["claim_id"],
            claim_token=claim["claim_token"],
        )
        assert {item["object_id"] for item in exact} == {
            item["object_id"] for item in claim["items"]
        }
        assert all(item["occurrence"]["locator"] for item in exact)


def test_expired_claim_recovers_checkpoint_and_rejects_stale_token(
    tmp_path: Path,
):
    store, _private_root, _repository_root = _store(tmp_path)
    _register_filesystem_work(
        store,
        scope_id="scope:documents",
        object_ids=("object:a",),
    )
    started_at = datetime(2026, 7, 19, 10, 0, tzinfo=timezone.utc)
    first = store.claim_registered_filesystem(
        worker_id="worker:first",
        limit=1,
        lease_seconds=10,
        now=started_at,
    )
    store.update_filesystem_claim_checkpoint(
        claim_id=first["claim_id"],
        claim_token=first["claim_token"],
        object_id="object:a",
        stage="extraction",
        checkpoint={"source_version_id": "source:1"},
        now=started_at + timedelta(seconds=1),
    )
    store.append(
        "object_coverage",
        "object:a",
        2,
        _coverage("object:a", source_status="current"),
    )

    recovered = store.claim_registered_filesystem(
        worker_id="worker:recovery",
        limit=1,
        lease_seconds=20,
        now=started_at + timedelta(seconds=11),
    )
    assert recovered["items"] == (
        {
            "object_id": "object:a",
            "scope_id": "scope:documents",
            "inventory_revision": 1,
            "stage": "extraction",
            "checkpoint": {"source_version_id": "source:1"},
            "attempt": 2,
            "recovered": True,
        },
    )
    with pytest.raises(ValueError, match="invalid or expired"):
        store.update_filesystem_claim_checkpoint(
            claim_id=first["claim_id"],
            claim_token=first["claim_token"],
            object_id="object:a",
            stage="evidence",
            checkpoint={},
            now=started_at + timedelta(seconds=12),
        )
    with pytest.raises(ValueError, match="invalid or expired"):
        store.complete_filesystem_claim_item(
            claim_id=recovered["claim_id"],
            claim_token="wrong-token",
            object_id="object:a",
            checkpoint={},
            now=started_at + timedelta(seconds=12),
        )

    store.update_filesystem_claim_checkpoint(
        claim_id=recovered["claim_id"],
        claim_token=recovered["claim_token"],
        object_id="object:a",
        stage="evidence",
        checkpoint={"anchor_count": 2},
        now=started_at + timedelta(seconds=12),
    )
    completed = store.complete_filesystem_claim_item(
        claim_id=recovered["claim_id"],
        claim_token=recovered["claim_token"],
        object_id="object:a",
        checkpoint={"coverage_revision": 2},
        now=started_at + timedelta(seconds=13),
    )
    assert completed["claim_completed"] is True
    assert (
        store.claim_registered_filesystem(
            worker_id="worker:later",
            limit=1,
            now=started_at + timedelta(seconds=14),
        )
        is None
    )


def test_abandoned_worker_claim_recovers_immediately_with_checkpoint(
    tmp_path: Path,
):
    store, _private_root, _repository_root = _store(tmp_path)
    _register_filesystem_work(
        store,
        scope_id="scope:documents",
        object_ids=("object:a", "object:b"),
    )
    started_at = datetime(2026, 7, 19, 10, 0, tzinfo=timezone.utc)
    first = store.claim_registered_filesystem(
        worker_id="worker:interrupted",
        limit=2,
        lease_seconds=300,
        now=started_at,
    )
    store.update_filesystem_claim_checkpoint(
        claim_id=first["claim_id"],
        claim_token=first["claim_token"],
        object_id="object:a",
        stage="evidence",
        checkpoint={"anchor_count": 2},
        now=started_at + timedelta(seconds=1),
    )

    abandoned = store.abandon_filesystem_worker_claim(
        worker_id="worker:interrupted",
        reason="test_interruption",
        now=started_at + timedelta(seconds=2),
    )
    assert abandoned["status"] == "abandoned"
    assert abandoned["released_item_count"] == 2
    recovered = store.claim_registered_filesystem(
        worker_id="worker:recovery",
        limit=2,
        lease_seconds=60,
        now=started_at + timedelta(seconds=2),
    )
    recovered_by_id = {
        item["object_id"]: item for item in recovered["items"]
    }
    assert recovered_by_id["object:a"]["stage"] == "evidence"
    assert recovered_by_id["object:a"]["checkpoint"] == {
        "anchor_count": 2
    }
    assert recovered_by_id["object:a"]["attempt"] == 2
    assert recovered_by_id["object:b"]["stage"] == "source_version"
    assert recovered_by_id["object:b"]["attempt"] == 2
    with pytest.raises(ValueError, match="invalid or expired"):
        store.complete_filesystem_claim_item(
            claim_id=first["claim_id"],
            claim_token=first["claim_token"],
            object_id="object:b",
            checkpoint={},
            now=started_at + timedelta(seconds=3),
        )


def test_recovered_claim_replay_preserves_stage_high_water_mark(
    tmp_path: Path,
):
    store, _private_root, _repository_root = _store(tmp_path)
    _register_filesystem_work(
        store,
        scope_id="scope:documents",
        object_ids=("object:a",),
    )
    started_at = datetime(2026, 7, 19, 10, 0, tzinfo=timezone.utc)
    first = store.claim_registered_filesystem(
        worker_id="worker:first",
        limit=1,
        lease_seconds=60,
        now=started_at,
    )
    store.update_filesystem_claim_checkpoint(
        claim_id=first["claim_id"],
        claim_token=first["claim_token"],
        object_id="object:a",
        stage="package",
        checkpoint={"anchor_count": 12},
        now=started_at + timedelta(seconds=1),
    )
    store.abandon_filesystem_worker_claim(
        worker_id="worker:first",
        reason="test_restart",
        now=started_at + timedelta(seconds=2),
    )
    recovered = store.claim_registered_filesystem(
        worker_id="worker:recovered",
        limit=1,
        lease_seconds=60,
        now=started_at + timedelta(seconds=2),
    )

    replayed = store.update_filesystem_claim_checkpoint(
        claim_id=recovered["claim_id"],
        claim_token=recovered["claim_token"],
        object_id="object:a",
        stage="extraction",
        checkpoint={"source_version_id": "source:replayed"},
        extend_lease_seconds=60,
        now=started_at + timedelta(seconds=3),
    )
    assert replayed["stage"] == "package"
    assert replayed["checkpoint"] == {"anchor_count": 12}
    advanced = store.update_filesystem_claim_checkpoint(
        claim_id=recovered["claim_id"],
        claim_token=recovered["claim_token"],
        object_id="object:a",
        stage="coverage",
        checkpoint={"queued": True},
        now=started_at + timedelta(seconds=4),
    )
    assert advanced["stage"] == "coverage"
    assert advanced["checkpoint"] == {"queued": True}


def test_pending_analysis_page_stays_bounded_on_large_current_queue(
    tmp_path: Path,
):
    store, _private_root, _repository_root = _store(tmp_path)
    package_count = 2_500
    store.append_many(
        (
            (
                "analysis_work_package",
                f"work:{index:04d}",
                1,
                {
                    "package_id": f"work:{index:04d}",
                    "capability_role": "low_cost_annotator",
                    "source_revision_ids": (),
                    "dependency_package_ids": (),
                },
            )
            for index in range(package_count)
        )
    )
    store.append_many(
        (
            (
                "agent_operation_result",
                f"work:{index:04d}",
                1,
                {
                    "package_id": f"work:{index:04d}",
                    "status": "passed",
                    "auto_apply_status": "annotation_current",
                },
            )
            for index in range(0, package_count, 2)
        )
    )

    started = perf_counter()
    rows, total = store.pending_analysis_page(
        offset=100,
        limit=50,
        capability_roles=("low_cost_annotator",),
    )
    elapsed = perf_counter() - started

    assert total == package_count // 2
    assert len(rows) == 50
    assert all(
        int(str(item["package_id"]).split(":")[1]) % 2 == 1
        for item in rows
    )
    assert elapsed < 3.0


def test_real_first_run_class_selection_gap_is_explicit_and_bounded(
    tmp_path: Path,
):
    """Regress the 53,706-document/15,934-image startup selection miss."""

    store, _private_root, _repository_root = _store(tmp_path)
    document_count = 53_706
    image_count = 15_934
    total_count = document_count + image_count
    with store.connection() as connection:
        connection.executemany(
            "INSERT INTO inventory_occurrence_current("
            "scope_id, object_id, inventory_revision, provider, object_type, "
            "disposition, occurrence_payload"
            ") VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                (
                    "scope:large-private-first-run",
                    f"occurrence:{index:05d}",
                    1,
                    "filesystem",
                    "document" if index < document_count else "image",
                    "tracked",
                    json.dumps(
                        {
                            "occurrence_id": f"occurrence:{index:05d}",
                            "provider": "filesystem",
                            "object_type": (
                                "document"
                                if index < document_count
                                else "image"
                            ),
                            "locator": f"private/item-{index:05d}",
                            "metadata": {},
                            "content_identity": f"content:{index:05d}",
                            "discovery_reason": "enumerated",
                            "parent_occurrence_id": "",
                        },
                        separators=(",", ":"),
                    ),
                )
                for index in range(total_count)
            ),
        )

    # Registration alone must not silently read or select the private corpus.
    assert store.content_selection_page(offset=0, limit=1) == ((), 0)

    started = perf_counter()
    first_page, has_more = store.content_selection_rebase_page(
        after_object_id="",
        limit=200,
    )
    second_page, second_has_more = store.content_selection_rebase_page(
        after_object_id=str(first_page[-1]["object_id"]),
        limit=200,
    )
    elapsed = perf_counter() - started

    assert len(first_page) == len(second_page) == 200
    assert has_more is second_has_more is True
    assert first_page[-1]["object_id"] < second_page[0]["object_id"]
    assert elapsed < 3.0


def test_related_matter_lookup_uses_current_coverage_index_and_is_bounded(
    tmp_path: Path,
):
    store, _private_root, _repository_root = _store(tmp_path)
    store.append_many(
        (
            (
                "object_coverage",
                f"object:{index}",
                1,
                {
                    **_coverage(f"object:{index}"),
                    "matter_ids": (
                        "matter:current",
                        "matter:strong",
                        f"matter:weak:{index}",
                    ),
                },
            )
            for index in range(3)
        )
    )

    related = store.matter_ids_for_coverage_objects(
        ("object:0", "object:1", "object:2"),
        exclude_matter_id="matter:current",
        limit=2,
    )

    assert related[0] == ("matter:strong", 3)
    assert len(related) == 2
    assert all(matter_id != "matter:current" for matter_id, _count in related)


def test_content_addressed_batch_277_noop_and_conflict_is_atomic(
    tmp_path: Path,
):
    store, _private_root, _repository_root = _store(tmp_path)
    rows = tuple(
        (
            "evidence_anchor",
            f"anchor:{index:03d}",
            {
                "anchor_id": f"anchor:{index:03d}",
                "source_id": "source:one",
                "offset": index,
            },
        )
        for index in range(277)
    )
    inserted = store.append_content_addressed_many(rows)
    assert len(inserted) == 277
    assert store.count_current("evidence_anchor") == 277
    assert store.append_content_addressed_many(rows) == ()
    assert len(store.history("evidence_anchor", "anchor:100")) == 1

    with pytest.raises(ValueError, match="different payload"):
        store.append_content_addressed_many(
            (
                (
                    "evidence_anchor",
                    "anchor:new",
                    {"anchor_id": "anchor:new"},
                ),
                (
                    "evidence_anchor",
                    "anchor:100",
                    {"anchor_id": "anchor:100", "offset": "conflict"},
                ),
            )
        )
    assert store.current("evidence_anchor", "anchor:new") is None
    assert store.count_current("evidence_anchor") == 277


def test_append_next_serializes_concurrent_revision_allocation(
    tmp_path: Path,
):
    store, private_root, repository_root = _store(tmp_path)
    stores = tuple(
        SQLiteStore(private_root, repository_root) for _ in range(8)
    )

    def append(index: int) -> int:
        return stores[index % len(stores)].append_next(
            "mutable_owner",
            "shared",
            {"writer_index": index},
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        revisions = tuple(executor.map(append, range(40)))

    assert sorted(revisions) == list(range(1, 41))
    assert len(store.history("mutable_owner", "shared")) == 40


def test_object_coverage_superseded_revision_is_compressed_but_history_is_exact(
    tmp_path: Path,
) -> None:
    store, _private_root, _repository_root = _store(tmp_path)
    first = {
        "object_id": "occurrence:one",
        "revision": 1,
        "evidence": "anchor:" * 10_000,
    }
    second = {
        "object_id": "occurrence:one",
        "revision": 2,
        "evidence": "bounded",
    }
    store.append("object_coverage", "occurrence:one", 1, first)
    store.append("object_coverage", "occurrence:one", 2, second)

    assert store.current("object_coverage", "occurrence:one") == second
    assert store.history("object_coverage", "occurrence:one") == (
        first,
        second,
    )
    with store.connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM snapshots "
            "WHERE owner='object_coverage' AND object_id='occurrence:one'"
        ).fetchone()[0] == 1
        archived = connection.execute(
            "SELECT length(payload) FROM snapshot_archive "
            "WHERE owner='object_coverage' AND object_id='occurrence:one'"
        ).fetchone()
    assert archived is not None
    assert int(archived[0]) < len(json.dumps(first).encode("utf-8"))


def test_existing_object_coverage_history_archive_is_bounded_and_resumable(
    tmp_path: Path,
) -> None:
    store, _private_root, _repository_root = _store(tmp_path)
    payloads = tuple(
        {
            "object_id": "occurrence:legacy",
            "revision": revision,
            "evidence": "anchor:" * 1_000 + str(revision),
        }
        for revision in range(1, 4)
    )
    with store.connection() as connection:
        for revision, payload in enumerate(payloads, start=1):
            encoded = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            payload_hash = (
                "sha256:" + hashlib.sha256(
                    encoded.encode("utf-8")
                ).hexdigest()
            )
            connection.execute(
                "INSERT INTO snapshots"
                "(owner, object_id, revision, payload, payload_hash, created_at) "
                "VALUES ('object_coverage', 'occurrence:legacy', ?, ?, ?, ?)",
                (
                    revision,
                    encoded,
                    payload_hash,
                    f"2026-07-20T00:00:0{revision}+00:00",
                ),
            )
        connection.execute(
            "INSERT INTO current_objects(owner, object_id, revision) "
            "VALUES ('object_coverage', 'occurrence:legacy', 3)"
        )

    first_page = store.archive_object_coverage_history_page(limit=1)
    assert first_page["archived_count"] == 1
    assert first_page["has_more"] is True
    second_page = store.archive_object_coverage_history_page(
        after_object_id=str(first_page["next_object_id"]),
        after_revision=int(first_page["next_revision"]),
        limit=1,
    )
    assert second_page["archived_count"] == 1
    assert second_page["has_more"] is False
    assert store.history("object_coverage", "occurrence:legacy") == payloads
    assert store.current("object_coverage", "occurrence:legacy") == payloads[-1]
    with store.connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM snapshots "
            "WHERE owner='object_coverage' AND object_id='occurrence:legacy'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM snapshot_archive "
            "WHERE owner='object_coverage' AND object_id='occurrence:legacy'"
        ).fetchone()[0] == 2


def test_every_mutable_coverage_append_route_archives_the_superseded_current(
    tmp_path: Path,
) -> None:
    store, _private_root, _repository_root = _store(tmp_path)
    store.append_many(
        (
            ("object_coverage", "occurrence:many", 1, {"value": 1}),
        )
    )
    store.append_many(
        (
            ("object_coverage", "occurrence:many", 2, {"value": 2}),
        )
    )
    store.append_next("object_coverage", "occurrence:next", {"value": 1})
    store.append_next("object_coverage", "occurrence:next", {"value": 2})
    store.compare_current_and_append(
        "object_coverage",
        "occurrence:compare",
        is_equivalent=lambda current: current == {"value": 1},
        payload_factory=lambda _revision, _current: {"value": 1},
    )
    store.compare_current_and_append(
        "object_coverage",
        "occurrence:compare",
        is_equivalent=lambda current: current == {"value": 2},
        payload_factory=lambda _revision, _current: {"value": 2},
    )

    for object_id in (
        "occurrence:many",
        "occurrence:next",
        "occurrence:compare",
    ):
        assert store.history("object_coverage", object_id) == (
            {"value": 1},
            {"value": 2},
        )
        with store.connection() as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM snapshots "
                "WHERE owner='object_coverage' AND object_id=?",
                (object_id,),
            ).fetchone()[0] == 1
            assert connection.execute(
                "SELECT COUNT(*) FROM snapshot_archive "
                "WHERE owner='object_coverage' AND object_id=?",
                (object_id,),
            ).fetchone()[0] == 1


def test_compare_current_and_append_converges_identical_source_race(
    tmp_path: Path,
):
    store, private_root, repository_root = _store(tmp_path)
    stores = (
        SQLiteStore(private_root, repository_root),
        SQLiteStore(private_root, repository_root),
    )

    def register(candidate: SQLiteStore) -> dict:
        return candidate.compare_current_and_append(
            "source_version",
            "source:shared",
            is_equivalent=lambda current: bool(
                current
                and current["content_hash"] == "sha256:content"
                and current["metadata_hash"] == "sha256:metadata"
                and not current["tombstone"]
            ),
            payload_factory=lambda revision, current: {
                "source_id": "source:shared",
                "version": revision,
                "predecessor_version": (
                    int(current["version"]) if current else None
                ),
                "content_hash": "sha256:content",
                "metadata_hash": "sha256:metadata",
                "tombstone": False,
            },
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(register, stores))

    assert {result["status"] for result in results} == {
        "appended",
        "current",
    }
    assert {result["revision"] for result in results} == {1}
    assert {result["payload"]["version"] for result in results} == {1}
    assert len(store.history("source_version", "source:shared")) == 1

    changed = store.compare_current_and_append(
        "source_version",
        "source:shared",
        is_equivalent=lambda current: bool(
            current and current["content_hash"] == "sha256:changed"
        ),
        payload_factory=lambda revision, current: {
            "source_id": "source:shared",
            "version": revision,
            "predecessor_version": int(current["version"]),
            "content_hash": "sha256:changed",
            "metadata_hash": "sha256:metadata",
            "tombstone": False,
        },
    )
    assert changed["status"] == "appended"
    assert changed["revision"] == 2
    assert changed["payload"]["version"] == 2
    assert changed["payload"]["predecessor_version"] == 1
