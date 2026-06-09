"""the-desktop MainWindow — 最前面・トレイ・空の中央領域。

判定ロジック (CapsLock トグル) は ToggleController に委譲。
MainWindow はプレゼンテーション層に徹する。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QStatusBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .config import Config, save_config


class MainWindow(QMainWindow):
    def __init__(self, cfg: Optional[Config] = None) -> None:
        super().__init__()
        self.cfg = cfg or Config()
        self._controller = None  # set_controller で注入

        self.setWindowTitle("the-desktop")
        self._apply_topmost(self.cfg.topmost)

        g = self.cfg.window
        self.setGeometry(g.x, g.y, g.w, g.h)

        from .features.bunpo import BunpoWidget
        from .features.news import NewsWidget
        from .features.remaining import RemainingWidget
        from .features.weather import WeatherWidget
        from .widgets import ResponsiveRow

        central = QWidget(self)
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # 上段: 定時カウントダウン + 天気
        # 幅が狭ければ縦並び、広ければ横並びに自動切替
        top = ResponsiveRow(threshold=380, parent=central)
        top.add_widget(RemainingWidget(parent=top))
        top.add_widget(WeatherWidget(parent=top))
        v.addWidget(top)

        # 下段: 分報 + ニュース (同じく幅で縦横切替)
        # 分報は履歴が縦に伸びるので少し広め (2 : 1)
        bottom = ResponsiveRow(threshold=480, parent=central)
        bottom.add_widget(BunpoWidget(parent=bottom), stretch=2)
        bottom.add_widget(NewsWidget(parent=bottom), stretch=1)
        v.addWidget(bottom, stretch=1)

        self.setCentralWidget(central)

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
        self.tray.setToolTip("the-desktop")

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
        """CapsLock / トレイ・メニュー経由のトグル要求。

        順序が重要: controller.on_hotkey() の **前に** show/restore してはいけない。
        事前に Qt をアクティブ化すると controller が「自分が前面」と誤判定して
        ループする。focus.restore() (Win32 側) が最小化解除と前面化を担う。
        その後で Qt の visible/minimized 状態を同期する。
        """
        if self._controller is None:
            return
        result = self._controller.on_hotkey()

        from .controller import ToggleAction
        if result.action is ToggleAction.ACTIVATE_SELF:
            # focus.restore が Win32 で SW_RESTORE/SW_SHOW しているので、
            # Qt 状態を後追いで合わせる
            if self.isMinimized():
                self.showNormal()
            elif not self.isVisible():
                self.show()
        elif result.action is ToggleAction.HIDE_SELF:
            # hide() でなく showMinimized() (Qt の visible 状態を保つ)
            self.showMinimized()

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
            "the-desktop",
            "トレイに格納しました。CapsLock で呼び出せます。",
            QSystemTrayIcon.MessageIcon.Information,
            1500,
        )

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.return_to_prev()
        else:
            super().keyPressEvent(event)
