# SPDX-License-Identifier: GPL-3.0-or-later
"""Calendar, like MagicMirror's default calendar module.

Ported from MagicMirror² (MIT, (c) Michael Teeuw); see THIRD_PARTY_NOTICES.md.

Reads one or more iCal (.ics) feeds: Google Calendar's "secret address in
iCal format", iCloud public calendars, Outlook/Office 365 published
calendars, Nextcloud and so on. Recurring events, exceptions and moved
occurrences are expanded by the recurring-ical-events library. Upcoming
events are listed with a symbol, title and MagicMirror's relative wording
("I dag", "Om 2 timmar", "På fredag 14:00").
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from functools import lru_cache

import pygame

from ..fetch import Poller, http_get, interval_option
from ..i18n import cap_first
from ..layout import Zone
from .base import Widget
from .clock import format_time
from .style import (ASSETS, BRIGHT, DIMMED, FONT_AWESOME, LIGHT, NORMAL, REGULAR, Text,
                    default_align, fade, fade_opacity, x_for)
from .text import font

log = logging.getLogger(__name__)


def _now() -> datetime:
    """Current local time (a function so tests can freeze it)."""
    return datetime.now().astimezone()

DEFAULT_SYMBOL = "calendar-days"


@lru_cache(maxsize=1)
def _fa_names() -> dict[str, str]:
    with open(ASSETS / "fa-solid-names.json", encoding="utf-8") as fh:
        return json.load(fh)


def symbol_char(name: str) -> str:
    """Font Awesome icon name (as in MagicMirror's config) -> character."""
    names = _fa_names()
    code = names.get(name.removeprefix("fa-")) or names[DEFAULT_SYMBOL]
    return chr(int(code, 16))


@dataclass(frozen=True)
class Event:
    title: str
    start: datetime  # aware, local time
    end: datetime
    all_day: bool
    symbol: str      # Font Awesome character
    source: int      # which calendar


# -- iCal parsing -----------------------------------------------------------------

def _local(value, is_end: bool = False) -> tuple[datetime, bool]:
    """DTSTART/DTEND value -> (aware local datetime, is_all_day)."""
    if isinstance(value, datetime):
        # Aware -> local; floating (no timezone) -> taken as local time.
        return value.astimezone(), False
    if isinstance(value, date):
        return datetime.combine(value, time.min).astimezone(), True
    raise ValueError(f"unexpected date value {value!r}")


def parse_ics(data: bytes | str, window_start: datetime, window_end: datetime,
              symbol: str, source: int) -> list[Event]:
    """All event occurrences overlapping the window, with recurrences expanded."""
    import icalendar
    import recurring_ical_events

    cal = icalendar.Calendar.from_ical(data)
    events = []
    for component in recurring_ical_events.of(cal).between(window_start, window_end):
        if str(component.get("STATUS", "")).upper() == "CANCELLED":
            continue
        start, all_day = _local(component.decoded("DTSTART"))
        if "DTEND" in component:
            end, _ = _local(component.decoded("DTEND"))
        elif "DURATION" in component:
            end = start + component.decoded("DURATION")
        else:
            end = start + (timedelta(days=1) if all_day else timedelta(0))
        title = " ".join(str(component.get("SUMMARY", "")).split())
        events.append(Event(title, start, end, all_day, symbol, source))
    return events


def fetch_calendar(url: str, days: int, symbol: str, source: int) -> list[Event]:
    now = _now()
    return parse_ics(http_get(url), now - timedelta(days=1), now + timedelta(days=days), symbol, source)


# -- MagicMirror's relative time text ---------------------------------------------

def _date(t: datetime, fmt: str | None, tr, capitalize: bool = False) -> str:
    """A far-away date: strftime ``fmt``, or MagicMirror's default "MMM Do" wording."""
    return format_time(fmt, t, capitalize) if fmt else tr.month_day(t)


def absolute_text(ev: Event, now: datetime, tr, date_format: str | None = None,
                  full_day_format: str | None = None, urgency: int = 7, get_relative: int = 6,
                  next_days_relative: bool = False, capitalize: bool = False) -> str:
    """Port of MagicMirror's calendar buildAbsoluteTimeText() (timeFormat "absolute")."""
    start, end = ev.start, ev.end
    if ev.all_day:
        text = cap_first(_date(start, full_day_format, tr, capitalize))
        last_day = (end - timedelta(seconds=1)).date()
        if last_day != start.date() and start < now:  # multi-day, already running
            text = cap_first(_date(now, full_day_format, tr, capitalize))
        if next_days_relative:
            offset = (start.date() - now.date()).days
            labels = {0: tr("TODAY"), 1: tr("TOMORROW"), 2: tr("DAYAFTERTOMORROW")}
            if labels.get(offset):
                text = cap_first(labels[offset])
        return text
    if get_relative > 0 and start < now:
        return cap_first(tr("RUNNING", tr.duration(end - now)))
    if urgency > 0 and int((start - now).total_seconds() // 86400) < urgency:
        return cap_first(tr.from_now(start, now))
    return cap_first(_date(start, date_format, tr, capitalize))


def relative_text(ev: Event, now: datetime, tr, get_relative: int = 6,
                  date_format: str | None = None, full_day_format: str | None = None,
                  capitalize: bool = False) -> str:
    """Port of MagicMirror's calendar buildRelativeTimeText() (default settings)."""
    start, end = ev.start, ev.end
    today = now.date()
    ends_today = ev.all_day and (end - now) < timedelta(days=1)  # moment diff(now, "days") == 0

    if start >= now or ends_today:
        if not ev.all_day:
            text = cap_first(tr.calendar(start, now, same_else=_date(start, date_format, tr, capitalize)))
            if (start - now) < timedelta(hours=get_relative):  # moment diff(now, "h") < getRelative
                text = cap_first(tr.from_now(start, now))
            return text

        offset = (start.date() - today).days
        category = tr.calendar_category(start, now)
        if category == "nextWeek":
            text = cap_first(start.strftime("%A"))
        elif category == "sameElse":
            text = cap_first(_date(start, full_day_format, tr, capitalize))
        else:
            text = ""
        if offset <= 0 or ends_today:
            text = tr("TODAY")
        elif offset == 1:
            text = tr("TOMORROW")
        elif offset == 2 and tr("DAYAFTERTOMORROW"):
            text = tr("DAYAFTERTOMORROW")
        return cap_first(text)

    # Already started: "Slutar om 2 timmar" / "Ends in 2 hours"
    return cap_first(tr("RUNNING", tr.duration(end - now)))


def shorten(title: str, max_length: int) -> str:
    """MagicMirror's CalendarUtils.shorten (no wrapping)."""
    title = title.strip()
    return f"{title[:max_length]}…" if max_length and len(title) > max_length else title


# -- widget -----------------------------------------------------------------------

class Calendar(Widget):
    refresh_interval = 60.0  # relative times ("om 2 timmar") change every minute

    def __init__(
        self,
        zone: Zone,
        calendars: list | None = None,     # [{url, symbol}], see config.toml
        url: str = "",                     # shorthand for a single calendar
        symbol: str = DEFAULT_SYMBOL,      # Font Awesome icon name
        header: str = "",
        maximum_entries: int = 10,
        maximum_number_of_days: int = 365,
        max_title_length: int = 25,
        get_relative: int = 6,             # hours: "Om 2 timmar" instead of a clock time
        display_symbol: bool = True,
        hide_duplicates: bool = True,
        fade: bool = True,
        fade_point: float = 0.25,
        fetch_interval: int = 3600,        # seconds
        align: str | None = None,
        time_format: str = "relative",     # or "absolute", like MagicMirror's timeFormat
        date_format: str | None = None,    # strftime for timed events; default like "MMM Do"
        full_day_event_date_format: str | None = None,  # e.g. "%a, %d %b" -> "Tor, 01 okt"
        urgency: int = 7,                  # absolute: days ahead that show "om 3 dagar"
        next_days_relative: bool = False,  # absolute: "I dag"/"I morgon" for full-day events
        table_class: str = "small",        # text size (MagicMirror's tableClass)
        cell_padding: dict | None = None,  # column spacing overrides (CSS px), see README
        capitalize_names: bool = False,    # "Tor, 01 Okt" instead of "Tor, 01 okt"
    ):
        super().__init__(zone)
        feeds = list(calendars or [])
        if url:
            feeds.insert(0, {"url": url})
        if not feeds or not all(isinstance(f, dict) and f.get("url") for f in feeds):
            raise ValueError('add at least one calendar: url = "https://…/basic.ics"')

        self.header = header
        self.maximum_entries = int(maximum_entries)
        self.max_title_length = int(max_title_length)
        self.get_relative = int(get_relative)
        self.display_symbol = bool(display_symbol)
        self.hide_duplicates = bool(hide_duplicates)
        self.fade = bool(fade)
        self.fade_point = float(fade_point)
        self.align = align or default_align(zone.col)
        if time_format not in ("relative", "absolute"):
            raise ValueError('time_format must be "relative" or "absolute"')
        self.time_format = time_format
        self.date_format = date_format
        self.full_day_format = full_day_event_date_format
        self.urgency = int(urgency)
        self.next_days_relative = bool(next_days_relative)
        self.table_class = table_class
        self.capitalize_names = bool(capitalize_names)
        # calendar.css: .title {padding: 0 10px} .time {padding-left: 20px}; others 1px
        self.cells = {"title_left": 10, "title_right": 10, "time_left": 20, **(cell_padding or {})}

        self.pollers = []
        for i, feed in enumerate(feeds):
            feed_url = feed["url"]
            char = symbol_char(feed.get("symbol", symbol))
            days = int(feed.get("maximum_number_of_days", maximum_number_of_days))
            interval = interval_option("fetch_interval", feed.get("fetch_interval", fetch_interval))
            fn = (lambda u=feed_url, d=days, c=char, n=i: fetch_calendar(u, d, c, n))
            self.pollers.append(Poller(f"calendar {i + 1}", fn, interval).start())
        self._rows: tuple = ()

    # -- state ----------------------------------------------------------------

    def _upcoming(self, now: datetime) -> tuple[list[Event], bool, str | None]:
        events, loading, error = [], False, None
        for poller in self.pollers:
            _, data, err = poller.snapshot()
            if data is None:
                loading = loading or err is None
                error = error or err
                continue
            events.extend(e for e in data if e.end > now)
        events.sort(key=lambda e: (e.start, e.source, e.title))
        if self.hide_duplicates:
            seen, unique = set(), []
            for e in events:
                key = (e.title, e.start, e.end)
                if key not in seen:
                    seen.add(key)
                    unique.append(e)
            events = unique
        return events[: self.maximum_entries], loading, error

    def update(self, now: float) -> bool:
        current = _now()
        events, loading, error = self._upcoming(current)
        if events:
            rows = tuple((e.symbol, shorten(e.title, self.max_title_length), self._when(e, current))
                         for e in events)
        elif loading:
            rows = ("message", self.tr("LOADING"))
        elif error:
            rows = ("message", self.tr(error))
        else:
            rows = ("message", self.tr("EMPTY"))
        changed = rows != self._rows
        self._rows = rows
        return changed

    def _when(self, e: Event, now: datetime) -> str:
        if self.time_format == "absolute":
            return absolute_text(e, now, self.tr, self.date_format, self.full_day_format,
                                 self.urgency, self.get_relative, self.next_days_relative,
                                 self.capitalize_names)
        return relative_text(e, now, self.tr, self.get_relative, self.date_format, self.full_day_format,
                             self.capitalize_names)

    # -- drawing --------------------------------------------------------------

    def _table(self, width: int | None = None):
        """Rows as Text cells plus column geometry (calendar.css)."""
        t, cls = self.theme, self.table_class
        size = t.size(cls)
        pad = t.cell_padding
        rows = []
        for i, (sym, title, when) in enumerate(self._rows):
            o = fade_opacity(i, len(self._rows), self.fade, self.fade_point)
            rows.append((Text(sym, size, fade(NORMAL, o), FONT_AWESOME) if self.display_symbol else None,
                         title, fade(BRIGHT, o), Text(when, size, fade(NORMAL, o), LIGHT)))
        # symbol: fa-fw box (1.25em) + default cell padding; title: 0 10px; time: 20px left, 1px right
        sym_w = (round(size * 1.25) + t.px(2 * pad)) if self.display_symbol else 0
        title_left, title_right = t.px(self.cells["title_left"]), t.px(self.cells["title_right"])
        time_left, time_right = t.px(self.cells["time_left"]), t.px(pad)
        time_w = max(r[3].width for r in rows)
        title_font = font(size, REGULAR)
        title_w = max(title_font.size(r[1])[0] for r in rows)
        fixed = sym_w + title_left + title_right + time_left + time_w + time_right
        if width is not None:
            title_w = max(0, min(title_w, width - fixed))  # squeeze titles if the zone is narrow
        return rows, sym_w, title_left, title_w, time_left, time_w, time_right, fixed + title_w

    def _message(self) -> Text:
        return Text(self._rows[1], self.theme.size(self.table_class), DIMMED, LIGHT)

    def size(self, width: int) -> tuple[int, int] | None:
        if not self._rows:
            return self.with_header(0, 0)
        if self._rows[0] == "message":
            return self.with_header(self._message().width, self.theme.line(self.table_class))
        table_w = self._table(width)[-1]
        return self.with_header(table_w, len(self._rows) * self.theme.row(self.table_class))

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        t = self.theme
        if not self._rows:
            surface.fill((0, 0, 0), rect)
            return
        if self._rows[0] == "message":
            text = self._message()
            y = self.begin(surface, rect, text.width)
            text.draw(surface, x_for(self.align, rect, text.width), text.baseline_in(y, t.line(self.table_class)))
            return

        rows, sym_w, title_pad, title_w, time_left, time_w, time_right, table_w = self._table(rect.width)
        y = self.begin(surface, rect, table_w)
        left = x_for(self.align, rect, table_w)
        size = t.size(self.table_class)
        row_h, pad, line_h = t.row(self.table_class), t.cell_padding * t.scale, t.line(self.table_class)
        title_font = font(size, REGULAR)
        title_col = pygame.Rect(left + sym_w + title_pad, 0, title_w, 0)
        for sym, title, title_color, when in rows:
            base = when.baseline_in(y + pad, line_h)
            if sym:
                sym.draw(surface, left + (sym_w - sym.width) / 2, base)     # fa-fw: centred in its box
            title_text = Text(self._fit(title, title_font, title_w), size, title_color, REGULAR)
            title_text.draw(surface, x_for(self.align, title_col, title_text.width), base)  # like the region
            when.draw(surface, left + table_w - time_right - when.width, base)            # right-aligned
            y += row_h

    @staticmethod
    def _fit(title: str, f: pygame.font.Font, width: int) -> str:
        """Trim with an ellipsis if the title still doesn't fit its column."""
        if f.size(title)[0] <= width:
            return title
        while title and f.size(title + "…")[0] > width:
            title = title[:-1]
        return title.rstrip() + "…" if title else ""
