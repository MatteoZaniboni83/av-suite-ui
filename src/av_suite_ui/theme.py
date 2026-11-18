"""Theme: dark / light palettes, a user-chosen accent, one stylesheet template.

The Tally look of the AV Suite (Smart Preview's amber, hue-shifted shade
families), authored once: styles.qss holds @token@ placeholders and both
modes fill them from a palette. The palette is also the source of any status
colour a widget paints directly, so painted colours and the stylesheet can
never disagree.

An app appends its own small sheet to the shared one, filled from the same
tokens::

    from importlib.resources import files
    from av_suite_ui import theme

    APP_QSS = files(__package__).joinpath("app.qss").read_text(encoding="utf-8")

    def build_stylesheet(mode, accent):
        return theme.build_stylesheet(mode, accent, extra=APP_QSS,
                                      icon_dir=lambda: os.path.join(data_directory(), "icons"))

Extracted from Media Transfer 0.1.8+ (8b4f22c), with Annotations' fallback
for an unwritable icon folder. With the default accent, the shared sheet plus
Media Transfer's own rules is what Media Transfer built before the switch,
except for the deliberate restyles listed in tests/test_golden.py (RESTYLES).
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from collections.abc import Callable, Iterable
from importlib.resources import files

from PySide6.QtGui import QColor

log = logging.getLogger(__name__)

MODES = ("dark", "light")

DARK_DEFAULT_ACCENT = "#f0a040"     # Tally amber, as Smart Preview
LIGHT_DEFAULT_ACCENT = "#c77a1f"

# warn is yellow, not amber (0.2.0): the default accent is amber, and a warning
# must not read as the accent. Light warn is dark enough for 4.5:1 text on its
# own note tint over every surface (test_theme checks both).
_BASE = {
    "dark": {
        "bg_base": "#1a1c1e", "bg_raised": "#22252a", "bg_elevated": "#2b2f36",
        "bg_overlay": "#333840", "bg_sunken": "#16181a",
        "border_subtle": "#2e3238", "border_default": "#3d4450",
        "border_strong": "#555f6e",
        "text_primary": "#e8eaed", "text_secondary": "#9aa3b0",
        "text_muted": "#5c6470",
        "ok": "#2ecc71", "warn": "#f1c40f", "error": "#e74c3c",
    },
    "light": {
        "bg_base": "#f0f1f3", "bg_raised": "#e8eaed", "bg_elevated": "#dde0e5",
        "bg_overlay": "#d1d5db", "bg_sunken": "#ffffff",
        "border_subtle": "#c5cad2", "border_default": "#a8b0bc",
        "border_strong": "#7c8695",
        "text_primary": "#1a1c1e", "text_secondary": "#4a5568",
        "text_muted": "#7c8695",
        "ok": "#16a34a", "warn": "#705700", "error": "#dc2626",
    },
}

# Hand-tuned accent families, copied from Smart Preview so the default accent
# reproduces its look exactly.
_SHADES = {
    "dark": (DARK_DEFAULT_ACCENT, {"accent_hover": "#e08f2e", "accent_pressed": "#c77a1f",
                                   "accent_tint": "#4a3316", "accent_dim": "#6b4a1f"}),
    "light": (LIGHT_DEFAULT_ACCENT, {"accent_hover": "#a8651a", "accent_pressed": "#8a5215",
                                     "accent_tint": "#fdf0dc", "accent_dim": "#e8b87a"}),
}

_MONO = "'SF Mono', Menlo, Consolas, 'JetBrains Mono', 'IBM Plex Mono', monospace"
_UI = "'Inter', 'Segoe UI', system-ui, -apple-system, 'IBM Plex Sans', sans-serif"

IconDir = str | os.PathLike | Callable[[], str] | None


def _hsl(c: QColor) -> tuple[float, float, float]:
    h = c.hueF()
    return (h if h >= 0 else 0.0), c.saturationF(), c.lightnessF()


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _derive(accent: str, default: str, shades: dict[str, str]) -> dict[str, str]:
    """Shift each hand-tuned shade by the hue change from default -> accent,
    keeping its saturation/lightness offsets. The default short-circuits so it
    round-trips exactly."""
    base = QColor(accent)
    if not base.isValid() or base.name().lower() == default.lower():
        return {"accent": default, **shades}
    bh, bs, bl = _hsl(QColor(default))
    h, s, lt = _hsl(base)
    out = {"accent": base.name()}
    for role, hexval in shades.items():
        sh, ss, sl = _hsl(QColor(hexval))
        out[role] = QColor.fromHslF((h + sh - bh) % 1.0, _clamp(s + ss - bs),
                                    _clamp(lt + sl - bl)).name()
    return out


def _luminance(c: QColor) -> float:
    def ch(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c.redF()) + 0.7152 * ch(c.greenF()) + 0.0722 * ch(c.blueF())


def on_colour(hex_colour: str) -> str:
    """Near-black or white — whichever contrasts more with *hex_colour*.

    White on the default amber is ~2.2:1, which fails legibility; this keeps
    accent-filled buttons readable whatever accent the user picks.
    """
    lum = _luminance(QColor(hex_colour))
    dark, light = "#121416", "#ffffff"
    c_dark = (lum + 0.05) / (_luminance(QColor(dark)) + 0.05)
    c_light = (_luminance(QColor(light)) + 0.05) / (lum + 0.05)
    return dark if c_dark >= c_light else light


def palette(mode: str = "dark", accent: str | None = None) -> dict[str, str]:
    """Every colour role (and the two font stacks) for *mode*, with the
    accent family derived from *accent* — the Tally default when None."""
    mode = mode if mode in _BASE else "dark"
    default, shades = _SHADES[mode]
    pal = {**_BASE[mode], **_derive(accent or default, default, shades)}
    pal["on_accent"] = on_colour(pal["accent"])
    pal["font_ui"], pal["font_mono"] = _UI, _MONO
    return pal


def _rgb(hex_colour: str) -> str:
    c = QColor(hex_colour)
    return f"{c.red()}, {c.green()}, {c.blue()}"


# ── Icons ────────────────────────────────────────────────────────────────────

def _fallback_icons_dir() -> str:
    """Per-user temp folder for icons when the app's own folder is unwritable
    (or none was given) — per-user, so two accounts on one machine don't fight
    over ownership."""
    try:
        owner = str(os.getuid())
    except AttributeError:                      # Windows has no getuid
        owner = os.environ.get("USERNAME") or "shared"
    return os.path.join(tempfile.gettempdir(), f"av-suite-ui-icons-{owner}")


def _icon_file(name: str, svg: str, icon_dir: IconDir = None) -> str:
    """Path to *svg*, kept as the file *name* in *icon_dir*.

    Stylesheets cannot take data: URIs, so whatever QSS draws from an image
    has to be a file. It is written when missing or when the drawing has
    changed: a file left by an older version must not outlive its shape.

    *icon_dir* is the app's folder for these (Media Transfer and Annotations
    use ``<data dir>/icons``), or a callable returning it, so that a data dir
    that cannot even be created raises in here and falls back. An unwritable
    folder must not kill the launch this runs in (it is on the path to the
    first stylesheet, before any app's own degraded handling): on OSError the
    icon falls back to a per-user temp folder, and if even that fails the
    path is logged and returned anyway — QSS then draws no image there, which
    is cosmetic; a dead app is not.
    """
    folders = []
    if icon_dir is not None:
        try:
            folders.append(os.fspath(icon_dir() if callable(icon_dir) else icon_dir))
        except OSError:                 # the app's data dir itself cannot be created
            log.warning("No icon folder from the app; using a temp folder")
    folders.append(_fallback_icons_dir())
    path = os.path.join(folders[-1], name)
    for folder in folders:
        path = os.path.join(folder, name)
        try:
            os.makedirs(folder, exist_ok=True)
            try:
                with open(path, encoding="utf-8") as f:
                    current = f.read()
            except OSError:
                current = None
            if current != svg:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(svg)
            return path.replace("\\", "/")      # QSS url() wants forward slashes
        except OSError:
            log.warning("Cannot write icon %s under %s", name, folder)
    return path.replace("\\", "/")              # missing icon: cosmetic only


def _check_icon(fill: str, mark: str, icon_dir: IconDir) -> str:
    """A ticked checkbox in these colours. Styling a checkbox indicator's
    background in QSS removes Qt's own tick, so the tick is an image."""
    return _icon_file(
        f"check_{fill.lstrip('#')}_{mark.lstrip('#')}.svg",
        '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" '
        'viewBox="0 0 14 14">'
        f'<rect x="0.5" y="0.5" width="13" height="13" rx="2" fill="{fill}"/>'
        f'<path d="M3.4 7.3 L5.9 9.7 L10.6 4.5" fill="none" stroke="{mark}" '
        'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        icon_dir)


def _arrow_icon(colour: str, icon_dir: IconDir) -> str:
    """A drop-down arrow in this colour. Styling QComboBox::drop-down removes
    Qt's own arrow as well: in Media Transfer up to 0.1.4 every drop-down
    looked like a text field, with nothing to say it opens a list."""
    return _icon_file(
        f"arrow_{colour.lstrip('#')}.svg",
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" '
        'viewBox="0 0 10 10">'
        f'<path d="M2 3.75 L5 6.75 L8 3.75" fill="none" stroke="{colour}" '
        'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        icon_dir)


def _branch_icon(colour: str, icon_dir: IconDir) -> str:
    """A tree's closed branch: the drop-down arrow turned to point right.
    Styling a QTreeView takes the platform's own triangles away (and Qt's
    fallback indicator is palette-drawn, invisible on the themed tree), as
    styling a drop-down took its arrow."""
    return _icon_file(
        f"branch_{colour.lstrip('#')}.svg",
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" '
        'viewBox="0 0 10 10">'
        f'<path d="M3.75 2 L6.75 5 L3.75 8" fill="none" stroke="{colour}" '
        'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        icon_dir)


# ── Templates ────────────────────────────────────────────────────────────────

def read_template(package: str, name: str) -> str:
    """The text of *name* shipped inside *package*, through importlib.resources
    — which a frozen app (PyInstaller) serves as well, provided its spec or a
    hook collects the file. Use it for an app's own sheet too."""
    return files(package).joinpath(name).read_text(encoding="utf-8")


def shared_template() -> str:
    """The suite's stylesheet template, tokens unfilled."""
    return read_template(__package__, "styles.qss")


def tokens(mode: str = "dark", accent: str | None = None, *,
           icon_dir: IconDir = None) -> dict[str, str]:
    """Every value a template may name: the palette, ``<colour>_rgb`` as
    'r, g, b' for rgba(), and the paths of the images QSS draws from.
    Writes those images (see _icon_file)."""
    pal = palette(mode, accent)
    values = dict(pal)
    for k, v in pal.items():
        if v.startswith("#"):
            values[k + "_rgb"] = _rgb(v)
    values["check_icon"] = _check_icon(pal["accent"], pal["on_accent"], icon_dir)
    values["arrow_icon"] = _arrow_icon(pal["text_secondary"], icon_dir)
    values["arrow_icon_disabled"] = _arrow_icon(pal["text_muted"], icon_dir)
    values["branch_icon"] = _branch_icon(pal["text_secondary"], icon_dir)
    # Annotations' name for the same image.
    values["arrow_right_icon"] = values["branch_icon"]
    return values


_TOKEN = re.compile(r"@([a-z_]+)@")


def fill(template: str, values: dict[str, str], source: str = "template") -> str:
    """`@name@` -> values[name]. An unknown name is an error that says where
    it was found: a typo must not ship as a literal @token@ Qt ignores."""
    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in values:
            raise KeyError(f"{source} uses unknown token @{key}@")
        return values[key]

    return _TOKEN.sub(sub, template)


def build_stylesheet(mode: str = "dark", accent: str | None = None, *,
                     extra: str | Iterable[str] | None = None,
                     icon_dir: IconDir = None) -> str:
    """The shared sheet for *mode* and *accent*, filled, with *extra* — an
    app's own template text, or several — appended after it and filled from
    the same tokens. Appended means an app rule overrides a shared rule of
    the same weight, so an app restyles a control without editing this
    package.

    *icon_dir*: where the SVG images go (a path, or a callable returning one);
    None means a per-user temp folder.
    """
    values = tokens(mode, accent, icon_dir=icon_dir)
    parts = [fill(shared_template(), values, "av_suite_ui/styles.qss")]
    if isinstance(extra, str):
        extra = [extra]
    for i, text in enumerate(extra or ()):
        parts.append(fill(text, values, f"app stylesheet #{i + 1}"))
    return "\n".join(parts)
