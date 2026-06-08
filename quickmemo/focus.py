"""前面ウィンドウ操作の Win32 実装 (Focus Protocol)。

Windows は他プロセスからの SetForegroundWindow を通常拒否するため、
現在の前面ウィンドウのスレッドに AttachThreadInput してから呼ぶ。
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_user32.GetForegroundWindow.restype = wt.HWND
_user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
_user32.GetWindowThreadProcessId.restype = wt.DWORD
_user32.AttachThreadInput.argtypes = [wt.DWORD, wt.DWORD, wt.BOOL]
_user32.AttachThreadInput.restype = wt.BOOL
_user32.SetForegroundWindow.argtypes = [wt.HWND]
_user32.SetForegroundWindow.restype = wt.BOOL
_user32.BringWindowToTop.argtypes = [wt.HWND]
_user32.BringWindowToTop.restype = wt.BOOL
_user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
_user32.ShowWindow.restype = wt.BOOL
_user32.IsIconic.argtypes = [wt.HWND]
_user32.IsIconic.restype = wt.BOOL
_user32.AllowSetForegroundWindow.argtypes = [wt.DWORD]
_user32.AllowSetForegroundWindow.restype = wt.BOOL

SW_SHOW = 5
SW_RESTORE = 9
ASFW_ANY = 0xFFFFFFFF


class Win32Focus:
    """Focus Protocol の Win32 実装。"""

    def get_foreground(self) -> int:
        return int(_user32.GetForegroundWindow() or 0)

    def restore(self, hwnd: int) -> bool:
        if not hwnd:
            return False
        if not _user32.IsWindow(hwnd):
            return False

        if _user32.IsIconic(hwnd):
            _user32.ShowWindow(hwnd, SW_RESTORE)

        cur_thread = _kernel32.GetCurrentThreadId()
        fg_hwnd = _user32.GetForegroundWindow()
        fg_thread = (
            _user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
        )

        attached = False
        if fg_thread and fg_thread != cur_thread:
            attached = bool(_user32.AttachThreadInput(cur_thread, fg_thread, True))

        _user32.AllowSetForegroundWindow(ASFW_ANY)
        _user32.ShowWindow(hwnd, SW_SHOW)
        _user32.BringWindowToTop(hwnd)
        ok = bool(_user32.SetForegroundWindow(hwnd))

        if attached:
            _user32.AttachThreadInput(cur_thread, fg_thread, False)
        return ok


# 既存スモークテスト互換のための薄いラッパー (削除可)
def restore_foreground(hwnd: int) -> bool:
    return Win32Focus().restore(hwnd)


def get_foreground_hwnd() -> int:
    return Win32Focus().get_foreground()
