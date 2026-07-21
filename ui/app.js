"use strict";

const app = document.getElementById("app");
const STORAGE = {
  density: "matters-card-density",
  locale: "matters-locale",
};
const API_TIMEOUT_MS = 12_000;

const COPY = {
  en: {
    search: "Search matters",
    navigation: "Browse",
    all: "All matters",
    status: "Status",
    planned: "Planned",
    in_progress: "In progress",
    completed: "Completed",
    startTime: "Start time",
    allYears: "All years",
    peopleFilter: "People",
    relationshipsFilter: "Relationships",
    topicTypeFilter: "Topic / Type",
    sourceTypeFilter: "Source type",
    noFilterValues: "No modeled values yet",
    clearFilter: "Clear",
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
    coverageBlocked: "Coverage is blocked",
    coverageStale: "Coverage needs refresh",
    coverageUnavailable: "Coverage audit unavailable",
    coverageFirstGaps: "First incomplete stages",
    coverageTotalSurfaces: "All surfaces",
    coverageCurrentSurfaces: "Current surfaces",
    coverageGapSurfaces: "Surfaces with gaps",
    coverageSurfaceGaps: "Surface gaps",
    coverageSurfaces: "Audited surfaces",
    coverageApplicability: "Surface applicability",
    coverageAuditLoading: "Checking every registered surface…",
    coverageAuditError: "The surface audit could not be loaded.",
    coverageClearDrilldown: "Show all surfaces",
    coverageOwner: "Owner",
    coverageFailure: "Failure",
    coverageFreshness: "Freshness",
    coverageUiReady: "UI ready",
    systemSurface: "System",
    rootMatterSurface: "Root Matter",
    childMatterSurface: "Child Matter",
    occurrenceSurface: "Source occurrence",
    yes: "Yes",
    no: "No",
    loadingTitle: "Loading your Matters",
    loadingBody: "Connecting to the local Matters service.",
    processingTitle: "Your sources are still being modeled",
    processingBody: "The browser will refresh automatically as Matters become ready.",
    honestEmptyTitle: "No Matter has been modeled yet",
    honestEmptyBody: "The local service is connected and the registered source scope is currently empty.",
    noFilterResultsTitle: "No matters match these filters",
    noFilterResultsBody: "Your modeled Matters are still available. Clear or change a filter to see them.",
    staleTitle: "Showing the last successful view",
    staleBody: "The local service is temporarily unreachable. Matters is reconnecting automatically.",
    transportErrorTitle: "Matters cannot reach the local service",
    transportErrorBody: "Nothing has been reported as empty. Matters will keep trying in the background.",
    reconnecting: "Reconnecting automatically",
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
    subMatters: "Sub-matters",
    subMatter: "Sub-matter",
    childStatus: "Status",
    childTime: "Start / next time",
    childResult: "Latest result / next step",
    childFiles: "Related files",
    noSubMatters: "No current sub-matter is modeled for this Matter.",
    subMattersUnavailable: "Sub-matters are temporarily unavailable.",
    graphHelp: "Drag to move, use the wheel or controls to zoom, and select any node for a single-layer quick view.",
    resetGraph: "Reset view",
    graphZoomIn: "Zoom in",
    graphZoomOut: "Zoom out",
    collapseBranch: "Collapse branch",
    expandBranch: "Expand branch",
    quickView: "Quick view",
    quickViewLoading: "Loading this quick view…",
    summaryCurrentState: "Summary & current state",
    factsAndProgress: "Facts and progress",
    noFacts: "No directly related facts are available yet.",
    filesLocations: "Files & information locations",
    closeQuickView: "Close quick view",
    graphUnavailable: "The Matter map is temporarily unavailable.",
    moreSubMatters: "Load more branches",
    loadingMoreSubMatters: "Loading more branches…",
    confirmedObserved: "Confirmed / observed",
    aiInferred: "AI inferred",
    aiHistoricalInference: "AI historical inference",
    reportedCertainty: "Source record",
    plannedCertainty: "Planned",
    previousPage: "Previous",
    nextPage: "Next",
    page: "Page",
    backToParent: "Back to parent Matter",
    openSubMatter: "Open sub-matter",
    viewFiles: "View related files",
    unknownCount: "Unavailable",
    showingLastKnown: "Showing the last successfully loaded Matters.",
    path: "Path",
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
    filesInformation: "Files & information",
    images: "Images",
    aiSupplementalInformation: "AI supplemental information",
    noSupplementalInformation: "No current supplemental information is available yet.",
    supplementalPending: "Supplemental information is still being prepared.",
    supplementalBlocked: "Supplemental information is blocked and is not current.",
    supplementalUnavailable: "Supplemental information is currently unavailable.",
    supplementalStale: "Existing supplemental information is stale and is not shown as current.",
    supplementalNotApplicable: "Supplemental information does not apply to this Matter.",
    actions: "Actions",
    noActions: "No current action is modeled for this Matter.",
    sourceList: "Sources",
    evidenceList: "Evidence",
    summary: "Summary",
    keyTime: "Start time",
    keyPeople: "Key people",
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
    fileOrInformation: "File or information",
    type: "Type",
    relationship: "Relationship",
    relatedToMatter: "Related to this Matter",
    sourceGroup: "Source group",
    location: "Location",
    informationModality: "Modality",
    observedTime: "Observed / received / modified",
    contentSummary: "Content summary",
    relevantTime: "Relevant time",
    currentResult: "Current summary / result",
    availability: "Availability",
    availableOnThisDevice: "Available on this device",
    evidenceAndHistory: "Evidence and history",
    evidenceForRecord: "Load bounded evidence",
    noImages: "No current authorized Matter-related image is available.",
    selectedImage: "Selected image",
    imageThumbnails: "Related image thumbnails",
    zoomIn: "Zoom in",
    zoomOut: "Zoom out",
    resetZoom: "Reset",
    imagePrevious: "Previous image",
    imageNext: "Next image",
    imageZoomHelp: "Use +/−, the mouse wheel, or drag while enlarged.",
    revealEvidence: "Load evidence",
    evidencePrivacy: "Evidence stays on this computer and is shown only on demand.",
    noEvidence: "No displayable anchored evidence is available.",
    statusUnknown: "Uncertain",
    linked: "Linked",
    plannedBasis: "Planned",
    reportedBasis: "Source record",
    observedBasis: "Observed",
    inferredBasis: "Inferred",
    sourceOnly: "Source only",
    backgroundIdle: "Background is idle",
  },
  "zh-CN": {
    search: "搜索事项",
    navigation: "浏览",
    all: "全部事项",
    status: "状态",
    planned: "计划中",
    in_progress: "进行中",
    completed: "已完成",
    startTime: "开始时间",
    allYears: "全部年份",
    peopleFilter: "相关人物",
    relationshipsFilter: "关系",
    topicTypeFilter: "主题 / 类型",
    sourceTypeFilter: "来源类型",
    noFilterValues: "暂无已建模选项",
    clearFilter: "清除",
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
    coverageBlocked: "覆盖流程受阻",
    coverageStale: "覆盖状态需要刷新",
    coverageUnavailable: "覆盖审计暂不可用",
    coverageFirstGaps: "最先未完成的阶段",
    coverageTotalSurfaces: "全部表面",
    coverageCurrentSurfaces: "已完成表面",
    coverageGapSurfaces: "存在缺口的表面",
    coverageSurfaceGaps: "表面缺口",
    coverageSurfaces: "已审计表面",
    coverageApplicability: "表面适用范围",
    coverageAuditLoading: "正在检查每一个已登记表面…",
    coverageAuditError: "暂时无法读取表面覆盖审计。",
    coverageClearDrilldown: "显示全部表面",
    coverageOwner: "负责人",
    coverageFailure: "失败原因",
    coverageFreshness: "新鲜度",
    coverageUiReady: "已到 UI",
    systemSurface: "系统",
    rootMatterSurface: "顶层事项",
    childMatterSurface: "子事项",
    occurrenceSurface: "来源对象",
    yes: "是",
    no: "否",
    loadingTitle: "正在载入您的事项",
    loadingBody: "正在连接本机 Matters 服务。",
    processingTitle: "来源仍在建模",
    processingBody: "事项准备好后，对象浏览器会自动刷新。",
    honestEmptyTitle: "目前还没有已建模的事项",
    honestEmptyBody: "本机服务连接正常；当前登记的来源范围确实为空。",
    noFilterResultsTitle: "这些筛选条件下没有事项",
    noFilterResultsBody: "已建模的事项仍然存在。清除或更改筛选条件即可查看。",
    staleTitle: "正在显示上一次成功载入的内容",
    staleBody: "本机服务暂时无法连接；Matters 正在自动重连。",
    transportErrorTitle: "Matters 暂时无法连接本机服务",
    transportErrorBody: "这里没有把故障误报成空数据；Matters 会继续在后台自动重试。",
    reconnecting: "正在自动重连",
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
    subMatters: "子事项",
    subMatter: "子事项",
    childStatus: "状态",
    childTime: "开始／下一重要时间",
    childResult: "最新结果／下一步",
    childFiles: "相关文件",
    noSubMatters: "这个事项目前还没有已建模的子事项。",
    subMattersUnavailable: "子事项暂时无法读取。",
    graphHelp: "拖动画布可移动，使用滚轮或按钮缩放；选择任一节点只会打开一层速览。",
    resetGraph: "重置视图",
    graphZoomIn: "放大",
    graphZoomOut: "缩小",
    collapseBranch: "收起分支",
    expandBranch: "展开分支",
    quickView: "节点速览",
    quickViewLoading: "正在载入这个节点的速览…",
    summaryCurrentState: "摘要与当前状态",
    factsAndProgress: "事实与进展",
    noFacts: "暂时没有与这个子事项直接相关的事实。",
    filesLocations: "文件与信息位置",
    closeQuickView: "关闭速览",
    graphUnavailable: "事项图暂时无法读取。",
    moreSubMatters: "载入更多分支",
    loadingMoreSubMatters: "正在载入更多分支…",
    confirmedObserved: "已确认／已观察",
    aiInferred: "AI 推测",
    aiHistoricalInference: "AI 历史推断",
    reportedCertainty: "来源记录",
    plannedCertainty: "计划",
    previousPage: "上一页",
    nextPage: "下一页",
    page: "第",
    backToParent: "返回上一级事项",
    openSubMatter: "打开子事项",
    viewFiles: "查看相关文件",
    unknownCount: "暂不可用",
    showingLastKnown: "正在显示上一次成功载入的事项。",
    path: "路径",
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
    filesInformation: "文件与信息",
    images: "图片",
    aiSupplementalInformation: "AI 补充信息",
    noSupplementalInformation: "目前还没有可显示的补充信息。",
    supplementalPending: "补充信息仍在准备中。",
    supplementalBlocked: "补充信息当前受阻，不能视为最新。",
    supplementalUnavailable: "补充信息当前不可用。",
    supplementalStale: "已有补充信息已经过期，不会作为当前信息显示。",
    supplementalNotApplicable: "这个事项不需要补充信息。",
    actions: "行动",
    noActions: "这个事项目前还没有已建模的行动。",
    sourceList: "相关来源",
    evidenceList: "相关证据",
    summary: "摘要",
    keyTime: "开始时间",
    keyPeople: "关键人物",
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
    fileOrInformation: "文件或信息",
    type: "类型",
    relationship: "与事项的关系",
    relatedToMatter: "与这个事项相关",
    sourceGroup: "来源分组",
    location: "位置",
    informationModality: "信息形态",
    observedTime: "观察／收取／修改时间",
    contentSummary: "内容摘要",
    relevantTime: "相关时间",
    currentResult: "当前摘要／结果",
    availability: "可用状态",
    availableOnThisDevice: "可在本机读取",
    evidenceAndHistory: "证据与变更记录",
    evidenceForRecord: "读取有限证据",
    noImages: "目前没有可显示且已授权的事项相关图片。",
    selectedImage: "当前图片",
    imageThumbnails: "相关图片缩略图",
    zoomIn: "放大",
    zoomOut: "缩小",
    resetZoom: "重置",
    imagePrevious: "上一张图片",
    imageNext: "下一张图片",
    imageZoomHelp: "可使用加减按钮、鼠标滚轮；放大后可拖动查看。",
    revealEvidence: "读取证据",
    evidencePrivacy: "证据只在本机保存，并且只有主动打开时才显示。",
    noEvidence: "目前没有可显示的定位证据。",
    statusUnknown: "不确定",
    linked: "已关联",
    plannedBasis: "计划",
    reportedBasis: "来源记录",
    observedBasis: "观察",
    inferredBasis: "推断",
    sourceOnly: "仅来源",
    backgroundIdle: "后台当前空闲",
  },
};

const state = {
  locale: "en",
  localeRegistry: null,
  density: localStorage.getItem(STORAGE.density) === "compact" ? "compact" : "standard",
  activeFilterGroup: null,
  filters: {
    status: "all",
    start_year: "all",
    people: [],
    relationships: [],
    topic_types: [],
    source_types: [],
  },
  query: "",
  browser: null,
  lastSuccessfulView: null,
  loading: true,
  loadingMore: false,
  transportPhase: "loading",
  retryAttempt: 0,
  error: "",
  focusCatalogErrorOnRender: false,
  settingsOpen: false,
  healthOpen: false,
  coverageAudit: null,
  coverageAuditLoading: false,
  coverageAuditError: "",
  coverageAuditFilters: {},
  coverageAuditLoadedAt: 0,
  mobileOpen: false,
  selectedMatterId: "",
  detail: null,
  detailLoading: false,
  detailSection: "overview",
  situationGraph: null,
  graphLoading: false,
  graphLoadingMore: false,
  graphError: "",
  graphZoom: 1,
  graphPan: { x: 0, y: 0 },
  quickView: null,
  quickViewLoading: false,
  quickViewError: "",
  quickViewOriginNodeId: "",
  pendingDetailRestore: null,
  gallerySelectedIndex: 0,
  galleryZoom: 1,
  galleryPan: { x: 0, y: 0 },
  focusDetailOnRender: false,
  evidence: null,
  toast: "",
  requestId: 0,
  graphRequestId: 0,
  quickViewRequestId: 0,
  coverageAuditRequestId: 0,
};

let catalogController = null;
let searchTimer = null;
let browserRefreshTimer = null;
let lastCardFocus = "";
let galleryDrag = null;
let graphDrag = null;
const GRAPH_PAGE_SIZE = 200;
const GRAPH_FOCUS_PAGE_LIMIT = 25;

function t(key) {
  return COPY[state.locale]?.[key] || COPY.en[key] || key;
}

function value(map, fallback = "") {
  if (!map || typeof map !== "object") return fallback;
  return String(map[state.locale] || map.en || fallback);
}

function displayText(input, fallback = "") {
  return input && typeof input === "object" ? value(input, fallback) : String(input ?? fallback);
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
    chevron: '<path d="m9 6 6 6-6 6"></path>',
    back: '<path d="m15 18-6-6 6-6"></path>',
    relationship: '<circle cx="7" cy="12" r="3"></circle><circle cx="17" cy="7" r="3"></circle><circle cx="17" cy="17" r="3"></circle><path d="m9.5 10.5 5-2M9.5 13.5l5 2"></path>',
    topic: '<path d="M4 5h16v14H4zM8 9h8M8 13h5"></path>',
    settings: '<circle cx="12" cy="12" r="3"></circle><path d="M19 12a7 7 0 0 0-.1-1l2-1.6-2-3.4-2.5 1a7 7 0 0 0-1.7-1L14.3 3h-4.6L9.3 6a7 7 0 0 0-1.7 1L5.1 6 3 9.4 5.1 11a7 7 0 0 0 0 2L3 14.6 5.1 18l2.5-1a7 7 0 0 0 1.7 1l.4 3h4.6l.4-3a7 7 0 0 0 1.7-1l2.5 1 2.1-3.4-2.1-1.6a7 7 0 0 0 .1-1Z"></path>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2"></rect><circle cx="8" cy="9" r="2"></circle><path d="m4 18 5-5 3 3 3-4 5 6"></path>',
    overview: '<path d="M4 5h16M4 12h16M4 19h10"></path>',
    timeline: '<path d="M7 4v16M7 7h8M7 12h11M7 17h6"></path>',
    people: '<circle cx="9" cy="8" r="3"></circle><circle cx="17" cy="9" r="2"></circle><path d="M4 20c0-4 2-7 5-7s5 3 5 7M14 15c3 0 5 2 5 5"></path>',
    source: '<path d="M7 3h8l4 4v14H7z"></path><path d="M15 3v5h4M10 13h6M10 17h6"></path>',
    evidence: '<path d="M5 4h14v16H5z"></path><path d="m8 12 2 2 5-5M8 17h8"></path>',
  };
  return `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.overview}</svg>`;
}

function canonicalStateKey(card) {
  const rawState = String(card.state || card.status_group || "uncertain");
  const aliases = {
    open: "in_progress",
    active: "in_progress",
    current: "in_progress",
  };
  return aliases[rawState] || rawState;
}

function stateLabel(card) {
  const stateKey = canonicalStateKey(card);
  const canonical = stateKey.replaceAll("_", " ");
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
  return labels[state.locale]?.[stateKey] || labels.en[stateKey] || canonical;
}

function localeDefinitions() {
  const definitions = Array.isArray(state.localeRegistry?.locales)
    ? state.localeRegistry.locales
    : [];
  const available = new Set(state.localeRegistry?.available_locales || []);
  return definitions.filter((definition) => (
    definition
    && available.has(String(definition.tag || ""))
    && definition.selectable !== false
  ));
}

function localeDisplayName(definition) {
  return String(
    definition?.native_name
    || definition?.english_name
    || definition?.tag
    || "",
  );
}

function localeOptionsHtml() {
  return localeDefinitions().map((definition) => {
    const locale = String(definition.tag);
    return `<option value="${escapeHtml(locale)}" ${state.locale === locale ? "selected" : ""}>${escapeHtml(localeDisplayName(definition))}</option>`;
  }).join("");
}

function currentCatalog() {
  return state.browser?.catalog || null;
}

function knownNumber(input) {
  return typeof input === "number" && Number.isFinite(input);
}

function formatCount(input) {
  return knownNumber(input) ? String(input) : "—";
}

function displayStartDate(input) {
  const raw = String(input || "").trim();
  if (!raw) return "—";
  const dayFromParts = (year, month, day) => {
    const parsed = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
    if (
      parsed.getUTCFullYear() !== Number(year)
      || parsed.getUTCMonth() !== Number(month) - 1
      || parsed.getUTCDate() !== Number(day)
    ) return "";
    return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  };
  const iso = raw.match(/((?:19|20)\d{2})-(\d{2})-(\d{2})(?!\d)/);
  if (iso) return dayFromParts(iso[1], iso[2], iso[3]) || "—";
  const slash = raw.match(/^(\d{1,2})\/(\d{1,2})\/((?:19|20)\d{2})\b/);
  if (slash) return dayFromParts(slash[3], slash[1], slash[2]) || "—";
  const parsed = new Date(raw);
  return Number.isNaN(parsed.getTime()) ? "—" : parsed.toISOString().slice(0, 10);
}

function catalogItems() {
  return currentCatalog()?.items || [];
}

function copyFilters(filters = state.filters) {
  return {
    status: filters.status,
    start_year: filters.start_year,
    people: [...filters.people],
    relationships: [...filters.relationships],
    topic_types: [...filters.topic_types],
    source_types: [...filters.source_types],
  };
}

function renderedCatalogView() {
  if (state.transportPhase === "ready_stale" && state.lastSuccessfulView) {
    return state.lastSuccessfulView;
  }
  return { query: state.query, filters: state.filters };
}

function isRootCatalogCard(card, query = state.query) {
  if (query) return true;
  if (typeof card.is_root === "boolean") return card.is_root;
  return !(card.parent_matter_id || card.parent?.matter_id);
}

function visibleCatalogItems(view = renderedCatalogView()) {
  const filters = view.filters;
  return catalogItems().filter((card) => {
    if (!isRootCatalogCard(card, view.query)) return false;
    if (filters.status !== "all" && String(card.state || card.status_group) !== filters.status) return false;
    const startYear = String(card.start_time || "").match(/\b(19|20)\d{2}\b/)?.[0] || "";
    if (filters.start_year !== "all" && startYear !== filters.start_year) return false;
    const dimensions = {
      people: (card.people || []).map((person) => String(person.value || person.person_id || person.id || person.name || "")),
      relationships: (card.relationships || card.relationship_types || []).map((entry) => String(entry?.value ?? entry?.id ?? entry?.key ?? entry?.name ?? entry)),
      topic_types: (card.topic_types || card.topics || (card.matter_type ? [card.matter_type] : [])).map((entry) => String(entry?.value ?? entry?.id ?? entry?.key ?? entry?.name ?? entry)),
      source_types: (card.source_types || (card.source_type ? [card.source_type] : [])).map((entry) => String(entry?.value ?? entry?.id ?? entry?.key ?? entry?.name ?? entry)),
    };
    return Object.entries(dimensions).every(([name, cardValues]) => (
      !filters[name].length
      || filters[name].every((filterValue) => cardValues.includes(filterValue))
    ));
  });
}

function allFiltersClear(filters = state.filters) {
  return filters.status === "all"
    && filters.start_year === "all"
    && !filters.people.length
    && !filters.relationships.length
    && !filters.topic_types.length
    && !filters.source_types.length;
}

function catalogDisplayCount() {
  if (state.transportPhase === "transport_error" || state.transportPhase === "ready_stale") {
    return undefined;
  }
  const projectionOnlyFilterActive = state.filters.start_year !== "all"
    || state.filters.people.length
    || state.filters.relationships.length
    || state.filters.topic_types.length
    || state.filters.source_types.length;
  if (projectionOnlyFilterActive) {
    return currentCatalog()?.filtered_total_count ?? currentCatalog()?.total_count;
  }
  return currentCatalog()?.total_count;
}

function localizedFacetLabel(input, fallback = "") {
  if (input && typeof input === "object") return value(input, fallback);
  return String(input ?? fallback);
}

function normalizeFacetEntries(name, fallbackValues = []) {
  const aliases = {
    start_year: ["start_year", "years", "year"],
    people: ["people", "person"],
    relationships: ["relationships", "relationship_types", "relationship"],
    topic_types: ["topic_types", "topic_type", "topics"],
    source_types: ["source_types", "source_type"],
  };
  const facets = currentCatalog()?.facets || {};
  const raw = (aliases[name] || [name]).map((key) => facets[key]).find((entry) => entry != null);
  const normalized = [];
  if (Array.isArray(raw)) {
    raw.forEach((entry) => {
      if (entry && typeof entry === "object") {
        const facetValue = String(entry.value ?? entry.id ?? entry.key ?? "");
        if (facetValue) {
          normalized.push({
            value: facetValue,
            label: localizedFacetLabel(entry.label ?? entry.name, facetValue),
            count: entry.count,
          });
        }
      } else if (entry != null) {
        normalized.push({ value: String(entry), label: String(entry) });
      }
    });
  } else if (raw && typeof raw === "object") {
    Object.entries(raw).forEach(([facetValue, payload]) => {
      if (payload && typeof payload === "object") {
        normalized.push({
          value: facetValue,
          label: localizedFacetLabel(payload.label ?? payload.name, facetValue),
          count: payload.count,
        });
      } else {
        normalized.push({ value: facetValue, label: facetValue, count: payload });
      }
    });
  }
  const seen = new Set(normalized.map((entry) => entry.value));
  fallbackValues.forEach((entry) => {
    const facetValue = String(entry.value ?? "");
    if (facetValue && !seen.has(facetValue)) {
      normalized.push(entry);
      seen.add(facetValue);
    }
  });
  return normalized;
}

function derivedFacetValues(name) {
  const values = new Map();
  catalogItems().forEach((card) => {
    let candidates = [];
    if (name === "start_year") {
      const year = String(card.start_time || "").match(/\b(19|20)\d{2}\b/)?.[0];
      candidates = year ? [{ value: year, label: year }] : [];
    } else if (name === "people") {
      candidates = (card.people || []).map((person) => ({
        value: String(person.person_id || person.id || person.name || ""),
        label: String(person.name || person.person_id || person.id || ""),
      }));
    } else if (name === "relationships") {
      candidates = card.relationships || card.relationship_types || [];
    } else if (name === "topic_types") {
      candidates = card.topic_types || card.topics || (card.matter_type ? [card.matter_type] : []);
    } else if (name === "source_types") {
      candidates = card.source_types || (card.source_type ? [card.source_type] : []);
    }
    candidates.forEach((candidate) => {
      const facetValue = String(
        candidate && typeof candidate === "object"
          ? candidate.value ?? candidate.id ?? candidate.key ?? candidate.name ?? candidate.label ?? ""
          : candidate,
      );
      if (!facetValue) return;
      const label = candidate && typeof candidate === "object"
        ? localizedFacetLabel(candidate.label ?? candidate.name, facetValue)
        : facetValue;
      values.set(facetValue, {
        value: facetValue,
        label,
        count: undefined,
      });
    });
  });
  return [...values.values()];
}

function facetEntries(name) {
  if (name === "status") {
    const statusFallback = ["planned", "in_progress", "completed"].map((status) => ({
      value: status,
      label: t(status),
      count: currentCatalog()?.facets?.status?.[status],
    }));
    return normalizeFacetEntries("status", statusFallback)
      .filter((entry) => entry.value !== "all")
      .map((entry) => ({ ...entry, label: t(entry.value) === entry.value ? entry.label : t(entry.value) }));
  }
  return normalizeFacetEntries(name, derivedFacetValues(name))
    .sort((left, right) => left.label.localeCompare(right.label, state.locale));
}

function filterValueActive(name, filterValue) {
  const active = state.filters[name];
  return Array.isArray(active) ? active.includes(filterValue) : active === filterValue;
}

function filterGroupHtml({ name, labelKey, iconName, single = false, includeAll = false }) {
  const open = state.activeFilterGroup === name;
  const entries = facetEntries(name);
  const options = [
    ...(includeAll ? [{
      value: "all",
      label: name === "start_year" ? t("allYears") : t("all"),
      count: name === "status" ? currentCatalog()?.facets?.status?.all : undefined,
    }] : []),
    ...entries,
  ];
  return `<section class="db-filter-group db-nav-group">
    <button type="button" class="db-filter-group-toggle db-nav-group-toggle" data-filter-group="${name}" aria-expanded="${open}" ${open ? `aria-controls="filter-panel-${name}"` : ""}>
      <span class="db-nav-icon">${icon(iconName)}</span>
      <span class="db-nav-label">${escapeHtml(t(labelKey))}</span>
      <span class="db-filter-chevron db-chevron">${icon("chevron")}</span>
    </button>
    ${open ? `<div id="filter-panel-${name}" class="db-filter-options db-nav-panel" data-filter-options="${name}">
      ${options.length ? options.map((entry) => {
        const selected = filterValueActive(name, entry.value);
        return `<button type="button" class="db-filter-option db-nav-item" data-filter-name="${name}" data-filter-value="${escapeHtml(entry.value)}" data-filter-single="${single}" aria-pressed="${selected}">
          <span class="db-nav-icon">${icon(iconName)}</span>
          <span class="db-nav-label">${escapeHtml(entry.label)}</span>
          <span class="db-nav-count">${formatCount(entry.count)}</span>
        </button>`;
      }).join("") : `<p class="db-filter-empty">${escapeHtml(t("noFilterValues"))}</p>`}
    </div>` : ""}
  </section>`;
}

function activeFilterChipsHtml() {
  const chips = [];
  Object.entries(state.filters).forEach(([name, active]) => {
    const values = Array.isArray(active) ? active : active === "all" ? [] : [active];
    values.forEach((filterValue) => {
      const label = facetEntries(name).find((entry) => entry.value === filterValue)?.label
        || (name === "status" ? t(filterValue) : filterValue);
      chips.push(`<button type="button" class="db-active-filter-chip" data-clear-filter="${name}" data-clear-value="${escapeHtml(filterValue)}" aria-label="${escapeHtml(`${t("clearFilter")}: ${label}`)}"><span>${escapeHtml(label)}</span><span aria-hidden="true">×</span></button>`);
    });
  });
  return chips.length ? `<div class="db-active-filters">${chips.join("")}</div>` : "";
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

function clearAllFilters() {
  state.filters = {
    status: "all",
    start_year: "all",
    people: [],
    relationships: [],
    topic_types: [],
    source_types: [],
  };
}

function coverageSurfaceStatus() {
  if (state.coverageAuditError) {
    if (state.coverageAudit) return "stale";
    const fallbackStatus = String(
      state.browser?.coverage?.coverage_status || "",
    );
    if (["complete", "current"].includes(fallbackStatus)) return "current";
    if (fallbackStatus === "blocked") return "blocked";
    if (fallbackStatus) return "partial";
    return "unavailable";
  }
  return String(
    state.coverageAudit?.coverage_contract?.surface_status
      || state.browser?.coverage?.coverage_contract?.surface_status
      || "pending",
  ).trim().toLowerCase();
}

function coverageStatusLabel(status = coverageSurfaceStatus()) {
  if (["complete", "current"].includes(status)) return t("coverageComplete");
  if (status === "blocked") return t("coverageBlocked");
  if (status === "stale") return t("coverageStale");
  if (status === "unavailable") return t("coverageUnavailable");
  return t("coverageWorking");
}

function coverageHealthTone(transportCurrent) {
  if (!transportCurrent) return "unavailable";
  const status = coverageSurfaceStatus();
  if (["complete", "current"].includes(status)) return "healthy";
  if (["blocked", "unavailable"].includes(status)) return "unavailable";
  return "changed";
}

function coverageTokenLabel(token) {
  const normalized = String(token || "").trim().toLowerCase();
  const known = {
    inventory_freshness: { en: "Inventory freshness", "zh-CN": "清单新鲜度" },
    source_group_projection: { en: "Source grouping", "zh-CN": "来源分组" },
    raw_cleanup: { en: "Raw-data cleanup", "zh-CN": "原始暂存清理" },
    staging_cleanup: { en: "Staging cleanup", "zh-CN": "中转区清理" },
    situation_graph: { en: "Sub-matter map", "zh-CN": "子事项图" },
    node_quick_view: { en: "Sub-matter quick view", "zh-CN": "子事项速览" },
    world_model: { en: "AI supplemental context", "zh-CN": "AI 补充背景" },
  };
  if (known[normalized]) return value(known[normalized], normalized);
  const words = normalized.replaceAll("_", " ");
  return state.locale === "en"
    ? words.replace(/\b\w/g, (letter) => letter.toUpperCase())
    : words;
}

function coverageDrilldownAttributes(surface) {
  return [
    ["surface-id", surface.surface_id],
    ["surface-status", surface.status],
    ["owner-id", surface.owner_id],
    ["failure-class", surface.failure_class],
    ["freshness", surface.freshness],
    ["ui-ready", typeof surface.ui_ready === "boolean" ? String(surface.ui_ready) : ""],
  ].filter(([, fieldValue]) => fieldValue !== "" && fieldValue != null).map(
    ([name, fieldValue]) => `data-coverage-${name}="${escapeHtml(fieldValue)}"`,
  ).join(" ");
}

function coverageSurfaceRows(rows, { gaps = false } = {}) {
  if (!rows.length) return "";
  return `<section class="db-coverage-surface-section">
    <h4>${escapeHtml(t(gaps ? "coverageSurfaceGaps" : "coverageSurfaces"))}</h4>
    <ul>${rows.slice(0, 30).map((surface) => {
      const surfaceId = surface.surface_id || surface.first_gap_stage || "";
      const status = surface.status || "pending";
      return `<li>
        <button type="button" class="db-coverage-surface-row" data-coverage-drilldown ${coverageDrilldownAttributes({ ...surface, surface_id: surfaceId })}>
          <strong>${escapeHtml(coverageTokenLabel(surfaceId))}</strong>
          <span data-status="${escapeHtml(status)}">${escapeHtml(coverageTokenLabel(status))}</span>
          ${surface.owner_id ? `<small>${escapeHtml(t("coverageOwner"))}: ${escapeHtml(coverageTokenLabel(surface.owner_id))}</small>` : ""}
          ${surface.failure_class ? `<small>${escapeHtml(t("coverageFailure"))}: ${escapeHtml(coverageTokenLabel(surface.failure_class))}</small>` : ""}
        </button>
      </li>`;
    }).join("")}</ul>
  </section>`;
}

function coveragePanel() {
  if (!state.healthOpen) return "";
  const audit = state.coverageAudit || {};
  const transportCurrent = !["transport_error", "ready_stale"].includes(state.transportPhase);
  const surfaces = Array.isArray(audit.surfaces) ? audit.surfaces : [];
  const gaps = Array.isArray(audit.surface_gaps) ? audit.surface_gaps : [];
  const applicability = audit.surface_applicability || {};
  const applicabilityLabels = {
    system: "systemSurface",
    root_matter: "rootMatterSurface",
    child_matter: "childMatterSurface",
    occurrence: "occurrenceSurface",
  };
  const hasFilters = Object.values(state.coverageAuditFilters).some(
    (filterValue) => filterValue !== "" && filterValue != null,
  );
  return `<section class="db-source-health-panel" role="dialog" aria-label="${escapeHtml(t("coverage"))}">
    <h3>${escapeHtml(t("coverage"))}</h3>
    <p>${escapeHtml(!transportCurrent ? t("reconnecting") : coverageStatusLabel())}</p>
    <dl class="db-coverage-facts db-coverage-surface-facts">
      <div><dt>${escapeHtml(t("coverageTotalSurfaces"))}</dt><dd>${formatCount(audit.total_surfaces)}</dd></div>
      <div><dt>${escapeHtml(t("coverageCurrentSurfaces"))}</dt><dd>${formatCount(audit.current_surfaces)}</dd></div>
      <div><dt>${escapeHtml(t("coverageGapSurfaces"))}</dt><dd>${formatCount(audit.gap_surfaces)}</dd></div>
    </dl>
    ${state.coverageAuditLoading ? `<p class="db-coverage-audit-note" role="status">${escapeHtml(t("coverageAuditLoading"))}</p>` : ""}
    ${state.coverageAuditError ? `<p class="db-coverage-audit-note db-coverage-audit-error" role="alert">${escapeHtml(t("coverageAuditError"))}</p>` : ""}
    ${hasFilters ? `<button type="button" class="db-coverage-clear" data-coverage-clear>${escapeHtml(t("coverageClearDrilldown"))}</button>` : ""}
    ${coverageSurfaceRows(gaps, { gaps: true })}
    ${coverageSurfaceRows(surfaces)}
    ${Object.keys(applicability).length ? `<section class="db-coverage-applicability">
      <h4>${escapeHtml(t("coverageApplicability"))}</h4>
      <dl>${Object.entries(applicability).map(([kind, surfaceIds]) => `<div><dt>${escapeHtml(t(applicabilityLabels[kind] || kind))}</dt><dd>${escapeHtml((surfaceIds || []).map(coverageTokenLabel).join(" · ") || "—")}</dd></div>`).join("")}</dl>
    </section>` : ""}
  </section>`;
}

function cardHtml(card) {
  const title = displayText(card.title, state.locale === "en" ? "Untitled matter" : "未命名事项");
  const hero = card.hero || {};
  const hasImage = hero.status === "generated_current" && hero.preview_token;
  const heroNotApplicable = hero.status === "not_applicable";
  const detailPending = state.detailLoading && state.selectedMatterId === card.matter_id;
  const startTimeRaw = card.start_time || "";
  const startTime = displayStartDate(startTimeRaw);
  const metrics = state.density === "compact" ? "" : `<div class="db-card-metrics">
    <div class="db-card-metric"><strong>${formatCount(card.event_count)}</strong><span>${escapeHtml(t("events"))}</span></div>
    <div class="db-card-metric"><strong>${formatCount(card.people_count)}</strong><span>${escapeHtml(t("people"))}</span></div>
    <div class="db-card-metric"><strong>${formatCount(card.source_count)}</strong><span>${escapeHtml(t("sources"))}</span></div>
  </div>`;
  return `<article
    id="matter-card-${escapeHtml(card.matter_id)}"
    class="db-project-card db-project-card--${state.density}${detailPending ? " is-detail-loading" : ""}"
    data-matter-id="${escapeHtml(card.matter_id)}"
    data-semantic-revision="${escapeHtml(card.semantic_revision || card.revision || "")}"
    data-hero-token="${escapeHtml(hero.preview_token || "")}"
    data-hero-status="${escapeHtml(hero.status || "")}"
    role="button"
    tabindex="0"
    aria-busy="${detailPending}"
    aria-label="${escapeHtml(title)}"
  >
    <header class="db-card-header"><h3 class="db-card-title" title="${escapeHtml(title)}">${escapeHtml(title)}</h3></header>
    <div class="db-card-meta">
      <span class="db-card-status" data-status="${escapeHtml(canonicalStateKey(card))}">${icon("overview")}<span>${escapeHtml(stateLabel(card))}</span></span>
      <span aria-hidden="true">·</span>
      <span class="db-card-start-time" title="${escapeHtml(startTimeRaw ? `${t("startTime")}: ${startTime}` : t("startTime"))}">${icon("calendar")}<span>${escapeHtml(startTime)}</span></span>
    </div>
    <section class="db-card-media" aria-label="${escapeHtml(value(hero.alt, title))}">
      ${hasImage
        ? `<img src="/api/heroes/${encodeURIComponent(hero.preview_token)}" alt="${escapeHtml(value(hero.alt, title))}" loading="lazy" decoding="async">`
        : heroNotApplicable
          ? '<div class="db-card-empty-media db-card-empty-media--not-applicable" aria-hidden="true"></div>'
          : `<div class="db-card-empty-media">${icon("image")}<strong>${escapeHtml(value(hero.alt, t("coverageWorking")))}</strong></div>`}
    </section>
    ${metrics}
  </article>`;
}

function searchPath(card) {
  const rawPath = card.breadcrumb || card.path || card.path_titles || card.hierarchy_path || [];
  const pathItems = Array.isArray(rawPath) ? rawPath : rawPath?.items || [];
  const pieces = pathItems
    .map((entry) => entry && typeof entry === "object" ? displayText(entry.title, entry.label || entry.matter_id) : String(entry))
    .filter(Boolean);
  const title = displayText(card.title);
  if (pieces.at(-1) === title) pieces.pop();
  return pieces.join(" › ");
}

function searchResultsHtml(cards) {
  return `<div class="db-typed-search-results" role="list">
    ${cards.map((card) => {
      const title = displayText(card.title, state.locale === "en" ? "Untitled matter" : "未命名事项");
      const path = searchPath(card);
      const owningRootId = String(card.owning_root_matter_id || card.hierarchy_path?.[0]?.matter_id || card.matter_id);
      const matchedNodeId = String(card.matched_node_id || card.matter_id);
      return `<article id="matter-card-${escapeHtml(card.matter_id)}" class="db-search-result" data-matter-id="${escapeHtml(card.matter_id)}" data-owning-root-matter-id="${escapeHtml(owningRootId)}" data-matched-node-id="${escapeHtml(matchedNodeId)}" role="button" tabindex="0">
        <div class="db-search-result-copy">
          <h3>${escapeHtml(title)}</h3>
          ${path ? `<p><strong>${escapeHtml(t("path"))}:</strong> ${escapeHtml(path)}</p>` : ""}
        </div>
        <span class="db-search-result-status" data-group="${escapeHtml(card.status_group || card.state || "")}">${escapeHtml(stateLabel(card))}</span>
        <time title="${escapeHtml(displayStartDate(card.start_time))}">${escapeHtml(displayStartDate(card.start_time))}</time>
      </article>`;
    }).join("")}
  </div>`;
}

function gridHtml() {
  const catalog = currentCatalog();
  if (state.transportPhase === "loading" && !catalog) {
    return `<div class="db-empty-state" role="status"><strong>${escapeHtml(t("loadingTitle"))}</strong><p>${escapeHtml(t("loadingBody"))}</p></div>`;
  }
  if (state.transportPhase === "transport_error" && !catalog) {
    return `<div id="catalog-error" class="db-error-state" role="alert" tabindex="-1"><strong>${escapeHtml(t("transportErrorTitle"))}</strong><p>${escapeHtml(t("transportErrorBody"))}</p><span class="db-reconnect-status">${escapeHtml(t("reconnecting"))}</span><button class="db-primary-button" data-retry>${escapeHtml(t("retry"))}</button></div>`;
  }
  const view = renderedCatalogView();
  const cards = visibleCatalogItems(view);
  const staleWarning = state.transportPhase === "ready_stale"
    ? `<div id="catalog-error" class="db-error-state db-error-state--inline" role="alert" tabindex="-1"><strong>${escapeHtml(t("staleTitle"))}</strong><p>${escapeHtml(t("staleBody"))}</p><span class="db-reconnect-status">${escapeHtml(t("reconnecting"))}</span><button class="db-primary-button" data-retry>${escapeHtml(t("retry"))}</button></div>`
    : "";
  if (!cards.length) {
    if (state.transportPhase === "processing") {
      return `${staleWarning}<div class="db-empty-state" role="status"><strong>${escapeHtml(t("processingTitle"))}</strong><p>${escapeHtml(t("processingBody"))}</p></div>`;
    }
    if (state.transportPhase === "no_filter_results") {
      return `<div class="db-empty-state" role="status"><strong>${escapeHtml(t("noFilterResultsTitle"))}</strong><p>${escapeHtml(t("noFilterResultsBody"))}</p></div>`;
    }
    if (state.transportPhase === "honest_empty") {
      return `<div class="db-empty-state" role="status"><strong>${escapeHtml(t("honestEmptyTitle"))}</strong><p>${escapeHtml(t("honestEmptyBody"))}</p></div>`;
    }
    return `${staleWarning}<div class="db-empty-state" role="status"><strong>${escapeHtml(t("emptyTitle"))}</strong><p>${escapeHtml(t("emptyBody"))}</p></div>`;
  }
  const content = view.query ? searchResultsHtml(cards) : cards.map(cardHtml).join("");
  return `${staleWarning}${content}${
    catalog?.has_more
      ? `<button type="button" class="db-load-more" data-load-more ${state.loadingMore ? "disabled" : ""}>${escapeHtml(state.loadingMore ? t("loadingMore") : t("moreMatters"))}</button>`
      : ""
  }`;
}

function detailNavItem(section, key, count = "") {
  const iconName = section === "filesInformation"
    ? "source"
    : section === "images"
      ? "image"
      : section === "aiSupplementalInformation"
        ? "evidence"
      : section;
  return `<button type="button" id="detail-nav-${section}" class="db-detail-nav-item" data-detail-section="${section}" aria-current="${state.detailSection === section ? "page" : "false"}">
    <span>${icon(iconName)}</span>
    <span>${escapeHtml(t(key))}</span>
    <span class="db-detail-nav-count">${count}</span>
  </button>`;
}

function detailOverview(detail) {
  const card = detail.matter;
  const hero = card.hero || {};
  const hasImage = hero.status === "generated_current" && hero.preview_token;
  const heroNotApplicable = hero.status === "not_applicable";
  return `<div class="db-overview">
    <div class="db-detail-hero${heroNotApplicable ? " db-detail-hero--without-visual" : ""}">
      ${heroNotApplicable ? "" : `<section class="db-detail-visual">
        ${hasImage
          ? `<img src="/api/heroes/${encodeURIComponent(hero.preview_token)}" alt="${escapeHtml(displayText(hero.alt, displayText(card.title)))}">`
          : `<div class="db-card-empty-media">${icon("image")}<strong>${escapeHtml(displayText(hero.alt, t("coverageWorking")))}</strong></div>`}
      </section>`}
      <section class="db-detail-summary">
        <h4>${escapeHtml(t("summary"))}</h4>
        <p>${escapeHtml(displayText(card.summary, displayText(card.title)))}</p>
        <dl class="db-detail-facts">
          <div><dt>${escapeHtml(t("state"))}</dt><dd>${escapeHtml(stateLabel(card))}</dd></div>
          <div><dt>${escapeHtml(t("keyTime"))}</dt><dd title="${escapeHtml(displayStartDate(card.start_time))}">${escapeHtml(displayStartDate(card.start_time))}</dd></div>
        </dl>
      </section>
    </div>
  </div>`;
}

function detailActions(detail) {
  const payload = detail.work_items || detail.actions || {};
  const items = Array.isArray(payload) ? payload : (payload.items || []);
  if (!items.length) return `<div class="db-empty-state">${escapeHtml(t("noActions"))}</div>`;
  return `<ul class="db-list">${items.map((item) => {
    const title = displayText(
      item.localized_title || item.title,
      state.locale === "en" ? "Action" : "行动",
    );
    const result = displayText(item.localized_result || item.result || item.next_step, "");
    const time = item.actual_end || item.planned_end || item.planned_start || item.next_time || "";
    return `<li class="db-list-item">
      <h4>${escapeHtml(title)}</h4>
      ${result ? `<p>${escapeHtml(result)}</p>` : ""}
      <p class="db-list-meta">${escapeHtml(stateLabel({ state: item.status || item.state }))}${time ? ` · ${escapeHtml(time)}` : ""}</p>
    </li>`;
  }).join("")}</ul>`;
}

function detailTimeline(detail) {
  const currentByLogicalEvent = new Map();
  (detail.timeline || []).forEach((entry) => {
    const sentence = displayText(entry.sentence).trim().replace(/\s+/g, " ").toLocaleLowerCase();
    const eventDay = displayStartDate(entry.claimed_time || entry.record_time);
    const owner = String(
      displayText(entry.sub_matter)
      || entry.owning_matter_id
      || (entry.source_level === "current_matter" ? state.selectedMatterId : entry.source_level)
      || "",
    );
    const semanticKey = sentence && eventDay !== "—"
      ? `timeline:${owner}|${eventDay}|${sentence}`
      : "";
    const logicalKey = String(
      semanticKey
      || entry.logical_event_key
      || entry.current_logical_event_key
      || entry.event_id
      || `${owner}|${sentence}|${eventDay}`,
    );
    const previous = currentByLogicalEvent.get(logicalKey);
    const previousIsCurrent = previous?.current_revision !== false;
    const entryIsCurrent = entry.current_revision !== false;
    if (
      !previous
      || (entryIsCurrent && !previousIsCurrent)
      || (
        entryIsCurrent === previousIsCurrent
        && Number(entry.revision || 0) >= Number(previous.revision || 0)
      )
    ) {
      currentByLogicalEvent.set(logicalKey, entry);
    }
  });
  const entries = [...currentByLogicalEvent.values()];
  if (!entries.length) return `<div class="db-empty-state">${escapeHtml(t("noTimeline"))}</div>`;
  return `<div class="db-timeline">${entries.map((entry) => `<article class="db-timeline-entry">
    <p>${escapeHtml(displayText(entry.sentence))}</p>
    <p class="db-list-meta">${escapeHtml(t("claimedTime"))}: ${escapeHtml(displayStartDate(entry.claimed_time || entry.record_time))} · ${escapeHtml(t("modality"))}: ${escapeHtml(displayText(entry.basis_label, t(`${entry.modality || "inferred"}Basis`)))}${entry.owning_matter_title ? ` · ${escapeHtml(displayText(entry.owning_matter_title))}` : ""}</p>
  </article>`).join("")}</div>`;
}

function detailPeople(detail) {
  if (!detail.people?.length) return `<div class="db-empty-state">${escapeHtml(t("noPeople"))}</div>`;
  return `<ul class="db-list">${detail.people.map((person) => {
    const role = displayText(person.role_label || person.role, "");
    const resolution = person.resolved ? t("linked") : t("statusUnknown");
    return `<li class="db-list-item"><h4>${escapeHtml(person.name)}</h4><p class="db-list-meta">${escapeHtml([role, resolution].filter(Boolean).join(" · "))}</p></li>`;
  }).join("")}</ul>`;
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
  return `<ul class="db-list">${detail.related_matters.map((matter) => {
    const relations = Array.isArray(matter.relations) ? matter.relations : [];
    const relationDetails = relations.map((relation) => {
      const label = displayText(relation.label, String(relation.relation_type || "").replaceAll("_", " "));
      const rationale = displayText(relation.rationale, "");
      return `<p class="db-related-relation"><strong>${escapeHtml(label)}</strong>${rationale ? `<span>${escapeHtml(rationale)}</span>` : ""}</p>`;
    }).join("");
    return `<li class="db-list-item">
      <button type="button" id="related-matter-${escapeHtml(matter.matter_id)}" class="db-related-matter" data-related-matter="${escapeHtml(matter.matter_id)}">
        <strong>${escapeHtml(displayText(matter.title))}</strong>
        <span>${escapeHtml(displayText(matter.summary))}</span>
      </button>
      ${relationDetails}
    </li>`;
  }).join("")}</ul>`;
}

function graphCertaintyLabel(certainty, basisScope = "") {
  if (
    String(certainty || "") === "ai_inferred"
    && String(basisScope || "") === "historical_inference"
  ) {
    return t("aiHistoricalInference");
  }
  return {
    confirmed_observed: t("confirmedObserved"),
    reported: t("reportedCertainty"),
    planned: t("plannedCertainty"),
    ai_inferred: t("aiInferred"),
  }[String(certainty || "")] || t("statusUnknown");
}

function graphNodeTitle(node) {
  const attributes = node?.attributes || {};
  return displayText(
    attributes.title || attributes.sentence || attributes.summary,
    {
      matter: t("subMatter"),
      work_item: t("actions"),
      event: t("events"),
      person: t("people"),
      source: t("sources"),
    }[node?.node_type] || t("subMatter"),
  );
}

function situationGraphLayout(graph) {
  const allNodes = (Array.isArray(graph?.nodes) ? graph.nodes : [])
    .filter((node) => ["matter", "work_item"].includes(
      String(node.node_type || "").toLowerCase(),
    ));
  const visibleIds = new Set(allNodes.map((node) => String(node.node_id)));
  const allEdges = (Array.isArray(graph?.edges) ? graph.edges : []).filter(
    (edge) => visibleIds.has(String(edge.source_node_id))
      && visibleIds.has(String(edge.target_node_id)),
  );
  const byId = new Map(allNodes.map((node) => [String(node.node_id), node]));
  const rootId = String(graph?.root_matter_id || "");
  const primaryChildren = new Map();
  allEdges.filter((edge) => edge.primary_containment).forEach((edge) => {
    const source = String(edge.source_node_id);
    if (!primaryChildren.has(source)) primaryChildren.set(source, []);
    primaryChildren.get(source).push(String(edge.target_node_id));
  });
  const nodes = allNodes;
  const edges = allEdges.filter(
    (edge) => visibleIds.has(String(edge.source_node_id))
      && visibleIds.has(String(edge.target_node_id)),
  );
  const depth = new Map([[rootId, 0]]);
  for (let pass = 0; pass < nodes.length + 2; pass += 1) {
    let changed = false;
    edges.forEach((edge) => {
      const source = String(edge.source_node_id);
      const target = String(edge.target_node_id);
      if (depth.has(source) && !depth.has(target)) {
        depth.set(target, depth.get(source) + 1);
        changed = true;
      }
    });
    if (!changed) break;
  }
  nodes.forEach((node) => {
    if (!depth.has(String(node.node_id))) depth.set(String(node.node_id), 1);
  });
  const levels = new Map();
  nodes.forEach((node) => {
    const nodeDepth = depth.get(String(node.node_id)) || 0;
    if (!levels.has(nodeDepth)) levels.set(nodeDepth, []);
    levels.get(nodeDepth).push(node);
  });
  levels.forEach((items) => items.sort((left, right) => (
    `${left.node_type}:${graphNodeTitle(left)}`.localeCompare(
      `${right.node_type}:${graphNodeTitle(right)}`,
      state.locale,
    )
  )));
  const positions = new Map();
  levels.forEach((items, nodeDepth) => {
    items.forEach((node, index) => {
      const isStage = String(node.node_type || "").toLowerCase() === "work_item";
      positions.set(String(node.node_id), {
        x: 42 + nodeDepth * 272,
        y: 42 + index * 112,
        width: isStage ? 184 : 214,
        height: isStage ? 66 : 76,
      });
    });
  });
  const maxDepth = Math.max(0, ...levels.keys());
  const maxRows = Math.max(1, ...[...levels.values()].map((items) => items.length));
  return {
    nodes,
    edges,
    positions,
    primaryChildren,
    width: Math.max(920, 90 + (maxDepth + 1) * 272),
    height: Math.max(520, 100 + maxRows * 112),
  };
}

function quickViewSourcesHtml(payload) {
  const projected = payload?.files_and_information || {};
  const rows = Array.isArray(projected.items)
    ? projected.items
    : (projected.groups || []).flatMap((group) => group.items || []);
  if (!rows.length) {
    return `<div class="db-empty-state">${escapeHtml(t("noSources"))}</div>`;
  }
  return `<ul class="db-quick-source-groups">${rows.slice(0, 12).map((source, index) => `
    <li>
      <strong>${escapeHtml(sourceLabel(source, index))}</strong>
      <span>${escapeHtml(sourceTypeLabel(source))} · ${escapeHtml(sourceModalityLabel(source))}</span>
      <p>${escapeHtml(displayText(source.summary, "—"))}</p>
      <dl class="db-quick-source-meta">
        <div><dt>${escapeHtml(t("location"))}</dt><dd>${escapeHtml(sourceLocationLabel(source))}</dd></div>
        <div><dt>${escapeHtml(t("sourceGroup"))}</dt><dd>${escapeHtml(displayText(source.location_group, "—"))}</dd></div>
        <div><dt>${escapeHtml(t("observedTime"))}</dt><dd>${escapeHtml(displayStartDate(source.observed_time || source.relevant_time))}</dd></div>
        <div><dt>${escapeHtml(t("availability"))}</dt><dd>${escapeHtml(sourceAvailabilityLabel(source))}</dd></div>
      </dl>
    </li>`).join("")}</ul>`;
}

function quickFactTitle(fact) {
  if (fact.kind === "wait") {
    const target = String(fact.wait_target || "").trim();
    return target ? `${t("waitTarget")}: ${target}` : t("openLoops");
  }
  return displayText(fact.title || fact.sentence, "—");
}

function quickFactBody(fact) {
  if (fact.kind === "wait") {
    const condition = String(fact.closure_condition || "").trim();
    return condition ? `${t("closureCondition")}: ${condition}` : "";
  }
  const title = displayText(fact.title || fact.sentence, "");
  const body = displayText(fact.summary || fact.result, "");
  const normalize = (value) => String(value || "")
    .trim()
    .replace(/[。.!！?？]+$/u, "")
    .replace(/\s+/gu, " ")
    .toLocaleLowerCase(state.locale);
  return normalize(body) === normalize(title) ? "" : body;
}

function quickFactBasis(fact) {
  return displayText(
    fact.basis_label,
    fact.modality || fact.certainty
      ? graphCertaintyLabel(fact.certainty || fact.modality, fact.basis_scope)
      : "",
  );
}

function graphQuickViewHtml() {
  if (state.quickViewLoading) {
    return `<aside class="db-node-quick-view" role="dialog" aria-modal="false" aria-label="${escapeHtml(t("quickView"))}"><div class="db-empty-state">${escapeHtml(t("quickViewLoading"))}</div></aside>`;
  }
  if (state.quickViewError) {
    return `<aside class="db-node-quick-view" role="dialog" aria-modal="false" aria-label="${escapeHtml(t("quickView"))}"><button type="button" class="db-quick-close" data-close-quick-view aria-label="${escapeHtml(t("closeQuickView"))}">×</button><div class="db-error-state">${escapeHtml(state.quickViewError)}</div></aside>`;
  }
  if (!state.quickView) return "";
  const summary = state.quickView.summary_current_state || {};
  const facts = state.quickView.facts_and_progress
    || state.quickView.facts
    || state.quickView.events
    || summary.facts
    || [];
  const factItems = Array.isArray(facts) ? facts : facts.items || [];
  const quickState = summary.state || summary.status;
  const quickModality = displayText(
    summary.state_basis_label,
    graphCertaintyLabel(
      summary.certainty || summary.state_basis_modality,
      summary.basis_scope || summary.state_basis_scope,
    ),
  );
  return `<aside class="db-node-quick-view" role="dialog" aria-modal="false" aria-labelledby="quick-view-title">
    <button type="button" class="db-quick-close" data-close-quick-view aria-label="${escapeHtml(t("closeQuickView"))}">×</button>
    <section class="db-quick-region">
      <p class="db-quick-kicker">${escapeHtml(t("summaryCurrentState"))}</p>
      <h4 id="quick-view-title" tabindex="-1">${escapeHtml(displayText(summary.title, t("quickView")))}</h4>
      <p>${escapeHtml(displayText(summary.summary, "—"))}</p>
      <dl>
        <div><dt>${escapeHtml(t("state"))}</dt><dd>${escapeHtml(stateLabel({ state: quickState }))}</dd></div>
        <div><dt>${escapeHtml(t("modality"))}</dt><dd>${escapeHtml(quickModality)}</dd></div>
        <div><dt>${escapeHtml(t("keyTime"))}</dt><dd title="${escapeHtml(displayStartDate(summary.start_time))}">${escapeHtml(displayStartDate(summary.start_time))}</dd></div>
      </dl>
      <section class="db-quick-facts" aria-label="${escapeHtml(t("factsAndProgress"))}">
        <h5>${escapeHtml(t("factsAndProgress"))}</h5>
        ${factItems.length ? `<ul>${factItems.map((fact) => {
          const factBody = quickFactBody(fact);
          const factBasis = quickFactBasis(fact);
          const factTime = displayStartDate(fact.claimed_time || fact.start_time || fact.relevant_time);
          return `<li>
            <strong>${escapeHtml(quickFactTitle(fact))}</strong>
            ${factBody ? `<p>${escapeHtml(factBody)}</p>` : ""}
            <span>${escapeHtml(factTime)}${factBasis ? ` · ${escapeHtml(factBasis)}` : ""}</span>
          </li>`;
        }).join("")}</ul>` : `<p class="db-empty-inline">${escapeHtml(t("noFacts"))}</p>`}
      </section>
    </section>
    <section class="db-quick-region">
      <p class="db-quick-kicker">${escapeHtml(t("filesLocations"))}</p>
      ${quickViewSourcesHtml(state.quickView)}
    </section>
  </aside>`;
}

function detailSituationGraph() {
  if (state.graphLoading && !state.situationGraph) {
    return `<div class="db-empty-state" role="status">${escapeHtml(t("coverageWorking"))}</div>`;
  }
  if (state.graphError && !state.situationGraph) {
    return `<div class="db-error-state" role="alert"><strong>${escapeHtml(t("graphUnavailable"))}</strong><p>${escapeHtml(state.graphError)}</p><button class="db-primary-button" data-retry-graph>${escapeHtml(t("retry"))}</button></div>`;
  }
  const graph = state.situationGraph;
  const visibleNodeCount = (graph?.nodes || []).filter(
    (node) => ["matter", "work_item"].includes(
      String(node.node_type || "").toLowerCase(),
    ),
  ).length;
  if ((!visibleNodeCount || visibleNodeCount === 1) && !graph?.has_more) {
    return `<div class="db-empty-state">${escapeHtml(t("noSubMatters"))}</div>`;
  }
  const layout = situationGraphLayout(graph);
  const edgeHtml = layout.edges.map((edge) => {
    const source = layout.positions.get(String(edge.source_node_id));
    const target = layout.positions.get(String(edge.target_node_id));
    if (!source || !target) return "";
    const x1 = source.x + source.width;
    const y1 = source.y + source.height / 2;
    const x2 = target.x;
    const y2 = target.y + target.height / 2;
    const mid = (x1 + x2) / 2;
    return `<path d="M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}" class="${edge.primary_containment ? "is-primary" : "is-secondary"}"></path>`;
  }).join("");
  const nodeHtml = layout.nodes.map((node) => {
    const id = String(node.node_id);
    const point = layout.positions.get(id);
    const attributes = node.attributes || {};
    const status = String(attributes.state || attributes.status || node.currentness || "");
    const technicalCurrentness = new Set(["current", "reported", "observed", "inferred"]);
    const statusLabel = technicalCurrentness.has(status.trim().toLowerCase())
      ? ""
      : status
        ? stateLabel({ state: status })
        : "";
    return `<article class="db-graph-node" data-node-type="${escapeHtml(node.node_type)}" data-status="${escapeHtml(canonicalStateKey({ state: status }))}" data-certainty="${escapeHtml(node.certainty)}" data-graph-x="${point.x}" data-graph-y="${point.y}">
      <button type="button" id="graph-node-${escapeHtml(id)}" class="db-graph-node-main" data-graph-node="${escapeHtml(id)}" aria-label="${escapeHtml(`${t("quickView")}: ${graphNodeTitle(node)}`)}">
         <strong>${escapeHtml(graphNodeTitle(node))}</strong>
        ${statusLabel ? `<span>${escapeHtml(statusLabel)}</span>` : ""}
      </button>
      ${String(node.certainty || "") === "ai_inferred" ? `<span class="db-graph-certainty">${escapeHtml(graphCertaintyLabel(node.certainty, attributes.basis_scope))}</span>` : ""}
    </article>`;
  }).join("");
  const miniNodes = layout.nodes.map((node) => {
    const point = layout.positions.get(String(node.node_id));
    return `<i data-graph-x="${Math.round((point.x / layout.width) * 100)}" data-graph-y="${Math.round((point.y / layout.height) * 100)}"></i>`;
  }).join("");
  return `<section class="db-situation-graph">
    <header class="db-graph-toolbar">
      <p>${escapeHtml(t("graphHelp"))}</p>
      <div>
        <button type="button" data-graph-zoom-out aria-label="${escapeHtml(t("graphZoomOut"))}">−</button>
        <output>${state.graphZoom.toFixed(2)}×</output>
        <button type="button" data-graph-zoom-in aria-label="${escapeHtml(t("graphZoomIn"))}">+</button>
        <button type="button" data-graph-reset>${escapeHtml(t("resetGraph"))}</button>
      </div>
    </header>
    ${state.graphError ? `<p class="db-browser-progress">${escapeHtml(t("showingLastKnown"))}</p>` : ""}
    <div class="db-graph-viewport" data-graph-viewport tabindex="0" aria-label="${escapeHtml(t("subMatters"))}">
      <div class="db-graph-inner" data-graph-inner data-graph-width="${layout.width}" data-graph-height="${layout.height}">
        <svg aria-hidden="true" width="${layout.width}" height="${layout.height}">${edgeHtml}</svg>
        ${nodeHtml}
      </div>
      <div class="db-graph-minimap" aria-hidden="true">${miniNodes}</div>
    </div>
    ${graph?.has_more ? `<button type="button" class="db-graph-load-more" data-graph-load-more ${state.graphLoadingMore ? "disabled" : ""}>${escapeHtml(state.graphLoadingMore ? t("loadingMoreSubMatters") : t("moreSubMatters"))}</button>` : ""}
    ${graphQuickViewHtml()}
  </section>`;
}

function detailSources(detail) {
  if (!detail.sources?.length) return `<div class="db-empty-state">${escapeHtml(t("noSources"))}</div>`;
  return `<ul class="db-list">${detail.sources.map((source) => `<li class="db-list-item">
    <h4>${escapeHtml(source.object_type || source.provider)}</h4>
    <p>${escapeHtml(source.provider)} · ${escapeHtml(value(source.disposition_label, source.disposition))}</p>
    ${source.next_stage ? `<p class="db-list-meta">${escapeHtml(source.next_stage)}</p>` : ""}
  </li>`).join("")}</ul>`;
}

function sourceTypeLabel(source) {
  const projectedType = source.type && typeof source.type === "object"
    ? displayText(source.type)
    : source.type;
  const raw = String(projectedType || source.object_type || source.kind || "").toLowerCase();
  const provider = String(source.provider || "").toLowerCase();
  if (raw.includes("mail") || raw.includes("message") || provider.includes("gmail")) {
    return state.locale === "zh-CN" ? "邮件" : "Email";
  }
  if (raw.includes("image") || raw.includes("photo")) {
    return state.locale === "zh-CN" ? "图片" : "Image";
  }
  if (raw.includes("document") || raw.includes("file") || provider.includes("filesystem")) {
    return state.locale === "zh-CN" ? "文件" : "File";
  }
  return state.locale === "zh-CN" ? "信息" : "Information";
}

function sourceAvailabilityLabel(source) {
  return displayText(
    source.localized_availability
      || source.availability?.label
      || source.availability,
    t("availableOnThisDevice"),
  );
}

function sourceModalityLabel(source) {
  const modalities = Array.isArray(source.modalities)
    ? source.modalities
    : source.modality
      ? [source.modality]
      : [];
  const labels = modalities.map((modality) => {
    const normalized = String(modality || "").trim().toLowerCase();
    if (normalized === "source_only") return t("sourceOnly");
    return t(`${normalized || "inferred"}Basis`);
  });
  return labels.length ? [...new Set(labels)].join(" / ") : t("sourceOnly");
}

function sourceLocationLabel(source) {
  return displayText(
    source.privacy_safe_location || source.location_group,
    t("availableOnThisDevice"),
  );
}

function sourceLabel(source, index) {
  return displayText(
    source.localized_label || source.label || source.title || source.name,
    `${sourceTypeLabel(source)} ${index + 1}`,
  );
}

function sourceEvidenceItems(source) {
  const items = state.evidence?.items || [];
  const objectId = String(source.record_ref || source.object_id || source.source_id || "");
  if (!objectId) return [];
  return items.filter((entry) => {
    const direct = String(entry.object_id || entry.source_object_id || entry.source_id || "");
    return direct === objectId || JSON.stringify(entry.location || {}).includes(objectId);
  });
}

function sourceDisclosure(source) {
  const items = sourceEvidenceItems(source);
  return `<details class="db-file-disclosure">
    <summary>${escapeHtml(t("evidenceAndHistory"))}</summary>
    ${state.evidence
      ? items.length
        ? `<ul class="db-file-evidence-list">${items.slice(0, 12).map((entry) => `<li><p>${escapeHtml(entry.excerpt || "")}</p><span>${escapeHtml(t(`${entry.modality || "inferred"}Basis`))}</span></li>`).join("")}</ul>`
        : `<p>${escapeHtml(t("noEvidence"))}</p>`
      : `<button type="button" class="db-secondary-button" data-load-evidence>${escapeHtml(t("evidenceForRecord"))}</button>`}
  </details>`;
}

function detailFilesInformation(detail) {
  const projected = detail.files_and_information
    || detail.files_information
    || detail.filesInformation;
  const flatRows = Array.isArray(projected)
    ? projected
    : Array.isArray(projected?.items)
      ? projected.items
      : (detail.sources || []);
  if (!flatRows.length) return `<div class="db-empty-state">${escapeHtml(t("noSources"))}</div>`;
  return `<div class="db-files-table-scroll">
    <table class="db-files-table">
      <thead><tr>
        <th scope="col">${escapeHtml(t("fileOrInformation"))}</th>
        <th scope="col">${escapeHtml(t("type"))}</th>
        <th scope="col">${escapeHtml(t("location"))}</th>
        <th scope="col">${escapeHtml(t("sourceGroup"))}</th>
        <th scope="col">${escapeHtml(t("observedTime"))}</th>
        <th scope="col">${escapeHtml(t("contentSummary"))}</th>
        <th scope="col">${escapeHtml(t("availability"))}</th>
        <th scope="col">${escapeHtml(t("informationModality"))}</th>
      </tr></thead>
      <tbody>
        ${flatRows.slice(0, 50).map((source, index) => {
          const result = displayText(
            source.localized_summary
              || source.summary
              || source.current_result
              || source.disposition_label,
            "—",
          );
          return `<tr>
            <th scope="row">
              <strong>${escapeHtml(sourceLabel(source, index))}</strong>
              ${sourceDisclosure(source)}
            </th>
            <td>${escapeHtml(sourceTypeLabel(source))}</td>
            <td>${escapeHtml(sourceLocationLabel(source))}</td>
            <td>${escapeHtml(displayText(source.location_group, "—"))}</td>
            <td>${escapeHtml(displayStartDate(
              source.observed_time
                || source.relevant_time
                || source.claimed_time
                || source.record_time,
            ))}</td>
            <td>${escapeHtml(result)}</td>
            <td>${escapeHtml(sourceAvailabilityLabel(source))}</td>
            <td>${escapeHtml(sourceModalityLabel(source))}</td>
          </tr>`;
        }).join("")}
      </tbody>
    </table>
  </div>`;
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

function galleryImages(detail) {
  const projected = Array.isArray(detail.images)
    ? detail.images
    : Array.isArray(detail.images?.items)
      ? detail.images.items
      : [];
  const candidates = [
    ...projected,
    ...(detail.visual_candidates || []),
  ];
  const seen = new Set();
  return candidates.filter((asset) => {
    if (!["photo", "existing_image"].includes(String(asset.kind || ""))) {
      return false;
    }
    const token = String(asset.preview_token || "");
    if (!token || seen.has(token)) return false;
    seen.add(token);
    return true;
  }).sort((left, right) => {
    const selected = String(detail.images?.selected_preview_token || "");
    return Number(String(right.preview_token || "") === selected)
      - Number(String(left.preview_token || "") === selected);
  });
}

function resetGalleryView({ keepSelection = true } = {}) {
  if (!keepSelection) state.gallerySelectedIndex = 0;
  state.galleryZoom = 1;
  state.galleryPan = { x: 0, y: 0 };
  galleryDrag = null;
}

function clampGalleryIndex(images, index = state.gallerySelectedIndex) {
  if (!images.length) return 0;
  return Math.max(0, Math.min(images.length - 1, index));
}

function detailImages(detail) {
  const images = galleryImages(detail);
  if (!images.length) return `<div class="db-empty-state">${escapeHtml(t("noImages"))}</div>`;
  state.gallerySelectedIndex = clampGalleryIndex(images);
  const selected = images[state.gallerySelectedIndex];
  const alt = displayText(selected.alt, `${t("selectedImage")} ${state.gallerySelectedIndex + 1}`);
  const transform = `translate3d(${state.galleryPan.x}px, ${state.galleryPan.y}px, 0) scale(${state.galleryZoom})`;
  return `<section class="db-image-gallery" data-image-gallery aria-label="${escapeHtml(t("images"))}">
    <div class="db-gallery-toolbar">
      <button type="button" data-gallery-previous aria-label="${escapeHtml(t("imagePrevious"))}" ${state.gallerySelectedIndex === 0 ? "disabled" : ""}>←</button>
      <button type="button" data-gallery-zoom-out aria-label="${escapeHtml(t("zoomOut"))}" ${state.galleryZoom <= 0.5 ? "disabled" : ""}>−</button>
      <output class="db-gallery-zoom-value" aria-live="polite">${state.galleryZoom.toFixed(2)}×</output>
      <button type="button" data-gallery-zoom-in aria-label="${escapeHtml(t("zoomIn"))}" ${state.galleryZoom >= 5 ? "disabled" : ""}>+</button>
      <button type="button" data-gallery-reset>${escapeHtml(t("resetZoom"))}</button>
      <button type="button" data-gallery-next aria-label="${escapeHtml(t("imageNext"))}" ${state.gallerySelectedIndex === images.length - 1 ? "disabled" : ""}>→</button>
    </div>
    <div class="db-gallery-stage${state.galleryZoom > 1 ? " is-zoomed" : ""}" data-gallery-stage tabindex="0" aria-label="${escapeHtml(t("selectedImage"))}">
      <img data-gallery-image src="/api/visuals/${encodeURIComponent(selected.preview_token)}?size=hero" alt="${escapeHtml(alt)}" draggable="false" style="transform: ${escapeHtml(transform)}">
    </div>
    <p class="db-gallery-help">${escapeHtml(t("imageZoomHelp"))}</p>
    <div class="db-gallery-thumbnails" role="listbox" aria-label="${escapeHtml(t("imageThumbnails"))}">
      ${images.map((asset, index) => {
        const thumbnailAlt = displayText(asset.alt, `${t("images")} ${index + 1}`);
        return `<button type="button" role="option" class="db-gallery-thumbnail" data-gallery-index="${index}" aria-selected="${index === state.gallerySelectedIndex}" aria-label="${escapeHtml(thumbnailAlt)}">
          <img src="/api/visuals/${encodeURIComponent(asset.preview_token)}" alt="" loading="lazy" decoding="async">
        </button>`;
      }).join("")}
    </div>
  </section>`;
}

function detailAiSupplementalInformation(detail) {
  const payload = detail.ai_supplemental_information
    || detail.sections?.ai_supplemental_information
    || {};
  const items = Array.isArray(payload) ? payload : payload.items || [];
  if (!items.length) {
    const status = String(payload.status || "pending").trim().toLowerCase();
    const statusKey = {
      pending: "supplementalPending",
      blocked: "supplementalBlocked",
      unavailable: "supplementalUnavailable",
      stale: "supplementalStale",
      not_applicable: "supplementalNotApplicable",
    }[status] || "noSupplementalInformation";
    return `<div class="db-empty-state" data-supplemental-status="${escapeHtml(status)}">${escapeHtml(t(statusKey))}</div>`;
  }
  return `<div class="db-supplemental-list">${items.map((item) => `
    <article class="db-supplemental-card">
      <h4>${escapeHtml(displayText(item.title, t("aiSupplementalInformation")))}</h4>
      <p>${escapeHtml(displayText(item.body))}</p>
      ${item.relevant_time ? `<time>${escapeHtml(displayStartDate(item.relevant_time))}</time>` : ""}
    </article>`).join("")}</div>`;
}

function detailBody(detail) {
  return {
    overview: detailOverview,
    subMatters: detailSituationGraph,
    timeline: detailTimeline,
    people: detailPeople,
    relatedMatters: detailRelated,
    filesInformation: detailFilesInformation,
    images: detailImages,
    aiSupplementalInformation: detailAiSupplementalInformation,
  }[state.detailSection]?.(detail) || detailOverview(detail);
}

function detailHtml() {
  if (!state.selectedMatterId) return "";
  if (state.detailLoading || !state.detail) {
    return "";
  }
  const detail = state.detail;
  const card = detail.matter;
  const childTotal = state.situationGraph?.nodes
    ? state.situationGraph.nodes.filter((node) => {
      const nodeType = String(node.node_type || "").toLowerCase();
      return ["matter", "work_item"].includes(nodeType)
        && String(node.node_id || "") !== String(state.selectedMatterId);
    }).length
    : detail.children_summary?.total_count
      ?? detail.children_summary?.total
      ?? 0;
  const filesTotal = detail.files_and_information?.total_count
    ?? detail.files_information?.total_count
    ?? detail.filesInformation?.total_count
    ?? detail.sources?.length
    ?? 0;
  const imagesTotal = detail.images?.total_count ?? galleryImages(detail).length;
  const supplementalTotal = detail.ai_supplemental_information?.total_count
    ?? detail.sections?.ai_supplemental_information?.total_count
    ?? 0;
  return `<div class="db-dialog-overlay" data-dialog-overlay>
    <section class="db-dialog" role="dialog" aria-modal="true" aria-labelledby="detail-title" data-detail-matter-id="${escapeHtml(state.selectedMatterId)}">
      <button class="db-dialog-close" data-close-detail aria-label="${escapeHtml(t("close"))}">×</button>
      <aside class="db-detail-rail">
        <header class="db-detail-brand"><div class="db-detail-brand-heading"><img class="db-brand-mark" src="/matters-icon.png" alt="" aria-hidden="true"><h2 id="detail-title" tabindex="-1">${escapeHtml(displayText(card.title))}</h2></div></header>
        <nav class="db-detail-nav" aria-label="${escapeHtml(t("navigation"))}">
          ${detailNavItem("overview", "overview")}
          ${detailNavItem("subMatters", "subMatters", formatCount(childTotal))}
          ${detailNavItem("timeline", "timeline", detail.timeline?.length || 0)}
          ${detailNavItem("people", "people", detail.people?.length || 0)}
          ${detailNavItem("relatedMatters", "relatedMatters", detail.related_matters?.length || 0)}
          ${detailNavItem("filesInformation", "filesInformation", filesTotal)}
          ${detailNavItem("images", "images", imagesTotal)}
          ${detailNavItem("aiSupplementalInformation", "aiSupplementalInformation", supplementalTotal)}
        </nav>
      </aside>
      <main class="db-detail-reader">
        <header class="db-reader-header"><h3>${escapeHtml(t(state.detailSection))}</h3>${state.detailSection === "overview" ? "" : `<span class="db-reader-status" data-group="${escapeHtml(canonicalStateKey(card))}">${escapeHtml(stateLabel(card))}</span>`}</header>
        ${detailBody(detail)}
      </main>
    </section>
  </div>`;
}

function render() {
  const snapshot = saveViewState();
  const catalog = currentCatalog();
  const renderedView = renderedCatalogView();
  const transportCurrent = !["transport_error", "ready_stale"].includes(state.transportPhase);
  const healthTone = coverageHealthTone(transportCurrent);
  app.innerHTML = `
    <button class="db-mobile-nav-toggle" data-mobile-menu aria-label="${escapeHtml(t("menu"))}">☰</button>
    ${state.mobileOpen ? '<button class="db-sidebar-backdrop" data-mobile-close aria-label="Close"></button>' : ""}
    <div class="db-shell" data-browser-shell-layout data-transport-state="${escapeHtml(state.transportPhase)}">
      <aside class="db-sidebar" data-open="${state.mobileOpen}">
        <div class="db-sidebar-top">
          <header class="db-sidebar-brand"><div class="db-sidebar-brand-copy"><img class="db-brand-mark" src="/matters-icon.png" alt="" aria-hidden="true"><h1>Matters</h1></div></header>
          <label class="db-search-shell">
            <span class="db-search-icon">${icon("search")}</span>
            <span class="db-sr-only">${escapeHtml(t("search"))}</span>
            <input id="matters-search" class="db-search-input" type="search" value="${escapeHtml(state.query)}" placeholder="${escapeHtml(t("search"))}">
          </label>
          ${activeFilterChipsHtml()}
        </div>
        <div class="db-sidebar-scroll">
          <p class="db-sidebar-heading">${escapeHtml(t("navigation"))}</p>
          <nav class="db-nav-list">
            <button type="button" class="db-nav-item" data-clear-all aria-current="${allFiltersClear() ? "page" : "false"}">
              <span class="db-nav-icon">${icon("all")}</span>
              <span class="db-nav-label">${escapeHtml(t("all"))}</span>
              <span class="db-nav-count">${formatCount(catalog?.facets?.status?.all ?? catalog?.total_count)}</span>
            </button>
          </nav>
          <div class="db-filter-groups">
            ${filterGroupHtml({ name: "status", labelKey: "status", iconName: "progress", single: true, includeAll: true })}
            ${filterGroupHtml({ name: "start_year", labelKey: "startTime", iconName: "calendar", single: true, includeAll: true })}
            ${filterGroupHtml({ name: "people", labelKey: "peopleFilter", iconName: "people" })}
            ${filterGroupHtml({ name: "relationships", labelKey: "relationshipsFilter", iconName: "relationship" })}
            ${filterGroupHtml({ name: "topic_types", labelKey: "topicTypeFilter", iconName: "topic" })}
            ${filterGroupHtml({ name: "source_types", labelKey: "sourceTypeFilter", iconName: "source" })}
          </div>
        </div>
        <footer class="db-sidebar-footer">
          <button id="settings-button" class="db-sidebar-settings" data-settings aria-expanded="${state.settingsOpen}"><span>${icon("settings")}</span><span>${escapeHtml(t("settings"))}</span></button>
          ${state.settingsOpen ? `<div class="db-settings-menu"><label class="db-settings-language-field"><span>${escapeHtml(t("language"))}</span><select id="locale-select">${localeOptionsHtml()}</select></label></div>` : ""}
        </footer>
      </aside>
      <main class="db-main">
        <header class="db-project-list-header">
          <h2>${escapeHtml(allFiltersClear(renderedView.filters) && !renderedView.query ? t("titleAll") : t("titleFiltered"))}</h2>
          <div class="db-project-header-meta">
            <span>${formatCount(catalogDisplayCount())} · ${escapeHtml(t("matters"))}</span>
            <button type="button" class="db-card-density-switch" role="switch" aria-checked="${state.density === "compact"}" data-density aria-label="${escapeHtml(t("density"))}">
              <span class="${state.density === "standard" ? "is-active" : ""}">${escapeHtml(t("standard"))}</span><span class="db-card-density-track"><span></span></span><span class="${state.density === "compact" ? "is-active" : ""}">${escapeHtml(t("compact"))}</span>
            </button>
            <div class="db-source-health">
              <button type="button" class="db-source-health-button" data-health data-tone="${healthTone}" aria-expanded="${state.healthOpen}">
                <span class="db-source-health-light"></span><strong>${escapeHtml(t("coverage"))}</strong><span aria-hidden="true">·</span><span>${escapeHtml(transportCurrent ? coverageStatusLabel() : t("reconnecting"))}</span>
              </button>
              ${coveragePanel()}
            </div>
          </div>
        </header>
        <section class="db-project-grid${renderedView.query ? " db-project-grid--search" : ""}" data-card-density="${state.density}" aria-label="${escapeHtml(t("titleAll"))}">
          ${gridHtml()}
        </section>
      </main>
    </div>
    ${detailHtml()}
    ${state.toast ? `<div class="db-toast" role="status">${escapeHtml(state.toast)}</div>` : ""}
  `;
  restoreViewState(snapshot);
  updateGraphDom();
  updateGalleryDom();
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
}

async function fetchJson(url, options = {}) {
  const timeoutMs = Number(options.timeoutMs || API_TIMEOUT_MS);
  const requestOptions = { ...options };
  delete requestOptions.timeoutMs;
  const controller = new AbortController();
  const upstreamSignal = requestOptions.signal;
  let timedOut = false;
  const abortFromUpstream = () => controller.abort(upstreamSignal.reason);
  if (upstreamSignal?.aborted) abortFromUpstream();
  else upstreamSignal?.addEventListener("abort", abortFromUpstream, { once: true });
  const timeoutId = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  try {
    const response = await fetch(url, {
      ...requestOptions,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(requestOptions.headers || {}),
      },
    });
    const payload = await response.json();
    if (!response.ok || payload.ok !== true) {
      throw new Error(payload.error?.code || `HTTP ${response.status}`);
    }
    return payload.result;
  } catch (error) {
    if (timedOut) {
      const timeoutError = new Error("request_timeout");
      timeoutError.name = "TimeoutError";
      throw timeoutError;
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
    upstreamSignal?.removeEventListener("abort", abortFromUpstream);
  }
}

function applyLocaleRegistry(registry) {
  const definitions = Array.isArray(registry?.locales) ? registry.locales : [];
  const declaredAvailable = Array.isArray(registry?.available_locales)
    ? registry.available_locales.map(String)
    : [];
  const selectable = new Set(
    definitions
      .filter((definition) => definition?.selectable !== false)
      .map((definition) => String(definition?.tag || ""))
      .filter(Boolean),
  );
  const availableLocales = declaredAvailable.filter((locale) => selectable.has(locale));
  const defaultLocale = String(registry?.default_locale || "");
  if (!availableLocales.length || !availableLocales.includes(defaultLocale)) {
    throw new Error("invalid_locale_registry");
  }
  state.localeRegistry = {
    ...registry,
    default_locale: defaultLocale,
    available_locales: availableLocales,
    locales: definitions,
  };
  const storedLocale = localStorage.getItem(STORAGE.locale);
  state.locale = storedLocale && availableLocales.includes(storedLocale)
    ? storedLocale
    : defaultLocale;
  if (storedLocale && !availableLocales.includes(storedLocale)) {
    localStorage.removeItem(STORAGE.locale);
  }
}

async function loadLocaleRegistry(signal) {
  applyLocaleRegistry(await fetchJson("/api/locales", { signal }));
}

function browserQueryParams(offset = 0) {
  const params = new URLSearchParams({
    locale: state.locale,
    query: state.query,
    status: state.filters.status,
    time: "all",
    sort: "activity",
    offset: String(offset),
    limit: "200",
    root_only: state.query ? "false" : "true",
  });
  if (state.filters.start_year !== "all") params.set("start_year", state.filters.start_year);
  [
    ["people", state.filters.people],
    ["relationships", state.filters.relationships],
    ["topic_type", state.filters.topic_types],
    ["source_type", state.filters.source_types],
  ].forEach(([name, values]) => {
    values.forEach((filterValue) => params.append(name, filterValue));
  });
  return params;
}

function successfulTransportPhase(result) {
  const catalog = result?.catalog || {};
  const coverage = result?.coverage || {};
  const visibleCount = Number(catalog.total_count || 0);
  const unfilteredCount = Number(catalog.facets?.status?.all || 0);
  if (visibleCount > 0) return "ready";
  if ((!allFiltersClear() || Boolean(state.query)) && unfilteredCount > 0) {
    return "no_filter_results";
  }
  const pendingCount = Number(coverage.pending_object_count || 0);
  const registeredCount = Number(coverage.registered_object_count || 0);
  if (
    pendingCount > 0
    || coverage.coverage_status === "partial"
    || (registeredCount > 0 && coverage.coverage_status !== "complete")
  ) {
    return "processing";
  }
  return "honest_empty";
}

function catalogRenderIdentity(result) {
  return JSON.stringify(result?.catalog || {});
}

function updateCoverageStatusDom() {
  const transportCurrent = !["transport_error", "ready_stale"].includes(state.transportPhase);
  const healthTone = coverageHealthTone(transportCurrent);
  const healthButton = document.querySelector(".db-source-health-button");
  if (healthButton) {
    healthButton.dataset.tone = healthTone;
    const title = healthButton.querySelector("strong");
    const status = healthButton.querySelector("span:last-child");
    if (title) title.textContent = t("coverage");
    if (status) {
      status.textContent = transportCurrent ? coverageStatusLabel() : t("reconnecting");
    }
  }
  const panel = document.querySelector(".db-source-health-panel");
  if (panel) panel.outerHTML = coveragePanel();
}

async function loadCoverageAudit(filters = {}, { summaryOnly = false } = {}) {
  const requestId = ++state.coverageAuditRequestId;
  state.coverageAuditLoading = true;
  state.coverageAuditError = "";
  state.coverageAuditFilters = { ...filters };
  if (state.healthOpen) render();
  const params = new URLSearchParams({
    offset: "0",
    limit: summaryOnly ? "1" : "100",
    surface_only: "true",
  });
  for (const key of (
    ["surface_id", "surface_status", "owner_id", "failure_class", "freshness"]
  )) {
    const filterValue = String(filters[key] || "").trim();
    if (filterValue) params.set(key, filterValue);
  }
  if (typeof filters.ui_ready === "boolean") {
    params.set("ui_ready", String(filters.ui_ready));
  }
  try {
    const audit = await fetchJson(
      `/api/coverage/audit?${params.toString()}`,
      { timeoutMs: 30_000 },
    );
    if (requestId !== state.coverageAuditRequestId) return;
    state.coverageAudit = audit;
    state.coverageAuditLoadedAt = Date.now();
  } catch (error) {
    if (requestId !== state.coverageAuditRequestId) return;
    state.coverageAuditError = error.message;
  } finally {
    if (requestId === state.coverageAuditRequestId) {
      state.coverageAuditLoading = false;
      if (state.healthOpen) render();
      else updateCoverageStatusDom();
    }
  }
}

function scheduleBrowserRefresh(delayMs) {
  window.clearTimeout(browserRefreshTimer);
  browserRefreshTimer = window.setTimeout(() => {
    browserRefreshTimer = null;
    void loadBrowser({ background: true });
  }, delayMs);
}

async function loadBrowser({ background = false } = {}) {
  const requestId = ++state.requestId;
  window.clearTimeout(browserRefreshTimer);
  browserRefreshTimer = null;
  catalogController?.abort();
  catalogController = new AbortController();
  const priorCatalogIdentity = catalogRenderIdentity(state.browser);
  state.loading = true;
  if (!background || !state.browser) {
    state.transportPhase = state.browser ? "processing" : "loading";
  }
  state.error = "";
  if (!background || !state.browser) render();
  try {
    await loadLocaleRegistry(catalogController.signal);
    if (requestId !== state.requestId) return;
    const params = browserQueryParams(0);
    const result = await fetchJson(`/api/browser?${params}`, { signal: catalogController.signal });
    if (requestId !== state.requestId) return;
    state.browser = result;
    state.lastSuccessfulView = {
      query: state.query,
      filters: copyFilters(),
    };
    state.loading = false;
    state.retryAttempt = 0;
    state.transportPhase = successfulTransportPhase(result);
    if (!background || priorCatalogIdentity !== catalogRenderIdentity(result)) {
      render();
    } else {
      updateCoverageStatusDom();
    }
    if (
      !state.coverageAudit
      || Date.now() - state.coverageAuditLoadedAt >= 30_000
    ) {
      void loadCoverageAudit(
        state.healthOpen ? state.coverageAuditFilters : {},
        { summaryOnly: !state.healthOpen },
      );
    }
    scheduleBrowserRefresh(state.transportPhase === "processing" ? 3000 : 30000);
  } catch (error) {
    if (error.name === "AbortError") return;
    if (requestId !== state.requestId) return;
    state.loading = false;
    state.error = error.message;
    state.transportPhase = state.browser ? "ready_stale" : "transport_error";
    state.retryAttempt += 1;
    state.focusCatalogErrorOnRender = true;
    if (background && state.browser) updateCoverageStatusDom();
    else render();
    scheduleBrowserRefresh(Math.min(30000, 1000 * (2 ** Math.min(state.retryAttempt - 1, 5))));
  }
}

async function loadMore() {
  const catalog = currentCatalog();
  if (!catalog || state.loadingMore || !catalog.has_more || catalog.next_offset == null) return;
  state.loadingMore = true;
  render();
  const params = browserQueryParams(catalog.next_offset);
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

function resetGraphView() {
  state.graphZoom = 1;
  state.graphPan = { x: 0, y: 0 };
  graphDrag = null;
  updateGraphDom();
}

function mergeSituationGraphPages(current, incoming) {
  if (!current) {
    return {
      ...incoming,
      nodes: [...(incoming.nodes || [])],
      edges: [...(incoming.edges || [])],
    };
  }
  if (
    current.snapshot_id
    && incoming.snapshot_id
    && current.snapshot_id !== incoming.snapshot_id
  ) throw new Error("graph_snapshot_changed");
  const nodes = new Map((current.nodes || []).map((node) => [String(node.node_id), node]));
  (incoming.nodes || []).forEach((node) => nodes.set(String(node.node_id), node));
  const edges = new Map((current.edges || []).map((edge) => [
    String(edge.edge_id || `${edge.source_node_id}|${edge.relation_type}|${edge.target_node_id}`),
    edge,
  ]));
  (incoming.edges || []).forEach((edge) => edges.set(
    String(edge.edge_id || `${edge.source_node_id}|${edge.relation_type}|${edge.target_node_id}`),
    edge,
  ));
  return {
    ...current,
    ...incoming,
    offset: 0,
    nodes: [...nodes.values()],
    edges: [...edges.values()],
  };
}

function graphContainsNode(graph, nodeId) {
  return Boolean((graph?.nodes || []).some((node) => String(node.node_id) === String(nodeId)));
}

function focusGraphNode(nodeId, { openQuickView = false } = {}) {
  if (!nodeId) return;
  requestAnimationFrame(() => {
    const button = document.getElementById(`graph-node-${nodeId}`);
    const node = button?.closest?.(".db-graph-node");
    const viewport = document.querySelector("[data-graph-viewport]");
    if (!button || !node || !viewport) return;
    const x = Number(node.dataset.graphX || 0);
    const y = Number(node.dataset.graphY || 0);
    state.graphPan = {
      x: Math.round((viewport.clientWidth / 2) - ((x + 107) * state.graphZoom)),
      y: Math.round((viewport.clientHeight / 2) - ((y + 38) * state.graphZoom)),
    };
    updateGraphDom();
    button.focus();
    if (openQuickView) void loadNodeQuickView(nodeId, { originNodeId: nodeId });
  });
}

function closeNodeQuickView() {
  const originNodeId = state.quickViewOriginNodeId;
  state.quickView = null;
  state.quickViewError = "";
  state.quickViewLoading = false;
  state.quickViewOriginNodeId = "";
  render();
  focusGraphNode(originNodeId);
}

async function loadSituationGraph({ continuation = "", append = false, focusNodeId = "" } = {}) {
  if (!state.selectedMatterId) return;
  const matterId = state.selectedMatterId;
  const requestId = ++state.graphRequestId;
  state.graphLoading = !append;
  state.graphLoadingMore = append;
  state.graphError = "";
  render();
  let aggregate = append ? state.situationGraph : null;
  let targetAvailable = false;
  try {
    let cursor = continuation;
    let pages = 0;
    do {
      const params = new URLSearchParams({
        locale: state.locale,
        limit: String(GRAPH_PAGE_SIZE),
      });
      if (cursor) params.set("continuation", cursor);
      const page = await fetchJson(
        `/api/matters/${encodeURIComponent(matterId)}/graph?${params.toString()}`,
      );
      if (state.selectedMatterId !== matterId || state.graphRequestId !== requestId) return;
      aggregate = mergeSituationGraphPages(aggregate, page);
      pages += 1;
      targetAvailable = focusNodeId ? graphContainsNode(aggregate, focusNodeId) : false;
      cursor = String(page.next_continuation || "");
      if (!focusNodeId || targetAvailable || !page.has_more || pages >= GRAPH_FOCUS_PAGE_LIMIT) break;
    } while (cursor);
    state.situationGraph = aggregate;
    if (!append) resetGraphView();
  } catch (error) {
    if (state.selectedMatterId !== matterId || state.graphRequestId !== requestId) return;
    state.graphError = error.message;
    if (aggregate) state.situationGraph = aggregate;
  } finally {
    if (state.selectedMatterId === matterId && state.graphRequestId === requestId) {
      state.graphLoading = false;
      state.graphLoadingMore = false;
      render();
      if (targetAvailable) focusGraphNode(focusNodeId, { openQuickView: true });
    }
  }
}

async function loadNodeQuickView(nodeId, { originNodeId = nodeId } = {}) {
  if (!state.selectedMatterId || !nodeId) return;
  const matterId = state.selectedMatterId;
  const requestId = ++state.quickViewRequestId;
  state.quickViewLoading = true;
  state.quickViewError = "";
  state.quickView = null;
  state.quickViewOriginNodeId = String(originNodeId || nodeId);
  render();
  try {
    const quickView = await fetchJson(
      `/api/matters/${encodeURIComponent(matterId)}/nodes/${encodeURIComponent(nodeId)}/quick-view?locale=${encodeURIComponent(state.locale)}`,
    );
    if (state.selectedMatterId !== matterId || state.quickViewRequestId !== requestId) return;
    state.quickView = quickView;
  } catch (error) {
    if (state.selectedMatterId !== matterId || state.quickViewRequestId !== requestId) return;
    state.quickViewError = error.message;
  } finally {
    if (state.selectedMatterId === matterId && state.quickViewRequestId === requestId) {
      state.quickViewLoading = false;
      render();
      requestAnimationFrame(() => document.getElementById("quick-view-title")?.focus());
    }
  }
}

async function loadDetail(matterId, { section = "overview", focusTitle = true, focusNodeId = "" } = {}) {
  state.selectedMatterId = matterId;
  state.detailLoading = true;
  state.detail = null;
  state.detailSection = section;
  state.focusDetailOnRender = focusTitle;
  state.situationGraph = null;
  state.graphLoading = false;
  state.graphLoadingMore = false;
  state.graphError = "";
  state.quickView = null;
  state.quickViewLoading = false;
  state.quickViewError = "";
  state.quickViewOriginNodeId = "";
  resetGraphView();
  state.evidence = null;
  resetGalleryView({ keepSelection: false });
  render();
  try {
    state.detail = await fetchJson(`/api/matters/${encodeURIComponent(matterId)}?locale=${encodeURIComponent(state.locale)}`);
    state.detailLoading = false;
    render();
    if (focusNodeId) await loadSituationGraph({ focusNodeId });
    else void loadSituationGraph();
    return true;
  } catch (error) {
    state.detailLoading = false;
    showToast(error.message);
    return false;
  }
}

async function openDetail(matterId) {
  lastCardFocus = document.activeElement?.closest?.("[data-matter-id]")?.id || `matter-card-${matterId}`;
  const opened = await loadDetail(matterId);
  if (!opened) closeDetail();
}

async function openCatalogResult(card) {
  const matchedMatterId = String(card.dataset.matchedNodeId || card.dataset.matterId || "");
  const rootMatterId = String(card.dataset.owningRootMatterId || matchedMatterId);
  if (!rootMatterId) return;
  lastCardFocus = card.id || `matter-card-${matchedMatterId || rootMatterId}`;
  const isDescendant = Boolean(matchedMatterId && matchedMatterId !== rootMatterId);
  const opened = await loadDetail(rootMatterId, {
    section: isDescendant ? "subMatters" : "overview",
    focusTitle: !isDescendant,
    focusNodeId: isDescendant ? matchedMatterId : "",
  });
  if (!opened) closeDetail();
}

async function refreshCurrentDetail() {
  if (!state.selectedMatterId) return;
  const matterId = state.selectedMatterId;
  const section = state.detailSection;
  try {
    const detail = await fetchJson(`/api/matters/${encodeURIComponent(matterId)}?locale=${encodeURIComponent(state.locale)}`);
    if (state.selectedMatterId !== matterId) return;
    state.detail = detail;
    state.detailSection = section;
    render();
    void loadSituationGraph();
  } catch (error) {
    showToast(error.message);
  }
}

async function reloadLocalizedDetails() {
  if (!state.selectedMatterId) return;
  const currentId = state.selectedMatterId;
  try {
    const detail = await fetchJson(`/api/matters/${encodeURIComponent(currentId)}?locale=${encodeURIComponent(state.locale)}`);
    if (state.selectedMatterId !== currentId) return;
    state.detail = detail;
    state.quickView = null;
    render();
    void loadSituationGraph();
  } catch (error) {
    showToast(error.message);
  }
}

function closeDetail() {
  state.selectedMatterId = "";
  state.detail = null;
  state.focusDetailOnRender = false;
  state.situationGraph = null;
  state.graphLoading = false;
  state.graphLoadingMore = false;
  state.graphError = "";
  state.quickView = null;
  state.quickViewLoading = false;
  state.quickViewError = "";
  state.quickViewOriginNodeId = "";
  resetGraphView();
  resetGalleryView({ keepSelection: false });
  state.evidence = null;
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

function updateGalleryDom() {
  const image = document.querySelector("[data-gallery-image]");
  if (image) {
    image.style.transform = `translate3d(${state.galleryPan.x}px, ${state.galleryPan.y}px, 0) scale(${state.galleryZoom})`;
  }
  const stage = document.querySelector("[data-gallery-stage]");
  stage?.classList.toggle("is-zoomed", state.galleryZoom > 1);
  const output = document.querySelector(".db-gallery-zoom-value");
  if (output) output.textContent = `${state.galleryZoom.toFixed(2)}×`;
  const zoomOut = document.querySelector("[data-gallery-zoom-out]");
  const zoomIn = document.querySelector("[data-gallery-zoom-in]");
  if (zoomOut instanceof HTMLButtonElement) zoomOut.disabled = state.galleryZoom <= 0.5;
  if (zoomIn instanceof HTMLButtonElement) zoomIn.disabled = state.galleryZoom >= 5;
}

function updateGraphDom() {
  const inner = document.querySelector("[data-graph-inner]");
  if (inner) {
    inner.style.width = `${Number(inner.dataset.graphWidth || 0)}px`;
    inner.style.height = `${Number(inner.dataset.graphHeight || 0)}px`;
    inner.style.transform = `translate3d(${state.graphPan.x}px, ${state.graphPan.y}px, 0) scale(${state.graphZoom})`;
  }
  document.querySelectorAll("[data-graph-x][data-graph-y].db-graph-node").forEach((node) => {
    node.style.left = `${Number(node.dataset.graphX || 0)}px`;
    node.style.top = `${Number(node.dataset.graphY || 0)}px`;
  });
  document.querySelectorAll(".db-graph-minimap [data-graph-x][data-graph-y]").forEach((node) => {
    node.style.left = `${Number(node.dataset.graphX || 0)}%`;
    node.style.top = `${Number(node.dataset.graphY || 0)}%`;
  });
  const output = document.querySelector(".db-graph-toolbar output");
  if (output) output.textContent = `${state.graphZoom.toFixed(2)}×`;
}

function setGraphZoom(nextZoom) {
  state.graphZoom = Math.max(
    0.45,
    Math.min(2.25, Math.round(nextZoom * 100) / 100),
  );
  updateGraphDom();
}

function setGalleryZoom(nextZoom) {
  state.galleryZoom = Math.max(0.5, Math.min(5, Math.round(nextZoom * 100) / 100));
  if (state.galleryZoom <= 1) state.galleryPan = { x: 0, y: 0 };
  updateGalleryDom();
}

function selectGalleryImage(index, { focus = true } = {}) {
  const images = galleryImages(state.detail || {});
  if (!images.length) return;
  state.gallerySelectedIndex = clampGalleryIndex(images, index);
  resetGalleryView();
  render();
  if (focus) {
    requestAnimationFrame(() => {
      document.querySelector(`[data-gallery-index="${state.gallerySelectedIndex}"]`)?.focus();
    });
  }
}

app.addEventListener("click", (event) => {
  const target = event.target instanceof Element ? event.target : null;
  if (!target) return;
  if (target.closest("[data-clear-all]")) {
    clearAllFilters();
    state.activeFilterGroup = null;
    state.mobileOpen = false;
    loadBrowser();
    return;
  }
  const filterGroup = target.closest("[data-filter-group]")?.dataset.filterGroup;
  if (filterGroup) {
    state.activeFilterGroup = state.activeFilterGroup === filterGroup ? null : filterGroup;
    render();
    return;
  }
  const filterOption = target.closest("[data-filter-name]");
  if (filterOption) {
    const name = filterOption.dataset.filterName;
    const filterValue = filterOption.dataset.filterValue;
    if (filterOption.dataset.filterSingle === "true") {
      state.filters[name] = filterValue;
    } else {
      const selected = new Set(state.filters[name]);
      if (selected.has(filterValue)) selected.delete(filterValue);
      else selected.add(filterValue);
      state.filters[name] = [...selected];
    }
    loadBrowser();
    return;
  }
  const clearFilter = target.closest("[data-clear-filter]");
  if (clearFilter) {
    const name = clearFilter.dataset.clearFilter;
    const filterValue = clearFilter.dataset.clearValue;
    state.filters[name] = Array.isArray(state.filters[name])
      ? state.filters[name].filter((entry) => entry !== filterValue)
      : "all";
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
  const coverageDrilldown = target.closest("[data-coverage-drilldown]");
  if (coverageDrilldown) {
    const uiReadyValue = coverageDrilldown.dataset.coverageUiReady;
    void loadCoverageAudit({
      surface_id: coverageDrilldown.dataset.coverageSurfaceId || "",
      surface_status: coverageDrilldown.dataset.coverageSurfaceStatus || "",
      owner_id: coverageDrilldown.dataset.coverageOwnerId || "",
      failure_class: coverageDrilldown.dataset.coverageFailureClass || "",
      freshness: coverageDrilldown.dataset.coverageFreshness || "",
      ...(uiReadyValue === "true" || uiReadyValue === "false"
        ? { ui_ready: uiReadyValue === "true" }
        : {}),
    });
    return;
  }
  if (target.closest("[data-coverage-clear]")) {
    void loadCoverageAudit({});
    return;
  }
  const card = target.closest("[data-matter-id]");
  if (card) {
    openCatalogResult(card);
    return;
  }
  if (target.closest("[data-density]")) {
    state.density = state.density === "standard" ? "compact" : "standard";
    localStorage.setItem(STORAGE.density, state.density);
    render();
    return;
  }
  if (target.closest("[data-health]")) {
    const opening = !state.healthOpen;
    state.healthOpen = opening;
    state.settingsOpen = false;
    render();
    if (opening) void loadCoverageAudit({});
    return;
  }
  if (target.closest("[data-settings]")) {
    const opening = !state.settingsOpen;
    state.settingsOpen = opening;
    state.healthOpen = false;
    render();
    if (opening) requestAnimationFrame(() => document.getElementById("locale-select")?.focus());
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
  const graphNode = target.closest("[data-graph-node]")?.dataset.graphNode;
  if (graphNode) {
    loadNodeQuickView(graphNode, { originNodeId: graphNode });
    return;
  }
  if (target.closest("[data-graph-load-more]")) {
    const continuation = String(state.situationGraph?.next_continuation || "");
    if (continuation) void loadSituationGraph({ continuation, append: true });
    return;
  }
  if (target.closest("[data-graph-zoom-out]")) {
    setGraphZoom(state.graphZoom - 0.15);
    return;
  }
  if (target.closest("[data-graph-zoom-in]")) {
    setGraphZoom(state.graphZoom + 0.15);
    return;
  }
  if (target.closest("[data-graph-reset]")) {
    resetGraphView();
    return;
  }
  if (target.closest("[data-retry-graph]")) {
    loadSituationGraph();
    return;
  }
  if (target.closest("[data-close-quick-view]")) {
    closeNodeQuickView();
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
  const galleryIndex = target.closest("[data-gallery-index]")?.dataset.galleryIndex;
  if (galleryIndex != null) {
    selectGalleryImage(Number.parseInt(galleryIndex, 10));
    return;
  }
  if (target.closest("[data-gallery-previous]")) {
    selectGalleryImage(state.gallerySelectedIndex - 1);
    return;
  }
  if (target.closest("[data-gallery-next]")) {
    selectGalleryImage(state.gallerySelectedIndex + 1);
    return;
  }
  if (target.closest("[data-gallery-zoom-out]")) {
    setGalleryZoom(state.galleryZoom - 0.25);
    return;
  }
  if (target.closest("[data-gallery-zoom-in]")) {
    setGalleryZoom(state.galleryZoom + 0.25);
    return;
  }
  if (target.closest("[data-gallery-reset]")) {
    resetGalleryView();
    updateGalleryDom();
    return;
  }
  if (target.closest("[data-load-evidence]")) {
    loadEvidence();
    return;
  }
  if (target.closest("[data-retry]")) loadBrowser();
});

app.addEventListener("keydown", (event) => {
  const target = event.target instanceof Element ? event.target : null;
  const graph = target?.closest("[data-graph-viewport]");
  if (graph && ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "+", "=", "-"].includes(event.key)) {
    event.preventDefault();
    if (event.key === "Home") resetGraphView();
    else if (event.key === "+" || event.key === "=") setGraphZoom(state.graphZoom + 0.15);
    else if (event.key === "-") setGraphZoom(state.graphZoom - 0.15);
    else {
      state.graphPan = {
        x: state.graphPan.x + (event.key === "ArrowLeft" ? 36 : event.key === "ArrowRight" ? -36 : 0),
        y: state.graphPan.y + (event.key === "ArrowUp" ? 36 : event.key === "ArrowDown" ? -36 : 0),
      };
      updateGraphDom();
    }
    return;
  }
  const gallery = target?.closest("[data-image-gallery]");
  if (gallery && ["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
    event.preventDefault();
    const lastIndex = Math.max(0, galleryImages(state.detail || {}).length - 1);
    const index = event.key === "Home"
      ? 0
      : event.key === "End"
        ? lastIndex
        : state.gallerySelectedIndex + (event.key === "ArrowLeft" ? -1 : 1);
    selectGalleryImage(index);
    return;
  }
  if (target?.id === "matters-search" && event.key === "Escape" && state.query) {
    event.preventDefault();
    state.query = "";
    loadBrowser();
    return;
  }
  if (target?.id === "matters-search" && event.key === "ArrowDown" && state.query) {
    event.preventDefault();
    document.querySelector(".db-search-result")?.focus();
    return;
  }
  const card = target?.closest("[data-matter-id]");
  if (card && !event.repeat && (event.key === "Enter" || event.key === " ")) {
    event.preventDefault();
    openCatalogResult(card);
  }
});

app.addEventListener("wheel", (event) => {
  const target = event.target instanceof Element ? event.target : null;
  if (target?.closest("[data-graph-viewport]")) {
    event.preventDefault();
    setGraphZoom(state.graphZoom + (event.deltaY < 0 ? 0.12 : -0.12));
    return;
  }
  if (!target?.closest("[data-gallery-stage]")) return;
  event.preventDefault();
  setGalleryZoom(state.galleryZoom + (event.deltaY < 0 ? 0.25 : -0.25));
}, { passive: false });

app.addEventListener("pointerdown", (event) => {
  const target = event.target instanceof Element ? event.target : null;
  const graphViewport = target?.closest("[data-graph-viewport]");
  if (
    graphViewport
    && !target.closest("button")
  ) {
    graphDrag = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: state.graphPan.x,
      originY: state.graphPan.y,
    };
    graphViewport.setPointerCapture?.(event.pointerId);
    graphViewport.classList.add("is-panning");
    return;
  }
  const stage = target?.closest("[data-gallery-stage]");
  if (!stage || state.galleryZoom <= 1) return;
  galleryDrag = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    originX: state.galleryPan.x,
    originY: state.galleryPan.y,
  };
  stage.setPointerCapture?.(event.pointerId);
  stage.classList.add("is-panning");
});

app.addEventListener("pointermove", (event) => {
  if (graphDrag && graphDrag.pointerId === event.pointerId) {
    state.graphPan = {
      x: graphDrag.originX + event.clientX - graphDrag.startX,
      y: graphDrag.originY + event.clientY - graphDrag.startY,
    };
    updateGraphDom();
    return;
  }
  if (!galleryDrag || galleryDrag.pointerId !== event.pointerId) return;
  state.galleryPan = {
    x: galleryDrag.originX + event.clientX - galleryDrag.startX,
    y: galleryDrag.originY + event.clientY - galleryDrag.startY,
  };
  updateGalleryDom();
});

function endGalleryPan(event) {
  if (graphDrag && graphDrag.pointerId === event.pointerId) {
    document.querySelector("[data-graph-viewport]")?.classList.remove("is-panning");
    graphDrag = null;
  }
  if (!galleryDrag || galleryDrag.pointerId !== event.pointerId) return;
  document.querySelector("[data-gallery-stage]")?.classList.remove("is-panning");
  galleryDrag = null;
}

app.addEventListener("pointerup", endGalleryPan);
app.addEventListener("pointercancel", endGalleryPan);

app.addEventListener("input", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement) || target.id !== "matters-search") return;
  state.query = target.value;
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(loadBrowser, 240);
});

app.addEventListener("change", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement) || target.id !== "locale-select") return;
  if (!state.localeRegistry?.available_locales?.includes(target.value)) return;
  state.locale = target.value;
  localStorage.setItem(STORAGE.locale, state.locale);
  state.settingsOpen = false;
  loadBrowser();
  if (state.selectedMatterId) void reloadLocalizedDetails();
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
    if (state.quickView || state.quickViewLoading || state.quickViewError) {
      closeNodeQuickView();
    } else if (state.selectedMatterId) closeDetail();
    else if (state.mobileOpen || state.settingsOpen || state.healthOpen) {
      const restoreSettings = state.settingsOpen;
      state.mobileOpen = false;
      state.settingsOpen = false;
      state.healthOpen = false;
      render();
      if (restoreSettings) requestAnimationFrame(() => document.getElementById("settings-button")?.focus());
    }
  }
});

loadBrowser();
