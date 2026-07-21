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
DETAIL_SECTION_IDS = (
    "overview",
    "sub_matters",
    "timeline",
    "people",
    "related_matters",
    "files_information",
    "images",
    "ai_supplemental_information",
)

REVISION_INPUTS = (
    Path("ui/index.html"),
    Path("ui/styles.css"),
    Path("ui/app.js"),
    Path("src/matters/application/orchestrator.py"),
    Path("src/matters/api/http/app.py"),
    Path("src/matters/api/http/static.py"),
    Path("src/matters/application/activity.py"),
    Path("src/matters/domain/activity.py"),
    Path("src/matters/presentation/browser.py"),
    Path("src/matters/presentation/projections.py"),
    Path("src/matters/presentation/localization.py"),
    Path("src/matters/presentation/visuals.py"),
    Path("src/matters/desktop.py"),
    Path("flowguard_models/models/c12_projection_bilingual_ui.py"),
    Path("flowguard_models/models/c06_matter_admission.py"),
    Path("flowguard_models/models/c07_lifecycle_board_state.py"),
    Path("flowguard_models/models/c08_open_loop_blocking.py"),
    Path("flowguard_models/models/c09_outcomes_reopen.py"),
    Path("flowguard_models/models/c10_correction_revocation.py"),
    Path("flowguard_design/ui_flow_structure.py"),
    Path("flowguard_design/run_ui_flow_structure.py"),
    Path("flowguard_design/ui_runtime_required_checks.json"),
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
            content = resolved.read_bytes()
            digest.update(content.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
        else:
            digest.update(b"<missing>")
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def visibility_plan(revision: str) -> UIContentVisibilityPlan:
    visible = (
        ("catalog_heading", "task:browse_matters"),
        ("catalog_summary", "task:browse_matters"),
        ("catalog_unknown_count", "recovery:catalog_error"),
        ("catalog_stale_warning", "recovery:catalog_stale_error"),
        ("filter_summary", "task:filter_matters"),
        ("coverage_summary", "state:catalog_ready"),
        ("background_status", "state:catalog_ready"),
        ("matter_cards", "task:browse_matters"),
        ("generated_hero", "task:browse_matters"),
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
            "matter_people",
            ("task:inspect_related_people",),
            ("open_matter",),
            ("close_detail", "escape_detail"),
        ),
        (
            "matter_hierarchy_graph",
            ("task:navigate_matter_hierarchy",),
            ("open_matter",),
            ("close_detail", "escape_detail"),
        ),
        (
            "node_quick_view",
            ("task:inspect_submatter",),
            ("open_submatter_node",),
            ("close_node_quick_view", "escape_node_quick_view"),
        ),
        (
            "files_information",
            ("task:inspect_files_information",),
            ("open_matter",),
            ("close_detail", "escape_detail"),
        ),
        (
            "image_gallery",
            ("task:inspect_images",),
            ("open_matter",),
            ("close_detail", "escape_detail"),
        ),
        (
            "ai_supplemental_information",
            ("task:inspect_ai_supplemental_information",),
            ("open_matter",),
            ("close_detail", "escape_detail"),
        ),
        (
            "evidence_details",
            ("task:inspect_evidence",),
            ("open_evidence",),
            ("close_evidence", "escape_evidence"),
        ),
    )
    return UIContentVisibilityPlan(
        VISIBILITY_ID,
        source_interaction_model_id=MODEL_ID,
        current_revision=revision,
        candidate_content_ids=(
            tuple(item[0] for item in visible)
            + tuple(item[0] for item in on_demand)
            + ("private_internal_material",)
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
            "exactly eight detail sections plus a Matter-only hierarchy graph, one reusable node quick view, and on-demand evidence disclosure",
            "the ordinary first-version object browser exposes no correction or other canonical-write control",
            "generated hero is presentation-only and never appears in the Images evidence gallery",
            "Images admits only real photos or meaningful visual images; email, TXT, document, form, and text-page screenshots remain Files & information",
            "Compact omits event, people, and source metrics so its same Hero fills the remaining equal-size card body",
            "future AI predictions appear only in AI supplemental information or the World Model and never as occurred timeline state",
            "Start time filters independently while latest meaningful clue orders every filtered catalog",
            "transport failure preserves prior content or shows an unknown count, never a false zero",
        ),
        rationale="Every state-bearing value is classified before it can render.",
    )


def _controls() -> tuple[UIControl, ...]:
    rows = (
        ("refresh_catalog", "Read again", "global", "loadCatalog", True),
        ("dismiss_refresh_error", "Keep browsing", "contextual", "dismissRefreshError", False),
        ("select_locale", "Language", "global", "selectLanguage", True),
        ("select_density", "Card size", "global", "selectCardDensity", True),
        ("search_catalog", "Search matters", "global", "searchCatalog", True),
        ("clear_search", "Clear search", "contextual", "clearSearch", False),
        ("select_status", "Status", "contextual", "selectStatus", True),
        ("select_time", "Start time", "contextual", "selectTimeWindow", True),
        ("next_page", "More matters", "contextual", "loadMatterPage", False),
        ("open_matter", "Open matter", "local", "openMatter", False),
        ("close_detail", "Close matter", "contextual", "closeMatter", False),
        ("select_detail_section", "Matter section", "contextual", "selectDetailSection", False),
        ("open_submatter_node", "Open sub-matter", "local", "openSubmatterNode", False),
        ("close_node_quick_view", "Close sub-matter", "contextual", "closeNodeQuickView", False),
        ("open_evidence", "View evidence", "local", "openEvidence", False),
        ("close_evidence", "Close evidence", "contextual", "closeEvidence", False),
        ("select_gallery_image", "Select image", "local", "selectGalleryImage", False),
        ("zoom_image_in", "Zoom in", "local", "zoomImageIn", False),
        ("zoom_image_out", "Zoom out", "local", "zoomImageOut", False),
        ("reset_image_zoom", "Reset image", "local", "resetImageZoom", False),
        ("pan_image", "Pan image", "local", "panImage", False),
        ("navigate_image_keyboard", "Previous or next image", "local", "navigateImageKeyboard", False),
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
            (
                "catalog_loading",
                "catalog_ready",
                "catalog_empty",
                "catalog_no_results",
                "catalog_error",
                "catalog_stale_error",
            ),
            "topbar",
            "catalog_heading",
        ),
        (
            "catalog_summary",
            "catalog_summary",
            "Matter catalog",
            "status",
            (
                "catalog_ready",
                "catalog_empty",
                "catalog_no_results",
                "catalog_stale_error",
                "detail_open",
            ),
            "catalog_header",
            "catalog_summary",
        ),
        (
            "catalog_unknown_count",
            "catalog_unknown_count",
            "Matter count unavailable",
            "status",
            ("catalog_error",),
            "catalog_header",
            "catalog_unknown_count",
        ),
        (
            "catalog_stale_warning",
            "catalog_stale_warning",
            "Showing the last successful catalog",
            "status",
            ("catalog_stale_error",),
            "catalog_header",
            "catalog_stale_warning",
        ),
        (
            "filter_summary",
            "filter_summary",
            "Current filters",
            "status",
            ("catalog_ready", "catalog_empty", "catalog_no_results", "catalog_stale_error"),
            "sidebar",
            "filter_summary",
        ),
        (
            "coverage_summary",
            "coverage_summary",
            "Coverage",
            "status",
            ("catalog_ready", "catalog_stale_error", "detail_open"),
            "catalog_header",
            "coverage_summary",
        ),
        (
            "background_status",
            "background_status",
            "Background work",
            "status",
            (
                "catalog_loading",
                "catalog_ready",
                "catalog_empty",
                "catalog_no_results",
                "catalog_stale_error",
                "detail_open",
            ),
            "topbar",
            "background_status",
        ),
        (
            "matter_cards",
            "matter_cards",
            "Matter cards",
            "grid",
            ("catalog_ready", "catalog_stale_error"),
            "catalog_grid",
            "matter_cards",
        ),
        (
            "generated_hero",
            "generated_hero",
            "Generated Matter image",
            "image",
            ("catalog_ready", "catalog_stale_error", "detail_open"),
            "matter_card_or_detail_header",
            "generated_hero",
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
            "matter_people",
            "matter_people",
            "People",
            "list",
            ("detail_open",),
            "detail",
            "matter_people",
        ),
        (
            "matter_relationships",
            "matter_relationships",
            "Related Matters",
            "list",
            ("detail_open",),
            "detail",
            "matter_relationships",
        ),
        (
            "matter_hierarchy_graph",
            "matter_hierarchy_graph",
            "Sub-matter hierarchy",
            "graph",
            ("detail_open",),
            "detail",
            "matter_hierarchy_graph",
        ),
        (
            "node_quick_view",
            "node_quick_view",
            "Sub-matter quick view",
            "dialog",
            ("node_quick_view_open",),
            "node_quick_view",
            "node_quick_view",
        ),
        (
            "files_information",
            "files_information",
            "Files & information",
            "table",
            ("detail_open",),
            "detail",
            "files_information",
        ),
        (
            "image_gallery",
            "image_gallery",
            "Images",
            "gallery",
            ("detail_open",),
            "detail",
            "image_gallery",
        ),
        (
            "ai_supplemental_information",
            "ai_supplemental_information",
            "AI supplemental information",
            "list",
            ("detail_open",),
            "detail",
            "ai_supplemental_information",
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
    "open_submatter_node",
    "open_evidence",
    "select_gallery_image",
    "zoom_image_in",
    "zoom_image_out",
    "reset_image_zoom",
    "pan_image",
    "navigate_image_keyboard",
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
                "matter_people",
                "matter_relationships",
                "matter_hierarchy_graph",
                "node_quick_view",
                "files_information",
                "image_gallery",
                "ai_supplemental_information",
                "generated_hero",
                "evidence_details",
            ),
            rationale="Launch and transport changes show immediate progress.",
        ),
        UIStateNode(
            "catalog_ready",
            visible_controls=CATALOG_CONTROLS + ("open_matter",),
            enabled_controls=CATALOG_CONTROLS + ("open_matter",),
            visible_displays=CATALOG_DISPLAYS + ("matter_cards", "generated_hero"),
            hidden_displays=(
                "empty_catalog",
                "no_search_results",
                "catalog_error",
                "catalog_unknown_count",
                "catalog_stale_warning",
                "matter_detail",
                "matter_timeline",
                "matter_people",
                "matter_relationships",
                "matter_hierarchy_graph",
                "node_quick_view",
                "files_information",
                "image_gallery",
                "ai_supplemental_information",
                "evidence_details",
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
                "generated_hero",
                "no_search_results",
                "catalog_error",
                "matter_detail",
                "matter_timeline",
                "matter_people",
                "matter_relationships",
                "matter_hierarchy_graph",
                "node_quick_view",
                "files_information",
                "image_gallery",
                "ai_supplemental_information",
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
                "generated_hero",
                "empty_catalog",
                "catalog_error",
                "matter_detail",
                "matter_timeline",
                "matter_people",
                "matter_relationships",
                "matter_hierarchy_graph",
                "node_quick_view",
                "files_information",
                "image_gallery",
                "ai_supplemental_information",
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
            visible_displays=("catalog_heading", "catalog_unknown_count", "catalog_error"),
            hidden_displays=(
                "matter_cards",
                "generated_hero",
                "matter_detail",
                "matter_timeline",
                "matter_people",
                "matter_relationships",
                "matter_hierarchy_graph",
                "node_quick_view",
                "files_information",
                "image_gallery",
                "ai_supplemental_information",
            ),
            failure=True,
            rationale="A first catalog read failure exposes one retry and an unknown count, never a false zero.",
        ),
        UIStateNode(
            "catalog_stale_error",
            role="failure",
            visible_controls=("refresh_catalog", "dismiss_refresh_error"),
            enabled_controls=("refresh_catalog", "dismiss_refresh_error"),
            recovery_controls=("refresh_catalog", "dismiss_refresh_error"),
            visible_displays=CATALOG_DISPLAYS
            + ("matter_cards", "generated_hero", "catalog_stale_warning"),
            hidden_displays=(
                "empty_catalog",
                "no_search_results",
                "catalog_error",
                "catalog_unknown_count",
                "matter_detail",
                "matter_timeline",
                "matter_people",
                "matter_relationships",
                "matter_hierarchy_graph",
                "node_quick_view",
                "files_information",
                "image_gallery",
                "ai_supplemental_information",
            ),
            failure=True,
            terminal=True,
            rationale="A failed refresh keeps the last successful cards readable and labels them stale.",
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
                "matter_people",
                "matter_relationships",
                "matter_hierarchy_graph",
                "files_information",
                "image_gallery",
                "ai_supplemental_information",
                "generated_hero",
            ),
            hidden_displays=(
                "evidence_details",
                "node_quick_view",
            ),
            terminal=True,
            rationale=(
                "The detail keeps global language and density choices stable and "
                "keeps the root detail open with exactly eight sections: "
                + ", ".join(DETAIL_SECTION_IDS)
                + ". Sub-matters is a Matter-only graph; selecting one Matter "
                "opens one reusable quick view. Evidence is a subordinate disclosure inside Files & "
                "information; correction remains outside the ordinary browser."
            ),
        ),
        UIStateNode(
            "node_quick_view_open",
            visible_controls=("close_node_quick_view",),
            enabled_controls=("close_node_quick_view",),
            visible_displays=("node_quick_view",),
            hidden_displays=("evidence_details",),
            terminal=True,
            rationale=(
                "One reusable overlay shows the selected Matter's human summary, "
                "current state, itemized facts/events/work/waits, and node-specific "
                "flat sources; selecting another node replaces this content and "
                "never opens a child detail shell or nested graph."
            ),
        ),
        UIStateNode(
            "evidence_open",
            visible_controls=("close_evidence",),
            enabled_controls=("close_evidence",),
            visible_displays=("evidence_details",),
            terminal=True,
            rationale="The evidence dialog owns focus and has Close and Escape return paths.",
        ),
    )

    transitions = (
        UITransition("load_ready", "refresh_catalog", "catalog_loading", "catalog_ready", function_block="LoadMatterCatalog", code_contract_id="http.get.matter_catalog", output="current_catalog", rationale="A non-empty current catalog becomes browsable."),
        UITransition("load_empty", "refresh_catalog", "catalog_loading", "catalog_empty", function_block="LoadMatterCatalog", code_contract_id="http.get.matter_catalog", output="empty_catalog", rationale="A current zero-object catalog reaches an honest empty state."),
        UITransition("load_failure", "refresh_catalog", "catalog_loading", "catalog_error", function_block="LoadMatterCatalog", code_contract_id="http.get.matter_catalog", output="catalog_error", rationale="A failed read reaches visible recovery."),
        UITransition("retry_catalog", "refresh_catalog", "catalog_error", "catalog_loading", function_block="LoadMatterCatalog", code_contract_id="http.get.matter_catalog", output="loading_feedback", rationale="Retry restarts only the catalog read."),
        UITransition("refresh_failure_with_prior", "refresh_catalog", "catalog_ready", "catalog_stale_error", function_block="LoadMatterCatalog", code_contract_id="http.get.matter_catalog", output="prior_catalog_with_stale_warning", rationale="A failed refresh preserves the last successful cards and count while labeling them stale."),
        UITransition("retry_refresh_with_prior", "refresh_catalog", "catalog_stale_error", "catalog_loading", function_block="LoadMatterCatalog", code_contract_id="http.get.matter_catalog", output="loading_feedback", rationale="Retry requests a current catalog without ever projecting a false zero."),
        UITransition("dismiss_refresh_error", "dismiss_refresh_error", "catalog_stale_error", "catalog_ready", function_block="DismissRefreshError", code_contract_id="ui.catalog.stale_error.dismiss", output="prior_catalog_warning_dismissed", pure_ui=True, rationale="Dismiss keeps the same last-successful catalog and does not claim a new revision."),
        UITransition("search_catalog", "search_catalog", "catalog_ready", "catalog_loading", function_block="SearchMatterCatalog", code_contract_id="http.get.matter_catalog", output="query_loading", rationale="Search preserves the previous window until a current result arrives."),
        UITransition("search_results", "search_catalog", "catalog_loading", "catalog_ready", function_block="SearchMatterCatalog", code_contract_id="http.get.matter_catalog", output="current_search_results", rationale="A current non-empty query result replaces the catalog window; a matching child includes its ancestor path and never increments the root count."),
        UITransition("search_no_results", "search_catalog", "catalog_loading", "catalog_no_results", function_block="SearchMatterCatalog", code_contract_id="http.get.matter_catalog", output="no_search_results", rationale="A current zero-result query has a distinct state."),
        UITransition("clear_search", "clear_search", "catalog_no_results", "catalog_loading", function_block="ClearMatterSearch", code_contract_id="http.get.matter_catalog", output="query_cleared_loading", rationale="Clearing a query restores the catalog without resetting other preferences."),
        UITransition("search_again", "search_catalog", "catalog_no_results", "catalog_loading", function_block="SearchMatterCatalog", code_contract_id="http.get.matter_catalog", output="query_loading", rationale="A revised query starts from the preserved zero-result state."),
        UITransition("select_status", "select_status", "catalog_ready", "catalog_loading", function_block="FilterMatterCatalog", code_contract_id="http.get.matter_catalog", output="filter_loading", rationale="Status filtering is a current bounded query."),
        UITransition("select_time", "select_time", "catalog_ready", "catalog_loading", function_block="FilterMatterCatalog", code_contract_id="http.get.matter_catalog", output="filter_loading", rationale="Start-time filtering is a current bounded query and never replaces latest-meaningful-clue ordering."),
        UITransition("select_status_no_results", "select_status", "catalog_no_results", "catalog_loading", function_block="FilterMatterCatalog", code_contract_id="http.get.matter_catalog", output="filter_loading", rationale="Changing status can recover a zero-result query."),
        UITransition("select_time_no_results", "select_time", "catalog_no_results", "catalog_loading", function_block="FilterMatterCatalog", code_contract_id="http.get.matter_catalog", output="filter_loading", rationale="Changing Start time can recover a zero-result query without changing the activity-order contract."),
        UITransition("next_page", "next_page", "catalog_ready", "catalog_loading", function_block="LoadMatterPage", code_contract_id="http.get.matter_catalog", output="next_page_loading", rationale="Next-page transport keeps one bounded catalog window."),
        UITransition("select_locale_ready", "select_locale", "catalog_ready", "catalog_ready", function_block="SelectLanguage", code_contract_id="locale.registry.select", output="same_revision_locale_projection", pure_ui=True, rationale="Language selection changes display text, not Matter semantics."),
        UITransition("select_density_ready", "select_density", "catalog_ready", "catalog_ready", function_block="SelectCardDensity", code_contract_id="ui.card_density.select", output="same_objects_new_density", pure_ui=True, rationale="Standard and Compact share objects, latest-meaningful-clue order, generated-hero identity, and revisions; Compact omits secondary metrics and expands the Hero."),
        UITransition("select_locale_loading", "select_locale", "catalog_loading", "catalog_loading", function_block="SelectLanguage", code_contract_id="locale.registry.select", output="localized_loading", pure_ui=True, rationale="Loading feedback follows the selected locale."),
        UITransition("select_density_loading", "select_density", "catalog_loading", "catalog_loading", function_block="SelectCardDensity", code_contract_id="ui.card_density.select", output="density_preference_saved", pure_ui=True, rationale="Density preference is independent of transport and viewport."),
        UITransition("select_locale_no_results", "select_locale", "catalog_no_results", "catalog_no_results", function_block="SelectLanguage", code_contract_id="locale.registry.select", output="localized_zero_results", pure_ui=True, rationale="The zero-result state follows the selected locale."),
        UITransition("select_density_no_results", "select_density", "catalog_no_results", "catalog_no_results", function_block="SelectCardDensity", code_contract_id="ui.card_density.select", output="density_preference_saved", pure_ui=True, rationale="Density remains independent of query results."),
        UITransition("open_matter", "open_matter", "catalog_ready", "detail_open", function_block="OpenMatterDetail", code_contract_id="http.get.matter_detail", output="current_matter_detail", rationale="A card opens the same Matter revision in a detail surface."),
        UITransition("close_detail", "close_detail", "detail_open", "catalog_ready", function_block="CloseMatterDetail", code_contract_id="ui.matter_detail.close", output="catalog_state_restored", pure_ui=True, rationale="Close restores query, filters, density, locale, selection, and scroll anchor."),
        UITransition("escape_detail", "close_detail", "detail_open", "catalog_ready", function_block="CloseMatterDetail", code_contract_id="ui.matter_detail.close", output="catalog_state_restored_focus", pure_ui=True, rationale="Escape closes detail and returns focus to the owning card."),
        UITransition("select_detail_section", "select_detail_section", "detail_open", "detail_open", function_block="SelectDetailSection", code_contract_id="ui.matter_detail.section", output="selected_detail_section", pure_ui=True, rationale="The only primary sections are Overview, Sub-matters, Timeline, People, Related Matters, Files & information, Images, and AI supplemental information."),
        UITransition(
            "open_submatter_node",
            "open_submatter_node",
            "detail_open",
            "node_quick_view_open",
            function_block="OpenSubmatterQuickView",
            code_contract_id="http.get.matter_node_quick_view",
            output="current_submatter_quick_view",
            rationale=(
                "Selecting a Matter node opens one reusable small overlay with "
                "human summary/current state, itemized facts/events/work/waits, "
                "and node-specific flat sources; it never replaces the root detail."
            ),
        ),
        UITransition(
            "close_node_quick_view",
            "close_node_quick_view",
            "node_quick_view_open",
            "detail_open",
            function_block="CloseSubmatterQuickView",
            code_contract_id="ui.matter_node_quick_view.close",
            output="root_detail_restored",
            pure_ui=True,
            rationale="Close returns focus to the selected graph node without changing the root detail.",
        ),
        UITransition(
            "escape_node_quick_view",
            "close_node_quick_view",
            "node_quick_view_open",
            "detail_open",
            function_block="CloseSubmatterQuickView",
            code_contract_id="ui.matter_node_quick_view.close",
            output="root_detail_restored_focus",
            pure_ui=True,
            rationale="Escape closes the same quick view and returns focus to its graph node.",
        ),
        UITransition("select_locale_detail", "select_locale", "detail_open", "detail_open", function_block="SelectLanguage", code_contract_id="locale.registry.select", output="same_detail_revision_locale_projection", pure_ui=True, rationale="Detail content changes locale without changing facts."),
        UITransition("select_density_detail", "select_density", "detail_open", "detail_open", function_block="SelectCardDensity", code_contract_id="ui.card_density.select", output="density_preference_saved", pure_ui=True, rationale="Density remains a persistent browser preference while detail is open."),
        UITransition("open_evidence", "open_evidence", "detail_open", "evidence_open", function_block="OpenEvidence", code_contract_id="ui.evidence.disclosure", output="evidence_dialog", pure_ui=True, rationale="Evidence is revealed only on demand from a Files & information row."),
        UITransition("close_evidence", "close_evidence", "evidence_open", "detail_open", function_block="CloseEvidence", code_contract_id="ui.evidence.disclosure", output="evidence_hidden", pure_ui=True, rationale="Close restores the detail surface."),
        UITransition("escape_evidence", "close_evidence", "evidence_open", "detail_open", function_block="CloseEvidence", code_contract_id="ui.evidence.disclosure", output="evidence_hidden_focus_return", pure_ui=True, rationale="Escape closes evidence and returns focus."),
        UITransition("select_gallery_image", "select_gallery_image", "detail_open", "detail_open", function_block="SelectGalleryImage", code_contract_id="ui.images.select", output="selected_image_transform_reset", pure_ui=True, rationale="Selecting a thumbnail changes only the reader view and resets zoom and pan."),
        UITransition("zoom_image_in", "zoom_image_in", "detail_open", "detail_open", function_block="ZoomGalleryImage", code_contract_id="ui.images.zoom", output="image_zoom_clamped_0_5_to_5", pure_ui=True, rationale="Zoom remains a local 0.5x to 5x reader transform."),
        UITransition("zoom_image_out", "zoom_image_out", "detail_open", "detail_open", function_block="ZoomGalleryImage", code_contract_id="ui.images.zoom", output="image_zoom_clamped_0_5_to_5", pure_ui=True, rationale="Zoom remains a local 0.5x to 5x reader transform."),
        UITransition("reset_image_zoom", "reset_image_zoom", "detail_open", "detail_open", function_block="ResetGalleryImage", code_contract_id="ui.images.reset", output="image_transform_reset", pure_ui=True, rationale="Reset restores the selected image to 1x and centered."),
        UITransition("pan_image", "pan_image", "detail_open", "detail_open", function_block="PanGalleryImage", code_contract_id="ui.images.pan", output="image_pan_clamped", pure_ui=True, rationale="Panning is available only while zoomed and cannot change canonical Matter data."),
        UITransition("navigate_image_keyboard", "navigate_image_keyboard", "detail_open", "detail_open", function_block="NavigateGalleryImage", code_contract_id="ui.images.keyboard", output="selected_image_transform_reset", pure_ui=True, rationale="Arrow, Home, and End select a thumbnail with roving focus and reset the transform."),
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
            "root-only catalog ordered by latest meaningful clue after every query/filter, with Start time as an independent filter",
            "root detail with a Matter-only hierarchy and one reusable node quick view, exactly eight primary sections, subordinate evidence, generated hero outside evidence, read-only image gallery, and no ordinary correction control",
            "background status never disables a current catalog",
        ),
        rationale="The model is an autonomous object browser, not an approval queue.",
    )


def visible_surface() -> UIVisibleSurface:
    rows = (
        ("surface_heading", "heading", "Matters", ("catalog_loading", "catalog_ready", "catalog_empty", "catalog_no_results", "catalog_error", "catalog_stale_error", "detail_open"), "catalog_heading", "catalog_heading"),
        ("surface_summary", "status", "Matter catalog", ("catalog_ready", "catalog_empty", "catalog_no_results", "catalog_stale_error", "detail_open"), "catalog_summary", "catalog_summary"),
        ("surface_unknown_count", "status", "Matter count unavailable", ("catalog_error",), "catalog_unknown_count", "catalog_unknown_count"),
        ("surface_stale_warning", "status", "Showing the last successful catalog", ("catalog_stale_error",), "catalog_stale_warning", "catalog_stale_warning"),
        ("surface_filters", "status", "Current filters", ("catalog_ready", "catalog_empty", "catalog_no_results", "catalog_stale_error"), "filter_summary", "filter_summary"),
        ("surface_coverage", "status", "Coverage", ("catalog_ready", "catalog_stale_error", "detail_open"), "coverage_summary", "coverage_summary"),
        ("surface_background", "status", "Background work", ("catalog_loading", "catalog_ready", "catalog_empty", "catalog_no_results", "catalog_stale_error", "detail_open"), "background_status", "background_status"),
        ("surface_cards", "grid", "Matter cards", ("catalog_ready", "catalog_stale_error"), "matter_cards", "matter_cards"),
        ("surface_generated_hero", "image", "Generated Matter image", ("catalog_ready", "catalog_stale_error", "detail_open"), "generated_hero", "generated_hero"),
        ("surface_empty", "status", "No matters yet", ("catalog_empty",), "empty_catalog", "empty_catalog"),
        ("surface_no_results", "status", "No matching matters", ("catalog_no_results",), "no_search_results", "no_search_results"),
        ("surface_error", "status", "Could not read the matter catalog", ("catalog_error",), "catalog_error", "catalog_recovery"),
        ("surface_detail", "panel", "Matter detail", ("detail_open",), "matter_detail", "matter_detail"),
        ("surface_people", "list", "People", ("detail_open",), "matter_people", "matter_people"),
        ("surface_timeline", "list", "Timeline", ("detail_open",), "matter_timeline", "matter_timeline"),
        ("surface_relations", "list", "Related Matters", ("detail_open",), "matter_relationships", "matter_relationships"),
        ("surface_hierarchy", "graph", "Sub-matter hierarchy", ("detail_open",), "matter_hierarchy_graph", "matter_hierarchy_graph"),
        ("surface_node_quick_view", "dialog", "Sub-matter quick view", ("node_quick_view_open",), "node_quick_view", "node_quick_view"),
        ("surface_files_information", "table", "Files & information", ("detail_open",), "files_information", "files_information"),
        ("surface_image_gallery", "gallery", "Images", ("detail_open",), "image_gallery", "image_gallery"),
        ("surface_ai_supplemental_information", "list", "AI supplemental information", ("detail_open",), "ai_supplemental_information", "ai_supplemental_information"),
        ("surface_evidence", "dialog", "Evidence", ("evidence_open",), "evidence_details", "evidence_details"),
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
            "root detail with Matter-only hierarchy and one reusable node quick view",
            "exactly eight detail sections",
            "evidence as a subordinate Files & information disclosure",
            "no correction or canonical-write control in the ordinary first-version browser",
            "read-only thumbnail and zoomable image gallery",
            "presentation-only generated hero remains distinct from the Images evidence gallery",
            "latest meaningful clue ordering survives Start-time/status filters, language, and density",
            "initial unknown-count and last-successful stale transport recovery",
        ),
        rationale="The visible surface contains browser content, not internal receipts or approval queues.",
    )


def observed_inventory(revision: str, evidence_ref: str) -> UIObservedSurfaceInventory:
    rows = (
        ("observed_retry", "button", "Try again", "catalog_error", "catalog_grid", "[data-retry]", "refresh_catalog", "", ""),
        ("observed_keep_browsing", "button", "Keep browsing", "catalog_stale_error", "catalog_grid", "[data-dismiss-refresh-error]", "dismiss_refresh_error", "", ""),
        ("observed_locale", "select", "English / 中文", "catalog_ready", "sidebar", "#locale-select", "select_locale", "", ""),
        ("observed_density", "toggle", "Standard / Compact", "catalog_ready", "catalog_header", ".db-card-density-switch", "select_density", "", ""),
        ("observed_search", "input", "Search matters", "catalog_ready", "sidebar", "#matters-search", "search_catalog", "", ""),
        ("observed_status_filter", "button", "Status", "catalog_ready", "sidebar", "[data-status]", "select_status", "", ""),
        ("observed_time_filter", "button", "Start time", "catalog_ready", "sidebar", "[data-time]", "select_time", "", ""),
        ("observed_more", "button", "Load more matters", "catalog_ready", "catalog_grid", "[data-load-more]", "next_page", "", ""),
        ("observed_heading", "text", "All matters", "catalog_ready", "catalog_header", ".db-project-list-header h2", "", "catalog_heading", "catalog_heading"),
        ("observed_summary", "status_text", "Matter count", "catalog_ready", "catalog_header", ".db-project-header-meta", "", "catalog_summary", "catalog_summary"),
        ("observed_filters", "text", "Current filters", "catalog_ready", "sidebar", ".db-sidebar-scroll", "", "filter_summary", "filter_summary"),
        ("observed_coverage", "status_text", "Coverage", "catalog_ready", "catalog_header", ".db-source-health-button", "", "coverage_summary", "coverage_summary"),
        ("observed_background", "status_text", "Background work", "catalog_ready", "catalog_header", ".db-source-health-button", "", "background_status", "background_status"),
        ("observed_cards", "text", "Matter cards", "catalog_ready", "catalog_grid", ".db-project-card", "", "matter_cards", "matter_cards"),
        ("observed_generated_hero", "display_field", "Generated Matter image", "catalog_ready", "catalog_grid", "[data-generated-hero]", "", "generated_hero", "generated_hero"),
        ("observed_empty", "status_text", "No matters yet", "catalog_empty", "catalog_grid", ".db-empty-state", "", "empty_catalog", "empty_catalog"),
        ("observed_no_results", "status_text", "No matching matters", "catalog_no_results", "catalog_grid", ".db-empty-state", "", "no_search_results", "no_search_results"),
        ("observed_error", "status_text", "Could not read the matter catalog", "catalog_error", "catalog_grid", "#catalog-error", "", "catalog_error", "catalog_recovery"),
        ("observed_unknown_count", "status_text", "Matter count unavailable", "catalog_error", "catalog_header", "[data-catalog-count='unknown']", "", "catalog_unknown_count", "catalog_unknown_count"),
        ("observed_stale_warning", "status_text", "Showing the last successful catalog", "catalog_stale_error", "catalog_header", "[data-catalog-stale]", "", "catalog_stale_warning", "catalog_stale_warning"),
        ("observed_detail", "text", "Matter detail", "detail_open", "detail", ".db-dialog", "", "matter_detail", "matter_detail"),
        ("observed_people", "text", "People", "detail_open", "detail", "[data-detail-section='people']", "", "matter_people", "matter_people"),
        ("observed_timeline", "text", "Timeline", "detail_open", "detail", ".db-timeline", "", "matter_timeline", "matter_timeline"),
        ("observed_relationships", "text", "Related matters", "detail_open", "detail", "[data-detail-section='relatedMatters']", "", "matter_relationships", "matter_relationships"),
        ("observed_hierarchy", "text", "Sub-matter hierarchy", "detail_open", "detail", "[data-detail-section='children']", "", "matter_hierarchy_graph", "matter_hierarchy_graph"),
        ("observed_node_quick_view", "text", "Sub-matter quick view", "node_quick_view_open", "node_quick_view", "[data-node-quick-view]", "", "node_quick_view", "node_quick_view"),
        ("observed_files_information", "text", "Files & information", "detail_open", "detail", "[data-detail-section='filesInformation']", "", "files_information", "files_information"),
        ("observed_image_gallery", "text", "Images", "detail_open", "detail", "[data-detail-section='images']", "", "image_gallery", "image_gallery"),
        ("observed_ai_supplemental_information", "text", "AI supplemental information", "detail_open", "detail", "[data-detail-section='aiSupplementalInformation']", "", "ai_supplemental_information", "ai_supplemental_information"),
        ("observed_gallery_select", "button", "Select image", "detail_open", "detail", "[data-gallery-thumbnail]", "select_gallery_image", "", ""),
        ("observed_gallery_zoom_in", "button", "Zoom in", "detail_open", "detail", "[data-gallery-zoom-in]", "zoom_image_in", "", ""),
        ("observed_gallery_zoom_out", "button", "Zoom out", "detail_open", "detail", "[data-gallery-zoom-out]", "zoom_image_out", "", ""),
        ("observed_gallery_reset", "button", "Reset image", "detail_open", "detail", "[data-gallery-reset]", "reset_image_zoom", "", ""),
        ("observed_open_submatter", "button", "Open sub-matter", "detail_open", "detail", "[data-matter-node]", "open_submatter_node", "", ""),
        ("observed_close_submatter", "button", "Close sub-matter", "node_quick_view_open", "node_quick_view", "[data-close-node-quick-view]", "close_node_quick_view", "", ""),
        ("observed_evidence", "text", "Evidence", "evidence_open", "detail", ".db-evidence-excerpt", "", "evidence_details", "evidence_details"),
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
            "root catalog ordered by latest meaningful clue, eight-section root detail, Matter-only hierarchy, one reusable quick view, generated hero, subordinate evidence, evidence image gallery, and recovery",
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
        UIFeatureJourney("recover_catalog_transport", label="Recover without inventing an empty catalog", entry_point_ids=("entry_search",), required_state_ids=("catalog_ready", "catalog_stale_error", "catalog_loading"), required_event_ids=("refresh_failure_with_prior", "retry_refresh_with_prior", "dismiss_refresh_error"), success_terminal_state_ids=("catalog_ready",), failure_state_ids=("catalog_stale_error",), recovery_event_ids=("retry_refresh_with_prior", "dismiss_refresh_error"), validation_boundaries=("last-successful content, unknown initial count, finite retry, and stale labeling",), rationale="A transport failure either preserves the prior catalog or shows an unknown count; it never projects zero without a current successful response."),
        UIFeatureJourney("select_language", label="Select language", entry_point_ids=("entry_locale",), required_state_ids=("catalog_loading", "catalog_ready", "detail_open"), required_event_ids=("select_locale_loading", "select_locale_ready", "select_locale_detail"), success_terminal_state_ids=("catalog_ready", "detail_open"), validation_boundaries=("locale switch and reload",), rationale="The same semantic revision renders in English or Chinese."),
        UIFeatureJourney("select_density", label="Select card size", entry_point_ids=("entry_density",), required_state_ids=("catalog_loading", "catalog_ready", "detail_open"), required_event_ids=("select_density_loading", "select_density_ready", "select_density_detail"), success_terminal_state_ids=("catalog_ready", "detail_open"), validation_boundaries=("Standard/Compact switch and reload",), rationale="Density is a persistent user choice independent of viewport."),
        UIFeatureJourney("search_and_filter", label="Search and filter matters", entry_point_ids=("entry_search", "entry_filters"), required_state_ids=("catalog_ready", "catalog_loading", "catalog_no_results"), required_event_ids=("search_catalog", "search_results", "search_no_results", "clear_search", "select_status", "select_time"), success_terminal_state_ids=("catalog_ready", "catalog_no_results"), validation_boundaries=("current query, zero results, clear, state preservation, Start-time filter, and latest-meaningful-clue ordering",), rationale="Search, Status, and Start time preserve all unrelated browser state and the latest meaningful clue remains the primary order inside every result."),
        UIFeatureJourney("page_catalog", label="Navigate a large catalog", entry_point_ids=("entry_page",), required_state_ids=("catalog_ready", "catalog_loading"), required_event_ids=("next_page", "load_ready"), success_terminal_state_ids=("catalog_ready",), validation_boundaries=("transport, stale response discard, scroll anchor, and latest-meaningful-clue order",), rationale="Load more extends the current bounded catalog without losing its activity order."),
        UIFeatureJourney("inspect_matter", label="Inspect one matter", entry_point_ids=("entry_detail",), required_state_ids=("catalog_ready", "detail_open"), required_event_ids=("open_matter", "select_detail_section", "close_detail", "escape_detail"), success_terminal_state_ids=("detail_open",), cancel_event_ids=("close_detail", "escape_detail"), validation_boundaries=("exactly eight detail sections and focus return",), rationale="One card opens a human-readable object detail with Overview, Sub-matters, Timeline, People, Related Matters, Files & information, Images, and AI supplemental information, then returns to the same catalog position."),
        UIFeatureJourney(
            "navigate_hierarchy",
            label="Inspect the Matter hierarchy",
            entry_point_ids=("entry_detail",),
            required_state_ids=("catalog_ready", "detail_open", "node_quick_view_open"),
            required_event_ids=(
                "open_matter",
                "open_submatter_node",
                "close_node_quick_view",
                "escape_node_quick_view",
            ),
            success_terminal_state_ids=("detail_open",),
            validation_boundaries=(
                "root-only catalog",
                "Matter-only graph nodes",
                "no per-node collapse control",
                "one reusable node quick view",
                "node-specific itemized facts and sources",
                "reparent freshness",
            ),
            rationale=(
                "Every current child Matter is reachable without recursive child "
                "detail pages; another selection replaces the one quick view."
            ),
        ),
        UIFeatureJourney("inspect_files_information", label="Inspect files and information", entry_point_ids=("entry_detail",), required_state_ids=("catalog_ready", "detail_open", "evidence_open"), required_event_ids=("open_matter", "select_detail_section", "open_evidence", "close_evidence", "escape_evidence"), success_terminal_state_ids=("detail_open", "evidence_open"), cancel_event_ids=("close_evidence", "escape_evidence"), validation_boundaries=("one bounded privacy-safe flat table, SourceGroup column without repeated group subheaders, row disclosure, and keyboard return",), rationale="Files, messages, and other information share one bounded flat table; each row retains its SourceGroup and evidence/history opens only from that row."),
        UIFeatureJourney("inspect_images", label="Inspect Matter images", entry_point_ids=("entry_detail",), required_state_ids=("catalog_ready", "detail_open"), required_event_ids=("open_matter", "select_detail_section", "select_gallery_image", "zoom_image_in", "zoom_image_out", "reset_image_zoom", "pan_image", "navigate_image_keyboard"), success_terminal_state_ids=("detail_open",), validation_boundaries=("true visual-image admission, document-preview exclusion, thumbnail selection, selected large image, 0.5x-5x clamp, reset, wheel/pan, and keyboard navigation",), rationale="Images is a read-only gallery for real photos or meaningful visual images; email, TXT, document, form, and text-page screenshots stay in Files & information."),
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
            "refresh_failure_with_prior",
        ),
        "catalog_no_results": (
            "select_locale_no_results",
            "select_density_no_results",
            "search_again",
            "clear_search",
            "select_status_no_results",
            "select_time_no_results",
        ),
        "catalog_stale_error": (
            "retry_refresh_with_prior",
            "dismiss_refresh_error",
        ),
        "detail_open": (
            "close_detail",
            "escape_detail",
            "select_detail_section",
            "select_locale_detail",
            "select_density_detail",
            "open_evidence",
            "open_submatter_node",
            "select_gallery_image",
            "zoom_image_in",
            "zoom_image_out",
            "reset_image_zoom",
            "pan_image",
            "navigate_image_keyboard",
        ),
        "node_quick_view_open": (
            "close_node_quick_view",
            "escape_node_quick_view",
        ),
        "evidence_open": ("close_evidence", "escape_evidence"),
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
            "initial and stale transport recovery",
            "exactly eight detail sections and hierarchy navigation",
            "Files & information with subordinate evidence",
            "ordinary browser has no correction or canonical-write control",
            "read-only evidence image gallery distinct from the generated hero",
            "AI supplemental information labeled as advisory rather than source evidence",
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
        ("capability:navigate_hierarchy", "Inspect the Matter hierarchy", "navigate", ("output:hierarchy",), "ui.openSubmatterNode"),
        ("capability:recover_transport", "Recover catalog transport without false zero", "load", ("output:transport_recovery",), "ui.loadCatalog"),
        ("capability:inspect_files_information", "Inspect files and information", "open", ("output:files_information",), "ui.openEvidence"),
        ("capability:inspect_images", "Inspect Matter images", "open", ("output:images",), "ui.selectGalleryImage"),
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
        ("recover_catalog_transport", "Recover catalog transport", "capability:recover_transport", ("entry_search",), ("refresh_catalog", "dismiss_refresh_error"), ("refresh_failure_with_prior", "retry_refresh_with_prior", "dismiss_refresh_error"), "output:transport_recovery"),
        ("select_language", "Select language", "capability:select_language", ("entry_locale",), ("select_locale",), ("select_locale_ready", "select_locale_loading", "select_locale_detail"), "output:locale"),
        ("select_density", "Select card size", "capability:select_density", ("entry_density",), ("select_density",), ("select_density_ready", "select_density_loading", "select_density_detail"), "output:density"),
        ("search_and_filter", "Search and filter", "capability:search_filter", ("entry_search", "entry_filters"), ("search_catalog", "clear_search", "select_status", "select_time"), ("search_catalog", "search_results", "search_no_results", "clear_search", "select_status", "select_time"), "output:query"),
        ("page_catalog", "Navigate catalog pages", "capability:page_catalog", ("entry_page",), ("next_page",), ("next_page", "load_ready"), "output:page"),
        ("inspect_matter", "Inspect one Matter", "capability:inspect_matter", ("entry_detail",), ("open_matter", "close_detail", "select_detail_section"), ("open_matter", "close_detail", "escape_detail", "select_detail_section"), "output:detail"),
        (
            "navigate_hierarchy",
            "Inspect the Matter hierarchy",
            "capability:navigate_hierarchy",
            ("entry_detail",),
            (
                "open_matter",
                "open_submatter_node",
                "close_node_quick_view",
            ),
            (
                "open_matter",
                "open_submatter_node",
                "close_node_quick_view",
                "escape_node_quick_view",
            ),
            "output:hierarchy",
        ),
        ("inspect_files_information", "Inspect files and information", "capability:inspect_files_information", ("entry_detail",), ("select_detail_section", "open_evidence", "close_evidence"), ("open_matter", "select_detail_section", "open_evidence", "close_evidence", "escape_evidence"), "output:files_information"),
        ("inspect_images", "Inspect Matter images", "capability:inspect_images", ("entry_detail",), ("select_detail_section", "select_gallery_image", "zoom_image_in", "zoom_image_out", "reset_image_zoom", "pan_image", "navigate_image_keyboard"), ("open_matter", "select_detail_section", "select_gallery_image", "zoom_image_in", "zoom_image_out", "reset_image_zoom", "pan_image", "navigate_image_keyboard"), "output:images"),
    )
    return tuple(
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
            pure_ui=feature_id in {"select_language", "select_density", "inspect_images"},
            rationale="The feature joins one task, journey, control set, and visible output.",
        )
        for feature_id, label, capability_id, entry_ids, control_ids, event_ids, output_id in simple
    )


OUTPUT_ROWS = (
    ("output:catalog", "capability:browse_catalog", ("catalog_ready", "catalog_empty", "catalog_error"), ("catalog_summary", "matter_cards", "empty_catalog", "catalog_error", "catalog_unknown_count"), "A current catalog, honest empty state, or visible recovery with an unknown count is observed."),
    ("output:transport_recovery", "capability:recover_transport", ("catalog_ready", "catalog_stale_error", "catalog_error"), ("matter_cards", "catalog_stale_warning", "catalog_unknown_count"), "A failed refresh preserves the last successful cards while a failed first load exposes an unknown count; neither becomes zero."),
    ("output:locale", "capability:select_language", ("catalog_ready", "detail_open"), ("catalog_summary", "matter_detail"), "English default and Chinese selection preserve one semantic revision."),
    ("output:density", "capability:select_density", ("catalog_ready",), ("matter_cards", "generated_hero"), "Standard and Compact preserve objects, latest-meaningful-clue order, generated-hero identity, locale, filters, selection, and scroll; Compact omits secondary metrics and expands the Hero."),
    ("output:query", "capability:search_filter", ("catalog_loading", "catalog_ready", "catalog_no_results"), ("matter_cards", "no_search_results"), "A current query result or clear zero-result state is observed; Status and Start time filter without replacing latest-meaningful-clue ordering."),
    ("output:page", "capability:page_catalog", ("catalog_loading", "catalog_ready"), ("matter_cards",), "Only the latest current bounded page replaces the grid and it preserves latest-meaningful-clue ordering."),
    ("output:detail", "capability:inspect_matter", ("detail_open", "catalog_ready"), ("matter_detail", "matter_hierarchy_graph", "matter_timeline", "matter_people", "matter_relationships", "files_information", "image_gallery", "ai_supplemental_information", "generated_hero"), "A human-readable root detail exposes exactly eight primary sections, a presentation-only generated hero, and returns to the preserved catalog."),
    ("output:hierarchy", "capability:navigate_hierarchy", ("detail_open", "node_quick_view_open"), ("matter_hierarchy_graph", "node_quick_view"), "Sub-matters is a Matter-only graph; selecting a Matter opens one reusable quick view with itemized current content and node-specific sources."),
    ("output:files_information", "capability:inspect_files_information", ("detail_open", "evidence_open"), ("files_information", "evidence_details"), "A bounded privacy-safe file and information table renders first; row evidence and history reveal only on demand."),
    ("output:images", "capability:inspect_images", ("detail_open",), ("image_gallery",), "A read-only evidence-image thumbnail gallery selects one large image with 0.5x-5x zoom, reset, pan, wheel, and keyboard navigation; generated heroes are excluded."),
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
    ("chain:transport-stale", "refresh_catalog", "refresh_failure_with_prior", "loadCatalog", "catalog_stale_error", "catalog_stale_warning", "last successful catalog retained with stale warning"),
    ("chain:transport-dismiss", "dismiss_refresh_error", "dismiss_refresh_error", "dismissRefreshError", "catalog_ready", "matter_cards", "same last-successful catalog remains browsable"),
    ("chain:locale", "select_locale", "select_locale_ready", "selectLanguage", "catalog_ready", "matter_cards", "same objects in selected locale"),
    ("chain:density", "select_density", "select_density_ready", "selectCardDensity", "catalog_ready", "matter_cards", "same objects at selected density"),
    ("chain:search", "search_catalog", "search_catalog", "searchCatalog", "catalog_ready", "matter_cards", "current search result"),
    ("chain:status", "select_status", "select_status", "selectStatus", "catalog_ready", "matter_cards", "current status-filtered catalog"),
    ("chain:time", "select_time", "select_time", "selectTimeWindow", "catalog_ready", "matter_cards", "current time-filtered catalog"),
    ("chain:page", "next_page", "next_page", "loadMatterPage", "catalog_ready", "matter_cards", "current next page"),
    ("chain:detail", "open_matter", "open_matter", "openMatter", "detail_open", "matter_detail", "current Matter detail"),
    ("chain:detail-close", "close_detail", "close_detail", "closeMatter", "catalog_ready", "matter_cards", "preserved catalog state"),
    ("chain:submatter-open", "open_submatter_node", "open_submatter_node", "openSubmatterNode", "node_quick_view_open", "node_quick_view", "selected Matter summary, facts, events, work, waits, and sources"),
    ("chain:submatter-close", "close_node_quick_view", "close_node_quick_view", "closeNodeQuickView", "detail_open", "matter_hierarchy_graph", "root detail and graph focus restored"),
    ("chain:files-information", "select_detail_section", "select_detail_section", "selectDetailSection", "detail_open", "files_information", "bounded privacy-safe file and information table"),
    ("chain:evidence", "open_evidence", "open_evidence", "openEvidence", "evidence_open", "evidence_details", "evidence revealed"),
    ("chain:evidence-close", "close_evidence", "close_evidence", "closeEvidence", "detail_open", "matter_detail", "evidence hidden and focus returned"),
    ("chain:image-select", "select_gallery_image", "select_gallery_image", "selectGalleryImage", "detail_open", "image_gallery", "selected large image with reset transform"),
    ("chain:image-zoom-in", "zoom_image_in", "zoom_image_in", "zoomImageIn", "detail_open", "image_gallery", "image zoom clamped to 0.5x-5x"),
    ("chain:image-zoom-out", "zoom_image_out", "zoom_image_out", "zoomImageOut", "detail_open", "image_gallery", "image zoom clamped to 0.5x-5x"),
    ("chain:image-reset", "reset_image_zoom", "reset_image_zoom", "resetImageZoom", "detail_open", "image_gallery", "image returned to centered 1x"),
    ("chain:image-pan", "pan_image", "pan_image", "panImage", "detail_open", "image_gallery", "local zoomed image pan"),
    ("chain:image-keyboard", "navigate_image_keyboard", "navigate_image_keyboard", "navigateImageKeyboard", "detail_open", "image_gallery", "roving keyboard selection with reset transform"),
)


def capability_bindings(revision: str, evidence_ref: str) -> tuple[UICapabilityCoverageBinding, ...]:
    mapping = (
        ("binding:catalog", "capability:browse_catalog", "browse_catalog", ("refresh_catalog",), ("load_ready", "load_empty", "load_failure", "retry_catalog"), ("chain:catalog",), "output:catalog"),
        ("binding:transport", "capability:recover_transport", "recover_catalog_transport", ("refresh_catalog", "dismiss_refresh_error"), ("refresh_failure_with_prior", "retry_refresh_with_prior", "dismiss_refresh_error"), ("chain:transport-stale", "chain:transport-dismiss"), "output:transport_recovery"),
        ("binding:locale", "capability:select_language", "select_language", ("select_locale",), ("select_locale_ready", "select_locale_loading", "select_locale_detail"), ("chain:locale",), "output:locale"),
        ("binding:density", "capability:select_density", "select_density", ("select_density",), ("select_density_ready", "select_density_loading", "select_density_detail"), ("chain:density",), "output:density"),
        ("binding:query", "capability:search_filter", "search_and_filter", ("search_catalog", "clear_search", "select_status", "select_time"), ("search_catalog", "search_results", "search_no_results", "clear_search", "select_status", "select_time"), ("chain:search", "chain:status", "chain:time"), "output:query"),
        ("binding:page", "capability:page_catalog", "page_catalog", ("next_page",), ("next_page", "load_ready"), ("chain:page",), "output:page"),
        ("binding:detail", "capability:inspect_matter", "inspect_matter", ("open_matter", "close_detail", "select_detail_section"), ("open_matter", "close_detail", "escape_detail", "select_detail_section"), ("chain:detail", "chain:detail-close"), "output:detail"),
        (
            "binding:hierarchy",
            "capability:navigate_hierarchy",
            "navigate_hierarchy",
            (
                "open_matter",
                "open_submatter_node",
                "close_node_quick_view",
            ),
            (
                "open_matter",
                "open_submatter_node",
                "close_node_quick_view",
                "escape_node_quick_view",
            ),
            (
                "chain:detail",
                "chain:submatter-open",
                "chain:submatter-close",
            ),
            "output:hierarchy",
        ),
        ("binding:files-information", "capability:inspect_files_information", "inspect_files_information", ("select_detail_section", "open_evidence", "close_evidence"), ("open_matter", "select_detail_section", "open_evidence", "close_evidence", "escape_evidence"), ("chain:files-information", "chain:evidence", "chain:evidence-close"), "output:files_information"),
        ("binding:images", "capability:inspect_images", "inspect_images", ("select_detail_section", "select_gallery_image", "zoom_image_in", "zoom_image_out", "reset_image_zoom", "pan_image", "navigate_image_keyboard"), ("open_matter", "select_detail_section", "select_gallery_image", "zoom_image_in", "zoom_image_out", "reset_image_zoom", "pan_image", "navigate_image_keyboard"), ("chain:image-select", "chain:image-zoom-in", "chain:image-zoom-out", "chain:image-reset", "chain:image-pan", "chain:image-keyboard"), "output:images"),
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
    pure_controls = {
        "select_locale",
        "select_density",
        "close_detail",
        "select_detail_section",
        "close_node_quick_view",
        "dismiss_refresh_error",
        "open_evidence",
        "close_evidence",
        "select_gallery_image",
        "zoom_image_in",
        "zoom_image_out",
        "reset_image_zoom",
        "pan_image",
        "navigate_image_keyboard",
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
                business_bearing=False,
                business_intent_id="",
                behavior_commitment_id="",
                primary_path_id="",
                consistency_rule_ids=(),
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
        "recover_catalog_transport": (
            ("refresh_failure_with_prior", "refresh_catalog", "catalog_ready", "catalog_stale_error"),
            ("retry_refresh_with_prior", "refresh_catalog", "catalog_stale_error", "catalog_loading"),
            ("dismiss_refresh_error", "dismiss_refresh_error", "catalog_stale_error", "catalog_ready"),
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
        "navigate_hierarchy": (
            ("open_matter", "open_matter", "catalog_ready", "detail_open"),
            (
                "open_submatter_node",
                "open_submatter_node",
                "detail_open",
                "node_quick_view_open",
            ),
            (
                "close_node_quick_view",
                "close_node_quick_view",
                "node_quick_view_open",
                "detail_open",
            ),
            (
                "escape_node_quick_view",
                "close_node_quick_view",
                "node_quick_view_open",
                "detail_open",
            ),
        ),
        "inspect_files_information": (
            ("open_matter", "open_matter", "catalog_ready", "detail_open"),
            ("select_detail_section", "select_detail_section", "detail_open", "detail_open"),
            ("open_evidence", "open_evidence", "detail_open", "evidence_open"),
            ("close_evidence", "close_evidence", "evidence_open", "detail_open"),
            ("escape_evidence", "close_evidence", "evidence_open", "detail_open"),
        ),
        "inspect_images": (
            ("open_matter", "open_matter", "catalog_ready", "detail_open"),
            ("select_detail_section", "select_detail_section", "detail_open", "detail_open"),
            ("select_gallery_image", "select_gallery_image", "detail_open", "detail_open"),
            ("zoom_image_in", "zoom_image_in", "detail_open", "detail_open"),
            ("zoom_image_out", "zoom_image_out", "detail_open", "detail_open"),
            ("reset_image_zoom", "reset_image_zoom", "detail_open", "detail_open"),
            ("pan_image", "pan_image", "detail_open", "detail_open"),
            ("navigate_image_keyboard", "navigate_image_keyboard", "detail_open", "detail_open"),
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
            ("generated_hero", "observed_generated_hero", "catalog_ready"),
            ("empty_catalog", "observed_empty", "catalog_empty"),
            ("no_search_results", "observed_no_results", "catalog_no_results"),
            ("catalog_recovery", "observed_error", "catalog_error"),
            ("catalog_unknown_count", "observed_unknown_count", "catalog_error"),
            ("catalog_stale_warning", "observed_stale_warning", "catalog_stale_error"),
        )
    )
    on_demand_evidence = tuple(
        evidence
        for content_id, observed_id, open_state, open_event, close_event in (
            ("matter_detail", "observed_detail", "detail_open", "open_matter", "close_detail"),
            ("matter_timeline", "observed_timeline", "detail_open", "open_matter", "close_detail"),
            ("matter_people", "observed_people", "detail_open", "open_matter", "close_detail"),
            ("matter_relationships", "observed_relationships", "detail_open", "open_matter", "close_detail"),
            ("matter_hierarchy_graph", "observed_hierarchy", "detail_open", "open_matter", "close_detail"),
            ("node_quick_view", "observed_node_quick_view", "node_quick_view_open", "open_submatter_node", "close_node_quick_view"),
            ("files_information", "observed_files_information", "detail_open", "open_matter", "close_detail"),
            ("image_gallery", "observed_image_gallery", "detail_open", "open_matter", "close_detail"),
            ("ai_supplemental_information", "observed_ai_supplemental_information", "detail_open", "open_matter", "close_detail"),
            ("evidence_details", "observed_evidence", "evidence_open", "open_evidence", "close_evidence"),
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
            "dismiss_refresh_error",
            "close_detail",
            "select_detail_section",
            "close_node_quick_view",
            "open_evidence",
            "close_evidence",
            "select_gallery_image",
            "zoom_image_in",
            "zoom_image_out",
            "reset_image_zoom",
            "pan_image",
            "navigate_image_keyboard",
        ),
        pure_ui_event_ids=(
            "select_locale_ready",
            "select_locale_loading",
            "select_locale_detail",
            "select_density_ready",
            "select_density_loading",
            "select_density_detail",
            "dismiss_refresh_error",
            "close_detail",
            "escape_detail",
            "select_detail_section",
            "close_node_quick_view",
            "escape_node_quick_view",
            "open_evidence",
            "close_evidence",
            "escape_evidence",
            "select_gallery_image",
            "zoom_image_in",
            "zoom_image_out",
            "reset_image_zoom",
            "pan_image",
            "navigate_image_keyboard",
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
                ("browser_click", "catalog ordered by latest meaningful clue, density, locale, search, Status and Start time filters, root eight-section detail with Matter-only hierarchy and one reusable quick view, generated hero, subordinate evidence, AI supplemental information, read-only evidence image gallery, and no ordinary correction control", "catalog_ready"),
                ("dom_text", "English and zh-CN object-browser surface with identical semantic revision and bilingual generated-hero alt text", "catalog_ready"),
                ("geometry", "1880x900 and 1440x900 desktop matrices across English/zh-CN and Standard/Compact, plus bounded narrow fallbacks", "catalog_ready"),
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
            "zero, one, few, and deep Matter-only graphs with one reusable quick view",
            "generated-hero ready, pending, blocked, stale, and transport-error states",
            "evidence-image gallery distinct from generated hero",
            "sidebar top, brand-to-search, and search-to-navigation gap inequalities",
            "visible non-transparent icon center, Matters wordmark center, and catalog-heading center-line alignment",
            "search-control top and first visible card-row top alignment",
            "day-only YYYY-MM-DD card Start projection with no time or timezone suffix",
            "plain lifecycle status and Start-date metadata typography parity without a status capsule",
            "approved font-size tokens and card metadata without repetition",
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
            UIHotPathAction("hot:quick-view-close", event_id="close_node_quick_view", feedback_target_id="matter_hierarchy_graph", feedback_description="The one quick view closes immediately and focus returns to its Matter node.", rationale="Closing the overlay is local to the current hierarchy revision."),
        ),
        cold_path_work=(
            UIColdPathWork("cold:catalog", trigger_event_id="retry_catalog", result_target_id="matter_cards", stale_guard="request revision accepts only the latest catalog response", cancellation_rule="a newer query or retry supersedes an older response", coalescing_rule="an unchanged background response updates only the coverage status region; a changed catalog performs one current catalog render", rationale="Late or unchanged background transport cannot overwrite newer browser state or detach an operable global control."),
            UIColdPathWork("cold:query", trigger_event_id="search_catalog", result_target_id="matter_cards", stale_guard="query/filter/window/revision identity", cancellation_rule="newer query cancels or invalidates older work", coalescing_rule="one current query window", rationale="Search and filtering are revision-safe."),
            UIColdPathWork("cold:node-quick-view", trigger_event_id="open_submatter_node", result_target_id="node_quick_view", stale_guard="selected Matter id plus C6 hierarchy revision", cancellation_rule="a newer Matter-node selection supersedes an older response", coalescing_rule="one root detail and one reusable node quick view", rationale="A stale node response cannot replace the newer quick view or open a child detail shell."),
        ),
        stable_region_rules=(
            UIStableRegionRule("topbar", preservation_rule="Brand, search, language, density, and background status keep stable placement and node identity while an unchanged background poll updates only coverage status.", unrelated_input_ids=("catalog length", "detail section", "unchanged background response"), rationale="Background progress cannot detach, disable, or move an operable global control."),
            UIStableRegionRule("sidebar", preservation_rule="The approved 48px logo and 26px Matters title remain unchanged, vertically aligned as one left-aligned group, and top-aligned with the catalog heading; search and navigation move upward so top whitespace is greater than both positive brand-to-search and search-to-navigation gaps.", unrelated_input_ids=("card density", "selected Matter", "catalog length"), rationale="Filtering context remains visible without changing the approved brand typography."),
            UIStableRegionRule("catalog_grid", preservation_rule="Query, Status and Start-time filters, latest-meaningful-clue sort, window, generated-hero identity, selection, and scroll anchor survive locale, density, detail, and recovery transitions.", unrelated_input_ids=("locale", "density", "detail section"), rationale="Display changes never reset browsing position or activity order."),
            UIStableRegionRule("detail", preservation_rule="One centered root detail remains stable while the Matter-only hierarchy and one reusable quick view update.", unrelated_input_ids=("hierarchy depth", "selected Matter node"), rationale="Recursive semantic depth never becomes recursive page or modal geometry."),
        ),
        validation_boundaries=(
            "immediate feedback",
            "stale response rejection",
            "persistent Standard/Compact preference",
            "stable global and catalog regions",
            "latest meaningful clue remains the primary order after every filter, language, and density transition",
            "generated hero never becomes source evidence or an Images-gallery item",
            "root-detail plus single quick-view navigation and stale hierarchy-response rejection",
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
