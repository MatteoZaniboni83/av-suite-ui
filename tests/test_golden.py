"""The shared sheet is what the apps built before they switched.

tests/golden/ holds each app's own build_stylesheet() output with the default
accent, captured from its repo (Media Transfer 8b4f22c, Annotations 1a06a1b)
with the icon folder written as @ICON_DIR@, and each app's own sheet: the
rules only that app uses, which it appends with build_stylesheet(extra=...).

Media Transfer: shared + its sheet has the very same rules, in the same order
once the app's rules are moved to the end — and the move cannot change what
any widget gets (cascade_conflicts). So switching is no visual change.

Annotations: its old sheet had none of Media Transfer's tree rules and no
generic checked button; shared + its sheet adds exactly those (listed below)
and loses nothing. Its page tree and its checkable tab are painted the same.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path

import pytest

GOLDEN = Path(__file__).parent / "golden"
MODES = ("dark", "light")


# ── A small QSS reader ──────────────────────────────────────────────────────

def rules(qss: str) -> list[tuple[str, str]]:
    """(selector, declarations) per selector, in order: comments dropped,
    whitespace collapsed, a selector group split into one rule per selector
    (the group's order kept)."""
    qss = re.sub(r"/\*.*?\*/", "", qss, flags=re.S)
    out = []
    for group, body in re.findall(r"([^{}]+)\{([^{}]*)\}", qss):
        body = " ".join(body.split())
        for selector in group.split(","):
            out.append((" ".join(selector.split()), body))
    return out


def properties(body: str) -> set[str]:
    return {d.split(":", 1)[0].strip() for d in body.split(";") if ":" in d}


def _subject(selector: str) -> str:
    return selector.split()[-1]


def specificity(selector: str) -> tuple[int, int, int]:
    ids = len(re.findall(r"#[\w-]+", selector))
    classes = len(re.findall(r"\[[^\]]*\]", selector)) + \
        len(re.findall(r"(?<!:):(?!:)[\w-]+", selector))
    types = len(re.findall(r"(?:^|\s)[A-Z]\w*", selector)) + len(re.findall(r"::[\w-]+", selector))
    return ids, classes, types


def _parts(compound: str) -> tuple[str | None, str | None, str | None]:
    """(type, id, sub-control) of a selector's subject; None where absent."""
    typ = re.match(r"([A-Z]\w*)", compound)
    ident = re.search(r"#([\w-]+)", compound)
    sub = re.search(r"::([\w-]+)", compound)
    return (typ.group(1) if typ else None, ident.group(1) if ident else None,
            sub.group(1) if sub else None)


def may_meet(a: str, b: str) -> bool:
    """Could selectors *a* and *b* style the same thing? Conservative: only
    a different ID, a different sub-control or two unrelated named classes
    rule it out (QWidget, or no type, may be anything)."""
    (ta, ia, sa), (tb, ib, sb) = _parts(_subject(a)), _parts(_subject(b))
    if sa != sb or (ia and ib and ia != ib):
        return False
    return ta is None or tb is None or "QWidget" in (ta, tb) or ta == tb


def overlap(p: set[str], q: set[str]) -> bool:
    """Shared properties, shorthands included: border covers border-color."""
    return any(x == y or x.startswith(y + "-") or y.startswith(x + "-") for x in p for y in q)


def cascade_conflicts(original: list[tuple[str, str]], moved: set[int]) -> list[str]:
    """Moving rule i to the end changes the result only where a rule j that
    followed it — and stays put — has equal weight, may style the same thing
    and sets a property it sets: then i used to lose and now wins. (Unequal
    weights decide the same in any order.)"""
    found = []
    for i in sorted(moved):
        sel_i, body_i = original[i]
        for j in range(i + 1, len(original)):
            if j in moved:
                continue
            sel_j, body_j = original[j]
            if (specificity(sel_i) == specificity(sel_j) and may_meet(sel_i, sel_j)
                    and overlap(properties(body_i), properties(body_j))):
                found.append(f"{sel_i} now overrides {sel_j}")
    return found


def built(mode: str, app: str, icons: str) -> str:
    from av_suite_ui import theme
    extra = (GOLDEN / f"{app}_app.qss").read_text(encoding="utf-8")
    return theme.build_stylesheet(mode, extra=extra, icon_dir=icons).replace(
        icons.replace("\\", "/"), "@ICON_DIR@")


def golden(mode: str, app: str) -> str:
    return (GOLDEN / f"{app}_{mode}.qss").read_text(encoding="utf-8")


def app_rules(app: str, mode: str, icons: str) -> list[tuple[str, str]]:
    from av_suite_ui import theme
    values = {k: v.replace(icons.replace("\\", "/"), "@ICON_DIR@")
              for k, v in theme.tokens(mode, icon_dir=icons).items()}
    return rules(theme.fill((GOLDEN / f"{app}_app.qss").read_text(encoding="utf-8"), values))


# ── Media Transfer ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("mode", MODES)
def test_shared_plus_media_transfers_sheet_is_media_transfers_stylesheet(qapp, mode, icons):
    old = rules(golden(mode, "media_transfer"))
    mine = app_rules("media_transfer", mode, icons)
    moved = [i for i, r in enumerate(old) if r in mine]
    assert len(moved) == len(mine), "every rule of the app sheet came from the app"
    relocated = [r for i, r in enumerate(old) if i not in moved] + [old[i] for i in moved]
    assert rules(built(mode, "media_transfer", icons)) == relocated
    assert cascade_conflicts(old, set(moved)) == []


@pytest.mark.parametrize("mode", MODES)
def test_the_shared_sheet_alone_has_nothing_only_media_transfer_uses(qapp, mode, icons):
    from av_suite_ui import theme
    shared = theme.build_stylesheet(mode, icon_dir=icons)
    for selector in ("QPlainTextEdit", "QLineEdit#number", "pairsScroll", "pairsSplit"):
        assert selector not in shared, selector


# ── Annotations ─────────────────────────────────────────────────────────────

# What shared + Annotations' sheet has that Annotations' own sheet did not:
# Media Transfer's tree rules and the generic checked button. Annotations'
# own tree rules come later and win; its checkable buttons all have IDs.
ADDED_FOR_ANNOTATIONS = Counter([
    "QPushButton:checked", "QPushButton:checked:disabled",
    "QTreeView",                    # in the table / list rule
    "QTreeView",                    # { color }
    "QTreeView::item",
    "QTreeView::item:selected",
    "QTreeView::branch",
    "QTreeView::branch:has-children:closed",
    "QTreeView::branch:has-children:open",
])


def annotations_golden(mode: str) -> str:
    # Annotations named the closed-branch image arrow_right_*.svg; the package
    # writes the same drawing as branch_*.svg (test_theme checks the drawing).
    return golden(mode, "annotations").replace("/arrow_right_", "/branch_")


@pytest.mark.parametrize("mode", MODES)
def test_shared_plus_annotations_sheet_adds_only_the_known_rules(qapp, mode, icons):
    old = Counter(rules(annotations_golden(mode)))
    new = Counter(rules(built(mode, "annotations", icons)))
    assert old - new == Counter(), "a rule Annotations had is missing"
    assert Counter(sel for sel, _ in (new - old).elements()) == ADDED_FOR_ANNOTATIONS


@pytest.mark.parametrize("mode", MODES)
def test_annotations_rules_moved_to_its_sheet_still_win_where_they_did(qapp, mode, icons):
    old = rules(annotations_golden(mode))
    mine = set(app_rules("annotations", mode, icons))
    moved = {i for i, r in enumerate(old) if r in mine}
    assert cascade_conflicts(old, moved) == []


def _real_sheet(text: str, icons: str) -> str:
    """A golden sheet pointed at real icon files."""
    return text.replace("@ICON_DIR@", icons.replace("\\", "/"))


@pytest.mark.parametrize("mode", MODES)
def test_annotations_page_tree_and_view_tab_paint_the_same(qapp, mode, icons):
    """The added rules reach the page tree and checkable buttons: painted with
    the old sheet and the new, they are the same pixels."""
    from PySide6.QtGui import QStandardItem, QStandardItemModel
    from PySide6.QtWidgets import QPushButton, QTreeView, QVBoxLayout, QWidget

    new_sheet = _real_sheet(built(mode, "annotations", icons), icons)
    old_sheet = _real_sheet(annotations_golden(mode), icons)
    assert os.path.isdir(icons)                 # built() wrote the images

    def paint(sheet: str):
        box = QWidget()
        box.setStyleSheet(sheet)
        lay = QVBoxLayout(box)
        tree = QTreeView()
        tree.setObjectName("pageTree")
        tree.setHeaderHidden(True)
        tree.setIndentation(14)
        tree.setUniformRowHeights(True)
        model = QStandardItemModel(tree)
        parent = QStandardItem("Show notes")
        for name in ("Rehearsal", "Load-in"):
            parent.appendRow(QStandardItem(name))
        model.appendRow(parent)
        model.appendRow(QStandardItem("Inbox"))
        tree.setModel(model)
        tree.expand(model.index(0, 0))
        tree.setCurrentIndex(model.index(1, 0, model.index(0, 0)))
        tree.setFixedSize(220, 140)
        tabs = []
        for checked in (True, False):
            tab = QPushButton("All")
            tab.setObjectName("viewTab")
            tab.setCheckable(True)
            tab.setChecked(checked)
            tabs.append(tab)
            lay.addWidget(tab)
        lay.addWidget(tree)
        box.show()
        qapp.processEvents()
        images = [w.grab().toImage() for w in (tree, *tabs)]
        box.close()
        return images

    assert paint(new_sheet) == paint(old_sheet)
