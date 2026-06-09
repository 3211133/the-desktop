"""paths モジュールの単体テスト。"""

from __future__ import annotations

from pathlib import Path

from quickmemo import paths


def test_repo_root_contains_quickmemo_package():
    """REPO_ROOT 直下に quickmemo/ パッケージがあるはず。"""
    assert (paths.REPO_ROOT / "quickmemo").is_dir()


def test_config_path_returns_under_config_dir():
    p = paths.config_path("app")
    assert p == paths.CONFIG_DIR / "app.json"
    assert p.suffix == ".json"


def test_data_path_returns_under_data_dir():
    p = paths.data_path("bunpo.jsonl")
    assert p == paths.DATA_DIR / "bunpo.jsonl"


def test_config_and_data_are_distinct():
    assert paths.CONFIG_DIR != paths.DATA_DIR


def test_data_path_preserves_extension():
    assert paths.data_path("foo.txt").suffix == ".txt"
    assert paths.data_path("a.b.c").name == "a.b.c"


def test_config_file_points_to_app_json():
    """config.py の CONFIG_FILE が新しい paths を経由している。"""
    from quickmemo.config import CONFIG_FILE
    assert CONFIG_FILE == paths.config_path("app")


def test_bunpo_default_path_points_to_data_dir():
    """bunpo.py の DEFAULT_PATH が新しい paths を経由している。"""
    from quickmemo.features.bunpo import DEFAULT_PATH
    assert DEFAULT_PATH == paths.data_path("bunpo.jsonl")
