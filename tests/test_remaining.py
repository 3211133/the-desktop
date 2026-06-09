"""remaining モジュールの単体テスト — pure (Qt 非依存)。"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from quickmemo.features.remaining import (
    DEFAULT_TARGET,
    RemainingConfig,
    format_remaining,
    load_config,
    next_occurrence,
    remaining_to,
    save_config,
)


# ── 設計上のデフォルト ─────────────────────────────────────────────────────

def test_default_target_is_09():
    assert DEFAULT_TARGET == time(9, 0)


# ── next_occurrence: 次に来る target ───────────────────────────────────────

def test_next_occurrence_today_if_not_yet_passed():
    """今日の target がまだ来ていなければ今日の target。"""
    now = datetime(2026, 6, 9, 6, 0, 0)
    assert next_occurrence(now) == datetime(2026, 6, 9, 9, 0, 0)


def test_next_occurrence_tomorrow_if_already_passed():
    """今日の target を過ぎていれば翌日の target。"""
    now = datetime(2026, 6, 9, 10, 0, 0)
    assert next_occurrence(now) == datetime(2026, 6, 10, 9, 0, 0)


def test_next_occurrence_at_target_advances_to_tomorrow():
    """target ちょうどは「過ぎた」扱い → 翌日に進む。"""
    now = datetime(2026, 6, 9, 9, 0, 0)
    assert next_occurrence(now) == datetime(2026, 6, 10, 9, 0, 0)


def test_next_occurrence_custom_target():
    now = datetime(2026, 6, 9, 13, 0, 0)
    assert next_occurrence(now, target=time(18, 0)) == datetime(2026, 6, 9, 18, 0, 0)


# ── remaining_to: 常に正 ───────────────────────────────────────────────────

def test_remaining_morning_before_9():
    now = datetime(2026, 6, 9, 8, 0, 0)
    assert remaining_to(now) == timedelta(hours=1)


def test_remaining_evening_wraps_to_tomorrow():
    """夕方 → 翌朝までの長い残り。"""
    now = datetime(2026, 6, 9, 22, 0, 0)
    assert remaining_to(now) == timedelta(hours=11)


def test_remaining_just_past_midnight_short_to_morning():
    now = datetime(2026, 6, 10, 0, 30, 0)
    assert remaining_to(now) == timedelta(hours=8, minutes=30)


def test_remaining_always_positive():
    """どの時刻でも remaining_to は正。"""
    for h in range(0, 24):
        now = datetime(2026, 6, 9, h, 30, 0)
        assert remaining_to(now).total_seconds() > 0


# ── format_remaining ───────────────────────────────────────────────────────

def test_format_remaining_typical():
    assert format_remaining(timedelta(hours=4, minutes=32, seconds=15)) == "09:00まで04:32:15"


def test_format_remaining_zero_padded():
    assert format_remaining(timedelta(hours=1, minutes=5, seconds=3)) == "09:00まで01:05:03"


def test_format_remaining_custom_target():
    assert format_remaining(timedelta(hours=2, minutes=30), target=time(18, 0)) == "18:00まで02:30:00"


def test_format_remaining_negative_clamped_to_zero():
    """常に正前提だが、念のため負を渡しても 00:00:00 にクランプ。"""
    assert format_remaining(timedelta(seconds=-30)) == "09:00まで00:00:00"


# ── 設定ファイルの読み書き ────────────────────────────────────────────────

def test_load_missing_returns_default(tmp_path):
    assert load_config(tmp_path / "nope.json") == RemainingConfig()


def test_load_broken_json_falls_back(tmp_path):
    p = tmp_path / "remaining.json"
    p.write_text("{not json", encoding="utf-8")
    assert load_config(p) == RemainingConfig()


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "remaining.json"
    save_config(RemainingConfig(target=time(7, 30)), p)
    loaded = load_config(p)
    assert loaded.target == time(7, 30)


def test_save_creates_parent_dir(tmp_path):
    p = tmp_path / "a" / "b" / "remaining.json"
    save_config(RemainingConfig(), p)
    assert p.exists()


def test_load_accepts_string_format(tmp_path):
    p = tmp_path / "remaining.json"
    p.write_text('{"target": "12:34"}', encoding="utf-8")
    assert load_config(p).target == time(12, 34)
