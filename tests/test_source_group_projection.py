from __future__ import annotations

from dataclasses import asdict
import json

import pytest

from matters.application.source_group_projection import SourceGroupProjection
from matters.inventory.owners import InventoryOccurrence
from matters.provenance.storage_policy import SourceAvailability


ROOT_GROUP = "filesystem-group:root"
TRIP_GROUP = "filesystem-group:trip"
BOOKINGS_GROUP = "filesystem-group:bookings"


def _occurrence(
    occurrence_id: str,
    *,
    locator: str,
    object_type: str,
    chain: tuple[str, ...],
    labels: tuple[str, ...],
) -> InventoryOccurrence:
    return InventoryOccurrence(
        occurrence_id=occurrence_id,
        provider="filesystem",
        object_type=object_type,
        locator=locator,
        metadata={
            "source_group_chain": chain,
            "source_group_labels": labels,
            "display_name": locator.rsplit("\\", 1)[-1],
        },
        content_identity="c" * 64,
    )


def _trip_occurrences() -> tuple[InventoryOccurrence, ...]:
    return (
        _occurrence(
            "filesystem:hotel",
            locator=r"P:\private-data\Travel\Japan\hotel.docx",
            object_type="docx",
            chain=(ROOT_GROUP, TRIP_GROUP, BOOKINGS_GROUP),
            labels=("Documents", "Japan trip", "Bookings"),
        ),
        _occurrence(
            "filesystem:flight",
            locator=r"P:\private-data\Travel\Japan\flight.pdf",
            object_type="pdf",
            chain=(ROOT_GROUP, TRIP_GROUP, BOOKINGS_GROUP),
            labels=("Documents", "Japan trip", "Bookings"),
        ),
        _occurrence(
            "filesystem:plan",
            locator=r"P:\private-data\Travel\Japan\plan.md",
            object_type="markdown",
            chain=(ROOT_GROUP, TRIP_GROUP),
            labels=("Documents", "Japan trip"),
        ),
    )


def test_source_group_identity_and_page_are_stable_across_input_order() -> None:
    occurrences = _trip_occurrences()
    first = SourceGroupProjection.from_occurrences(occurrences).page(limit=20)
    second = SourceGroupProjection.from_occurrences(
        reversed(occurrences)
    ).page(limit=20)

    assert first == second
    assert {item.group_id for item in first.items} == {
        ROOT_GROUP,
        TRIP_GROUP,
        BOOKINGS_GROUP,
    }
    trip = next(item for item in first.items if item.group_id == TRIP_GROUP)
    assert trip.parent_group_id == ROOT_GROUP
    assert trip.direct_member_count == 1
    assert trip.total_member_count == 3
    assert trip.child_group_count == 1
    assert trip.source_types == ("docx", "markdown", "pdf")


def test_source_group_detail_is_paginated_and_marks_partial_availability() -> None:
    projection = SourceGroupProjection.from_occurrences(
        _trip_occurrences(),
        availability_by_occurrence={
            "filesystem:plan": SourceAvailability.SOURCE_UNAVAILABLE,
        },
    )

    first = projection.detail(
        TRIP_GROUP,
        member_offset=0,
        member_limit=2,
    )
    second = projection.detail(
        TRIP_GROUP,
        member_offset=2,
        member_limit=2,
    )

    assert first.summary.availability == "partial"
    assert first.child_group_ids == (BOOKINGS_GROUP,)
    assert first.member_total_count == 3
    assert len(first.members) == 2
    assert first.next_member_offset == 2
    assert len(second.members) == 1
    assert second.next_member_offset is None
    assert {
        member.availability for member in (*first.members, *second.members)
    } == {"available", "source_unavailable"}


def test_page_and_detail_never_emit_absolute_paths() -> None:
    private_windows_path = r"P:\private-data\Travel\Japan"
    private_posix_path = "/private-mount/Pictures"
    neighborhood_only = InventoryOccurrence(
        occurrence_id=f"{private_posix_path}/photo.jpg",
        provider="filesystem",
        object_type="image",
        locator=f"{private_posix_path}/photo.jpg",
        metadata={
            "source_neighborhood_id": private_posix_path,
            "display_name": f"{private_posix_path}/photo.jpg",
        },
        content_identity="d" * 64,
    )
    projection = SourceGroupProjection.from_occurrences(
        (*_trip_occurrences(), neighborhood_only)
    )

    page = projection.page(limit=20)
    detail_payloads = [
        asdict(projection.detail(item.group_id))
        for item in page.items
    ]
    public_json = json.dumps(
        {
            "page": asdict(page),
            "details": detail_payloads,
        },
        sort_keys=True,
    )

    assert private_windows_path not in public_json
    assert private_posix_path not in public_json
    assert "source-group:" in public_json


def test_source_group_query_and_error_boundaries_are_explicit() -> None:
    projection = SourceGroupProjection.from_occurrences(_trip_occurrences())

    page = projection.page(query="book", limit=20)
    assert [item.group_id for item in page.items] == [BOOKINGS_GROUP]
    with pytest.raises(KeyError, match="unknown SourceGroup"):
        projection.detail("source-group:missing")
    with pytest.raises(ValueError, match="limit"):
        projection.page(limit=0)


def test_gmail_messages_and_attachments_share_the_thread_group() -> None:
    thread = InventoryOccurrence(
        occurrence_id="gmail:thread:opaque",
        provider="gmail",
        object_type="thread",
        locator="gmail:thread:opaque",
        metadata={"display_name": "mail thread"},
    )
    message = InventoryOccurrence(
        occurrence_id="gmail:message:opaque",
        provider="gmail",
        object_type="message",
        locator="gmail:message:opaque",
        metadata={"display_name": "mail message"},
        parent_occurrence_id=thread.occurrence_id,
    )
    attachment = InventoryOccurrence(
        occurrence_id="gmail:attachment:opaque",
        provider="gmail",
        object_type="attachment",
        locator="gmail:attachment:opaque",
        metadata={"display_name": "ticket.pdf"},
        parent_occurrence_id=message.occurrence_id,
    )

    projection = SourceGroupProjection.from_occurrences(
        (attachment, message, thread)
    )
    message_chain = projection.group_chain(
        provider="gmail",
        occurrence_id=message.occurrence_id,
    )
    attachment_chain = projection.group_chain(
        provider="gmail",
        occurrence_id=attachment.occurrence_id,
    )

    assert len(message_chain) == len(attachment_chain) == 1
    assert message_chain[0].group_id == attachment_chain[0].group_id
    assert message_chain[0].title == "Gmail conversation"
    assert message_chain[0].total_member_count == 3


def test_codex_project_group_uses_human_label_without_exposing_workspace_id() -> None:
    occurrence = InventoryOccurrence(
        occurrence_id="codex:task:opaque",
        provider="codex",
        object_type="codex_task",
        locator="codex:task:opaque",
        metadata={
            "workspace_id": r"P:\private-data\workspace",
            "workspace_name": "Matters",
            "display_name": "Implement SourceGroup",
        },
    )

    projection = SourceGroupProjection.from_occurrences((occurrence,))
    page = projection.page()
    rendered = json.dumps(asdict(page), sort_keys=True)

    assert page.items[0].title == "Matters"
    assert r"P:\private-data\workspace" not in rendered
    assert page.items[0].group_id.startswith("source-group:")
