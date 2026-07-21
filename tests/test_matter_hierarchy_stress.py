from __future__ import annotations

import json
from time import perf_counter

import pytest

from matters.application.orchestrator import MatterService


CHILD_CARD_PAGE_LIMIT = 50


def _service(tmp_path) -> MatterService:
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    return MatterService(
        private_root=tmp_path / "home",
        repository_root=repository_root,
    )


def _projection(matter_id: str) -> dict[str, object]:
    title = matter_id.removeprefix("matter:").replace("-", " ").title()
    semantic_revision = f"semantic:{matter_id}:1"
    return {
        "matter_id": matter_id,
        "semantic_revision": semantic_revision,
        "state": "planned",
        "evidence_ids": (),
        "localized_values": {
            "en": title,
            "zh-CN": f"{title}（中文）",
        },
        "localized_rationale": {
            "en": f"Current status for {title}",
            "zh-CN": f"{title} 的当前状态",
        },
        "locale_revisions": {
            "en": semantic_revision,
            "zh-CN": semantic_revision,
        },
        "locales": ("en", "zh-CN"),
        "equivalence_status": "equivalent",
    }


def _seed_projected_matters(
    service: MatterService,
    matter_ids: tuple[str, ...],
) -> None:
    service.store.append_many(
        tuple(
            ("projection", matter_id, 1, _projection(matter_id))
            for matter_id in matter_ids
        )
    )
    service.store.append_many(
        tuple(
            (
                "admission_decision",
                matter_id,
                1,
                {
                    "status": "admitted",
                    "matter": {"matter_id": matter_id},
                },
            )
            for matter_id in matter_ids
        )
    )


def _attach(
    service: MatterService,
    parent_matter_id: str,
    child_matter_id: str,
    *,
    ordinal: int,
) -> None:
    service.attach_matter_child(
        parent_matter_id=parent_matter_id,
        child_matter_id=child_matter_id,
        role="required",
        confidence="bounded",
        rationale="The child is independently trackable inside the parent.",
        evidence_ids=(f"evidence:{parent_matter_id}:{child_matter_id}",),
        ordinal=ordinal,
    )


def _seed_current_edges(
    service: MatterService,
    parent_matter_id: str,
    child_ids: tuple[str, ...],
    ordinals: dict[str, int],
) -> None:
    """Materialize a large read-side fixture without timing write rollups."""

    service.store.append_many(
        tuple(
            (
                "matter_containment_edge",
                service.hierarchy._edge_id(parent_matter_id, child_id),
                1,
                {
                    "edge_id": service.hierarchy._edge_id(
                        parent_matter_id,
                        child_id,
                    ),
                    "parent_matter_id": parent_matter_id,
                    "child_matter_id": child_id,
                    "role": "required",
                    "confidence": "bounded",
                    "rationale": (
                        "The child is independently trackable inside the parent."
                    ),
                    "evidence_ids": (
                        f"evidence:{parent_matter_id}:{child_id}",
                    ),
                    "ordinal": ordinals[child_id],
                    "boundary_revision": 1,
                    "freshness": "current",
                    "active": True,
                    "updated_at": "2026-07-19T00:00:00+00:00",
                },
            )
            for child_id in child_ids
        )
    )


def _hierarchy_ids_by_page(
    service: MatterService,
    parent_matter_id: str,
    *,
    page_size: int,
) -> tuple[str, ...]:
    offset = 0
    items: list[str] = []
    total_count = None
    while total_count is None or offset < total_count:
        page = service.hierarchy.children_page(
            parent_matter_id,
            offset=offset,
            limit=page_size,
        )
        if total_count is None:
            total_count = int(page["total_count"])
        assert int(page["total_count"]) == total_count
        current = tuple(
            str(item["child_matter_id"]) for item in page["items"]
        )
        if not current:
            break
        items.extend(current)
        offset += len(current)
    assert total_count is not None
    assert len(items) == total_count
    return tuple(items)


@pytest.mark.parametrize("child_count", (0, 1, 5, 50, 500))
def test_child_cardinality_matrix_is_paged_deterministically_and_bounded(
    tmp_path,
    child_count,
):
    service = _service(tmp_path)
    root_id = "matter:root"
    child_ids = tuple(
        f"matter:child-{index:04d}" for index in range(child_count)
    )
    _seed_projected_matters(service, (root_id, *child_ids))
    service.hierarchy.register_matter(
        root_id,
        change_ref="test:root-registration",
    )
    ordinals = {
        child_id: (index * 17) % 23
        for index, child_id in enumerate(child_ids)
    }
    if child_count == 500:
        # The 500-row case is a read/projection boundary test. The ordinary
        # write API refreshes every affected rollup synchronously, so repeating
        # it 500 times would turn this focused suite into an unbounded runtime
        # test instead of a deterministic hierarchy contract.
        _seed_current_edges(service, root_id, child_ids, ordinals)
        service.hierarchy.register_matter(
            root_id,
            change_ref="test:500-child-index-materialized",
        )
    else:
        for child_id in child_ids:
            _attach(
                service,
                root_id,
                child_id,
                ordinal=ordinals[child_id],
            )

    expected = tuple(
        sorted(child_ids, key=lambda item: (ordinals[item], item))
    )
    first_read = _hierarchy_ids_by_page(
        service,
        root_id,
        page_size=37,
    )
    second_read = _hierarchy_ids_by_page(
        service,
        root_id,
        page_size=61,
    )
    assert first_read == expected
    assert second_read == expected
    assert len(set(first_read)) == child_count

    summary = service.store.current("matter_hierarchy_summary", root_id)
    assert summary is not None
    assert summary["child_count"] == child_count
    assert sum(summary["child_state_counts"].values()) == child_count

    if child_count == 500:
        detail = service.matter_detail(matter_id=root_id)
        assert detail["sub_matters"]["total_count"] == 500
        assert len(detail["sub_matters"]["items"]) == CHILD_CARD_PAGE_LIMIT
        assert detail["sub_matters"]["has_more"] is True
        assert len(detail["timeline"]) <= 200
        assert detail["timeline_summary"]["descendant_count"] == 500
        assert all(
            "children" not in child for child in detail["sub_matters"]["items"]
        )
        assert "completion_barrier_ids" not in detail["children_summary"]
        # The public projection stays comfortably bounded and does not embed
        # the full recursive tree or private completion identities.
        assert len(json.dumps(detail, ensure_ascii=False)) < 2_000_000


@pytest.mark.parametrize("depth", (1, 2, 5, 20))
def test_depth_matrix_has_stable_paths_and_direct_only_parent_summaries(
    tmp_path,
    depth,
):
    service = _service(tmp_path)
    matter_ids = tuple(
        f"matter:level-{index:02d}" for index in range(depth + 1)
    )
    _seed_projected_matters(service, matter_ids)
    service.hierarchy.register_matter(
        matter_ids[0],
        change_ref="test:depth-root-registration",
    )
    for index in range(depth):
        _attach(
            service,
            matter_ids[index],
            matter_ids[index + 1],
            ordinal=index,
        )

    assert service.hierarchy.path(matter_ids[-1]) == matter_ids
    assert service.hierarchy.ancestors(
        matter_ids[-1],
        current_only=True,
    ) == tuple(reversed(matter_ids[:-1]))
    descendants = service.store.hierarchy_descendant_ids_page(
        matter_ids[0],
        offset=0,
        limit=100,
        current_only=True,
    )
    assert descendants == (matter_ids[1:], depth)

    root_summary = service.store.current(
        "matter_hierarchy_summary",
        matter_ids[0],
    )
    assert root_summary["child_count"] == 1
    assert root_summary["required_incomplete_count"] == 1
    detail = service.matter_detail(matter_id=matter_ids[0])
    assert detail["sub_matters"]["total_count"] == 1
    assert detail["timeline_summary"]["descendant_count"] == depth
    assert detail["timeline_summary"]["truncated"] is False


def test_hierarchy_pages_and_paths_remain_identical_after_restart(tmp_path):
    service = _service(tmp_path)
    root_id = "matter:restart-root"
    child_ids = tuple(f"matter:restart-{index:03d}" for index in range(75))
    _seed_projected_matters(service, (root_id, *child_ids))
    service.hierarchy.register_matter(
        root_id,
        change_ref="test:restart-root-registration",
    )
    ordinals = {
        child_id: (index * 11) % 9
        for index, child_id in enumerate(child_ids)
    }
    for child_id in child_ids:
        _attach(
            service,
            root_id,
            child_id,
            ordinal=ordinals[child_id],
        )

    before = _hierarchy_ids_by_page(service, root_id, page_size=13)
    before_paths = tuple(
        service.hierarchy.path(child_id) for child_id in child_ids
    )
    restarted = MatterService(
        private_root=service.config.private_root,
        repository_root=service.config.repository_root,
    )
    after = _hierarchy_ids_by_page(restarted, root_id, page_size=17)
    after_paths = tuple(
        restarted.hierarchy.path(child_id) for child_id in child_ids
    )

    assert restarted.migrated_root_hierarchy_count == 0
    assert after == before
    assert after_paths == before_paths
    assert restarted.store.current(
        "matter_hierarchy_summary",
        root_id,
    )["child_count"] == 75


def test_long_chain_rejects_cycle_and_second_primary_parent_without_delta(
    tmp_path,
):
    service = _service(tmp_path)
    chain = tuple(f"matter:chain-{index:02d}" for index in range(21))
    other_root = "matter:other-root"
    _seed_projected_matters(service, (*chain, other_root))
    service.hierarchy.register_matter(
        chain[0],
        change_ref="test:chain-root-registration",
    )
    service.hierarchy.register_matter(
        other_root,
        change_ref="test:other-root-registration",
    )
    for index in range(20):
        _attach(
            service,
            chain[index],
            chain[index + 1],
            ordinal=index,
        )

    before_descendants = service.hierarchy.descendants(
        chain[0],
        current_only=True,
    )
    before_parent = service.store.hierarchy_parent_edge(
        chain[10],
        current_only=True,
    )
    with pytest.raises(ValueError, match="cycle"):
        _attach(
            service,
            chain[-1],
            chain[0],
            ordinal=21,
        )
    with pytest.raises(ValueError, match="explicit reparent"):
        _attach(
            service,
            other_root,
            chain[10],
            ordinal=10,
        )

    assert service.hierarchy.descendants(
        chain[0],
        current_only=True,
    ) == before_descendants
    assert len(before_descendants) == 20
    assert (
        service.store.hierarchy_parent_edge(
            chain[10],
            current_only=True,
        )
        == before_parent
    )


def test_bounded_batch_attaches_200_children_once_with_practical_throughput(
    tmp_path,
):
    service = _service(tmp_path)
    root_id = "matter:batch-root"
    child_ids = tuple(f"matter:batch-{index:03d}" for index in range(200))
    _seed_projected_matters(service, (root_id, *child_ids))
    service.hierarchy.register_matter(
        root_id,
        change_ref="test:batch-root-registration",
    )
    attachments = tuple(
        {
            "child_matter_id": child_id,
            "role": "required",
            "confidence": "bounded",
            "rationale": "A bounded child admitted in one hierarchy batch.",
            "evidence_ids": (f"evidence:{child_id}",),
            "ordinal": index % 17,
        }
        for index, child_id in enumerate(child_ids)
    )
    summary_history_before = len(
        service.store.history("matter_hierarchy_summary", root_id)
    )

    started = perf_counter()
    first = service.attach_matter_children_batch(
        parent_matter_id=root_id,
        attachments=attachments,
        rationale="Attach the complete bounded sibling inventory.",
        evidence_ids=("evidence:batch-inventory",),
    )
    duration = perf_counter() - started
    edge_history_count = len(
        service.store.history(
            "matter_containment_edge",
            service.hierarchy._edge_id(root_id, child_ids[0]),
        )
    )
    summary_history_after = len(
        service.store.history("matter_hierarchy_summary", root_id)
    )
    second = service.attach_matter_children_batch(
        parent_matter_id=root_id,
        attachments=attachments,
        rationale="Attach the complete bounded sibling inventory.",
        evidence_ids=("evidence:batch-inventory",),
    )

    assert duration < 45
    assert first["change_kind"] == "batch_attach"
    assert second["revision_id"] == first["revision_id"]
    assert summary_history_after == summary_history_before + 1
    assert (
        len(service.store.history("matter_hierarchy_summary", root_id))
        == summary_history_after
    )
    assert (
        len(
            service.store.history(
                "matter_containment_edge",
                service.hierarchy._edge_id(root_id, child_ids[0]),
            )
        )
        == edge_history_count
    )
    assert service.hierarchy.children_page(
        root_id,
        offset=0,
        limit=200,
    )["total_count"] == 200
    assert service.store.current(
        "matter_hierarchy_summary",
        root_id,
    )["child_count"] == 200
    requests = tuple(
        service.store.iter_current(
            "matter_hierarchy_batch_publish_request"
        )
    )
    assert len(requests) == 1
    assert requests[0]["status"] == "current"


def test_batch_rejects_one_conflicting_parent_without_partial_writes(tmp_path):
    service = _service(tmp_path)
    matter_ids = (
        "matter:root-a",
        "matter:root-b",
        "matter:already-parented",
        "matter:must-not-attach",
    )
    _seed_projected_matters(service, matter_ids)
    service.hierarchy.register_matter(
        "matter:root-a",
        change_ref="test:root-a",
    )
    service.hierarchy.register_matter(
        "matter:root-b",
        change_ref="test:root-b",
    )
    _attach(
        service,
        "matter:root-a",
        "matter:already-parented",
        ordinal=0,
    )

    with pytest.raises(ValueError, match="explicit reparent"):
        service.attach_matter_children_batch(
            parent_matter_id="matter:root-b",
            attachments=(
                {
                    "child_matter_id": "matter:must-not-attach",
                    "role": "required",
                    "confidence": "bounded",
                    "rationale": "This valid row must roll back with the batch.",
                    "evidence_ids": ("evidence:new",),
                },
                {
                    "child_matter_id": "matter:already-parented",
                    "role": "required",
                    "confidence": "bounded",
                    "rationale": "This row conflicts with the current parent.",
                    "evidence_ids": ("evidence:conflict",),
                },
            ),
            rationale="An invalid batch must have no partial edge effects.",
        )

    assert service.store.hierarchy_parent_edge(
        "matter:must-not-attach",
        current_only=True,
    ) is None
    assert (
        service.store.hierarchy_parent_edge(
            "matter:already-parented",
            current_only=True,
        )["parent_matter_id"]
        == "matter:root-a"
    )
    assert service.store.count_current(
        "matter_hierarchy_batch_publish_request"
    ) == 0
    with pytest.raises(ValueError, match="cycle"):
        service.attach_matter_children_batch(
            parent_matter_id="matter:already-parented",
            attachments=(
                {
                    "child_matter_id": "matter:root-a",
                    "role": "required",
                    "confidence": "bounded",
                    "rationale": "A batch cannot close an ancestor cycle.",
                    "evidence_ids": ("evidence:cycle",),
                },
            ),
            rationale="Reject a cyclic batch without changing current edges.",
        )
    assert service.store.count_current(
        "matter_hierarchy_batch_publish_request"
    ) == 0


def test_batch_size_and_duplicate_child_bounds_fail_before_writes(tmp_path):
    service = _service(tmp_path)
    oversized = tuple(
        {
            "child_matter_id": f"matter:oversized-{index:03d}",
            "role": "required",
            "confidence": "bounded",
            "rationale": "The batch size gate runs before Matter lookup.",
            "evidence_ids": (f"evidence:oversized-{index:03d}",),
        }
        for index in range(501)
    )
    with pytest.raises(ValueError, match="between 1 and 500"):
        service.attach_matter_children_batch(
            parent_matter_id="matter:unavailable-parent",
            attachments=oversized,
            rationale="Reject an oversized write before side effects.",
        )

    _seed_projected_matters(
        service,
        ("matter:duplicate-root", "matter:duplicate-child"),
    )
    with pytest.raises(ValueError, match="duplicate children"):
        service.attach_matter_children_batch(
            parent_matter_id="matter:duplicate-root",
            attachments=(
                {
                    "child_matter_id": "matter:duplicate-child",
                    "role": "required",
                    "confidence": "bounded",
                    "rationale": "First duplicate.",
                    "evidence_ids": ("evidence:duplicate-1",),
                },
                {
                    "child_matter_id": "matter:duplicate-child",
                    "role": "optional",
                    "confidence": "bounded",
                    "rationale": "Second duplicate.",
                    "evidence_ids": ("evidence:duplicate-2",),
                },
            ),
            rationale="Reject ambiguous duplicate child ownership.",
        )
    assert service.store.count_current(
        "matter_hierarchy_batch_publish_request"
    ) == 0


def test_interrupted_batch_publication_recovers_on_service_restart(
    tmp_path,
    monkeypatch,
):
    service = _service(tmp_path)
    root_id = "matter:recover-root"
    child_id = "matter:recover-child"
    _seed_projected_matters(service, (root_id, child_id))
    service.hierarchy.register_matter(
        root_id,
        change_ref="test:recover-root-registration",
    )

    def interrupt_after_atomic_commit(_request_id):
        raise RuntimeError("simulated interruption after edge commit")

    monkeypatch.setattr(
        service.hierarchy,
        "_recover_batch_request",
        interrupt_after_atomic_commit,
    )
    with pytest.raises(RuntimeError, match="simulated interruption"):
        service.attach_matter_children_batch(
            parent_matter_id=root_id,
            attachments=(
                {
                    "child_matter_id": child_id,
                    "role": "required",
                    "confidence": "bounded",
                    "rationale": "Recover this child after restart.",
                    "evidence_ids": ("evidence:recover",),
                },
            ),
            rationale="Exercise durable deferred publication.",
        )
    pending = tuple(
        service.store.iter_current(
            "matter_hierarchy_batch_publish_request"
        )
    )
    assert pending[0]["status"] == "pending"
    assert service.store.hierarchy_parent_edge(
        child_id,
        current_only=True,
    )["parent_matter_id"] == root_id

    restarted = MatterService(
        private_root=service.config.private_root,
        repository_root=service.config.repository_root,
    )
    recovered = tuple(
        restarted.store.iter_current(
            "matter_hierarchy_batch_publish_request"
        )
    )
    assert restarted.hierarchy.recovered_batch_count == 1
    assert recovered[0]["status"] == "current"
    assert restarted.store.current(
        "matter_hierarchy_summary",
        root_id,
    )["child_count"] == 1
