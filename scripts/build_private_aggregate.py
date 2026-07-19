"""Project one privacy-safe aggregate from an external Matters runtime."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable


TERMINAL_NONTRACKED_DISPOSITIONS = frozenset(
    {
        "not_tracked",
        "hard_excluded",
        "metadata_only",
        "unsupported",
        "inaccessible",
        "quarantined",
        "cloud_placeholder",
        "changed_during_read",
        "revoked",
        "deleted",
    }
)


def _partition_stats(database: Path) -> dict[str, Any]:
    manifest_root = database.resolve().parent / "runs" / "filesystem-partitions"
    manifest_count = partition_count = terminal_count = 0
    failed_count = open_count = invalid_count = 0
    for path in sorted(manifest_root.glob("*.json")):
        manifest_count += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            nodes = payload["nodes"]
            if (
                payload.get("schema")
                != "matters.private-filesystem-partitions.v1"
                or not isinstance(nodes, dict)
            ):
                raise ValueError("malformed partition manifest")
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            invalid_count += 1
            continue
        for node in nodes.values():
            partition_count += 1
            status = str(node.get("status", ""))
            if status in {"complete", "partitioned"}:
                terminal_count += 1
            elif status == "failed":
                failed_count += 1
            else:
                open_count += 1
        if payload.get("inventory_status") not in {"complete", "blocked"}:
            open_count += 1
    if invalid_count or failed_count:
        status = "blocked"
    elif open_count:
        status = "partial"
    elif manifest_count:
        status = "complete"
    else:
        status = "not_started"
    return {
        "status": status,
        "manifest_count": manifest_count,
        "partition_count": partition_count,
        "terminal_partition_count": terminal_count,
        "open_partition_count": open_count,
        "failed_partition_count": failed_count + invalid_count,
    }


def _current_payloads(
    connection: sqlite3.Connection,
    owner: str,
) -> Iterable[dict[str, Any]]:
    query = """
        SELECT snapshots.payload
          FROM current_objects
          JOIN snapshots
            ON snapshots.owner = current_objects.owner
           AND snapshots.object_id = current_objects.object_id
           AND snapshots.revision = current_objects.revision
         WHERE current_objects.owner = ?
         ORDER BY current_objects.object_id
    """
    for (raw,) in connection.execute(query, (owner,)):
        yield json.loads(raw)


def _localized_map_stats(value: object) -> tuple[int, int, int]:
    complete = 0
    missing = 0
    revision_mismatch = 0

    def visit(item: object) -> None:
        nonlocal complete, missing, revision_mismatch
        if isinstance(item, dict):
            if "localized_values" in item:
                values = item.get("localized_values")
                revisions = item.get("locale_revisions")
                if (
                    isinstance(values, dict)
                    and set(values) >= {"en", "zh-CN"}
                    and all(str(values[tag]).strip() for tag in ("en", "zh-CN"))
                ):
                    complete += 1
                else:
                    missing += 1
                semantic_revision = str(item.get("semantic_revision", ""))
                if (
                    not isinstance(revisions, dict)
                    or revisions.get("en") != semantic_revision
                    or revisions.get("zh-CN") != semantic_revision
                ):
                    revision_mismatch += 1
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return complete, missing, revision_mismatch


def build_aggregate(database: Path, *, evidence_handle: str) -> dict[str, Any]:
    if not evidence_handle.startswith("private-evidence:"):
        raise ValueError("evidence handle must be opaque and private-evidence namespaced")
    connection = sqlite3.connect(
        f"file:{database.resolve()}?mode=ro",
        uri=True,
    )
    try:
        scopes = tuple(_current_payloads(connection, "candidate_scope"))
        snapshots = tuple(_current_payloads(connection, "inventory_snapshot"))
        depth_rows = tuple(_current_payloads(connection, "semantic_depth"))
        source_rows = tuple(_current_payloads(connection, "source_version"))
        projection_rows = tuple(_current_payloads(connection, "projection"))
        provider_counts = Counter(str(item.get("provider", "")) for item in scopes)
        disposition_counts: Counter[str] = Counter()
        occurrence_count = 0
        for snapshot in snapshots:
            occurrences = tuple(snapshot.get("occurrences", ()))
            dispositions = tuple(snapshot.get("dispositions", ()))
            occurrence_count += len(occurrences)
            disposition_counts.update(
                str(item.get("status", "")) for item in dispositions
            )
        depth_counts = Counter(str(item.get("state", "")) for item in depth_rows)
        complete_maps = missing_maps = revision_mismatches = 0
        legacy_projection_rows = 0
        for projection in projection_rows:
            if "english" in projection or "zh_cn" in projection:
                legacy_projection_rows += 1
            complete, missing, mismatch = _localized_map_stats(projection)
            complete_maps += complete
            missing_maps += missing
            revision_mismatches += mismatch
        owner_counts = {
            str(owner): int(count)
            for owner, count in connection.execute(
                """
                SELECT owner, COUNT(*)
                  FROM current_objects
                 GROUP BY owner
                 ORDER BY owner
                """
            )
        }
        active_catalog_count = int(
            connection.execute(
                """
                SELECT COUNT(*)
                  FROM current_objects c
                  JOIN snapshots s
                    ON s.owner = c.owner
                   AND s.object_id = c.object_id
                   AND s.revision = c.revision
                 WHERE c.owner = 'source_catalog'
                   AND COALESCE(
                       json_extract(s.payload, '$.active'),
                       0
                   ) = 1
                """
            ).fetchone()[0]
        )
    finally:
        connection.close()

    disposition_count = sum(disposition_counts.values())
    occurrence_ids = {
        str(item.get("occurrence_id", ""))
        for snapshot in snapshots
        for item in snapshot.get("occurrences", ())
    }
    disposition_by_occurrence = {
        str(item.get("occurrence_id", "")): str(item.get("status", ""))
        for snapshot in snapshots
        for item in snapshot.get("dispositions", ())
    }
    source_occurrence_ids = {
        str(item.get("external_reference", {}).get("external_id", ""))
        for item in source_rows
        if isinstance(item.get("external_reference"), dict)
    }
    depth_by_occurrence = {
        str(item.get("occurrence_id", "")): str(item.get("state", ""))
        for item in depth_rows
    }
    tracked_ids = {
        occurrence_id
        for occurrence_id, status in disposition_by_occurrence.items()
        if status == "tracked"
    }
    tracked_with_source = tracked_ids.intersection(source_occurrence_ids)
    tracked_depth_sufficient = {
        occurrence_id
        for occurrence_id in tracked_ids
        if depth_by_occurrence.get(occurrence_id) == "sufficient"
    }
    human_review_count = (
        disposition_counts.get("review_required", 0)
        + disposition_counts.get("deferred", 0)
    )
    tracked_open_count = len(tracked_ids - tracked_depth_sufficient)
    other_open_count = sum(
        count
        for status, count in disposition_counts.items()
        if status
        not in TERMINAL_NONTRACKED_DISPOSITIONS
        | {"tracked", "review_required", "deferred"}
    )
    nonterminal_count = human_review_count + tracked_open_count + other_open_count
    inventory_reconciled = (
        len(scopes) == len(snapshots)
        and occurrence_count == disposition_count
        and occurrence_count > 0
    )
    catalog_reconciled = active_catalog_count == len(occurrence_ids)
    locale_current = (
        len(projection_rows) == complete_maps
        and missing_maps == 0
        and revision_mismatches == 0
        and legacy_projection_rows == 0
    )
    partition_inventory = _partition_stats(database)
    report_current = (
        inventory_reconciled
        and catalog_reconciled
        and locale_current
        and partition_inventory["status"] != "blocked"
    )
    coverage_complete = (
        report_current
        and partition_inventory["status"] in {"complete", "not_started"}
        and nonterminal_count == 0
        and set(depth_by_occurrence) == occurrence_ids
    )
    return {
        "artifact_type": "matters.private-first-run-aggregate.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": (
            "coverage_complete"
            if coverage_complete
            else ("current_with_open_work" if report_current else "blocked")
        ),
        "ok": report_current,
        "coverage_complete": coverage_complete,
        "private_evidence_handle": evidence_handle,
        "inventory": {
            "scope_count": len(scopes),
            "provider_counts": dict(sorted(provider_counts.items())),
            "snapshot_count": len(snapshots),
            "occurrence_count": occurrence_count,
            "disposition_count": disposition_count,
            "disposition_counts": dict(sorted(disposition_counts.items())),
            "human_review_or_deferred_count": human_review_count,
            "tracked_count": len(tracked_ids),
            "tracked_with_source_version_count": len(tracked_with_source),
            "tracked_depth_sufficient_count": len(tracked_depth_sufficient),
            "tracked_open_count": tracked_open_count,
            "other_open_count": other_open_count,
            "nonterminal_count": nonterminal_count,
            "reconciled": inventory_reconciled,
            "active_catalog_count": active_catalog_count,
            "catalog_reconciled": catalog_reconciled,
        },
        "partition_inventory": partition_inventory,
        "durable_objects": {
            "source_version_count": owner_counts.get("source_version", 0),
            "evidence_anchor_count": owner_counts.get("evidence_anchor", 0),
            "review_result_count": owner_counts.get("review_result", 0),
            "projection_count": owner_counts.get("projection", 0),
        },
        "semantic_depth": {
            "counts": dict(sorted(depth_counts.items())),
            "all_accounted": set(depth_by_occurrence) == occurrence_ids,
        },
        "localization": {
            "required_locales": ["en", "zh-CN"],
            "projection_rows": len(projection_rows),
            "complete_locale_maps": complete_maps,
            "missing_locale_maps": missing_maps,
            "revision_mismatches": revision_mismatches,
            "legacy_pair_rows": legacy_projection_rows,
            "current": locale_current,
        },
        "claim_boundary": (
            "This public aggregate proves only count reconciliation, bounded "
            "partition traversal state, explicit disposition accounting, "
            "semantic-depth accounting, and required locale-map currentness "
            "for one private runtime. Inventory completion is kept distinct "
            "from content and semantic completion. It contains no "
            "paths, source ids, message ids, subjects, addresses, excerpts, "
            "content hashes, screenshots, or private model content. Any "
            "legacy review/deferred residual count remains a visible "
            "nonterminal migration diagnostic, never a normal v1 workflow."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--evidence-handle", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_aggregate(
        args.database,
        evidence_handle=args.evidence_handle,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
