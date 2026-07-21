"""A3: bounded AI information-map and append-only feedback gateway."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping, Protocol


AI_GATEWAY_CONTRACT_REVISION = "matters.ai-gateway.v1"
AI_GATEWAY_OWNER_ID = "A3_matters_ai_gateway_operation"
USER_OBSERVATION_OWNER = "ai_user_observation"
MAINTENANCE_FEEDBACK_RECEIPT_OWNER = "maintenance_ai_feedback_receipt"
QUERY_RECEIPT_OWNER = "ai_gateway_query"


class AIGatewayStore(Protocol):
    def current(self, owner: str, object_id: str) -> dict[str, Any] | None: ...

    def append(
        self,
        owner: str,
        object_id: str,
        revision: int,
        payload: Any,
    ) -> None: ...

    def current_filtered_page(
        self,
        owner: str,
        *,
        json_field: str,
        values: tuple[str, ...],
        offset: int,
        limit: int,
    ) -> tuple[tuple[dict[str, Any], ...], int]: ...


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _contract(
    model_id: str,
    *,
    plane: str,
    purpose: str,
    reads: tuple[str, ...],
    outputs: tuple[str, ...],
    operations: tuple[str, ...],
    related: tuple[str, ...],
    canonical_writer: bool,
    research_dependency: bool = False,
) -> dict[str, Any]:
    return {
        "model_id": model_id,
        "plane": plane,
        "purpose": purpose,
        "reads": reads,
        "outputs": outputs,
        "supported_operations": operations,
        "related_model_ids": related,
        "canonical_writer": canonical_writer,
        "research_dependency": research_dependency,
    }


MODEL_CONTRACTS: tuple[dict[str, Any], ...] = (
    _contract(
        "M0_matters_end_to_end_authority",
        plane="product_orchestration",
        purpose="Join current owner receipts and expose one coherent Matter service.",
        reads=("C1-C12 owner receipts",),
        outputs=("joined service currentness", "visible owner gaps"),
        operations=("get_situation_context",),
        related=(
            "C1_authorization_coverage",
            "C2_source_registry",
            "C3_evidence_qualification",
            "C4_person_entity_resolution",
            "C5_event_temporal_trace",
            "C6_matter_formation_admission",
            "C7_lifecycle_board_state",
            "C8_open_loop_waiting_blocking",
            "C9_completion_cancellation_reopen",
            "C10_correction_revocation",
            "C11_guard_artifact_prediction",
            "C12_projection_bilingual_ui",
            "A2_matters_maintenance_orchestrator_operation",
            AI_GATEWAY_OWNER_ID,
        ),
        canonical_writer=False,
    ),
    _contract(
        "C1_authorization_coverage",
        plane="product_runtime",
        purpose="Decide what the user authorized Matters to track.",
        reads=("authorization grants", "inventory occurrences"),
        outputs=("tracked/excluded/blocked dispositions", "coverage scope"),
        operations=("get_coverage", "get_stage_audit"),
        related=("C2_source_registry", "M0_matters_end_to_end_authority"),
        canonical_writer=True,
    ),
    _contract(
        "C2_source_registry",
        plane="product_runtime",
        purpose="Preserve source-in-place locator, fingerprint, and revision provenance.",
        reads=("authorized source observations",),
        outputs=("SourceVersion", "SourceGroup"),
        operations=("list_source_groups", "get_source_group"),
        related=("C1_authorization_coverage", "C3_evidence_qualification"),
        canonical_writer=True,
    ),
    _contract(
        "C3_evidence_qualification",
        plane="product_runtime",
        purpose="Qualify exact evidence anchors without inventing content.",
        reads=("current SourceVersion",),
        outputs=("EvidenceAnchor", "EvidenceGap"),
        operations=("get_evidence",),
        related=("C2_source_registry", "C4_person_entity_resolution", "C5_event_temporal_trace"),
        canonical_writer=True,
    ),
    _contract(
        "C4_person_entity_resolution",
        plane="product_runtime",
        purpose="Resolve people and entities while preserving uncertain identities.",
        reads=("qualified evidence",),
        outputs=("person/entity identities", "scoped roles"),
        operations=("get_matter", "get_situation_context"),
        related=("C3_evidence_qualification", "C6_matter_formation_admission"),
        canonical_writer=True,
    ),
    _contract(
        "C5_event_temporal_trace",
        plane="product_runtime",
        purpose="Maintain event time, modality, chronology, and conflict-preserving history.",
        reads=("qualified evidence", "reported observations"),
        outputs=("Event", "TemporalTrace"),
        operations=("get_ai_history", "get_matter_graph"),
        related=("C3_evidence_qualification", "C6_matter_formation_admission", "C11_guard_artifact_prediction"),
        canonical_writer=True,
    ),
    _contract(
        "C6_matter_formation_admission",
        plane="product_runtime",
        purpose="Own Matter identity, admission, hierarchy, and typed relations.",
        reads=("people", "events", "qualified evidence"),
        outputs=("Matter", "containment", "relations"),
        operations=("list_matters", "get_matter", "get_matter_graph"),
        related=("C4_person_entity_resolution", "C5_event_temporal_trace", "C7_lifecycle_board_state"),
        canonical_writer=True,
    ),
    _contract(
        "C7_lifecycle_board_state",
        plane="product_runtime",
        purpose="Own planned, in-progress, completed, uncertain, and blocked lifecycle state.",
        reads=("Matter evidence", "events", "reported observations"),
        outputs=("LifecycleDecision",),
        operations=("get_matter", "submit_correction"),
        related=("C6_matter_formation_admission", "C10_correction_revocation"),
        canonical_writer=True,
    ),
    _contract(
        "C8_open_loop_waiting_blocking",
        plane="product_runtime",
        purpose="Track waits, unresolved obligations, and scoped blocking.",
        reads=("Matter evidence", "events"),
        outputs=("OpenLoop", "BlockingDecision"),
        operations=("get_matter", "get_situation_context"),
        related=("C7_lifecycle_board_state", "C9_completion_cancellation_reopen"),
        canonical_writer=True,
    ),
    _contract(
        "C9_completion_cancellation_reopen",
        plane="product_runtime",
        purpose="Own outcome, cancellation, completion gaps, conflict, and reopening.",
        reads=("Matter evidence", "events", "open loops"),
        outputs=("OutcomeDecision",),
        operations=("get_matter", "submit_correction"),
        related=("C8_open_loop_waiting_blocking", "C10_correction_revocation"),
        canonical_writer=True,
    ),
    _contract(
        "C10_correction_revocation",
        plane="product_runtime",
        purpose="Append explicit corrections and make every affected owner recompute.",
        reads=("explicit correction", "current owner revisions"),
        outputs=("Revision", "InvalidationPlan", "owner recompute receipts"),
        operations=("submit_correction", "get_ai_history"),
        related=("C5_event_temporal_trace", "C6_matter_formation_admission", "C7_lifecycle_board_state", "C8_open_loop_waiting_blocking", "C9_completion_cancellation_reopen", "C12_projection_bilingual_ui"),
        canonical_writer=True,
    ),
    _contract(
        "C11_guard_artifact_prediction",
        plane="product_runtime",
        purpose="Own advisory AI findings, World Model inference, frozen predictions, and feedback.",
        reads=("current graph/evidence snapshot", "AI operation receipts", "later licensed observations"),
        outputs=("advisory", "prediction", "prediction feedback", "model-miss request"),
        operations=("get_world_model", "record_prediction_feedback"),
        related=("A0_matters_source_analysis_operation", "A1_matters_research_operation", "C5_event_temporal_trace", "C12_projection_bilingual_ui"),
        canonical_writer=True,
        research_dependency=True,
    ),
    _contract(
        "C12_projection_bilingual_ui",
        plane="product_runtime",
        purpose="Publish the bounded bilingual object-browser read model used by humans and AI.",
        reads=("current C1-C11 owner results",),
        outputs=("catalog", "Matter detail", "SituationGraph view", "coverage view"),
        operations=("get_browser", "list_matters", "get_matter", "get_situation_context"),
        related=("M0_matters_end_to_end_authority", "A3_matters_ai_gateway_operation"),
        canonical_writer=True,
    ),
    _contract(
        "S0_matters_skill_runtime",
        plane="skill_runtime",
        purpose="Validate the exact eleven app-local Matters skills and external ResearchGuard currentness.",
        reads=("bundled internal manifest", "portable external dependency receipts"),
        outputs=("internal pack status", "ResearchGuard status"),
        operations=("capabilities",),
        related=("A1_matters_research_operation", "A2_matters_maintenance_orchestrator_operation"),
        canonical_writer=False,
        research_dependency=True,
    ),
    _contract(
        "A0_matters_source_analysis_operation",
        plane="agent_operation",
        purpose="Execute one bounded model-agnostic source analysis package.",
        reads=("declared evidence package",),
        outputs=("typed advisory operation receipt",),
        operations=("list_pending_analysis", "import_autonomous_result"),
        related=("C3_evidence_qualification", "C11_guard_artifact_prediction", "A2_matters_maintenance_orchestrator_operation"),
        canonical_writer=False,
    ),
    _contract(
        "A1_matters_research_operation",
        plane="agent_operation",
        purpose="Execute one abstract research operation through external ResearchGuard only.",
        reads=("declared research package", "portable ResearchGuard currentness"),
        outputs=("research advisory receipt", "visible dependency gap"),
        operations=("capabilities",),
        related=("S0_matters_skill_runtime", "C11_guard_artifact_prediction", "A2_matters_maintenance_orchestrator_operation"),
        canonical_writer=False,
        research_dependency=True,
    ),
    _contract(
        "A2_matters_maintenance_orchestrator_operation",
        plane="agent_operation",
        purpose="Plan, delegate, join, retry, and truthfully finish one bounded maintenance run.",
        reads=("coverage gaps", "registered changes", "pending A3 feedback"),
        outputs=("maintenance plan", "child joins", "terminal maintenance receipt"),
        operations=("run_maintenance", "run_planned_maintenance"),
        related=("A0_matters_source_analysis_operation", "A1_matters_research_operation", "A3_matters_ai_gateway_operation", "M0_matters_end_to_end_authority"),
        canonical_writer=False,
    ),
    _contract(
        AI_GATEWAY_OWNER_ID,
        plane="agent_operation",
        purpose="Give AI one bounded information map and append-only feedback inbox.",
        reads=("C12 projection", "SituationGraph", "World Model", "bounded owner history"),
        outputs=("query receipt", "user observation", "typed owner-dispatch receipt"),
        operations=("list_model_contracts", "get_model_contract", "get_situation_context", "get_ai_history", "record_user_observation", "record_prediction_feedback", "report_model_miss"),
        related=("M0_matters_end_to_end_authority", "C10_correction_revocation", "C11_guard_artifact_prediction", "C12_projection_bilingual_ui", "A2_matters_maintenance_orchestrator_operation"),
        canonical_writer=False,
    ),
)

MODEL_CONTRACT_REVISION = _fingerprint(MODEL_CONTRACTS)

OBSERVATION_OWNER_BY_KIND = {
    "fact": "M0_matters_end_to_end_authority",
    "event": "C5_event_temporal_trace",
    "state": "C7_lifecycle_board_state",
    "outcome": "C9_completion_cancellation_reopen",
    "relationship": "C6_matter_formation_admission",
    "source_gap": "C2_source_registry",
    "other": "M0_matters_end_to_end_authority",
}


def _normalized_time(value: str) -> str:
    normalized = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("observed_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("observed_at must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def _opaque_ref(value: str) -> str:
    normalized = str(value).strip() or "user-report:direct"
    if (
        len(normalized) > 240
        or "\n" in normalized
        or "\r" in normalized
        or "\\" in normalized
        or "/" in normalized
        or normalized.casefold().startswith(("file:", "http:", "https:"))
    ):
        raise ValueError("source_ref must be a short opaque reference")
    return normalized


class MattersAIGateway:
    """A3 receipt owner; it never writes another model's state."""

    def __init__(self, store: AIGatewayStore | None) -> None:
        self.store = store

    def list_model_contracts(
        self,
        *,
        purpose: str = "",
        related_to: str = "",
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        if offset < 0 or limit < 1 or limit > 200:
            raise ValueError("model contract page bounds are invalid")
        query = purpose.strip().casefold()
        rows = tuple(
            dict(row)
            for row in MODEL_CONTRACTS
            if (
                not query
                or query in str(row["purpose"]).casefold()
                or query in " ".join(row["supported_operations"]).casefold()
            )
            and (
                not related_to
                or related_to == row["model_id"]
                or related_to in row["related_model_ids"]
            )
        )
        selected = rows[offset : offset + limit]
        receipt = self.record_query_receipt(
            request_kind="model_map",
            matter_id="",
            request_shape={
                "purpose_filter": bool(query),
                "related_to": related_to,
                "offset": offset,
                "limit": limit,
            },
            result_identity=_fingerprint(selected),
        )
        return {
            "contract_revision": AI_GATEWAY_CONTRACT_REVISION,
            "model_contract_revision": MODEL_CONTRACT_REVISION,
            "items": selected,
            "offset": offset,
            "limit": limit,
            "total_count": len(rows),
            "query_receipt": receipt,
        }

    def get_model_contract(self, model_id: str) -> dict[str, Any]:
        row = next(
            (dict(item) for item in MODEL_CONTRACTS if item["model_id"] == model_id),
            None,
        )
        if row is None:
            raise KeyError("model contract is unavailable")
        receipt = self.record_query_receipt(
            request_kind="model_contract",
            matter_id="",
            request_shape={"model_id": model_id},
            result_identity=_fingerprint(row),
        )
        return {
            "contract_revision": AI_GATEWAY_CONTRACT_REVISION,
            "model_contract_revision": MODEL_CONTRACT_REVISION,
            "contract": row,
            "query_receipt": receipt,
        }

    def record_query_receipt(
        self,
        *,
        request_kind: str,
        matter_id: str,
        request_shape: Mapping[str, Any],
        result_identity: str,
    ) -> dict[str, Any]:
        identity = {
            "contract_revision": AI_GATEWAY_CONTRACT_REVISION,
            "request_kind": request_kind,
            "matter_id": matter_id,
            "request_shape": dict(request_shape),
            "result_identity": result_identity,
        }
        receipt_id = "ai-query:" + _fingerprint(identity).removeprefix("sha256:")[:24]
        payload = {
            "artifact_type": "matters.ai-gateway-query-receipt.v1",
            "receipt_id": receipt_id,
            **identity,
            "status": "current",
            "durable": self.store is not None,
        }
        if self.store is not None and self.store.current(
            QUERY_RECEIPT_OWNER,
            receipt_id,
        ) is None:
            self.store.append(QUERY_RECEIPT_OWNER, receipt_id, 1, payload)
        return payload

    def record_user_observation(
        self,
        *,
        matter_id: str,
        observation_kind: str,
        statement: str,
        observed_at: str,
        source_ref: str = "",
    ) -> dict[str, Any]:
        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for AI feedback")
        if self.store.current("projection", matter_id) is None:
            raise KeyError("matter is unavailable")
        normalized_kind = observation_kind.strip()
        dispatch_owner = OBSERVATION_OWNER_BY_KIND.get(normalized_kind)
        if dispatch_owner is None:
            raise ValueError("observation_kind is invalid")
        normalized_statement = statement.strip()
        if not normalized_statement or len(normalized_statement) > 4_000:
            raise ValueError("observation statement is invalid")
        normalized_observed_at = _normalized_time(observed_at)
        normalized_source_ref = _opaque_ref(source_ref)
        identity = {
            "matter_id": matter_id,
            "observation_kind": normalized_kind,
            "statement": normalized_statement,
            "observed_at": normalized_observed_at,
            "source_ref": normalized_source_ref,
        }
        observation_id = (
            "ai-observation:"
            + _fingerprint(identity).removeprefix("sha256:")[:24]
        )
        payload = {
            "artifact_type": "matters.ai-user-observation.v1",
            "observation_id": observation_id,
            **identity,
            "modality": "reported",
            "gateway_owner_id": AI_GATEWAY_OWNER_ID,
            "dispatch_owner_id": dispatch_owner,
            "owner_dispatch_disposition": "pending_original_owner_validation",
            "status": "pending_owner",
            "full_conversation_stored": False,
            "canonical_write": False,
        }
        current = self.store.current(USER_OBSERVATION_OWNER, observation_id)
        if current is None:
            self.store.append(USER_OBSERVATION_OWNER, observation_id, 1, payload)
        elif current != payload:
            raise ValueError("observation identity collision")
        return payload

    def pending_user_observations(
        self,
        *,
        matter_id: str,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for AI feedback")
        if offset < 0 or limit < 1 or limit > 200:
            raise ValueError("AI feedback page bounds are invalid")
        rows, total = self.store.current_filtered_page(
            USER_OBSERVATION_OWNER,
            json_field="matter_id",
            values=(matter_id,),
            offset=offset,
            limit=limit,
        )
        items = tuple(
            row
            for row in rows
            if str(row.get("status", "")) == "pending_owner"
            and self.store.current(
                MAINTENANCE_FEEDBACK_RECEIPT_OWNER,
                str(row.get("observation_id", "")),
            )
            is None
        )
        terminal_count_on_page = sum(
            1
            for row in rows
            if str(row.get("status", "")) == "pending_owner"
            and self.store.current(
                MAINTENANCE_FEEDBACK_RECEIPT_OWNER,
                str(row.get("observation_id", "")),
            )
            is not None
        )
        return {
            "matter_id": matter_id,
            "items": items,
            "offset": offset,
            "limit": limit,
            "total_count": max(0, total - terminal_count_on_page),
            "status": "pending_owner" if items else "no_pending_feedback",
        }


__all__ = [
    "AI_GATEWAY_CONTRACT_REVISION",
    "AI_GATEWAY_OWNER_ID",
    "MAINTENANCE_FEEDBACK_RECEIPT_OWNER",
    "MODEL_CONTRACT_REVISION",
    "MODEL_CONTRACTS",
    "MattersAIGateway",
]
