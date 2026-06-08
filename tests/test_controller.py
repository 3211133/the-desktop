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


def test_active_press_without_prev_is_noop():
    ctrl, focus = make_ctrl(fg=0, my=1000, active=True)
    r = ctrl.on_hotkey()
    assert r.action is ToggleAction.NOOP
    assert focus.restore_calls == []


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
