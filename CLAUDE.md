# av-suite-ui

One shared Python package, `av_suite_ui`, holding the UI foundation of the
**AV Suite** apps: Media Transfer, Annotations, Smart Preview, and the apps
still to come. It contains the Tally theme (palettes, accent derivation, one
`@token@` stylesheet template) and the small widgets every screen is built
from. The point is to change the UI in one place, tag a release and bump
each app's pin.

| | av-suite-ui |
| --- | --- |
| Distribution | `av-suite-ui` |
| Package | `av_suite_ui` |
| Repo (planned) | `MatteoZaniboni83/av-suite-ui`, **public**, not created yet |
| Apps pin it as | `av-suite-ui @ git+https://github.com/MatteoZaniboni83/av-suite-ui.git@<full SHA>  # vX.Y.Z` |

"AV Suite", `avsuite` and `av-suite` stay free for the hub (Media Transfer's
CLAUDE.md, "The name"). This repo is `av-suite-ui`.

The sibling apps `../media-transfer/`, `../annotations/` and
`../smart-preview/` are **read-only from here**. Never edit them in a session
of this repo. Each app adopts a new version in its own session, in its own
repo. Media Transfer is the reference for the suite's conventions; its
CLAUDE.md lists the rules born of bugs that shaped this code.

## Structure

```
src/av_suite_ui/
├── __init__.py            # __version__ (one of the two version spots)
├── theme.py               # palettes, accent derivation, tokens, fill, build_stylesheet
├── styles.qss             # the shared template: tokens between @ signs
├── widgets.py             # restyle, shortcut_text, section_label, mono_font, hairline,
│                          #   ElidedLabel, PathField, Segmented
├── gallery.py             # python -m av_suite_ui.gallery: everything, dark and light
└── _pyinstaller/          # hook-av_suite_ui.py collects styles.qss (pyinstaller40 entry point)
tests/
├── golden/                # each app's stylesheet as built before the switch, + its own sheet;
│                          #   capture.py recaptures one (run with that app's venv)
├── test_golden.py         # shared + app sheet == what the app built, + RESTYLES (MT exact, Ann. listed)
.github/workflows/ci.yml   # Linux: ruff + suite, offscreen and no-fonts, Python 3.12 and 3.14
├── test_theme.py          # palette, tokens, icons, pixel checks (ported from both apps)
├── test_widgets.py, test_gallery.py, test_packaging.py
└── pixels.py              # distance / ink / crisp helpers for pixel tests
```

## Commands

```bash
./.venv/bin/python -m pytest -q                    # test (offscreen; pythonpath set in pyproject)
./.venv/bin/python -m ruff check src tests         # lint (config in pyproject)
./.venv/bin/python -m av_suite_ui.gallery          # look at it
QT_STYLE_OVERRIDE=macOS ./.venv/bin/python -m pytest -q   # the macOS style
QT_QPA_PLATFORM=minimal ./.venv/bin/python -m pytest -q   # no fonts, as the Windows runner
```

The venv is Python 3.14 and has the package installed editable
(`pip install -r requirements-dev.txt -e .`). The editable install registers
the `pyinstaller40` entry point, which `test_packaging` needs. Invoke tools as
modules.

## Rules that exist for a reason

The suite-wide rules are inherited from Media Transfer: px fonts, uppercase
in code, status colours mean state only, ⚠ plus words and never colour alone,
an image for every styled indicator or arrow, and the shortcut constants that
feed both QShortcut and tooltips through `shortcut_text()`. The rules this
package adds:

- **The golden test is the contract.** `tests/golden/` holds Media
  Transfer's (8b4f22c) and Annotations' (1a06a1b) own `build_stylesheet()`
  output, default accent, both modes, icon folder as `@ICON_DIR@`. For Media
  Transfer, shared + `media_transfer_app.qss` must be the same rules in the
  same order once the app's rules are moved to the end, and the move must
  change nothing in the cascade (`cascade_conflicts`). Any change to
  `styles.qss` or the palette fails it **on purpose**. The golden files stay
  what the apps built: recapture one (`capture.py`) only when the app's own
  output is the new reference. A deliberate restyle here is listed instead
  in `RESTYLES` in `test_golden.py`, value by value (hex and `r, g, b`),
  under the release that makes it, and said so in the commit and the tag's
  notes. `test_each_restyle_is_still_real` rejects a stale entry. Never edit
  the golden files by hand to make a test pass.
- **Rule of two.** A widget, helper or QSS rule lives here only when at
  least two apps use it. Media Transfer's `open_in_smart_preview`,
  `PickOneDialog`, its generic `QPlainTextEdit`, `QLineEdit#number` and the
  folder-pair rows stay in that app. So do all of Annotations' page,
  database and block rules. `format_size` is in both apps, but in Media
  Transfer it is an engine helper and its engines are Qt-free, so it has
  not moved (open question in HANDOFF).
- **An app restyles by appending, never by editing this package.**
  `build_stylesheet(extra=...)` fills the app's template from the same
  tokens and appends it, so an app rule of equal weight wins. An unknown
  token raises `KeyError` naming the sheet, because a typo must not ship as
  a literal `@token@` that Qt ignores.
- **Token names are an API.** Apps' own sheets name them. Renaming or
  removing one is a breaking change, so keep the old name as an alias, as
  `arrow_right_icon` (Annotations' name) is for `branch_icon` (Media
  Transfer's name for the same drawing).
- **No app imports.** The package knows nothing of any app's data dir. The
  app passes `icon_dir` (a path, or a callable so that a data dir that
  cannot be created raises *inside* `_icon_file` and falls back). Without
  one, images go to `<tmp>/av-suite-ui-icons-<uid>`.
- **Degraded mode must be reachable** (Annotations' rule): anything on the
  path to the first stylesheet falls back and logs instead of raising.
  An unwritable icon folder means a per-user temp folder, and if even that
  fails the path is returned anyway, because a missing image is cosmetic and
  a dead app is not.
- **Package data is read through `importlib.resources`**, never a path
  beside `__file__`, and the PyInstaller hook collects `*.qss`. A frozen
  build made on 2026-11-18 from the wheel, with no `datas` line, found the
  sheet (HANDOFF). A new data file type needs `package-data` in
  pyproject.toml **and** the hook's `includes`.
- **The gallery shows everything the shared sheet styles.**
  `test_gallery` fails when `styles.qss` gains an object name or dynamic
  state that no gallery widget carries, so a new rule is seen in the gallery
  before it reaches an app.
- **deleteLater waits for an event-loop pass**: a widget replaced in a
  visible layout is hidden and unparented at once (the gallery's swatches,
  after Annotations' view-tabs lesson).

## Design

- The default accent is Tally amber, `#f0a040` dark and `#c77a1f` light, with
  Smart Preview's hand-tuned shade families. The default round-trips exactly
  and is never computed. Another accent shifts each shade by the hue change.
- **The warning is yellow, not amber** (0.2.0, the user's choice):
  `#f1c40f` dark, `#705700` light. The apps' old `#f39c12` / `#d97706` read
  as the amber accent. `test_theme` holds the warning 12°+ of hue from the
  default accent and its note text at 4.5:1 or better on every surface (on
  the note's own 10% tint, not the bare surface). A new status colour gets
  the same two checks. Warnings still carry ⚠ and words.
- Qt stylesheets ignore `text-transform`: uppercase in code
  (`section_label`).

## Testing conventions

Media Transfer's conventions apply. `conftest.py` sets `QT_QPA_PLATFORM=offscreen`
(setdefault, so `minimal` can override it) and points `tempfile.tempdir` at a
throwaway folder, so the icon fallback never writes to the user's temp
folder. Tests pass `icon_dir` from the `icons` fixture. Spin the event loop
(`wait_until`) and never `time.sleep`. Look at what is painted
(`pixels.ink`, `distance`), and sample fills inside borders so the no-fonts
Windows runner sees the same. For UI changes, take real screenshots with
the gallery (`--screenshot`) and look at them in the macOS style too.

## Git and releases

- **No remote yet.** Do not create the GitHub repo or push until the user
  says so. The commit identity is in this repo's own config:
  MatteoZaniboni83 with the GitHub **noreply** address
  (`148096572+MatteoZaniboni83@users.noreply.github.com`), because the repo
  is public. The private app repos use the personal address; never copy
  their identity here. The global git config has none.
  When the remote exists, push with
  `git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push`.
- **No `Co-Authored-By` trailer** in commit messages: the user's convention
  across the suite.
- Small commits, one step each.
- **Version: two spots**, `__version__` in `src/av_suite_ui/__init__.py` and
  `version` in `pyproject.toml`. `test_packaging` fails if they differ.
- A release is a tag `vX.Y.Z` on `main` once the suite and ruff are green
  (and CI, once there is a remote). Nothing is built or uploaded, because
  apps install from git. **Apps pin the tag's full commit SHA**
  (`git rev-parse vX.Y.Z^{commit}`) with the tag in a comment, because a
  tag can be moved and a SHA cannot: no surprise upgrades. So never move or
  delete a pushed tag; fix forward with a new version. Then each app bumps
  its pin in its own repo and session, runs its own suite and looks at its
  screens. A change that alters the look (a `RESTYLES` entry)
  is said so in the tag's notes, so each app knows to look before
  bumping.
- **The repo is public** (the user's choice, 2026-11-18), so apps' CI
  installs it with no credential. Nothing secret goes in it: no data, no
  paths from the user's machine, no tokens.
- **CI** (`.github/workflows/ci.yml`) runs on Linux only, as the apps' CI
  does: ruff, then the suite offscreen and with `QT_QPA_PLATFORM=minimal`,
  on Python 3.12 (the floor in pyproject.toml) and 3.14 (what the apps
  ship). Markdown-only pushes skip it. When the floor or the apps' Python
  changes, change the matrix with it.
- Dependencies are pinned in `requirements.txt` / `requirements-dev.txt` to
  the apps' versions. `pyproject.toml` has only the minimum
  (`PySide6>=6.8`), because the apps' pins decide the Qt they ship.

## Session handoff

Read `HANDOFF.md` at the start of every session.
