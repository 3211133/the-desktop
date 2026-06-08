"""Focus / Hotkey の Protocol 定義 — pure (Qt/Win32 非依存)。

これらの Protocol に対してテストでは Fake 実装を差し込み、
実行時には Win32 実装を差し込む。
"""

from __future__ import annotations

import threading
from typing import Protocol, runtime_checkable


@runtime_checkable
class Focus(Protocol):
    """前面ウィンドウの取得と遷移を担う抽象。"""

    def get_foreground(self) -> int:
        """現在最前面の HWND を返す (取得不能なら 0)。"""
        ...

    def restore(self, hwnd: int) -> bool:
        """指定 HWND を前面化する。失敗時 False。hwnd=0 も False。"""
        ...


@runtime_checkable
class Hotkey(Protocol):
    """グローバルホットキーの抽象。`pressed_event` が立てば押下されたとみなす。"""

    pressed_event: threading.Event

    def install(self) -> None:
        """フックを張る (副作用)。多重 install は安全に no-op。"""
        ...

    def uninstall(self) -> None:
        """フックを外す。多重 uninstall は安全に no-op。"""
        ...
