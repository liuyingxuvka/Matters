"""C5 earliest traceable Matter Start-boundary derivation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Iterable, Mapping, Sequence


_SOURCE_TIME_FIELDS = frozenset(
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


@dataclass(frozen=True)
class StartBoundary:
    """One private-path-safe projection of the earliest user-world clue."""

    value: str
    at: datetime
    basis: str
    provider: str = ""
    field: str = ""

    @property
    def year(self) -> str:
        return f"{self.at.year:04d}"


def parse_user_world_time(value: Any, *, field: str = "") -> datetime | None:
    """Parse provider time values without accepting processing-time semantics."""

    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value or "").strip()
        if not raw or raw.casefold() in {"none", "null", "unknown"}:
            return None
        numeric: float | None = None
        try:
            numeric = float(raw)
        except ValueError:
            pass
        if numeric is not None:
            normalized_field = field.casefold().replace("-", "_")
            absolute = abs(numeric)
            if normalized_field.endswith("_ns") or absolute >= 1e17:
                numeric /= 1_000_000_000
            elif absolute >= 1e14:
                numeric /= 1_000_000
            elif absolute >= 1e11:
                numeric /= 1_000
            try:
                parsed = datetime.fromtimestamp(numeric, tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None
        else:
            normalized = raw.replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(normalized)
            except ValueError:
                try:
                    parsed = parsedate_to_datetime(raw)
                except (TypeError, ValueError, OverflowError):
                    return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _source_layers(
    source_version: Mapping[str, Any],
) -> Iterable[tuple[str, Mapping[str, Any]]]:
    temporal = source_version.get("source_time_metadata")
    if isinstance(temporal, Mapping):
        yield "source_time_metadata", temporal
    content = source_version.get("content")
    if not isinstance(content, Mapping):
        return
    yield "content", content
    metadata = content.get("metadata")
    if isinstance(metadata, Mapping):
        yield "content_metadata", metadata
    headers = content.get("headers")
    if isinstance(headers, Mapping):
        yield "headers", headers


def _source_basis(provider: str, field: str) -> str:
    normalized = field.casefold().replace("-", "_")
    if normalized.endswith("first_recorded_at"):
        return "codex_first_recorded_time"
    if normalized.endswith(("sent_at", "message_date")):
        return "message_sent_time"
    if normalized.endswith(("received_at", "internal_date")):
        return "message_received_time"
    if normalized.endswith(("modified_at", "modified_ns", "mtime")):
        return "source_modified_time"
    if normalized.endswith(("created_at", "ctime", "source_created_at")):
        return "source_created_time"
    if normalized.endswith(("authored_at", "date")):
        return "source_authored_time"
    if normalized.endswith(("observed_at", "source_observed_at")):
        return "provider_observed_time"
    return f"{provider or 'source'}_record_time"


def _source_candidates(
    source_versions: Sequence[Mapping[str, Any]],
) -> Iterable[StartBoundary]:
    for source in source_versions:
        provider = str(source.get("provider", "")).strip()
        seen: set[tuple[str, str]] = set()
        for layer, values in _source_layers(source):
            for raw_key, raw_value in values.items():
                key = str(raw_key).strip()
                leaf = key.rsplit(".", 1)[-1].casefold().replace("-", "_")
                if layer == "headers" and leaf == "date":
                    leaf = "message_date"
                if leaf not in _SOURCE_TIME_FIELDS:
                    continue
                parsed = parse_user_world_time(raw_value, field=leaf)
                if parsed is None:
                    continue
                identity = (leaf, parsed.isoformat())
                if identity in seen:
                    continue
                seen.add(identity)
                yield StartBoundary(
                    value=parsed.isoformat(),
                    at=parsed,
                    basis=_source_basis(provider, leaf),
                    provider=provider,
                    field=leaf,
                )


def earliest_start_boundary(
    events: Sequence[Mapping[str, Any]],
    source_versions: Sequence[Mapping[str, Any]] = (),
) -> StartBoundary | None:
    """Compare all Event and exact SourceVersion candidates, then choose earliest."""

    candidates: list[StartBoundary] = []
    for event in events:
        for field, basis in (
            ("claimed_time", "event_claimed_time"),
            ("record_time", "event_record_time"),
        ):
            raw = event.get(field)
            parsed = parse_user_world_time(raw, field=field)
            if parsed is None:
                continue
            candidates.append(
                StartBoundary(
                    value=str(raw).strip() or parsed.isoformat(),
                    at=parsed,
                    basis=basis,
                    field=field,
                )
            )
    candidates.extend(_source_candidates(source_versions))
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda candidate: (
            candidate.at,
            candidate.basis,
            candidate.provider,
            candidate.field,
            candidate.value,
        ),
    )


__all__ = [
    "StartBoundary",
    "earliest_start_boundary",
    "parse_user_world_time",
]
