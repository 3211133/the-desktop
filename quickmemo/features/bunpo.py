"""分報機能 — タイムスタンプ付き短文をローカル JSONL に追記して時系列で表示。

Store (pure) と Widget (Qt) を同居させ、Store は単体テスト可能にする。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

DEFAULT_PATH = Path.home() / ".quickmemo" / "bunpo.jsonl"


@dataclass(frozen=True)
class Entry:
    ts: str   # ISO8601 (秒精度)
    text: str


class BunpoStore:
    """分報の永続化 — JSONL 形式 (1行1エントリ)。Qt 非依存。"""

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = path

    def append(self, text: str, now: datetime | None = None) -> Entry:
        text = text.strip()
        if not text:
            raise ValueError("text must not be empty")
        ts = (now or datetime.now()).replace(microsecond=0).isoformat()
        entry = Entry(ts=ts, text=text)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return entry

    def load(self) -> list[Entry]:
        if not self.path.exists():
            return []
        out: list[Entry] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
                out.append(Entry(ts=str(raw["ts"]), text=str(raw["text"])))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue  # 破損行はスキップ
        return out


def format_entry(e: Entry) -> str:
    """表示用に整形 — "HH:MM テキスト" (日付は省略、トグル運用前提なら十分)。"""
    try:
        dt = datetime.fromisoformat(e.ts)
        return f"{dt.strftime('%m/%d %H:%M')}  {e.text}"
    except ValueError:
        return f"{e.ts}  {e.text}"


class BunpoWidget(QWidget):
    """分報入力 + 一覧表示。MainWindow の中央領域に差し込む。"""

    def __init__(self, store: BunpoStore | None = None, parent=None) -> None:
        super().__init__(parent)
        self.store = store or BunpoStore()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.input = QLineEdit(self)
        self.input.setPlaceholderText("分報を書いて Enter")
        self.input.returnPressed.connect(self._on_submit)
        layout.addWidget(self.input)

        self.list = QListWidget(self)
        layout.addWidget(self.list, stretch=1)

        self._reload()

    def _on_submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        try:
            entry = self.store.append(text)
        except ValueError:
            return
        self.input.clear()
        self.list.insertItem(0, QListWidgetItem(format_entry(entry)))

    def _reload(self) -> None:
        self.list.clear()
        for entry in reversed(self.store.load()):  # 新しいものを上に
            self.list.addItem(QListWidgetItem(format_entry(entry)))
