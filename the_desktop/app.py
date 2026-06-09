"""the-desktop エントリポイント — 配線のみ。

依存:
  Win32Focus       (focus.py)     ─┐
  CapsLockHook     (hotkey.py)    ─┼─→ ToggleController ─→ MainWindow
  Config           (config.py)    ─┘
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from .bootstrap import ensure_default_configs
from .config import load_config
from .controller import ToggleController
from .focus import Win32Focus
from .hotkey import CapsLockHook
from .window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("the-desktop")
    app.setQuitOnLastWindowClosed(False)

    # 初回起動: 不足している設定ファイルをデフォルト値で生成
    ensure_default_configs()

    cfg = load_config()
    focus = Win32Focus()
    hook = CapsLockHook()

    # QM 構築前の前面ウィンドウを記録 (最初の戻り先のシード)
    initial_fg = focus.get_foreground()

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
    # last_fg を初期 fg で seed することで、最初の "→ QM" 変化で note_foreground_change が
    # 起動時の前面ウィンドウを prev として記録する
    last_fg = [initial_fg]

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
