# av-suite-ui

The shared UI foundation of the AV Suite apps (Media Transfer, Annotations,
Smart Preview, more to come): the Tally theme — dark and light palettes, the
accent and its derived shades, one `@token@` stylesheet template — and the
small widgets every screen is built from. Change the look here, tag a release,
bump each app's pin.

## In an app

Pin a tag in `requirements.txt` (the repo is not on GitHub yet; see HANDOFF.md):

```
av-suite-ui @ git+https://github.com/MatteoZaniboni83/av-suite-ui.git@v0.2.0
```

Keep a small `ui/theme.py` in the app that appends its own sheet:

```python
import os

from av_suite_ui import theme
from av_suite_ui.theme import palette  # noqa: F401  (re-exported for the app's screens)

from ..engines.store import data_directory

APP_QSS = theme.read_template(__package__, "app.qss")   # the app's own rules


def build_stylesheet(mode="dark", accent=None):
    return theme.build_stylesheet(
        mode, accent, extra=APP_QSS,
        icon_dir=lambda: os.path.join(data_directory(), "icons"))
```

- `theme.build_stylesheet(mode, accent, *, extra=None, icon_dir=None)` fills the
  shared template, then appends `extra` (one template string or several),
  filled from the same tokens. An app rule of the same weight overrides a
  shared one, because it comes later.
- `theme.palette(mode, accent)` gives every colour role, for widgets that
  paint colours themselves. `theme.tokens(...)` adds `<role>_rgb` and the
  image paths a template can name.
- `icon_dir` is where the SVG ticks and arrows are written (QSS cannot take
  `data:` URIs). Pass a path or a callable. If it cannot be written, the
  images go to a per-user temp folder instead of failing the launch.
- Widgets: `restyle`, `shortcut_text`, `section_label`, `mono_font`,
  `hairline`, `ElidedLabel`, `PathField`, `Segmented`.

PyInstaller: the package ships a hook (found through its `pyinstaller40` entry
point) that collects `styles.qss`. An app's spec needs no line for it, only
for its own `app.qss`.

## Gallery

```bash
./.venv/bin/python -m av_suite_ui.gallery
./.venv/bin/python -m av_suite_ui.gallery --accent "#3fa0f0"
./.venv/bin/python -m av_suite_ui.gallery --screenshot screenshots/gallery.png
```

## Develop

```bash
/opt/homebrew/bin/python3.14 -m venv .venv
./.venv/bin/python -m pip install -r requirements-dev.txt -e .
./.venv/bin/python -m pytest -q
./.venv/bin/python -m ruff check src tests
```
