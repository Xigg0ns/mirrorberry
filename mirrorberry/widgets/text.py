# SPDX-License-Identifier: GPL-3.0-or-later
"""Small text helpers shared by widgets."""

from __future__ import annotations

import logging
import os
from functools import lru_cache

import pygame

log = logging.getLogger(__name__)

DIGITS = "0123456789"


@lru_cache(maxsize=None)
def _usable_font_path(path: str | None) -> str | None:
    """Return ``path`` if it can be loaded, else None (warns once per path)."""
    if not path:
        return None
    if not os.path.isfile(path):
        hint = ""
        if "/roboto/" in path:
            hint = " (install it with: sudo apt install fonts-roboto-unhinted)"
        log.warning("Font %s not found%s; using the default font", path, hint)
        return None
    return path


@lru_cache(maxsize=64)
def font(size: int, path: str | None = None) -> pygame.font.Font:
    """A cached font. ``path`` is a .ttf/.otf file; None means pygame's bundled font.

    Fonts are loaded by file path, not by name, because pygame's name lookup
    scans every installed font and takes seconds on a Pi Zero.
    """
    return pygame.font.Font(_usable_font_path(path), max(8, size))


@lru_cache(maxsize=None)
def _digit_ratio(path: str | None) -> float:
    """Digit height as a fraction of the font size, measured once per font."""
    return digit_height(font(200, path)) / 200


def digit_height(f: pygame.font.Font) -> int:
    """Height of the digits above the baseline, in pixels (the 'cap height' of numbers)."""
    return max(m[3] for m in f.metrics(DIGITS) if m)


def size_for_digit_height(pixels: float, path: str | None = None) -> int:
    """Font size whose digits are about ``pixels`` tall."""
    return max(8, round(pixels / _digit_ratio(path)))


@lru_cache(maxsize=256)
def render(text: str, size: int, color: tuple, path: str | None = None) -> pygame.Surface:
    """Cached antialiased render; repeated strings (dates, labels) cost nothing."""
    return font(size, path).render(text, True, color)


@lru_cache(maxsize=128)
def render_tracked(text: str, size: int, color: tuple, path: str | None = None,
                   tracking: int = 0) -> pygame.Surface:
    """Like ``render`` but with extra space (negative = tighter) between characters.

    pygame has no letter-spacing, so glyphs are placed one by one. That drops
    kerning, which is fine for digits and punctuation but not for words.
    """
    if not tracking or len(text) < 2:
        return render(text, size, color, path)
    f = font(size, path)
    glyphs = [f.render(ch, True, color) for ch in text]
    advances = [m[4] if m else g.get_width() for m, g in zip(f.metrics(text), glyphs)]
    width = sum(advances) + tracking * (len(text) - 1)
    overhang = max(0, glyphs[-1].get_width() - advances[-1])
    surf = pygame.Surface((max(1, width + overhang), f.get_height()), pygame.SRCALPHA)
    x = 0
    for glyph, advance in zip(glyphs, advances):
        surf.blit(glyph, (x, 0))
        x += advance + tracking
    return surf


def fit_text(text: str, max_width: int, size: int, color, path: str | None = None) -> pygame.Surface:
    """Render ``text`` at ``size`` or smaller so it fits within ``max_width``."""
    while True:
        surf = font(size, path).render(text, True, color)
        if surf.get_width() <= max_width or size <= 8:
            return surf
        size = int(size * 0.9)


def contrast_color(bg: pygame.Color) -> pygame.Color:
    """Black or white, whichever reads better on ``bg``."""
    luminance = 0.2126 * bg.r + 0.7152 * bg.g + 0.0722 * bg.b
    return pygame.Color("black") if luminance > 140 else pygame.Color("white")
