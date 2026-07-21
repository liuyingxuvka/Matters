import json
import sqlite3

from scripts.build_private_aggregate import build_aggregate


def _seed(database):
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE current_objects (
            owner TEXT NOT NULL,
            object_id TEXT NOT NULL,
            revision INTEGER NOT NULL
        );
        CREATE TABLE snapshots (
            owner TEXT NOT NULL,
            object_id TEXT NOT NULL,
            revision INTEGER NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE TABLE inventory_occurrence_current (
            scope_id TEXT NOT NULL,
            object_id TEXT NOT NULL,
            inventory_revision INTEGER NOT NULL,
            provider TEXT NOT NULL,
            object_type TEXT NOT NULL,
            disposition TEXT NOT NULL,
            occurrence_payload TEXT NOT NULL,
            PRIMARY KEY(scope_id, object_id)
        );
        """
    )

    def append(owner, object_id, payload):
        connection.execute(
            "INSERT INTO current_objects VALUES (?, ?, 1)",
            (owner, object_id),
        )
        connection.execute(
            "INSERT INTO snapshots VALUES (?, ?, 1, ?)",
            (owner, object_id, json.dumps(payload)),
        )

    append(
        "candidate_scope",
        "scope:private",
        {"provider": "filesystem", "root_locator": "must-not-escape"},
    )
    append(
        "inventory_snapshot",
        "snapshot:private",
        {
            "occurrences": [{"occurrence_id": "private:item"}],
            "dispositions": [
                {
                    "occurrence_id": "private:item",
                    "status": "review_required",
                }
            ],
        },
    )
    connection.execute(
        "INSERT INTO inventory_occurrence_current VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "scope:private",
            "private:item",
            1,
            "filesystem",
            "document",
            "review_required",
            json.dumps(
                {
                    "occurrence_id": "private:item",
                    "provider": "filesystem",
                    "object_type": "document",
                }
            ),
        ),
    )
    append(
        "semantic_depth",
        "depth:private",
        {"state": "partial"},
    )
    append(
        "source_catalog",
        "private:item",
        {"active": True},
    )
    append(
        "projection",
        "projection:private",
        {
            "semantic_revision": "revision:1",
            "localized_values": {"en": "Current", "zh-CN": "当前"},
            "locale_revisions": {
                "en": "revision:1",
                "zh-CN": "revision:1",
            },
        },
    )
    for owner in ("source_version", "evidence_anchor", "review_result"):
        append(owner, f"{owner}:private", {"private": "must-not-escape"})
    connection.commit()
    connection.close()


def _maintenance_evidence(path):
    payload = {
        "artifact_type": "matters.ai-owned-daily-maintenance-evidence.v2",
        "status": "current",
        "schedule_identity": "codex-automation:daily-maintenance-test",
        "execution_profile_identity": "execution-profile:private-test",
        "ai_setup_receipt_id": "ai-setup:private-test",
        "ai_setup_fingerprint": "sha256:" + "1" * 64,
        "install_currentness_receipt_id": (
            "maintenance-install:private-test"
        ),
        "install_currentness_fingerprint": "sha256:" + "2" * 64,
        "shared_service_entrypoint_fingerprint": "sha256:" + "3" * 64,
        "run_receipt_ids": ["maintenance-run:private-test"],
        "last_delta_status": "no_delta",
        "schedule_count": 1,
        "source_scope_origin": "user_supplied_during_install",
        "automation_status": "current",
        "model_agnostic": True,
        "shared_service_path": True,
        "app_api_key_required": False,
        "mutation_attempt_counts": {
            key: 0
            for key in (
                "source",
                "mailbox",
                "outbound",
                "grant",
                "code",
                "model",
                "install",
                "git",
                "tag",
                "release",
            )
        },
        "unattended_final_verification": False,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_private_aggregate_reconciles_without_leaking_payloads(tmp_path):
    database = tmp_path / "private.sqlite3"
    _seed(database)

    report = build_aggregate(
        database,
        evidence_handle="private-evidence:synthetic-1",
    )

    assert report["ok"] is True
    assert report["coverage_complete"] is False
    assert report["status"] == "current_with_open_work"
    assert report["inventory"]["human_review_or_deferred_count"] == 1
    assert report["inventory"]["nonterminal_count"] == 1
    assert report["inventory"]["distinct_occurrence_count"] == 1
    assert report["inventory"]["cross_scope_duplicate_count"] == 0
    assert report["inventory"]["catalog_reconciled"] is True
    serialized = json.dumps(report)
    assert "must-not-escape" not in serialized
    assert "private:item" not in serialized


def test_private_aggregate_includes_only_partition_counts(tmp_path):
    database = tmp_path / "private.sqlite3"
    _seed(database)
    manifest_root = tmp_path / "runs" / "filesystem-partitions"
    manifest_root.mkdir(parents=True)
    (manifest_root / "opaque.json").write_text(
        json.dumps(
            {
                "schema": "matters.private-filesystem-partitions.v1",
                "inventory_status": "partial",
                "authorized_root": "must-not-escape",
                "nodes": {
                    "private-node": {"status": "complete"},
                    "private-node-2": {"status": "pending"},
                },
            }
        ),
        encoding="utf-8",
    )

    report = build_aggregate(
        database,
        evidence_handle="private-evidence:synthetic-2",
    )
    serialized = json.dumps(report)

    assert report["ok"] is True
    assert report["partition_inventory"]["status"] == "partial"
    assert report["partition_inventory"]["partition_count"] == 2
    assert "must-not-escape" not in serialized
    assert "private-node" not in serialized


def test_private_aggregate_uses_current_distinct_occurrence_authority(tmp_path):
    database = tmp_path / "private.sqlite3"
    _seed(database)
    connection = sqlite3.connect(database)
    connection.execute(
        "INSERT INTO inventory_occurrence_current VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "scope:overlap",
            "private:item",
            1,
            "filesystem",
            "document",
            "review_required",
            json.dumps(
                {
                    "occurrence_id": "private:item",
                    "provider": "filesystem",
                    "object_type": "document",
                }
            ),
        ),
    )
    connection.execute(
        "INSERT INTO current_objects VALUES (?, ?, 1)",
        ("source_catalog", "matter:private"),
    )
    connection.execute(
        "INSERT INTO snapshots VALUES (?, ?, 1, ?)",
        (
            "source_catalog",
            "matter:private",
            json.dumps({"active": True, "object_type": "matter"}),
        ),
    )
    connection.commit()
    connection.close()

    report = build_aggregate(
        database,
        evidence_handle="private-evidence:synthetic-overlap",
    )

    assert report["ok"] is True
    assert report["inventory"]["occurrence_count"] == 2
    assert report["inventory"]["distinct_occurrence_count"] == 1
    assert report["inventory"]["cross_scope_duplicate_count"] == 1
    assert report["inventory"]["active_catalog_occurrence_count"] == 1
    assert report["inventory"]["active_catalog_nonoccurrence_count"] == 1


def test_private_aggregate_projects_current_daily_maintenance_receipts(tmp_path):
    database = tmp_path / "private.sqlite3"
    _seed(database)
    maintenance = _maintenance_evidence(tmp_path / "maintenance.json")

    report = build_aggregate(
        database,
        evidence_handle="private-evidence:synthetic-3",
        maintenance_evidence=maintenance,
    )

    projected = report["codex_daily_maintenance"]
    assert report["artifact_type"] == "matters.private-first-run-aggregate.v2"
    assert projected["current"] is True
    assert projected["ai_setup_current"] is True
    assert projected["schedule_count"] == 1
    assert projected["source_scope_origin"] == "user_supplied_during_install"
    assert projected["installed"] is True
    assert set(projected["mutation_attempt_counts"]) == {
        "source",
        "mailbox",
        "outbound",
        "grant",
        "code",
        "model",
        "install",
        "git",
        "tag",
        "release",
    }
    assert set(projected["mutation_attempt_counts"].values()) == {0}
