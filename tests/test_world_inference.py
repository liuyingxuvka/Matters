from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from matters.analysis.operations import AdvisoryFinding, AgentOperationResult
from matters.analysis.world_inference import (
    PersistentAdvisoryWorldModel,
    WORLD_MODEL_FEEDBACK_OWNER,
    WORLD_MODEL_OWNER,
)
from matters.application.situation_graph import SituationGraphBuilder
from matters.infrastructure.sqlite.store import SQLiteStore


NOW = datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)


def _store(tmp_path: Path) -> SQLiteStore:
    repository = tmp_path / "repository"
    repository.mkdir()
    return SQLiteStore(tmp_path / "private", repository)


def _graph(*, evidence_id: str = "e-root"):
    return SituationGraphBuilder().build(
        root_matter_id="matter:job-search",
        matter_records=(
            {
                "matter_id": "matter:job-search",
                "evidence_ids": (evidence_id,),
                "certainty": "reported",
            },
        ),
        generated_at=NOW,
        expires_at=NOW + timedelta(days=10),
    )


def _result(
    graph_fingerprint: str,
    *,
    result_id: str = "result:1",
    finding_id: str = "advisory:reply-risk",
    evidence_id: str = "e-root",
    kind: str = "risk",
) -> AgentOperationResult:
    prediction_attributes = (
        {
            "prediction_frozen_at": NOW.isoformat(),
            "expected_by": (NOW + timedelta(days=2)).isoformat(),
            "verification_condition": "A licensed later result records success.",
            "contradiction_condition": "A licensed later result records failure.",
            "weakening_conditions": (
                "The covered source scope is incomplete.",
                "The project plan changes before the horizon.",
            ),
            "retrospective_review_on_conflict": True,
            "canonical_write_allowed": False,
        }
        if kind == "prediction"
        else {}
    )
    return AgentOperationResult(
        result_id=result_id,
        package_id=f"package:{result_id}",
        package_version=1,
        package_input_fingerprint="sha256:package-input",
        provider_id="codex-agent",
        provider_version="5.6",
        status="passed",
        findings=(
            AdvisoryFinding(
                finding_id=finding_id,
                finding_type="world_inference",
                owner_model_id="C11_advisory_ai",
                statement="The application may need a follow-up this week.",
                localized_statement={
                    "en": "The application may need a follow-up this week.",
                    "zh-CN": "本周可能需要跟进这份申请。",
                },
                evidence_ids=(evidence_id,),
                confidence="bounded",
                modality="inferred",
                alternative_explanations=(
                    "The employer may still be reviewing candidates.",
                ),
                attributes={
                    "world_advisory_kind": kind,
                    "situation_graph_fingerprint": graph_fingerprint,
                    **prediction_attributes,
                },
            ),
        ),
        advisory_only=True,
        receipt_current=True,
    )


def test_world_model_persists_idempotently_and_survives_restart(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    graph = _graph()
    model = PersistentAdvisoryWorldModel(store)
    result = _result(graph.input_fingerprint)

    first = model.publish(
        matter_id=graph.root_matter_id,
        graph=graph,
        results=(result,),
        generated_at=NOW,
        ttl=timedelta(days=7),
    )
    repeated = model.publish(
        matter_id=graph.root_matter_id,
        graph=graph,
        results=(result,),
        generated_at=NOW,
        ttl=timedelta(days=7),
    )

    assert first.revision == repeated.revision == 1
    assert first.advisory_only is True
    assert first.canonical_write_allowed is False
    assert first.advisories[0].certainty == "ai_inferred"
    assert first.advisories[0].confidence == pytest.approx(0.65)
    assert first.advisories[0].evidence_ids == ("e-root",)
    assert len(store.history(WORLD_MODEL_OWNER, graph.root_matter_id)) == 1

    restarted = PersistentAdvisoryWorldModel(
        SQLiteStore(tmp_path / "private", tmp_path / "repository")
    )
    current = restarted.current(
        matter_id=graph.root_matter_id,
        expected_graph_fingerprint=graph.input_fingerprint,
        at=NOW,
    )
    assert current is not None
    assert current.model_fingerprint == first.model_fingerprint


def test_world_model_revision_and_paging_are_bound_to_current_inputs(
    tmp_path: Path,
) -> None:
    model = PersistentAdvisoryWorldModel(_store(tmp_path))
    graph = _graph()
    first = model.publish(
        matter_id=graph.root_matter_id,
        graph=graph,
        results=(
            _result(graph.input_fingerprint),
            _result(
                graph.input_fingerprint,
                result_id="result:2",
                finding_id="advisory:opportunity",
                kind="opportunity",
            ),
        ),
        generated_at=NOW,
    )
    page = first.page(
        limit=1,
        expected_graph_fingerprint=graph.input_fingerprint,
        at=NOW,
    )
    assert page.has_more is True

    second = model.publish(
        matter_id=graph.root_matter_id,
        graph=graph,
        results=(
            _result(
                graph.input_fingerprint,
                result_id="result:3",
                finding_id="advisory:recommendation",
                kind="recommendation",
            ),
        ),
        generated_at=NOW,
    )
    assert second.revision == 2
    with pytest.raises(ValueError, match="another world model revision"):
        second.page(
            continuation=page.next_continuation,
            limit=1,
            expected_graph_fingerprint=graph.input_fingerprint,
            at=NOW,
        )


def test_world_model_marks_graph_mismatch_and_expiry_without_writing(
    tmp_path: Path,
) -> None:
    model = PersistentAdvisoryWorldModel(_store(tmp_path))
    graph = _graph()
    snapshot = model.publish(
        matter_id=graph.root_matter_id,
        graph=graph,
        results=(_result(graph.input_fingerprint),),
        generated_at=NOW,
        ttl=timedelta(days=2),
    )

    stale = model.current(
        matter_id=graph.root_matter_id,
        expected_graph_fingerprint="sha256:another-graph",
        at=NOW,
    )
    expired = model.current(
        matter_id=graph.root_matter_id,
        expected_graph_fingerprint=graph.input_fingerprint,
        at=NOW + timedelta(days=3),
    )

    assert stale is not None and stale.currentness == "stale"
    assert stale.advisories[0].currentness == "stale"
    assert expired is not None and expired.currentness == "expired"
    assert expired.advisories[0].currentness == "expired"
    assert snapshot.currentness == "current"
    assert len(model.history(graph.root_matter_id)) == 1


@pytest.mark.parametrize(
    "mutate, error",
    (
        (lambda value: replace(value, status="failed"), "passed"),
        (lambda value: replace(value, advisory_only=False), "non-advisory"),
        (lambda value: replace(value, receipt_current=False), "current"),
    ),
)
def test_world_model_rejects_unusable_c11_results(
    tmp_path: Path,
    mutate,
    error: str,
) -> None:
    graph = _graph()
    result = mutate(_result(graph.input_fingerprint))

    with pytest.raises(ValueError, match=error):
        PersistentAdvisoryWorldModel(_store(tmp_path)).publish(
            matter_id=graph.root_matter_id,
            graph=graph,
            results=(result,),
            generated_at=NOW,
        )


def test_world_model_rejects_unbound_evidence_and_canonical_writes(
    tmp_path: Path,
) -> None:
    graph = _graph()
    model = PersistentAdvisoryWorldModel(_store(tmp_path))

    with pytest.raises(ValueError, match="outside the graph"):
        model.publish(
            matter_id=graph.root_matter_id,
            graph=graph,
            results=(
                _result(
                    graph.input_fingerprint,
                    evidence_id="e-foreign",
                ),
            ),
            generated_at=NOW,
        )
    with pytest.raises(PermissionError, match="advisory-only"):
        model.write_canonical(
            matter_id=graph.root_matter_id,
            lifecycle="completed",
        )


def test_future_prediction_is_frozen_testable_and_never_canonical(
    tmp_path: Path,
) -> None:
    graph = _graph()
    model = PersistentAdvisoryWorldModel(_store(tmp_path))
    snapshot = model.publish(
        matter_id=graph.root_matter_id,
        graph=graph,
        results=(_result(graph.input_fingerprint, kind="prediction"),),
        generated_at=NOW,
    )

    prediction = snapshot.advisories[0]
    assert prediction.kind == "prediction"
    assert prediction.attributes["projection_surface"] == "world_model_only"
    assert prediction.attributes["canonical_write_allowed"] is False
    assert prediction.attributes["retrospective_review_on_conflict"] is True
    assert prediction.attributes["verification_condition"]
    assert prediction.attributes["contradiction_condition"]


def test_contradicted_prediction_appends_feedback_and_queues_model_miss(
    tmp_path: Path,
) -> None:
    graph = _graph()
    store = _store(tmp_path)
    model = PersistentAdvisoryWorldModel(store)
    snapshot = model.publish(
        matter_id=graph.root_matter_id,
        graph=graph,
        results=(_result(graph.input_fingerprint, kind="prediction"),),
        generated_at=NOW,
    )
    reports: list[dict[str, object]] = []

    class FakeModelMissOwner:
        def report(self, **kwargs):
            reports.append(kwargs)
            return SimpleNamespace(miss_id="model-miss:prediction")

    feedback = model.evaluate_prediction(
        matter_id=graph.root_matter_id,
        advisory_id=snapshot.advisories[0].advisory_id,
        disposition="contradicted",
        observed_at=NOW + timedelta(days=1),
        observation_statement="A licensed later result records failure.",
        observation_evidence_ids=("e-later",),
        observation_graph_fingerprint="sha256:later-graph",
        model_miss_owner=FakeModelMissOwner(),
    )

    assert feedback.disposition == "contradicted"
    assert feedback.model_miss_required is True
    assert feedback.model_miss_id == "model-miss:prediction"
    assert reports[0]["failure_class"] == "world_prediction_contradicted"
    persisted = store.current(WORLD_MODEL_FEEDBACK_OWNER, feedback.feedback_id)
    assert persisted is not None
    assert persisted["model_miss_required"] is True


def test_prediction_without_verification_contract_is_rejected(
    tmp_path: Path,
) -> None:
    graph = _graph()
    result = _result(graph.input_fingerprint)
    finding = replace(
        result.findings[0],
        attributes={
            "world_advisory_kind": "prediction",
            "situation_graph_fingerprint": graph.input_fingerprint,
        },
    )

    with pytest.raises(ValueError, match="future prediction requires"):
        PersistentAdvisoryWorldModel(_store(tmp_path)).publish(
            matter_id=graph.root_matter_id,
            graph=graph,
            results=(replace(result, findings=(finding,)),),
            generated_at=NOW,
        )
