"""The palettes, the stylesheet, and the images it has to draw from.

A drop-down is the case that needed these: its arrow went missing without a
line of Python being wrong, so the tests look at what is painted. Ported from
Media Transfer's and Annotations' test_theme.py.
"""

from __future__ import annotations

import os
import re
import sys

import pytest
from pixels import crisp, distance, ink
from PySide6.QtGui import QColor

MODES = ("dark", "light")


def image_paths(qss: str) -> list[str]:
    return re.findall(r'url\("([^"]+)"\)', qss)


def arrow_rules(qss: str) -> dict[str, str]:
    """{selector: image path} for the drop-down arrow's rules."""
    return dict(re.findall(r'(QComboBox::down-arrow[:\w]*) \{ image: url\("([^"]+)"\)', qss))


def branch_rules(qss: str) -> dict[str, str]:
    """{selector: image path} for the tree's branch indicator rules."""
    return dict(re.findall(r'(QTreeView::branch[:\w-]+) \{ image: url\("([^"]+)"\)', qss))


# ── Palette and accent ──────────────────────────────────────────────────────

def test_the_default_accent_is_tally_amber_and_round_trips_exactly(qapp):
    """The hand-tuned shade families are Smart Preview's; the default must
    reproduce them byte for byte, not through the hue arithmetic."""
    from av_suite_ui import theme
    dark, light = theme.palette("dark"), theme.palette("light")
    assert dark["accent"] == theme.DARK_DEFAULT_ACCENT == "#f0a040"
    assert light["accent"] == theme.LIGHT_DEFAULT_ACCENT == "#c77a1f"
    assert (dark["accent_hover"], dark["accent_pressed"], dark["accent_tint"],
            dark["accent_dim"]) == ("#e08f2e", "#c77a1f", "#4a3316", "#6b4a1f")
    assert (light["accent_hover"], light["accent_pressed"], light["accent_tint"],
            light["accent_dim"]) == ("#a8651a", "#8a5215", "#fdf0dc", "#e8b87a")
    assert theme.palette("dark", "#F0A040") == dark       # any spelling of the default
    assert theme.palette("dark", "not a colour") == dark  # an invalid one falls back


def test_an_unknown_mode_is_dark(qapp):
    from av_suite_ui import theme
    assert theme.palette("sepia") == theme.palette("dark")


def test_another_accent_shifts_the_whole_family_by_its_hue(qapp):
    from av_suite_ui import theme
    pal = theme.palette("dark", "#3fa0f0")                 # a blue
    assert pal["accent"] == "#3fa0f0"
    for role in ("accent_hover", "accent_pressed", "accent_tint", "accent_dim"):
        hue = QColor(pal[role]).hueF()
        assert abs(hue - QColor("#3fa0f0").hueF()) < 0.03, role
    # Everything that is not the accent is untouched by it.
    base = theme.palette("dark")
    for role in ("bg_base", "text_primary", "ok", "warn", "error"):
        assert pal[role] == base[role]


@pytest.mark.parametrize("accent, ink_colour", [
    ("#f0a040", "#121416"),         # white on amber is ~2.2:1
    ("#c77a1f", "#121416"),
    ("#1d4ed8", "#ffffff"),
    ("#ffffff", "#121416"),
])
def test_text_on_the_accent_is_whichever_contrasts_more(qapp, accent, ink_colour):
    from av_suite_ui import theme
    assert theme.on_colour(accent) == ink_colour
    assert theme.palette("dark", accent)["on_accent"] == ink_colour


# ── The built sheet ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("mode", MODES)
def test_stylesheet_fills_every_token_and_names_only_images_that_exist(qapp, mode, icons):
    from av_suite_ui import theme
    qss = theme.build_stylesheet(mode, icon_dir=icons)
    assert not re.search(r"@[a-z_]+@", qss)
    paths = image_paths(qss)
    assert len(paths) >= 6                       # two ticks, three arrows, a branch
    for path in paths:
        assert path.startswith(icons.replace("\\", "/")), path
        assert os.path.isfile(path), path
        with open(path, encoding="utf-8") as f:
            assert f.read().startswith("<svg"), path


def test_without_an_icon_dir_the_images_go_to_a_per_user_temp_folder(qapp):
    import tempfile

    from av_suite_ui import theme
    for path in image_paths(theme.build_stylesheet("dark")):
        assert path.startswith(tempfile.gettempdir().replace("\\", "/")), path
        assert "av-suite-ui-icons-" in path and os.path.isfile(path)


def test_an_icon_dir_may_be_a_callable_and_is_asked_each_build(qapp, tmp_path):
    from av_suite_ui import theme
    asked = []

    def icon_dir():
        asked.append(1)
        return str(tmp_path / "late")
    qss = theme.build_stylesheet("dark", icon_dir=icon_dir)
    assert asked and all(p.startswith(str(tmp_path / "late")) for p in image_paths(qss))


@pytest.mark.parametrize("mode", MODES)
def test_an_app_sheet_is_appended_after_the_shared_one_and_filled_alike(qapp, mode, icons):
    from av_suite_ui import theme
    app_qss = "QLabel#appOnly { color: @accent@; background: rgba(@warn_rgb@, 0.1); }"
    qss = theme.build_stylesheet(mode, extra=app_qss, icon_dir=icons)
    pal = theme.palette(mode)
    shared = theme.build_stylesheet(mode, icon_dir=icons)
    assert qss.startswith(shared)
    assert qss.rstrip().endswith(
        f"QLabel#appOnly {{ color: {pal['accent']}; "
        f"background: rgba({QColor(pal['warn']).red()}, {QColor(pal['warn']).green()}, "
        f"{QColor(pal['warn']).blue()}, 0.1); }}")


def test_several_app_sheets_keep_their_order(qapp, icons):
    from av_suite_ui import theme
    qss = theme.build_stylesheet("dark", extra=["QLabel#a { }", "QLabel#b { }"], icon_dir=icons)
    assert qss.index("QLabel#a") < qss.index("QLabel#b")


def test_an_app_rule_overrides_a_shared_rule_of_the_same_weight(qapp, icons):
    """What appending is for: an app restyles a control without editing the
    package. Painted, not just present in the text."""
    from PySide6.QtWidgets import QPushButton

    from av_suite_ui import theme
    button = QPushButton("Go")
    button.setStyleSheet(theme.build_stylesheet(
        "dark", extra="QPushButton { background-color: #ff00ff; }", icon_dir=icons))
    button.resize(80, 30)
    button.show()
    qapp.processEvents()
    assert distance(button.grab().toImage().pixelColor(6, 6), QColor("#ff00ff")) <= 2
    button.close()


def test_a_typo_in_an_app_sheet_names_the_sheet_and_the_token(qapp, icons):
    from av_suite_ui import theme
    with pytest.raises(KeyError, match=r"app stylesheet #2 uses unknown token @acent@"):
        theme.build_stylesheet("dark", extra=["", "QLabel { color: @acent@; }"],
                               icon_dir=icons)


def test_the_shared_template_is_package_data(qapp):
    """Read through importlib.resources, which a frozen app serves too."""
    from av_suite_ui import theme
    template = theme.shared_template()
    assert template.startswith("/* AV Suite shared stylesheet template")
    assert "@accent@" in template


def test_read_template_reads_an_apps_own_file(qapp):
    from av_suite_ui import theme
    assert theme.read_template("av_suite_ui", "styles.qss") == theme.shared_template()


def test_the_closed_branch_image_answers_to_both_apps_token_names(qapp, icons):
    """Media Transfer calls it branch_icon, Annotations arrow_right_icon: the
    same drawing, so both names fill from the one file."""
    from av_suite_ui import theme
    values = theme.tokens("dark", icon_dir=icons)
    assert values["arrow_right_icon"] == values["branch_icon"]


# ── Drop-downs ──────────────────────────────────────────────────────────────

@pytest.fixture
def fields(qapp, request, icons):
    """A drop-down, a locked drop-down and a text field, drawn in each theme.
    Returns (palette, drop-down, locked drop-down, text field)."""
    from PySide6.QtWidgets import QComboBox, QLineEdit, QVBoxLayout, QWidget

    from av_suite_ui import theme
    mode = request.param
    box = QWidget()
    box.setStyleSheet(theme.build_stylesheet(mode, icon_dir=icons))
    lay = QVBoxLayout(box)
    combo, locked, text = QComboBox(), QComboBox(), QLineEdit("Select group…")
    for c in (combo, locked):
        c.addItems(["Select group…", "All servers  (4)"])
    locked.setEnabled(False)
    for w in (combo, locked, text):
        w.setFixedWidth(200)
        crisp(w)
        lay.addWidget(w)
    box.show()
    qapp.processEvents()
    yield theme.palette(mode), combo, locked, text
    box.close()


@pytest.mark.parametrize("mode", MODES)
def test_drop_down_arrow_is_an_image_in_the_text_colours(qapp, mode, icons):
    """Styling QComboBox::drop-down takes Qt's own arrow away. In Media
    Transfer up to 0.1.4 nothing replaced it, and every drop-down looked like
    a text field."""
    from av_suite_ui import theme
    pal = theme.palette(mode)
    rules = arrow_rules(theme.build_stylesheet(mode, icon_dir=icons))
    assert set(rules) == {"QComboBox::down-arrow", "QComboBox::down-arrow:disabled"}
    with open(rules["QComboBox::down-arrow"], encoding="utf-8") as f:
        assert f'stroke="{pal["text_secondary"]}"' in f.read()
    with open(rules["QComboBox::down-arrow:disabled"], encoding="utf-8") as f:
        assert f'stroke="{pal["text_muted"]}"' in f.read()


@pytest.mark.parametrize("fields", MODES, indirect=True)
def test_a_drop_down_is_painted_with_an_arrow_and_a_text_field_is_not(fields):
    pal, combo, locked, text = fields
    right = range(combo.width() - 18, combo.width() - 3)     # the drop-down's 20 px
    pixels, colour = ink(combo, right.start, right.stop, pal["bg_sunken"])
    assert pixels >= 12, "no arrow is painted"
    assert distance(colour, QColor(pal["text_secondary"])) <= 16
    # What tells the two apart: the same place on a text field is empty.
    assert ink(text, right.start, right.stop, pal["bg_sunken"]) == (0, None)


@pytest.mark.parametrize("fields", MODES, indirect=True)
def test_a_locked_drop_down_looks_locked(fields):
    """A drop-down locked while something runs goes to the muted colour, text
    and arrow both, as on a disabled button — and stays visible."""
    pal, combo, locked, text = fields
    muted, width = QColor(pal["text_muted"]), locked.width()
    arrow_pixels, arrow = ink(locked, width - 18, width - 3, pal["bg_sunken"])
    assert arrow_pixels >= 12 and distance(arrow, muted) <= 16
    _, words = ink(locked, 8, 120, pal["bg_sunken"])
    assert distance(words, muted) <= 16
    _, live_words = ink(combo, 8, 120, pal["bg_sunken"])
    assert distance(live_words, QColor(pal["text_primary"])) <= 16


def test_the_arrow_follows_the_theme(qapp, icons):
    from av_suite_ui import theme
    dark = arrow_rules(theme.build_stylesheet("dark", icon_dir=icons))
    light = arrow_rules(theme.build_stylesheet("light", icon_dir=icons))
    assert dark["QComboBox::down-arrow"] != light["QComboBox::down-arrow"]
    assert dark["QComboBox::down-arrow:disabled"] != light["QComboBox::down-arrow:disabled"]


# ── Buttons ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("mode", MODES)
def test_a_button_that_is_on_is_painted_on_and_locked_when_locked(qapp, mode, icons):
    """Media Transfer's Route by type is a checkable button. The stylesheet
    had no rule for a checked one: Qt's own states would have painted it like
    any other button. Sampled inside the border — fill, not text — so the
    no-fonts Windows runner sees the same."""
    from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

    from av_suite_ui import theme
    pal = theme.palette(mode)
    box = QWidget()
    box.setStyleSheet(theme.build_stylesheet(mode, icon_dir=icons))
    lay = QHBoxLayout(box)
    off, on, locked = (QPushButton("Route by type") for _ in range(3))
    for b, checked, enabled in ((off, False, True), (on, True, True), (locked, True, False)):
        b.setCheckable(True)
        b.setChecked(checked)
        b.setEnabled(enabled)
        lay.addWidget(b)
    box.show()
    qapp.processEvents()

    def fill(button):
        return button.grab().toImage().pixelColor(6, 6)

    def border(button):
        return button.grab().toImage().pixelColor(0, button.height() // 2)

    assert distance(fill(off), QColor(pal["bg_elevated"])) <= 2
    assert distance(fill(on), QColor(pal["accent_tint"])) <= 2, "on: tinted with the accent"
    assert distance(fill(locked), QColor(pal["bg_raised"])) <= 2, "locked: the disabled fill"
    assert distance(border(locked), QColor(pal["accent_dim"])) <= 2, "locked: still marked on"
    assert distance(fill(on), fill(off)) > 25
    box.close()


@pytest.mark.parametrize("mode", MODES)
def test_the_primary_button_is_filled_with_the_accent(qapp, mode, icons):
    from PySide6.QtWidgets import QPushButton

    from av_suite_ui import theme
    pal = theme.palette(mode)
    button = QPushButton("Sync")
    button.setObjectName("primary")
    button.setStyleSheet(theme.build_stylesheet(mode, icon_dir=icons))
    button.resize(100, 30)
    button.show()
    qapp.processEvents()
    assert distance(button.grab().toImage().pixelColor(6, 6), QColor(pal["accent"])) <= 2
    button.close()


# ── Trees ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("mode", MODES)
def test_tree_branch_chevrons_are_images_in_the_text_colour(qapp, mode, icons):
    """Qt's own expand/collapse indicator draws from the palette and was
    invisible on Annotations' themed tree; the macOS style's triangles go
    once a tree is styled. The closed and open states draw explicit arrows."""
    from av_suite_ui import theme
    pal = theme.palette(mode)
    rules = branch_rules(theme.build_stylesheet(mode, icon_dir=icons))
    closed = rules["QTreeView::branch:has-children:closed"]
    opened = rules["QTreeView::branch:has-children:open"]
    assert closed != opened              # the two states must be told apart
    for path in (closed, opened):
        with open(path, encoding="utf-8") as f:
            assert f'stroke="{pal["text_secondary"]}"' in f.read()


@pytest.mark.parametrize("mode", MODES)
def test_a_parent_row_paints_a_chevron_and_a_leaf_row_paints_none(qapp, mode, icons):
    """What is actually painted: ink in the branch strip of an expandable
    row — collapsed and expanded — and none beside a leaf."""
    from PySide6.QtGui import QStandardItem, QStandardItemModel
    from PySide6.QtWidgets import QTreeView

    from av_suite_ui import theme
    tree = QTreeView()
    tree.setStyleSheet(theme.build_stylesheet(mode, icon_dir=icons))
    tree.setHeaderHidden(True)
    tree.setIndentation(14)
    tree.setUniformRowHeights(True)
    model = QStandardItemModel()
    parent, leaf = QStandardItem("Alpha"), QStandardItem("Beta")
    parent.appendRow(QStandardItem("Gamma"))
    model.appendRow(parent)
    model.appendRow(leaf)
    tree.setModel(model)
    tree.setFixedSize(200, 120)
    tree.show()
    qapp.processEvents()
    pal = theme.palette(mode)
    secondary = QColor(pal["text_secondary"])
    row = tree.visualRect(model.index(0, 0)).height()
    top = tree.viewport().mapTo(tree, tree.visualRect(model.index(0, 0)).topLeft()).y()

    def strip(r):            # the 14 px branch strip of row r, inside the row
        y0 = top + r * row
        return ink(tree, 1, 15, pal["bg_sunken"], y0 + 2, y0 + row - 2)

    pixels, colour = strip(0)
    assert pixels >= 8, "no chevron on a collapsed parent row"
    assert distance(colour, secondary) <= 16
    assert strip(1) == (0, None), "a leaf row must not pretend to expand"
    tree.expand(model.index(0, 0))
    qapp.processEvents()
    pixels, colour = strip(0)
    assert pixels >= 8, "no chevron on an expanded parent row"
    assert distance(colour, secondary) <= 16
    tree.close()


# ── Icon files ──────────────────────────────────────────────────────────────

def test_an_icon_whose_drawing_changed_is_written_again(qapp, icons):
    """The file is named after its colours, so a new shape under an old name
    would otherwise never replace the file an older version left behind."""
    from av_suite_ui import theme
    path = theme._icon_file("probe_for_the_test.svg", "<svg>first shape</svg>", icons)
    with open(path, encoding="utf-8") as f:
        assert f.read() == "<svg>first shape</svg>"
    assert theme._icon_file("probe_for_the_test.svg", "<svg>second shape</svg>", icons) == path
    with open(path, encoding="utf-8") as f:
        assert f.read() == "<svg>second shape</svg>"
    stamp = os.stat(path).st_mtime_ns
    theme._icon_file("probe_for_the_test.svg", "<svg>second shape</svg>", icons)
    assert os.stat(path).st_mtime_ns == stamp           # unchanged: not rewritten


@pytest.mark.skipif(sys.platform == "win32",
                    reason="Windows ignores a folder's read-only bit, so chmod cannot lock it")
def test_an_unwritable_icon_dir_falls_back_instead_of_killing_launch(
        qapp, tmp_path, monkeypatch):
    """build_stylesheet runs before an app's own degraded handling: in
    Annotations a read-only data dir raised PermissionError out of _icon_file
    and the app died with no window, no dialog and no log. The icons fall
    back to a per-user temp folder instead."""
    from av_suite_ui import theme
    ro = tmp_path / "ro"
    ro.mkdir()
    fallback = tmp_path / "tempdir"
    fallback.mkdir()
    monkeypatch.setattr(theme.tempfile, "gettempdir", lambda: str(fallback))
    ro.chmod(0o555)
    try:
        qss = theme.build_stylesheet("dark", icon_dir=str(ro / "icons"))
    finally:
        ro.chmod(0o755)
    paths = image_paths(qss)
    assert len(paths) >= 6
    for path in paths:
        assert path.startswith(str(fallback)), path
        assert os.path.isfile(path), path


def test_a_data_dir_that_cannot_be_made_falls_back_too(qapp, tmp_path, monkeypatch):
    """The callable form: an app's data_directory() that raises OSError (it
    could not create the folder) must land in the same fallback."""
    from av_suite_ui import theme
    fallback = tmp_path / "tempdir"
    monkeypatch.setattr(theme.tempfile, "gettempdir", lambda: str(fallback))

    def no_data_dir():
        raise PermissionError("read-only volume")
    for path in image_paths(theme.build_stylesheet("dark", icon_dir=no_data_dir)):
        assert path.startswith(str(fallback)) and os.path.isfile(path), path


@pytest.mark.skipif(sys.platform == "win32",
                    reason="Windows ignores a folder's read-only bit, so chmod cannot lock it")
def test_an_icon_that_cannot_be_written_anywhere_still_returns_a_path(tmp_path, monkeypatch):
    """If even the temp fallback is unwritable, _icon_file logs and returns
    the intended path anyway: QSS draws no image there, which is cosmetic —
    a dead app is not."""
    from av_suite_ui import theme
    ro = tmp_path / "ro"
    ro.mkdir()
    monkeypatch.setattr(theme.tempfile, "gettempdir", lambda: str(ro))
    ro.chmod(0o555)
    try:
        path = theme._icon_file("probe_unwritable.svg", "<svg>x</svg>", str(ro / "icons"))
    finally:
        ro.chmod(0o755)
    assert path.endswith("probe_unwritable.svg")
