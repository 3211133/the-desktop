"""統合スモークテスト (Qt が必要なもの)。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def test_imports_clean():
    """全モジュールが import できる。"""
    from the_desktop import (  # noqa: F401
        app, config, controller, focus, hotkey, protocols, window,
    )


def test_focus_zero_hwnd_returns_false():
    from the_desktop.focus import Win32Focus
    assert Win32Focus().restore(0) is False


def test_hotkey_constructible_without_install():
    """install() を呼ばない限り副作用なし。"""
    from the_desktop.hotkey import CapsLockHook
    h = CapsLockHook()
    assert h._thread is None
    assert h._hook_id is None
    assert h.pressed_event.is_set() is False


@pytest.fixture
def main_window(qtbot):
    from the_desktop.config import Config
    from the_desktop.window import MainWindow
    w = MainWindow(Config())
    qtbot.addWidget(w)
    return w


def test_window_topmost_by_default(main_window):
    from PyQt6.QtCore import Qt
    assert main_window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint


def test_close_hides_to_tray(main_window):
    main_window.show()
    main_window.close()
    assert not main_window.isVisible()
    assert main_window.tray.isVisible()


def test_window_routes_hotkey_to_controller(main_window):
    """on_hotkey() が controller.on_hotkey() を呼ぶ。"""
    fake = MagicMock()
    main_window.set_controller(fake)
    main_window.on_hotkey()
    fake.on_hotkey.assert_called_once()


def test_window_routes_esc_to_controller(main_window, qtbot):
    """Esc キーで controller.return_to_prev が呼ばれる。"""
    from PyQt6.QtCore import Qt
    fake = MagicMock()
    main_window.set_controller(fake)
    main_window.show()
    qtbot.keyPress(main_window, Qt.Key.Key_Escape)
    fake.return_to_prev.assert_called_once()


def test_window_no_controller_safe(main_window):
    """controller 未設定でも on_hotkey/return_to_prev は例外を出さない。"""
    main_window.on_hotkey()
    main_window.return_to_prev()


def test_topmost_toggle_updates_flags(main_window):
    from PyQt6.QtCore import Qt
    main_window._on_topmost_toggled(False)
    assert not (main_window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
    main_window._on_topmost_toggled(True)
    assert main_window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
