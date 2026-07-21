"""Read-only C12 object-browser projection over current owner records."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, Sequence

from matters.application.source_group_projection import SourceGroupProjection
from matters.infrastructure.sqlite.store import SQLiteStore
from matters.inventory.owners import InventoryOccurrence
from matters.presentation.heroes import (
    GeneratedHeroProjectionOwner,
    GeneratedHeroRecord,
)
from matters.presentation.localization import (
    DEFAULT_LOCALE_REGISTRY,
)
from matters.timeline.start_boundary import earliest_start_boundary

PRIMARY_DETAIL_SECTIONS = (
    "overview",
    "sub_matters",
    "timeline",
    "people",
    "related_matters",
    "files_and_information",
    "images",
    "ai_supplemental_information",
)
FILES_INFORMATION_LIMIT = 50
RELATED_CANDIDATE_LIMIT = 200


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


def _activity_projection_is_current(
    activity: Mapping[str, Any],
    *,
    expected_matter_id: str,
) -> bool:
    """Validate the atomic C12 activity binding without comparing Matter revisions.

    An ancestor activity projection intentionally keeps the semantic revision of
    the descendant clue that caused the bubble.  Comparing that revision with
    the ancestor Matter projection would reject every legitimate child update.
    """

    binding_revisions = tuple(
        str(activity.get(field, "")).strip()
        for field in (
            "material_clue_revision",
            "summary_revision",
            "activity_order_revision",
        )
    )
    localized_summary = _text_map(activity, "localized_summary")
    try:
        persistence_revision = int(activity.get("persistence_revision", 0))
    except (TypeError, ValueError):
        return False
    return (
        bool(activity)
        and str(activity.get("matter_id", "")).strip() == expected_matter_id
        and bool(str(activity.get("source_matter_id", "")).strip())
        and bool(str(activity.get("material_clue_id", "")).strip())
        and _iso_datetime(
            str(activity.get("latest_meaningful_clue_at", ""))
        )
        is not None
        and persistence_revision >= 1
        and bool(binding_revisions[0])
        and len(set(binding_revisions)) == 1
        and all(localized_summary.values())
    )


def _title_and_summary(
    projection: Mapping[str, Any],
) -> tuple[dict[str, str], dict[str, str]]:
    title = _text_map(projection, "localized_values")
    internal_terms = {
        "en": (
            "the evidence shows",
            "semantic revision",
            "included in understanding",
            "coverage stage",
            "model confidence",
            "execution profile",
            "routing status",
            "provider receipt",
        ),
        "zh-CN": (
            "证据显示",
            "证据证明",
            "语义修订",
            "纳入事项理解",
            "覆盖阶段",
            "模型置信度",
            "执行配置",
            "路由状态",
            "提供方收据",
        ),
    }
    for key in (
        "localized_human_summary",
        "localized_summary",
        "localized_rationale",
    ):
        summary = _text_map(projection, key)
        if not all(summary.values()):
            continue
        if any(
            term in summary[locale].casefold()
            for locale, terms in internal_terms.items()
            for term in terms
        ):
            continue
        return title, summary
    return title, _localized("", "")


def _kind_label(kind: str) -> dict[str, str]:
    normalized = kind.casefold().strip()
    return _localized(
        {
            "file": "File",
            "document": "Document",
            "image": "Image",
            "message": "Email",
            "thread": "Email conversation",
            "attachment": "Attachment",
            "cloud_placeholder": "Cloud item",
        }.get(normalized, "Information"),
        {
            "file": "文件",
            "document": "文档",
            "image": "图片",
            "message": "邮件",
            "thread": "邮件会话",
            "attachment": "附件",
            "cloud_placeholder": "云端资料",
        }.get(normalized, "资料"),
    )


def _availability(
    coverage: Mapping[str, Any],
) -> tuple[str, dict[str, str]]:
    stages = coverage.get("stages", {})
    stage_values = (
        tuple(stages.values())
        if isinstance(stages, Mapping)
        else ()
    )
    stage_statuses = {
        str(item.get("status", ""))
        for item in stage_values
        if isinstance(item, Mapping)
    }
    disposition = str(coverage.get("disposition", "")).casefold()
    if "blocked" in stage_statuses or disposition in {"blocked", "unavailable"}:
        return "unavailable", _localized("Unavailable", "暂不可用")
    if disposition == "metadata_only":
        return "limited", _localized(
            "Limited information available",
            "仅有有限信息",
        )
    required = tuple(str(item) for item in coverage.get("required_stages", ()))
    terminal = bool(required) and all(
        str(
            (
                stages.get(stage_id, {})
                if isinstance(stages, Mapping)
                else {}
            ).get("status", "")
        )
        in {"current", "not_applicable", "no_finding", "uncertain"}
        for stage_id in required
    )
    if terminal:
        return "available", _localized("Available", "可用")
    return "processing", _localized("Being prepared", "正在整理")


def _relevant_time(coverage: Mapping[str, Any]) -> str:
    direct = str(coverage.get("updated_at", "")).strip()
    if direct:
        return direct
    stages = coverage.get("stages", {})
    if not isinstance(stages, Mapping):
        return ""
    return max(
        (
            str(item.get("updated_at", "")).strip()
            for item in stages.values()
            if isinstance(item, Mapping)
        ),
        default="",
    )


def _first_text(
    payload: Mapping[str, Any],
    keys: Sequence[str],
) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, Mapping):
            for locale in ("en", "zh-CN"):
                candidate = str(value.get(locale, "")).strip()
                if candidate:
                    return candidate
            continue
        candidate = str(value or "").strip()
        if candidate:
            return candidate
    return ""


def _source_observed_time(
    content: Mapping[str, Any],
    occurrence: Mapping[str, Any],
) -> str:
    metadata = occurrence.get("metadata", {})
    if not isinstance(metadata, Mapping):
        metadata = {}
    return _first_text(
        content,
        (
            "internal_date",
            "received_at",
            "observed_at",
            "modified_at",
            "mtime",
            "created_at",
            "date",
        ),
    ) or _first_text(
        metadata,
        (
            "internal_date",
            "received_at",
            "observed_at",
            "modified_at",
            "mtime",
            "created_at",
            "date",
        ),
    )


def _source_availability(
    source_version: Mapping[str, Any],
    occurrence_row: Mapping[str, Any],
) -> tuple[str, dict[str, str]]:
    status = str(
        source_version.get("original_availability", "")
        or occurrence_row.get("disposition", "")
        or "available"
    ).strip().casefold()
    if bool(source_version.get("tombstone", False)) or status == "deleted":
        return "deleted", _localized("Original deleted", "原件已删除")
    if status in {"revoked", "not_tracked"}:
        return "revoked", _localized("Access revoked", "访问已撤销")
    if status in {"unavailable", "blocked", "source_unavailable"}:
        return "unavailable", _localized("Unavailable", "暂不可用")
    if status == "metadata_only":
        return "limited", _localized(
            "Limited information available",
            "仅有有限信息",
        )
    return "available", _localized("Available in original location", "原位置可用")


def _safe_source_label(value: object, *, fallback: str) -> str:
    candidate = " ".join(str(value or "").strip().split())
    if (
        not candidate
        or "/" in candidate
        or "\\" in candidate
        or (len(candidate) >= 2 and candidate[1] == ":")
    ):
        return fallback
    return candidate[:160]


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


def _facet_value(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _relation_label(relation_type: str) -> dict[str, str]:
    normalized = _facet_value(relation_type)
    labels = {
        "relates": ("Related", "相关"),
        "depends_on": ("Depends on", "依赖"),
        "blocks": ("Blocks", "阻碍"),
        "supports": ("Supports", "支持"),
        "contradicts": ("Conflicts with", "存在冲突"),
        "follows": ("Follows", "后续"),
        "precedes": ("Precedes", "先于"),
        "same_context": ("Same context", "同一背景"),
        "same_project_context": ("Same project context", "同一项目背景"),
        "same_source_context": ("Same source context", "同一来源背景"),
        "shares_person": ("Shares a person", "涉及同一人物"),
        "temporal_context": ("Related in time", "时间相关"),
        "overlapping_goal": ("Overlapping goal", "目标有关联"),
    }
    en, zh_cn = labels.get(
        normalized,
        (
            normalized.replace("_", " ").strip().title() or "Related",
            normalized.replace("_", " ").strip() or "相关",
        ),
    )
    return _localized(en, zh_cn)


def _person_role_label(role: object) -> dict[str, str]:
    normalized = _facet_value(role)
    labels = {
        "customer_support_contact": ("Customer support contact", "客户支持联系人"),
        "recruiter": ("Recruiter", "招聘联系人"),
        "hiring_manager": ("Hiring manager", "招聘负责人"),
        "travel_companion": ("Travel companion", "同行人员"),
        "organizer": ("Organizer", "组织者"),
        "participant": ("Participant", "参与者"),
        "sender": ("Sender", "发件人"),
        "recipient": ("Recipient", "收件人"),
        "contact": ("Contact", "联系人"),
    }
    en, zh_cn = labels.get(
        normalized,
        (
            normalized.replace("_", " ").strip().title(),
            normalized.replace("_", " ").strip(),
        ),
    )
    return _localized(en, zh_cn)


def _normalized_filter_values(values: Sequence[str]) -> frozenset[str]:
    return frozenset(
        normalized
        for value in values
        if (normalized := _facet_value(value))
    )


def _card_facet_values(card: Mapping[str, Any], key: str) -> frozenset[str]:
    return frozenset(
        _facet_value(
            item.get("value", "")
            if isinstance(item, Mapping)
            else item
        )
        for item in card.get(key, ())
        if _facet_value(
            item.get("value", "")
            if isinstance(item, Mapping)
            else item
        )
    )


def _facet_rows(
    cards: Sequence[Mapping[str, Any]],
    key: str,
) -> tuple[dict[str, Any], ...]:
    values: dict[str, dict[str, Any]] = {}
    for card in cards:
        seen: set[str] = set()
        for raw in card.get(key, ()):
            if isinstance(raw, Mapping):
                value = _facet_value(raw.get("value", ""))
                label = _text_map(raw, "label")
            else:
                value = _facet_value(raw)
                label = _localized(str(raw), str(raw))
            if not value or value in seen:
                continue
            seen.add(value)
            current = values.setdefault(
                value,
                {
                    "value": value,
                    "label": label,
                    "count": 0,
                },
            )
            current["count"] = int(current["count"]) + 1
    return tuple(
        values[value]
        for value in sorted(
            values,
            key=lambda item: (
                str(values[item]["label"].get("en", "")).casefold(),
                item,
            ),
        )
    )


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


def _earliest_user_time(
    events: Sequence[Mapping[str, Any]],
    source_versions: Sequence[Mapping[str, Any]] = (),
) -> str:
    boundary = earliest_start_boundary(events, source_versions)
    return boundary.value if boundary is not None else ""


def _event_logical_key(event: Mapping[str, Any]) -> str:
    explicit = str(event.get("logical_event_key", "")).strip()
    if explicit:
        return explicit
    # Current rows created before logical Event identity still need an honest
    # one-row projection for an exact human occurrence.  This identity excludes
    # event/source/evidence ids, extraction revisions, and localized wording.
    return _digest(
        (
            "logical-event-projection",
            str(event.get("object_ref", "")).strip(),
            str(event.get("kind", "")).strip().casefold(),
            str(event.get("actor", "")).strip().casefold(),
            str(event.get("claimed_time", "")).strip(),
            str(event.get("record_time", "")).strip(),
        )
    )


def logical_event_key_for_payload(event: Mapping[str, Any]) -> str:
    """Return the stable logical identity shared by migration and projection."""

    return _event_logical_key(event)


def _event_revision_key(event: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(event.get("inference_as_of", "")),
        str(event.get("record_time", "")),
        str(event.get("claimed_time", "")),
        str(event.get("event_id", "")),
    )


def _event_interpretation_signature(event: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(event.get("claimed_time", "")),
        str(event.get("record_time", "")),
        str(event.get("modality", "")),
        tuple(sorted(_text_map(event, "localized_sentence").items())),
    )


def project_matter_only_graph(snapshot: object) -> dict[str, Any]:
    """Project an internal SituationGraph page to the ordinary Matter graph.

    Internal WorkItem, Event, source, person, and advisory nodes remain owned
    and queryable, but they are not second-class boxes in the user hierarchy.
    """

    if is_dataclass(snapshot):
        payload = asdict(snapshot)
    elif isinstance(snapshot, Mapping):
        payload = dict(snapshot)
    else:
        raise TypeError("Matter-only graph projection requires a graph payload")
    nodes = tuple(
        dict(node)
        for node in payload.get("nodes", ())
        if isinstance(node, Mapping)
        and str(node.get("node_type", "")) == "matter"
    )
    matter_node_ids = {
        str(node.get("node_id", ""))
        for node in nodes
        if str(node.get("node_id", ""))
    }
    edges = tuple(
        dict(edge)
        for edge in payload.get("edges", ())
        if isinstance(edge, Mapping)
        and str(edge.get("source_node_id", "")) in matter_node_ids
        and str(edge.get("target_node_id", "")) in matter_node_ids
        and (
            bool(edge.get("primary_containment", False))
            or str(edge.get("relation_type", ""))
            not in {"has_event", "has_work_item", "has_source", "has_person"}
        )
    )
    return {
        **payload,
        "nodes": nodes,
        "edges": edges,
        "visible_node_count": len(nodes),
        "visible_edge_count": len(edges),
        "projection_kind": "matter_only",
        "non_matter_details_in_quick_view": True,
        "per_node_collapse_allowed": False,
    }


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

    def _active_temporal_events(
        self,
        rows: Iterable[Mapping[str, Any]],
    ) -> tuple[dict[str, Any], ...]:
        events = tuple(dict(row) for row in rows)
        refs = tuple(
            f"temporal_event:{event_id}"
            for row in events
            if (event_id := str(row.get("event_id", "")))
        )
        invalidated = self.store.invalidated_analysis_output_refs(refs)
        valid = tuple(
            row
            for row in events
            if (
                not (event_id := str(row.get("event_id", "")))
                or f"temporal_event:{event_id}" not in invalidated
            )
        )
        superseded_ids = {
            str(row.get("supersedes_event_id", "")).strip()
            for row in valid
            if str(row.get("supersedes_event_id", "")).strip()
        }
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in valid:
            grouped.setdefault(_event_logical_key(row), []).append(row)
        current_rows: list[dict[str, Any]] = []
        for logical_event_key, revisions in grouped.items():
            candidates = tuple(
                row
                for row in revisions
                if bool(row.get("current_revision", True))
                and str(row.get("event_id", "")) not in superseded_ids
            )
            if not candidates:
                if revisions and all(
                    str(row.get("event_id", "")) in superseded_ids
                    for row in revisions
                ):
                    continue
                candidates = tuple(revisions)
            current = dict(max(candidates, key=_event_revision_key))
            alternatives = tuple(
                row
                for row in sorted(
                    revisions,
                    key=_event_revision_key,
                    reverse=True,
                )
                if row is not current
                and _event_interpretation_signature(row)
                != _event_interpretation_signature(current)
            )
            distinct_interpretations = {
                _event_interpretation_signature(row)
                for row in revisions
            }
            current["logical_event_key"] = logical_event_key
            current["current_revision"] = True
            current["revision_count"] = len(revisions)
            current["has_history"] = len(revisions) > 1
            current["conflict"] = bool(current.get("conflict", False)) or (
                len(distinct_interpretations) > 1
                and not any(
                    str(row.get("supersedes_event_id", "")).strip()
                    for row in revisions
                )
            )
            current["_alternative_events"] = alternatives
            current_rows.append(current)
        return tuple(current_rows)

    def active_temporal_events(
        self,
        rows: Iterable[Mapping[str, Any]],
    ) -> tuple[dict[str, Any], ...]:
        """Return one current row per logical event."""

        return self._active_temporal_events(rows)

    def _active_matter_output_ids(
        self,
        matter_ids: Iterable[str],
    ) -> set[str]:
        """Return Matters whose admission and projection owners are current."""

        ordered_ids = tuple(
            dict.fromkeys(str(item) for item in matter_ids if str(item))
        )
        invalidated = self.store.invalidated_analysis_output_refs(
            output_ref
            for matter_id in ordered_ids
            for output_ref in (
                f"projection:{matter_id}",
                f"admission_decision:{matter_id}",
            )
        )
        return {
            matter_id
            for matter_id in ordered_ids
            if f"projection:{matter_id}" not in invalidated
            and f"admission_decision:{matter_id}" not in invalidated
        }

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
        rows = list(self._active_temporal_events(rows))
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
        matter_id: str,
        evidence_ids: Sequence[str],
    ) -> tuple[dict[str, Any], ...]:
        evidence = set(evidence_ids)
        relevant_matter_ids = {
            matter_id,
            *self.store.hierarchy_descendant_ids(
                matter_id,
                current_only=True,
            ),
        }
        rows: dict[str, dict[str, Any]] = {}
        for row in self.store.iter_current("person_candidate"):
            refs = {
                str(row.get("evidence_ref", "")),
                *tuple(str(item) for item in row.get("evidence_ids", ())),
            }
            direct_matter_ids = {
                str(row.get("matter_id", "")),
                str(row.get("object_ref", "")),
                *tuple(str(item) for item in row.get("matter_ids", ())),
            }
            if (
                evidence.intersection(refs)
                or relevant_matter_ids.intersection(direct_matter_ids)
            ):
                person_id = str(row.get("person_id", "")) or _digest(row)
                rows[person_id] = dict(row)
        return tuple(
            sorted(
                rows.values(),
                key=lambda item: str(item.get("display_name", "")),
            )
        )

    def _open_loops(self, matter_id: str) -> tuple[dict[str, Any], ...]:
        return tuple(
            row
            for row in self.store.iter_current("open_loop")
            if str(row.get("matter_id", "")) == matter_id
        )

    def _source_versions_for_admission(
        self,
        admission: Mapping[str, Any] | None,
    ) -> tuple[dict[str, Any], ...]:
        matter = (
            admission.get("matter")
            if isinstance(admission, Mapping)
            else None
        )
        if not isinstance(matter, Mapping):
            return ()
        rows: list[dict[str, Any]] = []
        for raw_ref in matter.get("source_ids", ()):
            source_ref = str(raw_ref)
            source_id, separator, version_text = source_ref.rpartition(":v")
            if (
                not separator
                or not source_id.startswith("source:")
                or not version_text.isdigit()
            ):
                continue
            expected_version = int(version_text)
            current = self.store.current("source_version", source_id)
            payload = (
                current
                if current is not None
                and int(current.get("version", 0) or 0)
                == expected_version
                else next(
                    (
                        item
                        for item in self.store.history(
                            "source_version",
                            source_id,
                        )
                        if int(item.get("version", 0) or 0)
                        == expected_version
                    ),
                    None,
                )
            )
            if payload is not None:
                rows.append(dict(payload))
        occurrence_ids = tuple(
            dict.fromkeys(
                str(
                    dict(row.get("external_reference", {})).get(
                        "external_id",
                        "",
                    )
                ).strip()
                for row in rows
                if str(
                    dict(row.get("external_reference", {})).get(
                        "external_id",
                        "",
                    )
                ).strip()
            )
        )
        occurrences = self.store.inventory_occurrences_by_object_ids(
            occurrence_ids
        )
        for row in rows:
            if dict(row.get("source_time_metadata", {})):
                continue
            external_id = str(
                dict(row.get("external_reference", {})).get(
                    "external_id",
                    "",
                )
            ).strip()
            retained: dict[str, Any] = {}
            for occurrence_row in occurrences.get(external_id, ()):
                occurrence = dict(occurrence_row.get("occurrence", {}))
                metadata = occurrence.get("metadata")
                if not isinstance(metadata, Mapping):
                    continue
                for field in (
                    "authored_at",
                    "created_at",
                    "ctime",
                    "first_recorded_at",
                    "modified_at",
                    "modified_ns",
                    "mtime",
                    "observed_at",
                    "received_at",
                    "sent_at",
                ):
                    if field in metadata:
                        retained[f"current_inventory.{field}"] = metadata[field]
            if retained:
                row["source_time_metadata"] = retained
        return tuple(rows)

    def _files_and_information(
        self,
        *,
        source_versions: Sequence[Mapping[str, Any]],
        evidence_ids: Sequence[str],
    ) -> dict[str, Any]:
        # A SourceVersion history is one file/information object, not one UI
        # row per historical revision. Keep the newest admitted revision for
        # each logical source while preserving the original source order.
        latest_source_versions: dict[
            tuple[str, str],
            Mapping[str, Any],
        ] = {}
        for raw_source_version in source_versions:
            reference = dict(
                raw_source_version.get("external_reference", {})
            )
            provider = str(
                raw_source_version.get("provider")
                or reference.get("provider")
                or "source"
            ).strip().casefold()
            logical_id = (
                str(raw_source_version.get("source_id", "")).strip()
                or str(reference.get("external_id", "")).strip()
            )
            logical_key = (provider, logical_id)
            prior = latest_source_versions.get(logical_key)
            if (
                prior is None
                or int(raw_source_version.get("version", 0) or 0)
                > int(prior.get("version", 0) or 0)
            ):
                latest_source_versions[logical_key] = raw_source_version
        source_versions = tuple(latest_source_versions.values())
        occurrence_ids = tuple(
            dict.fromkeys(
                str(
                    dict(item.get("external_reference", {})).get(
                        "external_id",
                        "",
                    )
                )
                for item in source_versions
                if str(
                    dict(item.get("external_reference", {})).get(
                        "external_id",
                        "",
                    )
                )
            )
        )
        catalogs = self.store.current_many("source_catalog", occurrence_ids)
        occurrence_rows = self.store.inventory_occurrences_by_object_ids(
            occurrence_ids
        )
        source_group_occurrences: list[InventoryOccurrence] = []
        for candidates in occurrence_rows.values():
            if not candidates:
                continue
            raw_occurrence = dict(candidates[0]).get("occurrence", {})
            if not isinstance(raw_occurrence, Mapping):
                continue
            try:
                source_group_occurrences.append(
                    InventoryOccurrence(**dict(raw_occurrence))
                )
            except (TypeError, ValueError):
                continue
        source_group_projection = SourceGroupProjection.from_occurrences(
            source_group_occurrences
        )
        anchors = self.store.current_many(
            "evidence_anchor",
            tuple(str(item) for item in evidence_ids if str(item)),
        )
        anchors_by_source: dict[tuple[str, int], list[Mapping[str, Any]]] = {}
        for anchor in anchors.values():
            if not bool(anchor.get("current", True)):
                continue
            key = (
                str(anchor.get("source_id", "")),
                int(anchor.get("source_version", 0) or 0),
            )
            anchors_by_source.setdefault(key, []).append(anchor)

        grouped: dict[str, dict[str, Any]] = {}
        rows: list[dict[str, Any]] = []
        for source_version in source_versions:
            reference = dict(source_version.get("external_reference", {}))
            occurrence_id = str(reference.get("external_id", ""))
            provider = str(
                source_version.get("provider")
                or reference.get("provider")
                or "source"
            ).strip().casefold()
            candidates = occurrence_rows.get(occurrence_id, ())
            occurrence_row = dict(candidates[0]) if candidates else {}
            occurrence = dict(occurrence_row.get("occurrence", {}))
            metadata = occurrence.get("metadata", {})
            if not isinstance(metadata, Mapping):
                metadata = {}
            content = source_version.get("content", {})
            if not isinstance(content, Mapping):
                content = {}
            catalog = catalogs.get(occurrence_id, {})

            kind = str(
                reference.get("object_type")
                or catalog.get("object_type")
                or occurrence_row.get("object_type")
                or "information"
            ).strip().casefold()
            kind_label = _kind_label(kind)
            header_payload = content.get("headers", {})
            if not isinstance(header_payload, Mapping):
                header_payload = {}
            source_group_chain = (
                source_group_projection.group_chain(
                    provider=provider,
                    occurrence_id=occurrence_id,
                )
                if occurrence_id
                else ()
            )
            if provider == "gmail":
                raw_label = (
                    _first_text(header_payload, ("subject", "Subject"))
                    or _first_text(
                        content,
                        ("subject", "title", "display_name", "name"),
                    )
                    or _first_text(
                        catalog,
                        ("display_name", "title", "name"),
                    )
                    or _first_text(
                        metadata,
                        ("display_name", "title", "name"),
                    )
                )
            else:
                raw_label = (
                    _first_text(
                        catalog,
                        ("display_name", "title", "name"),
                    )
                    or _first_text(
                        content,
                        (
                            "subject",
                            "title",
                            "display_name",
                            "name",
                            "file_name",
                        ),
                    )
                    or _first_text(header_payload, ("subject", "Subject"))
                    or _first_text(
                        metadata,
                        ("display_name", "title", "name"),
                    )
                )
            if source_group_chain:
                source_group = source_group_chain[-1]
                group_id = source_group.group_id
                group_title = _localized(
                    source_group.title,
                    source_group.title,
                )
            label_text = _safe_source_label(
                raw_label,
                fallback=str(kind_label["en"]),
            )
            label = _localized(label_text, label_text)

            if provider == "gmail":
                private_group = _first_text(
                    content,
                    ("provider_thread_id", "thread_id"),
                ) or occurrence_id
                group_id = _digest(("gmail-thread", private_group))[:39]
                group_title = _localized(
                    (
                        f"Gmail conversation · {label_text}"
                        if label_text
                        else "Gmail conversation"
                    ),
                    (
                        f"Gmail 邮件会话 · {label_text}"
                        if label_text
                        else "Gmail 邮件会话"
                    ),
                )
            elif provider in {"filesystem", "local", "file"}:
                labels = metadata.get("source_group_labels", ())
                if not isinstance(labels, (list, tuple)):
                    labels = ()
                raw_group = next(
                    (
                        _safe_source_label(item, fallback="")
                        for item in reversed(tuple(labels))
                        if _safe_source_label(item, fallback="")
                    ),
                    "",
                )
                private_group = (
                    _first_text(
                        metadata,
                        ("source_neighborhood_id", "parent_occurrence_id"),
                    )
                    or raw_group
                    or "local-files"
                )
                group_id = _digest(("filesystem-group", private_group))[:39]
                safe_group = raw_group or "Local files"
                group_title = _localized(
                    safe_group,
                    safe_group if raw_group else "本地文件",
                )
            elif provider in {"codex", "codex_project", "codex-workspace"}:
                raw_group = _safe_source_label(
                    _first_text(
                        metadata,
                        (
                            "project_name",
                            "workspace_name",
                            "display_name",
                        ),
                    ),
                    fallback="Codex project",
                )
                private_group = _first_text(
                    metadata,
                    ("project_id", "workspace_id"),
                ) or raw_group
                group_id = _digest(("codex-project", private_group))[:39]
                group_title = _localized(raw_group, raw_group)
            else:
                provider_label = _safe_source_label(
                    provider.replace("_", " ").title(),
                    fallback="Other information",
                )
                group_id = _digest(
                    ("provider-group", provider, occurrence_id)
                )[:39]
                group_title = _localized(provider_label, provider_label)

            source_anchors = tuple(
                sorted(
                    anchors_by_source.get(
                        (
                            str(source_version.get("source_id", "")),
                            int(source_version.get("version", 0) or 0),
                        ),
                        (),
                    ),
                    key=lambda item: str(item.get("evidence_id", "")),
                )
            )
            summary_parts = tuple(
                dict.fromkeys(
                    " ".join(str(item.get("text", "")).strip().split())
                    for item in source_anchors
                    if str(item.get("text", "")).strip()
                )
            )
            summary_text = " · ".join(summary_parts[:2]).strip()
            if len(summary_text) > 360:
                summary_text = summary_text[:357].rstrip() + "…"
            if not summary_text:
                summary_text = _first_text(
                    content,
                    ("summary", "snippet", "description", "subject", "title"),
                )
            if not summary_text:
                summary_text = label_text
            availability_status, availability_label = _source_availability(
                source_version,
                occurrence_row,
            )
            modalities = tuple(
                dict.fromkeys(
                    str(item.get("modality", "reported")).strip()
                    for item in source_anchors
                    if str(item.get("modality", "")).strip()
                )
            ) or ("source_only",)
            if provider == "gmail":
                privacy_safe_location = _localized("Gmail", "Gmail")
            elif provider in {"filesystem", "local", "file"}:
                safe_path_parts = tuple(
                    part
                    for item in source_group_chain
                    if (
                        part := _safe_source_label(
                            getattr(item, "title", ""),
                            fallback="",
                        )
                    )
                )
                privacy_safe_location = (
                    _localized(" › ".join(safe_path_parts), " › ".join(safe_path_parts))
                    if safe_path_parts
                    else _localized("Local files", "本地文件")
                )
            elif provider in {"codex", "codex_project", "codex-workspace"}:
                privacy_safe_location = _localized("Codex project", "Codex 项目")
            else:
                provider_location = _safe_source_label(
                    provider.replace("_", " ").title(),
                    fallback="Other information",
                )
                privacy_safe_location = _localized(
                    provider_location,
                    provider_location,
                )
            row = {
                "record_ref": _digest(
                    (
                        "file-information",
                        source_version.get("source_id", ""),
                        source_version.get("version", 0),
                    )
                )[:39],
                "label": label,
                "type": kind_label,
                "kind": kind or "information",
                "provider": provider,
                "privacy_safe_location": privacy_safe_location,
                "location_group": dict(group_title),
                "observed_time": _source_observed_time(content, occurrence),
                "relevant_time": _source_observed_time(content, occurrence),
                "summary": _localized(summary_text, summary_text),
                "availability": {
                    "status": availability_status,
                    "label": availability_label,
                },
                "modalities": modalities,
                "evidence_available": bool(source_anchors),
                "history_available": int(
                    source_version.get("version", 1) or 1
                )
                > 1,
            }
            rows.append(row)
            group = grouped.setdefault(
                group_id,
                {
                    "group_id": group_id,
                    "title": group_title,
                    "provider": provider,
                    "source_type": kind,
                    "items": [],
                },
            )
            group["items"].append(row)

        rows.sort(
            key=lambda item: (
                str(dict(item["location_group"]).get("en", "")).casefold(),
                str(dict(item["label"]).get("en", "")).casefold(),
                str(item["record_ref"]),
            )
        )
        group_rows = []
        for group in grouped.values():
            items = tuple(
                sorted(
                    group["items"],
                    key=lambda item: (
                        str(dict(item["label"]).get("en", "")).casefold(),
                        str(item["record_ref"]),
                    ),
                )
            )
            group_rows.append(
                {
                    **{key: value for key, value in group.items() if key != "items"},
                    "items": items,
                    "count": len(items),
                }
            )
        group_rows.sort(
            key=lambda item: (
                str(dict(item["title"]).get("en", "")).casefold(),
                str(item["group_id"]),
            )
        )
        selected_rows = tuple(rows[:FILES_INFORMATION_LIMIT])
        return {
            "groups": tuple(group_rows),
            "items": selected_rows,
            "total_count": len(rows),
            "limit": FILES_INFORMATION_LIMIT,
            "has_more": len(rows) > FILES_INFORMATION_LIMIT,
        }

    def _legacy_coverage_files_and_information(
        self,
        *,
        coverage: Sequence[Mapping[str, Any]],
        evidence_ids: Sequence[str],
    ) -> dict[str, Any]:
        """Project pre-migration coverage rows until their SourceVersions exist."""

        object_ids = tuple(
            dict.fromkeys(
                str(item.get("object_id", ""))
                for item in coverage
                if str(item.get("object_id", ""))
            )
        )
        catalogs = self.store.current_many("source_catalog", object_ids)
        anchors = self.store.current_many(
            "evidence_anchor",
            tuple(str(item) for item in evidence_ids if str(item)),
        )
        summary_text = next(
            (
                " ".join(str(item.get("text", "")).strip().split())
                for item in anchors.values()
                if str(item.get("text", "")).strip()
            ),
            "",
        )
        rows = []
        for coverage_row in coverage:
            object_id = str(coverage_row.get("object_id", ""))
            if not object_id:
                continue
            catalog = catalogs.get(object_id, {})
            kind = str(
                catalog.get(
                    "object_type",
                    coverage_row.get("object_type", "information"),
                )
            ).casefold()
            kind_label = _kind_label(kind)
            display_name = _safe_source_label(
                catalog.get("display_name", ""),
                fallback=str(kind_label["en"]),
            )
            availability_status, availability_label = _availability(
                coverage_row
            )
            rows.append(
                {
                    "record_ref": _digest(
                        ("legacy-file-information", object_id)
                    )[:39],
                    "label": _localized(display_name, display_name),
                    "type": kind_label,
                    "kind": kind or "information",
                    "provider": "",
                    "privacy_safe_location": _localized(
                        "Registered source",
                        "已登记来源",
                    ),
                    "location_group": _localized(
                        "Registered source",
                        "已登记来源",
                    ),
                    "observed_time": _relevant_time(coverage_row),
                    "relevant_time": _relevant_time(coverage_row),
                    "summary": _localized(
                        summary_text or display_name,
                        summary_text or display_name,
                    ),
                    "availability": {
                        "status": availability_status,
                        "label": availability_label,
                    },
                    "modalities": tuple(
                        dict.fromkeys(
                            str(item.get("modality", "")).strip()
                            for item in anchors.values()
                            if str(item.get("modality", "")).strip()
                        )
                    ) or ("source_only",),
                    "evidence_available": bool(anchors),
                    "history_available": int(
                        coverage_row.get("revision", 1) or 1
                    )
                    > 1,
                }
            )
        rows.sort(
            key=lambda item: (
                str(dict(item["label"]).get("en", "")).casefold(),
                str(item["record_ref"]),
            )
        )
        selected = tuple(rows[:FILES_INFORMATION_LIMIT])
        group = {
            "group_id": _digest(("legacy-registered-source", object_ids))[:39],
            "title": _localized("Registered source", "已登记来源"),
            "provider": "",
            "source_type": "",
            "items": selected,
            "count": len(selected),
        }
        return {
            "groups": (group,) if selected else (),
            "items": selected,
            "total_count": len(rows),
            "limit": FILES_INFORMATION_LIMIT,
            "has_more": len(rows) > FILES_INFORMATION_LIMIT,
        }

    def _card(
        self,
        projection: Mapping[str, Any],
        *,
        coverage: tuple[dict[str, Any], ...] | None = None,
        hierarchy: Mapping[str, Any] | None = None,
        path_titles: Mapping[str, Mapping[str, str]] | None = None,
        context: Mapping[str, Any] | None = None,
        admission: Mapping[str, Any] | None = None,
        outcome: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        matter_id = str(projection["matter_id"])
        evidence_ids = tuple(str(item) for item in projection.get("evidence_ids", ()))
        title, summary = _title_and_summary(projection)
        state = str(projection.get("state", "uncertain"))
        events = (
            tuple(context.get("events", ()))
            if context is not None
            else self._events_for_matter(matter_id, evidence_ids)
        )
        people = (
            tuple(context.get("people", ()))
            if context is not None
            else self._people_for_matter(matter_id, evidence_ids)
        )
        loops = (
            tuple(context.get("loops", ()))
            if context is not None
            else self._open_loops(matter_id)
        )
        if coverage is None:
            coverage = self._coverage_for_matter(matter_id)
        if hierarchy is None:
            hierarchy = self.store.current(
                "matter_hierarchy_projection",
                matter_id,
            ) or {}
        if admission is None:
            admission = self.store.current(
                "admission_decision",
                matter_id,
            )
        if outcome is None:
            outcome = (
                context.get("outcome")
                if context is not None
                else self.store.current(
                    "outcome_decision",
                    f"{matter_id}:outcome",
                )
            )
        source_versions = self._source_versions_for_admission(admission)
        activity = (
            dict(context.get("activity", {}))
            if context is not None
            else self.store.current("matter_activity", matter_id) or {}
        )
        activity_current = _activity_projection_is_current(
            activity,
            expected_matter_id=matter_id,
        )
        try:
            hierarchy_child_count = int(
                hierarchy.get("child_count", 0)
            )
        except (TypeError, ValueError):
            hierarchy_child_count = 0
        hero_record_payload = (
            context.get("hero_record")
            if context is not None
            else self.store.current(
                "generated_hero_record",
                matter_id,
            )
        )
        is_root_matter = not str(
            hierarchy.get("parent_matter_id", "")
        ).strip()
        if hero_record_payload is not None and is_root_matter:
            hero_projection = GeneratedHeroProjectionOwner.project(
                GeneratedHeroRecord(**dict(hero_record_payload))
            )
            hero = {
                "status": hero_projection.status,
                "preview_token": hero_projection.private_asset_token,
                "alt": dict(hero_projection.localized_alt),
                "generation_revision": hero_projection.generation_revision,
            }
        elif is_root_matter:
            hero = {
                "status": "generation_pending_placeholder",
                "preview_token": "",
                "alt": _localized(
                    "A documentary-style Matter image is being prepared",
                    "纪实摄影风格的事项图片正在生成",
                ),
                "generation_revision": 0,
            }
        else:
            hero = {
                "status": "not_applicable",
                "preview_token": "",
                "alt": _localized("", ""),
                "generation_revision": 0,
            }
        classifications = (
            dict(context.get("classification", {}))
            if context is not None
            else self.store.current(
                "matter_classification",
                matter_id,
            ) or {}
        )
        relationships = (
            tuple(context.get("relationships", ()))
            if context is not None
            else tuple(
                row
                for row in self.store.iter_current("relation_candidate")
                if matter_id
                in {
                    str(row.get("source_matter_id", "")),
                    str(row.get("target_matter_id", "")),
                }
            )
        )
        start_boundary = earliest_start_boundary(events, source_versions)
        start_time = (
            start_boundary.value if start_boundary is not None else ""
        )
        latest_meaningful_clue_at = (
            str(activity.get("latest_meaningful_clue_at", ""))
            if activity_current
            else ""
        )
        path_ids = tuple(
            str(item)
            for item in hierarchy.get("path", (matter_id,))
            if str(item)
        ) or (matter_id,)
        if path_titles is None:
            path_projections = self.store.current_many("projection", path_ids)
            path_titles = {
                item_id: _title_and_summary(path_projection)[0]
                for item_id, path_projection in path_projections.items()
            }
        hierarchy_path = tuple(
            {
                "matter_id": item_id,
                "title": dict(
                    path_titles.get(
                        item_id,
                        _localized("Unavailable matter", "事项暂不可用"),
                    )
                ),
            }
            for item_id in path_ids
        )
        semantic_revision = str(projection.get("semantic_revision", ""))
        state_basis_modality = "reported"
        state_basis_scope = ""
        if (
            isinstance(outcome, Mapping)
            and str(outcome.get("status", "")) == state
        ):
            state_basis_modality = (
                str(outcome.get("basis_modality", "")).strip()
                or "unknown"
            )
            state_basis_scope = str(
                outcome.get("basis_scope", "")
            ).strip()
        coverage_source_ids = {
            str(item.get("object_id", ""))
            for item in coverage
            if str(item.get("object_id", ""))
        }
        source_type_values: dict[str, dict[str, Any]] = {}
        for item in source_versions:
            reference = dict(item.get("external_reference", {}))
            kind = _facet_value(
                reference.get(
                    "object_type",
                    item.get("provider", "information"),
                )
            )
            if not kind:
                continue
            source_type_values.setdefault(
                kind,
                {
                    "value": kind,
                    "label": _kind_label(kind),
                },
            )
        relationship_values: dict[str, dict[str, Any]] = {}
        for item in relationships:
            relation_type = _facet_value(item.get("relation_type", "relates"))
            if not relation_type:
                continue
            relationship_values.setdefault(
                relation_type,
                {
                    "value": relation_type,
                    "label": _relation_label(relation_type),
                },
            )
        topic_types = tuple(
            item
            for item in classifications.get("topic_types", ())
            if isinstance(item, Mapping)
            and _facet_value(item.get("value", ""))
            and set(item.get("label", {}))
            == set(DEFAULT_LOCALE_REGISTRY.available_locales)
        )
        return {
            "matter_id": matter_id,
            "semantic_revision": semantic_revision,
            "title_semantic_revision": semantic_revision,
            "summary_semantic_revision": semantic_revision,
            "state": state,
            "state_basis_modality": state_basis_modality,
            "state_basis_scope": state_basis_scope,
            "status_group": _status_group(state),
            "title": title,
            "summary": summary,
            "summary_status": (
                "current" if all(summary.values()) else "pending"
            ),
            "start_time": start_time,
            "start_time_basis": (
                start_boundary.basis if start_boundary is not None else ""
            ),
            "start_time_source_provider": (
                start_boundary.provider if start_boundary is not None else ""
            ),
            "latest_meaningful_clue_at": latest_meaningful_clue_at,
            "activity_status": "current" if activity_current else "pending",
            "start_year": (
                start_boundary.year
                if start_boundary is not None
                else ""
            ),
            "people": tuple(
                {
                    "person_id": str(item.get("person_id", "")),
                    "value": _facet_value(item.get("display_name", "")),
                    "name": str(item.get("display_name", "")).strip(),
                    "label": _localized(
                        str(item.get("display_name", "")).strip(),
                        str(item.get("display_name", "")).strip(),
                    ),
                    "role": str(item.get("role", "")).strip(),
                    "role_label": _person_role_label(item.get("role", "")),
                    "resolved": bool(item.get("resolved", False)),
                }
                for item in people
                if str(item.get("display_name", "")).strip()
            ),
            "event_count": len(events),
            "people_count": len(people),
            "source_count": (
                len(source_versions)
                if source_versions
                else len(coverage_source_ids)
            ),
            "open_loop_count": len(loops),
            "evidence_count": len(evidence_ids),
            "uncertainty": state in {"uncertain", "completion_unproven"},
            "parent_matter_id": str(hierarchy.get("parent_matter_id", "")),
            "owning_root_matter_id": path_ids[0],
            "matched_node_id": matter_id,
            "hierarchy_path": hierarchy_path,
            "search_result_kind": (
                "child"
                if str(hierarchy.get("parent_matter_id", ""))
                else "root"
            ),
            "child_count": hierarchy_child_count,
            "relationships": tuple(relationship_values.values()),
            "topic_types": topic_types,
            "source_types": tuple(source_type_values.values()),
            "hero": hero,
        }

    def _card_contexts(
        self,
        projections: Iterable[Mapping[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Load card-owned facts once, then group them for a bounded card set."""

        projection_rows = tuple(projections)
        matter_ids = tuple(
            dict.fromkeys(
                str(item.get("matter_id", ""))
                for item in projection_rows
                if str(item.get("matter_id", ""))
            )
        )
        matter_set = set(matter_ids)
        evidence_to_matters: dict[str, set[str]] = {}
        for projection in projection_rows:
            matter_id = str(projection.get("matter_id", ""))
            for evidence_id in projection.get("evidence_ids", ()):
                normalized = str(evidence_id)
                if normalized:
                    evidence_to_matters.setdefault(
                        normalized,
                        set(),
                    ).add(matter_id)
        evidence_ids = tuple(evidence_to_matters)
        contexts = {
            matter_id: {
                "events": [],
                "people": [],
                "loops": [],
                "relationships": [],
            }
            for matter_id in matter_ids
        }
        event_targets: dict[str, set[str]] = {}
        direct_events = self.store.current_by_json_scalar_values(
            "temporal_event",
            json_field="object_ref",
            values=matter_ids,
        )
        for matter_id, events in direct_events.items():
            for event in events:
                event_id = str(event.get("event_id", "")) or _digest(event)
                event_targets.setdefault(event_id, set()).add(matter_id)
        evidence_events = self.store.current_by_json_array_members(
            "temporal_event",
            json_field="evidence_ids",
            values=evidence_ids,
        )
        event_payloads: dict[str, Mapping[str, Any]] = {}
        for events in (*direct_events.values(), *evidence_events.values()):
            for event in events:
                event_id = str(event.get("event_id", "")) or _digest(event)
                event_payloads[event_id] = event
        event_payloads = {
            str(event.get("event_id", "")) or _digest(event): event
            for event in self._active_temporal_events(
                event_payloads.values()
            )
        }
        event_targets = {
            event_id: targets
            for event_id, targets in event_targets.items()
            if event_id in event_payloads
        }
        for evidence_id, events in evidence_events.items():
            targets = evidence_to_matters.get(evidence_id, set())
            for event in events:
                event_id = str(event.get("event_id", "")) or _digest(event)
                if event_id not in event_payloads:
                    continue
                event_targets.setdefault(event_id, set()).update(targets)
        for event_id, targets in event_targets.items():
            event = event_payloads[event_id]
            for matter_id in targets.intersection(matter_set):
                contexts[matter_id]["events"].append(event)

        direct_people = self.store.current_by_json_scalar_values(
            "person_candidate",
            json_field="evidence_ref",
            values=evidence_ids,
        )
        evidence_people = self.store.current_by_json_array_members(
            "person_candidate",
            json_field="evidence_ids",
            values=evidence_ids,
        )
        people_by_matter: dict[str, dict[str, Mapping[str, Any]]] = {
            matter_id: {} for matter_id in matter_ids
        }
        for evidence_id, people_rows in (
            *direct_people.items(),
            *evidence_people.items(),
        ):
            for matter_id in evidence_to_matters.get(evidence_id, set()):
                for person in people_rows:
                    person_id = (
                        str(person.get("person_id", ""))
                        or _digest(person)
                    )
                    people_by_matter[matter_id][person_id] = person
        direct_matter_people: list[
            tuple[str, tuple[dict[str, Any], ...]]
        ] = []
        for json_field in ("matter_id", "object_ref"):
            direct_matter_people.extend(
                self.store.current_by_json_scalar_values(
                    "person_candidate",
                    json_field=json_field,
                    values=matter_ids,
                ).items()
            )
        direct_matter_people.extend(
            self.store.current_by_json_array_members(
                "person_candidate",
                json_field="matter_ids",
                values=matter_ids,
            ).items()
        )
        for matter_id, people_rows in direct_matter_people:
            for person in people_rows:
                person_id = str(person.get("person_id", "")) or _digest(person)
                people_by_matter[matter_id][person_id] = person
        for matter_id, people_rows in people_by_matter.items():
            contexts[matter_id]["people"].extend(people_rows.values())

        loops_by_matter = self.store.current_by_json_scalar_values(
            "open_loop",
            json_field="matter_id",
            values=matter_ids,
        )
        for matter_id, loops in loops_by_matter.items():
            contexts[matter_id]["loops"].extend(loops)

        for grouped in (
            self.store.current_by_json_scalar_values(
                "relation_candidate",
                json_field="source_matter_id",
                values=matter_ids,
            ),
            self.store.current_by_json_scalar_values(
                "relation_candidate",
                json_field="target_matter_id",
                values=matter_ids,
            ),
        ):
            for matter_id, relationships in grouped.items():
                for relation in relationships:
                    relation_id = (
                        str(relation.get("relation_id", ""))
                        or _digest(relation)
                    )
                    contexts[matter_id]["relationships"].append(
                        (relation_id, relation)
                    )
        activities = self.store.current_many("matter_activity", matter_ids)
        heroes = self.store.current_many(
            "generated_hero_record",
            matter_ids,
        )
        classifications = self.store.current_many(
            "matter_classification",
            matter_ids,
        )
        outcomes = self.store.current_many(
            "outcome_decision",
            tuple(f"{matter_id}:outcome" for matter_id in matter_ids),
        )
        for matter_id, context in contexts.items():
            context["events"] = tuple(
                sorted(
                    context["events"],
                    key=lambda item: (
                        str(item.get("claimed_time", "")),
                        str(item.get("record_time", "")),
                        str(item.get("event_id", "")),
                    ),
                    reverse=True,
                )
            )
            context["people"] = tuple(
                sorted(
                    context["people"],
                    key=lambda item: str(item.get("display_name", "")),
                )
            )
            context["loops"] = tuple(context["loops"])
            context["relationships"] = tuple(
                relation
                for _relation_id, relation in dict(
                    context["relationships"]
                ).items()
            )
            context["activity"] = activities.get(matter_id, {})
            context["hero_record"] = heroes.get(matter_id)
            context["classification"] = classifications.get(matter_id, {})
            context["outcome"] = outcomes.get(f"{matter_id}:outcome", {})
        return contexts

    def _visible_projection(self, projection: Mapping[str, Any]) -> bool:
        matter_id = str(projection.get("matter_id", ""))
        admission = self.store.current("admission_decision", matter_id)
        return (
            matter_id in self._active_matter_output_ids((matter_id,))
            and self._exact_admission(admission, matter_id)
        )

    @staticmethod
    def _exact_admission(
        admission: Mapping[str, Any] | None,
        matter_id: str,
    ) -> bool:
        matter = (
            admission.get("matter")
            if isinstance(admission, Mapping)
            else None
        )
        return bool(
            matter_id
            and isinstance(admission, Mapping)
            and str(admission.get("status", "")) == "admitted"
            and isinstance(matter, Mapping)
            and str(matter.get("matter_id", "")) == matter_id
            and matter.get("admitted") is not False
        )

    def _catalog_revision(self, cards: Iterable[Mapping[str, Any]]) -> str:
        return _digest(
            {
                "cards": tuple(
                    (
                        item["matter_id"],
                        item["semantic_revision"],
                        item["state"],
                        tuple(sorted(dict(item["title"]).items())),
                        tuple(sorted(dict(item["summary"]).items())),
                        item["latest_meaningful_clue_at"],
                        item["activity_status"],
                        item["hero"]["preview_token"],
                        item["hero"]["status"],
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
        sort: str = "activity",
        offset: int = 0,
        limit: int = 60,
        root_only: bool = True,
        start_year: str = "all",
        people: Sequence[str] = (),
        relationships: Sequence[str] = (),
        topic_types: Sequence[str] = (),
        source_types: Sequence[str] = (),
    ) -> dict[str, Any]:
        DEFAULT_LOCALE_REGISTRY.require(locale)
        if offset < 0 or limit < 1 or limit > 200:
            raise ValueError("object catalog page bounds are invalid")
        if status not in {"all", "planned", "in_progress", "completed"}:
            raise ValueError("unsupported status filter")
        if time_filter != "all":
            raise ValueError("unsupported time filter")
        if sort != "activity":
            raise ValueError("unsupported catalog sort")
        normalized_start_year = str(start_year).strip()
        if (
            normalized_start_year != "all"
            and (
                len(normalized_start_year) != 4
                or not normalized_start_year.isdigit()
            )
        ):
            raise ValueError("unsupported start year filter")
        selected_facets = {
            "people": _normalized_filter_values(people),
            "relationships": _normalized_filter_values(relationships),
            "topic_types": _normalized_filter_values(topic_types),
            "source_types": _normalized_filter_values(source_types),
        }
        catalog_query = self.store.object_browser_catalog_page(
            locale=locale,
            query=query,
            status=status,
            root_only=root_only,
            start_year=normalized_start_year,
            people=selected_facets["people"],
            relationships=selected_facets["relationships"],
            topic_types=selected_facets["topic_types"],
            source_types=selected_facets["source_types"],
            offset=offset,
            limit=limit,
        )
        page = self.cards(catalog_query["matter_ids"])
        revision = str(catalog_query["revision_fingerprint"])
        counts = {
            group: int(
                catalog_query["status_counts"].get(group, 0)
            )
            for group in ("planned", "in_progress", "completed")
        }
        start_years = tuple(
            {
                "value": year,
                "label": _localized(year, year),
                "count": count,
            }
            for year, count in catalog_query["start_year_rows"]
        )
        people_facets = tuple(
            {
                "value": value,
                "label": _localized(label, label),
                "count": count,
            }
            for value, label, count in catalog_query["people_rows"]
        )
        relationship_facets = tuple(
            sorted(
                (
                    {
                        "value": value,
                        "label": _relation_label(value),
                        "count": count,
                    }
                    for value, count in catalog_query["relationship_rows"]
                ),
                key=lambda item: (
                    str(item["label"]["en"]).casefold(),
                    str(item["value"]),
                ),
            )
        )
        topic_facets = tuple(
            {
                "value": value,
                "label": _localized(label_en, label_zh_cn),
                "count": count,
            }
            for value, label_en, label_zh_cn, count in catalog_query[
                "topic_rows"
            ]
        )
        source_facets = tuple(
            sorted(
                (
                    {
                        "value": value,
                        "label": _kind_label(value),
                        "count": count,
                    }
                    for value, count in catalog_query["source_rows"]
                ),
                key=lambda item: (
                    str(item["label"]["en"]).casefold(),
                    str(item["value"]),
                ),
            )
        )
        total_count = int(catalog_query["total_count"])
        next_offset = offset + len(catalog_query["matter_ids"])
        return {
            "items": page,
            "offset": offset,
            "limit": limit,
            "total_count": total_count,
            "next_offset": next_offset if next_offset < total_count else None,
            "has_more": next_offset < total_count,
            "catalog_revision": revision,
            "selected_locale": locale,
            "query": query,
            "filters": {
                "status": status,
                "time": time_filter,
                "sort": sort,
                "start_year": normalized_start_year,
                "people": tuple(sorted(selected_facets["people"])),
                "relationships": tuple(
                    sorted(selected_facets["relationships"])
                ),
                "topic_types": tuple(sorted(selected_facets["topic_types"])),
                "source_types": tuple(sorted(selected_facets["source_types"])),
            },
            "facets": {
                "status": {
                    "all": sum(counts.values()),
                    **counts,
                },
                "hierarchy": dict(catalog_query["hierarchy_counts"]),
                "start_year": start_years,
                "people": people_facets,
                "relationships": relationship_facets,
                "topic_types": topic_facets,
                "source_types": source_facets,
            },
            "hierarchy_scope": "roots" if root_only else "all",
        }

    def cards(
        self,
        matter_ids: Iterable[str],
    ) -> tuple[dict[str, Any], ...]:
        """Build a bounded ordered card set for hierarchy child pages."""

        ordered_ids = tuple(
            dict.fromkeys(str(item) for item in matter_ids if str(item))
        )
        projections = self.store.current_many("projection", ordered_ids)
        coverage_by_matter = self._coverage_by_matter(ordered_ids)
        hierarchy_by_matter = self.store.current_many(
            "matter_hierarchy_projection",
            ordered_ids,
        )
        path_ids = {
            str(path_id)
            for hierarchy in hierarchy_by_matter.values()
            for path_id in hierarchy.get("path", ())
            if str(path_id)
        }
        path_projections = self.store.current_many("projection", path_ids)
        path_titles = {
            matter_id: _title_and_summary(path_projection)[0]
            for matter_id, path_projection in path_projections.items()
        }
        card_contexts = self._card_contexts(
            projection
            for matter_id in ordered_ids
            if (projection := projections.get(matter_id)) is not None
        )
        admissions = self.store.current_many(
            "admission_decision",
            ordered_ids,
        )
        active_matter_ids = self._active_matter_output_ids(ordered_ids)
        cards = []
        for matter_id in ordered_ids:
            projection = projections.get(matter_id)
            admission = admissions.get(matter_id)
            if (
                projection is None
                or matter_id not in active_matter_ids
                or str(projection.get("equivalence_status", "")) != "equivalent"
                or not self._exact_admission(admission, matter_id)
            ):
                continue
            cards.append(
                self._card(
                    projection,
                    coverage=coverage_by_matter.get(matter_id, ()),
                    hierarchy=hierarchy_by_matter.get(matter_id, {}),
                    path_titles=path_titles,
                    context=card_contexts.get(matter_id, {}),
                    admission=admission,
                )
            )
        return tuple(cards)

    @staticmethod
    def _timeline_sentence(event: Mapping[str, Any]) -> dict[str, str]:
        provided = _text_map(event, "localized_sentence")
        if all(provided.values()):
            return provided
        kind = str(event.get("kind", "event")).replace("_", " ")
        actor = str(event.get("actor", "")).strip()
        en_parts = [part for part in (actor, kind) if part]
        zh_kind = {
            "actual start reported": "已报告实际开始",
            "blocked reported": "已报告受阻",
            "deadline": "截止时间",
            "milestone": "里程碑",
            "planned event": "计划事件",
            "semantic event": "语义事件",
            "work recorded": "已记录工作",
        }.get(kind, kind)
        zh_parts = [part for part in (actor, zh_kind) if part]
        en = " · ".join(en_parts) or "An event was recorded"
        zh_cn = " · ".join(zh_parts) or "记录了一项事件"
        return _localized(en, zh_cn)

    def _timeline_item(self, event: Mapping[str, Any]) -> dict[str, Any]:
        modality = str(event.get("modality", "inferred"))
        historical_inference = (
            modality == "inferred"
            and str(event.get("temporal_direction", "")) == "past"
            and str(event.get("inference_purpose", ""))
            == "historical_gap_fill"
            and bool(event.get("revisable", False))
        )
        basis_label = {
            "observed": _localized("Observed", "已观察"),
            "reported": _localized("Source record", "来源记录"),
            "planned": _localized("Planned", "计划"),
            "inferred": (
                _localized(
                    "AI historical inference",
                    "AI 历史推断",
                )
                if historical_inference
                else _localized("AI inference", "AI 推断")
            ),
        }.get(modality, _localized("Unknown basis", "依据未知"))
        alternatives = tuple(
            {
                "sentence": self._timeline_sentence(item),
                "claimed_time": str(item.get("claimed_time", "")),
                "record_time": str(item.get("record_time", "")),
                "modality": str(item.get("modality", "inferred")),
            }
            for item in event.get("_alternative_events", ())
            if isinstance(item, Mapping)
        )
        return {
            "logical_event_key": _event_logical_key(event),
            "current_revision": bool(event.get("current_revision", True)),
            "revision": int(event.get("revision", 0) or 0),
            "owning_matter_id": str(event.get("object_ref", "")),
            "sentence": self._timeline_sentence(event),
            "claimed_time": str(event.get("claimed_time", "")),
            "record_time": str(event.get("record_time", "")),
            "modality": modality,
            "basis_label": basis_label,
            "historical_inference": historical_inference,
            "revisable": bool(event.get("revisable", False)),
            "confidence": float(event.get("confidence", 0.0) or 0.0),
            "conflict": bool(event.get("conflict", False)),
            "has_history": bool(event.get("has_history", False)),
            "revision_count": int(event.get("revision_count", 1) or 1),
            "alternatives": alternatives,
            "alternative_count": len(alternatives),
        }

    def timeline_item(self, event: Mapping[str, Any]) -> dict[str, Any]:
        """Project one already-selected logical Event for a private reader."""

        return self._timeline_item(event)

    def detail(self, matter_id: str, *, locale: str = "en") -> dict[str, Any]:
        DEFAULT_LOCALE_REGISTRY.require(locale)
        projection = self.store.current("projection", matter_id)
        if projection is None or not self._visible_projection(projection):
            raise KeyError("matter is unavailable")
        coverage = self._coverage_by_matter((matter_id,)).get(matter_id, ())
        admission = self.store.current("admission_decision", matter_id)
        outcome = self.store.current(
            "outcome_decision",
            f"{matter_id}:outcome",
        )
        source_versions = self._source_versions_for_admission(admission)
        card = self._card(
            projection,
            coverage=coverage,
            admission=admission,
            outcome=outcome,
        )
        evidence_ids = tuple(str(item) for item in projection.get("evidence_ids", ()))
        current_evidence_ids = {
            item for item in evidence_ids if item
        }
        current_people_names = {
            str(item.get("name", "")).casefold()
            for item in card["people"]
            if str(item.get("name", ""))
        }
        candidate_evidence_ids = set(current_evidence_ids)
        if current_people_names:
            for person in self.store.iter_current("person_candidate"):
                if (
                    str(person.get("display_name", "")).casefold()
                    not in current_people_names
                ):
                    continue
                evidence_ref = str(person.get("evidence_ref", ""))
                if evidence_ref:
                    candidate_evidence_ids.add(evidence_ref)
                candidate_evidence_ids.update(
                    str(item)
                    for item in person.get("evidence_ids", ())
                    if str(item)
                )
        candidate_scores: dict[str, int] = {}
        explicit_relations: dict[str, dict[str, dict[str, Any]]] = {}
        for json_field in ("source_matter_id", "target_matter_id"):
            grouped_relations = self.store.current_by_json_scalar_values(
                "relation_candidate",
                json_field=json_field,
                values=(matter_id,),
            )
            for relation in grouped_relations.get(matter_id, ()):
                if str(relation.get("freshness", "current")) != "current":
                    continue
                source_id = str(relation.get("source_matter_id", ""))
                target_id = str(relation.get("target_matter_id", ""))
                candidate_id = target_id if source_id == matter_id else source_id
                if not candidate_id or candidate_id == matter_id:
                    continue
                relation_id = str(relation.get("relation_id", "")) or _digest(
                    relation
                )
                explicit_relations.setdefault(candidate_id, {})[
                    relation_id
                ] = dict(relation)
                candidate_scores[candidate_id] = (
                    candidate_scores.get(candidate_id, 0) + 1000
                )
        evidence_candidates = self.store.current_by_json_array_members(
            "projection",
            json_field="evidence_ids",
            values=candidate_evidence_ids,
        )
        candidate_payloads: dict[str, dict[str, Any]] = {}
        for evidence_id, candidates in evidence_candidates.items():
            for candidate in candidates:
                candidate_id = str(candidate.get("matter_id", ""))
                if not candidate_id or candidate_id == matter_id:
                    continue
                candidate_payloads[candidate_id] = candidate
                candidate_scores[candidate_id] = (
                    candidate_scores.get(candidate_id, 0)
                    + (2 if evidence_id in current_evidence_ids else 1)
                )
        current_source_ids = {
            str(item.get("object_id", ""))
            for item in coverage
            if str(item.get("object_id", ""))
        }
        for candidate_id, shared_count in (
            self.store.matter_ids_for_coverage_objects(
                current_source_ids,
                exclude_matter_id=matter_id,
                limit=RELATED_CANDIDATE_LIMIT,
            )
        ):
            candidate_scores[candidate_id] = (
                candidate_scores.get(candidate_id, 0) + (shared_count * 3)
            )
        ranked_candidate_ids = tuple(
            candidate_id
            for candidate_id, _score in sorted(
                candidate_scores.items(),
                key=lambda item: (-item[1], item[0]),
            )[:RELATED_CANDIDATE_LIMIT]
        )
        missing_candidate_ids = tuple(
            candidate_id
            for candidate_id in ranked_candidate_ids
            if candidate_id not in candidate_payloads
        )
        candidate_payloads.update(
            self.store.current_many("projection", missing_candidate_ids)
        )
        admissions = self.store.current_many(
            "admission_decision",
            ranked_candidate_ids,
        )
        active_related_ids = self._active_matter_output_ids(
            ranked_candidate_ids
        )
        related_projections = tuple(
            candidate
            for candidate_id in ranked_candidate_ids
            if (candidate := candidate_payloads.get(candidate_id)) is not None
            and candidate_id in active_related_ids
            and str(candidate.get("equivalence_status", "")) == "equivalent"
            and self._exact_admission(
                admissions.get(candidate_id),
                candidate_id,
            )
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
        events = self._events_for_matter(matter_id, evidence_ids)
        loops = self._open_loops(matter_id)
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
            str(dict(item.get("external_reference", {})).get("external_id", ""))
            for item in source_versions
            if str(
                dict(item.get("external_reference", {})).get(
                    "external_id",
                    "",
                )
            )
        }
        if not occurrence_ids:
            occurrence_ids = {
                str(item.get("object_id", ""))
                for item in coverage
                if str(item.get("object_id", ""))
            }
        visual_candidates = [
            {
                "kind": str(item.get("kind", "")),
                "preview_token": str(item.get("preview_token", "")),
                "thumbnail_preview_token": str(item.get("preview_token", "")),
                "hero_preview_token": str(item.get("preview_token", "")),
                "alt": _text_map(item, "localized_alt"),
                "localized_alt": _text_map(item, "localized_alt"),
                "width": int(item.get("width", 0) or 0),
                "height": int(item.get("height", 0) or 0),
            }
            for item in self.store.iter_current("visual_asset")
            if str(item.get("occurrence_id", "")) in occurrence_ids
            and bool(item.get("current", False))
            and bool(item.get("display_allowed", False))
            and str(item.get("kind", "")) in {"photo", "existing_image"}
            and str(item.get("preview_token", ""))
        ]
        visual_candidates.sort(
            key=lambda item: (
                {"photo": 0, "existing_image": 1, "document_preview": 2}.get(
                    str(item["kind"]),
                    9,
                ),
                str(item["preview_token"]),
            )
        )
        current_people = {
            str(item.get("name", "")).casefold()
            for item in card["people"]
            if str(item.get("name", ""))
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
            typed_relations = tuple(
                {
                    "relation_type": str(
                        relation.get("relation_type", "related")
                    ),
                    "label": _relation_label(
                        str(relation.get("relation_type", "related"))
                    ),
                    "direction": (
                        "outgoing"
                        if str(relation.get("source_matter_id", ""))
                        == matter_id
                        else "incoming"
                    ),
                    "rationale": str(relation.get("rationale", "")).strip(),
                    "evidence_count": len(
                        tuple(relation.get("evidence_ids", ()))
                    ),
                }
                for relation in explicit_relations.get(
                    candidate_id,
                    {},
                ).values()
            )
            if (
                not shared_sources
                and not shared_people
                and not shared_evidence
                and not typed_relations
            ):
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
                    "relations": typed_relations,
                    "relation_types": tuple(
                        dict.fromkeys(
                            str(item["relation_type"])
                            for item in typed_relations
                        )
                    ),
                }
            )
        related.sort(
            key=lambda item: (
                -(
                    len(tuple(item.get("relations", ()))) * 100
                    +
                    int(item["shared_source_count"])
                    + int(item["shared_people_count"])
                    + int(item["shared_evidence_count"])
                ),
                str(item["matter_id"]),
            )
        )
        timeline = tuple(self._timeline_item(item) for item in events)
        safe_loops = tuple(
            {
                "wait_target": str(item.get("wait_target", "")),
                "closure_condition": str(item.get("closure_condition", "")),
                "status": str(item.get("status", "open")),
                "critical": bool(item.get("critical", False)),
            }
            for item in loops
        )
        files_and_information = self._files_and_information(
            source_versions=source_versions,
            evidence_ids=evidence_ids,
        )
        if (
            not files_and_information["items"]
            and coverage
        ):
            files_and_information = (
                self._legacy_coverage_files_and_information(
                    coverage=coverage,
                    evidence_ids=evidence_ids,
                )
            )
        images = {
            "items": tuple(visual_candidates),
            "total_count": len(visual_candidates),
            "selected_preview_token": (
                str(visual_candidates[0]["preview_token"])
                if visual_candidates
                else ""
            ),
        }
        supplemental_payload = self.store.current(
            "matter_supplemental_information",
            matter_id,
        ) or {}
        supplemental_status = str(
            supplemental_payload.get("status", "pending")
        ).strip().casefold()
        if supplemental_status not in {
            "current",
            "pending",
            "blocked",
            "unavailable",
            "stale",
            "not_applicable",
        }:
            supplemental_status = "pending"
        supplemental_items = tuple(
            {
                "title": _text_map(item, "localized_title"),
                "body": _text_map(item, "localized_body"),
                "kind": str(item.get("kind", "background")),
                "relevant_time": str(item.get("relevant_time", "")),
                "freshness": str(item.get("freshness", "current")),
            }
            for item in supplemental_payload.get("items", ())
            if isinstance(item, Mapping)
            and all(_text_map(item, "localized_body").values())
            and str(item.get("freshness", "current")).strip().casefold()
            == "current"
            and supplemental_status == "current"
        )
        ai_supplemental_information = {
            "items": supplemental_items,
            "total_count": len(supplemental_items),
            "status": "current" if supplemental_items else (
                supplemental_status
                if supplemental_status != "current"
                else "pending"
            ),
        }
        overview = {
            "summary": dict(card["summary"]),
            "state": card["state"],
            "status_group": card["status_group"],
            "start_time": card["start_time"],
            "latest_meaningful_clue_at": card[
                "latest_meaningful_clue_at"
            ],
            "actions": (),
            "open_loops": safe_loops,
            "lifecycle_status": str((lifecycle or {}).get("state", "")),
            "outcome_status": str((outcome or {}).get("status", "")),
        }
        sections = {
            "overview": overview,
            "sub_matters": {
                "items": (),
                "total_count": 0,
                "limit": 50,
                "has_more": False,
            },
            "timeline": timeline,
            "people": card["people"],
            "related_matters": tuple(related[:20]),
            "files_and_information": files_and_information,
            "images": images,
            "ai_supplemental_information": ai_supplemental_information,
        }
        return {
            "matter": card,
            "primary_sections": PRIMARY_DETAIL_SECTIONS,
            "sections": sections,
            "overview": overview,
            "sub_matters": sections["sub_matters"],
            "timeline": timeline,
            "people": card["people"],
            "open_loops": safe_loops,
            "related_matters": tuple(related[:20]),
            "files_and_information": files_and_information,
            "images": images,
            "ai_supplemental_information": ai_supplemental_information,
            "change_history_available": bool(corrections),
            "selected_locale": locale,
        }

    def node_quick_view(
        self,
        matter_id: str,
        *,
        locale: str = "en",
    ) -> dict[str, Any]:
        """Return exactly one selected Matter's facts and supporting material."""

        DEFAULT_LOCALE_REGISTRY.require(locale)
        projection = self.store.current("projection", matter_id)
        if projection is None or not self._visible_projection(projection):
            raise KeyError("matter is unavailable")
        admission = self.store.current("admission_decision", matter_id)
        source_versions = self._source_versions_for_admission(admission)
        evidence_ids = tuple(
            str(item)
            for item in projection.get("evidence_ids", ())
            if str(item)
        )
        card = self._card(
            projection,
            admission=admission,
        )
        events = self._events_for_matter(matter_id, evidence_ids)[:50]
        work_items, work_item_total = (
            self.store.matter_work_items_for_matters_page(
                (matter_id,),
                offset=0,
                limit=50,
            )
        )
        open_loops = self._open_loops(matter_id)[:50]
        facts: list[dict[str, Any]] = []
        for event in events:
            facts.append(
                {
                    "kind": "event",
                    **self._timeline_item(event),
                }
            )
        for item in work_items:
            facts.append(
                {
                    "kind": "work_item",
                    "title": _text_map(item, "localized_title"),
                    "result": _text_map(item, "localized_result"),
                    "status": str(item.get("status", "uncertain")),
                    "start_time": str(
                        item.get("actual_start")
                        or item.get("planned_start")
                        or ""
                    ),
                    "claimed_time": str(
                        item.get("actual_start")
                        or item.get("planned_start")
                        or item.get("actual_end")
                        or item.get("planned_end")
                        or ""
                    ),
                    "end_time": str(
                        item.get("actual_end")
                        or item.get("planned_end")
                        or ""
                    ),
                    "basis_label": (
                        _localized("Observed", "已观察")
                        if str(item.get("status", "")) == "completed"
                        else _localized("Planned", "计划")
                    ),
                }
            )
        for item in open_loops:
            wait_target = str(item.get("wait_target", "")).strip()
            closure_condition = str(
                item.get("closure_condition", "")
            ).strip()
            facts.append(
                {
                    "kind": "wait",
                    "title": _localized(
                        f"Waiting for {wait_target}" if wait_target else "Open wait",
                        f"等待 {wait_target}" if wait_target else "待闭环事项",
                    ),
                    "result": _localized(
                        (
                            f"Closes when {closure_condition}"
                            if closure_condition
                            else "Closure condition is not available"
                        ),
                        (
                            f"闭环条件：{closure_condition}"
                            if closure_condition
                            else "暂时没有闭环条件"
                        ),
                    ),
                    "wait_target": wait_target,
                    "closure_condition": closure_condition,
                    "status": str(item.get("status", "open")),
                    "basis_label": _localized(
                        "Source record",
                        "来源记录",
                    ),
                }
            )
        files_and_information = self._files_and_information(
            source_versions=source_versions,
            evidence_ids=evidence_ids,
        )
        flat_files = {
            "groups": (),
            "items": tuple(files_and_information["items"]),
            "total_count": int(files_and_information["total_count"]),
            "limit": int(files_and_information["limit"]),
            "has_more": bool(files_and_information["has_more"]),
        }
        state_basis_label = (
            _localized(
                "AI historical inference",
                "AI 历史推断",
            )
            if card["state_basis_modality"] == "inferred"
            and card["state_basis_scope"] == "historical_inference"
            else {
                "observed": _localized("Observed", "已观察"),
                "reported": _localized("Source record", "来源记录"),
                "planned": _localized("Planned", "计划"),
            }.get(
                card["state_basis_modality"],
                _localized("", ""),
            )
        )
        summary_region = {
            "title": dict(card["title"]),
            "summary": dict(card["summary"]),
            "summary_status": card["summary_status"],
            "state": card["state"],
            "start_time": card["start_time"],
            "state_basis_modality": card["state_basis_modality"],
            "state_basis_scope": card["state_basis_scope"],
            "state_basis_label": state_basis_label,
            "facts": tuple(facts),
            "fact_count": len(facts),
            "work_item_total": int(work_item_total),
            "facts_truncated": (
                len(events) >= 50
                or int(work_item_total) > len(work_items)
                or len(open_loops) >= 50
            ),
        }
        return {
            "node_id": matter_id,
            "selected_locale": locale,
            "regions": (
                {
                    "region_id": "summary_current_state",
                    "content": summary_region,
                },
                {
                    "region_id": "files_and_information",
                    "content": flat_files,
                },
            ),
            "summary_current_state": summary_region,
            "files_and_information": flat_files,
            "recursive_navigation_allowed": False,
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
        if projection is None or not self._visible_projection(projection):
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


__all__ = [
    "FILES_INFORMATION_LIMIT",
    "ObjectBrowserProjection",
    "PRIMARY_DETAIL_SECTIONS",
    "logical_event_key_for_payload",
    "project_matter_only_graph",
]
