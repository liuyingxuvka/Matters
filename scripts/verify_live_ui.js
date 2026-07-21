"use strict";

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const REQUIRED_CHECKS = JSON.parse(
  fs.readFileSync(
    path.resolve(__dirname, "../flowguard_design/ui_runtime_required_checks.json"),
    "utf8",
  ),
).required_checks;
const DETAIL_SECTIONS = [
  "overview",
  "subMatters",
  "timeline",
  "people",
  "relatedMatters",
  "filesInformation",
  "images",
  "aiSupplementalInformation",
];

function arg(name, fallback = "") {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

function phase(name) {
  console.error(`[live-ui] ${name}`);
}

function checkMap() {
  return Object.fromEntries(REQUIRED_CHECKS.map((name) => [name, false]));
}

async function apiResult(page, route) {
  return page.evaluate(async (apiRoute) => {
    const response = await fetch(apiRoute);
    const payload = await response.json();
    if (!response.ok || payload.ok !== true) {
      throw new Error(payload.error?.code || `HTTP ${response.status}`);
    }
    return payload.result;
  }, route);
}

async function waitForCatalog(page) {
  await page.waitForFunction(() => {
    const state = document.querySelector("[data-browser-shell-layout]")?.dataset.transportState;
    return ["ready", "processing", "honest_empty", "no_filter_results"].includes(state);
  });
}

async function cardSnapshot(page) {
  return page.evaluate(() => ({
    ids: [...document.querySelectorAll(".db-project-card")].map((node) => node.dataset.matterId),
    density: document.querySelector(".db-project-grid")?.dataset.cardDensity || "",
    summaries: document.querySelectorAll(".db-card-summary").length,
    people: document.querySelectorAll(".db-card-people").length,
    metrics: document.querySelectorAll(".db-card-metric").length,
    images: document.querySelectorAll(".db-card-media img").length,
    placeholders: document.querySelectorAll(".db-card-empty-media").length,
    generatedHeroCards: document.querySelectorAll(
      '.db-project-card[data-hero-status="generated_current"]',
    ).length,
    pendingHeroCards: document.querySelectorAll(
      '.db-project-card[data-hero-status="generation_pending_placeholder"]',
    ).length,
    blockedHeroCards: document.querySelectorAll(
      '.db-project-card[data-hero-status="generation_blocked_placeholder"]',
    ).length,
    clippedMediaLabels: [...document.querySelectorAll(".db-card-empty-media strong")].filter(
      (node) => getComputedStyle(node).display !== "none" && (
        node.scrollWidth > node.clientWidth + 1
        || node.scrollHeight > node.clientHeight + 1
      ),
    ).length,
    width: Math.round(document.querySelector(".db-project-card")?.getBoundingClientRect().width || 0),
    semanticRevisions: [...document.querySelectorAll(".db-project-card")].map(
      (node) => node.dataset.semanticRevision || "",
    ),
    titles: [...document.querySelectorAll(".db-project-card .db-card-title")].map(
      (node) => node.textContent?.trim() || "",
    ),
    elementMode: document.querySelector(".db-search-result")
      ? "search_result"
      : document.querySelector(".db-project-card")
        ? "project_card"
        : "empty",
  }));
}

async function cardWidthAt(page, width, height) {
  await page.setViewportSize({ width, height });
  return page.evaluate(() => Math.round(
    document.querySelector(".db-project-card")?.getBoundingClientRect().width || 0,
  ));
}

async function main() {
  const baseUrl = arg("url", "http://127.0.0.1:8767");
  const output = arg("output", ".flowguard/evidence/ui/G10_live_ui.json");
  const uiRevision = arg("ui-revision");
  const executablePath = arg("browser");
  if (!uiRevision) throw new Error("--ui-revision is required");
  const checks = checkMap();
  const observations = {};
  const browserErrors = [];
  let browser;

  try {
    phase("launch isolated browser");
    browser = await chromium.launch({
      headless: true,
      ...(executablePath ? { executablePath } : {}),
    });
    const context = await browser.newContext({ viewport: { width: 1880, height: 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(15_000);
    page.setDefaultNavigationTimeout(30_000);
    page.on("pageerror", (error) => browserErrors.push(String(error)));

    phase("verify registry-driven English catalog");
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.evaluate(() => localStorage.clear());
    await page.reload({ waitUntil: "networkidle" });
    await waitForCatalog(page);
    const localeRegistry = await apiResult(page, "/api/locales");
    const browserEnglish = await apiResult(page, "/api/browser?locale=en&limit=200&root_only=true");
    const english = await cardSnapshot(page);
    const englishTitle = await page.locator(".db-project-list-header h2").innerText();
    const localeOptions = await page.evaluate(() => {
      document.querySelector("[data-settings]")?.click();
      return [...document.querySelectorAll("#locale-select option")].map((option) => option.value);
    });
    checks.installed_runtime = true;
    checks.english_default = (
      englishTitle === "All matters"
      && localStorageValue(await page.evaluate(() => localStorage.getItem("matters-locale"))) === ""
      && localeRegistry.default_locale === "en"
    );
    checks.standard_density_default = english.density === "standard";
    checks.root_catalog_excludes_child_cards = (
      (browserEnglish.catalog?.items || []).every(
        (item) => item.is_root !== false && !item.parent_matter_id,
      )
      && english.ids.length === (browserEnglish.catalog?.items || []).length
    );
    checks.large_catalog_window = (
      english.ids.length <= 200
      && english.ids.length <= Number(browserEnglish.catalog?.total_count || 0)
      && (Number(browserEnglish.catalog?.total_count || 0) <= 200
        || browserEnglish.catalog?.has_more === true)
    );
    const englishItems = browserEnglish.catalog?.items || [];
    checks.latest_meaningful_clue_order = activityOrderIsCurrent(englishItems);
    const statusProbe = englishItems.find((item) => item.state)?.state || "planned";
    const statusFiltered = await apiResult(
      page,
      `/api/browser?locale=en&limit=200&root_only=true&status=${encodeURIComponent(statusProbe)}`,
    );
    checks.latest_meaningful_clue_order_after_filters = (
      (statusFiltered.catalog?.items || []).every((item) => item.state === statusProbe)
      && activityOrderIsCurrent(statusFiltered.catalog?.items || [])
    );
    const parentCard = englishItems.find(
      (item) => item.matter_id === "matter:ui-validation:229",
    );
    const childBrowser = await apiResult(
      page,
      "/api/browser?locale=en&limit=200&root_only=false",
    );
    const childCard = (childBrowser.catalog?.items || []).find(
      (item) => item.matter_id === "matter:ui-validation:228",
    );
    checks.ancestor_material_clue_bubbles = Boolean(
      parentCard
      && childCard
      && sameInstant(
        parentCard.latest_meaningful_clue_at,
        childCard.latest_meaningful_clue_at,
      )
      && parentCard.summary?.en === childCard.summary?.en
      && sameInstant(
        parentCard.latest_meaningful_clue_at,
        "2026-12-31T23:00:00+00:00",
      ),
    );
    checks.nonmaterial_processing_does_not_bubble = Boolean(
      parentCard
      && !sameInstant(
        parentCard.latest_meaningful_clue_at,
        "2027-01-01T12:00:00+00:00",
      )
      && sameInstant(
        parentCard.latest_meaningful_clue_at,
        "2026-12-31T23:00:00+00:00",
      ),
    );
    checks.generated_hero_present = Boolean(
      parentCard?.hero?.status === "generated_current"
      && parentCard.hero.preview_token
      && parentCard.matter_id === englishItems[0]?.matter_id,
    );
    checks.generated_hero_presentation_only = Boolean(
      parentCard?.hero
      && !("evidence_ids" in parentCard.hero)
      && !("source_ids" in parentCard.hero)
      && !("runner_contract_id" in parentCard.hero)
      && !("execution_identity" in parentCard.hero),
    );
    checks.generated_hero_pending_or_blocked_honest = (
      english.placeholders > 0
      && english.pendingHeroCards + english.blockedHeroCards === english.placeholders
    );
    observations.locale_options = localeOptions;
    observations.catalog_total = browserEnglish.catalog?.total_count;
    observations.first_matter_id = englishItems[0]?.matter_id || "";

    phase("verify density, locale, and query context");
    await page.evaluate(() => {
      window.__mattersStableDensityControl = document.querySelector("[data-density]");
    });
    await page.waitForTimeout(6_500);
    checks.background_refresh_controls_stable = await page.evaluate(() => (
      window.__mattersStableDensityControl === document.querySelector("[data-density]")
    ));
    await page.click("[data-density]");
    const compact = await cardSnapshot(page);
    checks.compact_density_selectable = (
      compact.density === "compact"
      && await page.evaluate(() => localStorage.getItem("matters-card-density")) === "compact"
      && compact.clippedMediaLabels === 0
    );
    checks.compact_date_not_clipped = await page.evaluate(() => (
      [...document.querySelectorAll(".db-card-start-time span")].every(
        (node) => node.scrollWidth <= node.clientWidth + 1,
      )
    ));
    checks.card_start_date_day_precision = await page.evaluate(() => (
      [...document.querySelectorAll(".db-card-start-time span")].every(
        (node) => /^(?:\d{4}-\d{2}-\d{2}|—)$/.test(node.textContent?.trim() || ""),
      )
    ));
    checks.card_status_plain_metadata_style = await page.evaluate(() => (
      [...document.querySelectorAll(".db-card-status")].every((status) => {
        const date = status.parentElement?.querySelector(".db-card-start-time");
        if (!date) return false;
        const statusStyle = getComputedStyle(status);
        const dateStyle = getComputedStyle(date);
        return (
          statusStyle.fontFamily === dateStyle.fontFamily
          && statusStyle.fontSize === dateStyle.fontSize
          && statusStyle.fontWeight === dateStyle.fontWeight
          && statusStyle.color === dateStyle.color
          && statusStyle.backgroundColor === "rgba(0, 0, 0, 0)"
          && statusStyle.borderTopWidth === "0px"
          && statusStyle.borderRadius === "0px"
        );
      })
    ));
    checks.density_semantics_preserved = (
      JSON.stringify(english.ids) === JSON.stringify(compact.ids)
      && JSON.stringify(english.semanticRevisions) === JSON.stringify(compact.semanticRevisions)
      && english.summaries === compact.summaries
      && english.people === compact.people
      && english.metrics === english.ids.length * 3
      && compact.metrics === 0
    );
    checks.density_hierarchy_revision_preserved = (
      JSON.stringify(english.semanticRevisions) === JSON.stringify(compact.semanticRevisions)
    );
    await page.selectOption("#locale-select", "zh-CN");
    await page.waitForFunction(() => (
      document.querySelector(".db-project-list-header h2")?.textContent?.trim() === "全部事项"
    ));
    const browserChinese = await apiResult(page, "/api/browser?locale=zh-CN&limit=200&root_only=true");
    checks.zh_cn_selectable = (
      await page.evaluate(() => localStorage.getItem("matters-locale")) === "zh-CN"
      && localeOptions.includes("zh-CN")
      && sameMembers(localeOptions, localeRegistry.available_locales || [])
    );
    checks.same_revision_locale_reload = (
      browserEnglish.catalog?.catalog_revision === browserChinese.catalog?.catalog_revision
    );
    const parentCardChinese = (browserChinese.catalog?.items || []).find(
      (item) => item.matter_id === "matter:ui-validation:229",
    );
    checks.generated_hero_bilingual_alt = Boolean(
      parentCard?.hero?.alt?.en
      && parentCard?.hero?.alt?.["zh-CN"]
      && parentCardChinese?.hero?.preview_token === parentCard.hero.preview_token
      && parentCardChinese.hero.generation_revision === parentCard.hero.generation_revision
    );
    checks.generated_hero_stable_for_ordinary_clue = Boolean(
      parentCard
      && parentCardChinese
      && parentCard.hero.preview_token === parentCardChinese.hero.preview_token
      && parentCard.latest_meaningful_clue_at === "2026-12-31T23:00:00+00:00"
    );
    checks.start_time_filter_labeled = (
      await page.locator('[data-filter-group="start_year"]').innerText()
    ).includes("开始时间");
    const searchProbe = String(
      browserChinese.catalog?.items?.[0]?.title?.["zh-CN"]
      || browserChinese.catalog?.items?.[0]?.matter_id
      || "",
    ).slice(0, 16);
    if (searchProbe) {
      await page.locator("#matters-search").fill(searchProbe);
      await page.waitForFunction(() => (
        document.querySelector("[data-browser-shell-layout]")?.dataset.transportState === "ready"
        && document.querySelectorAll(".db-search-result").length > 0
      ));
    }
    const searchState = await page.evaluate(() => ({
      density: localStorage.getItem("matters-card-density"),
      locale: localStorage.getItem("matters-locale"),
      resultCount: document.querySelectorAll(".db-search-result").length,
    }));
    await page.locator("#matters-search").fill("");
    await page.waitForFunction(() => (
      document.querySelector("[data-browser-shell-layout]")?.dataset.transportState === "ready"
      && document.querySelectorAll(".db-project-card").length > 0
    ));
    checks.search_filter_state_preserved = (
      searchState.density === "compact"
      && searchState.locale === "zh-CN"
      && (!searchProbe || searchState.resultCount >= 1)
    );

    phase("verify stale transport preservation and recovery");
    const beforeFailure = await cardSnapshot(page);
    await page.route("**/api/locales", (route) => route.abort(), { times: 1 });
    await page.locator("#matters-search").fill("transport-failure-probe");
    await page.waitForSelector("#catalog-error");
    const failure = await page.evaluate(() => ({
      focus: document.activeElement?.id || "",
      transport: document.querySelector("[data-browser-shell-layout]")?.dataset.transportState || "",
      cards: document.querySelectorAll(".db-project-card").length,
      ids: [...document.querySelectorAll(".db-project-card")].map((node) => node.dataset.matterId),
      titles: [...document.querySelectorAll(".db-project-card .db-card-title")].map(
        (node) => node.textContent?.trim() || "",
      ),
      elementMode: document.querySelector(".db-search-result")
        ? "search_result"
        : document.querySelector(".db-project-card")
          ? "project_card"
          : "empty",
      count: document.querySelector(".db-project-header-meta > span")?.textContent || "",
    }));
    checks.catalog_stale_content_preserved = (
      beforeFailure.ids.length > 0
      && failure.transport === "ready_stale"
      && failure.cards === beforeFailure.ids.length
      && JSON.stringify(failure.ids) === JSON.stringify(beforeFailure.ids)
      && JSON.stringify(failure.titles) === JSON.stringify(beforeFailure.titles)
      && failure.elementMode === beforeFailure.elementMode
    );
    observations.transport_failure = {
      before: {
        itemCount: beforeFailure.ids.length,
        firstMatterIds: beforeFailure.ids.slice(0, 10),
        firstTitles: beforeFailure.titles.slice(0, 10),
        elementMode: beforeFailure.elementMode,
      },
      during: {
        itemCount: failure.ids.length,
        firstMatterIds: failure.ids.slice(0, 10),
        firstTitles: failure.titles.slice(0, 10),
        elementMode: failure.elementMode,
        transport: failure.transport,
        focus: failure.focus,
      },
    };
    checks.catalog_error_focus_and_recovery = failure.focus === "catalog-error";
    await page.unroute("**/api/locales");
    await page.waitForFunction(() => !document.querySelector("#catalog-error"), null, {
      timeout: 10_000,
    });
    checks.catalog_auto_reconnect = true;
    checks.catalog_error_focus_and_recovery = (
      checks.catalog_error_focus_and_recovery
      && !await page.locator("#catalog-error").count()
    );
    await page.locator("#matters-search").fill("");
    await page.waitForFunction(() => (
      document.querySelector("[data-browser-shell-layout]")?.dataset.transportState === "ready"
      && document.querySelectorAll(".db-project-card").length > 0
    ));
    const initialErrorPage = await context.newPage();
    await initialErrorPage.route("**/api/locales", (route) => route.abort());
    await initialErrorPage.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await initialErrorPage.waitForSelector("#catalog-error");
    checks.catalog_initial_error_count_unknown = await initialErrorPage.evaluate(() => (
      document.querySelectorAll(".db-project-card").length === 0
      && (document.querySelector(".db-project-header-meta > span")?.textContent || "").includes("—")
      && document.querySelector("[data-browser-shell-layout]")?.dataset.transportState === "transport_error"
    ));
    await initialErrorPage.close();

    await selectDensity(page, "standard");
    const cardLayout = await page.evaluate(() => {
      const cards = [...document.querySelectorAll(".db-project-card")];
      const first = cards[0];
      const media = first?.querySelector(".db-card-media")?.getBoundingClientRect();
      const metrics = first?.querySelector(".db-card-metrics")?.getBoundingClientRect();
      const sidebar = document.querySelector(".db-sidebar")?.getBoundingClientRect();
      const brand = document.querySelector(".db-sidebar-brand")?.getBoundingClientRect();
      const brandIcon = document.querySelector(".db-sidebar-brand-copy .db-brand-mark")?.getBoundingClientRect();
      const brandWord = document.querySelector(".db-sidebar-brand-copy h1")?.getBoundingClientRect();
      const catalogHeading = document.querySelector(".db-project-list-header h2")?.getBoundingClientRect();
      const search = document.querySelector(".db-search-shell")?.getBoundingClientRect();
      const heading = document.querySelector(".db-sidebar-heading")?.getBoundingClientRect();
      const titleStyle = first ? getComputedStyle(first.querySelector(".db-card-title")) : null;
      const searchStyle = getComputedStyle(document.querySelector(".db-search-input"));
      const brandStyle = getComputedStyle(document.querySelector(".db-sidebar-brand-copy h1"));
      const statusText = document.querySelector(".db-source-health-button")?.textContent || "";
      return {
        metadataNotRepeated: cards.every((card) => (
          card.querySelectorAll(".db-card-start-time").length === 1
          && card.querySelectorAll(".db-card-summary").length === 0
          && card.querySelectorAll(".db-card-context").length === 0
        )),
        brandVisualCenterAlignment: (() => {
          if (!brandIcon || !brandWord || !catalogHeading) return null;
          const visibleIconCenter = (
            brandIcon.top + brandIcon.height * (((114 + 1122) / 2) / 1254)
          );
          const brandWordCenter = brandWord.top + brandWord.height / 2;
          const catalogHeadingCenter = (
            catalogHeading.top + catalogHeading.height / 2
          );
          const centers = [
            visibleIconCenter,
            brandWordCenter,
            catalogHeadingCenter,
          ];
          return {
            visibleIconCenter,
            brandWordCenter,
            catalogHeadingCenter,
            spread: Math.max(...centers) - Math.min(...centers),
          };
        })(),
        searchFirstCardTopAlignment: (
          search && first
            ? {
                searchTop: search.top,
                firstCardTop: first.getBoundingClientRect().top,
                delta: Math.abs(
                  search.top - first.getBoundingClientRect().top,
                ),
              }
            : null
        ),
        metricsDoNotOverlap: Boolean(
          media && metrics && media.bottom <= metrics.top + 1
        ),
        fonts: {
          titleFamily: titleStyle?.fontFamily || "",
          titleSize: titleStyle?.fontSize || "",
          searchSize: searchStyle.fontSize,
          brandSize: brandStyle.fontSize,
        },
        spacing: {
          top: brand && sidebar ? brand.top - sidebar.top : -1,
          brandSearch: brand && search ? search.top - brand.bottom : -1,
          searchNavigation: search && heading ? heading.top - search.bottom : -1,
        },
        statusText: statusText.trim(),
        statusDialogCount: document.querySelectorAll('[role="dialog"]').length,
      };
    });
    checks.card_metadata_not_repeated = cardLayout.metadataNotRepeated;
    checks.card_metrics_do_not_overlap_hero = cardLayout.metricsDoNotOverlap;
    checks.approved_font_tokens = (
      /Bahnschrift|DIN Alternate|Aptos Display|Segoe UI Variable Display/i.test(
        cardLayout.fonts.titleFamily,
      )
      && cardLayout.fonts.titleSize === "18px"
      && cardLayout.fonts.searchSize === "14px"
      && cardLayout.fonts.brandSize === "26px"
    );
    checks.sidebar_spacing_inequalities = (
      cardLayout.spacing.top > cardLayout.spacing.brandSearch
      && cardLayout.spacing.brandSearch > cardLayout.spacing.searchNavigation
      && cardLayout.spacing.searchNavigation >= 0
    );
    checks.brand_visual_center_alignment = (
      cardLayout.brandVisualCenterAlignment !== null
      && cardLayout.brandVisualCenterAlignment.spread <= 1
    );
    checks.search_first_card_top_alignment = (
      cardLayout.searchFirstCardTopAlignment !== null
      && cardLayout.searchFirstCardTopAlignment.delta <= 1
    );
    checks.status_indicator_nonblocking = (
      cardLayout.statusDialogCount === 0
      && !/\d+\s*\/\s*\d+/.test(cardLayout.statusText)
    );
    observations.card_layout = cardLayout;

    phase("verify detail hierarchy and eight-section reader");
    const firstCard = page.locator(".db-project-card").first();
    const firstCardId = await firstCard.getAttribute("id");
    await firstCard.click();
    await page.waitForSelector("#detail-title");
    await page.waitForFunction(() => document.activeElement?.id === "detail-title");
    const detail = await page.evaluate(() => ({
      focus: document.activeElement?.id || "",
      sections: [...document.querySelectorAll("[data-detail-section]")].map(
        (node) => node.dataset.detailSection,
      ),
      dialogs: document.querySelectorAll('[role="dialog"]').length,
      overviewActions: Boolean(document.querySelector("#overview-actions-title")),
      overviewLoops: Boolean(document.querySelector("#overview-open-loops-title")),
      overviewFactLabels: [...document.querySelectorAll(".db-detail-facts dt")].map(
        (node) => node.textContent.trim(),
      ),
      overviewSummary: document.querySelector(".db-detail-summary > p")?.textContent?.trim() || "",
    }));
    checks.exactly_eight_detail_sections = (
      JSON.stringify(detail.sections) === JSON.stringify(DETAIL_SECTIONS)
    );
    checks.overview_minimal_human_narrative = (
      !detail.overviewActions
      && !detail.overviewLoops
      && detail.overviewFactLabels.length === 2
      && detail.overviewSummary.length > 20
      && !/证据表明|语义修订|已纳入理解|AI 检查|evidence shows|semantic revision|analysis owner/i.test(
        detail.overviewSummary,
      )
    );
    if (await page.locator(".db-detail-hero img").count()) {
      await page.waitForFunction(() => (
        (document.querySelector(".db-detail-hero img")?.naturalWidth || 0) > 0
      ));
    }
    const detailHero = await page.evaluate(() => {
      const image = document.querySelector(".db-detail-hero img");
      return {
        src: image?.getAttribute("src") || "",
        alt: image?.getAttribute("alt") || "",
        naturalWidth: image?.naturalWidth || 0,
      };
    });
    checks.generated_hero_present = (
      checks.generated_hero_present
      && detailHero.src.startsWith("/api/heroes/")
      && detailHero.naturalWidth > 0
    );
    checks.generated_hero_bilingual_alt = (
      checks.generated_hero_bilingual_alt
      && Boolean(detailHero.alt)
      && !/抽象|示意图|abstract|illustration/i.test(detailHero.alt)
    );

    await page.click('[data-detail-section="subMatters"]');
    const graph = await page.evaluate(() => ({
      nodes: [...document.querySelectorAll(".db-graph-node")].map((node) => ({
        type: node.dataset.nodeType,
        title: node.querySelector("strong")?.textContent?.trim() || "",
      })),
      collapseControls: document.querySelectorAll("[data-graph-collapse]").length,
      rootTitle: document.querySelector("#detail-title")?.textContent?.trim() || "",
      hasTable: Boolean(document.querySelector(".db-submatter-table")),
      pending: /depth|层级|pending|处理中/i.test(
        document.querySelector(".db-detail-reader")?.textContent || "",
      ),
    }));
    const childNode = page.locator(".db-graph-node [data-graph-node]").nth(1);
    const childNodeCount = await page.locator(".db-graph-node [data-graph-node]").count();
    let quickView = { opened: false, facts: false, sources: false, rootTitleCurrent: false };
    if (childNodeCount > 1) {
      await childNode.click();
      await page.waitForSelector(".db-node-quick-view");
      await page.waitForSelector(
        "#quick-view-title, .db-node-quick-view .db-error-state",
      );
      quickView = await page.evaluate((rootTitle) => ({
        opened: Boolean(document.querySelector(".db-node-quick-view")),
        facts: Boolean(document.querySelector(".db-quick-facts")),
        sources: Boolean(document.querySelector(".db-quick-source-groups, .db-quick-region .db-empty-state")),
        rootTitleCurrent: document.querySelector("#detail-title")?.textContent?.trim() === rootTitle,
      }), graph.rootTitle);
    }
    checks.matter_only_hierarchy_node_quick_view = (
      graph.nodes.length > 1
      && graph.nodes.every((node) => node.type === "matter")
      && graph.collapseControls === 0
      && !graph.hasTable
      && quickView.opened
      && quickView.rootTitleCurrent
    );
    checks.hierarchy_reparent_path_current = (
      new Set(graph.nodes.map((node) => node.title)).size === graph.nodes.length
    );
    checks.hierarchy_depth_pending_visible = graph.nodes.length > 1 || graph.pending;
    checks.node_quick_view_facts_and_sources = quickView.facts && quickView.sources;
    if (quickView.opened) await page.click("[data-close-quick-view]");

    await page.click('[data-detail-section="timeline"]');
    const timelineEntries = await page.locator(".db-timeline-entry").allInnerTexts();
    const timelineText = await page.locator(".db-detail-reader").innerText();
    checks.human_readable_timeline = (
      timelineEntries.length > 0
      && /事情发生时间|Event time/.test(timelineText)
      && /判断依据|Basis/.test(timelineText)
    );
    checks.descendant_timeline_event_deduplicated = (
      timelineEntries.length === new Set(timelineEntries).size
    );

    await page.click('[data-detail-section="filesInformation"]');
    const files = await page.evaluate(() => ({
      rows: document.querySelectorAll(".db-files-table tbody tr").length,
      columns: document.querySelectorAll(".db-files-table thead th").length,
      disclosures: document.querySelectorAll(".db-file-disclosure").length,
      openDisclosures: document.querySelectorAll(".db-file-disclosure[open]").length,
    }));
    checks.files_information_bounded_table = (
      files.rows > 0 && files.rows <= 50 && files.columns === 8
    );
    checks.files_information_disclosure_on_demand = (
      files.disclosures === files.rows
      && files.openDisclosures === 0
    );

    await page.click('[data-detail-section="images"]');
    const gallery = await page.evaluate(() => ({
      thumbnails: document.querySelectorAll("[data-gallery-index]").length,
      large: Boolean(document.querySelector("[data-gallery-image]")),
      source: document.querySelector("[data-gallery-image]")?.getAttribute("src") || "",
      hasCoverEdit: Boolean(document.querySelector("[data-cover-asset], [data-cover-auto]")),
    }));
    checks.ordinary_cover_edit_absent = !gallery.hasCoverEdit;
    checks.images_gallery_thumbnail_large_image = gallery.thumbnails > 0 && gallery.large;
    checks.generated_hero_not_in_images_gallery = (
      detailHero.src.startsWith("/api/heroes/")
      && gallery.source.startsWith("/api/visuals/")
      && gallery.source !== detailHero.src
    );
    if (gallery.large) {
      await page.click("[data-gallery-zoom-in]");
      const zoomed = await page.locator(".db-gallery-zoom-value").innerText();
      await page.dispatchEvent("[data-gallery-stage]", "wheel", { deltaY: -100 });
      const wheelZoomed = await page.locator(".db-gallery-zoom-value").innerText();
      await page.dispatchEvent("[data-gallery-stage]", "pointerdown", {
        pointerId: 1, clientX: 20, clientY: 20,
      });
      await page.dispatchEvent("[data-gallery-stage]", "pointermove", {
        pointerId: 1, clientX: 45, clientY: 40,
      });
      const panned = await page.locator("[data-gallery-image]").getAttribute("style");
      await page.dispatchEvent("[data-gallery-stage]", "pointerup", { pointerId: 1 });
      await page.click("[data-gallery-reset]");
      const reset = await page.locator(".db-gallery-zoom-value").innerText();
      await page.locator("[data-gallery-stage]").press("ArrowRight");
      checks.images_gallery_wheel_zoom = wheelZoomed !== zoomed;
      checks.images_gallery_pan = /translate3d\((?!0px, 0px)/.test(panned || "");
      checks.images_gallery_reset = reset === "1.00×";
      checks.images_gallery_keyboard_navigation = gallery.thumbnails === 1
        || await page.locator('[data-gallery-index][aria-selected="true"]').count() === 1;
    }

    await page.click('[data-detail-section="aiSupplementalInformation"]');
    const supplemental = await page.evaluate(() => ({
      cards: document.querySelectorAll(".db-supplemental-card").length,
      text: document.querySelector(".db-detail-reader")?.textContent || "",
    }));
    checks.ai_supplemental_information_section = supplemental.cards > 0;
    checks.ai_supplemental_information_advisory = (
      /补充建议|不是来源证据|supplemental|not source evidence/i.test(
        supplemental.text,
      )
    );
    checks.background_blocked_catalog_usable = (
      Number(browserEnglish.coverage?.blocked_object_count || 0) > 0
      && english.ids.length > 0
    );

    phase("verify the autonomous first-version browser has no correction control");
    checks.ordinary_correction_absent = await page.evaluate(() => (
      !document.querySelector("[data-correction-form]")
      && !document.querySelector("[data-open-correction]")
      && !document.querySelector("[data-save-correction]")
    ));

    phase("verify geometry and privacy surface");
    await page.click('[data-detail-section="overview"]');
    const screenshotRoot = path.join(path.dirname(output), "screenshots");
    fs.mkdirSync(screenshotRoot, { recursive: true });
    const detailScreenshotPath = path.join(
      screenshotRoot,
      "matters-detail-zh-1880.png",
    );
    await page.screenshot({ path: detailScreenshotPath, fullPage: false });
    const detailScreenshotCaptured = (
      fs.existsSync(detailScreenshotPath)
      && fs.statSync(detailScreenshotPath).isFile()
      && fs.statSync(detailScreenshotPath).size > 0
    );
    await page.keyboard.press("Escape");
    const detailReturnFocus = (
      detail.focus === "detail-title"
      && firstCardId
      && await page.evaluate((id) => document.activeElement?.id === id, firstCardId)
    );
    const screenshotMatrix = [
      ["en", "standard", 1880, 900, "matters-standard-en-1880.png"],
      ["en", "compact", 1880, 900, "matters-compact-en-1880.png"],
      ["zh-CN", "standard", 1880, 900, "matters-standard-zh-1880.png"],
      ["zh-CN", "compact", 1880, 900, "matters-compact-zh-1880.png"],
      ["en", "standard", 1440, 900, "matters-standard-en-1440.png"],
      ["en", "compact", 1440, 900, "matters-compact-en-1440.png"],
      ["zh-CN", "standard", 1440, 900, "matters-standard-zh-1440.png"],
      ["zh-CN", "compact", 1440, 900, "matters-compact-zh-1440.png"],
    ];
    const screenshotResults = {};
    for (const [locale, density, width, height, filename] of screenshotMatrix) {
      await page.setViewportSize({ width, height });
      await selectLocale(page, locale);
      await selectDensity(page, density);
      await waitForCatalog(page);
      const screenshotPath = path.join(screenshotRoot, filename);
      await page.screenshot({ path: screenshotPath, fullPage: false });
      screenshotResults[`${width}:${locale}:${density}`] = (
        fs.existsSync(screenshotPath)
        && fs.statSync(screenshotPath).isFile()
        && fs.statSync(screenshotPath).size > 0
      );
    }
    checks.desktop_matrix_en_standard = screenshotResults["1880:en:standard"] === true;
    checks.desktop_matrix_en_compact = screenshotResults["1880:en:compact"] === true;
    checks.desktop_matrix_zh_standard = screenshotResults["1880:zh-CN:standard"] === true;
    checks.desktop_matrix_zh_compact = screenshotResults["1880:zh-CN:compact"] === true;
    checks.desktop_1440_en_standard = screenshotResults["1440:en:standard"] === true;
    checks.desktop_1440_en_compact = screenshotResults["1440:en:compact"] === true;
    checks.desktop_1440_zh_standard = screenshotResults["1440:zh-CN:standard"] === true;
    checks.desktop_1440_zh_compact = screenshotResults["1440:zh-CN:compact"] === true;
    checks.runtime_screenshots_captured = (
      detailScreenshotCaptured
      && Object.values(screenshotResults).every(Boolean)
    );
    observations.detail_screenshot = path.posix.join(
      "screenshots",
      path.basename(detailScreenshotPath),
    );
    observations.screenshots = Object.fromEntries(
      screenshotMatrix.map(([locale, density, width, , filename]) => [
        `${width}:${locale}:${density}`,
        path.posix.join("screenshots", filename),
      ]),
    );

    const compact1880 = await cardWidthAt(page, 1880, 900);
    const compact1440 = await cardWidthAt(page, 1440, 900);
    const compact1180 = await cardWidthAt(page, 1180, 900);
    await page.setViewportSize({ width: 740, height: 900 });
    const narrow = await page.evaluate(() => ({
      columns: getComputedStyle(document.querySelector(".db-shell")).gridTemplateColumns,
      mobileToggle: getComputedStyle(document.querySelector(".db-mobile-nav-toggle")).display,
    }));
    checks.geometry_1880 = compact1880 === 180;
    checks.geometry_1440 = compact1440 > 0 && compact1440 <= 180;
    checks.geometry_1180 = compact1180 > 0 && compact1180 <= 180;
    checks.narrow_geometry = narrow.columns !== "264px" && narrow.mobileToggle === "grid";
    const visibleText = await page.locator("body").innerText();
    checks.private_internal_absent = !(
      /[A-Z]:\\Users\\|message[_ -]?id|preview[_ -]?token|sha256:/i.test(visibleText)
    );
    checks.matter_detail_open_return = detailReturnFocus;

    const missingChecks = REQUIRED_CHECKS.filter((name) => checks[name] !== true);
    const now = new Date().toISOString();
    const receipt = {
      artifact_type: "matters.live-ui-evidence.v1",
      generated_at: now,
      status: missingChecks.length === 0 && browserErrors.length === 0 ? "passed" : "blocked",
      evidence_id: `evidence:ui:${uiRevision.replace("sha256:", "").slice(0, 16)}`,
      ui_revision: uiRevision,
      required_check_count: REQUIRED_CHECKS.length,
      checks,
      browser_errors: browserErrors,
      missing_checks: missingChecks,
      observed: {
        ...observations,
        detail_sections: detail.sections,
        child_node_count: graph.nodes.length,
        compact_card_width_1880: compact1880,
        compact_card_width_1440: compact1440,
        compact_card_width_1180: compact1180,
      },
      claim_boundary:
        "Synthetic installed-runtime evidence proves only the exact declared read-only object-browser behaviors observed against an isolated service. The ordinary first-version browser exposes no correction or other canonical-write control. This receipt does not prove private-run usefulness, installation parity, or release readiness.",
    };
    fs.mkdirSync(path.dirname(output), { recursive: true });
    fs.writeFileSync(output, `${JSON.stringify(receipt, null, 2)}\n`, "utf8");
    console.log(JSON.stringify(receipt, null, 2));
    process.exitCode = receipt.status === "passed" ? 0 : 1;
  } finally {
    phase("close browser");
    if (browser) await browser.close();
  }
}

function localStorageValue(value) {
  return value == null ? "" : String(value);
}

function sameMembers(left, right) {
  return JSON.stringify([...left].sort()) === JSON.stringify([...right].sort());
}

function activityOrderIsCurrent(items) {
  const keys = items.map((item) => [
    String(item.latest_meaningful_clue_at || ""),
    String(item.matter_id || ""),
  ]);
  return keys.every((key, index) => {
    if (index === 0) return true;
    const previous = keys[index - 1];
    if (previous[0] === key[0]) return previous[1] <= key[1];
    if (!previous[0]) return !key[0];
    if (!key[0]) return true;
    return previous[0] >= key[0];
  });
}

function sameInstant(left, right) {
  const leftTime = Date.parse(String(left || ""));
  const rightTime = Date.parse(String(right || ""));
  return Number.isFinite(leftTime) && Number.isFinite(rightTime) && leftTime === rightTime;
}

async function selectLocale(page, locale) {
  if (!await page.locator("#locale-select").count()) {
    await page.click("[data-settings]");
  }
  await page.selectOption("#locale-select", locale);
  await page.waitForFunction((selectedLocale) => (
    localStorage.getItem("matters-locale") === selectedLocale
  ), locale);
  if (await page.locator("#locale-select").count()) {
    await page.click("[data-settings]");
  }
}

async function selectDensity(page, density) {
  const compact = density === "compact";
  const current = await page.locator("[data-density]").getAttribute("aria-checked");
  if ((current === "true") !== compact) {
    await page.click("[data-density]");
  }
  await page.waitForFunction((expected) => (
    document.querySelector(".db-project-grid")?.dataset.cardDensity === expected
  ), density);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
