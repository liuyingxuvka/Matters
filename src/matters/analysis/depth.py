"""Per-occurrence semantic-depth and freshness accounting."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, TYPE_CHECKING

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


@dataclass(frozen=True)
class SemanticDepth:
    occurrence_id: str
    inventory_revision: int
    state: str
    satisfied: tuple[str, ...]
    missing: tuple[str, ...]
    stale_dependencies: tuple[str, ...] = ()
    blocker_class: str = ""

    def __post_init__(self) -> None:
        if self.state not in DEPTH_STATES:
            raise ValueError(f"unsupported semantic depth: {self.state}")


@dataclass
class SemanticDepthOwner:
    store: "SQLiteStore | None" = None

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
        return rows


__all__ = [
    "DEPTH_STATES",
    "SUFFICIENCY_CRITERIA",
    "SemanticDepth",
    "SemanticDepthOwner",
]
