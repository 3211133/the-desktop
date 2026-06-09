"""開発・UI 確認用のモック群。

`QUICKMEMO_DEV_MOCKS=1` で起動すると、各機能 widget が自前のフェッチャーを
持たない場合にこのモジュールのモックフェッチャーへフォールバックする。

UI 状態 (強度マーカー / 取得失敗表示 等) を実 API なしで再現するのに使う。
"""

from __future__ import annotations

import os

from .features.weather import WeeklyForecast


def is_dev_mocks_enabled() -> bool:
    return os.environ.get("QUICKMEMO_DEV_MOCKS") not in (None, "", "0")


def mock_weather_fetcher(area: str) -> WeeklyForecast:
    """強度バリエーションを含む固定の週間予報。

    日ごと: 晴 / 曇一時雨 / 大雨 / 雷雨 / 雪 / 暴風雪 / 雨で雷
    背景色のテスト (normal / warn / alert) が全部出る。
    """
    return WeeklyForecast(
        codes=[100, 202, 306, 208, 400, 407, 350],
        temps_max=["28", "26", "24", "29", "5", "0", "22"],
        temps_min=["18", "16", "14", "19", "-2", "-10", "12"],
    )
