"""Rebase the canonical BCL on the AI-autonomous object-browser revision.

This is an explicit one-way project migration.  It intentionally invalidates
all prior evidence and primary-path receipts because those artifacts describe
the retired confirmation/review workflow.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from flowguard import (
    BehaviorCommitmentLedger,
    behavior_commitment_ledger_to_mapping,
)
from flowguard_design.inventory import MODELS


LEDGER_PATH = Path(".flowguard/behavior_commitment_ledger/ledger.json")
REVISION = "v0.3.0-matter-browser-semantic-reset-v8"

UPDATES: dict[str, dict[str, object]] = {
    "BC-PR-000": {
        "label": "autonomously maintain an authorized situation from registration through object-browser projection",
        "expected_result": (
            "a current per-occurrence and per-Matter stage ledger plus evidence-backed "
            "Matter, source-only, not-applicable, uncertain, no-finding, blocked, "
            "or UI-ready terminal results; source originals remain in place while "
            "pointer/fingerprint and durable-derived stages, SourceGroup, a Matter-only "
            "hierarchy projection, logical-event timeline, people/relations, human narrative, "
            "Situation/World Model, root-only photographic Hero, materialized first-gap "
            "index, and actual UI reachability "
            "remain independently auditable; a passed result awaiting only original-owner "
            "redispatch is recovered as one isolated phase that defers new AI work to the "
            "next maintenance cycle"
        ),
        "expected_terminal": (
            "all registered objects have current required-stage terminal pointers and "
            "all admitted Matters have current Matter-only hierarchy, logical-event "
            "timeline, people/relations, human narrative, MaterialClue/summary activity, "
            "root Hero or descendant hero-not-applicable disposition, SituationGraph and "
            "World Model freshness, supplemental-information disposition, bilingual "
            "projection, and real UI reachability; every transient/raw retention stage is "
            "terminal or explicitly blocked"
        ),
        "trigger": (
            "an authorized source universe is registered, changed, rescanned, or opened "
            "in the desktop application"
        ),
        "failure_boundary": (
            "fail visibly when authorization, enumeration, disposition, freshness, "
            "analysis, owner dispatch, hierarchy, logical-event projection, people/"
            "relations, human narrative, graph, World Model inference, "
            "MaterialClue/summary activity, root Hero, raw/staging cleanup, supplemental "
            "information, localization, exact admitted-Matter identity, bounded storage "
            "migration, or UI reachability is nonterminal; an owner-recovery cycle cannot "
            "also expand source analysis, projection repair, hero generation, or "
            "supplemental research; startup and "
            "logical migration never own VACUUM or a physical-shrink claim"
        ),
    },
    "BC-PR-001": {
        "label": "automatically classify every authorized occurrence with a reversible terminal disposition",
        "expected_result": (
            "a versioned candidate-scope grant plus tracked, not_tracked, hard_excluded, "
            "metadata_only, blocked, or unavailable terminal disposition with reason and confidence; "
            "a Gmail body continuation additionally requires one raw-manifest hash, exact "
            "at-most-20 batch membership, status-specific minimal result projection, current "
            "metadata owners, and a recomputed canonical-row proof for no_text_body"
        ),
        "expected_terminal": (
            "candidate_scope_current, disposition_recorded, unavailable, access_gap, revoked, or blocked"
        ),
        "trigger": "authorized roots or mailbox pages produce a new, changed, moved, deleted, or newly reachable occurrence",
    },
    "BC-PR-002": {
        "label": "preserve source-in-place observation, inventory, derived-state, and cache provenance",
        "expected_result": (
            "immutable locator/fingerprint occurrence observations, change sets, tombstones, "
            "durable derived understanding, and safe private evidence-gallery caches with "
            "renderer identity, retention class, references, quota, TTL, and freshness; "
            "complete local/Gmail/image originals remain external and transient reads are "
            "removed after derived-state commit; "
            "content-selection semantic identity excludes scan-only inventory revision, "
            "generated heroes never become sources or evidence, and an exact Gmail body "
            "continuation writes either a locator/fingerprint receipt, exact anchor "
            "coordinates/digests, and declared derived outputs or one no-text content "
            "disposition over unchanged metadata, then removes complete staging bodies; "
            "every current metadata-only/identity-only Gmail message also retains one "
            "minimal SourceVersion under an exact current inventory/coverage-owner gate"
        ),
        "failure_boundary": (
            "a no-delta scan cannot rewrite content-selection identity or duplicate "
            "content/evidence/AI work; source and inventory authority cannot be "
            "replaced by projection, package, generated-hero state, or a copied-original "
            "fallback; unreferenced cache/staging deletion requires a bounded current "
            "reference check; a conflicting current Gmail observation or replay-amplified "
            "receipt/version is rejected; metadata reconciliation cannot downgrade a "
            "content observation, accept a stale/foreign owner, continue from a "
            "non-terminal page chain, or create evidence/semantic state"
        ),
    },
    "BC-PR-003": {
        "label": "qualify exact evidence and display-safe evidence-gallery anchors",
        "expected_result": (
            "exact current textual or visual anchors with modality, display permission, "
            "gallery display eligibility, or an explicit evidence gap; downstream owners "
            "receive only a bounded SourceVersion/count/digest anchor-set pointer while C3 "
            "retains every exact anchor; accepted Gmail continuation bodies receive exact "
            "current-version line anchors without model use, while proof-bound no_text_body "
            "terminates as not_applicable with no invented anchor; no evidence anchor "
            "authorizes generated-hero selection"
        ),
        "failure_boundary": (
            "unbounded anchor-id lists, stale count/digest pointers, unverified pointer "
            "migration, and evidence-to-generated-hero authority escape are rejected"
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
        "label": "reconstruct a human-readable logical-event trace and current MaterialClue activity while preserving conflict",
        "expected_result": (
            "typed planned, reported, observed, or inferred events with record/occurred "
            "times separated, conflicts retained, plus materiality disposition, rationale, "
            "latest_meaningful_clue_at, logical_event_key, one current revision with "
            "supersession history, and bounded ancestor activity propagation; events "
            "enter one versioned internal SituationGraph projection without changing C5 "
            "ownership; scan/retry/localization/hero work never bubbles catalog order"
        ),
    },
    "BC-PR-006": {
        "label": "autonomously admit, relate, graph, exclude, or preserve uncertainty for Matters",
        "expected_result": (
            "admitted, source_only, not_applicable, uncertain, or blocked Matter disposition "
            "plus current Matter-source relations; hierarchy, coverage, lifecycle, activity, "
            "and projection use only the exact current C6-admitted matter_id; one bounded "
            "internal SituationGraphSnapshot may include WorkItems, Events, and inference, "
            "while the ordinary UI MatterHierarchyProjection contains Matter nodes only "
            "with primary containment and typed Matter-to-Matter secondary relations; "
            "travel/software portfolio roots and cross-domain relations are reconciled; "
            "when one same-Matter source refresh makes a sibling package stale, that "
            "package is append-only superseded and exactly one exact-current successor "
            "is required"
        ),
        "failure_boundary": (
            "projection, source, candidate, package, title, or source-overlap identity "
            "cannot become canonical Matter authority; zero or multiple admitted owners "
            "block; a stale refresh cannot be retried or loosen its fingerprint, and a "
            "missing or duplicate current successor blocks"
        ),
    },
    "BC-PR-007": {
        "label": "autonomously maintain evidence-licensed lifecycle and board placement",
        "expected_result": (
            "planned, in_progress, completed, provisional/ai_inferred, uncertain, or blocked "
            "lifecycle axes with rationale, coverage-bounded gaps, a stable lifecycle "
            "display key separate from reported/observed/inferred modality, and no UI-owned write path"
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
            "append-only correction or revocation with exact MaterialClue, bilingual summary, "
            "ancestor activity, graph, World Model, root-Hero, source-retention, and "
            "supplemental-information invalidation, "
            "durable owner dispatch, and same-revision terminal join"
        ),
    },
    "BC-PR-011": {
        "label": "validate typed AI findings and automatically dispatch them to original owners",
        "expected_result": (
            "WorkPackageV2 results with complete input accounting, bilingual typed "
            "findings, no-finding/policy-rejected outcomes, human Matter narratives, "
            "privacy-minimized root-only photographic Hero briefs/results, Situation/World "
            "Model hypotheses with confidence/alternatives/expiry, nonempty-or-explicitly-"
            "unavailable supplemental-information, one idempotent root-only "
            "ResearchGuard package, explicit descendant not-applicable disposition, "
            "suggestions, and idempotent automatic original-owner dispatch"
        ),
        "expected_terminal": (
            "auto_applied, no_finding, policy_rejected, blocked, failed, unavailable, "
            "scope_incompatible, quarantined, superseded, or corrected_by_user"
        ),
    },
    "BC-PR-012": {
        "label": "project a bilingual desktop Matter object browser",
        "expected_result": (
            "a current bounded root-Matter catalog ordered by latest meaningful clue after "
            "every search/filter, with en/zh-CN atomic summary/activity content, Start-time "
            "filter, summary-free Standard/Compact cards retaining the same visible root "
            "photographic Hero (with metrics only in Standard), exactly eight detail sections "
            "with a minimal human Overview, one multi-depth Matter-only Sub-matters graph, "
            "one reusable node quick view containing itemized facts/events/work/waits and "
            "node-specific flat sources, grouped folder/Gmail-thread/Codex-project/provider "
            "source locations, logical-event-deduplicated timeline, nonempty-or-explicitly-"
            "unavailable AI supplemental information with automatic root-only A1 "
            "queuing and descendant not-applicable disposition, an evidence-only Images gallery, "
            "separate lifecycle and reported/observed/inferred modality labels, compact "
            "indexed coverage drilldown, preserved browsing state, exact "
            "C6-admitted matter_id projection, and optional correction entry"
        ),
        "expected_terminal": "projection_current, projection_pending, or blocked with current catalog preserved",
        "failure_boundary": (
            "projection/source/candidate rows without one exact current C6-admitted "
            "matter_id stay outside canonical root/child catalogs and admitted coverage"
        ),
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
            "ResearchGuard identity, or a visible pending/non-pass terminal; "
            "unchanged eligible root input reuses one package while descendants "
            "never enter the research queue"
        ),
    },
    "BC-AO-003": {
        "label": "plan one maintenance run and join bounded delegated capability work",
        "expected_result": (
            "one strongest-compatible primary Codex maintenance plan, bounded A0/A1 "
            "delegations, exact terminal child receipts, finite retry, and one joined "
            "maintenance terminal receipt without product, validation, or release writes"
        ),
        "expected_terminal": (
            "current, no_change, partial, failed, blocked, unavailable, or cancelled"
        ),
        "trigger": (
            "an interactive, first-run, or scheduled private maintenance request has "
            "current authorization, inventory identity, and resource budget"
        ),
        "failure_boundary": (
            "the orchestrator cannot write canonical Matter state, select a named public "
            "model contract, hide child receipt failures, retry indefinitely, run the final "
            "full validation owner, or perform install/Git/tag/release actions"
        ),
    },
    "BC-AO-004": {
        "label": "serve one bounded AI information-map request or append typed feedback",
        "expected_result": (
            "one revision-bound model-map, situation-context, or bounded-history "
            "receipt, or one privacy-minimized append-only user-observation, "
            "correction, prediction-feedback, or model-miss receipt with an exact "
            "existing-owner disposition and no canonical product write"
        ),
        "expected_terminal": (
            "current, recorded, pending_owner, rejected, stale, blocked, "
            "unavailable, or superseded"
        ),
        "trigger": (
            "an authorized AI invokes the public Matters gateway for bounded "
            "context or submits one typed feedback item"
        ),
        "failure_boundary": (
            "the gateway cannot inspect or export unbounded raw private storage, "
            "retain a full conversation by default, write C1-C12 state, become "
            "C13, complete A2 maintenance, vendor or fall back to a legacy Guard, "
            "or hide a ResearchGuard-dependent gap"
        ),
    },
    "BC-DP-003": {
        "label": (
            "publish generic v0.3.0 source, package, desktop, and AI gateway "
            "before the private first run"
        ),
        "expected_result": (
            "one private GitHub repository release whose commit, v0.3.0 tag, "
            "wheel, source distribution, Windows desktop package, installed "
            "Python and desktop identities, matters-mcp AI gateway, model/test "
            "receipts, public-safe inventory, and anonymous recheck agree "
            "without consuming or claiming completion of private-first-run data"
        ),
        "expected_terminal": (
            "published_and_anonymously_rechecked or blocked with exact "
            "package, privacy, install, Git, or publication gaps"
        ),
        "trigger": (
            "generic source, model, TestMesh, UI, privacy, package, desktop, "
            "MCP, bundled-skill, and ResearchGuard identities are current and "
            "the user authorizes liuyingxuvka/Matters as a private v0.3.0 release"
        ),
        "failure_boundary": (
            "private Gmail, filesystem, Codex-project, aggregate, receipt, "
            "screenshot, identifier, or first-run completion evidence cannot "
            "enter or gate the generic release; candidate drift, unexpected "
            "build-environment packages, missing matters-mcp, incomplete "
            "bundled skills, mismatched tag/install/assets, or a non-private "
            "remote blocks publication"
        ),
    },
    "BC-DP-004": {
        "label": "complete an autonomous progressive private first run with truthful object coverage",
        "expected_result": (
            "candidate roots, inventory snapshots, per-object stage rows, context-aware "
            "hierarchy, SourceGroups, SituationGraph, World Model, MaterialClue/summary "
            "activity, root-only photographic Heroes, raw/staging cleanup, supplemental "
            "information, localization, and UI reachability reconcile progressively under "
            "one strongest-compatible primary Codex plan with bounded low-cost delegation "
            "and no normal human gate"
        ),
        "trigger": (
            "the generic v0.3.0 release identity is current and the user starts "
            "or resumes the authorized post-release private first run"
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


def _append_unique(row: dict[str, object], key: str, *values: object) -> None:
    current = list(row.get(key, ()))
    for value in values:
        if value not in current:
            current.append(value)
    row[key] = current


def _ensure_maintenance_orchestrator_commitment(ledger: dict[str, object]) -> None:
    commitments = ledger["commitments"]
    if any(row.get("commitment_id") == "BC-AO-003" for row in commitments):
        return
    template = deepcopy(
        next(row for row in commitments if row.get("commitment_id") == "BC-AO-001")
    )
    template.update(
        {
            "actor": "Matters primary Codex maintenance orchestrator",
            "business_intent_id": "BI-AO-003-orchestrate-private-maintenance",
            "commitment_id": "BC-AO-003",
            "label": UPDATES["BC-AO-003"]["label"],
            "expected_result": UPDATES["BC-AO-003"]["expected_result"],
            "expected_terminal": UPDATES["BC-AO-003"]["expected_terminal"],
            "trigger": UPDATES["BC-AO-003"]["trigger"],
            "failure_boundary": UPDATES["BC-AO-003"]["failure_boundary"],
            "primary_owner_model_id": "A2_matters_maintenance_orchestrator_operation",
            "rationale": (
                "A2 alone owns maintenance-run planning, bounded delegation, finite retry, "
                "and child-receipt joins; A0/A1 execute bounded work and product owners "
                "retain every canonical write."
            ),
            "side_effects": [
                "create bounded A0/A1 work packages and join their terminal receipts"
            ],
            "source_surface_ids": [
                "surface:openspec:tasks-maintenance-orchestration"
            ],
            "state_writes": [
                "maintenance_operation.plan",
                "maintenance_operation.delegation_registry",
                "maintenance_operation.child_receipt_registry",
                "maintenance_operation.join_status",
                "maintenance_operation.resource_budget",
                "maintenance_operation.terminal_receipt",
            ],
            "relations": [
                {
                    "metadata": {},
                    "rationale": "A2 delegates one bounded source-analysis package to A0.",
                    "relation_type": "invokes",
                    "target_commitment_id": "BC-AO-001",
                },
                {
                    "metadata": {},
                    "rationale": "A2 may delegate one bounded supplemental research package to A1.",
                    "relation_type": "invokes",
                    "target_commitment_id": "BC-AO-002",
                },
                {
                    "metadata": {},
                    "rationale": "All admitted child artifacts return through the C11 product boundary.",
                    "relation_type": "invokes",
                    "target_commitment_id": "BC-PR-011",
                },
            ],
            "metadata": {
                "concrete_model_mapping": "private_machine_local_codex_execution_profile",
                "direct_api_fallback": False,
                "product_model_dependency": False,
                "retry_policy": "finite_typed_non_repeating",
            },
        }
    )
    template["evidence"]["model_obligation_ids"] = ["OB-AO-003"]
    template["evidence"]["risk_gate_ids"] = [
        "G6-maintenance-orchestration-contract",
        "G9-synthetic-maintenance-join-matrix",
    ]
    template["lookup_binding"] = {
        "error_signatures": [],
        "metadata": {},
        "path_patterns": [
            "openspec/changes/build-matters-model-driven-core/specs/authorization-coverage/**",
            "src/matters/application/maintenance_orchestration.py",
        ],
        "task_terms": [
            "maintenance orchestrator",
            "primary Codex plan",
            "low cost delegation",
            "bounded child receipt",
            "finite retry",
        ],
        "tool_ids": ["matters-maintenance-orchestrator"],
        "workflow_families": ["private_maintenance_orchestration"],
    }
    template["path_authority"].update(
        {
            "behavior_commitment_id": "BC-AO-003",
            "business_intent_id": "BI-AO-003-orchestrate-private-maintenance",
            "primary_path_id": "path:ao-private-maintenance-orchestrator",
        }
    )
    commitments.append(template)
    _append_unique(ledger, "expected_commitment_ids", "BC-AO-003")
    _append_unique(
        ledger,
        "expected_business_intent_ids",
        "BI-AO-003-orchestrate-private-maintenance",
    )


def _ensure_maintenance_orchestrator_surface_binding(
    ledger: dict[str, object],
) -> None:
    private_first_run_surface = next(
        row
        for row in ledger["source_surfaces"]
        if row.get("surface_id") == "surface:openspec:tasks-private-first-run"
    )
    private_first_run_surface["commitment_ids"] = [
        value
        for value in private_first_run_surface.get("commitment_ids", ())
        if value != "BC-AO-003"
    ]
    private_first_run_surface["business_intent_ids"] = [
        value
        for value in private_first_run_surface.get("business_intent_ids", ())
        if value != "BI-AO-003-orchestrate-private-maintenance"
    ]

    surface_id = "surface:openspec:tasks-maintenance-orchestration"
    surface = next(
        (
            row
            for row in ledger["source_surfaces"]
            if row.get("surface_id") == surface_id
        ),
        None,
    )
    if surface is None:
        surface = deepcopy(private_first_run_surface)
        ledger["source_surfaces"].append(surface)
    surface.update(
        {
            "surface_id": surface_id,
            "label": "Codex maintenance-orchestration task surface",
            "commitment_ids": ["BC-AO-003"],
            "business_intent_ids": [
                "BI-AO-003-orchestrate-private-maintenance"
            ],
            "primary_path_id": "path:ao-private-maintenance-orchestrator",
            "rationale": (
                "The OpenSpec task surface delegates bounded maintenance planning "
                "and child-receipt joining to the A2 agent-operation owner."
            ),
            "validation_boundary": (
                "strict OpenSpec validation plus current A2 operation-model, "
                "TestMesh, and runtime receipts"
            ),
        }
    )

    commitment = next(
        row
        for row in ledger["commitments"]
        if row.get("commitment_id") == "BC-AO-003"
    )
    commitment["source_surface_ids"] = [surface_id]


def _ensure_ai_gateway_commitment(ledger: dict[str, object]) -> None:
    commitments = ledger["commitments"]
    if any(row.get("commitment_id") == "BC-AO-004" for row in commitments):
        return
    template = deepcopy(
        next(row for row in commitments if row.get("commitment_id") == "BC-AO-001")
    )
    template.update(
        {
            "actor": "Matters AI gateway",
            "business_intent_id": "BI-AO-004-use-matters-ai-information-map",
            "commitment_id": "BC-AO-004",
            "label": UPDATES["BC-AO-004"]["label"],
            "expected_result": UPDATES["BC-AO-004"]["expected_result"],
            "expected_terminal": UPDATES["BC-AO-004"]["expected_terminal"],
            "trigger": UPDATES["BC-AO-004"]["trigger"],
            "failure_boundary": UPDATES["BC-AO-004"]["failure_boundary"],
            "primary_owner_model_id": "A3_matters_ai_gateway_operation",
            "rationale": (
                "A3 owns only bounded query and append-only feedback receipts; "
                "M0/C1-C12 retain every product fact and A2 retains maintenance "
                "planning, delegation, joins, and completion."
            ),
            "side_effects": [
                "write one bounded gateway receipt and request one existing owner disposition"
            ],
            "source_surface_ids": [
                "surface:openspec:tasks-ai-gateway-operation"
            ],
            "state_writes": [
                "ai_gateway.contract_revision",
                "ai_gateway.request_fingerprint",
                "ai_gateway.query_receipt",
                "ai_gateway.feedback_receipt",
                "ai_gateway.owner_dispatch_disposition",
                "ai_gateway.researchguard_status",
                "ai_gateway.completion_status",
            ],
            "relations": [
                {
                    "metadata": {},
                    "rationale": "Explicit corrections remain owned by the C10 correction path.",
                    "relation_type": "invokes",
                    "target_commitment_id": "BC-PR-010",
                },
                {
                    "metadata": {},
                    "rationale": "Prediction feedback and advisory model findings remain owned by C11.",
                    "relation_type": "invokes",
                    "target_commitment_id": "BC-PR-011",
                },
                {
                    "metadata": {},
                    "rationale": "Bounded human-readable context is read from the C12 projection path.",
                    "relation_type": "requires_evidence_from",
                    "target_commitment_id": "BC-PR-012",
                },
                {
                    "metadata": {},
                    "rationale": "Pending clues may be consumed by a later A2-owned maintenance run.",
                    "relation_type": "requires_evidence_from",
                    "target_commitment_id": "BC-AO-003",
                },
            ],
            "metadata": {
                "canonical_product_writer": False,
                "guard_distribution_owner": False,
                "maintenance_completion_owner": False,
                "public_gateway_skill_id": "matters",
                "research_provider": "external_researchguard_only",
            },
        }
    )
    template["evidence"]["model_obligation_ids"] = ["OB-AO-004"]
    template["evidence"]["risk_gate_ids"] = [
        "G6-ai-gateway-operation-contract",
        "G9-synthetic-ai-gateway-matrix",
    ]
    template["lookup_binding"] = {
        "error_signatures": [],
        "metadata": {},
        "path_patterns": [
            "openspec/changes/build-matters-model-driven-core/specs/guard-prediction-boundary/**",
            "src/matters/application/ai_gateway.py",
            "src/matters/api/mcp/server.py",
            "plugins/matters/**",
        ],
        "task_terms": [
            "AI information map",
            "situation context",
            "bounded history",
            "user observation",
            "prediction feedback",
            "model miss",
            "public matters skill",
        ],
        "tool_ids": ["matters-ai-gateway"],
        "workflow_families": ["ai_information_map_and_feedback"],
    }
    template["path_authority"].update(
        {
            "behavior_commitment_id": "BC-AO-004",
            "business_intent_id": "BI-AO-004-use-matters-ai-information-map",
            "primary_path_id": "path:ao-matters-ai-gateway",
        }
    )
    commitments.append(template)
    _append_unique(ledger, "expected_commitment_ids", "BC-AO-004")
    _append_unique(
        ledger,
        "expected_business_intent_ids",
        "BI-AO-004-use-matters-ai-information-map",
    )


def _ensure_ai_gateway_surface_binding(ledger: dict[str, object]) -> None:
    template_surface = next(
        row
        for row in ledger["source_surfaces"]
        if row.get("surface_id")
        == "surface:openspec:tasks-maintenance-orchestration"
    )
    surface_id = "surface:openspec:tasks-ai-gateway-operation"
    surface = next(
        (
            row
            for row in ledger["source_surfaces"]
            if row.get("surface_id") == surface_id
        ),
        None,
    )
    if surface is None:
        surface = deepcopy(template_surface)
        ledger["source_surfaces"].append(surface)
    surface.update(
        {
            "surface_id": surface_id,
            "label": "Public Matters AI gateway task surface",
            "commitment_ids": ["BC-AO-004"],
            "business_intent_ids": [
                "BI-AO-004-use-matters-ai-information-map"
            ],
            "primary_path_id": "path:ao-matters-ai-gateway",
            "rationale": (
                "The OpenSpec task surface delegates bounded model-map/context "
                "queries and typed feedback receipts to A3 without product writes."
            ),
            "validation_boundary": (
                "strict OpenSpec validation plus current A3 operation-model, "
                "focused gateway tests, TestMesh, and runtime receipts"
            ),
        }
    )
    commitment = next(
        row
        for row in ledger["commitments"]
        if row.get("commitment_id") == "BC-AO-004"
    )
    commitment["source_surface_ids"] = [surface_id]


def main() -> int:
    payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    ledger = payload["ledger"]
    ledger["current_revision"] = REVISION
    ledger["claim_scope"] = "routine"
    _ensure_maintenance_orchestrator_commitment(ledger)
    _ensure_maintenance_orchestrator_surface_binding(ledger)
    _ensure_ai_gateway_commitment(ledger)
    _ensure_ai_gateway_surface_binding(ledger)

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
            "v0.3.0 source-in-place storage, private retention classes, SourceGroup, "
            "Matter-only hierarchy, logical-event deduplication, human narrative, "
            "people/relations, Situation/World Model inference, root-only photographic Hero, "
            "summary-free cards, single-layer node quick view, grouped source locations, "
            "first-gap coverage, model fields, and desktop evidence changed"
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
                "orchestration.coverage_first_gap_index",
                "orchestration.worker_checkpoint",
                "orchestration.work_item_registry",
                "orchestration.per_object_stage_audit",
                "orchestration.evidence_pointer_rebase_cursor",
                "orchestration.evidence_pointer_rebase_status",
                "orchestration.coverage_history_archive_cursor",
                "orchestration.coverage_history_archive_status",
                "orchestration.coverage_history_archive_verification",
                "orchestration.storage_migration_order_status",
                "orchestration.physical_compaction_status",
                "orchestration.source_in_place_migration_cursor",
                "orchestration.source_in_place_migration_status",
                "orchestration.transient_cleanup_cursor",
                "orchestration.transient_cleanup_status",
                "orchestration.cache_reference_gc_status",
                "orchestration.source_group_coverage_status",
                "orchestration.situation_graph_status",
                "orchestration.world_model_status",
                "orchestration.human_narrative_status",
                "orchestration.logical_event_projection_status",
                "orchestration.people_relation_status",
                "orchestration.matter_hierarchy_projection_status",
                "orchestration.codex_source_coverage_status",
            )
        elif commitment_id == "BC-DP-003":
            row["rationale"] = (
                "This is the single generic private-repository publication path. "
                "It closes before, and never consumes, the separate private first run."
            )
            row["side_effects"] = [
                "push approved generic public-safe source to the private remote",
                "create the v0.3.0 tag and GitHub Release",
                "publish the wheel, source distribution, Windows desktop package, and checksums",
            ]
            row["source_surface_ids"] = [
                "surface:spec:privacy-publication-boundary",
                "surface:doc:public-boundary",
                "surface:openspec:tasks-release",
            ]
            row["state_writes"] = [
                "release_candidate.identity",
                "release_evidence.freshness",
                "release.private_first_run_separation",
                "release.package_identity",
                "release.desktop_identity",
                "release.ai_gateway_identity",
                "release.git_identity",
                "release.status",
            ]
            row["lookup_binding"] = {
                "error_signatures": [
                    "installed_version_stale",
                    "matters_mcp_missing",
                    "desktop_package_incomplete",
                    "private_aggregate_must_not_be_consumed_by_generic_release",
                ],
                "metadata": {},
                "path_patterns": [
                    "openspec/changes/build-matters-model-driven-core/specs/privacy-release-boundary/**",
                    "docs/security/public-boundary.md",
                    "plugins/matters/**",
                    "scripts/build_desktop_package.ps1",
                    "scripts/install_desktop_package.ps1",
                    ".github/**",
                    "SECURITY.md",
                ],
                "task_terms": [
                    "generic release",
                    "private GitHub",
                    "v0.3.0",
                    "tag",
                    "wheel",
                    "source distribution",
                    "Windows desktop",
                    "matters-mcp",
                    "clean clone",
                    "SBOM",
                    "anonymous download",
                ],
                "tool_ids": ["git", "github-release", "matters-mcp"],
                "workflow_families": ["generic_private_repository_release"],
            }
            authority["business_intent"] = (
                "publish generic v0.3.0 before the private first run"
            )
            authority["primary_path_id"] = (
                "path:dpf-generic-v030-release-before-private-first-run"
            )
            authority["scoped_out_reason"] = (
                "current generic release requires fresh package, installed "
                "desktop/MCP, TestMesh, Git/tag, privacy, and publication evidence; "
                "private-first-run completion is explicitly not required"
            )
        elif commitment_id == "BC-DP-004":
            _append_unique(
                row,
                "relations",
                {
                    "metadata": {},
                    "rationale": (
                        "The authorized private first run starts against the "
                        "already released generic v0.3.0 contract."
                    ),
                    "relation_type": "requires_evidence_from",
                    "target_commitment_id": "BC-DP-003",
                },
            )
        elif commitment_id == "BC-PR-002":
            row["state_writes"] = [
                value
                for value in row.get("state_writes", ())
                if not str(value).startswith("visual_asset.")
            ] + [
                "gallery_asset.identity",
                "gallery_asset.derivative_revision",
                "gallery_asset.renderer_identity",
                "gallery_asset.safety_disposition",
                "source.content_selection_semantic_identity",
                "source.content_selection_inventory_revision_context",
                "source.gmail_metadata_owner_status",
                "source.gmail_metadata_reconciliation_cursor",
                "source.locator",
                "source.content_fingerprint",
                "source.metadata_fingerprint",
                "source.storage_class",
                "source.transient_cleanup_status",
                "source.cache_retention_policy",
                "source.cache_reference_status",
                "source.unavailable_status",
                "source.source_group_identity",
                "source.source_group_membership_revision",
            ]
        elif commitment_id == "BC-PR-003":
            row["state_writes"] = [
                value
                for value in row.get("state_writes", ())
                if value != "evidence.visual_eligibility"
            ]
            _append_unique(
                row,
                "state_writes",
                "evidence.display_permission",
                "evidence.gallery_display_eligibility",
                "evidence.anchor_set_pointer",
                "evidence.anchor_set_source_version",
                "evidence.anchor_set_count",
                "evidence.anchor_set_digest",
            )
        elif commitment_id == "BC-PR-005":
            _append_unique(
                row,
                "state_writes",
                "trace.material_clue_identity",
                "trace.materiality_disposition",
                "trace.materiality_rationale",
                "trace.latest_meaningful_clue_at",
                "trace.material_clue_revision",
                "trace.ancestor_activity_rollup_revision",
                "trace.situation_graph_event_revision",
                "event.logical_event_key",
                "event.current_revision",
                "event.supersedes_event_id",
                "event.owning_matter_path",
                "event.importance",
            )
        elif commitment_id == "BC-PR-006":
            _append_unique(
                row,
                "state_writes",
                "matter.source_relation",
                "matter.admitted_matter_id_authority",
                "matter.canonical_matter_id",
                "matter.situation_graph_revision",
                "matter.situation_graph_primary_edges",
                "matter.situation_graph_secondary_edges",
                "matter.situation_graph_continuation",
                "matter.ui_hierarchy_projection_revision",
                "matter.ui_hierarchy_matter_ids",
                "matter.ui_hierarchy_secondary_edges",
            )
        elif commitment_id == "BC-PR-010":
            row["state_writes"] = [
                value
                for value in row.get("state_writes", ())
                if value != "correction.card_visual_intent"
            ]
            _append_unique(
                row,
                "state_writes",
                "correction.material_clue_invalidation",
                "correction.summary_activity_invalidation",
                "correction.generated_hero_invalidation",
                "correction.supplemental_information_invalidation",
                "correction.situation_graph_invalidation",
                "correction.world_model_invalidation",
                "correction.source_retention_invalidation",
            )
        elif commitment_id == "BC-PR-011":
            row["state_writes"] = [
                "agent.work_package_v2_registry",
                "agent.result_registry",
                "analysis.finding_history",
                "analysis.input_disposition_registry",
                "analysis.dispatch_outbox",
                "analysis.summary_candidate_registry",
                "analysis.narrative_registry",
                "analysis.generated_hero_registry",
                "analysis.supplemental_information_registry",
                "analysis.depth_registry",
                "forecast_registry",
                "analysis.situation_world_model_registry",
                "analysis.situation_inference_dependency_registry",
            ]
        elif commitment_id == "BC-PR-012":
            row["state_writes"] = [
                value
                for value in row.get("state_writes", ())
                if not str(value).startswith("matter.card_visual_")
            ]
            _append_unique(
                row,
                "state_writes",
                "matter.summary_clue_revision",
                "matter.latest_meaningful_clue_at",
                "matter.activity_order_revision",
                "matter.generated_hero_asset",
                "matter.generated_hero_revision",
                "matter.generated_hero_brief_fingerprint",
                "matter.generated_hero_safety_disposition",
                "matter.generated_hero_currentness",
                "matter.generated_hero_localized_alt",
                "matter.generated_hero_status",
                "matter.supplemental_information_revision",
                "matter.supplemental_information_status",
                "matter.supplemental_information_disposition",
                "matter.supplemental_research_package_id",
                "matter.supplemental_provider_gate",
                "projection.admitted_matter_id",
                "ui.card_density",
                "ui.viewport_mode",
                "ui.query",
                "ui.filter_state",
                "ui.selected_matter_id",
                "ui.detail_section",
                "ui.situation_graph_view_state",
                "ui.matter_hierarchy_projection",
                "ui.situation_graph_continuation",
                "ui.node_quick_view_state",
                "ui.node_quick_view_facts",
                "ui.node_quick_view_source_groups",
                "ui.source_group_window",
                "ui.coverage_indicator_state",
                "ui.coverage_drilldown",
                "ui.browser_scroll_anchor",
                "ui.coverage_summary",
                "ui.background_status",
            )
        elif commitment_id == "BC-AO-003":
            row["state_writes"] = [
                "maintenance_operation.plan",
                "maintenance_operation.delegation_registry",
                "maintenance_operation.child_receipt_registry",
                "maintenance_operation.join_status",
                "maintenance_operation.resource_budget",
                "maintenance_operation.terminal_receipt",
            ]
        elif commitment_id == "BC-AO-004":
            row["state_writes"] = [
                "ai_gateway.contract_revision",
                "ai_gateway.request_fingerprint",
                "ai_gateway.query_receipt",
                "ai_gateway.feedback_receipt",
                "ai_gateway.owner_dispatch_disposition",
                "ai_gateway.researchguard_status",
                "ai_gateway.completion_status",
            ]
        elif commitment_id == "BC-AO-001":
            row.setdefault("metadata", {})["capability_roles"] = [
                "deterministic_preprocessor",
                "low_cost_annotator",
                "ambiguity_resolver",
                "matter_modeler",
                "hero_image_generator",
                "consistency_reviewer",
            ]

        if commitment_id in {
            "BC-PR-000",
            "BC-PR-005",
            "BC-PR-006",
            "BC-PR-007",
            "BC-PR-011",
            "BC-PR-012",
        }:
            owner_model_id = str(row.get("primary_owner_model_id", ""))
            row["state_writes"] = list(MODELS[owner_model_id].owned_write_fields)

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
