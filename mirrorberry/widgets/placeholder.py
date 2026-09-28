# SPDX-License-Identifier: GPL-3.0-or-later
"""Revision-1 debug widget: a solid colour block labelled with its zone."""

from __future__ import annotations

import pygame

from ..layout import Zone
from .base import Widget
from .text import contrast_color, fit_text


class Placeholder(Widget):
    fills_zone = True  # colour the whole zone, edge to edge

    def __init__(self, zone: Zone, color: str = "#444444", label: str | None = None,
                 show_geometry: bool = True):
        super().__init__(zone)
        self.color = pygame.Color(color)
        self.label = label or zone.name
        self.show_geometry = show_geometry

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        surface.fill(self.color, rect)
        if rect.width < 20 or rect.height < 20:
            return  # collapsed zone, nothing readable to draw

        fg = contrast_color(self.color)
        max_w = int(rect.width * 0.9)
        title = fit_text(self.label, max_w, min(rect.width, rect.height) // 5, fg)

        lines = [title]
        if self.show_geometry:
            info = f"{rect.width}x{rect.height} at ({rect.x}, {rect.y})"
            lines.append(fit_text(info, max_w, max(14, min(rect.width, rect.height) // 10), fg))

        gap = title.get_height() // 4
        total_h = sum(s.get_height() for s in lines) + gap * (len(lines) - 1)
        y = rect.centery - total_h // 2
        for surf in lines:
            surface.blit(surf, surf.get_rect(midtop=(rect.centerx, y)))
            y += surf.get_height() + gap
