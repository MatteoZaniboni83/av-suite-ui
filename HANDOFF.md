# Session handoff

Read this after CLAUDE.md at the start of every session. Newest state first.

## State as of 2026-11-18: v0.1.0 and v0.2.0 tagged locally, nothing pushed

- **Two tags, both local.** `v0.1.0` is the extraction: what the apps build
  today, proven by the golden test. `v0.2.0` adds one deliberate restyle:
  the warning is yellow (below). There is no GitHub repo and no push: the
  user creates the repo once the open decisions below are settled. 85 tests
  pass, ruff is clean, and the suite gives the same
  result in the macOS style (`QT_STYLE_OVERRIDE=macOS`) and with no fonts
  (`QT_QPA_PLATFORM=minimal`). Run both before touching anything:

  ```bash
  ./.venv/bin/python -m pytest -q && ./.venv/bin/python -m ruff check src tests
  ```

- **What it holds**, extracted from Media Transfer at 8b4f22c:
  - palettes and accent derivation (default Tally amber, dark and light,
    byte-identical);
  - the stylesheet template, minus the three rules only Media Transfer uses;
  - `restyle`, `shortcut_text`, `section_label`, `mono_font`, `hairline`,
    `ElidedLabel`, `PathField`, `Segmented`;
  - a gallery (`python -m av_suite_ui.gallery`);
  - a PyInstaller hook.
- **No app uses it yet.** The three app repos were only read, never changed.
  Media Transfer's tree was clean when its golden output was captured.

### The user's decisions (2026-11-18)

- Git identity: the same as the apps, set in this repo's config only.
- Where Media Transfer and Annotations differed, the user chose:
  - **QTreeView**: Media Transfer's table-like tree goes in the shared
    sheet. Annotations keeps its sidebar look in its own sheet, which comes
    later and wins. The closed-branch image answers to both token names
    (`branch_icon`, `arrow_right_icon`).
  - **The rules only Media Transfer has are split**: the generic
    `QPushButton:checked` / `:checked:disabled` goes in the shared sheet;
    the generic `QPlainTextEdit` and `QLineEdit#number` stay in Media
    Transfer (in the shared sheet they would have turned Annotations' block
    text monospace).
  - **All four one-sided behaviours adopted**: Annotations' icon-folder
    fallback, Annotations' ElidedLabel tooltip fix, and Media Transfer's
    PathField history and read-only drop lock.
- Everything else that differed was app-specific, so it stays in that app
  (the rule of two): Media Transfer's `open_in_smart_preview`,
  `PickOneDialog` and folder-pair rows, and Annotations' page, block and
  database rules and its `format_size`. Comment wording differed too; the
  shared comments now name both apps.

### 0.2.0: the warning is yellow (the user chose option A, 2026-11-18)

- The amber accent and the amber warning were 4° (dark) and 0° (light) of
  hue apart. The warning is now `#f1c40f` dark and `#705700` light, about
  15° from the accent.
- The light shade is darker than the `#8a6d00` first proposed. That figure
  had been measured against the bare background, but the note's text sits
  on the note's own 10% tint, where `#8a6d00` gave only 3.3–4.3:1.
  `#705700` gives 4.5–5.9:1 on all four surfaces. The old `#d97706` gave
  2.2–2.9:1.
- Only `QLabel#warnNote` uses the warning in the shared sheet. The `warn`
  role in `palette()` changes too, so anything an app paints with
  `palette()["warn"]` changes with it. Today that is Media Transfer only:
  log ERROR lines (`ui/log_page.py`) and sync-row status text
  (`ui/sync_model.py`). As plain text the new colours give 5.2:1 or better
  on every surface and on a selected (accent-tint) row, in both modes.
  Annotations paints no warning colour itself.
- The golden files are untouched. `test_golden.RESTYLES` lists the change,
  and the comparison applies it to the captured text.
- Screenshots looked at: the gallery's swatches, and warning notes on all
  four surfaces in both modes beside the primary button and an error note.
  Taken with `--screenshot` into `screenshots/`, which git ignores.

### Proof that switching to v0.1.0 changes nothing

- `tests/golden/` holds each app's own `build_stylesheet()` output, captured
  by running its code with a throwaway data dir. It also holds each app's
  own sheet, which is the file that app adopts when it switches:
  `media_transfer_app.qss` and `annotations_app.qss`.
- **Media Transfer:** shared + its sheet gives the same rules in the same
  order, once its own rules are moved to the end, and a cascade check shows
  the move changes no widget. So the switch is pixel-identical.
- **Annotations:** no rule is lost. Exactly nine rules are added (MT's tree
  rules and the generic checked button). Its page tree and view tabs paint
  the same pixels with the old and the new sheet. Its only checkable buttons
  have IDs, so the generic checked rule cannot reach them.
- Mutation checks: a 1 px padding change fails 4 golden tests, and dropping
  Annotations' tree rule fails the pixel test.

### PyInstaller, checked for real

The wheel (`pip wheel .`) contains `styles.qss`, `py.typed`, the hook and the
`pyinstaller40` entry point. A probe script was built in a fresh venv with
the wheel installed, with no `datas` line. In the frozen build,
`_internal/av_suite_ui/styles.qss` was present and an appended app sheet
filled correctly. The run printed `frozen 11793 True`.

## Waiting on the user

1. **Settled:** amber accent vs warning amber went to option A, in
   v0.2.0, above.
2. **Settled 2026-11-18:** the repo is **public**; apps **pin by full
   commit SHA** with the tag in a comment; **Linux CI** is added
   (`.github/workflows/ci.yml`: ruff, then the suite offscreen and with no
   fonts, on Python 3.12 and 3.14). 3.12 has never run locally (only 3.14
   is installed), so CI's first run is the first test of the
   `requires-python = ">=3.12"` claim.
3. **Still open before creating the GitHub repo:**
   - **The go-ahead** to create the repo and push. (The commit email is
     settled: on the user's word, before any push, every commit was
     rewritten to the GitHub noreply address, and both tags were recreated
     on the rewritten commits with their messages and dates. No object
     reachable from `main` or the tags contains the personal address. A
     bundle of the old history was kept only in the session's scratchpad.)
   - **The folder name has a space** (`av-suite ui`). An app developing
     against a local checkout (`pip install -e "../av-suite ui"`) has to
     quote the path. Renaming it to `av-suite-ui` would match the repo
     name. It is the user's folder, so it was not renamed.
4. **`format_size`** is identical in both apps. It is an engine helper in
   Media Transfer, whose engines must stay Qt-free, so it has not moved. If it
   should be shared, it would go in a Qt-free submodule (say
   `av_suite_ui.text`). That is the user's call.

## Next up (rough priority)

1. Settle the decisions above, then create the public repo and push `main`
   plus the `v0.1.0` and `v0.2.0` tags. Check the first CI run, Python 3.12
   especially.
2. **Media Transfer switches** (in its own session and repo), best in two
   commits: first pin `v0.1.0` (by its commit SHA), a pure refactor that the golden test says
   looks the same; then bump to `v0.2.0` and look at its warning notes
   (and anything it paints with `palette()["warn"]`). For the first:
   - pin the package;
   - make `ui/theme.py` a thin wrapper that calls
     `build_stylesheet(extra=APP_QSS, icon_dir=<data dir>/icons)` and
     re-exports `palette`;
   - replace `styles.qss` with `tests/golden/media_transfer_app.qss`;
   - import the eight helpers from `av_suite_ui.widgets`;
   - change the spec's `datas` to the app sheet;
   - check that its own test_theme still passes.

3. **Annotations switches** the same way, with `annotations_app.qss`, and
   the same two steps. The
   closed-branch image file becomes `branch_*.svg` (the same drawing as
   `arrow_right_*.svg`); its own tests check by selector, not file name.
4. **Smart Preview, the later phase.** It has `utils/theme.py` (167 lines)
   and two hand-written 877-line sheets (`resources/styles/dark.qss`,
   `light.qss`). Its colours are hex values substituted in place, not
   tokens, and its `build_stylesheet(accent_hex, mode)` takes its arguments
   in the opposite order. Moving it means turning those sheets into
   tokens, likely with a golden test of its own.

## Operational notes

- Golden files are captured with `tests/golden/capture.py`, run from the
  app's checkout with the app's own venv (usage in its docstring). It
  points the app's data-dir variable (`MEDIA_TRANSFER_DATA_DIR`,
  `ANNOTATIONS_DATA_DIR`) at a temp folder, so nothing touches the user's
  data, and writes the icons path as `@ICON_DIR@`.
- Gallery screenshots go in `screenshots/` (git-ignored).
- The venv has the package installed editable. After changing the entry
  points in pyproject.toml, rerun `pip install -e .`.
