"""Injected persistence owner for C5 MaterialClue and C12 activity projection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from threading import RLock
from typing import Any, Callable, Iterable, Mapping, Sequence

from matters.domain.activity import MaterialClue, MatterActivityProjection
from matters.timeline.start_boundary import parse_user_world_time


ACTIVITY_CLUE_OWNER = "matter_activity_clue"
MATTER_ACTIVITY_OWNER = "matter_activity"

SnapshotRow = tuple[str, str, int, Mapping[str, Any]]
AppendMany = Callable[[Iterable[SnapshotRow]], None]
CurrentLookup = Callable[[str, str], Mapping[str, Any] | None]
AncestorResolver = Callable[[str], Iterable[str]]


_ACTIVITY_TIME_FIELD_PRIORITY = {
    "source_observed_at": 0,
    "observed_at": 0,
    "received_at": 1,
    "internal_date": 1,
    "source_created_at": 2,
    "created_at": 2,
    "ctime": 2,
    "first_recorded_at": 2,
    "source_modified_at": 3,
    "modified_at": 3,
    "modified_ns": 3,
    "mtime": 3,
    "sent_at": 4,
    "message_date": 4,
    "authored_at": 4,
    "date": 4,
}

_ACTIVITY_TIME_BASIS = {
    "source_observed_at": "provider_observed_time",
    "observed_at": "provider_observed_time",
    "received_at": "message_received_time",
    "internal_date": "message_received_time",
    "source_created_at": "source_created_time",
    "created_at": "source_created_time",
    "ctime": "source_created_time",
    "first_recorded_at": "codex_first_recorded_time",
    "source_modified_at": "source_modified_time",
    "modified_at": "source_modified_time",
    "modified_ns": "filesystem_modified_time",
    "mtime": "source_modified_time",
    "sent_at": "message_sent_time",
    "message_date": "message_sent_time",
    "authored_at": "source_authored_time",
    "date": "source_authored_time",
}

_DATABASE_PROCESSING_TIME_FIELDS = frozenset(
    {
        "analysis_completed_at",
        "analyzed_at",
        "created_at",
        "indexed_at",
        "ingested_at",
        "processed_at",
        "processing_time",
        "registered_at",
        "scanned_at",
        "updated_at",
    }
)


@dataclass(frozen=True)
class SourceActivityTime:
    """Auditable deterministic result for one current source revision.

    ``observed_at`` is always canonical UTC when ``status`` is ``resolved``.
    Database row timestamps are intentionally outside the accepted layers and
    can only be reported as rejected fields, never as activity evidence.
    """

    status: str
    observed_at: str = ""
    basis: str = ""
    field_path: str = ""
    provider: str = ""
    source_id: str = ""
    source_version: int | None = None
    failure: str = ""
    rejected_fields: tuple[str, ...] = ()
    invalid_fields: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.status == "resolved"


@dataclass(frozen=True)
class _SourceTimeCandidate:
    at: datetime
    field: str
    field_path: str
    basis: str
    layer_priority: int


def _source_value(source: Any, field: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(field, default)
    return getattr(source, field, default)


def _normalized_time_field(value: Any, *, headers: bool = False) -> str:
    field = str(value).strip().rsplit(".", 1)[-1].casefold().replace("-", "_")
    if headers and field == "date":
        return "message_date"
    return field


def _activity_source_layers(
    source: Any,
) -> tuple[tuple[int, str, Mapping[str, Any], bool], ...]:
    """Return only source-owned metadata layers in fixed authority order."""

    layers: list[tuple[int, str, Mapping[str, Any], bool]] = []
    source_time_metadata = _source_value(source, "source_time_metadata", {})
    if isinstance(source_time_metadata, Mapping):
        layers.append((0, "source_time_metadata", source_time_metadata, False))

    metadata = _source_value(source, "metadata", {})
    if isinstance(metadata, Mapping):
        layers.append((1, "metadata", metadata, False))

    content = _source_value(source, "content", {})
    if isinstance(content, Mapping):
        nested_metadata = content.get("metadata")
        if isinstance(nested_metadata, Mapping):
            layers.append((2, "content.metadata", nested_metadata, False))
        layers.append((3, "content", content, False))
        headers = content.get("headers")
        if isinstance(headers, Mapping):
            layers.append((4, "content.headers", headers, True))
    return tuple(layers)


def resolve_source_activity_time(source: Any) -> SourceActivityTime:
    """Resolve the first licensed user-world time from one current source.

    Resolution is field-priority based: explicit observed, received, created,
    and modified timestamps precede weaker authored/message fields.  Within
    one semantic priority, the earliest valid value wins deterministically.
    The function performs no persistence, wall-clock lookup, or AI inference.
    """

    provider = str(_source_value(source, "provider", "")).strip()
    source_id = str(_source_value(source, "source_id", "")).strip()
    raw_version = _source_value(source, "version", None)
    try:
        source_version = int(raw_version) if raw_version is not None else None
    except (TypeError, ValueError):
        source_version = None

    if bool(_source_value(source, "tombstone", False)):
        return SourceActivityTime(
            status="unavailable",
            provider=provider,
            source_id=source_id,
            source_version=source_version,
            failure="source_is_tombstoned",
        )

    rejected_fields = tuple(
        sorted(
            f"source.{key}"
            for key in (
                source.keys()
                if isinstance(source, Mapping)
                else _DATABASE_PROCESSING_TIME_FIELDS
            )
            if str(key).casefold().replace("-", "_")
            in _DATABASE_PROCESSING_TIME_FIELDS
            and _source_value(source, str(key), None) not in (None, "")
        )
    )
    candidates: list[_SourceTimeCandidate] = []
    invalid_fields: list[str] = []
    eligible_field_count = 0
    for layer_priority, layer, values, headers in _activity_source_layers(source):
        for raw_key, raw_value in values.items():
            field = _normalized_time_field(raw_key, headers=headers)
            priority = _ACTIVITY_TIME_FIELD_PRIORITY.get(field)
            if priority is None:
                continue
            eligible_field_count += 1
            field_path = f"{layer}.{str(raw_key).strip()}"
            parsed = parse_user_world_time(raw_value, field=field)
            if parsed is None:
                invalid_fields.append(field_path)
                continue
            candidates.append(
                _SourceTimeCandidate(
                    at=parsed,
                    field=field,
                    field_path=field_path,
                    basis=_ACTIVITY_TIME_BASIS[field],
                    layer_priority=layer_priority,
                )
            )

    if candidates:
        selected = min(
            candidates,
            key=lambda item: (
                _ACTIVITY_TIME_FIELD_PRIORITY[item.field],
                item.at,
                item.layer_priority,
                item.field_path,
            ),
        )
        return SourceActivityTime(
            status="resolved",
            observed_at=selected.at.isoformat(),
            basis=selected.basis,
            field_path=selected.field_path,
            provider=provider,
            source_id=source_id,
            source_version=source_version,
            rejected_fields=rejected_fields,
            invalid_fields=tuple(sorted(set(invalid_fields))),
        )

    if eligible_field_count:
        failure = "eligible_source_time_invalid"
    elif rejected_fields:
        failure = "database_processing_time_not_user_world_evidence"
    else:
        failure = "source_time_metadata_missing"
    return SourceActivityTime(
        status="unavailable",
        provider=provider,
        source_id=source_id,
        source_version=source_version,
        failure=failure,
        rejected_fields=rejected_fields,
        invalid_fields=tuple(sorted(set(invalid_fields))),
    )


@dataclass(frozen=True)
class ActivityUpdate:
    clue_id: str
    disposition: str
    written_row_count: int
    bubbled_matter_ids: tuple[str, ...]
    projections: tuple[MatterActivityProjection, ...]
    idempotent: bool = False


class MatterActivityOwner:
    """Atomically persist activity without depending on a concrete store.

    ``append_many`` is the transaction boundary. ``current`` and
    ``ancestor_resolver`` are injected so the owner remains isolated from
    SQLite and hierarchy implementation details.
    """

    def __init__(
        self,
        *,
        append_many: AppendMany,
        current: CurrentLookup,
        ancestor_resolver: AncestorResolver,
    ) -> None:
        self._append_many = append_many
        self._current = current
        self._ancestor_resolver = ancestor_resolver
        self._lock = RLock()

    @staticmethod
    def _next_revision(current: Mapping[str, Any] | None) -> int:
        if current is None:
            return 1
        revision = int(current.get("persistence_revision", 0))
        if revision < 1:
            raise ValueError("current activity payload lacks a valid revision")
        return revision + 1

    @staticmethod
    def _clue_payload(clue: MaterialClue, persistence_revision: int) -> dict[str, Any]:
        token = (
            "MaterialClue"
            if clue.disposition == "material"
            else (
                "NonMaterialProcessing"
                if clue.disposition == "nonmaterial"
                else "MaterialityUncertain"
            )
        )
        return {
            "clue_id": clue.clue_id,
            "matter_id": clue.matter_id,
            "clue_kind": clue.clue_kind,
            "user_world_at": clue.user_world_at,
            "processed_at": clue.processed_at,
            "disposition": clue.disposition,
            "rationale": clue.rationale,
            "localized_summary": dict(clue.localized_summary),
            "semantic_revision": clue.semantic_revision,
            "evidence_ids": clue.evidence_ids,
            "binding_revision": clue.binding_revision,
            "identity_fingerprint": clue.identity_fingerprint,
            "completion_token": token,
            "advances_activity": clue.advances_activity,
            "persistence_revision": persistence_revision,
        }

    @staticmethod
    def _projection(payload: Mapping[str, Any]) -> MatterActivityProjection:
        return MatterActivityProjection(
            matter_id=str(payload["matter_id"]),
            source_matter_id=str(payload["source_matter_id"]),
            material_clue_id=str(payload["material_clue_id"]),
            latest_meaningful_clue_at=str(
                payload["latest_meaningful_clue_at"]
            ),
            localized_summary=dict(payload["localized_summary"]),
            semantic_revision=str(payload["semantic_revision"]),
            material_clue_revision=str(payload["material_clue_revision"]),
            summary_revision=str(payload["summary_revision"]),
            activity_order_revision=str(payload["activity_order_revision"]),
            evidence_ids=tuple(payload.get("evidence_ids", ())),
            ancestor_propagated=bool(payload["ancestor_propagated"]),
            persistence_revision=int(payload["persistence_revision"]),
            processed_at=str(payload["processed_at"]),
        )

    @staticmethod
    def _incoming_is_current(
        clue: MaterialClue,
        current: Mapping[str, Any] | None,
    ) -> bool:
        if current is None:
            return True
        current_rank = (
            str(current["latest_meaningful_clue_at"]),
            str(current["material_clue_id"]),
        )
        incoming_rank = (clue.user_world_at, clue.clue_id)
        return incoming_rank > current_rank

    def current_projection(
        self,
        matter_id: str,
    ) -> MatterActivityProjection | None:
        payload = self._current(MATTER_ACTIVITY_OWNER, matter_id)
        return self._projection(payload) if payload is not None else None

    def refresh_parent_from_descendants(
        self,
        *,
        parent_matter_id: str,
        descendant_matter_ids: Iterable[str],
    ) -> MatterActivityProjection | None:
        """Project the newest existing descendant clue after hierarchy changes."""

        if not parent_matter_id.strip():
            raise ValueError("parent Matter id is required")
        with self._lock:
            candidates = tuple(
                payload
                for descendant_id in dict.fromkeys(
                    str(item).strip()
                    for item in descendant_matter_ids
                    if str(item).strip()
                )
                if (
                    payload := self._current(
                        MATTER_ACTIVITY_OWNER,
                        descendant_id,
                    )
                )
                is not None
            )
            if not candidates:
                return None
            selected = max(
                candidates,
                key=lambda item: (
                    str(item.get("latest_meaningful_clue_at", "")),
                    str(item.get("material_clue_id", "")),
                ),
            )
            current = self._current(
                MATTER_ACTIVITY_OWNER,
                parent_matter_id,
            )
            selected_rank = (
                str(selected["latest_meaningful_clue_at"]),
                str(selected["material_clue_id"]),
            )
            current_rank = (
                (
                    str(current["latest_meaningful_clue_at"]),
                    str(current["material_clue_id"]),
                )
                if current is not None
                else ("", "")
            )
            if current is not None and current_rank >= selected_rank:
                return self._projection(current)
            persistence_revision = self._next_revision(current)
            projection = MatterActivityProjection(
                matter_id=parent_matter_id,
                source_matter_id=str(selected["source_matter_id"]),
                material_clue_id=str(selected["material_clue_id"]),
                latest_meaningful_clue_at=str(
                    selected["latest_meaningful_clue_at"]
                ),
                localized_summary=dict(selected["localized_summary"]),
                semantic_revision=str(selected["semantic_revision"]),
                material_clue_revision=str(
                    selected["material_clue_revision"]
                ),
                summary_revision=str(selected["summary_revision"]),
                activity_order_revision=str(
                    selected["activity_order_revision"]
                ),
                evidence_ids=tuple(selected.get("evidence_ids", ())),
                ancestor_propagated=True,
                persistence_revision=persistence_revision,
                processed_at=str(selected["processed_at"]),
            )
            self._append_many(
                (
                    (
                        MATTER_ACTIVITY_OWNER,
                        parent_matter_id,
                        persistence_revision,
                        asdict(projection),
                    ),
                )
            )
            return projection

    def correct_observation_time(
        self,
        clue: MaterialClue,
        *,
        superseded_clue_id: str,
        projection_matter_ids: Sequence[str] = (),
    ) -> ActivityUpdate:
        """Replace a due-time activity with its evidence observation time."""

        with self._lock:
            superseded = self._current(
                ACTIVITY_CLUE_OWNER,
                superseded_clue_id,
            )
            if (
                superseded is None
                or str(superseded.get("matter_id", "")) != clue.matter_id
                or str(superseded.get("disposition", "")) != "material"
            ):
                raise ValueError(
                    "activity time correction requires a current material clue"
                )
            prior_clue = self._current(ACTIVITY_CLUE_OWNER, clue.clue_id)
            if prior_clue is not None:
                if prior_clue.get("identity_fingerprint") != clue.identity_fingerprint:
                    raise ValueError(
                        "activity correction identity already has different semantics"
                    )
            rows: list[SnapshotRow] = []
            if prior_clue is None:
                clue_revision = self._next_revision(prior_clue)
                clue_payload = self._clue_payload(clue, clue_revision)
                clue_payload["supersedes_clue_id"] = superseded_clue_id
                rows.append(
                    (
                        ACTIVITY_CLUE_OWNER,
                        clue.clue_id,
                        clue_revision,
                        clue_payload,
                    )
                )
            projections: list[MatterActivityProjection] = []
            direct_targets = tuple(
                dict.fromkeys(
                    (
                        clue.matter_id,
                        *(
                            str(item).strip()
                            for item in projection_matter_ids
                            if str(item).strip()
                        ),
                    )
                )
            )
            target_ids = tuple(
                dict.fromkeys(
                    (
                        *direct_targets,
                        *(
                            str(ancestor).strip()
                            for matter_id in direct_targets
                            for ancestor in self._ancestor_resolver(matter_id)
                            if str(ancestor).strip()
                        ),
                    )
                )
            )
            for target_id in target_ids:
                current = self._current(MATTER_ACTIVITY_OWNER, target_id)
                if (
                    current is not None
                    and str(current.get("material_clue_id", ""))
                    == clue.clue_id
                ):
                    continue
                if (
                    current is not None
                    and str(current.get("material_clue_id", ""))
                    != superseded_clue_id
                    and not self._incoming_is_current(clue, current)
                ):
                    continue
                persistence_revision = self._next_revision(current)
                projection = MatterActivityProjection(
                    matter_id=target_id,
                    source_matter_id=clue.matter_id,
                    material_clue_id=clue.clue_id,
                    latest_meaningful_clue_at=clue.user_world_at,
                    localized_summary=clue.localized_summary,
                    semantic_revision=clue.semantic_revision,
                    material_clue_revision=clue.binding_revision,
                    summary_revision=clue.binding_revision,
                    activity_order_revision=clue.binding_revision,
                    evidence_ids=clue.evidence_ids,
                    ancestor_propagated=target_id != clue.matter_id,
                    persistence_revision=persistence_revision,
                    processed_at=clue.processed_at,
                )
                rows.append(
                    (
                        MATTER_ACTIVITY_OWNER,
                        target_id,
                        persistence_revision,
                        asdict(projection),
                    )
                )
                projections.append(projection)
            self._append_many(tuple(rows))
            return ActivityUpdate(
                clue_id=clue.clue_id,
                disposition=clue.disposition,
                written_row_count=len(rows),
                bubbled_matter_ids=tuple(
                    projection.matter_id for projection in projections
                ),
                projections=tuple(projections),
                idempotent=not rows,
            )

    def record(self, clue: MaterialClue) -> ActivityUpdate:
        """Record one disposition and atomically publish every affected Matter."""

        with self._lock:
            prior_clue = self._current(ACTIVITY_CLUE_OWNER, clue.clue_id)
            if prior_clue is not None:
                if prior_clue.get("identity_fingerprint") != clue.identity_fingerprint:
                    raise ValueError(
                        "clue identity already exists with different semantics"
                    )
                return ActivityUpdate(
                    clue_id=clue.clue_id,
                    disposition=clue.disposition,
                    written_row_count=0,
                    bubbled_matter_ids=(),
                    projections=(),
                    idempotent=True,
                )

            clue_revision = self._next_revision(prior_clue)
            rows: list[SnapshotRow] = [
                (
                    ACTIVITY_CLUE_OWNER,
                    clue.clue_id,
                    clue_revision,
                    self._clue_payload(clue, clue_revision),
                )
            ]
            projections: list[MatterActivityProjection] = []

            if clue.advances_activity:
                target_ids = tuple(
                    dict.fromkeys(
                        (
                            clue.matter_id,
                            *(
                                str(item).strip()
                                for item in self._ancestor_resolver(clue.matter_id)
                                if str(item).strip()
                            ),
                        )
                    )
                )
                for target_id in target_ids:
                    current = self._current(MATTER_ACTIVITY_OWNER, target_id)
                    if not self._incoming_is_current(clue, current):
                        continue
                    persistence_revision = self._next_revision(current)
                    projection = MatterActivityProjection(
                        matter_id=target_id,
                        source_matter_id=clue.matter_id,
                        material_clue_id=clue.clue_id,
                        latest_meaningful_clue_at=clue.user_world_at,
                        localized_summary=clue.localized_summary,
                        semantic_revision=clue.semantic_revision,
                        material_clue_revision=clue.binding_revision,
                        summary_revision=clue.binding_revision,
                        activity_order_revision=clue.binding_revision,
                        evidence_ids=clue.evidence_ids,
                        ancestor_propagated=target_id != clue.matter_id,
                        persistence_revision=persistence_revision,
                        processed_at=clue.processed_at,
                    )
                    rows.append(
                        (
                            MATTER_ACTIVITY_OWNER,
                            target_id,
                            persistence_revision,
                            asdict(projection),
                        )
                    )
                    projections.append(projection)

            self._append_many(tuple(rows))
            return ActivityUpdate(
                clue_id=clue.clue_id,
                disposition=clue.disposition,
                written_row_count=len(rows),
                bubbled_matter_ids=tuple(
                    projection.matter_id for projection in projections
                ),
                projections=tuple(projections),
            )


__all__ = [
    "ACTIVITY_CLUE_OWNER",
    "MATTER_ACTIVITY_OWNER",
    "ActivityUpdate",
    "AncestorResolver",
    "AppendMany",
    "CurrentLookup",
    "MatterActivityOwner",
    "SnapshotRow",
    "SourceActivityTime",
    "resolve_source_activity_time",
]
