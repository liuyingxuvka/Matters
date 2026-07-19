"""Pure trace predicates."""

from matters.timeline.events import TemporalTrace


def has_actual_start(trace: TemporalTrace) -> bool:
    return any(
        event.kind in {"actual_start_reported", "work_recorded"}
        for event in trace.events
    )


__all__ = ["has_actual_start"]
