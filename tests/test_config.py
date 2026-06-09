"""config モジュールの単体テスト — pure。"""

from __future__ import annotations

from the_desktop.config import Config, WindowGeometry, load_config, save_config


def test_load_missing_returns_default(tmp_path):
    cfg = load_config(tmp_path / "nope.json")
    assert cfg == Config()


def test_load_broken_json_falls_back(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{not json", encoding="utf-8")
    assert load_config(p) == Config()


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "config.json"
    original = Config(window=WindowGeometry(x=10, y=20, w=300, h=400), topmost=False)
    save_config(original, p)
    assert load_config(p) == original


def test_save_creates_parent_dir(tmp_path):
    p = tmp_path / "a" / "b" / "config.json"
    save_config(Config(), p)
    assert p.exists()


def test_partial_json_fills_defaults(tmp_path):
    p = tmp_path / "config.json"
    p.write_text('{"topmost": false}', encoding="utf-8")
    cfg = load_config(p)
    assert cfg.topmost is False
    assert cfg.window == WindowGeometry()  # window 欠落時はデフォルト
