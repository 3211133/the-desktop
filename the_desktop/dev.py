"""開発・UI 確認用のモック群。

`THE_DESKTOP_DEV_MOCKS=1` で起動すると、各機能 widget が自前のフェッチャーを
持たない場合にこのモジュールのモックフェッチャーへフォールバックする。

UI 状態 (強度マーカー / 取得失敗表示 等) を実 API なしで再現するのに使う。
"""

from __future__ import annotations

import os

from .features.news import NewsFeed, NewsItem
from .features.weather import WeeklyForecast


def is_dev_mocks_enabled() -> bool:
    return os.environ.get("THE_DESKTOP_DEV_MOCKS") not in (None, "", "0")


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


def mock_news_fetcher(url: str, limit: int) -> NewsFeed:
    """固定のニュース見出し + サマリ。"""
    sample = [
        NewsItem("関東地方で記録的な大雨", "https://example.com/1",
                 "Tue, 09 Jun 2026 10:30:00 +0900",
                 "前線の影響で関東甲信地方は午前中に記録的な雨量を観測。河川の氾濫や土砂災害に警戒。"),
        NewsItem("半導体大手、設備投資を拡大", "https://example.com/2",
                 "Tue, 09 Jun 2026 10:15:00 +0900",
                 "国内の半導体メーカー3社が来年度の設備投資額を平均15%増やすと発表。"),
        NewsItem("プロ野球: 巨人が逆転勝ち", "https://example.com/3",
                 "Tue, 09 Jun 2026 09:55:00 +0900",
                 "9回裏に2点を奪い、3対2の逆転勝ち。"),
        NewsItem("円相場、一時 130 円台に", "https://example.com/4",
                 "Tue, 09 Jun 2026 09:40:00 +0900",
                 "東京外国為替市場で円相場が一時 130 円台前半まで上昇。"),
        NewsItem("新型ロケット打ち上げ成功", "https://example.com/5",
                 "Tue, 09 Jun 2026 09:20:00 +0900",
                 "国産新型ロケットの初打ち上げが成功、搭載衛星も予定の軌道に投入。"),
        NewsItem("AI 関連法案、衆院通過へ", "https://example.com/6",
                 "Tue, 09 Jun 2026 09:00:00 +0900",
                 "AI 利用の規律を定める法案が今週中にも衆議院本会議で可決の見通し。"),
        NewsItem("自治体、AI で介護支援を強化", "https://example.com/7",
                 "Tue, 09 Jun 2026 08:45:00 +0900",
                 "複数自治体が AI を使った介護プラン作成の試行を開始。"),
        NewsItem("国内消費者物価、3か月連続上昇", "https://example.com/8",
                 "Tue, 09 Jun 2026 08:30:00 +0900",
                 "5月の消費者物価指数は前年同月比 2.4% 上昇、3か月連続のプラス。"),
        NewsItem("マラソン日本記録、また更新", "https://example.com/9",
                 "Tue, 09 Jun 2026 08:10:00 +0900",
                 "国内大会で日本記録が更新、男子は 2時間 4分台。"),
        NewsItem("台風1号、来週にも本州接近か", "https://example.com/10",
                 "Tue, 09 Jun 2026 07:55:00 +0900",
                 "南海上で発生した台風1号が、来週前半にも本州の南海上に接近する可能性。"),
    ]
    return NewsFeed(items=sample[:limit])
