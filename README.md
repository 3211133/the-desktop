# the-desktop

デスクトップ常駐の「機能の入り口」。CapsLock でアクティブウィンドウと往復できる。

- 常に最前面
- **CapsLock** で「現在のアクティブウィンドウ ⇄ QuickMemo」をトグル
- CapsLock 本来の大文字ロックは抱殺（状態を変えない）
- Esc で元のウィンドウに戻る
- × ボタンで終了せずトレイに格納

中身は空のフレーム。機能は `quickmemo/features/` 配下に Widget として追加していく想定。

## 要件

- Windows 10 / 11
- Python 3.12+
- PyQt6

## 起動

```powershell
pip install PyQt6
python -m quickmemo.app
```

## テスト

```powershell
python -m pytest tests/ -v
```

## 構成

```
quickmemo/
├─ protocols.py    Focus / Hotkey の Protocol 定義 (pure)
├─ controller.py   トグル状態機械 (pure)
├─ config.py       設定の読み書き (pure)
├─ focus.py        Win32Focus 実装
├─ hotkey.py       CapsLockHook 実装
├─ window.py       MainWindow (PyQt6)
├─ app.py          配線 (composition root)
└─ features/       将来の機能プラグイン
```

設計方針: ロジック (`controller.py`) と OS/Qt 副作用 (`focus.py` / `hotkey.py` / `window.py`) を Protocol で分離。
ロジックは Qt も Win32 も触らず単体テスト可能。
