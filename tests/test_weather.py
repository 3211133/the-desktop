"""weather モジュールの単体テスト — pure (ネットワーク非依存)。"""

from __future__ import annotations

import pytest

from quickmemo.features.weather import (
    DEFAULT_AREA,
    WeatherConfig,
    WeeklyForecast,
    code_to_emoji,
    code_to_severity,
    format_forecast,
    format_temp,
    load_config,
    parse_weekly,
    parse_weekly_codes,
    save_config,
    severity_to_background,
)


# ── 絵文字マッピング ──────────────────────────────────────────────────────

VS16 = "️"


def test_code_to_emoji_pure_sun_and_cloud():
    assert code_to_emoji(100) == "☀" + VS16
    assert code_to_emoji(200) == "☁" + VS16


def test_code_to_emoji_sun_cloud_mix():
    assert code_to_emoji(101) == "⛅" + VS16
    assert code_to_emoji(111) == "⛅" + VS16
    assert code_to_emoji(201) == "⛅" + VS16
    assert code_to_emoji(211) == "⛅" + VS16


def test_code_to_emoji_sun_or_cloud_plus_rain():
    assert code_to_emoji(102) == "🌦" + VS16
    assert code_to_emoji(202) == "🌦" + VS16


def test_code_to_emoji_rain():
    assert code_to_emoji(300) == "🌧" + VS16
    assert code_to_emoji(214) == "🌧" + VS16


def test_code_to_emoji_snow_or_mixed():
    assert code_to_emoji(400) == "❄" + VS16
    assert code_to_emoji(204) == "🌨" + VS16
    assert code_to_emoji(303) == "🌨" + VS16


def test_code_to_emoji_thunder():
    assert code_to_emoji(208) == "⛈" + VS16
    assert code_to_emoji(350) == "⛈" + VS16


def test_code_to_emoji_fog():
    assert code_to_emoji(209) == "🌫" + VS16


def test_code_to_emoji_fallback_to_bucket():
    assert code_to_emoji(199) == "☀" + VS16
    assert code_to_emoji(299) == "☁" + VS16
    assert code_to_emoji(399) == "🌧" + VS16
    assert code_to_emoji(499) == "❄" + VS16


def test_code_to_emoji_unknown():
    assert code_to_emoji(999) == "❓" + VS16
    assert code_to_emoji(0) == "❓" + VS16


def test_code_to_emoji_always_ends_with_vs16():
    """全コード共通: 末尾は U+FE0F (カラー絵文字強制)。"""
    for c in [100, 200, 300, 400, 101, 202, 208, 999]:
        assert code_to_emoji(c).endswith(VS16)


# ── 強度マーカー ─────────────────────────────────────────────────────────

def test_severity_normal_for_typical_codes():
    for c in [100, 200, 300, 400, 101, 202]:
        assert code_to_severity(c) == "normal"


def test_severity_warn_for_heavy():
    assert code_to_severity(306) == "warn"  # 大雨
    assert code_to_severity(405) == "warn"  # 大雪


def test_severity_alert_for_storm_or_thunder():
    assert code_to_severity(307) == "alert"  # 風雨強い
    assert code_to_severity(308) == "alert"  # 雨で暴風
    assert code_to_severity(406) == "alert"
    assert code_to_severity(407) == "alert"
    assert code_to_severity(208) == "alert"  # 曇一時雷雨
    assert code_to_severity(350) == "alert"  # 雨で雷


def test_severity_to_background_normal_is_empty():
    assert severity_to_background("normal") == ""


def test_severity_to_background_warn_and_alert_nonempty():
    assert severity_to_background("warn")
    assert severity_to_background("alert")
    assert severity_to_background("warn") != severity_to_background("alert")


# ── parse_weekly_codes ─────────────────────────────────────────────────────

_SAMPLE_RESPONSE = [
    {  # 短期予報 (今回は使わない)
        "publishingOffice": "気象庁",
        "timeSeries": [{"timeDefines": [], "areas": [{"weatherCodes": ["100"]}]}],
    },
    {  # 週間予報
        "publishingOffice": "気象庁",
        "timeSeries": [
            {
                "timeDefines": ["2026-06-09", "2026-06-10", "2026-06-11"],
                "areas": [
                    {
                        "area": {"name": "東京", "code": "130010"},
                        "weatherCodes": ["100", "200", "300", "100", "211", "400", "101"],
                    }
                ],
            },
            {
                "timeDefines": ["2026-06-09", "2026-06-10", "2026-06-11"],
                "areas": [
                    {
                        "area": {"name": "東京", "code": "44132"},
                        "tempsMin": ["", "17", "16", "18", "19", "12", "20"],
                        "tempsMax": ["", "27", "26", "28", "29", "22", "30"],
                    }
                ],
            },
        ],
    },
]


def test_parse_weekly_codes_extracts_seven():
    codes = parse_weekly_codes(_SAMPLE_RESPONSE)
    assert codes == [100, 200, 300, 100, 211, 400, 101]


def test_parse_weekly_codes_skips_empty_strings():
    response = [{}, {"timeSeries": [{"areas": [{"weatherCodes": ["100", "", "200", None]}]}]}]
    assert parse_weekly_codes(response) == [100, 200]


def test_parse_weekly_codes_empty_on_malformed():
    assert parse_weekly_codes({}) == []
    assert parse_weekly_codes([]) == []
    assert parse_weekly_codes([{"x": 1}, {"y": 2}]) == []
    assert parse_weekly_codes(None) == []


# ── parse_weekly: codes + temps を一緒に ──────────────────────────────────

def test_parse_weekly_extracts_codes_and_temps():
    fc = parse_weekly(_SAMPLE_RESPONSE)
    assert fc.codes == [100, 200, 300, 100, 211, 400, 101]
    assert fc.temps_max == ["", "27", "26", "28", "29", "22", "30"]
    assert fc.temps_min == ["", "17", "16", "18", "19", "12", "20"]


def test_parse_weekly_missing_temps_still_returns_codes():
    response = [
        {},
        {
            "timeSeries": [
                {"areas": [{"weatherCodes": ["100", "200"]}]},
                # timeSeries[1] が無い
            ]
        },
    ]
    fc = parse_weekly(response)
    assert fc.codes == [100, 200]
    assert fc.temps_max == []
    assert fc.temps_min == []


def test_parse_weekly_empty_on_malformed():
    assert not parse_weekly({})
    assert not parse_weekly([])
    assert not parse_weekly(None)


# ── format_temp ────────────────────────────────────────────────────────────

def test_format_temp_passthrough():
    assert format_temp("25") == "25"


def test_format_temp_empty_becomes_dash():
    assert format_temp("") == "-"
    assert format_temp("   ") == "-"


# ── format_forecast ────────────────────────────────────────────────────────

def test_format_forecast_seven_emojis():
    s = format_forecast([100, 200, 300, 100, 211, 400, 101])
    # 100=☀ 200=☁ 300=🌧 100=☀ 211=⛅ 400=❄ 101=⛅ (各々 +VS16)
    expected = "".join(e + VS16 for e in "☀☁🌧☀⛅❄⛅")
    assert s == expected


def test_format_forecast_empty():
    assert format_forecast([]) == ""


# ── 設定ファイル ──────────────────────────────────────────────────────────

def test_default_area_is_tokyo():
    assert DEFAULT_AREA == "130000"


def test_load_missing_returns_default(tmp_path):
    assert load_config(tmp_path / "nope.json") == WeatherConfig()


def test_load_broken_falls_back(tmp_path):
    p = tmp_path / "weather.json"
    p.write_text("{garbage", encoding="utf-8")
    assert load_config(p) == WeatherConfig()


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "weather.json"
    save_config(WeatherConfig(area="270000"), p)
    assert load_config(p).area == "270000"


def test_save_creates_parent_dir(tmp_path):
    p = tmp_path / "a" / "b" / "weather.json"
    save_config(WeatherConfig(), p)
    assert p.exists()


# ── Widget スモーク (network 非依存、fetcher を DI) ────────────────────────

def test_widget_uses_injected_fetcher(qtbot):
    """fetcher を差し込めば実 HTTP なしで動く。3行 × 7列に値が入る。"""
    from quickmemo.features.weather import WeatherWidget
    captured = []

    def fake_fetcher(area):
        captured.append(area)
        return WeeklyForecast(
            codes=[100, 200, 300, 100, 211, 400, 101],
            temps_max=["", "27", "26", "28", "29", "22", "30"],
            temps_min=["", "17", "16", "18", "19", "12", "20"],
        )

    w = WeatherWidget(area="270000", fetcher=fake_fetcher)
    qtbot.addWidget(w)
    qtbot.waitUntil(lambda: w._emoji_labels[0].text() != "", timeout=2000)

    emojis = "".join(lbl.text() for lbl in w._emoji_labels)
    expected = "".join(e + VS16 for e in "☀☁🌧☀⛅❄⛅")
    assert emojis == expected
    assert w._max_labels[1].text() == "27"
    assert w._min_labels[1].text() == "17"
    assert w._max_labels[0].text() == "-"  # 当日分は空 → "-"
    assert captured == ["270000"]


def test_widget_handles_fetcher_failure(qtbot):
    from quickmemo.features.weather import WeatherWidget

    def boom(area):
        raise RuntimeError("network down")

    w = WeatherWidget(area="130000", fetcher=boom)
    qtbot.addWidget(w)
    qtbot.waitUntil(lambda: w._status.text() == "取得失敗", timeout=2000)
