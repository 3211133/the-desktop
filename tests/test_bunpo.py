"""BunpoStore の単体テスト — pure (Qt 非依存)。"""

from __future__ import annotations

from datetime import datetime

import pytest

from quickmemo.features.bunpo import BunpoStore, Entry, format_entry


def test_load_missing_returns_empty(tmp_path):
    store = BunpoStore(tmp_path / "nope.jsonl")
    assert store.load() == []


def test_append_then_load_roundtrip(tmp_path):
    store = BunpoStore(tmp_path / "b.jsonl")
    e1 = store.append("hello", now=datetime(2026, 6, 9, 10, 0, 0))
    e2 = store.append("world", now=datetime(2026, 6, 9, 10, 5, 0))
    assert store.load() == [e1, e2]


def test_append_strips_and_rejects_empty(tmp_path):
    store = BunpoStore(tmp_path / "b.jsonl")
    e = store.append("   spaced   ", now=datetime(2026, 6, 9, 10, 0, 0))
    assert e.text == "spaced"
    with pytest.raises(ValueError):
        store.append("   ")
    with pytest.raises(ValueError):
        store.append("")


def test_append_creates_parent_dir(tmp_path):
    p = tmp_path / "a" / "b" / "bunpo.jsonl"
    store = BunpoStore(p)
    store.append("hi", now=datetime(2026, 6, 9, 10, 0, 0))
    assert p.exists()


def test_load_skips_corrupted_lines(tmp_path):
    p = tmp_path / "b.jsonl"
    p.write_text(
        '{"ts":"2026-06-09T10:00:00","text":"ok"}\n'
        'broken line\n'
        '{"ts":"2026-06-09T11:00:00","text":"also ok"}\n',
        encoding="utf-8",
    )
    entries = BunpoStore(p).load()
    assert len(entries) == 2
    assert entries[0].text == "ok"
    assert entries[1].text == "also ok"


def test_format_entry_uses_short_datetime():
    e = Entry(ts="2026-06-09T10:30:00", text="昼休み")
    assert format_entry(e) == "06/09 10:30  昼休み"


def test_format_entry_fallback_on_invalid_ts():
    e = Entry(ts="not-a-date", text="x")
    assert format_entry(e) == "not-a-date  x"


# ── Widget レベルの submit キー仕様 ──────────────────────────────────────────

def test_submitline_plain_enter_does_not_submit(qtbot):
    from PyQt6.QtCore import Qt
    from quickmemo.features.bunpo import _SubmitLine
    line = _SubmitLine()
    qtbot.addWidget(line)
    received = []
    line.submit.connect(lambda: received.append(True))
    qtbot.keyPress(line, Qt.Key.Key_Return)
    assert received == []  # 素の Enter は無視 (IME 確定との衝突回避)


def test_submitline_ctrl_enter_emits_submit(qtbot):
    from PyQt6.QtCore import Qt
    from quickmemo.features.bunpo import _SubmitLine
    line = _SubmitLine()
    qtbot.addWidget(line)
    received = []
    line.submit.connect(lambda: received.append(True))
    qtbot.keyPress(line, Qt.Key.Key_Return, modifier=Qt.KeyboardModifier.ControlModifier)
    assert received == [True]
