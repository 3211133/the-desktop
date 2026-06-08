"""QuickMemo エントリポイント — 配線のみ。

依存:
  Win32Focus       (focus.py)     ─┐
  CapsLockHook     (hotkey.py)    ─┼─→ ToggleController ─→ MainWindow
  Config           (config.py)    ─┘
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from .config import load_config
from .controller import ToggleController
from .focus import Win32Focus
from .hotkey import CapsLockHook
from .window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("QuickMemo")
    app.setQuitOnLastWindowClosed(False)

    cfg = load_config()
    focus = Win32Focus()
    hook = CapsLockHook()
    window = MainWindow(cfg)

    controller = ToggleController(
        focus=focus,
        get_my_hwnd=lambda: int(window.winId()),
        is_self_active=window.isActiveWindow,
    )
    window.set_controller(controller)

    hook.install()

    timer = QTimer()
    timer.setInterval(40)  # Windows hook timeout 余裕
    last_fg = [0]

    def _tick() -> None:
        # フォアグラウンド追跡 — マウス等で QM に来ても戻れるように
        cur_fg = focus.get_foreground()
        if cur_fg != last_fg[0]:
            controller.note_foreground_change(last_fg[0], cur_fg)
            last_fg[0] = cur_fg
        # CapsLock 押下処理
        if hook.pressed_event.is_set():
            hook.pressed_event.clear()
            window.on_hotkey()
    timer.timeout.connect(_tick)
    timer.start()

    app.aboutToQuit.connect(hook.uninstall)

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
