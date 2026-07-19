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
