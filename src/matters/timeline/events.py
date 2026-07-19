"""C5: typed temporal events and contradiction-preserving traces."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any


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
    ) -> Event:
        """Record one owner-validated, evidence-bound semantic event."""

        if not evidence_ids:
            raise ValueError("semantic event requires evidence")
        digest = sha256(
            (
                f"{kind}\0{source_revision}\0{claimed_time}\0"
                f"{record_time}\0{object_ref}\0{evidence_ids}"
            ).encode("utf-8")
        ).hexdigest()[:24]
        event = Event(
            event_id=f"event:understanding:{digest}",
            kind=kind,
            modality="inferred",
            record_time=record_time,
            claimed_time=claimed_time,
            actor=actor,
            object_ref=object_ref or source_revision,
            evidence_ids=evidence_ids,
        )
        if event not in self._events:
            self._events.append(event)
        return event

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
                Event(
                    event_id=f"event:{external_id}:status:{index}",
                    kind=f"status:{target.lower().replace(' ', '_')}",
                    modality="reported",
                    record_time=str(item.get("at", "")),
                    object_ref=external_id,
                )
            )
        for index, worklog in enumerate(payload.get("worklog", ())):
            events.append(
                Event(
                    event_id=f"event:{external_id}:worklog:{index}",
                    kind="work_recorded",
                    modality="observed",
                    record_time=str(worklog.get("at", "")),
                    object_ref=external_id,
                )
            )
        comments = payload.get("comments", ())
        for index, comment in enumerate(comments):
            text = str(comment.get("body", "")).lower()
            if "started" in text:
                events.append(
                    Event(
                        event_id=f"event:{external_id}:start:{index}",
                        kind="actual_start_reported",
                        modality="reported",
                        record_time=str(comment.get("at", "")),
                        object_ref=external_id,
                    )
                )
            if "blocked" in text:
                events.append(
                    Event(
                        event_id=f"event:{external_id}:blocked:{index}",
                        kind="blocked_reported",
                        modality="reported",
                        record_time=str(comment.get("at", "")),
                        object_ref=external_id,
                    )
                )
        if payload.get("scheduled_event"):
            events.append(
                Event(
                    event_id=f"event:{external_id}:planned",
                    kind="planned_event",
                    modality="planned",
                    claimed_time=str(payload.get("scheduled_event")),
                    object_ref=external_id,
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
        self._events.extend(events)
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


__all__ = ["Event", "EventRegistry", "TemporalGap", "TemporalTrace"]
