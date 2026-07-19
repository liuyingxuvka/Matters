"""Read-only C12 object-browser projection over current owner records."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, Sequence

from matters.infrastructure.sqlite.store import SQLiteStore
from matters.presentation.localization import (
    DEFAULT_LOCALE_REGISTRY,
    state_localized,
)


def _localized(en: str, zh_cn: str) -> dict[str, str]:
    return {"en": en, "zh-CN": zh_cn}


def _digest(value: Any) -> str:
    return "sha256:" + sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _text_map(payload: Mapping[str, Any], key: str) -> dict[str, str]:
    raw = payload.get(key, {})
    if not isinstance(raw, Mapping):
        return _localized("", "")
    return {
        locale: str(raw.get(locale, "")).strip()
        for locale in DEFAULT_LOCALE_REGISTRY.available_locales
    }


def _status_group(state: str) -> str:
    value = state.casefold()
    if value in {"completed", "cancelled", "abandoned", "closed"}:
        return "completed"
    if value in {
        "in_progress",
        "active",
        "waiting",
        "blocked",
        "partially_blocked",
    }:
        return "in_progress"
    return "planned"


def _iso_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.fromisoformat(value[:10])
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class ObjectBrowserProjection:
    """C12 reader. It never infers or writes canonical Matter state."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def _coverage_for_matter(self, matter_id: str) -> tuple[dict[str, Any], ...]:
        return self._coverage_by_matter((matter_id,)).get(matter_id, ())

    def _coverage_by_matter(
        self,
        matter_ids: Iterable[str],
    ) -> dict[str, tuple[dict[str, Any], ...]]:
        return self.store.current_by_json_array_members(
            "object_coverage",
            json_field="matter_ids",
            values=matter_ids,
        )

    def _events_for_matter(
        self,
        matter_id: str,
        evidence_ids: Sequence[str],
    ) -> tuple[dict[str, Any], ...]:
        evidence = set(evidence_ids)
        rows = []
        for row in self.store.iter_current("temporal_event"):
            if str(row.get("object_ref", "")) == matter_id or evidence.intersection(
                row.get("evidence_ids", ())
            ):
                rows.append(row)
        rows.sort(
            key=lambda item: (
                str(item.get("claimed_time", "")),
                str(item.get("record_time", "")),
                str(item.get("event_id", "")),
            ),
            reverse=True,
        )
        return tuple(rows)

    def _people_for_matter(
        self,
        evidence_ids: Sequence[str],
    ) -> tuple[dict[str, Any], ...]:
        evidence = set(evidence_ids)
        rows = []
        for row in self.store.iter_current("person_candidate"):
            refs = {
                str(row.get("evidence_ref", "")),
                *tuple(str(item) for item in row.get("evidence_ids", ())),
            }
            if evidence.intersection(refs):
                rows.append(row)
        return tuple(
            sorted(rows, key=lambda item: str(item.get("display_name", "")))
        )

    def _open_loops(self, matter_id: str) -> tuple[dict[str, Any], ...]:
        return tuple(
            row
            for row in self.store.iter_current("open_loop")
            if str(row.get("matter_id", "")) == matter_id
        )

    def _card(
        self,
        projection: Mapping[str, Any],
        *,
        coverage: tuple[dict[str, Any], ...] | None = None,
    ) -> dict[str, Any]:
        matter_id = str(projection["matter_id"])
        evidence_ids = tuple(str(item) for item in projection.get("evidence_ids", ()))
        values = _text_map(projection, "localized_values")
        rationale = _text_map(projection, "localized_rationale")
        state = str(projection.get("state", "uncertain"))
        events = self._events_for_matter(matter_id, evidence_ids)
        people = self._people_for_matter(evidence_ids)
        loops = self._open_loops(matter_id)
        if coverage is None:
            coverage = self._coverage_for_matter(matter_id)
        visual = self.store.current("card_visual_decision", matter_id) or {}
        key_time = ""
        if events:
            key_time = str(
                events[0].get("claimed_time")
                or events[0].get("record_time")
                or ""
            )
        title = {
            locale: (
                text.splitlines()[0][:96]
                if text
                else (
                    "Untitled matter"
                    if locale == "en"
                    else "未命名事项"
                )
            )
            for locale, text in values.items()
        }
        summary = {
            locale: (rationale.get(locale) or values.get(locale, ""))[:360]
            for locale in DEFAULT_LOCALE_REGISTRY.available_locales
        }
        return {
            "matter_id": matter_id,
            "semantic_revision": str(projection.get("semantic_revision", "")),
            "state": state,
            "status_group": _status_group(state),
            "title": title,
            "summary": summary,
            "key_time": key_time,
            "people": tuple(
                {
                    "name": str(item.get("display_name", "")).strip(),
                    "resolved": bool(item.get("resolved", False)),
                }
                for item in people[:4]
                if str(item.get("display_name", "")).strip()
            ),
            "event_count": len(events),
            "people_count": len(people),
            "source_count": len(coverage),
            "open_loop_count": len(loops),
            "evidence_count": len(evidence_ids),
            "uncertainty": state in {"uncertain", "completion_unproven"},
            "visual": {
                "status": str(visual.get("status", "missing")),
                "asset_id": str(visual.get("asset_id", "")),
                "preview_token": str(visual.get("preview_token", "")),
                "selection_mode": str(visual.get("selection_mode", "placeholder")),
                "alt": _text_map(visual, "localized_alt"),
                "reason": _text_map(visual, "localized_reason"),
            },
        }

    def _visible_projection(self, projection: Mapping[str, Any]) -> bool:
        matter_id = str(projection.get("matter_id", ""))
        admission = self.store.current("admission_decision", matter_id)
        if admission is None:
            return True
        return str(admission.get("status", "")) in {"admitted", "uncertain"}

    def _catalog_revision(self, cards: Iterable[Mapping[str, Any]]) -> str:
        return _digest(
            {
                "cards": tuple(
                    (
                        item["matter_id"],
                        item["semantic_revision"],
                        item["state"],
                        item["visual"]["asset_id"],
                        item["visual"]["status"],
                    )
                    for item in cards
                ),
            }
        )

    def catalog(
        self,
        *,
        locale: str = "en",
        query: str = "",
        status: str = "all",
        time_filter: str = "all",
        sort: str = "recent",
        offset: int = 0,
        limit: int = 60,
    ) -> dict[str, Any]:
        DEFAULT_LOCALE_REGISTRY.require(locale)
        if offset < 0 or limit < 1 or limit > 200:
            raise ValueError("object catalog page bounds are invalid")
        if status not in {"all", "planned", "in_progress", "completed"}:
            raise ValueError("unsupported status filter")
        if time_filter not in {"all", "recent", "upcoming", "undated"}:
            raise ValueError("unsupported time filter")
        if sort not in {"recent", "title", "state"}:
            raise ValueError("unsupported catalog sort")
        projections = tuple(
            payload
            for payload in self.store.iter_current("projection")
            if str(payload.get("equivalence_status", "")) == "equivalent"
            and self._visible_projection(payload)
        )
        coverage_by_matter = self._coverage_by_matter(
            str(payload["matter_id"]) for payload in projections
        )
        all_cards = tuple(
            self._card(
                payload,
                coverage=coverage_by_matter.get(
                    str(payload["matter_id"]),
                    (),
                ),
            )
            for payload in projections
        )
        revision = self._catalog_revision(all_cards)
        needle = query.casefold().strip()
        now = datetime.now(timezone.utc)
        visible = []
        for card in all_cards:
            if status != "all" and card["status_group"] != status:
                continue
            when = _iso_datetime(str(card["key_time"]))
            if time_filter == "recent" and (
                when is None or abs((now - when).days) > 90
            ):
                continue
            if time_filter == "upcoming" and (when is None or when < now):
                continue
            if time_filter == "undated" and when is not None:
                continue
            if needle:
                haystack = "\n".join(
                    (
                        str(card["title"].get(locale, "")),
                        str(card["summary"].get(locale, "")),
                        " ".join(str(item["name"]) for item in card["people"]),
                    )
                ).casefold()
                if needle not in haystack:
                    continue
            visible.append(card)
        if sort == "title":
            visible.sort(
                key=lambda item: str(item["title"].get(locale, "")).casefold()
            )
        elif sort == "state":
            visible.sort(
                key=lambda item: (
                    str(item["status_group"]),
                    str(item["title"].get(locale, "")).casefold(),
                )
            )
        else:
            visible.sort(
                key=lambda item: (
                    _iso_datetime(str(item["key_time"]))
                    or datetime.min.replace(tzinfo=timezone.utc),
                    str(item["matter_id"]),
                ),
                reverse=True,
            )
        counts = {
            group: sum(card["status_group"] == group for card in all_cards)
            for group in ("planned", "in_progress", "completed")
        }
        page = tuple(visible[offset : offset + limit])
        next_offset = offset + len(page)
        return {
            "items": page,
            "offset": offset,
            "limit": limit,
            "total_count": len(visible),
            "next_offset": next_offset if next_offset < len(visible) else None,
            "has_more": next_offset < len(visible),
            "catalog_revision": revision,
            "selected_locale": locale,
            "query": query,
            "filters": {
                "status": status,
                "time": time_filter,
                "sort": sort,
            },
            "facets": {
                "status": {
                    "all": len(all_cards),
                    **counts,
                }
            },
        }

    @staticmethod
    def _timeline_sentence(event: Mapping[str, Any]) -> dict[str, str]:
        provided = _text_map(event, "localized_sentence")
        if all(provided.values()):
            return provided
        kind = str(event.get("kind", "event")).replace("_", " ")
        actor = str(event.get("actor", "")).strip()
        object_ref = str(event.get("object_ref", "")).strip()
        time = str(event.get("claimed_time") or event.get("record_time") or "").strip()
        en_parts = [part for part in (actor, kind, object_ref) if part]
        zh_kind = {
            "actual start reported": "已报告实际开始",
            "blocked reported": "已报告受阻",
            "deadline": "截止时间",
            "milestone": "里程碑",
            "planned event": "计划事件",
            "semantic event": "语义事件",
            "work recorded": "已记录工作",
        }.get(kind, kind)
        zh_parts = [part for part in (actor, zh_kind, object_ref) if part]
        en = " · ".join(en_parts) or "An event was recorded"
        zh_cn = " · ".join(zh_parts) or "记录了一项事件"
        if time:
            en = f"{en} — {time}"
            zh_cn = f"{zh_cn} — {time}"
        return _localized(en, zh_cn)

    def detail(self, matter_id: str, *, locale: str = "en") -> dict[str, Any]:
        DEFAULT_LOCALE_REGISTRY.require(locale)
        projection = self.store.current("projection", matter_id)
        if projection is None:
            raise KeyError("matter is unavailable")
        related_projections = tuple(
            candidate
            for candidate in self.store.iter_current("projection")
            if str(candidate.get("matter_id", "")) != matter_id
            and str(candidate.get("equivalence_status", "")) == "equivalent"
            and self._visible_projection(candidate)
        )
        coverage_by_matter = self._coverage_by_matter(
            (
                matter_id,
                *(
                    str(candidate.get("matter_id", ""))
                    for candidate in related_projections
                ),
            )
        )
        coverage = coverage_by_matter.get(matter_id, ())
        card = self._card(projection, coverage=coverage)
        evidence_ids = tuple(str(item) for item in projection.get("evidence_ids", ()))
        events = self._events_for_matter(matter_id, evidence_ids)
        loops = self._open_loops(matter_id)
        outcome = self.store.current("outcome_decision", f"{matter_id}:outcome")
        lifecycle = self.store.current(
            "lifecycle_decision",
            f"{matter_id}:lifecycle",
        )
        corrections = tuple(
            row
            for row in self.store.iter_current("revision")
            if str(row.get("target_id", "")) == matter_id
        )
        occurrence_ids = {
            str(item["object_id"]) for item in coverage
        }
        visual_candidates = tuple(
            {
                "asset_id": str(item.get("asset_id", "")),
                "kind": str(item.get("kind", "")),
                "preview_token": str(item.get("preview_token", "")),
                "alt": _text_map(item, "localized_alt"),
                "reason": _text_map(item, "localized_reason"),
            }
            for item in self.store.iter_current("visual_asset")
            if str(item.get("occurrence_id", "")) in occurrence_ids
            and bool(item.get("current", False))
            and bool(item.get("display_allowed", False))
        )
        current_source_ids = {
            str(item.get("object_id", ""))
            for item in coverage
            if str(item.get("object_id", ""))
        }
        current_people = {
            str(item.get("name", "")).casefold()
            for item in card["people"]
            if str(item.get("name", ""))
        }
        current_evidence_ids = {
            str(item)
            for item in projection.get("evidence_ids", ())
            if str(item)
        }
        related = []
        for candidate in related_projections:
            candidate_id = str(candidate.get("matter_id", ""))
            if not candidate_id:
                continue
            candidate_coverage = coverage_by_matter.get(candidate_id, ())
            candidate_card = self._card(
                candidate,
                coverage=candidate_coverage,
            )
            candidate_sources = {
                str(item.get("object_id", ""))
                for item in candidate_coverage
                if str(item.get("object_id", ""))
            }
            candidate_people = {
                str(item.get("name", "")).casefold()
                for item in candidate_card["people"]
                if str(item.get("name", ""))
            }
            candidate_evidence_ids = {
                str(item)
                for item in candidate.get("evidence_ids", ())
                if str(item)
            }
            shared_sources = current_source_ids.intersection(candidate_sources)
            shared_people = current_people.intersection(candidate_people)
            shared_evidence = current_evidence_ids.intersection(
                candidate_evidence_ids
            )
            if not shared_sources and not shared_people and not shared_evidence:
                continue
            related.append(
                {
                    "matter_id": candidate_id,
                    "title": candidate_card["title"],
                    "summary": candidate_card["summary"],
                    "state": candidate_card["state"],
                    "status_group": candidate_card["status_group"],
                    "shared_source_count": len(shared_sources),
                    "shared_people_count": len(shared_people),
                    "shared_evidence_count": len(shared_evidence),
                }
            )
        related.sort(
            key=lambda item: (
                -(
                    int(item["shared_source_count"])
                    + int(item["shared_people_count"])
                    + int(item["shared_evidence_count"])
                ),
                str(item["matter_id"]),
            )
        )
        timeline = tuple(
            {
                "event_id": str(item.get("event_id", "")),
                "sentence": self._timeline_sentence(item),
                "claimed_time": str(item.get("claimed_time", "")),
                "record_time": str(item.get("record_time", "")),
                "modality": str(item.get("modality", "inferred")),
                "confidence": float(item.get("confidence", 0.0) or 0.0),
                "conflict": bool(item.get("conflict", False)),
                "evidence_ids": tuple(item.get("evidence_ids", ())),
            }
            for item in events
        )
        return {
            "matter": card,
            "timeline": timeline,
            "people": card["people"],
            "open_loops": loops,
            "related_matters": tuple(related[:20]),
            "lifecycle": lifecycle or {},
            "outcome": outcome or {},
            "sources": tuple(
                {
                    "object_id": str(item["object_id"]),
                    "provider": str(item.get("provider", "")),
                    "object_type": str(item.get("object_type", "")),
                    "disposition": str(item.get("disposition", "")),
                    "disposition_label": state_localized(
                        str(item.get("disposition", "unknown"))
                    ),
                    "next_stage": next(
                        (
                            stage_id
                            for stage_id in item.get("required_stages", ())
                            if str(
                                item.get("stages", {})
                                .get(stage_id, {})
                                .get("status", "pending")
                            )
                            in {"pending", "stale"}
                        ),
                        "",
                    ),
                }
                for item in coverage
            ),
            "corrections": corrections,
            "visual_candidates": visual_candidates,
            "selected_locale": locale,
        }

    def evidence(
        self,
        matter_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        if offset < 0 or limit < 1 or limit > 200:
            raise ValueError("evidence page bounds are invalid")
        projection = self.store.current("projection", matter_id)
        if projection is None:
            raise KeyError("matter is unavailable")
        evidence_ids = tuple(str(item) for item in projection.get("evidence_ids", ()))
        rows = self.store.current_many("evidence_anchor", evidence_ids)
        items = tuple(
            {
                "evidence_ref": _digest(evidence_id)[:31],
                "excerpt": str(payload.get("text", ""))[:1200],
                "modality": str(payload.get("modality", "")),
                "location": {
                    key: value
                    for key, value in dict(payload.get("location", {})).items()
                    if key
                    in {
                        "field",
                        "page",
                        "line",
                        "line_start",
                        "line_end",
                        "slide",
                        "shape",
                        "sheet",
                        "cell",
                        "region",
                    }
                },
            }
            for evidence_id in evidence_ids
            if (payload := rows.get(evidence_id)) is not None
        )
        page = items[offset : offset + limit]
        next_offset = offset + len(page)
        return {
            "items": page,
            "offset": offset,
            "limit": limit,
            "total_count": len(items),
            "next_offset": next_offset if next_offset < len(items) else None,
            "has_more": next_offset < len(items),
        }


__all__ = ["ObjectBrowserProjection"]
