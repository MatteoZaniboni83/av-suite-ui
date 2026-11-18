"""The shared widget helpers: the pieces every screen is built from.

Ported from Annotations' test_widgets.py, with Media Transfer's folder
history and read-only lock added.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QMimeData, Qt, QUrl

MAC = sys.platform == "darwin"


class DragEvent:
    """Stands in for Qt's drag/drop events: just mime data and the verdict."""

    def __init__(self, md: QMimeData):
        self._md = md
        self.accepted = None

    def mimeData(self) -> QMimeData:
        return self._md

    def acceptProposedAction(self):
        self.accepted = True

    def ignore(self):
        self.accepted = False


def folder_drag(path) -> DragEvent:
    md = QMimeData()
    md.setUrls([QUrl.fromLocalFile(str(path))])
    return DragEvent(md)


def test_shortcut_text_is_how_this_system_writes_the_keys(qapp):
    from av_suite_ui.widgets import shortcut_text
    assert shortcut_text("Ctrl+Shift+V") == ("⇧⌘V" if MAC else "Ctrl+Shift+V")


def test_section_labels_are_uppercased_in_code(qapp):
    """QSS text-transform does not work in Qt, so .upper() has to happen here."""
    from av_suite_ui.widgets import section_label
    label = section_label("Destinations")
    assert label.text() == "DESTINATIONS"
    assert label.objectName() == "sectionLabel"


def test_the_value_font_is_sized_in_pixels(qapp):
    """In points it rendered a third larger wherever the system reports 96 dpi
    — Windows — and cut off Media Transfer's size and date columns there,
    while looking right on a Mac. Runs everywhere: it needs no fonts."""
    from PySide6.QtGui import QFont

    from av_suite_ui.widgets import mono_font
    font = mono_font()
    assert font.pixelSize() == 12, "sized in pixels, like the stylesheet"
    assert font.styleHint() == QFont.StyleHint.Monospace


def test_a_hairline_is_one_pixel_either_way(qapp):
    from av_suite_ui.widgets import hairline
    across, down = hairline(), hairline(vertical=True)
    assert across.objectName() == down.objectName() == "hairline"
    assert across.maximumHeight() == across.minimumHeight() == 1
    assert down.maximumWidth() == down.minimumWidth() == 1


def test_restyle_applies_a_changed_dynamic_property(qapp, icons):
    """QSS reads a dynamic property once, at polish: without restyle() the
    drop-target border would never appear."""
    from PySide6.QtWidgets import QLineEdit

    from av_suite_ui import theme
    from av_suite_ui.widgets import restyle
    field = QLineEdit()
    field.setObjectName("pathField")
    field.setStyleSheet(theme.build_stylesheet("dark", icon_dir=icons))
    field.resize(200, 30)
    field.show()
    qapp.processEvents()
    before = field.grab().toImage().pixelColor(10, 15)
    field.setProperty("dropTarget", True)
    restyle(field)
    qapp.processEvents()
    after = field.grab().toImage().pixelColor(10, 15)
    assert after.name() == theme.palette("dark")["accent_tint"] != before.name()
    field.close()


def test_an_elided_label_ends_in_dots_and_keeps_the_whole_text_as_tooltip(qapp):
    from av_suite_ui.widgets import ElidedLabel
    name = "a really long attachment name that cannot possibly fit.mov"
    label = ElidedLabel()
    label.setText(name)
    label.setFixedWidth(80)
    label.show()
    qapp.processEvents()
    label.grab()                      # the paint path must survive being drawn
    shown = label.fontMetrics().elidedText(name, Qt.TextElideMode.ElideRight, label.width())
    assert shown.endswith("…")
    assert label.fontMetrics().horizontalAdvance(shown) <= label.width()
    assert label.toolTip() == name
    label.close()


def test_an_elided_label_constructed_with_text_has_its_tooltip_from_birth(qapp):
    """QLabel's C++ constructor never calls the Python setText override, so a
    label built with text used to elide with no tooltip at all (Media
    Transfer's copy still does)."""
    from av_suite_ui.widgets import ElidedLabel
    name = "A003_C014_0192XK_S000_T013_PROXY.mov"
    label = ElidedLabel(name)
    assert label.text() == name
    assert label.toolTip() == name


def test_path_field_normalises_a_dropped_path_and_takes_a_files_folder(qapp, tmp_path):
    """Qt hands drop URLs back with "/" and whatever the drag source wrote;
    everything must go through normpath before it is shown or emitted."""
    from av_suite_ui.widgets import PathField
    f = tmp_path / "clips" / "a.mov"
    f.parent.mkdir()
    f.write_bytes(b"x")
    field = PathField()
    dropped: list[str] = []
    field.path_dropped.connect(lambda p: dropped.append(p))
    # An un-normalised spelling of the file's path, as a drag source may send.
    drop = folder_drag(tmp_path / "clips" / "." / "a.mov")
    field.dropEvent(drop)
    assert drop.accepted
    assert field.text() == str(tmp_path / "clips")
    assert dropped == [str(tmp_path / "clips")]
    assert PathField._folder_from(folder_drag(f.parent)) == str(f.parent)


def test_path_field_shows_the_drop_target_border_only_while_a_drag_hovers(qapp, tmp_path):
    from av_suite_ui.widgets import PathField
    folder = tmp_path / "clips"
    folder.mkdir()
    field = PathField()
    enter = folder_drag(folder)
    field.dragEnterEvent(enter)
    assert enter.accepted
    assert field.property("dropTarget") is True
    field.dragLeaveEvent(None)
    assert field.property("dropTarget") is False
    field.dropEvent(folder_drag(folder))
    assert field.property("dropTarget") is False     # dropped: the hover is over

    plain = DragEvent(QMimeData())                   # text, not files
    field.dragEnterEvent(plain)
    assert plain.accepted is False
    assert field.property("dropTarget") is False


def test_a_read_only_path_field_takes_no_drop(qapp, tmp_path):
    """Media Transfer locks a watched job's folders read-only: a drop must
    not change them behind the lock, nor even offer to."""
    from av_suite_ui.widgets import PathField
    folder = tmp_path / "clips"
    folder.mkdir()
    field = PathField()
    field.setText("/Volumes/Show")
    field.setReadOnly(True)
    dropped: list[str] = []
    field.path_dropped.connect(dropped.append)
    enter = folder_drag(folder)
    field.dragEnterEvent(enter)
    assert enter.accepted is False and field.property("dropTarget") is not True
    move = folder_drag(folder)
    field.dragMoveEvent(move)
    assert move.accepted is None
    drop = folder_drag(folder)
    field.dropEvent(drop)
    assert field.text() == "/Volumes/Show" and dropped == [] and drop.accepted is None


def test_path_field_history_completes_while_typing_and_shows_all_on_double_click(
        qapp, wait_until):
    """FreeFileSync's folder history, as Media Transfer has it: newest first,
    matched anywhere in the path, every one of them on a double-click."""
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest

    from av_suite_ui.widgets import PathField
    field = PathField()
    folders = ["/Volumes/Show/Day 2", "/Volumes/Show/Day 1", "/Users/me/Renders"]
    field.set_history(folders)
    assert field.history() == folders
    field.history().clear()                          # a copy, not the field's own list
    assert field.history() == folders
    completer = field.completer()
    completer.setCompletionPrefix("day")
    assert [completer.completionModel().index(r, 0).data()
            for r in range(completer.completionCount())] == folders[:2]
    field.show()
    QTest.mouseDClick(field, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
    assert wait_until(lambda: completer.popup().isVisible())
    assert completer.completionCount() == 3
    completer.popup().hide()
    field.close()


def test_without_history_a_double_click_selects_a_word_as_usual(qapp):
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest

    from av_suite_ui.widgets import PathField
    field = PathField()
    field.setText("Renders")
    field.show()
    QTest.mouseDClick(field, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
    assert field.selectedText() == "Renders"
    assert not field.completer().popup().isVisible()
    field.close()


def test_segmented_keeps_exactly_one_option_checked_and_reports_the_change(qapp):
    from av_suite_ui.widgets import Segmented
    seg = Segmented([("mirror", "Mirror", "Make the target a copy"),
                     ("update", "Update", "Copy new and newer only")])
    seen: list[str] = []
    seg.changed.connect(lambda k: seen.append(k))
    seg.set_value("mirror")
    assert seg.value() == "mirror"
    seg._buttons["update"].click()
    assert seen == ["update"]
    assert seg.value() == "update"
    assert [k for k, b in seg._buttons.items() if b.isChecked()] == ["update"]
    seg._buttons["mirror"].click()
    assert seen == ["update", "mirror"]
    assert [k for k, b in seg._buttons.items() if b.isChecked()] == ["mirror"]


def test_segmented_with_none_checked_reads_as_its_first_option_and_locks_whole(qapp):
    from av_suite_ui.widgets import Segmented
    seg = Segmented([("a", "A", ""), ("b", "B", ""), ("c", "C", "")])
    assert seg.value() == "a"
    seg.set_value("nonsense")                        # ignored, not an error
    assert seg.value() == "a"
    seg.setEnabled(False)
    assert not any(b.isEnabled() for b in seg._buttons.values())
    first, middle, last = seg._buttons.values()
    assert (first.property("first"), first.property("last")) == (True, False)
    assert (middle.property("first"), middle.property("last")) == (False, False)
    assert (last.property("first"), last.property("last")) == (False, True)
