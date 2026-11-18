"""Small reusable widgets and helpers every AV Suite app builds screens from.

Only what at least two apps use lives here (the rule of two). Media
Transfer's open_in_smart_preview and PickOneDialog stay in that app.
"""

from __future__ import annotations

import os

from PySide6.QtCore import QStringListModel, Qt, Signal
from PySide6.QtGui import QFont, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QButtonGroup, QCompleter, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy,
    QWidget,
)


def restyle(widget: QWidget):
    """Re-apply the stylesheet after a dynamic property change."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def shortcut_text(keys: str) -> str:
    """*keys* as this system writes them: "Ctrl+Shift+V" is "⇧⌘V" on a Mac.

    For tooltips. Qt's "Ctrl" is the ⌘ key on a Mac, and the menus show it
    that way by themselves. Media Transfer's tooltips spelled their keys by
    hand, so up to 0.1.3 they said "Ctrl+R" on a Mac, where the Control key
    does nothing. Give this the string the QShortcut is made from, so the key
    a tooltip names is the key that works.
    """
    return QKeySequence(keys).toString(QKeySequence.SequenceFormat.NativeText)


def section_label(text: str) -> QLabel:
    label = QLabel(text.upper())       # QSS cannot uppercase
    label.setObjectName("sectionLabel")
    return label


def mono_font() -> QFont:
    """The font for values that line up: sizes, dates, speeds, counts.

    Sized in pixels, like everything in styles.qss. Media Transfer's was once
    11.5 points, which is a third larger wherever the system reports 96 dpi —
    Windows — and there its size and date columns were cut off.
    """
    font = QFont("SF Mono")
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(12)
    return font


def hairline(vertical: bool = False) -> QFrame:
    line = QFrame()
    line.setObjectName("hairline")
    if vertical:
        line.setFixedWidth(1)
    else:
        line.setFixedHeight(1)
    return line


class ElidedLabel(QLabel):
    """One-line label that ends in … instead of squeezing its neighbours.

    The full text stays available as the tooltip.
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(40)
        # Through the override: QLabel's C++ constructor never calls Python's
        # setText, so the promised tooltip would otherwise stay unset.
        self.setText(text)

    def setText(self, text: str):
        super().setText(text)
        self.setToolTip(text)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(self.palette().color(self.foregroundRole()))
        shown = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight,
                                              self.width())
        painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignLeft |
                                          Qt.AlignmentFlag.AlignVCenter), shown)


class PathField(QLineEdit):
    """Folder path entry that also accepts a folder dragged from Finder/Explorer.

    Dropping a file uses its parent folder. The border turns to a dashed accent
    while a valid drag hovers, so the drop target is visible, not guessed. A
    read-only field takes no drop at all (Media Transfer locks a watched job's
    folders that way).
    """

    path_dropped = Signal(str)

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("pathField")
        self.setPlaceholderText(placeholder)
        self.setAcceptDrops(True)
        self.setClearButtonEnabled(True)
        self._history: list[str] = []
        self._completer = QCompleter([], self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.setCompleter(self._completer)

    def set_history(self, folders: list[str]):
        """Recent folders, newest first (FreeFileSync's folder history):
        offered as completions while typing, and all of them on a
        double-click in the field."""
        self._history = list(folders)
        self._completer.setModel(QStringListModel(self._history, self._completer))

    def history(self) -> list[str]:
        return list(self._history)

    def mouseDoubleClickEvent(self, event):
        if self._history:
            self._completer.setCompletionPrefix("")
            self._completer.complete()
            return
        super().mouseDoubleClickEvent(event)

    @staticmethod
    def _folder_from(event) -> str | None:
        md = event.mimeData()
        if not md.hasUrls():
            return None
        for url in md.urls():
            path = url.toLocalFile()
            if not path:
                continue
            path = os.path.normpath(path)       # Qt hands back "/" even on Windows
            return path if os.path.isdir(path) else os.path.dirname(path)
        return None

    def _set_target(self, on: bool):
        self.setProperty("dropTarget", on)
        restyle(self)

    def dragEnterEvent(self, event):
        if self.isReadOnly():               # a locked field: not even a drop
            event.ignore()
            return
        if self._folder_from(event):
            event.acceptProposedAction()
            self._set_target(True)
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if not self.isReadOnly() and self._folder_from(event):
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._set_target(False)

    def dropEvent(self, event):
        folder = self._folder_from(event)
        self._set_target(False)
        if folder and not self.isReadOnly():
            self.setText(folder)
            self.path_dropped.emit(folder)
            event.acceptProposedAction()


class Segmented(QWidget):
    """Adjacent checkable buttons, exactly one selected."""

    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str, str]], parent=None):
        """options: (key, label, tooltip)."""
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        for i, (key, label, tip) in enumerate(options):
            b = QPushButton(label)
            b.setObjectName("segment")
            b.setCheckable(True)
            b.setToolTip(tip)
            b.setProperty("first", i == 0)
            b.setProperty("last", i == len(options) - 1)
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            self._group.addButton(b)
            self._buttons[key] = b
            layout.addWidget(b)

    def value(self) -> str:
        for key, b in self._buttons.items():
            if b.isChecked():
                return key
        return next(iter(self._buttons))

    def set_value(self, key: str):
        if key in self._buttons:
            self._buttons[key].setChecked(True)

    def setEnabled(self, enabled: bool):
        for b in self._buttons.values():
            b.setEnabled(enabled)
