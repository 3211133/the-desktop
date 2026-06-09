"""news モジュールの単体テスト — pure (ネットワーク非依存)。"""

from __future__ import annotations

import pytest

from the_desktop.features.news import (
    DEFAULT_LIMIT,
    DEFAULT_URL,
    NewsConfig,
    NewsFeed,
    NewsItem,
    format_item,
    format_item_rich,
    load_config,
    parse_rss,
    save_config,
)


_SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>NHK</title>
    <item>
      <title>関東地方で記録的な大雨</title>
      <link>https://example.com/a</link>
      <pubDate>Tue, 09 Jun 2026 10:30:00 +0900</pubDate>
      <description>前線の影響で関東甲信地方は午前中に記録的な雨量を観測。</description>
    </item>
    <item>
      <title>半導体大手、設備投資を拡大</title>
      <link>https://example.com/b</link>
      <pubDate>Tue, 09 Jun 2026 10:15:00 +0900</pubDate>
      <description><![CDATA[国内の<b>半導体</b>メーカーが投資拡大]]></description>
    </item>
    <item>
      <title>タイトルだけで pubDate なし</title>
      <link>https://example.com/c</link>
    </item>
  </channel>
</rss>
"""


def test_parse_rss_extracts_items():
    feed = parse_rss(_SAMPLE_RSS)
    assert len(feed.items) == 3
    assert feed.items[0].title == "関東地方で記録的な大雨"
    assert feed.items[0].url == "https://example.com/a"
    assert "2026" in feed.items[0].pub_date
    assert "関東甲信" in feed.items[0].description


def test_parse_rss_strips_html_in_description():
    feed = parse_rss(_SAMPLE_RSS)
    assert feed.items[1].description == "国内の半導体メーカーが投資拡大"


def test_parse_rss_respects_limit():
    feed = parse_rss(_SAMPLE_RSS, limit=2)
    assert len(feed.items) == 2


def test_parse_rss_broken_xml_returns_empty():
    assert parse_rss("not xml").items == []


def test_parse_rss_skips_item_missing_title_or_link():
    xml = """<?xml version="1.0"?><rss><channel>
      <item><title>no link</title></item>
      <item><link>https://x</link></item>
      <item><title>both</title><link>https://y</link></item>
    </channel></rss>"""
    feed = parse_rss(xml)
    assert len(feed.items) == 1
    assert feed.items[0].title == "both"


def test_news_feed_truthiness():
    assert not NewsFeed()
    assert NewsFeed(items=[NewsItem("t", "u", "")])


# ── format_item ────────────────────────────────────────────────────────────

def test_format_item_with_valid_pub_date():
    item = NewsItem("テスト記事", "https://x", "Tue, 09 Jun 2026 10:30:00 +0900")
    assert format_item(item) == "10:30  テスト記事"


def test_format_item_without_pub_date():
    item = NewsItem("テスト記事", "https://x", "")
    assert format_item(item) == "テスト記事"


def test_format_item_with_unparseable_pub_date():
    item = NewsItem("テスト記事", "https://x", "yesterday")
    assert format_item(item) == "テスト記事"


# ── format_item_rich (サイクル表示用 HTML) ──────────────────────────────────

def test_format_item_rich_includes_title_and_description():
    item = NewsItem("見出し", "https://x", "Tue, 09 Jun 2026 10:30:00 +0900", "サマリ本文")
    html = format_item_rich(item)
    assert "見出し" in html
    assert "サマリ本文" in html
    assert "10:30" in html


def test_format_item_rich_omits_description_block_when_empty():
    item = NewsItem("見出し", "https://x", "", "")
    html = format_item_rich(item)
    assert "見出し" in html
    assert "<div style='color:#999" not in html


def test_format_item_rich_escapes_html_in_title():
    item = NewsItem("<script>", "https://x", "", "<b>x</b>")
    html = format_item_rich(item)
    assert "&lt;script&gt;" in html
    assert "&lt;b&gt;x&lt;/b&gt;" in html


# ── 設定ファイル ──────────────────────────────────────────────────────────

def test_default_url_is_nhk_cat0():
    assert DEFAULT_URL.startswith("https://www.nhk.or.jp/rss/news/")


def test_default_limit_is_unlimited():
    """0 は無制限 (RSS が返す全件)。"""
    assert DEFAULT_LIMIT == 0


def test_parse_rss_unlimited_returns_all():
    feed = parse_rss(_SAMPLE_RSS, limit=0)
    assert len(feed.items) == 3  # サンプル全件
    feed2 = parse_rss(_SAMPLE_RSS, limit=-1)
    assert len(feed2.items) == 3


def test_load_missing_returns_default(tmp_path):
    assert load_config(tmp_path / "nope.json") == NewsConfig()


def test_load_broken_falls_back(tmp_path):
    p = tmp_path / "news.json"
    p.write_text("not json", encoding="utf-8")
    assert load_config(p) == NewsConfig()


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "news.json"
    save_config(NewsConfig(url="https://other.example/rss", limit=5), p)
    loaded = load_config(p)
    assert loaded.url == "https://other.example/rss"
    assert loaded.limit == 5


# ── Widget スモーク ────────────────────────────────────────────────────────

def _make_widget(qtbot, monkeypatch, items, opener=None):
    monkeypatch.delenv("THE_DESKTOP_DEV_MOCKS", raising=False)
    from the_desktop.features.news import NewsWidget

    def fake_fetcher(url, limit):
        return NewsFeed(items=items)

    w = NewsWidget(
        url="x",
        limit=len(items),
        fetcher=fake_fetcher,
        opener=opener or (lambda u: None),
        fade_duration_ms=0,  # tests: アニメ無し
        cycle_interval_ms=10_000,  # 自動進行はテストで止める
    )
    qtbot.addWidget(w)
    return w


def test_widget_shows_first_item_initially(qtbot, monkeypatch):
    items = [
        NewsItem("見出しA", "https://example.com/a", ""),
        NewsItem("見出しB", "https://example.com/b", ""),
    ]
    w = _make_widget(qtbot, monkeypatch, items)
    qtbot.waitUntil(lambda: "見出しA" in w.label.text(), timeout=2000)
    assert w._index == 0


def test_widget_advances_to_next_item(qtbot, monkeypatch):
    items = [
        NewsItem("A", "https://example.com/a", ""),
        NewsItem("B", "https://example.com/b", ""),
        NewsItem("C", "https://example.com/c", ""),
    ]
    w = _make_widget(qtbot, monkeypatch, items)
    qtbot.waitUntil(lambda: "A" in w.label.text(), timeout=2000)
    w._advance()
    assert w._index == 1
    assert ">B<" in w.label.text() or w.label.text().endswith("B")
    w._advance()
    assert w._index == 2
    assert ">C<" in w.label.text() or w.label.text().endswith("C")


def test_widget_wraps_around_to_first(qtbot, monkeypatch):
    items = [
        NewsItem("A", "https://example.com/a", ""),
        NewsItem("B", "https://example.com/b", ""),
    ]
    w = _make_widget(qtbot, monkeypatch, items)
    qtbot.waitUntil(lambda: "A" in w.label.text(), timeout=2000)
    w._advance()  # B
    w._advance()  # back to A
    assert w._index == 0
    assert "A" in w.label.text()


def test_widget_click_opens_current_url(qtbot, monkeypatch):
    items = [
        NewsItem("A", "https://example.com/a", ""),
        NewsItem("B", "https://example.com/b", ""),
    ]
    captured = []
    w = _make_widget(qtbot, monkeypatch, items, opener=captured.append)
    qtbot.waitUntil(lambda: "A" in w.label.text(), timeout=2000)
    w._open_current()
    assert captured == ["https://example.com/a"]
    w._advance()
    w._open_current()
    assert captured == ["https://example.com/a", "https://example.com/b"]


def test_widget_handles_fetcher_failure(qtbot, monkeypatch):
    monkeypatch.delenv("THE_DESKTOP_DEV_MOCKS", raising=False)
    from the_desktop.features.news import NewsWidget

    def boom(url, limit):
        raise RuntimeError("network down")

    w = NewsWidget(
        fetcher=boom,
        opener=lambda u: None,
        fade_duration_ms=0,
        cycle_interval_ms=10_000,
    )
    qtbot.addWidget(w)
    qtbot.waitUntil(lambda: w.label.text() == "取得失敗", timeout=2000)


def test_widget_does_not_advance_without_items(qtbot, monkeypatch):
    """fetch 失敗状態で _advance() を呼んでも例外にならない。"""
    monkeypatch.delenv("THE_DESKTOP_DEV_MOCKS", raising=False)
    from the_desktop.features.news import NewsWidget

    w = NewsWidget(
        fetcher=lambda u, l: NewsFeed(),
        opener=lambda u: None,
        fade_duration_ms=0,
        cycle_interval_ms=10_000,
    )
    qtbot.addWidget(w)
    qtbot.waitUntil(lambda: w.label.text() == "取得失敗", timeout=2000)
    w._advance()  # no-op
    assert w.label.text() == "取得失敗"


# ── ホバーで一覧表示・離脱で自動遷移再開 ──────────────────────────────────

def test_widget_swaps_to_list_on_hover(qtbot, monkeypatch):
    """カーソルが入ったら QListWidget に切替、cycle timer 停止。"""
    items = [
        NewsItem("A", "https://example.com/a", ""),
        NewsItem("B", "https://example.com/b", ""),
    ]
    w = _make_widget(qtbot, monkeypatch, items)
    qtbot.waitUntil(lambda: "A" in w.label.text(), timeout=2000)

    assert w._stack.currentWidget() is w.label
    assert w._cycle_timer.isActive()

    w._set_hovered(True)
    assert w._stack.currentWidget() is w.list
    assert not w._cycle_timer.isActive()
    assert w.list.count() == 2

    w._set_hovered(False)
    assert w._stack.currentWidget() is w.label
    assert w._cycle_timer.isActive()


def test_list_view_activate_opens_clicked_item(qtbot, monkeypatch):
    items = [
        NewsItem("A", "https://example.com/a", ""),
        NewsItem("B", "https://example.com/b", ""),
        NewsItem("C", "https://example.com/c", ""),
    ]
    captured = []
    w = _make_widget(qtbot, monkeypatch, items, opener=captured.append)
    qtbot.waitUntil(lambda: "A" in w.label.text(), timeout=2000)
    w._set_hovered(True)

    w.list.itemActivated.emit(w.list.item(2))
    assert captured == ["https://example.com/c"]


def test_hover_ignored_when_no_items(qtbot, monkeypatch):
    """取得失敗時はホバーしても何も切り替えない。"""
    monkeypatch.delenv("THE_DESKTOP_DEV_MOCKS", raising=False)
    from the_desktop.features.news import NewsWidget
    w = NewsWidget(
        fetcher=lambda u, l: NewsFeed(),
        opener=lambda u: None,
        fade_duration_ms=0,
        cycle_interval_ms=10_000,
    )
    qtbot.addWidget(w)
    qtbot.waitUntil(lambda: w.label.text() == "取得失敗", timeout=2000)
    before = w._stack.currentWidget()
    w._set_hovered(True)
    assert w._stack.currentWidget() is before
