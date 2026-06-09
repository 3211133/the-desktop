"""bootstrap モジュールのテスト。"""

from __future__ import annotations

import pytest

from the_desktop import bootstrap


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    """すべての CONFIG_FILE を tmp_path 配下に差し替える。"""
    from the_desktop import config as app_cfg
    from the_desktop.features import news as news_mod
    from the_desktop.features import remaining as rem_mod
    from the_desktop.features import weather as weather_mod

    cfg_dir = tmp_path / "config"
    monkeypatch.setattr(app_cfg, "CONFIG_FILE", cfg_dir / "app.json")
    monkeypatch.setattr(news_mod, "CONFIG_FILE", cfg_dir / "news.json")
    monkeypatch.setattr(rem_mod, "CONFIG_FILE", cfg_dir / "remaining.json")
    monkeypatch.setattr(weather_mod, "CONFIG_FILE", cfg_dir / "weather.json")
    return cfg_dir


def test_creates_all_missing_configs(isolated_paths):
    created = bootstrap.ensure_default_configs()
    names = sorted(p.name for p in created)
    assert names == ["app.json", "news.json", "remaining.json", "weather.json"]
    for p in created:
        assert p.exists()


def test_does_not_overwrite_existing(isolated_paths):
    isolated_paths.mkdir(parents=True, exist_ok=True)
    p = isolated_paths / "news.json"
    p.write_text('{"url": "https://custom.example.com", "limit": 5}', encoding="utf-8")
    created = bootstrap.ensure_default_configs()
    # news.json は既存なので作成リストに含まれない
    assert p not in created
    # 既存内容は保たれる
    assert "custom.example.com" in p.read_text(encoding="utf-8")


def test_idempotent(isolated_paths):
    bootstrap.ensure_default_configs()
    second = bootstrap.ensure_default_configs()
    assert second == []  # 2回目は何も作らない


def test_loadable_after_bootstrap(isolated_paths):
    """生成された設定が各 load_config で読み戻せる (型が壊れていない)。"""
    bootstrap.ensure_default_configs()

    from the_desktop import config as app_cfg
    from the_desktop.features import news as news_mod
    from the_desktop.features import remaining as rem_mod
    from the_desktop.features import weather as weather_mod

    assert app_cfg.load_config(app_cfg.CONFIG_FILE) == app_cfg.Config()
    assert news_mod.load_config(news_mod.CONFIG_FILE) == news_mod.NewsConfig()
    assert rem_mod.load_config(rem_mod.CONFIG_FILE) == rem_mod.RemainingConfig()
    assert weather_mod.load_config(weather_mod.CONFIG_FILE) == weather_mod.WeatherConfig()
