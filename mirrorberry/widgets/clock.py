# SPDX-License-Identifier: GPL-3.0-or-later
"""Clock: date, large time with small superscript seconds, and the week number.

    söndag, 27 sep 2026
                17:01 ⁵¹
               Vecka 39

Proportions follow the MagicMirror-style reference design: the time's digits
are 1.27x the date's, seconds about half the time's, with fixed spacing, all
scaled together to fit the zone. Uses the Pi's local time; day and month names
follow the locale set in config.toml ([general] locale).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

import pygame

from ..layout import Zone
from .base import Widget
from .text import digit_height, font, render, render_tracked, size_for_digit_height

ALIGNMENTS = ("left", "center", "right")
ROBOTO = "/usr/share/fonts/truetype/roboto/unhinted"

# Proportions measured from the reference, in units of the date's digit height.
TIME_H = 1.255         # time digits
SECONDS_H = 0.62       # superscript seconds digits
WEEK_H = 1.0           # week line digits
GAP_ABOVE_TIME = 0.52  # date baseline -> top of the time digits
GAP_BELOW_TIME = 0.535 # time baseline -> top of the week digits
SECONDS_DROP = 0.045   # seconds tops sit this far below the time's tops
SECONDS_GAP = -0.075   # time -> seconds; negative because the time's letter-spacing
                       # carries past its last digit, as CSS letter-spacing does
DESCENT = 0.25         # room below the last line for descenders
# Letter-spacing, as a fraction of that text's own digit height (reference is tight).
TIME_TRACKING = -0.07
SECONDS_TRACKING = -0.10

# sizing = "theme": MagicMirror's clock as three lines (date: medium, time: large with
# small superscript seconds, week: medium). Measured from a MagicMirror screen:
THEME_TIME_LINE_EXTRA = 0.052   # the raised seconds make the time line a bit taller (x large size)
THEME_SECONDS_DROP = 0.02       # seconds tops sit this far below the time's tops (x medium digits)
THEME_SECONDS_GAP = 0.0         # extra time -> seconds gap (x medium digit height)

# Wide sample values so the layout doesn't resize as the digits change.
_SAMPLE = datetime(2000, 12, 31, 23, 59, 59)


_CODE = re.compile(r"%(-?)([A-Za-z%])")
_UNPADDED = {
    "d": lambda t: t.day,
    "m": lambda t: t.month,
    "H": lambda t: t.hour,
    "I": lambda t: t.hour % 12 or 12,
    "M": lambda t: t.minute,
    "S": lambda t: t.second,
    "V": lambda t: t.isocalendar()[1],
}


def format_time(fmt: str, t: datetime, capitalize_names: bool = False) -> str:
    """strftime with two extras that work on every platform.

    * ``%-d %-m %-H %-I %-M %-S %-V`` drop the leading zero (%-V: ISO week).
    * ``capitalize_names`` capitalizes day and month names (%A %a %B %b),
      e.g. "söndag, 27 sep" -> "Söndag, 27 Sep", leaving other words alone.
    """
    def expand(m: re.Match) -> str:
        dash, code = m.groups()
        if code == "%":
            return "%%"
        if dash and code in _UNPADDED:
            return str(_UNPADDED[code](t))
        if capitalize_names and not dash and code in "AaBb":
            name = t.strftime("%" + code)
            return (name[:1].upper() + name[1:]).replace("%", "%%")
        return m.group(0)

    return t.strftime(_CODE.sub(expand, fmt))


@dataclass(frozen=True)
class _Layout:
    unit: float
    date_size: int
    time_size: int
    seconds_size: int
    week_size: int


class Clock(Widget):
    # Checked just after every second ticks over; only redraws when the text changes.
    refresh_interval = 1.0

    def __init__(
        self,
        zone: Zone,
        time_format: str = "%H:%M",
        seconds: bool = False,                  # small superscript seconds after the time
        date_format: str = "%A, %-d %b %Y",     # "" hides the date
        week_format: str = "",                  # e.g. "Week %-V"; "" hides it
        capitalize_names: bool = False,         # "Söndag, 27 Sep" instead of "söndag, 27 sep"
        align: str = "right",
        color: str = "#FFFFFF",
        date_color: str = "#999999",
        seconds_color: str = "#666666",
        week_color: str = "#666666",
        background: str = "#000000",
        font: str | None = f"{ROBOTO}/RobotoCondensed-Regular.ttf",
        time_font: str | None = f"{ROBOTO}/RobotoCondensed-Light.ttf",
        sizing: str = "fit",                    # "fit": fill the zone; "theme": MagicMirror sizes
    ):
        super().__init__(zone)
        if align not in ALIGNMENTS:
            raise ValueError(f"align must be one of {ALIGNMENTS}, got {align!r}")
        self.time_format = time_format
        self.seconds = bool(seconds)
        self.date_format = date_format
        self.week_format = week_format
        self.capitalize_names = bool(capitalize_names)
        self.align = align
        self.color = tuple(pygame.Color(color))
        self.date_color = tuple(pygame.Color(date_color))
        self.seconds_color = tuple(pygame.Color(seconds_color))
        self.week_color = tuple(pygame.Color(week_color))
        self.background = pygame.Color(background)
        self.font = font
        self.time_font = time_font
        if sizing not in ("fit", "theme"):
            raise ValueError('sizing must be "fit" or "theme"')
        self.sizing = sizing
        self._texts: tuple[str, str, str, str] = ("", "", "", "")
        self._layout_key: tuple | None = None
        self._layout: _Layout | None = None
        self.update(0)

    # -- state ----------------------------------------------------------------

    def _format_all(self, t: datetime) -> tuple[str, str, str, str]:
        cap = self.capitalize_names
        return (
            format_time(self.date_format, t, cap) if self.date_format else "",
            format_time(self.time_format, t, cap),
            t.strftime("%S") if self.seconds else "",
            format_time(self.week_format, t, cap) if self.week_format else "",
        )

    def update(self, now: float) -> bool:
        texts = self._format_all(datetime.now())
        changed = texts != self._texts
        self._texts = texts
        return changed

    # -- layout ---------------------------------------------------------------

    def _sizes(self, unit: float) -> _Layout:
        return _Layout(
            unit=unit,
            date_size=size_for_digit_height(unit, self.font),
            time_size=size_for_digit_height(unit * TIME_H, self.time_font),
            seconds_size=size_for_digit_height(unit * SECONDS_H, self.time_font),
            week_size=size_for_digit_height(unit * WEEK_H, self.font),
        )

    def _block_width(self, lay: _Layout, date: str, week: str) -> int:
        _, time_sample, sec_sample, _ = self._format_all(_SAMPLE)
        widths = [self._time_surface(time_sample, lay.time_size).get_width()]
        if sec_sample:
            widths[0] += (round(lay.unit * SECONDS_GAP)
                          + self._seconds_surface(sec_sample, lay.seconds_size).get_width())
        if date:
            widths.append(font(lay.date_size, self.font).size(date)[0])
        if week:
            widths.append(font(lay.week_size, self.font).size(week)[0])
        return max(widths)

    def _layout_for(self, width: int, height: int, date: str, week: str) -> _Layout:
        """Largest layout that fits; recomputed only when the zone, date or week changes."""
        key = (width, height, date, week)
        if key == self._layout_key and self._layout:
            return self._layout

        units = TIME_H + DESCENT
        if date:
            units += 1.0 + GAP_ABOVE_TIME
        if week:
            units += GAP_BELOW_TIME + WEEK_H
        unit = height / units

        # Text width scales roughly linearly with size: measure once, scale, then nudge.
        trial = self._sizes(100)
        unit = min(unit, 100 * width / max(1, self._block_width(trial, date, week)))
        lay = self._sizes(unit)
        while unit > 4 and self._block_width(lay, date, week) > width:
            unit *= 0.97
            lay = self._sizes(unit)

        self._layout_key, self._layout = key, lay
        return lay

    # -- drawing --------------------------------------------------------------

    def _time_surface(self, text: str, size: int) -> pygame.Surface:
        tracking = round(TIME_TRACKING * digit_height(font(size, self.time_font)))
        return render_tracked(text, size, self.color, self.time_font, tracking)

    def _seconds_surface(self, text: str, size: int) -> pygame.Surface:
        tracking = round(SECONDS_TRACKING * digit_height(font(size, self.time_font)))
        return render_tracked(text, size, self.seconds_color, self.time_font, tracking)

    def _x_for(self, inner: pygame.Rect, width: int) -> int:
        if self.align == "right":
            return inner.right - width
        if self.align == "left":
            return inner.left
        return inner.centerx - width // 2

    def _line(self, surface, inner, top: float, text: str, size: int, color, path) -> float:
        """Draw one line with its digit tops at ``top``; return its baseline."""
        f = font(size, path)
        baseline = top + digit_height(f)
        surf = render(text, size, color, path)
        surface.blit(surf, (self._x_for(inner, surf.get_width()), round(baseline - f.get_ascent())))
        return baseline

    # -- theme sizing (MagicMirror classes) ------------------------------------

    def _theme_parts(self):
        t = self.theme
        date, time_text, secs, week = self._texts
        med, large, small = t.size("medium"), t.size("large"), t.size("small")
        unit = digit_height(font(med, self.font))
        date_t = render(date, med, self.date_color, self.font) if date else None
        spacing = t.spacing("large")  # the seconds sit inside the time element: same letter spacing
        time_t = render_tracked(time_text, large, self.color, self.time_font, spacing)
        sec_t = render_tracked(secs, small, self.seconds_color, self.time_font, spacing) if secs else None
        week_t = render(week, med, self.week_color, self.font) if week else None
        gap = spacing + round(unit * THEME_SECONDS_GAP)  # CSS letter-spacing also follows the last digit
        time_w = time_t.get_width() + ((gap + sec_t.get_width()) if sec_t else 0)
        width = max(time_w, date_t.get_width() if date_t else 0, week_t.get_width() if week_t else 0)
        time_line = t.line("large") + (THEME_TIME_LINE_EXTRA * t.sizes["large"] * t.scale if sec_t else 0)
        height = (t.line("medium") if date_t else 0) + time_line + (t.line("medium") if week_t else 0)
        return date_t, time_t, sec_t, week_t, gap, time_w, time_line, width, height, unit

    def size(self, width: int) -> tuple[int, int] | None:
        if self.sizing != "theme":
            return None  # fit mode fills whatever room it gets
        *_, w, h, _unit = self._theme_parts()
        return round(w), round(h)

    def _blit_line(self, surface, rect, surf, path, size, line_top, line_h) -> float:
        f = font(size, path)
        content = f.get_ascent() - f.get_descent()
        baseline = line_top + (line_h - content) / 2 + f.get_ascent()
        surface.blit(surf, (self._x_for(rect, surf.get_width()), round(baseline - f.get_ascent())))
        return baseline

    def _draw_theme(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        t = self.theme
        date_t, time_t, sec_t, week_t, gap, time_w, time_line, _w, _h, unit = self._theme_parts()
        y = float(rect.top)
        if date_t:
            self._blit_line(surface, rect, date_t, self.font, t.size("medium"), y, t.line("medium"))
            y += t.line("medium")
        # time: the raised seconds add their extra height above the baseline
        large = t.size("large")
        tf = font(large, self.time_font)
        extra = time_line - t.line("large")
        content = tf.get_ascent() - tf.get_descent()
        baseline = y + extra + (t.line("large") - content) / 2 + tf.get_ascent()
        x = self._x_for(rect, time_w)
        surface.blit(time_t, (x, round(baseline - tf.get_ascent())))
        if sec_t:
            sf = font(t.size("small"), self.time_font)
            digits_top = baseline - digit_height(tf) + THEME_SECONDS_DROP * unit
            sec_base = digits_top + digit_height(sf)
            surface.blit(sec_t, (x + time_t.get_width() + gap, round(sec_base - sf.get_ascent())))
        y += time_line
        if week_t:
            self._blit_line(surface, rect, week_t, self.font, t.size("medium"), y, t.line("medium"))

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        surface.fill(self.background, rect)
        if self.sizing == "theme":
            self._draw_theme(surface, rect)
            return
        inner = rect
        if inner.width <= 0 or inner.height <= 0:
            return

        date, time_text, secs, week = self._texts
        lay = self._layout_for(inner.width, inner.height, date, week)
        u = lay.unit
        y = float(inner.top)

        if date:
            y = self._line(surface, inner, y, date, lay.date_size, self.date_color, self.font)
            y += u * GAP_ABOVE_TIME

        # Time and seconds are placed as one unit.
        tf = font(lay.time_size, self.time_font)
        time_surf = self._time_surface(time_text, lay.time_size)
        total = time_surf.get_width()
        if secs:
            sf = font(lay.seconds_size, self.time_font)
            sec_surf = self._seconds_surface(secs, lay.seconds_size)
            gap = round(u * SECONDS_GAP)
            total += gap + sec_surf.get_width()
        x = self._x_for(inner, total)
        time_base = y + digit_height(tf)
        surface.blit(time_surf, (x, round(time_base - tf.get_ascent())))
        if secs:
            sec_base = y + u * SECONDS_DROP + digit_height(sf)
            surface.blit(sec_surf, (x + time_surf.get_width() + gap, round(sec_base - sf.get_ascent())))
        y = time_base

        if week:
            y += u * GAP_BELOW_TIME
            self._line(surface, inner, y, week, lay.week_size, self.week_color, self.font)
