"""定時 (デフォルト 18:00) までの残り時間を表示する機能。

Pure ロジック (`remaining_to` / `format_remaining`) と Widget を同居させ、
ロジックは Qt 非依存で単体テスト可能。
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

DEFAULT_TARGET = time(18, 0)


def remaining_to(now: datetime, target: time = DEFAULT_TARGET) -> timedelta:
    """now から **同日の** target 時刻までの残り。

    仕様:
    - target 前: 正の timedelta
    - target 後・同日中: 負の timedelta (「定時超過」を示す)
    - 日付が変わると新しい日の target を基準にするので自然に正値に戻る
      (深夜 00:00 過ぎに勤怠時計をリセットする動作)
    """
    target_dt = datetime.combine(now.date(), target)
    return target_dt - now


def format_remaining(td: timedelta, target: time = DEFAULT_TARGET) -> str:
    """timedelta を "HH:MM まで HH:MM:SS" 形式に。

    target 過ぎの場合は先頭に "-" を付ける。
    """
    total_seconds = int(td.total_seconds())
    sign = "-" if total_seconds < 0 else ""
    secs = abs(total_seconds)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{target.strftime('%H:%M')}まで{sign}{h:02d}:{m:02d}:{s:02d}"


class RemainingWidget(QWidget):
    """定時までの残り時間を表示する1行 Widget。30秒ごとに更新。"""

    def __init__(self, target: time = DEFAULT_TARGET, parent=None) -> None:
        super().__init__(parent)
        self.target = target

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)  # 1s
        self._timer.timeout.connect(self._refresh)
        self._timer.start()
        self._refresh()

    def _refresh(self) -> None:
        td = remaining_to(datetime.now(), self.target)
        self.label.setText(format_remaining(td, self.target))
