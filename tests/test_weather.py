"""weather モジュールの単体テスト — pure (ネットワーク非依存)。"""

from __future__ import annotations

import pytest

from quickmemo.features.weather import (
    DEFAULT_AREA,
    WeatherConfig,
    code_to_emoji,
    format_forecast,
    load_config,
    parse_weekly_codes,
    save_config,
)


# ── 絵文字マッピング ──────────────────────────────────────────────────────

def test_code_to_emoji_sun():
    assert code_to_emoji(100) == "☀"
    assert code_to_emoji(111) == "☀"


def test_code_to_emoji_cloud():
    assert code_to_emoji(200) == "☁"
    assert code_to_emoji(211) == "☁"


def test_code_to_emoji_rain():
    assert code_to_emoji(300) == "☔"
    assert code_to_emoji(314) == "☔"


def test_code_to_emoji_snow():
    assert code_to_emoji(400) == "❄"


def test_code_to_emoji_unknown():
    assert code_to_emoji(999) == "❓"
    assert code_to_emoji(0) == "❓"


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
            }
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


# ── format_forecast ────────────────────────────────────────────────────────

def test_format_forecast_seven_emojis():
    s = format_forecast([100, 200, 300, 100, 211, 400, 101])
    assert s == "☀☁☔☀☁❄☀"
    assert len(s) == 7


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
    """fetcher を差し込めば実 HTTP なしで動く。"""
    from quickmemo.features.weather import WeatherWidget
    captured = []

    def fake_fetcher(area):
        captured.append(area)
        return [100, 200, 300, 100, 211, 400, 101]

    w = WeatherWidget(area="270000", fetcher=fake_fetcher)
    qtbot.addWidget(w)
    qtbot.waitUntil(lambda: w.label.text() not in ("…", ""), timeout=2000)
    assert w.label.text() == "☀☁☔☀☁❄☀"
    assert captured == ["270000"]


def test_widget_handles_fetcher_failure(qtbot):
    from quickmemo.features.weather import WeatherWidget

    def boom(area):
        raise RuntimeError("network down")

    w = WeatherWidget(area="130000", fetcher=boom)
    qtbot.addWidget(w)
    qtbot.waitUntil(lambda: w.label.text() == "取得失敗", timeout=2000)
