from __future__ import annotations

from hashlib import sha256

import pytest

from matters.providers.cloud import (
    CloudAuthorizedPage,
    CloudOccurrence,
    CloudReadManifest,
    CloudReadOnlyAdapter,
)


def _opaque(value: str) -> str:
    return "sha256:" + sha256(value.encode("utf-8")).hexdigest()


def _manifest() -> CloudReadManifest:
    return CloudReadManifest(
        scope_id="scope:synthetic-cloud",
        provider_id="synthetic-cloud",
        account_ref=_opaque("account"),
        root_ref=_opaque("root"),
        authorization_revision="authorization:1",
        policy_revision="policy:1",
        configured=True,
    )


def test_optional_cloud_source_is_visibly_unconfigured_not_empty_complete():
    adapter = CloudReadOnlyAdapter()

    capability = adapter.capability()
    page = adapter.discover()

    assert capability.status == "unconfigured"
    assert page.status == "unconfigured"
    assert page.coverage == "unknown"
    assert not page.terminal
    assert page.reason == "optional_cloud_source_unconfigured"


def test_cloud_placeholder_is_complete_metadata_inventory_without_content():
    page = CloudAuthorizedPage(
        scope_id="scope:synthetic-cloud",
        provider_id="synthetic-cloud",
        authorization_revision="authorization:1",
        policy_revision="policy:1",
        requested_cursor="",
        next_cursor="",
        terminal=True,
        occurrences=(
            CloudOccurrence(
                "object-1",
                "cloud_file",
                {"name": "synthetic-placeholder.txt"},
                hydrated=False,
            ),
        ),
    )
    adapter = CloudReadOnlyAdapter(_manifest(), page_source=lambda _cursor: page)

    result = adapter.discover()

    assert result.status == "configured"
    assert result.terminal
    assert result.coverage == "complete"
    assert result.items[0].disposition == "metadata_only"
    assert result.items[0].reason == "stable_content_unavailable"
    assert "content" not in result.items[0].envelope.payload


def test_hydrated_cloud_content_requires_tracking_and_is_deterministic():
    occurrence = CloudOccurrence(
        "object-1",
        "cloud_file",
        {"name": "synthetic.txt"},
        hydrated=True,
        content=b"synthetic content",
    )
    page = CloudAuthorizedPage(
        scope_id="scope:synthetic-cloud",
        provider_id="synthetic-cloud",
        authorization_revision="authorization:1",
        policy_revision="policy:1",
        requested_cursor="",
        next_cursor="",
        terminal=True,
        occurrences=(occurrence,),
    )
    adapter = CloudReadOnlyAdapter(_manifest(), page_source=lambda _cursor: page)
    external_id = adapter.discover().items[0].envelope.external_id

    with pytest.raises(
        PermissionError,
        match="current_tracked_disposition_required",
    ):
        adapter.read(
            object_ids=(external_id,),
            tracking_dispositions={external_id: "metadata_only"},
        )

    first = adapter.read(
        object_ids=(external_id,),
        tracking_dispositions={external_id: "tracked"},
    )
    retry = adapter.read(
        object_ids=(external_id,),
        tracking_dispositions={external_id: "tracked"},
    )

    assert first == retry
    assert first[0].payload["content"] == b"synthetic content"
