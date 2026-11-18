"""The gallery shows everything the package styles, in both modes."""

from __future__ import annotations

import re

import pytest
from PySide6.QtWidgets import QWidget


@pytest.fixture
def gallery(qapp, icons):
    from av_suite_ui.gallery import Gallery
    window = Gallery(icon_dir=icons)
    window.show()
    qapp.processEvents()
    yield window
    window.close()


def test_one_panel_per_mode_each_with_its_own_sheet(gallery, icons):
    from av_suite_ui import theme
    assert [p.mode for p in gallery.panels] == list(theme.MODES)
    for panel in gallery.panels:
        assert panel.styleSheet() == theme.build_stylesheet(panel.mode, icon_dir=icons)


def test_every_object_name_the_shared_sheet_styles_is_on_show(gallery):
    """A selector added to styles.qss without a widget in the gallery would
    change the apps where nobody looks first."""
    from av_suite_ui import theme
    names = set(re.findall(r"#(\w+)", re.sub(r"/\*.*?\*/", "", theme.shared_template(),
                                               flags=re.S)))
    assert names                                   # the regex found the selectors
    for panel in gallery.panels:
        shown = {w.objectName() for w in panel.findChildren(QWidget)}
        assert names <= shown, sorted(names - shown)


def test_every_dynamic_state_the_sheet_knows_is_on_show(gallery):
    for panel in gallery.panels:
        widgets = panel.findChildren(QWidget)
        assert {w.property("state") for w in widgets} >= {"done", "failed"}
        assert any(w.property("dropTarget") is True for w in widgets)
        assert any(w.property("first") is True for w in widgets)
        assert any(w.property("last") is True for w in widgets)


def test_every_shared_widget_is_on_show(gallery):
    from av_suite_ui.widgets import ElidedLabel, PathField, Segmented
    for panel in gallery.panels:
        for cls in (ElidedLabel, PathField, Segmented):
            assert panel.findChildren(cls), cls.__name__
        assert any(w.objectName() == "hairline" for w in panel.findChildren(QWidget))
        assert any(w.objectName() == "sectionLabel" for w in panel.findChildren(QWidget))


def test_another_accent_restyles_both_sides_and_their_swatches(gallery, icons):
    from av_suite_ui import theme
    gallery.set_accent("#3fa0f0")
    for panel in gallery.panels:
        assert panel.styleSheet() == theme.build_stylesheet(panel.mode, "#3fa0f0",
                                                            icon_dir=icons)
        swatch = panel.findChild(QWidget, "swatch_accent")
        assert "#3fa0f0" in swatch.text()
    gallery.set_accent(None)
    assert "#f0a040" in gallery.panels[0].findChild(QWidget, "swatch_accent").text()


def test_the_command_line_saves_a_screenshot(qapp, tmp_path):
    from PySide6.QtGui import QImage

    from av_suite_ui import gallery
    out = tmp_path / "gallery.png"
    assert gallery.main(["--screenshot", str(out), "--accent", "#3fa0f0"]) == 0
    image = QImage(str(out))
    assert not image.isNull() and image.width() > 1000
    for w in qapp.topLevelWidgets():
        if isinstance(w, gallery.Gallery):
            w.close()
