"""External-root SQLite snapshot store."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Iterator

from matters.infrastructure.capability_status.status import validate_private_root


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteStore:
    def __init__(self, private_root: Path, repository_root: Path):
        status = validate_private_root(private_root, repository_root)
        if status.status != "active":
            raise ValueError(status.reason)
        private_root.mkdir(parents=True, exist_ok=True)
        self.path = private_root / "matters.sqlite3"
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS snapshots "
                "(owner TEXT NOT NULL, object_id TEXT NOT NULL, revision INTEGER NOT NULL, "
                "payload TEXT NOT NULL, payload_hash TEXT NOT NULL DEFAULT '', "
                "created_at TEXT NOT NULL DEFAULT '', "
                "PRIMARY KEY(owner, object_id, revision))"
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(snapshots)").fetchall()
            }
            if "payload_hash" not in columns:
                connection.execute(
                    "ALTER TABLE snapshots ADD COLUMN payload_hash TEXT NOT NULL DEFAULT ''"
                )
            if "created_at" not in columns:
                connection.execute(
                    "ALTER TABLE snapshots ADD COLUMN created_at TEXT NOT NULL DEFAULT ''"
                )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS idempotency "
                "(owner TEXT NOT NULL, idempotency_key TEXT NOT NULL, "
                "payload TEXT NOT NULL, created_at TEXT NOT NULL, "
                "PRIMARY KEY(owner, idempotency_key))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS current_objects "
                "(owner TEXT NOT NULL, object_id TEXT NOT NULL, revision INTEGER NOT NULL, "
                "PRIMARY KEY(owner, object_id), "
                "FOREIGN KEY(owner, object_id, revision) "
                "REFERENCES snapshots(owner, object_id, revision))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS coverage_matter_index "
                "(matter_id TEXT NOT NULL, object_id TEXT NOT NULL, "
                "PRIMARY KEY(matter_id, object_id))"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS "
                "coverage_matter_index_object_idx "
                "ON coverage_matter_index(object_id)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS store_metadata "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            indexed = connection.execute(
                "SELECT value FROM store_metadata "
                "WHERE key='coverage_matter_index:v1'"
            ).fetchone()
            if indexed is None:
                connection.execute(
                    "INSERT OR IGNORE INTO coverage_matter_index"
                    "(matter_id, object_id) "
                    "SELECT CAST(member.value AS TEXT), c.object_id "
                    "FROM current_objects c "
                    "JOIN snapshots s ON s.owner=c.owner "
                    "AND s.object_id=c.object_id AND s.revision=c.revision "
                    "JOIN json_each(s.payload, '$.matter_ids') AS member "
                    "WHERE c.owner='object_coverage' "
                    "AND CAST(member.value AS TEXT)!=''"
                )
                connection.execute(
                    "INSERT INTO store_metadata(key, value) "
                    "VALUES ('coverage_matter_index:v1', 'complete')"
                )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def next_revision(self, owner: str, object_id: str) -> int:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(revision), 0) FROM snapshots "
                "WHERE owner=? AND object_id=?",
                (owner, object_id),
            ).fetchone()
        return int(row[0]) + 1

    def append(
        self,
        owner: str,
        object_id: str,
        revision: int,
        payload: Any,
    ) -> None:
        if not owner or not object_id or revision < 1:
            raise ValueError("owner, object_id, and positive revision are required")
        encoded = _canonical_json(payload)
        payload_hash = "sha256:" + sha256(encoded.encode("utf-8")).hexdigest()
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO snapshots"
                "(owner, object_id, revision, payload, payload_hash, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (owner, object_id, revision, encoded, payload_hash, _utc_now()),
            )
            connection.execute(
                "INSERT INTO current_objects(owner, object_id, revision) VALUES (?, ?, ?) "
                "ON CONFLICT(owner, object_id) DO UPDATE SET revision=excluded.revision "
                "WHERE excluded.revision > current_objects.revision",
                (owner, object_id, revision),
            )
            if owner == "object_coverage":
                self._refresh_coverage_matter_index(
                    connection,
                    object_id=object_id,
                    revision=revision,
                    encoded_payload=encoded,
                )

    def next_revisions(
        self,
        owner: str,
        object_ids: Iterable[str],
    ) -> dict[str, int]:
        """Resolve many append revisions with one read transaction."""

        ids = tuple(dict.fromkeys(str(item) for item in object_ids))
        if not owner or any(not item for item in ids):
            raise ValueError("owner and object ids are required")
        if not ids:
            return {}
        with self.connection() as connection:
            current: dict[str, int] = {}
            for start in range(0, len(ids), 800):
                batch = ids[start : start + 800]
                placeholders = ",".join("?" for _ in batch)
                current.update(
                    {
                        str(object_id): int(revision)
                        for object_id, revision in connection.execute(
                            "SELECT object_id, revision FROM current_objects "
                            f"WHERE owner=? AND object_id IN ({placeholders})",
                            (owner, *batch),
                        )
                    }
                )
        return {object_id: current.get(object_id, 0) + 1 for object_id in ids}

    def append_many(
        self,
        rows: Iterable[tuple[str, str, int, Any]],
    ) -> None:
        """Append many independent owner rows in one atomic transaction."""

        prepared = []
        seen: set[tuple[str, str, int]] = set()
        created_at = _utc_now()
        for owner, object_id, revision, payload in rows:
            if not owner or not object_id or revision < 1:
                raise ValueError(
                    "owner, object_id, and positive revision are required"
                )
            identity = (owner, object_id, revision)
            if identity in seen:
                raise ValueError("duplicate append_many identity")
            seen.add(identity)
            encoded = _canonical_json(payload)
            payload_hash = (
                "sha256:" + sha256(encoded.encode("utf-8")).hexdigest()
            )
            prepared.append(
                (
                    owner,
                    object_id,
                    revision,
                    encoded,
                    payload_hash,
                    created_at,
                )
            )
        if not prepared:
            return
        with self.connection() as connection:
            connection.executemany(
                "INSERT INTO snapshots"
                "(owner, object_id, revision, payload, payload_hash, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                prepared,
            )
            connection.executemany(
                "INSERT INTO current_objects(owner, object_id, revision) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(owner, object_id) DO UPDATE SET "
                "revision=excluded.revision "
                "WHERE excluded.revision > current_objects.revision",
                (
                    (owner, object_id, revision)
                    for owner, object_id, revision, _payload, _hash, _at in prepared
                ),
            )
            for owner, object_id, revision, encoded, _hash, _at in prepared:
                if owner == "object_coverage":
                    self._refresh_coverage_matter_index(
                        connection,
                        object_id=object_id,
                        revision=revision,
                        encoded_payload=encoded,
                    )

    @staticmethod
    def _refresh_coverage_matter_index(
        connection: sqlite3.Connection,
        *,
        object_id: str,
        revision: int,
        encoded_payload: str,
    ) -> None:
        current = connection.execute(
            "SELECT revision FROM current_objects "
            "WHERE owner='object_coverage' AND object_id=?",
            (object_id,),
        ).fetchone()
        if current is None or int(current[0]) != revision:
            return
        connection.execute(
            "DELETE FROM coverage_matter_index WHERE object_id=?",
            (object_id,),
        )
        matter_ids = tuple(
            dict.fromkeys(
                str(item)
                for item in json.loads(encoded_payload).get("matter_ids", ())
                if str(item)
            )
        )
        connection.executemany(
            "INSERT INTO coverage_matter_index(matter_id, object_id) "
            "VALUES (?, ?)",
            ((matter_id, object_id) for matter_id in matter_ids),
        )

    def history(self, owner: str, object_id: str) -> tuple[dict, ...]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT payload FROM snapshots WHERE owner=? AND object_id=? ORDER BY revision",
                (owner, object_id),
            ).fetchall()
        return tuple(json.loads(row[0]) for row in rows)

    def current(self, owner: str, object_id: str) -> dict | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT s.payload FROM snapshots s "
                "JOIN current_objects c ON c.owner=s.owner "
                "AND c.object_id=s.object_id AND c.revision=s.revision "
                "WHERE s.owner=? AND s.object_id=?",
                (owner, object_id),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list_current(self, owner: str) -> tuple[dict, ...]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT s.payload FROM snapshots s "
                "JOIN current_objects c ON c.owner=s.owner "
                "AND c.object_id=s.object_id AND c.revision=s.revision "
                "WHERE s.owner=? ORDER BY s.object_id",
                (owner,),
            ).fetchall()
        return tuple(json.loads(row[0]) for row in rows)

    def iter_current(self, owner: str) -> Iterator[dict]:
        """Stream current payloads without materializing a whole owner."""

        with self.connection() as connection:
            cursor = connection.execute(
                "SELECT s.payload FROM snapshots s "
                "JOIN current_objects c ON c.owner=s.owner "
                "AND c.object_id=s.object_id AND c.revision=s.revision "
                "WHERE s.owner=? ORDER BY s.object_id",
                (owner,),
            )
            for (payload,) in cursor:
                yield json.loads(payload)

    def current_many(
        self,
        owner: str,
        object_ids: Iterable[str],
    ) -> dict[str, dict]:
        """Load current payloads for a bounded set of exact object ids."""

        ids = tuple(dict.fromkeys(str(item) for item in object_ids if str(item)))
        rows: dict[str, dict] = {}
        if not ids:
            return rows
        with self.connection() as connection:
            for start in range(0, len(ids), 800):
                batch = ids[start : start + 800]
                placeholders = ",".join("?" for _ in batch)
                query = (
                    "SELECT c.object_id, s.payload FROM current_objects c "
                    "JOIN snapshots s ON s.owner=c.owner "
                    "AND s.object_id=c.object_id AND s.revision=c.revision "
                    f"WHERE c.owner=? AND c.object_id IN ({placeholders})"
                )
                for object_id, payload in connection.execute(
                    query,
                    (owner, *batch),
                ):
                    rows[str(object_id)] = json.loads(payload)
        return rows

    def current_by_json_array_members(
        self,
        owner: str,
        *,
        json_field: str,
        values: Iterable[str],
    ) -> dict[str, tuple[dict, ...]]:
        """Group current payloads by matching members of one JSON array field."""

        members = tuple(
            dict.fromkeys(str(item) for item in values if str(item))
        )
        if (
            not owner
            or not json_field
            or not json_field.replace("_", "").isalnum()
        ):
            raise ValueError("owner and a simple JSON array field are required")
        grouped: dict[str, list[dict]] = {item: [] for item in members}
        if not members:
            return {key: tuple(value) for key, value in grouped.items()}
        if owner == "object_coverage" and json_field == "matter_ids":
            with self.connection() as connection:
                for start in range(0, len(members), 800):
                    batch = members[start : start + 800]
                    placeholders = ",".join("?" for _ in batch)
                    rows = connection.execute(
                        "SELECT idx.matter_id, s.payload "
                        "FROM coverage_matter_index idx "
                        "JOIN current_objects c "
                        "ON c.owner='object_coverage' "
                        "AND c.object_id=idx.object_id "
                        "JOIN snapshots s ON s.owner=c.owner "
                        "AND s.object_id=c.object_id "
                        "AND s.revision=c.revision "
                        f"WHERE idx.matter_id IN ({placeholders}) "
                        "ORDER BY idx.object_id",
                        batch,
                    )
                    for member, payload in rows:
                        grouped[str(member)].append(json.loads(payload))
            return {
                key: tuple(value)
                for key, value in grouped.items()
            }
        json_path = f"$.{json_field}"
        with self.connection() as connection:
            for start in range(0, len(members), 800):
                batch = members[start : start + 800]
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    "SELECT CAST(member.value AS TEXT), s.payload "
                    "FROM current_objects c "
                    "JOIN snapshots s ON s.owner=c.owner "
                    "AND s.object_id=c.object_id AND s.revision=c.revision "
                    "JOIN json_each(s.payload, ?) AS member "
                    f"WHERE c.owner=? AND member.value IN ({placeholders}) "
                    "ORDER BY c.object_id",
                    (json_path, owner, *batch),
                )
                for member, payload in rows:
                    grouped[str(member)].append(json.loads(payload))
        return {
            key: tuple(value)
            for key, value in grouped.items()
        }

    def count_current(self, owner: str) -> int:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM current_objects WHERE owner=?",
                (owner,),
            ).fetchone()
        return int(row[0])

    def current_page(
        self,
        owner: str,
        *,
        offset: int,
        limit: int,
    ) -> tuple[tuple[dict, ...], int]:
        if offset < 0 or limit < 1 or limit > 200:
            raise ValueError("current page bounds are invalid")
        with self.connection() as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM current_objects WHERE owner=?",
                    (owner,),
                ).fetchone()[0]
            )
            rows = connection.execute(
                "SELECT s.payload FROM current_objects c "
                "JOIN snapshots s ON s.owner=c.owner "
                "AND s.object_id=c.object_id AND s.revision=c.revision "
                "WHERE c.owner=? ORDER BY c.object_id LIMIT ? OFFSET ?",
                (owner, limit, offset),
            ).fetchall()
        return tuple(json.loads(row[0]) for row in rows), total

    def current_filtered_page(
        self,
        owner: str,
        *,
        json_field: str,
        values: Iterable[str],
        offset: int,
        limit: int,
    ) -> tuple[tuple[dict, ...], int]:
        """Read one bounded page whose current payload field matches a value."""

        allowed = tuple(dict.fromkeys(str(item) for item in values))
        if (
            not json_field
            or not allowed
            or offset < 0
            or limit < 1
            or limit > 200
        ):
            raise ValueError("filtered current page bounds are invalid")
        json_path = f"$.{json_field}"
        placeholders = ",".join("?" for _ in allowed)
        base = (
            " FROM current_objects c "
            "JOIN snapshots s ON s.owner=c.owner "
            "AND s.object_id=c.object_id AND s.revision=c.revision "
            "WHERE c.owner=? "
            f"AND json_extract(s.payload, ?) IN ({placeholders})"
        )
        parameters = (owner, json_path, *allowed)
        with self.connection() as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*)" + base,
                    parameters,
                ).fetchone()[0]
            )
            rows = connection.execute(
                "SELECT s.payload"
                + base
                + " ORDER BY c.object_id LIMIT ? OFFSET ?",
                (*parameters, limit, offset),
            ).fetchall()
        return tuple(json.loads(row[0]) for row in rows), total

    def pending_analysis_page(
        self,
        *,
        offset: int,
        limit: int,
    ) -> tuple[tuple[dict, ...], int]:
        """Read bounded work packages that do not have a passed current result."""

        if offset < 0 or limit < 1 or limit > 200:
            raise ValueError("analysis page bounds are invalid")
        base = (
            " FROM current_objects pc "
            "JOIN snapshots ps ON ps.owner=pc.owner "
            "AND ps.object_id=pc.object_id AND ps.revision=pc.revision "
            "LEFT JOIN current_objects rc ON rc.owner='agent_operation_result' "
            "AND rc.object_id=pc.object_id "
            "LEFT JOIN snapshots rs ON rs.owner=rc.owner "
            "AND rs.object_id=rc.object_id AND rs.revision=rc.revision "
            "WHERE pc.owner='analysis_work_package' "
            "AND COALESCE(json_extract(rs.payload, '$.status'), '')!='passed'"
        )
        with self.connection() as connection:
            total = int(
                connection.execute("SELECT COUNT(*)" + base).fetchone()[0]
            )
            rows = connection.execute(
                "SELECT ps.payload"
                + base
                + " ORDER BY pc.object_id LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return tuple(json.loads(row[0]) for row in rows), total

    def source_catalog_page(
        self,
        *,
        offset: int,
        limit: int,
        review_only: bool = False,
    ) -> tuple[tuple[dict, ...], int]:
        """Read one bounded private catalog page with current depth/freshness."""

        if offset < 0 or limit < 1 or limit > 200:
            raise ValueError("catalog page bounds are invalid")
        base = (
            " FROM current_objects cc "
            "JOIN snapshots cs ON cs.owner=cc.owner "
            "AND cs.object_id=cc.object_id AND cs.revision=cc.revision "
            "LEFT JOIN current_objects dc ON dc.owner='semantic_depth' "
            "AND dc.object_id=cc.object_id "
            "LEFT JOIN snapshots ds ON ds.owner=dc.owner "
            "AND ds.object_id=dc.object_id AND ds.revision=dc.revision "
            "LEFT JOIN current_objects fc ON fc.owner='dependency_freshness' "
            "AND fc.object_id=cc.object_id "
            "LEFT JOIN snapshots fs ON fs.owner=fc.owner "
            "AND fs.object_id=fc.object_id AND fs.revision=fc.revision "
            "WHERE cc.owner='source_catalog' "
            "AND COALESCE(json_extract(cs.payload, '$.active'), 0)=1 "
        )
        if review_only:
            base += (
                "AND ("
                "json_extract(cs.payload, '$.disposition') "
                "IN ('review_required','deferred') "
                "OR COALESCE(json_extract(ds.payload, '$.state'), "
                "'not_assessed') "
                "IN ('not_assessed','partial','blocked','stale') "
                "OR json_extract(fs.payload, '$.status')='stale'"
                ") "
            )
        with self.connection() as connection:
            total_row = connection.execute("SELECT COUNT(*)" + base).fetchone()
            result_rows = connection.execute(
                "SELECT cs.payload, ds.payload, fs.payload"
                + base
                + "ORDER BY cc.object_id LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        rows = tuple(
            {
                "catalog": json.loads(catalog),
                "depth": json.loads(depth) if depth else None,
                "freshness": json.loads(freshness) if freshness else None,
            }
            for catalog, depth, freshness in result_rows
        )
        return rows, int(total_row[0])

    def source_catalog_status_counts(self) -> dict[str, Any]:
        """Aggregate catalog disposition, freshness, depth, and review counts."""

        query = (
            "SELECT "
            "json_extract(cs.payload, '$.disposition'), "
            "COALESCE(json_extract(fs.payload, '$.status'), 'current'), "
            "COALESCE(json_extract(ds.payload, '$.state'), 'not_assessed'), "
            "COUNT(*) "
            "FROM current_objects cc "
            "JOIN snapshots cs ON cs.owner=cc.owner "
            "AND cs.object_id=cc.object_id AND cs.revision=cc.revision "
            "LEFT JOIN current_objects dc ON dc.owner='semantic_depth' "
            "AND dc.object_id=cc.object_id "
            "LEFT JOIN snapshots ds ON ds.owner=dc.owner "
            "AND ds.object_id=dc.object_id AND ds.revision=dc.revision "
            "LEFT JOIN current_objects fc ON fc.owner='dependency_freshness' "
            "AND fc.object_id=cc.object_id "
            "LEFT JOIN snapshots fs ON fs.owner=fc.owner "
            "AND fs.object_id=fc.object_id AND fs.revision=fc.revision "
            "WHERE cc.owner='source_catalog' "
            "AND COALESCE(json_extract(cs.payload, '$.active'), 0)=1 "
            "GROUP BY 1, 2, 3"
        )
        disposition: dict[str, int] = {}
        freshness: dict[str, int] = {}
        depth: dict[str, int] = {}
        total = review = 0
        with self.connection() as connection:
            rows = connection.execute(query).fetchall()
        for disposition_value, freshness_value, depth_value, count_value in rows:
            count = int(count_value)
            disposition_key = str(disposition_value or "")
            freshness_key = str(freshness_value or "current")
            depth_key = str(depth_value or "not_assessed")
            total += count
            disposition[disposition_key] = (
                disposition.get(disposition_key, 0) + count
            )
            freshness[freshness_key] = freshness.get(freshness_key, 0) + count
            depth[depth_key] = depth.get(depth_key, 0) + count
            if (
                disposition_key in {"review_required", "deferred"}
                or depth_key in {"not_assessed", "partial", "blocked", "stale"}
                or freshness_key == "stale"
            ):
                review += count
        return {
            "total_count": total,
            "review_count": review,
            "disposition_counts": disposition,
            "freshness_counts": freshness,
            "depth_counts": depth,
        }

    def latest(self, owner: str) -> dict | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload FROM snapshots WHERE owner=? "
                "ORDER BY created_at DESC, rowid DESC LIMIT 1",
                (owner,),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def put_idempotency(self, owner: str, key: str, payload: Any) -> None:
        if not owner or not key:
            raise ValueError("idempotency owner and key are required")
        encoded = _canonical_json(payload)
        with self.connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO idempotency"
                "(owner, idempotency_key, payload, created_at) VALUES (?, ?, ?, ?)",
                (owner, key, encoded, _utc_now()),
            )

    def get_idempotency(self, owner: str, key: str) -> dict | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload FROM idempotency WHERE owner=? AND idempotency_key=?",
                (owner, key),
            ).fetchone()
        return json.loads(row[0]) if row else None


__all__ = ["SQLiteStore"]
