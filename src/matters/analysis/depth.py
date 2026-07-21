"""Occurrence and aggregate-Matter semantic-depth accounting."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from matters.infrastructure.sqlite.store import SQLiteStore


DEPTH_STATES = frozenset(
    {"not_assessed", "partial", "sufficient", "blocked", "stale"}
)
SUFFICIENCY_CRITERIA = (
    "coverage_terminal",
    "extraction_current",
    "analysis_terminal",
    "evidence_anchored",
    "owner_dispatch_terminal",
)
MATTER_SUFFICIENCY_CRITERIA = (
    "canonical_admission_current",
    "source_depth_current",
    "evidence_anchored",
    "owner_results_terminal",
    "bilingual_projection_current",
    "activity_current",
    "hierarchy_current",
)
MATTER_HIERARCHY_DEPTH_STAGES = (
    "hierarchy_decision",
    "containment_current",
    "child_state_current",
    "ancestor_rollup_current",
)
MATTER_OWNER_TERMINAL_STATUSES = frozenset(
    {"current", "no_finding", "not_applicable", "uncertain"}
)


def _fingerprint(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _parse_source_revision_ref(value: object) -> tuple[str, int] | None:
    """Parse the direct-current ``source:<id>:vN`` reference contract."""

    reference = str(value).strip()
    source_id, marker, version_text = reference.rpartition(":v")
    if (
        marker != ":v"
        or not source_id
        or not version_text.isdigit()
        or int(version_text) < 1
        or reference != f"{source_id}:v{int(version_text)}"
    ):
        return None
    return source_id, int(version_text)


@dataclass(frozen=True)
class SemanticDepth:
    occurrence_id: str
    inventory_revision: int
    state: str
    satisfied: tuple[str, ...]
    missing: tuple[str, ...]
    stale_dependencies: tuple[str, ...] = ()
    blocker_class: str = ""
    assessment_kind: str = "occurrence"
    dependency_fingerprint: str = ""
    related_matter_count: int = 0
    source_count: int = 0
    evidence_count: int = 0
    owner_result_count: int = 0

    def __post_init__(self) -> None:
        if self.state not in DEPTH_STATES:
            raise ValueError(f"unsupported semantic depth: {self.state}")
        if self.assessment_kind not in {"occurrence", "matter"}:
            raise ValueError("unsupported semantic depth assessment kind")
        if min(
            self.related_matter_count,
            self.source_count,
            self.evidence_count,
            self.owner_result_count,
        ) < 0:
            raise ValueError("semantic depth counts cannot be negative")


@dataclass
class SemanticDepthOwner:
    store: "SQLiteStore | None" = None
    result_sink: Callable[[tuple[SemanticDepth, ...]], None] | None = None

    def assess(
        self,
        *,
        occurrence_id: str,
        inventory_revision: int,
        criteria: Mapping[str, bool],
        blocked_by: str = "",
        stale_dependencies: tuple[str, ...] = (),
    ) -> SemanticDepth:
        satisfied = tuple(
            criterion
            for criterion in SUFFICIENCY_CRITERIA
            if bool(criteria.get(criterion))
        )
        missing = tuple(
            criterion
            for criterion in SUFFICIENCY_CRITERIA
            if criterion not in satisfied
        )
        if blocked_by:
            state = "blocked"
        elif stale_dependencies:
            state = "stale"
        elif not any(criteria.values()):
            state = "not_assessed"
        elif not missing:
            state = "sufficient"
        else:
            state = "partial"
        depth = SemanticDepth(
            occurrence_id=occurrence_id,
            inventory_revision=inventory_revision,
            state=state,
            satisfied=satisfied,
            missing=missing,
            stale_dependencies=stale_dependencies,
            blocker_class=blocked_by,
        )
        if self.store is not None:
            self.store.append(
                "semantic_depth",
                occurrence_id,
                self.store.next_revision("semantic_depth", occurrence_id),
                asdict(depth),
            )
        if self.result_sink is not None:
            self.result_sink((depth,))
        return depth

    def mark_stale(
        self,
        *,
        occurrence_id: str,
        inventory_revision: int,
        dependencies: tuple[str, ...],
    ) -> SemanticDepth:
        return self.assess(
            occurrence_id=occurrence_id,
            inventory_revision=inventory_revision,
            criteria={},
            stale_dependencies=dependencies,
        )

    def mark_stale_many(
        self,
        *,
        inventory_revision: int,
        dependencies_by_occurrence: Mapping[str, tuple[str, ...]],
    ) -> tuple[SemanticDepth, ...]:
        """Persist one stale-depth batch without per-occurrence transactions."""

        rows = tuple(
            SemanticDepth(
                occurrence_id=occurrence_id,
                inventory_revision=inventory_revision,
                state="stale",
                satisfied=(),
                missing=SUFFICIENCY_CRITERIA,
                stale_dependencies=tuple(dependencies),
            )
            for occurrence_id, dependencies in sorted(
                dependencies_by_occurrence.items()
            )
        )
        if self.store is not None and rows:
            revisions = self.store.next_revisions(
                "semantic_depth",
                (item.occurrence_id for item in rows),
            )
            self.store.append_many(
                (
                    "semantic_depth",
                    item.occurrence_id,
                    revisions[item.occurrence_id],
                    asdict(item),
                )
                for item in rows
            )
        if rows and self.result_sink is not None:
            self.result_sink(rows)
        return rows


@dataclass
class MatterSemanticDepthOwner:
    """Assess one Matter from exact owner results, including descendants.

    Matter rows deliberately mark occurrence-only stages ``not_applicable``.
    Consequently this owner never calls :class:`SemanticDepthOwner` and never
    treats those statuses as Matter-level semantic evidence.
    """

    store: "SQLiteStore"
    result_sink: Callable[[tuple[SemanticDepth, ...]], None] | None = None

    @staticmethod
    def _canonical_admission(
        matter_id: str,
        payload: Mapping[str, Any] | None,
    ) -> bool:
        matter = payload.get("matter") if payload is not None else None
        return bool(
            payload is not None
            and str(payload.get("status", "")) == "admitted"
            and isinstance(matter, Mapping)
            and str(matter.get("matter_id", "")) == matter_id
            and bool(matter.get("admitted", True))
        )

    @staticmethod
    def _bilingual_projection_current(
        matter_id: str,
        payload: Mapping[str, Any] | None,
    ) -> bool:
        if payload is None or str(payload.get("matter_id", "")) != matter_id:
            return False
        semantic_revision = str(payload.get("semantic_revision", ""))
        locale_revisions = payload.get("locale_revisions")
        localized_values = payload.get("localized_values")
        localized_rationale = payload.get("localized_rationale")
        if not all(
            isinstance(item, Mapping)
            for item in (
                locale_revisions,
                localized_values,
                localized_rationale,
            )
        ):
            return False
        return bool(
            semantic_revision
            and str(payload.get("equivalence_status", "")) == "equivalent"
            and all(
                str(locale_revisions.get(locale, ""))
                == semantic_revision
                and str(localized_values.get(locale, "")).strip()
                and str(localized_rationale.get(locale, "")).strip()
                for locale in ("en", "zh-CN")
            )
        )

    @staticmethod
    def _activity_current(
        matter_id: str,
        payload: Mapping[str, Any] | None,
    ) -> bool:
        localized_summary = (
            payload.get("localized_summary") if payload is not None else None
        )
        return bool(
            payload is not None
            and str(payload.get("matter_id", "")) == matter_id
            and isinstance(localized_summary, Mapping)
            and all(
                str(localized_summary.get(locale, "")).strip()
                for locale in ("en", "zh-CN")
            )
            and str(payload.get("material_clue_id", ""))
            and str(payload.get("semantic_revision", ""))
            and str(payload.get("material_clue_revision", ""))
            and str(payload.get("summary_revision", ""))
            and str(payload.get("activity_order_revision", ""))
            and bool(tuple(payload.get("evidence_ids", ())))
        )

    @staticmethod
    def _hierarchy_current(
        payload: Mapping[str, Any] | None,
    ) -> bool:
        stages = payload.get("stages") if payload is not None else None
        return bool(
            payload is not None
            and isinstance(stages, Mapping)
            and all(
                str(stages.get(stage_id, "")) == "current"
                for stage_id in MATTER_HIERARCHY_DEPTH_STAGES
            )
        )

    def _descendants(
        self,
        matter_id: str,
        *,
        max_descendants: int,
    ) -> tuple[tuple[str, ...], int]:
        descendants: list[str] = []
        total = 0
        offset = 0
        while offset < max_descendants:
            page_limit = min(1000, max_descendants - offset)
            page, total = self.store.hierarchy_descendant_ids_page(
                matter_id,
                offset=offset,
                limit=page_limit,
                current_only=True,
            )
            descendants.extend(page)
            offset += len(page)
            if offset >= total or not page:
                break
        return tuple(dict.fromkeys(descendants)), total

    def assess(
        self,
        *,
        matter_id: str,
        inventory_revision: int,
        max_descendants: int = 1000,
        max_sources: int = 10000,
    ) -> SemanticDepth:
        if (
            not matter_id
            or inventory_revision < 1
            or max_descendants < 1
            or max_descendants > 10000
            or max_sources < 1
            or max_sources > 10000
        ):
            raise ValueError("Matter semantic-depth bounds are invalid")

        descendants, descendant_total = self._descendants(
            matter_id,
            max_descendants=max_descendants,
        )
        matter_ids = (matter_id, *descendants)
        admissions = self.store.current_many(
            "admission_decision",
            matter_ids,
        )
        canonical_by_matter = {
            current_matter_id: self._canonical_admission(
                current_matter_id,
                admissions.get(current_matter_id),
            )
            for current_matter_id in matter_ids
        }

        source_revision_refs = tuple(
            dict.fromkeys(
                str(source_ref)
                for current_matter_id in matter_ids
                for source_ref in (
                    (
                        admissions.get(current_matter_id, {})
                        .get("matter", {})
                        .get("source_ids", ())
                    )
                    if canonical_by_matter[current_matter_id]
                    else ()
                )
                if str(source_ref)
            )
        )
        sources_within_bound = len(source_revision_refs) <= max_sources
        bounded_source_refs = source_revision_refs[:max_sources]
        parsed_source_refs = {
            source_ref: _parse_source_revision_ref(source_ref)
            for source_ref in bounded_source_refs
        }
        source_ids = tuple(
            dict.fromkeys(
                parsed[0]
                for parsed in parsed_source_refs.values()
                if parsed is not None
            )
        )
        source_versions = self.store.current_many(
            "source_version",
            source_ids,
        )
        occurrence_ids_by_ref: dict[str, str] = {}
        for source_ref, parsed in parsed_source_refs.items():
            if parsed is None:
                continue
            source = source_versions.get(parsed[0])
            if source is None:
                continue
            reference = source.get("external_reference")
            if isinstance(reference, Mapping):
                occurrence_ids_by_ref[source_ref] = str(
                    reference.get("external_id", "")
                )
        occurrence_ids = tuple(
            dict.fromkeys(
                occurrence_id
                for occurrence_id in occurrence_ids_by_ref.values()
                if occurrence_id
            )
        )
        source_depths = self.store.current_many(
            "semantic_depth",
            occurrence_ids,
        )
        source_coverage = self.store.current_many(
            "object_coverage",
            occurrence_ids,
        )

        admission_evidence_ids_by_matter = {
            current_matter_id: tuple(
                dict.fromkeys(
                    str(evidence_id)
                    for evidence_id in (
                        admissions.get(current_matter_id, {})
                        .get("matter", {})
                        .get("evidence_ids", ())
                    )
                    if str(evidence_id)
                )
            )
            for current_matter_id in matter_ids
        }
        projections = self.store.current_many("projection", matter_ids)
        activities = self.store.current_many("matter_activity", matter_ids)
        evidence_ids = tuple(
            dict.fromkeys(
                evidence_id
                for current_matter_id in matter_ids
                for evidence_id in (
                    *admission_evidence_ids_by_matter[current_matter_id],
                    *tuple(
                        str(item)
                        for item in projections.get(
                            current_matter_id,
                            {},
                        ).get("evidence_ids", ())
                        if str(item)
                    ),
                    *tuple(
                        str(item)
                        for item in activities.get(
                            current_matter_id,
                            {},
                        ).get("evidence_ids", ())
                        if str(item)
                    ),
                )
                if evidence_id
            )
        )
        evidence_anchors = self.store.current_many(
            "evidence_anchor",
            evidence_ids,
        )
        hierarchy_audits = self.store.current_many(
            "matter_hierarchy_audit",
            matter_ids,
        )

        source_depth_current = (
            bool(source_revision_refs) and sources_within_bound
        )
        owner_results_terminal = (
            bool(source_revision_refs) and sources_within_bound
        )
        stale_dependencies: list[str] = []
        blockers: list[str] = []
        for source_ref in bounded_source_refs:
            parsed = parsed_source_refs[source_ref]
            if parsed is None:
                source_depth_current = False
                owner_results_terminal = False
                blockers.append(
                    f"source_revision_ref_invalid:{source_ref}"
                )
                continue
            source_id, expected_version = parsed
            source = source_versions.get(source_id)
            occurrence_id = occurrence_ids_by_ref.get(source_ref, "")
            depth = source_depths.get(occurrence_id)
            coverage = source_coverage.get(occurrence_id)
            source_version_current = bool(
                source is not None
                and not bool(source.get("tombstone", False))
                and str(source.get("source_id", "")) == source_id
                and int(source.get("version", 0)) == expected_version
            )
            if source is None:
                blockers.append(
                    f"source_revision_missing:{source_ref}"
                )
            elif not source_version_current:
                stale_dependencies.append(
                    f"source_version:{source_ref}"
                )
            if (
                not source_version_current
                or not occurrence_id
                or coverage is None
                or not bool(coverage.get("active", True))
                or str(coverage.get("provider", ""))
                != str(source.get("provider", ""))
                or depth is None
                or str(depth.get("assessment_kind", "occurrence"))
                != "occurrence"
                or str(depth.get("state", "")) != "sufficient"
                or int(depth.get("inventory_revision", 0))
                != int(coverage.get("inventory_revision", 0))
            ):
                source_depth_current = False
            if depth is not None and str(depth.get("state", "")) == "stale":
                stale_dependencies.append(
                    f"semantic_depth:{occurrence_id}"
                )
            if depth is not None and str(depth.get("state", "")) == "blocked":
                blockers.append(f"semantic_depth:{occurrence_id}")

            owner_dispatch = (
                coverage.get("stages", {}).get("owner_dispatch", {})
                if coverage is not None
                else {}
            )
            owner_status = str(owner_dispatch.get("status", ""))
            if owner_status not in MATTER_OWNER_TERMINAL_STATUSES:
                owner_results_terminal = False
            if owner_status == "stale":
                stale_dependencies.append(
                    f"owner_dispatch:{occurrence_id}"
                )
            if owner_status == "blocked":
                blockers.append(f"owner_dispatch:{occurrence_id}")

        evidence_anchored = bool(evidence_ids) and all(
            bool(admission_evidence_ids_by_matter[current_matter_id])
            for current_matter_id in matter_ids
        )
        admitted_source_revisions = {
            parsed
            for parsed in parsed_source_refs.values()
            if parsed is not None
        }
        for evidence_id in evidence_ids:
            anchor = evidence_anchors.get(evidence_id)
            if (
                anchor is None
                or not bool(anchor.get("current", True))
                or (
                    str(anchor.get("source_id", "")),
                    int(anchor.get("source_version", 0)),
                )
                not in admitted_source_revisions
            ):
                evidence_anchored = False
                stale_dependencies.append(f"evidence_anchor:{evidence_id}")

        bilingual_projection_current = all(
            self._bilingual_projection_current(
                current_matter_id,
                projections.get(current_matter_id),
            )
            for current_matter_id in matter_ids
        )
        activity_current = all(
            self._activity_current(
                current_matter_id,
                activities.get(current_matter_id),
            )
            for current_matter_id in matter_ids
        )
        hierarchy_current = all(
            self._hierarchy_current(
                hierarchy_audits.get(current_matter_id),
            )
            for current_matter_id in matter_ids
        )
        for current_matter_id in matter_ids:
            audit = hierarchy_audits.get(current_matter_id)
            stages = (
                audit.get("stages")
                if isinstance(audit, Mapping)
                else None
            )
            for stage_id in MATTER_HIERARCHY_DEPTH_STAGES:
                stage_status = (
                    str(stages.get(stage_id, ""))
                    if isinstance(stages, Mapping)
                    else ""
                )
                if stage_status == "stale":
                    stale_dependencies.append(
                        f"{stage_id}:{current_matter_id}"
                    )
                elif stage_status == "blocked":
                    blockers.append(f"{stage_id}:{current_matter_id}")

        if descendant_total > max_descendants:
            blockers.append("matter_descendant_bound_exceeded")
        if not sources_within_bound:
            blockers.append("matter_source_bound_exceeded")
        if not all(canonical_by_matter.values()):
            blockers.append("canonical_admission_missing")

        criteria = {
            "canonical_admission_current": all(
                canonical_by_matter.values()
            ),
            "source_depth_current": source_depth_current,
            "evidence_anchored": evidence_anchored,
            "owner_results_terminal": owner_results_terminal,
            "bilingual_projection_current": (
                bilingual_projection_current
            ),
            "activity_current": activity_current,
            "hierarchy_current": hierarchy_current,
        }
        satisfied = tuple(
            criterion
            for criterion in MATTER_SUFFICIENCY_CRITERIA
            if criteria[criterion]
        )
        missing = tuple(
            criterion
            for criterion in MATTER_SUFFICIENCY_CRITERIA
            if criterion not in satisfied
        )
        stale_dependencies = list(dict.fromkeys(stale_dependencies))
        blockers = list(dict.fromkeys(blockers))
        if blockers:
            state = "blocked"
        elif stale_dependencies:
            state = "stale"
        elif not missing:
            state = "sufficient"
        elif not satisfied:
            state = "not_assessed"
        else:
            state = "partial"

        dependency_fingerprint = _fingerprint(
            {
                "matter_ids": matter_ids,
                "admissions": admissions,
                "source_revision_refs": source_revision_refs,
                "parsed_source_refs": parsed_source_refs,
                "source_versions": source_versions,
                "source_depths": source_depths,
                "source_coverage": source_coverage,
                "evidence_anchors": evidence_anchors,
                "projections": projections,
                "activities": activities,
                "hierarchy_audits": hierarchy_audits,
                "criteria": criteria,
                "descendant_total": descendant_total,
            }
        )
        depth = SemanticDepth(
            occurrence_id=matter_id,
            inventory_revision=inventory_revision,
            state=state,
            satisfied=satisfied,
            missing=missing,
            stale_dependencies=tuple(stale_dependencies),
            blocker_class=",".join(blockers),
            assessment_kind="matter",
            dependency_fingerprint=dependency_fingerprint,
            related_matter_count=len(matter_ids),
            source_count=len(source_revision_refs),
            evidence_count=len(evidence_ids),
            owner_result_count=(
                len(source_depths)
                + len(projections)
                + len(activities)
                + len(hierarchy_audits)
            ),
        )
        payload = asdict(depth)
        stored = self.store.compare_current_and_append(
            "semantic_depth",
            matter_id,
            is_equivalent=lambda current: (
                current is not None
                and _fingerprint(current) == _fingerprint(payload)
            ),
            payload_factory=lambda _revision, _current: payload,
        )
        persisted = SemanticDepth(**dict(stored["payload"]))
        if (
            stored["status"] != "current"
            and self.result_sink is not None
        ):
            self.result_sink((persisted,))
        return persisted


__all__ = [
    "DEPTH_STATES",
    "MATTER_HIERARCHY_DEPTH_STAGES",
    "MATTER_OWNER_TERMINAL_STATUSES",
    "MATTER_SUFFICIENCY_CRITERIA",
    "SUFFICIENCY_CRITERIA",
    "MatterSemanticDepthOwner",
    "SemanticDepth",
    "SemanticDepthOwner",
]
