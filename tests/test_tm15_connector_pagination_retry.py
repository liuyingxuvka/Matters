from datetime import datetime, timezone
from pathlib import Path

import pytest

from matters.authorization.coverage import AuthorizationError
from matters.authorization.scopes import opaque_reference
from matters.providers.base import ProviderWriteForbidden
from matters.providers.filesystem import FilesystemReadOnlyAdapter
from matters.providers.jira.adapter import JiraReadOnlyAdapter
from matters.providers.jira.contracts import (
    JiraAuthorizationManifest,
    JiraSliceCoverageReceipt,
    ObjectTypeCoverage,
)
from matters.providers.jira.depth import (
    DEPTH_LAYERS,
    DepthLayer,
    MatterDepthReport,
)
from matters.providers.jira.slices import (
    JiraSliceGate,
    SliceDecisionRecord,
)


def _authorization(**changes):
    values = {
        "authorization_scope_id": "scope:synthetic-jira",
        "instance_ref_hash": opaque_reference("synthetic-instance"),
        "provider_edition": "synthetic",
        "provider_version": "0",
        "capabilities": ("issue", "comment", "pagination"),
        "project_ref_hashes": frozenset(
            {opaque_reference("synthetic-project")}
        ),
        "object_ids": frozenset({"SYN-A", "SYN-B"}),
        "object_types": frozenset({"issue", "comment"}),
        "time_start": "2026-01-01T00:00:00+00:00",
        "time_end": "2026-12-31T23:59:59+00:00",
        "permission_fingerprint": opaque_reference("synthetic-permissions"),
        "expires_at": "2099-01-01T00:00:00+00:00",
    }
    values.update(changes)
    return JiraAuthorizationManifest(**values)


def _depth(status: str = "licensed"):
    return MatterDepthReport(
        case_ref_hash=opaque_reference("case"),
        matter_ref_hash=opaque_reference("matter"),
        semantic_revision="revision:synthetic",
        layers=tuple(
            DepthLayer(layer, status, {"evidence": "synthetic"})
            for layer in DEPTH_LAYERS
        ),
        claim_boundary="Fully synthetic contract fixture only.",
    )


def _coverage_receipt(**changes):
    values = {
        "experiment_id": "experiment:synthetic:J1",
        "slice_id": "J1",
        "authorization_scope_id": "scope:synthetic-jira",
        "provider_edition_and_capabilities": {
            "edition": "synthetic",
            "version": "0",
            "capabilities": ["issue"],
        },
        "selected_issue_ref_hash": opaque_reference("SYN-A"),
        "coverage_type": "bounded_query",
        "as_of_time": "2026-07-18T00:00:00+00:00",
        "permission_fingerprint": opaque_reference("synthetic-permissions"),
        "per_object_type": (
            ObjectTypeCoverage("issue", 1, 1, True),
        ),
        "attachment_metadata_count": 0,
        "attachment_content_count": 0,
        "source_version_hashes": (opaque_reference("source-version"),),
        "evidence_anchor_counts": {"field": 2},
        "person_candidate_count": 1,
        "event_candidate_count": 1,
        "matter_candidate_count": 1,
        "action_candidate_count": 0,
        "unsupported_claims": (),
        "contradictions": (),
        "review_items": (),
        "guard_artifact_versions": {"logicguard": "synthetic"},
        "localization_status": "same_revision",
        "privacy_scan_status": "pass",
        "idempotency_key": "synthetic-idempotency-key",
        "oracle_expected_outcome": "needs_review",
        "product_outcome": "needs_review",
        "coverage_status": "complete",
        "test_result": "pass",
        "claim_boundary": "Fully synthetic receipt contract only.",
    }
    values.update(changes)
    return JiraSliceCoverageReceipt(**values)


def test_generic_jira_projection_paginates_and_forbids_writes():
    calls = []

    def fetch(ids, cursor):
        calls.append((tuple(ids), cursor))
        if not cursor:
            return {
                "objects": [
                    {
                        "external_id": "SYN-A",
                        "authorization_object_id": "SYN-A",
                        "object_type": "issue",
                        "payload": {"summary": "First"},
                    }
                ],
                "next_cursor": "two",
                "coverage": "complete",
            }
        return {
            "objects": [
                {
                    "external_id": "SYN-B",
                    "authorization_object_id": "SYN-B",
                    "object_type": "issue",
                    "payload": {"summary": "Second"},
                }
            ],
            "next_cursor": "",
            "coverage": "partial",
            "denied_fields": ["private_comments"],
        }

    adapter = JiraReadOnlyAdapter(
        fetch,
        authorization=_authorization(),
        g8_current=True,
    )
    rows = adapter.read(object_ids=("SYN-A", "SYN-B"))
    assert len(rows) == 2
    assert rows[0].payload["summary"] == "First"
    assert rows[1].coverage == "partial"
    assert len(calls) == 2
    with pytest.raises(ProviderWriteForbidden):
        adapter.write({"status": "Done"})


def test_pagination_boundary_is_visible():
    adapter = JiraReadOnlyAdapter(
        lambda _ids, _cursor: {"objects": [], "next_cursor": "again"},
        authorization=_authorization(),
        g8_current=True,
        max_pages=2,
    )
    with pytest.raises(RuntimeError, match="pagination boundary"):
        adapter.read(object_ids=("SYN-A",))


def test_missing_g8_expired_or_outside_scope_never_calls_fetch():
    calls = []

    def fetch(_ids, _cursor):
        calls.append("fetch")
        return {"objects": [], "next_cursor": ""}

    with pytest.raises(AuthorizationError, match="g8_not_current"):
        JiraReadOnlyAdapter(
            fetch,
            authorization=_authorization(),
            g8_current=False,
        )
    with pytest.raises(
        AuthorizationError,
        match="explicit_authorization_missing",
    ):
        JiraReadOnlyAdapter(
            fetch,
            authorization=None,
            g8_current=True,
        )
    expired = _authorization(expires_at="2026-01-02T00:00:00+00:00")
    with pytest.raises(AuthorizationError, match="authorization_expired"):
        JiraReadOnlyAdapter(
            fetch,
            authorization=expired,
            g8_current=True,
            as_of=datetime(2026, 7, 18, tzinfo=timezone.utc),
        )
    adapter = JiraReadOnlyAdapter(
        fetch,
        authorization=_authorization(),
        g8_current=True,
    )
    with pytest.raises(AuthorizationError, match="outside_scope"):
        adapter.read(object_ids=("SYN-OUTSIDE",))
    assert calls == []


def test_returned_object_scope_escape_is_rejected():
    adapter = JiraReadOnlyAdapter(
        lambda _ids, _cursor: {
            "objects": [
                {
                    "external_id": "COMMENT-OUTSIDE",
                    "authorization_object_id": "SYN-OUTSIDE",
                    "object_type": "comment",
                    "payload": {"body": "synthetic"},
                }
            ],
            "next_cursor": "",
        },
        authorization=_authorization(),
        g8_current=True,
    )
    with pytest.raises(AuthorizationError, match="returned_object_outside_scope"):
        adapter.read(object_ids=("SYN-A",), object_types=("comment",))


def test_coverage_receipt_keeps_product_coverage_and_test_results_separate():
    receipt = _coverage_receipt(
        per_object_type=(
            ObjectTypeCoverage("issue", 1, 1, True),
            ObjectTypeCoverage("comment", None, 0, None),
        ),
        product_outcome="source_only",
        coverage_status="unknown",
        test_result="pass",
    )
    payload = receipt.to_dict()
    assert payload["product_outcome"] == "source_only"
    assert payload["coverage_status"] == "unknown"
    assert payload["test_result"] == "pass"
    assert payload["per_object_type"]["comment"]["pagination"] == "unknown"


def test_depth_report_blocks_complete_claim_on_critical_gap():
    rows = [
        DepthLayer(layer, "licensed", {"evidence": "synthetic"})
        for layer in DEPTH_LAYERS
    ]
    rows[DEPTH_LAYERS.index("Coverage")] = DepthLayer(
        "Coverage",
        "blocked",
        {"reason": "permission denied"},
    )
    report = MatterDepthReport(
        case_ref_hash=opaque_reference("case"),
        matter_ref_hash=opaque_reference("matter"),
        semantic_revision="revision:synthetic",
        layers=tuple(rows),
        claim_boundary="Fully synthetic contract fixture only.",
    )
    assert not report.analysis_complete
    assert report.blocking_layers == ("Coverage",)


def test_slice_sequence_requires_prior_user_go_and_current_receipts():
    gate = JiraSliceGate()
    authorization = _authorization()
    blocked = gate.preflight(
        slice_id="J2",
        g8_current=True,
        authorization=authorization,
    )
    assert not blocked.read_allowed
    assert "prior_slice_not_run:J1" in blocked.blockers

    hold = SliceDecisionRecord(
        slice_id="J1",
        decision="HOLD",
        coverage_receipt_id="receipt:J1",
        depth_report_id="depth:J1",
        user_decision_id="user-decision:J1",
    )
    held = gate.preflight(
        slice_id="J2",
        g8_current=True,
        authorization=authorization,
        prior_decisions=(hold,),
    )
    assert held.blockers == ("prior_slice_not_go:J1:HOLD",)

    go = gate.validate_user_decision(
        decision="GO",
        coverage_receipt=_coverage_receipt(),
        depth_report=_depth(),
        user_decision_id="user-decision:J1",
    )
    ready = gate.preflight(
        slice_id="J2",
        g8_current=True,
        authorization=authorization,
        prior_decisions=(go,),
    )
    assert ready.read_allowed

    with pytest.raises(ValueError, match="GO is not licensed"):
        gate.validate_user_decision(
            decision="GO",
            coverage_receipt=_coverage_receipt(test_result="blocked"),
            depth_report=_depth(),
            user_decision_id="user-decision:J1",
        )


def test_filesystem_partition_boundary_is_explicit_and_children_are_safe(
    tmp_path: Path,
):
    included = tmp_path / "included"
    included.mkdir()
    (included / "nested.txt").write_text("nested", encoding="utf-8")
    adapter = FilesystemReadOnlyAdapter(
        tmp_path,
        page_size=10,
        max_entries=10,
        max_depth=0,
    )

    page = adapter.discover()
    boundary = next(
        item for item in page.items if item.external_id == "included"
    )

    assert boundary.outcome == "partition_boundary"
    assert boundary.reason == "covered_by_declared_child_scope"
    assert adapter.partition_children() == (included,)
