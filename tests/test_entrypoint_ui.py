from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

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
    assert "en: {" in javascript
    assert '"zh-CN": {' in javascript
    assert 'locale: "matters-locale"' in javascript
    assert (
        'localStorage.getItem(STORAGE.locale) === "zh-CN" ? "zh-CN" : "en"'
        in javascript
    )
    assert '<option value="en"' in javascript
    assert '<option value="zh-CN"' in javascript
    assert "Search matters" in javascript
    assert "All matters" in javascript
    assert "搜索事项" in javascript
    assert "全部事项" in javascript


def test_entrypoint_ui_uses_only_autonomous_browser_and_post_result_routes():
    javascript = (UI_ROOT / "app.js").read_text(encoding="utf-8")

    for route in (
        "/api/browser?",
        "/api/matters/${encodeURIComponent(matterId)}?locale=",
        "/api/matters/${encodeURIComponent(state.selectedMatterId)}/evidence",
        "/api/matters/${encodeURIComponent(state.selectedMatterId)}/corrections",
        "/api/matters/${encodeURIComponent(state.selectedMatterId)}/cover",
        "/api/visuals/${encodeURIComponent(visual.preview_token)}",
    ):
        assert route in javascript

    for retired_route in (
        "/api/projection",
        "/api/tracking-intents",
        "/api/review-queue",
        "/api/understanding",
        "/api/understanding-intents",
    ):
        assert retired_route not in javascript

    assert "Review queue" not in javascript
    assert "待确认队列" not in javascript
    assert "confirm" not in javascript.casefold()
    assert "automatic result" in javascript.casefold()
    assert "自动结果" in javascript
    assert "Working in background" in javascript
    assert "正在后台处理" in javascript


def test_entrypoint_ui_supports_standard_and_compact_cards_with_same_visual():
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
    assert 'state.density === "standard" ? `<div class="db-card-metrics">' in javascript
    assert (
        '<img src="/api/visuals/${encodeURIComponent(visual.preview_token)}"'
        in javascript
    )
    assert "No current authorized image yet." in javascript
    assert "目前还没有当前且已授权的图片。" in javascript
    assert "db-card-summary" in javascript
    assert "db-card-people" in javascript
    assert "card.event_count" in javascript
    assert "card.people_count" in javascript
    assert "card.source_count" in javascript
    assert "data-load-more" in javascript
    assert "catalog.next_offset" in javascript
    assert "items: [...existing, ...appended]" in javascript

    assert "grid-template-columns: 264px minmax(0, 1fr)" in css
    assert "grid-template-columns: repeat(3, minmax(0, 360px))" in css
    assert '.db-project-grid[data-card-density="compact"]' in css
    assert "repeat(auto-fit, 180px)" in css
    assert "aspect-ratio: 20 / 21" in css
    assert ".db-project-card--compact .db-card-media" in css
    assert ".db-card-metrics" in css
    assert ".db-card-copy" in css


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
    assert "claimedTime" in javascript
    assert "recordTime" in javascript
    assert "modality" in javascript
    assert "evidencePrivacy" in javascript
    assert 'id="correction-error"' in javascript
    assert "state.correctionDraft" in javascript
    assert "focusCorrectionErrorOnRender" in javascript
    assert 'detailNavItem("openLoops", "openLoops"' in javascript
    assert 'detailNavItem("relatedMatters", "relatedMatters"' in javascript

    assert "width: min(1400px, calc(100vw - 48px))" in css
    assert "height: min(900px, calc(100vh - 48px))" in css
    assert "grid-template-columns: 236px minmax(0, 1fr)" in css
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
