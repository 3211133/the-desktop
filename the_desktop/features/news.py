"""ニュース機能 — NHK RSS から最新記事を取ってリスト表示。

エンドポイント (デフォルト): https://www.nhk.or.jp/rss/news/cat0.xml
カテゴリは `config/news.json` で変更可能 (例: cat1.xml=社会、cat6.xml=スポーツ)。

操作:
  矢印キー: 記事を選択
  Enter:    記事 URL をブラウザで開く
"""

from __future__ import annotations

import json
import threading
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QStackedWidget,
    QWidget,
)

from ..paths import config_path

DEFAULT_URL = "https://www.nhk.or.jp/rss/news/cat0.xml"
DEFAULT_LIMIT = 0  # 0 = 上限なし (RSS が返す全件)
CONFIG_FILE = config_path("news")

# 1件あたりの表示時間とフェード時間
CYCLE_INTERVAL_MS = 3000
FADE_DURATION_MS = 400

# RSS 再取得の間隔 (5分)
FETCH_INTERVAL_MS = 5 * 60 * 1000


@dataclass
class NewsConfig:
    url: str = DEFAULT_URL
    limit: int = DEFAULT_LIMIT


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str
    pub_date: str  # ISO8601 or 元の文字列のフォールバック
    description: str = ""  # 記事サマリ (RSS の <description>、HTML タグ除去済み)


@dataclass
class NewsFeed:
    items: list[NewsItem] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.items)


# ── Pure ロジック ──────────────────────────────────────────────────────────

def load_config(path: Path = CONFIG_FILE) -> NewsConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return NewsConfig(
            url=str(raw.get("url", DEFAULT_URL)),
            limit=int(raw.get("limit", DEFAULT_LIMIT)),
        )
    except Exception:
        return NewsConfig()


def save_config(cfg: NewsConfig, path: Path = CONFIG_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"url": cfg.url, "limit": cfg.limit}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


_TAG_RE = __import__("re").compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """description にしばしば含まれる HTML タグを除去。"""
    return _TAG_RE.sub("", text).strip()


def parse_rss(xml_text: str, limit: int = DEFAULT_LIMIT) -> NewsFeed:
    """RSS 2.0 (channel/item/title|link|pubDate|description) を解析。

    limit <= 0 のときは上限なし (RSS が返す全件)。
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return NewsFeed()

    items: list[NewsItem] = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        url = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        desc = _strip_html(it.findtext("description") or "")
        if title and url:
            items.append(NewsItem(title=title, url=url, pub_date=pub, description=desc))
        if 0 < limit <= len(items):
            break
    return NewsFeed(items=items)


def format_item(item: NewsItem) -> str:
    """リスト表示用の1行文字列。時刻が読めれば "HH:MM タイトル"。"""
    hhmm = _try_parse_hhmm(item.pub_date)
    if hhmm:
        return f"{hhmm}  {item.title}"
    return item.title


def format_item_rich(item: NewsItem) -> str:
    """サイクル表示用の HTML。タイトル太字 + サマリ小さめグレー。"""
    hhmm = _try_parse_hhmm(item.pub_date)
    head = f"<span style='color:#888'>{hhmm}</span>  " if hhmm else ""
    title = item.title.replace("<", "&lt;").replace(">", "&gt;")
    desc = item.description.replace("<", "&lt;").replace(">", "&gt;")
    body = (
        f"<div style='color:#999; font-size: 11px; margin-top: 4px;'>{desc}</div>"
        if desc
        else ""
    )
    return (
        f"<div style='font-weight: 600;'>{head}{title}</div>"
        f"{body}"
    )


def _try_parse_hhmm(pub_date: str) -> str:
    """RSS の pubDate (RFC 822) を "HH:MM" に。失敗時は空。"""
    if not pub_date:
        return ""
    # 例: "Mon, 09 Jun 2026 15:30:00 +0900"
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"):
        try:
            dt = datetime.strptime(pub_date, fmt)
            return dt.strftime("%H:%M")
        except ValueError:
            continue
    return ""


def fetch_news(url: str, limit: int = DEFAULT_LIMIT, timeout: float = 5.0) -> NewsFeed:
    """RSS を取得して NewsFeed を返す。"""
    req = urllib.request.Request(url, headers={"User-Agent": "the-desktop/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return parse_rss(body, limit=limit)


# ── Widget ─────────────────────────────────────────────────────────────────

Fetcher = Callable[[str, int], NewsFeed]


class _ClickableLabel(QLabel):
    """クリックで signal を出す QLabel。"""

    clicked = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(e)


class NewsWidget(QWidget):
    """ニュース見出しを 1件ずつフェード切替で表示。クリックで記事を開く。

    記事は CYCLE_INTERVAL_MS ごとに次へ進む。フェードは
    FADE_DURATION_MS かけて 0 → 1 に opacity を上げる。
    """

    updated = pyqtSignal(NewsFeed)

    def __init__(
        self,
        url: str | None = None,
        limit: int | None = None,
        fetcher: Fetcher | None = None,
        opener: Callable[[str], None] | None = None,
        fade_duration_ms: int = FADE_DURATION_MS,
        cycle_interval_ms: int = CYCLE_INTERVAL_MS,
        parent=None,
    ) -> None:
        super().__init__(parent)
        cfg = load_config()
        self.url = url or cfg.url
        self.limit = limit if limit is not None else cfg.limit
        if fetcher is None:
            from ..dev import is_dev_mocks_enabled
            if is_dev_mocks_enabled():
                from ..dev import mock_news_fetcher
                fetcher = mock_news_fetcher
            else:
                fetcher = fetch_news
        self._fetcher = fetcher
        self._opener = opener or webbrowser.open
        self._fade_duration = fade_duration_ms

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # ── 単一行 (フェード切替) と一覧 (スクロール) を切替えるための stack ──
        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack)

        # フェードビュー
        self.label = _ClickableLabel(self._stack)
        self.label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.clicked.connect(self._open_current)
        self._stack.addWidget(self.label)

        self._effect = QGraphicsOpacityEffect(self.label)
        self._effect.setOpacity(1.0)
        self.label.setGraphicsEffect(self._effect)

        # 一覧ビュー (ホバー中に出す)
        self.list = QListWidget(self._stack)
        self.list.itemActivated.connect(self._open_from_list)
        self._stack.addWidget(self.list)

        self._items: list[NewsItem] = []
        self._index = 0
        self._anim: QPropertyAnimation | None = None

        self.updated.connect(self._apply)

        self._cycle_timer = QTimer(self)
        self._cycle_timer.setInterval(cycle_interval_ms)
        self._cycle_timer.timeout.connect(self._advance)

        self._fetch_timer = QTimer(self)
        self._fetch_timer.setInterval(FETCH_INTERVAL_MS)
        self._fetch_timer.timeout.connect(self._refresh)
        self._fetch_timer.start()
        self._refresh()

    # ── 取得 ──────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self) -> None:
        try:
            feed = self._fetcher(self.url, self.limit)
        except Exception:
            feed = NewsFeed()
        self.updated.emit(feed)

    def _apply(self, feed: NewsFeed) -> None:
        self._items = list(feed.items)
        self._index = 0

        # 一覧ビュー側を更新
        self.list.clear()

        if not self._items:
            self._cycle_timer.stop()
            self.label.setText("取得失敗")
            self.list.addItem(QListWidgetItem("取得失敗"))
            return

        for it in self._items:
            self.list.addItem(QListWidgetItem(format_item(it)))

        self._show_current()
        self._animate_fade_in()
        if self._stack.currentWidget() is self.label:
            self._cycle_timer.start()

    # ── 切替 ──────────────────────────────────────────────────────────────

    def _advance(self) -> None:
        if not self._items:
            return
        self._index = (self._index + 1) % len(self._items)
        self._show_current()
        self._animate_fade_in()

    def _show_current(self) -> None:
        if not self._items:
            return
        self.label.setText(format_item_rich(self._items[self._index]))

    def _animate_fade_in(self) -> None:
        if self._fade_duration <= 0:
            self._effect.setOpacity(1.0)
            return
        anim = QPropertyAnimation(self._effect, b"opacity")
        anim.setDuration(self._fade_duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start()
        self._anim = anim  # 参照保持

    # ── ホバーで一覧 ⇄ フェード切替 ────────────────────────────────────────

    def _set_hovered(self, hovered: bool) -> None:
        """ホバー状態を内部に反映 (テスト seam)。"""
        if not self._items:
            return
        if hovered:
            self._stack.setCurrentWidget(self.list)
            self._cycle_timer.stop()
        else:
            self._stack.setCurrentWidget(self.label)
            self._cycle_timer.start()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._set_hovered(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._set_hovered(False)
        super().leaveEvent(event)

    # ── クリック / 開く ────────────────────────────────────────────────────

    def _open_current(self) -> None:
        if 0 <= self._index < len(self._items):
            self._opener(self._items[self._index].url)

    def _open_from_list(self, item: QListWidgetItem) -> None:
        idx = self.list.row(item)
        if 0 <= idx < len(self._items):
            self._opener(self._items[idx].url)
