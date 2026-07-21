"""Persistent, advisory-only world inference over a SituationGraph snapshot.

This module consumes current C11 ``AgentOperationResult`` findings.  It never
changes canonical Matter hierarchy, lifecycle, outcome, timeline, or evidence
records.  Persisted snapshots are revisioned projections that a caller may
discard whenever their bound SituationGraph fingerprint is no longer current.
"""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Protocol

if TYPE_CHECKING:
    from matters.maintenance.model_miss import ModelMissOwner, ModelMissWorkItem

from matters.analysis.operations import AdvisoryFinding, AgentOperationResult
from matters.application.situation_graph import (
    CERTAINTY_STATES,
    COVERAGE_STATES,
    CURRENTNESS_STATES,
    SituationGraphSnapshot,
    certainty_from_modality,
)


WORLD_MODEL_OWNER = "world_model_advisory"
WORLD_MODEL_FEEDBACK_OWNER = "world_model_feedback"
WORLD_MODEL_SCHEMA_VERSION = 2
MAX_WORLD_ADVISORY_PAGE_SIZE = 200
WORLD_ADVISORY_KINDS = frozenset(
    {
        "prediction",
        "risk",
        "opportunity",
        "plan_assumption",
        "information_gap",
        "recommendation",
        "background_context",
    }
)

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


class WorldModelStore(Protocol):
    """The generic append-only store surface required by this projection."""

    def compare_current_and_append(
        self,
        owner: str,
        object_id: str,
        *,
        is_equivalent: Any,
        payload_factory: Any,
    ) -> dict[str, Any]: ...

    def current(self, owner: str, object_id: str) -> dict[str, Any] | None: ...

    def history(self, owner: str, object_id: str) -> tuple[dict[str, Any], ...]: ...

    def append(
        self,
        owner: str,
        object_id: str,
        revision: int,
        payload: dict[str, Any],
    ) -> Any: ...


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return value.astimezone(timezone.utc).isoformat()


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


def _identities(values: Iterable[object]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(str(item).strip() for item in values if str(item).strip())
    )


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _fingerprint(payload: Any) -> str:
    return "sha256:" + sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _confidence(value: object) -> float:
    if isinstance(value, bool):
        return 0.4
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
                result = 0.4
    return max(0.0, min(1.0, result))


def _prediction_contract(
    attributes: Mapping[str, Any],
    *,
    expires_at: str,
) -> dict[str, Any]:
    """Validate one frozen, advisory-only future prediction contract."""

    required_text = (
        "verification_condition",
        "contradiction_condition",
        "expected_by",
    )
    normalized = dict(attributes)
    missing = tuple(
        field_name
        for field_name in required_text
        if not str(normalized.get(field_name, "")).strip()
    )
    if missing:
        raise ValueError(
            "future prediction requires " + ", ".join(missing)
        )
    if normalized.get("retrospective_review_on_conflict") is not True:
        raise ValueError(
            "future prediction must require retrospective model review on conflict"
        )
    if normalized.get("canonical_write_allowed", False) is not False:
        raise ValueError("future prediction cannot permit canonical writes")
    weakening = normalized.get("weakening_conditions", ())
    if isinstance(weakening, (str, bytes)) or not isinstance(
        weakening, Iterable
    ):
        raise ValueError("future prediction weakening_conditions must be a list")
    weakening_conditions = _identities(weakening)
    if not weakening_conditions:
        raise ValueError("future prediction requires weakening conditions")
    expected_by = _parse_timestamp(
        str(normalized["expected_by"]),
        "prediction expected_by",
    )
    expiry = _parse_timestamp(expires_at, "prediction expires_at")
    if expected_by > expiry:
        raise ValueError("prediction expected_by cannot follow expiry")
    frozen_at = str(normalized.get("prediction_frozen_at", "")).strip()
    if not frozen_at:
        raise ValueError("future prediction requires prediction_frozen_at")
    frozen = _parse_timestamp(frozen_at, "prediction_frozen_at")
    if expected_by <= frozen:
        raise ValueError("future prediction horizon must follow its freeze time")
    normalized.update(
        {
            "prediction_frozen_at": _timestamp(frozen),
            "expected_by": _timestamp(expected_by),
            "weakening_conditions": weakening_conditions,
            "retrospective_review_on_conflict": True,
            "canonical_write_allowed": False,
            "projection_surface": "world_model_only",
        }
    )
    return normalized


def _effective_currentness(
    currentness: str,
    *,
    expires_at: str,
    at: datetime,
) -> str:
    if currentness != "current":
        return currentness
    if _parse_timestamp(expires_at, "expires_at") <= at:
        return "expired"
    return "current"


def _cursor(
    *,
    model_fingerprint: str,
    revision: int,
    offset: int,
) -> str:
    payload = _canonical_json(
        {
            "model_fingerprint": model_fingerprint,
            "revision": revision,
            "offset": offset,
        }
    ).encode("utf-8")
    return urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _cursor_offset(
    continuation: str,
    *,
    model_fingerprint: str,
    revision: int,
) -> int:
    if not continuation:
        return 0
    try:
        padded = continuation + ("=" * (-len(continuation) % 4))
        payload = json.loads(urlsafe_b64decode(padded.encode("ascii")))
        if (
            str(payload["model_fingerprint"]) != model_fingerprint
            or int(payload["revision"]) != revision
        ):
            raise ValueError("continuation belongs to another world model revision")
        offset = int(payload["offset"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith(
            "continuation belongs"
        ):
            raise
        raise ValueError("invalid world model continuation") from exc
    if offset < 0:
        raise ValueError("invalid world model continuation")
    return offset


@dataclass(frozen=True)
class WorldAdvisory:
    advisory_id: str
    kind: str
    statement: str
    localized_statement: Mapping[str, str]
    certainty: str
    confidence: float
    evidence_ids: tuple[str, ...]
    alternatives: tuple[str, ...] = ()
    coverage: str = "partial"
    expires_at: str = ""
    currentness: str = "current"
    source_result_id: str = ""
    source_finding_id: str = ""
    graph_fingerprint: str = ""
    attributes: Mapping[str, Any] = field(default_factory=dict)
    advisory_only: bool = field(default=True, init=False)
    canonical_write_allowed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        advisory_id = str(self.advisory_id).strip()
        kind = str(self.kind).strip()
        statement = str(self.statement).strip()
        certainty = str(self.certainty).strip()
        coverage = str(self.coverage).strip()
        currentness = str(self.currentness).strip()
        evidence_ids = _identities(self.evidence_ids)
        alternatives = _identities(self.alternatives)
        localized = {
            str(key).strip(): str(value).strip()
            for key, value in self.localized_statement.items()
            if str(key).strip() and str(value).strip()
        }
        if not advisory_id or not statement:
            raise ValueError("world advisory identity and statement are required")
        if kind not in WORLD_ADVISORY_KINDS:
            raise ValueError(f"unsupported world advisory kind: {kind}")
        if certainty not in CERTAINTY_STATES:
            raise ValueError("unsupported world advisory certainty")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("world advisory confidence must be between zero and one")
        if not evidence_ids:
            raise ValueError("world advisory requires graph-bound evidence")
        if coverage not in COVERAGE_STATES:
            raise ValueError("unsupported world advisory coverage")
        if currentness not in CURRENTNESS_STATES:
            raise ValueError("unsupported world advisory currentness")
        if not self.source_result_id or not self.source_finding_id:
            raise ValueError("world advisory source result and finding are required")
        if not self.graph_fingerprint.startswith("sha256:"):
            raise ValueError("world advisory graph fingerprint is required")
        _parse_timestamp(self.expires_at, "expires_at")
        attributes = dict(self.attributes)
        if kind == "prediction":
            attributes = _prediction_contract(
                attributes,
                expires_at=self.expires_at,
            )
        object.__setattr__(self, "advisory_id", advisory_id)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "statement", statement)
        object.__setattr__(self, "localized_statement", localized)
        object.__setattr__(self, "certainty", certainty)
        object.__setattr__(self, "confidence", float(self.confidence))
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "alternatives", alternatives)
        object.__setattr__(self, "coverage", coverage)
        object.__setattr__(self, "currentness", currentness)
        object.__setattr__(self, "attributes", attributes)

    def effective_currentness(self, *, at: datetime | None = None) -> str:
        return _effective_currentness(
            self.currentness,
            expires_at=self.expires_at,
            at=(at or _utc_now()).astimezone(timezone.utc),
        )


@dataclass(frozen=True)
class WorldAdvisoryPage:
    matter_id: str
    revision: int
    graph_fingerprint: str
    model_fingerprint: str
    advisories: tuple[WorldAdvisory, ...]
    offset: int
    limit: int
    total_count: int
    next_continuation: str
    has_more: bool
    coverage: str
    coverage_gaps: tuple[str, ...]
    currentness: str
    expires_at: str


@dataclass(frozen=True)
class WorldModelSnapshot:
    matter_id: str
    revision: int
    graph_fingerprint: str
    source_fingerprint: str
    model_fingerprint: str
    generated_at: str
    expires_at: str
    coverage: str
    coverage_gaps: tuple[str, ...]
    advisories: tuple[WorldAdvisory, ...]
    source_result_ids: tuple[str, ...]
    currentness: str = "current"
    schema_version: int = WORLD_MODEL_SCHEMA_VERSION
    advisory_only: bool = field(default=True, init=False)
    canonical_write_allowed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        advisories = tuple(self.advisories)
        advisory_ids = tuple(item.advisory_id for item in advisories)
        coverage_gaps = _identities(self.coverage_gaps)
        source_result_ids = _identities(self.source_result_ids)
        if not self.matter_id or self.revision < 1:
            raise ValueError("world model identity and positive revision are required")
        for value, label in (
            (self.graph_fingerprint, "graph"),
            (self.source_fingerprint, "source"),
            (self.model_fingerprint, "model"),
        ):
            if not value.startswith("sha256:"):
                raise ValueError(f"world model {label} fingerprint is required")
        if len(advisory_ids) != len(set(advisory_ids)):
            raise ValueError("world advisory identities must be unique")
        if any(
            advisory.graph_fingerprint != self.graph_fingerprint
            for advisory in advisories
        ):
            raise ValueError("world advisories must bind the snapshot graph")
        if self.coverage not in COVERAGE_STATES:
            raise ValueError("unsupported world model coverage")
        if self.coverage == "complete" and coverage_gaps:
            raise ValueError("complete world model cannot retain coverage gaps")
        if self.currentness not in CURRENTNESS_STATES:
            raise ValueError("unsupported world model currentness")
        generated = _parse_timestamp(self.generated_at, "generated_at")
        expires = _parse_timestamp(self.expires_at, "expires_at")
        if expires <= generated:
            raise ValueError("world model expiry must follow generation")
        if self.schema_version != WORLD_MODEL_SCHEMA_VERSION:
            raise ValueError("unsupported world model schema version")
        object.__setattr__(self, "advisories", advisories)
        object.__setattr__(self, "coverage_gaps", coverage_gaps)
        object.__setattr__(self, "source_result_ids", source_result_ids)

    def effective_currentness(
        self,
        *,
        expected_graph_fingerprint: str,
        at: datetime | None = None,
    ) -> str:
        if expected_graph_fingerprint != self.graph_fingerprint:
            return "stale"
        return _effective_currentness(
            self.currentness,
            expires_at=self.expires_at,
            at=(at or _utc_now()).astimezone(timezone.utc),
        )

    def view(
        self,
        *,
        expected_graph_fingerprint: str,
        at: datetime | None = None,
    ) -> "WorldModelSnapshot":
        effective = self.effective_currentness(
            expected_graph_fingerprint=expected_graph_fingerprint,
            at=at,
        )
        return replace(
            self,
            currentness=effective,
            advisories=tuple(
                replace(
                    item,
                    currentness=(
                        "stale"
                        if expected_graph_fingerprint != self.graph_fingerprint
                        else item.effective_currentness(at=at)
                    ),
                )
                for item in self.advisories
            ),
        )

    def page(
        self,
        *,
        continuation: str = "",
        limit: int = 50,
        expected_graph_fingerprint: str,
        at: datetime | None = None,
    ) -> WorldAdvisoryPage:
        if limit < 1 or limit > MAX_WORLD_ADVISORY_PAGE_SIZE:
            raise ValueError("world advisory page bounds are invalid")
        offset = _cursor_offset(
            continuation,
            model_fingerprint=self.model_fingerprint,
            revision=self.revision,
        )
        if offset > len(self.advisories):
            raise ValueError("world model continuation is outside the snapshot")
        view = self.view(
            expected_graph_fingerprint=expected_graph_fingerprint,
            at=at,
        )
        ordered = tuple(
            sorted(
                view.advisories,
                key=lambda item: (
                    item.kind,
                    item.advisory_id,
                ),
            )
        )
        page_items = ordered[offset : offset + limit]
        next_offset = offset + len(page_items)
        has_more = next_offset < len(ordered)
        return WorldAdvisoryPage(
            matter_id=self.matter_id,
            revision=self.revision,
            graph_fingerprint=self.graph_fingerprint,
            model_fingerprint=self.model_fingerprint,
            advisories=page_items,
            offset=offset,
            limit=limit,
            total_count=len(ordered),
            next_continuation=(
                _cursor(
                    model_fingerprint=self.model_fingerprint,
                    revision=self.revision,
                    offset=next_offset,
                )
                if has_more
                else ""
            ),
            has_more=has_more,
            coverage=self.coverage,
            coverage_gaps=self.coverage_gaps,
            currentness=view.currentness,
            expires_at=self.expires_at,
        )


@dataclass(frozen=True)
class WorldPredictionFeedback:
    feedback_id: str
    matter_id: str
    advisory_id: str
    disposition: str
    observed_at: str
    observation_statement: str
    observation_evidence_ids: tuple[str, ...]
    prediction_model_fingerprint: str
    prediction_graph_fingerprint: str
    observation_graph_fingerprint: str
    model_miss_required: bool
    model_miss_id: str = ""
    advisory_only: bool = field(default=True, init=False)
    canonical_write_allowed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self.disposition not in {"confirmed", "contradicted", "unresolved"}:
            raise ValueError("unsupported prediction feedback disposition")
        if not self.feedback_id or not self.matter_id or not self.advisory_id:
            raise ValueError("prediction feedback identity is required")
        _parse_timestamp(self.observed_at, "prediction observed_at")
        evidence_ids = _identities(self.observation_evidence_ids)
        if self.disposition != "unresolved" and not evidence_ids:
            raise ValueError(
                "decisive prediction feedback requires licensed observation evidence"
            )
        if not self.observation_statement.strip():
            raise ValueError("prediction feedback statement is required")
        for value in (
            self.prediction_model_fingerprint,
            self.prediction_graph_fingerprint,
            self.observation_graph_fingerprint,
        ):
            if not str(value).startswith("sha256:"):
                raise ValueError("prediction feedback fingerprints are required")
        if self.model_miss_required != (self.disposition == "contradicted"):
            raise ValueError(
                "only contradicted prediction feedback requires model-miss review"
            )
        object.__setattr__(self, "observation_evidence_ids", evidence_ids)


def _advisory_from_payload(payload: Mapping[str, Any]) -> WorldAdvisory:
    return WorldAdvisory(
        advisory_id=str(payload.get("advisory_id", "")),
        kind=str(payload.get("kind", "")),
        statement=str(payload.get("statement", "")),
        localized_statement=dict(payload.get("localized_statement", {})),
        certainty=str(payload.get("certainty", "")),
        confidence=float(payload.get("confidence", 0.0)),
        evidence_ids=tuple(payload.get("evidence_ids", ())),
        alternatives=tuple(payload.get("alternatives", ())),
        coverage=str(payload.get("coverage", "")),
        expires_at=str(payload.get("expires_at", "")),
        currentness=str(payload.get("currentness", "")),
        source_result_id=str(payload.get("source_result_id", "")),
        source_finding_id=str(payload.get("source_finding_id", "")),
        graph_fingerprint=str(payload.get("graph_fingerprint", "")),
        attributes=dict(payload.get("attributes", {})),
    )


def _snapshot_from_payload(payload: Mapping[str, Any]) -> WorldModelSnapshot:
    return WorldModelSnapshot(
        matter_id=str(payload.get("matter_id", "")),
        revision=int(payload.get("revision", 0)),
        graph_fingerprint=str(payload.get("graph_fingerprint", "")),
        source_fingerprint=str(payload.get("source_fingerprint", "")),
        model_fingerprint=str(payload.get("model_fingerprint", "")),
        generated_at=str(payload.get("generated_at", "")),
        expires_at=str(payload.get("expires_at", "")),
        coverage=str(payload.get("coverage", "")),
        coverage_gaps=tuple(payload.get("coverage_gaps", ())),
        advisories=tuple(
            _advisory_from_payload(item)
            for item in payload.get("advisories", ())
        ),
        source_result_ids=tuple(payload.get("source_result_ids", ())),
        currentness=str(payload.get("currentness", "current")),
        schema_version=int(
            payload.get("schema_version", WORLD_MODEL_SCHEMA_VERSION)
        ),
    )


@dataclass
class PersistentAdvisoryWorldModel:
    store: WorldModelStore
    owner: str = WORLD_MODEL_OWNER

    @staticmethod
    def _accept_result(
        result: AgentOperationResult,
        *,
        graph: SituationGraphSnapshot,
        expires_at: str,
    ) -> tuple[WorldAdvisory, ...]:
        if result.status != "passed":
            raise ValueError("world model requires a passed C11 operation result")
        if not result.advisory_only:
            raise ValueError("world model rejects non-advisory operation results")
        if not result.receipt_current:
            raise ValueError("world model requires a current operation receipt")

        graph_evidence = set(graph.evidence_ids)
        advisories: list[WorldAdvisory] = []
        for finding in result.findings:
            attributes = dict(finding.attributes)
            kind = str(attributes.get("world_advisory_kind", "")).strip()
            bound_graph = str(
                attributes.get("situation_graph_fingerprint", "")
            ).strip()
            if kind not in WORLD_ADVISORY_KINDS:
                raise ValueError(
                    "C11 finding lacks a supported world_advisory_kind"
                )
            if bound_graph != graph.input_fingerprint:
                raise ValueError("C11 finding targets another SituationGraph")
            evidence_ids = _identities(finding.evidence_ids)
            if not evidence_ids:
                raise ValueError("world inference requires finding evidence")
            if not set(evidence_ids).issubset(graph_evidence):
                raise ValueError(
                    "world inference finding references evidence outside the graph"
                )
            finding_expires = str(attributes.get("expires_at", "")).strip()
            if finding_expires:
                expiry = min(
                    _parse_timestamp(finding_expires, "finding expires_at"),
                    _parse_timestamp(expires_at, "snapshot expires_at"),
                )
                finding_expires = _timestamp(expiry)
            else:
                finding_expires = expires_at
            coverage = str(attributes.get("coverage", graph.coverage)).strip()
            if coverage not in COVERAGE_STATES:
                raise ValueError("unsupported finding coverage")
            certainty = certainty_from_modality(finding.modality)
            advisory_id = (
                str(finding.finding_id).strip()
                or "world-advisory:"
                + sha256(
                    (
                        f"{result.result_id}\0{kind}\0{finding.statement}"
                    ).encode("utf-8")
                ).hexdigest()[:24]
            )
            advisories.append(
                WorldAdvisory(
                    advisory_id=advisory_id,
                    kind=kind,
                    statement=finding.statement,
                    localized_statement=finding.localized_statement,
                    certainty=certainty,
                    confidence=_confidence(finding.confidence),
                    evidence_ids=evidence_ids,
                    alternatives=finding.alternative_explanations,
                    coverage=coverage,
                    expires_at=finding_expires,
                    currentness="current",
                    source_result_id=result.result_id,
                    source_finding_id=finding.finding_id or advisory_id,
                    graph_fingerprint=graph.input_fingerprint,
                    attributes={
                        **attributes,
                        "finding_type": finding.finding_type,
                        "owner_model_id": finding.owner_model_id,
                        "semantic_revision": finding.semantic_revision,
                        "uncertainty_codes": tuple(finding.uncertainty_codes),
                    },
                )
            )
        return tuple(advisories)

    def publish(
        self,
        *,
        matter_id: str,
        graph: SituationGraphSnapshot,
        results: Iterable[AgentOperationResult],
        generated_at: datetime | None = None,
        ttl: timedelta = timedelta(days=7),
        coverage_gaps: Iterable[str] = (),
    ) -> WorldModelSnapshot:
        """Validate and persist one current advisory projection revision."""

        matter_id = str(matter_id).strip()
        if not matter_id or matter_id != graph.root_matter_id:
            raise ValueError("world model matter must match the graph root")
        if ttl <= timedelta(0):
            raise ValueError("world model ttl must be positive")
        generated = (generated_at or _utc_now()).astimezone(timezone.utc)
        if graph.effective_currentness(at=generated) != "current":
            raise ValueError("world model requires a current SituationGraph")
        expires = min(
            generated + ttl,
            _parse_timestamp(graph.expires_at, "graph expires_at"),
        )
        if expires <= generated:
            raise ValueError("world model expiry must follow generation")
        expires_at = _timestamp(expires)
        ordered_results = tuple(sorted(results, key=lambda item: item.result_id))
        advisories = tuple(
            sorted(
                (
                    advisory
                    for result in ordered_results
                    for advisory in self._accept_result(
                        result,
                        graph=graph,
                        expires_at=expires_at,
                    )
                ),
                key=lambda item: (item.kind, item.advisory_id),
            )
        )
        advisory_ids = tuple(item.advisory_id for item in advisories)
        if len(advisory_ids) != len(set(advisory_ids)):
            raise ValueError("C11 results produced duplicate world advisory ids")
        gaps = _identities((*graph.coverage_gaps, *coverage_gaps))
        coverage = graph.coverage
        if gaps and coverage == "complete":
            coverage = "partial"
        source_result_ids = _identities(
            result.result_id for result in ordered_results
        )
        source_payload = {
            "schema_version": WORLD_MODEL_SCHEMA_VERSION,
            "matter_id": matter_id,
            "graph_fingerprint": graph.input_fingerprint,
            "advisories": [asdict(item) for item in advisories],
            "source_result_ids": source_result_ids,
            "coverage": coverage,
            "coverage_gaps": gaps,
            "expires_at": expires_at,
        }
        source_fingerprint = _fingerprint(source_payload)
        model_fingerprint = _fingerprint(
            {
                "source_fingerprint": source_fingerprint,
                "advisory_ids": advisory_ids,
            }
        )

        def equivalent(current: dict[str, Any] | None) -> bool:
            return bool(
                current
                and str(current.get("source_fingerprint", ""))
                == source_fingerprint
                and str(current.get("model_fingerprint", ""))
                == model_fingerprint
            )

        def payload_factory(
            revision: int,
            _current: dict[str, Any] | None,
        ) -> dict[str, Any]:
            return asdict(
                WorldModelSnapshot(
                    matter_id=matter_id,
                    revision=revision,
                    graph_fingerprint=graph.input_fingerprint,
                    source_fingerprint=source_fingerprint,
                    model_fingerprint=model_fingerprint,
                    generated_at=_timestamp(generated),
                    expires_at=expires_at,
                    coverage=coverage,
                    coverage_gaps=gaps,
                    advisories=advisories,
                    source_result_ids=source_result_ids,
                )
            )

        saved = self.store.compare_current_and_append(
            self.owner,
            matter_id,
            is_equivalent=equivalent,
            payload_factory=payload_factory,
        )
        return _snapshot_from_payload(saved["payload"])

    def current(
        self,
        *,
        matter_id: str,
        expected_graph_fingerprint: str,
        at: datetime | None = None,
    ) -> WorldModelSnapshot | None:
        payload = self.store.current(self.owner, matter_id)
        if payload is None:
            return None
        return _snapshot_from_payload(payload).view(
            expected_graph_fingerprint=expected_graph_fingerprint,
            at=at,
        )

    def history(self, matter_id: str) -> tuple[WorldModelSnapshot, ...]:
        return tuple(
            _snapshot_from_payload(payload)
            for payload in self.store.history(self.owner, matter_id)
        )

    def evaluate_prediction(
        self,
        *,
        matter_id: str,
        advisory_id: str,
        disposition: str,
        observed_at: datetime,
        observation_statement: str,
        observation_evidence_ids: Iterable[str],
        observation_graph_fingerprint: str,
        model_miss_owner: "ModelMissOwner | None" = None,
    ) -> WorldPredictionFeedback:
        """Append empirical feedback and queue review for contradictions.

        The feedback never writes the observed fact.  Its caller must still
        route licensed observations through the original C3-C9 owner.
        """

        payload = self.store.current(self.owner, matter_id)
        if payload is None:
            raise ValueError("prediction feedback requires a current world model")
        snapshot = _snapshot_from_payload(payload)
        prediction = next(
            (
                advisory
                for advisory in snapshot.advisories
                if advisory.advisory_id == advisory_id
            ),
            None,
        )
        if prediction is None or prediction.kind != "prediction":
            raise ValueError("prediction feedback requires a frozen prediction")
        observed = observed_at.astimezone(timezone.utc)
        frozen_at = _parse_timestamp(
            str(prediction.attributes.get("prediction_frozen_at", "")),
            "prediction_frozen_at",
        )
        if observed <= frozen_at:
            raise ValueError("prediction observation must follow the frozen prediction")
        evidence_ids = _identities(observation_evidence_ids)
        feedback_id = "world-feedback:" + sha256(
            _canonical_json(
                {
                    "matter_id": matter_id,
                    "advisory_id": advisory_id,
                    "disposition": disposition,
                    "observed_at": _timestamp(observed),
                    "observation_statement": observation_statement,
                    "observation_evidence_ids": evidence_ids,
                    "observation_graph_fingerprint": observation_graph_fingerprint,
                }
            ).encode("utf-8")
        ).hexdigest()[:24]
        model_miss_id = ""
        if disposition == "contradicted" and model_miss_owner is not None:
            miss = model_miss_owner.report(
                failure_class="world_prediction_contradicted",
                expected_behavior=(
                    "the frozen future prediction should remain empirically "
                    "consistent with later licensed observations"
                ),
                observed_behavior=(
                    f"prediction {advisory_id} contradicted by feedback "
                    f"{feedback_id}; review the original evidence, grouping, "
                    "temporal interpretation, and model boundary"
                ),
                model_path="flowguard_models/models/c11_guard_prediction.py",
                private_evidence_handle=f"private-evidence:{feedback_id}",
                current_runtime_disposition="partial",
            )
            model_miss_id = miss.miss_id
        feedback = WorldPredictionFeedback(
            feedback_id=feedback_id,
            matter_id=matter_id,
            advisory_id=advisory_id,
            disposition=disposition,
            observed_at=_timestamp(observed),
            observation_statement=str(observation_statement).strip(),
            observation_evidence_ids=evidence_ids,
            prediction_model_fingerprint=snapshot.model_fingerprint,
            prediction_graph_fingerprint=snapshot.graph_fingerprint,
            observation_graph_fingerprint=observation_graph_fingerprint,
            model_miss_required=disposition == "contradicted",
            model_miss_id=model_miss_id,
        )
        if self.store.current(WORLD_MODEL_FEEDBACK_OWNER, feedback_id) is None:
            self.store.append(
                WORLD_MODEL_FEEDBACK_OWNER,
                feedback_id,
                1,
                asdict(feedback),
            )
        return feedback

    @staticmethod
    def write_canonical(*_args: Any, **_kwargs: Any) -> None:
        raise PermissionError(
            "the World Model is advisory-only and cannot write canonical state"
        )


__all__ = [
    "MAX_WORLD_ADVISORY_PAGE_SIZE",
    "PersistentAdvisoryWorldModel",
    "WORLD_ADVISORY_KINDS",
    "WORLD_MODEL_FEEDBACK_OWNER",
    "WORLD_MODEL_OWNER",
    "WORLD_MODEL_SCHEMA_VERSION",
    "WorldAdvisory",
    "WorldAdvisoryPage",
    "WorldModelSnapshot",
    "WorldModelStore",
    "WorldPredictionFeedback",
]
