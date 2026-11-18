"""Every shared widget and stylesheet rule, dark and light side by side.

    python -m av_suite_ui.gallery                     # the window
    python -m av_suite_ui.gallery --accent "#3fa0f0"  # another accent
    python -m av_suite_ui.gallery --screenshot shot.png   # a PNG, then quit

Each side carries its own stylesheet (theme.build_stylesheet for its mode),
so both modes are on screen at once. Look here after changing the theme —
and in the macOS style too (QT_STYLE_OVERRIDE=macOS), which reports 0 frame
widths where Fusion does not.
"""

from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget, QMainWindow, QProgressBar, QPushButton,
    QScrollArea, QSplitter, QStatusBar, QTableView, QTreeView, QVBoxLayout, QWidget,
)

from . import __version__, theme
from .widgets import (
    ElidedLabel, PathField, Segmented, hairline, mono_font, restyle, section_label, shortcut_text,
)

# The colour roles shown as swatches, in the order a designer reads them.
SWATCHES = (
    ("Surfaces", ("bg_sunken", "bg_base", "bg_raised", "bg_elevated", "bg_overlay")),
    ("Borders", ("border_subtle", "border_default", "border_strong")),
    ("Text", ("text_primary", "text_secondary", "text_muted")),
    ("Accent", ("accent", "accent_hover", "accent_pressed", "accent_dim", "accent_tint",
                "on_accent")),
    ("Status", ("ok", "warn", "error")),
)


def _button(text: str, name: str = "", *, checkable=False, checked=False, enabled=True,
            tip: str = "") -> QPushButton:
    b = QPushButton(text)
    if name:
        b.setObjectName(name)
    b.setCheckable(checkable)
    b.setChecked(checked)
    b.setEnabled(enabled)
    if tip:
        b.setToolTip(tip)
    return b


def _label(text: str, name: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName(name)
    return label


def _row(*widgets, stretch=True) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(8)
    for w in widgets:
        lay.addWidget(w)
    if stretch:
        lay.addStretch()
    return lay


class Panel(QWidget):
    """One mode's worth of everything. Rebuilt in place by set_accent."""

    def __init__(self, mode: str, accent: str | None = None, icon_dir=None, parent=None):
        super().__init__(parent)
        self.mode, self._icon_dir = mode, icon_dir
        self.setObjectName(f"panel_{mode}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._structure())
        body = QWidget()
        self._body = QVBoxLayout(body)
        self._body.setContentsMargins(20, 16, 20, 20)
        self._body.setSpacing(10)
        self._swatch_grid = QGridLayout()
        self._sections()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(body)
        lay.addWidget(scroll, 1)
        status = QStatusBar()
        status.showMessage(f"{mode.title()} · av_suite_ui {__version__}")
        lay.addWidget(status)
        self.set_accent(accent)

    # ── structure: nav rail, toolbar, action bar ────────────────────────────
    def _structure(self) -> QWidget:
        frame = QWidget()
        outer = QHBoxLayout(frame)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        rail = QFrame()
        rail.setObjectName("navRail")
        rail.setFixedWidth(130)
        rl = QVBoxLayout(rail)
        rl.setContentsMargins(0, 8, 0, 8)
        rl.setSpacing(0)
        for text, checked, enabled in (("Sync", True, True), ("Transfer", False, True),
                                       ("Log", False, False)):
            rl.addWidget(_button(text, "navButton", checkable=True, checked=checked,
                                 enabled=enabled))
        rl.addStretch()
        outer.addWidget(rail)
        right = QVBoxLayout()
        right.setSpacing(0)
        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(16, 10, 16, 10)
        tl.addWidget(_label(f"{self.mode.title()} mode", "appTitle"))
        tl.addStretch()
        tl.addWidget(_button("⋯", "iconButton", tip="More"))
        tl.addWidget(_button("Compare", "primary",
                             tip=f"Compare the folders ({shortcut_text('Ctrl+R')})"))
        right.addWidget(toolbar)
        middle = QLabel("Nothing compared yet")
        middle.setObjectName("placeholder")
        middle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        middle.setMinimumHeight(48)
        right.addWidget(middle, 1)
        bar = QFrame()
        bar.setObjectName("actionBar")
        al = QHBoxLayout(bar)
        al.setContentsMargins(16, 8, 16, 8)
        al.addWidget(_label("3 files · 1.24 GB", "data"))
        al.addStretch()
        al.addWidget(_button("Mirror with deletes", "danger"))
        right.addWidget(bar)
        outer.addLayout(right, 1)
        return frame

    # ── the sections ────────────────────────────────────────────────────────
    def _section(self, title: str):
        if self._body.count():
            self._body.addSpacing(8)
        self._body.addWidget(section_label(title))

    def _sections(self):
        b = self._body
        self._section("Palette")
        b.addLayout(self._swatch_grid)

        self._section("Buttons")
        b.addLayout(_row(_button("Default"), _button("Primary", "primary"),
                         _button("Danger", "danger"), _button("Disabled", enabled=False)))
        b.addLayout(_row(_button("Route by type", checkable=True, checked=True),
                         _button("On, locked", checkable=True, checked=True, enabled=False),
                         _button("Primary off", "primary", enabled=False),
                         _button("✕", "iconButton", tip="Remove"),
                         _button("✕", "iconButton", enabled=False)))
        seg = Segmented([("mirror", "Mirror", "Make the target a copy of the source"),
                         ("update", "Update", "Copy new and newer files only"),
                         ("two_way", "Two-way", "Changes go both ways")])
        seg.set_value("update")
        locked = Segmented([("a", "Locked", ""), ("b", "Segments", "")])
        locked.set_value("a")
        locked.setEnabled(False)
        b.addLayout(_row(seg, locked))
        b.addLayout(_row(*(_button(t, "chip", checkable=True, checked=c)
                           for t, c in (("All  1,204", True), ("Newer  12", False),
                                        ("Conflict  2", False)))))

        self._section("Inputs")
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        text = QLineEdit("FOH_Show_v12")
        empty = QLineEdit()
        empty.setPlaceholderText("Placeholder")
        path = PathField("Drop a folder here")
        path.setText("/Volumes/Media/Show/Day 2")
        path.set_history(["/Volumes/Media/Show/Day 2", "/Volumes/Media/Show/Day 1"])
        target = PathField()
        target.setText("Drop target, while a drag hovers")
        target.setProperty("dropTarget", True)
        restyle(target)
        locked_path = PathField()
        locked_path.setText("/Volumes/Media/Watched (read-only)")
        locked_path.setReadOnly(True)
        combo = QComboBox()
        combo.addItems(["All servers  (4)", "actor-01", "actor-02"])
        dead = QComboBox()
        dead.addItems(["Locked during a transfer"])
        dead.setEnabled(False)
        on, off = QCheckBox("Verify after copy"), QCheckBox("Keep versions")
        on.setChecked(True)
        for i, w in enumerate((text, empty, path, target, locked_path, combo, dead)):
            grid.addWidget(w, i // 2, i % 2)
        checks = _row(on, off)
        checks.setSpacing(20)
        grid.addLayout(checks, 3, 1)
        b.addLayout(grid)

        self._section("Table, list and tree")
        b.addWidget(self._table())
        lists = QHBoxLayout()
        pick = QListWidget()
        pick.addItems(["Show A", "Show B", "Rehearsal"])
        pick.setCurrentRow(1)
        pick.setFixedHeight(96)
        lists.addWidget(pick)
        lists.addWidget(self._tree())
        b.addLayout(lists)

        self._section("Progress")
        for value, state in ((62, ""), (100, "done"), (40, "failed")):
            bar = QProgressBar()
            bar.setValue(value)
            if state:
                bar.setProperty("state", state)
            b.addWidget(bar)

        self._section("Labels")
        b.addWidget(_label("App title", "appTitle"))
        b.addWidget(_label(f"A hint under a field · Compare is {shortcut_text('Ctrl+R')}",
                           "hint"))
        b.addLayout(_row(_label("1023.9 MB", "data"), _label("30 Sep 26  23:59", "dataStrong")))
        mono = QLabel("mono_font(): 0123456789  A003_C014.mov")
        mono.setFont(mono_font())
        b.addWidget(mono)
        elided = ElidedLabel("ElidedLabel: A003_C014_0192XK_S000_T013_PROXY_a_very_long_name.mov")
        elided.setFixedWidth(260)
        b.addWidget(elided)
        b.addWidget(hairline())
        b.addWidget(_label("⚠ 2 files could not be read: they were left as they are",
                           "warnNote"))
        b.addWidget(_label("✕ The destination is not mounted", "errorNote"))
        b.addWidget(_label("Placeholder: nothing here yet", "placeholder"))
        b.addStretch()

    def _table(self) -> QTableView:
        model = QStandardItemModel(0, 4, self)
        model.setHorizontalHeaderLabels(["NAME", "SIZE", "MODIFIED", "STATUS"])
        rows = (("A003_C014.mov", "1023.9 MB", "30 Sep 26  23:59", "Newer source", True),
                ("A003_C015.mov", "812.4 MB", "30 Sep 26  21:10", "In sync · verified", False),
                ("B001_C001.mov", "2.31 GB", "29 Sep 26  09:02", "Conflict · unreadable", True))
        for name, size, date, status, ticked in rows:
            first = QStandardItem(name)
            first.setCheckable(True)
            first.setCheckState(Qt.CheckState.Checked if ticked else Qt.CheckState.Unchecked)
            cells = [first, QStandardItem(size), QStandardItem(date), QStandardItem(status)]
            for cell in cells[1:3]:
                cell.setFont(mono_font())
            model.appendRow(cells)
        table = QTableView()
        table.setModel(model)
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.verticalHeader().hide()
        table.verticalHeader().setDefaultSectionSize(30)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, width in ((1, 110), (2, 170), (3, 170)):
            table.setColumnWidth(col, width)
        table.selectRow(1)
        table.setFixedHeight(28 + 3 * 30 + 4)
        return table

    def _tree(self) -> QTreeView:
        model = QStandardItemModel(self)
        show = QStandardItem("Show")
        for day in ("Day 1", "Day 2"):
            item = QStandardItem(day)
            item.appendRow(QStandardItem("Renders"))
            show.appendRow(item)
        model.appendRow(show)
        model.appendRow(QStandardItem("Rehearsal"))
        tree = QTreeView()
        tree.setModel(model)
        tree.setHeaderHidden(True)
        tree.expand(model.index(0, 0))
        tree.setCurrentIndex(model.index(1, 0, model.index(0, 0)))
        tree.setFixedHeight(96)
        return tree

    # ── accent ──────────────────────────────────────────────────────────────
    def set_accent(self, accent: str | None):
        self.accent = accent
        self.setStyleSheet(theme.build_stylesheet(self.mode, accent, icon_dir=self._icon_dir))
        pal = theme.palette(self.mode, accent)
        grid = self._swatch_grid
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                # deleteLater waits for the next event-loop pass: until then
                # the old swatch would still be shown (and found) beside the new.
                old = item.widget()
                old.hide()
                old.setParent(None)
                old.deleteLater()
        for row, (group, roles) in enumerate(SWATCHES):
            grid.addWidget(_label(group, "hint"), row, 0)
            for col, role in enumerate(roles, start=1):
                chip = QLabel(f"{role}\n{pal[role]}")
                chip.setObjectName(f"swatch_{role}")
                ink = theme.on_colour(pal[role])
                chip.setStyleSheet(
                    f"QLabel {{ background: {pal[role]}; color: {ink}; font-size: 10px;"
                    f" border: 1px solid {pal['border_subtle']}; padding: 4px; }}")
                chip.setMinimumWidth(92)
                grid.addWidget(chip, row, col)


class Gallery(QMainWindow):
    def __init__(self, accent: str | None = None, icon_dir=None):
        super().__init__()
        self.setWindowTitle(f"AV Suite UI gallery — av_suite_ui {__version__}")
        self.panels = [Panel(mode, accent, icon_dir) for mode in theme.MODES]
        split = QSplitter()
        for panel in self.panels:
            split.addWidget(panel)
        top = QFrame()
        top.setObjectName("toolbar")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(12, 6, 12, 6)
        tl.addWidget(_label("Accent", "hint"))
        self.accent_btn = _button("Pick…", tip="Try another accent on both sides")
        self.accent_btn.clicked.connect(self._pick_accent)
        reset = _button("Tally amber", tip="Back to the default accent")
        reset.clicked.connect(lambda: self.set_accent(None))
        tl.addWidget(self.accent_btn)
        tl.addWidget(reset)
        tl.addStretch()
        central = QWidget()
        cl = QVBoxLayout(central)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.addWidget(top)
        cl.addWidget(split, 1)
        self.setCentralWidget(central)
        self.setStyleSheet(theme.build_stylesheet("dark", accent, icon_dir=icon_dir))
        self.resize(1400, 960)

    def set_accent(self, accent: str | None):
        for panel in self.panels:
            panel.set_accent(accent)

    def _pick_accent(self):
        current = QColor(self.panels[0].accent or theme.DARK_DEFAULT_ACCENT)
        colour = QColorDialog.getColor(current, self, "Accent colour")
        if colour.isValid():
            self.set_accent(colour.name())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m av_suite_ui.gallery",
                                     description="Every shared widget, dark and light.")
    parser.add_argument("--accent", help="an accent colour, e.g. #3fa0f0")
    parser.add_argument("--screenshot", metavar="PNG", help="save the window as PNG and quit")
    args = parser.parse_args(argv)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = Gallery(args.accent)
    window.show()
    if args.screenshot:
        app.processEvents()
        ok = window.grab().save(args.screenshot)
        print(args.screenshot if ok else f"could not write {args.screenshot}")
        return 0 if ok else 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
