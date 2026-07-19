from matters.providers.base import ProviderEnvelope
from matters.provenance.source_registry import SourceRegistry
from dataclasses import FrozenInstanceError
import pytest


def _envelope(value=1, **changes):
    values = {
        "provider": "fake",
        "external_id": "one",
        "object_type": "object",
        "payload": {"value": value},
    }
    values.update(changes)
    return ProviderEnvelope(**values)


def test_versions_separate_content_metadata_retry_and_tombstone():
    registry = SourceRegistry()
    first = registry.register(_envelope(), idempotency_key="a")
    retry = registry.register(_envelope(), idempotency_key="a")
    metadata = registry.register(
        _envelope(metadata={"label": "changed"}),
        idempotency_key="b",
    )
    changed = registry.register(_envelope(2), idempotency_key="c")
    deleted = registry.register(_envelope(2), idempotency_key="d", deleted=True)
    assert first.status == "source_version_created"
    assert retry.status == "no_delta"
    assert metadata.status == "metadata_revision_created"
    assert changed.status == "source_version_created"
    assert deleted.status == "tombstone_created"
    history = registry.history(first.source_version.source_id)
    assert [item.version for item in history] == [1, 2, 3, 4]
    assert history[0].content == {"value": 1}
    assert history[-1].tombstone
    with pytest.raises(FrozenInstanceError):
        history[0].content_hash = "ai-rewrite"
