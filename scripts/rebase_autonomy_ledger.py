"""Rebase the canonical BCL on the AI-autonomous object-browser revision.

This is an explicit one-way project migration.  It intentionally invalidates
all prior evidence and primary-path receipts because those artifacts describe
the retired confirmation/review workflow.
"""

from __future__ import annotations

import json
from pathlib import Path

from flowguard import (
    BehaviorCommitmentLedger,
    behavior_commitment_ledger_to_mapping,
)


LEDGER_PATH = Path(".flowguard/behavior_commitment_ledger/ledger.json")
REVISION = "autonomous-object-browser-v2"

UPDATES: dict[str, dict[str, object]] = {
    "BC-PR-000": {
        "label": "autonomously maintain an authorized situation from registration through object-browser projection",
        "expected_result": (
            "a current ObjectCoverageLedger plus evidence-backed Matter, source-only, "
            "not-applicable, uncertain, no-finding, blocked, or UI-ready terminal results"
        ),
        "expected_terminal": (
            "all registered objects have current required-stage terminal pointers and "
            "all admitted Matters are bilingual, visually disposed, and UI-reachable"
        ),
        "trigger": (
            "an authorized source universe is registered, changed, rescanned, or opened "
            "in the desktop application"
        ),
        "failure_boundary": (
            "fail visibly when authorization, enumeration, disposition, freshness, "
            "analysis, owner dispatch, localization, visual, or UI reachability is nonterminal"
        ),
    },
    "BC-PR-001": {
        "label": "automatically classify every authorized occurrence with a reversible terminal disposition",
        "expected_result": (
            "a versioned candidate-scope grant plus tracked, not_tracked, hard_excluded, "
            "metadata_only, blocked, or unavailable terminal disposition with reason and confidence"
        ),
        "expected_terminal": (
            "candidate_scope_current, disposition_recorded, unavailable, access_gap, revoked, or blocked"
        ),
        "trigger": "authorized roots or mailbox pages produce a new, changed, moved, deleted, or newly reachable occurrence",
    },
    "BC-PR-002": {
        "label": "preserve immutable source, inventory, and safe visual-derivative provenance",
        "expected_result": (
            "immutable occurrence/source versions, change sets, tombstones, and safe "
            "private visual derivatives with renderer identity and freshness"
        ),
    },
    "BC-PR-003": {
        "label": "qualify exact evidence and display-safe representative-visual anchors",
        "expected_result": (
            "exact current textual or visual anchors with modality, display permission, "
            "visual eligibility, or an explicit evidence gap"
        ),
    },
    "BC-PR-004": {
        "label": "resolve identities automatically without unsafe merges",
        "expected_result": (
            "current identity assertions, separate uncertain identities, scoped roles, "
            "or explicit identity uncertainty with evidence"
        ),
    },
    "BC-PR-005": {
        "label": "reconstruct a human-readable temporal trace while preserving conflict",
        "expected_result": (
            "typed planned, reported, observed, or inferred events with record/occurred "
            "times separated, conflicts retained, and one best-supported current interpretation"
        ),
    },
    "BC-PR-006": {
        "label": "autonomously admit, exclude, or preserve uncertainty for Matters",
        "expected_result": (
            "admitted, source_only, not_applicable, uncertain, or blocked Matter disposition "
            "plus current Matter-source relations"
        ),
    },
    "BC-PR-007": {
        "label": "autonomously maintain evidence-licensed lifecycle and board placement",
        "expected_result": (
            "planned, in_progress, completed, uncertain, or blocked lifecycle axes with "
            "rationale and no UI-owned write path"
        ),
    },
    "BC-PR-008": {
        "label": "autonomously track open loops, closure gaps, and scoped blocking",
        "expected_result": (
            "open loop, closed loop, open_loop_gap, partial block, full block, or not-applicable terminal disposition"
        ),
    },
    "BC-PR-009": {
        "label": "autonomously maintain outcomes while preserving completion gaps and conflict",
        "expected_result": (
            "completed, cancelled, abandoned, reopened, completion_unproven, or "
            "outcome_conflict terminal disposition"
        ),
    },
    "BC-PR-010": {
        "label": "append optional corrections and recompute through original owners",
        "expected_result": (
            "append-only correction, revocation, or card-cover intent with exact "
            "invalidation, durable owner dispatch, and same-revision terminal join"
        ),
    },
    "BC-PR-011": {
        "label": "validate typed AI findings and automatically dispatch them to original owners",
        "expected_result": (
            "WorkPackageV2 results with complete input accounting, bilingual typed "
            "findings, no-finding/policy-rejected outcomes, visual recommendations, "
            "and idempotent automatic original-owner dispatch"
        ),
        "expected_terminal": (
            "auto_applied, no_finding, policy_rejected, blocked, failed, unavailable, "
            "scope_incompatible, quarantined, superseded, or corrected_by_user"
        ),
    },
    "BC-PR-012": {
        "label": "project a bilingual desktop Matter object browser",
        "expected_result": (
            "a current bounded Matter catalog and detail projection with en/zh-CN "
            "content, human-readable timeline, Standard/Compact density, one "
            "representative visual or placeholder, preserved browsing state, and "
            "optional correction entry"
        ),
        "expected_terminal": "projection_current, projection_pending, or blocked with current catalog preserved",
    },
    "BC-AO-001": {
        "label": "execute one bounded WorkPackageV2 and account every declared input",
        "expected_result": (
            "a schema-valid anchor-bound bilingual result, complete per-input "
            "dispositions, and one durable automatic owner-dispatch disposition"
        ),
    },
    "BC-AO-002": {
        "label": "execute one abstract ResearchOperation through the single ResearchGuard provider",
        "expected_result": (
            "one typed anchor-bound ResearchOperation result from the frozen "
            "ResearchGuard identity, or a visible pending/non-pass terminal"
        ),
    },
    "BC-DP-004": {
        "label": "complete an autonomous progressive private first run with truthful object coverage",
        "expected_result": (
            "candidate roots, inventory snapshots, ObjectCoverageLedger rows, "
            "dispositions, freshness, depth, localization, visual and UI reachability "
            "reconcile progressively without a normal human gate"
        ),
    },
    "BC-DP-005": {
        "label": "freeze the exact eleven-skill app-local Matters consumer pack",
        "expected_result": (
            "one immutable versioned hash-bound inventory containing exactly the "
            "eleven required autonomous-maintenance consumer skills"
        ),
    },
}


def _append_unique(row: dict[str, object], key: str, *values: str) -> None:
    current = list(row.get(key, ()))
    for value in values:
        if value not in current:
            current.append(value)
    row[key] = current


def main() -> int:
    payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    ledger = payload["ledger"]
    ledger["current_revision"] = REVISION
    ledger["claim_scope"] = "routine"

    for row in ledger["commitments"]:
        commitment_id = str(row["commitment_id"])
        row.update(UPDATES.get(commitment_id, {}))
        if row.get("replacement_state", "active") != "active":
            continue

        row["model_sync_state"] = "owner_model_current"
        evidence = row.setdefault("evidence", {})
        evidence["current"] = False
        evidence["evidence_state"] = "stale"
        evidence["test_mesh_state"] = "stale"
        metadata = evidence.setdefault("metadata", {})
        metadata["scope_revision"] = REVISION
        metadata["stale_reason"] = (
            "requirements, model fields, automatic owner dispatch, object coverage, "
            "representative visual, bilingual object browser, and desktop worker changed"
        )

        authority = row.setdefault("path_authority", {})
        authority["evidence_current"] = False
        authority["ppa_confidence"] = "blocked"
        authority["ppa_decision"] = "primary_path_authority_blocked"
        authority["ppa_ok"] = False
        authority["scoped_out_reason"] = (
            "current autonomy revision requires fresh model, TestMesh, runtime, "
            "private-run, installed-desktop, and release evidence"
        )

        if commitment_id == "BC-PR-000":
            authority["business_intent"] = (
                "autonomously maintain an authorized situation"
            )
            _append_unique(
                row,
                "state_writes",
                "orchestration.object_coverage_ledger_revision",
                "orchestration.object_stage_terminal_index",
                "orchestration.worker_checkpoint",
                "orchestration.work_item_registry",
            )
        elif commitment_id == "BC-PR-002":
            _append_unique(
                row,
                "state_writes",
                "visual_asset.identity",
                "visual_asset.derivative_revision",
                "visual_asset.renderer_identity",
                "visual_asset.safety_disposition",
            )
        elif commitment_id == "BC-PR-003":
            _append_unique(
                row,
                "state_writes",
                "evidence.display_permission",
                "evidence.visual_eligibility",
            )
        elif commitment_id == "BC-PR-006":
            _append_unique(row, "state_writes", "matter.source_relation")
        elif commitment_id == "BC-PR-010":
            _append_unique(row, "state_writes", "correction.card_visual_intent")
        elif commitment_id == "BC-PR-011":
            row["state_writes"] = [
                "agent.work_package_v2_registry",
                "agent.result_registry",
                "analysis.finding_history",
                "analysis.input_disposition_registry",
                "analysis.dispatch_outbox",
                "analysis.visual_recommendation_registry",
                "analysis.depth_registry",
                "forecast_registry",
            ]
        elif commitment_id == "BC-PR-012":
            _append_unique(
                row,
                "state_writes",
                "matter.card_visual_decision",
                "matter.card_visual_revision",
                "matter.card_visual_selection_mode",
                "matter.card_visual_status",
                "ui.card_density",
                "ui.viewport_mode",
                "ui.query",
                "ui.filter_state",
                "ui.selected_matter_id",
                "ui.detail_section",
                "ui.browser_scroll_anchor",
                "ui.coverage_summary",
                "ui.background_status",
            )

    payload = behavior_commitment_ledger_to_mapping(
        BehaviorCommitmentLedger(**payload["ledger"])
    )
    LEDGER_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ledger_revision": REVISION,
                "updated_commitments": sorted(UPDATES),
                "all_active_evidence_invalidated": True,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
