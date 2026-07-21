"""Review the Matters UI through the native FlowGuard UI-flow route."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from flowguard import (
    review_ui_content_visibility,
    review_ui_control_functional_chains,
    review_ui_functional_capability_coverage,
    review_ui_geometry_layout_evidence,
    review_ui_implementation_validation,
    review_ui_interaction_model,
    review_ui_journey_coverage,
    review_ui_observed_surface_inventory,
    review_ui_render_evidence,
    review_ui_responsiveness_contract,
    review_ui_visible_surface,
)

from flowguard_design.ui_flow_structure import (
    capability_bindings,
    capability_inventory,
    current_revision,
    feature_contracts,
    functional_chains,
    geometry_evidence,
    implementation_validation,
    interaction_model,
    journey_coverage,
    observed_inventory,
    output_contracts,
    render_evidence,
    responsiveness_contract,
    visibility_plan,
    visible_surface,
)
from flowguard_design.ui_runtime_contract import REQUIRED_UI_CHECKS


RUNTIME_EVIDENCE = Path(".flowguard/evidence/ui/G10_live_ui.json")
OUTPUT = Path(".flowguard/evidence/ui/UI_flow_structure.json")


def _runtime_gate(revision: str) -> dict:
    if not RUNTIME_EVIDENCE.is_file():
        return {
            "ok": False,
            "status": "not_run",
            "evidence_id": "",
            "blockers": ["installed_runtime_evidence_missing"],
        }
    try:
        payload = json.loads(RUNTIME_EVIDENCE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "ok": False,
            "status": "blocked",
            "evidence_id": "",
            "blockers": ["installed_runtime_evidence_unreadable"],
        }
    checks = payload.get("checks", {})
    required = set(REQUIRED_UI_CHECKS)
    missing = sorted(
        check_id
        for check_id in required
        if not isinstance(checks, dict) or checks.get(check_id) is not True
    )
    current = payload.get("ui_revision") == revision
    exact_inventory = isinstance(checks, dict) and set(checks) == required
    ok = (
        payload.get("artifact_type") == "matters.live-ui-evidence.v1"
        and payload.get("status") == "passed"
        and current
        and exact_inventory
        and not missing
        and str(payload.get("evidence_id", "")).startswith("evidence:ui:")
    )
    return {
        "ok": ok,
        "status": "passed" if ok else "blocked",
        "evidence_id": str(payload.get("evidence_id", "")),
        "ui_revision_current": current,
        "missing_checks": missing,
        "exact_check_inventory": exact_inventory,
        "blockers": ([] if ok else ["installed_runtime_evidence_not_current"]),
    }


def _row(report) -> dict:
    return {
        "ok": report.ok,
        "decision": getattr(
            report,
            "decision",
            "green" if report.ok else "blocked",
        ),
        "finding_codes": sorted({item.code for item in report.findings}),
        "finding_count": len(report.findings),
    }


def build_receipt(root: Path = Path(".")) -> dict:
    revision = current_revision(root)
    visibility = visibility_plan(revision)
    model = interaction_model()
    surface = visible_surface()
    journey = journey_coverage()
    capabilities = capability_inventory(revision)
    runtime = _runtime_gate(revision)
    evidence_ref = runtime["evidence_id"] or "not-run:installed-ui"

    structural_reports = {
        "content_visibility": _row(
            review_ui_content_visibility(
                visibility,
                interaction_model=model,
                visible_surface=surface,
            )
        ),
        "interaction_model": _row(
            review_ui_interaction_model(
                model,
                content_visibility_plan=visibility,
            )
        ),
        "visible_surface": _row(
            review_ui_visible_surface(
                surface,
                interaction_model=model,
                content_visibility_plan=visibility,
            )
        ),
        "journey_coverage": _row(
            review_ui_journey_coverage(journey, interaction_model=model)
        ),
        "responsiveness": _row(
            review_ui_responsiveness_contract(
                responsiveness_contract(),
                interaction_model=model,
            )
        ),
    }

    runtime_reports = {}
    if runtime["ok"]:
        observed = observed_inventory(revision, evidence_ref)
        chains = functional_chains(revision, evidence_ref)
        implementation = implementation_validation(revision, evidence_ref)
        capability_report = review_ui_functional_capability_coverage(
            capabilities,
            feature_contracts=feature_contracts(),
            journey_coverage=journey,
            interaction_model=model,
            functional_chains=chains,
            implementation_validation=implementation,
            current_revision=revision,
        )
        runtime_reports = {
            "observed_surface": _row(
                review_ui_observed_surface_inventory(
                    observed,
                    interaction_model=model,
                    visible_surface=surface,
                    content_visibility_plan=visibility,
                )
            ),
            "functional_chains": _row(
                review_ui_control_functional_chains(
                    chains,
                    observed_inventory=observed,
                    interaction_model=model,
                )
            ),
            "capability_coverage": _row(capability_report),
            "implementation": _row(
                review_ui_implementation_validation(
                    implementation,
                    interaction_model=model,
                    journey_coverage=journey,
                    capability_inventory=capabilities,
                    capability_coverage=capability_report,
                    visible_surface=surface,
                    observed_inventory=observed,
                    content_visibility_plan=visibility,
                )
            ),
            "render": _row(
                review_ui_render_evidence(
                    render_evidence(revision, evidence_ref),
                    interaction_model=model,
                )
            ),
            "geometry": _row(
                review_ui_geometry_layout_evidence(
                    geometry_evidence(evidence_ref),
                    interaction_model=model,
                )
            ),
        }

    structural_ok = all(item["ok"] for item in structural_reports.values())
    runtime_ok = runtime["ok"] and bool(runtime_reports) and all(
        item["ok"] for item in runtime_reports.values()
    )
    return {
        "artifact_type": "matters.flowguard-ui-flow-structure.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": (
            "ui_flow_green"
            if structural_ok and runtime_ok
            else ("structural_green_runtime_not_run" if structural_ok else "blocked")
        ),
        "ok": structural_ok and runtime_ok,
        "ui_revision": revision,
        "work_mode": "mixed",
        "runtime_evidence": runtime,
        "structural_reports": structural_reports,
        "runtime_reports": runtime_reports,
        "failures": sorted(
            {
                code
                for report in (*structural_reports.values(), *runtime_reports.values())
                for code in report["finding_codes"]
            }
        ),
        "blockers": runtime["blockers"],
        "skipped_checks": (
            [] if runtime["ok"] else ["runtime-only FlowGuard UI reviews"]
        ),
        "residual_risk": (
            []
        ),
        "claim_boundary": (
            "Native FlowGuard reviews admitted content, UI event/state behavior, "
            "journeys, capabilities, click-to-output chains, installed desktop runtime, "
            "English/zh-CN behavior, Standard/Compact cards, exactly eight detail "
            "sections, Files & information, AI supplemental information, a read-only "
            "evidence image gallery, truthful transport recovery, generated presentation-only "
            "heroes, latest-meaningful-clue catalog ordering, root-only catalog, "
            "Matter-only hierarchy graph, one reusable node quick view, "
            "logical-event timeline deduplication, no ordinary "
            "correction or canonical-write control, recovery, disclosure, approved font tokens, sidebar "
            "spacing, non-overlap, and desktop geometry. "
            "The separate C10 correction capability remains outside this object browser. "
            "Figma design evidence does not substitute for runtime proof."
        ),
        "typed_next_actions": (
            []
            if structural_ok and runtime_ok
            else [
                "implement the modeled eight-section root UI, Matter-only hierarchy "
                "and one reusable node quick view, generated hero, "
                "latest-meaningful-clue activity order, Files & information table, "
                "AI supplemental information, read-only evidence Images gallery, and "
                "truthful transport recovery; then "
                "produce current installed-browser evidence for every required check and "
                "rerun this owner"
            ]
        ),
    }


def main() -> int:
    receipt = build_receipt()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
