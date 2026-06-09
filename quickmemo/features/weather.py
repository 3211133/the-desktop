"""天気予報機能 — 気象庁 (JMA) から週間予報を取得して絵文字で表示。

エンドポイント:
    https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json

area_code は気象台の office code (例: 東京=130000、大阪=270000、福岡=400000)。
レスポンスは [短期, 週間] の2要素配列で、週間部分の timeSeries[0] に
weatherCodes が並ぶ。

絵文字は先頭桁で分類: 1=晴 2=曇 3=雨 4=雪 (それ以外は ❓)。
"""

from __future__ import annotations

import json
import threading
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QWidget

from ..paths import config_path

DEFAULT_AREA = "130000"  # 東京
CONFIG_FILE = config_path("weather")
JMA_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{area}.json"


@dataclass
class WeatherConfig:
    area: str = DEFAULT_AREA


@dataclass
class WeeklyForecast:
    """週間予報の生データ。長さは原則 7、不揃いはそのまま保持。"""
    codes: list[int] = field(default_factory=list)
    temps_max: list[str] = field(default_factory=list)
    temps_min: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.codes)


# ── Pure ロジック ──────────────────────────────────────────────────────────

def load_config(path: Path = CONFIG_FILE) -> WeatherConfig:
    """`{"area": "130000"}` を読み込む。不存在・破損は DEFAULT。"""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return WeatherConfig(area=str(raw.get("area", DEFAULT_AREA)))
    except Exception:
        return WeatherConfig()


def save_config(cfg: WeatherConfig, path: Path = CONFIG_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"area": cfg.area}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# JMA 電文コードを絵文字へ。情報量を重視:
#   ☀ 晴 / ⛅ 晴+曇 / ☁ 曇 / 🌦 晴/曇+雨混在 / 🌧 雨 / 🌨 雨雪混在 / ❄ 雪 /
#   ⛈ 雷雨 / 🌫 霧
#
# 完全網羅ではないが主要コードはカバー。未収録は先頭桁で粗くフォールバック。
# 出力時に U+FE0F (VS-16) を付けてカラー絵文字スタイルを強制する (環境依存軽減)。
_VS16 = "️"

_CODE_EMOJI: dict[int, str] = {
    # 晴れベース 1xx
    100: "☀", 101: "⛅", 102: "🌦", 103: "🌦", 104: "🌨", 105: "🌨",
    106: "🌨", 107: "🌨", 108: "⛈",
    110: "⛅", 111: "⛅", 112: "🌦", 113: "🌦", 114: "🌦",
    115: "🌨", 116: "🌨", 117: "🌨", 118: "🌨", 119: "⛈",
    120: "🌦", 121: "🌦", 122: "🌦", 123: "⛈", 124: "🌨",
    125: "⛈", 126: "🌦", 127: "🌦", 128: "🌦",
    130: "☀", 131: "☀", 132: "⛅", 140: "⛈",
    # 曇りベース 2xx
    200: "☁", 201: "⛅", 202: "🌦", 203: "🌦", 204: "🌨", 205: "🌨",
    206: "🌨", 207: "🌨", 208: "⛈", 209: "🌫",
    210: "⛅", 211: "⛅", 212: "🌦", 213: "🌦", 214: "🌧",
    215: "🌨", 216: "🌨", 217: "🌨", 218: "🌨", 219: "⛈",
    220: "🌦", 221: "🌦", 222: "🌦", 223: "⛅", 224: "🌦",
    225: "🌦", 226: "🌦", 228: "🌨", 229: "🌨", 230: "🌨",
    231: "🌫", 240: "⛈", 250: "⛈",
    # 雨ベース 3xx
    300: "🌧", 301: "🌦", 302: "🌧", 303: "🌨", 304: "🌨",
    306: "🌧", 307: "⛈", 308: "⛈", 309: "🌨",
    311: "🌦", 313: "🌧", 314: "🌨", 315: "🌨", 316: "🌦", 317: "🌧",
    320: "🌦", 321: "🌧", 322: "🌨", 323: "🌦", 324: "🌦",
    325: "🌦", 326: "🌨", 327: "🌨", 328: "🌧", 329: "🌨",
    340: "🌨", 350: "⛈", 361: "🌦", 371: "🌧",
    # 雪ベース 4xx
    400: "❄", 401: "❄", 402: "❄", 403: "🌨", 405: "❄",
    406: "❄", 407: "❄", 409: "🌨",
    411: "❄", 413: "🌨", 414: "❄",
    420: "❄", 421: "❄", 422: "🌨", 423: "🌨",
    425: "❄", 426: "🌨", 427: "🌨", 450: "⛈",
}


def code_to_emoji(code: int) -> str:
    """JMA 天気コードを絵文字に。出力は VS-16 付き (カラー絵文字を強制)。

    主要コード (1xx 晴 / 2xx 曇 / 3xx 雨 / 4xx 雪) を細分化して絵文字を選ぶ。
    未収録は先頭桁で粗くフォールバック。
    """
    base = _CODE_EMOJI.get(code)
    if base is None:
        bucket = code // 100
        base = {1: "☀", 2: "☁", 3: "🌧", 4: "❄"}.get(bucket, "❓")
    return base + _VS16


# 強度マーカー — セル背景色で強い予報を強調 (1セル内に収まる)。
# "warn" は黄色系 (注意)、"alert" は赤系 (警戒)。
_WARN_CODES = {306, 405}  # 大雨 / 大雪
_ALERT_CODES = {
    307, 308,             # 風雨強い / 雨で暴風
    406, 407,             # 風雪強い / 暴風雪
    140, 208, 219, 240, 250, 350, 450,  # 各種雷雨
}


def code_to_severity(code: int) -> str:
    """強度を返す: "alert" / "warn" / "normal"。"""
    if code in _ALERT_CODES:
        return "alert"
    if code in _WARN_CODES:
        return "warn"
    return "normal"


def severity_to_background(severity: str) -> str:
    """強度 → CSS 背景色 (空文字なら塗らない)。"""
    return {
        "alert": "rgba(220, 60, 60, 0.30)",
        "warn": "rgba(220, 180, 50, 0.30)",
        "normal": "",
    }.get(severity, "")


def parse_weekly_codes(data: object) -> list[int]:
    """JMA forecast JSON から週間 weatherCodes だけを抽出 (互換用)。"""
    return parse_weekly(data).codes


def parse_weekly(data: object) -> WeeklyForecast:
    """JMA forecast JSON から週間予報 (codes + temps) を抽出。

    JMA の週間予報は data[1]["timeSeries"] に格納される:
      - [0]: weatherCodes (7日分)
      - [1]: tempsMin / tempsMax (7日分、当日分は "" のことが多い)
    形式異常時は空 WeeklyForecast。
    """
    try:
        weekly = data[1]  # type: ignore[index]
        ts_codes = weekly["timeSeries"][0]
        codes = [
            int(c)
            for c in ts_codes["areas"][0]["weatherCodes"]
            if c is not None and str(c) != ""
        ]

        temps_min: list[str] = []
        temps_max: list[str] = []
        try:
            ts_temp = weekly["timeSeries"][1]
            area = ts_temp["areas"][0]
            temps_min = [str(t) for t in area.get("tempsMin", [])]
            temps_max = [str(t) for t in area.get("tempsMax", [])]
        except (KeyError, IndexError, TypeError):
            pass

        return WeeklyForecast(codes=codes, temps_max=temps_max, temps_min=temps_min)
    except (KeyError, IndexError, TypeError, ValueError):
        return WeeklyForecast()


def format_forecast(codes: Sequence[int]) -> str:
    """天気コード列を絵文字列に。"""
    return "".join(code_to_emoji(c) for c in codes)


def format_temp(t: str) -> str:
    """空文字や "-" は "-" に、それ以外はそのまま。"""
    s = str(t).strip()
    return s if s else "-"


def fetch_weekly_codes(area: str, timeout: float = 5.0) -> list[int]:
    """JMA から週間予報を取得して天気コードのリストを返す (互換用)。"""
    return fetch_weekly(area, timeout).codes


def fetch_weekly(area: str, timeout: float = 5.0) -> WeeklyForecast:
    """JMA から週間予報を取得して WeeklyForecast を返す。"""
    url = JMA_URL.format(area=area)
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        data = json.load(resp)
    return parse_weekly(data)


# ── Widget ─────────────────────────────────────────────────────────────────

# fetcher = エリアコード → WeeklyForecast を返す関数 (DI 用)
Fetcher = Callable[[str], WeeklyForecast]


class WeatherWidget(QWidget):
    """週間予報を 3行 × 7列 のグリッドで表示。1時間ごとに更新。

    1行目: 天気絵文字
    2行目: 最高気温
    3行目: 最低気温
    """

    updated = pyqtSignal(WeeklyForecast)

    def __init__(
        self,
        area: str | None = None,
        fetcher: Fetcher | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.area = area or load_config().area
        # 明示的に渡された fetcher を最優先。なければ dev モックを試し、
        # それも無ければ実 API。
        if fetcher is None:
            from ..dev import is_dev_mocks_enabled, mock_weather_fetcher
            fetcher = mock_weather_fetcher if is_dev_mocks_enabled() else fetch_weekly
        self._fetcher = fetcher

        # グリッドは固定幅。左に伸縮スペーサだけ置いて右寄せにする
        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 4)
        outer.addStretch(1)

        inner = QWidget(self)
        self._grid = QGridLayout(inner)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(6)
        self._grid.setVerticalSpacing(0)
        outer.addWidget(inner)

        # 7列分の QLabel を 3行で確保 (中央寄せ)
        # 最高=赤系 / 最低=青系
        self._emoji_labels: list[QLabel] = []
        self._max_labels: list[QLabel] = []
        self._min_labels: list[QLabel] = []
        for col in range(7):
            for row, store, style in (
                (0, self._emoji_labels, ""),
                (1, self._max_labels, "color: #d8453b;"),  # 最高
                (2, self._min_labels, "color: #2f7dd1;"),  # 最低
            ):
                lbl = QLabel("", inner)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                if style:
                    lbl.setStyleSheet(style)
                self._grid.addWidget(lbl, row, col)
                store.append(lbl)

        # 初期表示
        self._status = QLabel("…", inner)
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._grid.addWidget(self._status, 0, 0, 1, 7)

        self.updated.connect(self._apply)

        self._timer = QTimer(self)
        self._timer.setInterval(60 * 60 * 1000)  # 1h
        self._timer.timeout.connect(self._refresh)
        self._timer.start()
        self._refresh()

    def _refresh(self) -> None:
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self) -> None:
        try:
            fc = self._fetcher(self.area)
        except Exception:
            fc = WeeklyForecast()
        self.updated.emit(fc)

    def _apply(self, fc: WeeklyForecast) -> None:
        if not fc:
            self._status.setText("取得失敗")
            self._status.show()
            for lbl in self._emoji_labels + self._max_labels + self._min_labels:
                lbl.setText("")
                lbl.setStyleSheet(lbl.styleSheet().split("background")[0])  # bg 解除
            return
        self._status.hide()
        for i in range(7):
            code = fc.codes[i] if i < len(fc.codes) else 0
            self._emoji_labels[i].setText(code_to_emoji(code) if code else "")
            self._max_labels[i].setText(
                format_temp(fc.temps_max[i]) if i < len(fc.temps_max) else "-"
            )
            self._min_labels[i].setText(
                format_temp(fc.temps_min[i]) if i < len(fc.temps_min) else "-"
            )
            # 列 (3セル) の背景色を強度に応じて変える
            bg = severity_to_background(code_to_severity(code)) if code else ""
            bg_css = f"background: {bg};" if bg else ""
            self._emoji_labels[i].setStyleSheet(bg_css)
            self._max_labels[i].setStyleSheet(f"color: #d8453b; {bg_css}")
            self._min_labels[i].setStyleSheet(f"color: #2f7dd1; {bg_css}")
