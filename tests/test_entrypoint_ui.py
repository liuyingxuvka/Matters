from __future__ import annotations

from html.parser import HTMLParser
import hashlib
from pathlib import Path

import pytest
from PIL import Image

from matters.api.http import static as static_ui


UI_ROOT = Path("ui")


class SurfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()

    def handle_starttag(self, _tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(str(values["id"]))


def test_entrypoint_ui_is_an_english_default_bilingual_object_browser():
    html = (UI_ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (UI_ROOT / "app.js").read_text(encoding="utf-8")
    parser = SurfaceParser()
    parser.feed(html)

    assert parser.ids == {"app"}
    assert '<html lang="en">' in html
    assert '<title>Matters</title>' in html
    assert '<link rel="icon" href="/favicon.ico" sizes="any">' in html
    assert '<link rel="icon" href="/matters-icon.png" type="image/png">' in html
    assert '<img class="db-brand-mark" src="/matters-icon.png"' in html
    assert "en: {" in javascript
    assert '"zh-CN": {' in javascript
    assert 'locale: "matters-locale"' in javascript
    assert 'locale: "en"' in javascript
    assert 'fetchJson("/api/locales"' in javascript
    assert "localeDefinitions().map" in javascript
    assert 'definition?.native_name' in javascript
    assert "state.localeRegistry?.available_locales?.includes(target.value)" in javascript
    assert '<option value="en"' not in javascript
    assert '<option value="zh-CN"' not in javascript
    assert "Search matters" in javascript
    assert "All matters" in javascript
    assert "搜索事项" in javascript
    assert "全部事项" in javascript


def test_entrypoint_ui_uses_the_transparent_approved_brand_asset_and_bounded_larger_brand_size():
    javascript = (UI_ROOT / "app.js").read_text(encoding="utf-8")
    css = (UI_ROOT / "styles.css").read_text(encoding="utf-8")
    icon = Path("src/matters/assets/matters-icon.png")

    assert icon.is_file()
    assert hashlib.sha256(icon.read_bytes()).hexdigest() == (
        "65da4baafc76e060cf6248719ac18b0adf06a87b878768b2c6aeb650be08fd51"
    )
    with Image.open(icon) as image:
        assert image.mode == "RGBA"
        corners = (
            (0, 0),
            (image.width - 1, 0),
            (0, image.height - 1),
            (image.width - 1, image.height - 1),
        )
        assert all(image.getpixel(point)[3] == 0 for point in corners)
    assert javascript.count(
        '<img class="db-brand-mark" src="/matters-icon.png"'
    ) == 2
    brand_mark_css = css.split(
        ".db-sidebar-brand-copy .db-brand-mark {", 1
    )[1].split("}", 1)[0]
    assert "width: 48px" in brand_mark_css
    assert "height: 48px" in brand_mark_css
    assert "transform: translateY(0)" in brand_mark_css
    brand_copy = css.split(".db-sidebar-brand-copy {", 1)[1].split("}", 1)[0]
    assert "align-items: center" in brand_copy
    assert "justify-content: start" in brand_copy
    assert "min-height: 48px" in brand_copy
    assert "transform: translateY(-13px)" in brand_copy
    assert "padding: 24px 12px 12px;" in css
    assert "margin-bottom: 18px;" in css
    assert "gap: 8px;" in css
    assert "font: 700 26px/28px var(--display);" in css
    assert "object-fit: contain;" in css
    assert "border-radius: 0;" in css
    assert "background: transparent;" in css


def test_entrypoint_ui_serves_packaged_brand_assets_from_the_fixed_allowlist():
    application = static_ui.LocalUI(object(), UI_ROOT)

    for path, media_type, signature in (
        ("/matters-icon.png", "image/png", b"\x89PNG\r\n\x1a\n"),
        ("/favicon.ico", "image/x-icon", b"\x00\x00\x01\x00"),
    ):
        response: dict[str, object] = {}

        def start_response(status, headers):
            response["status"] = status
            response["headers"] = dict(headers)

        body = b"".join(
            application(
                {"REQUEST_METHOD": "GET", "PATH_INFO": path},
                start_response,
            )
        )
        assert response["status"] == "200 OK"
        assert response["headers"]["Content-Type"] == media_type
        assert body.startswith(signature)


def test_static_asset_contract_blocks_unregistered_document_assets(
    tmp_path: Path,
):
    ui_root = tmp_path / "ui"
    ui_root.mkdir()
    (ui_root / "index.html").write_text(
        '<html><body><img src="/unregistered-icon.png" alt=""></body></html>',
        encoding="utf-8",
    )

    with pytest.raises(
        static_ui.StaticAssetContractError,
        match=r"/unregistered-icon\.png:route_unregistered",
    ):
        static_ui.LocalUI(object(), ui_root)


def test_static_asset_contract_covers_every_local_index_reference():
    assert static_ui.validate_static_asset_contract(UI_ROOT) == (
        "/app.js",
        "/favicon.ico",
        "/matters-icon.png",
        "/styles.css",
    )


def test_entrypoint_ui_uses_only_autonomous_browser_and_post_result_routes():
    javascript = (UI_ROOT / "app.js").read_text(encoding="utf-8")

    for route in (
        "/api/browser?",
        "/api/matters/${encodeURIComponent(matterId)}?locale=",
        "/api/matters/${encodeURIComponent(matterId)}/graph?${params.toString()}",
        "/nodes/${encodeURIComponent(nodeId)}/quick-view?locale=",
        "/api/matters/${encodeURIComponent(state.selectedMatterId)}/evidence",
        "/api/heroes/${encodeURIComponent(hero.preview_token)}",
        "/api/visuals/${encodeURIComponent(selected.preview_token)}?size=hero",
        "/api/visuals/${encodeURIComponent(asset.preview_token)}",
    ):
        assert route in javascript

    for retired_route in (
        "/api/projection",
        "/api/tracking-intents",
        "/api/review-queue",
        "/api/understanding",
        "/api/understanding-intents",
        "/api/matters/${encodeURIComponent(state.selectedMatterId)}/corrections",
    ):
        assert retired_route not in javascript

    assert "Review queue" not in javascript
    assert "待确认队列" not in javascript
    assert "data-confirm" not in javascript.casefold()
    assert "confirm matter" not in javascript.casefold()
    assert "correction form" not in javascript.casefold()
    assert "事后纠正" not in javascript
    assert "Working in background" in javascript
    assert "正在后台处理" in javascript
    assert "/api/matters/${encodeURIComponent(state.selectedMatterId)}/cover" not in javascript
    assert "data-cover-asset" not in javascript


def test_entrypoint_ui_supports_standard_and_compact_cards_with_same_hero():
    javascript = (UI_ROOT / "app.js").read_text(encoding="utf-8")
    css = (UI_ROOT / "styles.css").read_text(encoding="utf-8")

    assert 'density: "matters-card-density"' in javascript
    assert (
        'localStorage.getItem(STORAGE.density) === "compact"'
        ' ? "compact" : "standard"'
        in javascript
    )
    assert 'data-card-density="${state.density}"' in javascript
    assert 'db-project-card--${state.density}' in javascript
    assert 'const hero = card.hero || {}' in javascript
    assert 'const metrics = state.density === "compact" ? "" : `<div class="db-card-metrics">' in javascript
    assert "function displayStartDate(input)" in javascript
    assert 'return Number.isNaN(parsed.getTime()) ? "—" : parsed.toISOString().slice(0, 10);' in javascript
    assert 'if (iso) return dayFromParts(iso[1], iso[2], iso[3]) || "—";' in javascript
    assert "displayStartDate(source.observed_time || source.relevant_time)" in javascript
    assert "source.observed_time\n                || source.relevant_time" in javascript
    assert 'class="db-card-status" data-status=' in javascript
    assert 'class="db-card-type"' not in javascript
    assert ".db-card-status," in css
    status_css = css.split(".db-card-status,", 1)[1].split("}", 1)[0]
    assert "border-radius" not in status_css
    assert "background:" not in status_css
    assert (
        '<img src="/api/heroes/${encodeURIComponent(hero.preview_token)}"'
        in javascript
    )
    assert "No current authorized image yet." in javascript
    assert "目前还没有当前且已授权的图片。" in javascript
    assert "db-card-summary" not in javascript
    assert 'data-semantic-revision="${escapeHtml(card.semantic_revision' in javascript
    assert 'data-hero-token="${escapeHtml(hero.preview_token' in javascript
    assert "data-visual-token" not in javascript
    assert "card.event_count" in javascript
    assert "card.people_count" in javascript
    assert "card.source_count" in javascript
    assert "data-load-more" in javascript
    assert "catalog.next_offset" in javascript
    assert "items: [...existing, ...appended]" in javascript
    assert '["matter", "work_item"].includes(nodeType)' in javascript
    assert 'String(node.node_id || "") !== String(state.selectedMatterId)' in javascript

    assert "grid-template-columns: 264px minmax(0, 1fr)" in css
    assert "grid-template-columns: repeat(3, minmax(0, 360px))" in css
    assert '.db-project-grid[data-card-density="compact"]' in css
    assert "repeat(auto-fit, 180px)" in css
    assert "aspect-ratio: 20 / 21" in css
    assert ".db-project-card--compact .db-card-media" in css
    assert 'state.density === "compact" ? ""' in javascript
    compact_css = css.split(".db-project-card--compact {", 1)[1].split("}", 1)[0]
    assert "grid-template-rows: 32px 20px minmax(0, 1fr)" in compact_css
    assert "38px" not in compact_css
    assert ".db-card-metrics" in css
    assert ".db-card-copy" not in css
    assert ".db-card-summary" not in css
    assert ".db-card-media img { width: 100%; height: 100%; object-fit: cover" in css
    assert '.db-search-result-status[data-group="planned"] { color: var(--success); }' in css
    assert '.db-search-result-status[data-group="in_progress"] { color: var(--signal-red); }' in css
    assert '.db-search-result-status[data-group="completed"] { color: var(--info); }' in css
    assert ".db-status-chip" not in css
    assert (
        '.db-card-status[data-status="planned"],\n'
        '.db-card-status[data-status="in_progress"],\n'
        '.db-card-status[data-status="completed"] { color: var(--muted); }'
    ) in css


def test_entrypoint_ui_uses_grouped_filters_and_keeps_unknown_transport_counts_honest():
    javascript = (UI_ROOT / "app.js").read_text(encoding="utf-8")
    css = (UI_ROOT / "styles.css").read_text(encoding="utf-8")

    for filter_name in (
        "status",
        "start_year",
        "people",
        "relationships",
        "topic_types",
        "source_types",
    ):
        assert f'name: "{filter_name}"' in javascript

    assert 'data-clear-all' in javascript
    assert 'data-filter-group="${name}"' in javascript
    assert 'data-filter-name="${name}"' in javascript
    assert 'root_only: state.query ? "false" : "true"' in javascript
    assert "Recent" not in javascript
    assert "Upcoming" not in javascript
    assert 'return knownNumber(input) ? String(input) : "—"' in javascript
    assert "Showing the last successfully loaded Matters." in javascript
    assert "正在显示上一次成功载入的事项。" in javascript
    for transport_state in (
        "loading",
        "processing",
        "ready",
        "honest_empty",
        "no_filter_results",
        "ready_stale",
        "transport_error",
    ):
        assert f'"{transport_state}"' in javascript
    assert 'data-transport-state="${escapeHtml(state.transportPhase)}"' in javascript
    assert 'state.browser ? "ready_stale" : "transport_error"' in javascript
    assert "successfulTransportPhase(result)" in javascript
    assert "scheduleBrowserRefresh(state.transportPhase === \"processing\" ? 3000 : 30000)" in javascript
    assert "void loadBrowser({ background: true })" in javascript
    assert "priorCatalogIdentity !== catalogRenderIdentity(result)" in javascript
    assert "updateCoverageStatusDom()" in javascript
    assert 'if (!background || !state.browser) render();' in javascript
    assert "Math.min(30000, 1000 * (2 ** Math.min(state.retryAttempt - 1, 5)))" in javascript
    assert "const API_TIMEOUT_MS = 12_000" in javascript
    assert "window.setTimeout(() => {" in javascript
    assert 'timeoutError.name = "TimeoutError"' in javascript
    assert 'new Error("request_timeout")' in javascript
    assert "Nothing has been reported as empty." in javascript
    assert "这里没有把故障误报成空数据" in javascript
    assert "formatCount(audit.current_surfaces)" in javascript
    assert ".db-filter-group-toggle" in css
    assert ".db-active-filter-chip" in css
    assert ".db-typed-search-results" in css


def test_entrypoint_ui_uses_surface_coverage_contract_and_bounded_drilldown():
    javascript = (UI_ROOT / "app.js").read_text(encoding="utf-8")
    css = (UI_ROOT / "styles.css").read_text(encoding="utf-8")

    assert "function coverageSurfaceStatus()" in javascript
    assert "state.coverageAudit?.coverage_contract?.surface_status" in javascript
    assert "coverageHealthTone(transportCurrent)" in javascript
    assert "audit.total_surfaces" in javascript
    assert "audit.current_surfaces" in javascript
    assert "audit.gap_surfaces" in javascript
    assert "audit.surface_gaps" in javascript
    assert "audit.surfaces" in javascript
    assert "audit.surface_applicability" in javascript
    assert "async function loadCoverageAudit" in javascript
    assert "`/api/coverage/audit?${params.toString()}`" in javascript
    for query_filter in (
        "surface_id",
        "surface_status",
        "owner_id",
        "failure_class",
        "freshness",
        "ui_ready",
    ):
        assert query_filter in javascript
    assert "data-coverage-drilldown" in javascript
    assert "data-coverage-clear" in javascript
    assert ".db-coverage-surface-facts" in css
    assert ".db-coverage-surface-row" in css
    assert ".db-coverage-applicability" in css


def test_entrypoint_ui_detail_is_a_bounded_keyboard_operable_object_view():
    javascript = (UI_ROOT / "app.js").read_text(encoding="utf-8")
    css = (UI_ROOT / "styles.css").read_text(encoding="utf-8")

    assert 'role="dialog"' in javascript
    assert 'aria-modal="true"' in javascript
    assert 'aria-labelledby="detail-title"' in javascript
    assert 'id="detail-title" tabindex="-1"' in javascript
    assert 'event.key === "Enter" || event.key === " "' in javascript
    assert 'event.key === "Tab"' in javascript
    assert 'event.key === "Escape"' in javascript
    assert "lastCardFocus" in javascript
    assert "document.getElementById(lastCardFocus)?.focus()" in javascript
    assert 'aria-busy="${detailPending}"' in javascript
    assert 'class="db-project-card db-project-card--${state.density}${detailPending ? " is-detail-loading" : ""}"' in javascript
    assert 'if (state.detailLoading || !state.detail) {\n    return "";' in javascript
    assert ".db-project-card.is-detail-loading::after" in css
    assert 'quickViewLoading: "Loading this quick view…"' in javascript
    assert 'quickViewLoading: "正在载入这个节点的速览…"' in javascript
    assert '${escapeHtml(t("quickViewLoading"))}' in javascript
    assert 'reportedCertainty: "Source record"' in javascript
    assert 'reportedCertainty: "来源记录"' in javascript
    assert 'reportedBasis: "Source record"' in javascript
    assert 'reportedBasis: "来源记录"' in javascript
    assert 'return normalize(body) === normalize(title) ? "" : body;' in javascript
    assert (
        r"raw.match(/((?:19|20)\d{2})-(\d{2})-(\d{2})(?!\d)/)"
        in javascript
    )
    assert 'const technicalCurrentness = new Set(["current", "reported", "observed", "inferred"])' in javascript
    assert '${statusLabel ? `<span>${escapeHtml(statusLabel)}</span>` : ""}' in javascript
    assert "claimedTime" in javascript
    assert "recordTime" in javascript
    assert "modality" in javascript
    assert "evidencePrivacy" in javascript
    assert 'id="correction-error"' not in javascript
    assert "state.correctionDraft" not in javascript
    assert "focusCorrectionErrorOnRender" not in javascript
    assert "data-correction-form" not in javascript
    for section, label in (
        ("overview", "overview"),
        ("subMatters", "subMatters"),
        ("timeline", "timeline"),
        ("people", "people"),
        ("relatedMatters", "relatedMatters"),
        ("filesInformation", "filesInformation"),
        ("images", "images"),
        ("aiSupplementalInformation", "aiSupplementalInformation"),
    ):
        assert f'detailNavItem("{section}", "{label}"' in javascript
    assert javascript.count("${detailNavItem(") == 8
    assert 'detailNavItem("subMatters", "subMatters"' in javascript
    assert 'detailNavItem("relatedMatters", "relatedMatters"' in javascript
    assert 'detailNavItem("openLoops", "openLoops"' not in javascript
    assert 'detailNavItem("sourceList", "sourceList"' not in javascript
    assert 'detailNavItem("evidenceList", "evidenceList"' not in javascript
    assert 'detailNavItem("corrections", "corrections"' not in javascript
    assert 'detailNavItem("cover", "cover"' not in javascript
    overview = javascript.split("function detailOverview(detail)", 1)[1].split(
        "function detailActions(detail)", 1
    )[0]
    assert "detailActions(detail)" not in overview
    assert "detailOpenLoops(detail)" not in overview
    assert 't("sources")' not in overview
    assert 't("evidence")' not in overview
    assert "detail.files_and_information" in javascript
    assert 'class="db-files-table"' in javascript
    assert 'data-image-gallery' in javascript
    assert "Math.max(0.5, Math.min(5" in javascript
    assert "[\"ArrowLeft\", \"ArrowRight\", \"Home\", \"End\"]" in javascript
    assert 'data-gallery-zoom-in' in javascript
    assert 'data-gallery-zoom-out' in javascript
    assert 'data-gallery-reset' in javascript
    assert 'data-gallery-stage' in javascript
    assert "function detailSituationGraph()" in javascript
    assert 'class="db-graph-viewport"' in javascript
    assert 'data-graph-node="${escapeHtml(id)}"' in javascript
    assert 'data-graph-collapse="${escapeHtml(id)}"' not in javascript
    assert '["matter", "work_item"].includes(' in javascript
    assert 'class="db-graph-minimap"' in javascript
    assert "loadNodeQuickView(graphNode, { originNodeId: graphNode })" in javascript
    assert 'class="db-node-quick-view"' in javascript
    assert 'id="quick-view-title" tabindex="-1"' in javascript
    assert "closeNodeQuickView()" in javascript
    assert "focusGraphNode(originNodeId)" in javascript
    assert "summary_current_state" in javascript
    assert 'class="db-quick-facts"' in javascript
    assert "files_and_information" in javascript
    assert "sourcePrivacySafeLocation" in javascript or "sourceLocationLabel" in javascript
    assert "sourceModalityLabel" in javascript
    assert "recursive_navigation_allowed" not in javascript
    assert "detailStack" not in javascript
    assert "openNestedDetail" not in javascript
    assert "embeddedChildPage" not in javascript
    assert "summary.coverage" not in javascript
    assert "AI historical inference" in javascript
    assert "AI 历史推断" in javascript
    assert "relation.label" in javascript
    assert "relation.rationale" in javascript
    assert "person.role_label" in javascript
    for supplemental_status in (
        "supplementalPending",
        "supplementalBlocked",
        "supplementalUnavailable",
        "supplementalStale",
        "supplementalNotApplicable",
    ):
        assert supplemental_status in javascript

    assert "width: min(1400px, calc(100vw - 48px))" in css
    assert "height: min(900px, calc(100vh - 48px))" in css
    assert "grid-template-columns: 236px minmax(0, 1fr)" in css
    assert ".db-submatter-table" not in css
    assert 'class="db-graph-load-more"' in javascript
    assert ".db-graph-load-more" in css
    assert "GRAPH_FOCUS_PAGE_LIMIT" in javascript
    assert "quickViewOriginNodeId" in javascript
    assert "padding: 18px 70px 18px 18px" in css
    assert "grid-template-columns: 44px minmax(0, 1fr)" in css
    assert "gap: 10px" in css
    assert ".db-detail-brand-heading .db-brand-mark { width: 44px; height: 44px; }" in css
    assert "font: 650 15px/1.25 var(--display)" in css
    assert ".db-image-gallery" in css
    assert ".db-gallery-thumbnails" in css
    assert ".db-files-table" in css
    assert "privacy_safe_location" in javascript
    assert "source.privacy_safe_location || source.location_group" in javascript
    assert "source.privacy_safe_location || source.location," not in javascript
    assert "source.modality" in javascript
    assert "min-width: 980px" not in css
    assert ".db-files-table thead th:nth-child(8)" in css
    files_table_css = css.split(".db-files-table {", 1)[1].split("}", 1)[0]
    assert "font-size: 10.5px" in files_table_css
    files_header_css = css.split(".db-files-table thead th {", 1)[1].split("}", 1)[0]
    assert "font-size: 11.5px" in files_header_css
    assert ".db-situation-graph" in css
    assert ".db-node-quick-view" in css
    assert "@media (max-width: 760px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "linear-gradient" not in css
    assert "radial-gradient" not in css
    assert "http://" not in javascript
    assert "https://" not in javascript
    assert "C:\\Users\\" not in javascript
    assert "C:\\Users\\" not in css


def test_installed_ui_root_comes_from_the_distribution_record(
    tmp_path: Path,
    monkeypatch,
):
    ui_root = tmp_path / "share" / "matters" / "ui"
    ui_root.mkdir(parents=True)
    index = ui_root / "index.html"
    index.write_text("<html></html>", encoding="utf-8")

    class InstalledDistribution:
        files = (Path("../../share/matters/ui/index.html"),)

        @staticmethod
        def locate_file(_entry: Path) -> Path:
            return index

    monkeypatch.setattr(
        static_ui.importlib.metadata,
        "distribution",
        lambda _name: InstalledDistribution(),
    )

    assert static_ui._installed_ui_root() == ui_root.resolve()
