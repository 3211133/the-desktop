"""トグル状態機械 — pure (Qt/Win32 非依存)。

CapsLock 押下時の判断 (前面化するか戻るか) と prev_hwnd の管理だけを行う。
実際のフォーカス操作は Focus 経由、自分が前面かは外部 callable で受け取る。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

from .protocols import Focus


class ToggleAction(Enum):
    NOOP = auto()
    ACTIVATE_SELF = auto()
    RETURN_TO_PREV = auto()


@dataclass
class DecideResult:
    action: ToggleAction
    target_hwnd: int  # ACTIVATE_SELF→自分のHWND, RETURN_TO_PREV→prev_hwnd, NOOP→0


class ToggleController:
    """トグルの判断と副作用の実行を担う。状態は prev_hwnd のみ。"""

    def __init__(
        self,
        focus: Focus,
        get_my_hwnd: Callable[[], int],
        is_self_active: Callable[[], bool],
    ) -> None:
        self._focus = focus
        self._get_my_hwnd = get_my_hwnd
        self._is_self_active = is_self_active
        self._prev_hwnd: int = 0

    @property
    def prev_hwnd(self) -> int:
        return self._prev_hwnd

    def decide(self) -> DecideResult:
        """次にとるアクションを決定する (副作用なし)。"""
        if self._is_self_active():
            if self._prev_hwnd:
                return DecideResult(ToggleAction.RETURN_TO_PREV, self._prev_hwnd)
            return DecideResult(ToggleAction.NOOP, 0)

        my = self._get_my_hwnd()
        return DecideResult(ToggleAction.ACTIVATE_SELF, my)

    def on_hotkey(self) -> DecideResult:
        """CapsLock 押下時に呼ぶ。decide → 副作用 (focus 操作 + prev_hwnd 更新)。"""
        result = self.decide()
        if result.action is ToggleAction.ACTIVATE_SELF:
            fg = self._focus.get_foreground()
            my = result.target_hwnd
            if fg and fg != my:
                self._prev_hwnd = fg
            self._focus.restore(my)
        elif result.action is ToggleAction.RETURN_TO_PREV:
            self._focus.restore(result.target_hwnd)
            self._prev_hwnd = 0
        return result

    def return_to_prev(self) -> bool:
        """Esc 等から: 明示的に戻る。戻り先がなければ False。"""
        if not self._prev_hwnd:
            return False
        ok = self._focus.restore(self._prev_hwnd)
        self._prev_hwnd = 0
        return ok
