"""次の "定時" までの残り時間を表示する機能 (デフォルト 09:00)。

Pure ロジック (`remaining_to` / `format_remaining` / `next_occurrence`) と
Widget を同居させ、ロジックは Qt 非依存で単体テスト可能。

セマンティクス: target は「now より後で最初に来る HH:MM」。
すでに今日の target を過ぎていれば翌日の target を採用する。
従って残り時間は **常に正**。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ..paths import config_path

DEFAULT_TARGET = time(9, 0)
CONFIG_FILE = config_path("remaining")


@dataclass
class RemainingConfig:
    target: time = DEFAULT_TARGET


def load_config(path: Path = CONFIG_FILE) -> RemainingConfig:
    """`{"target": "HH:MM"}` を読み込む。不存在・破損は DEFAULT。"""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        h, m = (int(x) for x in str(raw["target"]).split(":", 1))
        return RemainingConfig(target=time(h, m))
    except Exception:
        return RemainingConfig()


def save_config(cfg: RemainingConfig, path: Path = CONFIG_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"target": cfg.target.strftime("%H:%M")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def next_occurrence(now: datetime, target: time = DEFAULT_TARGET) -> datetime:
    """now より後で最初に来る target 時刻の datetime を返す。

    target が今日まだ来ていなければ今日の target、来ていれば翌日の target。
    """
    today_target = datetime.combine(now.date(), target)
    if today_target > now:
        return today_target
    return today_target + timedelta(days=1)


def remaining_to(now: datetime, target: time = DEFAULT_TARGET) -> timedelta:
    """now から次の target 時刻までの残り。常に正の timedelta。"""
    return next_occurrence(now, target) - now


def format_remaining(td: timedelta, target: time = DEFAULT_TARGET) -> str:
    """timedelta を "HH:MM まで HH:MM:SS" 形式に。"""
    total_seconds = max(0, int(td.total_seconds()))
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{target.strftime('%H:%M')}まで{h:02d}:{m:02d}:{s:02d}"


class RemainingWidget(QWidget):
    """定時までの残り時間を表示する1行 Widget。30秒ごとに更新。"""

    def __init__(self, target: time | None = None, parent=None) -> None:
        super().__init__(parent)
        # target 引数が無ければ設定ファイルから読む
        self.target = target if target is not None else load_config().target

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
