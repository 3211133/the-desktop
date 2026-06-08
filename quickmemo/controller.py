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
    HIDE_SELF = auto()  # 戻り先が無い/失敗時のフォールバック


@dataclass
class DecideResult:
    action: ToggleAction
    target_hwnd: int  # ACTIVATE_SELF→自分のHWND, RETURN_TO_PREV→prev_hwnd, NOOP/HIDE_SELF→0
    ok: bool = True   # RETURN_TO_PREV の restore 成否


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

    def note_foreground_change(self, old_fg: int, new_fg: int) -> None:
        """フォアグラウンド変化の通知。

        QM が新たに前面になり、かつ前のフォアグラウンドが他アプリだったなら
        それを「戻り先」として記録する。CapsLock 以外 (マウス・タスクバー等)
        で QM に来た場合でも戻れるようにする。
        """
        my = self._get_my_hwnd()
        if new_fg == my and old_fg and old_fg != my:
            self._prev_hwnd = old_fg

    def decide(self) -> DecideResult:
        """次にとるアクションを決定する (副作用なし)。"""
        if self._is_self_active():
            if self._prev_hwnd:
                return DecideResult(ToggleAction.RETURN_TO_PREV, self._prev_hwnd)
            # 戻り先がない場合は HIDE_SELF (OS が次の z-order を前面化する)
            return DecideResult(ToggleAction.HIDE_SELF, 0)

        my = self._get_my_hwnd()
        return DecideResult(ToggleAction.ACTIVATE_SELF, my)

    def on_hotkey(self) -> DecideResult:
        """CapsLock 押下時に呼ぶ。decide → 副作用 (focus 操作 + prev_hwnd 更新)。

        RETURN_TO_PREV で restore に失敗したら HIDE_SELF に格下げする
        (戻り先が閉じられた等)。
        """
        result = self.decide()
        if result.action is ToggleAction.ACTIVATE_SELF:
            fg = self._focus.get_foreground()
            my = result.target_hwnd
            if fg and fg != my:
                self._prev_hwnd = fg
            self._focus.restore(my)
        elif result.action is ToggleAction.RETURN_TO_PREV:
            ok = self._focus.restore(result.target_hwnd)
            self._prev_hwnd = 0
            if not ok:
                # restore 失敗 → HIDE_SELF に格下げ
                return DecideResult(ToggleAction.HIDE_SELF, 0, ok=False)
            result.ok = True
        # HIDE_SELF は副作用なし (window 側で hide する)
        return result

    def return_to_prev(self) -> bool:
        """Esc 等から: 明示的に戻る。戻り先がなければ False。"""
        if not self._prev_hwnd:
            return False
        ok = self._focus.restore(self._prev_hwnd)
        self._prev_hwnd = 0
        return ok
