"""QuickMemo dev launcher — モックフェッチャー有効で起動。

UI 状態 (天気の強度マーカー、取得失敗表示 等) を実 API なしで確認するのに使う。
"""

import os
import sys

os.environ["QUICKMEMO_DEV_MOCKS"] = "1"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quickmemo.app import main

sys.exit(main())
