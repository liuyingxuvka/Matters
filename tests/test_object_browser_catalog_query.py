from __future__ import annotations

from datetime import datetime, timedelta, timezone

from matters.application.orchestrator import MatterService


def _service(tmp_path) -> MatterService:
    repository = tmp_path / "repository"
    repository.mkdir()
    return MatterService(
        repository_root=repository,
        private_root=tmp_path / "private",
    )


def test_catalog_pages_in_sql_and_hydrates_only_the_visible_ids(tmp_path) -> None:
    service = _service(tmp_path)
    assert service.store is not None
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    writes = []
    for index in range(300):
        matter_id = f"matter:{index:04d}"
        semantic_revision = f"semantic:{index}:v1"
        status = ("planned", "in_progress", "completed")[index % 3]
        activity_at = (base + timedelta(minutes=index)).isoformat()
        writes.extend(
            (
                (
                    "projection",
                    matter_id,
                    1,
                    {
                        "matter_id": matter_id,
                        "semantic_revision": semantic_revision,
                        "state": status,
                        "evidence_ids": (),
                        "localized_values": {
                            "en": f"Matter {index:04d}",
                            "zh-CN": f"事项 {index:04d}",
                        },
                        "localized_rationale": {
                            "en": f"Summary {index:04d}",
                            "zh-CN": f"摘要 {index:04d}",
                        },
                        "equivalence_status": "equivalent",
                    },
                ),
                (
                    "admission_decision",
                    matter_id,
                    1,
                        {
                            "status": "admitted",
                            "matter": {
                                "matter_id": matter_id,
                                "source_ids": (),
                                "rationale": "Catalog scale fixture",
                                "evidence_ids": (),
                                "admitted": True,
                                "semantic_identity_id": semantic_revision,
                                "object_kind": "matter",
                            },
                            "candidate": None,
                        },
                ),
                (
                    "matter_activity",
                    matter_id,
                    1,
                    {
                        "matter_id": matter_id,
                        "source_matter_id": matter_id,
                        "material_clue_id": f"clue:{index}",
                        "latest_meaningful_clue_at": activity_at,
                        "persistence_revision": 1,
                        "material_clue_revision": f"clue:{index}:v1",
                        "summary_revision": f"clue:{index}:v1",
                        "activity_order_revision": f"clue:{index}:v1",
                        "localized_summary": {
                            "en": f"Latest update {index:04d}",
                            "zh-CN": f"最新进展 {index:04d}",
                        },
                    },
                ),
            )
        )
    service.store.append_many(writes)

    def forbidden_full_owner_scan(_owner: str):
        raise AssertionError("catalog must not iterate a complete owner")

    service.store.iter_current = forbidden_full_owner_scan  # type: ignore[method-assign]
    original_current_many = service.store.current_many
    projection_batch_sizes: list[int] = []

    def recorded_current_many(owner, object_ids):
        ids = tuple(object_ids)
        if owner == "projection":
            projection_batch_sizes.append(len(ids))
        return original_current_many(owner, ids)

    service.store.current_many = recorded_current_many  # type: ignore[method-assign]

    first = service.object_catalog_page(offset=0, limit=7)
    second = service.object_catalog_page(offset=7, limit=7)
    filtered = service.object_catalog_page(
        query="Matter 0299",
        status="completed",
        offset=0,
        limit=7,
    )

    assert first["total_count"] == 300
    assert [item["matter_id"] for item in first["items"]] == [
        f"matter:{index:04d}" for index in range(299, 292, -1)
    ]
    assert [item["matter_id"] for item in second["items"]] == [
        f"matter:{index:04d}" for index in range(292, 285, -1)
    ]
    assert first["catalog_revision"] == second["catalog_revision"]
    assert first["facets"]["status"] == {
        "all": 300,
        "planned": 100,
        "in_progress": 100,
        "completed": 100,
    }
    assert filtered["total_count"] == 1
    assert filtered["items"][0]["matter_id"] == "matter:0299"
    assert projection_batch_sizes
    assert max(projection_batch_sizes) <= 7


def test_parent_card_keeps_aggregate_projection_summary_when_child_bubbles(
    tmp_path,
) -> None:
    service = _service(tmp_path)
    assert service.store is not None
    service.store.append_many(
        (
            (
                "projection",
                "matter:trip",
                1,
                {
                    "matter_id": "matter:trip",
                    "semantic_revision": "semantic:trip:v1",
                    "state": "in_progress",
                    "evidence_ids": (),
                    "localized_values": {
                        "en": "Japan trip",
                        "zh-CN": "日本旅行",
                    },
                    "localized_rationale": {
                        "en": (
                            "The trip combines confirmed flights, lodging, "
                            "and remaining preparation."
                        ),
                        "zh-CN": "行程汇总了已确认航班、住宿和剩余准备事项。",
                    },
                    "equivalence_status": "equivalent",
                },
            ),
            (
                "admission_decision",
                "matter:trip",
                1,
                    {
                        "status": "admitted",
                        "matter": {
                            "matter_id": "matter:trip",
                            "source_ids": (),
                            "rationale": "Trip fixture",
                            "evidence_ids": (),
                            "admitted": True,
                            "semantic_identity_id": "semantic:trip",
                            "object_kind": "matter",
                        },
                        "candidate": None,
                    },
            ),
            (
                "matter_hierarchy_projection",
                "matter:trip",
                1,
                {
                    "matter_id": "matter:trip",
                    "path": ("matter:trip",),
                    "child_count": 2,
                },
            ),
            (
                "matter_activity",
                "matter:trip",
                1,
                {
                    "matter_id": "matter:trip",
                    "source_matter_id": "matter:flight",
                    "material_clue_id": "clue:flight-confirmed",
                    "latest_meaningful_clue_at": (
                        "2026-07-19T09:30:00+00:00"
                    ),
                    "persistence_revision": 1,
                    "material_clue_revision": "clue:flight:v1",
                    "summary_revision": "clue:flight:v1",
                    "activity_order_revision": "clue:flight:v1",
                    "localized_summary": {
                        "en": "The flight has been confirmed.",
                        "zh-CN": "航班已经确认。",
                    },
                },
            ),
        )
    )

    card = service.object_catalog_page()["items"][0]
    child_update_search = service.object_catalog_page(
        query="flight has been confirmed"
    )

    assert card["latest_meaningful_clue_at"] == (
        "2026-07-19T09:30:00+00:00"
    )
    assert card["activity_status"] == "current"
    assert card["summary"] == {
        "en": (
            "The trip combines confirmed flights, lodging, "
            "and remaining preparation."
        ),
        "zh-CN": "行程汇总了已确认航班、住宿和剩余准备事项。",
    }
    assert child_update_search["total_count"] == 0


def test_descendant_search_result_carries_root_and_matched_node_identity(
    tmp_path,
) -> None:
    service = _service(tmp_path)
    assert service.store is not None
    rows = []
    for matter_id, title, path in (
        ("matter:trip", "Australia trip", ("matter:trip",)),
        (
            "matter:hotel",
            "Melbourne hotel booking",
            ("matter:trip", "matter:hotel"),
        ),
    ):
        rows.extend(
            (
                (
                    "projection",
                    matter_id,
                    1,
                    {
                        "matter_id": matter_id,
                        "semantic_revision": f"semantic:{matter_id}:v1",
                        "state": "planned",
                        "evidence_ids": (),
                        "localized_values": {"en": title, "zh-CN": title},
                        "localized_rationale": {
                            "en": f"Current summary for {title}.",
                            "zh-CN": f"{title} 的当前摘要。",
                        },
                        "equivalence_status": "equivalent",
                    },
                ),
                (
                    "admission_decision",
                    matter_id,
                    1,
                    {
                        "status": "admitted",
                        "matter": {
                            "matter_id": matter_id,
                            "source_ids": (),
                            "evidence_ids": (),
                            "admitted": True,
                        },
                    },
                ),
                (
                    "matter_hierarchy_projection",
                    matter_id,
                    1,
                    {
                        "matter_id": matter_id,
                        "path": path,
                        "parent_matter_id": path[-2] if len(path) > 1 else "",
                        "child_count": 0,
                        "freshness": "current",
                    },
                ),
            )
        )
    service.store.append_many(rows)

    result = service.object_catalog_page(
        query="Melbourne hotel",
        root_only=False,
    )

    assert result["total_count"] == 1
    card = result["items"][0]
    assert card["matter_id"] == "matter:hotel"
    assert card["owning_root_matter_id"] == "matter:trip"
    assert card["matched_node_id"] == "matter:hotel"
    assert card["search_result_kind"] == "child"


def test_leaf_card_keeps_semantic_projection_summary_when_activity_bubbles(
    tmp_path,
) -> None:
    service = _service(tmp_path)
    assert service.store is not None
    service.store.append_many(
        (
            (
                "projection",
                "matter:visit",
                1,
                {
                    "matter_id": "matter:visit",
                    "semantic_revision": "semantic:visit:v2",
                    "state": "completed",
                    "evidence_ids": ("evidence:ticket",),
                    "localized_values": {
                        "en": "Theme-park visit",
                        "zh-CN": "主题公园之行",
                    },
                    "localized_rationale": {
                        "en": (
                            "The ticket is confirmed and the past visit is "
                            "shown as likely completed by a revisable AI "
                            "historical inference."
                        ),
                        "zh-CN": (
                            "门票已经确认；已过去的行程以可修正的 AI "
                            "历史推断显示为很可能已完成。"
                        ),
                    },
                    "equivalence_status": "equivalent",
                },
            ),
            (
                "admission_decision",
                "matter:visit",
                1,
                {
                    "status": "admitted",
                    "matter": {
                        "matter_id": "matter:visit",
                        "source_ids": ("source:ticket",),
                        "rationale": "Visit fixture",
                        "evidence_ids": ("evidence:ticket",),
                        "admitted": True,
                        "semantic_identity_id": "semantic:visit",
                        "object_kind": "matter",
                    },
                    "candidate": None,
                },
            ),
            (
                "matter_activity",
                "matter:visit",
                1,
                {
                    "matter_id": "matter:visit",
                    "source_matter_id": "matter:visit",
                    "material_clue_id": "clue:ticket-purchased",
                    "latest_meaningful_clue_at": "2026-06-28T10:00:00+00:00",
                    "persistence_revision": 1,
                    "material_clue_revision": "clue:ticket:v1",
                    "summary_revision": "clue:ticket:v1",
                    "activity_order_revision": "clue:ticket:v1",
                    "localized_summary": {
                        "en": "The ticket purchase was confirmed.",
                        "zh-CN": "门票购买已经确认。",
                    },
                },
            ),
        )
    )

    card = service.object_catalog_page()["items"][0]

    assert card["summary"] == {
        "en": (
            "The ticket is confirmed and the past visit is shown as likely "
            "completed by a revisable AI historical inference."
        ),
        "zh-CN": (
            "门票已经确认；已过去的行程以可修正的 AI "
            "历史推断显示为很可能已完成。"
        ),
    }
    assert card["latest_meaningful_clue_at"] == "2026-06-28T10:00:00+00:00"


def test_catalog_start_filter_uses_earliest_exact_source_time(tmp_path) -> None:
    service = _service(tmp_path)
    assert service.store is not None
    modified = datetime(2024, 2, 3, 9, 15, tzinfo=timezone.utc)
    service.store.append_many(
        (
            (
                "inventory_snapshot",
                "scope:documents",
                1,
                {
                    "snapshot_id": "inventory:documents:1",
                    "scope_id": "scope:documents",
                    "revision": 1,
                    "occurrences": (
                        {
                            "occurrence_id": "cover-letter",
                            "provider": "filesystem",
                            "object_type": "file",
                            "metadata": {
                                "modified_ns": int(
                                    modified.timestamp() * 1_000_000_000
                                ),
                            },
                        },
                    ),
                    "dispositions": (
                        {
                            "occurrence_id": "cover-letter",
                            "status": "tracked",
                        },
                    ),
                },
            ),
            (
                "source_version",
                "source:cover-letter",
                1,
                {
                    "source_id": "source:cover-letter",
                    "version": 1,
                    "provider": "filesystem",
                    "external_reference": {
                        "provider": "filesystem",
                        "external_id": "cover-letter",
                        "object_type": "file",
                        "locator": "",
                    },
                    "content": {},
                    "content_hash": "sha256:content",
                    "metadata_hash": "sha256:metadata",
                    "predecessor_version": None,
                    "tombstone": False,
                    "storage_class": "external_original",
                    "locator_fingerprint": "sha256:locator",
                    "original_availability": "available",
                },
            ),
            (
                "projection",
                "matter:job-search",
                1,
                {
                    "matter_id": "matter:job-search",
                    "semantic_revision": "semantic:job-search:v1",
                    "state": "in_progress",
                    "evidence_ids": (),
                    "localized_values": {
                        "en": "Job search",
                        "zh-CN": "求职",
                    },
                    "localized_rationale": {
                        "en": "Applications and interview preparation.",
                        "zh-CN": "求职申请与面试准备。",
                    },
                    "equivalence_status": "equivalent",
                },
            ),
            (
                "admission_decision",
                "matter:job-search",
                1,
                {
                    "status": "admitted",
                    "matter": {
                        "matter_id": "matter:job-search",
                        "source_ids": ("source:cover-letter:v1",),
                        "rationale": "Job-search source fixture",
                        "evidence_ids": (),
                        "admitted": True,
                        "semantic_identity_id": "semantic:job-search",
                        "object_kind": "matter",
                    },
                    "candidate": None,
                },
            ),
        )
    )

    page = service.object_catalog_page(start_year="2024")

    assert page["total_count"] == 1
    card = page["items"][0]
    assert card["matter_id"] == "matter:job-search"
    assert card["start_time"] == modified.isoformat()
    assert card["start_year"] == "2024"
    assert card["start_time_basis"] == "source_modified_time"
    assert card["start_time_source_provider"] == "filesystem"
