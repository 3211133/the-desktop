"""the-desktop launcher — ダブルクリックで起動 (コンソール無し)。

`.pyw` 拡張子は pythonw.exe に関連付けられているので
エクスプローラーで本ファイルをダブルクリックすれば常駐する。
"""

import os
import sys

# repo ルート (本ファイルのある場所) を sys.path に追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from the_desktop.app import main

sys.exit(main())
