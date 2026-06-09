"""QuickMemo 設定の読み書き — pure (Qt/Win32 非依存)。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .paths import config_path

CONFIG_FILE = config_path("app")


@dataclass
class WindowGeometry:
    x: int = 200
    y: int = 200
    w: int = 420
    h: int = 320


@dataclass
class Config:
    window: WindowGeometry = field(default_factory=WindowGeometry)
    topmost: bool = True


def load_config(path: Path = CONFIG_FILE) -> Config:
    """設定をロード。不存在・破損は DEFAULT で返す。"""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return Config()

    win = raw.get("window") or {}
    geom = WindowGeometry(
        x=int(win.get("x", 200)),
        y=int(win.get("y", 200)),
        w=int(win.get("w", 420)),
        h=int(win.get("h", 320)),
    )
    return Config(window=geom, topmost=bool(raw.get("topmost", True)))


def save_config(cfg: Config, path: Path = CONFIG_FILE) -> None:
    """設定を保存。親ディレクトリは自動作成。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
