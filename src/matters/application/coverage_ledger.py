"""M0 ObjectCoverageLedger: current pointers across existing C1-C12 owners."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import sqlite3
from typing import Any, Callable, Iterable, Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from matters.infrastructure.sqlite.store import SQLiteStore


STAGE_ORDER = (
    "authorization",
    "inventory",
    "content_selection",
    "source_version",
    "extraction",
    "evidence",
    "analysis",
    "owner_dispatch",
    "matter",
    "semantic_depth",
    "hierarchy_registration",
    "hierarchy_local_validation",
    "hierarchy_global_validation",
    "hierarchy_freshness",
    "hierarchy_projection",
    "localization",
    "meaningful_clue_summary",
    "generated_hero",
    "supplemental_information",
    "ui_projection",
    "ui_reachable",
)
TERMINAL_STAGE_STATUSES = frozenset(
    {"current", "not_applicable", "no_finding", "uncertain", "blocked"}
)
OPEN_STAGE_STATUSES = frozenset({"pending", "stale"})
STAGE_STATUSES = TERMINAL_STAGE_STATUSES | OPEN_STAGE_STATUSES
SEMANTIC_DEPTH_STAGE_STATUS = {
    "not_assessed": "pending",
    "partial": "pending",
    "sufficient": "current",
    "blocked": "blocked",
    "stale": "stale",
}
HIERARCHY_OWNER_STAGE_MAP = {
    "hierarchy_registration": "hierarchy_decision",
    "hierarchy_local_validation": "containment_current",
    "hierarchy_global_validation": "child_state_current",
    "hierarchy_freshness": "ancestor_rollup_current",
    "hierarchy_projection": "hierarchy_projection_current",
}


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


def _owner_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    raise TypeError("owner result must be a mapping or dataclass")


def _combined_stage_status(statuses: Iterable[str]) -> str:
    normalized = tuple(str(status) for status in statuses)
    if not normalized:
        return "pending"
    for status in ("blocked", "stale", "pending"):
        if status in normalized:
            return status
    if "uncertain" in normalized:
        return "uncertain"
    if all(status == "not_applicable" for status in normalized):
        return "not_applicable"
    if all(status in {"current", "not_applicable"} for status in normalized):
        return "current"
    return "pending"


def bounded_stage_output_set_ref(
    owner_id: str,
    set_identity: str,
    output_ids: Iterable[str],
) -> str:
    """Return one exact, bounded pointer to an owner-held output set."""

    normalized = tuple(str(item) for item in output_ids if str(item))
    identity = str(set_identity)
    if not owner_id or not identity:
        raise ValueError("bounded output-set owner and identity are required")
    if len(identity) > 160:
        identity = _fingerprint(identity)
    digest = _fingerprint(normalized).removeprefix("sha256:")
    return (
        f"{owner_id}_set:{identity}:count:{len(normalized)}:"
        f"sha256:{digest}"
    )


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
    active: bool = True
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
        if not self.active:
            return True
        return all(
            (pointer := self.stages.get(stage_id)) is not None and pointer.terminal
            for stage_id in self.required_stages
        )

    @property
    def blocked(self) -> bool:
        if not self.active:
            return False
        return any(
            pointer.status == "blocked"
            for pointer in self.stages.values()
        )

    @property
    def ui_ready(self) -> bool:
        if not self.active or not self.matter_ids:
            return False

        def stage_is(
            stage_id: str,
            allowed_statuses: frozenset[str],
        ) -> bool:
            pointer = self.stages.get(stage_id)
            return (
                pointer is not None
                and pointer.status in allowed_statuses
            )

        current = frozenset({"current", "uncertain"})
        hierarchy = (
            current
            if self.provider == "matters"
            else current | {"not_applicable"}
        )
        hero = (
            current
            if self.object_type == "root_matter"
            else current | {"not_applicable"}
        )
        return (
            stage_is("matter", current)
            and stage_is("semantic_depth", current)
            and all(
                stage_is(stage_id, hierarchy)
                for stage_id in (
                    "hierarchy_registration",
                    "hierarchy_local_validation",
                    "hierarchy_global_validation",
                    "hierarchy_freshness",
                    "hierarchy_projection",
                )
            )
            and stage_is("localization", current)
            and stage_is("meaningful_clue_summary", current)
            and stage_is("generated_hero", hero)
            and stage_is(
                "supplemental_information",
                current | {"no_finding"},
            )
            and all(
                stage_is(stage_id, current)
                for stage_id in (
                    "ui_projection",
                    "ui_reachable",
                )
            )
        )

    @property
    def next_stage(self) -> str:
        if not self.active:
            return ""
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
    contract_version: int = 2
    inventory_status: str = "partial"
    audit_index_status: str = "partial"
    source_group_status: str = "partial"
    matter_consistency_status: str = "partial"
    audit_indexed_object_count: int = 0
    audit_unindexed_object_count: int = 0
    source_group_eligible_occurrence_count: int = 0
    source_group_indexed_occurrence_count: int = 0
    source_group_remaining_occurrence_count: int = 0
    source_group_stale_occurrence_count: int = 0
    admitted_matter_count: int = 0
    ready_matter_count: int = 0
    coverage_reasons: tuple[str, ...] = ()
    updated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "next_stage_counts",
            {
                str(stage_id): int(count)
                for stage_id, count in dict(
                    self.next_stage_counts
                ).items()
            },
        )
        object.__setattr__(
            self,
            "coverage_reasons",
            tuple(str(reason) for reason in self.coverage_reasons),
        )


@dataclass
class ObjectCoverageLedger:
    """M0-owned cross-stage pointers; child facts remain with their owners."""

    store: "SQLiteStore"
    owner_terminal_sink: Callable[[str, str], None] | None = None

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
            active=bool(payload.get("active", True)),
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
        if disposition in {"tracked", "blocked"}:
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
                "semantic_depth",
                "hierarchy_registration",
                "hierarchy_local_validation",
                "hierarchy_global_validation",
                "hierarchy_freshness",
                "hierarchy_projection",
                "localization",
                "meaningful_clue_summary",
                "generated_hero",
                "supplemental_information",
                "ui_projection",
                "ui_reachable",
            )
        # A deterministic hard disposition is itself the terminal content
        # admission decision.  Such rows remain registered and auditable, but
        # they must not be expanded through every content/model/UI stage.
        return ("authorization", "inventory")

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
                    "content_selection",
                    "evidence",
                    "analysis",
                    "owner_dispatch",
                    "matter",
                    "semantic_depth",
                    "hierarchy_registration",
                    "hierarchy_local_validation",
                    "hierarchy_global_validation",
                    "hierarchy_freshness",
                    "hierarchy_projection",
                    "localization",
                    "meaningful_clue_summary",
                    "generated_hero",
                    "supplemental_information",
                    "ui_projection",
                    "ui_reachable",
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
            stages = (
                dict(prior.stages)
                if (
                    prior is not None
                    and prior.active
                    and prior.disposition == disposition
                )
                else {}
            )
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
                active=True,
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

    def register_matters(
        self,
        *,
        matters: Iterable[Mapping[str, Any]],
        scope_id: str = "matters:canonical",
        inventory_revision: int = 1,
        refresh_summary: bool = True,
    ) -> tuple[ObjectCoverageRow, ...]:
        """Register canonical root/child Matters as first-class stage-audit objects."""

        normalized = tuple(dict(item) for item in matters)
        object_ids = tuple(str(item.get("matter_id", "")) for item in normalized)
        if any(not object_id for object_id in object_ids):
            raise ValueError("registered Matter requires matter_id")
        prior_payloads = self.store.current_many("object_coverage", object_ids)
        next_revisions = self.store.next_revisions("object_coverage", object_ids)
        writes: list[tuple[str, str, int, Any]] = []
        rows: list[ObjectCoverageRow] = []
        source_only_stages = STAGE_ORDER[:8]
        for item, matter_id in zip(normalized, object_ids):
            fingerprint = _fingerprint(
                {
                    "matter_id": matter_id,
                    "matter_kind": item.get("matter_kind", "root"),
                    "semantic_revision": item.get("semantic_revision", ""),
                    "hierarchy_revision": item.get("hierarchy_revision", ""),
                }
            )
            prior_payload = prior_payloads.get(matter_id)
            prior = (
                self._row_from_payload(prior_payload)
                if prior_payload is not None
                else None
            )
            stages = dict(prior.stages) if prior is not None else {}
            for stage_id in source_only_stages:
                stages[stage_id] = self._pointer(
                    stage_id,
                    "not_applicable",
                    self._stage_owner(stage_id),
                    fingerprint,
                    output_ref="canonical_matter",
                )
            stages["matter"] = self._pointer(
                "matter",
                "current",
                self._stage_owner("matter"),
                fingerprint,
                output_ref=f"matter:{matter_id}",
            )
            for stage_id in STAGE_ORDER[9:]:
                stages.setdefault(
                    stage_id,
                    self._pointer(
                        stage_id,
                        "pending",
                        self._stage_owner(stage_id),
                        fingerprint,
                    ),
                )
            revision = next_revisions[matter_id]
            row = ObjectCoverageRow(
                object_id=matter_id,
                provider="matters",
                object_type=str(item.get("matter_kind", "root_matter")),
                scope_id=scope_id,
                inventory_revision=max(1, int(inventory_revision)),
                disposition="tracked",
                required_stages=STAGE_ORDER,
                stages=stages,
                active=bool(item.get("active", True)),
                matter_ids=(matter_id,),
                revision=revision,
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
            writes.append(("object_coverage", matter_id, revision, payload))
            rows.append(row)
        self.store.append_many(writes)
        if refresh_summary:
            self._save_summary()
        return tuple(rows)

    def replace_matter_reference(
        self,
        *,
        source_matter_id: str,
        target_matter_id: str,
        refresh_summary: bool = True,
    ) -> tuple[ObjectCoverageRow, ...]:
        """Replace one retired Matter reference in exact current coverage rows."""

        if (
            not source_matter_id
            or not target_matter_id
            or source_matter_id == target_matter_id
        ):
            raise ValueError("distinct source and target Matter ids are required")
        payloads = self.store.current_by_json_array_members(
            "object_coverage",
            json_field="matter_ids",
            values=(source_matter_id,),
        ).get(source_matter_id, ())
        object_ids = tuple(
            str(payload["object_id"]) for payload in payloads
        )
        next_revisions = self.store.next_revisions(
            "object_coverage",
            object_ids,
        )
        rows: list[ObjectCoverageRow] = []
        writes: list[tuple[str, str, int, Any]] = []
        for payload in payloads:
            object_id = str(payload["object_id"])
            prior = self._row_from_payload(payload)
            matter_ids = tuple(
                dict.fromkeys(
                    target_matter_id
                    if item == source_matter_id
                    else item
                    for item in prior.matter_ids
                )
            )
            row = ObjectCoverageRow(
                object_id=prior.object_id,
                provider=prior.provider,
                object_type=prior.object_type,
                scope_id=prior.scope_id,
                inventory_revision=prior.inventory_revision,
                disposition=prior.disposition,
                required_stages=prior.required_stages,
                stages=prior.stages,
                active=prior.active,
                matter_ids=matter_ids,
                revision=next_revisions[object_id],
                retry_count=prior.retry_count,
                next_retry_at=prior.next_retry_at,
            )
            writes.append(
                (
                    "object_coverage",
                    object_id,
                    next_revisions[object_id],
                    asdict(row),
                )
            )
            rows.append(row)
        self.store.append_many(writes)
        if writes and refresh_summary:
            self._save_summary()
        return tuple(rows)

    def remove_matter_reference(
        self,
        *,
        matter_id: str,
        reason: str,
        refresh_summary: bool = True,
    ) -> tuple[ObjectCoverageRow, ...]:
        """Retire a rejected candidate reference while preserving source coverage."""

        normalized_id = str(matter_id).strip()
        normalized_reason = str(reason).strip()
        if not normalized_id or not normalized_reason:
            raise ValueError("Matter id and retirement reason are required")
        payloads = self.store.current_by_json_array_members(
            "object_coverage",
            json_field="matter_ids",
            values=(normalized_id,),
        ).get(normalized_id, ())
        object_ids = tuple(str(payload["object_id"]) for payload in payloads)
        next_revisions = self.store.next_revisions(
            "object_coverage",
            object_ids,
        )
        fingerprint = _fingerprint(
            {
                "matter_id": normalized_id,
                "disposition": "source_only",
                "reason": normalized_reason,
            }
        )
        rows: list[ObjectCoverageRow] = []
        writes: list[tuple[str, str, int, Any]] = []
        for payload in payloads:
            object_id = str(payload["object_id"])
            prior = self._row_from_payload(payload)
            matter_ids = tuple(
                item for item in prior.matter_ids if item != normalized_id
            )
            stages = dict(prior.stages)
            for stage_id in STAGE_ORDER[STAGE_ORDER.index("matter") :]:
                stages[stage_id] = self._pointer(
                    stage_id,
                    "not_applicable",
                    self._stage_owner(stage_id),
                    fingerprint,
                    output_ref=(
                        f"admission:{normalized_id}:source_only:"
                        f"{normalized_reason}"
                    ),
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
                active=prior.active,
                matter_ids=matter_ids,
                revision=next_revisions[object_id],
                retry_count=prior.retry_count,
                next_retry_at=prior.next_retry_at,
            )
            writes.append(
                (
                    "object_coverage",
                    object_id,
                    next_revisions[object_id],
                    asdict(row),
                )
            )
            rows.append(row)
        self.store.append_many(writes)
        if writes and refresh_summary:
            self._save_summary()
        return tuple(rows)

    def retire_objects(
        self,
        *,
        object_ids: Iterable[str],
        scope_id: str,
        inventory_revision: int,
        reason: str,
        refresh_summary: bool = True,
    ) -> tuple[ObjectCoverageRow, ...]:
        """Retire deleted or policy-pruned objects from active work and UI."""

        normalized = tuple(
            sorted(
                {
                    str(object_id)
                    for object_id in object_ids
                    if str(object_id)
                }
            )
        )
        prior_payloads = self.store.current_many(
            "object_coverage",
            normalized,
        )
        next_revisions = self.store.next_revisions(
            "object_coverage",
            normalized,
        )
        writes: list[tuple[str, str, int, Any]] = []
        rows: list[ObjectCoverageRow] = []
        for object_id in normalized:
            prior_payload = prior_payloads.get(object_id)
            if prior_payload is None:
                continue
            prior = self._row_from_payload(prior_payload)
            if not prior.active:
                rows.append(prior)
                continue
            fingerprint = _fingerprint(
                {
                    "object_id": object_id,
                    "scope_id": scope_id,
                    "inventory_revision": inventory_revision,
                    "retirement_reason": reason,
                }
            )
            stages = {
                stage_id: self._pointer(
                    stage_id,
                    "not_applicable",
                    self._stage_owner(stage_id),
                    fingerprint,
                    output_ref=f"retired:{reason}",
                )
                for stage_id in STAGE_ORDER
            }
            revision = next_revisions[object_id]
            row = ObjectCoverageRow(
                object_id=prior.object_id,
                provider=prior.provider,
                object_type=prior.object_type,
                scope_id=scope_id or prior.scope_id,
                inventory_revision=inventory_revision,
                disposition="not_tracked",
                required_stages=STAGE_ORDER,
                stages=stages,
                active=False,
                matter_ids=(),
                revision=revision,
                retry_count=prior.retry_count,
                next_retry_at="",
            )
            writes.append(
                ("object_coverage", object_id, revision, asdict(row))
            )
            rows.append(row)
        self.store.append_many(writes)
        if refresh_summary:
            self._save_summary()
        return tuple(rows)

    @staticmethod
    def _stage_owner(stage_id: str) -> str:
        return {
            "authorization": "C1_authorization_coverage",
            "inventory": "C1_authorization_coverage",
            "content_selection": "C1_authorization_coverage",
            "source_version": "C2_source_registry",
            "extraction": "C3_evidence_qualification",
            "evidence": "C3_evidence_qualification",
            "analysis": "C11_guard_prediction",
            "owner_dispatch": "M0_matters_end_to_end_authority",
            "matter": "C6_matter_admission",
            "semantic_depth": "C11_guard_prediction",
            "hierarchy_registration": "C6_matter_admission",
            "hierarchy_local_validation": "C6_matter_admission",
            "hierarchy_global_validation": "C6_matter_admission",
            "hierarchy_freshness": "C6_matter_admission",
            "hierarchy_projection": "C12_projection_bilingual_ui",
            "localization": "C12_projection_bilingual_ui",
            "meaningful_clue_summary": "C12_projection_bilingual_ui",
            "generated_hero": "C12_projection_bilingual_ui",
            "supplemental_information": "C12_projection_bilingual_ui",
            "ui_projection": "C12_projection_bilingual_ui",
            "ui_reachable": "C12_projection_bilingual_ui",
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
        if not prior.active:
            raise ValueError(f"inactive coverage object: {object_id}")
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
            active=prior.active,
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
        if (
            stage_id == "owner_dispatch"
            and status in TERMINAL_STAGE_STATUSES
            and persisted.revision != prior.revision
            and self.owner_terminal_sink is not None
        ):
            self.owner_terminal_sink(object_id, input_fingerprint)
        if refresh_summary:
            self._save_summary()
        return persisted

    def apply_content_selection_many(
        self,
        plans: Iterable[Mapping[str, Any]],
    ) -> tuple[ObjectCoverageRow, ...]:
        """Apply one bounded selection page without per-stage transactions."""

        normalized = tuple(dict(item) for item in plans)
        object_ids = tuple(str(item["occurrence_id"]) for item in normalized)
        prior_payloads = self.store.current_many("object_coverage", object_ids)
        next_revisions = self.store.next_revisions("object_coverage", object_ids)
        rows: list[ObjectCoverageRow] = []
        writes: list[tuple[str, str, int, Any]] = []
        for plan in normalized:
            object_id = str(plan["occurrence_id"])
            prior_payload = prior_payloads.get(object_id)
            if prior_payload is None:
                raise KeyError(f"unregistered coverage object: {object_id}")
            prior = self._row_from_payload(prior_payload)
            # The semantic selection decision is stable across inventory
            # snapshot counters.  Keeping that volatile revision in the stage
            # fingerprint caused a full coverage revision for every unchanged
            # occurrence after each refresh/rebase.
            fingerprint = _fingerprint(
                {
                    key: value
                    for key, value in plan.items()
                    if key != "inventory_revision"
                }
            )
            stages = dict(prior.stages)
            mode = str(plan["mode"])
            status = str(plan["status"])
            stages["content_selection"] = self._pointer(
                "content_selection",
                "current" if status == "current" else "blocked",
                self._stage_owner("content_selection"),
                fingerprint,
                output_ref=f"content_selection:{mode}",
                failure_class=(
                    "deep_continuation_unavailable" if mode == "deep" else ""
                ),
            )
            if status == "current" and mode in {"sampled", "bounded"}:
                for stage_id in STAGE_ORDER[3:]:
                    pointer = stages.get(stage_id)
                    if pointer is None or pointer.status == "not_applicable":
                        stages[stage_id] = self._pointer(
                            stage_id,
                            "pending",
                            self._stage_owner(stage_id),
                            fingerprint,
                            output_ref=f"content_selection:{mode}",
                        )
            else:
                reason = str(plan.get("reason", ""))
                for stage_id in STAGE_ORDER[3:]:
                    stages[stage_id] = self._pointer(
                        stage_id,
                        "not_applicable",
                        self._stage_owner(stage_id),
                        fingerprint,
                        output_ref=f"content_selection:{mode}:{reason}",
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
                active=prior.active,
                matter_ids=prior.matter_ids,
                revision=next_revisions[object_id],
                retry_count=prior.retry_count,
                next_retry_at=prior.next_retry_at,
            )
            payload = asdict(row)
            comparable = dict(payload)
            comparable.pop("revision", None)
            comparable.pop("updated_at", None)
            prior_comparable = dict(prior_payload)
            prior_comparable.pop("revision", None)
            prior_comparable.pop("updated_at", None)
            if comparable == prior_comparable:
                rows.append(prior)
                continue
            writes.append(("object_coverage", object_id, next_revisions[object_id], payload))
            rows.append(row)
        self.store.append_many(writes)
        return tuple(rows)

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
        if not row.active:
            return row
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
            if not prior.active:
                rows.append(prior)
                continue
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
                active=prior.active,
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

    def sync_semantic_depth_owner_results(
        self,
        results: Iterable[Any],
        *,
        refresh_summary: bool = True,
    ) -> tuple[ObjectCoverageRow, ...]:
        """Join exact current depth-owner results without inferring sufficiency."""

        by_object = {
            str(payload.get("occurrence_id", "")): payload
            for item in results
            if (payload := _owner_payload(item)).get("occurrence_id")
        }
        object_ids = tuple(sorted(by_object))
        if not object_ids:
            return ()
        prior_payloads = self.store.current_many(
            "object_coverage",
            object_ids,
        )
        writable_ids = tuple(
            object_id
            for object_id in object_ids
            if object_id in prior_payloads
            and bool(prior_payloads[object_id].get("active", True))
        )
        if not writable_ids:
            return ()
        next_revisions = self.store.next_revisions(
            "object_coverage",
            writable_ids,
        )
        rows: list[ObjectCoverageRow] = []
        writes: list[tuple[str, str, int, Any]] = []
        for object_id in writable_ids:
            prior = self._row_from_payload(prior_payloads[object_id])
            prior_depth = prior.stages.get("semantic_depth")
            if prior_depth is not None and prior_depth.status == "not_applicable":
                rows.append(prior)
                continue
            owner_result = by_object[object_id]
            owner_state = str(owner_result.get("state", ""))
            stage_status = SEMANTIC_DEPTH_STAGE_STATUS.get(
                owner_state,
                "pending",
            )
            fingerprint = _fingerprint(owner_result)
            stages = dict(prior.stages)
            stages["semantic_depth"] = self._pointer(
                "semantic_depth",
                stage_status,
                self._stage_owner("semantic_depth"),
                fingerprint,
                output_ref=(
                    f"semantic_depth:{object_id}:"
                    f"{fingerprint.removeprefix('sha256:')[:16]}"
                ),
                failure_class=(
                    str(owner_result.get("blocker_class", ""))
                    if stage_status == "blocked"
                    else ""
                ),
            )
            if stage_status != "current":
                downstream_status = (
                    "stale" if stage_status == "stale" else "pending"
                )
                for downstream_stage in ("ui_projection", "ui_reachable"):
                    pointer = stages.get(downstream_stage)
                    if pointer is not None and pointer.status == "not_applicable":
                        continue
                    stages[downstream_stage] = self._pointer(
                        downstream_stage,
                        downstream_status,
                        self._stage_owner(downstream_stage),
                        fingerprint,
                        failure_class=(
                            "semantic_depth_prerequisite_blocked"
                            if stage_status == "blocked"
                            else ""
                        ),
                    )
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
                active=prior.active,
                matter_ids=prior.matter_ids,
                revision=revision,
                retry_count=(
                    prior.retry_count + 1
                    if stage_status in {"blocked", "stale"}
                    else prior.retry_count
                ),
                next_retry_at=prior.next_retry_at,
            )
            writes.append(
                ("object_coverage", object_id, revision, asdict(row))
            )
            rows.append(row)
        self.store.append_many(writes)
        if writes and refresh_summary:
            self._save_summary()
        return tuple(rows)

    def sync_hierarchy_owner_results(
        self,
        results: Iterable[Mapping[str, Any]],
        *,
        refresh_summary: bool = True,
    ) -> tuple[ObjectCoverageRow, ...]:
        """Project exact hierarchy-owner audits into the five M0 stage pointers."""

        supplied = {
            str(payload.get("matter_id", "")): dict(payload)
            for item in results
            if (payload := _owner_payload(item)).get("matter_id")
        }
        if not supplied:
            return ()
        affected_matter_ids = frozenset(supplied)
        coverage_by_matter = self.store.current_by_json_array_members(
            "object_coverage",
            json_field="matter_ids",
            values=affected_matter_ids,
        )
        prior_payloads = {
            str(payload.get("object_id", "")): payload
            for matter_id in sorted(affected_matter_ids)
            for payload in coverage_by_matter.get(matter_id, ())
            if str(payload.get("object_id", ""))
            and bool(payload.get("active", True))
        }
        prior_rows = tuple(
            self._row_from_payload(prior_payloads[object_id])
            for object_id in sorted(prior_payloads)
        )
        if not prior_rows:
            return ()
        object_ids = tuple(row.object_id for row in prior_rows)
        next_revisions = self.store.next_revisions(
            "object_coverage",
            object_ids,
        )
        all_matter_ids = tuple(
            dict.fromkeys(
                matter_id
                for row in prior_rows
                for matter_id in row.matter_ids
                if matter_id
            )
        )
        audits = self.store.current_many(
            "matter_hierarchy_audit",
            all_matter_ids,
        )
        writes: list[tuple[str, str, int, Any]] = []
        rows: list[ObjectCoverageRow] = []
        for prior in prior_rows:
            matter_audits = {
                matter_id: audits.get(matter_id)
                for matter_id in prior.matter_ids
            }
            fingerprint = _fingerprint(matter_audits)
            output_ref = ",".join(
                (
                    f"matter_hierarchy_audit:{matter_id}:"
                    f"v{int(payload.get('revision', 0))}"
                )
                for matter_id, payload in matter_audits.items()
                if payload is not None
            )
            stages = dict(prior.stages)
            projected_statuses: list[str] = []
            for coverage_stage, owner_stage in HIERARCHY_OWNER_STAGE_MAP.items():
                statuses = tuple(
                    (
                        str(payload.get("stages", {}).get(owner_stage, "pending"))
                        if payload is not None
                        else "pending"
                    )
                    for payload in matter_audits.values()
                )
                stage_status = _combined_stage_status(statuses)
                projected_statuses.append(stage_status)
                stages[coverage_stage] = self._pointer(
                    coverage_stage,
                    stage_status,
                    self._stage_owner(coverage_stage),
                    fingerprint,
                    output_ref=output_ref,
                    failure_class=(
                        f"hierarchy_owner_stage_{stage_status}"
                        if stage_status in {"blocked", "stale"}
                        else ""
                    ),
                )
            revision = next_revisions[prior.object_id]
            row = ObjectCoverageRow(
                object_id=prior.object_id,
                provider=prior.provider,
                object_type=prior.object_type,
                scope_id=prior.scope_id,
                inventory_revision=prior.inventory_revision,
                disposition=prior.disposition,
                required_stages=prior.required_stages,
                stages=stages,
                active=prior.active,
                matter_ids=prior.matter_ids,
                revision=revision,
                retry_count=(
                    prior.retry_count + 1
                    if any(
                        status in {"blocked", "stale"}
                        for status in projected_statuses
                    )
                    else prior.retry_count
                ),
                next_retry_at=prior.next_retry_at,
            )
            writes.append(
                ("object_coverage", prior.object_id, revision, asdict(row))
            )
            rows.append(row)
        self.store.append_many(writes)
        if writes and refresh_summary:
            self._save_summary()
        return tuple(rows)

    def next_work(self, *, limit: int = 100) -> tuple[tuple[str, str], ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        return self.store.coverage_next_work(limit=limit)

    def page(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        next_stage: str = "",
    ) -> tuple[tuple[dict[str, Any], ...], int]:
        """Return one indexed diagnostic page, not the private row payloads."""

        return self.store.coverage_index_page(
            offset=offset,
            limit=limit,
            next_stage=next_stage,
        )

    def rebase_audit_index(
        self,
        *,
        after_object_id: str = "",
        limit: int = 500,
    ) -> dict[str, Any]:
        """Materialize one explicit bounded first-gap/status-index page."""

        return self.store.rebase_coverage_audit_index_page(
            after_object_id=after_object_id,
            limit=limit,
        )

    def summary(
        self,
        *,
        worker_health: str = "idle",
        worker_checkpoint: str = "",
    ) -> CoverageLedgerSummary:
        counts = self.store.coverage_summary_counts()
        contract = self.store.coverage_contract_status()
        registered = int(counts["registered_object_count"])
        terminal = int(counts["terminal_object_count"])
        current = self.store.current("object_coverage_summary", "current")
        return CoverageLedgerSummary(
            ledger_revision=int(current.get("ledger_revision", 0)) if current else 0,
            registered_object_count=registered,
            terminal_object_count=terminal,
            ui_ready_object_count=int(counts["ui_ready_object_count"]),
            blocked_object_count=int(counts["blocked_object_count"]),
            pending_object_count=int(counts["pending_object_count"]),
            next_stage_counts=dict(counts["next_stage_counts"]),
            worker_health=worker_health,
            worker_checkpoint=worker_checkpoint,
            coverage_status=str(contract["status"]),
            contract_version=int(contract["contract_version"]),
            inventory_status=str(contract["inventory_status"]),
            audit_index_status=str(contract["audit_index_status"]),
            source_group_status=str(contract["source_group_status"]),
            matter_consistency_status=str(
                contract["matter_consistency_status"]
            ),
            audit_indexed_object_count=int(
                contract["audit_indexed_object_count"]
            ),
            audit_unindexed_object_count=int(
                contract["audit_unindexed_object_count"]
            ),
            source_group_eligible_occurrence_count=int(
                contract["source_group_eligible_occurrence_count"]
            ),
            source_group_indexed_occurrence_count=int(
                contract["source_group_indexed_occurrence_count"]
            ),
            source_group_remaining_occurrence_count=int(
                contract["source_group_remaining_occurrence_count"]
            ),
            source_group_stale_occurrence_count=int(
                contract["source_group_stale_occurrence_count"]
            ),
            admitted_matter_count=int(contract["admitted_matter_count"]),
            ready_matter_count=int(contract["ready_matter_count"]),
            coverage_reasons=tuple(contract["reasons"]),
        )

    def current_summary(
        self,
        *,
        coverage_contract: Mapping[str, Any] | None = None,
    ) -> CoverageLedgerSummary | None:
        """Read the persisted aggregate without scanning every private row."""

        payload = self.store.current("object_coverage_summary", "current")
        if payload is None:
            return None
        normalized = dict(payload)
        if int(normalized.get("contract_version", 0)) != 2:
            strict = asdict(
                self.summary(
                    worker_health=str(
                        normalized.get("worker_health", "idle")
                    ),
                    worker_checkpoint=str(
                        normalized.get("worker_checkpoint", "")
                    ),
                )
            )
            strict["ledger_revision"] = int(
                normalized.get("ledger_revision", 0)
            )
            strict["updated_at"] = str(
                normalized.get("updated_at", strict["updated_at"])
            )
            return CoverageLedgerSummary(**strict)
        contract = (
            dict(coverage_contract)
            if coverage_contract is not None
            else self.store.coverage_contract_status()
        )
        normalized.update(
            {
                "coverage_status": str(contract["status"]),
                "contract_version": int(contract["contract_version"]),
                "inventory_status": str(contract["inventory_status"]),
                "audit_index_status": str(
                    contract["audit_index_status"]
                ),
                "source_group_status": str(
                    contract["source_group_status"]
                ),
                "matter_consistency_status": str(
                    contract["matter_consistency_status"]
                ),
                "audit_indexed_object_count": int(
                    contract["audit_indexed_object_count"]
                ),
                "audit_unindexed_object_count": int(
                    contract["audit_unindexed_object_count"]
                ),
                "source_group_eligible_occurrence_count": int(
                    contract["source_group_eligible_occurrence_count"]
                ),
                "source_group_indexed_occurrence_count": int(
                    contract["source_group_indexed_occurrence_count"]
                ),
                "source_group_remaining_occurrence_count": int(
                    contract["source_group_remaining_occurrence_count"]
                ),
                "source_group_stale_occurrence_count": int(
                    contract["source_group_stale_occurrence_count"]
                ),
                "admitted_matter_count": int(
                    contract["admitted_matter_count"]
                ),
                "ready_matter_count": int(
                    contract["ready_matter_count"]
                ),
                "coverage_reasons": tuple(contract["reasons"]),
            }
        )
        return CoverageLedgerSummary(**normalized)

    def _save_summary(
        self,
        *,
        worker_health: str = "idle",
        worker_checkpoint: str = "",
    ) -> CoverageLedgerSummary:
        for _attempt in range(8):
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
            next_revision = (
                int(prior.get("ledger_revision", 0)) + 1
                if prior
                else 1
            )
            summary = CoverageLedgerSummary(
                **{
                    **asdict(summary),
                    "ledger_revision": next_revision,
                }
            )
            try:
                self.store.append(
                    "object_coverage_summary",
                    "current",
                    self.store.next_revision(
                        "object_coverage_summary",
                        "current",
                    ),
                    asdict(summary),
                )
            except sqlite3.IntegrityError:
                # Another Matters process published the same aggregate between
                # our read and append. Recompute from its current revision.
                continue
            return summary
        raise RuntimeError("coverage summary publication remained contended")

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

    def rebase_legacy_evidence_pointers(
        self,
        *,
        after_object_id: str = "",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Replace retired anchor-id lists without reading source content."""

        payloads, has_more = self.store.legacy_evidence_pointer_page(
            after_object_id=after_object_id,
            limit=limit,
        )
        prepared: list[tuple[str, str, tuple[str, ...]]] = []
        for payload in payloads:
            object_id = str(payload.get("object_id", ""))
            stages = dict(payload.get("stages", {}))
            evidence = dict(stages.get("evidence", {}))
            source_version = dict(stages.get("source_version", {}))
            source_ref = str(source_version.get("output_ref", ""))
            output_ref = str(evidence.get("output_ref", ""))
            anchor_ids = tuple(
                item for item in output_ref.split(",") if item
            )
            if not object_id or not source_ref or len(anchor_ids) < 2:
                raise ValueError(
                    "legacy evidence pointer lacks exact source/set identity"
                )
            prepared.append((object_id, source_ref, anchor_ids))

        migrated = 0
        for object_id, source_ref, anchor_ids in prepared:
            bounded_ref = bounded_stage_output_set_ref(
                "evidence_anchor",
                source_ref,
                anchor_ids,
            )

            def equivalent(current: dict[str, Any] | None) -> bool:
                if current is None:
                    return False
                return (
                    str(
                        dict(
                            dict(current.get("stages", {})).get(
                                "evidence",
                                {},
                            )
                        ).get("output_ref", "")
                    )
                    == bounded_ref
                )

            def replacement(
                revision: int,
                current: dict[str, Any] | None,
            ) -> dict[str, Any]:
                if current is None:
                    raise ValueError("coverage row disappeared during rebase")
                updated = dict(current)
                stages = {
                    str(stage_id): dict(pointer)
                    for stage_id, pointer in dict(
                        current.get("stages", {})
                    ).items()
                }
                evidence = dict(stages.get("evidence", {}))
                observed_ids = tuple(
                    item
                    for item in str(
                        evidence.get("output_ref", "")
                    ).split(",")
                    if item
                )
                if observed_ids != anchor_ids:
                    raise ValueError(
                        "legacy evidence pointer changed during rebase"
                    )
                evidence["output_ref"] = bounded_ref
                evidence["updated_at"] = _utc_now()
                stages["evidence"] = evidence
                updated["stages"] = stages
                updated["revision"] = revision
                updated["updated_at"] = _utc_now()
                return updated

            result = self.store.compare_current_and_append(
                "object_coverage",
                object_id,
                is_equivalent=equivalent,
                payload_factory=replacement,
            )
            if result["status"] == "appended":
                migrated += 1
        next_cursor = (
            str(payloads[-1]["object_id"])
            if payloads and has_more
            else ""
        )
        return {
            "scanned_object_count": len(payloads),
            "migrated_object_count": migrated,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "status": "partial" if has_more else "current",
        }

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
    "bounded_stage_output_set_ref",
    "CoverageLedgerSummary",
    "CoverageStagePointer",
    "ObjectCoverageLedger",
    "ObjectCoverageRow",
    "OPEN_STAGE_STATUSES",
    "STAGE_ORDER",
    "STAGE_STATUSES",
    "TERMINAL_STAGE_STATUSES",
]
