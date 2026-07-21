"""Metadata-first, durable content-selection plans for registered sources.

Registration is deliberately broader than content reading.  This owner turns
the safe inventory metadata already held by C1/C2 into a deterministic,
auditable plan before a filesystem worker is allowed to read file bytes.
It never reads a path, runs an AI model, or exposes a locator.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

from matters.application.coverage_ledger import ObjectCoverageLedger, STAGE_ORDER
from matters.inventory.owners import InventoryOccurrence, InventorySnapshot


CONTENT_SELECTION_MODES = frozenset(
    {"metadata_only", "deferred", "sampled", "bounded", "deep"}
)
READABLE_CONTENT_SELECTION_MODES = frozenset({"sampled", "bounded"})
CONTENT_SELECTION_REVISION = "content-selection:v1"


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
class ContentSelectionPlan:
    """One current, private plan for an inventoried occurrence."""

    occurrence_id: str
    inventory_revision: int
    mode: str
    status: str
    priority: int
    reason: str
    source_neighborhood_id: str = ""
    source_group_chain: tuple[str, ...] = ()
    planner_revision: str = CONTENT_SELECTION_REVISION
    continuation: str = ""

    def __post_init__(self) -> None:
        if not self.occurrence_id or self.inventory_revision < 1:
            raise ValueError("content selection identity is required")
        if self.mode not in CONTENT_SELECTION_MODES:
            raise ValueError("unsupported content selection mode")
        if self.status not in {"current", "blocked"}:
            raise ValueError("unsupported content selection status")
        if self.mode == "deep" and self.status == "current" and not self.continuation:
            raise ValueError("deep selection requires an explicit continuation")

    @property
    def permits_read(self) -> bool:
        return self.status == "current" and self.mode in READABLE_CONTENT_SELECTION_MODES


class ContentSelectionOwner:
    """Persist deterministic first-pass plans and synchronize coverage truth."""

    owner_id = "content_selection"

    def __init__(self, store: Any, ledger: ObjectCoverageLedger) -> None:
        self.store = store
        self.ledger = ledger

    @staticmethod
    def _plan(
        occurrence: InventoryOccurrence,
        *,
        disposition: str,
        inventory_revision: int,
    ) -> ContentSelectionPlan:
        metadata = dict(occurrence.metadata)
        neighborhood = str(metadata.get("source_neighborhood_id", ""))
        groups = tuple(str(item) for item in metadata.get("source_group_chain", ()))
        suffix = str(metadata.get("file_kind", "")).casefold()
        size = max(0, int(metadata.get("size", 0) or 0))
        modified_ns = max(0, int(metadata.get("modified_ns", 0) or 0))
        # Absolute mtime makes newer material win without a wall-clock dependent
        # rescoring pass.  The fixed offsets keep type precedence visible.
        recency = min(2_000_000_000, modified_ns // 1_000_000_000)

        if disposition != "tracked":
            return ContentSelectionPlan(
                occurrence.occurrence_id,
                inventory_revision,
                "metadata_only",
                "current",
                0,
                f"disposition:{disposition}",
                neighborhood,
                groups,
            )
        if occurrence.object_type == "image":
            return ContentSelectionPlan(
                occurrence.occurrence_id,
                inventory_revision,
                "deferred",
                "current",
                recency,
                "image_metadata_first",
                neighborhood,
                groups,
            )
        if bool(metadata.get("software_tree", False)) and suffix in {
            "md", "markdown", "json", "jsonl", "yaml", "yml", "toml",
        }:
            return ContentSelectionPlan(
                occurrence.occurrence_id,
                inventory_revision,
                "deferred",
                "current",
                recency,
                "software_tree_document_deferred",
                neighborhood,
                groups,
            )
        if size > 16 * 1024 * 1024:
            # Do not pretend a whole-file extraction is a deep read.  A later
            # continuation-capable owner must explicitly replace this plan.
            return ContentSelectionPlan(
                occurrence.occurrence_id,
                inventory_revision,
                "deferred",
                "current",
                recency,
                "bounded_reader_size_limit",
                neighborhood,
                groups,
            )
        if suffix in {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "odt", "epub"}:
            type_priority = 500
            reason = "human_office_or_pdf_bounded"
        elif suffix in {"txt", "md", "markdown", "rst", "rtf", "csv", "tsv"}:
            type_priority = 400
            reason = "user_text_bounded"
        else:
            type_priority = 300
            reason = "supported_document_bounded"
        return ContentSelectionPlan(
            occurrence.occurrence_id,
            inventory_revision,
            "bounded",
            "current",
            type_priority + recency,
            reason,
            neighborhood,
            groups,
        )

    @staticmethod
    def _selection_fingerprint(plan: ContentSelectionPlan) -> str:
        payload = asdict(plan)
        # A scope snapshot revision proves when this occurrence was observed,
        # but it does not change the content-admission decision.  Binding the
        # semantic plan to that volatile counter rewrites every unchanged plan
        # (and its full coverage row) after each inventory refresh.
        payload.pop("inventory_revision", None)
        payload.pop("continuation", None)
        return _fingerprint(payload)

    @staticmethod
    def _equivalent_plan(
        prior: Mapping[str, Any] | None,
        desired: Mapping[str, Any],
    ) -> bool:
        if prior is None:
            return False
        prior_semantics = dict(prior)
        desired_semantics = dict(desired)
        prior_semantics.pop("inventory_revision", None)
        desired_semantics.pop("inventory_revision", None)
        # Persisted tuples return from JSON as lists; compare their canonical
        # serialized shape rather than Python container implementation types.
        return _fingerprint(prior_semantics) == _fingerprint(desired_semantics)

    def plan_snapshot(self, snapshot: InventorySnapshot) -> tuple[ContentSelectionPlan, ...]:
        dispositions = {
            item.occurrence_id: item.status for item in snapshot.dispositions
        }
        return self.plan_rows(
            (
                (occurrence, dispositions[occurrence.occurrence_id], snapshot.revision)
                for occurrence in snapshot.occurrences
            )
        )

    def plan_rows(
        self,
        rows: Iterable[tuple[InventoryOccurrence, str, int]],
    ) -> tuple[ContentSelectionPlan, ...]:
        """Plan an already bounded set of indexed inventory occurrences."""

        plans = tuple(
            self._plan(
                occurrence,
                disposition=disposition,
                inventory_revision=inventory_revision,
            )
            for occurrence, disposition, inventory_revision in rows
        )
        plan_ids = tuple(plan.occurrence_id for plan in plans)
        prior_plans = self.store.current_many(self.owner_id, plan_ids)
        coverage_payloads = self.store.current_many("object_coverage", plan_ids)
        changed: list[ContentSelectionPlan] = []
        writes: list[tuple[str, str, int, Any]] = []
        next_revisions = self.store.next_revisions(self.owner_id, plan_ids)
        for plan in plans:
            desired = asdict(plan)
            prior = prior_plans.get(plan.occurrence_id)
            if not self._equivalent_plan(prior, desired):
                writes.append(
                    (self.owner_id, plan.occurrence_id, next_revisions[plan.occurrence_id], desired)
                )
                changed.append(plan)
                continue
            coverage = coverage_payloads.get(plan.occurrence_id, {})
            stages = dict(coverage.get("stages", {}))
            if "content_selection" not in stages:
                changed.append(plan)
        self.store.append_many(writes)
        if changed:
            self.ledger.apply_content_selection_many(
                asdict(plan) for plan in changed
            )
        return plans

    def current(self, occurrence_id: str) -> ContentSelectionPlan | None:
        payload = self.store.current(self.owner_id, occurrence_id)
        return ContentSelectionPlan(**dict(payload)) if payload else None


__all__ = [
    "CONTENT_SELECTION_MODES",
    "CONTENT_SELECTION_REVISION",
    "ContentSelectionOwner",
    "ContentSelectionPlan",
    "READABLE_CONTENT_SELECTION_MODES",
]
