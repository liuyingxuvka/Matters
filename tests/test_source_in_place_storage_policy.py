from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest

from matters.inventory.owners import InventoryOccurrence
from matters.provenance.storage_policy import (
    CleanupAction,
    ExternalOriginalReference,
    RetentionLimits,
    SourceAvailability,
    SourceUnavailableError,
    StorageClass,
    StoredArtifact,
    decide_cleanup,
)


UTC = timezone.utc
NOW = datetime(2026, 7, 20, 8, 0, tzinfo=UTC)


def test_storage_classes_are_the_five_source_in_place_owners() -> None:
    assert {item.value for item in StorageClass} == {
        "external_original",
        "durable_derived",
        "rebuildable_cache",
        "transient_staging",
        "recovery_backup",
    }


def test_external_original_keeps_private_locator_out_of_public_projection() -> None:
    private_root = r"P:\private-data\Documents"
    private_locator = r"Travel\Japan\passport-scan.pdf"
    occurrence = InventoryOccurrence(
        occurrence_id="filesystem:passport",
        provider="filesystem",
        object_type="pdf",
        locator=private_locator,
        metadata={"size": 100, "display_name": "passport-scan.pdf"},
        content_identity="A" * 64,
    )

    reference = ExternalOriginalReference.from_occurrence(
        scope_id="scope:documents",
        private_root_locator=private_root,
        occurrence=occurrence,
    )
    public_json = json.dumps(reference.to_public_mapping(), sort_keys=True)

    assert reference.storage_class is StorageClass.EXTERNAL_ORIGINAL
    assert reference.content_fingerprint == f"sha256:{'a' * 64}"
    assert reference.metadata_fingerprint.startswith("sha256:")
    assert reference.reference_id.startswith("source-ref:")
    assert reference.readable is True
    assert private_root not in repr(reference)
    assert private_locator not in repr(reference)
    assert private_root not in public_json
    assert private_locator not in public_json
    assert "passport-scan.pdf" not in public_json


def test_external_original_unavailable_state_is_explicit_and_path_free() -> None:
    reference = ExternalOriginalReference(
        provider="filesystem",
        scope_id="scope:photos",
        occurrence_id="filesystem:missing",
        private_root_locator="/private-mount/Pictures",
        private_locator="missing/photo.jpg",
        metadata_fingerprint="b" * 64,
    ).mark_unavailable(reason="provider_not_mounted")

    assert reference.availability is SourceAvailability.SOURCE_UNAVAILABLE
    assert reference.readable is False
    assert reference.to_public_mapping()["availability"] == "source_unavailable"
    with pytest.raises(SourceUnavailableError):
        reference.require_readable()


@pytest.mark.parametrize(
    ("artifact", "usage_bytes", "expected_action", "expected_reason"),
    [
        (
            StoredArtifact(
                artifact_id="stage:committed",
                storage_class=StorageClass.TRANSIENT_STAGING,
                byte_count=100,
                created_at=NOW - timedelta(minutes=5),
                terminal_committed=True,
            ),
            100,
            CleanupAction.DELETE,
            "terminal_commit",
        ),
        (
            StoredArtifact(
                artifact_id="stage:expired",
                storage_class=StorageClass.TRANSIENT_STAGING,
                byte_count=200,
                created_at=NOW - timedelta(hours=25),
            ),
            200,
            CleanupAction.DELETE,
            "ttl_expired",
        ),
        (
            StoredArtifact(
                artifact_id="stage:quota",
                storage_class=StorageClass.TRANSIENT_STAGING,
                byte_count=300,
                created_at=NOW - timedelta(minutes=5),
            ),
            1_001,
            CleanupAction.DELETE,
            "quota_pressure",
        ),
        (
            StoredArtifact(
                artifact_id="stage:active",
                storage_class=StorageClass.TRANSIENT_STAGING,
                byte_count=400,
                created_at=NOW - timedelta(days=10),
                reference_count=1,
            ),
            10_000,
            CleanupAction.DEFER,
            "active_reference",
        ),
        (
            StoredArtifact(
                artifact_id="derived:evidence",
                storage_class=StorageClass.DURABLE_DERIVED,
                byte_count=500,
                created_at=NOW - timedelta(days=365),
            ),
            10_000,
            CleanupAction.RETAIN,
            "storage_class_not_reclaimable",
        ),
        (
            StoredArtifact(
                artifact_id="backup:offline",
                storage_class=StorageClass.RECOVERY_BACKUP,
                byte_count=600,
                created_at=NOW - timedelta(days=365),
                offline_recovery_owner_id="offline-migration:test",
            ),
            10_000,
            CleanupAction.DEFER,
            "offline_recovery_owner",
        ),
    ],
)
def test_cleanup_decision_covers_commit_ttl_quota_and_active_references(
    artifact: StoredArtifact,
    usage_bytes: int,
    expected_action: CleanupAction,
    expected_reason: str,
) -> None:
    decision = decide_cleanup(
        artifact,
        limits=RetentionLimits(
            transient_ttl=timedelta(hours=24),
            transient_quota_bytes=1_000,
        ),
        evaluated_at=NOW,
        class_usage_bytes=usage_bytes,
    )

    assert decision.action is expected_action
    assert decision.reason == expected_reason
    assert decision.reclaimable_bytes == (
        artifact.byte_count
        if expected_action is CleanupAction.DELETE
        else 0
    )


def test_external_original_cannot_claim_local_bytes() -> None:
    with pytest.raises(ValueError, match="cannot own local bytes"):
        StoredArtifact(
            artifact_id="original:invalid",
            storage_class=StorageClass.EXTERNAL_ORIGINAL,
            byte_count=1,
            created_at=NOW,
        )


def test_recovery_backup_requires_explicit_offline_owner() -> None:
    with pytest.raises(ValueError, match="offline recovery owner"):
        StoredArtifact(
            artifact_id="backup:invalid",
            storage_class=StorageClass.RECOVERY_BACKUP,
            byte_count=1,
            created_at=NOW,
        )


def test_fingerprints_reject_non_sha256_values() -> None:
    with pytest.raises(ValueError, match="fingerprint"):
        ExternalOriginalReference(
            provider="filesystem",
            scope_id="scope:documents",
            occurrence_id="filesystem:invalid",
            private_root_locator=r"C:\Documents",
            private_locator="notes.txt",
            metadata_fingerprint="not-a-fingerprint",
        )
