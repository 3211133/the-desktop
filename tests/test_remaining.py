"""remaining_to / format_remaining の単体テスト — pure (Qt 非依存)。"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from quickmemo.features.remaining import (
    DEFAULT_TARGET,
    format_remaining,
    remaining_to,
)


def test_default_target_is_18():
    assert DEFAULT_TARGET == time(18, 0)


def test_remaining_before_target_is_positive():
    now = datetime(2026, 6, 9, 10, 0, 0)
    td = remaining_to(now)
    assert td == timedelta(hours=8)


def test_remaining_after_target_is_negative():
    now = datetime(2026, 6, 9, 20, 30, 0)
    td = remaining_to(now)
    assert td == timedelta(hours=-2, minutes=-30)


def test_remaining_at_target_is_zero():
    now = datetime(2026, 6, 9, 18, 0, 0)
    assert remaining_to(now) == timedelta(0)


def test_remaining_custom_target():
    now = datetime(2026, 6, 9, 10, 0, 0)
    td = remaining_to(now, target=time(12, 30))
    assert td == timedelta(hours=2, minutes=30)


def test_format_remaining_typical():
    assert format_remaining(timedelta(hours=4, minutes=32, seconds=15)) == "18:00まで04:32:15"


def test_format_remaining_zero_padded():
    assert format_remaining(timedelta(hours=1, minutes=5, seconds=3)) == "18:00まで01:05:03"


def test_format_remaining_negative_prefix():
    assert format_remaining(timedelta(hours=-1, minutes=-15, seconds=-30)) == "18:00まで-01:15:30"


def test_format_remaining_zero():
    assert format_remaining(timedelta(0)) == "18:00まで00:00:00"


def test_format_remaining_custom_target():
    assert format_remaining(timedelta(hours=2, minutes=30), target=time(12, 30)) == "12:30まで02:30:00"


# ── 「日付が変わるまで - 表記」の仕様テスト ────────────────────────────────

def test_overtime_continues_negative_until_midnight():
    """18:00 後、同日中はずっと負の値で増え続ける。"""
    just_past = datetime(2026, 6, 9, 18, 0, 30)
    assert remaining_to(just_past) == timedelta(seconds=-30)

    late = datetime(2026, 6, 9, 23, 59, 30)
    assert remaining_to(late) == timedelta(hours=-5, minutes=-59, seconds=-30)


def test_after_midnight_resets_to_next_target():
    """日付が変わったら新しい日の 18:00 までの正値に戻る。"""
    after_midnight = datetime(2026, 6, 10, 0, 0, 30)
    td = remaining_to(after_midnight)
    assert td.total_seconds() > 0
    assert td == timedelta(hours=17, minutes=59, seconds=30)


def test_format_late_evening_shows_minus():
    late = datetime(2026, 6, 9, 22, 30, 0)
    td = remaining_to(late)
    assert format_remaining(td) == "18:00まで-04:30:00"
