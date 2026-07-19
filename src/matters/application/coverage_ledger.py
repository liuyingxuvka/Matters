"""M0 ObjectCoverageLedger: current pointers across existing C1-C12 owners."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from matters.infrastructure.sqlite.store import SQLiteStore


STAGE_ORDER = (
    "authorization",
    "inventory",
    "source_version",
    "extraction",
    "evidence",
    "analysis",
    "owner_dispatch",
    "matter",
    "localization",
    "visual",
    "ui_projection",
)
TERMINAL_STAGE_STATUSES = frozenset(
    {"current", "not_applicable", "no_finding", "uncertain", "blocked"}
)
OPEN_STAGE_STATUSES = frozenset({"pending", "stale"})
STAGE_STATUSES = TERMINAL_STAGE_STATUSES | OPEN_STAGE_STATUSES


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CoverageStagePointer:
    stage_id: str
    status: str
    owner_id: str
    input_fingerprint: str
    output_ref: str = ""
    failure_class: str = ""
    updated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if self.stage_id not in STAGE_ORDER:
            raise ValueError(f"unsupported coverage stage: {self.stage_id}")
        if self.status not in STAGE_STATUSES:
            raise ValueError(f"unsupported coverage stage status: {self.status}")
        if not self.owner_id or not self.input_fingerprint:
            raise ValueError("coverage stage owner and input fingerprint are required")

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL_STAGE_STATUSES


@dataclass(frozen=True)
class ObjectCoverageRow:
    object_id: str
    provider: str
    object_type: str
    scope_id: str
    inventory_revision: int
    disposition: str
    required_stages: tuple[str, ...]
    stages: Mapping[str, CoverageStagePointer]
    matter_ids: tuple[str, ...] = ()
    revision: int = 1
    retry_count: int = 0
    next_retry_at: str = ""
    updated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.object_id or not self.provider or self.inventory_revision < 1:
            raise ValueError("object identity, provider, and inventory revision are required")
        unknown = set(self.required_stages) - set(STAGE_ORDER)
        if unknown:
            raise ValueError("unknown required coverage stages")
        normalized = {
            str(stage_id): (
                pointer
                if isinstance(pointer, CoverageStagePointer)
                else CoverageStagePointer(**dict(pointer))
            )
            for stage_id, pointer in self.stages.items()
        }
        object.__setattr__(self, "required_stages", tuple(self.required_stages))
        object.__setattr__(self, "stages", normalized)
        object.__setattr__(self, "matter_ids", tuple(self.matter_ids))

    @property
    def terminal(self) -> bool:
        return all(
            (pointer := self.stages.get(stage_id)) is not None and pointer.terminal
            for stage_id in self.required_stages
        )

    @property
    def blocked(self) -> bool:
        return any(
            pointer.status == "blocked"
            for pointer in self.stages.values()
        )

    @property
    def ui_ready(self) -> bool:
        if not self.matter_ids:
            return self.terminal
        return all(
            (pointer := self.stages.get(stage_id)) is not None
            and pointer.status in {"current", "uncertain"}
            for stage_id in ("matter", "localization", "visual", "ui_projection")
        )

    @property
    def next_stage(self) -> str:
        for stage_id in self.required_stages:
            pointer = self.stages.get(stage_id)
            if pointer is None or not pointer.terminal:
                return stage_id
        return ""

    @property
    def terminal_index(self) -> Mapping[str, str]:
        return {
            stage_id: self.stages[stage_id].status
            for stage_id in self.required_stages
            if stage_id in self.stages and self.stages[stage_id].terminal
        }


@dataclass(frozen=True)
class CoverageLedgerSummary:
    ledger_revision: int
    registered_object_count: int
    terminal_object_count: int
    ui_ready_object_count: int
    blocked_object_count: int
    pending_object_count: int
    next_stage_counts: Mapping[str, int]
    worker_health: str
    worker_checkpoint: str
    coverage_status: str
    updated_at: str = field(default_factory=_utc_now)


@dataclass
class ObjectCoverageLedger:
    """M0-owned cross-stage pointers; child facts remain with their owners."""

    store: "SQLiteStore"

    @staticmethod
    def _row_from_payload(payload: Mapping[str, Any]) -> ObjectCoverageRow:
        return ObjectCoverageRow(
            object_id=str(payload["object_id"]),
            provider=str(payload["provider"]),
            object_type=str(payload["object_type"]),
            scope_id=str(payload["scope_id"]),
            inventory_revision=int(payload["inventory_revision"]),
            disposition=str(payload["disposition"]),
            required_stages=tuple(payload.get("required_stages", ())),
            stages={
                str(stage_id): CoverageStagePointer(**dict(pointer))
                for stage_id, pointer in dict(payload.get("stages", {})).items()
            },
            matter_ids=tuple(payload.get("matter_ids", ())),
            revision=int(payload.get("revision", 1)),
            retry_count=int(payload.get("retry_count", 0)),
            next_retry_at=str(payload.get("next_retry_at", "")),
            updated_at=str(payload.get("updated_at", "")),
        )

    def current(self, object_id: str) -> ObjectCoverageRow | None:
        payload = self.store.current("object_coverage", object_id)
        return self._row_from_payload(payload) if payload else None

    def rows(self) -> tuple[ObjectCoverageRow, ...]:
        return tuple(
            self._row_from_payload(payload)
            for payload in self.store.iter_current("object_coverage")
        )

    @staticmethod
    def required_stages(disposition: str) -> tuple[str, ...]:
        if disposition == "tracked":
            return STAGE_ORDER
        if disposition == "metadata_only":
            return (
                "authorization",
                "inventory",
                "source_version",
                "extraction",
                "evidence",
                "analysis",
                "owner_dispatch",
                "matter",
                "localization",
                "visual",
                "ui_projection",
            )
        return STAGE_ORDER

    @staticmethod
    def _pointer(
        stage_id: str,
        status: str,
        owner_id: str,
        fingerprint: str,
        *,
        output_ref: str = "",
        failure_class: str = "",
    ) -> CoverageStagePointer:
        return CoverageStagePointer(
            stage_id,
            status,
            owner_id,
            fingerprint,
            output_ref,
            failure_class,
        )

    @staticmethod
    def _not_applicable_after_disposition(
        disposition: str,
    ) -> frozenset[str]:
        if disposition in {"not_tracked", "hard_excluded", "unavailable"}:
            return frozenset(STAGE_ORDER[2:])
        if disposition == "metadata_only":
            return frozenset(
                {
                    "evidence",
                    "analysis",
                    "owner_dispatch",
                    "matter",
                    "localization",
                    "visual",
                    "ui_projection",
                }
            )
        return frozenset()

    def reconcile_inventory(
        self,
        *,
        scope_id: str,
        inventory_revision: int,
        occurrences: Iterable[Mapping[str, Any]],
        dispositions: Iterable[Mapping[str, Any]],
        refresh_summary: bool = True,
    ) -> tuple[ObjectCoverageRow, ...]:
        occurrence_rows = tuple(dict(item) for item in occurrences)
        disposition_by_id = {
            str(item["occurrence_id"]): dict(item) for item in dispositions
        }
        object_ids = tuple(
            str(item["occurrence_id"]) for item in occurrence_rows
        )
        prior_payloads = self.store.current_many(
            "object_coverage",
            object_ids,
        )
        next_revisions = self.store.next_revisions(
            "object_coverage",
            object_ids,
        )
        rows: list[ObjectCoverageRow] = []
        writes: list[tuple[str, str, int, Any]] = []
        for occurrence in occurrence_rows:
            object_id = str(occurrence["occurrence_id"])
            disposition = str(disposition_by_id[object_id]["status"])
            fingerprint = _fingerprint(
                {
                    "scope_id": scope_id,
                    "inventory_revision": inventory_revision,
                    "occurrence": occurrence,
                    "disposition": disposition_by_id[object_id],
                }
            )
            prior_payload = prior_payloads.get(object_id)
            prior = (
                self._row_from_payload(prior_payload)
                if prior_payload is not None
                else None
            )
            stages = dict(prior.stages) if prior else {}
            stages["authorization"] = self._pointer(
                "authorization",
                "current",
                "C1_authorization_coverage",
                fingerprint,
                output_ref=f"scope:{scope_id}",
            )
            stages["inventory"] = self._pointer(
                "inventory",
                "current",
                "C1_authorization_coverage",
                fingerprint,
                output_ref=f"inventory:{scope_id}:{inventory_revision}",
            )
            for stage_id in self._not_applicable_after_disposition(disposition):
                stages[stage_id] = self._pointer(
                    stage_id,
                    "not_applicable",
                    self._stage_owner(stage_id),
                    fingerprint,
                    output_ref=f"disposition:{disposition}",
                )
            if disposition == "blocked":
                for stage_id in STAGE_ORDER[2:]:
                    stages[stage_id] = self._pointer(
                        stage_id,
                        "blocked",
                        self._stage_owner(stage_id),
                        fingerprint,
                        failure_class="source_disposition_blocked",
                    )
            row = ObjectCoverageRow(
                object_id=object_id,
                provider=str(occurrence["provider"]),
                object_type=str(occurrence["object_type"]),
                scope_id=scope_id,
                inventory_revision=inventory_revision,
                disposition=disposition,
                required_stages=self.required_stages(disposition),
                stages=stages,
                matter_ids=prior.matter_ids if prior else (),
                revision=(prior.revision + 1 if prior else 1),
                retry_count=prior.retry_count if prior else 0,
                next_retry_at=prior.next_retry_at if prior else "",
            )
            payload = asdict(row)
            comparable = dict(payload)
            comparable.pop("revision", None)
            comparable.pop("updated_at", None)
            prior_comparable = dict(prior_payload or {})
            prior_comparable.pop("revision", None)
            prior_comparable.pop("updated_at", None)
            if prior_payload is not None and prior_comparable == comparable:
                rows.append(prior)
                continue
            revision = next_revisions[object_id]
            payload["revision"] = revision
            writes.append(
                ("object_coverage", object_id, revision, payload)
            )
            rows.append(self._row_from_payload(payload))
        self.store.append_many(writes)
        if refresh_summary:
            self._save_summary()
        return tuple(rows)

    @staticmethod
    def _stage_owner(stage_id: str) -> str:
        return {
            "authorization": "C1_authorization_coverage",
            "inventory": "C1_authorization_coverage",
            "source_version": "C2_source_registry",
            "extraction": "C3_evidence_qualification",
            "evidence": "C3_evidence_qualification",
            "analysis": "C11_guard_prediction",
            "owner_dispatch": "M0_matters_end_to_end_authority",
            "matter": "C6_matter_admission",
            "localization": "C12_projection_bilingual_ui",
            "visual": "C12_projection_bilingual_ui",
            "ui_projection": "C12_projection_bilingual_ui",
        }[stage_id]

    def mark_stage(
        self,
        *,
        object_id: str,
        stage_id: str,
        status: str,
        input_fingerprint: str,
        output_ref: str = "",
        failure_class: str = "",
        matter_ids: tuple[str, ...] | None = None,
        refresh_summary: bool = True,
    ) -> ObjectCoverageRow:
        prior = self.current(object_id)
        if prior is None:
            raise KeyError(f"unregistered coverage object: {object_id}")
        stages = dict(prior.stages)
        stages[stage_id] = self._pointer(
            stage_id,
            status,
            self._stage_owner(stage_id),
            input_fingerprint,
            output_ref=output_ref,
            failure_class=failure_class,
        )
        row = ObjectCoverageRow(
            object_id=prior.object_id,
            provider=prior.provider,
            object_type=prior.object_type,
            scope_id=prior.scope_id,
            inventory_revision=prior.inventory_revision,
            disposition=prior.disposition,
            required_stages=prior.required_stages,
            stages=stages,
            matter_ids=prior.matter_ids if matter_ids is None else matter_ids,
            revision=prior.revision + 1,
            retry_count=(
                prior.retry_count + 1
                if status in {"blocked", "stale"}
                else prior.retry_count
            ),
            next_retry_at=prior.next_retry_at,
        )
        persisted = self._persist_if_changed(row)
        if refresh_summary:
            self._save_summary()
        return persisted

    def mark_stale(
        self,
        *,
        object_id: str,
        stage_ids: Iterable[str],
        input_fingerprint: str,
        refresh_summary: bool = True,
    ) -> ObjectCoverageRow:
        row = self.current(object_id)
        if row is None:
            raise KeyError(f"unregistered coverage object: {object_id}")
        for stage_id in stage_ids:
            row = self.mark_stage(
                object_id=object_id,
                stage_id=stage_id,
                status="stale",
                input_fingerprint=input_fingerprint,
                refresh_summary=False,
            )
        if refresh_summary:
            self._save_summary()
        return row

    def mark_stale_many(
        self,
        *,
        stage_ids_by_object: Mapping[str, Iterable[str]],
        input_fingerprint: str,
        refresh_summary: bool = True,
    ) -> tuple[ObjectCoverageRow, ...]:
        """Mark a reconciliation batch stale in one atomic append."""

        normalized = {
            str(object_id): tuple(stage_ids)
            for object_id, stage_ids in stage_ids_by_object.items()
        }
        object_ids = tuple(
            sorted(
                object_id
                for object_id, stage_ids in normalized.items()
                if object_id and stage_ids
            )
        )
        prior_payloads = self.store.current_many(
            "object_coverage",
            object_ids,
        )
        next_revisions = self.store.next_revisions(
            "object_coverage",
            object_ids,
        )
        rows: list[ObjectCoverageRow] = []
        writes: list[tuple[str, str, int, Any]] = []
        for object_id in object_ids:
            prior_payload = prior_payloads.get(object_id)
            if prior_payload is None:
                continue
            prior = self._row_from_payload(prior_payload)
            stages = dict(prior.stages)
            changed = False
            for stage_id in normalized[object_id]:
                pointer = stages.get(stage_id)
                if pointer is not None and pointer.status == "not_applicable":
                    continue
                stages[stage_id] = self._pointer(
                    stage_id,
                    "stale",
                    self._stage_owner(stage_id),
                    input_fingerprint,
                )
                changed = True
            if not changed:
                rows.append(prior)
                continue
            revision = next_revisions[object_id]
            row = ObjectCoverageRow(
                object_id=prior.object_id,
                provider=prior.provider,
                object_type=prior.object_type,
                scope_id=prior.scope_id,
                inventory_revision=prior.inventory_revision,
                disposition=prior.disposition,
                required_stages=prior.required_stages,
                stages=stages,
                matter_ids=prior.matter_ids,
                revision=revision,
                retry_count=prior.retry_count + 1,
                next_retry_at=prior.next_retry_at,
            )
            payload = asdict(row)
            writes.append(
                ("object_coverage", object_id, revision, payload)
            )
            rows.append(row)
        self.store.append_many(writes)
        if refresh_summary:
            self._save_summary()
        return tuple(rows)

    def next_work(self, *, limit: int = 100) -> tuple[tuple[str, str], ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        candidates = (
            (row.object_id, row.next_stage)
            for row in self.rows()
            if row.next_stage
        )
        return tuple(sorted(candidates))[:limit]

    def summary(
        self,
        *,
        worker_health: str = "idle",
        worker_checkpoint: str = "",
    ) -> CoverageLedgerSummary:
        rows = self.rows()
        next_counts: dict[str, int] = {}
        for row in rows:
            if row.next_stage:
                next_counts[row.next_stage] = next_counts.get(row.next_stage, 0) + 1
        terminal = sum(row.terminal for row in rows)
        ui_ready = sum(row.ui_ready for row in rows)
        blocked = sum(row.blocked for row in rows)
        pending = len(rows) - terminal
        current = self.store.current("object_coverage_summary", "current")
        return CoverageLedgerSummary(
            ledger_revision=int(current.get("ledger_revision", 0)) if current else 0,
            registered_object_count=len(rows),
            terminal_object_count=terminal,
            ui_ready_object_count=ui_ready,
            blocked_object_count=blocked,
            pending_object_count=pending,
            next_stage_counts=dict(sorted(next_counts.items())),
            worker_health=worker_health,
            worker_checkpoint=worker_checkpoint,
            coverage_status=(
                "complete"
                if rows and terminal == len(rows)
                else ("empty" if not rows else "partial")
            ),
        )

    def _save_summary(
        self,
        *,
        worker_health: str = "idle",
        worker_checkpoint: str = "",
    ) -> CoverageLedgerSummary:
        summary = self.summary(
            worker_health=worker_health,
            worker_checkpoint=worker_checkpoint,
        )
        prior = self.store.current("object_coverage_summary", "current")
        comparable = asdict(summary)
        comparable.pop("ledger_revision", None)
        comparable.pop("updated_at", None)
        prior_comparable = dict(prior or {})
        prior_comparable.pop("ledger_revision", None)
        prior_comparable.pop("updated_at", None)
        if prior is not None and prior_comparable == comparable:
            return CoverageLedgerSummary(**dict(prior))
        next_revision = int(prior.get("ledger_revision", 0)) + 1 if prior else 1
        summary = CoverageLedgerSummary(
            **{
                **asdict(summary),
                "ledger_revision": next_revision,
            }
        )
        self.store.append(
            "object_coverage_summary",
            "current",
            self.store.next_revision("object_coverage_summary", "current"),
            asdict(summary),
        )
        return summary

    def record_worker_state(
        self,
        *,
        worker_health: str,
        worker_checkpoint: str,
    ) -> CoverageLedgerSummary:
        return self._save_summary(
            worker_health=worker_health,
            worker_checkpoint=worker_checkpoint,
        )

    def refresh_summary(self) -> CoverageLedgerSummary:
        """Persist one summary after a caller completes a batch of row writes."""

        return self._save_summary()

    def _persist_if_changed(self, row: ObjectCoverageRow) -> ObjectCoverageRow:
        prior_payload = self.store.current("object_coverage", row.object_id)
        payload = asdict(row)
        comparable = dict(payload)
        comparable.pop("revision", None)
        comparable.pop("updated_at", None)
        prior_comparable = dict(prior_payload or {})
        prior_comparable.pop("revision", None)
        prior_comparable.pop("updated_at", None)
        if prior_payload is not None and prior_comparable == comparable:
            return self._row_from_payload(prior_payload)
        revision = self.store.next_revision("object_coverage", row.object_id)
        payload["revision"] = revision
        self.store.append(
            "object_coverage",
            row.object_id,
            revision,
            payload,
        )
        payload["revision"] = revision
        return self._row_from_payload(payload)


__all__ = [
    "CoverageLedgerSummary",
    "CoverageStagePointer",
    "ObjectCoverageLedger",
    "ObjectCoverageRow",
    "OPEN_STAGE_STATUSES",
    "STAGE_ORDER",
    "STAGE_STATUSES",
    "TERMINAL_STAGE_STATUSES",
]
