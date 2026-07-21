from __future__ import annotations

from dataclasses import asdict
import json

from matters.application.orchestrator import MatterService
from matters.inventory.owners import (
    CandidateScope,
    InventoryOccurrence,
    TrackingPolicy,
)


def test_service_projects_current_source_groups_without_private_paths(
    tmp_path,
) -> None:
    private_root = tmp_path / "private"
    service = MatterService(
        repository_root=tmp_path / "repository",
        private_root=private_root,
    )
    scope = CandidateScope(
        scope_id="scope:documents",
        revision=1,
        provider="filesystem",
        root_locator=str(tmp_path / "Documents"),
        object_types=("pdf",),
    )
    occurrence = InventoryOccurrence(
        occurrence_id="filesystem:ticket",
        provider="filesystem",
        object_type="pdf",
        locator=r"Travel\Japan\ticket.pdf",
        metadata={
            "display_name": "ticket.pdf",
            "source_group_chain": ("filesystem-group:travel",),
            "source_group_labels": ("Japan travel",),
            "recommended_disposition": "tracked",
        },
        content_identity="f" * 64,
    )

    service.reconcile_inventory(
        scope=scope,
        policy=TrackingPolicy(
            policy_id="tracking-policy:test",
            revision=1,
        ),
        occurrences=(occurrence,),
    )
    page = service.source_groups()
    detail = service.source_group_detail(
        group_id="filesystem-group:travel"
    )
    rendered = json.dumps(
        {"page": page, "detail": detail},
        sort_keys=True,
    )

    assert page["total_count"] == 1
    assert page["registered_occurrence_count"] == 1
    assert page["freshness_fingerprint"].startswith("sha256:")
    assert detail["summary"]["title"] == "Japan travel"
    assert detail["members"][0]["title"] == "ticket.pdf"
    assert str(tmp_path) not in rendered
    assert r"Travel\Japan\ticket.pdf" not in rendered


def test_service_rebuilds_source_group_index_in_bounded_restartable_pages(
    tmp_path,
) -> None:
    service = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    scope = CandidateScope(
        scope_id="scope:documents",
        revision=1,
        provider="filesystem",
        root_locator=str(tmp_path / "Documents"),
        object_types=("pdf",),
    )
    occurrences = tuple(
        InventoryOccurrence(
            occurrence_id=f"filesystem:item:{index}",
            provider="filesystem",
            object_type="pdf",
            locator=f"Group/item-{index}.pdf",
            metadata={
                "display_name": f"item-{index}.pdf",
                "source_group_chain": ("filesystem-group:shared",),
                "source_group_labels": ("Shared",),
                "recommended_disposition": "tracked",
            },
            content_identity=f"{index:064x}",
        )
        for index in range(3)
    )
    service.reconcile_inventory(
        scope=scope,
        policy=TrackingPolicy(
            policy_id="tracking-policy:test",
            revision=1,
        ),
        occurrences=occurrences,
    )
    assert service.store is not None
    assert service.store.source_group_index_status()["status"] == "current"
    service.store.append(
        "inventory_snapshot",
        scope.scope_id,
        2,
        {
            "scope_id": scope.scope_id,
            "revision": 2,
            "occurrences": tuple(asdict(item) for item in occurrences),
            "dispositions": tuple(
                {
                    "occurrence_id": item.occurrence_id,
                    "status": "tracked",
                }
                for item in occurrences
            ),
        },
    )
    stale = service.store.source_group_index_status()
    assert stale["status"] == "partial"
    assert stale["eligible_occurrence_count"] == 3
    assert stale["indexed_occurrence_count"] == 0
    assert stale["remaining_occurrence_count"] == 3
    assert stale["stale_occurrence_count"] == 3
    assert service.source_groups()["total_count"] == 0
    assert (
        service.store.source_group_detail_page(
            group_id="filesystem-group:shared",
            member_offset=0,
            member_limit=20,
        )
        is None
    )

    first = service.rebase_source_group_index(limit=2)
    second = service.rebase_source_group_index(
        after_object_id=first["next_object_id"],
        after_scope_id=first["next_scope_id"],
        limit=2,
    )

    assert first["status"] == "partial"
    assert first["has_more"] is True
    assert second["status"] == "current"
    assert second["has_more"] is False
    page = service.source_groups()
    assert page["index_status"] == "current"
    assert page["items"][0]["total_member_count"] == 3


def test_source_group_status_rejects_a_partial_current_chain(tmp_path) -> None:
    service = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    occurrence = InventoryOccurrence(
        occurrence_id="filesystem:three-level-chain",
        provider="filesystem",
        object_type="pdf",
        locator="Travel/Japan/booking.pdf",
        metadata={
            "display_name": "booking.pdf",
            "source_group_chain": (
                "filesystem-group:travel",
                "filesystem-group:japan",
                "filesystem-group:bookings",
            ),
            "source_group_labels": (
                "Travel",
                "Japan",
                "Bookings",
            ),
            "recommended_disposition": "tracked",
        },
    )
    service.reconcile_inventory(
        scope=CandidateScope(
            scope_id="scope:three-level-chain",
            revision=1,
            provider="filesystem",
            root_locator="Travel",
            object_types=("pdf",),
        ),
        policy=TrackingPolicy(
            policy_id="tracking-policy:three-level-chain",
            revision=1,
        ),
        occurrences=(occurrence,),
    )
    assert service.store is not None
    assert service.store.source_group_index_status()["status"] == "current"
    with service.store.connection() as connection:
        connection.execute(
            "DELETE FROM source_group_member_index "
            "WHERE object_id=? AND depth=1",
            (occurrence.occurrence_id,),
        )

    status = service.store.source_group_index_status()

    assert status["status"] == "partial"
    assert status["eligible_occurrence_count"] == 1
    assert status["indexed_occurrence_count"] == 0
    assert status["remaining_occurrence_count"] == 1


def test_source_group_status_requires_exact_current_projection_identity(
    tmp_path,
) -> None:
    service = MatterService(
        repository_root=tmp_path / "repository",
        private_root=tmp_path / "private",
    )
    occurrence = InventoryOccurrence(
        occurrence_id="filesystem:exact-projection",
        provider="filesystem",
        object_type="pdf",
        locator="Travel/exact.pdf",
        metadata={
            "display_name": "exact.pdf",
            "source_group_chain": (
                "filesystem-group:travel",
                "filesystem-group:exact",
            ),
            "source_group_labels": ("Travel", "Exact"),
            "recommended_disposition": "tracked",
        },
    )
    service.reconcile_inventory(
        scope=CandidateScope(
            scope_id="scope:exact-projection",
            revision=1,
            provider="filesystem",
            root_locator="Travel",
            object_types=("pdf",),
        ),
        policy=TrackingPolicy(
            policy_id="tracking-policy:exact-projection",
            revision=1,
        ),
        occurrences=(occurrence,),
    )
    assert service.store is not None
    assert service.store.source_group_index_status()["status"] == "current"

    with service.store.connection() as connection:
        connection.execute(
            "UPDATE source_group_member_index "
            "SET group_id='filesystem-group:wrong' "
            "WHERE object_id=? AND depth=1",
            (occurrence.occurrence_id,),
        )
    wrong_set = service.store.source_group_index_status()
    assert wrong_set["status"] == "partial"
    assert wrong_set["indexed_occurrence_count"] == 0

    service.rebase_source_group_index(limit=10)
    assert service.store.source_group_index_status()["status"] == "current"
    with service.store.connection() as connection:
        connection.execute(
            "UPDATE source_group_member_index SET title='Wrong title' "
            "WHERE object_id=? AND depth=1",
            (occurrence.occurrence_id,),
        )
    wrong_projection = service.store.source_group_index_status()
    assert wrong_projection["status"] == "partial"
    assert wrong_projection["indexed_occurrence_count"] == 0

    service.rebase_source_group_index(limit=10)
    assert service.store.source_group_index_status()["status"] == "current"
    with service.store.connection() as connection:
        connection.execute(
            "UPDATE source_group_projection_state SET projection_version=1 "
            "WHERE object_id=?",
            (occurrence.occurrence_id,),
        )
    wrong_version = service.store.source_group_index_status()
    assert wrong_version["status"] == "partial"
    assert wrong_version["indexed_occurrence_count"] == 0
    assert wrong_version["stale_occurrence_count"] == 1
