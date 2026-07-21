from hashlib import sha256
import json

import pytest

from matters.cli.main import main
from matters.infrastructure.sqlite.store import SQLiteStore
from matters.provenance.source_in_place_migration import (
    apply_database_batch,
    clean_staging,
    create_verified_backup,
    reclaim_orphan_blobs,
    residual_report,
    verify_backup,
    verify_migration,
)


def _blob(private_root, content):
    digest = sha256(content).hexdigest()
    path = private_root / "blobs" / digest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return "sha256:" + digest


def test_offline_source_in_place_migration_is_backed_up_bounded_and_resumable(
    tmp_path,
):
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    backup = tmp_path / "recovery" / "source-in-place"
    repository.mkdir()
    store = SQLiteStore(private, repository)

    source = {
        "source_id": "source:mail",
        "version": 1,
        "provider": "gmail",
        "external_reference": {
            "provider": "gmail",
            "external_id": "message-one",
            "object_type": "gmail_message",
            "locator": "gmail://message-one",
        },
        "content": {
            "body_text": "copied original body",
            "internal_date": "2026-07-18T12:00:00Z",
            "headers": {"subject": "Private subject"},
        },
        "content_hash": "sha256:" + "1" * 64,
        "metadata_hash": "sha256:" + "2" * 64,
        "predecessor_version": None,
        "tombstone": False,
    }
    store.append("source_version", "source:mail", 1, source)
    store.append(
        "candidate_scope",
        "scope:gmail",
        1,
        {
            "scope_id": "scope:gmail",
            "revision": 1,
            "provider": "gmail",
            "root_locator": "authorized-account",
            "object_types": ("gmail_message",),
            "active": True,
        },
    )
    with store.connection() as connection:
        connection.execute(
            "INSERT INTO inventory_occurrence_current"
            "(scope_id,object_id,inventory_revision,provider,object_type,"
            "disposition,occurrence_payload) VALUES(?,?,?,?,?,?,?)",
            (
                "scope:gmail",
                "message-one",
                1,
                "gmail",
                "gmail_message",
                "tracked",
                json.dumps(
                    {
                        "occurrence_id": "message-one",
                        "provider": "gmail",
                        "object_type": "gmail_message",
                        "locator": "message-one",
                        "metadata": {},
                        "content_identity": "sha256:" + "3" * 64,
                        "discovery_reason": "enumerated",
                        "parent_occurrence_id": "",
                    },
                    sort_keys=True,
                ),
            ),
        )
    processing = {
        "terminal_status": "complete",
        "registration": {
            "status": "source_version_created",
            "reason": "",
            "source_version": source,
        },
    }
    store.append("source_processing_result", "source:mail", 1, processing)
    store.put_idempotency(
        "source_registration",
        "gmail:message-one",
        {
            "status": "source_version_created",
            "reason": "",
            "source_version": source,
        },
    )

    preview_original = _blob(private, b"legacy-preview-original")
    preview_hero = _blob(private, b"legacy-preview-hero")
    preview_thumb = _blob(private, b"legacy-preview-thumb")
    store.append(
        "visual_asset",
        "visual:document",
        1,
        {
            "asset_id": "visual:document",
            "source_revision_id": "source:mail:1",
            "occurrence_id": "occurrence:mail",
            "kind": "document_preview",
            "media_type": "image/jpeg",
            "original_blob_ref": preview_original,
            "hero_blob_ref": preview_hero,
            "thumbnail_blob_ref": preview_thumb,
            "preview_token": "preview:document",
            "width": 1200,
            "height": 750,
            "current": True,
            "display_allowed": True,
            "evidence_ids": [],
            "localized_alt": {"en": "Document", "zh-CN": "文档"},
            "localized_reason": {"en": "Legacy", "zh-CN": "旧版"},
            "derivation_id": "legacy",
        },
    )
    store.append(
        "visual_preview_token",
        "preview:document",
        1,
        {
            "preview_token": "preview:document",
            "asset_id": "visual:document",
            "thumbnail_blob_ref": preview_thumb,
            "hero_blob_ref": preview_hero,
            "media_type": "image/jpeg",
            "current": True,
            "display_allowed": True,
        },
    )

    child_blob = _blob(private, b"legacy-child-hero")
    store.append(
        "generated_hero_record",
        "matter:child",
        1,
        {
            "matter_id": "matter:child",
            "status": "generated_current",
            "private_asset_token": "hero:child",
            "private_blob_ref": child_blob,
        },
    )
    store.append(
        "generated_hero_token",
        "hero:child",
        1,
        {
            "private_asset_token": "hero:child",
            "private_blob_ref": child_blob,
            "media_type": "image/png",
            "current": True,
            "display_allowed": True,
        },
    )
    with store.connection() as connection:
        connection.execute(
            "INSERT INTO matter_hierarchy_index"
            "(child_matter_id,parent_matter_id,edge_id,role,ordinal,freshness) "
            "VALUES(?,?,?,?,?,?)",
            (
                "matter:child",
                "matter:root",
                "edge:child",
                "sub_matter",
                0,
                "current",
            ),
        )

    (private / "connector-pages").mkdir()
    (private / "connector-pages" / "page.json").write_text(
        "copied connector page",
        encoding="utf-8",
    )
    (private / "generated-hero-staging").mkdir()
    (private / "generated-hero-staging" / "candidate.png").write_bytes(
        b"staged"
    )

    before = residual_report(private / "matters.sqlite3")
    assert before["unrebased_source_snapshot_count"] == 1
    assert before["source_snapshot_raw_count"] == 1
    assert before["processing_snapshot_raw_count"] == 1
    assert before["idempotency_raw_count"] == 1
    assert before["current_source_pointer_readable_count"] == 1
    assert before["raw_source_pointer_blocked_count"] == 0
    assert before["active_document_preview_count"] == 1
    assert before["current_child_hero_count"] == 1

    manifest = create_verified_backup(
        private_root=private,
        backup_root=backup,
    )
    assert manifest["status"] == "verified_restorable_backup"
    assert verify_backup(backup)["status"] == "verified_restorable_backup"

    phases = []
    for _ in range(20):
        result = apply_database_batch(
            private_root=private,
            backup_root=backup,
            limit=1,
        )
        phases.append(result["phase"])
        if not result["has_more"]:
            break
    assert phases[-1] == "database"
    assert {
        "source_pointer_rebase",
        "source_snapshots",
        "processing_snapshots",
        "source_idempotency",
        "document_previews",
        "descendant_heroes",
    } <= set(phases)

    current_source = store.current("source_version", "source:mail")
    assert "body_text" not in current_source["content"]
    assert current_source["content"]["body_text_fingerprint"].startswith(
        "sha256:"
    )
    assert current_source["content"]["body_text_byte_length"] > 0
    assert current_source["storage_class"] == "external_original"
    assert current_source["original_availability"] == "available"
    assert current_source["scope_id"] == "scope:gmail"
    assert current_source["external_reference"]["locator"] == "message-one"
    assert current_source["pointer_rebase_revision"].startswith(
        "source-in-place-direct-current:"
    )

    current_preview = store.current("visual_asset", "visual:document")
    assert current_preview["current"] is False
    assert current_preview["display_allowed"] is False
    assert current_preview["original_blob_ref"] == ""
    assert store.current("generated_hero_record", "matter:child") is None

    gc = reclaim_orphan_blobs(
        database_path=private / "matters.sqlite3",
        blob_root=private / "blobs",
        limit=100,
    )
    assert gc["remaining_orphan_count"] == 0
    assert gc["deleted_count"] == 4
    staging = clean_staging(private_root=private, backup_root=backup)
    assert staging["deleted_file_count"] == 2

    verified = verify_migration(
        private_root=private,
        backup_root=backup,
    )
    assert verified["status"] == "verified_current"
    assert verified["physical_compaction"] == "separate_not_run"
    assert json.loads(
        (backup / "backup-manifest.json").read_text(encoding="utf-8")
    )["status"] == "verified_restorable_backup"


def test_backup_root_must_not_contain_or_be_contained_by_matters_home(tmp_path):
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    repository.mkdir()
    SQLiteStore(private, repository)

    with pytest.raises(ValueError, match="separate sibling"):
        create_verified_backup(
            private_root=private,
            backup_root=private / "recovery",
        )
    with pytest.raises(ValueError, match="separate sibling"):
        create_verified_backup(
            private_root=private,
            backup_root=tmp_path,
        )


def test_storage_plan_cli_does_not_construct_the_normal_runtime(
    tmp_path,
    monkeypatch,
    capsys,
):
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    repository.mkdir()
    SQLiteStore(private, repository)
    monkeypatch.setenv("MATTERS_HOME", str(private))

    exit_code = main(["storage-migration-plan"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["result"]["database_quick_check"] == "ok"
