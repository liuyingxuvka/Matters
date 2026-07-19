"use strict";

const fs = require("fs");
const { chromium } = require("playwright");

function arg(name, fallback = "") {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

function phase(name) {
  console.error(`[live-ui] ${name}`);
}

async function main() {
  const baseUrl = arg("url", "http://127.0.0.1:8767");
  const output = arg("output", ".flowguard/evidence/ui/G10_live_ui.json");
  const uiRevision = arg("ui-revision");
  const executablePath = arg("browser");
  if (!uiRevision) throw new Error("--ui-revision is required");

  let browser;
  try {
    phase("launch browser");
    browser = await chromium.launch({
      headless: true,
      ...(executablePath ? { executablePath } : {}),
    });
    const errors = [];
    const context = await browser.newContext({
      viewport: { width: 1880, height: 1120 },
    });
    const page = await context.newPage();
    page.setDefaultTimeout(15_000);
    page.setDefaultNavigationTimeout(30_000);
    page.on("pageerror", (error) => errors.push(String(error)));
    phase("load English catalog");
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.evaluate(() => localStorage.clear());
    await page.reload({ waitUntil: "networkidle" });
    await page.waitForFunction(
      () => document.querySelectorAll(".db-project-card").length === 200,
    );

    const english = await page.evaluate(() => ({
      locale: localStorage.getItem("matters-locale"),
      title: document.querySelector(".db-project-list-header h2")?.textContent || "",
      ids: [...document.querySelectorAll(".db-project-card")].map(
        (node) => node.dataset.matterId,
      ),
      standard: document.querySelector(".db-project-grid")?.dataset.cardDensity,
      cardCount: document.querySelectorAll(".db-project-card").length,
      imageCount: document.querySelectorAll(".db-card-media img").length,
      placeholderCount: document.querySelectorAll(".db-card-empty-media").length,
      metricCount: document.querySelectorAll(".db-card-metric").length,
      summaryCount: document.querySelectorAll(".db-card-summary").length,
      peopleCount: document.querySelectorAll(".db-card-people").length,
    }));
    const apiEn = await page.evaluate(async () => {
      const response = await fetch("/api/browser?locale=en&limit=200");
      return response.json();
    });
    const catalogRevision = apiEn.result.catalog.catalog_revision;
    const totalCount = apiEn.result.catalog.total_count;
    const blockedCount = apiEn.result.coverage.blocked_object_count;

    phase("verify density, locale, search, and recovery");
    await page.click("[data-density]");
    await page.waitForFunction(
      () => document.querySelector(".db-project-grid")?.dataset.cardDensity === "compact"
        && Boolean(document.querySelector(".db-project-card")),
    );
    const compact = await page.evaluate(() => ({
      ids: [...document.querySelectorAll(".db-project-card")].map(
        (node) => node.dataset.matterId,
      ),
      density: localStorage.getItem("matters-card-density"),
      metricCount: document.querySelectorAll(".db-card-metric").length,
      summaryCount: document.querySelectorAll(".db-card-summary").length,
      peopleCount: document.querySelectorAll(".db-card-people").length,
      width: Math.round(
        document.querySelector(".db-project-card").getBoundingClientRect().width,
      ),
    }));

    await page.click("[data-settings]");
    await page.selectOption("#locale-select", "zh-CN");
    await page.waitForTimeout(300);
    const apiZh = await page.evaluate(async () => {
      const response = await fetch("/api/browser?locale=zh-CN&limit=200");
      return response.json();
    });
    const chinese = await page.evaluate(() => ({
      locale: localStorage.getItem("matters-locale"),
      title: document.querySelector(".db-project-list-header h2")?.textContent || "",
    }));

    await page.locator("#matters-search").fill("229");
  await page.waitForFunction(
    () => document.querySelectorAll(".db-project-card").length === 1,
  );
  const searchState = await page.evaluate(() => ({
    density: localStorage.getItem("matters-card-density"),
    locale: localStorage.getItem("matters-locale"),
    resultCount: document.querySelectorAll(".db-project-card").length,
  }));
    await page.locator("#matters-search").fill("");
  await page.waitForFunction(
    () => document.querySelectorAll(".db-project-card").length === 200,
  );

    await page.route("**/api/browser?*", (route) => route.abort(), { times: 1 });
  await page.locator("#matters-search").fill("error-probe");
  await page.waitForSelector("#catalog-error");
  const errorFocus = await page.evaluate(() => document.activeElement?.id || "");
  await page.click("[data-retry]");
  await page.waitForFunction(
    () => !document.querySelector("#catalog-error")
      && Boolean(document.querySelector(".db-empty-state")),
  );
  const errorRecovered = true;
  await page.locator("#matters-search").fill("");
  await page.waitForFunction(
    () => document.querySelectorAll(".db-project-card").length === 200,
  );
  await page.click("[data-load-more]");
  await page.waitForFunction(
    (expected) => document.querySelectorAll(".db-project-card").length === expected,
    totalCount,
  );
    const loadedCatalogCount = await page.locator(".db-project-card").count();

    phase("verify detail, evidence, and correction recovery");
    const firstCardId = await page.locator(".db-project-card").first().getAttribute("id");
  await page.locator(".db-project-card").first().click();
  await page.waitForSelector("#detail-title");
  const detail = await page.evaluate(() => ({
    focus: document.activeElement?.id || "",
    sections: [...document.querySelectorAll("[data-detail-section]")].map(
      (node) => node.dataset.detailSection,
    ),
    dialog: (() => {
      const rect = document.querySelector(".db-dialog").getBoundingClientRect();
      const rail = document.querySelector(".db-detail-rail").getBoundingClientRect();
      return {
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        rail: Math.round(rail.width),
      };
    })(),
  }));
  await page.click('[data-detail-section="timeline"]');
  const timelineText = await page.locator(".db-detail-reader").innerText();
  await page.click('[data-detail-section="evidenceList"]');
  await page.click("[data-load-evidence]");
  await page.waitForSelector(".db-evidence-excerpt");
  const evidenceLoaded = await page.locator(".db-evidence-excerpt").count() > 0;
  await page.click('[data-detail-section="corrections"]');
  await page.route("**/api/matters/*/corrections", (route) => route.abort(), {
    times: 1,
  });
  await page.fill('[name="field_name"]', "summary");
  await page.fill('[name="corrected_value"]', "Public UI validation value.");
  await page.fill('[name="rationale"]', "Public UI validation correction.");
  await page.click('[data-correction-form] button[type="submit"]');
  await page.waitForSelector("#correction-error");
  const correctionFailure = await page.evaluate(() => ({
    focus: document.activeElement?.id || "",
    field: document.querySelector('[name="field_name"]')?.value || "",
    value: document.querySelector('[name="corrected_value"]')?.value || "",
    rationale: document.querySelector('[name="rationale"]')?.value || "",
  }));
  await page.click('[data-correction-form] button[type="submit"]');
  await page.waitForFunction(
    () => document.querySelector(".db-toast")?.textContent.includes("纠正已保存"),
  );
  const correctionRecovered =
    correctionFailure.focus === "correction-error"
    && correctionFailure.field === "summary"
    && correctionFailure.value === "Public UI validation value."
    && correctionFailure.rationale === "Public UI validation correction.";
  await page.waitForSelector("#detail-title");
  await page.keyboard.press("Escape");
    const restoredFocus = await page.evaluate(() => document.activeElement?.id || "");

    phase("verify representative visual correction");
    const visualCard = page.locator(".db-card-media img").first().locator("xpath=../..");
  const visualCardAvailable = await page.locator(".db-card-media img").count() > 0;
  let coverCorrected = false;
    if (visualCardAvailable) {
    await visualCard.click();
    await page.waitForSelector("#detail-title");
    await page.click('[data-detail-section="cover"]');
    await page.click("[data-cover-auto]");
    await page.waitForFunction(
      () => document.querySelector(".db-toast")?.textContent.includes("代表图片已更新"),
    );
    coverCorrected = true;
    await page.keyboard.press("Escape");
    }

    phase("verify desktop and narrow geometry");
    await page.setViewportSize({ width: 1440, height: 1000 });
  const geometry1440 = await page.evaluate(() =>
    Math.round(document.querySelector(".db-project-card").getBoundingClientRect().width),
  );
  await page.setViewportSize({ width: 1180, height: 900 });
  const geometry1180 = await page.evaluate(() =>
    Math.round(document.querySelector(".db-project-card").getBoundingClientRect().width),
  );
  await page.setViewportSize({ width: 740, height: 900 });
  const narrow = await page.evaluate(() => ({
    columns: getComputedStyle(document.querySelector(".db-shell")).gridTemplateColumns,
    mobileToggle: getComputedStyle(
      document.querySelector(".db-mobile-nav-toggle"),
    ).display,
  }));

    const visibleText = await page.locator("body").innerText();
    const checks = {
    installed_runtime: true,
    english_default: english.title === "All matters" && english.locale === null,
    zh_cn_selectable: chinese.title === "全部事项" && chinese.locale === "zh-CN",
    same_revision_locale_reload:
      catalogRevision === apiZh.result.catalog.catalog_revision,
    standard_density_default: english.standard === "standard",
    compact_density_selectable: compact.density === "compact",
    density_semantics_preserved:
      JSON.stringify(english.ids) === JSON.stringify(compact.ids)
      && english.summaryCount === compact.summaryCount
      && english.peopleCount === compact.peopleCount
      && english.metricCount === english.cardCount * 3
      && compact.metricCount === 0,
    large_catalog_window:
      english.cardCount === 200
      && totalCount >= 210
      && loadedCatalogCount === totalCount,
    search_filter_state_preserved:
      searchState.resultCount === 1
      && searchState.density === "compact"
      && searchState.locale === "zh-CN",
    matter_detail_open_return:
      detail.focus === "detail-title" && restoredFocus === firstCardId,
    human_readable_timeline:
      timelineText.includes("事情发生时间") && timelineText.includes("记录时间"),
    representative_visual: english.imageCount >= 1,
    honest_visual_placeholder: english.placeholderCount >= 1,
    background_blocked_catalog_usable: blockedCount >= 1 && english.cardCount > 0,
    catalog_error_focus_and_recovery:
      errorFocus === "catalog-error" && errorRecovered,
    evidence_reveal_and_return:
      detail.sections.includes("evidenceList") && evidenceLoaded,
    optional_correction_recovery:
      detail.sections.includes("corrections") && correctionRecovered,
    optional_cover_correction:
      detail.sections.includes("cover") && coverCorrected,
    geometry_1880: compact.width === 180,
    geometry_1440: geometry1440 === 172,
    geometry_1180: geometry1180 > 0 && geometry1180 <= 180,
    narrow_geometry:
      narrow.columns !== "264px" && narrow.mobileToggle === "grid",
    private_internal_absent:
      !/[A-Z]:\\Users\\|message[_ -]?id|preview[_ -]?token|sha256:/i.test(visibleText),
    };
    const missing = Object.entries(checks)
    .filter(([, passed]) => !passed)
    .map(([name]) => name);
    const now = new Date().toISOString();
    const receipt = {
    artifact_type: "matters.live-ui-evidence.v1",
    generated_at: now,
    status: missing.length === 0 && errors.length === 0 ? "passed" : "blocked",
    evidence_id: `evidence:ui:${uiRevision.replace("sha256:", "").slice(0, 16)}`,
    ui_revision: uiRevision,
    checks,
    browser_errors: errors,
    missing_checks: missing,
    observed: {
      total_count: totalCount,
      standard_card_count: english.cardCount,
      loaded_catalog_count: loadedCatalogCount,
      compact_card_width_1880: compact.width,
      compact_card_width_1440: geometry1440,
      compact_card_width_1180: geometry1180,
      detail_sections: detail.sections,
      detail_geometry_1440: detail.dialog,
    },
    claim_boundary:
      "Public synthetic installed-runtime evidence proves UI behavior and geometry only; it does not substitute for the separate real-private first run.",
    };
    fs.mkdirSync(require("path").dirname(output), { recursive: true });
    fs.writeFileSync(output, `${JSON.stringify(receipt, null, 2)}\n`, "utf8");
    console.log(JSON.stringify(receipt, null, 2));
    process.exitCode = receipt.status === "passed" ? 0 : 1;
  } finally {
    phase("close browser");
    if (browser) await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
