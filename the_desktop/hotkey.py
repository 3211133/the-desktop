"""CapsLock 抱殺グローバルフック (Win32, Qt 非依存)。

`__init__` では何もしない。`install()` を呼んで初めて
別スレッドで `WH_KEYBOARD_LL` を張る。これで構築だけならテストでも安全。
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import threading

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
_KEY_MSGS = (WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP)

VK_CAPITAL = 0x14
VK_DBE_ALPHANUMERIC = 0xF0  # 日本語キーボードの英数キー
_CAPS_VKS = {VK_CAPITAL, VK_DBE_ALPHANUMERIC}


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wt.DWORD),
        ("scanCode", wt.DWORD),
        ("flags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


_LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_int, wt.WPARAM, wt.LPARAM
)

_user32.SetWindowsHookExW.restype = wt.HHOOK
_user32.SetWindowsHookExW.argtypes = [ctypes.c_int, _LowLevelKeyboardProc, wt.HINSTANCE, wt.DWORD]
_user32.CallNextHookEx.restype = ctypes.c_long
_user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
_user32.UnhookWindowsHookEx.restype = wt.BOOL
_user32.UnhookWindowsHookEx.argtypes = [wt.HHOOK]
_user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]


class CapsLockHook:
    """Hotkey Protocol の Win32 実装。install() で初めてフックを張る。"""

    def __init__(self) -> None:
        self.pressed_event = threading.Event()
        self._hook_id: int | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._cb = None  # ctypes コールバック参照保持

    def install(self) -> None:
        if self._thread is not None:
            return  # 多重 install は no-op
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=2.0)

    def uninstall(self) -> None:
        if self._hook_id:
            _user32.UnhookWindowsHookEx(self._hook_id)
            self._hook_id = None

    def _run(self) -> None:
        def _proc(nCode, wParam, lParam):
            if nCode >= 0 and wParam in _KEY_MSGS:
                kb = ctypes.cast(lParam, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents
                if kb.vkCode in _CAPS_VKS:
                    if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        self.pressed_event.set()
                    return 1  # 抱殺: OS に CapsLock を渡さない
            return _user32.CallNextHookEx(None, nCode, wParam, lParam)

        self._cb = _LowLevelKeyboardProc(_proc)
        self._hook_id = _user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._cb, None, 0)
        self._ready.set()

        msg = wt.MSG()
        while True:
            ret = _user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret in (0, -1):
                break
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))
