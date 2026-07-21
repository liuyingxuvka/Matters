"""C6 values for bounded, evidence-bound Matter reconciliation.

The values in this module describe context and placement decisions only.  They
do not replace ``MatterAdmission`` or the hierarchy owner that persist the
resulting canonical Matter and containment state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import unicodedata


CONTEXT_SIGNAL_KINDS = frozenset(
    {
        "goal",
        "subject",
        "outcome",
        "person",
        "time",
        "source_neighborhood",
        "provider_thread",
        "repository_project",
        "codex_workspace",
        "containment_scope",
    }
)
CONTEXT_FRESHNESS_STATES = frozenset({"current", "stale", "blocked"})
PLACEMENT_OUTCOMES = frozenset(
    {
        "append_to_current",
        "admit_child",
        "admit_related",
        "admit_root",
        "preserve_uncertain_alternative",
        "blocked",
    }
)
GRANULARITY_KINDS = frozenset({"matter", "work_item", "event", "source"})
RELATED_MATTER_TYPES = frozenset(
    {
        "related",
        "supports",
        "depends_on",
        "blocks",
        "precedes",
        "follows",
        "same_context",
        "same_project_context",
        "same_source_context",
        "shares_person",
        "temporal_context",
        "overlapping_goal",
    }
)
MAX_CONTEXT_SIGNALS = 100
MAX_RECONCILIATION_CANDIDATES = 50


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalized_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    return " ".join(normalized.split())


def _identities(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


@dataclass(frozen=True)
class ContextSignal:
    """One evidence-bound contextual signal.

    A signal is deliberately insufficient to license a merge by itself.  The
    reconciliation owner compares combinations of distinct signal kinds.
    """

    kind: str
    value: str
    evidence_ids: tuple[str, ...]
    confidence: str = "bounded"
    freshness: str = "current"

    def __post_init__(self) -> None:
        kind = str(self.kind).strip()
        value = _normalized_text(self.value)
        evidence_ids = _identities(self.evidence_ids)
        if kind not in CONTEXT_SIGNAL_KINDS:
            raise ValueError(f"unsupported Matter context signal: {kind}")
        if not value:
            raise ValueError("Matter context signal value is required")
        if not evidence_ids:
            raise ValueError("Matter context signals require current evidence")
        if not str(self.confidence).strip():
            raise ValueError("Matter context signal confidence is required")
        if self.freshness not in CONTEXT_FRESHNESS_STATES:
            raise ValueError("unsupported Matter context freshness")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "evidence_ids", evidence_ids)

    @property
    def match_key(self) -> tuple[str, str]:
        return self.kind, self.value


@dataclass(frozen=True)
class ProjectContext:
    """One bounded semantic/project context supplied to C6."""

    signals: tuple[ContextSignal, ...]
    revision: int = 1
    freshness: str = "current"

    def __post_init__(self) -> None:
        signals = tuple(self.signals)
        if self.revision < 1:
            raise ValueError("Matter project-context revision must be positive")
        if self.freshness not in CONTEXT_FRESHNESS_STATES:
            raise ValueError("unsupported Matter project-context freshness")
        if len(signals) > MAX_CONTEXT_SIGNALS:
            raise ValueError("Matter project context exceeds its bounded signal limit")
        keys = tuple(signal.match_key for signal in signals)
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate Matter context signals must be consolidated")
        object.__setattr__(self, "signals", signals)

    @property
    def current_signals(self) -> tuple[ContextSignal, ...]:
        if self.freshness != "current":
            return ()
        return tuple(signal for signal in self.signals if signal.freshness == "current")


@dataclass(frozen=True)
class GranularityAssessment:
    """Evidence-bounded distinction between Matter, WorkItem, Event, and source."""

    independently_useful_goal: bool = False
    independently_useful_state: bool = False
    independently_useful_outcome: bool = False
    independently_useful_next_step: bool = False
    bounded_task: bool = False
    one_time_occurrence: bool = False

    @property
    def object_kind(self) -> str:
        if any(
            (
                self.independently_useful_goal,
                self.independently_useful_state,
                self.independently_useful_outcome,
                self.independently_useful_next_step,
            )
        ):
            return "matter"
        if self.one_time_occurrence:
            return "event"
        if self.bounded_task:
            return "work_item"
        return "source"


@dataclass(frozen=True)
class MatterPlacementCandidate:
    """One current Matter candidate in the bounded reconciliation window."""

    matter_id: str
    semantic_identity_key: str
    context: ProjectContext
    broad_scope: bool = False
    parent_matter_id: str = ""

    def __post_init__(self) -> None:
        matter_id = str(self.matter_id).strip()
        semantic_identity_key = str(self.semantic_identity_key).strip()
        if not matter_id or not semantic_identity_key:
            raise ValueError("candidate Matter and semantic identities are required")
        object.__setattr__(self, "matter_id", matter_id)
        object.__setattr__(self, "semantic_identity_key", semantic_identity_key)
        object.__setattr__(
            self,
            "parent_matter_id",
            str(self.parent_matter_id).strip(),
        )


@dataclass(frozen=True)
class MatterRelationshipHint:
    """One evidence-backed secondary relation that never licenses containment."""

    target_matter_id: str
    relation_type: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        target_matter_id = str(self.target_matter_id).strip()
        relation_type = _normalized_text(self.relation_type).replace(" ", "_")
        evidence_ids = _identities(self.evidence_ids)
        if not target_matter_id or relation_type not in RELATED_MATTER_TYPES:
            raise ValueError("typed related-Matter hint is invalid")
        if not evidence_ids:
            raise ValueError("typed related-Matter hint requires evidence")
        object.__setattr__(self, "target_matter_id", target_matter_id)
        object.__setattr__(self, "relation_type", relation_type)
        object.__setattr__(self, "evidence_ids", evidence_ids)


@dataclass(frozen=True)
class MatterReconciliationRequest:
    """One C6 reconciliation request over a finite current candidate set."""

    source_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    semantic_identity_key: str
    context: ProjectContext
    candidates: tuple[MatterPlacementCandidate, ...] = ()
    relationship_hints: tuple[MatterRelationshipHint, ...] = ()
    granularity: GranularityAssessment = field(default_factory=GranularityAssessment)
    access_blocked: bool = False
    conflict: bool = False
    revision: int = 1

    def __post_init__(self) -> None:
        source_ids = _identities(self.source_ids)
        evidence_ids = _identities(self.evidence_ids)
        candidates = tuple(self.candidates)
        relationship_hints = tuple(self.relationship_hints)
        if not source_ids:
            raise ValueError("Matter reconciliation requires source provenance")
        if not evidence_ids and not self.access_blocked:
            raise ValueError("Matter reconciliation requires current evidence")
        if self.revision < 1:
            raise ValueError("Matter reconciliation revision must be positive")
        candidate_ids = tuple(candidate.matter_id for candidate in candidates)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("Matter reconciliation candidates must be unique")
        hint_targets = tuple(
            hint.target_matter_id for hint in relationship_hints
        )
        if len(hint_targets) != len(set(hint_targets)):
            raise ValueError("one typed relation is allowed per candidate Matter")
        if not set(hint_targets).issubset(candidate_ids):
            raise ValueError("typed relations must target current candidates")
        if any(
            not set(hint.evidence_ids).issubset(evidence_ids)
            for hint in relationship_hints
        ):
            raise ValueError(
                "typed relations require evidence from the current request"
            )
        object.__setattr__(self, "source_ids", source_ids)
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "relationship_hints", relationship_hints)
        object.__setattr__(
            self,
            "semantic_identity_key",
            str(self.semantic_identity_key).strip(),
        )


@dataclass(frozen=True)
class MatterPlacementDecision:
    """Terminal C6 placement decision before canonical owner dispatch."""

    status: str
    granularity: str
    candidate_matter_ids: tuple[str, ...]
    rationale: str
    evidence_ids: tuple[str, ...]
    matched_signal_kinds: tuple[str, ...] = ()
    target_matter_id: str = ""
    parent_matter_id: str = ""
    related_matter_ids: tuple[str, ...] = ()
    related_matter_types: tuple[tuple[str, str], ...] = ()
    revision: int = 1
    freshness: str = "current"
    decided_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        candidate_matter_ids = _identities(self.candidate_matter_ids)
        evidence_ids = _identities(self.evidence_ids)
        matched_signal_kinds = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in self.matched_signal_kinds
                if str(item).strip()
            )
        )
        related_matter_ids = _identities(self.related_matter_ids)
        related_matter_types = tuple(
            (
                str(matter_id).strip(),
                _normalized_text(relation_type).replace(" ", "_"),
            )
            for matter_id, relation_type in self.related_matter_types
            if str(matter_id).strip()
        )
        target_matter_id = str(self.target_matter_id).strip()
        parent_matter_id = str(self.parent_matter_id).strip()
        if self.status not in PLACEMENT_OUTCOMES:
            raise ValueError("unsupported Matter placement outcome")
        if self.granularity not in GRANULARITY_KINDS:
            raise ValueError("unsupported Matter granularity")
        if not str(self.rationale).strip() or self.revision < 1:
            raise ValueError("Matter placement rationale and revision are required")
        if self.freshness not in CONTEXT_FRESHNESS_STATES:
            raise ValueError("unsupported Matter placement freshness")
        if len(candidate_matter_ids) > MAX_RECONCILIATION_CANDIDATES:
            raise ValueError("Matter placement decision exceeds candidate bound")
        if any(kind not in CONTEXT_SIGNAL_KINDS for kind in matched_signal_kinds):
            raise ValueError("Matter placement contains an unknown signal kind")
        if self.status != "blocked" and not evidence_ids:
            raise ValueError("non-blocked Matter placement requires evidence")
        if self.status == "append_to_current" and not target_matter_id:
            raise ValueError("append-to-current requires a target Matter")
        if self.status == "admit_child" and not parent_matter_id:
            raise ValueError("child admission requires a parent Matter")
        if self.status == "admit_related" and not related_matter_ids:
            raise ValueError("related admission requires related Matters")
        if (
            set(matter_id for matter_id, _relation_type in related_matter_types)
            != set(related_matter_ids)
        ):
            raise ValueError(
                "every related Matter requires exactly one relation type"
            )
        if any(
            relation_type not in RELATED_MATTER_TYPES
            for _matter_id, relation_type in related_matter_types
        ):
            raise ValueError("related Matter type is unsupported")
        if self.status in {"admit_child", "admit_related", "admit_root"}:
            if self.granularity != "matter":
                raise ValueError("only independently useful Matters may be admitted")
        if target_matter_id and target_matter_id not in candidate_matter_ids:
            raise ValueError("placement target must be a current candidate")
        if parent_matter_id and parent_matter_id not in candidate_matter_ids:
            raise ValueError("placement parent must be a current candidate")
        if not set(related_matter_ids).issubset(candidate_matter_ids):
            raise ValueError("related Matters must come from current candidates")
        object.__setattr__(self, "candidate_matter_ids", candidate_matter_ids)
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "matched_signal_kinds", matched_signal_kinds)
        object.__setattr__(self, "target_matter_id", target_matter_id)
        object.__setattr__(self, "parent_matter_id", parent_matter_id)
        object.__setattr__(self, "related_matter_ids", related_matter_ids)
        object.__setattr__(
            self,
            "related_matter_types",
            related_matter_types,
        )


__all__ = [
    "CONTEXT_FRESHNESS_STATES",
    "CONTEXT_SIGNAL_KINDS",
    "ContextSignal",
    "GRANULARITY_KINDS",
    "GranularityAssessment",
    "MAX_CONTEXT_SIGNALS",
    "MAX_RECONCILIATION_CANDIDATES",
    "MatterPlacementCandidate",
    "MatterPlacementDecision",
    "MatterReconciliationRequest",
    "MatterRelationshipHint",
    "PLACEMENT_OUTCOMES",
    "ProjectContext",
    "RELATED_MATTER_TYPES",
]
