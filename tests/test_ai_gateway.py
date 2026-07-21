from __future__ import annotations

from matters.application.ai_gateway import (
    AI_GATEWAY_OWNER_ID,
    MODEL_CONTRACTS,
    MattersAIGateway,
)
from matters.application.orchestrator import MatterService


class FakeStore:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], dict] = {}
        self.appends: list[tuple[str, str, int, dict]] = []

    def current(self, owner: str, object_id: str):
        return self.rows.get((owner, object_id))

    def append(self, owner: str, object_id: str, revision: int, payload):
        row = dict(payload)
        self.appends.append((owner, object_id, revision, row))
        self.rows[(owner, object_id)] = row

    def current_filtered_page(
        self,
        owner: str,
        *,
        json_field: str,
        values: tuple[str, ...],
        offset: int,
        limit: int,
    ):
        rows = tuple(
            payload
            for (row_owner, _), payload in sorted(self.rows.items())
            if row_owner == owner and str(payload.get(json_field, "")) in values
        )
        return rows[offset : offset + limit], len(rows)


def test_ai_gateway_model_map_has_one_noncanonical_a3_entry():
    store = FakeStore()
    gateway = MattersAIGateway(store)

    result = gateway.list_model_contracts(limit=200)
    by_id = {row["model_id"]: row for row in result["items"]}

    assert len(MODEL_CONTRACTS) == 18
    assert set(by_id) >= {
        "M0_matters_end_to_end_authority",
        "C1_authorization_coverage",
        "C12_projection_bilingual_ui",
        "S0_matters_skill_runtime",
        "A0_matters_source_analysis_operation",
        "A1_matters_research_operation",
        "A2_matters_maintenance_orchestrator_operation",
        AI_GATEWAY_OWNER_ID,
    }
    assert by_id[AI_GATEWAY_OWNER_ID]["canonical_writer"] is False
    assert by_id["A1_matters_research_operation"]["research_dependency"] is True
    assert result["query_receipt"]["durable"] is True
    assert store.appends[0][0] == "ai_gateway_query"


def test_ai_gateway_observation_is_minimized_idempotent_and_pending_owner():
    store = FakeStore()
    store.rows[("projection", "matter:1")] = {
        "matter_id": "matter:1",
        "semantic_revision": "semantic:1",
    }
    gateway = MattersAIGateway(store)
    arguments = {
        "matter_id": "matter:1",
        "observation_kind": "event",
        "statement": "The appointment happened.",
        "observed_at": "2026-07-20T12:00:00Z",
        "source_ref": "conversation:codex:opaque",
    }

    first = gateway.record_user_observation(**arguments)
    second = gateway.record_user_observation(**arguments)
    pending = gateway.pending_user_observations(matter_id="matter:1")

    assert first == second
    assert first["modality"] == "reported"
    assert first["dispatch_owner_id"] == "C5_event_temporal_trace"
    assert first["owner_dispatch_disposition"] == (
        "pending_original_owner_validation"
    )
    assert first["full_conversation_stored"] is False
    assert first["canonical_write"] is False
    assert pending["items"] == (first,)
    assert len(
        [row for row in store.appends if row[0] == "ai_user_observation"]
    ) == 1

    store.append(
        "maintenance_ai_feedback_receipt",
        first["observation_id"],
        1,
        {
            "artifact_type": "matters.ai-feedback-owner-terminal.v1",
            "observation_id": first["observation_id"],
            "disposition": "processed",
            "canonical_write": False,
        },
    )
    closed = gateway.pending_user_observations(matter_id="matter:1")
    assert closed["items"] == ()
    assert closed["total_count"] == 0
    assert closed["status"] == "no_pending_feedback"


def test_ai_gateway_rejects_raw_path_or_unbounded_observation():
    store = FakeStore()
    store.rows[("projection", "matter:1")] = {"matter_id": "matter:1"}
    gateway = MattersAIGateway(store)

    try:
        private_path = (
            "C:"
            + chr(92)
            + "Users"
            + chr(92)
            + "person"
            + chr(92)
            + "conversation.txt"
        )
        gateway.record_user_observation(
            matter_id="matter:1",
            observation_kind="fact",
            statement="A bounded statement.",
            observed_at="2026-07-20T12:00:00+00:00",
            source_ref=private_path,
        )
    except ValueError as exc:
        assert "opaque reference" in str(exc)
    else:
        raise AssertionError("raw private path must be rejected")

    try:
        gateway.record_user_observation(
            matter_id="matter:1",
            observation_kind="fact",
            statement="x" * 4_001,
            observed_at="2026-07-20T12:00:00+00:00",
        )
    except ValueError as exc:
        assert "statement" in str(exc)
    else:
        raise AssertionError("unbounded observation must be rejected")


def test_matter_service_persists_gateway_receipts_and_pending_feedback(tmp_path):
    repository_root = tmp_path / "repository"
    repository_root.mkdir()
    service = MatterService(
        private_root=tmp_path / "private",
        repository_root=repository_root,
    )
    assert service.store is not None
    service.store.append(
        "projection",
        "matter:1",
        1,
        {"matter_id": "matter:1", "semantic_revision": "semantic:1"},
    )

    model_map = service.ai_model_contracts(limit=5)
    observation = service.record_user_observation(
        matter_id="matter:1",
        observation_kind="state",
        statement="The work is paused while approval is pending.",
        observed_at="2026-07-20T12:00:00+00:00",
        source_ref="conversation:codex:opaque",
    )
    pending = service.pending_ai_feedback(matter_id="matter:1")

    assert model_map["query_receipt"]["durable"] is True
    assert service.store.current(
        "ai_gateway_query",
        model_map["query_receipt"]["receipt_id"],
    ) is not None
    assert observation["dispatch_owner_id"] == "C7_lifecycle_board_state"
    assert pending["items"] == (observation,)
