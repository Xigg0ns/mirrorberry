# SPDX-License-Identifier: GPL-3.0-or-later
"""The MagicMirror look: sizes, colours and fonts, configurable like its CSS.

MagicMirror styles text with size classes (xsmall, small, medium, large,
xlarge) and module headers. A Theme holds the font size and line height of
each class in MagicMirror's CSS pixels; ``scale`` turns those into screen
pixels. The defaults are MagicMirror's own main.css. [theme] in config.toml
overrides them, the way a custom.css would.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pygame

from .text import font, render

ROBOTO = "/usr/share/fonts/truetype/roboto/unhinted"
REGULAR = f"{ROBOTO}/RobotoCondensed-Regular.ttf"
LIGHT = f"{ROBOTO}/RobotoCondensed-Light.ttf"
ASSETS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
WEATHER_ICONS = str(ASSETS / "weathericons-regular-webfont.ttf")
FONT_AWESOME = str(ASSETS / "fa-solid-900.ttf")

BRIGHT = (255, 255, 255)
NORMAL = (0x99, 0x99, 0x99)
DIMMED = (0x66, 0x66, 0x66)

ALIGNMENTS = ("left", "center", "right")
CLASSES = ("xsmall", "small", "medium", "large", "xlarge")


@dataclass
class Theme:
    """Sizes in MagicMirror CSS px (before ``scale``); defaults = MagicMirror's main.css."""

    scale: float = 1.0
    sizes: dict = field(default_factory=lambda: {
        "xsmall": 15, "small": 20, "medium": 30, "large": 65, "xlarge": 75})
    line_heights: dict = field(default_factory=lambda: {
        "xsmall": 1.275, "small": 1.25, "medium": 1.225, "large": 1.0, "xlarge": 1.0})
    letter_spacing: dict = field(default_factory=lambda: {"xlarge": -3})  # CSS px, MagicMirror: .xlarge
    header_size: float = 15         # module header font size
    header_line: float = 1.0        # header line height, times header_size (MagicMirror: 15px)
    header_padding: float = 5       # space between header text line and its rule
    header_rule: float = 1          # rule thickness
    header_margin: float = 10       # space between the rule and the module's content
    cell_padding: float = 1         # table cell padding (browser default)

    def px(self, css: float) -> int:
        return max(1, round(css * self.scale))

    def size(self, cls: str) -> int:
        """Font size in screen px for a MagicMirror class ("small", "medium", …)."""
        return self.px(self.sizes[cls])

    def spacing(self, cls: str) -> int:
        """Letter spacing in screen px for a class (negative = tighter)."""
        return round(self.letter_spacing.get(cls, 0) * self.scale)

    def line(self, cls: str) -> float:
        """Line-box height in screen px for a class (unrounded, so rows don't drift)."""
        return self.sizes[cls] * self.line_heights[cls] * self.scale

    def row(self, cls: str) -> float:
        """Height of a table row in this class: line box plus cell padding."""
        return self.line(cls) + 2 * self.cell_padding * self.scale

    def header_height(self) -> float:
        return (self.header_size * self.header_line + self.header_padding
                + self.header_rule + self.header_margin) * self.scale


def default_align(col: int) -> str:
    """Like MagicMirror's regions: left column left-aligned, and so on."""
    return ALIGNMENTS[col]


def fade(color: tuple, opacity: float) -> tuple:
    """CSS opacity over the black background is just a darker colour."""
    return tuple(round(c * opacity) for c in color[:3])


def fade_opacity(index: int, count: int, enabled: bool = True, fade_point: float = 0.25) -> float:
    """MagicMirror's list fade: rows past ``fade_point`` of the list fade to nothing."""
    if not enabled or fade_point >= 1 or count <= 0:
        return 1.0
    start = count * max(0.0, fade_point)
    steps = count - start
    return 1.0 if index < start else max(0.0, 1 - (index - start) / steps)


class Text:
    """One piece of text in a CSS-like line box, measured before it's drawn."""

    def __init__(self, text: str, size: int, color: tuple, path: str | None = REGULAR, spacing: int = 0):
        self.font = font(size, path)
        if spacing:
            from .text import render_tracked
            self.surface = render_tracked(text, size, tuple(color[:3]), path, spacing)
        else:
            self.surface = render(text, size, tuple(color[:3]), path)
        self.width = self.surface.get_width()

    @property
    def ascent(self) -> int:
        return self.font.get_ascent()

    @property
    def content_height(self) -> int:
        return self.font.get_ascent() - self.font.get_descent()

    def baseline_in(self, line_top: float, line_height: float) -> float:
        """CSS centres the font's ascent+descent box in the line box (half-leading)."""
        return line_top + (line_height - self.content_height) / 2 + self.ascent

    def draw(self, surface: pygame.Surface, x: float, baseline: float) -> None:
        surface.blit(self.surface, (round(x), round(baseline - self.ascent)))


def x_for(align: str, rect: pygame.Rect, width: float) -> int:
    if align == "right":
        return round(rect.right - width)
    if align == "center":
        return round(rect.centerx - width / 2)
    return rect.left


def header_text(theme: Theme, text: str) -> Text:
    return Text(text.upper(), theme.px(theme.header_size), NORMAL)


def draw_header(surface: pygame.Surface, rect: pygame.Rect, text: str, theme: Theme,
                align: str, width: int) -> float:
    """MagicMirror's module header at the top of ``rect``; returns where content starts.

    Uppercase text, then a rule as wide as the module (``width``: MagicMirror
    modules in a region share the region's width), then a gap.
    """
    label = header_text(theme, text)
    width = max(width, label.width)
    left = x_for(align, rect, width)
    line_h = theme.header_size * theme.header_line * theme.scale
    label.draw(surface, x_for(align, pygame.Rect(left, 0, width, 0), label.width),
               label.baseline_in(rect.top, line_h))
    rule_y = rect.top + line_h + theme.header_padding * theme.scale
    pygame.draw.rect(surface, DIMMED, (left, round(rule_y), width, max(1, theme.px(theme.header_rule))))
    return rect.top + theme.header_height()
