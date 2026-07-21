from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from matters.infrastructure.sqlite.store import SQLiteStore
from matters.providers.base import ProviderEnvelope
from matters.provenance.source_registry import SourceRegistry


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


def test_durable_registries_atomically_converge_identical_source_race(
    tmp_path: Path,
):
    repository_root = tmp_path / "repository"
    private_root = tmp_path / "private"
    repository_root.mkdir()
    registries = tuple(
        SourceRegistry(
            store=SQLiteStore(private_root, repository_root),
        )
        for _ in range(2)
    )

    def register(index: int):
        return registries[index].register(
            _envelope(),
            idempotency_key=f"concurrent:{index}",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(register, range(2)))

    assert {item.status for item in results} == {
        "source_version_created",
        "no_delta",
    }
    assert {item.source_version.version for item in results} == {1}
    history = tuple(
        registries[0].store.history(
            "source_version",
            results[0].source_version.source_id,
        )
    )
    assert len(history) == 1
