"use strict";

const app = document.getElementById("app");
const STORAGE = {
  density: "matters-card-density",
  locale: "matters-locale",
};

const COPY = {
  en: {
    search: "Search matters",
    navigation: "Browse",
    all: "All matters",
    planned: "Planned",
    in_progress: "In progress",
    completed: "Completed",
    time: "Time",
    recent: "Recent",
    upcoming: "Upcoming",
    undated: "Undated",
    settings: "Settings",
    language: "Language",
    titleAll: "All matters",
    titleFiltered: "Filtered matters",
    matters: "matters",
    standard: "Standard",
    compact: "Compact",
    density: "Card density",
    coverage: "Coverage",
    coverageComplete: "Coverage current",
    coverageWorking: "Working in background",
    registered: "Registered",
    ready: "In browser",
    pending: "Still processing",
    blocked: "Blocked",
    imageUnavailable: "Image unavailable",
    noAuthorizedImage: "No current authorized image yet.",
    sources: "Sources",
    evidence: "Evidence",
    events: "Events",
    openLoops: "Open loops",
    relatedMatters: "Related matters",
    emptyTitle: "No matters match this view",
    emptyBody: "The browser updates automatically when source modeling reaches a visible result.",
    loadError: "Matters could not load the object browser.",
    retry: "Try again",
    moreMatters: "Load more matters",
    loadingMore: "Loading more matters…",
    moreFailed: "More matters could not be loaded.",
    menu: "Open navigation",
    close: "Close",
    overview: "Overview",
    timeline: "Timeline",
    people: "People",
    sourceList: "Sources",
    evidenceList: "Evidence",
    corrections: "Corrections",
    cover: "Cover",
    summary: "Summary",
    keyTime: "Key time",
    state: "State",
    uncertainty: "Uncertainty",
    currentBest: "Current best interpretation",
    noTimeline: "No dated event is available yet.",
    claimedTime: "Event time",
    recordTime: "Recorded",
    modality: "Basis",
    noPeople: "No person is currently linked with enough evidence.",
    noOpenLoops: "No current open loop needs attention.",
    noRelatedMatters: "No evidence-linked related matter is currently available.",
    waitTarget: "Waiting for",
    closureCondition: "Closes when",
    noSources: "No current source pointer is available.",
    revealEvidence: "Load evidence",
    evidencePrivacy: "Evidence stays on this computer and is shown only on demand.",
    noEvidence: "No displayable anchored evidence is available.",
    correctionHelp: "Add a correction after the automatic result. Matters keeps history and queues the affected owners to recompute.",
    fieldOptional: "Field (optional)",
    correctedValue: "Corrected value (optional)",
    rationale: "What should be corrected?",
    saveCorrection: "Save correction",
    correctionSaved: "Correction saved. Affected stages are recomputing.",
    correctionFailed: "The correction could not be saved.",
    correctionRetry: "Your correction was preserved. Review it and try again.",
    chooseCover: "Choose a representative image",
    automaticCover: "Use automatic selection",
    coverSaved: "Representative image updated.",
    coverFailed: "The representative image could not be updated.",
    noCoverCandidates: "No other current authorized visual candidates are available.",
    statusUnknown: "Uncertain",
    linked: "Linked",
    plannedBasis: "Planned",
    reportedBasis: "Reported",
    observedBasis: "Observed",
    inferredBasis: "Inferred",
    sourceOnly: "Source only",
    backgroundIdle: "Background is idle",
  },
  "zh-CN": {
    search: "搜索事项",
    navigation: "浏览",
    all: "全部事项",
    planned: "计划中",
    in_progress: "进行中",
    completed: "已完成",
    time: "时间",
    recent: "最近",
    upcoming: "即将发生",
    undated: "暂无日期",
    settings: "设置",
    language: "语言",
    titleAll: "全部事项",
    titleFiltered: "筛选后的事项",
    matters: "个事项",
    standard: "标准",
    compact: "紧凑",
    density: "卡片密度",
    coverage: "覆盖进度",
    coverageComplete: "覆盖已更新",
    coverageWorking: "正在后台处理",
    registered: "已登记",
    ready: "已进入浏览器",
    pending: "仍在处理",
    blocked: "受阻",
    imageUnavailable: "暂无图片",
    noAuthorizedImage: "目前还没有当前且已授权的图片。",
    sources: "来源",
    evidence: "证据",
    events: "事件",
    openLoops: "待闭环",
    relatedMatters: "关联事项",
    emptyTitle: "这个视图中还没有事项",
    emptyBody: "当来源建模得到可显示的结果后，对象浏览器会自动更新。",
    loadError: "Matters 暂时无法载入对象浏览器。",
    retry: "重试",
    moreMatters: "载入更多事项",
    loadingMore: "正在载入更多事项…",
    moreFailed: "暂时无法载入更多事项。",
    menu: "打开导航",
    close: "关闭",
    overview: "概览",
    timeline: "时间线",
    people: "人物",
    sourceList: "相关来源",
    evidenceList: "相关证据",
    corrections: "事后纠正",
    cover: "代表图片",
    summary: "摘要",
    keyTime: "关键时间",
    state: "状态",
    uncertainty: "不确定性",
    currentBest: "当前最佳解释",
    noTimeline: "目前还没有可显示日期的事件。",
    claimedTime: "事情发生时间",
    recordTime: "记录时间",
    modality: "判断依据",
    noPeople: "目前还没有证据足够的人物关联。",
    noOpenLoops: "目前没有需要处理的待闭环事项。",
    noRelatedMatters: "目前还没有由证据关联起来的其他事项。",
    waitTarget: "正在等待",
    closureCondition: "闭环条件",
    noSources: "目前还没有可显示的来源指针。",
    revealEvidence: "读取证据",
    evidencePrivacy: "证据只在本机保存，并且只有主动打开时才显示。",
    noEvidence: "目前没有可显示的定位证据。",
    correctionHelp: "在自动结果出来后补充纠正。Matters 会保留历史，并让受影响的 owner 自动重算。",
    fieldOptional: "字段（可选）",
    correctedValue: "纠正后的值（可选）",
    rationale: "哪里需要纠正？",
    saveCorrection: "保存纠正",
    correctionSaved: "纠正已保存，受影响的阶段正在重新计算。",
    correctionFailed: "纠正暂时无法保存。",
    correctionRetry: "纠正内容已保留，请检查后重试。",
    chooseCover: "选择代表图片",
    automaticCover: "使用自动选择",
    coverSaved: "代表图片已更新。",
    coverFailed: "代表图片暂时无法更新。",
    noCoverCandidates: "没有其他当前且已授权的视觉候选。",
    statusUnknown: "不确定",
    linked: "已关联",
    plannedBasis: "计划",
    reportedBasis: "报告",
    observedBasis: "观察",
    inferredBasis: "推断",
    sourceOnly: "仅来源",
    backgroundIdle: "后台当前空闲",
  },
};

const state = {
  locale: localStorage.getItem(STORAGE.locale) === "zh-CN" ? "zh-CN" : "en",
  density: localStorage.getItem(STORAGE.density) === "compact" ? "compact" : "standard",
  status: "all",
  time: "all",
  query: "",
  browser: null,
  loading: true,
  loadingMore: false,
  error: "",
  focusCatalogErrorOnRender: false,
  settingsOpen: false,
  healthOpen: false,
  mobileOpen: false,
  selectedMatterId: "",
  detail: null,
  detailLoading: false,
  detailSection: "overview",
  focusDetailOnRender: false,
  evidence: null,
  correctionDraft: { field_name: "", corrected_value: "", rationale: "" },
  correctionError: false,
  focusCorrectionErrorOnRender: false,
  toast: "",
  requestId: 0,
};

let catalogController = null;
let searchTimer = null;
let lastCardFocus = "";

function t(key) {
  return COPY[state.locale][key] || COPY.en[key] || key;
}

function value(map, fallback = "") {
  if (!map || typeof map !== "object") return fallback;
  return String(map[state.locale] || map.en || fallback);
}

function escapeHtml(input) {
  return String(input ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function icon(name) {
  const paths = {
    search: '<circle cx="11" cy="11" r="6"></circle><path d="m16 16 4 4"></path>',
    all: '<rect x="4" y="4" width="6" height="6" rx="1"></rect><rect x="14" y="4" width="6" height="6" rx="1"></rect><rect x="4" y="14" width="6" height="6" rx="1"></rect><rect x="14" y="14" width="6" height="6" rx="1"></rect>',
    planned: '<circle cx="12" cy="12" r="8"></circle><path d="M12 8v5l3 2"></path>',
    progress: '<circle cx="12" cy="12" r="8"></circle><path d="M12 4a8 8 0 0 1 8 8"></path><path d="M12 12V7"></path>',
    completed: '<circle cx="12" cy="12" r="8"></circle><path d="m8 12 3 3 5-6"></path>',
    calendar: '<rect x="4" y="6" width="16" height="14" rx="2"></rect><path d="M8 3v5M16 3v5M4 10h16"></path>',
    settings: '<circle cx="12" cy="12" r="3"></circle><path d="M19 12a7 7 0 0 0-.1-1l2-1.6-2-3.4-2.5 1a7 7 0 0 0-1.7-1L14.3 3h-4.6L9.3 6a7 7 0 0 0-1.7 1L5.1 6 3 9.4 5.1 11a7 7 0 0 0 0 2L3 14.6 5.1 18l2.5-1a7 7 0 0 0 1.7 1l.4 3h4.6l.4-3a7 7 0 0 0 1.7-1l2.5 1 2.1-3.4-2.1-1.6a7 7 0 0 0 .1-1Z"></path>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2"></rect><circle cx="8" cy="9" r="2"></circle><path d="m4 18 5-5 3 3 3-4 5 6"></path>',
    overview: '<path d="M4 5h16M4 12h16M4 19h10"></path>',
    timeline: '<path d="M7 4v16M7 7h8M7 12h11M7 17h6"></path>',
    people: '<circle cx="9" cy="8" r="3"></circle><circle cx="17" cy="9" r="2"></circle><path d="M4 20c0-4 2-7 5-7s5 3 5 7M14 15c3 0 5 2 5 5"></path>',
    source: '<path d="M7 3h8l4 4v14H7z"></path><path d="M15 3v5h4M10 13h6M10 17h6"></path>',
    evidence: '<path d="M5 4h14v16H5z"></path><path d="m8 12 2 2 5-5M8 17h8"></path>',
    correction: '<path d="m4 20 4-1 10-10-3-3L5 16z"></path><path d="m13 8 3 3"></path>',
    cover: '<rect x="3" y="5" width="18" height="14" rx="2"></rect><path d="m4 17 5-5 3 3 3-4 5 6"></path>',
  };
  return `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.overview}</svg>`;
}

function stateLabel(card) {
  const canonical = String(card.state || "uncertain").replaceAll("_", " ");
  const labels = {
    en: {
      planned: "Planned",
      in_progress: "In progress",
      completed: "Completed",
      waiting: "Waiting",
      blocked: "Blocked",
      uncertain: "Uncertain",
      completion_unproven: "Completion unproven",
      outcome_conflict: "Outcome conflict",
    },
    "zh-CN": {
      planned: "计划中",
      in_progress: "进行中",
      completed: "已完成",
      waiting: "等待中",
      blocked: "受阻",
      uncertain: "不确定",
      completion_unproven: "完成尚未证明",
      outcome_conflict: "结果存在冲突",
    },
  };
  return labels[state.locale][card.state] || canonical;
}

function currentCatalog() {
  return state.browser?.catalog || {
    items: [],
    total_count: 0,
    facets: { status: { all: 0, planned: 0, in_progress: 0, completed: 0 } },
  };
}

function saveViewState() {
  const main = document.querySelector(".db-main");
  return {
    scrollTop: main?.scrollTop || 0,
    activeId: document.activeElement?.id || "",
  };
}

function restoreViewState(snapshot) {
  requestAnimationFrame(() => {
    const main = document.querySelector(".db-main");
    if (main) main.scrollTop = snapshot.scrollTop;
    if (snapshot.activeId) document.getElementById(snapshot.activeId)?.focus();
  });
}

function navItem(key, status, iconName) {
  const count = currentCatalog().facets?.status?.[status] ?? 0;
  return `<button type="button" class="db-nav-item" data-status="${status}" aria-current="${state.status === status ? "page" : "false"}">
    <span class="db-nav-icon">${icon(iconName)}</span>
    <span class="db-nav-label">${escapeHtml(t(key))}</span>
    <span class="db-nav-count">${count}</span>
  </button>`;
}

function timeItem(key, timeFilter) {
  return `<button type="button" class="db-nav-item" data-time="${timeFilter}" aria-current="${state.time === timeFilter ? "page" : "false"}">
    <span class="db-nav-icon">${icon("calendar")}</span>
    <span class="db-nav-label">${escapeHtml(t(key))}</span>
    <span></span>
  </button>`;
}

function coveragePanel() {
  if (!state.healthOpen) return "";
  const coverage = state.browser?.coverage || {};
  return `<section class="db-source-health-panel" role="dialog" aria-label="${escapeHtml(t("coverage"))}">
    <h3>${escapeHtml(t("coverage"))}</h3>
    <p>${escapeHtml(coverage.coverage_status === "complete" ? t("coverageComplete") : t("coverageWorking"))}</p>
    <dl class="db-coverage-facts">
      <div><dt>${escapeHtml(t("registered"))}</dt><dd>${coverage.registered_object_count || 0}</dd></div>
      <div><dt>${escapeHtml(t("ready"))}</dt><dd>${coverage.ui_ready_object_count || 0}</dd></div>
      <div><dt>${escapeHtml(t("pending"))}</dt><dd>${coverage.pending_object_count || 0}</dd></div>
      <div><dt>${escapeHtml(t("blocked"))}</dt><dd>${coverage.blocked_object_count || 0}</dd></div>
    </dl>
  </section>`;
}

function cardHtml(card) {
  const title = value(card.title, state.locale === "en" ? "Untitled matter" : "未命名事项");
  const summary = value(card.summary, title);
  const people = (card.people || []).map((person) => person.name).filter(Boolean).join(", ");
  const visual = card.visual || {};
  const hasImage = visual.status === "current" && visual.preview_token;
  const year = String(card.key_time || "").match(/\b(20\d{2})\b/)?.[1] || "—";
  const metrics = state.density === "standard" ? `<div class="db-card-metrics">
    <div class="db-card-metric"><strong>${card.event_count || 0}</strong><span>${escapeHtml(t("events"))}</span></div>
    <div class="db-card-metric"><strong>${card.people_count || 0}</strong><span>${escapeHtml(t("people"))}</span></div>
    <div class="db-card-metric"><strong>${card.source_count || 0}</strong><span>${escapeHtml(t("sources"))}</span></div>
  </div>` : "";
  return `<article
    id="matter-card-${escapeHtml(card.matter_id)}"
    class="db-project-card db-project-card--${state.density}"
    data-matter-id="${escapeHtml(card.matter_id)}"
    role="button"
    tabindex="0"
    aria-label="${escapeHtml(title)}"
  >
    <header class="db-card-header"><h3 class="db-card-title" title="${escapeHtml(title)}">${escapeHtml(title)}</h3></header>
    <div class="db-card-meta">
      <span class="db-card-type">${icon("overview")}${escapeHtml(stateLabel(card))}</span>
      <span aria-hidden="true">·</span>
      <span class="db-card-year">${escapeHtml(year)}</span>
    </div>
    <section class="db-card-media" aria-label="${escapeHtml(value(visual.alt, title))}">
      ${hasImage
        ? `<img src="/api/visuals/${encodeURIComponent(visual.preview_token)}" alt="${escapeHtml(value(visual.alt, title))}" loading="lazy" decoding="async">`
        : `<div class="db-card-empty-media">${icon("image")}<strong>${escapeHtml(t("imageUnavailable"))}</strong><span>${escapeHtml(t("noAuthorizedImage"))}</span></div>`}
      <div class="db-card-copy">
        <p class="db-card-summary">${escapeHtml(summary)}</p>
        <p class="db-card-people">${escapeHtml(people || t("noPeople"))}</p>
      </div>
    </section>
    ${metrics}
  </article>`;
}

function gridHtml() {
  if (state.loading) {
    return `<div class="db-empty-state" role="status">${escapeHtml(t("coverageWorking"))}</div>`;
  }
  if (state.error) {
    return `<div id="catalog-error" class="db-error-state" role="alert" tabindex="-1"><strong>${escapeHtml(t("loadError"))}</strong><p>${escapeHtml(state.error)}</p><button class="db-primary-button" data-retry>${escapeHtml(t("retry"))}</button></div>`;
  }
  const cards = currentCatalog().items || [];
  if (!cards.length) {
    return `<div class="db-empty-state" role="status"><strong>${escapeHtml(t("emptyTitle"))}</strong><p>${escapeHtml(t("emptyBody"))}</p></div>`;
  }
  return `${cards.map(cardHtml).join("")}${
    currentCatalog().has_more
      ? `<button type="button" class="db-load-more" data-load-more ${state.loadingMore ? "disabled" : ""}>${escapeHtml(state.loadingMore ? t("loadingMore") : t("moreMatters"))}</button>`
      : ""
  }`;
}

function detailNavItem(section, key, count = "") {
  return `<button type="button" id="detail-nav-${section}" class="db-detail-nav-item" data-detail-section="${section}" aria-current="${state.detailSection === section ? "page" : "false"}">
    <span>${icon(section === "sourceList" ? "source" : section === "evidenceList" ? "evidence" : section)}</span>
    <span>${escapeHtml(t(key))}</span>
    <span class="db-detail-nav-count">${count}</span>
  </button>`;
}

function detailOverview(detail) {
  const card = detail.matter;
  const visual = card.visual || {};
  const hasImage = visual.status === "current" && visual.preview_token;
  return `<div class="db-detail-hero">
    <section class="db-detail-visual">
      ${hasImage
        ? `<img src="/api/visuals/${encodeURIComponent(visual.preview_token)}?size=hero" alt="${escapeHtml(value(visual.alt, value(card.title)))}">`
        : `<div class="db-card-empty-media">${icon("image")}<strong>${escapeHtml(t("imageUnavailable"))}</strong><span>${escapeHtml(t("noAuthorizedImage"))}</span></div>`}
    </section>
    <section class="db-detail-summary">
      <h4>${escapeHtml(t("summary"))}</h4>
      <p>${escapeHtml(value(card.summary, value(card.title)))}</p>
      <dl class="db-detail-facts">
        <div><dt>${escapeHtml(t("state"))}</dt><dd>${escapeHtml(stateLabel(card))}</dd></div>
        <div><dt>${escapeHtml(t("keyTime"))}</dt><dd>${escapeHtml(card.key_time || "—")}</dd></div>
        <div><dt>${escapeHtml(t("sources"))}</dt><dd>${card.source_count || 0}</dd></div>
        <div><dt>${escapeHtml(t("evidence"))}</dt><dd>${card.evidence_count || 0}</dd></div>
      </dl>
      ${card.uncertainty ? `<p class="db-list-meta">${escapeHtml(t("currentBest"))}</p>` : ""}
    </section>
  </div>`;
}

function detailTimeline(detail) {
  if (!detail.timeline?.length) return `<div class="db-empty-state">${escapeHtml(t("noTimeline"))}</div>`;
  return `<div class="db-timeline">${detail.timeline.map((entry) => `<article class="db-timeline-entry">
    <p>${escapeHtml(value(entry.sentence))}</p>
    <p class="db-list-meta">${escapeHtml(t("claimedTime"))}: ${escapeHtml(entry.claimed_time || "—")} · ${escapeHtml(t("recordTime"))}: ${escapeHtml(entry.record_time || "—")} · ${escapeHtml(t("modality"))}: ${escapeHtml(t(`${entry.modality || "inferred"}Basis`))}</p>
  </article>`).join("")}</div>`;
}

function detailPeople(detail) {
  if (!detail.people?.length) return `<div class="db-empty-state">${escapeHtml(t("noPeople"))}</div>`;
  return `<ul class="db-list">${detail.people.map((person) => `<li class="db-list-item"><h4>${escapeHtml(person.name)}</h4><p class="db-list-meta">${escapeHtml(person.resolved ? t("linked") : t("statusUnknown"))}</p></li>`).join("")}</ul>`;
}

function detailOpenLoops(detail) {
  if (!detail.open_loops?.length) return `<div class="db-empty-state">${escapeHtml(t("noOpenLoops"))}</div>`;
  return `<ul class="db-list">${detail.open_loops.map((loop) => `<li class="db-list-item">
    <h4>${escapeHtml(loop.wait_target || t("openLoops"))}</h4>
    <p>${escapeHtml(t("waitTarget"))}: ${escapeHtml(loop.wait_target || "—")}</p>
    <p class="db-list-meta">${escapeHtml(t("closureCondition"))}: ${escapeHtml(loop.closure_condition || "—")} · ${escapeHtml(loop.status || "open")}</p>
  </li>`).join("")}</ul>`;
}

function detailRelated(detail) {
  if (!detail.related_matters?.length) return `<div class="db-empty-state">${escapeHtml(t("noRelatedMatters"))}</div>`;
  return `<ul class="db-list">${detail.related_matters.map((matter) => `<li class="db-list-item">
    <button type="button" class="db-related-matter" data-related-matter="${escapeHtml(matter.matter_id)}">
      <strong>${escapeHtml(value(matter.title))}</strong>
      <span>${escapeHtml(value(matter.summary))}</span>
    </button>
  </li>`).join("")}</ul>`;
}

function detailSources(detail) {
  if (!detail.sources?.length) return `<div class="db-empty-state">${escapeHtml(t("noSources"))}</div>`;
  return `<ul class="db-list">${detail.sources.map((source) => `<li class="db-list-item">
    <h4>${escapeHtml(source.object_type || source.provider)}</h4>
    <p>${escapeHtml(source.provider)} · ${escapeHtml(value(source.disposition_label, source.disposition))}</p>
    ${source.next_stage ? `<p class="db-list-meta">${escapeHtml(source.next_stage)}</p>` : ""}
  </li>`).join("")}</ul>`;
}

function detailEvidence() {
  if (!state.evidence) {
    return `<section class="db-correction-form"><p>${escapeHtml(t("evidencePrivacy"))}</p><button class="db-primary-button" data-load-evidence>${escapeHtml(t("revealEvidence"))}</button></section>`;
  }
  if (!state.evidence.items?.length) return `<div class="db-empty-state">${escapeHtml(t("noEvidence"))}</div>`;
  return `<ul class="db-list">${state.evidence.items.map((entry) => `<li class="db-list-item">
    <p class="db-evidence-excerpt">${escapeHtml(entry.excerpt)}</p>
    <p class="db-list-meta">${escapeHtml(entry.modality)} · ${escapeHtml(JSON.stringify(entry.location || {}))}</p>
  </li>`).join("")}</ul>`;
}

function detailCorrections() {
  return `<section>
    <form class="db-correction-form" data-correction-form>
      <p>${escapeHtml(t("correctionHelp"))}</p>
      ${state.correctionError ? `<p id="correction-error" class="db-inline-error" role="alert" tabindex="-1"><strong>${escapeHtml(t("correctionFailed"))}</strong><span>${escapeHtml(t("correctionRetry"))}</span></p>` : ""}
      <label>${escapeHtml(t("fieldOptional"))}<input name="field_name" value="${escapeHtml(state.correctionDraft.field_name)}" autocomplete="off"></label>
      <label>${escapeHtml(t("correctedValue"))}<input name="corrected_value" value="${escapeHtml(state.correctionDraft.corrected_value)}" autocomplete="off"></label>
      <label>${escapeHtml(t("rationale"))}<textarea name="rationale" required>${escapeHtml(state.correctionDraft.rationale)}</textarea></label>
      <button class="db-primary-button" type="submit">${escapeHtml(t("saveCorrection"))}</button>
    </form>
  </section>`;
}

function detailCover(detail) {
  const current = detail.matter.visual?.asset_id || "";
  const candidates = detail.visual_candidates || [];
  if (!candidates.length) return `<div class="db-empty-state">${escapeHtml(t("noCoverCandidates"))}</div>`;
  return `<section>
    <h4>${escapeHtml(t("chooseCover"))}</h4>
    <div class="db-cover-grid">
      ${candidates.map((asset) => `<button type="button" class="db-cover-option" data-cover-asset="${escapeHtml(asset.asset_id)}" aria-pressed="${asset.asset_id === current}">
        <img src="/api/visuals/${encodeURIComponent(asset.preview_token)}" alt="${escapeHtml(value(asset.alt))}">
        <span>${escapeHtml(value(asset.reason, asset.kind))}</span>
      </button>`).join("")}
      <button type="button" class="db-cover-option" data-cover-auto aria-pressed="false">${icon("image")}<span>${escapeHtml(t("automaticCover"))}</span></button>
    </div>
  </section>`;
}

function detailBody(detail) {
  return {
    overview: detailOverview,
    timeline: detailTimeline,
    people: detailPeople,
    openLoops: detailOpenLoops,
    relatedMatters: detailRelated,
    sourceList: detailSources,
    evidenceList: detailEvidence,
    corrections: detailCorrections,
    cover: detailCover,
  }[state.detailSection]?.(detail) || detailOverview(detail);
}

function detailHtml() {
  if (!state.selectedMatterId) return "";
  if (state.detailLoading || !state.detail) {
    return `<div class="db-dialog-overlay"><section class="db-dialog"><aside class="db-detail-rail"></aside><main class="db-detail-reader">${escapeHtml(t("coverageWorking"))}</main></section></div>`;
  }
  const detail = state.detail;
  const card = detail.matter;
  return `<div class="db-dialog-overlay" data-dialog-overlay>
    <section class="db-dialog" role="dialog" aria-modal="true" aria-labelledby="detail-title">
      <button class="db-dialog-close" data-close-detail aria-label="${escapeHtml(t("close"))}">×</button>
      <aside class="db-detail-rail">
        <header class="db-detail-brand"><div class="db-detail-brand-heading"><div class="db-brand-mark">M</div><h2 id="detail-title" tabindex="-1">${escapeHtml(value(card.title))}</h2></div></header>
        <nav class="db-detail-nav" aria-label="${escapeHtml(t("navigation"))}">
          ${detailNavItem("overview", "overview")}
          ${detailNavItem("timeline", "timeline", detail.timeline?.length || 0)}
          ${detailNavItem("people", "people", detail.people?.length || 0)}
          ${detailNavItem("openLoops", "openLoops", detail.open_loops?.length || 0)}
          ${detailNavItem("relatedMatters", "relatedMatters", detail.related_matters?.length || 0)}
          ${detailNavItem("sourceList", "sourceList", detail.sources?.length || 0)}
          ${detailNavItem("evidenceList", "evidenceList", card.evidence_count || 0)}
          ${detailNavItem("corrections", "corrections", detail.corrections?.length || 0)}
          ${detailNavItem("cover", "cover", detail.visual_candidates?.length || 0)}
        </nav>
      </aside>
      <main class="db-detail-reader">
        <header class="db-reader-header"><h3>${escapeHtml(t(state.detailSection))}</h3><span class="db-status-chip" data-group="${escapeHtml(card.status_group)}">${escapeHtml(stateLabel(card))}</span></header>
        ${detailBody(detail)}
      </main>
    </section>
  </div>`;
}

function render() {
  const snapshot = saveViewState();
  const catalog = currentCatalog();
  const coverage = state.browser?.coverage || {};
  const healthTone = coverage.coverage_status === "complete" ? "healthy" : coverage.blocked_object_count ? "unavailable" : "changed";
  app.innerHTML = `
    <button class="db-mobile-nav-toggle" data-mobile-menu aria-label="${escapeHtml(t("menu"))}">☰</button>
    ${state.mobileOpen ? '<button class="db-sidebar-backdrop" data-mobile-close aria-label="Close"></button>' : ""}
    <div class="db-shell" data-browser-shell-layout>
      <aside class="db-sidebar" data-open="${state.mobileOpen}">
        <div class="db-sidebar-top">
          <header class="db-sidebar-brand"><div class="db-sidebar-brand-copy"><div class="db-brand-mark">M</div><h1>Matters</h1></div></header>
          <label class="db-search-shell">
            <span class="db-search-icon">${icon("search")}</span>
            <span class="db-sr-only">${escapeHtml(t("search"))}</span>
            <input id="matters-search" class="db-search-input" type="search" value="${escapeHtml(state.query)}" placeholder="${escapeHtml(t("search"))}">
          </label>
        </div>
        <div class="db-sidebar-scroll">
          <p class="db-sidebar-heading">${escapeHtml(t("navigation"))}</p>
          <nav class="db-nav-list">
            ${navItem("all", "all", "all")}
            ${navItem("planned", "planned", "planned")}
            ${navItem("in_progress", "in_progress", "progress")}
            ${navItem("completed", "completed", "completed")}
          </nav>
          <p class="db-sidebar-heading" style="margin-top:22px">${escapeHtml(t("time"))}</p>
          <nav class="db-nav-list">
            ${timeItem("all", "all")}
            ${timeItem("recent", "recent")}
            ${timeItem("upcoming", "upcoming")}
            ${timeItem("undated", "undated")}
          </nav>
        </div>
        <footer class="db-sidebar-footer">
          <button class="db-sidebar-settings" data-settings aria-expanded="${state.settingsOpen}"><span>${icon("settings")}</span><span>${escapeHtml(t("settings"))}</span></button>
          ${state.settingsOpen ? `<div class="db-settings-menu"><label class="db-settings-language-field"><span>${escapeHtml(t("language"))}</span><select id="locale-select"><option value="en" ${state.locale === "en" ? "selected" : ""}>English</option><option value="zh-CN" ${state.locale === "zh-CN" ? "selected" : ""}>中文</option></select></label></div>` : ""}
        </footer>
      </aside>
      <main class="db-main">
        <header class="db-project-list-header">
          <h2>${escapeHtml(state.status === "all" && state.time === "all" && !state.query ? t("titleAll") : t("titleFiltered"))}</h2>
          <div class="db-project-header-meta">
            <span>${catalog.total_count || 0} · ${escapeHtml(t("matters"))}</span>
            <button type="button" class="db-card-density-switch" role="switch" aria-checked="${state.density === "compact"}" data-density aria-label="${escapeHtml(t("density"))}">
              <span class="${state.density === "standard" ? "is-active" : ""}">${escapeHtml(t("standard"))}</span><span class="db-card-density-track"><span></span></span><span class="${state.density === "compact" ? "is-active" : ""}">${escapeHtml(t("compact"))}</span>
            </button>
            <div class="db-source-health">
              <button type="button" class="db-source-health-button" data-health data-tone="${healthTone}" aria-expanded="${state.healthOpen}">
                <span class="db-source-health-light"></span><span class="db-source-health-labels"><strong>${escapeHtml(t("coverage"))}</strong><span>${coverage.ui_ready_object_count || 0}/${coverage.registered_object_count || 0}</span></span>
              </button>
              ${coveragePanel()}
            </div>
          </div>
        </header>
        <section class="db-project-grid" data-card-density="${state.density}" aria-label="${escapeHtml(t("titleAll"))}">
          ${gridHtml()}
        </section>
      </main>
    </div>
    ${detailHtml()}
    ${state.toast ? `<div class="db-toast" role="status">${escapeHtml(state.toast)}</div>` : ""}
  `;
  restoreViewState(snapshot);
  if (state.selectedMatterId && state.focusDetailOnRender) {
    requestAnimationFrame(() => {
      const title = document.getElementById("detail-title");
      if (!title) return;
      title.focus();
      state.focusDetailOnRender = false;
    });
  }
  if (state.focusCatalogErrorOnRender) {
    requestAnimationFrame(() => {
      document.getElementById("catalog-error")?.focus();
      state.focusCatalogErrorOnRender = false;
    });
  }
  if (state.focusCorrectionErrorOnRender) {
    requestAnimationFrame(() => {
      document.getElementById("correction-error")?.focus();
      state.focusCorrectionErrorOnRender = false;
    });
  }
}

async function fetchJson(url, options) {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
  });
  const payload = await response.json();
  if (!response.ok || payload.ok !== true) {
    throw new Error(payload.error?.code || `HTTP ${response.status}`);
  }
  return payload.result;
}

async function loadBrowser() {
  const requestId = ++state.requestId;
  catalogController?.abort();
  catalogController = new AbortController();
  state.loading = true;
  state.error = "";
  render();
  const params = new URLSearchParams({
    locale: state.locale,
    query: state.query,
    status: state.status,
    time: state.time,
    sort: "recent",
    offset: "0",
    limit: "200",
  });
  try {
    const result = await fetchJson(`/api/browser?${params}`, { signal: catalogController.signal });
    if (requestId !== state.requestId) return;
    state.browser = result;
    state.loading = false;
    render();
  } catch (error) {
    if (error.name === "AbortError") return;
    if (requestId !== state.requestId) return;
    state.loading = false;
    state.error = error.message;
    state.focusCatalogErrorOnRender = true;
    render();
  }
}

async function loadMore() {
  const catalog = currentCatalog();
  if (state.loadingMore || !catalog.has_more || catalog.next_offset == null) return;
  state.loadingMore = true;
  render();
  const params = new URLSearchParams({
    locale: state.locale,
    query: state.query,
    status: state.status,
    time: state.time,
    sort: "recent",
    offset: String(catalog.next_offset),
    limit: "200",
  });
  try {
    const result = await fetchJson(`/api/browser?${params}`);
    const existing = currentCatalog().items || [];
    const seen = new Set(existing.map((item) => item.matter_id));
    const appended = (result.catalog.items || []).filter(
      (item) => !seen.has(item.matter_id),
    );
    state.browser = {
      ...result,
      catalog: {
        ...result.catalog,
        items: [...existing, ...appended],
      },
    };
  } catch {
    showToast(t("moreFailed"));
  } finally {
    state.loadingMore = false;
    render();
  }
}

async function openDetail(matterId) {
  lastCardFocus = `matter-card-${matterId}`;
  state.selectedMatterId = matterId;
  state.detailLoading = true;
  state.detail = null;
  state.detailSection = "overview";
  state.focusDetailOnRender = true;
  state.evidence = null;
  state.correctionError = false;
  render();
  try {
    state.detail = await fetchJson(`/api/matters/${encodeURIComponent(matterId)}?locale=${encodeURIComponent(state.locale)}`);
    state.detailLoading = false;
    render();
  } catch (error) {
    state.detailLoading = false;
    state.toast = error.message;
    closeDetail();
  }
}

function closeDetail() {
  state.selectedMatterId = "";
  state.detail = null;
  state.focusDetailOnRender = false;
  state.evidence = null;
  state.correctionDraft = { field_name: "", corrected_value: "", rationale: "" };
  state.correctionError = false;
  render();
  requestAnimationFrame(() => document.getElementById(lastCardFocus)?.focus());
}

async function loadEvidence() {
  if (!state.selectedMatterId) return;
  try {
    state.evidence = await fetchJson(`/api/matters/${encodeURIComponent(state.selectedMatterId)}/evidence?limit=200`);
    render();
  } catch (error) {
    showToast(error.message);
  }
}

function showToast(message) {
  state.toast = message;
  render();
  window.setTimeout(() => {
    if (state.toast === message) {
      state.toast = "";
      render();
    }
  }, 3500);
}

async function submitCorrection(form) {
  const formData = new FormData(form);
  state.correctionDraft = {
    field_name: String(formData.get("field_name") || ""),
    corrected_value: String(formData.get("corrected_value") || ""),
    rationale: String(formData.get("rationale") || ""),
  };
  state.correctionError = false;
  try {
    await fetchJson(`/api/matters/${encodeURIComponent(state.selectedMatterId)}/corrections`, {
      method: "POST",
      body: JSON.stringify({
        field_name: formData.get("field_name") || "",
        corrected_value: formData.get("corrected_value") || "",
        rationale: formData.get("rationale") || "",
      }),
    });
    state.correctionDraft = { field_name: "", corrected_value: "", rationale: "" };
    showToast(t("correctionSaved"));
    await openDetail(state.selectedMatterId);
  } catch {
    state.correctionError = true;
    state.focusCorrectionErrorOnRender = true;
    render();
  }
}

async function setCover(assetId, active) {
  try {
    await fetchJson(`/api/matters/${encodeURIComponent(state.selectedMatterId)}/cover`, {
      method: "POST",
      body: JSON.stringify({
        asset_id: assetId,
        active,
        rationale: active ? "user_selected_representative_visual" : "return_to_automatic_visual_selection",
      }),
    });
    showToast(t("coverSaved"));
    await openDetail(state.selectedMatterId);
    await loadBrowser();
  } catch {
    showToast(t("coverFailed"));
  }
}

app.addEventListener("click", (event) => {
  const target = event.target instanceof Element ? event.target : null;
  if (!target) return;
  const status = target.closest("[data-status]")?.dataset.status;
  if (status) {
    state.status = status;
    state.mobileOpen = false;
    loadBrowser();
    return;
  }
  const time = target.closest("[data-time]")?.dataset.time;
  if (time) {
    state.time = time;
    state.mobileOpen = false;
    loadBrowser();
    return;
  }
  const relatedMatter = target.closest("[data-related-matter]")?.dataset.relatedMatter;
  if (relatedMatter) {
    openDetail(relatedMatter);
    return;
  }
  if (target.closest("[data-load-more]")) {
    loadMore();
    return;
  }
  const card = target.closest("[data-matter-id]");
  if (card) {
    openDetail(card.dataset.matterId);
    return;
  }
  if (target.closest("[data-density]")) {
    state.density = state.density === "standard" ? "compact" : "standard";
    localStorage.setItem(STORAGE.density, state.density);
    render();
    return;
  }
  if (target.closest("[data-health]")) {
    state.healthOpen = !state.healthOpen;
    state.settingsOpen = false;
    render();
    return;
  }
  if (target.closest("[data-settings]")) {
    state.settingsOpen = !state.settingsOpen;
    state.healthOpen = false;
    render();
    return;
  }
  if (target.closest("[data-mobile-menu]")) {
    state.mobileOpen = true;
    render();
    return;
  }
  if (target.closest("[data-mobile-close]")) {
    state.mobileOpen = false;
    render();
    return;
  }
  if (target.closest("[data-close-detail]") || (target.matches("[data-dialog-overlay]"))) {
    closeDetail();
    return;
  }
  const section = target.closest("[data-detail-section]")?.dataset.detailSection;
  if (section) {
    state.detailSection = section;
    render();
    return;
  }
  if (target.closest("[data-load-evidence]")) {
    loadEvidence();
    return;
  }
  const cover = target.closest("[data-cover-asset]")?.dataset.coverAsset;
  if (cover) {
    setCover(cover, true);
    return;
  }
  if (target.closest("[data-cover-auto]")) {
    setCover("", false);
    return;
  }
  if (target.closest("[data-retry]")) loadBrowser();
});

app.addEventListener("keydown", (event) => {
  const target = event.target instanceof Element ? event.target : null;
  const card = target?.closest("[data-matter-id]");
  if (card && !event.repeat && (event.key === "Enter" || event.key === " ")) {
    event.preventDefault();
    openDetail(card.dataset.matterId);
  }
});

app.addEventListener("input", (event) => {
  const target = event.target;
  if (
    (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement)
    && target.closest("[data-correction-form]")
    && target.name in state.correctionDraft
  ) {
    state.correctionDraft[target.name] = target.value;
    return;
  }
  if (!(target instanceof HTMLInputElement) || target.id !== "matters-search") return;
  state.query = target.value;
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(loadBrowser, 240);
});

app.addEventListener("change", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement) || target.id !== "locale-select") return;
  state.locale = target.value === "zh-CN" ? "zh-CN" : "en";
  localStorage.setItem(STORAGE.locale, state.locale);
  state.settingsOpen = false;
  loadBrowser();
  if (state.selectedMatterId) openDetail(state.selectedMatterId);
});

app.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || !form.matches("[data-correction-form]")) return;
  event.preventDefault();
  submitCorrection(form);
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Tab" && state.selectedMatterId) {
    const dialog = document.querySelector(".db-dialog");
    const focusable = dialog
      ? [...dialog.querySelectorAll(
          'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
        )].filter((node) => node.getClientRects().length > 0)
      : [];
    if (focusable.length) {
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (
        document.activeElement === first
        || !dialog.contains(document.activeElement)
        || !focusable.includes(document.activeElement)
      )) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }
  if (event.key === "Escape") {
    if (state.selectedMatterId) closeDetail();
    else if (state.mobileOpen || state.settingsOpen || state.healthOpen) {
      state.mobileOpen = false;
      state.settingsOpen = false;
      state.healthOpen = false;
      render();
    }
  }
});

loadBrowser();
