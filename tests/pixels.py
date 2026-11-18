"""Looking at what is painted: colour distance and ink in a strip."""

from __future__ import annotations

from PySide6.QtGui import QColor


def distance(a: QColor, b: QColor) -> int:
    return max(abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue()))


def ink(widget, x0: int, x1: int, background: str, y0: int = 4,
        y1: int | None = None) -> tuple[int, QColor | None]:
    """What is painted on *widget* in the box x0..x1, y0..y1 that is not its
    background: how many pixels, and the colour furthest from the background
    — the full colour of a stroke, past its smoothed edges. By default the
    rows inside a 4 px border."""
    img, bg = widget.grab().toImage(), QColor(background)
    y1 = img.height() - 4 if y1 is None else y1
    count, furthest, far = 0, None, -1
    for x in range(x0, x1):
        for y in range(y0, y1):
            colour = img.pixelColor(x, y)
            d = distance(colour, bg)
            if d > 25:
                count += 1
                if d > far:
                    furthest, far = colour, d
    return count, furthest


def crisp(widget):
    """Linux renders text with subpixel anti-aliasing, whose coloured fringes
    are further from the background than the glyph itself: ink() took a blue
    fringe for the text colour there (Annotations, 98789b0)."""
    font = widget.font()
    font.setStyleStrategy(font.StyleStrategy.NoSubpixelAntialias)
    widget.setFont(font)
