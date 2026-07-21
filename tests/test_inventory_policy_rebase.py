from __future__ import annotations

from matters.application.orchestrator import MatterService
from matters.inventory.owners import (
    CURRENT_TRACKING_POLICY_REVISION,
    CandidateScope,
    InventoryOccurrence,
    TrackingPolicy,
)


def test_current_inventory_policy_rebase_reuses_durable_occurrences(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    service = MatterService(
        private_root=tmp_path / "private",
        repository_root=repository,
    )
    scope = CandidateScope(
        scope_id="scope:gmail:tracked",
        revision=1,
        provider="gmail",
        root_locator="sha256:" + ("a" * 64),
        object_types=("message",),
    )
    occurrence = InventoryOccurrence(
        occurrence_id="gmail:message:opaque",
        provider="gmail",
        object_type="message",
        locator="gmail:message:opaque",
        metadata={
            "recommended_disposition": "tracked",
            "disposition_reason": "synthetic tracked message",
        },
        content_identity="sha256:" + ("b" * 64),
    )
    prior, _ = service.reconcile_inventory(
        scope=scope,
        policy=TrackingPolicy(
            policy_id="tracking-policy:default",
            revision=CURRENT_TRACKING_POLICY_REVISION - 1,
        ),
        occurrences=(occurrence,),
    )

    result = service.rebase_current_inventory_policy(
        provider="gmail",
        offset=0,
        limit=10,
    )

    assert service.inventory is not None
    current = service.inventory.latest_snapshot(scope.scope_id)
    assert current is not None
    assert current.revision > prior.revision
    assert current.policy_revision == CURRENT_TRACKING_POLICY_REVISION
    assert current.occurrences == prior.occurrences
    assert result == {
        "provider": "gmail",
        "scanned_scope_count": 1,
        "rebased_scope_count": 1,
        "already_current_scope_count": 0,
        "missing_snapshot_scope_count": 0,
        "next_offset": 0,
        "has_more": False,
        "status": "current",
    }
