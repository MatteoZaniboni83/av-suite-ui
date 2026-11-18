"""PyInstaller support: the hook directory, announced by the pyinstaller40
entry point in pyproject.toml."""

import os


def get_hook_dirs() -> list[str]:
    return [os.path.dirname(__file__)]
