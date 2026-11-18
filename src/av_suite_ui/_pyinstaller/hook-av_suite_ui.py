"""Collect the stylesheet template: theme.py reads styles.qss through
importlib.resources, so a frozen app without it opens unstyled."""

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("av_suite_ui", includes=["*.qss"])
