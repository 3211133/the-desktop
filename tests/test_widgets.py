"""ResponsiveRow の単体テスト (qtbot)。"""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel

from quickmemo.widgets import ResponsiveRow


def test_starts_horizontal(qtbot):
    row = ResponsiveRow(threshold=300)
    qtbot.addWidget(row)
    row.add_widget(QLabel("A"))
    row.add_widget(QLabel("B"))
    assert row.is_horizontal()


def test_switches_to_vertical_below_threshold(qtbot):
    row = ResponsiveRow(threshold=300)
    qtbot.addWidget(row)
    row.add_widget(QLabel("A"))
    row.add_widget(QLabel("B"))
    row.apply_orientation(200)
    assert not row.is_horizontal()


def test_switches_back_to_horizontal_above_threshold(qtbot):
    row = ResponsiveRow(threshold=300)
    qtbot.addWidget(row)
    row.add_widget(QLabel("A"))
    row.apply_orientation(100)
    assert not row.is_horizontal()
    row.apply_orientation(500)
    assert row.is_horizontal()


def test_threshold_boundary_is_inclusive_for_horizontal(qtbot):
    """ちょうど threshold = 横並び、未満なら縦。"""
    row = ResponsiveRow(threshold=300)
    qtbot.addWidget(row)
    row.add_widget(QLabel("A"))
    row.apply_orientation(300)
    assert row.is_horizontal()
    row.apply_orientation(299)
    assert not row.is_horizontal()
