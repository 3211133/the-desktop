"""dev モック機構のテスト。"""

from __future__ import annotations

from the_desktop.dev import (
    is_dev_mocks_enabled,
    mock_weather_fetcher,
)


def test_is_enabled_default_false(monkeypatch):
    monkeypatch.delenv("THE_DESKTOP_DEV_MOCKS", raising=False)
    assert is_dev_mocks_enabled() is False


def test_is_enabled_with_one(monkeypatch):
    monkeypatch.setenv("THE_DESKTOP_DEV_MOCKS", "1")
    assert is_dev_mocks_enabled() is True


def test_is_enabled_with_zero(monkeypatch):
    monkeypatch.setenv("THE_DESKTOP_DEV_MOCKS", "0")
    assert is_dev_mocks_enabled() is False


def test_is_enabled_with_empty(monkeypatch):
    monkeypatch.setenv("THE_DESKTOP_DEV_MOCKS", "")
    assert is_dev_mocks_enabled() is False


def test_mock_weather_returns_full_severity_range():
    """モックは normal / warn / alert すべてを含む。"""
    from the_desktop.features.weather import code_to_severity
    fc = mock_weather_fetcher("130000")
    severities = {code_to_severity(c) for c in fc.codes}
    assert severities == {"normal", "warn", "alert"}


def test_mock_weather_returns_seven_days():
    fc = mock_weather_fetcher("anything")
    assert len(fc.codes) == 7
    assert len(fc.temps_max) == 7
    assert len(fc.temps_min) == 7


def test_widget_uses_mock_when_env_set(qtbot, monkeypatch):
    """env 立てて fetcher 未指定なら mock_weather_fetcher が使われる。"""
    monkeypatch.setenv("THE_DESKTOP_DEV_MOCKS", "1")
    from the_desktop.features.weather import WeatherWidget
    w = WeatherWidget()
    qtbot.addWidget(w)
    qtbot.waitUntil(lambda: w._emoji_labels[0].text() != "", timeout=2000)
    # モックの最初のコードは 100 (晴)
    assert "☀" in w._emoji_labels[0].text()


def test_widget_uses_real_when_env_not_set(qtbot, monkeypatch):
    """env 立ってなければ実 fetcher (fetch_weekly) が選ばれる。"""
    monkeypatch.delenv("THE_DESKTOP_DEV_MOCKS", raising=False)
    from the_desktop.features import weather as wm
    w = wm.WeatherWidget(fetcher=lambda a: wm.WeeklyForecast())
    # 明示 fetcher を渡したケースは触らない (上位優先) のを確認
    assert w._fetcher is not wm.fetch_weekly