"""C12 bilingual desktop Matter object-browser finite FlowGuard model."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


TRANSPORT_PHASE_CASES = {
    "loading": "catalog_load_started",
    "processing": "catalog_processing_current",
    "ready": "matter_catalog_current",
    "honest_empty": "catalog_honest_empty_current",
    "no_filter_results": "catalog_no_filter_results_current",
    "ready_stale": "catalog_timeout_with_prior_content",
    "transport_error": "catalog_transport_error_initial",
}


OBSERVED_TRANSPORT_MODEL_MISS = {
    "miss_id": "MM-C12-001-zero-matters-failed-fetch",
    "miss_type": "state_too_coarse",
    "behavior_plane": "product_ui_projection",
    "primary_owner_model_id": "C12_projection_bilingual_ui",
    "previous_claim": (
        "the object browser truthfully displayed catalog and coverage state"
    ),
    "observed_failure": (
        "the visible browser simultaneously showed 0 matters, 0/0 coverage, "
        "and Failed to fetch"
    ),
    "error_signature": "0 matters + 0/0 coverage + Failed to fetch",
    "supported_cause": (
        "transport failure, a successful empty catalog, and a successful "
        "zero-result filter were not represented as separate UI states"
    ),
    "would_have_failed_if": (
        "the model had required an explicit transport phase and forbidden zero "
        "catalog or coverage counts without a current successful response"
    ),
    "generalized_case_ids": (
        "catalog_transport_error_initial",
        "catalog_timeout_with_prior_content",
        "catalog_no_filter_results_current",
        "catalog_honest_empty_current",
        "catalog_transport_recovered",
    ),
    "closure_evidence_ids": (
        "H-C12-024-transport-error-becomes-empty",
        "H-C12-025-timeout-erases-prior-catalog",
        "H-C12-026-filter-zero-becomes-global-empty",
        "H-C12-027-auto-reconnect-stuck",
    ),
}


SPEC = FiniteModelSpec(
    model_id="C12_projection_bilingual_ui",
    title="C12 Bilingual Desktop Matter Object Browser",
    modeled_boundary=(
        "one-revision Matter catalog and detail projection, English-default and "
        "Chinese locale selection, distinct human-readable localized root-card "
        "title with no card summary or key-person row, day-only visible Start "
        "projection, plain status/date metadata parity, visible brand/heading "
        "visual-center alignment with transparent-icon compensation plus "
        "independent search/first-card-row top alignment, "
        "human-readable timelines, latest-material-clue activity ordering, one "
        "presentation-only photoreal generated hero per root Matter, Standard/Compact "
        "density, preserved search/filter/selection/scroll state, coverage and "
        "worker status, exactly eight ordinary detail sections, one bounded flat "
        "Files and information row set with folder, Gmail thread, Codex project/"
        "workspace, or provider retained as a SourceGroup column, one compact "
        "single-line truthful coverage indicator with indexed first-gap drilldown, "
        "a pannable bounded multi-depth Matter-only hierarchy graph and one "
        "reusable single-layer descendant quick view that keeps itemized facts, "
        "events, work, waits, and node-specific sources inside the selected Matter, an operable "
        "Images evidence gallery, labeled AI supplemental "
        "information, optional on-demand correction outside primary "
        "navigation, root-only catalog, descendant-aware timeline, "
        "transport-error preservation, internal-data hiding, and projection-only "
        "desktop UI"
    ),
    state_fields=(
        "projection.localized_values",
        "projection.locale_registry",
        "projection.equivalence_status",
        "projection.hierarchy_revision",
        "projection.material_clue_revision",
        "projection.summary_revision",
        "projection.parent_narrative_revision",
        "projection.parent_narrative_scope_revision",
        "projection.parent_narrative_child_projection_revisions",
        "projection.parent_narrative_evidence_revisions",
        "projection.parent_narrative_refresh_status",
        "projection.activity_order_revision",
        "projection.generated_hero_asset",
        "projection.generated_hero_revision",
        "projection.generated_hero_brief_fingerprint",
        "projection.generated_hero_safety_disposition",
        "projection.generated_hero_currentness",
        "projection.generated_hero_localized_alt",
        "projection.generated_hero_status",
        "projection.supplemental_information",
        "projection.supplemental_information_revision",
        "projection.supplemental_information_status",
        "projection.supplemental_information_disposition",
        "projection.supplemental_research_package_id",
        "projection.supplemental_provider_gate",
        "projection.admitted_matter_id",
        "projection.analysis_owner_currentness",
        "projection.state_basis_modality",
        "projection.state_basis_scope",
        "projection.lifecycle_visual_state",
        "ui.selected_locale",
        "ui.locale_preference",
        "ui.card_density",
        "ui.viewport_mode",
        "ui.query",
        "ui.filter_state",
        "ui.sort_state",
        "ui.catalog_window",
        "ui.catalog_cursor",
        "ui.catalog_revision",
        "ui.catalog_query_plan_revision",
        "ui.catalog_page_id_set",
        "ui.selected_matter_id",
        "ui.detail_section",
        "ui.detail_sections",
        "ui.files_information_window",
        "ui.image_gallery_state",
        "ui.supplemental_information_state",
        "ui.browser_scroll_anchor",
        "ui.focus_context",
        "ui.coverage_summary",
        "ui.coverage_indicator_state",
        "ui.coverage_drilldown",
        "ui.background_status",
        "ui.correction_state",
        "ui.request_state",
        "ui.transport_phase",
        "ui.last_successful_catalog_revision",
        "ui.transport_retry_attempt",
        "ui.transport_retry_due_at",
        "ui.surface_evidence_revision",
        "ui.surface_evidence_status",
        "ui.situation_graph_view_state",
        "ui.matter_hierarchy_projection",
        "ui.situation_graph_continuation",
        "ui.node_quick_view_state",
        "ui.node_quick_view_facts",
        "ui.node_quick_view_source_groups",
        "ui.source_group_window",
    ),
    owned_write_fields=(
        "projection.localized_values",
        "projection.locale_registry",
        "projection.equivalence_status",
        "projection.hierarchy_revision",
        "projection.material_clue_revision",
        "projection.summary_revision",
        "projection.parent_narrative_revision",
        "projection.parent_narrative_scope_revision",
        "projection.parent_narrative_child_projection_revisions",
        "projection.parent_narrative_evidence_revisions",
        "projection.parent_narrative_refresh_status",
        "projection.activity_order_revision",
        "projection.generated_hero_asset",
        "projection.generated_hero_revision",
        "projection.generated_hero_brief_fingerprint",
        "projection.generated_hero_safety_disposition",
        "projection.generated_hero_currentness",
        "projection.generated_hero_localized_alt",
        "projection.generated_hero_status",
        "projection.supplemental_information",
        "projection.supplemental_information_revision",
        "projection.supplemental_information_status",
        "projection.supplemental_information_disposition",
        "projection.supplemental_research_package_id",
        "projection.supplemental_provider_gate",
        "projection.admitted_matter_id",
        "projection.analysis_owner_currentness",
        "projection.state_basis_modality",
        "projection.state_basis_scope",
        "projection.lifecycle_visual_state",
        "ui.selected_locale",
        "ui.locale_preference",
        "ui.card_density",
        "ui.viewport_mode",
        "ui.query",
        "ui.filter_state",
        "ui.sort_state",
        "ui.catalog_window",
        "ui.catalog_cursor",
        "ui.catalog_revision",
        "ui.catalog_query_plan_revision",
        "ui.catalog_page_id_set",
        "ui.selected_matter_id",
        "ui.detail_section",
        "ui.detail_sections",
        "ui.files_information_window",
        "ui.image_gallery_state",
        "ui.supplemental_information_state",
        "ui.browser_scroll_anchor",
        "ui.focus_context",
        "ui.coverage_summary",
        "ui.coverage_indicator_state",
        "ui.coverage_drilldown",
        "ui.background_status",
        "ui.correction_state",
        "ui.request_state",
        "ui.transport_phase",
        "ui.last_successful_catalog_revision",
        "ui.transport_retry_attempt",
        "ui.transport_retry_due_at",
        "ui.surface_evidence_revision",
        "ui.surface_evidence_status",
        "ui.situation_graph_view_state",
        "ui.matter_hierarchy_projection",
        "ui.situation_graph_continuation",
        "ui.node_quick_view_state",
        "ui.node_quick_view_facts",
        "ui.node_quick_view_source_groups",
        "ui.source_group_window",
    ),
    side_effect_classes=(
        "projection_publish",
        "ui_preference_write",
        "ui_window_write",
        "activity_projection_publish",
        "generated_hero_projection_publish",
        "supplemental_information_publish",
        "supplemental_research_queue",
        "surface_evidence_write",
        "transport_reconnect_schedule",
        "transport_reconnect_cancel",
    ),
    completion_evidence=(
        "LocalizedProjection",
        "LocaleRegistry",
        "MatterCatalog",
        "IndexedCatalogPage",
        "VisibleCardHydrationBounded",
        "MatterCard",
        "MatterDetail",
        "MatterDetailEightSections",
        "FilesInformationTable",
        "ImagesGallery",
        "GalleryViewState",
        "AISupplementalInformation",
        "SupplementalInformationUnavailable",
        "SupplementalResearchQueued",
        "SupplementalNotApplicable",
        "TransportErrorPreserved",
        "HumanReadableTimeline",
        "MaterialClue",
        "ActivityOrderCurrent",
        "SummaryClueAtomicProjection",
        "ParentNarrativeCurrent",
        "ParentNarrativeRefreshQueued",
        "ParentNarrativeWriteBoundaryPreserved",
        "GeneratedHeroProjection",
        "HeroPendingPlaceholder",
        "SurfaceEvidenceCurrent",
        "DensitySelection",
        "CoverageSummary",
        "BackgroundStatus",
        "ProjectionPending",
        "CorrectionEvent",
        "RootMatterCatalog",
        "HierarchyProjectionCurrent",
        "HierarchyUIReachable",
        "HierarchyDepthPendingVisible",
        "BrowserLoading",
        "BrowserProcessing",
        "BrowserReady",
        "HonestEmptyCatalog",
        "NoFilterResults",
        "BrowserReadyStale",
        "BrowserTransportError",
        "TransportReconnectScheduled",
        "TransportRecovered",
        "AdmittedMatterProjectionIdentity",
        "NonCanonicalProjectionExcluded",
        "StaleAnalysisProjectionExcluded",
        "SituationGraphView",
        "SituationGraphContinuation",
        "NodeQuickView",
        "SourceGroupWindow",
        "SummaryFreeRootCard",
        "RootHeroProjection",
        "DescendantHeroNotApplicable",
        "OverviewMinimalProjection",
        "HumanNarrative",
        "MatterOnlyHierarchyGraph",
        "NodeQuickViewFacts",
        "LogicalTimelineProjection",
        "CompactCoverageIndicator",
        "CoverageFirstGapDrilldown",
        "LifecycleVisualLanguage",
        "FilesInformationReadableTypography",
    ),
    rules=(
        CaseRule(
            case_id="indexed_catalog_page_requested",
            decision="catalog_page_selected_before_card_hydration",
            label="catalog_page_selected_before_card_hydration",
            writes=(
                "ui.catalog_window",
                "ui.catalog_cursor",
                "ui.catalog_revision",
                "ui.catalog_query_plan_revision",
                "ui.catalog_page_id_set",
                "ui.request_state",
            ),
            side_effects=("ui_window_write",),
            emitted_tokens=(
                "MatterCatalog",
                "IndexedCatalogPage",
                "VisibleCardHydrationBounded",
            ),
            reason=(
                "indexed root/admission/search/filter/activity ordering and "
                "offset/limit selection return visible Matter ids, totals, and "
                "bounded facets before only those ids and bounded display "
                "dependencies are hydrated into cards"
            ),
        ),
        CaseRule(
            case_id="same_revision_equivalent",
            decision="required_localized_projection_published",
            label="required_localized_projection_published",
            writes=(
                "projection.localized_values",
                "projection.locale_registry",
                "projection.equivalence_status",
            ),
            side_effects=("projection_publish",),
            emitted_tokens=("LocalizedProjection", "LocaleRegistry", "MatterCard"),
            reason=(
                "non-empty en and zh-CN values express one semantic revision; "
                "additional locales require complete registered values"
            ),
        ),
        CaseRule(
            case_id="exact_admitted_matter_projection_identity",
            decision="admitted_matter_projection_identity_current",
            label="admitted_matter_projection_identity_current",
            writes=(
                "projection.admitted_matter_id",
                "ui.catalog_page_id_set",
                "ui.selected_matter_id",
            ),
            side_effects=("projection_publish", "ui_window_write"),
            emitted_tokens=(
                "AdmittedMatterProjectionIdentity",
                "MatterCatalog",
            ),
            reason=(
                "cards, child rows, breadcrumbs, coverage relations, details, "
                "locale, and density retain the exact current C6-admitted "
                "matter_id rather than a projection or source-derived alias"
            ),
        ),
        CaseRule(
            case_id="projection_source_or_candidate_without_c6_identity",
            decision="noncanonical_projection_excluded",
            label="noncanonical_projection_excluded",
            emitted_tokens=("NonCanonicalProjectionExcluded", "ProjectionPending"),
            reason=(
                "projection-only, source-only, and candidate rows without one "
                "exact current C6 matter_id stay outside canonical root/child "
                "catalogs and admitted-Matter coverage"
            ),
        ),
        CaseRule(
            case_id="analysis_owned_projection_or_admission_superseded",
            decision="stale_analysis_projection_excluded_pending_rebuild",
            label="stale_analysis_projection_excluded_pending_rebuild",
            writes=(
                "ui.catalog_window",
                "ui.catalog_revision",
                "ui.background_status",
            ),
            side_effects=("ui_window_write",),
            emitted_tokens=(
                "StaleAnalysisProjectionExcluded",
                "ProjectionPending",
                "BackgroundStatus",
            ),
            reason=(
                "a superseded analysis package keeps immutable admission and "
                "projection history but its old title, summary, state, detail, "
                "and evidence view are absent from current catalogs and graphs; "
                "a still-registered hierarchy row may show only a localized "
                "projection-pending placeholder until one active replacement "
                "owner reuses the exact output identity"
            ),
        ),
        CaseRule(
            case_id="first_launch_without_preference",
            decision="english_default_selected",
            label="english_default_selected",
            writes=("ui.selected_locale", "ui.locale_preference", "ui.focus_context"),
            side_effects=("ui_preference_write",),
            emitted_tokens=("LocaleSelection", "MatterCatalog"),
            reason="desktop first launch defaults to English without changing canonical data",
        ),
        CaseRule(
            case_id="select_chinese_same_context",
            decision="locale_selection_applied",
            label="locale_selection_applied",
            writes=("ui.selected_locale", "ui.locale_preference", "ui.focus_context"),
            side_effects=("ui_preference_write",),
            emitted_tokens=("LocaleSelection", "LocalizedProjection"),
            reason="locale changes only display projection and preserves object-browser context",
        ),
        CaseRule(
            case_id="future_locale_complete",
            decision="registered_locale_published",
            label="registered_locale_published",
            writes=(
                "projection.localized_values",
                "projection.locale_registry",
                "projection.equivalence_status",
            ),
            side_effects=("projection_publish",),
            emitted_tokens=("LocaleRegistry", "LocalizedProjection"),
            reason="a future locale is published only after complete semantic-equivalence validation",
        ),
        CaseRule(
            case_id="missing_required_locale",
            decision="localization_gap_blocked",
            label="localization_gap_blocked",
            writes=("projection.equivalence_status",),
            emitted_tokens=("LocalizationGap", "ProjectionPending"),
            reason="missing English or Chinese values block a fresh complete projection",
        ),
        CaseRule(
            case_id="catalog_load_started",
            decision="browser_loading",
            label="browser_loading",
            writes=("ui.request_state", "ui.transport_phase"),
            emitted_tokens=("BrowserLoading", "BackgroundStatus"),
            reason=(
                "a first or superseding catalog request immediately enters loading "
                "without publishing catalog or coverage counts"
            ),
        ),
        CaseRule(
            case_id="catalog_processing_current",
            decision="browser_processing",
            label="browser_processing",
            writes=(
                "ui.request_state",
                "ui.transport_phase",
                "ui.background_status",
            ),
            emitted_tokens=("BrowserProcessing", "BackgroundStatus", "ProjectionPending"),
            reason=(
                "a successful transport with unfinished semantic or hierarchy "
                "owners is processing, not empty and not current-ready"
            ),
        ),
        CaseRule(
            case_id="matter_catalog_current",
            decision="bounded_matter_catalog_rendered",
            label="bounded_matter_catalog_rendered",
            writes=(
                "ui.catalog_window",
                "ui.catalog_cursor",
                "ui.catalog_revision",
                "projection.hierarchy_revision",
                "ui.coverage_summary",
                "ui.background_status",
                "ui.request_state",
                "ui.transport_phase",
                "ui.last_successful_catalog_revision",
                "ui.transport_retry_attempt",
                "ui.transport_retry_due_at",
            ),
            side_effects=("ui_window_write", "transport_reconnect_cancel"),
            emitted_tokens=(
                "MatterCatalog",
                "RootMatterCatalog",
                "MatterCard",
                "CoverageSummary",
                "BackgroundStatus",
                "HierarchyProjectionCurrent",
                "BrowserReady",
            ),
            reason=(
                "one bounded current catalog window renders exactly one card for "
                "each visible root Matter; child Matters remain reachable through "
                "their root/detail path and are not duplicated in the default catalog; "
                "after search and filters, cards are ordered by last material clue "
                "descending with a deterministic stable tie break"
            ),
        ),
        CaseRule(
            case_id="material_clue_summary_activity_current",
            decision="summary_and_activity_order_atomically_published",
            label="summary_and_activity_order_atomically_published",
            writes=(
                "projection.localized_values",
                "projection.material_clue_revision",
                "projection.summary_revision",
                "projection.activity_order_revision",
                "ui.catalog_window",
                "ui.catalog_revision",
            ),
            side_effects=("projection_publish", "activity_projection_publish"),
            emitted_tokens=(
                "MaterialClue",
                "ActivityOrderCurrent",
                "SummaryClueAtomicProjection",
                "MatterCard",
            ),
            reason=(
                "one current material clue updates the affected Matter's bilingual "
                "summary, latest-clue timestamp, activity ordering, and catalog "
                "revision as one publish; a material child clue propagates a derived "
                "ancestor activity revision and summary refresh before publication"
            ),
        ),
        CaseRule(
            case_id="evidence_bound_parent_narrative_current",
            decision="bilingual_parent_narrative_atomically_published",
            label="bilingual_parent_narrative_atomically_published",
            writes=(
                "projection.localized_values",
                "projection.parent_narrative_revision",
                "projection.parent_narrative_scope_revision",
                "projection.parent_narrative_child_projection_revisions",
                "projection.parent_narrative_evidence_revisions",
                "projection.parent_narrative_refresh_status",
            ),
            side_effects=("projection_publish",),
            emitted_tokens=(
                "LocalizedProjection",
                "ParentNarrativeCurrent",
                "ParentNarrativeWriteBoundaryPreserved",
                "HumanNarrative",
            ),
            reason=(
                "one bilingual parent overview tells a human what the Matter is, "
                "what has happened, where it stands, and what is next, while "
                "binding the complete current child/projection/evidence scope; it "
                "does not expose evidence-counting, coverage, model-owner, or "
                "internal-review language and may update only the overview; "
                "title, lifecycle, activity recency/order, and hero identity remain unchanged"
            ),
        ),
        CaseRule(
            case_id="parent_narrative_bound_input_changed",
            decision="stale_parent_narrative_retained_and_refresh_queued",
            label="stale_parent_narrative_retained_and_refresh_queued",
            writes=("projection.parent_narrative_refresh_status",),
            side_effects=("projection_publish",),
            emitted_tokens=("ParentNarrativeRefreshQueued",),
            reason=(
                "a changed clue, hierarchy, child projection, canonicalization, "
                "or evidence revision keeps the last overview visibly stale and "
                "queues its original AI owner instead of copying the latest child summary"
            ),
        ),
        CaseRule(
            case_id="nonmaterial_processing_update",
            decision="background_status_only_no_activity_bubble",
            label="background_status_only_no_activity_bubble",
            writes=("ui.background_status",),
            emitted_tokens=("BackgroundStatus",),
            reason=(
                "scan, retry, rephrasing, classification-only, image-generation, "
                "or projection-only changes may update worker status but do not "
                "change a Matter summary, latest meaningful clue, or activity order"
            ),
        ),
        CaseRule(
            case_id="matter_card_summary_free_current",
            decision="localized_summary_free_root_card_rendered",
            label="localized_summary_free_root_card_rendered",
            writes=("projection.localized_values", "ui.catalog_window"),
            side_effects=("projection_publish", "ui_window_write"),
            emitted_tokens=("LocalizedProjection", "MatterCard"),
            reason=(
                "each root card renders only the current localized title, status, "
                "one day-only YYYY-MM-DD Start date, and Hero; status uses the "
                "same calm metadata typography as Start with no capsule, pill, "
                "chip, fill, border, or rounded container; Standard also retains event/person/"
                "source metrics while Compact gives its remaining body to the Hero; the "
                "summary remains durable for search and the Overview but neither "
                "Standard nor Compact renders a card summary or key-person row"
            ),
        ),
        CaseRule(
            case_id="matter_card_same_result_owner_binding_current",
            decision="same_result_matter_title_and_detail_summary_owner_joined",
            label="same_result_matter_title_and_detail_summary_owner_joined",
            writes=(
                "projection.localized_values",
                "projection.equivalence_status",
                "ui.catalog_window",
            ),
            side_effects=("projection_publish", "ui_window_write"),
            emitted_tokens=("LocalizedProjection", "MatterCard"),
            reason=(
                "when a finding does not declare a Matter id, its card title and "
                "detail-only summary bind only to the unique current C6 admission owner "
                "from the same accepted result and semantic revision; source "
                "overlap with another Matter never selects the projection owner"
            ),
        ),
        CaseRule(
            case_id="catalog_honest_empty_current",
            decision="honest_empty_catalog_rendered",
            label="honest_empty_catalog_rendered",
            writes=(
                "ui.catalog_window",
                "ui.catalog_cursor",
                "ui.catalog_revision",
                "ui.coverage_summary",
                "ui.request_state",
                "ui.transport_phase",
                "ui.last_successful_catalog_revision",
                "ui.transport_retry_attempt",
                "ui.transport_retry_due_at",
            ),
            side_effects=("ui_window_write", "transport_reconnect_cancel"),
            emitted_tokens=(
                "MatterCatalog",
                "CoverageSummary",
                "HonestEmptyCatalog",
            ),
            reason=(
                "zero Matters is honest only after a current successful unfiltered "
                "catalog and coverage response explicitly reports zero"
            ),
        ),
        CaseRule(
            case_id="catalog_no_filter_results_current",
            decision="no_filter_results_rendered",
            label="no_filter_results_rendered",
            writes=(
                "ui.catalog_window",
                "ui.catalog_cursor",
                "ui.catalog_revision",
                "ui.query",
                "ui.filter_state",
                "ui.request_state",
                "ui.transport_phase",
                "ui.last_successful_catalog_revision",
                "ui.transport_retry_attempt",
                "ui.transport_retry_due_at",
            ),
            side_effects=("ui_window_write", "transport_reconnect_cancel"),
            emitted_tokens=("MatterCatalog", "NoFilterResults"),
            reason=(
                "a current successful query may return no matching cards while "
                "preserving the underlying catalog and coverage truth"
            ),
        ),
        CaseRule(
            case_id="matter_coverage_relation_index_current",
            decision="bounded_indexed_card_relation_lookup",
            label="bounded_indexed_card_relation_lookup",
            writes=("ui.catalog_window", "ui.catalog_revision"),
            side_effects=("ui_window_write",),
            emitted_tokens=("MatterCatalog", "MatterCard", "MatterDetail"),
            reason=(
                "catalog and detail readers resolve every visible Matter's "
                "coverage relations through one current private index batch "
                "instead of transferring and reparsing the full ledger per card"
            ),
        ),
        CaseRule(
            case_id="catalog_search_or_filter_changed",
            decision="catalog_query_applied_preserving_context",
            label="catalog_query_applied_preserving_context",
            writes=(
                "ui.query",
                "ui.filter_state",
                "ui.catalog_window",
                "ui.catalog_cursor",
                "ui.browser_scroll_anchor",
                "ui.focus_context",
            ),
            side_effects=("ui_window_write",),
            emitted_tokens=("MatterCatalog",),
            reason=(
                "search/filter updates a bounded window while preserving density, "
                "locale, selected Matter, restorable scroll context, and the "
                "latest-material-clue ordering inside the result set"
            ),
        ),
        CaseRule(
            case_id="child_search_result_with_path",
            decision="owning_root_opened_and_descendant_focused_in_graph",
            label="owning_root_opened_and_descendant_focused_in_graph",
            writes=(
                "projection.hierarchy_revision",
                "ui.query",
                "ui.catalog_window",
                "ui.selected_matter_id",
                "ui.detail_section",
                "ui.situation_graph_view_state",
                "ui.focus_context",
            ),
            side_effects=("ui_window_write",),
            emitted_tokens=(
                "MatterCatalog",
                "SituationGraphView",
                "HierarchyUIReachable",
            ),
            reason=(
                "search may surface a matching child Matter only with its current "
                "owning-root path and child role; selecting it opens the owning "
                "root at Sub-matters and focuses the matching graph node instead "
                "of turning the descendant into a catalog card or full detail"
            ),
        ),
        CaseRule(
            case_id="density_switched",
            decision="density_preference_applied",
            label="density_preference_applied",
            writes=("ui.card_density", "ui.focus_context", "ui.browser_scroll_anchor"),
            side_effects=("ui_preference_write",),
            emitted_tokens=("DensitySelection", "MatterCard"),
            reason=(
                "Standard/Compact changes geometry only; Matter order, status, "
                "same recognizable root Hero, locale, filters, selection, and "
                "responsive mode remain unchanged; Compact removes the three "
                "secondary metrics and expands the image instead of hiding it"
            ),
        ),
        CaseRule(
            case_id="viewport_changed",
            decision="responsive_viewport_applied",
            label="responsive_viewport_applied",
            writes=("ui.viewport_mode",),
            emitted_tokens=("MatterCatalog",),
            reason="responsive columns change independently of persisted density",
        ),
        CaseRule(
            case_id="single_card_catalog",
            decision="single_card_top_aligned",
            label="single_card_top_aligned",
            writes=("ui.catalog_window",),
            emitted_tokens=("MatterCard",),
            reason="one card remains top-aligned and never stretches or vertically centers",
        ),
        CaseRule(
            case_id="matter_detail_opened",
            decision="matter_detail_rendered",
            label="matter_detail_rendered",
            writes=(
                "ui.selected_matter_id",
                "ui.detail_section",
                "ui.detail_sections",
                "ui.browser_scroll_anchor",
                "ui.focus_context",
                "ui.request_state",
            ),
            side_effects=("ui_window_write",),
            emitted_tokens=(
                "MatterDetail",
                "MatterDetailEightSections",
                "OverviewMinimalProjection",
            ),
            reason=(
                "detail exposes exactly Overview, Sub-matters, Timeline, People, "
                "Related Matters, Files and information, Images, and AI supplemental "
                "information; Overview contains only the vertically balanced Hero, "
                "human narrative, lifecycle state, and Start date, with no source, "
                "evidence, action, or open-loop panels; evidence/history stay "
                "on-demand inside Files and information"
            ),
        ),
        CaseRule(
            case_id="files_information_table_current",
            decision="bounded_files_information_rendered",
            label="bounded_files_information_rendered",
            writes=(
                "ui.detail_section",
                "ui.files_information_window",
                "ui.source_group_window",
                "ui.request_state",
            ),
            side_effects=("ui_window_write",),
            emitted_tokens=(
                "FilesInformationTable",
                "FilesInformationReadableTypography",
            ),
            reason=(
                "related files and information use one flat table; each row shows "
                "its contained folder, Gmail thread, Codex project/workspace, or "
                "provider in a source-group column together with human label, "
                "source type, privacy-safe location, "
                "day-only source observed/received/modified time while private "
                "canonical precision is retained, content summary, "
                "availability, and modality, with no repeated group subheader, "
                "absolute path, or internal identifier; body text is subordinate "
                "to the table header, wraps inside its column, and never forces "
                "horizontal overflow merely because source titles are long"
            ),
        ),
        CaseRule(
            case_id="images_gallery_current",
            decision="operable_images_gallery_rendered",
            label="operable_images_gallery_rendered",
            writes=(
                "ui.detail_section",
                "ui.image_gallery_state",
                "ui.focus_context",
            ),
            side_effects=("ui_window_write",),
            emitted_tokens=("ImagesGallery", "GalleryViewState"),
            reason=(
                "only authorized current real photos or meaningful visual images "
                "enter the gallery; email, TXT, document, form, and text-page "
                "screenshots remain Files and information derivatives; admitted "
                "thumbnails share one selected image and support "
                "0.5x-5x zoom, reset, wheel zoom, enlarged-image pan, and keyboard "
                "navigation without a canonical write"
            ),
        ),
        CaseRule(
            case_id="ai_supplemental_information_current",
            decision="labeled_supplemental_information_rendered",
            label="labeled_supplemental_information_rendered",
            writes=(
                "projection.supplemental_information",
                "projection.supplemental_information_revision",
                "ui.detail_section",
                "ui.supplemental_information_state",
            ),
            side_effects=("supplemental_information_publish", "ui_window_write"),
            emitted_tokens=("AISupplementalInformation",),
            reason=(
                "the eighth section renders current bilingual AI-added background, "
                "implications, preparation, and time-zone/jurisdiction normalization "
                "with evidence links where available and an explicit distinction "
                "between sourced facts and AI interpretation"
            ),
        ),
        CaseRule(
            case_id="ai_supplemental_information_unavailable",
            decision="supplemental_information_unavailable_rendered",
            label="supplemental_information_unavailable_rendered",
            writes=(
                "projection.supplemental_information_revision",
                "ui.detail_section",
                "ui.supplemental_information_state",
            ),
            side_effects=("supplemental_information_publish", "ui_window_write"),
            emitted_tokens=("SupplementalInformationUnavailable",),
            reason=(
                "zero current supplemental items is pending or unavailable, never "
                "current; the eighth section remains present with a bounded "
                "explanation and never invents research"
            ),
        ),
        CaseRule(
            case_id="eligible_root_supplemental_research_queued",
            decision="supplemental_research_pending_rendered",
            label="supplemental_research_pending_rendered",
            writes=(
                "projection.supplemental_information_revision",
                "projection.supplemental_information_status",
                "projection.supplemental_information_disposition",
                "projection.supplemental_research_package_id",
                "projection.supplemental_provider_gate",
                "ui.supplemental_information_state",
            ),
            side_effects=(
                "supplemental_information_publish",
                "supplemental_research_queue",
            ),
            emitted_tokens=(
                "SupplementalResearchQueued",
                "SupplementalInformationUnavailable",
            ),
            reason=(
                "each admitted root Matter with one current equivalent bilingual "
                "projection and zero accepted supplemental items receives exactly "
                "one idempotent A1 ResearchGuard package; pending, unavailable, or "
                "blocked stays visible until the original C12 owner accepts a "
                "current bilingual item"
            ),
        ),
        CaseRule(
            case_id="descendant_supplemental_not_applicable",
            decision="supplemental_not_applicable_rendered",
            label="supplemental_not_applicable_rendered",
            writes=(
                "projection.supplemental_information_revision",
                "projection.supplemental_information_status",
                "projection.supplemental_information_disposition",
                "projection.supplemental_provider_gate",
                "ui.supplemental_information_state",
            ),
            side_effects=("supplemental_information_publish",),
            emitted_tokens=("SupplementalNotApplicable",),
            reason=(
                "a descendant Matter inherits the root research context and records "
                "one explicit not_applicable disposition without creating a "
                "duplicate ResearchGuard request"
            ),
        ),
        CaseRule(
            case_id="future_world_model_prediction_current",
            decision="future_prediction_labeled_world_model_only",
            label="future_prediction_labeled_world_model_only",
            writes=(
                "projection.supplemental_information",
                "ui.supplemental_information_state",
            ),
            side_effects=("supplemental_information_publish", "ui_window_write"),
            emitted_tokens=("AISupplementalInformation",),
            reason=(
                "a future AI prediction appears only in AI supplemental information "
                "or the World Model with uncertainty, verification horizon, expiry, "
                "and predicted status; it never appears as an occurred timeline "
                "event or current lifecycle state"
            ),
        ),
        CaseRule(
            case_id="situation_graph_current",
            decision="bounded_interactive_matter_hierarchy_rendered",
            label="bounded_interactive_matter_hierarchy_rendered",
            writes=(
                "projection.hierarchy_revision",
                "ui.situation_graph_view_state",
                "ui.matter_hierarchy_projection",
                "ui.situation_graph_continuation",
                "ui.detail_section",
                "ui.request_state",
            ),
            side_effects=("ui_window_write",),
            emitted_tokens=(
                "SituationGraphView",
                "SituationGraphContinuation",
                "HierarchyProjectionCurrent",
                "HierarchyUIReachable",
                "MatterOnlyHierarchyGraph",
            ),
            reason=(
                "Sub-matters renders only the current multi-depth Matter hierarchy "
                "with primary containment plus typed Matter-to-Matter secondary "
                "relations, pan, zoom, reset, minimap, and keyboard operation; "
                "Matter nodes have no per-node collapse control, while WorkItems, "
                "Events, facts, waits, and inferences stay inside the selected "
                "Matter quick view and an honest continuation marks deeper work"
            ),
        ),
        CaseRule(
            case_id="descendant_graph_node_opened",
            decision="single_layer_node_quick_view_rendered",
            label="single_layer_node_quick_view_rendered",
            writes=(
                "ui.node_quick_view_state",
                "ui.node_quick_view_facts",
                "ui.node_quick_view_source_groups",
                "ui.source_group_window",
                "ui.focus_context",
            ),
            side_effects=("ui_window_write",),
            emitted_tokens=(
                "NodeQuickView",
                "NodeQuickViewFacts",
                "SourceGroupWindow",
            ),
            reason=(
                "clicking any descendant Matter updates the same one-layer small "
                "dialog over the root detail; its first region contains a human "
                "summary/current state plus itemized facts, Events, WorkItems, "
                "waits, and explicitly labeled historical inferences owned by "
                "that Matter, and its second region contains only that Matter's "
                "flat files/information-location list with a SourceGroup field and "
                "uses the exact current lifecycle/outcome state basis, collapses "
                "historical SourceVersions into one logical source row, omits "
                "internal unknown coverage vocabulary, renders ordinary source time "
                "with day precision only, and never opens another full "
                "Matter detail, page, card, graph, modal, or Hero"
            ),
        ),
        CaseRule(
            case_id="historical_inferred_completion_opened",
            decision="historical_inference_state_basis_rendered",
            label="historical_inference_state_basis_rendered",
            writes=(
                "projection.state_basis_modality",
                "projection.state_basis_scope",
                "ui.node_quick_view_state",
            ),
            side_effects=("ui_window_write",),
            emitted_tokens=("NodeQuickView", "HistoricalInferenceStateBasis"),
            reason=(
                "a completed Matter whose current C9 outcome was inferred only "
                "to bridge a past evidence gap is labeled AI historical inference "
                "in both locales instead of being mislabeled reported"
            ),
        ),
        CaseRule(
            case_id="different_descendant_selected_while_quick_view_open",
            decision="existing_quick_view_content_replaced",
            label="existing_quick_view_content_replaced",
            writes=(
                "ui.node_quick_view_state",
                "ui.node_quick_view_source_groups",
                "ui.source_group_window",
                "ui.focus_context",
            ),
            side_effects=("ui_window_write",),
            emitted_tokens=("NodeQuickView", "SourceGroupWindow"),
            reason=(
                "a new node selection replaces the contents of the already open "
                "quick view and never increases overlay depth"
            ),
        ),
        CaseRule(
            case_id="hierarchy_reparented_projection",
            decision="situation_graph_and_quick_view_rebased",
            label="situation_graph_and_quick_view_rebased",
            writes=(
                "projection.hierarchy_revision",
                "ui.situation_graph_view_state",
                "ui.situation_graph_continuation",
                "ui.node_quick_view_state",
                "ui.request_state",
            ),
            side_effects=("ui_window_write",),
            emitted_tokens=(
                "SituationGraphView",
                "NodeQuickView",
                "HierarchyProjectionCurrent",
            ),
            reason=(
                "after C10 joins the old and new ancestor invalidations, C12 "
                "rebases the graph and any open node quick view to the same "
                "current C6 revision"
            ),
        ),
        CaseRule(
            case_id="hierarchy_depth_pending",
            decision="bounded_hierarchy_pending_visible",
            label="bounded_hierarchy_pending_visible",
            writes=(
                "projection.hierarchy_revision",
                "ui.situation_graph_view_state",
                "ui.situation_graph_continuation",
                "ui.background_status",
            ),
            emitted_tokens=(
                "HierarchyDepthPendingVisible",
                "ProjectionPending",
                "BackgroundStatus",
            ),
            reason=(
                "known modeled children remain browseable while unmodeled deeper "
                "branches are explicitly pending and never labeled complete"
            ),
        ),
        CaseRule(
            case_id="descendant_event_in_parent_timeline",
            decision="descendant_event_projected_once_with_child_label",
            label="descendant_event_projected_once_with_child_label",
            writes=("projection.localized_values", "ui.detail_section"),
            side_effects=("projection_publish",),
            emitted_tokens=("HumanReadableTimeline", "HierarchyProjectionCurrent"),
            reason=(
                "a significant descendant Event may appear once in the parent "
                "timeline with its child label, logical_event_key, and current "
                "revision; superseded source or wording revisions do not create "
                "additional entries, and "
                "ordinary low-signal child events remain inside the child detail"
            ),
        ),
        CaseRule(
            case_id="logical_event_revisions_current",
            decision="one_current_logical_event_projected",
            label="one_current_logical_event_projected",
            writes=("projection.localized_values", "ui.detail_section"),
            side_effects=("projection_publish",),
            emitted_tokens=("HumanReadableTimeline", "LogicalTimelineProjection"),
            reason=(
                "all source, inference, and wording revisions that share one "
                "logical_event_key project exactly one current human timeline "
                "entry; superseded revisions remain available only in evidence history"
            ),
        ),
        CaseRule(
            case_id="human_readable_timeline",
            decision="localized_timeline_rendered",
            label="localized_timeline_rendered",
            writes=("projection.localized_values", "ui.detail_section"),
            side_effects=("projection_publish",),
            emitted_tokens=("HumanReadableTimeline",),
            reason=(
                "localized sentences distinguish record time from occurred time, "
                "badge planned/reported/observed/inferred, and retain conflicts"
            ),
        ),
        CaseRule(
            case_id="generated_hero_current",
            decision="generated_hero_projection_current",
            label="generated_hero_projection_current",
            writes=(
                "projection.generated_hero_asset",
                "projection.generated_hero_revision",
                "projection.generated_hero_brief_fingerprint",
                "projection.generated_hero_safety_disposition",
                "projection.generated_hero_currentness",
                "projection.generated_hero_localized_alt",
                "projection.generated_hero_status",
                "ui.catalog_window",
            ),
            side_effects=("generated_hero_projection_publish", "ui_window_write"),
            emitted_tokens=("GeneratedHeroProjection", "MatterCard"),
            reason=(
                "C12 publishes the one current C11-generated photorealistic "
                "presentation artifact only for a root Matter using the same "
                "recognizable image in every locale and both densities with "
                "bilingual alt text; the Matter-specific setting, equipment, "
                "objects, or activity remains recognizable without a caption "
                "and generic people-at-computer imagery is not current; it never "
                "uses a source photo, file preview, "
                "email screenshot, attachment, abstract illustration, 3D render, "
                "collage, text, or logo as a Hero"
            ),
        ),
        CaseRule(
            case_id="descendant_hero_not_applicable",
            decision="descendant_hero_projection_suppressed",
            label="descendant_hero_projection_suppressed",
            writes=("projection.generated_hero_status", "ui.node_quick_view_state"),
            side_effects=("generated_hero_projection_publish", "ui_window_write"),
            emitted_tokens=("DescendantHeroNotApplicable",),
            reason=(
                "child Matters, WorkItems, Events, inferred nodes, sources, and "
                "quick views ignore any legacy Hero token and render no Hero or placeholder"
            ),
        ),
        CaseRule(
            case_id="generated_hero_pending_or_blocked",
            decision="hero_pending_placeholder_visible",
            label="hero_pending_placeholder_visible",
            writes=(
                "projection.generated_hero_revision",
                "projection.generated_hero_status",
                "ui.catalog_window",
            ),
            side_effects=("generated_hero_projection_publish", "ui_window_write"),
            emitted_tokens=("HeroPendingPlaceholder",),
            reason=(
                "only a pending/blocked generation state, including a typed "
                "visual-quality refresh, may show a temporary neutral placeholder; "
                "retry never promotes source evidence as a second hero authority"
            ),
        ),
        CaseRule(
            case_id="desktop_surface_evidence_current",
            decision="required_surface_matrix_verified",
            label="required_surface_matrix_verified",
            writes=(
                "ui.surface_evidence_revision",
                "ui.surface_evidence_status",
            ),
            side_effects=("surface_evidence_write",),
            emitted_tokens=("SurfaceEvidenceCurrent",),
            reason=(
                "current 8766 screenshots and DOM geometry cover 1880x900 and "
                "1440x900, English and Chinese, Standard and Compact, catalog/detail/"
                "gallery/transport states, and contain no clipping, overlap, hidden "
                "labels, duplicate metadata, or unapproved font-size drift"
            ),
        ),
        CaseRule(
            case_id="optional_correction_requested",
            decision="correction_delegated_to_c10",
            label="correction_delegated_to_c10",
            writes=("ui.correction_state",),
            emitted_tokens=("CorrectionEvent", "C10Request"),
            reason=(
                "an explicitly reached on-demand semantic correction delegates to "
                "C10 and is not an ordinary primary section or cover workflow"
            ),
        ),
        CaseRule(
            case_id="background_work_pending_or_blocked",
            decision="background_status_visible_browser_usable",
            label="background_status_visible_browser_usable",
            writes=("ui.background_status", "ui.coverage_summary"),
            emitted_tokens=("BackgroundStatus", "CoverageSummary", "ProjectionPending"),
            reason="one blocked object or provider does not make current catalog objects unusable",
        ),
        CaseRule(
            case_id="coverage_current_with_first_gap_index",
            decision="compact_truthful_coverage_indicator_rendered",
            label="compact_truthful_coverage_indicator_rendered",
            writes=(
                "ui.coverage_summary",
                "ui.coverage_indicator_state",
                "ui.coverage_drilldown",
            ),
            side_effects=("ui_window_write",),
            emitted_tokens=(
                "CoverageSummary",
                "CompactCoverageIndicator",
                "CoverageFirstGapDrilldown",
            ),
            reason=(
                "the catalog header shows one slim dot-and-label indicator rather "
                "than a two-row metric capsule; blue means a current terminal "
                "scan with no first gap, red means a material gap or blocker, and "
                "green means active processing, while its drilldown reads one "
                "materialized first-gap index instead of scanning the full ledger"
            ),
        ),
        CaseRule(
            case_id="lifecycle_visual_projection_current",
            decision="lifecycle_status_and_modality_rendered_separately",
            label="lifecycle_status_and_modality_rendered_separately",
            writes=(
                "projection.lifecycle_visual_state",
                "projection.state_basis_modality",
                "ui.catalog_window",
                "ui.node_quick_view_state",
            ),
            side_effects=("projection_publish", "ui_window_write"),
            emitted_tokens=("LifecycleVisualLanguage", "MatterCard", "NodeQuickView"),
            reason=(
                "planned is green, in progress is red, and completed is blue; "
                "reported, observed, and inferred describe the separate evidence "
                "basis and never replace or duplicate the human lifecycle label"
            ),
        ),
        CaseRule(
            case_id="stale_or_cancelled_response",
            decision="stale_response_discarded",
            label="stale_response_discarded",
            writes=("ui.request_state",),
            emitted_tokens=("ProjectionPending",),
            reason="an older revision, cancelled request, or stale page cannot overwrite current UI state",
        ),
        CaseRule(
            case_id="catalog_timeout_with_prior_content",
            decision="ready_stale_prior_catalog_preserved",
            label="ready_stale_prior_catalog_preserved",
            writes=(
                "ui.request_state",
                "ui.transport_phase",
                "ui.background_status",
                "ui.transport_retry_attempt",
                "ui.transport_retry_due_at",
            ),
            side_effects=("transport_reconnect_schedule",),
            emitted_tokens=(
                "TransportErrorPreserved",
                "BrowserReadyStale",
                "TransportReconnectScheduled",
                "BackgroundStatus",
            ),
            reason=(
                "a timeout after a successful catalog keeps that exact catalog, "
                "coverage, and revision visible as stale while scheduling a bounded "
                "automatic reconnect"
            ),
        ),
        CaseRule(
            case_id="catalog_transport_error_initial",
            decision="transport_error_unknown_counts",
            label="transport_error_unknown_counts",
            writes=(
                "ui.request_state",
                "ui.transport_phase",
                "ui.background_status",
                "ui.transport_retry_attempt",
                "ui.transport_retry_due_at",
            ),
            side_effects=("transport_reconnect_schedule",),
            emitted_tokens=(
                "TransportErrorPreserved",
                "BrowserTransportError",
                "TransportReconnectScheduled",
                "BackgroundStatus",
            ),
            reason=(
                "a failed first request shows localized recovery with unknown "
                "catalog and coverage counts and schedules a bounded automatic "
                "reconnect; it never writes zero or an honest-empty projection"
            ),
        ),
        CaseRule(
            case_id="catalog_transport_recovered",
            decision="automatic_reconnect_restored_ready",
            label="automatic_reconnect_restored_ready",
            writes=(
                "ui.catalog_window",
                "ui.catalog_cursor",
                "ui.catalog_revision",
                "ui.coverage_summary",
                "ui.request_state",
                "ui.transport_phase",
                "ui.last_successful_catalog_revision",
                "ui.transport_retry_attempt",
                "ui.transport_retry_due_at",
            ),
            side_effects=("ui_window_write", "transport_reconnect_cancel"),
            emitted_tokens=(
                "MatterCatalog",
                "CoverageSummary",
                "BrowserReady",
                "TransportRecovered",
            ),
            reason=(
                "the next successful bounded reconnect atomically restores a "
                "current ready projection and cancels the pending retry"
            ),
        ),
        CaseRule(
            case_id="recompute_not_terminal",
            decision="projection_pending",
            label="projection_pending",
            writes=("projection.equivalence_status", "ui.background_status"),
            emitted_tokens=("ProjectionPending", "BackgroundStatus"),
            reason="C12 never publishes a fresh projection before required owner joins are terminal",
        ),
        CaseRule(
            case_id="ui_infers_state",
            decision="ui_inference_rejected",
            label="ui_inference_rejected",
            emitted_tokens=("ProjectionWriteRejected",),
            reason="desktop and browser surfaces cannot infer or write canonical product state",
        ),
        CaseRule(
            case_id="internal_identifier_requested_by_default",
            decision="internal_content_hidden",
            label="internal_content_hidden",
            emitted_tokens=("ExplanationView",),
            reason="paths, message ids, hashes, receipts, tokens, and internal model ids are hidden",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-C12-042-projection-id-becomes-canonical-matter",
            protected_error_class="projection_identity_canonicalization_escape",
            description=(
                "C12 promotes a projection, source, or candidate id into the "
                "canonical root/child catalog without exact C6 admission"
            ),
            protected_harm=(
                "the UI invents phantom hierarchy and admitted coverage or "
                "binds details to an unrelated Matter"
            ),
            case_id="projection_source_or_candidate_without_c6_identity",
            broken_decision="admitted_matter_projection_identity_current",
            broken_writes=(
                "projection.admitted_matter_id",
                "ui.catalog_page_id_set",
                "ui.selected_matter_id",
            ),
            broken_side_effects=("projection_publish",),
            broken_tokens=("MatterCatalog", "RootMatterCatalog"),
        ),
        HazardSpec(
            failure_id="H-C12-048-superseded-analysis-projection-stays-visible",
            protected_error_class="stale_analysis_projection_publication",
            description=(
                "a superseded analysis package remains visible through its old "
                "Matter title, summary, state, detail, or evidence projection"
            ),
            protected_harm=(
                "an invalid historical judgment is presented as current product truth"
            ),
            case_id="analysis_owned_projection_or_admission_superseded",
            broken_decision="stale_analysis_projection_rendered_current",
            broken_writes=(
                "ui.catalog_window",
                "ui.catalog_revision",
                "ui.background_status",
            ),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("MatterCard", "MatterDetail"),
        ),
        HazardSpec(
            failure_id="H-C12-040-latest-child-summary-becomes-parent-overview",
            protected_error_class="parent_narrative_latest_child_substitution",
            description=(
                "the newest child summary is published as the broader parent "
                "overview without the complete current child/evidence bindings"
            ),
            protected_harm=(
                "a multi-part project is presented as though it were only its latest subtask"
            ),
            case_id="evidence_bound_parent_narrative_current",
            broken_decision="latest_child_summary_published_as_parent",
            broken_writes=(
                "projection.localized_values",
                "projection.parent_narrative_revision",
            ),
            broken_side_effects=("projection_publish",),
            broken_tokens=("LocalizedProjection",),
        ),
        HazardSpec(
            failure_id="H-C12-041-parent-narrative-mutates-foreign-authority",
            protected_error_class="parent_narrative_write_scope_escape",
            description=(
                "an AI narrative result changes title, lifecycle, activity "
                "recency/order, or generated-hero identity"
            ),
            protected_harm=(
                "presentation synthesis silently overrides canonical product owners"
            ),
            case_id="evidence_bound_parent_narrative_current",
            broken_decision="parent_narrative_foreign_fields_published",
            broken_writes=(
                "projection.activity_order_revision",
                "projection.generated_hero_revision",
            ),
            broken_side_effects=("projection_publish",),
            broken_tokens=("ParentNarrativeCurrent",),
        ),
        HazardSpec(
            failure_id="H-C12-039-full-catalog-card-materialization-before-page",
            protected_error_class="catalog_query_shape_unbounded_hydration",
            description=(
                "request handling iterates every current projection, hydrates "
                "every relation, constructs every card, and only then applies "
                "offset and limit"
            ),
            protected_harm=(
                "a bounded HTTP/DOM page still performs unbounded private-store "
                "reads and card construction as the catalog grows"
            ),
            case_id="indexed_catalog_page_requested",
            broken_decision="all_cards_built_before_page_slice",
            broken_writes=(
                "ui.catalog_window",
                "ui.catalog_query_plan_revision",
                "ui.catalog_page_id_set",
            ),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("MatterCatalog",),
        ),
        HazardSpec(
            failure_id="H-C12-001-missing-locale-fallback",
            protected_error_class="localized_semantic_fallback",
            description="missing required language silently falls back to another language",
            protected_harm="the UI presents incomplete or divergent meaning as complete",
            case_id="missing_required_locale",
            broken_decision="required_localized_projection_published",
            broken_writes=("projection.localized_values", "projection.equivalence_status"),
            broken_side_effects=("projection_publish",),
            broken_tokens=("LocalizedProjection",),
        ),
        HazardSpec(
            failure_id="H-C12-002-locale-switch-mutates-context",
            protected_error_class="locale_projection_context_loss",
            description="switching locale resets the current object-browser context",
            protected_harm="language selection changes what the user is looking at",
            case_id="select_chinese_same_context",
            broken_decision="locale_switch_restarts_catalog",
            broken_writes=(
                "ui.selected_locale",
                "ui.query",
                "ui.filter_state",
                "ui.selected_matter_id",
            ),
            broken_tokens=("LocaleSelection",),
        ),
        HazardSpec(
            failure_id="H-C12-003-density-changes-semantic-object",
            protected_error_class="density_semantic_drift",
            description="Compact renders a different Matter, state, visual, or ordering",
            protected_harm="display density becomes an alternate product truth",
            case_id="density_switched",
            broken_decision="compact_projection_recomputed",
            broken_writes=("ui.card_density", "ui.catalog_revision"),
            broken_side_effects=("ui_preference_write",),
            broken_tokens=("MatterCard",),
        ),
        HazardSpec(
            failure_id="H-C12-004-single-card-stretches",
            protected_error_class="single_card_geometry_failure",
            description="a one-card catalog stretches or vertically centers the card",
            protected_harm="the reference layout breaks at an important empty-near state",
            case_id="single_card_catalog",
            broken_decision="single_card_stretched",
            broken_writes=("ui.catalog_window",),
            broken_tokens=("MatterCard",),
        ),
        HazardSpec(
            failure_id="H-C12-005-search-resets-context",
            protected_error_class="catalog_query_context_loss",
            description="entering or clearing search resets density, locale, filters, selection, or scroll",
            protected_harm="the user loses their place while browsing modeled objects",
            case_id="catalog_search_or_filter_changed",
            broken_decision="catalog_context_reset",
            broken_writes=(
                "ui.query",
                "ui.card_density",
                "ui.selected_locale",
                "ui.selected_matter_id",
            ),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("MatterCatalog",),
        ),
        HazardSpec(
            failure_id="H-C12-006-stale-response-overwrites-current",
            protected_error_class="stale_projection_overwrite",
            description="an older page or cancelled response overwrites current UI state",
            protected_harm="the browser displays data from the wrong projection revision",
            case_id="stale_or_cancelled_response",
            broken_decision="stale_response_rendered",
            broken_writes=("ui.catalog_window", "ui.catalog_revision"),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("MatterCatalog",),
        ),
        HazardSpec(
            failure_id="H-C12-007-early-projection",
            protected_error_class="nonterminal_owner_projection",
            description="C12 publishes fresh content before required owner joins terminate",
            protected_harm="stale or partial canonical state looks current",
            case_id="recompute_not_terminal",
            broken_decision="required_localized_projection_published",
            broken_writes=("projection.localized_values", "projection.equivalence_status"),
            broken_side_effects=("projection_publish",),
            broken_tokens=("LocalizedProjection",),
        ),
        HazardSpec(
            failure_id="H-C12-008-ui-writes-canonical",
            protected_error_class="projection_writer_escape",
            description="the UI directly writes lifecycle, outcome, or relation state",
            protected_harm="a second truth path bypasses the original owner",
            case_id="ui_infers_state",
            broken_decision="canonical_state_written",
            broken_writes=("matter.lifecycle_axes",),
            broken_tokens=("LifecycleState",),
        ),
        HazardSpec(
            failure_id="H-C12-009-real-source-promoted-as-generated-hero",
            protected_error_class="generated_hero_source_boundary_escape",
            description="a photo, attachment, document preview, or email screenshot becomes the card hero",
            protected_harm="private evidence is exposed in the catalog and a second hero authority appears",
            case_id="generated_hero_pending_or_blocked",
            broken_decision="source_image_fallback_rendered",
            broken_writes=("projection.generated_hero_asset", "ui.catalog_window"),
            broken_side_effects=("generated_hero_projection_publish", "ui_window_write"),
            broken_tokens=("GeneratedHeroProjection",),
        ),
        HazardSpec(
            failure_id="H-C12-010-correction-writes-directly",
            protected_error_class="correction_owner_bypass",
            description="an optional correction directly patches the current projection",
            protected_harm="canonical data and other projections remain inconsistent",
            case_id="optional_correction_requested",
            broken_decision="projection_patched_directly",
            broken_writes=("projection.localized_values",),
            broken_side_effects=("projection_publish",),
            broken_tokens=("LocalizedProjection",),
        ),
        HazardSpec(
            failure_id="H-C12-011-internal-data-shown",
            protected_error_class="private_internal_surface_leak",
            description="paths, message ids, hashes, tokens, or receipts appear by default",
            protected_harm="private implementation identity leaks into the product surface",
            case_id="internal_identifier_requested_by_default",
            broken_decision="internal_content_rendered",
            broken_tokens=("InternalIdentifier",),
        ),
        HazardSpec(
            failure_id="H-C12-012-card-repeats-full-coverage-ledger-scan",
            protected_error_class="object_browser_coverage_relation_amplification",
            description=(
                "each catalog card and related-Matter candidate transfers and "
                "parses the entire private ObjectCoverageLedger"
            ),
            protected_harm=(
                "ordinary catalog and detail reads scale as cards times covered "
                "objects and become unusable after a real first-run inventory"
            ),
            case_id="matter_coverage_relation_index_current",
            broken_decision="bounded_matter_catalog_rendered",
            broken_writes=("ui.catalog_window", "ui.catalog_revision"),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("MatterCatalog", "MatterCard"),
        ),
        HazardSpec(
            failure_id="H-C12-013-child-duplicated-as-root-card",
            protected_error_class="root_catalog_hierarchy_duplication",
            description="a child Matter is also rendered as a default root catalog card",
            protected_harm="one semantic Matter appears twice and root counts become false",
            case_id="matter_catalog_current",
            broken_decision="bounded_matter_catalog_rendered",
            broken_writes=("ui.catalog_window", "projection.hierarchy_revision"),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("MatterCatalog", "MatterCard"),
        ),
        HazardSpec(
            failure_id="H-C12-014-child-opens-nested-modal",
            protected_error_class="descendant_recursive_detail_stack",
            description="opening a descendant creates another full detail, page, graph, card, modal, or Hero",
            protected_harm="the object browser becomes an unbounded event-inside-event stack",
            case_id="descendant_graph_node_opened",
            broken_decision="nested_descendant_detail_opened",
            broken_writes=("ui.node_quick_view_state", "ui.focus_context"),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("NodeQuickView",),
        ),
        HazardSpec(
            failure_id="H-C12-015-reparent-keeps-stale-path",
            protected_error_class="hierarchy_navigation_stale_revision",
            description="graph or quick view retains the old parent after reparenting",
            protected_harm="the visible graph displays a containment path no longer licensed by C6",
            case_id="hierarchy_reparented_projection",
            broken_decision="old_graph_parent_retained",
            broken_writes=(
                "ui.situation_graph_view_state",
                "ui.node_quick_view_state",
                "projection.hierarchy_revision",
            ),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("SituationGraphView", "NodeQuickView"),
        ),
        HazardSpec(
            failure_id="H-C12-016-depth-pending-shown-complete",
            protected_error_class="hierarchy_depth_projection_false_complete",
            description="unmodeled deeper branches are displayed as a complete hierarchy",
            protected_harm="the user cannot distinguish bounded current work from exhaustive modeling",
            case_id="hierarchy_depth_pending",
            broken_decision="hierarchy_projection_complete",
            broken_writes=("ui.background_status", "ui.situation_graph_continuation"),
            broken_tokens=("HierarchyProjectionCurrent",),
        ),
        HazardSpec(
            failure_id="H-C12-017-density-changes-hierarchy-revision",
            protected_error_class="density_hierarchy_semantic_drift",
            description="Standard and Compact use different hierarchy revisions or child counts",
            protected_harm="display density becomes a second hierarchy truth",
            case_id="density_switched",
            broken_decision="compact_projection_recomputed",
            broken_writes=("ui.card_density", "projection.hierarchy_revision"),
            broken_side_effects=("ui_preference_write",),
            broken_tokens=("MatterCard", "HierarchyProjectionCurrent"),
        ),
        HazardSpec(
            failure_id="H-C12-018-child-not-ui-reachable",
            protected_error_class="modeled_child_ui_orphan",
            description="a current child Matter has no reachable graph node or quick view",
            protected_harm="modeled user content exists but cannot be reviewed",
            case_id="situation_graph_current",
            broken_decision="descendant_graph_node_hidden",
            broken_writes=("ui.situation_graph_view_state",),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("HierarchyProjectionCurrent",),
        ),
        HazardSpec(
            failure_id="H-C12-019-descendant-event-duplicated",
            protected_error_class="hierarchy_timeline_event_duplication",
            description="one descendant Event appears multiple times in the parent timeline",
            protected_harm="the timeline overstates activity and loses canonical Event identity",
            case_id="descendant_event_in_parent_timeline",
            broken_decision="descendant_event_projected_per_membership",
            broken_writes=("projection.localized_values", "ui.detail_section"),
            broken_side_effects=("projection_publish",),
            broken_tokens=("HumanReadableTimeline",),
        ),
        HazardSpec(
            failure_id="H-C12-020-child-search-hit-looks-like-root",
            protected_error_class="hierarchy_search_context_loss",
            description="a child search result is rendered as an unqualified root card",
            protected_harm="search changes hierarchy meaning and inflates the apparent root catalog",
            case_id="child_search_result_with_path",
            broken_decision="bounded_matter_catalog_rendered",
            broken_writes=("ui.catalog_window", "ui.situation_graph_view_state"),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("MatterCard",),
        ),
        HazardSpec(
            failure_id="H-C12-021-detail-navigation-not-eight",
            protected_error_class="detail_primary_section_sprawl",
            description=(
                "the detail reader has fewer or more than Overview, Sub-matters, "
                "Timeline, People, Related Matters, Files and information, Images, "
                "and AI supplemental information"
            ),
            protected_harm="the object reader becomes an internal workflow console instead of a human Matter browser",
            case_id="matter_detail_opened",
            broken_decision="matter_detail_rendered",
            broken_writes=("ui.detail_sections",),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("MatterDetailEightSections",),
        ),
        HazardSpec(
            failure_id="H-C12-022-gallery-behavior-missing",
            protected_error_class="related_image_inoperable",
            description="Images is a label or static cover without thumbnail, zoom, pan, reset, and keyboard behavior",
            protected_harm="the user cannot inspect the visual evidence that made a Matter recognizable",
            case_id="images_gallery_current",
            broken_decision="static_image_rendered",
            broken_writes=("ui.image_gallery_state",),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("ImagesGallery", "GalleryViewState"),
        ),
        HazardSpec(
            failure_id="H-C12-023-files-information-unbounded-or-internal",
            protected_error_class="files_information_projection_leak",
            description="Files and information materializes an unbounded private source list or internal identities",
            protected_harm="ordinary browsing becomes slow and leaks machine or connector details",
            case_id="files_information_table_current",
            broken_decision="unbounded_internal_source_table_rendered",
            broken_writes=("ui.files_information_window",),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("InternalIdentifier",),
        ),
        HazardSpec(
            failure_id="H-C12-024-transport-error-becomes-empty",
            protected_error_class="fetch_failure_false_empty",
            description=(
                "the observed Failed to fetch request renders zero Matters and "
                "zero coverage"
            ),
            protected_harm="a transport defect is misreported as absence of modeled user activity",
            case_id="catalog_transport_error_initial",
            broken_decision="honest_empty_catalog",
            broken_writes=("ui.catalog_window", "ui.coverage_summary"),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("MatterCatalog", "CoverageSummary"),
        ),
        HazardSpec(
            failure_id="H-C12-025-timeout-erases-prior-catalog",
            protected_error_class="timeout_stale_catalog_erasure",
            description="a refresh timeout erases the last successful cards and counts",
            protected_harm="recoverable current knowledge disappears and looks globally absent",
            case_id="catalog_timeout_with_prior_content",
            broken_decision="transport_error_unknown_counts",
            broken_writes=(
                "ui.catalog_window",
                "ui.coverage_summary",
                "ui.transport_phase",
            ),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("BrowserTransportError",),
        ),
        HazardSpec(
            failure_id="H-C12-026-filter-zero-becomes-global-empty",
            protected_error_class="filter_zero_global_empty_conflation",
            description="a successful zero-result filter is rendered as an empty whole catalog",
            protected_harm="the user is told no modeled Matters exist when only the filter matched none",
            case_id="catalog_no_filter_results_current",
            broken_decision="honest_empty_catalog_rendered",
            broken_writes=(
                "ui.catalog_window",
                "ui.coverage_summary",
                "ui.transport_phase",
            ),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("HonestEmptyCatalog",),
        ),
        HazardSpec(
            failure_id="H-C12-027-auto-reconnect-stuck",
            protected_error_class="transport_reconnect_liveness_failure",
            description="a successful automatic reconnect leaves the browser in transport error",
            protected_harm="the UI remains failed after transport has recovered",
            case_id="catalog_transport_recovered",
            broken_decision="transport_error_auto_reconnect_stuck",
            broken_writes=(
                "ui.request_state",
                "ui.transport_phase",
                "ui.transport_retry_attempt",
                "ui.transport_retry_due_at",
            ),
            broken_side_effects=("transport_reconnect_schedule",),
            broken_tokens=("BrowserTransportError", "TransportReconnectScheduled"),
        ),
        HazardSpec(
            failure_id="H-C12-028-summary-promoted-to-card-title",
            protected_error_class="matter_card_summary_leak",
            description=(
                "a localized summary or key-person row is rendered inside a "
                "Standard or Compact root catalog card"
            ),
            protected_harm=(
                "the image is obscured and the catalog becomes harder to scan"
            ),
            case_id="matter_card_summary_free_current",
            broken_decision="card_summary_rendered",
            broken_writes=("projection.localized_values", "ui.catalog_window"),
            broken_side_effects=("projection_publish", "ui_window_write"),
            broken_tokens=("MatterCard",),
        ),
        HazardSpec(
            failure_id="H-C12-029-summary-bound-to-foreign-matter",
            protected_error_class="cross_matter_projection_owner_mismatch",
            description=(
                "a bounded summary is projected onto an older Matter merely "
                "because that Matter shares a source revision"
            ),
            protected_harm=(
                "one card receives another Matter's summary while the newly "
                "admitted Matter loses its current projection"
            ),
            case_id="matter_card_same_result_owner_binding_current",
            broken_decision="foreign_source_overlap_matter_selected",
            broken_writes=(
                "projection.localized_values",
                "projection.equivalence_status",
                "ui.catalog_window",
            ),
            broken_side_effects=("projection_publish", "ui_window_write"),
            broken_tokens=("MatterCard",),
        ),
        HazardSpec(
            failure_id="H-C12-030-catalog-not-sorted-by-latest-material-clue",
            protected_error_class="activity_order_wrong_authority",
            description="catalog order follows start time, scan time, title, or raw update time",
            protected_harm="recently progressing Matters do not bubble to the front",
            case_id="material_clue_summary_activity_current",
            broken_decision="bounded_matter_catalog_rendered",
            broken_writes=("projection.activity_order_revision", "ui.catalog_window"),
            broken_side_effects=("activity_projection_publish", "ui_window_write"),
            broken_tokens=("ActivityOrderCurrent",),
        ),
        HazardSpec(
            failure_id="H-C12-031-nonmaterial-processing-bubbles-matter",
            protected_error_class="processing_activity_false_signal",
            description="scan, retry, translation, summary rephrasing, or hero generation changes activity order",
            protected_harm="background maintenance looks like a new real-world development",
            case_id="nonmaterial_processing_update",
            broken_decision="summary_and_activity_order_atomically_published",
            broken_writes=("projection.activity_order_revision", "ui.catalog_window"),
            broken_side_effects=("activity_projection_publish",),
            broken_tokens=("ActivityOrderCurrent",),
        ),
        HazardSpec(
            failure_id="H-C12-032-material-child-clue-does-not-refresh-ancestor",
            protected_error_class="ancestor_activity_propagation_gap",
            description="a material child clue updates only the child summary and order",
            protected_harm="the root Matter appears stale despite a meaningful descendant development",
            case_id="material_clue_summary_activity_current",
            broken_decision="child_only_activity_published",
            broken_writes=(
                "projection.summary_revision",
                "projection.activity_order_revision",
                "ui.catalog_window",
            ),
            broken_side_effects=("activity_projection_publish",),
            broken_tokens=("SummaryClueAtomicProjection",),
        ),
        HazardSpec(
            failure_id="H-C12-033-summary-clue-order-partial-publication",
            protected_error_class="activity_projection_torn_revision",
            description="summary, latest clue, and card order are published from different revisions",
            protected_harm="a card position and its visible explanation contradict each other",
            case_id="material_clue_summary_activity_current",
            broken_decision="partial_activity_projection_published",
            broken_writes=(
                "projection.localized_values",
                "projection.material_clue_revision",
                "projection.summary_revision",
                "projection.activity_order_revision",
                "ui.catalog_window",
            ),
            broken_side_effects=("projection_publish",),
            broken_tokens=("MatterCard",),
        ),
        HazardSpec(
            failure_id="H-C12-034-generated-hero-entered-images-evidence",
            protected_error_class="generated_hero_evidence_gallery_pollution",
            description="the generated hero token is also present in Images or Files and information",
            protected_harm="synthetic presentation art appears to be user evidence",
            case_id="generated_hero_current",
            broken_decision="generated_hero_admitted_to_gallery",
            broken_writes=("projection.generated_hero_asset", "ui.image_gallery_state"),
            broken_side_effects=("generated_hero_projection_publish", "ui_window_write"),
            broken_tokens=("ImagesGallery",),
        ),
        HazardSpec(
            failure_id="H-C12-035-generated-hero-regenerated-on-every-clue",
            protected_error_class="generated_hero_identity_churn",
            description="a normal clue, scan, summary update, or locale switch regenerates the hero",
            protected_harm="catalog visuals churn, waste work, and lose stable Matter recognition",
            case_id="material_clue_summary_activity_current",
            broken_decision="generated_hero_projection_current",
            broken_writes=(
                "projection.generated_hero_asset",
                "projection.generated_hero_revision",
            ),
            broken_side_effects=("generated_hero_projection_publish",),
            broken_tokens=("GeneratedHeroProjection",),
        ),
        HazardSpec(
            failure_id="H-C12-047-unrepresentative-hero-published-current",
            protected_error_class="generated_hero_visual_specificity_gap",
            description=(
                "a generic person-at-computer, interchangeable office image, or "
                "person-only scene without two dominant Matter-specific physical "
                "cues is published as the current root Hero"
            ),
            protected_harm=(
                "the visual browser cannot help the reader distinguish one "
                "Matter from another without rereading every title"
            ),
            case_id="generated_hero_current",
            broken_decision="generic_hero_projection_current",
            broken_writes=(
                "projection.generated_hero_asset",
                "projection.generated_hero_currentness",
                "ui.catalog_window",
            ),
            broken_side_effects=(
                "generated_hero_projection_publish",
                "ui_window_write",
            ),
            broken_tokens=("GeneratedHeroProjection",),
        ),
        HazardSpec(
            failure_id="H-C12-049-inferred-completion-labeled-reported",
            protected_error_class="matter_state_basis_misrepresentation",
            description=(
                "a completion produced by a past-gap AI inference is displayed "
                "as reported or confirmed"
            ),
            protected_harm=(
                "the reader cannot distinguish evidence-backed state from a "
                "revisable historical inference"
            ),
            case_id="historical_inferred_completion_opened",
            broken_decision="reported_state_basis_rendered",
            broken_writes=(
                "projection.state_basis_modality",
                "projection.state_basis_scope",
                "ui.node_quick_view_state",
            ),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("HistoricalInferenceStateBasis",),
        ),
        HazardSpec(
            failure_id="H-C12-050-source-history-duplicated-in-flat-view",
            protected_error_class="files_information_logical_source_duplication",
            description=(
                "two historical SourceVersions of one Gmail message or file are "
                "rendered as duplicate current source rows"
            ),
            protected_harm=(
                "the quick view looks recursively duplicated and overstates the "
                "number of supporting sources"
            ),
            case_id="descendant_graph_node_opened",
            broken_decision="source_revision_rows_repeated",
            broken_writes=(
                "ui.node_quick_view_source_groups",
                "ui.source_group_window",
            ),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("SourceGroupWindow",),
        ),
        HazardSpec(
            failure_id="H-C12-051-raw-source-timestamp-shown-in-ordinary-view",
            protected_error_class="ordinary_source_time_precision_noise",
            description=(
                "a flat Files and information row or node quick view renders a "
                "full source timestamp with hours, seconds, timezone, or a "
                "truncated ISO suffix"
            ),
            protected_harm=(
                "ordinary reading is cluttered by precision that belongs only "
                "to the private canonical record"
            ),
            case_id="descendant_graph_node_opened",
            broken_decision="raw_source_timestamp_rendered",
            broken_writes=(
                "ui.node_quick_view_source_groups",
                "ui.source_group_window",
            ),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("SourceGroupWindow",),
        ),
        HazardSpec(
            failure_id="H-C12-052-detail-loading-opens-empty-background-modal",
            protected_error_class="detail_request_background_modal_interruption",
            description=(
                "activating a Matter opens an empty generic background-work "
                "dialog before the current detail projection is ready"
            ),
            protected_harm=(
                "ordinary navigation is interrupted by a blank modal that "
                "misrepresents detail loading as autonomous background work"
            ),
            case_id="matter_detail_opened",
            broken_decision="empty_loading_dialog_rendered",
            broken_writes=("ui.detail_section", "ui.catalog_window"),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("MatterDetail", "MatterCard"),
        ),
        HazardSpec(
            failure_id="H-C12-053-technical-currentness-rendered-as-node-state",
            protected_error_class="graph_node_technical_state_leak",
            description=(
                "a graph node renders current, reported, observed, or inferred "
                "as if it were a human lifecycle state"
            ),
            protected_harm=(
                "the user sees duplicate or meaningless status text beside the "
                "separately owned modality and certainty label"
            ),
            case_id="descendant_graph_node_opened",
            broken_decision="technical_currentness_rendered",
            broken_writes=("ui.situation_graph_view_state",),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("SituationGraph",),
        ),
        HazardSpec(
            failure_id="H-C12-054-overview-exposes-internal-review-panels",
            protected_error_class="overview_internal_console_density",
            description=(
                "Overview renders source/evidence counters, actions, open loops, "
                "or an audit-style narrative beside the Hero"
            ),
            protected_harm=(
                "the human object browser becomes an internal review console and "
                "the primary image and meaning are pushed out of balance"
            ),
            case_id="matter_detail_opened",
            broken_decision="internal_overview_panels_rendered",
            broken_writes=("ui.detail_sections",),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("MatterDetail",),
        ),
        HazardSpec(
            failure_id="H-C12-055-nonmatter-node-enters-hierarchy-graph",
            protected_error_class="hierarchy_graph_node_type_pollution",
            description=(
                "a WorkItem, Event, fact, wait, source, or inference is rendered "
                "as a peer graph box beside Matter nodes"
            ),
            protected_harm=(
                "the visible hierarchy becomes a noisy recursive event-inside-event graph"
            ),
            case_id="situation_graph_current",
            broken_decision="mixed_type_situation_graph_rendered",
            broken_writes=(
                "ui.situation_graph_view_state",
                "ui.matter_hierarchy_projection",
            ),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("SituationGraphView",),
        ),
        HazardSpec(
            failure_id="H-C12-056-logical-event-revisions-duplicate-timeline",
            protected_error_class="timeline_revision_duplication",
            description=(
                "multiple source or wording revisions of one logical event appear "
                "as repeated current timeline entries"
            ),
            protected_harm=(
                "the timeline overstates activity and hides which revision is current"
            ),
            case_id="logical_event_revisions_current",
            broken_decision="event_revision_rows_repeated",
            broken_writes=("projection.localized_values", "ui.detail_section"),
            broken_side_effects=("projection_publish",),
            broken_tokens=("HumanReadableTimeline",),
        ),
        HazardSpec(
            failure_id="H-C12-057-empty-supplemental-marked-current",
            protected_error_class="supplemental_false_current",
            description=(
                "AI supplemental information is marked current while it contains "
                "zero usable background or preparation items"
            ),
            protected_harm=(
                "an unfinished analysis lane looks complete and the user sees an empty section"
            ),
            case_id="ai_supplemental_information_unavailable",
            broken_decision="labeled_supplemental_information_rendered",
            broken_writes=(
                "projection.supplemental_information_revision",
                "ui.supplemental_information_state",
            ),
            broken_side_effects=("supplemental_information_publish",),
            broken_tokens=("AISupplementalInformation",),
        ),
        HazardSpec(
            failure_id="H-C12-061-eligible-root-never-queues-supplemental-research",
            protected_error_class="supplemental_queue_omission",
            description=(
                "an admitted root Matter with current bilingual context and no "
                "supplemental items remains pending without an A1 package"
            ),
            protected_harm=(
                "AI supplemental information can never advance unless a user or "
                "developer notices the missing background manually"
            ),
            case_id="eligible_root_supplemental_research_queued",
            broken_decision="supplemental_pending_without_work",
            broken_writes=(
                "projection.supplemental_information_disposition",
                "projection.supplemental_research_package_id",
            ),
            broken_side_effects=("supplemental_information_publish",),
            broken_tokens=("SupplementalInformationUnavailable",),
        ),
        HazardSpec(
            failure_id="H-C12-062-descendant-duplicates-root-research",
            protected_error_class="supplemental_descendant_duplicate_queue",
            description=(
                "a descendant Matter receives another ResearchGuard package instead "
                "of one explicit not_applicable disposition"
            ),
            protected_harm=(
                "the same external background is researched repeatedly and appears "
                "as conflicting parent and child advisory state"
            ),
            case_id="descendant_supplemental_not_applicable",
            broken_decision="descendant_supplemental_research_queued",
            broken_writes=(
                "projection.supplemental_research_package_id",
                "projection.supplemental_information_status",
            ),
            broken_side_effects=("supplemental_research_queue",),
            broken_tokens=("SupplementalResearchQueued",),
        ),
        HazardSpec(
            failure_id="H-C12-058-coverage-green-with-unprocessed-ui-gap",
            protected_error_class="coverage_false_green",
            description=(
                "coverage reports complete while admitted source objects still "
                "lack indexed, modeled, or UI-reachable terminal disposition"
            ),
            protected_harm=(
                "the one-click audit hides the exact unfinished objects that block usefulness"
            ),
            case_id="coverage_current_with_first_gap_index",
            broken_decision="coverage_complete_rendered",
            broken_writes=(
                "ui.coverage_summary",
                "ui.coverage_indicator_state",
                "ui.coverage_drilldown",
            ),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("CoverageSummary",),
        ),
        HazardSpec(
            failure_id="H-C12-059-coverage-drilldown-full-ledger-scan",
            protected_error_class="coverage_drilldown_unbounded_scan",
            description=(
                "opening coverage scans or transfers the complete ObjectCoverageLedger"
            ),
            protected_harm=(
                "the diagnostic intended to explain one first gap becomes too slow "
                "to use on the real private inventory"
            ),
            case_id="coverage_current_with_first_gap_index",
            broken_decision="full_coverage_ledger_scanned",
            broken_writes=("ui.coverage_drilldown",),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("CoverageFirstGapDrilldown",),
        ),
        HazardSpec(
            failure_id="H-C12-060-lifecycle-and-modality-conflated",
            protected_error_class="lifecycle_visual_semantic_conflation",
            description=(
                "reported, observed, inferred, or current replaces the planned, "
                "in-progress, or completed lifecycle label or color"
            ),
            protected_harm=(
                "the user cannot tell what stage the Matter is in or how that "
                "state was established"
            ),
            case_id="lifecycle_visual_projection_current",
            broken_decision="modality_rendered_as_lifecycle",
            broken_writes=(
                "projection.lifecycle_visual_state",
                "projection.state_basis_modality",
            ),
            broken_side_effects=("projection_publish",),
            broken_tokens=("LifecycleVisualLanguage",),
        ),
        HazardSpec(
            failure_id="H-C12-036-ai-supplemental-information-shown-as-local-evidence",
            protected_error_class="supplemental_information_evidence_conflation",
            description="AI-added background is rendered without its advisory boundary",
            protected_harm="the user cannot distinguish local evidence from generated context",
            case_id="ai_supplemental_information_current",
            broken_decision="sourced_fact_rendered",
            broken_writes=(
                "projection.supplemental_information",
                "ui.detail_section",
            ),
            broken_side_effects=("supplemental_information_publish",),
            broken_tokens=("FilesInformationTable",),
        ),
        HazardSpec(
            failure_id="H-C12-037-surface-evidence-misses-overlap-or-repetition",
            protected_error_class="ui_runtime_evidence_false_green",
            description=(
                "the UI is accepted without screenshots and DOM geometry for both "
                "desktop sizes, locales, densities, and required states"
            ),
            protected_harm="clipped text, image/metric overlap, repeated metadata, or font drift ships unseen",
            case_id="desktop_surface_evidence_current",
            broken_decision="required_surface_matrix_verified",
            broken_writes=("ui.surface_evidence_status",),
            broken_side_effects=("surface_evidence_write",),
            broken_tokens=("SurfaceEvidenceCurrent",),
        ),
        HazardSpec(
            failure_id="H-C12-043-compact-retains-secondary-metrics",
            protected_error_class="compact_card_image_space_stolen",
            description="Compact still renders event, people, and source metrics",
            protected_harm="the compact Hero collapses into a narrow decorative strip",
            case_id="density_switched",
            broken_decision="compact_metrics_rendered",
            broken_writes=("ui.card_density", "ui.catalog_window"),
            broken_side_effects=("ui_preference_write", "ui_window_write"),
            broken_tokens=("MatterCard",),
        ),
        HazardSpec(
            failure_id="H-C12-044-document-preview-enters-images",
            protected_error_class="text_screenshot_gallery_pollution",
            description="an email, TXT, document, form, or text-page screenshot enters Images",
            protected_harm="nonvisual source text is presented as meaningful visual evidence",
            case_id="images_gallery_current",
            broken_decision="document_preview_gallery_rendered",
            broken_writes=("ui.image_gallery_state",),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("ImagesGallery",),
        ),
        HazardSpec(
            failure_id="H-C12-045-source-groups-rendered-as-repeated-table-headings",
            protected_error_class="files_table_duplicate_group_metadata",
            description="Files and information repeats provider or thread group headings above typed rows",
            protected_harm="the table duplicates information already present in its type and group columns",
            case_id="files_information_table_current",
            broken_decision="grouped_subtable_rendered",
            broken_writes=("ui.files_information_window",),
            broken_side_effects=("ui_window_write",),
            broken_tokens=("FilesInformationTable",),
        ),
        HazardSpec(
            failure_id="H-C12-046-future-prediction-rendered-as-occurred",
            protected_error_class="world_model_prediction_fact_projection",
            description="a future prediction appears as an occurred event or current state",
            protected_harm="the user sees a guess as if it already happened",
            case_id="future_world_model_prediction_current",
            broken_decision="localized_timeline_rendered",
            broken_writes=("projection.localized_values", "ui.detail_section"),
            broken_side_effects=("projection_publish", "ui_window_write"),
            broken_tokens=("HumanReadableTimeline",),
        ),
    ),
    risk_classes=(
        "projection",
        "localization",
        "privacy",
        "state_transition",
        "ownership",
        "visual",
        "accessibility",
        "resource",
        "hierarchy",
        "gallery",
        "transport_recovery",
        "side_effect",
    ),
    template_no_match_reason=(
        "No existing template owns the Databank-authority bilingual desktop "
        "Matter object browser with generated-hero, activity-order, and density invariants."
    ),
    blindspots=(
        "pixel geometry and focus behavior require executable desktop/browser capture evidence",
        "bilingual semantic quality and generated-hero usefulness require private canaries",
        "desktop packaging and worker lifecycle require installed-runtime evidence",
    ),
    claim_boundary=(
        "This model establishes bounded C12 localization, root catalog, child "
        "table, single-shell hierarchy navigation, descendant-aware timeline, "
        "exactly eight ordinary detail sections, bounded Files and information, "
        "operable Images evidence gallery, labeled AI supplemental information, "
        "density, search-state, latest-material-clue order, generated hero, "
        "explicit loading/processing/ready/honest-empty/no-filter-results/"
        "ready-stale/transport-error states, automatic reconnect recovery, "
        "on-demand correction, projection-only rendering that preserves the exact "
        "C6-admitted matter_id and excludes noncanonical source/candidate rows, "
        "and privacy transitions. It does not prove pixel parity, factual truth, "
        "hierarchy completeness, desktop installation, or private-run usefulness."
    ),
)
