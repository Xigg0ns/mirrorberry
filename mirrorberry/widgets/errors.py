# SPDX-License-Identifier: GPL-3.0-or-later
"""Shown in a zone whose widget couldn't be set up from config.toml."""

from __future__ import annotations

import pygame

from ..layout import Zone
from .base import Widget
from .style import DIMMED, LIGHT, NORMAL, Text, default_align, x_for
from .text import font


class ConfigErrorWidget(Widget):
    def __init__(self, zone: Zone, message: str):
        super().__init__(zone)
        self.message = message
        self.align = default_align(zone.col)

    def _lines(self, width: int) -> list[Text]:
        t = self.theme
        lines = [Text(self.tr("ERROR_CONFIG"), t.size("small"), NORMAL, LIGHT)]
        size = t.size("xsmall")
        f = font(size, LIGHT)
        line = ""
        for word in self.message.split():  # word-wrap the error itself
            if line and f.size(f"{line} {word}")[0] > width:
                lines.append(Text(line, size, DIMMED, LIGHT))
                line = word
            else:
                line = f"{line} {word}".strip()
        if line:
            lines.append(Text(line, size, DIMMED, LIGHT))
        return lines

    def size(self, width: int) -> tuple[int, int] | None:
        lines = self._lines(width)
        t = self.theme
        return max(x.width for x in lines), round(t.line("small") + (len(lines) - 1) * t.line("xsmall"))

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        surface.fill((0, 0, 0), rect)
        t = self.theme
        y = float(rect.top)
        for i, text in enumerate(self._lines(rect.width)):
            lh = t.line("small" if i == 0 else "xsmall")
            text.draw(surface, x_for(self.align, rect, text.width), text.baseline_in(y, lh))
            y += lh
