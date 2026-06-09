"""ファイル配置の一元管理。

ポリシー:
- すべてのユーザーファイルはプロジェクトディレクトリ配下に置く (ホーム汚さない)
- **設定** と **データ** を分離する
  - config/  ... 設定 (機能別 *.json、アプリが書き換えうるが「ユーザーが消しても困らない」)
  - data/    ... 機能データ (例: 分報エントリ、ユーザー入力の蓄積。失うと困る)

両ディレクトリは .gitignore 対象 — ユーザー固有の内容を commit しない。
存在しない場合は書き込み時に自動生成する。
"""

from __future__ import annotations

from pathlib import Path

# the_desktop/paths.py → リポジトリルートは2つ上 (the_desktop の親)
REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"


def config_path(name: str) -> Path:
    """機能設定ファイルのパス。`name` は拡張子なし。

    例: config_path("app") → <repo>/config/app.json
    """
    return CONFIG_DIR / f"{name}.json"


def data_path(name: str) -> Path:
    """機能データファイルのパス。`name` は拡張子付き (機能側で形式を決める)。

    例: data_path("bunpo.jsonl") → <repo>/data/bunpo.jsonl
    """
    return DATA_DIR / name
