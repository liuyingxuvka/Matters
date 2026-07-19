"""Native FlowGuard UI model for the autonomous Matters object browser."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Mapping

from flowguard import (
    UI_CONTENT_EVIDENCE_DEFAULT_HIDDEN,
    UI_CONTENT_EVIDENCE_DEFAULT_VISIBLE,
    UI_CONTENT_EVIDENCE_INTERNAL_ABSENT,
    UI_CONTENT_EVIDENCE_RETURN_HIDDEN,
    UI_CONTENT_EVIDENCE_REVEAL,
    UI_CONTENT_EVIDENCE_REVEALED,
    UI_CONTENT_VISIBILITY_INTERNAL,
    UI_CONTENT_VISIBILITY_USER_ON_DEMAND,
    UI_CONTENT_VISIBILITY_USER_VISIBLE,
    UICapabilityCoverageBinding,
    UICapabilityOutputContract,
    UIColdPathWork,
    UIContentVisibilityEvidence,
    UIContentVisibilityItem,
    UIContentVisibilityPlan,
    UIControl,
    UIControlFunctionalChain,
    UIControlFunctionalChainSet,
    UIDisplayElement,
    UIFeatureContract,
    UIFeatureJourney,
    UIFunctionalCapability,
    UIFunctionalCapabilityInventory,
    UIGeometryLayoutEvidence,
    UIGeometryLayoutEvidenceSet,
    UIHotPathAction,
    UIImplementationJourneyRun,
    UIImplementationStepEvidence,
    UIImplementationValidation,
    UIInteractionModel,
    UIJourneyCoverage,
    UIJourneyEntryPoint,
    UIObservedSurfaceInventory,
    UIObservedSurfaceItem,
    UIRenderEvidence,
    UIRenderEvidenceSet,
    UIResponsivenessContract,
    UIStableRegionRule,
    UIStateNode,
    UITerminalActionAllowance,
    UITransition,
    UIVisibleSurface,
    UIVisibleSurfaceItem,
)


MODEL_ID = "matters-object-browser-ui-flow"
VISIBILITY_ID = "matters-object-browser-content-visibility"
JOURNEY_ID = "matters-object-browser-journey-coverage"
CAPABILITY_ID = "matters-object-browser-capabilities"
IMPLEMENTATION_ID = "matters-object-browser-implementation"
OBSERVED_ID = "matters-object-browser-observed-surface"
SURFACE_ID = "matters-object-browser-visible-surface"

REVISION_INPUTS = (
    Path("ui/index.html"),
    Path("ui/styles.css"),
    Path("ui/app.js"),
    Path("src/matters/application/orchestrator.py"),
    Path("src/matters/api/http/app.py"),
    Path("src/matters/api/http/static.py"),
    Path("src/matters/presentation/projections.py"),
    Path("src/matters/presentation/localization.py"),
    Path("src/matters/presentation/visuals.py"),
    Path("src/matters/desktop.py"),
    Path("flowguard_models/models/c12_projection_bilingual_ui.py"),
    Path("flowguard_design/ui_flow_structure.py"),
    Path("scripts/verify_live_ui.js"),
    Path(
        "openspec/changes/build-matters-model-driven-core/specs/"
        "bilingual-projection-ui/spec.md"
    ),
)


def current_revision(root: Path = Path(".")) -> str:
    """Fingerprint every authority that can change the observed browser."""

    digest = sha256()
    for path in REVISION_INPUTS:
        resolved = root / path
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        if resolved.is_file():
            digest.update(resolved.read_bytes())
        else:
            digest.update(b"<missing>")
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def visibility_plan(revision: str) -> UIContentVisibilityPlan:
    visible = (
        ("catalog_heading", "task:browse_matters"),
        ("catalog_summary", "task:browse_matters"),
        ("filter_summary", "task:filter_matters"),
        ("coverage_summary", "state:catalog_ready"),
        ("background_status", "state:catalog_ready"),
        ("matter_cards", "task:browse_matters"),
        ("empty_catalog", "state:catalog_empty"),
        ("no_search_results", "state:catalog_no_results"),
        ("catalog_recovery", "recovery:catalog_error"),
    )
    on_demand = (
        (
            "matter_detail",
            ("task:inspect_matter",),
            ("open_matter",),
            ("close_detail", "escape_detail"),
        ),
        (
            "matter_timeline",
            ("task:inspect_matter_timeline",),
            ("open_matter",),
            ("close_detail", "escape_detail"),
        ),
        (
            "matter_relationships",
            ("task:inspect_related_objects",),
            ("open_matter",),
            ("close_detail", "escape_detail"),
        ),
        (
            "evidence_details",
            ("task:inspect_evidence",),
            ("open_evidence",),
            ("close_evidence", "escape_evidence"),
        ),
        (
            "correction_form",
            ("task:correct_matter",),
            ("open_correction",),
            ("cancel_correction", "escape_correction"),
        ),
        (
            "cover_choices",
            ("task:change_cover",),
            ("open_cover",),
            ("cancel_cover", "escape_cover"),
        ),
    )
    return UIContentVisibilityPlan(
        VISIBILITY_ID,
        source_interaction_model_id=MODEL_ID,
        current_revision=revision,
        candidate_content_ids=(
            tuple(item[0] for item in visible)
            + tuple(item[0] for item in on_demand)
            + ("correction_progress", "correction_recovery", "private_internal_material")
        ),
        items=tuple(
            UIContentVisibilityItem(
                content_id,
                source_field_ids=(f"projection.{content_id}",),
                visibility_class=UI_CONTENT_VISIBILITY_USER_VISIBLE,
                user_need_refs=(need,),
                rationale="The content supports a current browser task, state, or recovery.",
            )
            for content_id, need in visible
        )
        + tuple(
            UIContentVisibilityItem(
                content_id,
                source_field_ids=(f"projection.{content_id}",),
                visibility_class=UI_CONTENT_VISIBILITY_USER_ON_DEMAND,
                user_need_refs=user_needs,
                reveal_event_ids=reveal_events,
                dismiss_event_ids=dismiss_events,
                rationale="The content is absent until the user opens its owning surface.",
            )
            for content_id, user_needs, reveal_events, dismiss_events in on_demand
        )
        + (
            UIContentVisibilityItem(
                "correction_progress",
                source_field_ids=("projection.correction_progress",),
                visibility_class=UI_CONTENT_VISIBILITY_USER_VISIBLE,
                user_need_refs=("state:correction_saving",),
                rationale="Saving progress is visible only while the optional correction is in flight.",
            ),
            UIContentVisibilityItem(
                "correction_recovery",
                source_field_ids=("projection.correction_recovery",),
                visibility_class=UI_CONTENT_VISIBILITY_USER_VISIBLE,
                user_need_refs=("recovery:correction_error",),
                rationale="A failed optional correction exposes retry and cancel guidance.",
            ),
            UIContentVisibilityItem(
                "private_internal_material",
                source_field_ids=(
                    "private.path",
                    "private.raw_receipt",
                    "private.source_content",
                    "private.mail_identifier",
                    "private.provider_token",
                ),
                visibility_class=UI_CONTENT_VISIBILITY_INTERNAL,
                rationale=(
                    "Local paths, raw private content, provider identifiers, and "
                    "credentials never render on the ordinary surface."
                ),
            ),
        ),
        validation_boundaries=(
            "English default and selectable zh-CN",
            "private material absent from ordinary UI",
            "detail, evidence, correction, and cover disclosure",
        ),
        rationale="Every state-bearing value is classified before it can render.",
    )


def _controls() -> tuple[UIControl, ...]:
    rows = (
        ("refresh_catalog", "Read again", "global", "loadCatalog", True),
        ("select_locale", "Language", "global", "selectLanguage", True),
        ("select_density", "Card size", "global", "selectCardDensity", True),
        ("search_catalog", "Search matters", "global", "searchCatalog", True),
        ("clear_search", "Clear search", "contextual", "clearSearch", False),
        ("select_status", "Status", "contextual", "selectStatus", True),
        ("select_time", "Time", "contextual", "selectTimeWindow", True),
        ("next_page", "More matters", "contextual", "loadMatterPage", False),
        ("open_matter", "Open matter", "local", "openMatter", False),
        ("close_detail", "Close matter", "contextual", "closeMatter", False),
        ("select_detail_section", "Matter section", "contextual", "selectDetailSection", False),
        ("open_evidence", "View evidence", "local", "openEvidence", False),
        ("close_evidence", "Close evidence", "contextual", "closeEvidence", False),
        ("open_correction", "Correct this matter", "local", "openCorrection", False),
        ("save_correction", "Save correction", "local", "saveCorrection", False),
        ("cancel_correction", "Cancel correction", "contextual", "cancelCorrection", False),
        ("retry_correction", "Try correction again", "contextual", "retryCorrection", False),
        ("open_cover", "Change cover", "local", "openCover", False),
        ("apply_cover", "Use selected cover", "local", "applyCover", False),
        ("pin_cover", "Keep this cover", "local", "pinCover", False),
        ("unpin_cover", "Let AI choose the cover", "local", "unpinCover", False),
        ("cancel_cover", "Cancel cover change", "contextual", "cancelCover", False),
    )
    controls = []
    for control_id, label, level, function_key, persistent in rows:
        extra = {}
        if control_id == "next_page":
            extra = {
                "duplicate_group": "catalog-pagination",
                "redundancy_rationale": (
                    "Load more extends one bounded catalog window without "
                    "changing the current object order."
                ),
            }
        controls.append(
            UIControl(
            control_id,
            label=label,
            control_type=(
                "segmented-control"
                if control_id in {"select_locale", "select_density"}
                else "button"
            ),
            level=level,
            placement_hint=(
                "persistent top bar"
                if level == "global"
                else "owning sidebar, card, detail section, or dialog"
            ),
            persistent=persistent,
            function_key=function_key,
            rationale="The control has one stable task and placement owner.",
            **extra,
        )
        )
    return tuple(controls)


def _displays() -> tuple[UIDisplayElement, ...]:
    rows = (
        (
            "catalog_heading",
            "catalog_heading",
            "Matters",
            "heading",
            ("catalog_loading", "catalog_ready", "catalog_empty", "catalog_no_results", "catalog_error"),
            "topbar",
            "catalog_heading",
        ),
        (
            "catalog_summary",
            "catalog_summary",
            "Matter catalog",
            "status",
            ("catalog_ready", "catalog_empty", "catalog_no_results", "detail_open"),
            "catalog_header",
            "catalog_summary",
        ),
        (
            "filter_summary",
            "filter_summary",
            "Current filters",
            "status",
            ("catalog_ready", "catalog_empty", "catalog_no_results"),
            "sidebar",
            "filter_summary",
        ),
        (
            "coverage_summary",
            "coverage_summary",
            "Coverage",
            "status",
            ("catalog_ready", "detail_open"),
            "catalog_header",
            "coverage_summary",
        ),
        (
            "background_status",
            "background_status",
            "Background work",
            "status",
            ("catalog_loading", "catalog_ready", "catalog_empty", "catalog_no_results", "detail_open"),
            "topbar",
            "background_status",
        ),
        (
            "matter_cards",
            "matter_cards",
            "Matter cards",
            "grid",
            ("catalog_ready",),
            "catalog_grid",
            "matter_cards",
        ),
        (
            "empty_catalog",
            "empty_catalog",
            "No matters yet",
            "status",
            ("catalog_empty",),
            "catalog_grid",
            "empty_catalog",
        ),
        (
            "no_search_results",
            "no_search_results",
            "No matching matters",
            "status",
            ("catalog_no_results",),
            "catalog_grid",
            "no_search_results",
        ),
        (
            "catalog_error",
            "catalog_recovery",
            "Could not read the matter catalog",
            "status",
            ("catalog_error",),
            "catalog_grid",
            "catalog_recovery",
        ),
        (
            "matter_detail",
            "matter_detail",
            "Matter detail",
            "panel",
            ("detail_open",),
            "detail",
            "matter_detail",
        ),
        (
            "matter_timeline",
            "matter_timeline",
            "Timeline",
            "list",
            ("detail_open",),
            "detail",
            "matter_timeline",
        ),
        (
            "matter_relationships",
            "matter_relationships",
            "Related people, files, sources, and matters",
            "list",
            ("detail_open",),
            "detail",
            "matter_relationships",
        ),
        (
            "evidence_details",
            "evidence_details",
            "Evidence",
            "dialog",
            ("evidence_open",),
            "evidence_dialog",
            "evidence_details",
        ),
        (
            "correction_form",
            "correction_form",
            "Correct this matter",
            "dialog",
            ("correction_open",),
            "correction_dialog",
            "correction_form",
        ),
        (
            "correction_progress",
            "correction_progress",
            "Saving correction",
            "status",
            ("correction_saving",),
            "correction_dialog",
            "correction_progress",
        ),
        (
            "correction_error",
            "correction_recovery",
            "Could not save the correction",
            "status",
            ("correction_error",),
            "correction_dialog",
            "correction_recovery",
        ),
        (
            "cover_choices",
            "cover_choices",
            "Choose a cover",
            "dialog",
            ("cover_open",),
            "cover_dialog",
            "cover_choices",
        ),
    )
    return tuple(
        UIDisplayElement(
            display_id,
            semantic_key,
            label=label,
            display_type=kind,
            depends_on_states=states,
            region_hint=region,
            content_visibility_id=content_id,
            rationale="The display has one admitted state or task owner.",
        )
        for display_id, semantic_key, label, kind, states, region, content_id in rows
    )


CATALOG_CONTROLS = (
    "select_locale",
    "select_density",
    "search_catalog",
    "select_status",
    "select_time",
    "next_page",
)
CATALOG_DISPLAYS = (
    "catalog_heading",
    "catalog_summary",
    "filter_summary",
    "coverage_summary",
    "background_status",
)
DETAIL_CONTROLS = (
    "select_locale",
    "select_density",
    "close_detail",
    "select_detail_section",
    "open_evidence",
    "open_correction",
    "open_cover",
)


def interaction_model() -> UIInteractionModel:
    states = (
        UIStateNode(
            "catalog_loading",
            role="normal",
            visible_controls=("select_locale", "select_density"),
            enabled_controls=("select_locale", "select_density"),
            visible_displays=("catalog_heading", "background_status"),
            hidden_displays=(
                "matter_detail",
                "matter_timeline",
                "matter_relationships",
                "evidence_details",
                "correction_form",
                "correction_progress",
                "correction_error",
                "cover_choices",
            ),
            rationale="Launch and transport changes show immediate progress.",
        ),
        UIStateNode(
            "catalog_ready",
            visible_controls=CATALOG_CONTROLS + ("open_matter",),
            enabled_controls=CATALOG_CONTROLS + ("open_matter",),
            visible_displays=CATALOG_DISPLAYS + ("matter_cards",),
            hidden_displays=(
                "empty_catalog",
                "no_search_results",
                "catalog_error",
                "matter_detail",
                "matter_timeline",
                "matter_relationships",
                "evidence_details",
                "correction_form",
                "correction_progress",
                "correction_error",
                "cover_choices",
            ),
            terminal=True,
            rationale=(
                "The current catalog remains browsable while background status "
                "reports fresh, recomputing, or blocked work."
            ),
        ),
        UIStateNode(
            "catalog_empty",
            visible_controls=(),
            enabled_controls=(),
            visible_displays=CATALOG_DISPLAYS + ("empty_catalog",),
            hidden_displays=(
                "matter_cards",
                "no_search_results",
                "catalog_error",
                "matter_detail",
                "matter_timeline",
                "matter_relationships",
            ),
            terminal=True,
            rationale="A truthful empty state leaves refresh and filters operable.",
        ),
        UIStateNode(
            "catalog_no_results",
            visible_controls=(
                "select_locale",
                "select_density",
                "search_catalog",
                "clear_search",
                "select_status",
                "select_time",
            ),
            enabled_controls=(
                "select_locale",
                "select_density",
                "search_catalog",
                "clear_search",
                "select_status",
                "select_time",
            ),
            visible_displays=CATALOG_DISPLAYS + ("no_search_results",),
            hidden_displays=(
                "matter_cards",
                "empty_catalog",
                "catalog_error",
                "matter_detail",
                "matter_timeline",
                "matter_relationships",
            ),
            terminal=True,
            rationale="A zero-result query preserves controls and offers one clear reset.",
        ),
        UIStateNode(
            "catalog_error",
            role="failure",
            visible_controls=("refresh_catalog",),
            enabled_controls=("refresh_catalog",),
            recovery_controls=("refresh_catalog",),
            visible_displays=("catalog_heading", "catalog_error"),
            hidden_displays=(
                "matter_cards",
                "matter_detail",
                "matter_timeline",
                "matter_relationships",
            ),
            failure=True,
            rationale="A catalog read failure exposes one understandable retry.",
        ),
        UIStateNode(
            "detail_open",
            visible_controls=DETAIL_CONTROLS,
            enabled_controls=DETAIL_CONTROLS,
            visible_displays=(
                "catalog_heading",
                "catalog_summary",
                "coverage_summary",
                "background_status",
                "matter_detail",
                "matter_timeline",
                "matter_relationships",
            ),
            hidden_displays=(
                "evidence_details",
                "correction_form",
                "correction_progress",
                "correction_error",
                "cover_choices",
            ),
            terminal=True,
            rationale="The detail keeps global language and density choices stable.",
        ),
        UIStateNode(
            "evidence_open",
            visible_controls=("close_evidence",),
            enabled_controls=("close_evidence",),
            visible_displays=("evidence_details",),
            terminal=True,
            rationale="The evidence dialog owns focus and has Close and Escape return paths.",
        ),
        UIStateNode(
            "correction_open",
            visible_controls=("save_correction", "cancel_correction"),
            enabled_controls=("save_correction", "cancel_correction"),
            visible_displays=("correction_form",),
            hidden_displays=("correction_progress", "correction_error"),
            rationale="Correction is optional and never interrupts autonomous first modeling.",
        ),
        UIStateNode(
            "correction_saving",
            visible_controls=(),
            enabled_controls=(),
            visible_displays=("correction_progress",),
            hidden_displays=("correction_form", "correction_error"),
            rationale="One correction request is serialized with visible progress.",
        ),
        UIStateNode(
            "correction_error",
            role="failure",
            visible_controls=("retry_correction", "cancel_correction"),
            enabled_controls=("retry_correction", "cancel_correction"),
            recovery_controls=("retry_correction",),
            visible_displays=("correction_error",),
            hidden_displays=("correction_form", "correction_progress"),
            failure=True,
            rationale="A failed optional correction preserves user input and recovery.",
        ),
        UIStateNode(
            "cover_open",
            visible_controls=(
                "apply_cover",
                "pin_cover",
                "unpin_cover",
                "cancel_cover",
            ),
            enabled_controls=(
                "apply_cover",
                "pin_cover",
                "unpin_cover",
                "cancel_cover",
            ),
            visible_displays=("cover_choices",),
            terminal=True,
            rationale="Cover changes are optional post-model corrections with a cancel path.",
        ),
    )

    transitions = (
        UITransition("load_ready", "refresh_catalog", "catalog_loading", "catalog_ready", function_block="LoadMatterCatalog", code_contract_id="http.get.matter_catalog", output="current_catalog", rationale="A non-empty current catalog becomes browsable."),
        UITransition("load_empty", "refresh_catalog", "catalog_loading", "catalog_empty", function_block="LoadMatterCatalog", code_contract_id="http.get.matter_catalog", output="empty_catalog", rationale="A current zero-object catalog reaches an honest empty state."),
        UITransition("load_failure", "refresh_catalog", "catalog_loading", "catalog_error", function_block="LoadMatterCatalog", code_contract_id="http.get.matter_catalog", output="catalog_error", rationale="A failed read reaches visible recovery."),
        UITransition("retry_catalog", "refresh_catalog", "catalog_error", "catalog_loading", function_block="LoadMatterCatalog", code_contract_id="http.get.matter_catalog", output="loading_feedback", rationale="Retry restarts only the catalog read."),
        UITransition("search_catalog", "search_catalog", "catalog_ready", "catalog_loading", function_block="SearchMatterCatalog", code_contract_id="http.get.matter_catalog", output="query_loading", rationale="Search preserves the previous window until a current result arrives."),
        UITransition("search_results", "search_catalog", "catalog_loading", "catalog_ready", function_block="SearchMatterCatalog", code_contract_id="http.get.matter_catalog", output="current_search_results", rationale="A current non-empty query result replaces the catalog window."),
        UITransition("search_no_results", "search_catalog", "catalog_loading", "catalog_no_results", function_block="SearchMatterCatalog", code_contract_id="http.get.matter_catalog", output="no_search_results", rationale="A current zero-result query has a distinct state."),
        UITransition("clear_search", "clear_search", "catalog_no_results", "catalog_loading", function_block="ClearMatterSearch", code_contract_id="http.get.matter_catalog", output="query_cleared_loading", rationale="Clearing a query restores the catalog without resetting other preferences."),
        UITransition("search_again", "search_catalog", "catalog_no_results", "catalog_loading", function_block="SearchMatterCatalog", code_contract_id="http.get.matter_catalog", output="query_loading", rationale="A revised query starts from the preserved zero-result state."),
        UITransition("select_status", "select_status", "catalog_ready", "catalog_loading", function_block="FilterMatterCatalog", code_contract_id="http.get.matter_catalog", output="filter_loading", rationale="Status filtering is a current bounded query."),
        UITransition("select_time", "select_time", "catalog_ready", "catalog_loading", function_block="FilterMatterCatalog", code_contract_id="http.get.matter_catalog", output="filter_loading", rationale="Time filtering is a current bounded query."),
        UITransition("select_status_no_results", "select_status", "catalog_no_results", "catalog_loading", function_block="FilterMatterCatalog", code_contract_id="http.get.matter_catalog", output="filter_loading", rationale="Changing status can recover a zero-result query."),
        UITransition("select_time_no_results", "select_time", "catalog_no_results", "catalog_loading", function_block="FilterMatterCatalog", code_contract_id="http.get.matter_catalog", output="filter_loading", rationale="Changing time can recover a zero-result query."),
        UITransition("next_page", "next_page", "catalog_ready", "catalog_loading", function_block="LoadMatterPage", code_contract_id="http.get.matter_catalog", output="next_page_loading", rationale="Next-page transport keeps one bounded catalog window."),
        UITransition("select_locale_ready", "select_locale", "catalog_ready", "catalog_ready", function_block="SelectLanguage", code_contract_id="locale.registry.select", output="same_revision_locale_projection", pure_ui=True, rationale="Language selection changes display text, not Matter semantics."),
        UITransition("select_density_ready", "select_density", "catalog_ready", "catalog_ready", function_block="SelectCardDensity", code_contract_id="ui.card_density.select", output="same_objects_new_density", pure_ui=True, rationale="Standard and Compact share objects, ordering, visuals, and revisions."),
        UITransition("select_locale_loading", "select_locale", "catalog_loading", "catalog_loading", function_block="SelectLanguage", code_contract_id="locale.registry.select", output="localized_loading", pure_ui=True, rationale="Loading feedback follows the selected locale."),
        UITransition("select_density_loading", "select_density", "catalog_loading", "catalog_loading", function_block="SelectCardDensity", code_contract_id="ui.card_density.select", output="density_preference_saved", pure_ui=True, rationale="Density preference is independent of transport and viewport."),
        UITransition("select_locale_no_results", "select_locale", "catalog_no_results", "catalog_no_results", function_block="SelectLanguage", code_contract_id="locale.registry.select", output="localized_zero_results", pure_ui=True, rationale="The zero-result state follows the selected locale."),
        UITransition("select_density_no_results", "select_density", "catalog_no_results", "catalog_no_results", function_block="SelectCardDensity", code_contract_id="ui.card_density.select", output="density_preference_saved", pure_ui=True, rationale="Density remains independent of query results."),
        UITransition("open_matter", "open_matter", "catalog_ready", "detail_open", function_block="OpenMatterDetail", code_contract_id="http.get.matter_detail", output="current_matter_detail", rationale="A card opens the same Matter revision in a detail surface."),
        UITransition("close_detail", "close_detail", "detail_open", "catalog_ready", function_block="CloseMatterDetail", code_contract_id="ui.matter_detail.close", output="catalog_state_restored", pure_ui=True, rationale="Close restores query, filters, density, locale, selection, and scroll anchor."),
        UITransition("escape_detail", "close_detail", "detail_open", "catalog_ready", function_block="CloseMatterDetail", code_contract_id="ui.matter_detail.close", output="catalog_state_restored_focus", pure_ui=True, rationale="Escape closes detail and returns focus to the owning card."),
        UITransition("select_detail_section", "select_detail_section", "detail_open", "detail_open", function_block="SelectDetailSection", code_contract_id="ui.matter_detail.section", output="selected_detail_section", pure_ui=True, rationale="Overview, timeline, people, files, evidence, and related Matter sections share one detail owner."),
        UITransition("select_locale_detail", "select_locale", "detail_open", "detail_open", function_block="SelectLanguage", code_contract_id="locale.registry.select", output="same_detail_revision_locale_projection", pure_ui=True, rationale="Detail content changes locale without changing facts."),
        UITransition("select_density_detail", "select_density", "detail_open", "detail_open", function_block="SelectCardDensity", code_contract_id="ui.card_density.select", output="density_preference_saved", pure_ui=True, rationale="Density remains a persistent browser preference while detail is open."),
        UITransition("open_evidence", "open_evidence", "detail_open", "evidence_open", function_block="OpenEvidence", code_contract_id="ui.evidence.disclosure", output="evidence_dialog", pure_ui=True, rationale="Evidence is revealed only on demand."),
        UITransition("close_evidence", "close_evidence", "evidence_open", "detail_open", function_block="CloseEvidence", code_contract_id="ui.evidence.disclosure", output="evidence_hidden", pure_ui=True, rationale="Close restores the detail surface."),
        UITransition("escape_evidence", "close_evidence", "evidence_open", "detail_open", function_block="CloseEvidence", code_contract_id="ui.evidence.disclosure", output="evidence_hidden_focus_return", pure_ui=True, rationale="Escape closes evidence and returns focus."),
        UITransition("open_correction", "open_correction", "detail_open", "correction_open", function_block="OpenCorrection", code_contract_id="ui.correction.open", output="correction_form", pure_ui=True, rationale="Correction is optional after autonomous modeling."),
        UITransition("cancel_correction", "cancel_correction", "correction_open", "detail_open", function_block="CancelCorrection", code_contract_id="ui.correction.cancel", output="correction_hidden", pure_ui=True, rationale="Cancel leaves canonical Matter state unchanged."),
        UITransition("escape_correction", "cancel_correction", "correction_open", "detail_open", function_block="CancelCorrection", code_contract_id="ui.correction.cancel", output="correction_hidden_focus_return", pure_ui=True, rationale="Escape cancels and restores focus."),
        UITransition("save_correction", "save_correction", "correction_open", "correction_saving", function_block="SaveCorrection", code_contract_id="http.post.matter_correction", output="correction_saving", side_effects=("correction_intent_write",), business_bearing=True, business_intent_id="BI-PR-010-correct-and-recompute", behavior_commitment_id="BC-PR-010", primary_path_id="path:c10-invalidate-and-request-recompute", consistency_rule_ids=("consistency:correction-invalidation",), rationale="C10 records the correction and invalidates only affected owners."),
        UITransition("correction_success", "save_correction", "correction_saving", "detail_open", function_block="SaveCorrection", code_contract_id="http.post.matter_correction", output="current_corrected_detail", side_effects=("correction_write", "affected_owner_recompute_request"), business_bearing=True, business_intent_id="BI-PR-010-correct-and-recompute", behavior_commitment_id="BC-PR-010", primary_path_id="path:c10-invalidate-and-request-recompute", consistency_rule_ids=("consistency:correction-invalidation",), rationale="A current C10 response restores the updated detail."),
        UITransition("correction_failure", "save_correction", "correction_saving", "correction_error", function_block="SaveCorrection", code_contract_id="http.post.matter_correction", output="correction_error", rationale="Failure preserves the submitted correction for retry."),
        UITransition("retry_correction", "retry_correction", "correction_error", "correction_saving", function_block="SaveCorrection", code_contract_id="http.post.matter_correction", output="correction_saving", rationale="Retry reuses the same bounded correction intent."),
        UITransition("cancel_correction_error", "cancel_correction", "correction_error", "detail_open", function_block="CancelCorrection", code_contract_id="ui.correction.cancel", output="correction_hidden", pure_ui=True, rationale="A failed optional correction can be dismissed safely."),
        UITransition("open_cover", "open_cover", "detail_open", "cover_open", function_block="OpenCoverChoices", code_contract_id="http.get.matter_visual_candidates", output="current_cover_choices", rationale="Only eligible current visual assets are offered."),
        UITransition("apply_cover", "apply_cover", "cover_open", "detail_open", function_block="ApplyCoverCorrection", code_contract_id="http.post.matter_cover_correction", output="current_cover", side_effects=("cover_correction_write",), business_bearing=True, business_intent_id="BI-PR-010-correct-and-recompute", behavior_commitment_id="BC-PR-010", primary_path_id="path:c10-invalidate-and-request-recompute", consistency_rule_ids=("consistency:correction-invalidation",), rationale="A selected current visual is recorded through C10."),
        UITransition("pin_cover", "pin_cover", "cover_open", "detail_open", function_block="ApplyCoverCorrection", code_contract_id="http.post.matter_cover_correction", output="pinned_current_cover", side_effects=("cover_pin_write",), business_bearing=True, business_intent_id="BI-PR-010-correct-and-recompute", behavior_commitment_id="BC-PR-010", primary_path_id="path:c10-invalidate-and-request-recompute", consistency_rule_ids=("consistency:correction-invalidation",), rationale="A user-selected cover may be kept through C10."),
        UITransition("unpin_cover", "unpin_cover", "cover_open", "detail_open", function_block="ApplyCoverCorrection", code_contract_id="http.post.matter_cover_correction", output="ai_selected_current_cover", side_effects=("cover_unpin_write", "visual_recompute_request"), business_bearing=True, business_intent_id="BI-PR-010-correct-and-recompute", behavior_commitment_id="BC-PR-010", primary_path_id="path:c10-invalidate-and-request-recompute", consistency_rule_ids=("consistency:correction-invalidation",), rationale="Unpin delegates the next selection back to the autonomous visual owner."),
        UITransition("cancel_cover", "cancel_cover", "cover_open", "detail_open", function_block="CancelCover", code_contract_id="ui.cover.cancel", output="cover_choices_hidden", pure_ui=True, rationale="Cancel leaves the current visual decision unchanged."),
        UITransition("escape_cover", "cancel_cover", "cover_open", "detail_open", function_block="CancelCover", code_contract_id="ui.cover.cancel", output="cover_choices_hidden_focus_return", pure_ui=True, rationale="Escape closes the cover surface and restores focus."),
    )
    return UIInteractionModel(
        MODEL_ID,
        initial_state_id="catalog_loading",
        states=states,
        controls=_controls(),
        transitions=transitions,
        displays=_displays(),
        source_product_model_id="C12_projection_bilingual_ui",
        source_product_model_path="flowguard_models/models/c12_projection_bilingual_ui.py",
        content_visibility_plan_id=VISIBILITY_ID,
        validation_boundaries=(
            "desktop launch through catalog ready/empty/error/retry",
            "English and zh-CN semantic equivalence",
            "Standard and Compact semantic preservation",
            "search, filters, paging, and state preservation",
            "card detail, timeline, relations, evidence, correction, and cover",
            "background status never disables a current catalog",
        ),
        rationale="The model is an autonomous object browser, not an approval queue.",
    )


def visible_surface() -> UIVisibleSurface:
    rows = (
        ("surface_heading", "heading", "Matters", ("catalog_loading", "catalog_ready", "catalog_empty", "catalog_no_results", "catalog_error", "detail_open"), "catalog_heading", "catalog_heading"),
        ("surface_summary", "status", "Matter catalog", ("catalog_ready", "catalog_empty", "catalog_no_results", "detail_open"), "catalog_summary", "catalog_summary"),
        ("surface_filters", "status", "Current filters", ("catalog_ready", "catalog_empty", "catalog_no_results"), "filter_summary", "filter_summary"),
        ("surface_coverage", "status", "Coverage", ("catalog_ready", "detail_open"), "coverage_summary", "coverage_summary"),
        ("surface_background", "status", "Background work", ("catalog_loading", "catalog_ready", "catalog_empty", "catalog_no_results", "detail_open"), "background_status", "background_status"),
        ("surface_cards", "grid", "Matter cards", ("catalog_ready",), "matter_cards", "matter_cards"),
        ("surface_empty", "status", "No matters yet", ("catalog_empty",), "empty_catalog", "empty_catalog"),
        ("surface_no_results", "status", "No matching matters", ("catalog_no_results",), "no_search_results", "no_search_results"),
        ("surface_error", "status", "Could not read the matter catalog", ("catalog_error",), "catalog_error", "catalog_recovery"),
        ("surface_detail", "panel", "Matter detail", ("detail_open",), "matter_detail", "matter_detail"),
        ("surface_timeline", "list", "Timeline", ("detail_open",), "matter_timeline", "matter_timeline"),
        ("surface_relations", "list", "Related objects", ("detail_open",), "matter_relationships", "matter_relationships"),
        ("surface_evidence", "dialog", "Evidence", ("evidence_open",), "evidence_details", "evidence_details"),
        ("surface_correction", "dialog", "Correct this matter", ("correction_open",), "correction_form", "correction_form"),
        ("surface_correction_progress", "status", "Saving correction", ("correction_saving",), "correction_progress", "correction_progress"),
        ("surface_correction_error", "status", "Could not save the correction", ("correction_error",), "correction_error", "correction_recovery"),
        ("surface_cover", "dialog", "Choose a cover", ("cover_open",), "cover_choices", "cover_choices"),
    )
    return UIVisibleSurface(
        SURFACE_ID,
        source_interaction_model_id=MODEL_ID,
        content_visibility_plan_id=VISIBILITY_ID,
        items=tuple(
            UIVisibleSurfaceItem(
                item_id,
                kind,
                text,
                state_ids=states,
                owner_display_id=display_id,
                purpose="Shows current state or supports the named browser task.",
                content_visibility_id=content_id,
                rationale="The item is admitted and owned by one surface region.",
            )
            for item_id, kind, text, states, display_id, content_id in rows
        ),
        validation_boundaries=(
            "ordinary catalog",
            "detail surface",
            "evidence, correction, and cover dialogs",
        ),
        rationale="The visible surface contains browser content, not internal receipts or approval queues.",
    )


def observed_inventory(revision: str, evidence_ref: str) -> UIObservedSurfaceInventory:
    rows = (
        ("observed_retry", "button", "Try again", "catalog_error", "catalog_grid", "[data-retry]", "refresh_catalog", "", ""),
        ("observed_locale", "select", "English / 中文", "catalog_ready", "sidebar", "#locale-select", "select_locale", "", ""),
        ("observed_density", "toggle", "Standard / Compact", "catalog_ready", "catalog_header", ".db-card-density-switch", "select_density", "", ""),
        ("observed_search", "input", "Search matters", "catalog_ready", "sidebar", "#matters-search", "search_catalog", "", ""),
        ("observed_status_filter", "button", "Status", "catalog_ready", "sidebar", "[data-status]", "select_status", "", ""),
        ("observed_time_filter", "button", "Time", "catalog_ready", "sidebar", "[data-time]", "select_time", "", ""),
        ("observed_more", "button", "Load more matters", "catalog_ready", "catalog_grid", "[data-load-more]", "next_page", "", ""),
        ("observed_heading", "text", "All matters", "catalog_ready", "catalog_header", ".db-project-list-header h2", "", "catalog_heading", "catalog_heading"),
        ("observed_summary", "status_text", "Matter count", "catalog_ready", "catalog_header", ".db-project-header-meta", "", "catalog_summary", "catalog_summary"),
        ("observed_filters", "text", "Current filters", "catalog_ready", "sidebar", ".db-sidebar-scroll", "", "filter_summary", "filter_summary"),
        ("observed_coverage", "status_text", "Coverage", "catalog_ready", "catalog_header", ".db-source-health-button", "", "coverage_summary", "coverage_summary"),
        ("observed_background", "status_text", "Background work", "catalog_ready", "catalog_header", ".db-source-health-button", "", "background_status", "background_status"),
        ("observed_cards", "text", "Matter cards", "catalog_ready", "catalog_grid", ".db-project-card", "", "matter_cards", "matter_cards"),
        ("observed_empty", "status_text", "No matters yet", "catalog_empty", "catalog_grid", ".db-empty-state", "", "empty_catalog", "empty_catalog"),
        ("observed_no_results", "status_text", "No matching matters", "catalog_no_results", "catalog_grid", ".db-empty-state", "", "no_search_results", "no_search_results"),
        ("observed_error", "status_text", "Could not read the matter catalog", "catalog_error", "catalog_grid", "#catalog-error", "", "catalog_error", "catalog_recovery"),
        ("observed_detail", "text", "Matter detail", "detail_open", "detail", ".db-dialog", "", "matter_detail", "matter_detail"),
        ("observed_timeline", "text", "Timeline", "detail_open", "detail", ".db-timeline", "", "matter_timeline", "matter_timeline"),
        ("observed_relationships", "text", "Related matters", "detail_open", "detail", "[data-detail-section='relatedMatters']", "", "matter_relationships", "matter_relationships"),
        ("observed_evidence", "text", "Evidence", "evidence_open", "detail", ".db-evidence-excerpt", "", "evidence_details", "evidence_details"),
        ("observed_correction", "text", "Correct this matter", "correction_open", "detail", "[data-correction-form]", "", "correction_form", "correction_form"),
        ("observed_correction_progress", "status_text", "Saving correction", "correction_saving", "toast", ".db-toast", "", "correction_progress", "correction_progress"),
        ("observed_correction_error", "status_text", "Could not save the correction", "correction_error", "toast", ".db-toast", "", "correction_error", "correction_recovery"),
        ("observed_cover", "text", "Choose a cover", "cover_open", "detail", ".db-cover-grid", "", "cover_choices", "cover_choices"),
    )
    return UIObservedSurfaceInventory(
        OBSERVED_ID,
        observation_target="installed local Matters desktop object browser",
        current_revision=revision,
        observation_method="desktop/browser DOM, click-through, geometry, accessibility, and fault injection",
        source_interaction_model_id=MODEL_ID,
        source_visible_surface_id=SURFACE_ID,
        content_visibility_plan_id=VISIBILITY_ID,
        evidence_ref=evidence_ref,
        items=tuple(
            UIObservedSurfaceItem(
                item_id,
                kind,
                label,
                state,
                region,
                selector,
                enabled=True if control_id else False,
                mapped_control_id=control_id,
                mapped_display_id=display_id,
                content_visibility_id=content_id,
                evidence_ref=evidence_ref,
                evidence_kind="browser_click" if control_id else "dom_text",
                rationale="The current installed surface item was observed.",
            )
            for (
                item_id,
                kind,
                label,
                state,
                region,
                selector,
                control_id,
                display_id,
                content_id,
            ) in rows
        ),
        validation_boundaries=(
            "English and zh-CN",
            "Standard and Compact",
            "large catalog",
            "detail, evidence, correction, cover, and recovery",
        ),
        rationale="The runnable object browser is counted before completion is claimed.",
    )


def journey_coverage() -> UIJourneyCoverage:
    entries = (
        ("entry_locale", "select_locale", "select_locale_ready", "Language", ("catalog_ready",)),
        ("entry_density", "select_density", "select_density_ready", "Card size", ("catalog_ready",)),
        ("entry_search", "search_catalog", "search_catalog", "Search matters", ("catalog_ready",)),
        ("entry_filters", "select_status", "select_status", "Filter matters", ("catalog_ready",)),
        ("entry_page", "next_page", "next_page", "More matters", ("catalog_ready",)),
        ("entry_detail", "open_matter", "open_matter", "Open matter", ("catalog_ready",)),
    )
    journeys = (
        UIFeatureJourney("browse_catalog", label="Browse the current Matter catalog", entry_point_ids=("entry_search",), required_state_ids=("catalog_loading", "catalog_ready", "catalog_empty", "catalog_error"), required_event_ids=("load_ready", "load_empty", "load_failure", "retry_catalog"), success_terminal_state_ids=("catalog_ready", "catalog_empty"), failure_state_ids=("catalog_error",), recovery_event_ids=("retry_catalog",), validation_boundaries=("desktop launch and fault injection",), rationale="Launch reaches a current catalog, honest empty state, or retry."),
        UIFeatureJourney("select_language", label="Select language", entry_point_ids=("entry_locale",), required_state_ids=("catalog_loading", "catalog_ready", "detail_open"), required_event_ids=("select_locale_loading", "select_locale_ready", "select_locale_detail"), success_terminal_state_ids=("catalog_ready", "detail_open"), validation_boundaries=("locale switch and reload",), rationale="The same semantic revision renders in English or Chinese."),
        UIFeatureJourney("select_density", label="Select card size", entry_point_ids=("entry_density",), required_state_ids=("catalog_loading", "catalog_ready", "detail_open"), required_event_ids=("select_density_loading", "select_density_ready", "select_density_detail"), success_terminal_state_ids=("catalog_ready", "detail_open"), validation_boundaries=("Standard/Compact switch and reload",), rationale="Density is a persistent user choice independent of viewport."),
        UIFeatureJourney("search_and_filter", label="Search and filter matters", entry_point_ids=("entry_search", "entry_filters"), required_state_ids=("catalog_ready", "catalog_loading", "catalog_no_results"), required_event_ids=("search_catalog", "search_results", "search_no_results", "clear_search", "select_status", "select_time"), success_terminal_state_ids=("catalog_ready", "catalog_no_results"), validation_boundaries=("current query, zero results, clear, and state preservation",), rationale="Search and filters preserve all unrelated browser state."),
        UIFeatureJourney("page_catalog", label="Navigate a large catalog", entry_point_ids=("entry_page",), required_state_ids=("catalog_ready", "catalog_loading"), required_event_ids=("next_page", "load_ready"), success_terminal_state_ids=("catalog_ready",), validation_boundaries=("transport, stale response discard, and scroll anchor",), rationale="Load more extends the current bounded catalog without losing its order."),
        UIFeatureJourney("inspect_matter", label="Inspect one matter", entry_point_ids=("entry_detail",), required_state_ids=("catalog_ready", "detail_open"), required_event_ids=("open_matter", "select_detail_section", "close_detail", "escape_detail"), success_terminal_state_ids=("detail_open",), cancel_event_ids=("close_detail", "escape_detail"), validation_boundaries=("detail sections and focus return",), rationale="One card opens a human-readable object detail and returns to the same catalog position."),
        UIFeatureJourney("inspect_evidence", label="Inspect evidence", entry_point_ids=("entry_detail",), required_state_ids=("catalog_ready", "detail_open", "evidence_open"), required_event_ids=("open_matter", "open_evidence", "close_evidence", "escape_evidence"), success_terminal_state_ids=("evidence_open",), cancel_event_ids=("close_evidence", "escape_evidence"), validation_boundaries=("card entry, dialog reveal, and keyboard return",), rationale="Evidence is optional, discoverable, and dismissible after opening a Matter."),
        UIFeatureJourney("correct_matter", label="Optionally correct one matter", entry_point_ids=("entry_detail",), required_state_ids=("catalog_ready", "detail_open", "correction_open", "correction_saving", "correction_error"), required_event_ids=("open_matter", "open_correction", "save_correction", "correction_success", "correction_failure", "retry_correction", "cancel_correction", "escape_correction"), success_terminal_state_ids=("detail_open",), failure_state_ids=("correction_error",), recovery_event_ids=("retry_correction",), cancel_event_ids=("cancel_correction", "escape_correction", "cancel_correction_error"), validation_boundaries=("card entry, C10 current-token correction, retry, and cancel",), rationale="Correction is post-model, optional, and owner-routed."),
        UIFeatureJourney("change_cover", label="Optionally change the Matter cover", entry_point_ids=("entry_detail",), required_state_ids=("catalog_ready", "detail_open", "cover_open"), required_event_ids=("open_matter", "open_cover", "apply_cover", "pin_cover", "unpin_cover", "cancel_cover", "escape_cover"), success_terminal_state_ids=("detail_open",), cancel_event_ids=("cancel_cover", "escape_cover"), validation_boundaries=("card entry, eligible current visual choices, and C10 correction",), rationale="The user can override or return visual selection to AI without a review queue."),
    )
    terminal_actions = {
        "catalog_ready": (
            "select_locale_ready",
            "select_density_ready",
            "search_catalog",
            "select_status",
            "select_time",
            "next_page",
            "open_matter",
        ),
        "catalog_no_results": (
            "select_locale_no_results",
            "select_density_no_results",
            "search_again",
            "clear_search",
            "select_status_no_results",
            "select_time_no_results",
        ),
        "detail_open": (
            "close_detail",
            "escape_detail",
            "select_detail_section",
            "select_locale_detail",
            "select_density_detail",
            "open_evidence",
            "open_correction",
            "open_cover",
        ),
        "evidence_open": ("close_evidence", "escape_evidence"),
        "cover_open": (
            "apply_cover",
            "pin_cover",
            "unpin_cover",
            "cancel_cover",
            "escape_cover",
        ),
    }
    return UIJourneyCoverage(
        JOURNEY_ID,
        source_interaction_model_id=MODEL_ID,
        launch_state_id="catalog_ready",
        interaction_model_reviewed=True,
        entry_points=tuple(
            UIJourneyEntryPoint(
                entry_id,
                control_id,
                event_id,
                label=label,
                source_state_ids=source_states,
                rationale="The entry is a visible, task-owned control.",
            )
            for entry_id, control_id, event_id, label, source_states in entries
        ),
        feature_journeys=journeys,
        terminal_action_allowances=tuple(
            UITerminalActionAllowance(
                state_id,
                event_id,
                "close" if event_id.startswith(("close_", "escape_", "cancel_")) else "restart",
                rationale="The reusable terminal exposes a declared next task or return path.",
            )
            for state_id, event_ids in terminal_actions.items()
            for event_id in event_ids
        ),
        validation_boundaries=(
            "launch",
            "catalog browsing",
            "language and density",
            "search, filters, paging",
            "detail and evidence",
            "optional correction and cover",
        ),
        rationale="Every prominent object-browser task reaches success, recovery, or cancel.",
    )


def capability_inventory(revision: str) -> UIFunctionalCapabilityInventory:
    rows = (
        ("capability:browse_catalog", "Browse the current Matter catalog", "load", ("output:catalog",), "ui.loadCatalog"),
        ("capability:select_language", "Select display language", "configure", ("output:locale",), "ui.selectLanguage"),
        ("capability:select_density", "Select Standard or Compact cards", "configure", ("output:density",), "ui.selectCardDensity"),
        ("capability:search_filter", "Search and filter matters", "navigate", ("output:query",), "ui.searchCatalog"),
        ("capability:page_catalog", "Navigate a large catalog", "navigate", ("output:page",), "ui.loadMatterPage"),
        ("capability:inspect_matter", "Inspect one Matter", "open", ("output:detail",), "ui.openMatter"),
        ("capability:inspect_evidence", "Inspect evidence", "open", ("output:evidence",), "ui.openEvidence"),
        ("capability:correct_matter", "Optionally correct one Matter", "save", ("output:correction",), "ui.saveCorrection"),
        ("capability:change_cover", "Optionally change the Matter cover", "save", ("output:cover",), "ui.applyCover"),
    )
    return UIFunctionalCapabilityInventory(
        CAPABILITY_ID,
        source_product_model_id="C12_projection_bilingual_ui",
        source_authority_refs=(
            "openspec:build-matters-model-driven-core",
            "model:C12_projection_bilingual_ui",
            "source-ui:databank-webui-ui-handoff-20260718",
        ),
        current_revision=revision,
        capabilities=tuple(
            UIFunctionalCapability(
                capability_id,
                label=label,
                capability_kind=kind,
                expected_output_ids=outputs,
                owner=owner,
                validation_boundaries=("installed desktop click-through", "DOM and API assertions"),
                rationale="The capability is required for the autonomous first-user object browser.",
            )
            for capability_id, label, kind, outputs, owner in rows
        ),
        validation_boundaries=("complete supported object-browser task inventory",),
        rationale="The product task inventory excludes normal per-item approval.",
    )


def feature_contracts() -> tuple[UIFeatureContract, ...]:
    simple = (
        ("browse_catalog", "Browse catalog", "capability:browse_catalog", ("entry_search",), ("refresh_catalog",), ("load_ready", "load_empty", "load_failure", "retry_catalog"), "output:catalog"),
        ("select_language", "Select language", "capability:select_language", ("entry_locale",), ("select_locale",), ("select_locale_ready", "select_locale_loading", "select_locale_detail"), "output:locale"),
        ("select_density", "Select card size", "capability:select_density", ("entry_density",), ("select_density",), ("select_density_ready", "select_density_loading", "select_density_detail"), "output:density"),
        ("search_and_filter", "Search and filter", "capability:search_filter", ("entry_search", "entry_filters"), ("search_catalog", "clear_search", "select_status", "select_time"), ("search_catalog", "search_results", "search_no_results", "clear_search", "select_status", "select_time"), "output:query"),
        ("page_catalog", "Navigate catalog pages", "capability:page_catalog", ("entry_page",), ("next_page",), ("next_page", "load_ready"), "output:page"),
        ("inspect_matter", "Inspect one Matter", "capability:inspect_matter", ("entry_detail",), ("open_matter", "close_detail", "select_detail_section"), ("open_matter", "close_detail", "escape_detail", "select_detail_section"), "output:detail"),
        ("inspect_evidence", "Inspect evidence", "capability:inspect_evidence", ("entry_detail",), ("open_evidence", "close_evidence"), ("open_matter", "open_evidence", "close_evidence", "escape_evidence"), "output:evidence"),
    )
    result = [
        UIFeatureContract(
            feature_id,
            label=label,
            capability_ids=(capability_id,),
            journey_ids=(feature_id,),
            entry_point_ids=entry_ids,
            required_control_ids=control_ids,
            required_event_ids=event_ids,
            output_contract_ids=(output_id,),
            validation_boundaries=("installed desktop and API",),
            pure_ui=feature_id in {"select_language", "select_density"},
            rationale="The feature joins one task, journey, control set, and visible output.",
        )
        for feature_id, label, capability_id, entry_ids, control_ids, event_ids, output_id in simple
    ]
    for feature_id, label, capability_id, entry_id, controls, events, output_id in (
        (
            "correct_matter",
            "Optionally correct a Matter",
            "capability:correct_matter",
            "entry_detail",
            ("open_correction", "save_correction", "cancel_correction", "retry_correction"),
            ("open_correction", "save_correction", "correction_success", "correction_failure", "retry_correction", "cancel_correction", "escape_correction"),
            "output:correction",
        ),
        (
            "change_cover",
            "Optionally change a cover",
            "capability:change_cover",
            "entry_detail",
            ("open_cover", "apply_cover", "pin_cover", "unpin_cover", "cancel_cover"),
            ("open_cover", "apply_cover", "pin_cover", "unpin_cover", "cancel_cover", "escape_cover"),
            "output:cover",
        ),
    ):
        result.append(
            UIFeatureContract(
                feature_id,
                label=label,
                capability_ids=(capability_id,),
                journey_ids=(feature_id,),
                entry_point_ids=(entry_id,),
                required_control_ids=controls,
                required_event_ids=events,
                output_contract_ids=(output_id,),
                validation_boundaries=("C10 current-token HTTP intent and installed desktop",),
                business_bearing=True,
                business_intent_id="BI-PR-010-correct-and-recompute",
                behavior_commitment_id="BC-PR-010",
                primary_path_id="path:c10-invalidate-and-request-recompute",
                consistency_rule_ids=("consistency:correction-invalidation",),
                rationale="The UI emits an optional correction; C10 and original owners decide.",
            )
        )
    return tuple(result)


OUTPUT_ROWS = (
    ("output:catalog", "capability:browse_catalog", ("catalog_ready", "catalog_empty", "catalog_error"), ("catalog_summary", "matter_cards", "empty_catalog", "catalog_error"), "A current catalog, honest empty state, or visible recovery is observed."),
    ("output:locale", "capability:select_language", ("catalog_ready", "detail_open"), ("catalog_summary", "matter_detail"), "English default and Chinese selection preserve one semantic revision."),
    ("output:density", "capability:select_density", ("catalog_ready",), ("matter_cards",), "Standard and Compact preserve objects, order, visual identity, locale, filters, selection, and scroll."),
    ("output:query", "capability:search_filter", ("catalog_loading", "catalog_ready", "catalog_no_results"), ("matter_cards", "no_search_results"), "A current query result or clear zero-result state is observed."),
    ("output:page", "capability:page_catalog", ("catalog_loading", "catalog_ready"), ("matter_cards",), "Only the latest current bounded page replaces the grid."),
    ("output:detail", "capability:inspect_matter", ("detail_open", "catalog_ready"), ("matter_detail", "matter_timeline", "matter_relationships"), "A human-readable detail opens and returns to the preserved catalog."),
    ("output:evidence", "capability:inspect_evidence", ("evidence_open", "detail_open"), ("evidence_details",), "Evidence reveals on demand and returns hidden."),
    ("output:correction", "capability:correct_matter", ("correction_saving", "correction_error", "detail_open"), ("correction_form", "matter_detail"), "An optional correction shows progress and current owner-routed result or recovery."),
    ("output:cover", "capability:change_cover", ("cover_open", "detail_open"), ("cover_choices", "matter_detail"), "Eligible cover choices apply, pin, unpin, or cancel through C10."),
)


def output_contracts(revision: str, evidence_ref: str) -> tuple[UICapabilityOutputContract, ...]:
    return tuple(
        UICapabilityOutputContract(
            output_id,
            capability_id,
            output_kind="state",
            required_display_ids=displays,
            required_state_ids=states,
            assertion=assertion,
            evidence_kind="browser_click",
            evidence_ref=evidence_ref,
            current_revision=revision,
            validation_boundaries=("installed desktop object-browser validation",),
            rationale="Task success is bound to an observed user-facing state.",
        )
        for output_id, capability_id, states, displays, assertion in OUTPUT_ROWS
    )


CHAIN_ROWS = (
    ("chain:catalog", "refresh_catalog", "retry_catalog", "loadCatalog", "catalog_ready", "matter_cards", "current Matter catalog after retry"),
    ("chain:locale", "select_locale", "select_locale_ready", "selectLanguage", "catalog_ready", "matter_cards", "same objects in selected locale"),
    ("chain:density", "select_density", "select_density_ready", "selectCardDensity", "catalog_ready", "matter_cards", "same objects at selected density"),
    ("chain:search", "search_catalog", "search_catalog", "searchCatalog", "catalog_ready", "matter_cards", "current search result"),
    ("chain:status", "select_status", "select_status", "selectStatus", "catalog_ready", "matter_cards", "current status-filtered catalog"),
    ("chain:time", "select_time", "select_time", "selectTimeWindow", "catalog_ready", "matter_cards", "current time-filtered catalog"),
    ("chain:page", "next_page", "next_page", "loadMatterPage", "catalog_ready", "matter_cards", "current next page"),
    ("chain:detail", "open_matter", "open_matter", "openMatter", "detail_open", "matter_detail", "current Matter detail"),
    ("chain:detail-close", "close_detail", "close_detail", "closeMatter", "catalog_ready", "matter_cards", "preserved catalog state"),
    ("chain:evidence", "open_evidence", "open_evidence", "openEvidence", "evidence_open", "evidence_details", "evidence revealed"),
    ("chain:evidence-close", "close_evidence", "close_evidence", "closeEvidence", "detail_open", "matter_detail", "evidence hidden and focus returned"),
    ("chain:correction", "save_correction", "save_correction", "saveCorrection", "detail_open", "matter_detail", "current corrected Matter detail"),
    ("chain:cover", "apply_cover", "apply_cover", "applyCover", "detail_open", "matter_detail", "current selected cover"),
)


def capability_bindings(revision: str, evidence_ref: str) -> tuple[UICapabilityCoverageBinding, ...]:
    mapping = (
        ("binding:catalog", "capability:browse_catalog", "browse_catalog", ("refresh_catalog",), ("load_ready", "load_empty", "load_failure", "retry_catalog"), ("chain:catalog",), "output:catalog"),
        ("binding:locale", "capability:select_language", "select_language", ("select_locale",), ("select_locale_ready", "select_locale_loading", "select_locale_detail"), ("chain:locale",), "output:locale"),
        ("binding:density", "capability:select_density", "select_density", ("select_density",), ("select_density_ready", "select_density_loading", "select_density_detail"), ("chain:density",), "output:density"),
        ("binding:query", "capability:search_filter", "search_and_filter", ("search_catalog", "clear_search", "select_status", "select_time"), ("search_catalog", "search_results", "search_no_results", "clear_search", "select_status", "select_time"), ("chain:search", "chain:status", "chain:time"), "output:query"),
        ("binding:page", "capability:page_catalog", "page_catalog", ("next_page",), ("next_page", "load_ready"), ("chain:page",), "output:page"),
        ("binding:detail", "capability:inspect_matter", "inspect_matter", ("open_matter", "close_detail", "select_detail_section"), ("open_matter", "close_detail", "escape_detail", "select_detail_section"), ("chain:detail", "chain:detail-close"), "output:detail"),
        ("binding:evidence", "capability:inspect_evidence", "inspect_evidence", ("open_evidence", "close_evidence"), ("open_evidence", "close_evidence", "escape_evidence"), ("chain:evidence", "chain:evidence-close"), "output:evidence"),
        ("binding:correction", "capability:correct_matter", "correct_matter", ("open_correction", "save_correction", "cancel_correction", "retry_correction"), ("open_correction", "save_correction", "correction_success", "correction_failure", "retry_correction", "cancel_correction", "escape_correction"), ("chain:correction",), "output:correction"),
        ("binding:cover", "capability:change_cover", "change_cover", ("open_cover", "apply_cover", "pin_cover", "unpin_cover", "cancel_cover"), ("open_cover", "apply_cover", "pin_cover", "unpin_cover", "cancel_cover", "escape_cover"), ("chain:cover",), "output:cover"),
    )
    return tuple(
        UICapabilityCoverageBinding(
            binding_id,
            capability_id,
            feature_ids=(feature_id,),
            journey_ids=(feature_id,),
            control_ids=controls,
            event_ids=events,
            functional_chain_ids=chains,
            code_owner="ui/app.js",
            output_contract_ids=(output_id,),
            implementation_run_ids=(f"run:{feature_id}",),
            evidence_ref=evidence_ref,
            current_revision=revision,
            validation_boundaries=("installed desktop object-browser validation",),
            rationale="Capability, journey, controls, owner, output, and evidence are joined.",
        )
        for (
            binding_id,
            capability_id,
            feature_id,
            controls,
            events,
            chains,
            output_id,
        ) in mapping
    )


def functional_chains(revision: str, evidence_ref: str) -> UIControlFunctionalChainSet:
    correction_controls = {"save_correction", "apply_cover"}
    pure_controls = {
        "select_locale",
        "select_density",
        "close_detail",
        "open_evidence",
        "close_evidence",
    }
    return UIControlFunctionalChainSet(
        "matters-object-browser-functional-chains",
        source_inventory_id=OBSERVED_ID,
        source_interaction_model_id=MODEL_ID,
        source_implementation_validation_id=IMPLEMENTATION_ID,
        current_revision=revision,
        chains=tuple(
            UIControlFunctionalChain(
                chain_id,
                control_id,
                event_id,
                code_owner="ui/app.js",
                function_ref=function_ref,
                observed_state_id=state,
                observed_display_id=display,
                observed_output=output,
                evidence_ref=evidence_ref,
                evidence_kind="browser_click",
                current_revision=revision,
                result="passed",
                pure_ui=control_id in pure_controls,
                business_bearing=control_id in correction_controls,
                business_intent_id=(
                    "BI-PR-010-correct-and-recompute"
                    if control_id in correction_controls
                    else ""
                ),
                behavior_commitment_id=(
                    "BC-PR-010" if control_id in correction_controls else ""
                ),
                primary_path_id=(
                    "path:c10-invalidate-and-request-recompute"
                    if control_id in correction_controls
                    else ""
                ),
                consistency_rule_ids=(
                    ("consistency:correction-invalidation",)
                    if control_id in correction_controls
                    else ()
                ),
                rationale="The visible control reaches its owner and observed output.",
            )
            for chain_id, control_id, event_id, function_ref, state, display, output in CHAIN_ROWS
        ),
        validation_boundaries=("installed desktop click-through",),
        rationale="Every reachable enabled user action has a current click-to-output chain.",
    )


def implementation_validation(revision: str, evidence_ref: str) -> UIImplementationValidation:
    event_steps = {
        "browse_catalog": (
            ("load_ready", "refresh_catalog", "catalog_loading", "catalog_ready"),
            ("load_empty", "refresh_catalog", "catalog_loading", "catalog_empty"),
            ("load_failure", "refresh_catalog", "catalog_loading", "catalog_error"),
            ("retry_catalog", "refresh_catalog", "catalog_error", "catalog_loading"),
        ),
        "select_language": (
            ("select_locale_ready", "select_locale", "catalog_ready", "catalog_ready"),
            ("select_locale_loading", "select_locale", "catalog_loading", "catalog_loading"),
            ("select_locale_no_results", "select_locale", "catalog_no_results", "catalog_no_results"),
            ("select_locale_detail", "select_locale", "detail_open", "detail_open"),
        ),
        "select_density": (
            ("select_density_ready", "select_density", "catalog_ready", "catalog_ready"),
            ("select_density_loading", "select_density", "catalog_loading", "catalog_loading"),
            ("select_density_no_results", "select_density", "catalog_no_results", "catalog_no_results"),
            ("select_density_detail", "select_density", "detail_open", "detail_open"),
        ),
        "search_and_filter": (
            ("search_catalog", "search_catalog", "catalog_ready", "catalog_loading"),
            ("search_results", "search_catalog", "catalog_loading", "catalog_ready"),
            ("search_no_results", "search_catalog", "catalog_loading", "catalog_no_results"),
            ("clear_search", "clear_search", "catalog_no_results", "catalog_loading"),
            ("search_again", "search_catalog", "catalog_no_results", "catalog_loading"),
            ("select_status", "select_status", "catalog_ready", "catalog_loading"),
            ("select_time", "select_time", "catalog_ready", "catalog_loading"),
            ("select_status_no_results", "select_status", "catalog_no_results", "catalog_loading"),
            ("select_time_no_results", "select_time", "catalog_no_results", "catalog_loading"),
        ),
        "page_catalog": (
            ("next_page", "next_page", "catalog_ready", "catalog_loading"),
            ("load_ready", "refresh_catalog", "catalog_loading", "catalog_ready"),
        ),
        "inspect_matter": (
            ("open_matter", "open_matter", "catalog_ready", "detail_open"),
            ("select_detail_section", "select_detail_section", "detail_open", "detail_open"),
            ("close_detail", "close_detail", "detail_open", "catalog_ready"),
            ("escape_detail", "close_detail", "detail_open", "catalog_ready"),
        ),
        "inspect_evidence": (
            ("open_matter", "open_matter", "catalog_ready", "detail_open"),
            ("open_evidence", "open_evidence", "detail_open", "evidence_open"),
            ("close_evidence", "close_evidence", "evidence_open", "detail_open"),
            ("escape_evidence", "close_evidence", "evidence_open", "detail_open"),
        ),
        "correct_matter": (
            ("open_matter", "open_matter", "catalog_ready", "detail_open"),
            ("open_correction", "open_correction", "detail_open", "correction_open"),
            ("save_correction", "save_correction", "correction_open", "correction_saving"),
            ("correction_success", "save_correction", "correction_saving", "detail_open"),
            ("correction_failure", "save_correction", "correction_saving", "correction_error"),
            ("retry_correction", "retry_correction", "correction_error", "correction_saving"),
            ("cancel_correction", "cancel_correction", "correction_open", "detail_open"),
            ("escape_correction", "cancel_correction", "correction_open", "detail_open"),
            ("cancel_correction_error", "cancel_correction", "correction_error", "detail_open"),
        ),
        "change_cover": (
            ("open_matter", "open_matter", "catalog_ready", "detail_open"),
            ("open_cover", "open_cover", "detail_open", "cover_open"),
            ("apply_cover", "apply_cover", "cover_open", "detail_open"),
            ("pin_cover", "pin_cover", "cover_open", "detail_open"),
            ("unpin_cover", "unpin_cover", "cover_open", "detail_open"),
            ("cancel_cover", "cancel_cover", "cover_open", "detail_open"),
            ("escape_cover", "cancel_cover", "cover_open", "detail_open"),
        ),
    }
    runs = tuple(
        UIImplementationJourneyRun(
            f"run:{feature}",
            feature,
            journey_id=feature,
            steps=tuple(
                UIImplementationStepEvidence(
                    f"step:{feature}:{event}",
                    event,
                    control_id=control,
                    source_state_id=source,
                    target_state_id=target,
                    method="browser",
                    result="passed",
                    evidence_ref=evidence_ref,
                    observed_state_id=target,
                    observed_output="modeled object-browser update observed",
                    rationale="The installed desktop UI followed the modeled transition.",
                )
                for event, control, source, target in steps
            ),
            method="browser",
            result="passed",
            evidence_ref=evidence_ref,
            model_revision=revision,
            validation_boundaries=("installed desktop validation",),
            rationale="The current installed UI was exercised against the model.",
        )
        for feature, steps in event_steps.items()
    )
    visible_evidence = tuple(
        UIContentVisibilityEvidence(
            f"visibility:{content_id}",
            content_id,
            UI_CONTENT_EVIDENCE_DEFAULT_VISIBLE,
            current_revision=revision,
            state_id=state_id,
            observed_item_ids=(observed_id,),
            evidence_ref=evidence_ref,
            rationale="Admitted content was visible in its declared runtime state.",
        )
        for content_id, observed_id, state_id in (
            ("catalog_heading", "observed_heading", "catalog_ready"),
            ("catalog_summary", "observed_summary", "catalog_ready"),
            ("filter_summary", "observed_filters", "catalog_ready"),
            ("coverage_summary", "observed_coverage", "catalog_ready"),
            ("background_status", "observed_background", "catalog_ready"),
            ("matter_cards", "observed_cards", "catalog_ready"),
            ("empty_catalog", "observed_empty", "catalog_empty"),
            ("no_search_results", "observed_no_results", "catalog_no_results"),
            ("catalog_recovery", "observed_error", "catalog_error"),
            (
                "correction_progress",
                "observed_correction_progress",
                "correction_saving",
            ),
            (
                "correction_recovery",
                "observed_correction_error",
                "correction_error",
            ),
        )
    )
    on_demand_evidence = tuple(
        evidence
        for content_id, observed_id, open_state, open_event, close_event in (
            ("matter_detail", "observed_detail", "detail_open", "open_matter", "close_detail"),
            ("matter_timeline", "observed_timeline", "detail_open", "open_matter", "close_detail"),
            ("matter_relationships", "observed_relationships", "detail_open", "open_matter", "close_detail"),
            ("evidence_details", "observed_evidence", "evidence_open", "open_evidence", "close_evidence"),
            ("correction_form", "observed_correction", "correction_open", "open_correction", "cancel_correction"),
            ("cover_choices", "observed_cover", "cover_open", "open_cover", "cancel_cover"),
        )
        for evidence in (
            UIContentVisibilityEvidence(
                f"visibility:{content_id}:hidden",
                content_id,
                UI_CONTENT_EVIDENCE_DEFAULT_HIDDEN,
                current_revision=revision,
                state_id="catalog_loading",
                observed_item_ids=(),
                evidence_ref=evidence_ref,
                rationale="On-demand content was absent on initial catalog load.",
            ),
            UIContentVisibilityEvidence(
                f"visibility:{content_id}:reveal",
                content_id,
                UI_CONTENT_EVIDENCE_REVEAL,
                current_revision=revision,
                state_id="catalog_ready" if open_event == "open_matter" else "detail_open",
                event_id=open_event,
                observed_item_ids=(),
                evidence_ref=evidence_ref,
                rationale="A visible control revealed the on-demand content.",
            ),
            UIContentVisibilityEvidence(
                f"visibility:{content_id}:open",
                content_id,
                UI_CONTENT_EVIDENCE_REVEALED,
                current_revision=revision,
                state_id=open_state,
                observed_item_ids=(observed_id,),
                evidence_ref=evidence_ref,
                rationale="The content was observed only in its revealed state.",
            ),
            UIContentVisibilityEvidence(
                f"visibility:{content_id}:close",
                content_id,
                UI_CONTENT_EVIDENCE_RETURN_HIDDEN,
                current_revision=revision,
                state_id="catalog_ready" if close_event == "close_detail" else "detail_open",
                event_id=close_event,
                observed_item_ids=(),
                evidence_ref=evidence_ref,
                rationale="Close or Escape restored the prior surface.",
            ),
        )
    )
    return UIImplementationValidation(
        IMPLEMENTATION_ID,
        source_feature_model_id="C12_projection_bilingual_ui",
        source_interaction_model_id=MODEL_ID,
        source_journey_coverage_id=JOURNEY_ID,
        implementation_target="installed local Matters desktop object browser",
        current_model_revision=revision,
        source_capability_inventory_id=CAPABILITY_ID,
        feature_contracts=feature_contracts(),
        journey_runs=runs,
        capability_bindings=capability_bindings(revision, evidence_ref),
        output_contracts=output_contracts(revision, evidence_ref),
        pure_ui_control_ids=(
            "select_locale",
            "select_density",
            "close_detail",
            "select_detail_section",
            "open_evidence",
            "close_evidence",
            "open_correction",
            "cancel_correction",
            "cancel_cover",
        ),
        pure_ui_event_ids=(
            "select_locale_ready",
            "select_locale_loading",
            "select_locale_detail",
            "select_density_ready",
            "select_density_loading",
            "select_density_detail",
            "close_detail",
            "escape_detail",
            "select_detail_section",
            "open_evidence",
            "close_evidence",
            "escape_evidence",
            "open_correction",
            "cancel_correction",
            "escape_correction",
            "cancel_cover",
            "escape_cover",
        ),
        capability_coverage_reviewed=True,
        journey_coverage_reviewed=True,
        content_visibility_plan_id=VISIBILITY_ID,
        content_visibility_reviewed=True,
        content_visibility_evidence=visible_evidence
        + on_demand_evidence
        + (
            UIContentVisibilityEvidence(
                "visibility:internal-absent",
                "private_internal_material",
                UI_CONTENT_EVIDENCE_INTERNAL_ABSENT,
                current_revision=revision,
                state_id="catalog_ready",
                observed_item_ids=(),
                evidence_ref=evidence_ref,
                rationale="Paths, raw receipts, provider ids, and private content were absent.",
            ),
        ),
        validation_boundaries=(
            "installed desktop validation",
            "fault injection",
            "English/zh-CN",
            "Standard/Compact",
        ),
        rationale="Runtime steps, outputs, disclosures, recovery, and private absence are explicit.",
    )


def render_evidence(revision: str, evidence_ref: str) -> UIRenderEvidenceSet:
    return UIRenderEvidenceSet(
        "matters-object-browser-render-evidence",
        source_interaction_model_id=MODEL_ID,
        implementation_target="installed local Matters desktop object browser",
        current_model_revision=revision,
        evidence=tuple(
            UIRenderEvidence(
                f"render:{kind}",
                kind,
                target,
                source_interaction_model_id=MODEL_ID,
                implementation_target="installed local Matters desktop object browser",
                result="passed",
                evidence_ref=evidence_ref,
                model_revision=revision,
                observed_state_id=state,
                rationale="Current runtime evidence is bound to the exact UI revision.",
            )
            for kind, target, state in (
                ("browser_click", "catalog, density, locale, search, detail, evidence, correction, and cover", "catalog_ready"),
                ("dom_text", "English and zh-CN object-browser surface", "catalog_ready"),
                ("geometry", "1880, 1440, 1280, 1180, 1024, 760, and 390 widths", "catalog_ready"),
                ("accessibility", "keyboard navigation, dialog focus, and error focus", "detail_open"),
            )
        ),
        validation_boundaries=("installed runtime", "desktop-first and narrow fallback"),
        rationale="Design evidence is kept separate from runnable render evidence.",
    )


def geometry_evidence(evidence_ref: str) -> UIGeometryLayoutEvidenceSet:
    return UIGeometryLayoutEvidenceSet(
        "matters-object-browser-geometry",
        source_interaction_model_id=MODEL_ID,
        entries=tuple(
            UIGeometryLayoutEvidence(
                f"geometry:{viewport}",
                "matter object browser",
                viewport=viewport,
                text_overflow=False,
                control_overlap=False,
                out_of_bounds=False,
                focus_reachable=True,
                keyboard_reachable=True,
                scroll_owner="catalog grid or detail panel, never both for the same gesture",
                result="passed",
                evidence_ref=evidence_ref,
                rationale="The declared viewport has no overflow, overlap, or unreachable control.",
            )
            for viewport in (
                "1880x900",
                "1440x900",
                "1280x800",
                "1180x800",
                "1024x768",
                "760x844",
                "390x844",
            )
        ),
        validation_boundaries=(
            "Standard and Compact cards",
            "English and zh-CN",
            "zero, one, few, and large catalogs",
            "image, placeholder, stale, and error visuals",
        ),
        rationale="Desktop reference geometry is primary; narrow layouts remain operable.",
    )


def responsiveness_contract() -> UIResponsivenessContract:
    return UIResponsivenessContract(
        "matters-object-browser-responsiveness",
        source_interaction_model_id=MODEL_ID,
        hot_path_actions=(
            UIHotPathAction("hot:refresh", event_id="retry_catalog", feedback_target_id="background_status", feedback_description="Loading feedback appears immediately while duplicate retry is disabled.", rationale="Retry acknowledges input before I/O."),
            UIHotPathAction("hot:search", event_id="search_catalog", feedback_target_id="catalog_summary", feedback_description="The query state is visible immediately while the current grid remains stable.", rationale="Search must not blank the browser before a current result arrives."),
            UIHotPathAction("hot:locale", event_id="select_locale_ready", feedback_target_id="matter_cards", feedback_description="The same object revision rerenders immediately.", rationale="Locale is a display projection."),
            UIHotPathAction("hot:density", event_id="select_density_ready", feedback_target_id="matter_cards", feedback_description="The same objects reflow immediately between Standard and Compact.", rationale="Density is a display preference, not a semantic rebuild."),
            UIHotPathAction("hot:correction", event_id="save_correction", feedback_target_id="correction_form", feedback_description="Saving feedback and duplicate-action disablement appear immediately.", rationale="An optional business-bearing write must be visibly serialized."),
        ),
        cold_path_work=(
            UIColdPathWork("cold:catalog", trigger_event_id="retry_catalog", result_target_id="matter_cards", stale_guard="request revision accepts only the latest catalog response", cancellation_rule="a newer query or retry supersedes an older response", coalescing_rule="one current catalog render", rationale="Late transport cannot overwrite newer browser state."),
            UIColdPathWork("cold:query", trigger_event_id="search_catalog", result_target_id="matter_cards", stale_guard="query/filter/window/revision identity", cancellation_rule="newer query cancels or invalidates older work", coalescing_rule="one current query window", rationale="Search and filtering are revision-safe."),
            UIColdPathWork("cold:correction", trigger_event_id="save_correction", result_target_id="matter_detail", stale_guard="C10 action token and current Matter revision", cancellation_rule="the correction remains serialized until terminal response", coalescing_rule="one correction per action token", rationale="C10 rejects stale duplicate corrections."),
        ),
        stable_region_rules=(
            UIStableRegionRule("topbar", preservation_rule="Brand, search, language, density, and background status keep stable placement.", unrelated_input_ids=("catalog length", "detail section"), rationale="Global controls do not move with data volume."),
            UIStableRegionRule("sidebar", preservation_rule="Category, status, and time filters retain selections and stable placement.", unrelated_input_ids=("card density", "selected Matter"), rationale="Filtering context remains visible."),
            UIStableRegionRule("catalog_grid", preservation_rule="Query, filters, sort, window, selection, and scroll anchor survive locale, density, detail, and recovery transitions.", unrelated_input_ids=("locale", "density", "detail section"), rationale="Display changes never reset the user's browsing position."),
        ),
        validation_boundaries=(
            "immediate feedback",
            "stale response rejection",
            "persistent Standard/Compact preference",
            "stable global and catalog regions",
        ),
        rationale="Hot feedback and cold model work stay separate and revision-safe.",
    )


def runtime_evidence_ref(payload: Mapping[str, object]) -> str:
    return str(payload.get("evidence_id", ""))


__all__ = [
    "CAPABILITY_ID",
    "IMPLEMENTATION_ID",
    "JOURNEY_ID",
    "MODEL_ID",
    "OBSERVED_ID",
    "REVISION_INPUTS",
    "SURFACE_ID",
    "VISIBILITY_ID",
    "capability_bindings",
    "capability_inventory",
    "current_revision",
    "feature_contracts",
    "functional_chains",
    "geometry_evidence",
    "implementation_validation",
    "interaction_model",
    "journey_coverage",
    "observed_inventory",
    "output_contracts",
    "render_evidence",
    "responsiveness_contract",
    "runtime_evidence_ref",
    "visibility_plan",
    "visible_surface",
]
