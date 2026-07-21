from __future__ import annotations

from datetime import datetime, timezone

from matters.providers.base import ProviderEnvelope
from matters.provenance.source_registry import SourceRegistry
from matters.timeline.start_boundary import earliest_start_boundary


def test_earliest_boundary_compares_claimed_and_record_times() -> None:
    boundary = earliest_start_boundary(
        (
            {
                "claimed_time": "2026-09-30T12:00:00+00:00",
                "record_time": "2026-03-10T08:30:00+00:00",
            },
        )
    )

    assert boundary is not None
    assert boundary.value == "2026-03-10T08:30:00+00:00"
    assert boundary.basis == "event_record_time"


def test_source_metadata_can_establish_an_earlier_start_without_an_event() -> None:
    modified = datetime(2024, 2, 3, 9, 15, tzinfo=timezone.utc)
    boundary = earliest_start_boundary(
        (),
        (
            {
                "provider": "filesystem",
                "source_time_metadata": {
                    "provider_metadata.modified_ns": int(
                        modified.timestamp() * 1_000_000_000
                    ),
                },
            },
            {
                "provider": "gmail",
                "content": {
                    "internal_date": "2025-06-01T10:00:00+00:00",
                },
            },
        ),
    )

    assert boundary is not None
    assert boundary.at == modified
    assert boundary.basis == "source_modified_time"
    assert boundary.provider == "filesystem"
    assert boundary.year == "2024"


def test_processing_due_and_hero_times_never_fill_start() -> None:
    boundary = earliest_start_boundary(
        (),
        (
            {
                "provider": "filesystem",
                "content": {
                    "processed_at": "2024-01-01T00:00:00+00:00",
                    "due_date": "2024-02-01T00:00:00+00:00",
                    "hero_generated_at": "2024-03-01T00:00:00+00:00",
                },
            },
        ),
    )

    assert boundary is None


def test_source_registry_retains_only_start_eligible_temporal_metadata() -> None:
    registry = SourceRegistry()
    result = registry.register(
        ProviderEnvelope(
            provider="filesystem",
            external_id="cover-letter",
            object_type="file",
            payload={"relative_path": "cover-letter.docx"},
            metadata={
                "modified_ns": 1_700_000_000_000_000_000,
                "processed_at": "2026-07-20T00:00:00+00:00",
                "due_date": "2026-08-01T00:00:00+00:00",
            },
        ),
        idempotency_key="cover-letter:v1",
    )

    assert result.source_version is not None
    assert result.source_version.source_time_metadata == {
        "provider_metadata.modified_ns": 1_700_000_000_000_000_000,
    }
