"""C6 Matter hierarchy values and invariants.

Matter containment is distinct from ordinary related-Matter links.  A WorkItem
is a bounded stateful step owned by one Matter; an Event remains a temporal
fact and a Source remains evidence provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _localized(values: Mapping[str, str], field_name: str) -> dict[str, str]:
    normalized = {
        str(locale): str(value).strip()
        for locale, value in values.items()
        if str(locale) and str(value).strip()
    }
    if not normalized.get("en") or not normalized.get("zh-CN"):
        raise ValueError(f"{field_name} requires non-empty en and zh-CN values")
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
    evidence_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    planned_start: str = ""
    planned_end: str = ""
    actual_start: str = ""
    actual_end: str = ""
    required_for_parent: bool = False
    freshness: str = "current"
    revision: int = 1
    updated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        evidence_ids = tuple(
            dict.fromkeys(str(item) for item in self.evidence_ids if str(item))
        )
        source_ids = tuple(
            dict.fromkeys(str(item) for item in self.source_ids if str(item))
        )
        if not self.item_id or not self.matter_id:
            raise ValueError("WorkItem and owning Matter identities are required")
        if self.kind not in WORK_ITEM_KINDS:
            raise ValueError("unsupported WorkItem kind")
        if self.status not in WORK_ITEM_STATUSES:
            raise ValueError("unsupported WorkItem status")
        if self.freshness not in WORK_ITEM_FRESHNESS_STATES:
            raise ValueError("unsupported WorkItem freshness")
        if not evidence_ids and not source_ids:
            raise ValueError("WorkItem requires evidence or source provenance")
        if self.revision < 1:
            raise ValueError("WorkItem revision must be positive")
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
