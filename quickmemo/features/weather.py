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
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ..paths import config_path

DEFAULT_AREA = "130000"  # 東京
CONFIG_FILE = config_path("weather")
JMA_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{area}.json"


@dataclass
class WeatherConfig:
    area: str = DEFAULT_AREA


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


def code_to_emoji(code: int) -> str:
    """JMA 天気コードを絵文字に。先頭桁: 1=晴 2=曇 3=雨 4=雪。"""
    bucket = code // 100
    return {1: "☀", 2: "☁", 3: "☔", 4: "❄"}.get(bucket, "❓")


def parse_weekly_codes(data: object) -> list[int]:
    """JMA forecast JSON から週間 weatherCodes を抽出。

    形式異常時は空リスト。
    """
    try:
        weekly = data[1]  # type: ignore[index]
        ts = weekly["timeSeries"][0]
        area = ts["areas"][0]
        return [int(c) for c in area["weatherCodes"] if c is not None and str(c) != ""]
    except (KeyError, IndexError, TypeError, ValueError):
        return []


def format_forecast(codes: Sequence[int]) -> str:
    """天気コード列を絵文字列に。"""
    return "".join(code_to_emoji(c) for c in codes)


def fetch_weekly_codes(area: str, timeout: float = 5.0) -> list[int]:
    """JMA から週間予報を取得して天気コードのリストを返す。"""
    url = JMA_URL.format(area=area)
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        data = json.load(resp)
    return parse_weekly_codes(data)


# ── Widget ─────────────────────────────────────────────────────────────────

# fetcher = エリアコード → 天気コード列 を返す関数 (DI 用)
Fetcher = Callable[[str], list[int]]


class WeatherWidget(QWidget):
    """週間予報を絵文字で1行表示。1時間ごとに更新。"""

    updated = pyqtSignal(str)

    def __init__(
        self,
        area: str | None = None,
        fetcher: Fetcher | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.area = area or load_config().area
        self._fetcher = fetcher or fetch_weekly_codes

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        self.label = QLabel("…", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        self.updated.connect(self.label.setText)

        self._timer = QTimer(self)
        self._timer.setInterval(60 * 60 * 1000)  # 1h
        self._timer.timeout.connect(self._refresh)
        self._timer.start()
        self._refresh()

    def _refresh(self) -> None:
        # ネットワーク I/O は別スレッドで (Qt メインを止めない)
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self) -> None:
        try:
            codes = self._fetcher(self.area)
            text = format_forecast(codes) if codes else "取得失敗"
        except Exception:
            text = "取得失敗"
        self.updated.emit(text)
