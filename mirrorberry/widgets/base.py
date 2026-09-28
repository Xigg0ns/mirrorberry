# SPDX-License-Identifier: GPL-3.0-or-later
"""Base class for everything that lives in a zone."""

from __future__ import annotations

import pygame

from ..i18n import Translator
from ..layout import Zone
from .style import Theme, draw_header, header_text


class Widget:
    """Subclass this to make a new module (clock, weather, calendar, ...).

    The app calls ``update()`` every ``refresh_interval`` seconds, aligned to
    the wall clock, and redraws the widget only when it returns True. Leave
    ``refresh_interval`` as None for static content, or override
    ``next_update_in()`` for custom timing.

    Several widgets can share a zone, stacked top to bottom like modules in a
    MagicMirror region. ``size()`` tells the app how much room the widget
    needs; returning None means "fill whatever is left".
    """

    refresh_interval: float | None = None
    fills_zone = False  # True: drawn over the whole zone, edge to edge (placeholders)

    # Set by the app before the first update.
    theme: Theme = Theme()
    language: str = "en"
    stack_width: int = 0  # widest module in this zone: header rules span it, like a MagicMirror region

    header: str = ""
    align: str = "left"

    @property
    def tr(self) -> Translator:
        """Translations and date wording in the display language."""
        cached = getattr(self, "_tr", None)
        if cached is None or cached.language != self.language:
            cached = self._tr = Translator(self.language)
        return cached

    def __init__(self, zone: Zone, **options):
        self.zone = zone
        self.options = options

    def next_update_in(self, wall_time: float) -> float | None:
        """Seconds until ``update()`` should run again, or None for never.

        The default lines updates up with the wall clock: a 1 s widget runs
        just after each second ticks over, a 60 s widget just after each
        minute. Scheduling from the clock, not from "last run + interval",
        means slow redraws can't make updates drift and skip a beat.
        """
        interval = self.refresh_interval
        if interval is None:
            return None
        return interval - (wall_time % interval) + 0.005

    def update(self, now: float) -> bool:
        """Refresh internal state. Return True if the widget needs redrawing."""
        return False

    def size(self, width: int) -> tuple[int, int] | None:
        """(content width, height) this widget needs at ``width``; None = fill the space."""
        return None

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Paint the widget inside ``rect``. Drawing is clipped to the rect."""
        raise NotImplementedError

    # -- helpers for MagicMirror-style modules ------------------------------

    def header_size(self) -> tuple[int, float]:
        """(width, height) of this widget's header, (0, 0) if it has none."""
        if not self.header:
            return 0, 0.0
        return header_text(self.theme, self.header).width, self.theme.header_height()

    def with_header(self, content_w: float, content_h: float) -> tuple[int, int]:
        hw, hh = self.header_size()
        return round(max(content_w, hw)), round(content_h + hh)

    def begin(self, surface: pygame.Surface, rect: pygame.Rect, content_w: float) -> float:
        """Clear the rect, draw the header (if any); return the y where content starts."""
        surface.fill((0, 0, 0), rect)
        if not self.header:
            return float(rect.top)
        width = max(self.stack_width, round(content_w))
        return draw_header(surface, rect, self.header, self.theme, self.align, width)
