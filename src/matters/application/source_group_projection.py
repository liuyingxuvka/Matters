"""Path-free SourceGroup projections from registered inventory occurrences."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Mapping

from matters.inventory.owners import InventoryOccurrence
from matters.provenance.storage_policy import SourceAvailability


_SOURCE_GROUP_CHAIN = "source_group_chain"
_SOURCE_GROUP_LABELS = "source_group_labels"
_SOURCE_NEIGHBORHOOD_ID = "source_neighborhood_id"


def _required_text(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _looks_like_absolute_path(value: str) -> bool:
    return (
        PureWindowsPath(value).is_absolute()
        or PurePosixPath(value).is_absolute()
        or value.startswith(("\\\\", "//"))
    )


def _opaque_id(prefix: str, *parts: str) -> str:
    payload = "\0".join(parts).encode("utf-8")
    return f"{prefix}:{sha256(payload).hexdigest()[:32]}"


def _safe_identifier(value: str, *, fallback: str) -> str:
    candidate = str(value).strip()
    if (
        not candidate
        or _looks_like_absolute_path(candidate)
        or "/" in candidate
        or "\\" in candidate
    ):
        return fallback
    return candidate


def _public_occurrence_id(provider: str, private_occurrence_id: str) -> str:
    candidate = _safe_identifier(private_occurrence_id, fallback="")
    if candidate:
        return candidate
    return _opaque_id("source-occurrence", provider, private_occurrence_id)


def _public_group_id(provider: str, private_group_id: str) -> str:
    private_value = str(private_group_id).strip()
    candidate = _safe_identifier(private_value, fallback="")
    if candidate:
        return candidate
    return _opaque_id("source-group", provider, private_value)


def _safe_label(value: Any, *, fallback: str) -> str:
    candidate = str(value or "").strip()
    if (
        not candidate
        or _looks_like_absolute_path(candidate)
        or "/" in candidate
        or "\\" in candidate
    ):
        return fallback
    return candidate[:160]


def _availability(
    occurrence: InventoryOccurrence,
    availability_by_occurrence: Mapping[str, SourceAvailability | str],
) -> SourceAvailability:
    raw = availability_by_occurrence.get(
        occurrence.occurrence_id,
        occurrence.metadata.get(
            "source_availability",
            SourceAvailability.AVAILABLE,
        ),
    )
    return SourceAvailability(raw)


@dataclass(frozen=True)
class SourceGroupMember:
    """One path-free member row in a SourceGroup detail projection."""

    occurrence_id: str
    provider: str
    object_type: str
    title: str
    availability: str


@dataclass(frozen=True)
class SourceGroupSummary:
    """Stable list projection for one source group."""

    group_id: str
    parent_group_id: str
    title: str
    depth: int
    direct_member_count: int
    total_member_count: int
    child_group_count: int
    source_types: tuple[str, ...]
    availability: str


@dataclass(frozen=True)
class SourceGroupPage:
    """Deterministic page of SourceGroup summaries."""

    items: tuple[SourceGroupSummary, ...]
    total_count: int
    offset: int
    limit: int
    next_offset: int | None


@dataclass(frozen=True)
class SourceGroupDetail:
    """Stable group identity plus its paginated path-free members."""

    summary: SourceGroupSummary
    child_group_ids: tuple[str, ...]
    members: tuple[SourceGroupMember, ...]
    member_total_count: int
    member_offset: int
    member_limit: int
    next_member_offset: int | None


@dataclass(frozen=True)
class SourceGroupIndexRow:
    """One rebuildable row joining an occurrence to one ancestor group."""

    group_id: str
    parent_group_id: str
    child_group_id: str
    title: str
    depth: int
    inventory_occurrence_id: str
    occurrence_id: str
    provider: str
    object_type: str
    member_title: str
    availability: str
    direct_member: bool


@dataclass
class _GroupAccumulator:
    group_id: str
    parent_group_id: str
    title: str
    depth: int
    member_ids: set[str] = field(default_factory=set)
    direct_member_ids: set[str] = field(default_factory=set)
    child_group_ids: set[str] = field(default_factory=set)
    source_types: set[str] = field(default_factory=set)


class SourceGroupProjection:
    """Read model built from existing neighborhood and group-chain metadata."""

    def __init__(
        self,
        *,
        groups: Mapping[str, _GroupAccumulator],
        members: Mapping[str, SourceGroupMember],
        occurrence_group_ids: Mapping[tuple[str, str], tuple[str, ...]],
    ) -> None:
        self._groups = dict(groups)
        self._members = dict(members)
        self._occurrence_group_ids = dict(occurrence_group_ids)

    @classmethod
    def from_occurrences(
        cls,
        occurrences: Iterable[InventoryOccurrence],
        *,
        availability_by_occurrence: (
            Mapping[str, SourceAvailability | str] | None
        ) = None,
    ) -> SourceGroupProjection:
        availability_map = dict(availability_by_occurrence or {})
        occurrence_list = tuple(occurrences)
        occurrence_by_id = {
            item.occurrence_id: item for item in occurrence_list
        }
        groups: dict[str, _GroupAccumulator] = {}
        members: dict[str, SourceGroupMember] = {}
        occurrence_group_ids: dict[tuple[str, str], tuple[str, ...]] = {}

        for occurrence in occurrence_list:
            status = _availability(occurrence, availability_map)
            public_provider = _safe_identifier(
                occurrence.provider,
                fallback="source",
            )
            public_object_type = _safe_identifier(
                occurrence.object_type,
                fallback="object",
            )
            member = SourceGroupMember(
                occurrence_id=_public_occurrence_id(
                    occurrence.provider,
                    occurrence.occurrence_id,
                ),
                provider=public_provider,
                object_type=public_object_type,
                title=_member_title(occurrence),
                availability=status.value,
            )
            members[member.occurrence_id] = member

            private_chain = _metadata_sequence(
                occurrence.metadata.get(_SOURCE_GROUP_CHAIN)
            )
            labels = _metadata_sequence(
                occurrence.metadata.get(_SOURCE_GROUP_LABELS)
            )
            if private_chain:
                public_chain = tuple(
                    _public_group_id(occurrence.provider, private_group_id)
                    for private_group_id in private_chain
                )
            else:
                private_chain, labels = _fallback_group_chain(
                    occurrence,
                    occurrence_by_id=occurrence_by_id,
                )
                public_chain = tuple(
                    _public_group_id(occurrence.provider, private_group_id)
                    for private_group_id in private_chain
                )
            if not public_chain:
                continue
            occurrence_group_ids[
                (occurrence.provider, occurrence.occurrence_id)
            ] = public_chain

            for index, group_id in enumerate(public_chain):
                parent_group_id = public_chain[index - 1] if index else ""
                fallback = f"Source group {index + 1}"
                title = _safe_label(
                    labels[index] if index < len(labels) else "",
                    fallback=fallback,
                )
                group = groups.get(group_id)
                if group is None:
                    group = _GroupAccumulator(
                        group_id=group_id,
                        parent_group_id=parent_group_id,
                        title=title,
                        depth=index,
                    )
                    groups[group_id] = group
                elif (
                    group.parent_group_id != parent_group_id
                    or group.depth != index
                ):
                    raise ValueError(
                        f"inconsistent SourceGroup hierarchy for {group_id}"
                    )
                group.member_ids.add(member.occurrence_id)
                group.source_types.add(member.object_type)
                if index == len(public_chain) - 1:
                    group.direct_member_ids.add(member.occurrence_id)
                if index + 1 < len(public_chain):
                    group.child_group_ids.add(public_chain[index + 1])

        return cls(
            groups=groups,
            members=members,
            occurrence_group_ids=occurrence_group_ids,
        )

    def page(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        query: str = "",
    ) -> SourceGroupPage:
        _validate_page(offset=offset, limit=limit)
        normalized_query = str(query).strip().casefold()
        summaries = [
            self._summary(group)
            for group in self._groups.values()
            if not normalized_query
            or normalized_query in group.title.casefold()
            or any(
                normalized_query in source_type.casefold()
                for source_type in group.source_types
            )
        ]
        summaries.sort(key=lambda item: (item.title.casefold(), item.group_id))
        page_items = tuple(summaries[offset : offset + limit])
        next_offset = (
            offset + len(page_items)
            if offset + len(page_items) < len(summaries)
            else None
        )
        return SourceGroupPage(
            items=page_items,
            total_count=len(summaries),
            offset=offset,
            limit=limit,
            next_offset=next_offset,
        )

    def detail(
        self,
        group_id: str,
        *,
        member_offset: int = 0,
        member_limit: int = 100,
    ) -> SourceGroupDetail:
        _validate_page(offset=member_offset, limit=member_limit)
        normalized_group_id = _required_text(group_id, "group_id")
        try:
            group = self._groups[normalized_group_id]
        except KeyError as exc:
            raise KeyError(f"unknown SourceGroup: {normalized_group_id}") from exc
        member_ids = sorted(group.member_ids)
        selected_ids = member_ids[
            member_offset : member_offset + member_limit
        ]
        selected_members = tuple(self._members[item] for item in selected_ids)
        next_offset = (
            member_offset + len(selected_members)
            if member_offset + len(selected_members) < len(member_ids)
            else None
        )
        return SourceGroupDetail(
            summary=self._summary(group),
            child_group_ids=tuple(sorted(group.child_group_ids)),
            members=selected_members,
            member_total_count=len(member_ids),
            member_offset=member_offset,
            member_limit=member_limit,
            next_member_offset=next_offset,
        )

    def group_chain(
        self,
        *,
        provider: str,
        occurrence_id: str,
    ) -> tuple[SourceGroupSummary, ...]:
        """Return the stable root-to-leaf SourceGroup chain for one occurrence."""

        key = (
            _required_text(provider, "provider"),
            _required_text(occurrence_id, "occurrence_id"),
        )
        return tuple(
            self._summary(self._groups[group_id])
            for group_id in self._occurrence_group_ids.get(key, ())
        )

    def index_rows(self) -> tuple[SourceGroupIndexRow, ...]:
        """Project exact, path-free rows for the rebuildable SQLite index."""

        rows: list[SourceGroupIndexRow] = []
        for (provider, private_occurrence_id), group_ids in sorted(
            self._occurrence_group_ids.items()
        ):
            public_occurrence_id = _public_occurrence_id(
                provider,
                private_occurrence_id,
            )
            member = self._members[public_occurrence_id]
            for index, group_id in enumerate(group_ids):
                group = self._groups[group_id]
                rows.append(
                    SourceGroupIndexRow(
                        group_id=group_id,
                        parent_group_id=group.parent_group_id,
                        child_group_id=(
                            group_ids[index + 1]
                            if index + 1 < len(group_ids)
                            else ""
                        ),
                        title=group.title,
                        depth=group.depth,
                        inventory_occurrence_id=private_occurrence_id,
                        occurrence_id=member.occurrence_id,
                        provider=member.provider,
                        object_type=member.object_type,
                        member_title=member.title,
                        availability=member.availability,
                        direct_member=index == len(group_ids) - 1,
                    )
                )
        return tuple(rows)

    def _summary(self, group: _GroupAccumulator) -> SourceGroupSummary:
        availability = _group_availability(
            self._members[member_id].availability
            for member_id in group.member_ids
        )
        return SourceGroupSummary(
            group_id=group.group_id,
            parent_group_id=group.parent_group_id,
            title=group.title,
            depth=group.depth,
            direct_member_count=len(group.direct_member_ids),
            total_member_count=len(group.member_ids),
            child_group_count=len(group.child_group_ids),
            source_types=tuple(sorted(group.source_types)),
            availability=availability,
        )


def _metadata_sequence(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value.strip() else ()
    try:
        return tuple(str(item) for item in value if str(item).strip())
    except TypeError as exc:
        raise ValueError("SourceGroup metadata must be a sequence") from exc


def _fallback_group_chain(
    occurrence: InventoryOccurrence,
    *,
    occurrence_by_id: Mapping[str, InventoryOccurrence],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    provider = occurrence.provider.strip().casefold()
    metadata = occurrence.metadata
    if provider == "gmail":
        thread_id = _gmail_thread_occurrence_id(
            occurrence,
            occurrence_by_id=occurrence_by_id,
        )
        private_group_id = thread_id or occurrence.occurrence_id
        label = _safe_label(
            metadata.get("source_group_label"),
            fallback="Gmail conversation",
        )
        return (private_group_id,), (label,)
    if provider in {"codex", "codex_project", "codex-workspace"}:
        private_group_id = next(
            (
                str(metadata.get(key, "")).strip()
                for key in (
                    "project_id",
                    "workspace_id",
                    _SOURCE_NEIGHBORHOOD_ID,
                )
                if str(metadata.get(key, "")).strip()
            ),
            occurrence.parent_occurrence_id or provider,
        )
        label = next(
            (
                _safe_label(metadata.get(key), fallback="")
                for key in (
                    "project_name",
                    "workspace_name",
                    "source_group_label",
                )
                if _safe_label(metadata.get(key), fallback="")
            ),
            "Codex project",
        )
        return (private_group_id,), (label,)
    neighborhood = str(metadata.get(_SOURCE_NEIGHBORHOOD_ID, "")).strip()
    if neighborhood:
        return (neighborhood,), (
            _safe_label(
                metadata.get("source_group_label"),
                fallback="Source group",
            ),
        )
    label = _safe_label(
        metadata.get("source_group_label"),
        fallback=provider.replace("_", " ").title() or "Source",
    )
    return (f"provider:{provider or 'source'}",), (label,)


def _gmail_thread_occurrence_id(
    occurrence: InventoryOccurrence,
    *,
    occurrence_by_id: Mapping[str, InventoryOccurrence],
) -> str:
    current = occurrence
    seen: set[str] = set()
    for _ in range(4):
        if current.occurrence_id in seen:
            break
        seen.add(current.occurrence_id)
        if current.object_type.strip().casefold() == "thread":
            return current.occurrence_id
        parent_id = current.parent_occurrence_id.strip()
        if not parent_id:
            break
        parent = occurrence_by_id.get(parent_id)
        if parent is None:
            return parent_id
        current = parent
    return occurrence.parent_occurrence_id.strip()


def _member_title(occurrence: InventoryOccurrence) -> str:
    for key in ("display_name", "name", "subject", "file_name"):
        candidate = occurrence.metadata.get(key)
        if candidate:
            return _safe_label(candidate, fallback=occurrence.object_type)
    return occurrence.object_type


def _group_availability(values: Iterable[str]) -> str:
    statuses = tuple(values)
    if statuses and all(
        status == SourceAvailability.AVAILABLE.value for status in statuses
    ):
        return SourceAvailability.AVAILABLE.value
    if statuses and any(
        status == SourceAvailability.AVAILABLE.value for status in statuses
    ):
        return "partial"
    return SourceAvailability.SOURCE_UNAVAILABLE.value


def _validate_page(*, offset: int, limit: int) -> None:
    if offset < 0:
        raise ValueError("offset cannot be negative")
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
