from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from matters.application.situation_graph import SituationGraphBuilder
from matters.domain.hierarchy import MatterContainmentEdge, MatterWorkItem
from matters.domain.relations import MatterRelationCandidate
from matters.timeline.events import Event


NOW = datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)


def _build_graph(*, relation_type: str = "depends_on"):
    return SituationGraphBuilder().build(
        root_matter_id="matter:trip",
        matter_records=(
            {
                "matter_id": "matter:trip",
                "evidence_ids": ("e-root",),
                "certainty": "reported",
                "confidence": "high",
                "semantic_revision": "trip-v3",
            },
            {
                "matter_id": "matter:flight",
                "evidence_ids": ("e-flight",),
                "certainty": "reported",
                "confidence": "bounded",
            },
        ),
        containment_edges=(
            MatterContainmentEdge(
                edge_id="containment:trip-flight",
                parent_matter_id="matter:trip",
                child_matter_id="matter:flight",
                role="required",
                confidence="bounded",
                rationale="The flight is required for this trip.",
                evidence_ids=("e-flight",),
                freshness="current",
            ),
        ),
        work_items=(
            MatterWorkItem(
                item_id="work:book-hotel",
                matter_id="matter:trip",
                kind="booking",
                status="planned",
                localized_title={
                    "en": "Book the hotel",
                    "zh-CN": "预订酒店",
                },
                localized_result={
                    "en": "Not booked yet",
                    "zh-CN": "尚未预订",
                },
                evidence_ids=("e-hotel",),
                planned_start="2026-07-21T08:00:00+00:00",
            ),
        ),
        events=(
            Event(
                event_id="event:flight-confirmed",
                kind="confirmation",
                modality="observed",
                record_time="2026-07-20T07:00:00+00:00",
                object_ref="matter:trip",
                evidence_ids=("e-event",),
            ),
        ),
        relations=(
            MatterRelationCandidate(
                source_matter_id="matter:trip",
                relation_type=relation_type,
                target_matter_id="matter:flight",
            ),
        ),
        generated_at=NOW,
        expires_at=NOW + timedelta(days=1),
    )


def test_graph_projects_primary_containment_and_typed_secondary_edges() -> None:
    graph = _build_graph()

    assert graph.advisory_only is True
    assert graph.canonical_write_allowed is False
    assert graph.coverage == "complete"
    assert set(graph.evidence_ids) == {
        "e-flight",
        "e-root",
        "e-event",
        "e-hotel",
    }

    primary = tuple(edge for edge in graph.edges if edge.primary_containment)
    assert [(edge.source_node_id, edge.target_node_id, edge.relation_type) for edge in primary] == [
        ("matter:trip", "matter:flight", "contains")
    ]
    assert {
        edge.relation_type for edge in graph.edges if not edge.primary_containment
    } == {"depends_on", "has_event", "has_work_item"}

    nodes = {node.node_id: node for node in graph.nodes}
    assert nodes["event:flight-confirmed"].certainty == "confirmed_observed"
    assert nodes["work:book-hotel"].certainty == "reported"
    assert nodes["work:book-hotel"].attributes["status"] == "planned"
    assert all(node.canonical_write_allowed is False for node in graph.nodes)
    assert all(edge.canonical_write_allowed is False for edge in graph.edges)


def test_graph_pages_edges_without_duplicates_and_hydrates_endpoints() -> None:
    graph = _build_graph()
    continuation = ""
    seen: list[str] = []

    while True:
        page = graph.page(continuation=continuation, limit=2, at=NOW)
        page_node_ids = {node.node_id for node in page.nodes}
        assert graph.root_matter_id in page_node_ids
        assert all(
            edge.source_node_id in page_node_ids
            and edge.target_node_id in page_node_ids
            for edge in page.edges
        )
        seen.extend(edge.edge_id for edge in page.edges)
        if not page.has_more:
            assert page.next_continuation == ""
            break
        continuation = page.next_continuation

    assert len(seen) == len(set(seen)) == len(graph.edges)


def test_graph_continuation_is_bound_to_one_snapshot() -> None:
    first = _build_graph(relation_type="depends_on")
    second = _build_graph(relation_type="related_to")
    continuation = first.page(limit=1).next_continuation

    with pytest.raises(ValueError, match="another graph snapshot"):
        second.page(continuation=continuation, limit=1)


@pytest.mark.parametrize(
    "relation",
    (
        {
            "source_matter_id": "matter:trip",
            "target_matter_id": "matter:flight",
            "relation_type": "causes",
            "causal": True,
            "certainty": "reported",
            "evidence_ids": ("e-flight",),
        },
        {
            "source_matter_id": "matter:trip",
            "target_matter_id": "matter:flight",
            "relation_type": "same_as",
            "auto_merge": True,
        },
    ),
)
def test_graph_rejects_unproven_causality_and_automatic_merge(
    relation: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        SituationGraphBuilder().build(
            root_matter_id="matter:trip",
            matter_records=(
                {"matter_id": "matter:trip", "evidence_ids": ("e-root",)},
                {"matter_id": "matter:flight", "evidence_ids": ("e-flight",)},
            ),
            relations=(relation,),
            generated_at=NOW,
            expires_at=NOW + timedelta(days=1),
        )


def test_graph_reports_expired_without_mutating_the_snapshot() -> None:
    graph = _build_graph()

    assert graph.currentness == "current"
    assert graph.effective_currentness(at=NOW + timedelta(days=2)) == "expired"
    assert graph.page(limit=10, at=NOW + timedelta(days=2)).currentness == "expired"
    assert graph.currentness == "current"


def test_matter_state_basis_preserves_historical_gap_and_unknown() -> None:
    graph = SituationGraphBuilder().build(
        root_matter_id="matter:trip",
        matter_records=(
            {
                "matter_id": "matter:trip",
                "state": "completed",
                "state_basis_modality": "inferred",
                "state_basis_scope": "historical_gap",
                "evidence_ids": ("e-ticket",),
            },
            {
                "matter_id": "matter:unmigrated",
                "state": "completed",
                "evidence_ids": ("e-old",),
            },
        ),
        containment_edges=(
            {
                "parent_matter_id": "matter:trip",
                "child_matter_id": "matter:unmigrated",
                "modality": "reported",
                "evidence_ids": ("e-old",),
            },
        ),
        generated_at=NOW,
        expires_at=NOW + timedelta(days=1),
    )

    nodes = {node.node_id: node for node in graph.nodes}
    assert nodes["matter:trip"].certainty == "ai_inferred"
    assert (
        nodes["matter:trip"].attributes["state_basis_scope"]
        == "historical_gap"
    )
    assert nodes["matter:unmigrated"].certainty == "unknown"


def test_graph_preserves_conflicting_certainty_instead_of_picking_a_winner():
    graph = SituationGraphBuilder().build(
        root_matter_id="matter:build-week",
        matter_records=(
            {
                "matter_id": "matter:build-week",
                "certainty": "reported",
                "confidence": "high",
                "state": "planned",
                "evidence_ids": ("evidence:registration",),
            },
            {
                "matter_id": "matter:build-week",
                "certainty": "ai_inferred",
                "confidence": "bounded",
                "state": "in_progress",
                "evidence_ids": ("evidence:workspace-activity",),
                "alternative_explanations": (
                    "Preparation may be paused.",
                ),
            },
        ),
        generated_at=NOW,
        expires_at=NOW + timedelta(days=1),
    )

    node = graph.nodes[0]
    assert node.certainty == "unknown"
    assert node.confidence == 0.65
    assert node.attributes["certainty_conflict"] == (
        "reported",
        "ai_inferred",
    )
    assert set(node.attributes["conflicting_attributes"]["state"]) == {
        "'planned'",
        "'in_progress'",
    }
    assert set(node.evidence_ids) == {
        "evidence:registration",
        "evidence:workspace-activity",
    }
    assert "Preparation may be paused." in node.alternatives
