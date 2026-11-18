"""What an app needs from the package at build time: one version, the
stylesheet inside the wheel, and a PyInstaller hook that collects it."""

from __future__ import annotations

import os
import re
import tomllib
from importlib.metadata import entry_points
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_version_is_the_same_in_both_spots():
    """__init__.py and pyproject.toml, as in the apps: bump both, nothing else."""
    import av_suite_ui
    with open(ROOT / "pyproject.toml", "rb") as f:
        project = tomllib.load(f)["project"]
    assert project["version"] == av_suite_ui.__version__
    assert re.fullmatch(r"\d+\.\d+\.\d+", av_suite_ui.__version__)


def test_the_stylesheet_is_declared_package_data():
    with open(ROOT / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)["tool"]["setuptools"]["package-data"]["av_suite_ui"]
    assert "*.qss" in data


def test_the_pyinstaller_hook_is_announced_and_collects_the_stylesheet():
    """PyInstaller finds hook directories through the pyinstaller40 entry
    point (the package must be installed, as an app installs it from its
    pin). The hook must hand over styles.qss to land at av_suite_ui/."""
    from PyInstaller.utils.hooks import collect_data_files

    hooks = [ep for ep in entry_points(group="pyinstaller40") if ep.value.startswith("av_suite_ui")]
    assert [ep.name for ep in hooks] == ["hook-dirs"]
    (hook_dir,) = hooks[0].load()()
    assert os.path.isfile(os.path.join(hook_dir, "hook-av_suite_ui.py"))
    datas = collect_data_files("av_suite_ui", includes=["*.qss"])
    assert [(os.path.basename(src), dest) for src, dest in datas] == [
        ("styles.qss", "av_suite_ui")]
    with open(os.path.join(hook_dir, "hook-av_suite_ui.py"), encoding="utf-8") as f:
        assert 'collect_data_files("av_suite_ui", includes=["*.qss"])' in f.read()
