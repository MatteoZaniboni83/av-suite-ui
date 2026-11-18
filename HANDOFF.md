# Session handoff

Read this after CLAUDE.md at the start of every session. Newest state first.

## State as of 2026-11-18: v0.1.0 tagged locally, nothing pushed

- **The package exists and v0.1.0 is tagged locally.** There is no GitHub
  repo and no push: the user creates the repo once the open decisions below
  are settled. 71 tests pass, ruff is clean, and the suite gives the same
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

### Proof that switching changes nothing

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

1. **Amber accent vs warning amber**, flagged and not fixed. The dark accent
   is `#f0a040` (hue 33°) and the dark warning is `#f39c12` (hue 37°). In
   light mode the accent is `#c77a1f` and the warning `#d97706`, both hue
   32°, nearly the same colour. A second problem turned up: light-mode
   `#d97706` is only 2.8:1 on `bg_base`, below the 4.5:1 that text needs, so
   `QLabel#warnNote` text is hard to read in light mode. The options:
   - **A. Move the warning to yellow** (recommended). Use `#f1c40f` in dark
     (hue 48°, 10.3:1) and `#8a6d00` in light (hue 47°, 4.35:1, which also
     fixes the contrast). The accent stays Tally amber. Warnings in every
     app change colour: a deliberate restyle, with regenerated golden files
     and a 0.2.0.
   - **B. Move the accent off amber** to a hue no status uses. This changes
     every app's identity, Smart Preview's included.
   - **C. Keep both colours and rely on non-colour cues.** ⚠ and words are
     already a suite rule. A warning could also get its own shape (say a
     left bar on `warnNote`). There is no visual change, but the light-mode
     contrast problem stays.
2. **Before creating the GitHub repo:**
   - **Private or public.** If private, each app's CI needs a credential to
     `pip install` from it (a fine-grained PAT or a deploy key as a secret in
     each app repo). The repo holds no secrets, so public is the simplest.
   - **Pin form.** A tag (`@v0.1.0`) reads well, but a tag can be moved. A
     commit SHA cannot. The apps' rule is "no surprise upgrades", so
     consider pinning by SHA with the tag in a comment.
   - **CI here.** Media Transfer's `ci.yml` pattern would be lint + tests on
     Linux only, on push, with no artifacts. Is that wanted?
   - **The folder name has a space** (`av-suite ui`). An app developing
     against a local checkout (`pip install -e "../av-suite ui"`) has to
     quote the path. Renaming it to `av-suite-ui` would match the repo
     name. It is the user's folder, so it was not renamed.
3. **`format_size`** is identical in both apps. It is an engine helper in
   Media Transfer, whose engines must stay Qt-free, so it has not moved. If it
   should be shared, it would go in a Qt-free submodule (say
   `av_suite_ui.text`). That is the user's call.

## Next up (rough priority)

1. Settle the decisions above, then create the repo and push `main` plus
   the `v0.1.0` tag.
2. **Media Transfer switches** (in its own session and repo):
   - pin the package;
   - make `ui/theme.py` a thin wrapper that calls
     `build_stylesheet(extra=APP_QSS, icon_dir=<data dir>/icons)` and
     re-exports `palette`;
   - replace `styles.qss` with `tests/golden/media_transfer_app.qss`;
   - import the eight helpers from `av_suite_ui.widgets`;
   - change the spec's `datas` to the app sheet;
   - check that its own test_theme still passes.

   The golden test says the look will not change.
3. **Annotations switches** the same way, with `annotations_app.qss`. The
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
