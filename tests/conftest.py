"""Shared fixtures. Qt runs headless, and every icon the theme writes lands in
throwaway folders, never the user's own temp or data folders."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# build_stylesheet() without an icon_dir writes to a per-user folder under the
# system temp dir: point that at a folder of the test run's own.
import tempfile  # noqa: E402

tempfile.tempdir = tempfile.mkdtemp(prefix="av-suite-ui-tests-")

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from av_suite_ui import theme
    app.setStyleSheet(theme.build_stylesheet("dark"))
    return app


@pytest.fixture
def icons(tmp_path) -> str:
    """An app's icon folder, as Media Transfer's <data dir>/icons."""
    return str(tmp_path / "icons")


@pytest.fixture
def spin(qapp):
    from PySide6.QtCore import QEventLoop, QTimer

    def _spin(ms: int):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()
    return _spin


@pytest.fixture
def wait_until(spin):
    """Spin the event loop until *predicate* holds; sleep() would block the
    queued events Qt delivers results through."""
    def _wait(predicate, timeout_ms: int = 10000) -> bool:
        waited = 0
        while waited < timeout_ms:
            if predicate():
                return True
            spin(25)
            waited += 25
        return predicate()
    return _wait
