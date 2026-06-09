"""初回起動でデフォルト設定ファイルを書き出すブートストラップ。

各機能の `*Config` と `save_config` を集めて、まだ存在しない設定ファイルを
デフォルト値で生成する。`load_config` は読み専に保ち、ここを別経路にする。

`app.py` の `main()` から一度だけ呼ばれる。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, NamedTuple


class _Spec(NamedTuple):
    path: Path
    save: Callable[[Path], None]  # path を明示的に渡す (monkeypatch 対応)


def _specs() -> list[_Spec]:
    # 遅延 import: bootstrap がトップレベル import で重くなるのを避ける
    from . import config as app_cfg
    from .features import news as news_mod
    from .features import remaining as rem_mod
    from .features import weather as weather_mod

    return [
        _Spec(app_cfg.CONFIG_FILE,
              lambda p: app_cfg.save_config(app_cfg.Config(), p)),
        _Spec(news_mod.CONFIG_FILE,
              lambda p: news_mod.save_config(news_mod.NewsConfig(), p)),
        _Spec(rem_mod.CONFIG_FILE,
              lambda p: rem_mod.save_config(rem_mod.RemainingConfig(), p)),
        _Spec(weather_mod.CONFIG_FILE,
              lambda p: weather_mod.save_config(weather_mod.WeatherConfig(), p)),
    ]


def ensure_default_configs() -> list[Path]:
    """存在しない設定ファイルをデフォルト値で作る。

    返り値は新規に作成したファイルのパス一覧 (テスト/ログ確認用)。
    """
    created: list[Path] = []
    for spec in _specs():
        if not spec.path.exists():
            spec.save(spec.path)
            created.append(spec.path)
    return created
