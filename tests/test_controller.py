"""ToggleController の単体テスト — Qt/Win32 非依存。"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from quickmemo.controller import ToggleAction, ToggleController


@dataclass
class FakeFocus:
    """Focus Protocol の偽実装。呼び出し履歴を記録する。"""
    fg_hwnd: int = 0
    restore_calls: list[int] = field(default_factory=list)
    restore_returns: bool = True

    def get_foreground(self) -> int:
        return self.fg_hwnd

    def restore(self, hwnd: int) -> bool:
        self.restore_calls.append(hwnd)
        return self.restore_returns


def make_ctrl(fg=0, my=1000, active=False):
    focus = FakeFocus(fg_hwnd=fg)
    ctrl = ToggleController(
        focus,
        get_my_hwnd=lambda: my,
        is_self_active=lambda: active,
    )
    return ctrl, focus


def test_inactive_press_activates_self_and_records_prev():
    ctrl, focus = make_ctrl(fg=42, my=1000, active=False)
    r = ctrl.on_hotkey()
    assert r.action is ToggleAction.ACTIVATE_SELF
    assert r.target_hwnd == 1000
    assert focus.restore_calls == [1000]
    assert ctrl.prev_hwnd == 42


def test_inactive_press_with_fg_equal_self_does_not_record_prev():
    ctrl, focus = make_ctrl(fg=1000, my=1000, active=False)
    ctrl.on_hotkey()
    assert ctrl.prev_hwnd == 0


def test_active_press_returns_to_prev():
    ctrl, focus = make_ctrl(fg=42, my=1000, active=False)
    ctrl.on_hotkey()  # ACTIVATE_SELF, prev=42

    ctrl._is_self_active = lambda: True
    r = ctrl.on_hotkey()
    assert r.action is ToggleAction.RETURN_TO_PREV
    assert r.target_hwnd == 42
    assert focus.restore_calls == [1000, 42]
    assert ctrl.prev_hwnd == 0


def test_active_press_without_prev_hides_self():
    """戻り先がないなら HIDE_SELF (OS が次の z-order を前面に)。"""
    ctrl, focus = make_ctrl(fg=0, my=1000, active=True)
    r = ctrl.on_hotkey()
    assert r.action is ToggleAction.HIDE_SELF
    assert focus.restore_calls == []  # focus 側は何もしない


def test_return_to_prev_failure_downgrades_to_hide():
    """戻り先が閉じられた等で restore 失敗 → HIDE_SELF にフォールバック。"""
    ctrl, focus = make_ctrl(fg=42, my=1000, active=False)
    ctrl.on_hotkey()  # ACTIVATE_SELF, prev=42
    ctrl._is_self_active = lambda: True
    focus.restore_returns = False  # 戻り先が無効になったと仮定
    r = ctrl.on_hotkey()
    assert r.action is ToggleAction.HIDE_SELF
    assert r.ok is False
    assert ctrl.prev_hwnd == 0  # クリアはする


def test_cycle_activate_return_activate():
    ctrl, focus = make_ctrl(fg=42, my=1000, active=False)
    ctrl.on_hotkey()  # ACTIVATE
    ctrl._is_self_active = lambda: True
    ctrl.on_hotkey()  # RETURN
    ctrl._is_self_active = lambda: False
    # 戻った後の前面が変わったと仮定
    focus.fg_hwnd = 99
    ctrl.on_hotkey()  # ACTIVATE again
    assert ctrl.prev_hwnd == 99
    assert focus.restore_calls == [1000, 42, 1000]


def test_return_to_prev_explicit_succeeds_when_prev_set():
    ctrl, focus = make_ctrl(fg=42, my=1000, active=False)
    ctrl.on_hotkey()
    assert ctrl.return_to_prev() is True
    assert focus.restore_calls == [1000, 42]
    assert ctrl.prev_hwnd == 0


def test_return_to_prev_explicit_fails_when_no_prev():
    ctrl, focus = make_ctrl(fg=0, my=1000, active=False)
    assert ctrl.return_to_prev() is False
    assert focus.restore_calls == []


def test_return_to_prev_propagates_focus_failure():
    ctrl, focus = make_ctrl(fg=42, my=1000, active=False)
    ctrl.on_hotkey()
    focus.restore_returns = False
    assert ctrl.return_to_prev() is False
    assert ctrl.prev_hwnd == 0  # 失敗してもクリアはする


# ── note_foreground_change (マウス等で QM に来ても戻れる経路) ────────────────

def test_note_fg_change_records_when_self_becomes_active():
    """他アプリ → QM のフォアグラウンド変化で prev_hwnd を記録する。"""
    ctrl, _ = make_ctrl(my=1000, active=True)
    ctrl.note_foreground_change(old_fg=42, new_fg=1000)
    assert ctrl.prev_hwnd == 42


def test_note_fg_change_ignored_when_target_not_self():
    ctrl, _ = make_ctrl(my=1000, active=False)
    ctrl.note_foreground_change(old_fg=42, new_fg=99)
    assert ctrl.prev_hwnd == 0


def test_note_fg_change_ignored_when_old_was_self():
    ctrl, _ = make_ctrl(my=1000, active=True)
    ctrl.note_foreground_change(old_fg=1000, new_fg=1000)
    assert ctrl.prev_hwnd == 0


def test_mouse_activation_then_capslock_returns():
    """マウスで QM に来た直後の CapsLock で戻れる (今回の修正点)。"""
    ctrl, focus = make_ctrl(my=1000, active=True)
    ctrl.note_foreground_change(old_fg=42, new_fg=1000)
    r = ctrl.on_hotkey()
    assert r.action is ToggleAction.RETURN_TO_PREV
    assert focus.restore_calls == [42]
