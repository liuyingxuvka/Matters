"""C5: typed temporal events and contradiction-preserving traces."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Iterable
import unicodedata


EVENT_MODALITIES = frozenset({"observed", "reported", "planned", "inferred"})


def _normalized_identity(value: object) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(normalized.split())


def _logical_event_key(
    *,
    explicit_key: str,
    kind: str,
    object_ref: str,
    actor: str,
    occurrence_boundary: str,
) -> str:
    """Return a stable C5 identity that excludes source/evidence revisions.

    The semantic owner should provide ``explicit_key`` whenever a later
    correction may change time or wording.  The bounded derivation is retained
    for typed provider events and older current callers; unlike ``event_id`` it
    never consumes a SourceVersion or EvidenceAnchor identity.
    """

    supplied = _normalized_identity(explicit_key)
    if supplied:
        return "logical-event:" + sha256(supplied.encode("utf-8")).hexdigest()
    boundary = "\0".join(
        (
            _normalized_identity(object_ref),
            _normalized_identity(kind),
            _normalized_identity(actor),
            _normalized_identity(occurrence_boundary),
        )
    )
    return "logical-event:" + sha256(boundary.encode("utf-8")).hexdigest()


def _parse_aware_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("historical inference times require a timezone")
    return parsed.astimezone(timezone.utc)


def _provider_event_id(
    external_id: str,
    event_kind: str,
    event_boundary: object,
    revision_payload: object,
) -> str:
    digest = sha256(
        repr(
            (
                _normalized_identity(external_id),
                _normalized_identity(event_kind),
                _normalized_identity(event_boundary),
                revision_payload,
            )
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"event:{external_id}:{event_kind}:{digest}"


@dataclass(frozen=True)
class Event:
    event_id: str
    kind: str
    modality: str
    record_time: str = ""
    claimed_time: str = ""
    actor: str = ""
    object_ref: str = ""
    evidence_ids: tuple[str, ...] = ()
    logical_event_key: str = ""
    current_revision: bool = True
    supersedes_event_id: str = ""
    temporal_direction: str = ""
    inference_purpose: str = ""
    inference_as_of: str = ""
    target_time: str = ""
    revisable: bool = False
    contradiction_triggers: tuple[str, ...] = ()


@dataclass(frozen=True)
class TemporalGap:
    reason: str
    source_event_id: str = ""


@dataclass(frozen=True)
class TemporalTrace:
    events: tuple[Event, ...]
    conflicts: tuple[str, ...] = ()
    gaps: tuple[TemporalGap, ...] = ()
    best_interpretation: str = ""
    interpretation_status: str = "current_best"


@dataclass
class EventRegistry:
    _events: list[Event] = field(default_factory=list)

    def restore(self, events: Iterable[Event]) -> None:
        """Restore durable event revisions without inventing new history.

        Durable rows use one object id per semantic extraction and append a
        later revision to that same object id when the original C5 owner
        corrects its logical identity or supersession edge.  Restoration must
        therefore preserve the stored event ids and only project explicit
        supersession edges into the in-memory current flags.
        """

        by_id: dict[str, Event] = {}
        order: list[str] = []
        for event in events:
            if event.event_id not in by_id:
                order.append(event.event_id)
            by_id[event.event_id] = event
        superseded_ids = {
            event.supersedes_event_id
            for event in by_id.values()
            if event.supersedes_event_id
        }
        self._events = [
            replace(
                by_id[event_id],
                current_revision=(
                    bool(by_id[event_id].current_revision)
                    and event_id not in superseded_ids
                ),
            )
            for event_id in order
        ]

    def revise_existing(
        self,
        *,
        event_id: str,
        kind: str,
        claimed_time: str,
        record_time: str,
        actor: str,
        object_ref: str,
        evidence_ids: tuple[str, ...],
        modality: str,
        logical_event_key: str,
        occurrence_boundary: str = "",
        supersedes_event_id: str = "",
        temporal_direction: str = "",
        inference_purpose: str = "",
        inference_as_of: str = "",
        target_time: str = "",
        revisable: bool = False,
        contradiction_triggers: tuple[str, ...] = (),
    ) -> Event:
        """Append one C5-owned correction to an existing durable event id."""

        if not event_id:
            raise ValueError("event revision target is required")
        target_indexes = tuple(
            index
            for index, existing in enumerate(self._events)
            if existing.event_id == event_id
        )
        if len(target_indexes) != 1:
            raise ValueError("event revision target is unavailable or ambiguous")
        if not evidence_ids:
            raise ValueError("semantic events require evidence")
        if modality not in EVENT_MODALITIES:
            raise ValueError("unsupported event modality")
        normalized_triggers = tuple(
            item.strip() for item in contradiction_triggers if item.strip()
        )
        self._validate_inference_boundary(
            modality=modality,
            temporal_direction=temporal_direction,
            inference_purpose=inference_purpose,
            inference_as_of=inference_as_of,
            target_time=target_time,
            revisable=revisable,
            contradiction_triggers=normalized_triggers,
        )
        stable_logical_key = _logical_event_key(
            explicit_key=logical_event_key,
            kind=kind,
            object_ref=object_ref,
            actor=actor,
            occurrence_boundary=(
                occurrence_boundary or claimed_time or record_time
            ),
        )
        if supersedes_event_id:
            superseded_indexes = tuple(
                index
                for index, existing in enumerate(self._events)
                if existing.event_id == supersedes_event_id
                and existing.current_revision
            )
            if len(superseded_indexes) != 1:
                raise ValueError(
                    "event supersession target is unavailable or not current"
                )
            if supersedes_event_id == event_id:
                raise ValueError("an event cannot supersede itself")
            for index in superseded_indexes:
                self._events[index] = replace(
                    self._events[index],
                    current_revision=False,
                )
        target_index = target_indexes[0]
        revised = replace(
            self._events[target_index],
            kind=kind,
            modality=modality,
            record_time=record_time,
            claimed_time=claimed_time,
            actor=actor,
            object_ref=object_ref,
            evidence_ids=evidence_ids,
            logical_event_key=stable_logical_key,
            current_revision=True,
            supersedes_event_id=supersedes_event_id,
            temporal_direction=temporal_direction,
            inference_purpose=inference_purpose,
            inference_as_of=inference_as_of,
            target_time=target_time,
            revisable=revisable,
            contradiction_triggers=normalized_triggers,
        )
        self._events[target_index] = revised
        return revised

    def _record_revision(self, event: Event) -> Event:
        """Record one current revision and retain replaced revisions in history."""

        for existing in self._events:
            if existing.event_id == event.event_id:
                return existing
        current_indexes = tuple(
            index
            for index, existing in enumerate(self._events)
            if existing.logical_event_key == event.logical_event_key
            and existing.current_revision
        )
        supersedes_event_id = event.supersedes_event_id
        if current_indexes:
            current = self._events[current_indexes[-1]]
            if supersedes_event_id and supersedes_event_id != current.event_id:
                raise ValueError(
                    "event supersession must name the exact current revision"
                )
            supersedes_event_id = current.event_id
            for index in current_indexes:
                self._events[index] = replace(
                    self._events[index],
                    current_revision=False,
                )
        elif supersedes_event_id and not any(
            existing.event_id == supersedes_event_id
            for existing in self._events
        ):
            raise ValueError("event supersession target is unavailable")
        recorded = replace(
            event,
            current_revision=True,
            supersedes_event_id=supersedes_event_id,
        )
        self._events.append(recorded)
        return recorded

    @staticmethod
    def _validate_inference_boundary(
        *,
        modality: str,
        temporal_direction: str,
        inference_purpose: str,
        inference_as_of: str,
        target_time: str,
        revisable: bool,
        contradiction_triggers: tuple[str, ...],
    ) -> None:
        if modality != "inferred":
            if any(
                (
                    temporal_direction,
                    inference_purpose,
                    inference_as_of,
                    target_time,
                    revisable,
                    contradiction_triggers,
                )
            ):
                raise ValueError(
                    "historical-inference metadata requires inferred modality"
                )
            return
        supplied = any(
            (
                temporal_direction,
                inference_purpose,
                inference_as_of,
                target_time,
                revisable,
                contradiction_triggers,
            )
        )
        if not supplied:
            return
        if (
            temporal_direction != "past"
            or inference_purpose != "historical_gap_fill"
            or not revisable
            or not contradiction_triggers
            or not inference_as_of
            or not target_time
        ):
            raise ValueError(
                "inferred canonical events must be revisable historical gap fills"
            )
        if _parse_aware_time(target_time) > _parse_aware_time(inference_as_of):
            raise ValueError(
                "future predictions cannot become canonical temporal events"
            )

    def from_understanding(
        self,
        *,
        kind: str,
        source_revision: str,
        claimed_time: str = "",
        record_time: str = "",
        actor: str = "",
        object_ref: str = "",
        evidence_ids: tuple[str, ...] = (),
        modality: str = "inferred",
        logical_event_key: str = "",
        occurrence_boundary: str = "",
        supersedes_event_id: str = "",
        temporal_direction: str = "",
        inference_purpose: str = "",
        inference_as_of: str = "",
        target_time: str = "",
        revisable: bool = False,
        contradiction_triggers: tuple[str, ...] = (),
    ) -> Event:
        """Record one owner-validated, evidence-bound semantic event."""

        if not evidence_ids:
            raise ValueError("semantic event requires evidence")
        if modality not in EVENT_MODALITIES:
            raise ValueError("semantic event modality is unsupported")
        normalized_triggers = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in contradiction_triggers
                if str(item).strip()
            )
        )
        self._validate_inference_boundary(
            modality=modality,
            temporal_direction=temporal_direction,
            inference_purpose=inference_purpose,
            inference_as_of=inference_as_of,
            target_time=target_time,
            revisable=revisable,
            contradiction_triggers=normalized_triggers,
        )
        stable_logical_key = _logical_event_key(
            explicit_key=logical_event_key,
            kind=kind,
            object_ref=object_ref or source_revision,
            actor=actor,
            occurrence_boundary=(
                occurrence_boundary or claimed_time or record_time
            ),
        )
        digest = sha256(
            (
                f"{kind}\0{source_revision}\0{claimed_time}\0"
                f"{record_time}\0{object_ref}\0{evidence_ids}\0"
                f"{stable_logical_key}"
            ).encode("utf-8")
        ).hexdigest()[:24]
        event = Event(
            event_id=f"event:understanding:{digest}",
            kind=kind,
            modality=modality,
            record_time=record_time,
            claimed_time=claimed_time,
            actor=actor,
            object_ref=object_ref or source_revision,
            evidence_ids=evidence_ids,
            logical_event_key=stable_logical_key,
            supersedes_event_id=supersedes_event_id,
            temporal_direction=temporal_direction,
            inference_purpose=inference_purpose,
            inference_as_of=inference_as_of,
            target_time=target_time,
            revisable=revisable,
            contradiction_triggers=normalized_triggers,
        )
        return self._record_revision(event)

    def from_provider_payload(
        self,
        external_id: str,
        payload: dict[str, Any],
    ) -> TemporalTrace:
        events: list[Event] = []
        gaps: list[TemporalGap] = []
        conflicts: list[str] = []
        for index, item in enumerate(payload.get("change_items", ())):
            if item.get("field") != "status":
                continue
            target = str(item.get("to", ""))
            events.append(
                self._record_revision(
                    Event(
                        event_id=_provider_event_id(
                            external_id,
                            "status",
                            item.get("event_boundary", index),
                            (
                                target,
                                str(item.get("at", "")),
                                str(item.get("actor", "")),
                            ),
                        ),
                        kind=f"status:{target.lower().replace(' ', '_')}",
                        modality="reported",
                        record_time=str(item.get("at", "")),
                        object_ref=external_id,
                        logical_event_key=_logical_event_key(
                            explicit_key=str(
                                item.get("logical_event_key", "")
                            ),
                            kind=f"status:{target.lower().replace(' ', '_')}",
                            object_ref=external_id,
                            actor=str(item.get("actor", "")),
                            occurrence_boundary=str(
                                item.get("event_boundary", index)
                            ),
                        ),
                    )
                )
            )
        for index, worklog in enumerate(payload.get("worklog", ())):
            events.append(
                self._record_revision(
                    Event(
                        event_id=_provider_event_id(
                            external_id,
                            "worklog",
                            worklog.get("event_boundary", index),
                            (
                                str(worklog.get("at", "")),
                                str(worklog.get("actor", "")),
                            ),
                        ),
                        kind="work_recorded",
                        modality="observed",
                        record_time=str(worklog.get("at", "")),
                        object_ref=external_id,
                        logical_event_key=_logical_event_key(
                            explicit_key=str(
                                worklog.get("logical_event_key", "")
                            ),
                            kind="work_recorded",
                            object_ref=external_id,
                            actor=str(worklog.get("actor", "")),
                            occurrence_boundary=str(
                                worklog.get("event_boundary", index)
                            ),
                        ),
                    )
                )
            )
        comments = payload.get("comments", ())
        for index, comment in enumerate(comments):
            text = str(comment.get("body", "")).lower()
            if "started" in text:
                events.append(
                    self._record_revision(
                        Event(
                            event_id=_provider_event_id(
                                external_id,
                                "start",
                                comment.get("event_boundary", index),
                                (
                                    str(comment.get("at", "")),
                                    str(comment.get("actor", "")),
                                    text,
                                ),
                            ),
                            kind="actual_start_reported",
                            modality="reported",
                            record_time=str(comment.get("at", "")),
                            object_ref=external_id,
                            logical_event_key=_logical_event_key(
                                explicit_key=str(
                                    comment.get(
                                        "start_logical_event_key",
                                        "",
                                    )
                                ),
                                kind="actual_start_reported",
                                object_ref=external_id,
                                actor=str(comment.get("actor", "")),
                                occurrence_boundary=str(
                                    comment.get("event_boundary", index)
                                ),
                            ),
                        )
                    )
                )
            if "blocked" in text:
                events.append(
                    self._record_revision(
                        Event(
                            event_id=_provider_event_id(
                                external_id,
                                "blocked",
                                comment.get("event_boundary", index),
                                (
                                    str(comment.get("at", "")),
                                    str(comment.get("actor", "")),
                                    text,
                                ),
                            ),
                            kind="blocked_reported",
                            modality="reported",
                            record_time=str(comment.get("at", "")),
                            object_ref=external_id,
                            logical_event_key=_logical_event_key(
                                explicit_key=str(
                                    comment.get(
                                        "blocked_logical_event_key",
                                        "",
                                    )
                                ),
                                kind="blocked_reported",
                                object_ref=external_id,
                                actor=str(comment.get("actor", "")),
                                occurrence_boundary=str(
                                    comment.get("event_boundary", index)
                                ),
                            ),
                        )
                    )
                )
        if payload.get("scheduled_event"):
            events.append(
                self._record_revision(
                    Event(
                        event_id=_provider_event_id(
                            external_id,
                            "planned",
                            "scheduled_event",
                            str(payload.get("scheduled_event")),
                        ),
                        kind="planned_event",
                        modality="planned",
                        claimed_time=str(payload.get("scheduled_event")),
                        object_ref=external_id,
                        logical_event_key=_logical_event_key(
                            explicit_key=str(
                                payload.get(
                                    "scheduled_logical_event_key",
                                    "",
                                )
                            ),
                            kind="planned_event",
                            object_ref=external_id,
                            actor="",
                            occurrence_boundary="scheduled_event",
                        ),
                    )
                )
            )
        status_kinds = {event.kind for event in events}
        if "status:done" in status_kinds and "status:reopened" in status_kinds:
            conflicts.append("done_then_reopened")
        if payload.get("assignee") and not any(
            event.kind in {"actual_start_reported", "work_recorded"}
            for event in events
        ):
            gaps.append(TemporalGap("assignment does not prove actual start"))
        return TemporalTrace(
            events=tuple(events),
            conflicts=tuple(conflicts),
            gaps=tuple(gaps),
            best_interpretation=(
                "latest reported transition is current while the earlier "
                "completion remains in history"
                if conflicts
                else "events are ordered by claimed time then record time"
            ),
            interpretation_status=(
                "conflicted_current_best" if conflicts else "current_best"
            ),
        )


__all__ = [
    "EVENT_MODALITIES",
    "Event",
    "EventRegistry",
    "TemporalGap",
    "TemporalTrace",
]
