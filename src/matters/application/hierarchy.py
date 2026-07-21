"""C6 hierarchy owner over the append-only SQLite snapshot store."""

from __future__ import annotations

from dataclasses import asdict, replace
from hashlib import sha256
import json
from threading import RLock
from typing import Any, Callable, Iterable, Mapping

from matters.domain.hierarchy import (
    HIERARCHY_STAGE_IDS,
    HierarchyMemberDisposition,
    MAX_HIERARCHY_ATTACH_BATCH,
    MatterChildAttachment,
    MatterContainmentEdge,
    MatterHierarchyRevision,
    MatterHierarchySummary,
    MatterWorkItem,
)
from matters.infrastructure.sqlite.store import SQLiteStore


def _fingerprint(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


class MatterHierarchyOwner:
    """Single writer for Matter containment, WorkItems, and hierarchy summaries."""

    def __init__(
        self,
        store: SQLiteStore,
        *,
        coverage_result_sink: (
            Callable[[tuple[Mapping[str, Any], ...]], None] | None
        ) = None,
    ) -> None:
        self.store = store
        self.coverage_result_sink = coverage_result_sink
        self._lock = RLock()
        self.recovered_batch_count = self.recover_pending_batches(limit=20)

    def _sync_coverage(
        self,
        payloads: Iterable[Mapping[str, Any]],
    ) -> None:
        normalized = tuple(dict(payload) for payload in payloads)
        if normalized and self.coverage_result_sink is not None:
            self.coverage_result_sink(normalized)

    @staticmethod
    def _edge_id(parent_matter_id: str, child_matter_id: str) -> str:
        digest = sha256(
            f"{parent_matter_id}\0{child_matter_id}".encode("utf-8")
        ).hexdigest()[:24]
        return f"containment:{digest}"

    @staticmethod
    def _edge(payload: Mapping[str, Any]) -> MatterContainmentEdge:
        return MatterContainmentEdge(
            edge_id=str(payload["edge_id"]),
            parent_matter_id=str(payload["parent_matter_id"]),
            child_matter_id=str(payload["child_matter_id"]),
            role=str(payload["role"]),
            confidence=str(payload["confidence"]),
            rationale=str(payload["rationale"]),
            evidence_ids=tuple(payload.get("evidence_ids", ())),
            ordinal=int(payload.get("ordinal", 0)),
            boundary_revision=int(payload.get("boundary_revision", 1)),
            freshness=str(payload.get("freshness", "pending")),
            active=bool(payload.get("active", True)),
            updated_at=str(payload.get("updated_at", "")),
        )

    def _matter_exists(self, matter_id: str) -> bool:
        admission = self.store.current("admission_decision", matter_id)
        return bool(
            admission
            and admission.get("status") == "admitted"
            and isinstance(admission.get("matter"), Mapping)
            and str(admission["matter"].get("matter_id", "")) == matter_id
        )

    def _require_matter(self, matter_id: str) -> None:
        if not matter_id or not self._matter_exists(matter_id):
            raise KeyError(f"admitted Matter is unavailable: {matter_id}")

    def parent_edge(
        self,
        matter_id: str,
        *,
        current_only: bool = True,
    ) -> MatterContainmentEdge | None:
        payload = self.store.hierarchy_parent_edge(
            matter_id,
            current_only=current_only,
        )
        return self._edge(payload) if payload else None

    def ancestors(
        self,
        matter_id: str,
        *,
        current_only: bool = False,
    ) -> tuple[str, ...]:
        return self.store.hierarchy_ancestor_ids(
            matter_id,
            current_only=current_only,
        )

    def descendants(
        self,
        matter_id: str,
        *,
        current_only: bool = False,
    ) -> tuple[str, ...]:
        return self.store.hierarchy_descendant_ids(
            matter_id,
            current_only=current_only,
        )

    def path(self, matter_id: str) -> tuple[str, ...]:
        self._require_matter(matter_id)
        return (*reversed(self.ancestors(matter_id, current_only=True)), matter_id)

    def root_matter_ids(self, matter_ids: Iterable[str]) -> tuple[str, ...]:
        child_ids = set(self.store.hierarchy_child_ids(current_only=True))
        return tuple(
            matter_id
            for matter_id in dict.fromkeys(str(item) for item in matter_ids)
            if matter_id and matter_id not in child_ids
        )

    def _validate_parent(
        self,
        *,
        parent_matter_id: str,
        child_matter_id: str,
    ) -> None:
        self._require_matter(parent_matter_id)
        self._require_matter(child_matter_id)
        if parent_matter_id == child_matter_id:
            raise ValueError("a Matter cannot be its own parent")
        if child_matter_id in (
            parent_matter_id,
            *self.ancestors(parent_matter_id, current_only=False),
        ):
            raise ValueError("containment would create a cycle")

    def _new_edge(
        self,
        *,
        parent_matter_id: str,
        child_matter_id: str,
        role: str,
        confidence: str,
        rationale: str,
        evidence_ids: tuple[str, ...],
        ordinal: int,
        active: bool = True,
        freshness: str = "pending",
    ) -> MatterContainmentEdge:
        edge_id = self._edge_id(parent_matter_id, child_matter_id)
        return MatterContainmentEdge(
            edge_id=edge_id,
            parent_matter_id=parent_matter_id,
            child_matter_id=child_matter_id,
            role=role,
            confidence=confidence,
            rationale=rationale,
            evidence_ids=evidence_ids,
            ordinal=ordinal,
            boundary_revision=self.store.next_revision(
                "matter_containment_edge",
                edge_id,
            ),
            freshness=freshness,
            active=active,
        )

    def attach_child(
        self,
        *,
        parent_matter_id: str,
        child_matter_id: str,
        role: str,
        confidence: str,
        rationale: str,
        evidence_ids: tuple[str, ...],
        ordinal: int = 0,
    ) -> MatterHierarchyRevision:
        with self._lock:
            self._validate_parent(
                parent_matter_id=parent_matter_id,
                child_matter_id=child_matter_id,
            )
            prior = self.parent_edge(child_matter_id, current_only=False)
            if prior is not None and prior.parent_matter_id != parent_matter_id:
                raise ValueError(
                    "child already has a primary parent; use explicit reparent"
                )
            change_kind = "attach"
            if prior is not None:
                if (
                    prior.role == role
                    and prior.confidence == confidence
                    and prior.rationale == rationale
                    and prior.evidence_ids == tuple(evidence_ids)
                    and prior.ordinal == ordinal
                    and prior.freshness == "current"
                ):
                    revision = self._latest_revision_for_subject(
                        child_matter_id,
                        current_parent_matter_id=parent_matter_id,
                    )
                    if revision is not None:
                        return revision
                change_kind = "role_change"
            edge = self._new_edge(
                parent_matter_id=parent_matter_id,
                child_matter_id=child_matter_id,
                role=role,
                confidence=confidence,
                rationale=rationale,
                evidence_ids=evidence_ids,
                ordinal=ordinal,
            )
            self.store.append(
                "matter_containment_edge",
                edge.edge_id,
                edge.boundary_revision,
                asdict(edge),
            )
            new_chain = (
                parent_matter_id,
                *self.ancestors(parent_matter_id, current_only=False),
            )
            revision = self._record_revision(
                change_kind=change_kind,
                subject_matter_ids=(child_matter_id,),
                prior_parent_ids=(
                    (prior.parent_matter_id,) if prior is not None else ()
                ),
                current_parent_ids=(parent_matter_id,),
                rationale=rationale,
                evidence_ids=evidence_ids,
                invalidated_matter_ids=(child_matter_id, *new_chain),
            )
            self._invalidate(
                revision.invalidated_matter_ids,
                change_ref=revision.revision_id,
            )
            self._publish(
                revision.invalidated_matter_ids,
                pending_edge=edge,
                change_ref=revision.revision_id,
            )
            return revision

    def attach_children_batch(
        self,
        *,
        parent_matter_id: str,
        attachments: Iterable[MatterChildAttachment],
        rationale: str,
        evidence_ids: tuple[str, ...],
    ) -> MatterHierarchyRevision:
        """Attach one bounded sibling set and publish its rollup exactly once."""

        with self._lock:
            items = tuple(attachments)
            if not items or len(items) > MAX_HIERARCHY_ATTACH_BATCH:
                raise ValueError(
                    "hierarchy attach batch must contain between 1 and "
                    f"{MAX_HIERARCHY_ATTACH_BATCH} children"
                )
            if not rationale.strip():
                raise ValueError("hierarchy attach batch rationale is required")
            child_ids = tuple(item.child_matter_id for item in items)
            if len(set(child_ids)) != len(child_ids):
                raise ValueError(
                    "hierarchy attach batch contains duplicate children"
                )
            batch_evidence_ids = tuple(
                dict.fromkeys(
                    (
                        *tuple(str(item) for item in evidence_ids if str(item)),
                        *tuple(
                            evidence_id
                            for attachment in items
                            for evidence_id in attachment.evidence_ids
                        ),
                    )
                )
            )
            for attachment in items:
                self._validate_parent(
                    parent_matter_id=parent_matter_id,
                    child_matter_id=attachment.child_matter_id,
                )

            priors: dict[str, MatterContainmentEdge | None] = {}
            changed_items: list[MatterChildAttachment] = []
            for attachment in items:
                prior = self.parent_edge(
                    attachment.child_matter_id,
                    current_only=False,
                )
                if (
                    prior is not None
                    and prior.parent_matter_id != parent_matter_id
                ):
                    raise ValueError(
                        "child already has a primary parent; "
                        "use explicit reparent"
                    )
                priors[attachment.child_matter_id] = prior
                if (
                    prior is None
                    or prior.role != attachment.role
                    or prior.confidence != attachment.confidence
                    or prior.rationale != attachment.rationale
                    or prior.evidence_ids != attachment.evidence_ids
                    or prior.ordinal != attachment.ordinal
                    or prior.freshness != "current"
                    or not prior.active
                ):
                    changed_items.append(attachment)

            parent_chain = (
                parent_matter_id,
                *self.ancestors(parent_matter_id, current_only=False),
            )
            invalidated_ids = tuple(
                dict.fromkeys((*child_ids, *parent_chain))
            )
            identity_payload = {
                "change_kind": "batch_attach",
                "parent_matter_id": parent_matter_id,
                "attachments": tuple(asdict(item) for item in items),
                "rationale": rationale,
                "evidence_ids": batch_evidence_ids,
                "invalidated_matter_ids": invalidated_ids,
            }
            identity = _fingerprint(identity_payload)
            request_id = self._batch_publish_request_id(identity)
            existing_identity = self.store.current(
                "matter_hierarchy_revision_identity",
                identity,
            )
            if existing_identity is not None:
                self._recover_batch_request(request_id)
                return self.revision(
                    str(existing_identity["revision_id"])
                )

            sequence = self.store.next_revision(
                "matter_hierarchy_revision_sequence",
                "global",
            )
            digest = identity.removeprefix("sha256:")[:16]
            revision_id = (
                f"hierarchy-revision:{sequence:08d}:{digest}"
            )
            revision = MatterHierarchyRevision(
                revision_id=revision_id,
                change_kind="batch_attach",
                subject_matter_ids=child_ids,
                prior_parent_ids=tuple(
                    dict.fromkeys(
                        prior.parent_matter_id
                        for prior in priors.values()
                        if prior is not None
                    )
                ),
                current_parent_ids=(parent_matter_id,),
                rationale=rationale,
                evidence_ids=batch_evidence_ids,
                invalidated_matter_ids=invalidated_ids,
            )

            edge_ids = tuple(
                self._edge_id(
                    parent_matter_id,
                    attachment.child_matter_id,
                )
                for attachment in changed_items
            )
            edge_revisions = self.store.next_revisions(
                "matter_containment_edge",
                edge_ids,
            )
            edge_rows = []
            for attachment, edge_id in zip(
                changed_items,
                edge_ids,
                strict=True,
            ):
                edge = MatterContainmentEdge(
                    edge_id=edge_id,
                    parent_matter_id=parent_matter_id,
                    child_matter_id=attachment.child_matter_id,
                    role=attachment.role,
                    confidence=attachment.confidence,
                    rationale=attachment.rationale,
                    evidence_ids=attachment.evidence_ids,
                    ordinal=attachment.ordinal,
                    boundary_revision=edge_revisions[edge_id],
                    freshness="current",
                    active=True,
                )
                edge_rows.append(
                    (
                        "matter_containment_edge",
                        edge_id,
                        edge.boundary_revision,
                        asdict(edge),
                    )
                )

            request_payload = {
                "request_id": request_id,
                "revision_id": revision_id,
                "status": "pending",
                "matter_ids": invalidated_ids,
                "batch_identity": identity,
                "attachment_count": len(items),
            }
            self.store.append_many(
                (
                    (
                        "matter_hierarchy_revision_sequence",
                        "global",
                        sequence,
                        {"sequence": sequence},
                    ),
                    (
                        "matter_hierarchy_revision",
                        revision_id,
                        1,
                        asdict(revision),
                    ),
                    (
                        "matter_hierarchy_revision_identity",
                        identity,
                        1,
                        {
                            "identity_fingerprint": identity,
                            "revision_id": revision_id,
                        },
                    ),
                    *edge_rows,
                    *self._invalidation_rows(
                        invalidated_ids,
                        change_ref=revision_id,
                    ),
                    (
                        "matter_hierarchy_batch_publish_request",
                        request_id,
                        1,
                        request_payload,
                    ),
                )
            )
            self._recover_batch_request(request_id)
            return revision

    def reparent_child(
        self,
        *,
        child_matter_id: str,
        expected_parent_matter_id: str,
        new_parent_matter_id: str,
        role: str,
        confidence: str,
        rationale: str,
        evidence_ids: tuple[str, ...],
        ordinal: int = 0,
    ) -> MatterHierarchyRevision:
        with self._lock:
            prior = self.parent_edge(child_matter_id, current_only=False)
            if prior is None:
                raise ValueError("reparent requires a current primary parent")
            if prior.parent_matter_id != expected_parent_matter_id:
                raise ValueError("current primary parent changed")
            if prior.parent_matter_id == new_parent_matter_id:
                return self.attach_child(
                    parent_matter_id=new_parent_matter_id,
                    child_matter_id=child_matter_id,
                    role=role,
                    confidence=confidence,
                    rationale=rationale,
                    evidence_ids=evidence_ids,
                    ordinal=ordinal,
                )
            old_chain = (
                prior.parent_matter_id,
                *self.ancestors(prior.parent_matter_id, current_only=False),
            )
            self._validate_parent(
                parent_matter_id=new_parent_matter_id,
                child_matter_id=child_matter_id,
            )
            new_chain = (
                new_parent_matter_id,
                *self.ancestors(new_parent_matter_id, current_only=False),
            )
            retired = replace(
                prior,
                boundary_revision=self.store.next_revision(
                    "matter_containment_edge",
                    prior.edge_id,
                ),
                freshness="stale",
                active=False,
            )
            edge = self._new_edge(
                parent_matter_id=new_parent_matter_id,
                child_matter_id=child_matter_id,
                role=role,
                confidence=confidence,
                rationale=rationale,
                evidence_ids=evidence_ids,
                ordinal=ordinal,
            )
            self.store.append_many(
                (
                    (
                        "matter_containment_edge",
                        retired.edge_id,
                        retired.boundary_revision,
                        asdict(retired),
                    ),
                    (
                        "matter_containment_edge",
                        edge.edge_id,
                        edge.boundary_revision,
                        asdict(edge),
                    ),
                )
            )
            invalidated = tuple(
                dict.fromkeys((child_matter_id, *old_chain, *new_chain))
            )
            revision = self._record_revision(
                change_kind="reparent",
                subject_matter_ids=(child_matter_id,),
                prior_parent_ids=(prior.parent_matter_id,),
                current_parent_ids=(new_parent_matter_id,),
                rationale=rationale,
                evidence_ids=evidence_ids,
                invalidated_matter_ids=invalidated,
            )
            self._invalidate(invalidated, change_ref=revision.revision_id)
            self._publish(
                invalidated,
                pending_edge=edge,
                change_ref=revision.revision_id,
            )
            return revision

    def detach_child(
        self,
        *,
        child_matter_id: str,
        expected_parent_matter_id: str,
        rationale: str,
        evidence_ids: tuple[str, ...],
    ) -> MatterHierarchyRevision:
        with self._lock:
            prior = self.parent_edge(child_matter_id, current_only=False)
            if prior is None or prior.parent_matter_id != expected_parent_matter_id:
                raise ValueError("current primary parent changed or is absent")
            old_chain = (
                prior.parent_matter_id,
                *self.ancestors(prior.parent_matter_id, current_only=False),
            )
            retired = replace(
                prior,
                boundary_revision=self.store.next_revision(
                    "matter_containment_edge",
                    prior.edge_id,
                ),
                freshness="stale",
                active=False,
            )
            self.store.append(
                "matter_containment_edge",
                retired.edge_id,
                retired.boundary_revision,
                asdict(retired),
            )
            invalidated = tuple(dict.fromkeys((child_matter_id, *old_chain)))
            revision = self._record_revision(
                change_kind="detach",
                subject_matter_ids=(child_matter_id,),
                prior_parent_ids=(prior.parent_matter_id,),
                current_parent_ids=(),
                rationale=rationale,
                evidence_ids=evidence_ids,
                invalidated_matter_ids=invalidated,
            )
            self._invalidate(invalidated, change_ref=revision.revision_id)
            self._publish(invalidated, change_ref=revision.revision_id)
            return revision

    def register_matter(self, matter_id: str, *, change_ref: str) -> None:
        with self._lock:
            self._require_matter(matter_id)
            self._invalidate((matter_id,), change_ref=change_ref)
            self._publish((matter_id,), change_ref=change_ref)

    def save_work_item(self, item: MatterWorkItem) -> MatterWorkItem:
        with self._lock:
            self._require_matter(item.matter_id)
            revision = self.store.next_revision("matter_work_item", item.item_id)
            persisted = replace(item, revision=revision)
            self.store.append(
                "matter_work_item",
                persisted.item_id,
                revision,
                asdict(persisted),
            )
            affected = (
                persisted.matter_id,
                *self.ancestors(persisted.matter_id, current_only=False),
            )
            change_ref = f"work-item:{persisted.item_id}:v{revision}"
            self._invalidate(affected, change_ref=change_ref)
            self._publish(affected, change_ref=change_ref)
            return persisted

    def work_items_page(
        self,
        matter_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        self._require_matter(matter_id)
        rows, total = self.store.matter_work_items_page(
            matter_id,
            offset=offset,
            limit=limit,
        )
        next_offset = offset + len(rows)
        return {
            "items": rows,
            "total_count": total,
            "offset": offset,
            "limit": limit,
            "next_offset": next_offset if next_offset < total else None,
            "has_more": next_offset < total,
        }

    def audit_page(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        next_stage: str = "",
    ) -> dict[str, Any]:
        """Expose one private bounded page of hierarchy stage dispositions."""

        rows, total = self.store.matter_hierarchy_audit_page(
            offset=offset,
            limit=limit,
            next_stage=next_stage,
        )
        next_offset = offset + len(rows)
        return {
            "items": rows,
            "total_count": total,
            "offset": offset,
            "limit": limit,
            "next_offset": next_offset if next_offset < total else None,
            "has_more": next_offset < total,
            "disclosure": "private_local_audit_only",
        }

    def children_page(
        self,
        matter_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        self._require_matter(matter_id)
        rows, total = self.store.hierarchy_children_page(
            matter_id,
            offset=offset,
            limit=limit,
            current_only=True,
        )
        next_offset = offset + len(rows)
        return {
            "items": rows,
            "total_count": total,
            "offset": offset,
            "limit": limit,
            "next_offset": next_offset if next_offset < total else None,
            "has_more": next_offset < total,
        }

    def mark_dependency_changed(
        self,
        matter_id: str,
        *,
        change_ref: str,
        refresh: bool,
    ) -> tuple[str, ...]:
        with self._lock:
            self._require_matter(matter_id)
            affected = (
                matter_id,
                *self.ancestors(matter_id, current_only=False),
            )
            affected = tuple(dict.fromkeys(affected))
            self._invalidate(affected, change_ref=change_ref)
            if refresh:
                self._publish(affected, change_ref=change_ref)
            return affected

    def record_split_or_merge(
        self,
        *,
        change_kind: str,
        subject_matter_ids: tuple[str, ...],
        rationale: str,
        evidence_ids: tuple[str, ...],
        dispositions: tuple[HierarchyMemberDisposition, ...],
    ) -> MatterHierarchyRevision:
        if change_kind not in {"split", "merge"}:
            raise ValueError("only split or merge is accepted")
        with self._lock:
            for matter_id in subject_matter_ids:
                self._require_matter(matter_id)
            inventory = self._member_inventory(subject_matter_ids)
            provided = {
                (item.member_kind, item.member_id)
                for item in dispositions
            }
            missing = inventory - provided
            if missing:
                raise ValueError(
                    "split/merge dispositions are incomplete: "
                    + ", ".join(f"{kind}:{item_id}" for kind, item_id in sorted(missing))
                )
            invalidated = list(subject_matter_ids)
            for matter_id in subject_matter_ids:
                invalidated.extend(
                    self.ancestors(matter_id, current_only=False)
                )
            for disposition in dispositions:
                invalidated.extend(disposition.target_matter_ids)
                for target in disposition.target_matter_ids:
                    self._require_matter(target)
                    invalidated.extend(
                        self.ancestors(target, current_only=False)
                    )
            invalidated_ids = tuple(dict.fromkeys(invalidated))
            revision = self._record_revision(
                change_kind=change_kind,
                subject_matter_ids=subject_matter_ids,
                prior_parent_ids=tuple(
                    edge.parent_matter_id
                    for matter_id in subject_matter_ids
                    if (edge := self.parent_edge(matter_id, current_only=False))
                    is not None
                ),
                current_parent_ids=tuple(
                    edge.parent_matter_id
                    for matter_id in subject_matter_ids
                    if (edge := self.parent_edge(matter_id, current_only=False))
                    is not None
                ),
                rationale=rationale,
                evidence_ids=evidence_ids,
                dispositions=dispositions,
                invalidated_matter_ids=invalidated_ids,
            )
            self._invalidate(invalidated_ids, change_ref=revision.revision_id)
            for disposition in dispositions:
                request_id = self._disposition_request_id(
                    revision.revision_id,
                    disposition,
                )
                if self.store.current(
                    "hierarchy_disposition_request",
                    request_id,
                ) is not None:
                    continue
                self.store.append(
                    "hierarchy_disposition_request",
                    request_id,
                    1,
                    {
                        "request_id": request_id,
                        "hierarchy_revision_id": revision.revision_id,
                        "status": (
                            "current"
                            if disposition.action == "retain"
                            else (
                                "blocked"
                                if disposition.action == "review"
                                else "pending"
                            )
                        ),
                        "member_kind": disposition.member_kind,
                        "member_id": disposition.member_id,
                        "action": disposition.action,
                        "target_matter_ids": disposition.target_matter_ids,
                        "evidence_ids": disposition.evidence_ids,
                        "owner_model_id": {
                            "source": "C6_matter_admission",
                            "event": "C5_event_temporal_trace",
                            "work_item": "C6_matter_admission",
                            "child": "C6_matter_admission",
                            "open_loop": "C8_open_loop_waiting_blocking",
                        }[disposition.member_kind],
                        "output_refs": (),
                        "failure_class": (
                            "explicit_hierarchy_review_disposition"
                            if disposition.action == "review"
                            else ""
                        ),
                    },
                )
            if all(item.action == "retain" for item in dispositions):
                self._publish(
                    invalidated_ids,
                    change_ref=revision.revision_id,
                )
            return revision

    @staticmethod
    def _disposition_request_id(
        revision_id: str,
        disposition: HierarchyMemberDisposition,
    ) -> str:
        identity = _fingerprint(
            {
                "revision_id": revision_id,
                "disposition": asdict(disposition),
            }
        )
        return (
            "hierarchy-disposition:"
            + identity.removeprefix("sha256:")[:24]
        )

    def disposition_requests(
        self,
        revision_id: str,
    ) -> tuple[dict[str, Any], ...]:
        return tuple(
            payload
            for payload in self.store.iter_current(
                "hierarchy_disposition_request"
            )
            if str(payload.get("hierarchy_revision_id", ""))
            == revision_id
        )

    def pending_disposition_revision_ids(
        self,
        *,
        limit: int = 20,
    ) -> tuple[str, ...]:
        rows, _total = self.store.current_filtered_page(
            "hierarchy_disposition_request",
            json_field="status",
            values=("pending", "blocked"),
            offset=0,
            limit=limit,
        )
        return tuple(
            dict.fromkeys(
                str(item.get("hierarchy_revision_id", ""))
                for item in rows
                if str(item.get("hierarchy_revision_id", ""))
            )
        )

    def revision(self, revision_id: str) -> MatterHierarchyRevision:
        payload = self.store.current(
            "matter_hierarchy_revision",
            revision_id,
        )
        if payload is None:
            raise KeyError(revision_id)
        return MatterHierarchyRevision(
            revision_id=str(payload["revision_id"]),
            change_kind=str(payload["change_kind"]),
            subject_matter_ids=tuple(payload.get("subject_matter_ids", ())),
            prior_parent_ids=tuple(payload.get("prior_parent_ids", ())),
            current_parent_ids=tuple(payload.get("current_parent_ids", ())),
            rationale=str(payload["rationale"]),
            evidence_ids=tuple(payload.get("evidence_ids", ())),
            dispositions=tuple(
                HierarchyMemberDisposition(**item)
                for item in payload.get("dispositions", ())
            ),
            invalidated_matter_ids=tuple(
                payload.get("invalidated_matter_ids", ())
            ),
            created_at=str(payload.get("created_at", "")),
        )

    def mark_disposition_result(
        self,
        *,
        request_id: str,
        status: str,
        output_refs: tuple[str, ...] = (),
        failure_class: str = "",
    ) -> None:
        if status not in {"current", "blocked"}:
            raise ValueError("hierarchy disposition result is invalid")
        current = self.store.current(
            "hierarchy_disposition_request",
            request_id,
        )
        if current is None:
            raise KeyError(request_id)
        self.store.append(
            "hierarchy_disposition_request",
            request_id,
            self.store.next_revision(
                "hierarchy_disposition_request",
                request_id,
            ),
            {
                **current,
                "status": status,
                "output_refs": tuple(output_refs),
                "failure_class": failure_class,
            },
        )

    def publish_revision(
        self,
        revision: MatterHierarchyRevision,
    ) -> None:
        requests = self.disposition_requests(revision.revision_id)
        if any(str(item.get("status", "")) != "current" for item in requests):
            raise ValueError(
                "hierarchy revision has incomplete original-owner dispositions"
            )
        self._publish(
            revision.invalidated_matter_ids,
            change_ref=revision.revision_id,
        )

    def _member_inventory(
        self,
        matter_ids: Iterable[str],
    ) -> set[tuple[str, str]]:
        inventory: set[tuple[str, str]] = set()
        matter_set = set(matter_ids)
        for matter_id in matter_set:
            admission = self.store.current("admission_decision", matter_id) or {}
            matter = admission.get("matter")
            if isinstance(matter, Mapping):
                inventory.update(
                    ("source", str(source_id))
                    for source_id in matter.get("source_ids", ())
                    if str(source_id)
                )
            for edge in self.store.hierarchy_children(
                matter_id,
                current_only=False,
            ):
                inventory.add(("child", str(edge["child_matter_id"])))
            offset = 0
            while True:
                work_items, total = self.store.matter_work_items_page(
                    matter_id,
                    offset=offset,
                    limit=200,
                )
                inventory.update(
                    ("work_item", str(item["item_id"]))
                    for item in work_items
                )
                offset += len(work_items)
                if offset >= total or not work_items:
                    break
        events = tuple(self.store.iter_current("temporal_event"))
        invalidated_event_refs = self.store.invalidated_analysis_output_refs(
            f"temporal_event:{event_id}"
            for event in events
            if (event_id := str(event.get("event_id", "")))
        )
        for event in events:
            event_id = str(event.get("event_id", ""))
            if (
                event_id
                and f"temporal_event:{event_id}" in invalidated_event_refs
            ):
                continue
            object_ref = str(event.get("object_ref", ""))
            if object_ref in matter_set:
                inventory.add(("event", event_id))
        for loop in self.store.iter_current("open_loop"):
            if str(loop.get("matter_id", "")) in matter_set:
                inventory.add(("open_loop", str(loop["loop_id"])))
        return inventory

    def _record_revision(
        self,
        *,
        change_kind: str,
        subject_matter_ids: tuple[str, ...],
        prior_parent_ids: tuple[str, ...],
        current_parent_ids: tuple[str, ...],
        rationale: str,
        evidence_ids: tuple[str, ...],
        invalidated_matter_ids: tuple[str, ...],
        dispositions: tuple[HierarchyMemberDisposition, ...] = (),
    ) -> MatterHierarchyRevision:
        identity_payload = {
            "change_kind": change_kind,
            "subject_matter_ids": subject_matter_ids,
            "prior_parent_ids": prior_parent_ids,
            "current_parent_ids": current_parent_ids,
            "rationale": rationale,
            "evidence_ids": evidence_ids,
            "dispositions": tuple(asdict(item) for item in dispositions),
            "invalidated_matter_ids": invalidated_matter_ids,
        }
        identity = _fingerprint(identity_payload)
        existing_identity = self.store.current(
            "matter_hierarchy_revision_identity",
            identity,
        )
        if existing_identity is not None:
            existing = self.store.current(
                "matter_hierarchy_revision",
                str(existing_identity["revision_id"]),
            )
            if existing is not None:
                return MatterHierarchyRevision(
                    revision_id=str(existing["revision_id"]),
                    change_kind=str(existing["change_kind"]),
                    subject_matter_ids=tuple(
                        existing.get("subject_matter_ids", ())
                    ),
                    prior_parent_ids=tuple(
                        existing.get("prior_parent_ids", ())
                    ),
                    current_parent_ids=tuple(
                        existing.get("current_parent_ids", ())
                    ),
                    rationale=str(existing["rationale"]),
                    evidence_ids=tuple(existing.get("evidence_ids", ())),
                    dispositions=tuple(
                        HierarchyMemberDisposition(**item)
                        for item in existing.get("dispositions", ())
                    ),
                    invalidated_matter_ids=tuple(
                        existing.get("invalidated_matter_ids", ())
                    ),
                    created_at=str(existing.get("created_at", "")),
                )
        sequence = self.store.next_revision(
            "matter_hierarchy_revision_sequence",
            "global",
        )
        self.store.append(
            "matter_hierarchy_revision_sequence",
            "global",
            sequence,
            {"sequence": sequence},
        )
        digest = identity.split(":", 1)[1][:16]
        revision_id = f"hierarchy-revision:{sequence:08d}:{digest}"
        revision = MatterHierarchyRevision(
            revision_id=revision_id,
            change_kind=change_kind,
            subject_matter_ids=subject_matter_ids,
            prior_parent_ids=prior_parent_ids,
            current_parent_ids=current_parent_ids,
            rationale=rationale,
            evidence_ids=evidence_ids,
            dispositions=dispositions,
            invalidated_matter_ids=invalidated_matter_ids,
        )
        if self.store.current("matter_hierarchy_revision", revision_id) is None:
            self.store.append(
                "matter_hierarchy_revision",
                revision_id,
                1,
                asdict(revision),
            )
            self.store.append(
                "matter_hierarchy_revision_identity",
                identity,
                1,
                {
                    "identity_fingerprint": identity,
                    "revision_id": revision_id,
                },
            )
        return revision

    def _latest_revision_for_subject(
        self,
        matter_id: str,
        *,
        current_parent_matter_id: str,
    ) -> MatterHierarchyRevision | None:
        candidates = [
            payload
            for payload in self.store.iter_current("matter_hierarchy_revision")
            if matter_id in payload.get("subject_matter_ids", ())
            and current_parent_matter_id
            in payload.get("current_parent_ids", ())
            and payload.get("change_kind")
            in {"attach", "batch_attach", "role_change"}
        ]
        if not candidates:
            return None
        payload = max(candidates, key=lambda item: str(item.get("created_at", "")))
        return MatterHierarchyRevision(
            revision_id=str(payload["revision_id"]),
            change_kind=str(payload["change_kind"]),
            subject_matter_ids=tuple(payload.get("subject_matter_ids", ())),
            prior_parent_ids=tuple(payload.get("prior_parent_ids", ())),
            current_parent_ids=tuple(payload.get("current_parent_ids", ())),
            rationale=str(payload["rationale"]),
            evidence_ids=tuple(payload.get("evidence_ids", ())),
            dispositions=tuple(
                HierarchyMemberDisposition(**item)
                for item in payload.get("dispositions", ())
            ),
            invalidated_matter_ids=tuple(
                payload.get("invalidated_matter_ids", ())
            ),
            created_at=str(payload.get("created_at", "")),
        )

    @staticmethod
    def _batch_publish_request_id(identity: str) -> str:
        return (
            "hierarchy-batch-publish:"
            + identity.removeprefix("sha256:")[:24]
        )

    def recover_pending_batches(self, *, limit: int = 20) -> int:
        """Finish committed edge batches whose derived publication was interrupted."""

        if limit < 1 or limit > 100:
            raise ValueError("hierarchy batch recovery limit is invalid")
        with self._lock:
            rows, _total = self.store.current_filtered_page(
                "matter_hierarchy_batch_publish_request",
                json_field="status",
                values=("pending",),
                offset=0,
                limit=limit,
            )
            recovered = 0
            for payload in rows:
                self._recover_batch_request(str(payload["request_id"]))
                recovered += 1
            return recovered

    def _recover_batch_request(self, request_id: str) -> None:
        request = self.store.current(
            "matter_hierarchy_batch_publish_request",
            request_id,
        )
        if request is None:
            raise KeyError(
                f"hierarchy batch publication request is unavailable: "
                f"{request_id}"
            )
        if str(request.get("status", "")) == "current":
            return
        if str(request.get("status", "")) != "pending":
            raise ValueError("hierarchy batch publication request is invalid")
        matter_ids = tuple(
            str(item) for item in request.get("matter_ids", ()) if str(item)
        )
        self._publish_batch(
            matter_ids,
            change_ref=str(request["revision_id"]),
        )
        revision = self.store.next_revision(
            "matter_hierarchy_batch_publish_request",
            request_id,
        )
        self.store.append(
            "matter_hierarchy_batch_publish_request",
            request_id,
            revision,
            {
                **request,
                "status": "current",
                "publication_revision": revision,
            },
        )

    def _invalidation_rows(
        self,
        matter_ids: Iterable[str],
        *,
        change_ref: str,
    ) -> tuple[tuple[str, str, int, dict[str, Any]], ...]:
        ids = tuple(
            dict.fromkeys(str(item) for item in matter_ids if str(item))
        )
        revisions = self.store.next_revisions(
            "matter_hierarchy_audit",
            ids,
        )
        return tuple(
            (
                "matter_hierarchy_audit",
                matter_id,
                revisions[matter_id],
                {
                    "matter_id": matter_id,
                    "revision": revisions[matter_id],
                    "status": "stale",
                    "change_ref": change_ref,
                    "stages": {
                        stage_id: (
                            "current"
                            if stage_id == "hierarchy_decision"
                            else "stale"
                        )
                        for stage_id in HIERARCHY_STAGE_IDS
                    },
                },
            )
            for matter_id in ids
        )

    def _invalidate(
        self,
        matter_ids: Iterable[str],
        *,
        change_ref: str,
    ) -> None:
        rows = self._invalidation_rows(
            matter_ids,
            change_ref=change_ref,
        )
        self.store.append_many(rows)
        self._sync_coverage(row[3] for row in rows)

    def _publish_batch(
        self,
        matter_ids: Iterable[str],
        *,
        change_ref: str,
    ) -> None:
        """Publish a committed batch with one bounded derived-state write."""

        ids = tuple(
            matter_id
            for matter_id in dict.fromkeys(
                str(item) for item in matter_ids if str(item)
            )
            if self._matter_exists(matter_id)
        )
        if not ids:
            return
        summary_revisions = self.store.next_revisions(
            "matter_hierarchy_summary",
            ids,
        )
        hierarchy_revisions = self.store.next_revisions(
            "matter_hierarchy_projection",
            ids,
        )
        audit_revisions = self.store.next_revisions(
            "matter_hierarchy_audit",
            ids,
        )
        projections = self.store.current_many("projection", ids)
        rows: list[tuple[str, str, int, dict[str, Any]]] = []
        audit_payloads: list[dict[str, Any]] = []
        for matter_id in ids:
            summary = self._summary(
                matter_id,
                revision=summary_revisions[matter_id],
            )
            path = self.path(matter_id)
            parent = self.parent_edge(matter_id, current_only=True)
            projection_available = matter_id in projections
            path_projections = self.store.current_many("projection", path)
            path_projection_current = projection_available and all(
                item in path_projections for item in path
            )
            hierarchy_revision = hierarchy_revisions[matter_id]
            hierarchy_status = (
                "current" if projection_available else "blocked"
            )
            ui_status = (
                "current" if path_projection_current else "blocked"
            )
            audit_revision = audit_revisions[matter_id]
            audit_payload = {
                "matter_id": matter_id,
                "revision": audit_revision,
                "status": (
                    "current"
                    if hierarchy_status == "current"
                    and ui_status == "current"
                    else "blocked"
                ),
                "change_ref": change_ref,
                "stages": {
                    "hierarchy_decision": "current",
                    "containment_current": "current",
                    "child_state_current": "current",
                    "ancestor_rollup_current": "current",
                    "hierarchy_projection_current": hierarchy_status,
                    "ui_reachable": ui_status,
                },
            }
            audit_payloads.append(audit_payload)
            rows.extend(
                (
                    (
                        "matter_hierarchy_summary",
                        matter_id,
                        summary.revision,
                        asdict(summary),
                    ),
                    (
                        "matter_hierarchy_projection",
                        matter_id,
                        hierarchy_revision,
                        {
                            "matter_id": matter_id,
                            "parent_matter_id": (
                                parent.parent_matter_id
                                if parent is not None
                                else ""
                            ),
                            "path": path,
                            "child_count": summary.child_count,
                            "summary_revision": summary.revision,
                            "freshness": hierarchy_status,
                            "change_ref": change_ref,
                            "revision": hierarchy_revision,
                        },
                    ),
                    (
                        "matter_hierarchy_audit",
                        matter_id,
                        audit_revision,
                        audit_payload,
                    ),
                )
            )
        self.store.append_many(rows)
        self._sync_coverage(audit_payloads)

    def _publish(
        self,
        matter_ids: Iterable[str],
        *,
        change_ref: str,
        pending_edge: MatterContainmentEdge | None = None,
    ) -> None:
        if pending_edge is not None and pending_edge.freshness != "current":
            current_edge = replace(
                pending_edge,
                boundary_revision=self.store.next_revision(
                    "matter_containment_edge",
                    pending_edge.edge_id,
                ),
                freshness="current",
                active=True,
            )
            self.store.append(
                "matter_containment_edge",
                current_edge.edge_id,
                current_edge.boundary_revision,
                asdict(current_edge),
            )
        for matter_id in dict.fromkeys(matter_ids):
            if not matter_id or not self._matter_exists(matter_id):
                continue
            summary = self._summary(matter_id)
            self.store.append(
                "matter_hierarchy_summary",
                matter_id,
                summary.revision,
                asdict(summary),
            )
            path = self.path(matter_id)
            parent = self.parent_edge(matter_id, current_only=True)
            projection_available = (
                self.store.current("projection", matter_id) is not None
            )
            path_projection_current = projection_available and all(
                self.store.current("projection", item) is not None
                for item in path
            )
            hierarchy_projection_revision = self.store.next_revision(
                "matter_hierarchy_projection",
                matter_id,
            )
            self.store.append(
                "matter_hierarchy_projection",
                matter_id,
                hierarchy_projection_revision,
                {
                    "matter_id": matter_id,
                    "parent_matter_id": (
                        parent.parent_matter_id if parent is not None else ""
                    ),
                    "path": path,
                    "child_count": summary.child_count,
                    "summary_revision": summary.revision,
                    "freshness": (
                        "current" if projection_available else "blocked"
                    ),
                    "change_ref": change_ref,
                    "revision": hierarchy_projection_revision,
                },
            )
            audit_revision = self.store.next_revision(
                "matter_hierarchy_audit",
                matter_id,
            )
            hierarchy_projection_status = (
                "current" if projection_available else "blocked"
            )
            ui_status = "current" if path_projection_current else "blocked"
            audit_payload = {
                "matter_id": matter_id,
                "revision": audit_revision,
                "status": (
                    "current"
                    if hierarchy_projection_status == "current"
                    and ui_status == "current"
                    else "blocked"
                ),
                "change_ref": change_ref,
                "stages": {
                    "hierarchy_decision": "current",
                    "containment_current": "current",
                    "child_state_current": "current",
                    "ancestor_rollup_current": "current",
                    "hierarchy_projection_current": hierarchy_projection_status,
                    "ui_reachable": ui_status,
                },
            }
            self.store.append(
                "matter_hierarchy_audit",
                matter_id,
                audit_revision,
                audit_payload,
            )
            self._sync_coverage((audit_payload,))

    def _summary(
        self,
        matter_id: str,
        *,
        revision: int | None = None,
    ) -> MatterHierarchySummary:
        edges = self.store.hierarchy_children(
            matter_id,
            current_only=True,
        )
        state_counts: dict[str, int] = {}
        completion_barriers: list[str] = []
        critical_attention = 0
        latest_update = ""
        for edge in edges:
            child_id = str(edge["child_matter_id"])
            lifecycle = self.store.current(
                "lifecycle_decision",
                f"{child_id}:lifecycle",
            )
            projection = self.store.current("projection", child_id) or {}
            state = str(
                (lifecycle or {}).get("state")
                or projection.get("state")
                or "uncertain"
            )
            state_counts[state] = state_counts.get(state, 0) + 1
            outcome = self.store.current(
                "outcome_decision",
                f"{child_id}:outcome",
            )
            role = str(edge["role"])
            if role in {"required", "critical"} and str(
                (outcome or {}).get("status", "")
            ) != "completed":
                completion_barriers.append(child_id)
            if role == "critical" and state == "blocked":
                critical_attention += 1
            latest_update = max(
                latest_update,
                str(edge.get("updated_at", "")),
            )
        offset = 0
        while True:
            work_items, total = self.store.matter_work_items_page(
                matter_id,
                offset=offset,
                limit=200,
            )
            for item in work_items:
                if bool(item.get("required_for_parent", False)) and str(
                    item.get("status", "")
                ) != "completed":
                    completion_barriers.append(str(item["item_id"]))
                latest_update = max(
                    latest_update,
                    str(item.get("updated_at", "")),
                )
            offset += len(work_items)
            if offset >= total or not work_items:
                break
        parent_outcome = self.store.current(
            "outcome_decision",
            f"{matter_id}:outcome",
        )
        if revision is None:
            revision = self.store.next_revision(
                "matter_hierarchy_summary",
                matter_id,
            )
        return MatterHierarchySummary(
            matter_id=matter_id,
            child_count=len(edges),
            child_state_counts=state_counts,
            required_incomplete_count=len(completion_barriers),
            critical_attention_count=critical_attention,
            completion_coherent=(
                str((parent_outcome or {}).get("status", "")) == "completed"
                and not completion_barriers
            ),
            completion_barrier_ids=tuple(completion_barriers),
            latest_child_update=latest_update,
            revision=revision,
        )


__all__ = ["MatterHierarchyOwner"]
