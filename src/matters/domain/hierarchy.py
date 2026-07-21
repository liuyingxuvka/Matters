"""C6 Matter hierarchy values and invariants.

Matter containment is distinct from ordinary related-Matter links.  A WorkItem
is a bounded stateful step owned by one Matter; an Event remains a temporal
fact and a Source remains evidence provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Mapping


CONTAINMENT_ROLES = frozenset({"required", "optional", "critical"})
EDGE_FRESHNESS_STATES = frozenset({"pending", "current", "stale", "blocked"})
WORK_ITEM_KINDS = frozenset(
    {
        "action",
        "milestone",
        "decision",
        "booking",
        "application_step",
        "travel_leg",
    }
)
WORK_ITEM_STATUSES = frozenset(
    {
        "planned",
        "in_progress",
        "waiting",
        "blocked",
        "completed",
        "cancelled",
        "uncertain",
    }
)
WORK_ITEM_FRESHNESS_STATES = frozenset({"current", "stale", "blocked"})
WORK_ITEM_BASIS_MODALITIES = frozenset(
    {"observed", "reported", "planned", "ai_inferred"}
)
WORK_ITEM_BASIS_SCOPES = frozenset(
    {"", "source_record", "historical_gap", "current_phase"}
)
WORK_ITEM_TEMPORAL_ASSERTIONS = frozenset(
    {"planned", "ongoing", "occurred", "unknown"}
)
WORK_ITEM_TERMINALITY = frozenset({"confirmed", "provisional"})
HIERARCHY_CHANGE_KINDS = frozenset(
    {
        "attach",
        "batch_attach",
        "detach",
        "reparent",
        "role_change",
        "split",
        "merge",
    }
)
HIERARCHY_DISPOSITION_KINDS = frozenset(
    {"retain", "move", "copy_with_provenance", "review"}
)
HIERARCHY_MEMBER_KINDS = frozenset(
    {"source", "event", "work_item", "child", "open_loop"}
)
HIERARCHY_STAGE_IDS = (
    "hierarchy_decision",
    "containment_current",
    "child_state_current",
    "ancestor_rollup_current",
    "hierarchy_projection_current",
    "ui_reachable",
)
HIERARCHY_STAGE_STATUSES = frozenset(
    {"pending", "current", "stale", "blocked", "not_applicable", "uncertain"}
)
MAX_HIERARCHY_ATTACH_BATCH = 500
_SEMANTIC_ROLE_KEY = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _aware_time(value: str, field_name: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} requires a timezone")
    return parsed.astimezone(timezone.utc)


def _localized(values: Mapping[str, str], field_name: str) -> dict[str, str]:
    normalized = {
        str(locale): str(value).strip()
        for locale, value in values.items()
        if str(locale) and str(value).strip()
    }
    if not normalized.get("en") or not normalized.get("zh-CN"):
        raise ValueError(f"{field_name} requires non-empty en and zh-CN values")
    return normalized


def normalize_semantic_role_key(value: str) -> str:
    normalized = str(value).strip().casefold()
    if normalized and _SEMANTIC_ROLE_KEY.fullmatch(normalized) is None:
        raise ValueError(
            "semantic role key must use lowercase letters, numbers, dot, "
            "colon, underscore, or hyphen"
        )
    return normalized


@dataclass(frozen=True)
class MatterContainmentEdge:
    edge_id: str
    parent_matter_id: str
    child_matter_id: str
    role: str
    confidence: str
    rationale: str
    evidence_ids: tuple[str, ...] = ()
    ordinal: int = 0
    boundary_revision: int = 1
    freshness: str = "pending"
    active: bool = True
    updated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        evidence_ids = tuple(
            dict.fromkeys(str(item) for item in self.evidence_ids if str(item))
        )
        if not self.edge_id or not self.parent_matter_id or not self.child_matter_id:
            raise ValueError("containment edge and Matter identities are required")
        if self.parent_matter_id == self.child_matter_id:
            raise ValueError("a Matter cannot be its own parent")
        if self.role not in CONTAINMENT_ROLES:
            raise ValueError("unsupported containment role")
        if not self.confidence or not self.rationale.strip():
            raise ValueError("containment confidence and rationale are required")
        if self.active and not evidence_ids:
            raise ValueError("active containment requires current evidence")
        if self.ordinal < 0 or self.boundary_revision < 1:
            raise ValueError("containment ordinal and revision are invalid")
        if self.freshness not in EDGE_FRESHNESS_STATES:
            raise ValueError("unsupported containment freshness")
        object.__setattr__(
            self,
            "evidence_ids",
            evidence_ids,
        )


@dataclass(frozen=True)
class MatterChildAttachment:
    child_matter_id: str
    role: str
    confidence: str
    rationale: str
    evidence_ids: tuple[str, ...]
    ordinal: int = 0

    def __post_init__(self) -> None:
        evidence_ids = tuple(
            dict.fromkeys(str(item) for item in self.evidence_ids if str(item))
        )
        if not self.child_matter_id:
            raise ValueError("child Matter identity is required")
        if self.role not in CONTAINMENT_ROLES:
            raise ValueError("unsupported containment role")
        if not self.confidence or not self.rationale.strip():
            raise ValueError("containment confidence and rationale are required")
        if not evidence_ids:
            raise ValueError("active containment requires current evidence")
        if self.ordinal < 0:
            raise ValueError("containment ordinal is invalid")
        object.__setattr__(self, "evidence_ids", evidence_ids)


@dataclass(frozen=True)
class MatterWorkItem:
    item_id: str
    matter_id: str
    kind: str
    status: str
    localized_title: Mapping[str, str]
    localized_result: Mapping[str, str]
    semantic_role_key: str = ""
    evidence_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    planned_start: str = ""
    planned_end: str = ""
    actual_start: str = ""
    actual_end: str = ""
    required_for_parent: bool = False
    material_stage: bool = False
    basis_modality: str = "reported"
    basis_scope: str = "source_record"
    temporal_assertion: str = "unknown"
    terminality: str = "confirmed"
    confidence: str = "unknown"
    inference_as_of: str = ""
    target_time: str = ""
    prerequisite_evidence_ids: tuple[str, ...] = ()
    remaining_obligation_ids: tuple[str, ...] = ()
    active_window_start: str = ""
    active_window_end: str = ""
    contradiction_checked: bool = False
    coverage_boundary: str = ""
    supporting_signals: tuple[str, ...] = ()
    counter_signals: tuple[str, ...] = ()
    alternative_explanations: tuple[str, ...] = ()
    contradiction_triggers: tuple[str, ...] = ()
    expires_at: str = ""
    freshness: str = "current"
    deleted: bool = False
    superseded_by: str = ""
    retirement_reason: str = ""
    revision: int = 1
    updated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        evidence_ids = tuple(
            dict.fromkeys(str(item) for item in self.evidence_ids if str(item))
        )
        source_ids = tuple(
            dict.fromkeys(str(item) for item in self.source_ids if str(item))
        )
        prerequisite_evidence_ids = tuple(
            dict.fromkeys(
                str(item)
                for item in self.prerequisite_evidence_ids
                if str(item)
            )
        )
        remaining_obligation_ids = tuple(
            dict.fromkeys(
                str(item)
                for item in self.remaining_obligation_ids
                if str(item)
            )
        )
        if not self.item_id or not self.matter_id:
            raise ValueError("WorkItem and owning Matter identities are required")
        semantic_role_key = normalize_semantic_role_key(
            self.semantic_role_key
        )
        if self.kind not in WORK_ITEM_KINDS:
            raise ValueError("unsupported WorkItem kind")
        if self.status not in WORK_ITEM_STATUSES:
            raise ValueError("unsupported WorkItem status")
        if self.freshness not in WORK_ITEM_FRESHNESS_STATES:
            raise ValueError("unsupported WorkItem freshness")
        if self.basis_modality not in WORK_ITEM_BASIS_MODALITIES:
            raise ValueError("unsupported WorkItem basis modality")
        if self.basis_scope not in WORK_ITEM_BASIS_SCOPES:
            raise ValueError("unsupported WorkItem basis scope")
        if self.temporal_assertion not in WORK_ITEM_TEMPORAL_ASSERTIONS:
            raise ValueError("unsupported WorkItem temporal assertion")
        if self.terminality not in WORK_ITEM_TERMINALITY:
            raise ValueError("unsupported WorkItem terminality")
        if not evidence_ids and not source_ids:
            raise ValueError("WorkItem requires evidence or source provenance")
        if self.revision < 1:
            raise ValueError("WorkItem revision must be positive")
        if self.deleted and (
            not self.superseded_by or not self.retirement_reason.strip()
        ):
            raise ValueError(
                "retired WorkItem requires its replacement and reason"
            )
        supporting_signals = tuple(
            dict.fromkeys(str(item).strip() for item in self.supporting_signals if str(item).strip())
        )
        counter_signals = tuple(
            dict.fromkeys(str(item).strip() for item in self.counter_signals if str(item).strip())
        )
        alternatives = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in self.alternative_explanations
                if str(item).strip()
            )
        )
        contradiction_triggers = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in self.contradiction_triggers
                if str(item).strip()
            )
        )
        if self.basis_modality == "ai_inferred":
            common_complete = (
                self.basis_scope in {"historical_gap", "current_phase"}
                and self.terminality == "provisional"
                and bool(self.inference_as_of)
                and bool(self.coverage_boundary)
                and bool(supporting_signals)
                and bool(alternatives)
                and bool(contradiction_triggers)
                and bool(self.expires_at)
            )
            historical_complete = (
                self.basis_scope == "historical_gap"
                and self.status == "completed"
                and self.temporal_assertion == "occurred"
                and bool(self.target_time)
            )
            current_phase_complete = (
                self.basis_scope == "current_phase"
                and self.status == "in_progress"
                and self.temporal_assertion == "ongoing"
                and bool(prerequisite_evidence_ids)
                and set(prerequisite_evidence_ids).issubset(evidence_ids)
                and bool(remaining_obligation_ids)
                and bool(self.active_window_start)
                and bool(self.active_window_end)
                and self.contradiction_checked
                and not counter_signals
            )
            if not common_complete or not (
                historical_complete or current_phase_complete
            ):
                raise ValueError(
                    "AI-inferred WorkItems require a complete revisable inference contract"
                )
            inference_as_of = _aware_time(
                self.inference_as_of,
                "WorkItem inference_as_of",
            )
            if historical_complete and _aware_time(
                self.target_time,
                "WorkItem target_time",
            ) > inference_as_of:
                raise ValueError(
                    "historical WorkItem inference cannot target the future"
                )
            if current_phase_complete and not (
                _aware_time(
                    self.active_window_start,
                    "WorkItem active_window_start",
                )
                <= inference_as_of
                <= _aware_time(
                    self.active_window_end,
                    "WorkItem active_window_end",
                )
            ):
                raise ValueError(
                    "current-phase WorkItem inference requires an active window"
                )
            if _aware_time(
                self.expires_at,
                "WorkItem expires_at",
            ) < inference_as_of:
                raise ValueError(
                    "AI-inferred WorkItem expiry cannot predate its analysis"
                )
        object.__setattr__(
            self,
            "localized_title",
            _localized(self.localized_title, "localized_title"),
        )
        object.__setattr__(
            self,
            "localized_result",
            _localized(self.localized_result, "localized_result"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            evidence_ids,
        )
        object.__setattr__(
            self,
            "source_ids",
            source_ids,
        )
        object.__setattr__(
            self,
            "prerequisite_evidence_ids",
            prerequisite_evidence_ids,
        )
        object.__setattr__(
            self,
            "remaining_obligation_ids",
            remaining_obligation_ids,
        )
        object.__setattr__(
            self,
            "semantic_role_key",
            semantic_role_key,
        )
        object.__setattr__(self, "supporting_signals", supporting_signals)
        object.__setattr__(self, "counter_signals", counter_signals)
        object.__setattr__(self, "alternative_explanations", alternatives)
        object.__setattr__(
            self,
            "contradiction_triggers",
            contradiction_triggers,
        )

    @property
    def key_time(self) -> str:
        return (
            self.actual_end
            or self.actual_start
            or self.planned_end
            or self.planned_start
        )


@dataclass(frozen=True)
class HierarchyMemberDisposition:
    member_kind: str
    member_id: str
    action: str
    target_matter_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.member_kind not in HIERARCHY_MEMBER_KINDS:
            raise ValueError("unsupported hierarchy member kind")
        if not self.member_id or self.action not in HIERARCHY_DISPOSITION_KINDS:
            raise ValueError("hierarchy member identity and disposition are required")
        if not self.target_matter_ids:
            raise ValueError("hierarchy disposition requires a target Matter")
        object.__setattr__(
            self,
            "target_matter_ids",
            tuple(dict.fromkeys(str(item) for item in self.target_matter_ids if str(item))),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            tuple(dict.fromkeys(str(item) for item in self.evidence_ids if str(item))),
        )


@dataclass(frozen=True)
class MatterHierarchyRevision:
    revision_id: str
    change_kind: str
    subject_matter_ids: tuple[str, ...]
    prior_parent_ids: tuple[str, ...]
    current_parent_ids: tuple[str, ...]
    rationale: str
    evidence_ids: tuple[str, ...] = ()
    dispositions: tuple[HierarchyMemberDisposition, ...] = ()
    invalidated_matter_ids: tuple[str, ...] = ()
    created_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.revision_id or self.change_kind not in HIERARCHY_CHANGE_KINDS:
            raise ValueError("hierarchy revision identity and kind are required")
        if not self.subject_matter_ids or not self.rationale.strip():
            raise ValueError("hierarchy revision subjects and rationale are required")
        for field_name in (
            "subject_matter_ids",
            "prior_parent_ids",
            "current_parent_ids",
            "evidence_ids",
            "invalidated_matter_ids",
        ):
            object.__setattr__(
                self,
                field_name,
                tuple(
                    dict.fromkeys(
                        str(item)
                        for item in getattr(self, field_name)
                        if str(item)
                    )
                ),
            )
        object.__setattr__(self, "dispositions", tuple(self.dispositions))


@dataclass(frozen=True)
class MatterHierarchySummary:
    matter_id: str
    child_count: int
    child_state_counts: Mapping[str, int]
    required_incomplete_count: int
    critical_attention_count: int
    completion_coherent: bool
    completion_barrier_ids: tuple[str, ...]
    latest_child_update: str = ""
    freshness: str = "current"
    revision: int = 1
    updated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.matter_id or self.child_count < 0 or self.revision < 1:
            raise ValueError("hierarchy summary identity and counts are invalid")
        if self.required_incomplete_count < 0 or self.critical_attention_count < 0:
            raise ValueError("hierarchy summary counts cannot be negative")
        if self.freshness not in {"current", "stale", "blocked"}:
            raise ValueError("unsupported hierarchy summary freshness")
        object.__setattr__(
            self,
            "child_state_counts",
            {
                str(key): int(value)
                for key, value in self.child_state_counts.items()
                if int(value) >= 0
            },
        )
        object.__setattr__(
            self,
            "completion_barrier_ids",
            tuple(
                dict.fromkeys(
                    str(item) for item in self.completion_barrier_ids if str(item)
                )
            ),
        )


__all__ = [
    "CONTAINMENT_ROLES",
    "EDGE_FRESHNESS_STATES",
    "HIERARCHY_CHANGE_KINDS",
    "HIERARCHY_DISPOSITION_KINDS",
    "HIERARCHY_MEMBER_KINDS",
    "HIERARCHY_STAGE_IDS",
    "HIERARCHY_STAGE_STATUSES",
    "HierarchyMemberDisposition",
    "MAX_HIERARCHY_ATTACH_BATCH",
    "MatterChildAttachment",
    "MatterContainmentEdge",
    "MatterHierarchyRevision",
    "MatterHierarchySummary",
    "MatterWorkItem",
    "WORK_ITEM_FRESHNESS_STATES",
    "WORK_ITEM_KINDS",
    "WORK_ITEM_STATUSES",
]
