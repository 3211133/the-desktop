"""共通の小物 Widget。"""

from __future__ import annotations

from PyQt6.QtWidgets import QBoxLayout, QWidget


class ResponsiveRow(QWidget):
    """子ウィジェットを横並びにする。幅が threshold 未満なら縦並びへ自動切替。

    QBoxLayout の direction を resizeEvent で切り替えるだけ。
    子の再配置 (Qt 側で複雑) は QBoxLayout が面倒見てくれる。
    """

    def __init__(self, threshold: int = 400, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._threshold = threshold
        self._layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    @property
    def threshold(self) -> int:
        return self._threshold

    def add_widget(self, widget: QWidget, stretch: int = 1) -> None:
        self._layout.addWidget(widget, stretch)

    def is_horizontal(self) -> bool:
        return self._layout.direction() == QBoxLayout.Direction.LeftToRight

    def apply_orientation(self, width: int) -> None:
        """指定幅で向きを決めて反映する (テスト用の seam も兼ねる)。"""
        target = (
            QBoxLayout.Direction.LeftToRight
            if width >= self._threshold
            else QBoxLayout.Direction.TopToBottom
        )
        if self._layout.direction() != target:
            self._layout.setDirection(target)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self.apply_orientation(event.size().width())
        super().resizeEvent(event)
