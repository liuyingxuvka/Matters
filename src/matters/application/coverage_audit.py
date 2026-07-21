"""Bounded one-scan coverage audit over occurrence and canonical Matter rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping

from matters.application.coverage_ledger import (
    ObjectCoverageLedger,
    STAGE_ORDER,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


@dataclass(frozen=True)
class StageAuditGap:
    object_id: str
    object_kind: str
    first_gap_stage: str
    status: str
    owner_id: str
    failure_class: str = ""


@dataclass(frozen=True)
class StageAuditObject:
    object_id: str
    object_kind: str
    active: bool
    terminal: bool
    ui_ready: bool
    first_gap_stage: str
    stages: Mapping[str, str]


@dataclass(frozen=True)
class StageAuditSurface:
    surface_id: str
    subject_id: str
    subject_kind: str
    status: str
    owner_id: str
    failure_class: str
    input_fingerprint: str
    freshness: str
    ui_ready: bool
    updated_at: str


@dataclass(frozen=True)
class StageAuditSnapshot:
    run_identity: str
    ledger_revision: int
    total_objects: int
    indexed_objects: int
    unindexed_objects: int
    audit_index_status: str
    occurrence_objects: int
    matter_objects: int
    ui_ready_objects: int
    blocked_objects: int
    coverage_contract: Mapping[str, Any]
    stage_counts: Mapping[str, Mapping[str, int]]
    gaps: tuple[StageAuditGap, ...]
    objects: tuple[StageAuditObject, ...]
    surface_order: tuple[str, ...]
    surface_status_counts: Mapping[str, int]
    total_surfaces: int
    current_surfaces: int
    gap_surfaces: int
    surface_gaps: tuple[StageAuditGap, ...]
    surfaces: tuple[StageAuditSurface, ...]
    surface_applicability: Mapping[str, tuple[str, ...]]
    offset: int
    limit: int
    total_matching: int
    generated_at: str


@dataclass(frozen=True)
class CoverageSurfaceAuditSnapshot:
    run_identity: str
    ledger_revision: int
    coverage_contract: Mapping[str, Any]
    surface_order: tuple[str, ...]
    surface_status_counts: Mapping[str, int]
    total_surfaces: int
    current_surfaces: int
    gap_surfaces: int
    surface_gaps: tuple[StageAuditGap, ...]
    surfaces: tuple[StageAuditSurface, ...]
    surface_applicability: Mapping[str, tuple[str, ...]]
    offset: int
    limit: int
    total_matching: int
    generated_at: str


@dataclass
class CoverageAuditService:
    ledger: ObjectCoverageLedger

    @staticmethod
    def _surface_applicability() -> Mapping[str, tuple[str, ...]]:
        return {
            "system": (
                "inventory_freshness",
                "source_group_projection",
                "raw_cleanup",
                "staging_cleanup",
            ),
            "root_matter": (
                "situation_graph",
                "node_quick_view",
                "world_model",
            ),
            "child_matter": (),
            "occurrence": (),
        }

    def surface_audit(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        surface_id: str = "",
        surface_status: str = "",
        owner_id: str = "",
        failure_class: str = "",
        freshness: str = "",
        ui_ready: bool | None = None,
    ) -> CoverageSurfaceAuditSnapshot:
        """Read the UI surface index without rescanning the object universe."""

        query = self.ledger.store.coverage_surface_audit_page(
            offset=offset,
            limit=limit,
            surface_id=surface_id,
            status=surface_status,
            owner_id=owner_id,
            failure_class=failure_class,
            freshness=freshness,
            ui_ready=ui_ready,
        )
        summary = self.ledger.store.current(
            "object_coverage_summary",
            "current",
        )
        ledger_revision = int((summary or {}).get("ledger_revision", 0))
        surfaces = tuple(
            StageAuditSurface(**dict(item)) for item in query["rows"]
        )
        surface_gaps = tuple(
            StageAuditGap(
                object_id=item.subject_id,
                object_kind=item.subject_kind,
                first_gap_stage=item.surface_id,
                status=item.status,
                owner_id=item.owner_id,
                failure_class=item.failure_class,
            )
            for item in surfaces
            if item.status not in {"current", "not_applicable", "no_finding"}
        )
        total_surfaces = int(query["total_surface_count"])
        current_surfaces = int(query["current_surface_count"])
        gap_surfaces = int(query["gap_surface_count"])
        contract_status = (
            "current"
            if total_surfaces and gap_surfaces == 0
            else "partial"
        )
        run_identity = _fingerprint(
            {
                "ledger_revision": ledger_revision,
                "surface_order": query["surface_order"],
                "surface_status_counts": query["status_counts"],
                "filters": {
                    "surface_id": surface_id,
                    "surface_status": surface_status,
                    "owner_id": owner_id,
                    "failure_class": failure_class,
                    "freshness": freshness,
                    "ui_ready": ui_ready,
                },
            }
        )
        return CoverageSurfaceAuditSnapshot(
            run_identity=run_identity,
            ledger_revision=ledger_revision,
            coverage_contract={
                "surface_status": contract_status,
                "required_surface_count": total_surfaces,
                "current_surface_count": current_surfaces,
                "gap_surface_count": gap_surfaces,
                "surface_status_counts": dict(query["status_counts"]),
            },
            surface_order=tuple(query["surface_order"]),
            surface_status_counts=dict(query["status_counts"]),
            total_surfaces=total_surfaces,
            current_surfaces=current_surfaces,
            gap_surfaces=gap_surfaces,
            surface_gaps=surface_gaps,
            surfaces=surfaces,
            surface_applicability=self._surface_applicability(),
            offset=offset,
            limit=limit,
            total_matching=int(query["total_matching"]),
            generated_at=_utc_now(),
        )

    def audit(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        object_kind: str = "",
        surface_id: str = "",
        surface_status: str = "",
        owner_id: str = "",
        failure_class: str = "",
        freshness: str = "",
        ui_ready: bool | None = None,
    ) -> StageAuditSnapshot:
        if offset < 0 or limit < 1 or limit > 200:
            raise ValueError("coverage audit page bounds are invalid")
        if object_kind not in {"", "occurrence", "matter"}:
            raise ValueError("coverage audit object kind is invalid")
        query = self.ledger.store.coverage_audit_page(
            offset=offset,
            limit=limit,
            object_kind=object_kind,
            stage_order=STAGE_ORDER,
        )
        surface_query = self.ledger.store.coverage_surface_audit_page(
            offset=offset,
            limit=limit,
            surface_id=surface_id,
            status=surface_status,
            owner_id=owner_id,
            failure_class=failure_class,
            freshness=freshness,
            ui_ready=ui_ready,
        )
        stage_counts: dict[str, dict[str, int]] = {
            stage_id: {
                "current": 0,
                "pending": 0,
                "stale": 0,
                "blocked": 0,
                "uncertain": 0,
                "not_applicable": 0,
                "no_finding": 0,
                "missing": 0,
                "unindexed": 0,
            }
            for stage_id in STAGE_ORDER
        }
        for stage_id, counts in query["stage_counts"].items():
            for status, count in counts.items():
                stage_counts[stage_id].setdefault(status, 0)
                stage_counts[stage_id][status] = int(count)
        page_gaps: list[StageAuditGap] = []
        object_rows: list[StageAuditObject] = []
        for page_row in query["rows"]:
            index = dict(page_row["index"])
            object_id = str(index["object_id"])
            provider = str(index["provider"])
            kind = (
                "unindexed"
                if not provider
                else ("matter" if provider == "matters" else "occurrence")
            )
            index_current = bool(index.get("index_current", False))
            if index_current:
                stage_statuses = {
                    stage_id: "not_applicable"
                    for stage_id in STAGE_ORDER
                }
                stage_statuses.update(
                    {
                        str(stage_id): str(status)
                        for stage_id, status in dict(
                            page_row.get("stages", {})
                        ).items()
                    }
                )
                first_gap = str(index.get("first_gap_stage", ""))
                if first_gap:
                    status = str(
                        index.get("first_gap_status", "missing")
                    )
                    page_gaps.append(
                        StageAuditGap(
                            object_id=object_id,
                            object_kind=kind,
                            first_gap_stage=first_gap,
                            status=status,
                            owner_id=(
                                str(index.get("first_gap_owner_id", ""))
                                or self.ledger._stage_owner(first_gap)
                            ),
                            failure_class=(
                                str(
                                    index.get(
                                        "first_gap_failure_class",
                                        "",
                                    )
                                )
                                or (
                                    "missing_stage"
                                    if status == "missing"
                                    else ""
                                )
                            ),
                        )
                    )
            else:
                stage_statuses = {
                    stage_id: "unindexed"
                    for stage_id in STAGE_ORDER
                }
                first_gap = "coverage_first_gap_index"
                page_gaps.append(
                    StageAuditGap(
                        object_id=object_id,
                        object_kind=kind,
                        first_gap_stage=first_gap,
                        status="stale",
                        owner_id="M0_matters_end_to_end_authority",
                        failure_class="coverage_first_gap_index_stale",
                    )
                )
            object_rows.append(
                StageAuditObject(
                    object_id=object_id,
                    object_kind=kind,
                    active=True,
                    terminal=bool(index.get("terminal", False)),
                    ui_ready=bool(index.get("ui_ready", False)),
                    first_gap_stage=first_gap,
                    stages=stage_statuses,
                )
            )
        coverage_contract = self.ledger.store.coverage_contract_status()
        summary = self.ledger.current_summary(
            coverage_contract=coverage_contract
        )
        ledger_revision = summary.ledger_revision if summary is not None else 0
        run_identity = _fingerprint(
            {
                "ledger_revision": ledger_revision,
                "audit_index": query["revision_fingerprint"],
                "stage_order": STAGE_ORDER,
                "surface_order": surface_query["surface_order"],
                "surface_status_counts": surface_query["status_counts"],
            }
        )
        surfaces = tuple(
            StageAuditSurface(**dict(item)) for item in surface_query["rows"]
        )
        surface_gaps = tuple(
            StageAuditGap(
                object_id=item.subject_id,
                object_kind=item.subject_kind,
                first_gap_stage=item.surface_id,
                status=item.status,
                owner_id=item.owner_id,
                failure_class=item.failure_class,
            )
            for item in surfaces
            if item.status not in {"current", "not_applicable", "no_finding"}
        )
        return StageAuditSnapshot(
            run_identity=run_identity,
            ledger_revision=ledger_revision,
            total_objects=int(query["total_objects"]),
            indexed_objects=int(query["indexed_objects"]),
            unindexed_objects=int(query["unindexed_objects"]),
            audit_index_status=str(query["index_status"]),
            occurrence_objects=int(query["occurrence_objects"]),
            matter_objects=int(query["matter_objects"]),
            ui_ready_objects=int(query["ui_ready_objects"]),
            blocked_objects=int(query["blocked_objects"]),
            coverage_contract=coverage_contract,
            stage_counts=stage_counts,
            gaps=tuple(page_gaps),
            objects=tuple(object_rows),
            surface_order=tuple(surface_query["surface_order"]),
            surface_status_counts=dict(surface_query["status_counts"]),
            total_surfaces=int(surface_query["total_surface_count"]),
            current_surfaces=int(surface_query["current_surface_count"]),
            gap_surfaces=int(surface_query["gap_surface_count"]),
            surface_gaps=surface_gaps,
            surfaces=surfaces,
            surface_applicability=self._surface_applicability(),
            offset=offset,
            limit=limit,
            total_matching=int(query["total_objects"]),
            generated_at=_utc_now(),
        )


__all__ = [
    "CoverageSurfaceAuditSnapshot",
    "CoverageAuditService",
    "StageAuditGap",
    "StageAuditObject",
    "StageAuditSurface",
    "StageAuditSnapshot",
]
