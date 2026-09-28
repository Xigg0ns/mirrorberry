# SPDX-License-Identifier: GPL-3.0-or-later
"""Today's Swedish name days, like MMM-Namnsdag.

Names come from the "Svenska Dagar" API 2.1 (sholiday.faboul.se, formerly
api.dryg.net), the same source MMM-Namnsdag uses. One name per line in white;
fetched every update_interval and again right after midnight.

Written from scratch in Python to behave like MMM-Namnsdag (Menturan,
GPL-3.0); no code was copied. See THIRD_PARTY_NOTICES.md.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime

import pygame

from ..fetch import Poller, http_get, interval_option
from ..layout import Zone
from .base import Widget
from .style import BRIGHT, DIMMED, LIGHT, REGULAR, Text, default_align, x_for

log = logging.getLogger(__name__)

API = "https://sholiday.faboul.se/dagar/v2.1"


def _today() -> date:
    """Today's date (a function so tests can freeze it)."""
    return datetime.now().date()


def build_url(day: date) -> str:
    return f"{API}/{day.year}/{day.month}/{day.day}"


def parse_names(data: dict, day: date) -> tuple[date, list[str]]:
    """The names for ``day`` from a Svenska Dagar response."""
    for entry in data.get("dagar", []):
        if entry.get("datum") == day.isoformat():
            names = entry.get("namnsdag") or []
            return day, [str(n) for n in names if str(n).strip()]
    raise ValueError(f"no entry for {day.isoformat()} in the response")


def fetch_names() -> tuple[date, list[str]]:
    day = _today()
    return parse_names(json.loads(http_get(build_url(day))), day)


class Namnsdag(Widget):
    refresh_interval = 60.0  # notices midnight within a minute

    def __init__(
        self,
        zone: Zone,
        header: str = "",
        single_line: bool = False,     # "Lennart, Leonard" on one line instead of one per line
        separator: str = ", ",
        align: str | None = None,
        center_lines: bool = False,    # centre the names on each other (MMM-Namnsdag's Firefox look)
        text_class: str = "small",
        update_interval: int = 21600,  # seconds (6 h); a new day always fetches right after midnight
    ):
        super().__init__(zone)
        self.header = header
        self.single_line = bool(single_line)
        self.separator = separator
        self.align = align or default_align(zone.col)
        self.center_lines = bool(center_lines)
        self.text_class = text_class
        # Refetched every update_interval; failures retry every 5 minutes, like MMM-Namnsdag.
        self.poller = Poller.shared("namnsdag", "namnsdag", fetch_names,
                                    interval_option("update_interval", update_interval))
        self.poller.retry = 300
        self.poller.start()
        self._view: tuple = ()

    def update(self, now: float) -> bool:
        _, data, error = self.poller.snapshot()
        today = _today()
        if data is not None and data[0] != today:
            self.poller.refresh()  # a new day: fetch today's names now
            data = None
        if data is not None:
            names = data[1]
            if not names:
                view = ("message", self.tr("NAMEDAY_EMPTY"))
            elif self.single_line:
                view = ("names", (self.separator.join(names),))
            else:
                view = ("names", tuple(names))
        elif error:
            view = ("message", self.tr("NAMEDAY_ERROR"))
        else:
            view = ("message", self.tr("NAMEDAY_LOADING"))
        changed = view != self._view
        self._view = view
        return changed

    def _lines(self) -> list[Text]:
        size = self.theme.size(self.text_class)
        kind, payload = self._view
        if kind == "message":
            return [Text(payload, size, DIMMED, LIGHT)]
        return [Text(name, size, BRIGHT, REGULAR) for name in payload]

    def size(self, width: int) -> tuple[int, int] | None:
        if not self._view:
            return self.with_header(0, 0)
        lines = self._lines()
        return self.with_header(max(t.width for t in lines), len(lines) * self.theme.line(self.text_class))

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if not self._view:
            surface.fill((0, 0, 0), rect)
            return
        lines = self._lines()
        line_h = self.theme.line(self.text_class)
        block_w = max(t.width for t in lines)
        y = self.begin(surface, rect, block_w)
        block = pygame.Rect(x_for(self.align, rect, block_w), 0, block_w, 0)
        for text in lines:
            x = x_for("center" if self.center_lines else self.align, block, text.width)
            text.draw(surface, x, text.baseline_in(y, line_h))
            y += line_h
