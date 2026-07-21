"""External-root SQLite snapshot store."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from threading import local
from typing import Any, Callable, Iterable, Iterator
from uuid import uuid4
import zlib

from matters.infrastructure.capability_status.status import validate_private_root
from matters.timeline.start_boundary import parse_user_world_time


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _source_group_projection_identity(row: dict[str, Any]) -> str:
    """Canonical exact public projection identity for one membership row."""

    return _canonical_json(
        [
            str(row["group_id"]),
            str(row.get("parent_group_id", "")),
            str(row.get("child_group_id", "")),
            str(row["title"]),
            int(row["depth"]),
            str(row["occurrence_id"]),
            str(row["provider"]),
            str(row["object_type"]),
            str(row["member_title"]),
            str(row["availability"]),
            int(bool(row["direct_member"])),
        ]
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalized_utc(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("claim time must be timezone-aware")
    return current.astimezone(timezone.utc)


def _normalized_facet_value(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


_START_SOURCE_TIME_FIELDS = frozenset(
    {
        "authored_at",
        "created_at",
        "ctime",
        "date",
        "first_recorded_at",
        "internal_date",
        "message_date",
        "modified_at",
        "modified_ns",
        "mtime",
        "observed_at",
        "received_at",
        "sent_at",
        "source_created_at",
        "source_modified_at",
        "source_observed_at",
    }
)


def _start_time_field(value: object) -> int:
    leaf = str(value or "").strip().casefold().replace("-", "_").rsplit(".", 1)[-1]
    return int(leaf in _START_SOURCE_TIME_FIELDS)


def _normalized_temporal_iso(value: object, field: object) -> str:
    parsed = parse_user_world_time(value, field=str(field or ""))
    return parsed.isoformat() if parsed is not None else ""


def _source_ref_id(value: object) -> str:
    source_id, separator, version_text = str(value or "").rpartition(":v")
    if (
        not separator
        or not source_id.startswith("source:")
        or not version_text.isdigit()
    ):
        return ""
    return source_id


def _source_ref_version(value: object) -> int:
    source_id, separator, version_text = str(value or "").rpartition(":v")
    if (
        not separator
        or not source_id.startswith("source:")
        or not version_text.isdigit()
    ):
        return -1
    return int(version_text)


FILESYSTEM_CLAIM_STAGES = (
    "source_version",
    "extraction",
    "evidence",
    "package",
    "coverage",
    "complete",
)

COMPRESSED_HISTORY_OWNER = "object_coverage"
COMPRESSED_HISTORY_CODEC = "zlib-json-utf8-v1"
SOURCE_GROUP_PROJECTION_VERSION = 2

_MATERIALIZED_INDEX_OWNERS = {
    "matter_context_signal_index:v1": "matter_context",
    "coverage_matter_index:v1": "object_coverage",
    "inventory_occurrence_current:v1": "inventory_snapshot",
    "matter_hierarchy_index:v1": "matter_containment_edge",
    "matter_hierarchy_stage_index:v1": "matter_hierarchy_audit",
    "matter_work_item_index:v1": "matter_work_item",
}

_COVERAGE_SURFACE_OWNERS = {
    "inventory_freshness": "C1_authorization_coverage",
    "source_group_projection": "C2_source_registry",
    "raw_cleanup": "M0_matters_end_to_end_authority",
    "staging_cleanup": "M0_matters_end_to_end_authority",
    "situation_graph": "C6_matter_admission",
    "node_quick_view": "C12_projection_bilingual_ui",
    "world_model": "C11_guard_prediction",
}
_GLOBAL_COVERAGE_SURFACES = (
    "inventory_freshness",
    "source_group_projection",
    "raw_cleanup",
    "staging_cleanup",
)
_ROOT_MATTER_COVERAGE_SURFACES = (
    "situation_graph",
    "node_quick_view",
    "world_model",
)
_CURRENT_COVERAGE_SURFACE_STATUSES = frozenset(
    {"current", "not_applicable", "no_finding"}
)


class SQLiteStore:
    def __init__(self, private_root: Path, repository_root: Path):
        status = validate_private_root(private_root, repository_root)
        if status.status != "active":
            raise ValueError(status.reason)
        private_root.mkdir(parents=True, exist_ok=True)
        self.path = private_root / "matters.sqlite3"
        self._connection_state = local()
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
            connection.execute(
                "CREATE TABLE IF NOT EXISTS snapshot_archive "
                "(owner TEXT NOT NULL, object_id TEXT NOT NULL, revision INTEGER NOT NULL, "
                "codec TEXT NOT NULL, payload BLOB NOT NULL, "
                "payload_hash TEXT NOT NULL, created_at TEXT NOT NULL, "
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
                "CREATE TABLE IF NOT EXISTS coverage_stage_index "
                "(object_id TEXT PRIMARY KEY, provider TEXT NOT NULL, "
                "object_type TEXT NOT NULL, disposition TEXT NOT NULL, "
                "next_stage TEXT NOT NULL, terminal INTEGER NOT NULL, "
                "ui_ready INTEGER NOT NULL, blocked INTEGER NOT NULL, "
                "active INTEGER NOT NULL DEFAULT 1, "
                "first_gap_stage TEXT NOT NULL DEFAULT '', "
                "first_gap_status TEXT NOT NULL DEFAULT '', "
                "first_gap_owner_id TEXT NOT NULL DEFAULT '', "
                "first_gap_failure_class TEXT NOT NULL DEFAULT '', "
                "first_gap_input_fingerprint TEXT NOT NULL DEFAULT '', "
                "first_gap_updated_at TEXT NOT NULL DEFAULT '', "
                "first_gap_indexed_revision INTEGER NOT NULL DEFAULT 0, "
                "revision INTEGER NOT NULL, updated_at TEXT NOT NULL)"
            )
            coverage_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(coverage_stage_index)"
                ).fetchall()
            }
            if "active" not in coverage_columns:
                connection.execute(
                    "ALTER TABLE coverage_stage_index "
                    "ADD COLUMN active INTEGER NOT NULL DEFAULT 1"
                )
            coverage_audit_columns = {
                "first_gap_stage": "TEXT NOT NULL DEFAULT ''",
                "first_gap_status": "TEXT NOT NULL DEFAULT ''",
                "first_gap_owner_id": "TEXT NOT NULL DEFAULT ''",
                "first_gap_failure_class": "TEXT NOT NULL DEFAULT ''",
                "first_gap_input_fingerprint": "TEXT NOT NULL DEFAULT ''",
                "first_gap_updated_at": "TEXT NOT NULL DEFAULT ''",
                "first_gap_indexed_revision": "INTEGER NOT NULL DEFAULT 0",
            }
            for column_name, declaration in coverage_audit_columns.items():
                if column_name not in coverage_columns:
                    connection.execute(
                        "ALTER TABLE coverage_stage_index "
                        f"ADD COLUMN {column_name} {declaration}"
                    )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS coverage_stage_next_idx "
                "ON coverage_stage_index(next_stage, object_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS coverage_stage_state_idx "
                "ON coverage_stage_index(terminal, ui_ready, blocked)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS coverage_stage_active_next_idx "
                "ON coverage_stage_index(active, next_stage, object_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS coverage_stage_active_state_idx "
                "ON coverage_stage_index(active, terminal, ui_ready, blocked)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS coverage_stage_first_gap_idx "
                "ON coverage_stage_index"
                "(active, first_gap_stage, first_gap_status, object_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS coverage_stage_audit_revision_idx "
                "ON coverage_stage_index"
                "(active, first_gap_indexed_revision, revision, object_id)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS coverage_stage_status_index "
                "(object_id TEXT NOT NULL, stage_id TEXT NOT NULL, "
                "status TEXT NOT NULL, owner_id TEXT NOT NULL, "
                "failure_class TEXT NOT NULL, "
                "input_fingerprint TEXT NOT NULL, "
                "stage_updated_at TEXT NOT NULL, "
                "coverage_revision INTEGER NOT NULL, "
                "PRIMARY KEY(object_id, stage_id))"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS coverage_stage_status_count_idx "
                "ON coverage_stage_status_index"
                "(stage_id, status, object_id, coverage_revision)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS coverage_stage_status_object_idx "
                "ON coverage_stage_status_index"
                "(object_id, coverage_revision, stage_id)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS coverage_audit_index_state "
                "(singleton_id INTEGER PRIMARY KEY CHECK(singleton_id=1), "
                "generation INTEGER NOT NULL, "
                "last_object_id TEXT NOT NULL, updated_at TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT OR IGNORE INTO coverage_audit_index_state"
                "(singleton_id, generation, last_object_id, updated_at) "
                "VALUES (1, 0, '', '')"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS coverage_surface_index "
                "(surface_id TEXT NOT NULL, subject_id TEXT NOT NULL, "
                "subject_kind TEXT NOT NULL, status TEXT NOT NULL, "
                "owner_id TEXT NOT NULL, failure_class TEXT NOT NULL, "
                "input_fingerprint TEXT NOT NULL, updated_at TEXT NOT NULL, "
                "PRIMARY KEY(surface_id, subject_id))"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS coverage_surface_status_idx "
                "ON coverage_surface_index"
                "(surface_id, status, owner_id, failure_class, subject_id)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS inventory_occurrence_current "
                "(scope_id TEXT NOT NULL, object_id TEXT NOT NULL, "
                "inventory_revision INTEGER NOT NULL, provider TEXT NOT NULL, "
                "object_type TEXT NOT NULL, disposition TEXT NOT NULL, "
                "occurrence_payload TEXT NOT NULL, "
                "PRIMARY KEY(scope_id, object_id))"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS inventory_occurrence_object_idx "
                "ON inventory_occurrence_current(object_id, scope_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS inventory_occurrence_work_idx "
                "ON inventory_occurrence_current"
                "(provider, disposition, object_id, scope_id)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS source_group_member_index "
                "(scope_id TEXT NOT NULL, inventory_revision INTEGER NOT NULL, "
                "object_id TEXT NOT NULL, occurrence_id TEXT NOT NULL, "
                "group_id TEXT NOT NULL, "
                "parent_group_id TEXT NOT NULL, child_group_id TEXT NOT NULL, "
                "title TEXT NOT NULL, depth INTEGER NOT NULL, "
                "provider TEXT NOT NULL, object_type TEXT NOT NULL, "
                "member_title TEXT NOT NULL, availability TEXT NOT NULL, "
                "direct_member INTEGER NOT NULL, "
                "PRIMARY KEY(scope_id, object_id, group_id))"
            )
            source_group_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(source_group_member_index)"
                ).fetchall()
            }
            if "occurrence_id" not in source_group_columns:
                connection.execute(
                    "ALTER TABLE source_group_member_index "
                    "ADD COLUMN occurrence_id TEXT NOT NULL DEFAULT ''"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS source_group_lookup_idx "
                "ON source_group_member_index(group_id, object_id, scope_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS source_group_member_lookup_idx "
                "ON source_group_member_index(object_id, scope_id, group_id)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS source_group_projection_state "
                "(scope_id TEXT NOT NULL, object_id TEXT NOT NULL, "
                "inventory_revision INTEGER NOT NULL, "
                "projection_version INTEGER NOT NULL, "
                "expected_group_ids TEXT NOT NULL, "
                "expected_projection_rows TEXT NOT NULL, "
                "PRIMARY KEY(scope_id, object_id))"
            )
            source_group_state_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(source_group_projection_state)"
                ).fetchall()
            }
            if "expected_projection_rows" not in source_group_state_columns:
                connection.execute(
                    "ALTER TABLE source_group_projection_state "
                    "ADD COLUMN expected_projection_rows "
                    "TEXT NOT NULL DEFAULT '[]'"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS source_group_projection_revision_idx "
                "ON source_group_projection_state"
                "(inventory_revision, projection_version, object_id, scope_id)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS content_selection_index "
                "(object_id TEXT PRIMARY KEY, mode TEXT NOT NULL, "
                "status TEXT NOT NULL, priority INTEGER NOT NULL, "
                "neighborhood_id TEXT NOT NULL, revision INTEGER NOT NULL)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS content_selection_work_idx "
                "ON content_selection_index(status, mode, priority DESC, "
                "neighborhood_id, object_id)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS filesystem_claims "
                "(claim_id TEXT PRIMARY KEY, claim_token TEXT NOT NULL UNIQUE, "
                "worker_id TEXT NOT NULL, lease_expires_at TEXT NOT NULL, "
                "status TEXT NOT NULL, item_count INTEGER NOT NULL, "
                "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS filesystem_claim_items "
                "(object_id TEXT PRIMARY KEY, claim_id TEXT NOT NULL, "
                "claim_token TEXT NOT NULL, worker_id TEXT NOT NULL, "
                "scope_id TEXT NOT NULL, inventory_revision INTEGER NOT NULL, "
                "provider TEXT NOT NULL, object_type TEXT NOT NULL, "
                "disposition TEXT NOT NULL, occurrence_payload TEXT NOT NULL, "
                "stage TEXT NOT NULL, checkpoint_payload TEXT NOT NULL, "
                "lease_expires_at TEXT NOT NULL, completed INTEGER NOT NULL, "
                "attempt INTEGER NOT NULL, updated_at TEXT NOT NULL, "
                "FOREIGN KEY(claim_id) REFERENCES filesystem_claims(claim_id))"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS filesystem_claim_items_claim_idx "
                "ON filesystem_claim_items(claim_id, object_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS filesystem_claim_items_lease_idx "
                "ON filesystem_claim_items(completed, lease_expires_at, object_id)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS matter_hierarchy_index "
                "(child_matter_id TEXT PRIMARY KEY, "
                "parent_matter_id TEXT NOT NULL, "
                "edge_id TEXT NOT NULL UNIQUE, "
                "role TEXT NOT NULL, ordinal INTEGER NOT NULL, "
                "freshness TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS "
                "matter_hierarchy_parent_idx "
                "ON matter_hierarchy_index(parent_matter_id, ordinal, child_matter_id)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS matter_hierarchy_stage_index "
                "(matter_id TEXT PRIMARY KEY, next_stage TEXT NOT NULL, "
                "terminal INTEGER NOT NULL, ui_reachable INTEGER NOT NULL, "
                "blocked INTEGER NOT NULL, revision INTEGER NOT NULL, "
                "change_ref TEXT NOT NULL, updated_at TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS "
                "matter_hierarchy_stage_next_idx "
                "ON matter_hierarchy_stage_index(next_stage, matter_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS "
                "matter_hierarchy_stage_state_idx "
                "ON matter_hierarchy_stage_index"
                "(terminal, ui_reachable, blocked)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS matter_work_item_index "
                "(item_id TEXT PRIMARY KEY, matter_id TEXT NOT NULL, "
                "status TEXT NOT NULL, key_time TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS matter_work_item_matter_idx "
                "ON matter_work_item_index(matter_id, key_time, item_id)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS matter_context_signal_index "
                "(matter_id TEXT NOT NULL, signal_kind TEXT NOT NULL, "
                "signal_value TEXT NOT NULL, context_revision INTEGER NOT NULL, "
                "PRIMARY KEY(matter_id, signal_kind, signal_value))"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS matter_context_signal_lookup_idx "
                "ON matter_context_signal_index"
                "(signal_kind, signal_value, matter_id)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS store_metadata "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            for index_id, owner in _MATERIALIZED_INDEX_OWNERS.items():
                indexed = connection.execute(
                    "SELECT value FROM store_metadata WHERE key=?",
                    (index_id,),
                ).fetchone()
                if indexed is not None:
                    continue
                has_current_owner = connection.execute(
                    "SELECT 1 FROM current_objects "
                    "WHERE owner=? LIMIT 1",
                    (owner,),
                ).fetchone()
                if has_current_owner is None:
                    connection.execute(
                        "INSERT INTO store_metadata(key, value) "
                        "VALUES (?, 'complete')",
                        (index_id,),
                    )
            coverage_stage_indexed = connection.execute(
                "SELECT value FROM store_metadata "
                "WHERE key='coverage_stage_index:v2'"
            ).fetchone()
            if coverage_stage_indexed is None:
                current_coverage_count = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM current_objects "
                        "WHERE owner='object_coverage'"
                    ).fetchone()[0]
                )
                if not current_coverage_count:
                    connection.execute(
                        "INSERT INTO store_metadata(key, value) "
                        "VALUES ('coverage_stage_index:v2', 'complete')"
                    )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        ambient = getattr(
            self._connection_state,
            "connection",
            None,
        )
        if ambient is not None:
            atomic = bool(
                getattr(
                    self._connection_state,
                    "atomic_transaction",
                    False,
                )
            )
            try:
                yield ambient
                if not atomic:
                    ambient.commit()
            except BaseException:
                if not atomic:
                    ambient.rollback()
                raise
            return

        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @contextmanager
    def immediate_transaction(self) -> Iterator[None]:
        """Run nested store operations in one serialized write transaction."""

        if getattr(self._connection_state, "connection", None) is not None:
            raise RuntimeError("immediate transaction cannot be nested")
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        self._connection_state.connection = connection
        self._connection_state.atomic_transaction = True
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            self._connection_state.atomic_transaction = False
            self._connection_state.connection = None
            connection.close()

    def in_atomic_transaction(self) -> bool:
        return bool(
            getattr(self._connection_state, "connection", None)
            is not None
            and getattr(
                self._connection_state,
                "atomic_transaction",
                False,
            )
        )

    @contextmanager
    def connection_session(self) -> Iterator[None]:
        """Reuse one connection across many individually committed methods."""

        ambient = getattr(
            self._connection_state,
            "connection",
            None,
        )
        if ambient is not None:
            yield
            return
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        self._connection_state.connection = connection
        try:
            yield
        finally:
            if connection.in_transaction:
                connection.rollback()
            self._connection_state.connection = None
            connection.close()

    def next_revision(self, owner: str, object_id: str) -> int:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(revision), 0) FROM snapshots "
                "WHERE owner=? AND object_id=?",
                (owner, object_id),
            ).fetchone()
        return int(row[0]) + 1

    @staticmethod
    def _archive_snapshot(
        connection: sqlite3.Connection,
        *,
        owner: str,
        object_id: str,
        revision: int,
    ) -> tuple[int, int]:
        """Move one non-current coverage revision to verified compressed history."""

        if owner != COMPRESSED_HISTORY_OWNER or revision < 1:
            return (0, 0)
        current = connection.execute(
            "SELECT revision FROM current_objects WHERE owner=? AND object_id=?",
            (owner, object_id),
        ).fetchone()
        if current is not None and int(current[0]) == revision:
            raise ValueError("current snapshot cannot be archived")
        row = connection.execute(
            "SELECT payload, payload_hash, created_at FROM snapshots "
            "WHERE owner=? AND object_id=? AND revision=?",
            (owner, object_id, revision),
        ).fetchone()
        if row is None:
            return (0, 0)
        encoded = str(row[0])
        payload_hash = str(row[1]) or (
            "sha256:" + sha256(encoded.encode("utf-8")).hexdigest()
        )
        compressed = zlib.compress(encoded.encode("utf-8"), level=9)
        if zlib.decompress(compressed).decode("utf-8") != encoded:
            raise ValueError("compressed snapshot verification failed")
        connection.execute(
            "INSERT INTO snapshot_archive"
            "(owner, object_id, revision, codec, payload, payload_hash, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(owner, object_id, revision) DO NOTHING",
            (
                owner,
                object_id,
                revision,
                COMPRESSED_HISTORY_CODEC,
                compressed,
                payload_hash,
                str(row[2]),
            ),
        )
        archived = connection.execute(
            "SELECT codec, payload, payload_hash, created_at "
            "FROM snapshot_archive "
            "WHERE owner=? AND object_id=? AND revision=?",
            (owner, object_id, revision),
        ).fetchone()
        if (
            archived is None
            or str(archived[0]) != COMPRESSED_HISTORY_CODEC
            or str(archived[2]) != payload_hash
            or str(archived[3]) != str(row[2])
            or zlib.decompress(bytes(archived[1])).decode("utf-8") != encoded
        ):
            raise ValueError("compressed snapshot archive did not verify")
        connection.execute(
            "DELETE FROM snapshots "
            "WHERE owner=? AND object_id=? AND revision=?",
            (owner, object_id, revision),
        )
        return (len(encoded.encode("utf-8")), len(compressed))

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
            prior = connection.execute(
                "SELECT revision FROM current_objects "
                "WHERE owner=? AND object_id=?",
                (owner, object_id),
            ).fetchone()
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
            self._refresh_current_indexes(
                connection,
                owner=owner,
                object_id=object_id,
                revision=revision,
                encoded_payload=encoded,
            )
            if prior is not None and revision > int(prior[0]):
                self._archive_snapshot(
                    connection,
                    owner=owner,
                    object_id=object_id,
                    revision=int(prior[0]),
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
            prior_revisions: dict[tuple[str, str], int] = {}
            coverage_ids = tuple(
                dict.fromkeys(
                    object_id
                    for owner, object_id, _revision, _payload, _hash, _at
                    in prepared
                    if owner == COMPRESSED_HISTORY_OWNER
                )
            )
            for start in range(0, len(coverage_ids), 800):
                batch = coverage_ids[start : start + 800]
                placeholders = ",".join("?" for _ in batch)
                prior_revisions.update(
                    {
                        (COMPRESSED_HISTORY_OWNER, str(object_id)): int(revision)
                        for object_id, revision in connection.execute(
                            "SELECT object_id, revision FROM current_objects "
                            "WHERE owner=? "
                            f"AND object_id IN ({placeholders})",
                            (COMPRESSED_HISTORY_OWNER, *batch),
                        )
                    }
                )
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
                self._refresh_current_indexes(
                    connection,
                    owner=owner,
                    object_id=object_id,
                    revision=revision,
                    encoded_payload=encoded,
                )
            for (owner, object_id), prior_revision in prior_revisions.items():
                current = connection.execute(
                    "SELECT revision FROM current_objects "
                    "WHERE owner=? AND object_id=?",
                    (owner, object_id),
                ).fetchone()
                if current is not None and int(current[0]) > prior_revision:
                    self._archive_snapshot(
                        connection,
                        owner=owner,
                        object_id=object_id,
                        revision=prior_revision,
                    )

    def append_next(
        self,
        owner: str,
        object_id: str,
        payload: Any,
    ) -> int:
        """Atomically allocate and append the next mutable revision."""

        if not owner or not object_id:
            raise ValueError("owner and object_id are required")
        encoded = _canonical_json(payload)
        payload_hash = "sha256:" + sha256(encoded.encode("utf-8")).hexdigest()
        with self.connection() as connection:
            if not connection.in_transaction:
                connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                "SELECT revision FROM current_objects "
                "WHERE owner=? AND object_id=?",
                (owner, object_id),
            ).fetchone()
            row = connection.execute(
                "SELECT COALESCE(MAX(revision), 0) FROM snapshots "
                "WHERE owner=? AND object_id=?",
                (owner, object_id),
            ).fetchone()
            revision = int(row[0]) + 1
            connection.execute(
                "INSERT INTO snapshots"
                "(owner, object_id, revision, payload, payload_hash, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    owner,
                    object_id,
                    revision,
                    encoded,
                    payload_hash,
                    _utc_now(),
                ),
            )
            connection.execute(
                "INSERT INTO current_objects(owner, object_id, revision) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(owner, object_id) DO UPDATE SET "
                "revision=excluded.revision "
                "WHERE excluded.revision > current_objects.revision",
                (owner, object_id, revision),
            )
            self._refresh_current_indexes(
                connection,
                owner=owner,
                object_id=object_id,
                revision=revision,
                encoded_payload=encoded,
            )
            if prior is not None and revision > int(prior[0]):
                self._archive_snapshot(
                    connection,
                    owner=owner,
                    object_id=object_id,
                    revision=int(prior[0]),
                )
        return revision

    def compare_current_and_append(
        self,
        owner: str,
        object_id: str,
        *,
        is_equivalent: Callable[[dict[str, Any] | None], bool],
        payload_factory: Callable[
            [int, dict[str, Any] | None],
            Any,
        ],
    ) -> dict[str, Any]:
        """Atomically compare current state and build the next revision.

        The callbacks execute under the short ``BEGIN IMMEDIATE`` write
        transaction and therefore must be deterministic and non-blocking.
        ``payload_factory`` receives the allocated database revision so
        payload-internal version fields cannot drift from storage identity.
        """

        if not owner or not object_id:
            raise ValueError("owner and object_id are required")
        with self.connection() as connection:
            if not connection.in_transaction:
                connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT c.revision, s.payload, s.payload_hash "
                "FROM current_objects c "
                "JOIN snapshots s ON s.owner=c.owner "
                "AND s.object_id=c.object_id AND s.revision=c.revision "
                "WHERE c.owner=? AND c.object_id=?",
                (owner, object_id),
            ).fetchone()
            current_revision = int(row[0]) if row else 0
            current_payload = json.loads(row[1]) if row else None
            if is_equivalent(current_payload):
                if row is None:
                    raise ValueError(
                        "equivalence callback accepted a missing current row"
                    )
                return {
                    "status": "current",
                    "revision": current_revision,
                    "payload": current_payload,
                    "payload_hash": str(row[2]),
                }

            next_row = connection.execute(
                "SELECT COALESCE(MAX(revision), 0) FROM snapshots "
                "WHERE owner=? AND object_id=?",
                (owner, object_id),
            ).fetchone()
            revision = int(next_row[0]) + 1
            payload = payload_factory(revision, current_payload)
            encoded = _canonical_json(payload)
            payload_hash = (
                "sha256:" + sha256(encoded.encode("utf-8")).hexdigest()
            )
            connection.execute(
                "INSERT INTO snapshots"
                "(owner, object_id, revision, payload, payload_hash, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    owner,
                    object_id,
                    revision,
                    encoded,
                    payload_hash,
                    _utc_now(),
                ),
            )
            connection.execute(
                "INSERT INTO current_objects(owner, object_id, revision) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(owner, object_id) DO UPDATE SET "
                "revision=excluded.revision "
                "WHERE excluded.revision > current_objects.revision",
                (owner, object_id, revision),
            )
            self._refresh_current_indexes(
                connection,
                owner=owner,
                object_id=object_id,
                revision=revision,
                encoded_payload=encoded,
            )
            if current_revision and revision > current_revision:
                self._archive_snapshot(
                    connection,
                    owner=owner,
                    object_id=object_id,
                    revision=current_revision,
                )
        return {
            "status": "appended",
            "revision": revision,
            "payload": json.loads(encoded),
            "payload_hash": payload_hash,
        }

    def append_content_addressed_many(
        self,
        rows: Iterable[tuple[str, str, Any]],
    ) -> tuple[tuple[str, str], ...]:
        """Atomically converge immutable identities to one exact payload.

        An existing identity with the same canonical payload is a no-op.  Any
        different payload for that identity rejects the entire transaction.
        """

        prepared: dict[tuple[str, str], tuple[str, str]] = {}
        for owner, object_id, payload in rows:
            if not owner or not object_id:
                raise ValueError("owner and object_id are required")
            encoded = _canonical_json(payload)
            payload_hash = (
                "sha256:" + sha256(encoded.encode("utf-8")).hexdigest()
            )
            identity = (owner, object_id)
            prior = prepared.get(identity)
            if prior is not None and prior != (encoded, payload_hash):
                raise ValueError(
                    "content-addressed identity has conflicting payloads"
                )
            prepared[identity] = (encoded, payload_hash)
        if not prepared:
            return ()

        inserted: list[tuple[str, str]] = []
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing: dict[tuple[str, str], tuple[str, str]] = {}
            identities = tuple(prepared)
            for start in range(0, len(identities), 400):
                batch = identities[start : start + 400]
                predicates = " OR ".join(
                    "(owner=? AND object_id=?)" for _ in batch
                )
                parameters = tuple(
                    value
                    for identity in batch
                    for value in identity
                )
                for owner, object_id, payload, payload_hash in connection.execute(
                    "SELECT owner, object_id, payload, payload_hash "
                    "FROM snapshots WHERE " + predicates,
                    parameters,
                ):
                    identity = (str(owner), str(object_id))
                    encoded = str(payload)
                    digest = str(payload_hash) or (
                        "sha256:"
                        + sha256(encoded.encode("utf-8")).hexdigest()
                    )
                    prior = existing.get(identity)
                    if prior is not None and prior != (encoded, digest):
                        raise ValueError(
                            "content-addressed identity already has "
                            "conflicting history"
                        )
                    existing[identity] = (encoded, digest)

            for identity, expected in prepared.items():
                observed = existing.get(identity)
                if observed is not None and observed != expected:
                    raise ValueError(
                        "content-addressed identity already has "
                        "a different payload"
                    )

            created_at = _utc_now()
            for (owner, object_id), (encoded, payload_hash) in prepared.items():
                if (owner, object_id) in existing:
                    continue
                connection.execute(
                    "INSERT INTO snapshots"
                    "(owner, object_id, revision, payload, payload_hash, created_at) "
                    "VALUES (?, ?, 1, ?, ?, ?)",
                    (
                        owner,
                        object_id,
                        encoded,
                        payload_hash,
                        created_at,
                    ),
                )
                connection.execute(
                    "INSERT INTO current_objects(owner, object_id, revision) "
                    "VALUES (?, ?, 1)",
                    (owner, object_id),
                )
                self._refresh_current_indexes(
                    connection,
                    owner=owner,
                    object_id=object_id,
                    revision=1,
                    encoded_payload=encoded,
                )
                inserted.append((owner, object_id))
        return tuple(inserted)

    @staticmethod
    def _refresh_current_indexes(
        connection: sqlite3.Connection,
        *,
        owner: str,
        object_id: str,
        revision: int,
        encoded_payload: str,
    ) -> None:
        if owner == "object_coverage":
            SQLiteStore._refresh_coverage_matter_index(
                connection,
                object_id=object_id,
                revision=revision,
                encoded_payload=encoded_payload,
            )
            SQLiteStore._refresh_coverage_stage_index(
                connection,
                object_id=object_id,
                revision=revision,
                encoded_payload=encoded_payload,
            )
        elif owner == "inventory_snapshot":
            SQLiteStore._refresh_inventory_occurrence_index(
                connection,
                scope_id=object_id,
                revision=revision,
                encoded_payload=encoded_payload,
            )
        elif owner == "content_selection":
            SQLiteStore._refresh_content_selection_index(
                connection,
                object_id=object_id,
                revision=revision,
                encoded_payload=encoded_payload,
            )
        elif owner == "matter_containment_edge":
            SQLiteStore._refresh_hierarchy_index(
                connection,
                edge_id=object_id,
                revision=revision,
                encoded_payload=encoded_payload,
            )
        elif owner == "matter_hierarchy_audit":
            SQLiteStore._refresh_hierarchy_stage_index(
                connection,
                matter_id=object_id,
                revision=revision,
                encoded_payload=encoded_payload,
            )
        elif owner == "matter_work_item":
            SQLiteStore._refresh_work_item_index(
                connection,
                item_id=object_id,
                revision=revision,
                encoded_payload=encoded_payload,
            )
        elif owner == "matter_context":
            SQLiteStore._refresh_matter_context_signal_index(
                connection,
                matter_id=object_id,
                revision=revision,
                encoded_payload=encoded_payload,
            )

    @staticmethod
    def _refresh_matter_context_signal_index(
        connection: sqlite3.Connection,
        *,
        matter_id: str,
        revision: int,
        encoded_payload: str,
    ) -> None:
        """Replace one current Matter's exact-signal recall projection."""

        current = connection.execute(
            "SELECT revision FROM current_objects "
            "WHERE owner='matter_context' AND object_id=?",
            (matter_id,),
        ).fetchone()
        if current is None or int(current[0]) != revision:
            return
        connection.execute(
            "DELETE FROM matter_context_signal_index WHERE matter_id=?",
            (matter_id,),
        )
        payload = json.loads(encoded_payload)
        if str(payload.get("freshness", "current")) != "current":
            return
        context_revision = int(payload.get("context_revision", 1) or 1)
        rows = tuple(
            (
                matter_id,
                str(signal.get("kind", "")),
                str(signal.get("value", "")),
                context_revision,
            )
            for signal in payload.get("signals", ())
            if isinstance(signal, dict)
            and str(signal.get("freshness", "current")) == "current"
            and str(signal.get("kind", ""))
            and str(signal.get("value", ""))
        )
        connection.executemany(
            "INSERT OR IGNORE INTO matter_context_signal_index"
            "(matter_id, signal_kind, signal_value, context_revision) "
            "VALUES (?, ?, ?, ?)",
            rows,
        )

    @staticmethod
    def _refresh_inventory_occurrence_index(
        connection: sqlite3.Connection,
        *,
        scope_id: str,
        revision: int,
        encoded_payload: str,
    ) -> None:
        """Replace one scope's rebuildable occurrence projection atomically."""

        current = connection.execute(
            "SELECT revision FROM current_objects "
            "WHERE owner='inventory_snapshot' AND object_id=?",
            (scope_id,),
        ).fetchone()
        if current is None or int(current[0]) != revision:
            return
        payload = json.loads(encoded_payload)
        dispositions = {
            str(item.get("occurrence_id", "")): str(item.get("status", ""))
            for item in payload.get("dispositions", ())
            if str(item.get("occurrence_id", ""))
        }
        rows = []
        for occurrence in payload.get("occurrences", ()):
            occurrence_payload = dict(occurrence)
            object_id = str(occurrence_payload.get("occurrence_id", ""))
            if not object_id:
                raise ValueError(
                    "inventory occurrence requires an occurrence_id"
                )
            disposition = dispositions.get(object_id)
            if disposition is None:
                raise ValueError(
                    "inventory occurrence requires one disposition"
                )
            rows.append(
                (
                    scope_id,
                    object_id,
                    revision,
                    str(occurrence_payload.get("provider", "")),
                    str(occurrence_payload.get("object_type", "")),
                    disposition,
                    _canonical_json(occurrence_payload),
                )
            )
        connection.execute(
            "DELETE FROM inventory_occurrence_current WHERE scope_id=?",
            (scope_id,),
        )
        connection.executemany(
            "INSERT INTO inventory_occurrence_current"
            "(scope_id, object_id, inventory_revision, provider, object_type, "
            "disposition, occurrence_payload) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )

    @staticmethod
    def _refresh_content_selection_index(
        connection: sqlite3.Connection,
        *,
        object_id: str,
        revision: int,
        encoded_payload: str,
    ) -> None:
        """Maintain a private, locator-free scheduling projection."""

        current = connection.execute(
            "SELECT revision FROM current_objects "
            "WHERE owner='content_selection' AND object_id=?",
            (object_id,),
        ).fetchone()
        if current is None or int(current[0]) != revision:
            return
        payload = json.loads(encoded_payload)
        connection.execute(
            "INSERT INTO content_selection_index"
            "(object_id, mode, status, priority, neighborhood_id, revision) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(object_id) DO UPDATE SET "
            "mode=excluded.mode, status=excluded.status, "
            "priority=excluded.priority, neighborhood_id=excluded.neighborhood_id, "
            "revision=excluded.revision "
            "WHERE excluded.revision >= content_selection_index.revision",
            (
                object_id,
                str(payload.get("mode", "metadata_only")),
                str(payload.get("status", "blocked")),
                int(payload.get("priority", 0) or 0),
                str(payload.get("source_neighborhood_id", "")),
                revision,
            ),
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

    @staticmethod
    def _refresh_coverage_stage_index(
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
        payload = json.loads(encoded_payload)
        active = bool(payload.get("active", True))
        stages = dict(payload.get("stages", {}))
        required_stages = tuple(
            dict.fromkeys(
                str(stage_id)
                for stage_id in payload.get("required_stages", ())
                if str(stage_id)
            )
        )
        terminal_statuses = {
            "current",
            "not_applicable",
            "no_finding",
            "uncertain",
            "blocked",
        }
        indexed_stages: list[tuple[str, str, str, str, str, str]] = []
        for stage_id in required_stages:
            pointer = stages.get(stage_id)
            normalized_pointer = (
                dict(pointer)
                if isinstance(pointer, dict)
                else {}
            )
            indexed_stages.append(
                (
                    stage_id,
                    str(normalized_pointer.get("status", "missing")),
                    str(normalized_pointer.get("owner_id", "")),
                    str(normalized_pointer.get("failure_class", "")),
                    str(normalized_pointer.get("input_fingerprint", "")),
                    str(normalized_pointer.get("updated_at", "")),
                )
            )
        first_gap = next(
            (
                stage
                for stage in indexed_stages
                if stage[1] in {"missing", "pending", "stale", "blocked"}
            ),
            ("", "", "", "", "", ""),
        )
        next_stage = next(
            (
                stage_id
                for stage_id, status, *_rest in indexed_stages
                if status not in terminal_statuses
            ),
            "",
        )
        terminal = (not next_stage) or not active
        blocked = active and any(
            status == "blocked"
            for _stage_id, status, *_rest in indexed_stages
        )
        matter_ids = tuple(payload.get("matter_ids", ()))
        provider = str(payload.get("provider", ""))
        object_type = str(payload.get("object_type", ""))

        def stage_is(
            stage_id: str,
            allowed_statuses: set[str],
        ) -> bool:
            pointer = stages.get(stage_id)
            return (
                isinstance(pointer, dict)
                and str(pointer.get("status", "")) in allowed_statuses
            )

        hierarchy_statuses = (
            {"current", "uncertain"}
            if provider == "matters"
            else {"current", "uncertain", "not_applicable"}
        )
        hero_statuses = (
            {"current", "uncertain"}
            if object_type == "root_matter"
            else {"current", "uncertain", "not_applicable"}
        )
        ui_ready = (
            active
            and bool(matter_ids)
            and stage_is("matter", {"current", "uncertain"})
            and stage_is("semantic_depth", {"current", "uncertain"})
            and all(
                stage_is(stage_id, hierarchy_statuses)
                for stage_id in (
                    "hierarchy_registration",
                    "hierarchy_local_validation",
                    "hierarchy_global_validation",
                    "hierarchy_freshness",
                    "hierarchy_projection",
                )
            )
            and stage_is("localization", {"current", "uncertain"})
            and stage_is(
                "meaningful_clue_summary",
                {"current", "uncertain"},
            )
            and stage_is("generated_hero", hero_statuses)
            and stage_is(
                "supplemental_information",
                {"current", "uncertain", "no_finding"},
            )
            and stage_is("ui_projection", {"current", "uncertain"})
            and stage_is("ui_reachable", {"current", "uncertain"})
        )
        connection.execute(
            "INSERT INTO coverage_stage_index"
            "(object_id, provider, object_type, disposition, next_stage, "
            "terminal, ui_ready, blocked, active, "
            "first_gap_stage, first_gap_status, first_gap_owner_id, "
            "first_gap_failure_class, first_gap_input_fingerprint, "
            "first_gap_updated_at, first_gap_indexed_revision, "
            "revision, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(object_id) DO UPDATE SET "
            "provider=excluded.provider, object_type=excluded.object_type, "
            "disposition=excluded.disposition, next_stage=excluded.next_stage, "
            "terminal=excluded.terminal, ui_ready=excluded.ui_ready, "
            "blocked=excluded.blocked, active=excluded.active, "
            "first_gap_stage=excluded.first_gap_stage, "
            "first_gap_status=excluded.first_gap_status, "
            "first_gap_owner_id=excluded.first_gap_owner_id, "
            "first_gap_failure_class=excluded.first_gap_failure_class, "
            "first_gap_input_fingerprint="
            "excluded.first_gap_input_fingerprint, "
            "first_gap_updated_at=excluded.first_gap_updated_at, "
            "first_gap_indexed_revision="
            "excluded.first_gap_indexed_revision, "
            "revision=excluded.revision, "
            "updated_at=excluded.updated_at "
            "WHERE excluded.revision >= coverage_stage_index.revision",
            (
                object_id,
                provider,
                object_type,
                str(payload.get("disposition", "")),
                next_stage if active else "",
                int(terminal),
                int(ui_ready),
                int(blocked),
                int(active),
                first_gap[0] if active else "",
                first_gap[1] if active else "",
                first_gap[2] if active else "",
                first_gap[3] if active else "",
                first_gap[4] if active else "",
                first_gap[5] if active else "",
                revision,
                revision,
                str(payload.get("updated_at", "")),
            ),
        )
        connection.execute(
            "DELETE FROM coverage_stage_status_index WHERE object_id=?",
            (object_id,),
        )
        if active:
            connection.executemany(
                "INSERT INTO coverage_stage_status_index"
                "(object_id, stage_id, status, owner_id, failure_class, "
                "input_fingerprint, stage_updated_at, coverage_revision) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    (
                        object_id,
                        stage_id,
                        status,
                        owner_id,
                        failure_class,
                        input_fingerprint,
                        stage_updated_at,
                        revision,
                    )
                    for (
                        stage_id,
                        status,
                        owner_id,
                        failure_class,
                        input_fingerprint,
                        stage_updated_at,
                    ) in indexed_stages
                ),
            )
        connection.execute(
            "UPDATE coverage_audit_index_state SET "
            "generation=generation+1, last_object_id=?, updated_at=? "
            "WHERE singleton_id=1",
            (object_id, _utc_now()),
        )

    @staticmethod
    def _refresh_hierarchy_stage_index(
        connection: sqlite3.Connection,
        *,
        matter_id: str,
        revision: int,
        encoded_payload: str,
    ) -> None:
        """Materialize one Matter's first non-current hierarchy stage."""

        current = connection.execute(
            "SELECT revision FROM current_objects "
            "WHERE owner='matter_hierarchy_audit' AND object_id=?",
            (matter_id,),
        ).fetchone()
        if current is None or int(current[0]) != revision:
            return
        payload = json.loads(encoded_payload)
        stages = dict(payload.get("stages", {}))
        stage_order = (
            "hierarchy_decision",
            "containment_current",
            "child_state_current",
            "ancestor_rollup_current",
            "hierarchy_projection_current",
            "ui_reachable",
        )
        statuses = {
            stage_id: str(stages.get(stage_id, ""))
            for stage_id in stage_order
        }
        next_stage = next(
            (
                stage_id
                for stage_id in stage_order
                if statuses[stage_id] not in {"current", "not_applicable"}
            ),
            "",
        )
        terminal_statuses = {
            "current",
            "not_applicable",
            "uncertain",
            "blocked",
        }
        terminal = all(
            status in terminal_statuses for status in statuses.values()
        )
        blocked = any(status == "blocked" for status in statuses.values())
        ui_reachable = (
            statuses["ui_reachable"] == "current"
            and not next_stage
        )
        connection.execute(
            "INSERT INTO matter_hierarchy_stage_index"
            "(matter_id, next_stage, terminal, ui_reachable, blocked, "
            "revision, change_ref, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(matter_id) DO UPDATE SET "
            "next_stage=excluded.next_stage, terminal=excluded.terminal, "
            "ui_reachable=excluded.ui_reachable, blocked=excluded.blocked, "
            "revision=excluded.revision, change_ref=excluded.change_ref, "
            "updated_at=excluded.updated_at "
            "WHERE excluded.revision >= matter_hierarchy_stage_index.revision",
            (
                matter_id,
                next_stage,
                int(terminal),
                int(ui_reachable),
                int(blocked),
                revision,
                str(payload.get("change_ref", "")),
                str(payload.get("updated_at", "")),
            ),
        )

    @staticmethod
    def _refresh_hierarchy_index(
        connection: sqlite3.Connection,
        *,
        edge_id: str,
        revision: int,
        encoded_payload: str,
    ) -> None:
        current = connection.execute(
            "SELECT revision FROM current_objects "
            "WHERE owner='matter_containment_edge' AND object_id=?",
            (edge_id,),
        ).fetchone()
        if current is None or int(current[0]) != revision:
            return
        connection.execute(
            "DELETE FROM matter_hierarchy_index WHERE edge_id=?",
            (edge_id,),
        )
        payload = json.loads(encoded_payload)
        if not bool(payload.get("active", False)):
            return
        connection.execute(
            "INSERT INTO matter_hierarchy_index"
            "(child_matter_id, parent_matter_id, edge_id, role, ordinal, freshness) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(payload["child_matter_id"]),
                str(payload["parent_matter_id"]),
                edge_id,
                str(payload["role"]),
                int(payload.get("ordinal", 0)),
                str(payload.get("freshness", "pending")),
            ),
        )

    @staticmethod
    def _refresh_work_item_index(
        connection: sqlite3.Connection,
        *,
        item_id: str,
        revision: int,
        encoded_payload: str,
    ) -> None:
        current = connection.execute(
            "SELECT revision FROM current_objects "
            "WHERE owner='matter_work_item' AND object_id=?",
            (item_id,),
        ).fetchone()
        if current is None or int(current[0]) != revision:
            return
        connection.execute(
            "DELETE FROM matter_work_item_index WHERE item_id=?",
            (item_id,),
        )
        payload = json.loads(encoded_payload)
        if bool(payload.get("deleted", False)):
            return
        key_time = str(
            payload.get("actual_end")
            or payload.get("actual_start")
            or payload.get("planned_end")
            or payload.get("planned_start")
            or ""
        )
        connection.execute(
            "INSERT INTO matter_work_item_index(item_id, matter_id, status, key_time) "
            "VALUES (?, ?, ?, ?)",
            (
                item_id,
                str(payload["matter_id"]),
                str(payload["status"]),
                key_time,
            ),
        )

    def history(self, owner: str, object_id: str) -> tuple[dict, ...]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT revision, payload FROM snapshots "
                "WHERE owner=? AND object_id=?",
                (owner, object_id),
            ).fetchall()
            archived = connection.execute(
                "SELECT revision, codec, payload FROM snapshot_archive "
                "WHERE owner=? AND object_id=?",
                (owner, object_id),
            ).fetchall()
        payloads = {
            int(revision): str(payload)
            for revision, payload in rows
        }
        for revision, codec, payload in archived:
            if str(codec) != COMPRESSED_HISTORY_CODEC:
                raise ValueError("unsupported compressed snapshot codec")
            payloads[int(revision)] = zlib.decompress(bytes(payload)).decode(
                "utf-8"
            )
        return tuple(
            json.loads(payloads[revision])
            for revision in sorted(payloads)
        )

    def archive_object_coverage_history_page(
        self,
        *,
        after_object_id: str = "",
        after_revision: int = 0,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Compress one verified page of existing non-current coverage history.

        The caller owns backup verification and iteration.  Each page is one
        short transaction: archive insert, byte/hash verification, then source
        deletion.  Freed pages remain on SQLite's freelist for later writes;
        this method never runs VACUUM.
        """

        if limit < 1 or limit > 1_000 or after_revision < 0:
            raise ValueError("coverage history archive bounds are invalid")
        with self.connection() as connection:
            if not connection.in_transaction:
                connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT s.object_id, s.revision "
                "FROM snapshots s "
                "LEFT JOIN current_objects c "
                "ON c.owner=s.owner AND c.object_id=s.object_id "
                "AND c.revision=s.revision "
                "WHERE s.owner=? AND c.object_id IS NULL "
                "AND (s.object_id>? OR (s.object_id=? AND s.revision>?)) "
                "ORDER BY s.object_id, s.revision LIMIT ?",
                (
                    COMPRESSED_HISTORY_OWNER,
                    after_object_id,
                    after_object_id,
                    after_revision,
                    limit,
                ),
            ).fetchall()
            raw_bytes = 0
            compressed_bytes = 0
            for object_id, revision in rows:
                raw_size, compressed_size = self._archive_snapshot(
                    connection,
                    owner=COMPRESSED_HISTORY_OWNER,
                    object_id=str(object_id),
                    revision=int(revision),
                )
                raw_bytes += raw_size
                compressed_bytes += compressed_size
            next_object_id = str(rows[-1][0]) if rows else ""
            next_revision = int(rows[-1][1]) if rows else 0
            has_more = bool(
                connection.execute(
                    "SELECT 1 FROM snapshots s "
                    "LEFT JOIN current_objects c "
                    "ON c.owner=s.owner AND c.object_id=s.object_id "
                    "AND c.revision=s.revision "
                    "WHERE s.owner=? AND c.object_id IS NULL "
                    "AND (s.object_id>? OR "
                    "(s.object_id=? AND s.revision>?)) LIMIT 1",
                    (
                        COMPRESSED_HISTORY_OWNER,
                        next_object_id or after_object_id,
                        next_object_id or after_object_id,
                        next_revision if rows else after_revision,
                    ),
                ).fetchone()
            )
        return {
            "scanned_count": len(rows),
            "archived_count": len(rows),
            "raw_bytes": raw_bytes,
            "compressed_bytes": compressed_bytes,
            "freed_page_candidate_bytes": max(
                0,
                raw_bytes - compressed_bytes,
            ),
            "next_object_id": next_object_id if has_more else "",
            "next_revision": next_revision if has_more else 0,
            "has_more": has_more,
            "status": "partial" if has_more else "current",
        }

    def legacy_evidence_pointer_page(
        self,
        *,
        after_object_id: str = "",
        limit: int = 20,
    ) -> tuple[tuple[dict[str, Any], ...], bool]:
        """Read one bounded current page with the retired comma-list pointer."""

        if limit < 1 or limit > 100:
            raise ValueError("legacy evidence pointer page bounds are invalid")
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT s.payload FROM current_objects c "
                "JOIN snapshots s ON s.owner=c.owner "
                "AND s.object_id=c.object_id AND s.revision=c.revision "
                "WHERE c.owner='object_coverage' AND c.object_id>? "
                "AND json_extract(s.payload, '$.stages.evidence.output_ref') "
                "LIKE '%,%' "
                "ORDER BY c.object_id LIMIT ?",
                (after_object_id, limit + 1),
            ).fetchall()
        return (
            tuple(json.loads(row[0]) for row in rows[:limit]),
            len(rows) > limit,
        )

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

    def legacy_coverage_stage_schema_page(
        self,
        *,
        after_object_id: str,
        limit: int,
        current_stage_order: tuple[str, ...],
    ) -> tuple[dict, ...]:
        """Read one keyset page of coverage rows on a retired stage schema."""

        if (
            not current_stage_order
            or limit < 1
            or limit > 500
        ):
            raise ValueError("coverage stage rebase bounds are invalid")
        expected = json.dumps(current_stage_order)
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT s.payload FROM current_objects c "
                "JOIN snapshots s ON s.owner=c.owner "
                "AND s.object_id=c.object_id AND s.revision=c.revision "
                "WHERE c.owner='object_coverage' AND c.object_id>? "
                "AND COALESCE(json_extract("
                "s.payload, '$.active'), 1)=1 "
                "AND json_extract("
                "s.payload, '$.disposition')='tracked' AND (EXISTS ("
                "SELECT 1 FROM json_each(s.payload, '$.required_stages') "
                "WHERE value='visual'"
                ") OR json_type(s.payload, '$.stages.visual') IS NOT NULL "
                "OR ("
                "COALESCE(json_array_length("
                "s.payload, '$.required_stages'), 0)<>? "
                "OR EXISTS ("
                "SELECT 1 FROM json_each(?) expected "
                "WHERE NOT EXISTS ("
                "SELECT 1 FROM json_each("
                "s.payload, '$.required_stages'"
                ") observed WHERE observed.value=expected.value"
                ")"
                ") OR EXISTS ("
                "SELECT 1 FROM json_each(?) expected "
                "WHERE json_type("
                "s.payload, '$.stages.' || expected.value"
                ") IS NULL"
                ")"
                ")"
                ") ORDER BY c.object_id LIMIT ?",
                (
                    after_object_id,
                    len(current_stage_order),
                    expected,
                    expected,
                    limit,
                ),
            ).fetchall()
        return tuple(json.loads(payload) for (payload,) in rows)

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

    def invalidated_analysis_output_refs(
        self,
        output_refs: Iterable[str],
    ) -> set[str]:
        """Return superseded owner outputs that have no current active owner."""

        refs = tuple(
            dict.fromkeys(str(item) for item in output_refs if str(item))
        )
        if not refs:
            return set()
        invalidations = self.current_by_json_scalar_values(
            "analysis_output_invalidation",
            json_field="output_ref",
            values=refs,
        )
        candidates = {
            output_ref
            for output_ref, rows in invalidations.items()
            if any(
                str(row.get("status", "")) == "superseded"
                for row in rows
            )
        }
        if not candidates:
            return set()
        owner_rows = self.current_by_json_scalar_values(
            "autonomous_finding",
            json_field="owner_output_ref",
            values=candidates,
        )
        package_ids = tuple(
            dict.fromkeys(
                str(row.get("package_id", ""))
                for rows in owner_rows.values()
                for row in rows
                if str(row.get("package_id", ""))
            )
        )
        package_invalidations = self.current_many(
            "analysis_result_invalidation",
            package_ids,
        )
        active_refs = {
            output_ref
            for output_ref, rows in owner_rows.items()
            if any(
                str(row.get("status", ""))
                in {"auto_applied", "uncertain"}
                and str(
                    package_invalidations.get(
                        str(row.get("package_id", "")),
                        {},
                    ).get("status", "")
                )
                != "superseded"
                for row in rows
            )
        }
        return candidates - active_refs

    def current_by_json_scalar_values(
        self,
        owner: str,
        *,
        json_field: str,
        values: Iterable[str],
    ) -> dict[str, tuple[dict, ...]]:
        """Group current payloads by one exact scalar JSON field value."""

        members = tuple(
            dict.fromkeys(str(item) for item in values if str(item))
        )
        if (
            not owner
            or not json_field
            or not json_field.replace("_", "").isalnum()
        ):
            raise ValueError("owner and a simple JSON scalar field are required")
        grouped: dict[str, list[dict]] = {item: [] for item in members}
        if not members:
            return {key: tuple(value) for key, value in grouped.items()}
        json_path = f"$.{json_field}"
        with self.connection() as connection:
            for start in range(0, len(members), 800):
                batch = members[start : start + 800]
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    "SELECT CAST(json_extract(s.payload, ?) AS TEXT), "
                    "s.payload "
                    "FROM current_objects c "
                    "JOIN snapshots s ON s.owner=c.owner "
                    "AND s.object_id=c.object_id AND s.revision=c.revision "
                    f"WHERE c.owner=? AND json_extract(s.payload, ?) "
                    f"IN ({placeholders}) ORDER BY c.object_id",
                    (json_path, owner, json_path, *batch),
                )
                for member, payload in rows:
                    grouped[str(member)].append(json.loads(payload))
        return {
            key: tuple(value)
            for key, value in grouped.items()
        }

    def inventory_occurrences_by_object_ids(
        self,
        object_ids: Iterable[str],
    ) -> dict[str, tuple[dict[str, Any], ...]]:
        """Resolve exact current occurrences without decoding scope snapshots."""

        ids = tuple(
            dict.fromkeys(str(item) for item in object_ids if str(item))
        )
        grouped: dict[str, list[dict[str, Any]]] = {
            object_id: [] for object_id in ids
        }
        if not ids:
            return {}
        with self.connection() as connection:
            for start in range(0, len(ids), 800):
                batch = ids[start : start + 800]
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    "SELECT scope_id, object_id, inventory_revision, provider, "
                    "object_type, disposition, occurrence_payload "
                    "FROM inventory_occurrence_current "
                    f"WHERE object_id IN ({placeholders}) "
                    "ORDER BY object_id, scope_id",
                    batch,
                )
                for row in rows:
                    grouped[str(row[1])].append(
                        {
                            "scope_id": str(row[0]),
                            "object_id": str(row[1]),
                            "inventory_revision": int(row[2]),
                            "provider": str(row[3]),
                            "object_type": str(row[4]),
                            "disposition": str(row[5]),
                            "occurrence": json.loads(row[6]),
                        }
                    )
        return {
            object_id: tuple(grouped[object_id])
            for object_id in ids
        }

    def current_gmail_message_sources_by_provider_ids(
        self,
        provider_message_ids: Iterable[str],
    ) -> dict[str, tuple[dict[str, Any], ...]]:
        """Resolve a bounded exact Gmail metadata-owner set.

        The provider message ids remain SQL parameters and are never projected
        into diagnostics or aggregate results.
        """

        ids = tuple(
            dict.fromkeys(
                str(item)
                for item in provider_message_ids
                if str(item)
            )
        )
        if len(ids) > 20:
            raise ValueError("gmail_body_batch_budget_exceeded")
        grouped: dict[str, list[dict[str, Any]]] = {
            message_id: [] for message_id in ids
        }
        if not ids:
            return {}
        with self.connection() as connection:
            placeholders = ",".join("?" for _ in ids)
            rows = connection.execute(
                "SELECT CAST(json_extract(s.payload, "
                "'$.content.provider_message_id') AS TEXT), s.payload "
                "FROM current_objects c "
                "JOIN snapshots s ON s.owner=c.owner "
                "AND s.object_id=c.object_id AND s.revision=c.revision "
                "WHERE c.owner='source_version' "
                "AND json_extract(s.payload, '$.provider')='gmail' "
                "AND json_extract(s.payload, "
                "'$.external_reference.provider')='gmail' "
                "AND json_extract(s.payload, "
                "'$.external_reference.object_type')='gmail_message' "
                "AND json_extract(s.payload, "
                f"'$.content.provider_message_id') IN ({placeholders}) "
                "ORDER BY c.object_id",
                ids,
            )
            for provider_message_id, payload in rows:
                grouped[str(provider_message_id)].append(
                    json.loads(payload)
                )
        return {
            message_id: tuple(grouped[message_id])
            for message_id in ids
        }

    def claim_registered_filesystem(
        self,
        *,
        worker_id: str,
        limit: int,
        lease_seconds: int = 300,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        """Atomically claim disjoint current or expired filesystem work."""

        if not worker_id:
            raise ValueError("filesystem claim worker_id is required")
        if limit < 1 or limit > 500:
            raise ValueError("filesystem claim limit is invalid")
        if lease_seconds < 1 or lease_seconds > 86_400:
            raise ValueError("filesystem claim lease is invalid")
        current_time = _normalized_utc(now)
        current_at = current_time.isoformat()
        lease_expires_at = (
            current_time + timedelta(seconds=lease_seconds)
        ).isoformat()
        claim_id = "filesystem-claim:" + uuid4().hex
        claim_token = uuid4().hex + uuid4().hex

        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            expired = connection.execute(
                "SELECT object_id, claim_id, scope_id, inventory_revision, "
                "provider, object_type, disposition, occurrence_payload, "
                "stage, checkpoint_payload, attempt "
                "FROM filesystem_claim_items "
                "WHERE completed=0 AND lease_expires_at<=? "
                "ORDER BY lease_expires_at, object_id LIMIT ?",
                (current_at, limit),
            ).fetchall()
            items: list[dict[str, Any]] = [
                {
                    "object_id": str(row[0]),
                    "prior_claim_id": str(row[1]),
                    "scope_id": str(row[2]),
                    "inventory_revision": int(row[3]),
                    "provider": str(row[4]),
                    "object_type": str(row[5]),
                    "disposition": str(row[6]),
                    "occurrence_payload": str(row[7]),
                    "stage": str(row[8]),
                    "checkpoint_payload": str(row[9]),
                    "attempt": int(row[10]) + 1,
                    "recovered": True,
                }
                for row in expired
            ]

            remaining = limit - len(items)
            if remaining:
                new_rows = connection.execute(
                    "SELECT i.object_id, i.scope_id, i.inventory_revision, "
                    "i.provider, i.object_type, i.disposition, "
                    "i.occurrence_payload "
                    "FROM coverage_stage_index coverage "
                    "JOIN inventory_occurrence_current i "
                    "ON i.object_id=coverage.object_id "
                    "JOIN content_selection_index selection "
                    "ON selection.object_id=i.object_id "
                    "LEFT JOIN filesystem_claim_items claimed "
                    "ON claimed.object_id=i.object_id "
                    "WHERE coverage.active=1 "
                    "AND coverage.provider='filesystem' "
                    "AND coverage.disposition='tracked' "
                    "AND coverage.next_stage='source_version' "
                    "AND selection.status='current' "
                    "AND selection.mode IN ('sampled', 'bounded') "
                    "AND i.provider='filesystem' "
                    "AND i.disposition='tracked' "
                    "AND i.scope_id=("
                    "SELECT MIN(candidate.scope_id) "
                    "FROM inventory_occurrence_current candidate "
                    "WHERE candidate.object_id=i.object_id "
                    "AND candidate.provider='filesystem' "
                    "AND candidate.disposition='tracked') "
                    "AND (claimed.object_id IS NULL OR claimed.completed=1) "
                    "ORDER BY selection.priority DESC, "
                    "selection.neighborhood_id, i.object_id LIMIT ?",
                    (remaining,),
                ).fetchall()
                items.extend(
                    {
                        "object_id": str(row[0]),
                        "prior_claim_id": "",
                        "scope_id": str(row[1]),
                        "inventory_revision": int(row[2]),
                        "provider": str(row[3]),
                        "object_type": str(row[4]),
                        "disposition": str(row[5]),
                        "occurrence_payload": str(row[6]),
                        "stage": "source_version",
                        "checkpoint_payload": "{}",
                        "attempt": 1,
                        "recovered": False,
                    }
                    for row in new_rows
                )

            if not items:
                return None
            connection.execute(
                "INSERT INTO filesystem_claims"
                "(claim_id, claim_token, worker_id, lease_expires_at, status, "
                "item_count, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 'active', ?, ?, ?)",
                (
                    claim_id,
                    claim_token,
                    worker_id,
                    lease_expires_at,
                    len(items),
                    current_at,
                    current_at,
                ),
            )
            prior_claim_ids = tuple(
                dict.fromkeys(
                    item["prior_claim_id"]
                    for item in items
                    if item["prior_claim_id"]
                )
            )
            if prior_claim_ids:
                placeholders = ",".join("?" for _ in prior_claim_ids)
                connection.execute(
                    "UPDATE filesystem_claims SET status='reclaimed', "
                    "updated_at=? "
                    f"WHERE claim_id IN ({placeholders}) AND status='active'",
                    (current_at, *prior_claim_ids),
                )
            for item in items:
                connection.execute(
                    "INSERT INTO filesystem_claim_items"
                    "(object_id, claim_id, claim_token, worker_id, scope_id, "
                    "inventory_revision, provider, object_type, disposition, "
                    "occurrence_payload, stage, checkpoint_payload, "
                    "lease_expires_at, completed, attempt, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?) "
                    "ON CONFLICT(object_id) DO UPDATE SET "
                    "claim_id=excluded.claim_id, "
                    "claim_token=excluded.claim_token, "
                    "worker_id=excluded.worker_id, "
                    "scope_id=excluded.scope_id, "
                    "inventory_revision=excluded.inventory_revision, "
                    "provider=excluded.provider, "
                    "object_type=excluded.object_type, "
                    "disposition=excluded.disposition, "
                    "occurrence_payload=excluded.occurrence_payload, "
                    "stage=excluded.stage, "
                    "checkpoint_payload=excluded.checkpoint_payload, "
                    "lease_expires_at=excluded.lease_expires_at, "
                    "completed=0, attempt=excluded.attempt, "
                    "updated_at=excluded.updated_at",
                    (
                        item["object_id"],
                        claim_id,
                        claim_token,
                        worker_id,
                        item["scope_id"],
                        item["inventory_revision"],
                        item["provider"],
                        item["object_type"],
                        item["disposition"],
                        item["occurrence_payload"],
                        item["stage"],
                        item["checkpoint_payload"],
                        lease_expires_at,
                        item["attempt"],
                        current_at,
                    ),
                )
        return {
            "claim_id": claim_id,
            "claim_token": claim_token,
            "worker_id": worker_id,
            "lease_expires_at": lease_expires_at,
            "items": tuple(
                {
                    "object_id": item["object_id"],
                    "scope_id": item["scope_id"],
                    "inventory_revision": item["inventory_revision"],
                    "stage": item["stage"],
                    "checkpoint": json.loads(item["checkpoint_payload"]),
                    "attempt": item["attempt"],
                    "recovered": item["recovered"],
                }
                for item in items
            ),
        }

    def filesystem_claim_occurrences(
        self,
        *,
        claim_id: str,
        claim_token: str,
    ) -> tuple[dict[str, Any], ...]:
        """Read the exact private occurrences frozen into one claim."""

        if not claim_id or not claim_token:
            raise ValueError("filesystem claim identity and token are required")
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT object_id, scope_id, inventory_revision, provider, "
                "object_type, disposition, occurrence_payload, stage, "
                "checkpoint_payload, completed, attempt, lease_expires_at "
                "FROM filesystem_claim_items "
                "WHERE claim_id=? AND claim_token=? ORDER BY object_id",
                (claim_id, claim_token),
            ).fetchall()
        return tuple(
            {
                "object_id": str(row[0]),
                "scope_id": str(row[1]),
                "inventory_revision": int(row[2]),
                "provider": str(row[3]),
                "object_type": str(row[4]),
                "disposition": str(row[5]),
                "occurrence": json.loads(row[6]),
                "stage": str(row[7]),
                "checkpoint": json.loads(row[8]),
                "completed": bool(row[9]),
                "attempt": int(row[10]),
                "lease_expires_at": str(row[11]),
            }
            for row in rows
        )

    def abandon_filesystem_worker_claim(
        self,
        *,
        worker_id: str,
        reason: str,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        """Release one exact worker claim while preserving item checkpoints."""

        if not worker_id:
            raise ValueError("filesystem claim worker_id is required")
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ValueError("filesystem claim abandon reason is required")
        current_at = _normalized_utc(now).isoformat()
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT claim_id, claim_token "
                "FROM filesystem_claims "
                "WHERE worker_id=? AND status='active' "
                "ORDER BY created_at",
                (worker_id,),
            ).fetchall()
            if not rows:
                return None
            if len(rows) != 1:
                raise ValueError(
                    "filesystem worker owns multiple active claims"
                )
            claim_id = str(rows[0][0])
            claim_token = str(rows[0][1])
            incomplete = int(
                connection.execute(
                    "SELECT COUNT(*) FROM filesystem_claim_items "
                    "WHERE claim_id=? AND claim_token=? AND completed=0",
                    (claim_id, claim_token),
                ).fetchone()[0]
            )
            connection.execute(
                "UPDATE filesystem_claim_items "
                "SET lease_expires_at=?, updated_at=? "
                "WHERE claim_id=? AND claim_token=? AND completed=0",
                (
                    current_at,
                    current_at,
                    claim_id,
                    claim_token,
                ),
            )
            connection.execute(
                "UPDATE filesystem_claims "
                "SET lease_expires_at=?, status='abandoned', updated_at=? "
                "WHERE claim_id=? AND claim_token=? AND status='active'",
                (
                    current_at,
                    current_at,
                    claim_id,
                    claim_token,
                ),
            )
        return {
            "claim_id": claim_id,
            "worker_id": worker_id,
            "status": "abandoned",
            "reason": normalized_reason,
            "released_item_count": incomplete,
        }

    def update_filesystem_claim_checkpoint(
        self,
        *,
        claim_id: str,
        claim_token: str,
        object_id: str,
        stage: str,
        checkpoint: Any,
        extend_lease_seconds: int = 0,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Advance one claimed item after validating its live token."""

        if stage not in FILESYSTEM_CLAIM_STAGES[:-1]:
            raise ValueError("filesystem claim stage is invalid")
        if extend_lease_seconds < 0 or extend_lease_seconds > 86_400:
            raise ValueError("filesystem claim lease extension is invalid")
        current_time = _normalized_utc(now)
        current_at = current_time.isoformat()
        encoded_checkpoint = _canonical_json(checkpoint)
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT item.stage, item.completed, item.lease_expires_at, "
                "item.checkpoint_payload "
                "FROM filesystem_claim_items item "
                "JOIN filesystem_claims claim "
                "ON claim.claim_id=item.claim_id "
                "WHERE item.object_id=? AND item.claim_id=? "
                "AND item.claim_token=? AND claim.claim_token=? "
                "AND claim.status='active'",
                (
                    object_id,
                    claim_id,
                    claim_token,
                    claim_token,
                ),
            ).fetchone()
            if (
                row is None
                or bool(row[1])
                or str(row[2]) <= current_at
            ):
                raise ValueError(
                    "filesystem claim token is invalid or expired"
                )
            prior_stage = str(row[0])
            if (
                prior_stage not in FILESYSTEM_CLAIM_STAGES
            ):
                raise ValueError("filesystem claim prior stage is invalid")
            if (
                FILESYSTEM_CLAIM_STAGES.index(stage)
                < FILESYSTEM_CLAIM_STAGES.index(prior_stage)
            ):
                # A recovered item may replay idempotent earlier owners before
                # it reaches its saved checkpoint. Keep the durable high-water
                # mark and only renew the live lease; never erase later stage
                # evidence or fail the whole file page.
                stage = prior_stage
                encoded_checkpoint = str(row[3])
            lease_expires_at = str(row[2])
            if extend_lease_seconds:
                lease_expires_at = (
                    current_time
                    + timedelta(seconds=extend_lease_seconds)
                ).isoformat()
                connection.execute(
                    "UPDATE filesystem_claim_items "
                    "SET lease_expires_at=?, updated_at=? "
                    "WHERE claim_id=? AND claim_token=? AND completed=0",
                    (
                        lease_expires_at,
                        current_at,
                        claim_id,
                        claim_token,
                    ),
                )
                connection.execute(
                    "UPDATE filesystem_claims "
                    "SET lease_expires_at=?, updated_at=? "
                    "WHERE claim_id=? AND claim_token=? AND status='active'",
                    (
                        lease_expires_at,
                        current_at,
                        claim_id,
                        claim_token,
                    ),
                )
            connection.execute(
                "UPDATE filesystem_claim_items "
                "SET stage=?, checkpoint_payload=?, updated_at=? "
                "WHERE object_id=? AND claim_id=? AND claim_token=?",
                (
                    stage,
                    encoded_checkpoint,
                    current_at,
                    object_id,
                    claim_id,
                    claim_token,
                ),
            )
        return {
            "claim_id": claim_id,
            "object_id": object_id,
            "stage": stage,
            "checkpoint": json.loads(encoded_checkpoint),
            "lease_expires_at": lease_expires_at,
        }

    def complete_filesystem_claim_item(
        self,
        *,
        claim_id: str,
        claim_token: str,
        object_id: str,
        checkpoint: Any,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Complete one item, rejecting stale, expired, or foreign tokens."""

        current_at = _normalized_utc(now).isoformat()
        encoded_checkpoint = _canonical_json(checkpoint)
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT item.completed, item.lease_expires_at "
                "FROM filesystem_claim_items item "
                "JOIN filesystem_claims claim "
                "ON claim.claim_id=item.claim_id "
                "WHERE item.object_id=? AND item.claim_id=? "
                "AND item.claim_token=? AND claim.claim_token=? "
                "AND claim.status='active'",
                (
                    object_id,
                    claim_id,
                    claim_token,
                    claim_token,
                ),
            ).fetchone()
            if (
                row is None
                or bool(row[0])
                or str(row[1]) <= current_at
            ):
                raise ValueError(
                    "filesystem claim token is invalid or expired"
                )
            connection.execute(
                "UPDATE filesystem_claim_items "
                "SET stage='complete', checkpoint_payload=?, completed=1, "
                "updated_at=? "
                "WHERE object_id=? AND claim_id=? AND claim_token=?",
                (
                    encoded_checkpoint,
                    current_at,
                    object_id,
                    claim_id,
                    claim_token,
                ),
            )
            incomplete = int(
                connection.execute(
                    "SELECT COUNT(*) FROM filesystem_claim_items "
                    "WHERE claim_id=? AND completed=0",
                    (claim_id,),
                ).fetchone()[0]
            )
            if incomplete == 0:
                connection.execute(
                    "UPDATE filesystem_claims "
                    "SET status='completed', updated_at=? "
                    "WHERE claim_id=? AND claim_token=?",
                    (current_at, claim_id, claim_token),
                )
        return {
            "claim_id": claim_id,
            "object_id": object_id,
            "stage": "complete",
            "checkpoint": json.loads(encoded_checkpoint),
            "claim_completed": incomplete == 0,
        }

    def evidence_anchors_for_source_version(
        self,
        *,
        source_id: str,
        source_version: int,
    ) -> tuple[dict[str, Any], ...]:
        """Read the exact current evidence set for one source revision."""

        if not source_id or source_version < 1:
            raise ValueError("source evidence identity is invalid")
        prefix = f"evidence:{source_id}:{source_version}:"
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT s.payload FROM current_objects current "
                "JOIN snapshots s ON s.owner=current.owner "
                "AND s.object_id=current.object_id "
                "AND s.revision=current.revision "
                "WHERE current.owner='evidence_anchor' "
                "AND current.object_id>=? AND current.object_id<? "
                "ORDER BY current.object_id",
                (prefix, prefix + "\uffff"),
            ).fetchall()
        return tuple(json.loads(row[0]) for row in rows)

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
            # Fetch relation ids first, then use exact primary-key lookups for
            # their current payloads. On a multi-million-row snapshot history,
            # SQLite can otherwise choose a snapshots-first join plan even
            # when the relation index is empty, turning one browser request
            # into a full historical scan.
            relations: list[tuple[str, str]] = []
            with self.connection() as connection:
                for start in range(0, len(members), 800):
                    batch = members[start : start + 800]
                    placeholders = ",".join("?" for _ in batch)
                    rows = connection.execute(
                        "SELECT matter_id, object_id "
                        "FROM coverage_matter_index "
                        f"WHERE matter_id IN ({placeholders}) "
                        "ORDER BY object_id",
                        batch,
                    )
                    relations.extend(
                        (str(member), str(object_id))
                        for member, object_id in rows
                    )
            payloads = self.current_many(
                "object_coverage",
                (object_id for _member, object_id in relations),
            )
            for member, object_id in relations:
                payload = payloads.get(object_id)
                if payload is not None:
                    grouped[member].append(payload)
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

    def matter_ids_for_coverage_objects(
        self,
        object_ids: Iterable[str],
        *,
        exclude_matter_id: str = "",
        limit: int = 200,
    ) -> tuple[tuple[str, int], ...]:
        """Rank bounded Matter candidates that share indexed coverage objects."""

        ids = tuple(
            dict.fromkeys(str(item) for item in object_ids if str(item))
        )
        if limit < 1 or limit > 1_000:
            raise ValueError("related Matter coverage limit is invalid")
        if not ids:
            return ()
        counts: dict[str, int] = {}
        with self.connection() as connection:
            for start in range(0, len(ids), 800):
                batch = ids[start : start + 800]
                placeholders = ",".join("?" for _ in batch)
                query = (
                    "SELECT matter_id, COUNT(*) "
                    "FROM coverage_matter_index "
                    f"WHERE object_id IN ({placeholders}) "
                )
                parameters: tuple[object, ...] = tuple(batch)
                if exclude_matter_id:
                    query += "AND matter_id<>? "
                    parameters = (*parameters, exclude_matter_id)
                query += "GROUP BY matter_id"
                for matter_id, count in connection.execute(query, parameters):
                    normalized = str(matter_id)
                    counts[normalized] = counts.get(normalized, 0) + int(count)
        return tuple(
            sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:limit]
        )

    def matter_context_match_page(
        self,
        signal_keys: Iterable[tuple[str, str]],
        *,
        after_matter_id: str = "",
        limit: int = 200,
    ) -> tuple[dict, ...]:
        """Read one keyset page of every current exact-signal Matter match."""

        keys = tuple(
            dict.fromkeys(
                (str(kind), str(value))
                for kind, value in signal_keys
                if str(kind) and str(value)
            )
        )
        if not keys or limit < 1 or limit > 500:
            raise ValueError("Matter context match page bounds are invalid")
        predicates = " OR ".join(
            "(idx.signal_kind=? AND idx.signal_value=?)"
            for _kind, _value in keys
        )
        parameters = tuple(
            item
            for key in keys
            for item in key
        )
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT DISTINCT idx.matter_id, s.payload "
                "FROM matter_context_signal_index idx "
                "JOIN current_objects c "
                "ON c.owner='matter_context' "
                "AND c.object_id=idx.matter_id "
                "JOIN snapshots s ON s.owner=c.owner "
                "AND s.object_id=c.object_id AND s.revision=c.revision "
                "WHERE idx.matter_id>? AND ("
                + predicates
                + ") ORDER BY idx.matter_id LIMIT ?",
                (after_matter_id, *parameters, limit),
            ).fetchall()
        return tuple(json.loads(payload) for _matter_id, payload in rows)

    def count_current(self, owner: str) -> int:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM current_objects WHERE owner=?",
                (owner,),
            ).fetchone()
        return int(row[0])

    def retire_current_owner(
        self,
        owner: str,
        *,
        migration_id: str,
    ) -> int:
        """Remove one retired owner from current authority while preserving history."""

        if not owner or not migration_id:
            raise ValueError("owner and migration_id are required")
        marker = f"retired-current-owner:{migration_id}"
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT value FROM store_metadata WHERE key=?",
                (marker,),
            ).fetchone()
            previous_total = 0
            if existing is not None:
                try:
                    existing_payload = json.loads(str(existing[0]))
                    previous_total = int(
                        existing_payload.get(
                            "total_retired_count",
                            existing_payload.get("retired_count", 0),
                        )
                    )
                except (TypeError, ValueError, json.JSONDecodeError):
                    previous_total = 0
            row = connection.execute(
                "SELECT COUNT(*) FROM current_objects WHERE owner=?",
                (owner,),
            ).fetchone()
            retired_count = int(row[0])
            connection.execute(
                "DELETE FROM current_objects WHERE owner=?",
                (owner,),
            )
            connection.execute(
                "INSERT OR REPLACE INTO store_metadata(key, value) VALUES (?, ?)",
                (
                    marker,
                    _canonical_json(
                        {
                            "owner": owner,
                            "retired_count": retired_count,
                            "total_retired_count": (
                                previous_total + retired_count
                            ),
                            "last_swept_at": _utc_now(),
                        }
                    ),
                ),
            )
        return retired_count

    def coverage_summary_counts(self) -> dict[str, Any]:
        """Read complete coverage counts without decoding private rows."""

        with self.connection() as connection:
            aggregate = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(terminal), 0), "
                "COALESCE(SUM(ui_ready), 0), COALESCE(SUM(blocked), 0) "
                "FROM coverage_stage_index WHERE active=1"
            ).fetchone()
            next_rows = connection.execute(
                "SELECT next_stage, COUNT(*) FROM coverage_stage_index "
                "WHERE active=1 AND next_stage!='' "
                "GROUP BY next_stage ORDER BY next_stage"
            ).fetchall()
        registered = int(aggregate[0])
        terminal = int(aggregate[1])
        return {
            "registered_object_count": registered,
            "terminal_object_count": terminal,
            "ui_ready_object_count": int(aggregate[2]),
            "blocked_object_count": int(aggregate[3]),
            "pending_object_count": registered - terminal,
            "next_stage_counts": {
                str(stage_id): int(count)
                for stage_id, count in next_rows
            },
        }

    def coverage_audit_index_status(self) -> dict[str, Any]:
        """Report whether every current row has its current first-gap projection."""

        with self.connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*), "
                "COALESCE(SUM(CASE WHEN coverage.object_id IS NOT NULL "
                "AND coverage.revision=current.revision "
                "AND coverage.first_gap_indexed_revision=current.revision "
                "THEN 1 ELSE 0 END), 0), "
                "COALESCE(SUM(CASE WHEN coverage.active=1 "
                "THEN 1 ELSE 0 END), 0) "
                "FROM current_objects current "
                "LEFT JOIN coverage_stage_index coverage "
                "ON coverage.object_id=current.object_id "
                "WHERE current.owner='object_coverage'"
            ).fetchone()
            state = connection.execute(
                "SELECT generation, last_object_id, updated_at "
                "FROM coverage_audit_index_state WHERE singleton_id=1"
            ).fetchone()
        total = int(row[0])
        indexed = int(row[1])
        return {
            "status": "current" if indexed == total else "partial",
            "active_object_count": int(row[2]),
            "registered_object_count": total,
            "indexed_object_count": indexed,
            "remaining_object_count": max(0, total - indexed),
            "generation": int(state[0]) if state is not None else 0,
            "last_object_id": str(state[1]) if state is not None else "",
            "updated_at": str(state[2]) if state is not None else "",
        }

    def materialized_index_status(self, index_id: str) -> dict[str, Any]:
        """Return the explicit migration status for one rebuildable index."""

        owner = _MATERIALIZED_INDEX_OWNERS.get(str(index_id))
        if owner is None:
            raise ValueError("materialized index id is invalid")
        with self.connection() as connection:
            marker = connection.execute(
                "SELECT value FROM store_metadata WHERE key=?",
                (index_id,),
            ).fetchone()
            owner_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM current_objects WHERE owner=?",
                    (owner,),
                ).fetchone()[0]
            )
        return {
            "index_id": str(index_id),
            "owner": owner,
            "status": (
                "current"
                if marker is not None and str(marker[0]) == "complete"
                else "partial"
            ),
            "current_owner_count": owner_count,
        }

    def rebase_materialized_index_page(
        self,
        *,
        index_id: str,
        phase: str = "current",
        after_object_id: str = "",
        limit: int = 500,
    ) -> dict[str, Any]:
        """Rebuild one startup projection through bounded resumable pages."""

        owner = _MATERIALIZED_INDEX_OWNERS.get(str(index_id))
        if owner is None:
            raise ValueError("materialized index id is invalid")
        if phase not in {"current", "stale"}:
            raise ValueError("materialized index rebase phase is invalid")
        if limit < 1 or limit > 500:
            raise ValueError("materialized index rebase limit is invalid")

        key_column_by_index = {
            "matter_context_signal_index:v1": (
                "matter_context_signal_index",
                "matter_id",
            ),
            "coverage_matter_index:v1": (
                "coverage_matter_index",
                "object_id",
            ),
            "inventory_occurrence_current:v1": (
                "inventory_occurrence_current",
                "scope_id",
            ),
            "matter_hierarchy_index:v1": (
                "matter_hierarchy_index",
                "edge_id",
            ),
            "matter_hierarchy_stage_index:v1": (
                "matter_hierarchy_stage_index",
                "matter_id",
            ),
            "matter_work_item_index:v1": (
                "matter_work_item_index",
                "item_id",
            ),
        }
        table_name, key_column = key_column_by_index[str(index_id)]
        selected: list[tuple[Any, ...]]
        has_more = False
        rebuilt = 0
        cleared = 0

        with self.connection() as connection:
            if phase == "current":
                if not after_object_id:
                    connection.execute(
                        "INSERT INTO store_metadata(key, value) "
                        "VALUES (?, 'partial') "
                        "ON CONFLICT(key) DO UPDATE SET value='partial'",
                        (index_id,),
                    )
                rows = connection.execute(
                    "SELECT current.object_id, current.revision, snapshot.payload "
                    "FROM current_objects current "
                    "JOIN snapshots snapshot ON snapshot.owner=current.owner "
                    "AND snapshot.object_id=current.object_id "
                    "AND snapshot.revision=current.revision "
                    "WHERE current.owner=? AND current.object_id>? "
                    "ORDER BY current.object_id LIMIT ?",
                    (owner, after_object_id, limit + 1),
                ).fetchall()
                has_more = len(rows) > limit
                selected = rows[:limit]
                for object_id, revision, payload in selected:
                    refresh_args = {
                        "revision": int(revision),
                        "encoded_payload": str(payload),
                    }
                    if index_id == "matter_context_signal_index:v1":
                        self._refresh_matter_context_signal_index(
                            connection,
                            matter_id=str(object_id),
                            **refresh_args,
                        )
                    elif index_id == "coverage_matter_index:v1":
                        self._refresh_coverage_matter_index(
                            connection,
                            object_id=str(object_id),
                            **refresh_args,
                        )
                    elif index_id == "inventory_occurrence_current:v1":
                        self._refresh_inventory_occurrence_index(
                            connection,
                            scope_id=str(object_id),
                            **refresh_args,
                        )
                    elif index_id == "matter_hierarchy_index:v1":
                        self._refresh_hierarchy_index(
                            connection,
                            edge_id=str(object_id),
                            **refresh_args,
                        )
                    elif index_id == "matter_hierarchy_stage_index:v1":
                        self._refresh_hierarchy_stage_index(
                            connection,
                            matter_id=str(object_id),
                            **refresh_args,
                        )
                    else:
                        self._refresh_work_item_index(
                            connection,
                            item_id=str(object_id),
                            **refresh_args,
                        )
                rebuilt = len(selected)
            else:
                rows = connection.execute(
                    f"SELECT DISTINCT projection.{key_column} "
                    f"FROM {table_name} projection "
                    "LEFT JOIN current_objects current "
                    "ON current.owner=? "
                    f"AND current.object_id=projection.{key_column} "
                    f"WHERE projection.{key_column}>? "
                    "AND current.object_id IS NULL "
                    f"ORDER BY projection.{key_column} LIMIT ?",
                    (owner, after_object_id, limit + 1),
                ).fetchall()
                has_more = len(rows) > limit
                selected = rows[:limit]
                if selected:
                    connection.executemany(
                        f"DELETE FROM {table_name} WHERE {key_column}=?",
                        ((str(row[0]),) for row in selected),
                    )
                cleared = len(selected)
                if not has_more:
                    connection.execute(
                        "INSERT INTO store_metadata(key, value) "
                        "VALUES (?, 'complete') "
                        "ON CONFLICT(key) DO UPDATE SET value='complete'",
                        (index_id,),
                    )

        if phase == "current" and not has_more:
            next_phase = "stale"
            next_cursor = ""
            more_work = True
        else:
            next_phase = phase
            next_cursor = (
                str(selected[-1][0])
                if selected and has_more
                else ""
            )
            more_work = has_more
        return {
            "index_id": str(index_id),
            "owner": owner,
            "phase": phase,
            "scanned_object_count": len(selected),
            "rebuilt_object_count": rebuilt,
            "cleared_object_count": cleared,
            "next_phase": next_phase,
            "next_cursor": next_cursor,
            "has_more": more_work,
            "status": (
                "current"
                if phase == "stale" and not has_more
                else "partial"
            ),
        }

    def rebase_coverage_audit_index_page(
        self,
        *,
        after_object_id: str = "",
        limit: int = 500,
        calculate_status: bool = True,
    ) -> dict[str, Any]:
        """Materialize one bounded legacy first-gap/status page explicitly."""

        if limit < 1 or limit > 500:
            raise ValueError("coverage audit rebase limit is invalid")
        with self.connection() as connection:
            if not after_object_id:
                connection.execute(
                    "INSERT INTO store_metadata(key, value) "
                    "VALUES ('coverage_stage_index:v2', 'partial') "
                    "ON CONFLICT(key) DO UPDATE SET value='partial'"
                )
            rows = connection.execute(
                "SELECT current.object_id, current.revision, snapshot.payload "
                "FROM current_objects current "
                "JOIN snapshots snapshot ON snapshot.owner=current.owner "
                "AND snapshot.object_id=current.object_id "
                "AND snapshot.revision=current.revision "
                "LEFT JOIN coverage_stage_index coverage "
                "ON coverage.object_id=current.object_id "
                "WHERE current.owner='object_coverage' "
                "AND current.object_id>? "
                "AND (coverage.object_id IS NULL OR "
                "coverage.first_gap_indexed_revision<>current.revision) "
                "ORDER BY current.object_id LIMIT ?",
                (after_object_id, limit + 1),
            ).fetchall()
            selected = rows[:limit]
            for object_id, revision, payload in selected:
                self._refresh_coverage_stage_index(
                    connection,
                    object_id=str(object_id),
                    revision=int(revision),
                    encoded_payload=str(payload),
                )
        has_more = len(rows) > limit
        status = (
            self.coverage_audit_index_status()
            if calculate_status or not has_more
            else None
        )
        if status is not None and status["status"] == "current":
            with self.connection() as connection:
                connection.execute(
                    "INSERT INTO store_metadata(key, value) "
                    "VALUES ('coverage_stage_index:v2', 'complete') "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
                )
        next_cursor = (
            str(selected[-1][0])
            if selected and has_more
            else ""
        )
        return {
            "scanned_object_count": len(selected),
            "indexed_object_count": len(selected),
            "remaining_object_count": (
                int(status["remaining_object_count"])
                if status is not None
                else None
            ),
            "remaining_count_status": (
                "exact" if status is not None else "deferred_until_terminal_page"
            ),
            "next_cursor": next_cursor,
            "has_more": has_more,
            "status": (
                "current"
                if status is not None and status["status"] == "current"
                else "partial"
            ),
        }

    def record_coverage_surface_status(
        self,
        *,
        surface_id: str,
        status: str,
        input_fingerprint: str,
        subject_id: str = "system:coverage",
        subject_kind: str = "system",
        failure_class: str = "",
    ) -> None:
        """Persist one small owner-produced surface-currentness marker."""

        normalized_surface = str(surface_id)
        if normalized_surface not in _COVERAGE_SURFACE_OWNERS:
            raise ValueError("coverage surface id is invalid")
        if status not in {
            "current",
            "pending",
            "stale",
            "blocked",
            "not_applicable",
            "no_finding",
        }:
            raise ValueError("coverage surface status is invalid")
        if not subject_id or not subject_kind or not input_fingerprint:
            raise ValueError("coverage surface identity is incomplete")
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO coverage_surface_index"
                "(surface_id, subject_id, subject_kind, status, owner_id, "
                "failure_class, input_fingerprint, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(surface_id, subject_id) DO UPDATE SET "
                "subject_kind=excluded.subject_kind, status=excluded.status, "
                "owner_id=excluded.owner_id, "
                "failure_class=excluded.failure_class, "
                "input_fingerprint=excluded.input_fingerprint, "
                "updated_at=excluded.updated_at",
                (
                    normalized_surface,
                    str(subject_id),
                    str(subject_kind),
                    str(status),
                    _COVERAGE_SURFACE_OWNERS[normalized_surface],
                    str(failure_class),
                    str(input_fingerprint),
                    _utc_now(),
                ),
            )

    def _global_coverage_surface_rows(self) -> tuple[dict[str, Any], ...]:
        inventory = self.materialized_index_status(
            "inventory_occurrence_current:v1"
        )
        source_groups = self.source_group_index_status()
        with self.connection() as connection:
            stored = {
                str(row[0]): {
                    "status": str(row[1]),
                    "owner_id": str(row[2]),
                    "failure_class": str(row[3]),
                    "input_fingerprint": str(row[4]),
                    "updated_at": str(row[5]),
                }
                for row in connection.execute(
                    "SELECT surface_id, status, owner_id, failure_class, "
                    "input_fingerprint, updated_at "
                    "FROM coverage_surface_index "
                    "WHERE subject_id='system:coverage'"
                )
            }

        def row(
            surface_id: str,
            status: str,
            failure_class: str,
            *,
            input_fingerprint: str,
            updated_at: str = "",
        ) -> dict[str, Any]:
            return {
                "surface_id": surface_id,
                "subject_id": "system:coverage",
                "subject_kind": "system",
                "status": status,
                "owner_id": _COVERAGE_SURFACE_OWNERS[surface_id],
                "failure_class": failure_class,
                "input_fingerprint": input_fingerprint,
                "freshness": (
                    "current"
                    if status in _CURRENT_COVERAGE_SURFACE_STATUSES
                    else status
                ),
                "ui_ready": False,
                "updated_at": updated_at,
            }

        inventory_status = str(inventory["status"])
        source_group_status = str(source_groups["status"])
        rows = [
            row(
                "inventory_freshness",
                "current" if inventory_status == "current" else "stale",
                "" if inventory_status == "current" else "inventory_index_not_current",
                input_fingerprint=(
                    f"inventory-index:{inventory_status}:"
                    f"{inventory['current_owner_count']}"
                ),
            ),
            row(
                "source_group_projection",
                "current" if source_group_status == "current" else "stale",
                ""
                if source_group_status == "current"
                else "source_group_index_not_current",
                input_fingerprint=(
                    f"source-group-index:{source_group_status}:"
                    f"{source_groups['indexed_occurrence_count']}:"
                    f"{source_groups['eligible_occurrence_count']}"
                ),
            ),
        ]
        for surface_id in ("raw_cleanup", "staging_cleanup"):
            marker = stored.get(surface_id)
            if marker is None:
                rows.append(
                    row(
                        surface_id,
                        "missing",
                        f"{surface_id}_proof_missing",
                        input_fingerprint="missing",
                    )
                )
                continue
            rows.append(
                row(
                    surface_id,
                    str(marker["status"]),
                    str(marker["failure_class"]),
                    input_fingerprint=str(marker["input_fingerprint"]),
                    updated_at=str(marker["updated_at"]),
                )
            )
        return tuple(rows)

    @staticmethod
    def _coverage_surface_where(
        *,
        surface_id: str,
        status: str,
        owner_id: str,
        failure_class: str,
        freshness: str,
        ui_ready: bool | None,
    ) -> tuple[str, tuple[Any, ...]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        for column, value in (
            ("surface_id", surface_id),
            ("status", status),
            ("owner_id", owner_id),
            ("failure_class", failure_class),
            ("freshness", freshness),
        ):
            if value:
                clauses.append(f"resolved.{column}=?")
                parameters.append(value)
        if ui_ready is not None:
            clauses.append("resolved.ui_ready=?")
            parameters.append(1 if ui_ready else 0)
        return (
            ("WHERE " + " AND ".join(clauses) + " ") if clauses else "",
            tuple(parameters),
        )

    def coverage_surface_audit_page(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        surface_id: str = "",
        status: str = "",
        owner_id: str = "",
        failure_class: str = "",
        freshness: str = "",
        ui_ready: bool | None = None,
    ) -> dict[str, Any]:
        """Return one bounded indexed audit page for non-duplicated surfaces."""

        if offset < 0 or limit < 1 or limit > 200:
            raise ValueError("coverage surface page bounds are invalid")
        if surface_id and surface_id not in _COVERAGE_SURFACE_OWNERS:
            raise ValueError("coverage surface id is invalid")
        if status and status not in {
            "current",
            "pending",
            "stale",
            "blocked",
            "not_applicable",
            "no_finding",
            "missing",
        }:
            raise ValueError("coverage surface status is invalid")
        if freshness and freshness not in {
            "current",
            "pending",
            "stale",
            "blocked",
            "missing",
        }:
            raise ValueError("coverage surface freshness is invalid")

        global_rows = self._global_coverage_surface_rows()

        def matches(item: Mapping[str, Any]) -> bool:
            return (
                (not surface_id or item["surface_id"] == surface_id)
                and (not status or item["status"] == status)
                and (not owner_id or item["owner_id"] == owner_id)
                and (
                    not failure_class
                    or item["failure_class"] == failure_class
                )
                and (not freshness or item["freshness"] == freshness)
                and (
                    ui_ready is None
                    or bool(item["ui_ready"]) is bool(ui_ready)
                )
            )

        matching_globals = tuple(item for item in global_rows if matches(item))
        source_groups_current = next(
            item["status"] == "current"
            for item in global_rows
            if item["surface_id"] == "source_group_projection"
        )
        cte = (
            "WITH admitted_roots AS ("
            "SELECT coverage.object_id AS matter_id, coverage.ui_ready "
            "FROM coverage_stage_index coverage "
            "JOIN current_objects admission_current "
            "ON admission_current.owner='admission_decision' "
            "AND admission_current.object_id=coverage.object_id "
            "JOIN snapshots admission "
            "ON admission.owner=admission_current.owner "
            "AND admission.object_id=admission_current.object_id "
            "AND admission.revision=admission_current.revision "
            "WHERE coverage.provider='matters' AND coverage.active=1 "
            "AND coverage.object_type='root_matter' "
            "AND json_extract(admission.payload, '$.status')='admitted'"
            "), root_state AS ("
            "SELECT roots.matter_id, roots.ui_ready, "
            "graph.revision AS graph_revision, graph_snapshot.payload AS graph_payload, "
            "world.revision AS world_revision, world_snapshot.payload AS world_payload "
            "FROM admitted_roots roots "
            "LEFT JOIN current_objects graph "
            "ON graph.owner='situation_graph_projection' "
            "AND graph.object_id=roots.matter_id "
            "LEFT JOIN snapshots graph_snapshot "
            "ON graph_snapshot.owner=graph.owner "
            "AND graph_snapshot.object_id=graph.object_id "
            "AND graph_snapshot.revision=graph.revision "
            "LEFT JOIN current_objects world "
            "ON world.owner='world_model_advisory' "
            "AND world.object_id=roots.matter_id "
            "LEFT JOIN snapshots world_snapshot "
            "ON world_snapshot.owner=world.owner "
            "AND world_snapshot.object_id=world.object_id "
            "AND world_snapshot.revision=world.revision"
            "), surface_def(surface_id, rank) AS (VALUES "
            "('situation_graph', 0), ('node_quick_view', 1), "
            "('world_model', 2)), resolved AS ("
            "SELECT surface.surface_id, roots.matter_id AS subject_id, "
            "'root_matter' AS subject_kind, "
            "CASE surface.surface_id "
            "WHEN 'situation_graph' THEN "
            "CASE WHEN roots.graph_revision IS NULL THEN 'pending' ELSE 'current' END "
            "WHEN 'node_quick_view' THEN CASE "
            "WHEN roots.graph_revision IS NULL THEN 'pending' "
            "WHEN roots.ui_ready<>1 OR ?=0 THEN 'stale' ELSE 'current' END "
            "ELSE CASE WHEN roots.world_revision IS NULL THEN 'pending' "
            "WHEN roots.graph_revision IS NULL "
            "OR COALESCE(json_extract(roots.world_payload, '$.graph_fingerprint'),'') "
            "<>COALESCE(json_extract(roots.graph_payload, '$.input_fingerprint'),'') "
            "OR COALESCE(json_extract(roots.world_payload, '$.expires_at'),'')<=? "
            "THEN 'stale' ELSE 'current' END END AS status, "
            "CASE surface.surface_id "
            "WHEN 'situation_graph' THEN 'C6_matter_admission' "
            "WHEN 'node_quick_view' THEN 'C12_projection_bilingual_ui' "
            "ELSE 'C11_guard_prediction' END AS owner_id, "
            "CASE surface.surface_id "
            "WHEN 'situation_graph' THEN CASE WHEN roots.graph_revision IS NULL "
            "THEN 'situation_graph_missing' ELSE '' END "
            "WHEN 'node_quick_view' THEN CASE "
            "WHEN roots.graph_revision IS NULL THEN 'situation_graph_missing' "
            "WHEN roots.ui_ready<>1 THEN 'matter_ui_projection_not_current' "
            "WHEN ?=0 THEN 'source_group_index_not_current' ELSE '' END "
            "ELSE CASE WHEN roots.world_revision IS NULL THEN 'world_model_missing' "
            "WHEN roots.graph_revision IS NULL THEN 'situation_graph_missing' "
            "WHEN COALESCE(json_extract(roots.world_payload, '$.graph_fingerprint'),'') "
            "<>COALESCE(json_extract(roots.graph_payload, '$.input_fingerprint'),'') "
            "THEN 'world_model_graph_fingerprint_stale' "
            "WHEN COALESCE(json_extract(roots.world_payload, '$.expires_at'),'')<=? "
            "THEN 'world_model_expired' ELSE '' END END AS failure_class, "
            "CASE surface.surface_id "
            "WHEN 'situation_graph' THEN COALESCE(json_extract(roots.graph_payload, '$.input_fingerprint'),'missing') "
            "WHEN 'node_quick_view' THEN COALESCE(json_extract(roots.graph_payload, '$.input_fingerprint'),'missing') "
            "ELSE COALESCE(json_extract(roots.world_payload, '$.graph_fingerprint'),'missing') END "
            "AS input_fingerprint, "
            "CASE surface.surface_id "
            "WHEN 'situation_graph' THEN CASE WHEN roots.graph_revision IS NULL THEN 'pending' ELSE 'current' END "
            "WHEN 'node_quick_view' THEN CASE WHEN roots.graph_revision IS NULL THEN 'pending' "
            "WHEN roots.ui_ready<>1 OR ?=0 THEN 'stale' ELSE 'current' END "
            "ELSE CASE WHEN roots.world_revision IS NULL THEN 'pending' "
            "WHEN roots.graph_revision IS NULL "
            "OR COALESCE(json_extract(roots.world_payload, '$.graph_fingerprint'),'') "
            "<>COALESCE(json_extract(roots.graph_payload, '$.input_fingerprint'),'') "
            "OR COALESCE(json_extract(roots.world_payload, '$.expires_at'),'')<=? "
            "THEN 'stale' ELSE 'current' END END AS freshness, "
            "CASE WHEN surface.surface_id='node_quick_view' "
            "AND roots.graph_revision IS NOT NULL AND roots.ui_ready=1 AND ?=1 "
            "THEN 1 WHEN surface.surface_id<>'node_quick_view' "
            "AND ((surface.surface_id='situation_graph' AND roots.graph_revision IS NOT NULL) "
            "OR (surface.surface_id='world_model' AND roots.world_revision IS NOT NULL "
            "AND roots.graph_revision IS NOT NULL "
            "AND COALESCE(json_extract(roots.world_payload, '$.graph_fingerprint'),'') "
            "=COALESCE(json_extract(roots.graph_payload, '$.input_fingerprint'),'') "
            "AND COALESCE(json_extract(roots.world_payload, '$.expires_at'),'')>?)) "
            "THEN 1 ELSE 0 END AS ui_ready, '' AS updated_at, surface.rank "
            "FROM root_state roots CROSS JOIN surface_def surface) "
        )
        now = _utc_now()
        cte_parameters = (
            1 if source_groups_current else 0,
            now,
            1 if source_groups_current else 0,
            now,
            1 if source_groups_current else 0,
            now,
            1 if source_groups_current else 0,
            now,
        )
        where, filter_parameters = self._coverage_surface_where(
            surface_id=surface_id,
            status=status,
            owner_id=owner_id,
            failure_class=failure_class,
            freshness=freshness,
            ui_ready=ui_ready,
        )
        with self.connection() as connection:
            aggregate_rows = connection.execute(
                cte
                + "SELECT status, COUNT(*) FROM resolved "
                + where
                + "GROUP BY status",
                (*cte_parameters, *filter_parameters),
            ).fetchall()
            database_matching = sum(int(item[1]) for item in aggregate_rows)
            page_offset = max(0, offset - len(matching_globals))
            global_page = (
                matching_globals[offset : offset + limit]
                if offset < len(matching_globals)
                else ()
            )
            remaining_limit = limit - len(global_page)
            matter_page = ()
            if remaining_limit > 0:
                matter_page = tuple(
                    {
                        "surface_id": str(item[0]),
                        "subject_id": str(item[1]),
                        "subject_kind": str(item[2]),
                        "status": str(item[3]),
                        "owner_id": str(item[4]),
                        "failure_class": str(item[5]),
                        "input_fingerprint": str(item[6]),
                        "freshness": str(item[7]),
                        "ui_ready": bool(item[8]),
                        "updated_at": str(item[9]),
                    }
                    for item in connection.execute(
                        cte
                        + "SELECT surface_id, subject_id, subject_kind, status, "
                        "owner_id, failure_class, input_fingerprint, freshness, "
                        "ui_ready, updated_at FROM resolved "
                        + where
                        + "ORDER BY rank, subject_id LIMIT ? OFFSET ?",
                        (
                            *cte_parameters,
                            *filter_parameters,
                            remaining_limit,
                            page_offset,
                        ),
                    ).fetchall()
                )
        status_counts: dict[str, int] = {}
        for item in matching_globals:
            normalized = str(item["status"])
            status_counts[normalized] = status_counts.get(normalized, 0) + 1
        for normalized, count in aggregate_rows:
            key = str(normalized)
            status_counts[key] = status_counts.get(key, 0) + int(count)
        total_matching = len(matching_globals) + database_matching
        current_count = sum(
            count
            for key, count in status_counts.items()
            if key in _CURRENT_COVERAGE_SURFACE_STATUSES
        )
        return {
            "surface_order": (
                *_GLOBAL_COVERAGE_SURFACES,
                *_ROOT_MATTER_COVERAGE_SURFACES,
            ),
            "total_surface_count": total_matching,
            "current_surface_count": current_count,
            "gap_surface_count": total_matching - current_count,
            "status_counts": status_counts,
            "rows": (*global_page, *matter_page),
            "offset": offset,
            "limit": limit,
            "total_matching": total_matching,
        }

    def coverage_surface_contract_status(self) -> dict[str, Any]:
        page = self.coverage_surface_audit_page(limit=1)
        return {
            "status": (
                "current"
                if int(page["total_surface_count"])
                and not int(page["gap_surface_count"])
                else "partial"
            ),
            "required_surface_count": int(page["total_surface_count"]),
            "current_surface_count": int(page["current_surface_count"]),
            "gap_surface_count": int(page["gap_surface_count"]),
            "status_counts": dict(page["status_counts"]),
        }

    def coverage_contract_status(self) -> dict[str, Any]:
        """Evaluate the strict no-false-green coverage contract from indexes."""

        audit_index = self.coverage_audit_index_status()
        source_groups = self.source_group_index_status()
        surfaces = self.coverage_surface_contract_status()
        with self.connection() as connection:
            aggregate = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(terminal), 0), "
                "COALESCE(SUM(blocked), 0), "
                "COALESCE(SUM(CASE WHEN disposition IN ('tracked','blocked') "
                "OR provider='matters' THEN 1 ELSE 0 END), 0) "
                "FROM coverage_stage_index WHERE active=1"
            ).fetchone()
            inventory_row = connection.execute(
                "WITH inventory AS MATERIALIZED ("
                "SELECT object_id, provider "
                "FROM inventory_occurrence_current "
                "GROUP BY object_id, provider"
                "), source_coverage AS MATERIALIZED ("
                "SELECT object_id, provider FROM coverage_stage_index "
                "WHERE active=1 AND provider<>'matters'"
                "), missing AS ("
                "SELECT object_id, provider FROM inventory "
                "EXCEPT SELECT object_id, provider FROM source_coverage"
                "), orphaned AS ("
                "SELECT object_id, provider FROM source_coverage "
                "EXCEPT SELECT object_id, provider FROM inventory"
                ") "
                "SELECT (SELECT COUNT(*) FROM inventory), "
                "(SELECT COUNT(*) FROM missing), "
                "(SELECT COUNT(*) FROM orphaned)"
            ).fetchone()
            matter_row = connection.execute(
                "WITH admitted AS ("
                "SELECT admission_current.object_id AS matter_id "
                "FROM current_objects admission_current "
                "JOIN snapshots admission "
                "ON admission.owner=admission_current.owner "
                "AND admission.object_id=admission_current.object_id "
                "AND admission.revision=admission_current.revision "
                "WHERE admission_current.owner='admission_decision' "
                "AND json_extract(admission.payload, '$.status')='admitted' "
                "AND CAST(json_extract(admission.payload, "
                "'$.matter.matter_id') AS TEXT)="
                "admission_current.object_id "
                "AND COALESCE(json_extract(admission.payload, "
                "'$.matter.admitted'), 1)=1"
                ") "
                "SELECT COUNT(*), "
                "COALESCE(SUM(CASE WHEN coverage.object_id IS NOT NULL "
                "THEN 1 ELSE 0 END), 0), "
                "COALESCE(SUM(CASE WHEN coverage.ui_ready=1 "
                "AND coverage.first_gap_indexed_revision=coverage.revision "
                "AND hierarchy.terminal=1 "
                "AND hierarchy.ui_reachable=1 "
                "AND hierarchy.blocked=0 "
                "THEN 1 ELSE 0 END), 0) "
                "FROM admitted "
                "LEFT JOIN coverage_stage_index coverage "
                "ON coverage.object_id=admitted.matter_id "
                "AND coverage.provider='matters' AND coverage.active=1 "
                "LEFT JOIN matter_hierarchy_stage_index hierarchy "
                "ON hierarchy.matter_id=admitted.matter_id"
            ).fetchone()
        registered = int(aggregate[0])
        terminal = int(aggregate[1])
        blockers = int(aggregate[2])
        eligible_objects = int(aggregate[3])
        inventory_objects = int(inventory_row[0])
        missing_registration = int(inventory_row[1])
        orphaned_coverage = int(inventory_row[2])
        admitted_matters = int(matter_row[0])
        registered_matters = int(matter_row[1])
        ready_matters = int(matter_row[2])
        reasons: list[str] = []
        audit_remaining = int(audit_index["remaining_object_count"])
        if not registered and not audit_remaining:
            reasons.append("coverage_empty")
        if registered and not eligible_objects and not admitted_matters:
            reasons.append("terminal_hard_exclusion_only")
        if audit_index["status"] != "current":
            reasons.append("coverage_audit_index_stale")
        if missing_registration:
            reasons.append("inventory_registration_missing")
        if orphaned_coverage:
            reasons.append("source_coverage_orphaned")
        if terminal != registered:
            reasons.append("object_stage_pending")
        if blockers:
            reasons.append("coverage_blocked")
        if source_groups["status"] != "current":
            reasons.append("source_group_reconciliation_pending")
        if registered_matters != admitted_matters:
            reasons.append("admitted_matter_coverage_missing")
        if ready_matters != admitted_matters:
            reasons.append(
                "admitted_matter_semantic_hierarchy_ui_not_current"
            )
        if surfaces["status"] != "current":
            reasons.append("coverage_surface_not_current")
        inventory_status = (
            "current"
            if not missing_registration and not orphaned_coverage
            else "partial"
        )
        matter_status = (
            "current"
            if registered_matters == admitted_matters
            and ready_matters == admitted_matters
            else "partial"
        )
        complete = bool(registered) and not reasons
        return {
            "contract_version": 2,
            "status": (
                "complete"
                if complete
                else (
                    "empty"
                    if not registered and not audit_remaining
                    else "partial"
                )
            ),
            "inventory_status": inventory_status,
            "inventory_object_count": inventory_objects,
            "missing_registration_count": missing_registration,
            "orphaned_source_coverage_count": orphaned_coverage,
            "audit_index_status": str(audit_index["status"]),
            "audit_indexed_object_count": int(
                audit_index["indexed_object_count"]
            ),
            "audit_unindexed_object_count": int(
                audit_index["remaining_object_count"]
            ),
            "source_group_status": str(source_groups["status"]),
            "source_group_eligible_occurrence_count": int(
                source_groups["eligible_occurrence_count"]
            ),
            "source_group_indexed_occurrence_count": int(
                source_groups["indexed_occurrence_count"]
            ),
            "source_group_remaining_occurrence_count": int(
                source_groups["remaining_occurrence_count"]
            ),
            "source_group_stale_occurrence_count": int(
                source_groups["stale_occurrence_count"]
            ),
            "surface_status": str(surfaces["status"]),
            "required_surface_count": int(
                surfaces["required_surface_count"]
            ),
            "current_surface_count": int(
                surfaces["current_surface_count"]
            ),
            "gap_surface_count": int(surfaces["gap_surface_count"]),
            "surface_status_counts": dict(surfaces["status_counts"]),
            "admitted_matter_count": admitted_matters,
            "registered_matter_count": registered_matters,
            "ready_matter_count": ready_matters,
            "matter_consistency_status": matter_status,
            "blocker_count": blockers,
            "eligible_object_count": eligible_objects,
            "reasons": tuple(reasons),
        }

    def coverage_next_work(
        self,
        *,
        limit: int,
    ) -> tuple[tuple[str, str], ...]:
        """Return a stable bounded work queue from the coverage index."""

        if limit < 1 or limit > 1000:
            raise ValueError("coverage work limit is invalid")
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT object_id, next_stage FROM coverage_stage_index "
                "WHERE active=1 AND next_stage!='' "
                "ORDER BY next_stage, object_id LIMIT ?",
                (limit,),
            ).fetchall()
        return tuple((str(object_id), str(stage_id)) for object_id, stage_id in rows)

    def registered_filesystem_source_page(
        self,
        *,
        limit: int,
    ) -> tuple[tuple[str, ...], int]:
        """Return one stable page of registered filesystem content work.

        The materialized coverage index is the work authority here.  Callers
        receive opaque occurrence ids only; private locators stay in the
        inventory snapshot that already owns them.
        """

        if limit < 1 or limit > 500:
            raise ValueError("registered filesystem batch limit is invalid")
        where = (
            "coverage.active=1 AND coverage.provider='filesystem' "
            "AND coverage.disposition='tracked' "
            "AND coverage.next_stage='source_version' "
            "AND selection.status='current' "
            "AND selection.mode IN ('sampled', 'bounded')"
        )
        with self.connection() as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM coverage_stage_index coverage "
                    "JOIN content_selection_index selection "
                    "ON selection.object_id=coverage.object_id WHERE " + where
                ).fetchone()[0]
            )
            rows = connection.execute(
                "SELECT coverage.object_id FROM coverage_stage_index coverage "
                "JOIN content_selection_index selection "
                "ON selection.object_id=coverage.object_id WHERE "
                + where
                + " ORDER BY selection.priority DESC, selection.neighborhood_id, "
                "coverage.object_id LIMIT ?",
                (limit,),
            ).fetchall()
        return tuple(str(row[0]) for row in rows), total

    def content_selection_page(
        self,
        *,
        offset: int,
        limit: int,
    ) -> tuple[tuple[dict[str, Any], ...], int]:
        """Return an opaque, bounded audit page for content planning."""

        if offset < 0 or limit < 1 or limit > 200:
            raise ValueError("content selection page bounds are invalid")
        with self.connection() as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM content_selection_index"
                ).fetchone()[0]
            )
            rows = connection.execute(
                "SELECT object_id, mode, status, priority, revision "
                "FROM content_selection_index "
                "ORDER BY priority DESC, neighborhood_id, object_id "
                "LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return (
            tuple(
                {
                    "object_id": str(row[0]),
                    "mode": str(row[1]),
                    "status": str(row[2]),
                    "priority": int(row[3]),
                    "revision": int(row[4]),
                }
                for row in rows
            ),
            total,
        )

    def content_selection_rebase_page(
        self,
        *,
        after_object_id: str,
        limit: int,
    ) -> tuple[tuple[dict[str, Any], ...], bool]:
        """Read one bounded private inventory page for explicit replanning.

        This deliberately does not run during store/service construction.  The
        caller supplies the opaque checkpoint and owns any resulting plan
        writes.
        """

        if limit < 1 or limit > 500:
            raise ValueError("content selection rebase limit is invalid")
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT i.object_id, i.inventory_revision, i.disposition, "
                "i.occurrence_payload FROM inventory_occurrence_current i "
                "WHERE i.object_id>? AND i.disposition='tracked' "
                "AND i.scope_id=("
                "SELECT selected.scope_id "
                "FROM inventory_occurrence_current selected "
                "WHERE selected.object_id=i.object_id "
                "AND selected.disposition='tracked' "
                "ORDER BY selected.inventory_revision DESC, "
                "selected.scope_id LIMIT 1"
                ") ORDER BY i.object_id LIMIT ?",
                (after_object_id, limit + 1),
            ).fetchall()
        has_more = len(rows) > limit
        return (
            tuple(
                {
                    "object_id": str(row[0]),
                    "inventory_revision": int(row[1]),
                    "disposition": str(row[2]),
                    "occurrence": json.loads(str(row[3])),
                }
                for row in rows[:limit]
            ),
            has_more,
        )

    def replace_source_group_scope(
        self,
        *,
        scope_id: str,
        inventory_revision: int,
        rows: Iterable[dict[str, Any]],
    ) -> int:
        """Replace one scope's rebuildable SourceGroup membership atomically."""

        normalized_rows = tuple(dict(row) for row in rows)
        expected_ids_by_object: dict[str, set[str]] = {}
        expected_rows_by_object: dict[str, set[str]] = {}
        for row in normalized_rows:
            object_id = str(row["inventory_occurrence_id"])
            expected_ids_by_object.setdefault(object_id, set()).add(
                str(row["group_id"])
            )
            expected_rows_by_object.setdefault(object_id, set()).add(
                _source_group_projection_identity(row)
            )
        expected_by_object = {
            object_id: _canonical_json(sorted(group_ids))
            for object_id, group_ids in expected_ids_by_object.items()
        }
        with self.connection() as connection:
            current = connection.execute(
                "SELECT revision FROM current_objects "
                "WHERE owner='inventory_snapshot' AND object_id=?",
                (scope_id,),
            ).fetchone()
            if current is None or int(current[0]) != inventory_revision:
                raise ValueError("source group inventory owner is not current")
            connection.execute(
                "DELETE FROM source_group_member_index WHERE scope_id=?",
                (scope_id,),
            )
            connection.execute(
                "DELETE FROM source_group_projection_state WHERE scope_id=?",
                (scope_id,),
            )
            connection.executemany(
                "INSERT INTO source_group_member_index"
                "(scope_id, inventory_revision, object_id, occurrence_id, "
                "group_id, parent_group_id, child_group_id, title, depth, "
                "provider, object_type, member_title, availability, "
                "direct_member) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    (
                        scope_id,
                        inventory_revision,
                        str(row["inventory_occurrence_id"]),
                        str(row["occurrence_id"]),
                        str(row["group_id"]),
                        str(row.get("parent_group_id", "")),
                        str(row.get("child_group_id", "")),
                        str(row["title"]),
                        int(row["depth"]),
                        str(row["provider"]),
                        str(row["object_type"]),
                        str(row["member_title"]),
                        str(row["availability"]),
                        int(bool(row["direct_member"])),
                    )
                    for row in normalized_rows
                ),
            )
            connection.executemany(
                "INSERT INTO source_group_projection_state"
                "(scope_id, object_id, inventory_revision, "
                "projection_version, expected_group_ids, "
                "expected_projection_rows) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    (
                        scope_id,
                        object_id,
                        inventory_revision,
                        SOURCE_GROUP_PROJECTION_VERSION,
                        expected_group_ids,
                        _canonical_json(
                            sorted(expected_rows_by_object[object_id])
                        ),
                    )
                    for object_id, expected_group_ids in (
                        expected_by_object.items()
                    )
                ),
            )
        return len(normalized_rows)

    def source_group_rebase_page(
        self,
        *,
        after_object_id: str = "",
        after_scope_id: str = "",
        limit: int = 500,
    ) -> tuple[tuple[dict[str, Any], ...], bool]:
        """Read a stable bounded occurrence page for explicit index repair."""

        if limit < 1 or limit > 500:
            raise ValueError("source group rebase limit is invalid")
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT scope_id, object_id, inventory_revision, "
                "disposition, occurrence_payload "
                "FROM inventory_occurrence_current "
                "WHERE (object_id>? OR (object_id=? AND scope_id>?)) "
                "ORDER BY object_id, scope_id LIMIT ?",
                (
                    after_object_id,
                    after_object_id,
                    after_scope_id,
                    limit + 1,
                ),
            ).fetchall()
        has_more = len(rows) > limit
        return (
            tuple(
                {
                    "scope_id": str(row[0]),
                    "object_id": str(row[1]),
                    "inventory_revision": int(row[2]),
                    "disposition": str(row[3]),
                    "occurrence": json.loads(str(row[4])),
                }
                for row in rows[:limit]
            ),
            has_more,
        )

    def replace_source_group_occurrences(
        self,
        rows: Iterable[dict[str, Any]],
    ) -> int:
        """Replace several exact occurrence memberships in one transaction."""

        normalized = tuple(dict(row) for row in rows)
        grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
        for row in normalized:
            key = (
                str(row["scope_id"]),
                str(row["inventory_occurrence_id"]),
                int(row["inventory_revision"]),
            )
            grouped.setdefault(key, []).append(row)
        with self.connection() as connection:
            for (scope_id, object_id, revision), group_rows in grouped.items():
                current = connection.execute(
                    "SELECT inventory_revision FROM "
                    "inventory_occurrence_current "
                    "WHERE scope_id=? AND object_id=?",
                    (scope_id, object_id),
                ).fetchone()
                if current is None or int(current[0]) != revision:
                    continue
                connection.execute(
                    "DELETE FROM source_group_member_index "
                    "WHERE scope_id=? AND object_id=?",
                    (scope_id, object_id),
                )
                connection.execute(
                    "DELETE FROM source_group_projection_state "
                    "WHERE scope_id=? AND object_id=?",
                    (scope_id, object_id),
                )
                connection.executemany(
                    "INSERT INTO source_group_member_index"
                    "(scope_id, inventory_revision, object_id, occurrence_id, "
                    "group_id, parent_group_id, child_group_id, title, depth, "
                    "provider, object_type, member_title, availability, "
                    "direct_member) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        (
                            scope_id,
                            revision,
                            object_id,
                            str(row["occurrence_id"]),
                            str(row["group_id"]),
                            str(row.get("parent_group_id", "")),
                            str(row.get("child_group_id", "")),
                            str(row["title"]),
                            int(row["depth"]),
                            str(row["provider"]),
                            str(row["object_type"]),
                            str(row["member_title"]),
                            str(row["availability"]),
                            int(bool(row["direct_member"])),
                        )
                        for row in group_rows
                    ),
                )
                connection.execute(
                    "INSERT INTO source_group_projection_state"
                    "(scope_id, object_id, inventory_revision, "
                    "projection_version, expected_group_ids, "
                    "expected_projection_rows) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        scope_id,
                        object_id,
                        revision,
                        SOURCE_GROUP_PROJECTION_VERSION,
                        _canonical_json(
                            sorted(
                                {
                                    str(row["group_id"])
                                    for row in group_rows
                                }
                            )
                        ),
                        _canonical_json(
                            sorted(
                                {
                                    _source_group_projection_identity(row)
                                    for row in group_rows
                                }
                            )
                        ),
                    ),
                )
        return len(normalized)

    def clear_source_group_occurrences(
        self,
        identities: Iterable[tuple[str, str, int]],
    ) -> int:
        """Remove stale memberships for exact current occurrence owners."""

        normalized = tuple(
            (str(scope_id), str(object_id), int(revision))
            for scope_id, object_id, revision in identities
        )
        deleted = 0
        with self.connection() as connection:
            for scope_id, object_id, revision in normalized:
                current = connection.execute(
                    "SELECT inventory_revision FROM "
                    "inventory_occurrence_current "
                    "WHERE scope_id=? AND object_id=?",
                    (scope_id, object_id),
                ).fetchone()
                if current is None or int(current[0]) != revision:
                    continue
                cursor = connection.execute(
                    "DELETE FROM source_group_member_index "
                    "WHERE scope_id=? AND object_id=?",
                    (scope_id, object_id),
                )
                deleted += max(0, int(cursor.rowcount))
                connection.execute(
                    "DELETE FROM source_group_projection_state "
                    "WHERE scope_id=? AND object_id=?",
                    (scope_id, object_id),
                )
        return deleted

    def source_group_index_status(self) -> dict[str, int | str]:
        """Compare the rebuildable group index with eligible inventory."""

        member_identity_sql = (
            "json_array(member.group_id, member.parent_group_id, "
            "member.child_group_id, member.title, member.depth, "
            "member.occurrence_id, member.provider, member.object_type, "
            "member.member_title, member.availability, member.direct_member)"
        )
        with self.connection() as connection:
            eligible = int(
                connection.execute(
                    "SELECT COUNT(*) FROM inventory_occurrence_current "
                    "WHERE disposition NOT IN ('hard_excluded','not_tracked')"
                ).fetchone()[0]
            )
            indexed = int(
                connection.execute(
                    "WITH expected AS ("
                    "SELECT inventory.scope_id, inventory.object_id, "
                    "inventory.inventory_revision "
                    "FROM inventory_occurrence_current inventory "
                    "WHERE inventory.disposition NOT IN "
                    "('hard_excluded','not_tracked')"
                    ") "
                    "SELECT COUNT(*) FROM expected "
                    "JOIN source_group_projection_state state "
                    "ON state.scope_id=expected.scope_id "
                    "AND state.object_id=expected.object_id "
                    "AND state.inventory_revision="
                    "expected.inventory_revision "
                    "WHERE state.projection_version=? "
                    "AND json_valid(state.expected_group_ids)=1 "
                    "AND json_valid(state.expected_projection_rows)=1 "
                    "AND NOT EXISTS ("
                    "SELECT 1 FROM json_each(state.expected_projection_rows) "
                    "expected_row WHERE NOT EXISTS ("
                    "SELECT 1 FROM source_group_member_index member "
                    "WHERE member.scope_id=expected.scope_id "
                    "AND member.object_id=expected.object_id "
                    "AND member.inventory_revision="
                    "expected.inventory_revision "
                    f"AND {member_identity_sql}="
                    "CAST(expected_row.value AS TEXT)"
                    ")) "
                    "AND NOT EXISTS ("
                    "SELECT 1 FROM source_group_member_index member "
                    "WHERE member.scope_id=expected.scope_id "
                    "AND member.object_id=expected.object_id "
                    "AND member.inventory_revision="
                    "expected.inventory_revision "
                    "AND NOT EXISTS ("
                    "SELECT 1 FROM json_each(state.expected_projection_rows) "
                    "expected_row WHERE CAST(expected_row.value AS TEXT)="
                    f"{member_identity_sql}"
                    "))",
                    (SOURCE_GROUP_PROJECTION_VERSION,),
                ).fetchone()[0]
            )
            stale = int(
                connection.execute(
                    "SELECT COUNT(*) FROM ("
                    "SELECT member.scope_id, member.object_id "
                    "FROM source_group_member_index member "
                    "LEFT JOIN inventory_occurrence_current inventory "
                    "ON inventory.scope_id=member.scope_id "
                    "AND inventory.object_id=member.object_id "
                    "AND inventory.inventory_revision="
                    "member.inventory_revision "
                    "WHERE inventory.object_id IS NULL "
                    "OR inventory.disposition IN "
                    "('hard_excluded','not_tracked')"
                    " UNION "
                    "SELECT state.scope_id, state.object_id "
                    "FROM source_group_projection_state state "
                    "LEFT JOIN inventory_occurrence_current inventory "
                    "ON inventory.scope_id=state.scope_id "
                    "AND inventory.object_id=state.object_id "
                    "AND inventory.inventory_revision="
                    "state.inventory_revision "
                    "WHERE inventory.object_id IS NULL "
                    "OR inventory.disposition IN "
                    "('hard_excluded','not_tracked') "
                    "OR state.projection_version<>?"
                    ")",
                    (SOURCE_GROUP_PROJECTION_VERSION,),
                ).fetchone()[0]
            )
        remaining = max(0, eligible - indexed)
        return {
            "status": (
                "current"
                if not remaining and not stale
                else "partial"
            ),
            "eligible_occurrence_count": eligible,
            "indexed_occurrence_count": indexed,
            "remaining_occurrence_count": remaining,
            "stale_occurrence_count": stale,
        }

    def source_group_page(
        self,
        *,
        offset: int,
        limit: int,
        query: str = "",
    ) -> tuple[tuple[dict[str, Any], ...], int]:
        """Read one bounded aggregate page without decoding inventories."""

        if offset < 0 or limit < 1 or limit > 200:
            raise ValueError("source group page bounds are invalid")
        normalized_query = str(query).strip().casefold()
        pattern = f"%{normalized_query}%"
        grouped_sql = (
            "WITH grouped AS ("
            "SELECT g.group_id, MAX(g.parent_group_id) parent_group_id, "
            "MAX(g.title) title, MIN(g.depth) depth, "
            "COUNT(DISTINCT CASE WHEN g.direct_member=1 "
            "THEN g.object_id END) direct_member_count, "
            "COUNT(DISTINCT g.object_id) total_member_count, "
            "COUNT(DISTINCT NULLIF(g.child_group_id,'')) child_group_count, "
            "GROUP_CONCAT(DISTINCT g.object_type) source_types, "
            "COUNT(DISTINCT CASE WHEN g.availability='available' "
            "THEN g.object_id END) available_member_count "
            "FROM source_group_member_index g "
            "JOIN inventory_occurrence_current i "
            "ON i.scope_id=g.scope_id AND i.object_id=g.object_id "
            "AND i.inventory_revision=g.inventory_revision "
            "JOIN source_group_projection_state state "
            "ON state.scope_id=g.scope_id AND state.object_id=g.object_id "
            "AND state.inventory_revision=g.inventory_revision "
            f"AND state.projection_version={SOURCE_GROUP_PROJECTION_VERSION} "
            "AND EXISTS (SELECT 1 FROM json_each(state.expected_group_ids) "
            "expected_group WHERE CAST(expected_group.value AS TEXT)=g.group_id) "
            "WHERE i.disposition NOT IN ('hard_excluded','not_tracked') "
            "GROUP BY g.group_id"
            ") "
        )
        filter_sql = (
            "WHERE (?='' OR LOWER(title) LIKE ? "
            "OR LOWER(source_types) LIKE ?) "
        )
        with self.connection() as connection:
            total = int(
                connection.execute(
                    grouped_sql + "SELECT COUNT(*) FROM grouped " + filter_sql,
                    (normalized_query, pattern, pattern),
                ).fetchone()[0]
            )
            rows = connection.execute(
                grouped_sql
                + "SELECT group_id, parent_group_id, title, depth, "
                "direct_member_count, total_member_count, child_group_count, "
                "source_types, available_member_count FROM grouped "
                + filter_sql
                + "ORDER BY LOWER(title), group_id LIMIT ? OFFSET ?",
                (normalized_query, pattern, pattern, limit, offset),
            ).fetchall()
        return (
            tuple(
                {
                    "group_id": str(row[0]),
                    "parent_group_id": str(row[1]),
                    "title": str(row[2]),
                    "depth": int(row[3]),
                    "direct_member_count": int(row[4]),
                    "total_member_count": int(row[5]),
                    "child_group_count": int(row[6]),
                    "source_types": tuple(
                        sorted(
                            item
                            for item in str(row[7] or "").split(",")
                            if item
                        )
                    ),
                    "availability": (
                        "available"
                        if int(row[8]) == int(row[5]) and int(row[5])
                        else (
                            "partial"
                            if int(row[8])
                            else "source_unavailable"
                        )
                    ),
                }
                for row in rows
            ),
            total,
        )

    def source_group_detail_page(
        self,
        *,
        group_id: str,
        member_offset: int,
        member_limit: int,
    ) -> dict[str, Any] | None:
        """Read one group summary plus a bounded, path-free member page."""

        if (
            not group_id
            or member_offset < 0
            or member_limit < 1
            or member_limit > 200
        ):
            raise ValueError("source group detail bounds are invalid")
        summaries, _total = self.source_group_page(
            offset=0,
            limit=200,
            query="",
        )
        summary = next(
            (item for item in summaries if item["group_id"] == group_id),
            None,
        )
        if summary is None:
            with self.connection() as connection:
                exists = connection.execute(
                    "SELECT 1 FROM source_group_member_index g "
                    "JOIN inventory_occurrence_current i "
                    "ON i.scope_id=g.scope_id AND i.object_id=g.object_id "
                    "AND i.inventory_revision=g.inventory_revision "
                    "JOIN source_group_projection_state state "
                    "ON state.scope_id=g.scope_id "
                    "AND state.object_id=g.object_id "
                    "AND state.inventory_revision=g.inventory_revision "
                    f"AND state.projection_version="
                    f"{SOURCE_GROUP_PROJECTION_VERSION} "
                    "AND EXISTS (SELECT 1 "
                    "FROM json_each(state.expected_group_ids) expected_group "
                    "WHERE CAST(expected_group.value AS TEXT)=g.group_id) "
                    "WHERE g.group_id=? AND i.disposition NOT IN "
                    "('hard_excluded','not_tracked') LIMIT 1",
                    (group_id,),
                ).fetchone()
            if exists is None:
                return None
            # The requested group may sort beyond the first aggregate page.
            with self.connection() as connection:
                row = connection.execute(
                    "SELECT MAX(g.parent_group_id), MAX(g.title), "
                    "MIN(g.depth), "
                    "COUNT(DISTINCT CASE WHEN g.direct_member=1 "
                    "THEN g.object_id END), COUNT(DISTINCT g.object_id), "
                    "COUNT(DISTINCT NULLIF(g.child_group_id,'')), "
                    "GROUP_CONCAT(DISTINCT g.object_type), "
                    "COUNT(DISTINCT CASE WHEN g.availability='available' "
                    "THEN g.object_id END) "
                    "FROM source_group_member_index g "
                    "JOIN inventory_occurrence_current i "
                    "ON i.scope_id=g.scope_id AND i.object_id=g.object_id "
                    "AND i.inventory_revision=g.inventory_revision "
                    "JOIN source_group_projection_state state "
                    "ON state.scope_id=g.scope_id "
                    "AND state.object_id=g.object_id "
                    "AND state.inventory_revision=g.inventory_revision "
                    f"AND state.projection_version="
                    f"{SOURCE_GROUP_PROJECTION_VERSION} "
                    "AND EXISTS (SELECT 1 "
                    "FROM json_each(state.expected_group_ids) expected_group "
                    "WHERE CAST(expected_group.value AS TEXT)=g.group_id) "
                    "WHERE g.group_id=? AND i.disposition NOT IN "
                    "('hard_excluded','not_tracked')",
                    (group_id,),
                ).fetchone()
            member_count = int(row[4])
            summary = {
                "group_id": group_id,
                "parent_group_id": str(row[0]),
                "title": str(row[1]),
                "depth": int(row[2]),
                "direct_member_count": int(row[3]),
                "total_member_count": member_count,
                "child_group_count": int(row[5]),
                "source_types": tuple(
                    sorted(
                        item for item in str(row[6] or "").split(",") if item
                    )
                ),
                "availability": (
                    "available"
                    if int(row[7]) == member_count and member_count
                    else ("partial" if int(row[7]) else "source_unavailable")
                ),
            }
        with self.connection() as connection:
            member_total = int(
                connection.execute(
                    "SELECT COUNT(DISTINCT g.object_id) "
                    "FROM source_group_member_index g "
                    "JOIN inventory_occurrence_current i "
                    "ON i.scope_id=g.scope_id AND i.object_id=g.object_id "
                    "AND i.inventory_revision=g.inventory_revision "
                    "JOIN source_group_projection_state state "
                    "ON state.scope_id=g.scope_id "
                    "AND state.object_id=g.object_id "
                    "AND state.inventory_revision=g.inventory_revision "
                    f"AND state.projection_version="
                    f"{SOURCE_GROUP_PROJECTION_VERSION} "
                    "AND EXISTS (SELECT 1 "
                    "FROM json_each(state.expected_group_ids) expected_group "
                    "WHERE CAST(expected_group.value AS TEXT)=g.group_id) "
                    "WHERE g.group_id=? AND i.disposition NOT IN "
                    "('hard_excluded','not_tracked')",
                    (group_id,),
                ).fetchone()[0]
            )
            member_rows = connection.execute(
                "SELECT g.occurrence_id, MAX(g.provider), "
                "MAX(g.object_type), MAX(g.member_title), "
                "CASE WHEN SUM(CASE WHEN g.availability='available' "
                "THEN 1 ELSE 0 END)>0 THEN 'available' "
                "ELSE 'source_unavailable' END "
                "FROM source_group_member_index g "
                "JOIN inventory_occurrence_current i "
                "ON i.scope_id=g.scope_id AND i.object_id=g.object_id "
                "AND i.inventory_revision=g.inventory_revision "
                "JOIN source_group_projection_state state "
                "ON state.scope_id=g.scope_id "
                "AND state.object_id=g.object_id "
                "AND state.inventory_revision=g.inventory_revision "
                f"AND state.projection_version="
                f"{SOURCE_GROUP_PROJECTION_VERSION} "
                "AND EXISTS (SELECT 1 "
                "FROM json_each(state.expected_group_ids) expected_group "
                "WHERE CAST(expected_group.value AS TEXT)=g.group_id) "
                "WHERE g.group_id=? AND i.disposition NOT IN "
                "('hard_excluded','not_tracked') "
                "GROUP BY g.object_id ORDER BY g.occurrence_id "
                "LIMIT ? OFFSET ?",
                (group_id, member_limit, member_offset),
            ).fetchall()
            child_rows = connection.execute(
                "SELECT DISTINCT g.child_group_id "
                "FROM source_group_member_index g "
                "JOIN inventory_occurrence_current i "
                "ON i.scope_id=g.scope_id AND i.object_id=g.object_id "
                "AND i.inventory_revision=g.inventory_revision "
                "JOIN source_group_projection_state state "
                "ON state.scope_id=g.scope_id "
                "AND state.object_id=g.object_id "
                "AND state.inventory_revision=g.inventory_revision "
                f"AND state.projection_version="
                f"{SOURCE_GROUP_PROJECTION_VERSION} "
                "AND EXISTS (SELECT 1 "
                "FROM json_each(state.expected_group_ids) expected_group "
                "WHERE CAST(expected_group.value AS TEXT)=g.group_id) "
                "WHERE g.group_id=? AND g.child_group_id<>'' "
                "AND i.disposition NOT IN "
                "('hard_excluded','not_tracked') "
                "ORDER BY g.child_group_id",
                (group_id,),
            ).fetchall()
        next_offset = member_offset + len(member_rows)
        return {
            "summary": summary,
            "child_group_ids": tuple(str(row[0]) for row in child_rows),
            "members": tuple(
                {
                    "occurrence_id": str(row[0]),
                    "provider": str(row[1]),
                    "object_type": str(row[2]),
                    "title": str(row[3]),
                    "availability": str(row[4]),
                }
                for row in member_rows
            ),
            "member_total_count": member_total,
            "member_offset": member_offset,
            "member_limit": member_limit,
            "next_member_offset": (
                next_offset if next_offset < member_total else None
            ),
        }

    def current_inventory_identity(self) -> str:
        """Hash current scope revisions without decoding occurrence payloads."""

        digest = sha256()
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT current.object_id, current.revision, "
                "snapshot.payload_hash "
                "FROM current_objects current "
                "JOIN snapshots snapshot ON snapshot.owner=current.owner "
                "AND snapshot.object_id=current.object_id "
                "AND snapshot.revision=current.revision "
                "WHERE current.owner='inventory_snapshot' "
                "ORDER BY current.object_id"
            )
            for scope_id, revision, payload_hash in rows:
                digest.update(
                    (
                        _canonical_json(
                            (
                                str(scope_id),
                                int(revision),
                                str(payload_hash),
                            )
                        )
                        + "\n"
                    ).encode("utf-8")
                )
        return "sha256:" + digest.hexdigest()

    def missing_matter_coverage_page(
        self,
        *,
        after_matter_id: str,
        limit: int,
    ) -> tuple[tuple[dict[str, Any], ...], bool]:
        """Read one bounded hierarchy-owned Matter page missing coverage."""

        if limit < 1 or limit > 500:
            raise ValueError("Matter coverage rebase limit is invalid")
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT hierarchy.matter_id, projection.payload, "
                "hierarchy.change_ref, edge.parent_matter_id "
                "FROM matter_hierarchy_stage_index hierarchy "
                "JOIN current_objects admission_current "
                "ON admission_current.owner='admission_decision' "
                "AND admission_current.object_id=hierarchy.matter_id "
                "JOIN snapshots admission "
                "ON admission.owner=admission_current.owner "
                "AND admission.object_id=admission_current.object_id "
                "AND admission.revision=admission_current.revision "
                "LEFT JOIN current_objects projection_current "
                "ON projection_current.owner='projection' "
                "AND projection_current.object_id=hierarchy.matter_id "
                "LEFT JOIN snapshots projection "
                "ON projection.owner=projection_current.owner "
                "AND projection.object_id=projection_current.object_id "
                "AND projection.revision=projection_current.revision "
                "LEFT JOIN matter_hierarchy_index edge "
                "ON edge.child_matter_id=hierarchy.matter_id "
                "LEFT JOIN coverage_stage_index coverage "
                "ON coverage.object_id=hierarchy.matter_id "
                "WHERE hierarchy.matter_id>? "
                "AND json_extract(admission.payload, '$.status')='admitted' "
                "AND CAST(json_extract(admission.payload, "
                "'$.matter.matter_id') AS TEXT)=hierarchy.matter_id "
                "AND coverage.object_id IS NULL "
                "ORDER BY hierarchy.matter_id LIMIT ?",
                (after_matter_id, limit + 1),
            ).fetchall()
        has_more = len(rows) > limit
        result: list[dict[str, Any]] = []
        for (
            matter_id,
            projection_payload,
            change_ref,
            parent_matter_id,
        ) in rows[:limit]:
            projection = (
                json.loads(str(projection_payload))
                if projection_payload is not None
                else {}
            )
            result.append(
                {
                    "matter_id": str(matter_id),
                    "matter_kind": (
                        "child_matter"
                        if str(parent_matter_id or "")
                        else "root_matter"
                    ),
                    "semantic_revision": str(
                        projection.get(
                            "semantic_revision",
                            f"hierarchy:{change_ref}",
                        )
                    ),
                    "hierarchy_revision": str(change_ref),
                }
            )
        return tuple(result), has_more

    def canonical_matter_presentation_page(
        self,
        *,
        after_matter_id: str,
        limit: int,
    ) -> tuple[tuple[dict[str, Any], ...], bool]:
        """Read one bounded exact-admission page with presentation owners."""

        if limit < 1 or limit > 500:
            raise ValueError("Matter presentation page limit is invalid")
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT admission_current.object_id, "
                "admission_current.revision, admission.payload, "
                "projection.payload, hero.payload "
                "FROM current_objects admission_current "
                "JOIN snapshots admission "
                "ON admission.owner=admission_current.owner "
                "AND admission.object_id=admission_current.object_id "
                "AND admission.revision=admission_current.revision "
                "LEFT JOIN current_objects projection_current "
                "ON projection_current.owner='projection' "
                "AND projection_current.object_id=admission_current.object_id "
                "LEFT JOIN snapshots projection "
                "ON projection.owner=projection_current.owner "
                "AND projection.object_id=projection_current.object_id "
                "AND projection.revision=projection_current.revision "
                "LEFT JOIN current_objects hero_current "
                "ON hero_current.owner='generated_hero_record' "
                "AND hero_current.object_id=admission_current.object_id "
                "LEFT JOIN snapshots hero "
                "ON hero.owner=hero_current.owner "
                "AND hero.object_id=hero_current.object_id "
                "AND hero.revision=hero_current.revision "
                "WHERE admission_current.owner='admission_decision' "
                "AND admission_current.object_id>? "
                "AND json_extract(admission.payload, '$.status')='admitted' "
                "AND CAST(json_extract(admission.payload, "
                "'$.matter.matter_id') AS TEXT)=admission_current.object_id "
                "AND COALESCE(json_extract(admission.payload, "
                "'$.matter.admitted'), 1)=1 "
                "ORDER BY admission_current.object_id LIMIT ?",
                (after_matter_id, limit + 1),
            ).fetchall()
        has_more = len(rows) > limit
        return (
            tuple(
                {
                    "matter_id": str(matter_id),
                    "admission_revision": int(admission_revision),
                    "admission": json.loads(str(admission_payload)),
                    "projection": (
                        json.loads(str(projection_payload))
                        if projection_payload is not None
                        else None
                    ),
                    "generated_hero": (
                        json.loads(str(hero_payload))
                        if hero_payload is not None
                        else None
                    ),
                }
                for (
                    matter_id,
                    admission_revision,
                    admission_payload,
                    projection_payload,
                    hero_payload,
                ) in rows[:limit]
            ),
            has_more,
        )

    def noncanonical_matter_coverage_page(
        self,
        *,
        after_object_id: str,
        limit: int,
    ) -> tuple[tuple[str, ...], bool]:
        """Read one page of active Matter coverage without canonical admission."""

        if limit < 1 or limit > 500:
            raise ValueError("noncanonical Matter coverage page limit is invalid")
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT coverage.object_id "
                "FROM coverage_stage_index coverage "
                "LEFT JOIN current_objects admission_current "
                "ON admission_current.owner='admission_decision' "
                "AND admission_current.object_id=coverage.object_id "
                "LEFT JOIN snapshots admission "
                "ON admission.owner=admission_current.owner "
                "AND admission.object_id=admission_current.object_id "
                "AND admission.revision=admission_current.revision "
                "WHERE coverage.active=1 "
                "AND coverage.provider='matters' "
                "AND coverage.object_type IN ('root_matter', 'child_matter') "
                "AND coverage.object_id>? "
                "AND NOT ("
                "COALESCE(json_extract(admission.payload, '$.status'), '')="
                "'admitted' AND COALESCE(CAST(json_extract("
                "admission.payload, '$.matter.matter_id') AS TEXT), '')="
                "coverage.object_id"
                ") "
                "ORDER BY coverage.object_id LIMIT ?",
                (after_object_id, limit + 1),
            ).fetchall()
        has_more = len(rows) > limit
        return tuple(str(row[0]) for row in rows[:limit]), has_more

    def noncanonical_matter_hierarchy_page(
        self,
        *,
        after_matter_id: str,
        limit: int,
    ) -> tuple[tuple[str, ...], bool]:
        """Read one exclusive-cursor page of hierarchy-only non-Matters.

        A canonical Matter is exactly one current C6 admission whose payload
        says ``admitted`` and whose embedded ``matter_id`` equals the current
        object id.  Merely having a hierarchy audit, summary, projection, or
        materialized stage-index row does not satisfy that contract.
        """

        if limit < 1 or limit > 500:
            raise ValueError(
                "noncanonical Matter hierarchy page limit is invalid"
            )
        with self.connection() as connection:
            rows = connection.execute(
                "WITH hierarchy_candidates(matter_id) AS ("
                "SELECT object_id FROM current_objects "
                "WHERE owner IN ('matter_hierarchy_audit', "
                "'matter_hierarchy_projection', 'matter_hierarchy_summary') "
                "UNION SELECT matter_id FROM matter_hierarchy_stage_index"
                ") "
                "SELECT candidate.matter_id "
                "FROM hierarchy_candidates candidate "
                "LEFT JOIN current_objects admission_current "
                "ON admission_current.owner='admission_decision' "
                "AND admission_current.object_id=candidate.matter_id "
                "LEFT JOIN snapshots admission "
                "ON admission.owner=admission_current.owner "
                "AND admission.object_id=admission_current.object_id "
                "AND admission.revision=admission_current.revision "
                "WHERE candidate.matter_id>? AND NOT ("
                "COALESCE(json_extract(admission.payload, '$.status'), '')="
                "'admitted' AND COALESCE(CAST(json_extract("
                "admission.payload, '$.matter.matter_id') AS TEXT), '')="
                "candidate.matter_id AND COALESCE(json_extract("
                "admission.payload, '$.matter.admitted'), 1)=1"
                ") ORDER BY candidate.matter_id LIMIT ?",
                (after_matter_id, limit + 1),
            ).fetchall()
        has_more = len(rows) > limit
        return tuple(str(row[0]) for row in rows[:limit]), has_more

    def retire_noncanonical_matter_hierarchy_ids(
        self,
        matter_ids: Iterable[str],
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Remove only current noncanonical hierarchy authority.

        Immutable snapshots (and therefore ``history``) are preserved.  The
        page is an atomic zero-write block when any selected noncanonical
        endpoint still participates in an active containment edge.
        """

        requested = tuple(
            dict.fromkeys(str(item) for item in matter_ids if str(item))
        )
        if len(requested) > 500:
            raise ValueError(
                "noncanonical Matter hierarchy retirement is unbounded"
            )
        if not requested:
            return {
                "scanned_matter_count": 0,
                "retired_matter_count": 0,
                "retired_pointer_count": 0,
                "retired_stage_index_count": 0,
                "blocked_matter_ids": (),
                "dry_run": dry_run,
                "status": "current",
            }
        placeholders = ",".join("?" for _ in requested)
        with self.connection() as connection:
            if not connection.in_transaction:
                connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "WITH hierarchy_candidates(matter_id) AS ("
                "SELECT object_id FROM current_objects "
                "WHERE owner IN ('matter_hierarchy_audit', "
                "'matter_hierarchy_projection', 'matter_hierarchy_summary') "
                f"AND object_id IN ({placeholders}) "
                "UNION SELECT matter_id FROM matter_hierarchy_stage_index "
                f"WHERE matter_id IN ({placeholders})"
                ") "
                "SELECT candidate.matter_id "
                "FROM hierarchy_candidates candidate "
                "LEFT JOIN current_objects admission_current "
                "ON admission_current.owner='admission_decision' "
                "AND admission_current.object_id=candidate.matter_id "
                "LEFT JOIN snapshots admission "
                "ON admission.owner=admission_current.owner "
                "AND admission.object_id=admission_current.object_id "
                "AND admission.revision=admission_current.revision "
                "WHERE NOT ("
                "COALESCE(json_extract(admission.payload, '$.status'), '')="
                "'admitted' AND COALESCE(CAST(json_extract("
                "admission.payload, '$.matter.matter_id') AS TEXT), '')="
                "candidate.matter_id AND COALESCE(json_extract("
                "admission.payload, '$.matter.admitted'), 1)=1"
                ") ORDER BY candidate.matter_id",
                (*requested, *requested),
            ).fetchall()
            targets = tuple(str(row[0]) for row in rows)
            if not targets:
                return {
                    "scanned_matter_count": len(requested),
                    "retired_matter_count": 0,
                    "retired_pointer_count": 0,
                    "retired_stage_index_count": 0,
                    "blocked_matter_ids": (),
                    "dry_run": dry_run,
                    "status": "current",
                }
            target_placeholders = ",".join("?" for _ in targets)
            active_edges = connection.execute(
                "SELECT child_matter_id, parent_matter_id "
                "FROM matter_hierarchy_index WHERE "
                f"child_matter_id IN ({target_placeholders}) OR "
                f"parent_matter_id IN ({target_placeholders})",
                (*targets, *targets),
            ).fetchall()
            target_set = set(targets)
            blocked = tuple(
                sorted(
                    {
                        endpoint
                        for row in active_edges
                        for endpoint in (str(row[0]), str(row[1]))
                        if endpoint in target_set
                    }
                )
            )
            if blocked:
                return {
                    "scanned_matter_count": len(requested),
                    "retired_matter_count": 0,
                    "retired_pointer_count": 0,
                    "retired_stage_index_count": 0,
                    "blocked_matter_ids": blocked,
                    "dry_run": dry_run,
                    "status": "blocked",
                }
            pointer_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM current_objects "
                    "WHERE owner IN ('matter_hierarchy_audit', "
                    "'matter_hierarchy_projection', "
                    "'matter_hierarchy_summary') "
                    f"AND object_id IN ({target_placeholders})",
                    targets,
                ).fetchone()[0]
            )
            stage_index_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM matter_hierarchy_stage_index "
                    f"WHERE matter_id IN ({target_placeholders})",
                    targets,
                ).fetchone()[0]
            )
            if not dry_run:
                connection.execute(
                    "DELETE FROM current_objects "
                    "WHERE owner IN ('matter_hierarchy_audit', "
                    "'matter_hierarchy_projection', "
                    "'matter_hierarchy_summary') "
                    f"AND object_id IN ({target_placeholders})",
                    targets,
                )
                connection.execute(
                    "DELETE FROM matter_hierarchy_stage_index "
                    f"WHERE matter_id IN ({target_placeholders})",
                    targets,
                )
            return {
                "scanned_matter_count": len(requested),
                "retired_matter_count": (
                    0 if dry_run else len(targets)
                ),
                "retired_pointer_count": (
                    0 if dry_run else pointer_count
                ),
                "retired_stage_index_count": (
                    0 if dry_run else stage_index_count
                ),
                "candidate_matter_count": len(targets),
                "candidate_pointer_count": pointer_count,
                "candidate_stage_index_count": stage_index_count,
                "blocked_matter_ids": (),
                "dry_run": dry_run,
                "status": "current",
            }

    def orphaned_active_source_coverage_page(
        self,
        *,
        limit: int,
    ) -> tuple[str, ...]:
        """Find active source coverage whose inventory occurrence disappeared."""

        if limit < 1 or limit > 500:
            raise ValueError("coverage orphan page bounds are invalid")
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT c.object_id FROM coverage_stage_index c "
                "WHERE c.active=1 "
                "AND c.provider IN ('filesystem', 'gmail') "
                "AND NOT EXISTS ("
                "SELECT 1 FROM inventory_occurrence_current i "
                "WHERE i.object_id=c.object_id"
                ") ORDER BY c.object_id LIMIT ?",
                (limit,),
            ).fetchall()
        return tuple(str(row[0]) for row in rows)

    @staticmethod
    def _gmail_current_scope_reconciliation_record(
        connection: sqlite3.Connection,
        object_id: str,
    ) -> dict[str, Any] | None:
        """Hydrate one privacy-bounded C1/C2 reconciliation input.

        The application owner makes the policy decision.  This store primitive
        only returns exact current authorities plus the historical inventory
        snapshot referenced by the current coverage row.  No provider access
        or source-body read occurs here.
        """

        def current_record(owner: str, identity: str) -> dict[str, Any] | None:
            row = connection.execute(
                "SELECT c.revision, s.payload, s.payload_hash, s.created_at "
                "FROM current_objects c JOIN snapshots s "
                "ON s.owner=c.owner AND s.object_id=c.object_id "
                "AND s.revision=c.revision "
                "WHERE c.owner=? AND c.object_id=?",
                (owner, identity),
            ).fetchone()
            if row is None:
                return None
            return {
                "revision": int(row[0]),
                "payload": json.loads(row[1]),
                "payload_hash": str(row[2]),
                "created_at": str(row[3]),
            }

        coverage = current_record("object_coverage", object_id)
        if coverage is None:
            return None
        coverage_payload = dict(coverage["payload"])
        if not (
            bool(coverage_payload.get("active", True))
            and str(coverage_payload.get("provider", "")) == "gmail"
            and str(coverage_payload.get("object_type", "")) == "message"
            and str(coverage_payload.get("disposition", ""))
            == "metadata_only"
        ):
            return None

        bound_scope_id = str(coverage_payload.get("scope_id", ""))
        bound_inventory_revision = int(
            coverage_payload.get("inventory_revision", 0) or 0
        )
        bound_inventory_row = connection.execute(
            "SELECT payload, payload_hash, created_at FROM snapshots "
            "WHERE owner='inventory_snapshot' AND object_id=? AND revision=?",
            (bound_scope_id, bound_inventory_revision),
        ).fetchone()
        bound_inventory = (
            {
                "payload": json.loads(bound_inventory_row[0]),
                "payload_hash": str(bound_inventory_row[1]),
                "created_at": str(bound_inventory_row[2]),
            }
            if bound_inventory_row is not None
            else None
        )
        bound_scope = current_record("candidate_scope", bound_scope_id)
        tracking_policy = current_record(
            "tracking_policy",
            "tracking-policy:default",
        )

        occurrence_rows = connection.execute(
            "SELECT scope_id, inventory_revision, provider, object_type, "
            "disposition, occurrence_payload "
            "FROM inventory_occurrence_current "
            "WHERE object_id=? AND disposition='tracked' "
            "ORDER BY scope_id",
            (object_id,),
        ).fetchall()
        candidates: list[dict[str, Any]] = []
        for row in occurrence_rows:
            scope_id = str(row[0])
            candidates.append(
                {
                    "scope_id": scope_id,
                    "inventory_revision": int(row[1]),
                    "provider": str(row[2]),
                    "object_type": str(row[3]),
                    "disposition": str(row[4]),
                    "occurrence": json.loads(row[5]),
                    "scope": current_record("candidate_scope", scope_id),
                    "inventory": current_record(
                        "inventory_snapshot",
                        scope_id,
                    ),
                }
            )

        source_rows = connection.execute(
            "SELECT s.payload, s.payload_hash, s.created_at "
            "FROM current_objects c JOIN snapshots s "
            "ON s.owner=c.owner AND s.object_id=c.object_id "
            "AND s.revision=c.revision "
            "WHERE c.owner='source_version' "
            "AND json_extract(s.payload, '$.provider')='gmail' "
            "AND json_extract(s.payload, "
            "'$.external_reference.provider')='gmail' "
            "AND json_extract(s.payload, "
            "'$.external_reference.object_type')='gmail_message' "
            "AND json_extract(s.payload, "
            "'$.external_reference.external_id')=? "
            "ORDER BY c.object_id",
            (object_id,),
        ).fetchall()
        sources: list[dict[str, Any]] = []
        for payload_json, payload_hash, created_at in source_rows:
            payload = json.loads(payload_json)
            source_id = str(payload.get("source_id", ""))
            sources.append(
                {
                    "payload": payload,
                    "payload_hash": str(payload_hash),
                    "created_at": str(created_at),
                    "body_receipt": current_record(
                        "gmail_message_body",
                        source_id,
                    ),
                    "no_text_disposition": current_record(
                        "gmail_message_content_disposition",
                        source_id,
                    ),
                }
            )

        record: dict[str, Any] = {
            "object_id": object_id,
            "coverage": coverage,
            "bound_inventory": bound_inventory,
            "bound_scope": bound_scope,
            "tracking_policy": tracking_policy,
            "tracked_candidates": candidates,
            "sources": sources,
        }
        record["context_fingerprint"] = (
            "sha256:"
            + sha256(_canonical_json(record).encode("utf-8")).hexdigest()
        )
        return record

    def gmail_current_scope_reconciliation_page(
        self,
        *,
        after_object_id: str = "",
        limit: int = 200,
    ) -> tuple[tuple[dict[str, Any], ...], str]:
        """Return one stable keyset page of Gmail scope-owner mismatches."""

        if limit < 1 or limit > 500:
            raise ValueError("Gmail scope reconciliation page bounds are invalid")
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT coverage.object_id FROM coverage_stage_index coverage "
                "WHERE coverage.active=1 AND coverage.provider='gmail' "
                "AND coverage.object_type='message' "
                "AND coverage.disposition='metadata_only' "
                "AND coverage.object_id>? AND EXISTS ("
                "SELECT 1 FROM inventory_occurrence_current inventory "
                "WHERE inventory.object_id=coverage.object_id "
                "AND inventory.provider='gmail' "
                "AND inventory.object_type='message' "
                "AND inventory.disposition='tracked'"
                ") ORDER BY coverage.object_id LIMIT ?",
                (after_object_id, limit + 1),
            ).fetchall()
            object_ids = tuple(str(row[0]) for row in rows)
            has_more = len(object_ids) > limit
            selected = object_ids[:limit]
            records = tuple(
                record
                for object_id in selected
                if (
                    record
                    := self._gmail_current_scope_reconciliation_record(
                        connection,
                        object_id,
                    )
                )
                is not None
            )
        return records, (selected[-1] if has_more and selected else "")

    def commit_gmail_current_scope_reconciliation(
        self,
        *,
        object_id: str,
        expected_context_fingerprint: str,
        receipt_payload: dict[str, Any],
        coverage_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """CAS one current-scope decision and its append-only receipt.

        A stale read never changes either owner.  Coverage and receipt writes
        share one ``BEGIN IMMEDIATE`` transaction so the historical row cannot
        be detached from the decision that replaced it.
        """

        if (
            not object_id
            or not expected_context_fingerprint.startswith("sha256:")
            or str(receipt_payload.get("input_fingerprint", ""))
            != expected_context_fingerprint
            or str(receipt_payload.get("status", ""))
            not in {"current", "pending", "blocked"}
        ):
            raise ValueError("Gmail scope reconciliation commit is invalid")
        if coverage_payload is not None and (
            str(coverage_payload.get("object_id", "")) != object_id
            or str(coverage_payload.get("provider", "")) != "gmail"
            or str(coverage_payload.get("object_type", "")) != "message"
            or str(coverage_payload.get("disposition", "")) != "tracked"
            or str(receipt_payload.get("status", "")) != "current"
        ):
            raise ValueError("Gmail tracked coverage replacement is invalid")

        receipt_owner = "gmail_current_scope_reconciliation"
        with self.immediate_transaction():
            connection = self._connection_state.connection
            current_input = self._gmail_current_scope_reconciliation_record(
                connection,
                object_id,
            )
            if (
                current_input is None
                or current_input["context_fingerprint"]
                != expected_context_fingerprint
            ):
                return {"status": "stale", "coverage_revision": 0}

            if coverage_payload is not None:
                target_scope_id = str(coverage_payload.get("scope_id", ""))
                target_inventory_revision = int(
                    coverage_payload.get("inventory_revision", 0) or 0
                )
                target_matches = tuple(
                    candidate
                    for candidate in current_input["tracked_candidates"]
                    if candidate["scope_id"] == target_scope_id
                    and candidate["inventory_revision"]
                    == target_inventory_revision
                )
                if len(target_matches) != 1:
                    return {"status": "stale", "coverage_revision": 0}
                next_coverage_revision = self.next_revision(
                    "object_coverage",
                    object_id,
                )
                replacement = dict(coverage_payload)
                replacement["revision"] = next_coverage_revision
                replacement["updated_at"] = _utc_now()
                self.append(
                    "object_coverage",
                    object_id,
                    next_coverage_revision,
                    replacement,
                )
            else:
                next_coverage_revision = 0

            current_receipt = self.current(receipt_owner, object_id)
            if current_receipt == receipt_payload:
                receipt_changed = False
            else:
                self.append(
                    receipt_owner,
                    object_id,
                    self.next_revision(receipt_owner, object_id),
                    receipt_payload,
                )
                receipt_changed = True
        return {
            "status": "appended" if receipt_changed else "current",
            "coverage_revision": next_coverage_revision,
        }

    def gmail_manifest_coverage_snapshot(
        self,
        *,
        object_ids: Iterable[str],
        scope_ids: Iterable[str],
        stage_order: Iterable[str],
        batch_size: int = 200,
    ) -> dict[str, Any]:
        """Aggregate one manifest membership set through indexed owners.

        This read-only projection deliberately returns no object, scope, source,
        Matter, or provider message identifiers.  Callers receive only counts
        and deterministic set fingerprints.
        """

        objects = tuple(dict.fromkeys(str(item) for item in object_ids if str(item)))
        scopes = tuple(dict.fromkeys(str(item) for item in scope_ids if str(item)))
        stages = tuple(dict.fromkeys(str(item) for item in stage_order if str(item)))
        if (
            not objects
            or not scopes
            or len(objects) > 100_000
            or len(scopes) > 100
            or batch_size < 1
            or batch_size > 500
            or any(not item.startswith("gmail:message:") for item in objects)
        ):
            raise ValueError("Gmail manifest coverage audit bounds are invalid")

        def batches(values: tuple[str, ...]) -> Iterator[tuple[str, ...]]:
            for start in range(0, len(values), batch_size):
                yield values[start : start + batch_size]

        def fingerprint(values: Iterable[str]) -> str:
            return "sha256:" + sha256(
                _canonical_json(sorted(set(values))).encode("utf-8")
            ).hexdigest()

        expected = set(objects)
        fixed_hits: set[str] = set()
        fixed_occurrences = 0
        inventory_scopes: dict[str, set[str]] = {}
        inventory_dispositions: dict[str, dict[str, int]] = {}
        coverage_hits: set[str] = set()
        coverage_dispositions: dict[str, int] = {}
        next_stage_counts: dict[str, int] = {}
        terminal_count = ui_ready_count = blocked_count = 0
        stage_counts: dict[str, dict[str, int]] = {
            stage_id: {} for stage_id in stages
        }
        matter_linked: set[str] = set()
        matter_ids: set[str] = set()
        matter_stage_counts: dict[str, int] = {}

        with self.connection() as connection:
            for scope_id in scopes:
                for batch in batches(objects):
                    placeholders = ",".join("?" for _ in batch)
                    rows = connection.execute(
                        "SELECT object_id FROM inventory_occurrence_current "
                        "WHERE scope_id=? AND object_id IN ("
                        + placeholders
                        + ")",
                        (scope_id, *batch),
                    ).fetchall()
                    fixed_occurrences += len(rows)
                    fixed_hits.update(str(row[0]) for row in rows)

            for batch in batches(objects):
                placeholders = ",".join("?" for _ in batch)
                inventory_rows = connection.execute(
                    "SELECT object_id, scope_id, disposition "
                    "FROM inventory_occurrence_current WHERE object_id IN ("
                    + placeholders
                    + ")",
                    batch,
                ).fetchall()
                for object_id, scope_id, disposition in inventory_rows:
                    normalized_id = str(object_id)
                    inventory_scopes.setdefault(normalized_id, set()).add(
                        str(scope_id)
                    )
                    per_object = inventory_dispositions.setdefault(
                        normalized_id,
                        {},
                    )
                    normalized_disposition = str(disposition)
                    per_object[normalized_disposition] = (
                        per_object.get(normalized_disposition, 0) + 1
                    )

                coverage_rows = connection.execute(
                    "SELECT object_id, disposition, next_stage, terminal, "
                    "ui_ready, blocked, active FROM coverage_stage_index "
                    "WHERE object_id IN ("
                    + placeholders
                    + ")",
                    batch,
                ).fetchall()
                for (
                    object_id,
                    disposition,
                    next_stage,
                    terminal,
                    ui_ready,
                    blocked,
                    active,
                ) in coverage_rows:
                    if not bool(active):
                        continue
                    normalized_id = str(object_id)
                    coverage_hits.add(normalized_id)
                    normalized_disposition = str(disposition)
                    coverage_dispositions[normalized_disposition] = (
                        coverage_dispositions.get(normalized_disposition, 0) + 1
                    )
                    normalized_next = str(next_stage) or "terminal"
                    next_stage_counts[normalized_next] = (
                        next_stage_counts.get(normalized_next, 0) + 1
                    )
                    terminal_count += int(bool(terminal))
                    ui_ready_count += int(bool(ui_ready))
                    blocked_count += int(bool(blocked))

                status_rows = connection.execute(
                    "SELECT object_id, stage_id, status "
                    "FROM coverage_stage_status_index WHERE object_id IN ("
                    + placeholders
                    + ")",
                    batch,
                ).fetchall()
                for object_id, stage_id, status in status_rows:
                    if str(object_id) not in coverage_hits:
                        continue
                    normalized_stage = str(stage_id)
                    if normalized_stage not in stage_counts:
                        continue
                    normalized_status = str(status)
                    counts = stage_counts[normalized_stage]
                    counts[normalized_status] = counts.get(normalized_status, 0) + 1

                link_rows = connection.execute(
                    "SELECT object_id, matter_id FROM coverage_matter_index "
                    "WHERE object_id IN (" + placeholders + ")",
                    batch,
                ).fetchall()
                for object_id, matter_id in link_rows:
                    if str(object_id) not in coverage_hits:
                        continue
                    matter_linked.add(str(object_id))
                    matter_ids.add(str(matter_id))

            for batch in batches(tuple(sorted(matter_ids))):
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    "SELECT next_stage, terminal, ui_reachable, blocked "
                    "FROM matter_hierarchy_stage_index WHERE matter_id IN ("
                    + placeholders
                    + ")",
                    batch,
                ).fetchall()
                for next_stage, terminal, ui_reachable, blocked in rows:
                    key = "|".join(
                        (
                            str(next_stage) or "terminal",
                            "terminal" if bool(terminal) else "open",
                            "ui_reachable" if bool(ui_reachable) else "ui_pending",
                            "blocked" if bool(blocked) else "unblocked",
                        )
                    )
                    matter_stage_counts[key] = matter_stage_counts.get(key, 0) + 1

        inventory_hits = set(inventory_scopes)
        manifest_only = expected - coverage_hits
        for stage_id, counts in stage_counts.items():
            indexed = sum(counts.values())
            not_required = len(coverage_hits) - indexed
            if not_required:
                counts["not_required"] = not_required
            if manifest_only:
                counts["manifest_only"] = len(manifest_only)
            stage_counts[stage_id] = dict(sorted(counts.items()))

        ambiguous_inventory = {
            object_id
            for object_id, bound_scopes in inventory_scopes.items()
            if len(bound_scopes) > 1
        }
        conflicting_dispositions = {
            object_id
            for object_id, dispositions in inventory_dispositions.items()
            if len(dispositions) > 1
        }
        return {
            "expected_identity_count": len(expected),
            "fixed_scope": {
                "scope_count": len(scopes),
                "inventory_identity_count": len(fixed_hits),
                "inventory_occurrence_count": fixed_occurrences,
                "missing_identity_count": len(expected - fixed_hits),
                "set_equal": fixed_hits == expected,
            },
            "cross_scope": {
                "inventory_identity_count": len(inventory_hits),
                "cross_scope_only_identity_count": len(inventory_hits - fixed_hits),
                "missing_identity_count": len(expected - inventory_hits),
                "ambiguous_identity_count": len(ambiguous_inventory),
                "conflicting_disposition_identity_count": len(
                    conflicting_dispositions
                ),
            },
            "coverage": {
                "identity_count": len(coverage_hits),
                "missing_identity_count": len(expected - coverage_hits),
                "set_equal": coverage_hits == expected,
                "disposition_counts": dict(sorted(coverage_dispositions.items())),
                "next_stage_counts": dict(sorted(next_stage_counts.items())),
                "terminal_identity_count": terminal_count,
                "ui_ready_identity_count": ui_ready_count,
                "blocked_identity_count": blocked_count,
            },
            "stage_counts": stage_counts,
            "matter_modeling": {
                "linked_identity_count": len(matter_linked),
                "distinct_matter_count": len(matter_ids),
                "stage_counts": dict(sorted(matter_stage_counts.items())),
            },
            "set_fingerprints": {
                "expected": fingerprint(expected),
                "fixed_scope_inventory": fingerprint(fixed_hits),
                "cross_scope_inventory": fingerprint(inventory_hits),
                "cross_scope_ambiguous": fingerprint(ambiguous_inventory),
                "coverage": fingerprint(coverage_hits),
                "manifest_only": fingerprint(manifest_only),
            },
        }

    def coverage_index_page(
        self,
        *,
        offset: int,
        limit: int,
        next_stage: str = "",
    ) -> tuple[tuple[dict[str, Any], ...], int]:
        """Read one bounded progress page without decoding full ledger rows."""

        if offset < 0 or limit < 1 or limit > 200:
            raise ValueError("coverage index page bounds are invalid")
        where = (
            "WHERE active=1 AND next_stage=?"
            if next_stage
            else "WHERE active=1"
        )
        parameters: tuple[Any, ...] = (next_stage,) if next_stage else ()
        with self.connection() as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM coverage_stage_index " + where,
                    parameters,
                ).fetchone()[0]
            )
            rows = connection.execute(
                "SELECT object_id, provider, object_type, disposition, "
                "next_stage, terminal, ui_ready, blocked, revision, updated_at "
                "FROM coverage_stage_index "
                + where
                + " ORDER BY object_id LIMIT ? OFFSET ?",
                (*parameters, limit, offset),
            ).fetchall()
        keys = (
            "object_id",
            "provider",
            "object_type",
            "disposition",
            "next_stage",
            "terminal",
            "ui_ready",
            "blocked",
            "revision",
            "updated_at",
        )
        return (
            tuple(
                {
                    **dict(zip(keys, row)),
                    "terminal": bool(row[5]),
                    "ui_ready": bool(row[6]),
                    "blocked": bool(row[7]),
                }
                for row in rows
            ),
            total,
        )

    def coverage_audit_page(
        self,
        *,
        offset: int,
        limit: int,
        object_kind: str,
        stage_order: Iterable[str],
    ) -> dict[str, Any]:
        """Aggregate active current coverage and hydrate only one audit page."""

        stages = tuple(dict.fromkeys(str(item) for item in stage_order if str(item)))
        if (
            offset < 0
            or limit < 1
            or limit > 200
            or object_kind not in {"", "occurrence", "matter"}
            or not stages
            or any(
                not stage_id.replace("_", "").isalnum()
                for stage_id in stages
            )
        ):
            raise ValueError("coverage audit query is invalid")
        kind_clause = ""
        if object_kind == "matter":
            kind_clause = " AND candidate.provider='matters'"
        elif object_kind == "occurrence":
            kind_clause = " AND candidate.provider<>'matters'"
        where = "WHERE 1=1" + kind_clause + " "
        candidate_cte = (
            "WITH candidate AS ("
            "SELECT coverage.object_id, coverage.provider, "
            "coverage.object_type, coverage.terminal, coverage.ui_ready, "
            "coverage.blocked, coverage.revision, coverage.updated_at, "
            "coverage.first_gap_stage, coverage.first_gap_status, "
            "coverage.first_gap_owner_id, "
            "coverage.first_gap_failure_class, "
            "coverage.first_gap_input_fingerprint, "
            "coverage.first_gap_updated_at, "
            "coverage.first_gap_indexed_revision, "
            "CASE WHEN current.revision IS NOT NULL "
            "AND coverage.revision=current.revision "
            "AND coverage.first_gap_indexed_revision=current.revision "
            "THEN 1 ELSE 0 END AS index_current "
            "FROM coverage_stage_index coverage "
            "LEFT JOIN current_objects current "
            "ON current.owner='object_coverage' "
            "AND current.object_id=coverage.object_id "
            "WHERE coverage.active=1 OR (current.revision IS NOT NULL "
            "AND coverage.revision<>current.revision) "
            "UNION ALL "
            "SELECT current.object_id, "
            "COALESCE(CAST(json_extract(snapshot.payload, '$.provider') "
            "AS TEXT), ''), "
            "COALESCE(CAST(json_extract(snapshot.payload, '$.object_type') "
            "AS TEXT), ''), 0, 0, 0, "
            "current.revision, '', '', '', '', '', '', '', 0, 0 "
            "FROM current_objects current "
            "JOIN snapshots snapshot "
            "ON snapshot.owner=current.owner "
            "AND snapshot.object_id=current.object_id "
            "AND snapshot.revision=current.revision "
            "LEFT JOIN coverage_stage_index coverage "
            "ON coverage.object_id=current.object_id "
            "WHERE current.owner='object_coverage' "
            "AND coverage.object_id IS NULL"
            ") "
        )
        with self.connection() as connection:
            aggregate = connection.execute(
                candidate_cte + "SELECT COUNT(*), "
                "COALESCE(SUM(CASE WHEN candidate.provider<>'matters' "
                "THEN 1 ELSE 0 END), 0), "
                "COALESCE(SUM(CASE WHEN candidate.provider='matters' "
                "THEN 1 ELSE 0 END), 0), "
                "COALESCE(SUM(CASE WHEN candidate.index_current=1 "
                "THEN candidate.ui_ready ELSE 0 END), 0), "
                "COALESCE(SUM(CASE WHEN candidate.index_current=1 "
                "THEN candidate.blocked ELSE 0 END), 0), "
                "COALESCE(SUM(candidate.index_current), 0) "
                "FROM candidate " + where,
            ).fetchone()
            index_rows = connection.execute(
                candidate_cte
                + "SELECT candidate.object_id, candidate.provider, "
                "candidate.object_type, candidate.terminal, "
                "candidate.ui_ready, candidate.blocked, "
                "candidate.revision, candidate.updated_at, "
                "candidate.first_gap_stage, candidate.first_gap_status, "
                "candidate.first_gap_owner_id, "
                "candidate.first_gap_failure_class, "
                "candidate.first_gap_input_fingerprint, "
                "candidate.first_gap_updated_at, "
                "candidate.first_gap_indexed_revision, "
                "candidate.index_current FROM candidate "
                + where
                + " ORDER BY candidate.object_id LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            total_objects = int(aggregate[0])
            indexed_objects = int(aggregate[5])
            state = connection.execute(
                "SELECT generation, updated_at "
                "FROM coverage_audit_index_state WHERE singleton_id=1"
            ).fetchone()
            stage_counts: dict[str, dict[str, int]] = {
                stage_id: {
                    "not_applicable": indexed_objects,
                    "unindexed": total_objects - indexed_objects,
                }
                for stage_id in stages
            }
            placeholders = ",".join("?" for _ in stages)
            for stage_id, status, count in connection.execute(
                candidate_cte
                + "SELECT stage.stage_id, stage.status, COUNT(*) "
                "FROM coverage_stage_status_index stage "
                "JOIN candidate "
                "ON candidate.object_id=stage.object_id "
                "AND candidate.revision=stage.coverage_revision "
                "AND candidate.index_current=1 "
                + where
                + f"AND stage.stage_id IN ({placeholders}) "
                "GROUP BY stage.stage_id, stage.status",
                stages,
            ):
                normalized_stage = str(stage_id)
                normalized_status = str(status)
                normalized_count = int(count)
                stage_counts[normalized_stage][normalized_status] = (
                    stage_counts[normalized_stage].get(
                        normalized_status,
                        0,
                    )
                    + normalized_count
                )
                stage_counts[normalized_stage]["not_applicable"] -= (
                    normalized_count
                )
            page_ids = tuple(str(row[0]) for row in index_rows)
            page_stage_rows: list[tuple[Any, ...]] = []
            if page_ids:
                page_placeholders = ",".join("?" for _ in page_ids)
                page_stage_rows = connection.execute(
                    "SELECT stage.object_id, stage.stage_id, stage.status "
                    "FROM coverage_stage_status_index stage "
                    "JOIN coverage_stage_index coverage "
                    "ON coverage.object_id=stage.object_id "
                    "AND coverage.revision=stage.coverage_revision "
                    "JOIN current_objects current "
                    "ON current.owner='object_coverage' "
                    "AND current.object_id=coverage.object_id "
                    "AND current.revision=coverage.revision "
                    f"WHERE stage.object_id IN ({page_placeholders}) "
                    "AND coverage.first_gap_indexed_revision="
                    "current.revision "
                    "ORDER BY stage.object_id, stage.stage_id",
                    page_ids,
                ).fetchall()
        page_stages: dict[str, dict[str, str]] = {}
        for object_id, stage_id, status in page_stage_rows:
            page_stages.setdefault(str(object_id), {})[
                str(stage_id)
            ] = str(status)
        revision_fingerprint = (
            "sha256:"
            + sha256(
                _canonical_json(
                    {
                        "generation": (
                            int(state[0]) if state is not None else 0
                        ),
                        "state_updated_at": (
                            str(state[1]) if state is not None else ""
                        ),
                        "object_kind": object_kind,
                        "total_objects": total_objects,
                        "indexed_objects": indexed_objects,
                    }
                ).encode("utf-8")
            ).hexdigest()
        )
        return {
            "total_objects": total_objects,
            "occurrence_objects": int(aggregate[1]),
            "matter_objects": int(aggregate[2]),
            "ui_ready_objects": int(aggregate[3]),
            "blocked_objects": int(aggregate[4]),
            "indexed_objects": indexed_objects,
            "unindexed_objects": total_objects - indexed_objects,
            "index_status": (
                "current"
                if indexed_objects == total_objects
                else "partial"
            ),
            "stage_counts": stage_counts,
            "revision_fingerprint": revision_fingerprint,
            "rows": tuple(
                {
                    "index": {
                        "object_id": str(row[0]),
                        "provider": str(row[1]),
                        "object_type": str(row[2]),
                        "terminal": bool(row[3]),
                        "ui_ready": bool(row[4]),
                        "blocked": bool(row[5]),
                        "revision": int(row[6]),
                        "updated_at": str(row[7]),
                        "first_gap_stage": str(row[8]),
                        "first_gap_status": str(row[9]),
                        "first_gap_owner_id": str(row[10]),
                        "first_gap_failure_class": str(row[11]),
                        "first_gap_input_fingerprint": str(row[12]),
                        "first_gap_updated_at": str(row[13]),
                        "index_current": bool(row[15]),
                    },
                    "stages": page_stages.get(str(row[0]), {}),
                }
                for row in index_rows
            ),
        }

    def matter_coverage_ui_ready(self, matter_id: str) -> bool:
        """Confirm that a Matter has at least one UI-ready source path."""

        if not matter_id:
            return False
        with self.connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM coverage_matter_index relation "
                "JOIN coverage_stage_index coverage "
                "ON coverage.object_id=relation.object_id "
                "WHERE relation.matter_id=? AND coverage.active=1 "
                "AND coverage.ui_ready=1 LIMIT 1",
                (matter_id,),
            ).fetchone()
        return row is not None

    def matter_hierarchy_summary_counts(self) -> dict[str, int]:
        """Read hierarchy readiness counts without decoding audit payloads."""

        with self.connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(terminal), 0), "
                "COALESCE(SUM(ui_reachable), 0), "
                "COALESCE(SUM(blocked), 0) "
                "FROM matter_hierarchy_stage_index idx "
                "JOIN current_objects admission_current "
                "ON admission_current.owner='admission_decision' "
                "AND admission_current.object_id=idx.matter_id "
                "JOIN snapshots admission "
                "ON admission.owner=admission_current.owner "
                "AND admission.object_id=admission_current.object_id "
                "AND admission.revision=admission_current.revision "
                "WHERE json_extract(admission.payload, '$.status')="
                "'admitted' AND CAST(json_extract(admission.payload, "
                "'$.matter.matter_id') AS TEXT)=idx.matter_id "
                "AND COALESCE(json_extract(admission.payload, "
                "'$.matter.admitted'), 1)=1"
            ).fetchone()
        total = int(row[0])
        terminal = int(row[1])
        reachable = int(row[2])
        blocked = int(row[3])
        return {
            "registered_matter_count": total,
            "hierarchy_terminal_matter_count": terminal,
            "ui_reachable_matter_count": reachable,
            "hierarchy_blocked_matter_count": blocked,
            "hierarchy_pending_matter_count": total - terminal,
            "hierarchy_current_matter_count": reachable,
        }

    def matter_hierarchy_audit_page(
        self,
        *,
        offset: int,
        limit: int,
        next_stage: str = "",
    ) -> tuple[tuple[dict[str, Any], ...], int]:
        """Return one bounded hierarchy audit page from materialized indexes."""

        if offset < 0 or limit < 1 or limit > 200:
            raise ValueError("hierarchy audit page bounds are invalid")
        stage_filter = "AND idx.next_stage=? " if next_stage else ""
        parameters: tuple[Any, ...] = (next_stage,) if next_stage else ()
        canonical_join = (
            " FROM matter_hierarchy_stage_index idx "
            "JOIN current_objects c "
            "ON c.owner='matter_hierarchy_audit' "
            "AND c.object_id=idx.matter_id "
            "JOIN snapshots s ON s.owner=c.owner "
            "AND s.object_id=c.object_id AND s.revision=c.revision "
            "JOIN current_objects admission_current "
            "ON admission_current.owner='admission_decision' "
            "AND admission_current.object_id=idx.matter_id "
            "JOIN snapshots admission "
            "ON admission.owner=admission_current.owner "
            "AND admission.object_id=admission_current.object_id "
            "AND admission.revision=admission_current.revision "
            "WHERE json_extract(admission.payload, '$.status')='admitted' "
            "AND CAST(json_extract(admission.payload, "
            "'$.matter.matter_id') AS TEXT)=idx.matter_id "
            "AND COALESCE(json_extract(admission.payload, "
            "'$.matter.admitted'), 1)=1 "
            + stage_filter
        )
        with self.connection() as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*)" + canonical_join,
                    parameters,
                ).fetchone()[0]
            )
            rows = connection.execute(
                "SELECT idx.matter_id, idx.next_stage, idx.terminal, "
                "idx.ui_reachable, idx.blocked, idx.revision, "
                "idx.change_ref, s.payload "
                + canonical_join
                + "ORDER BY idx.matter_id LIMIT ? OFFSET ?",
                (*parameters, limit, offset),
            ).fetchall()
        return (
            tuple(
                {
                    "subject_kind": "matter",
                    "matter_id": str(row[0]),
                    "next_stage": str(row[1]),
                    "terminal": bool(row[2]),
                    "ui_reachable": bool(row[3]),
                    "blocked": bool(row[4]),
                    "revision": int(row[5]),
                    "change_ref": str(row[6]),
                    "stages": dict(json.loads(row[7]).get("stages", {})),
                }
                for row in rows
            ),
            total,
        )

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

    def pending_generated_hero_page(
        self,
        *,
        offset: int,
        limit: int,
    ) -> tuple[tuple[dict[str, Any], ...], int]:
        """Read a bounded private generated-hero work page."""

        if offset < 0 or limit < 1 or limit > 100:
            raise ValueError("generated hero page bounds are invalid")
        predicate = (
            "c.owner='generated_hero_record' "
            "AND json_extract(s.payload, '$.status')="
            "'generation_pending_placeholder' "
            "AND COALESCE(json_extract(s.payload, '$.brief_fingerprint'), '')"
            "<>'' "
            "AND COALESCE(json_extract(s.payload, '$.retryable'), 1)=1"
        )
        with self.connection() as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM current_objects c "
                    "JOIN snapshots s ON s.owner=c.owner "
                    "AND s.object_id=c.object_id "
                    "AND s.revision=c.revision WHERE "
                    + predicate
                ).fetchone()[0]
            )
            rows = connection.execute(
                "SELECT s.payload FROM current_objects c "
                "JOIN snapshots s ON s.owner=c.owner "
                "AND s.object_id=c.object_id "
                "AND s.revision=c.revision WHERE "
                + predicate
                + " ORDER BY c.object_id LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return tuple(json.loads(str(row[0])) for row in rows), total

    def object_browser_catalog_page(
        self,
        *,
        locale: str,
        query: str,
        status: str,
        root_only: bool,
        start_year: str,
        people: Iterable[str],
        relationships: Iterable[str],
        topic_types: Iterable[str],
        source_types: Iterable[str],
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        """Filter, sort, and page the Matter catalog before payload hydration.

        Temporary relational projections keep the current JSON snapshot store
        authoritative while ensuring the presentation layer receives only the
        exact visible Matter ids. They intentionally disappear with the read
        connection; there is no second catalog authority or compatibility path.
        """

        if (
            locale not in {"en", "zh-CN"}
            or status not in {"all", "planned", "in_progress", "completed"}
            or start_year != "all"
            and (len(start_year) != 4 or not start_year.isdigit())
            or offset < 0
            or limit < 1
            or limit > 200
        ):
            raise ValueError("object browser catalog query is invalid")
        selected = {
            "people": tuple(
                dict.fromkeys(
                    _normalized_facet_value(item)
                    for item in people
                    if _normalized_facet_value(item)
                )
            ),
            "relationships": tuple(
                dict.fromkeys(
                    _normalized_facet_value(item)
                    for item in relationships
                    if _normalized_facet_value(item)
                )
            ),
            "topic_types": tuple(
                dict.fromkeys(
                    _normalized_facet_value(item)
                    for item in topic_types
                    if _normalized_facet_value(item)
                )
            ),
            "source_types": tuple(
                dict.fromkeys(
                    _normalized_facet_value(item)
                    for item in source_types
                    if _normalized_facet_value(item)
                )
            ),
        }
        normalized_query = str(query).strip().casefold()
        activity_valid = (
            "aps.payload IS NOT NULL "
            "AND COALESCE(json_extract(aps.payload, '$.matter_id'), '')="
            "p.object_id "
            "AND COALESCE(json_extract(aps.payload, '$.source_matter_id'), '')"
            "<>'' "
            "AND COALESCE(json_extract(aps.payload, '$.material_clue_id'), '')"
            "<>'' "
            "AND julianday(json_extract("
            "aps.payload, '$.latest_meaningful_clue_at')) IS NOT NULL "
            "AND COALESCE(CAST(json_extract("
            "aps.payload, '$.persistence_revision') AS INTEGER), 0)>=1 "
            "AND COALESCE(json_extract("
            "aps.payload, '$.material_clue_revision'), '')<>'' "
            "AND json_extract(aps.payload, '$.material_clue_revision')="
            "json_extract(aps.payload, '$.summary_revision') "
            "AND json_extract(aps.payload, '$.material_clue_revision')="
            "json_extract(aps.payload, '$.activity_order_revision') "
            "AND COALESCE(json_extract("
            "aps.payload, '$.localized_summary.en'), '')<>'' "
            "AND COALESCE(json_extract("
            "aps.payload, '$.localized_summary.\"zh-CN\"'), '')<>''"
        )
        temporary_tables = (
            "temp_object_browser_path_title",
            "temp_object_browser_topic",
            "temp_object_browser_source",
            "temp_object_browser_relation",
            "temp_object_browser_people",
            "temp_object_browser_person_link",
            "temp_object_browser_event_link",
            "temp_object_browser_start_candidate",
            "temp_object_browser_evidence",
            "temp_object_browser_eligible",
        )
        with self.connection() as connection:
            connection.create_function(
                "matters_facet_value",
                1,
                _normalized_facet_value,
                deterministic=True,
            )
            connection.create_function(
                "matters_contains",
                2,
                lambda value, needle: int(
                    str(needle or "").casefold()
                    in str(value or "").casefold()
                ),
                deterministic=True,
            )
            connection.create_function(
                "matters_start_time_field",
                1,
                _start_time_field,
                deterministic=True,
            )
            connection.create_function(
                "matters_temporal_iso",
                2,
                _normalized_temporal_iso,
                deterministic=True,
            )
            connection.create_function(
                "matters_source_ref_id",
                1,
                _source_ref_id,
                deterministic=True,
            )
            connection.create_function(
                "matters_source_ref_version",
                1,
                _source_ref_version,
                deterministic=True,
            )
            for table in temporary_tables:
                connection.execute(f"DROP TABLE IF EXISTS {table}")
            try:
                connection.execute(
                    "CREATE TEMP TABLE temp_object_browser_eligible AS "
                    "SELECT p.object_id AS matter_id, "
                    "ps.payload AS projection_payload, "
                    "admission_payload.payload AS admission_payload, "
                    "p.revision AS projection_revision, "
                    "CASE WHEN "
                    + activity_valid
                    + " THEN a.revision ELSE 0 END AS activity_revision, "
                    "CASE WHEN "
                    + activity_valid
                    + " THEN aps.payload ELSE NULL END AS activity_payload, "
                    "COALESCE(h.revision, 0) AS hero_revision, "
                    "COALESCE(hierarchy_projection.revision, 0) "
                    "AS hierarchy_revision, "
                    "COALESCE(CAST(json_extract("
                    "hierarchy_projection_payload.payload, '$.child_count') "
                    "AS INTEGER), 0) AS child_count, "
                    "CASE "
                    "WHEN lower(COALESCE(json_extract("
                    "ps.payload, '$.state'), 'uncertain')) "
                    "IN ('completed','cancelled','abandoned','closed') "
                    "THEN 'completed' "
                    "WHEN lower(COALESCE(json_extract("
                    "ps.payload, '$.state'), 'uncertain')) "
                    "IN ('in_progress','active','waiting','blocked',"
                    "'partially_blocked') THEN 'in_progress' "
                    "ELSE 'planned' END AS status_group, "
                    "CASE WHEN "
                    + activity_valid
                    + " THEN CAST(json_extract("
                    "aps.payload, '$.latest_meaningful_clue_at') AS TEXT) "
                    "ELSE '' END AS activity_at, "
                    "CASE WHEN EXISTS ("
                    "SELECT 1 FROM matter_hierarchy_index hierarchy "
                    "WHERE hierarchy.child_matter_id=p.object_id "
                    "AND hierarchy.freshness='current'"
                    ") THEN 1 ELSE 0 END AS parented, "
                    "'' AS start_time, '' AS start_year "
                    "FROM current_objects p "
                    "CROSS JOIN snapshots ps ON ps.owner=p.owner "
                    "AND ps.object_id=p.object_id "
                    "AND ps.revision=p.revision "
                    "LEFT JOIN current_objects admission "
                    "ON admission.owner='admission_decision' "
                    "AND admission.object_id=p.object_id "
                    "LEFT JOIN snapshots admission_payload "
                    "ON admission_payload.owner=admission.owner "
                    "AND admission_payload.object_id=admission.object_id "
                    "AND admission_payload.revision=admission.revision "
                    "LEFT JOIN current_objects a "
                    "ON a.owner='matter_activity' "
                    "AND a.object_id=p.object_id "
                    "LEFT JOIN snapshots aps ON aps.owner=a.owner "
                    "AND aps.object_id=a.object_id "
                    "AND aps.revision=a.revision "
                    "LEFT JOIN current_objects h "
                    "ON h.owner='generated_hero_record' "
                    "AND h.object_id=p.object_id "
                    "LEFT JOIN current_objects hierarchy_projection "
                    "ON hierarchy_projection.owner="
                    "'matter_hierarchy_projection' "
                    "AND hierarchy_projection.object_id=p.object_id "
                    "LEFT JOIN snapshots hierarchy_projection_payload "
                    "ON hierarchy_projection_payload.owner="
                    "hierarchy_projection.owner "
                    "AND hierarchy_projection_payload.object_id="
                    "hierarchy_projection.object_id "
                    "AND hierarchy_projection_payload.revision="
                    "hierarchy_projection.revision "
                    "WHERE p.owner='projection' "
                    "AND json_extract("
                    "ps.payload, '$.equivalence_status')='equivalent' "
                    "AND json_extract("
                    "admission_payload.payload, '$.status')='admitted' "
                    "AND CAST(json_extract(admission_payload.payload, "
                    "'$.matter.matter_id') AS TEXT)=p.object_id "
                    "AND COALESCE(json_extract(admission_payload.payload, "
                    "'$.matter.admitted'), 1)=1"
                )
                connection.execute(
                    "CREATE UNIQUE INDEX temp_object_browser_eligible_id_idx "
                    "ON temp_object_browser_eligible(matter_id)"
                )
                eligible_matter_ids = tuple(
                    str(row[0])
                    for row in connection.execute(
                        "SELECT matter_id FROM temp_object_browser_eligible "
                        "ORDER BY matter_id"
                    )
                )
                invalidated_matter_outputs = (
                    self.invalidated_analysis_output_refs(
                        output_ref
                        for matter_id in eligible_matter_ids
                        for output_ref in (
                            f"projection:{matter_id}",
                            f"admission_decision:{matter_id}",
                        )
                    )
                )
                stale_matter_ids = tuple(
                    matter_id
                    for matter_id in eligible_matter_ids
                    if f"projection:{matter_id}"
                    in invalidated_matter_outputs
                    or f"admission_decision:{matter_id}"
                    in invalidated_matter_outputs
                )
                if stale_matter_ids:
                    connection.executemany(
                        "DELETE FROM temp_object_browser_eligible "
                        "WHERE matter_id=?",
                        ((matter_id,) for matter_id in stale_matter_ids),
                    )
                connection.execute(
                    "CREATE INDEX temp_object_browser_eligible_scope_idx "
                    "ON temp_object_browser_eligible"
                    "(parented, status_group, start_year, matter_id)"
                )
                connection.execute(
                    "CREATE TEMP TABLE temp_object_browser_evidence "
                    "(matter_id TEXT NOT NULL, evidence_id TEXT NOT NULL, "
                    "PRIMARY KEY(matter_id, evidence_id))"
                )
                connection.execute(
                    "INSERT OR IGNORE INTO temp_object_browser_evidence "
                    "SELECT eligible.matter_id, CAST(evidence.value AS TEXT) "
                    "FROM temp_object_browser_eligible eligible "
                    "JOIN json_each("
                    "eligible.projection_payload, '$.evidence_ids') evidence "
                    "WHERE COALESCE(CAST(evidence.value AS TEXT), '')<>''"
                )
                connection.execute(
                    "CREATE INDEX temp_object_browser_evidence_value_idx "
                    "ON temp_object_browser_evidence(evidence_id, matter_id)"
                )
                connection.execute(
                    "CREATE TEMP TABLE temp_object_browser_event_link "
                    "(matter_id TEXT NOT NULL, event_id TEXT NOT NULL, "
                    "event_payload TEXT NOT NULL, "
                    "PRIMARY KEY(matter_id, event_id))"
                )
                connection.execute(
                    "INSERT OR IGNORE INTO temp_object_browser_event_link "
                    "SELECT eligible.matter_id, event.object_id, es.payload "
                    "FROM temp_object_browser_eligible eligible "
                    "CROSS JOIN current_objects event "
                    "ON event.owner='temporal_event' "
                    "CROSS JOIN snapshots es ON es.owner=event.owner "
                    "AND es.object_id=event.object_id "
                    "AND es.revision=event.revision "
                    "AND CAST(json_extract("
                    "es.payload, '$.object_ref') AS TEXT)=eligible.matter_id"
                )
                connection.execute(
                    "INSERT OR IGNORE INTO temp_object_browser_event_link "
                    "SELECT evidence.matter_id, event.object_id, es.payload "
                    "FROM current_objects event "
                    "CROSS JOIN snapshots es ON es.owner=event.owner "
                    "AND es.object_id=event.object_id "
                    "AND es.revision=event.revision "
                    "CROSS JOIN json_each("
                    "es.payload, '$.evidence_ids') event_evidence "
                    "CROSS JOIN temp_object_browser_evidence evidence "
                    "ON evidence.evidence_id="
                    "CAST(event_evidence.value AS TEXT) "
                    "WHERE event.owner='temporal_event'"
                )
                connection.execute(
                    "CREATE TEMP TABLE temp_object_browser_start_candidate "
                    "(matter_id TEXT NOT NULL, time_value TEXT NOT NULL, "
                    "basis TEXT NOT NULL, provider TEXT NOT NULL DEFAULT '')"
                )
                connection.execute(
                    "INSERT INTO temp_object_browser_start_candidate "
                    "SELECT matter_id, matters_temporal_iso("
                    "json_extract(event_payload, '$.claimed_time'), "
                    "'claimed_time'), 'event_claimed_time', '' "
                    "FROM temp_object_browser_event_link "
                    "WHERE matters_temporal_iso("
                    "json_extract(event_payload, '$.claimed_time'), "
                    "'claimed_time')<>''"
                )
                connection.execute(
                    "INSERT INTO temp_object_browser_start_candidate "
                    "SELECT matter_id, matters_temporal_iso("
                    "json_extract(event_payload, '$.record_time'), "
                    "'record_time'), 'event_record_time', '' "
                    "FROM temp_object_browser_event_link "
                    "WHERE matters_temporal_iso("
                    "json_extract(event_payload, '$.record_time'), "
                    "'record_time')<>''"
                )
                for source_path in (
                    "$.source_time_metadata",
                    "$.content",
                    "$.content.metadata",
                    "$.content.headers",
                ):
                    connection.execute(
                        "INSERT INTO temp_object_browser_start_candidate "
                        "SELECT eligible.matter_id, matters_temporal_iso("
                        "source_time.value, source_time.key), "
                        "'source_' || lower(CAST(source_time.key AS TEXT)), "
                        "CAST(COALESCE(json_extract("
                        "source_snapshot.payload, '$.provider'), '') AS TEXT) "
                        "FROM temp_object_browser_eligible eligible "
                        "CROSS JOIN json_each("
                        "eligible.admission_payload, '$.matter.source_ids') "
                        "source_ref "
                        "CROSS JOIN snapshots source_snapshot "
                        "ON source_snapshot.owner='source_version' "
                        "AND source_snapshot.object_id="
                        "matters_source_ref_id(source_ref.value) "
                        "AND source_snapshot.revision="
                        "matters_source_ref_version(source_ref.value) "
                        f"CROSS JOIN json_each(source_snapshot.payload, "
                        f"'{source_path}') source_time "
                        "WHERE matters_start_time_field(source_time.key)=1 "
                        "AND matters_temporal_iso("
                        "source_time.value, source_time.key)<>''"
                    )
                connection.execute(
                    "INSERT INTO temp_object_browser_start_candidate "
                    "SELECT eligible.matter_id, matters_temporal_iso("
                    "source_time.value, source_time.key), "
                    "'inventory_' || lower(CAST(source_time.key AS TEXT)), "
                    "CAST(COALESCE(json_extract("
                    "source_snapshot.payload, '$.provider'), '') AS TEXT) "
                    "FROM temp_object_browser_eligible eligible "
                    "CROSS JOIN json_each("
                    "eligible.admission_payload, '$.matter.source_ids') "
                    "source_ref "
                    "CROSS JOIN snapshots source_snapshot "
                    "ON source_snapshot.owner='source_version' "
                    "AND source_snapshot.object_id="
                    "matters_source_ref_id(source_ref.value) "
                    "AND source_snapshot.revision="
                    "matters_source_ref_version(source_ref.value) "
                    "CROSS JOIN inventory_occurrence_current occurrence "
                    "ON occurrence.object_id=CAST(json_extract("
                    "source_snapshot.payload, "
                    "'$.external_reference.external_id') AS TEXT) "
                    "CROSS JOIN json_each("
                    "occurrence.occurrence_payload, '$.metadata') source_time "
                    "WHERE matters_start_time_field(source_time.key)=1 "
                    "AND matters_temporal_iso("
                    "source_time.value, source_time.key)<>''"
                )
                connection.execute(
                    "CREATE INDEX temp_object_browser_start_candidate_idx "
                    "ON temp_object_browser_start_candidate"
                    "(matter_id, time_value, basis, provider)"
                )
                connection.execute(
                    "UPDATE temp_object_browser_eligible "
                    "SET start_time=COALESCE(("
                    "SELECT candidate.time_value "
                    "FROM temp_object_browser_start_candidate candidate "
                    "WHERE candidate.matter_id="
                    "temp_object_browser_eligible.matter_id "
                    "ORDER BY julianday(candidate.time_value), "
                    "candidate.basis, candidate.provider LIMIT 1"
                    "), '')"
                )
                connection.execute(
                    "UPDATE temp_object_browser_eligible "
                    "SET start_year=CASE WHEN start_time<>'' "
                    "THEN strftime('%Y', start_time) ELSE '' END"
                )
                connection.execute(
                    "CREATE TEMP TABLE temp_object_browser_person_link "
                    "(matter_id TEXT NOT NULL, person_id TEXT NOT NULL, "
                    "display_name TEXT NOT NULL, resolved INTEGER NOT NULL, "
                    "PRIMARY KEY(matter_id, person_id))"
                )
                connection.execute(
                    "INSERT OR IGNORE INTO temp_object_browser_person_link "
                    "SELECT evidence.matter_id, person.object_id, "
                    "CAST(COALESCE(json_extract("
                    "ps.payload, '$.display_name'), '') AS TEXT), "
                    "COALESCE(CAST(json_extract("
                    "ps.payload, '$.resolved') AS INTEGER), 0) "
                    "FROM current_objects person "
                    "CROSS JOIN snapshots ps ON ps.owner=person.owner "
                    "AND ps.object_id=person.object_id "
                    "AND ps.revision=person.revision "
                    "CROSS JOIN temp_object_browser_evidence evidence "
                    "ON evidence.evidence_id=CAST(json_extract("
                    "ps.payload, '$.evidence_ref') AS TEXT) "
                    "WHERE person.owner='person_candidate'"
                )
                connection.execute(
                    "INSERT OR IGNORE INTO temp_object_browser_person_link "
                    "SELECT evidence.matter_id, person.object_id, "
                    "CAST(COALESCE(json_extract("
                    "ps.payload, '$.display_name'), '') AS TEXT), "
                    "COALESCE(CAST(json_extract("
                    "ps.payload, '$.resolved') AS INTEGER), 0) "
                    "FROM current_objects person "
                    "CROSS JOIN snapshots ps ON ps.owner=person.owner "
                    "AND ps.object_id=person.object_id "
                    "AND ps.revision=person.revision "
                    "CROSS JOIN json_each("
                    "ps.payload, '$.evidence_ids') person_evidence "
                    "CROSS JOIN temp_object_browser_evidence evidence "
                    "ON evidence.evidence_id="
                    "CAST(person_evidence.value AS TEXT) "
                    "WHERE person.owner='person_candidate'"
                )
                connection.execute(
                    "CREATE TEMP TABLE temp_object_browser_people AS "
                    "SELECT matter_id, person_id, display_name, resolved, "
                    "ROW_NUMBER() OVER (PARTITION BY matter_id "
                    "ORDER BY display_name, person_id) AS rank "
                    "FROM temp_object_browser_person_link "
                    "WHERE trim(display_name)<>''"
                )
                connection.execute(
                    "CREATE INDEX temp_object_browser_people_lookup_idx "
                    "ON temp_object_browser_people"
                    "(matter_id, rank, display_name)"
                )
                connection.execute(
                    "CREATE TEMP TABLE temp_object_browser_relation "
                    "(matter_id TEXT NOT NULL, relation_type TEXT NOT NULL, "
                    "PRIMARY KEY(matter_id, relation_type))"
                )
                connection.execute(
                    "INSERT OR IGNORE INTO temp_object_browser_relation "
                    "SELECT eligible.matter_id, CAST(COALESCE(json_extract("
                    "rs.payload, '$.relation_type'), 'relates') AS TEXT) "
                    "FROM current_objects relation "
                    "CROSS JOIN snapshots rs ON rs.owner=relation.owner "
                    "AND rs.object_id=relation.object_id "
                    "AND rs.revision=relation.revision "
                    "CROSS JOIN temp_object_browser_eligible eligible "
                    "ON eligible.matter_id=CAST(json_extract("
                    "rs.payload, '$.source_matter_id') AS TEXT) "
                    "OR eligible.matter_id=CAST(json_extract("
                    "rs.payload, '$.target_matter_id') AS TEXT) "
                    "WHERE relation.owner='relation_candidate'"
                )
                connection.execute(
                    "CREATE TEMP TABLE temp_object_browser_source "
                    "(matter_id TEXT NOT NULL, source_type TEXT NOT NULL, "
                    "PRIMARY KEY(matter_id, source_type))"
                )
                connection.execute(
                    "INSERT OR IGNORE INTO temp_object_browser_source "
                    "SELECT eligible.matter_id, CAST(COALESCE(json_extract("
                    "cs.payload, '$.object_type'), 'information') AS TEXT) "
                    "FROM temp_object_browser_eligible eligible "
                    "CROSS JOIN coverage_matter_index coverage "
                    "ON coverage.matter_id=eligible.matter_id "
                    "CROSS JOIN current_objects current_coverage "
                    "ON current_coverage.owner='object_coverage' "
                    "AND current_coverage.object_id=coverage.object_id "
                    "CROSS JOIN snapshots cs "
                    "ON cs.owner=current_coverage.owner "
                    "AND cs.object_id=current_coverage.object_id "
                    "AND cs.revision=current_coverage.revision"
                )
                connection.execute(
                    "CREATE TEMP TABLE temp_object_browser_topic "
                    "(matter_id TEXT NOT NULL, topic_type TEXT NOT NULL, "
                    "label_en TEXT NOT NULL, label_zh_cn TEXT NOT NULL, "
                    "PRIMARY KEY(matter_id, topic_type))"
                )
                connection.execute(
                    "INSERT OR IGNORE INTO temp_object_browser_topic "
                    "SELECT eligible.matter_id, "
                    "CAST(json_extract(topic.value, '$.value') AS TEXT), "
                    "CAST(json_extract(topic.value, '$.label.en') AS TEXT), "
                    "CAST(json_extract("
                    "topic.value, '$.label.\"zh-CN\"') AS TEXT) "
                    "FROM temp_object_browser_eligible eligible "
                    "CROSS JOIN current_objects classification "
                    "ON classification.owner='matter_classification' "
                    "AND classification.object_id=eligible.matter_id "
                    "CROSS JOIN snapshots classification_payload "
                    "ON classification_payload.owner=classification.owner "
                    "AND classification_payload.object_id="
                    "classification.object_id "
                    "AND classification_payload.revision="
                    "classification.revision "
                    "CROSS JOIN json_each("
                    "classification_payload.payload, '$.topic_types') topic "
                    "WHERE COALESCE(json_extract(topic.value, '$.value'), '')<>'' "
                    "AND json_type(topic.value, '$.label.en')='text' "
                    "AND json_type("
                    "topic.value, '$.label.\"zh-CN\"')='text' "
                    "AND (SELECT COUNT(*) "
                    "FROM json_each(topic.value, '$.label'))=2"
                )
                connection.execute(
                    "CREATE TEMP TABLE temp_object_browser_path_title "
                    "(matter_id TEXT NOT NULL, path_matter_id TEXT NOT NULL, "
                    "title_en TEXT NOT NULL, title_zh_cn TEXT NOT NULL, "
                    "PRIMARY KEY(matter_id, path_matter_id))"
                )
                connection.execute(
                    "INSERT OR IGNORE INTO temp_object_browser_path_title "
                    "SELECT eligible.matter_id, CAST(path.value AS TEXT), "
                    "CAST(COALESCE(json_extract("
                    "path_projection.payload, '$.localized_values.en'), '') "
                    "AS TEXT), "
                    "CAST(COALESCE(json_extract(path_projection.payload, "
                    "'$.localized_values.\"zh-CN\"'), '') AS TEXT) "
                    "FROM temp_object_browser_eligible eligible "
                    "CROSS JOIN current_objects hierarchy "
                    "ON hierarchy.owner='matter_hierarchy_projection' "
                    "AND hierarchy.object_id=eligible.matter_id "
                    "CROSS JOIN snapshots hierarchy_payload "
                    "ON hierarchy_payload.owner=hierarchy.owner "
                    "AND hierarchy_payload.object_id=hierarchy.object_id "
                    "AND hierarchy_payload.revision=hierarchy.revision "
                    "CROSS JOIN json_each("
                    "hierarchy_payload.payload, '$.path') path "
                    "CROSS JOIN current_objects path_current "
                    "ON path_current.owner='projection' "
                    "AND path_current.object_id=CAST(path.value AS TEXT) "
                    "CROSS JOIN snapshots path_projection "
                    "ON path_projection.owner=path_current.owner "
                    "AND path_projection.object_id=path_current.object_id "
                    "AND path_projection.revision=path_current.revision"
                )

                scope_clause = "eligible.parented=0" if root_only else "1=1"
                predicates = [scope_clause]
                parameters: list[object] = []
                if status != "all":
                    predicates.append("eligible.status_group=?")
                    parameters.append(status)
                if start_year != "all":
                    predicates.append("eligible.start_year=?")
                    parameters.append(start_year)
                for value in selected["people"]:
                    predicates.append(
                        "EXISTS (SELECT 1 "
                        "FROM temp_object_browser_people people "
                        "WHERE people.matter_id=eligible.matter_id "
                        "AND people.rank<=4 "
                        "AND matters_facet_value(people.display_name)=?)"
                    )
                    parameters.append(value)
                for value in selected["relationships"]:
                    predicates.append(
                        "EXISTS (SELECT 1 "
                        "FROM temp_object_browser_relation relation "
                        "WHERE relation.matter_id=eligible.matter_id "
                        "AND matters_facet_value("
                        "relation.relation_type)=?)"
                    )
                    parameters.append(value)
                for value in selected["topic_types"]:
                    predicates.append(
                        "EXISTS (SELECT 1 "
                        "FROM temp_object_browser_topic topic "
                        "WHERE topic.matter_id=eligible.matter_id "
                        "AND matters_facet_value(topic.topic_type)=?)"
                    )
                    parameters.append(value)
                for value in selected["source_types"]:
                    predicates.append(
                        "EXISTS (SELECT 1 "
                        "FROM temp_object_browser_source source "
                        "WHERE source.matter_id=eligible.matter_id "
                        "AND matters_facet_value(source.source_type)=?)"
                    )
                    parameters.append(value)
                if normalized_query:
                    title_path = (
                        "$.localized_values.en"
                        if locale == "en"
                        else '$.localized_values."zh-CN"'
                    )
                    summary_path = (
                        "$.localized_rationale.en"
                        if locale == "en"
                        else '$.localized_rationale."zh-CN"'
                    )
                    activity_summary_path = (
                        "$.localized_summary.en"
                        if locale == "en"
                        else '$.localized_summary."zh-CN"'
                    )
                    path_title_column = (
                        "title_en" if locale == "en" else "title_zh_cn"
                    )
                    predicates.append(
                        "(matters_contains(json_extract("
                        "eligible.projection_payload, ?), ?)=1 "
                        "OR matters_contains(CASE "
                        "WHEN eligible.child_count=0 "
                        "AND eligible.activity_payload IS NOT NULL "
                        "THEN json_extract("
                        "eligible.activity_payload, ?) "
                        "ELSE json_extract("
                        "eligible.projection_payload, ?) END, ?)=1 "
                        "OR EXISTS (SELECT 1 "
                        "FROM temp_object_browser_people people "
                        "WHERE people.matter_id=eligible.matter_id "
                        "AND people.rank<=4 "
                        "AND matters_contains(people.display_name, ?)=1) "
                        "OR EXISTS (SELECT 1 "
                        "FROM temp_object_browser_path_title path_title "
                        "WHERE path_title.matter_id=eligible.matter_id "
                        f"AND matters_contains(path_title.{path_title_column}, "
                        "?)=1))"
                    )
                    parameters.extend(
                        (
                            title_path,
                            normalized_query,
                            activity_summary_path,
                            summary_path,
                            normalized_query,
                            normalized_query,
                            normalized_query,
                        )
                    )
                where = " AND ".join(predicates)
                total = int(
                    connection.execute(
                        "SELECT COUNT(*) "
                        "FROM temp_object_browser_eligible eligible "
                        f"WHERE {where}",
                        parameters,
                    ).fetchone()[0]
                )
                matter_ids = tuple(
                    str(row[0])
                    for row in connection.execute(
                        "SELECT eligible.matter_id "
                        "FROM temp_object_browser_eligible eligible "
                        f"WHERE {where} "
                        "ORDER BY COALESCE("
                        "julianday(eligible.activity_at), -1.0e100) DESC, "
                        "eligible.matter_id LIMIT ? OFFSET ?",
                        (*parameters, limit, offset),
                    ).fetchall()
                )
                status_counts = {
                    str(group): int(count)
                    for group, count in connection.execute(
                        "SELECT status_group, COUNT(*) "
                        "FROM temp_object_browser_eligible eligible "
                        f"WHERE {scope_clause} GROUP BY status_group"
                    )
                }
                root_count, nested_count = connection.execute(
                    "SELECT SUM(CASE WHEN parented=0 THEN 1 ELSE 0 END), "
                    "SUM(CASE WHEN parented=1 THEN 1 ELSE 0 END) "
                    "FROM temp_object_browser_eligible"
                ).fetchone()
                start_year_rows = tuple(
                    (str(year), int(count))
                    for year, count in connection.execute(
                        "SELECT start_year, COUNT(*) "
                        "FROM temp_object_browser_eligible eligible "
                        f"WHERE {scope_clause} AND start_year<>'' "
                        "GROUP BY start_year ORDER BY start_year DESC"
                    )
                )
                people_rows = tuple(
                    (str(value), str(label), int(count))
                    for value, label, count in connection.execute(
                        "SELECT matters_facet_value(people.display_name), "
                        "MIN(people.display_name), "
                        "COUNT(DISTINCT people.matter_id) "
                        "FROM temp_object_browser_people people "
                        "JOIN temp_object_browser_eligible eligible "
                        "ON eligible.matter_id=people.matter_id "
                        f"WHERE {scope_clause} AND people.rank<=4 "
                        "AND matters_facet_value(people.display_name)<>'' "
                        "GROUP BY matters_facet_value(people.display_name) "
                        "ORDER BY lower(MIN(people.display_name)), "
                        "matters_facet_value(people.display_name)"
                    )
                )
                relationship_rows = tuple(
                    (str(value), int(count))
                    for value, count in connection.execute(
                        "SELECT matters_facet_value(relation.relation_type), "
                        "COUNT(DISTINCT relation.matter_id) "
                        "FROM temp_object_browser_relation relation "
                        "JOIN temp_object_browser_eligible eligible "
                        "ON eligible.matter_id=relation.matter_id "
                        f"WHERE {scope_clause} "
                        "AND matters_facet_value(relation.relation_type)<>'' "
                        "GROUP BY matters_facet_value("
                        "relation.relation_type) "
                        "ORDER BY matters_facet_value(relation.relation_type)"
                    )
                )
                topic_rows = tuple(
                    (
                        str(value),
                        str(label_en),
                        str(label_zh_cn),
                        int(count),
                    )
                    for value, label_en, label_zh_cn, count in connection.execute(
                        "SELECT matters_facet_value(topic.topic_type), "
                        "MIN(topic.label_en), MIN(topic.label_zh_cn), "
                        "COUNT(DISTINCT topic.matter_id) "
                        "FROM temp_object_browser_topic topic "
                        "JOIN temp_object_browser_eligible eligible "
                        "ON eligible.matter_id=topic.matter_id "
                        f"WHERE {scope_clause} "
                        "AND matters_facet_value(topic.topic_type)<>'' "
                        "GROUP BY matters_facet_value(topic.topic_type) "
                        "ORDER BY lower(MIN(topic.label_en)), "
                        "matters_facet_value(topic.topic_type)"
                    )
                )
                source_rows = tuple(
                    (str(value), int(count))
                    for value, count in connection.execute(
                        "SELECT matters_facet_value(source.source_type), "
                        "COUNT(DISTINCT source.matter_id) "
                        "FROM temp_object_browser_source source "
                        "JOIN temp_object_browser_eligible eligible "
                        "ON eligible.matter_id=source.matter_id "
                        f"WHERE {scope_clause} "
                        "AND matters_facet_value(source.source_type)<>'' "
                        "GROUP BY matters_facet_value(source.source_type) "
                        "ORDER BY matters_facet_value(source.source_type)"
                    )
                )
                revision_digest = sha256()
                for (
                    matter_id,
                    projection_revision,
                    activity_revision,
                    hero_revision,
                    hierarchy_revision,
                ) in connection.execute(
                    "SELECT matter_id, projection_revision, "
                    "activity_revision, hero_revision, "
                    "hierarchy_revision "
                    "FROM temp_object_browser_eligible eligible "
                    f"WHERE {scope_clause} ORDER BY matter_id"
                ):
                    revision_digest.update(
                        (
                            _canonical_json(
                                (
                                    str(matter_id),
                                    int(projection_revision),
                                    int(activity_revision),
                                    int(hero_revision),
                                    int(hierarchy_revision),
                                )
                            )
                            + "\n"
                        ).encode("utf-8")
                    )
            finally:
                for table in temporary_tables:
                    connection.execute(f"DROP TABLE IF EXISTS {table}")
        return {
            "matter_ids": matter_ids,
            "total_count": total,
            "status_counts": status_counts,
            "hierarchy_counts": {
                "root": int(root_count or 0),
                "nested": int(nested_count or 0),
            },
            "start_year_rows": start_year_rows,
            "people_rows": people_rows,
            "relationship_rows": relationship_rows,
            "topic_rows": topic_rows,
            "source_rows": source_rows,
            "revision_fingerprint": (
                "sha256:" + revision_digest.hexdigest()
            ),
        }

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

    def hierarchy_parent_edge(
        self,
        child_matter_id: str,
        *,
        current_only: bool = True,
    ) -> dict | None:
        if not child_matter_id:
            raise ValueError("child Matter identity is required")
        current_clause = "AND idx.freshness='current' " if current_only else ""
        with self.connection() as connection:
            row = connection.execute(
                "SELECT s.payload FROM matter_hierarchy_index idx "
                "JOIN current_objects c "
                "ON c.owner='matter_containment_edge' "
                "AND c.object_id=idx.edge_id "
                "JOIN snapshots s ON s.owner=c.owner "
                "AND s.object_id=c.object_id AND s.revision=c.revision "
                "WHERE idx.child_matter_id=? "
                + current_clause,
                (child_matter_id,),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def hierarchy_children_page(
        self,
        parent_matter_id: str,
        *,
        offset: int,
        limit: int,
        current_only: bool = True,
    ) -> tuple[tuple[dict, ...], int]:
        if (
            not parent_matter_id
            or offset < 0
            or limit < 1
            or limit > 200
        ):
            raise ValueError("hierarchy children page bounds are invalid")
        current_clause = "AND idx.freshness='current' " if current_only else ""
        base = (
            " FROM matter_hierarchy_index idx "
            "JOIN current_objects c "
            "ON c.owner='matter_containment_edge' "
            "AND c.object_id=idx.edge_id "
            "JOIN snapshots s ON s.owner=c.owner "
            "AND s.object_id=c.object_id AND s.revision=c.revision "
            "WHERE idx.parent_matter_id=? "
            + current_clause
        )
        with self.connection() as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*)" + base,
                    (parent_matter_id,),
                ).fetchone()[0]
            )
            rows = connection.execute(
                "SELECT s.payload"
                + base
                + "ORDER BY idx.ordinal, idx.child_matter_id LIMIT ? OFFSET ?",
                (parent_matter_id, limit, offset),
            ).fetchall()
        return tuple(json.loads(row[0]) for row in rows), total

    def hierarchy_children(
        self,
        parent_matter_id: str,
        *,
        current_only: bool = True,
    ) -> tuple[dict, ...]:
        if not parent_matter_id:
            raise ValueError("parent Matter identity is required")
        current_clause = "AND idx.freshness='current' " if current_only else ""
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT s.payload FROM matter_hierarchy_index idx "
                "JOIN current_objects c "
                "ON c.owner='matter_containment_edge' "
                "AND c.object_id=idx.edge_id "
                "JOIN snapshots s ON s.owner=c.owner "
                "AND s.object_id=c.object_id AND s.revision=c.revision "
                "WHERE idx.parent_matter_id=? "
                + current_clause
                + "ORDER BY idx.ordinal, idx.child_matter_id",
                (parent_matter_id,),
            ).fetchall()
        return tuple(json.loads(row[0]) for row in rows)

    def hierarchy_child_ids(
        self,
        *,
        current_only: bool = True,
    ) -> tuple[str, ...]:
        current_clause = "WHERE freshness='current'" if current_only else ""
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT child_matter_id FROM matter_hierarchy_index "
                + current_clause
                + " ORDER BY child_matter_id"
            ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def hierarchy_ancestor_ids(
        self,
        matter_id: str,
        *,
        current_only: bool = False,
    ) -> tuple[str, ...]:
        if not matter_id:
            raise ValueError("Matter identity is required")
        freshness_seed = "AND freshness='current'" if current_only else ""
        freshness_step = "AND edge.freshness='current'" if current_only else ""
        query = (
            "WITH RECURSIVE ancestors(matter_id, depth) AS ("
            "SELECT parent_matter_id, 1 FROM matter_hierarchy_index "
            "WHERE child_matter_id=? "
            + freshness_seed
            + " UNION ALL "
            "SELECT edge.parent_matter_id, ancestors.depth + 1 "
            "FROM matter_hierarchy_index edge "
            "JOIN ancestors ON edge.child_matter_id=ancestors.matter_id "
            "WHERE ancestors.depth < 10000 "
            + freshness_step
            + ") "
            "SELECT matter_id FROM ancestors ORDER BY depth"
        )
        with self.connection() as connection:
            rows = connection.execute(query, (matter_id,)).fetchall()
        return tuple(str(row[0]) for row in rows)

    def hierarchy_descendant_ids(
        self,
        matter_id: str,
        *,
        current_only: bool = False,
    ) -> tuple[str, ...]:
        if not matter_id:
            raise ValueError("Matter identity is required")
        freshness_seed = "AND freshness='current'" if current_only else ""
        freshness_step = "AND edge.freshness='current'" if current_only else ""
        query = (
            "WITH RECURSIVE descendants(matter_id, depth) AS ("
            "SELECT child_matter_id, 1 FROM matter_hierarchy_index "
            "WHERE parent_matter_id=? "
            + freshness_seed
            + " UNION ALL "
            "SELECT edge.child_matter_id, descendants.depth + 1 "
            "FROM matter_hierarchy_index edge "
            "JOIN descendants ON edge.parent_matter_id=descendants.matter_id "
            "WHERE descendants.depth < 10000 "
            + freshness_step
            + ") "
            "SELECT matter_id FROM descendants ORDER BY depth, matter_id"
        )
        with self.connection() as connection:
            rows = connection.execute(query, (matter_id,)).fetchall()
        return tuple(str(row[0]) for row in rows)

    def hierarchy_descendant_ids_page(
        self,
        matter_id: str,
        *,
        offset: int,
        limit: int,
        current_only: bool = True,
    ) -> tuple[tuple[str, ...], int]:
        """Read one bounded recursive descendant page."""

        if not matter_id or offset < 0 or limit < 1 or limit > 1000:
            raise ValueError("descendant page bounds are invalid")
        freshness_seed = "AND freshness='current'" if current_only else ""
        freshness_step = "AND edge.freshness='current'" if current_only else ""
        cte = (
            "WITH RECURSIVE descendants(matter_id, depth) AS ("
            "SELECT child_matter_id, 1 FROM matter_hierarchy_index "
            "WHERE parent_matter_id=? "
            + freshness_seed
            + " UNION ALL "
            "SELECT edge.child_matter_id, descendants.depth + 1 "
            "FROM matter_hierarchy_index edge "
            "JOIN descendants ON edge.parent_matter_id=descendants.matter_id "
            "WHERE descendants.depth < 10000 "
            + freshness_step
            + ") "
        )
        with self.connection() as connection:
            total = int(
                connection.execute(
                    cte + "SELECT COUNT(*) FROM descendants",
                    (matter_id,),
                ).fetchone()[0]
            )
            rows = connection.execute(
                cte
                + "SELECT matter_id FROM descendants "
                "ORDER BY depth, matter_id LIMIT ? OFFSET ?",
                (matter_id, limit, offset),
            ).fetchall()
        return tuple(str(row[0]) for row in rows), total

    def matter_work_items_page(
        self,
        matter_id: str,
        *,
        offset: int,
        limit: int,
    ) -> tuple[tuple[dict, ...], int]:
        if not matter_id or offset < 0 or limit < 1 or limit > 200:
            raise ValueError("WorkItem page bounds are invalid")
        base = (
            " FROM matter_work_item_index idx "
            "JOIN current_objects c "
            "ON c.owner='matter_work_item' AND c.object_id=idx.item_id "
            "JOIN snapshots s ON s.owner=c.owner "
            "AND s.object_id=c.object_id AND s.revision=c.revision "
            "WHERE idx.matter_id=? "
        )
        with self.connection() as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*)" + base,
                    (matter_id,),
                ).fetchone()[0]
            )
            rows = connection.execute(
                "SELECT s.payload"
                + base
                + "ORDER BY "
                "CASE idx.status "
                "WHEN 'blocked' THEN 0 WHEN 'in_progress' THEN 1 "
                "WHEN 'waiting' THEN 2 WHEN 'planned' THEN 3 "
                "WHEN 'uncertain' THEN 4 ELSE 5 END, "
                "idx.key_time, idx.item_id LIMIT ? OFFSET ?",
                (matter_id, limit, offset),
            ).fetchall()
        return tuple(json.loads(row[0]) for row in rows), total

    def matter_work_items_for_matters_page(
        self,
        matter_ids: Iterable[str],
        *,
        offset: int,
        limit: int,
    ) -> tuple[tuple[dict, ...], int]:
        """Read one bounded WorkItem page across a Matter hierarchy."""

        ids = tuple(dict.fromkeys(str(item) for item in matter_ids if str(item)))
        if not ids or offset < 0 or limit < 1 or limit > 500:
            raise ValueError("hierarchy WorkItem page bounds are invalid")
        placeholders = ",".join("?" for _ in ids)
        base = (
            " FROM matter_work_item_index idx "
            "JOIN current_objects c "
            "ON c.owner='matter_work_item' AND c.object_id=idx.item_id "
            "JOIN snapshots s ON s.owner=c.owner "
            "AND s.object_id=c.object_id AND s.revision=c.revision "
            f"WHERE idx.matter_id IN ({placeholders}) "
        )
        with self.connection() as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*)" + base,
                    ids,
                ).fetchone()[0]
            )
            rows = connection.execute(
                "SELECT s.payload"
                + base
                + "ORDER BY idx.key_time, idx.item_id LIMIT ? OFFSET ?",
                (*ids, limit, offset),
            ).fetchall()
        return tuple(json.loads(row[0]) for row in rows), total

    def analysis_work_package_page(
        self,
        *,
        after_package_id: str,
        limit: int,
        task_kinds: tuple[str, ...],
    ) -> tuple[dict, ...]:
        """Read a deterministic keyset page for current-contract rebasing."""

        kinds = tuple(dict.fromkeys(str(item) for item in task_kinds if str(item)))
        if limit < 1 or limit > 500 or not kinds:
            raise ValueError("analysis work-package page bounds are invalid")
        placeholders = ",".join("?" for _ in kinds)
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT s.payload FROM current_objects c "
                "JOIN snapshots s ON s.owner=c.owner "
                "AND s.object_id=c.object_id AND s.revision=c.revision "
                "LEFT JOIN current_objects rebase "
                "ON rebase.owner='analysis_contract_rebase' "
                "AND rebase.object_id=c.object_id "
                "WHERE c.owner='analysis_work_package' "
                "AND rebase.object_id IS NULL "
                "AND c.object_id>? "
                "AND json_extract(s.payload, '$.task_kind') "
                f"IN ({placeholders}) "
                "ORDER BY c.object_id LIMIT ?",
                (after_package_id, *kinds, limit),
            ).fetchall()
        return tuple(json.loads(payload) for (payload,) in rows)

    def record_analysis_contract_rebase(
        self,
        *,
        old_package_id: str,
        current_package_id: str,
        current_package_payload: dict[str, Any],
        queued_result_payload: dict[str, Any],
        audit_payload: dict[str, Any],
        invalidation_payload: dict[str, Any] | None,
        legacy_migration_payload: dict[str, Any] | None,
        output_invalidation_payloads: tuple[dict[str, Any], ...] = (),
    ) -> bool:
        """Atomically preserve old evidence and activate one rebuilt package."""

        if (
            not old_package_id
            or not current_package_id
            or str(current_package_payload.get("package_id", ""))
            != current_package_id
            or str(queued_result_payload.get("package_id", ""))
            != current_package_id
        ):
            raise ValueError("analysis contract rebase identities are invalid")
        with self.immediate_transaction():
            if self.current("analysis_contract_rebase", old_package_id) is not None:
                return False
            current_package = self.current(
                "analysis_work_package",
                current_package_id,
            )
            if current_package is None:
                self.append(
                    "analysis_work_package",
                    current_package_id,
                    self.next_revision(
                        "analysis_work_package",
                        current_package_id,
                    ),
                    current_package_payload,
                )
            elif _canonical_json(current_package) != _canonical_json(
                current_package_payload
            ):
                raise ValueError(
                    "rebuilt analysis package identity has conflicting content"
                )

            current_result = self.current(
                "agent_operation_result",
                current_package_id,
            )
            if current_result is None:
                self.append(
                    "agent_operation_result",
                    current_package_id,
                    self.next_revision(
                        "agent_operation_result",
                        current_package_id,
                    ),
                    queued_result_payload,
                )
            elif str(
                current_result.get("package_input_fingerprint", "")
            ) != str(
                queued_result_payload.get("package_input_fingerprint", "")
            ):
                raise ValueError(
                    "rebuilt analysis result identity has conflicting content"
                )

            self.append(
                "analysis_contract_rebase",
                old_package_id,
                self.next_revision(
                    "analysis_contract_rebase",
                    old_package_id,
                ),
                audit_payload,
            )
            if invalidation_payload is not None:
                self.append(
                    "analysis_result_invalidation",
                    old_package_id,
                    self.next_revision(
                        "analysis_result_invalidation",
                        old_package_id,
                    ),
                    invalidation_payload,
                )
            for output_invalidation in output_invalidation_payloads:
                invalidation_id = str(
                    output_invalidation.get("invalidation_id", "")
                )
                if (
                    not invalidation_id
                    or not str(output_invalidation.get("output_ref", ""))
                    or str(
                        output_invalidation.get("old_package_id", "")
                    )
                    != old_package_id
                    or str(
                        output_invalidation.get(
                            "replacement_package_id",
                            "",
                        )
                    )
                    != current_package_id
                ):
                    raise ValueError(
                        "analysis output invalidation identity is invalid"
                    )
                current_output_invalidation = self.current(
                    "analysis_output_invalidation",
                    invalidation_id,
                )
                if current_output_invalidation is None:
                    self.append(
                        "analysis_output_invalidation",
                        invalidation_id,
                        self.next_revision(
                            "analysis_output_invalidation",
                            invalidation_id,
                        ),
                        output_invalidation,
                    )
                elif _canonical_json(
                    current_output_invalidation
                ) != _canonical_json(output_invalidation):
                    raise ValueError(
                        "analysis output invalidation has conflicting content"
                    )
            if (
                legacy_migration_payload is not None
                and self.current(
                    "analysis_work_package_migration",
                    old_package_id,
                )
                is None
            ):
                self.append(
                    "analysis_work_package_migration",
                    old_package_id,
                    self.next_revision(
                        "analysis_work_package_migration",
                        old_package_id,
                    ),
                    legacy_migration_payload,
                )
        return True

    def pending_analysis_page(
        self,
        *,
        offset: int,
        limit: int,
        capability_roles: tuple[str, ...],
        package_id: str = "",
        source_revision: str = "",
        task_kind: str = "",
    ) -> tuple[tuple[dict, ...], int]:
        """Read bounded work packages that do not have a passed current result."""

        if (
            offset < 0
            or limit < 1
            or limit > 200
            or not capability_roles
        ):
            raise ValueError("analysis page bounds are invalid")
        exact_package_id = package_id.strip()
        exact_source_revision = source_revision.strip()
        exact_task_kind = task_kind.strip()
        if any(
            "\n" in selector or "\r" in selector
            for selector in (
                exact_package_id,
                exact_source_revision,
                exact_task_kind,
            )
        ):
            raise ValueError("analysis page selectors must be single-line values")
        allowed_roles = set(capability_roles)
        with self.connection() as connection:
            def current_items(owner: str) -> tuple[tuple[str, dict], ...]:
                rows = connection.execute(
                    "SELECT current.object_id, s.payload "
                    "FROM current_objects current "
                    "JOIN snapshots s ON s.owner=current.owner "
                    "AND s.object_id=current.object_id "
                    "AND s.revision=current.revision "
                    "WHERE current.owner=? ORDER BY current.object_id",
                    (owner,),
                ).fetchall()
                return tuple(
                    (str(object_id), json.loads(payload))
                    for object_id, payload in rows
                )

            package_rows = current_items("analysis_work_package")
            results = dict(current_items("agent_operation_result"))
            migrated_ids = {
                str(payload.get("old_package_id", object_id))
                for object_id, payload in current_items(
                    "analysis_work_package_migration"
                )
            }
            migrated_ids.update(
                str(payload.get("old_package_id", object_id))
                for object_id, payload in current_items(
                    "analysis_contract_rebase"
                )
            )
            source_occurrence_by_revision = {
                (
                    f"{payload.get('source_id', '')}:"
                    f"v{int(payload.get('version', 0) or 0)}"
                ): str(
                    dict(payload.get("external_reference", {})).get(
                        "external_id",
                        "",
                    )
                )
                for _object_id, payload in current_items("source_version")
                if str(payload.get("source_id", ""))
                and int(payload.get("version", 0) or 0) > 0
            }
            occurrence_ids = tuple(
                dict.fromkeys(
                    item
                    for item in source_occurrence_by_revision.values()
                    if item
                )
            )
            coverage: dict[str, tuple[bool, str]] = {}
            for start in range(0, len(occurrence_ids), 800):
                batch = occurrence_ids[start : start + 800]
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    "SELECT object_id, active, disposition "
                    "FROM coverage_stage_index "
                    f"WHERE object_id IN ({placeholders})",
                    batch,
                )
                coverage.update(
                    {
                        str(object_id): (
                            bool(active),
                            str(disposition),
                        )
                        for object_id, active, disposition in rows
                    }
                )

        accepted_apply_statuses = {
            "auto_applied",
            "no_finding",
            "annotation_current",
        }
        pending: list[dict] = []
        for package_id, package in package_rows:
            if (
                package_id in migrated_ids
                or str(package.get("capability_role", ""))
                not in allowed_roles
            ):
                continue
            if exact_package_id and package_id != exact_package_id:
                continue
            if (
                exact_source_revision
                and exact_source_revision
                not in {
                    str(item)
                    for item in package.get("source_revision_ids", ())
                }
            ):
                continue
            if (
                exact_task_kind
                and str(package.get("task_kind", "")) != exact_task_kind
            ):
                continue
            source_retired = False
            for source_revision in package.get("source_revision_ids", ()):
                occurrence_id = source_occurrence_by_revision.get(
                    str(source_revision),
                    "",
                )
                source_coverage = coverage.get(occurrence_id)
                if (
                    source_coverage is not None
                    and (
                        not source_coverage[0]
                        or source_coverage[1] != "tracked"
                    )
                ):
                    source_retired = True
                    break
            if source_retired:
                continue
            dependency_blocked = any(
                str(results.get(str(dependency_id), {}).get("status", ""))
                != "passed"
                for dependency_id in package.get(
                    "dependency_package_ids",
                    (),
                )
            )
            if dependency_blocked:
                continue
            result = results.get(package_id, {})
            if (
                str(result.get("status", "")) == "passed"
                and str(
                    result.get(
                        "auto_apply_status",
                        "not_dispatched",
                    )
                )
                in accepted_apply_statuses
            ):
                continue
            pending.append(package)
        total = len(pending)
        return tuple(pending[offset : offset + limit]), total

    def redispatchable_analysis_page(
        self,
        *,
        limit: int,
    ) -> tuple[dict, ...]:
        """Read passed current results that only need original-owner retry."""

        if limit < 1 or limit > 200:
            raise ValueError("redispatch page limit is invalid")
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT ps.payload "
                "FROM current_objects rc "
                "JOIN snapshots rs ON rs.owner=rc.owner "
                "AND rs.object_id=rc.object_id AND rs.revision=rc.revision "
                "JOIN current_objects pc "
                "ON pc.owner='analysis_work_package' "
                "AND pc.object_id=rc.object_id "
                "JOIN snapshots ps ON ps.owner=pc.owner "
                "AND ps.object_id=pc.object_id AND ps.revision=pc.revision "
                "WHERE rc.owner='agent_operation_result' "
                "AND json_extract(rs.payload, '$.status')='passed' "
                "AND COALESCE("
                "json_extract(rs.payload, '$.receipt_current'), 0"
                ")=1 "
                "AND COALESCE("
                "json_extract(rs.payload, '$.auto_apply_status'), "
                "'not_dispatched'"
                ") NOT IN ('auto_applied', 'no_finding', 'annotation_current') "
                "AND NOT EXISTS ("
                "SELECT 1 FROM current_objects invalid "
                "WHERE invalid.owner='analysis_result_invalidation' "
                "AND invalid.object_id=rc.object_id"
                ") "
                "ORDER BY rc.object_id LIMIT ?",
                (limit,),
            ).fetchall()
        return tuple(json.loads(row[0]) for row in rows)

    def legacy_analysis_page(
        self,
        *,
        limit: int = 200,
        capability_roles: tuple[str, ...],
        task_kinds: tuple[str, ...] = (),
    ) -> tuple[dict, ...]:
        """Read pre-capability WorkPackageV2 rows for one direct migration."""

        if limit < 1 or limit > 500 or not capability_roles:
            raise ValueError("legacy analysis page limit is invalid")
        role_placeholders = ",".join("?" for _ in capability_roles)
        kinds = tuple(dict.fromkeys(str(item) for item in task_kinds if str(item)))
        task_clause = ""
        if kinds:
            task_placeholders = ",".join("?" for _ in kinds)
            task_clause = (
                "AND json_extract(ps.payload, '$.task_kind') "
                f"IN ({task_placeholders}) "
            )
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT ps.payload FROM current_objects pc "
                "JOIN snapshots ps ON ps.owner=pc.owner "
                "AND ps.object_id=pc.object_id AND ps.revision=pc.revision "
                "LEFT JOIN current_objects mc "
                "ON mc.owner='analysis_work_package_migration' "
                "AND mc.object_id=pc.object_id "
                "WHERE pc.owner='analysis_work_package' "
                "AND mc.object_id IS NULL "
                "AND (json_extract(ps.payload, '$.capability_role') IS NULL "
                "OR json_extract(ps.payload, '$.execution_profile_contract_id') "
                "IS NULL "
                "OR json_extract(ps.payload, '$.required_runner_id') "
                "!='codex-hosted-capability-router' "
                "OR json_extract(ps.payload, '$.capability_role') "
                f"NOT IN ({role_placeholders})) "
                + task_clause
                + "ORDER BY pc.object_id LIMIT ?",
                (*capability_roles, *kinds, limit),
            ).fetchall()
        return tuple(json.loads(row[0]) for row in rows)

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
                "SELECT s.payload FROM current_objects current "
                "JOIN snapshots s ON s.owner=current.owner "
                "AND s.object_id=current.object_id "
                "AND s.revision=current.revision "
                "WHERE current.owner=? "
                "ORDER BY s.created_at DESC, s.rowid DESC LIMIT 1",
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
