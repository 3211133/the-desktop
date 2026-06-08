"""QuickMemo MainWindow — 最前面・トレイ・空の中央領域。

判定ロジック (CapsLock トグル) は ToggleController に委譲。
MainWindow はプレゼンテーション層に徹する。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QStatusBar,
    QSystemTrayIcon,
)

from .config import Config, save_config


class MainWindow(QMainWindow):
    def __init__(self, cfg: Optional[Config] = None) -> None:
        super().__init__()
        self.cfg = cfg or Config()
        self._controller = None  # set_controller で注入

        self.setWindowTitle("QuickMemo")
        self._apply_topmost(self.cfg.topmost)

        g = self.cfg.window
        self.setGeometry(g.x, g.y, g.w, g.h)

        from .features.bunpo import BunpoWidget
        self.setCentralWidget(BunpoWidget(parent=self))

        self.status = QStatusBar(self)
        self.setStatusBar(self.status)
        self.status.showMessage("Ready — CapsLock で呼び出し")

        self._build_tray()

    # ── DI ─────────────────────────────────────────────────────────────────

    def set_controller(self, controller) -> None:
        """ToggleController を注入する。app.py から呼ぶ。"""
        self._controller = controller

    # ── トレイ ─────────────────────────────────────────────────────────────

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(
            QApplication.style().standardIcon(
                QApplication.style().StandardPixmap.SP_ComputerIcon
            )
        )
        self.tray.setToolTip("QuickMemo")

        menu = QMenu()
        act_toggle = QAction("表示/復帰", self)
        act_toggle.triggered.connect(self.on_hotkey)
        menu.addAction(act_toggle)

        self.act_topmost = QAction("最前面", self, checkable=True)
        self.act_topmost.setChecked(self.cfg.topmost)
        self.act_topmost.triggered.connect(self._on_topmost_toggled)
        menu.addAction(self.act_topmost)

        menu.addSeparator()
        act_quit = QAction("終了", self)
        act_quit.triggered.connect(self._quit)
        menu.addAction(act_quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: self.on_hotkey()
            if r == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )
        self.tray.show()

    # ── 最前面 ─────────────────────────────────────────────────────────────

    def _apply_topmost(self, on: bool) -> None:
        flags = self.windowFlags()
        if on:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        if self.isVisible():
            self.show()

    def _on_topmost_toggled(self, checked: bool) -> None:
        self.cfg.topmost = checked
        self._apply_topmost(checked)

    # ── Controller への橋渡し ──────────────────────────────────────────────

    def on_hotkey(self) -> None:
        """CapsLock / トレイ・メニュー経由のトグル要求。"""
        if self._controller is None:
            return
        # 自分が見えていなければ先に show する (Controller は表示状態を知らない)
        if not self.isVisible() or self.isMinimized():
            self.showNormal()
        self._controller.on_hotkey()

    def return_to_prev(self) -> None:
        """Esc 経由の明示的「戻る」。"""
        if self._controller is None:
            return
        self._controller.return_to_prev()

    # ── 終了 / 永続化 ──────────────────────────────────────────────────────

    def _save_geometry(self) -> None:
        g = self.geometry()
        self.cfg.window.x = g.x()
        self.cfg.window.y = g.y()
        self.cfg.window.w = g.width()
        self.cfg.window.h = g.height()
        save_config(self.cfg)

    def _quit(self) -> None:
        self._save_geometry()
        QApplication.quit()

    # ── Qt overrides ───────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "QuickMemo",
            "トレイに格納しました。CapsLock で呼び出せます。",
            QSystemTrayIcon.MessageIcon.Information,
            1500,
        )

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.return_to_prev()
        else:
            super().keyPressEvent(event)
