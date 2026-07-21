"""Bounded read-model graph over current Matter-owned records.

The graph does not become a canonical owner.  C6 continues to own primary
Matter containment, C5 owns temporal events, and typed related-Matter owners
retain their own records.  This module only normalizes those records into one
revision-bound, page-safe projection for advisory reasoning.
"""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping


CERTAINTY_STATES = frozenset(
    {
        "confirmed_observed",
        "reported",
        "planned",
        "ai_inferred",
        "unknown",
    }
)
CURRENTNESS_STATES = frozenset({"current", "stale", "expired", "blocked"})
COVERAGE_STATES = frozenset({"complete", "partial", "unknown", "blocked"})
NODE_TYPES = frozenset({"matter", "work_item", "event", "person", "source"})
MAX_GRAPH_PAGE_SIZE = 200
SITUATION_GRAPH_SCHEMA_VERSION = 1

_CERTAINTY_RANK = {
    "unknown": 0,
    "ai_inferred": 1,
    "planned": 2,
    "reported": 3,
    "confirmed_observed": 4,
}
_CURRENTNESS_RANK = {
    "current": 0,
    "stale": 1,
    "expired": 2,
    "blocked": 3,
}
_COVERAGE_RANK = {
    "complete": 0,
    "partial": 1,
    "unknown": 2,
    "blocked": 3,
}
_CONFIDENCE_VALUES = {
    "certain": 1.0,
    "confirmed": 1.0,
    "high": 0.85,
    "bounded": 0.65,
    "medium": 0.6,
    "uncertain": 0.4,
    "low": 0.25,
    "unknown": 0.0,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str, field_name: str) -> datetime:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return value.astimezone(timezone.utc).isoformat()


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _fingerprint(payload: Any) -> str:
    return "sha256:" + sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    raise TypeError("situation graph records must be mappings or dataclass values")


def _identities(values: Iterable[object]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(item).strip()
            for item in values
            if str(item).strip()
        )
    )


def _confidence(value: object, *, default: float = 0.4) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        result = float(value)
    else:
        normalized = str(value).strip().casefold()
        if normalized in _CONFIDENCE_VALUES:
            result = _CONFIDENCE_VALUES[normalized]
        else:
            try:
                result = float(normalized)
            except ValueError:
                result = default
    return max(0.0, min(1.0, result))


def certainty_from_modality(value: object) -> str:
    """Map current C5 modalities into the public graph certainty vocabulary."""

    normalized = str(value).strip().casefold()
    return {
        "observed": "confirmed_observed",
        "confirmed_observed": "confirmed_observed",
        "reported": "reported",
        "planned": "planned",
        "inferred": "ai_inferred",
        "ai_inferred": "ai_inferred",
        "unknown": "unknown",
    }.get(normalized, "unknown")


def _currentness(value: object, *, expires_at: str, at: datetime) -> str:
    normalized = str(value or "current").strip().casefold()
    if normalized not in CURRENTNESS_STATES:
        normalized = "stale"
    if (
        normalized == "current"
        and expires_at
        and _parse_timestamp(expires_at, "expires_at") <= at
    ):
        return "expired"
    return normalized


def _coverage(value: object, *, has_evidence: bool) -> str:
    normalized = str(value).strip().casefold()
    if normalized in COVERAGE_STATES:
        return normalized
    return "complete" if has_evidence else "unknown"


def _opaque_cursor(
    *,
    snapshot_id: str,
    input_fingerprint: str,
    offset: int,
) -> str:
    payload = _canonical_json(
        {
            "snapshot_id": snapshot_id,
            "input_fingerprint": input_fingerprint,
            "offset": offset,
        }
    ).encode("utf-8")
    return urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _cursor_offset(
    continuation: str,
    *,
    snapshot_id: str,
    input_fingerprint: str,
) -> int:
    if not continuation:
        return 0
    try:
        padded = continuation + ("=" * (-len(continuation) % 4))
        payload = json.loads(urlsafe_b64decode(padded.encode("ascii")))
        if (
            str(payload["snapshot_id"]) != snapshot_id
            or str(payload["input_fingerprint"]) != input_fingerprint
        ):
            raise ValueError("continuation belongs to another graph snapshot")
        offset = int(payload["offset"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith("continuation belongs"):
            raise
        raise ValueError("invalid situation graph continuation") from exc
    if offset < 0:
        raise ValueError("invalid situation graph continuation")
    return offset


@dataclass(frozen=True)
class SituationNode:
    node_id: str
    node_type: str
    certainty: str
    confidence: float
    evidence_ids: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    coverage: str = "unknown"
    expires_at: str = ""
    currentness: str = "current"
    attributes: Mapping[str, Any] = field(default_factory=dict)
    canonical_write_allowed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        node_id = str(self.node_id).strip()
        node_type = str(self.node_type).strip()
        certainty = str(self.certainty).strip()
        evidence_ids = _identities(self.evidence_ids)
        alternatives = _identities(self.alternatives)
        coverage = str(self.coverage).strip()
        currentness = str(self.currentness).strip()
        if not node_id:
            raise ValueError("situation node identity is required")
        if node_type not in NODE_TYPES:
            raise ValueError(f"unsupported situation node type: {node_type}")
        if certainty not in CERTAINTY_STATES:
            raise ValueError(f"unsupported situation node certainty: {certainty}")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("situation node confidence must be between zero and one")
        if coverage not in COVERAGE_STATES:
            raise ValueError("unsupported situation node coverage")
        if currentness not in CURRENTNESS_STATES:
            raise ValueError("unsupported situation node currentness")
        if self.expires_at:
            _parse_timestamp(self.expires_at, "expires_at")
        object.__setattr__(self, "node_id", node_id)
        object.__setattr__(self, "node_type", node_type)
        object.__setattr__(self, "certainty", certainty)
        object.__setattr__(self, "confidence", float(self.confidence))
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "alternatives", alternatives)
        object.__setattr__(self, "coverage", coverage)
        object.__setattr__(self, "currentness", currentness)
        object.__setattr__(self, "attributes", dict(self.attributes))


@dataclass(frozen=True)
class SituationEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    relation_type: str
    primary_containment: bool
    certainty: str
    confidence: float
    evidence_ids: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    coverage: str = "unknown"
    expires_at: str = ""
    currentness: str = "current"
    causal: bool = False
    auto_merge: bool = False
    attributes: Mapping[str, Any] = field(default_factory=dict)
    canonical_write_allowed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        edge_id = str(self.edge_id).strip()
        source = str(self.source_node_id).strip()
        target = str(self.target_node_id).strip()
        relation = str(self.relation_type).strip()
        certainty = str(self.certainty).strip()
        evidence_ids = _identities(self.evidence_ids)
        alternatives = _identities(self.alternatives)
        coverage = str(self.coverage).strip()
        currentness = str(self.currentness).strip()
        if not edge_id or not source or not target or not relation:
            raise ValueError("situation edge identity and endpoints are required")
        if source == target and self.primary_containment:
            raise ValueError("primary containment cannot self-reference")
        if self.primary_containment and relation != "contains":
            raise ValueError("primary containment must use the contains relation")
        if certainty not in CERTAINTY_STATES:
            raise ValueError(f"unsupported situation edge certainty: {certainty}")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("situation edge confidence must be between zero and one")
        if coverage not in COVERAGE_STATES:
            raise ValueError("unsupported situation edge coverage")
        if currentness not in CURRENTNESS_STATES:
            raise ValueError("unsupported situation edge currentness")
        if self.causal and (
            certainty != "confirmed_observed" or not evidence_ids
        ):
            raise ValueError(
                "causal graph edges require confirmed observed evidence"
            )
        if self.auto_merge:
            raise ValueError("situation graph edges never authorize automatic merge")
        if self.expires_at:
            _parse_timestamp(self.expires_at, "expires_at")
        object.__setattr__(self, "edge_id", edge_id)
        object.__setattr__(self, "source_node_id", source)
        object.__setattr__(self, "target_node_id", target)
        object.__setattr__(self, "relation_type", relation)
        object.__setattr__(self, "certainty", certainty)
        object.__setattr__(self, "confidence", float(self.confidence))
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "alternatives", alternatives)
        object.__setattr__(self, "coverage", coverage)
        object.__setattr__(self, "currentness", currentness)
        object.__setattr__(self, "attributes", dict(self.attributes))


@dataclass(frozen=True)
class SituationGraphPage:
    snapshot_id: str
    input_fingerprint: str
    root_matter_id: str
    nodes: tuple[SituationNode, ...]
    edges: tuple[SituationEdge, ...]
    offset: int
    limit: int
    total_node_count: int
    total_edge_count: int
    next_continuation: str
    has_more: bool
    coverage: str
    coverage_gaps: tuple[str, ...]
    currentness: str
    expires_at: str


@dataclass(frozen=True)
class SituationGraphSnapshot:
    snapshot_id: str
    root_matter_id: str
    input_fingerprint: str
    nodes: tuple[SituationNode, ...]
    edges: tuple[SituationEdge, ...]
    generated_at: str
    expires_at: str
    coverage: str = "complete"
    coverage_gaps: tuple[str, ...] = ()
    currentness: str = "current"
    schema_version: int = SITUATION_GRAPH_SCHEMA_VERSION
    advisory_only: bool = field(default=True, init=False)
    canonical_write_allowed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        nodes = tuple(self.nodes)
        edges = tuple(self.edges)
        node_ids = tuple(node.node_id for node in nodes)
        edge_ids = tuple(edge.edge_id for edge in edges)
        coverage_gaps = _identities(self.coverage_gaps)
        if self.schema_version != SITUATION_GRAPH_SCHEMA_VERSION:
            raise ValueError("unsupported situation graph schema version")
        if not self.snapshot_id or not self.root_matter_id:
            raise ValueError("situation graph snapshot and root identities are required")
        if not self.input_fingerprint.startswith("sha256:"):
            raise ValueError("situation graph input fingerprint is required")
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("situation graph node identities must be unique")
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("situation graph edge identities must be unique")
        by_id = {node.node_id: node for node in nodes}
        root = by_id.get(self.root_matter_id)
        if root is None or root.node_type != "matter":
            raise ValueError("situation graph root must be a Matter node")
        for edge in edges:
            if (
                edge.source_node_id not in by_id
                or edge.target_node_id not in by_id
            ):
                raise ValueError("situation graph edge endpoint is unavailable")
            source = by_id[edge.source_node_id]
            target = by_id[edge.target_node_id]
            if edge.primary_containment and (
                source.node_type != "matter" or target.node_type != "matter"
            ):
                raise ValueError(
                    "primary containment may connect only Matter nodes"
                )
            if not edge.primary_containment and edge.relation_type == "contains":
                raise ValueError(
                    "the contains relation is reserved for primary containment"
                )
        incident_node_ids = {
            node_id
            for edge in edges
            for node_id in (edge.source_node_id, edge.target_node_id)
        }
        if any(
            node_id != self.root_matter_id and node_id not in incident_node_ids
            for node_id in node_ids
        ):
            raise ValueError(
                "situation graph cannot retain an unpageable orphan node"
            )
        if self.coverage not in COVERAGE_STATES:
            raise ValueError("unsupported situation graph coverage")
        if self.coverage == "complete" and coverage_gaps:
            raise ValueError("complete situation graph cannot retain coverage gaps")
        if self.currentness not in CURRENTNESS_STATES:
            raise ValueError("unsupported situation graph currentness")
        generated = _parse_timestamp(self.generated_at, "generated_at")
        expires = _parse_timestamp(self.expires_at, "expires_at")
        if expires <= generated:
            raise ValueError("situation graph expiry must follow generation")
        self._validate_primary_containment(edges)
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "coverage_gaps", coverage_gaps)

    @staticmethod
    def _validate_primary_containment(edges: tuple[SituationEdge, ...]) -> None:
        primary = tuple(edge for edge in edges if edge.primary_containment)
        parents: dict[str, str] = {}
        children: dict[str, list[str]] = {}
        for edge in primary:
            if edge.target_node_id in parents:
                raise ValueError(
                    "situation graph cannot project two primary containment edges"
                )
            parents[edge.target_node_id] = edge.source_node_id
            children.setdefault(edge.source_node_id, []).append(
                edge.target_node_id
            )

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("situation graph primary containment is cyclic")
            if node_id in visited:
                return
            visiting.add(node_id)
            for child_id in children.get(node_id, ()):
                visit(child_id)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in tuple(children):
            visit(node_id)

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return _identities(
            item
            for member in (*self.nodes, *self.edges)
            for item in member.evidence_ids
        )

    def effective_currentness(self, *, at: datetime | None = None) -> str:
        return _currentness(
            self.currentness,
            expires_at=self.expires_at,
            at=(at or _utc_now()).astimezone(timezone.utc),
        )

    def page(
        self,
        *,
        continuation: str = "",
        limit: int = 50,
        at: datetime | None = None,
    ) -> SituationGraphPage:
        """Page over edges and hydrate only the endpoint nodes for that page."""

        if limit < 1 or limit > MAX_GRAPH_PAGE_SIZE:
            raise ValueError("situation graph page bounds are invalid")
        ordered_edges = tuple(
            sorted(
                self.edges,
                key=lambda item: (
                    0 if item.primary_containment else 1,
                    item.source_node_id,
                    item.relation_type,
                    item.target_node_id,
                    item.edge_id,
                ),
            )
        )
        offset = _cursor_offset(
            continuation,
            snapshot_id=self.snapshot_id,
            input_fingerprint=self.input_fingerprint,
        )
        if offset > len(ordered_edges):
            raise ValueError("situation graph continuation is outside the snapshot")
        page_edges = ordered_edges[offset : offset + limit]
        referenced_ids = {
            self.root_matter_id,
            *(
                node_id
                for edge in page_edges
                for node_id in (
                    edge.source_node_id,
                    edge.target_node_id,
                )
            ),
        }
        page_nodes = tuple(
            sorted(
                (
                    node
                    for node in self.nodes
                    if node.node_id in referenced_ids
                ),
                key=lambda item: (
                    0 if item.node_id == self.root_matter_id else 1,
                    item.node_type,
                    item.node_id,
                ),
            )
        )
        next_offset = offset + len(page_edges)
        has_more = next_offset < len(ordered_edges)
        return SituationGraphPage(
            snapshot_id=self.snapshot_id,
            input_fingerprint=self.input_fingerprint,
            root_matter_id=self.root_matter_id,
            nodes=page_nodes,
            edges=page_edges,
            offset=offset,
            limit=limit,
            total_node_count=len(self.nodes),
            total_edge_count=len(ordered_edges),
            next_continuation=(
                _opaque_cursor(
                    snapshot_id=self.snapshot_id,
                    input_fingerprint=self.input_fingerprint,
                    offset=next_offset,
                )
                if has_more
                else ""
            ),
            has_more=has_more,
            coverage=self.coverage,
            coverage_gaps=self.coverage_gaps,
            currentness=self.effective_currentness(at=at),
            expires_at=self.expires_at,
        )


class SituationGraphBuilder:
    """Normalize already-bounded current owner records into one graph snapshot."""

    @staticmethod
    def _node(
        *,
        node_id: str,
        node_type: str,
        record: Mapping[str, Any],
        default_certainty: str,
        default_confidence: float,
        default_expiry: str,
        at: datetime,
        attributes: Mapping[str, Any] | None = None,
    ) -> SituationNode:
        evidence_ids = _identities(record.get("evidence_ids", ()))
        expires_at = str(record.get("expires_at", "") or default_expiry)
        return SituationNode(
            node_id=node_id,
            node_type=node_type,
            certainty=certainty_from_modality(
                record.get("certainty", record.get("modality", default_certainty))
            ),
            confidence=_confidence(
                record.get("confidence", default_confidence),
                default=default_confidence,
            ),
            evidence_ids=evidence_ids,
            alternatives=_identities(
                record.get(
                    "alternatives",
                    record.get("alternative_explanations", ()),
                )
            ),
            coverage=_coverage(
                record.get("coverage", ""),
                has_evidence=bool(evidence_ids),
            ),
            expires_at=expires_at,
            currentness=_currentness(
                record.get("currentness", record.get("freshness", "current")),
                expires_at=expires_at,
                at=at,
            ),
            attributes=dict(attributes or {}),
        )

    @staticmethod
    def _merge_node(
        prior: SituationNode | None,
        incoming: SituationNode,
    ) -> SituationNode:
        if prior is None:
            return incoming
        if prior.node_type != incoming.node_type:
            raise ValueError("one situation identity cannot have two node types")
        certainty = max(
            (prior.certainty, incoming.certainty),
            key=_CERTAINTY_RANK.__getitem__,
        )
        coverage = max(
            (prior.coverage, incoming.coverage),
            key=_COVERAGE_RANK.__getitem__,
        )
        currentness = max(
            (prior.currentness, incoming.currentness),
            key=_CURRENTNESS_RANK.__getitem__,
        )
        attributes = dict(prior.attributes)
        for key, value in incoming.attributes.items():
            if (
                key not in attributes
                or attributes[key] == ""
                or attributes[key] is None
            ):
                attributes[key] = value
        return SituationNode(
            node_id=prior.node_id,
            node_type=prior.node_type,
            certainty=certainty,
            confidence=max(prior.confidence, incoming.confidence),
            evidence_ids=_identities(
                (*prior.evidence_ids, *incoming.evidence_ids)
            ),
            alternatives=_identities(
                (*prior.alternatives, *incoming.alternatives)
            ),
            coverage=coverage,
            expires_at=min(
                item
                for item in (prior.expires_at, incoming.expires_at)
                if item
            ),
            currentness=currentness,
            attributes=attributes,
        )

    def build(
        self,
        *,
        root_matter_id: str,
        matter_records: Iterable[Any],
        containment_edges: Iterable[Any] = (),
        work_items: Iterable[Any] = (),
        events: Iterable[Any] = (),
        relations: Iterable[Any] = (),
        generated_at: datetime | None = None,
        expires_at: datetime | None = None,
        coverage: str = "complete",
        coverage_gaps: Iterable[str] = (),
    ) -> SituationGraphSnapshot:
        generated = (generated_at or _utc_now()).astimezone(timezone.utc)
        expires = (
            expires_at.astimezone(timezone.utc)
            if expires_at is not None
            else generated + timedelta(hours=24)
        )
        generated_text = _timestamp(generated)
        expires_text = _timestamp(expires)
        root_matter_id = str(root_matter_id).strip()
        if not root_matter_id:
            raise ValueError("situation graph root Matter is required")

        nodes: dict[str, SituationNode] = {}
        edges: dict[str, SituationEdge] = {}

        def add_node(node: SituationNode) -> None:
            nodes[node.node_id] = self._merge_node(
                nodes.get(node.node_id),
                node,
            )

        matter_payloads = tuple(_record(item) for item in matter_records)
        if root_matter_id not in {
            str(item.get("matter_id", "")).strip()
            for item in matter_payloads
        }:
            raise ValueError("root Matter record is required for situation graph")
        for item in matter_payloads:
            matter_id = str(item.get("matter_id", "")).strip()
            if not matter_id:
                raise ValueError("Matter graph records require matter_id")
            add_node(
                self._node(
                    node_id=matter_id,
                    node_type="matter",
                    record=item,
                    default_certainty=str(
                        item.get("state_basis_modality", "unknown")
                    ),
                    default_confidence=0.8,
                    default_expiry=expires_text,
                    at=generated,
                    attributes={
                        "semantic_revision": str(
                            item.get("semantic_revision", "")
                        ),
                        "title": dict(item.get("title", {})),
                        "summary": dict(item.get("summary", {})),
                        "state": str(item.get("state", "uncertain")),
                        "state_basis_scope": str(
                            item.get("state_basis_scope", "")
                        ),
                        "status_group": str(
                            item.get("status_group", "in_progress")
                        ),
                        "start_time": str(item.get("start_time", "")),
                        "latest_result": dict(
                            item.get(
                                "latest_result",
                                item.get("summary", {}),
                            )
                        ),
                    },
                )
            )

        for raw in containment_edges:
            item = _record(raw)
            if item.get("active") is False:
                continue
            parent_id = str(item.get("parent_matter_id", "")).strip()
            child_id = str(item.get("child_matter_id", "")).strip()
            if not parent_id or not child_id:
                raise ValueError("containment graph records require both Matters")
            for matter_id in (parent_id, child_id):
                if matter_id not in nodes:
                    add_node(
                        self._node(
                            node_id=matter_id,
                            node_type="matter",
                            record=item,
                            default_certainty="ai_inferred",
                            default_confidence=0.65,
                            default_expiry=expires_text,
                            at=generated,
                        )
                    )
            evidence_ids = _identities(item.get("evidence_ids", ()))
            edge_id = str(item.get("edge_id", "")).strip() or (
                "containment:"
                + sha256(
                    f"{parent_id}\0{child_id}".encode("utf-8")
                ).hexdigest()[:24]
            )
            edge = SituationEdge(
                edge_id=edge_id,
                source_node_id=parent_id,
                target_node_id=child_id,
                relation_type="contains",
                primary_containment=True,
                certainty=certainty_from_modality(
                    item.get("certainty", item.get("modality", "ai_inferred"))
                ),
                confidence=_confidence(item.get("confidence", "bounded")),
                evidence_ids=evidence_ids,
                alternatives=_identities(item.get("alternatives", ())),
                coverage=_coverage(
                    item.get("coverage", ""),
                    has_evidence=bool(evidence_ids),
                ),
                expires_at=str(item.get("expires_at", "") or expires_text),
                currentness=_currentness(
                    item.get("currentness", item.get("freshness", "current")),
                    expires_at=str(item.get("expires_at", "") or expires_text),
                    at=generated,
                ),
                attributes={"role": str(item.get("role", "required"))},
            )
            edges[edge.edge_id] = edge

        for raw in work_items:
            item = _record(raw)
            item_id = str(item.get("item_id", "")).strip()
            matter_id = str(item.get("matter_id", "")).strip()
            if not item_id or not matter_id:
                raise ValueError("WorkItem graph records require item and Matter")
            status = str(item.get("status", "uncertain")).strip()
            if item.get("certainty"):
                default_certainty = str(item["certainty"])
            elif status == "planned":
                default_certainty = "planned"
            elif status == "completed" and (
                item.get("actual_end") or item.get("actual_start")
            ):
                default_certainty = "confirmed_observed"
            elif status in {"in_progress", "waiting", "blocked", "completed"}:
                default_certainty = "reported"
            else:
                default_certainty = "ai_inferred"
            node = self._node(
                node_id=item_id,
                node_type="work_item",
                record=item,
                default_certainty=default_certainty,
                default_confidence=0.7,
                default_expiry=expires_text,
                at=generated,
                attributes={
                    "kind": str(item.get("kind", "action")),
                    "status": status,
                    "title": dict(
                        item.get(
                            "localized_title",
                            item.get("title", {}),
                        )
                    ),
                    "summary": dict(
                        item.get(
                            "localized_summary",
                            item.get("summary", {}),
                        )
                    ),
                    "planned_start": str(item.get("planned_start", "")),
                    "planned_end": str(item.get("planned_end", "")),
                    "actual_start": str(item.get("actual_start", "")),
                    "actual_end": str(item.get("actual_end", "")),
                },
            )
            add_node(node)
            if matter_id not in nodes:
                raise ValueError("WorkItem graph owner Matter is unavailable")
            edge_id = "work-item-edge:" + sha256(
                f"{matter_id}\0{item_id}".encode("utf-8")
            ).hexdigest()[:24]
            edges[edge_id] = SituationEdge(
                edge_id=edge_id,
                source_node_id=matter_id,
                target_node_id=item_id,
                relation_type="has_work_item",
                primary_containment=False,
                certainty=node.certainty,
                confidence=node.confidence,
                evidence_ids=node.evidence_ids,
                alternatives=node.alternatives,
                coverage=node.coverage,
                expires_at=node.expires_at,
                currentness=node.currentness,
            )

        for raw in events:
            item = _record(raw)
            event_id = str(item.get("event_id", "")).strip()
            matter_id = str(item.get("object_ref", "")).strip()
            if not event_id or not matter_id:
                raise ValueError("event graph records require event and Matter")
            node = self._node(
                node_id=event_id,
                node_type="event",
                record=item,
                default_certainty=str(item.get("modality", "inferred")),
                default_confidence=0.6,
                default_expiry=expires_text,
                at=generated,
                attributes={
                    "kind": str(item.get("kind", "event")),
                    "modality": str(item.get("modality", "inferred")),
                    "record_time": str(item.get("record_time", "")),
                    "claimed_time": str(item.get("claimed_time", "")),
                    "sentence": dict(item.get("localized_sentence", {})),
                },
            )
            add_node(node)
            if matter_id not in nodes:
                raise ValueError("event graph owner Matter is unavailable")
            edge_id = "event-edge:" + sha256(
                f"{matter_id}\0{event_id}".encode("utf-8")
            ).hexdigest()[:24]
            edges[edge_id] = SituationEdge(
                edge_id=edge_id,
                source_node_id=matter_id,
                target_node_id=event_id,
                relation_type="has_event",
                primary_containment=False,
                certainty=node.certainty,
                confidence=node.confidence,
                evidence_ids=node.evidence_ids,
                alternatives=node.alternatives,
                coverage=node.coverage,
                expires_at=node.expires_at,
                currentness=node.currentness,
            )

        for raw in relations:
            item = _record(raw)
            source_id = str(item.get("source_matter_id", "")).strip()
            target_id = str(item.get("target_matter_id", "")).strip()
            relation_type = str(item.get("relation_type", "related")).strip()
            if not source_id or not target_id:
                raise ValueError("relationship graph records require both Matters")
            if source_id not in nodes or target_id not in nodes:
                raise ValueError("relationship graph Matter is unavailable")
            evidence_ids = _identities(item.get("evidence_ids", ()))
            relation_id = str(item.get("relation_id", "")).strip() or (
                "relation:"
                + sha256(
                    f"{source_id}\0{relation_type}\0{target_id}".encode("utf-8")
                ).hexdigest()[:24]
            )
            edges[relation_id] = SituationEdge(
                edge_id=relation_id,
                source_node_id=source_id,
                target_node_id=target_id,
                relation_type=relation_type,
                primary_containment=False,
                certainty=certainty_from_modality(
                    item.get("certainty", item.get("modality", "ai_inferred"))
                ),
                confidence=_confidence(item.get("confidence", "uncertain")),
                evidence_ids=evidence_ids,
                alternatives=_identities(
                    item.get(
                        "alternatives",
                        item.get("alternative_explanations", ()),
                    )
                ),
                coverage=_coverage(
                    item.get("coverage", ""),
                    has_evidence=bool(evidence_ids),
                ),
                expires_at=str(item.get("expires_at", "") or expires_text),
                currentness=_currentness(
                    item.get("currentness", item.get("freshness", "current")),
                    expires_at=str(item.get("expires_at", "") or expires_text),
                    at=generated,
                ),
                causal=bool(item.get("causal", False)),
                auto_merge=bool(item.get("auto_merge", False)),
                attributes={"rationale": str(item.get("rationale", ""))},
            )

        ordered_nodes = tuple(
            sorted(nodes.values(), key=lambda item: (item.node_type, item.node_id))
        )
        ordered_edges = tuple(
            sorted(
                edges.values(),
                key=lambda item: (
                    0 if item.primary_containment else 1,
                    item.source_node_id,
                    item.relation_type,
                    item.target_node_id,
                    item.edge_id,
                ),
            )
        )
        coverage_gaps_tuple = _identities(coverage_gaps)
        fingerprint_payload = {
            "schema_version": SITUATION_GRAPH_SCHEMA_VERSION,
            "root_matter_id": root_matter_id,
            "nodes": [asdict(item) for item in ordered_nodes],
            "edges": [asdict(item) for item in ordered_edges],
            "generated_at": generated_text,
            "expires_at": expires_text,
            "coverage": coverage,
            "coverage_gaps": coverage_gaps_tuple,
        }
        input_fingerprint = _fingerprint(fingerprint_payload)
        snapshot_id = (
            "situation-graph:"
            + sha256(
                f"{root_matter_id}\0{input_fingerprint}".encode("utf-8")
            ).hexdigest()[:24]
        )
        return SituationGraphSnapshot(
            snapshot_id=snapshot_id,
            root_matter_id=root_matter_id,
            input_fingerprint=input_fingerprint,
            nodes=ordered_nodes,
            edges=ordered_edges,
            generated_at=generated_text,
            expires_at=expires_text,
            coverage=coverage,
            coverage_gaps=coverage_gaps_tuple,
        )


def situation_graph_snapshot_from_payload(
    payload: Mapping[str, Any],
) -> SituationGraphSnapshot:
    """Restore one validated persisted read-model snapshot."""

    return SituationGraphSnapshot(
        snapshot_id=str(payload.get("snapshot_id", "")),
        root_matter_id=str(payload.get("root_matter_id", "")),
        input_fingerprint=str(payload.get("input_fingerprint", "")),
        nodes=tuple(
            SituationNode(
                node_id=str(item.get("node_id", "")),
                node_type=str(item.get("node_type", "")),
                certainty=str(item.get("certainty", "")),
                confidence=float(item.get("confidence", 0.0) or 0.0),
                evidence_ids=tuple(item.get("evidence_ids", ())),
                alternatives=tuple(item.get("alternatives", ())),
                coverage=str(item.get("coverage", "unknown")),
                expires_at=str(item.get("expires_at", "")),
                currentness=str(item.get("currentness", "current")),
                attributes=dict(item.get("attributes", {})),
            )
            for item in payload.get("nodes", ())
            if isinstance(item, Mapping)
        ),
        edges=tuple(
            SituationEdge(
                edge_id=str(item.get("edge_id", "")),
                source_node_id=str(item.get("source_node_id", "")),
                target_node_id=str(item.get("target_node_id", "")),
                relation_type=str(item.get("relation_type", "")),
                primary_containment=bool(
                    item.get("primary_containment", False)
                ),
                certainty=str(item.get("certainty", "")),
                confidence=float(item.get("confidence", 0.0) or 0.0),
                evidence_ids=tuple(item.get("evidence_ids", ())),
                alternatives=tuple(item.get("alternatives", ())),
                coverage=str(item.get("coverage", "unknown")),
                expires_at=str(item.get("expires_at", "")),
                currentness=str(item.get("currentness", "current")),
                causal=bool(item.get("causal", False)),
                auto_merge=bool(item.get("auto_merge", False)),
                attributes=dict(item.get("attributes", {})),
            )
            for item in payload.get("edges", ())
            if isinstance(item, Mapping)
        ),
        generated_at=str(payload.get("generated_at", "")),
        expires_at=str(payload.get("expires_at", "")),
        coverage=str(payload.get("coverage", "unknown")),
        coverage_gaps=tuple(payload.get("coverage_gaps", ())),
        currentness=str(payload.get("currentness", "current")),
        schema_version=int(
            payload.get("schema_version", SITUATION_GRAPH_SCHEMA_VERSION)
        ),
    )


__all__ = [
    "CERTAINTY_STATES",
    "COVERAGE_STATES",
    "CURRENTNESS_STATES",
    "MAX_GRAPH_PAGE_SIZE",
    "NODE_TYPES",
    "SITUATION_GRAPH_SCHEMA_VERSION",
    "SituationEdge",
    "SituationGraphBuilder",
    "SituationGraphPage",
    "SituationGraphSnapshot",
    "SituationNode",
    "certainty_from_modality",
    "situation_graph_snapshot_from_payload",
]
