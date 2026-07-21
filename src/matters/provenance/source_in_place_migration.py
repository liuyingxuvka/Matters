"""Offline, resumable direct migration to the source-in-place authority.

The migration deliberately has no compatibility reader.  It creates and
verifies one separate recovery backup, scrubs legacy copied source text from
every historical snapshot and idempotency receipt, retires document-preview
and descendant-Hero presentation copies, then reclaims only blobs that no
current display owner references.  SQLite compaction remains a separate
operator action.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import sqlite3
from typing import Any, Iterable, Mapping

from matters.provenance.source_registry import durable_source_content


MIGRATION_ID = "source-in-place-direct-current:v1"
MANIFEST_NAME = "backup-manifest.json"
_SHA256_FILE = re.compile(r"^[0-9a-f]{64}$")
_CRITICAL_COUNT_OWNERS = (
    "source_version",
    "source_processing_result",
    "evidence_anchor",
    "admission_decision",
    "projection",
    "matter_containment_edge",
    "matter_work_item",
    "material_clue",
    "object_coverage",
    "generated_hero_record",
    "generated_hero_token",
    "visual_asset",
    "visual_preview_token",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _digest(value: Any) -> str:
    return "sha256:" + sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _payload_hash(encoded: str) -> str:
    return "sha256:" + sha256(encoded.encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8 * 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _tree_stats(root: Path, *, verify_named_hashes: bool = False) -> dict[str, Any]:
    count = 0
    byte_count = 0
    named_hash_failure_count = 0
    if not root.exists():
        return {
            "file_count": 0,
            "byte_count": 0,
            "named_hash_failure_count": 0,
        }
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        count += 1
        byte_count += path.stat().st_size
        if verify_named_hashes and _SHA256_FILE.fullmatch(path.name):
            if _file_hash(path) != "sha256:" + path.name:
                named_hash_failure_count += 1
    return {
        "file_count": count,
        "byte_count": byte_count,
        "named_hash_failure_count": named_hash_failure_count,
    }


def _database_uri(path: Path, *, read_only: bool) -> str:
    suffix = "?mode=ro" if read_only else ""
    return f"file:{path.as_posix()}{suffix}"


def _connect(path: Path, *, read_only: bool = False) -> sqlite3.Connection:
    connection = sqlite3.connect(
        _database_uri(path, read_only=read_only),
        uri=True,
        timeout=120,
    )
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _quick_check(connection: sqlite3.Connection) -> str:
    row = connection.execute("PRAGMA quick_check(1)").fetchone()
    return str(row[0]) if row else "missing"


def _current_owner_counts(connection: sqlite3.Connection) -> dict[str, int]:
    rows = connection.execute(
        "SELECT owner, COUNT(*) FROM current_objects "
        "WHERE owner IN ("
        + ",".join("?" for _ in _CRITICAL_COUNT_OWNERS)
        + ") GROUP BY owner ORDER BY owner",
        _CRITICAL_COUNT_OWNERS,
    ).fetchall()
    observed = {str(owner): int(count) for owner, count in rows}
    return {owner: observed.get(owner, 0) for owner in _CRITICAL_COUNT_OWNERS}


def _source_identity_digest(connection: sqlite3.Connection) -> str:
    digest = sha256()
    cursor = connection.execute(
        "SELECT c.object_id, c.revision, "
        "COALESCE(json_extract(s.payload,'$.content_hash'),''), "
        "COALESCE(json_extract(s.payload,'$.metadata_hash'),'') "
        "FROM current_objects c JOIN snapshots s "
        "ON s.owner=c.owner AND s.object_id=c.object_id "
        "AND s.revision=c.revision "
        "WHERE c.owner='source_version' ORDER BY c.object_id"
    )
    for row in cursor:
        digest.update("\0".join(str(item) for item in row).encode("utf-8"))
        digest.update(b"\n")
    return "sha256:" + digest.hexdigest()


def _residual_count(
    connection: sqlite3.Connection,
    *,
    table: str,
    json_column: str,
    where: str,
    parameters: Iterable[Any] = (),
) -> int:
    row = connection.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {where}",
        tuple(parameters),
    ).fetchone()
    return int(row[0]) if row else 0


def _pointer_readiness_report(
    connection: sqlite3.Connection,
) -> dict[str, int]:
    current_payloads = {
        str(object_id): dict(json.loads(str(encoded)))
        for object_id, encoded in connection.execute(
            "SELECT c.object_id,s.payload FROM current_objects c "
            "JOIN snapshots s ON s.owner=c.owner AND s.object_id=c.object_id "
            "AND s.revision=c.revision WHERE c.owner='source_version'"
        )
    }
    candidate_index = _source_pointer_candidate_index(
        connection,
        (
            str(
                dict(payload.get("external_reference", {})).get(
                    "external_id",
                    "",
                )
            )
            for payload in current_payloads.values()
        ),
    )
    readable_by_source: dict[str, bool] = {}
    for source_id, payload in current_payloads.items():
        pointer = _source_pointer_context(
            connection,
            payload,
            candidate_index=candidate_index,
        )
        readable_by_source[source_id] = (
            str(pointer.get("original_availability", "")) == "available"
        )
    raw_source_ids = {
        str(object_id)
        for (object_id,) in connection.execute(
            "SELECT DISTINCT object_id FROM snapshots "
            "WHERE owner='source_version' AND "
            "json_type(payload,'$.content.body_text') IS NOT NULL"
        )
    }
    raw_source_ids.update(
        str(source_id)
        for (source_id,) in connection.execute(
            "SELECT DISTINCT json_extract("
            "payload,'$.registration.source_version.source_id') "
            "FROM snapshots WHERE owner='source_processing_result' "
            "AND json_type("
            "payload,'$.registration.source_version.content.body_text'"
            ") IS NOT NULL"
        )
        if source_id
    )
    raw_source_ids.update(
        str(source_id)
        for (source_id,) in connection.execute(
            "SELECT DISTINCT json_extract("
            "payload,'$.source_version.source_id') FROM idempotency "
            "WHERE owner='source_registration' AND json_valid(payload) "
            "AND EXISTS (SELECT 1 FROM json_tree(payload) "
            "WHERE key='body_text')"
        )
        if source_id
    )
    return {
        "current_source_pointer_readable_count": sum(
            readable_by_source.values()
        ),
        "current_source_pointer_unavailable_count": sum(
            not value for value in readable_by_source.values()
        ),
        "raw_source_pointer_blocked_count": sum(
            not readable_by_source.get(source_id, False)
            for source_id in raw_source_ids
        ),
    }


def residual_report(database_path: Path) -> dict[str, Any]:
    """Return bounded migration residuals without source contents."""

    with _connect(database_path, read_only=True) as connection:
        unrebased_source_snapshot = _residual_count(
            connection,
            table="snapshots",
            json_column="payload",
            where=(
                "owner='source_version' AND COALESCE("
                "json_extract(payload,'$.pointer_rebase_revision'),'')<>?"
            ),
            parameters=(MIGRATION_ID,),
        )
        source_snapshot = _residual_count(
            connection,
            table="snapshots",
            json_column="payload",
            where=(
                "owner='source_version' AND "
                "json_type(payload,'$.content.body_text') IS NOT NULL"
            ),
        )
        processing_snapshot = _residual_count(
            connection,
            table="snapshots",
            json_column="payload",
            where=(
                "owner='source_processing_result' AND "
                "json_type("
                "payload,'$.registration.source_version.content.body_text'"
                ") IS NOT NULL"
            ),
        )
        idempotency = _residual_count(
            connection,
            table="idempotency",
            json_column="payload",
            where=(
                "owner='source_registration' AND json_valid(payload) "
                "AND EXISTS (SELECT 1 FROM json_tree(payload) "
                "WHERE key='body_text')"
            ),
        )
        document_previews = _residual_count(
            connection,
            table=(
                "current_objects c JOIN snapshots s "
                "ON s.owner=c.owner AND s.object_id=c.object_id "
                "AND s.revision=c.revision"
            ),
            json_column="s.payload",
            where=(
                "c.owner='visual_asset' "
                "AND json_extract(s.payload,'$.kind')='document_preview' "
                "AND (COALESCE(json_extract(s.payload,'$.current'),0)<>0 "
                "OR COALESCE(json_extract(s.payload,'$.display_allowed'),0)<>0 "
                "OR COALESCE(json_extract("
                "s.payload,'$.original_blob_ref'),'')<>'' "
                "OR COALESCE(json_extract("
                "s.payload,'$.hero_blob_ref'),'')<>'' "
                "OR COALESCE(json_extract("
                "s.payload,'$.thumbnail_blob_ref'),'')<>'')"
            ),
        )
        child_heroes = _residual_count(
            connection,
            table="current_objects c",
            json_column="",
            where=(
                "c.owner='generated_hero_record' AND EXISTS ("
                "SELECT 1 FROM matter_hierarchy_index h "
                "WHERE h.child_matter_id=c.object_id)"
            ),
        )
        current_source_unavailable = _residual_count(
            connection,
            table=(
                "current_objects c JOIN snapshots s "
                "ON s.owner=c.owner AND s.object_id=c.object_id "
                "AND s.revision=c.revision"
            ),
            json_column="s.payload",
            where=(
                "c.owner='source_version' AND COALESCE("
                "json_extract(s.payload,'$.original_availability'),"
                "'source_unavailable')<>'available'"
            ),
        )
        pointer_readiness = _pointer_readiness_report(connection)
        return {
            "migration_id": MIGRATION_ID,
            "unrebased_source_snapshot_count": unrebased_source_snapshot,
            "source_snapshot_raw_count": source_snapshot,
            "processing_snapshot_raw_count": processing_snapshot,
            "idempotency_raw_count": idempotency,
            "active_document_preview_count": document_previews,
            "current_child_hero_count": child_heroes,
            "current_source_unavailable_count": current_source_unavailable,
            **pointer_readiness,
            "critical_current_counts": _current_owner_counts(connection),
            "source_identity_digest": _source_identity_digest(connection),
            "database_quick_check": _quick_check(connection),
        }


def _source_time_metadata(content: Mapping[str, Any]) -> dict[str, Any]:
    retained: dict[str, Any] = {}
    internal_date = content.get("internal_date")
    if internal_date not in (None, ""):
        retained["payload.internal_date"] = internal_date
    headers = content.get("headers")
    if isinstance(headers, Mapping):
        message_date = headers.get("date")
        if message_date not in (None, ""):
            retained["headers.message_date"] = message_date
    return retained


def _source_pointer_candidate_index(
    connection: sqlite3.Connection,
    external_ids: Iterable[str],
) -> dict[str, list[tuple[Any, ...]]]:
    normalized = tuple(
        dict.fromkeys(
            str(item).strip() for item in external_ids if str(item).strip()
        )
    )
    result: dict[str, list[tuple[Any, ...]]] = {}
    for offset in range(0, len(normalized), 500):
        page = normalized[offset : offset + 500]
        rows = connection.execute(
            "SELECT i.object_id,i.scope_id,i.disposition,"
            "i.occurrence_payload,scope_snapshot.payload "
            "FROM inventory_occurrence_current i "
            "LEFT JOIN current_objects scope_current "
            "ON scope_current.owner='candidate_scope' "
            "AND scope_current.object_id=i.scope_id "
            "LEFT JOIN snapshots scope_snapshot "
            "ON scope_snapshot.owner=scope_current.owner "
            "AND scope_snapshot.object_id=scope_current.object_id "
            "AND scope_snapshot.revision=scope_current.revision "
            "WHERE i.object_id IN ("
            + ",".join("?" for _ in page)
            + ") ORDER BY i.object_id,i.scope_id",
            page,
        ).fetchall()
        for object_id, *candidate in rows:
            result.setdefault(str(object_id), []).append(tuple(candidate))
    return result


def _source_pointer_context(
    connection: sqlite3.Connection,
    payload: Mapping[str, Any],
    *,
    candidate_index: Mapping[str, list[tuple[Any, ...]]] | None = None,
) -> dict[str, Any]:
    reference = payload.get("external_reference")
    reference_payload = (
        dict(reference) if isinstance(reference, Mapping) else {}
    )
    external_id = str(reference_payload.get("external_id", "")).strip()
    provider = str(
        reference_payload.get("provider", payload.get("provider", ""))
    ).strip()
    object_type = str(reference_payload.get("object_type", "")).strip()
    existing_scope_id = str(payload.get("scope_id", "")).strip()
    existing_locator = str(reference_payload.get("locator", "")).strip()
    candidates = (
        tuple(candidate_index.get(external_id, ()))
        if candidate_index is not None
        else tuple(
            _source_pointer_candidate_index(
                connection,
                (external_id,),
            ).get(external_id, ())
        )
    )
    ranked: list[tuple[int, str, str, str, str, str]] = []
    for scope_id, disposition, occurrence_encoded, scope_encoded in candidates:
        try:
            occurrence = dict(json.loads(str(occurrence_encoded)))
            scope = (
                dict(json.loads(str(scope_encoded)))
                if scope_encoded is not None
                else {}
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        occurrence_provider = str(
            occurrence.get("provider", provider)
        ).strip()
        if provider and occurrence_provider and occurrence_provider != provider:
            continue
        locator = str(occurrence.get("locator", "")).strip()
        root_locator = str(scope.get("root_locator", "")).strip()
        scope_active = bool(scope.get("active", True))
        disposition_available = str(disposition) not in {
            "blocked",
            "unavailable",
            "hard_excluded",
            "not_tracked",
        }
        readable = bool(locator and scope_active and disposition_available)
        if provider == "filesystem":
            readable = bool(
                readable
                and root_locator
                and (Path(root_locator) / Path(*Path(locator).parts)).is_file()
            )
        elif provider == "gmail":
            readable = bool(readable and root_locator)
        ranked.append(
            (
                0 if readable else 1,
                str(scope_id),
                locator,
                root_locator,
                str(disposition),
                occurrence_provider,
            )
        )
    if ranked:
        _, scope_id, locator, root_locator, disposition, _ = sorted(ranked)[0]
        readable = sorted(ranked)[0][0] == 0
        return {
            "scope_id": scope_id,
            "locator": locator,
            "root_locator_fingerprint": (
                _digest(root_locator) if root_locator else ""
            ),
            "original_availability": (
                "available" if readable else "source_unavailable"
            ),
            "unavailable_reason": (
                ""
                if readable
                else f"current inventory disposition is {disposition}"
            ),
        }
    existing_complete = bool(
        existing_locator
        and (
            provider != "filesystem"
            or Path(existing_locator).is_file()
        )
    )
    if bool(payload.get("tombstone", False)):
        availability = "deleted"
        reason = "source version is a tombstone"
    elif existing_complete:
        availability = "available"
        reason = ""
    else:
        availability = "source_unavailable"
        reason = "source occurrence is absent from current inventory"
    return {
        "scope_id": existing_scope_id,
        "locator": existing_locator,
        "root_locator_fingerprint": str(
            payload.get("root_locator_fingerprint", "")
        ),
        "original_availability": availability,
        "unavailable_reason": reason,
    }


def _rebase_source_pointer(
    payload: Mapping[str, Any],
    pointer: Mapping[str, Any],
) -> dict[str, Any]:
    result = dict(payload)
    reference = result.get("external_reference")
    reference_payload = (
        dict(reference) if isinstance(reference, Mapping) else {}
    )
    if str(pointer.get("locator", "")):
        reference_payload["locator"] = str(pointer["locator"])
    result["external_reference"] = reference_payload
    result["scope_id"] = str(pointer.get("scope_id", ""))
    result["root_locator_fingerprint"] = str(
        pointer.get("root_locator_fingerprint", "")
    )
    result["storage_class"] = "external_original"
    result["original_availability"] = str(
        pointer.get("original_availability", "source_unavailable")
    )
    result["unavailable_reason"] = str(pointer.get("unavailable_reason", ""))
    result["pointer_rebase_revision"] = MIGRATION_ID
    result["locator_fingerprint"] = _digest(
        {
            "provider": reference_payload.get(
                "provider",
                result.get("provider", ""),
            ),
            "object_type": reference_payload.get("object_type", ""),
            "external_id": reference_payload.get("external_id", ""),
            "scope_id": result["scope_id"],
            "locator": reference_payload.get("locator", ""),
            "root_locator_fingerprint": result[
                "root_locator_fingerprint"
            ],
        }
    )
    return result


def _sanitize_source_version(
    payload: Mapping[str, Any],
    *,
    pointer: Mapping[str, Any],
) -> dict[str, Any]:
    result = _rebase_source_pointer(payload, pointer)
    original_content = result.get("content")
    content = (
        dict(original_content)
        if isinstance(original_content, Mapping)
        else {}
    )
    result["content"] = durable_source_content(content)
    result.pop("transient_content", None)
    existing_time = result.get("source_time_metadata")
    result["source_time_metadata"] = (
        dict(existing_time)
        if isinstance(existing_time, Mapping)
        else _source_time_metadata(content)
    )
    return result


def _sanitize_processing(
    connection: sqlite3.Connection,
    payload: Mapping[str, Any],
    *,
    candidate_index: Mapping[str, list[tuple[Any, ...]]] | None = None,
) -> dict[str, Any]:
    result = dict(payload)
    registration = result.get("registration")
    if not isinstance(registration, Mapping):
        return result
    registration_payload = dict(registration)
    version = registration_payload.get("source_version")
    if isinstance(version, Mapping):
        pointer = _source_pointer_context(
            connection,
            version,
            candidate_index=candidate_index,
        )
        if str(pointer["original_availability"]) != "available":
            raise RuntimeError(
                "processing raw source copy has no current readable pointer"
            )
        registration_payload["source_version"] = _sanitize_source_version(
            version,
            pointer=pointer,
        )
    result["registration"] = registration_payload
    return result


def _sanitize_idempotency(
    connection: sqlite3.Connection,
    payload: Mapping[str, Any],
    *,
    candidate_index: Mapping[str, list[tuple[Any, ...]]] | None = None,
) -> dict[str, Any]:
    result = dict(payload)
    version = result.get("source_version")
    if isinstance(version, Mapping):
        pointer = _source_pointer_context(
            connection,
            version,
            candidate_index=candidate_index,
        )
        if str(pointer["original_availability"]) != "available":
            raise RuntimeError(
                "idempotency raw source copy has no current readable pointer"
            )
        result["source_version"] = _sanitize_source_version(
            version,
            pointer=pointer,
        )
    return result


def _append_payload(
    connection: sqlite3.Connection,
    *,
    owner: str,
    object_id: str,
    prior_revision: int,
    payload: Mapping[str, Any],
) -> int:
    row = connection.execute(
        "SELECT COALESCE(MAX(revision),0) FROM snapshots "
        "WHERE owner=? AND object_id=?",
        (owner, object_id),
    ).fetchone()
    revision = max(prior_revision + 1, int(row[0]) + 1)
    encoded = _canonical_json(payload)
    connection.execute(
        "INSERT INTO snapshots"
        "(owner,object_id,revision,payload,payload_hash,created_at) "
        "VALUES(?,?,?,?,?,?)",
        (
            owner,
            object_id,
            revision,
            encoded,
            _payload_hash(encoded),
            _utc_now(),
        ),
    )
    connection.execute(
        "UPDATE current_objects SET revision=? "
        "WHERE owner=? AND object_id=? AND revision=?",
        (revision, owner, object_id, prior_revision),
    )
    return revision


def _scrub_snapshot_batch(
    connection: sqlite3.Connection,
    *,
    owner: str,
    json_path: str,
    limit: int,
) -> int:
    rows = connection.execute(
        "SELECT object_id,revision,payload FROM snapshots "
        "WHERE owner=? AND json_type(payload,?) IS NOT NULL "
        "ORDER BY object_id,revision LIMIT ?",
        (owner, json_path, limit),
    ).fetchall()
    decoded_rows = [
        (object_id, revision, dict(json.loads(str(encoded))))
        for object_id, revision, encoded in rows
    ]
    source_payloads = [
        (
            payload
            if owner == "source_version"
            else dict(
                dict(payload.get("registration", {})).get(
                    "source_version",
                    {},
                )
            )
        )
        for _, _, payload in decoded_rows
    ]
    candidate_index = _source_pointer_candidate_index(
        connection,
        (
            str(
                dict(payload.get("external_reference", {})).get(
                    "external_id",
                    "",
                )
            )
            for payload in source_payloads
        ),
    )
    for object_id, revision, payload in decoded_rows:
        if owner == "source_version":
            pointer = _source_pointer_context(
                connection,
                payload,
                candidate_index=candidate_index,
            )
            if str(pointer["original_availability"]) != "available":
                raise RuntimeError(
                    "raw source copy has no current readable pointer"
                )
            sanitized = _sanitize_source_version(
                payload,
                pointer=pointer,
            )
        else:
            sanitized = _sanitize_processing(
                connection,
                payload,
                candidate_index=candidate_index,
            )
        next_encoded = _canonical_json(sanitized)
        connection.execute(
            "UPDATE snapshots SET payload=?,payload_hash=? "
            "WHERE owner=? AND object_id=? AND revision=?",
            (
                next_encoded,
                _payload_hash(next_encoded),
                owner,
                str(object_id),
                int(revision),
            ),
        )
    return len(rows)


def _rebase_source_pointer_batch(
    connection: sqlite3.Connection,
    *,
    limit: int,
) -> int:
    rows = connection.execute(
        "SELECT object_id,revision,payload FROM snapshots "
        "WHERE owner='source_version' AND COALESCE("
        "json_extract(payload,'$.pointer_rebase_revision'),'')<>? "
        "ORDER BY object_id,revision LIMIT ?",
        (MIGRATION_ID, limit),
    ).fetchall()
    decoded_rows = [
        (object_id, revision, dict(json.loads(str(encoded))))
        for object_id, revision, encoded in rows
    ]
    candidate_index = _source_pointer_candidate_index(
        connection,
        (
            str(
                dict(payload.get("external_reference", {})).get(
                    "external_id",
                    "",
                )
            )
            for _, _, payload in decoded_rows
        ),
    )
    for object_id, revision, payload in decoded_rows:
        pointer = _source_pointer_context(
            connection,
            payload,
            candidate_index=candidate_index,
        )
        rebased = _rebase_source_pointer(payload, pointer)
        next_encoded = _canonical_json(rebased)
        connection.execute(
            "UPDATE snapshots SET payload=?,payload_hash=? "
            "WHERE owner='source_version' AND object_id=? AND revision=?",
            (
                next_encoded,
                _payload_hash(next_encoded),
                str(object_id),
                int(revision),
            ),
        )
    return len(rows)


def _scrub_idempotency_batch(
    connection: sqlite3.Connection,
    *,
    limit: int,
) -> int:
    rows = connection.execute(
        "SELECT idempotency_key,payload FROM idempotency "
        "WHERE owner='source_registration' AND json_valid(payload) "
        "AND EXISTS (SELECT 1 FROM json_tree(payload) WHERE key='body_text') "
        "ORDER BY idempotency_key LIMIT ?",
        (limit,),
    ).fetchall()
    decoded_rows = [
        (key, dict(json.loads(str(encoded))))
        for key, encoded in rows
    ]
    source_payloads = [
        dict(payload.get("source_version", {}))
        for _, payload in decoded_rows
    ]
    candidate_index = _source_pointer_candidate_index(
        connection,
        (
            str(
                dict(payload.get("external_reference", {})).get(
                    "external_id",
                    "",
                )
            )
            for payload in source_payloads
        ),
    )
    for key, decoded in decoded_rows:
        payload = _sanitize_idempotency(
            connection,
            decoded,
            candidate_index=candidate_index,
        )
        connection.execute(
            "UPDATE idempotency SET payload=? "
            "WHERE owner='source_registration' AND idempotency_key=?",
            (_canonical_json(payload), str(key)),
        )
    return len(rows)


def _retire_token(
    connection: sqlite3.Connection,
    *,
    token: str,
    owner: str,
    blob_field: str,
) -> None:
    if not token:
        return
    row = connection.execute(
        "SELECT c.revision,s.payload FROM current_objects c "
        "JOIN snapshots s ON s.owner=c.owner AND s.object_id=c.object_id "
        "AND s.revision=c.revision "
        "WHERE c.owner=? AND c.object_id=?",
        (owner, token),
    ).fetchone()
    if row is None:
        return
    revision, encoded = int(row[0]), str(row[1])
    payload = dict(json.loads(encoded))
    if (
        not bool(payload.get("current", False))
        and not bool(payload.get("display_allowed", False))
        and not str(payload.get(blob_field, ""))
        and not str(payload.get("thumbnail_blob_ref", ""))
        and not str(payload.get("hero_blob_ref", ""))
    ):
        return
    payload["current"] = False
    payload["display_allowed"] = False
    payload[blob_field] = ""
    if "thumbnail_blob_ref" in payload:
        payload["thumbnail_blob_ref"] = ""
    if "hero_blob_ref" in payload:
        payload["hero_blob_ref"] = ""
    _append_payload(
        connection,
        owner=owner,
        object_id=token,
        prior_revision=revision,
        payload=payload,
    )


def _retire_document_preview_batch(
    connection: sqlite3.Connection,
    *,
    limit: int,
) -> int:
    rows = connection.execute(
        "SELECT c.object_id,c.revision,s.payload FROM current_objects c "
        "JOIN snapshots s ON s.owner=c.owner AND s.object_id=c.object_id "
        "AND s.revision=c.revision "
        "WHERE c.owner='visual_asset' "
        "AND json_extract(s.payload,'$.kind')='document_preview' "
        "AND (COALESCE(json_extract(s.payload,'$.current'),0)<>0 "
        "OR COALESCE(json_extract(s.payload,'$.display_allowed'),0)<>0 "
        "OR COALESCE(json_extract(s.payload,'$.original_blob_ref'),'')<>'' "
        "OR COALESCE(json_extract(s.payload,'$.hero_blob_ref'),'')<>'' "
        "OR COALESCE(json_extract(s.payload,'$.thumbnail_blob_ref'),'')<>'') "
        "ORDER BY c.object_id LIMIT ?",
        (limit,),
    ).fetchall()
    for object_id, revision, encoded in rows:
        payload = dict(json.loads(str(encoded)))
        token = str(payload.get("preview_token", ""))
        payload["current"] = False
        payload["display_allowed"] = False
        payload["original_blob_ref"] = ""
        payload["hero_blob_ref"] = ""
        payload["thumbnail_blob_ref"] = ""
        payload["derivation_id"] = "matters.visual.document-preview:retired-v2"
        payload["localized_reason"] = {
            "en": "Document screenshots are outside the Images gallery",
            "zh-CN": "文档截图不属于图片库",
        }
        _append_payload(
            connection,
            owner="visual_asset",
            object_id=str(object_id),
            prior_revision=int(revision),
            payload=payload,
        )
        _retire_token(
            connection,
            token=token,
            owner="visual_preview_token",
            blob_field="thumbnail_blob_ref",
        )
    return len(rows)


def _retire_child_hero_batch(
    connection: sqlite3.Connection,
    *,
    limit: int,
) -> int:
    rows = connection.execute(
        "SELECT c.object_id,s.payload FROM current_objects c "
        "JOIN snapshots s ON s.owner=c.owner AND s.object_id=c.object_id "
        "AND s.revision=c.revision "
        "WHERE c.owner='generated_hero_record' AND EXISTS ("
        "SELECT 1 FROM matter_hierarchy_index h "
        "WHERE h.child_matter_id=c.object_id) "
        "ORDER BY c.object_id LIMIT ?",
        (limit,),
    ).fetchall()
    for matter_id, encoded in rows:
        payload = dict(json.loads(str(encoded)))
        _retire_token(
            connection,
            token=str(payload.get("private_asset_token", "")),
            owner="generated_hero_token",
            blob_field="private_blob_ref",
        )
        connection.execute(
            "DELETE FROM current_objects "
            "WHERE owner='generated_hero_record' AND object_id=?",
            (str(matter_id),),
        )
        coverage = connection.execute(
            "SELECT c.revision,s.payload FROM current_objects c "
            "JOIN snapshots s ON s.owner=c.owner AND s.object_id=c.object_id "
            "AND s.revision=c.revision "
            "WHERE c.owner='object_coverage' AND c.object_id=?",
            (str(matter_id),),
        ).fetchone()
        if coverage is not None:
            revision, coverage_encoded = int(coverage[0]), str(coverage[1])
            coverage_payload = dict(json.loads(coverage_encoded))
            stages = dict(coverage_payload.get("stages", {}))
            prior_stage = dict(stages.get("generated_hero", {}))
            prior_stage.update(
                {
                    "stage_id": "generated_hero",
                    "status": "not_applicable",
                    "owner_id": prior_stage.get(
                        "owner_id",
                        "presentation.generated_hero",
                    ),
                    "input_fingerprint": _digest(
                        {
                            "matter_id": str(matter_id),
                            "eligibility": "not_applicable",
                        }
                    ),
                    "output_ref": "",
                    "failure_class": "",
                    "updated_at": _utc_now(),
                }
            )
            stages["generated_hero"] = prior_stage
            coverage_payload["stages"] = stages
            coverage_payload["revision"] = revision + 1
            coverage_payload["updated_at"] = _utc_now()
            _append_payload(
                connection,
                owner="object_coverage",
                object_id=str(matter_id),
                prior_revision=revision,
                payload=coverage_payload,
            )
    return len(rows)


def _current_blob_refs(connection: sqlite3.Connection) -> set[str]:
    references: set[str] = set()
    owners_and_fields = {
        "visual_asset": (
            "original_blob_ref",
            "hero_blob_ref",
            "thumbnail_blob_ref",
        ),
        "visual_preview_token": (
            "hero_blob_ref",
            "thumbnail_blob_ref",
        ),
        "generated_hero_record": ("private_blob_ref",),
        "generated_hero_token": ("private_blob_ref",),
    }
    for owner, fields in owners_and_fields.items():
        cursor = connection.execute(
            "SELECT s.payload FROM current_objects c JOIN snapshots s "
            "ON s.owner=c.owner AND s.object_id=c.object_id "
            "AND s.revision=c.revision WHERE c.owner=?",
            (owner,),
        )
        for (encoded,) in cursor:
            payload = dict(json.loads(str(encoded)))
            if owner.endswith("_token") and not bool(
                payload.get("current", False)
            ):
                continue
            if owner == "visual_asset" and (
                not bool(payload.get("current", False))
                or not bool(payload.get("display_allowed", False))
            ):
                continue
            if owner == "generated_hero_record" and str(
                payload.get("status", "")
            ) != "generated_current":
                continue
            for field_name in fields:
                value = str(payload.get(field_name, ""))
                if value.startswith("sha256:") and _SHA256_FILE.fullmatch(
                    value.removeprefix("sha256:")
                ):
                    references.add(value)
    return references


def reclaim_orphan_blobs(
    *,
    database_path: Path,
    blob_root: Path,
    limit: int,
) -> dict[str, Any]:
    if limit < 1 or limit > 10_000:
        raise ValueError("blob cleanup limit must be between one and ten thousand")
    with _connect(database_path, read_only=True) as connection:
        referenced = _current_blob_refs(connection)
    deleted = 0
    reclaimed = 0
    for path in sorted(
        item
        for item in blob_root.iterdir()
        if item.is_file() and _SHA256_FILE.fullmatch(item.name)
    ):
        if "sha256:" + path.name in referenced:
            continue
        size = path.stat().st_size
        path.unlink()
        deleted += 1
        reclaimed += size
        if deleted >= limit:
            break
    remaining = sum(
        1
        for path in blob_root.iterdir()
        if path.is_file()
        and _SHA256_FILE.fullmatch(path.name)
        and "sha256:" + path.name not in referenced
    )
    return {
        "deleted_count": deleted,
        "reclaimed_bytes": reclaimed,
        "remaining_orphan_count": remaining,
        "referenced_count": len(referenced),
    }


def _copy_tree_if_present(source: Path, target: Path) -> None:
    if not source.exists():
        return
    shutil.copytree(source, target, dirs_exist_ok=False, copy_function=shutil.copy2)


def create_verified_backup(
    *,
    private_root: Path,
    backup_root: Path,
) -> dict[str, Any]:
    """Create a separate restorable database and content backup."""

    private_root = private_root.resolve()
    backup_root = backup_root.resolve()
    if (
        backup_root == private_root
        or private_root in backup_root.parents
        or backup_root in private_root.parents
    ):
        raise ValueError(
            "backup root must be a separate sibling of MATTERS_HOME"
        )
    if backup_root.exists():
        raise FileExistsError("backup root already exists")
    backup_root.mkdir(parents=True)
    database_path = private_root / "matters.sqlite3"
    target_database = backup_root / "matters.sqlite3"
    with _connect(database_path) as source:
        source.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        before = {
            "quick_check": _quick_check(source),
            "critical_current_counts": _current_owner_counts(source),
            "source_identity_digest": _source_identity_digest(source),
        }
        target = sqlite3.connect(target_database)
        try:
            source.backup(target, pages=8192, sleep=0.01)
        finally:
            target.close()
    copied_directories: list[str] = []
    for name in (
        "blobs",
        "connector-pages",
        "generated-hero-staging",
        "runtime",
        "receipts",
        "release-evidence",
        "flowguard-receipts",
    ):
        source = private_root / name
        if source.exists():
            _copy_tree_if_present(source, backup_root / name)
            copied_directories.append(name)
    with _connect(target_database, read_only=True) as restored:
        after = {
            "quick_check": _quick_check(restored),
            "critical_current_counts": _current_owner_counts(restored),
            "source_identity_digest": _source_identity_digest(restored),
        }
    if before != after or after["quick_check"] != "ok":
        raise RuntimeError("recovery database verification failed")
    blob_stats = _tree_stats(
        backup_root / "blobs",
        verify_named_hashes=True,
    )
    if blob_stats["named_hash_failure_count"]:
        raise RuntimeError("recovery blob verification failed")
    manifest = {
        "migration_id": MIGRATION_ID,
        "created_at": _utc_now(),
        "source_private_root": str(private_root),
        "backup_root": str(backup_root),
        "database_file": "matters.sqlite3",
        "database_byte_count": target_database.stat().st_size,
        "database_sha256": _file_hash(target_database),
        "database_verification": after,
        "copied_directories": copied_directories,
        "blob_stats": blob_stats,
        "status": "verified_restorable_backup",
    }
    (backup_root / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest


def verify_backup(backup_root: Path) -> dict[str, Any]:
    manifest_path = backup_root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError("verified backup manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    database_path = backup_root / str(manifest["database_file"])
    if _file_hash(database_path) != str(manifest["database_sha256"]):
        raise RuntimeError("recovery database hash does not match manifest")
    with _connect(database_path, read_only=True) as connection:
        observed = {
            "quick_check": _quick_check(connection),
            "critical_current_counts": _current_owner_counts(connection),
            "source_identity_digest": _source_identity_digest(connection),
        }
    if observed != dict(manifest["database_verification"]):
        raise RuntimeError("recovery database contents do not match manifest")
    blob_stats = _tree_stats(
        backup_root / "blobs",
        verify_named_hashes=True,
    )
    if blob_stats != dict(manifest["blob_stats"]):
        raise RuntimeError("recovery blob tree does not match manifest")
    return {
        "status": "verified_restorable_backup",
        "backup_root": str(backup_root.resolve()),
        "database_verification": observed,
        "blob_stats": blob_stats,
    }


def _require_verified_manifest(backup_root: Path) -> dict[str, Any]:
    manifest_path = backup_root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError("verified backup manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if str(manifest.get("status", "")) != "verified_restorable_backup":
        raise RuntimeError("backup manifest is not a verified recovery owner")
    database_path = backup_root / str(manifest.get("database_file", ""))
    if not database_path.is_file():
        raise FileNotFoundError("recovery database is missing")
    return manifest


def apply_database_batch(
    *,
    private_root: Path,
    backup_root: Path,
    limit: int = 200,
) -> dict[str, Any]:
    """Apply one bounded, idempotent database migration batch."""

    if limit < 1 or limit > 1000:
        raise ValueError("migration batch limit must be between one and one thousand")
    _require_verified_manifest(backup_root)
    database_path = private_root / "matters.sqlite3"
    with _connect(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            phases = (
                (
                    "source_pointer_rebase",
                    lambda: _rebase_source_pointer_batch(
                        connection,
                        limit=limit,
                    ),
                ),
                (
                    "source_snapshots",
                    lambda: _scrub_snapshot_batch(
                        connection,
                        owner="source_version",
                        json_path="$.content.body_text",
                        limit=limit,
                    ),
                ),
                (
                    "processing_snapshots",
                    lambda: _scrub_snapshot_batch(
                        connection,
                        owner="source_processing_result",
                        json_path=(
                            "$.registration.source_version.content.body_text"
                        ),
                        limit=limit,
                    ),
                ),
                (
                    "source_idempotency",
                    lambda: _scrub_idempotency_batch(
                        connection,
                        limit=limit,
                    ),
                ),
                (
                    "document_previews",
                    lambda: _retire_document_preview_batch(
                        connection,
                        limit=limit,
                    ),
                ),
                (
                    "descendant_heroes",
                    lambda: _retire_child_hero_batch(
                        connection,
                        limit=limit,
                    ),
                ),
            )
            for phase, action in phases:
                processed = action()
                if processed:
                    connection.commit()
                    return {
                        "migration_id": MIGRATION_ID,
                        "phase": phase,
                        "processed_count": processed,
                        "status": "batch_committed",
                        "has_more": True,
                    }
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
    return {
        "migration_id": MIGRATION_ID,
        "phase": "database",
        "processed_count": 0,
        "status": "database_current",
        "has_more": False,
    }


def clean_staging(
    *,
    private_root: Path,
    backup_root: Path,
) -> dict[str, Any]:
    _require_verified_manifest(backup_root)
    report = residual_report(private_root / "matters.sqlite3")
    blocking = {
        key: value
        for key, value in report.items()
        if key.endswith("_raw_count")
        or key in {
            "unrebased_source_snapshot_count",
            "active_document_preview_count",
            "current_child_hero_count",
        }
        if int(value)
    }
    if blocking:
        raise RuntimeError(
            "staging cleanup blocked by migration residuals: "
            + ",".join(sorted(blocking))
        )
    deleted_files = 0
    deleted_bytes = 0
    for name in ("connector-pages", "generated-hero-staging"):
        root = private_root / name
        if not root.exists():
            continue
        for path in sorted(
            (item for item in root.rglob("*") if item.is_file()),
            reverse=True,
        ):
            deleted_bytes += path.stat().st_size
            path.unlink()
            deleted_files += 1
        for path in sorted(
            (item for item in root.rglob("*") if item.is_dir()),
            key=lambda item: len(item.parts),
            reverse=True,
        ):
            if path != root:
                path.rmdir()
    return {
        "status": "staging_current",
        "deleted_file_count": deleted_files,
        "deleted_bytes": deleted_bytes,
    }


def verify_migration(
    *,
    private_root: Path,
    backup_root: Path,
) -> dict[str, Any]:
    backup = verify_backup(backup_root)
    database_path = private_root / "matters.sqlite3"
    report = residual_report(database_path)
    current_counts = dict(report["critical_current_counts"])
    current_source_digest = str(report["source_identity_digest"])
    quick_check = str(report["database_quick_check"])
    with _connect(database_path, read_only=True) as connection:
        referenced = _current_blob_refs(connection)
    expected = dict(backup["database_verification"])
    count_mismatches = {
        owner: {
            "before": int(expected["critical_current_counts"].get(owner, 0)),
            "after": int(current_counts.get(owner, 0)),
        }
        for owner in _CRITICAL_COUNT_OWNERS
        if owner not in {"generated_hero_record", "visual_asset"}
        and int(expected["critical_current_counts"].get(owner, 0))
        != int(current_counts.get(owner, 0))
    }
    missing_blob_refs = tuple(
        sorted(
            reference
            for reference in referenced
            if not (
                private_root
                / "blobs"
                / reference.removeprefix("sha256:")
            ).is_file()
        )
    )
    residual_total = sum(
        int(report[key])
        for key in (
            "unrebased_source_snapshot_count",
            "source_snapshot_raw_count",
            "processing_snapshot_raw_count",
            "idempotency_raw_count",
            "active_document_preview_count",
            "current_child_hero_count",
        )
    )
    source_digest_matches = (
        current_source_digest == str(expected["source_identity_digest"])
    )
    status = (
        "verified_current"
        if (
            residual_total == 0
            and not count_mismatches
            and not missing_blob_refs
            and source_digest_matches
            and quick_check == "ok"
        )
        else "blocked"
    )
    return {
        "migration_id": MIGRATION_ID,
        "status": status,
        "residual_report": report,
        "count_mismatches": count_mismatches,
        "source_identity_digest_matches": source_digest_matches,
        "database_quick_check": quick_check,
        "missing_current_blob_ref_count": len(missing_blob_refs),
        "missing_current_blob_refs": missing_blob_refs[:20],
        "physical_compaction": "separate_not_run",
    }


@dataclass(frozen=True)
class SourceInPlaceMigrationPaths:
    private_root: Path
    backup_root: Path

    def __post_init__(self) -> None:
        private_root = self.private_root.expanduser().resolve()
        backup_root = self.backup_root.expanduser().resolve()
        if (
            private_root == backup_root
            or private_root in backup_root.parents
            or backup_root in private_root.parents
        ):
            raise ValueError(
                "backup root must be a separate sibling of MATTERS_HOME"
            )
        object.__setattr__(self, "private_root", private_root)
        object.__setattr__(self, "backup_root", backup_root)

    @property
    def database_path(self) -> Path:
        return self.private_root / "matters.sqlite3"


__all__ = [
    "MANIFEST_NAME",
    "MIGRATION_ID",
    "SourceInPlaceMigrationPaths",
    "apply_database_batch",
    "clean_staging",
    "create_verified_backup",
    "reclaim_orphan_blobs",
    "residual_report",
    "verify_backup",
    "verify_migration",
]
