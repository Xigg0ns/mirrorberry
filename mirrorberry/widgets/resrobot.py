# SPDX-License-Identifier: GPL-3.0-or-later
"""Public transport departures from Trafiklab, like MMM-ResRobot.

Ported from MMM-ResRobot (MIT, (c) Johan Alvinger); see THIRD_PARTY_NOTICES.md.

One table for all routes, earliest first:  time | icon | line | track | destination.
Two data sources, both need a free key from trafiklab.se:

* provider = "resrobot":  ResRobot v2.1 departureBoard, what MMM-ResRobot uses.
  Trafiklab has marked it deprecated in favour of:
* provider = "trafiklab": Trafiklab Realtime API (Timetables), the official
  replacement, with real-time data for most regions. Its data is CC-BY, so a
  small "Data från Trafiklab.se" line is shown under the table.

Differences from MMM-ResRobot, all small:
* real-time departure times and tracks are used when Trafiklab has them
  (SL and all train traffic); ``realtime = false`` shows timetable times only.
* each route is fetched on a fixed interval (default 5 min) to stay well
  inside the API quota; departed vehicles drop off the list every minute.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pygame

from ..fetch import AuthError, Poller, http_get, interval_option
from ..layout import Zone
from .base import Widget
from .calendar import symbol_char
from .text import font
from .style import (DIMMED, FONT_AWESOME, LIGHT, NORMAL, REGULAR, Text, default_align, fade,
                    fade_opacity, x_for)

log = logging.getLogger(__name__)

API = "https://api.resrobot.se/v2.1/departureBoard"
REALTIME_API = "https://realtime-api.trafiklab.se/v1/departures"
PROVIDERS = ("resrobot", "trafiklab")

# Trafiklab Realtime transport_mode -> the letters MMM-ResRobot's tables use
MODE_LETTER = {"BUS": "B", "TRAM": "S", "TRAIN": "J", "METRO": "U", "BOAT": "F", "TAXI": "T"}

def _ellipsize(text: str, f, width: int) -> str:
    """Shorten ``text`` with "…" until it fits ``width`` pixels."""
    if f.size(text)[0] <= width:
        return text
    while text and f.size(text.rstrip() + "…")[0] > width:
        text = text[:-1]
    return text.rstrip() + "…" if text else ""


# MMM-ResRobot's iconTable, keyed on the first letter of ProductAtStop.catOutS
# (B = buss, S = spårvagn, J = tåg, U = tunnelbana, F = färja), as Font Awesome names.
ICON_TABLE = {"B": "bus", "S": "train-subway", "J": "train", "U": "train-subway", "F": "ship", "T": "taxi"}
COLOR_TABLE = {"B": "#DA4439", "S": "#019CD5", "J": "#FDB813", "U": "#019CD5", "F": "#444400"}

try:
    SWEDEN = ZoneInfo("Europe/Stockholm")  # ResRobot times are Swedish local time
except ZoneInfoNotFoundError:  # no tzdata: fall back to the Pi's own timezone
    SWEDEN = None


def _now() -> datetime:
    """Current local time (a function so tests can freeze it)."""
    return datetime.now().astimezone()


@dataclass(frozen=True)
class Departure:
    when: datetime   # real-time if available, else timetable (local, aware)
    line: str
    track: str
    category: str    # catOutS, e.g. "BLT"
    to: str
    route: int


def build_url(api_key: str, stop: str, direction: str, duration: int, provider: str = "resrobot") -> str:
    if provider == "trafiklab":  # always the next 60 minutes; filtering happens here
        return f"{REALTIME_API}/{urllib.parse.quote(stop)}?{urllib.parse.urlencode({'key': api_key})}"
    params = {"format": "json", "passlist": "0", "accessId": api_key, "id": stop, "duration": str(duration)}
    if direction:
        params["direction"] = direction
    return f"{API}?{urllib.parse.urlencode(params)}"


def truncate_destination(name: str, after: int) -> str:
    """MMM-ResRobot: cut at the first space after ``after`` characters."""
    if after > 0:
        cut = name.find(" ", after)
        if cut > 0:
            return name[:cut]
    return name


def parse_departures(data: dict, route: int, realtime: bool = True,
                     truncate_after: int = 5, truncate_line_after: int = 5) -> list[Departure]:
    if "Departure" not in data and ("errorCode" in data or "errorText" in data):
        message = f"ResRobot: {data.get('errorCode', '')} {data.get('errorText', '')}".strip()
        raise (AuthError if "AUTH" in str(data.get("errorCode", "")).upper() else ValueError)(message)
    departures = []
    for d in data.get("Departure", []):
        product = d.get("ProductAtStop") or {}
        if realtime and d.get("rtTime"):
            day, clock, track = d.get("rtDate") or d["date"], d["rtTime"], d.get("rtTrack") or d.get("track") or ""
        else:
            day, clock, track = d["date"], d["time"], d.get("track") or d.get("rtTrack") or ""
        when = _local(f"{day}T{clock}")
        line = str(product.get("num") or product.get("displayNumber") or "")
        if truncate_line_after > 0:
            line = line[:truncate_line_after]
        departures.append(Departure(
            when=when, line=line, track=str(track), category=str(product.get("catOutS") or ""),
            to=truncate_destination(str(d.get("direction", "")), truncate_after), route=route,
        ))
    return departures


def _local(timestamp: str) -> datetime:
    """A Swedish local-time timestamp -> aware datetime in the Pi's timezone."""
    when = datetime.fromisoformat(timestamp)
    return when.replace(tzinfo=SWEDEN).astimezone() if SWEDEN else when.astimezone()


def parse_realtime(data: dict, route: int, realtime: bool = True, truncate_after: int = 5,
                   truncate_line_after: int = 5, show_canceled: bool = False) -> list[Departure]:
    """Trafiklab Realtime API (Timetables) -> departures."""
    departures = []
    for d in data.get("departures", []):
        if d.get("canceled") and not show_canceled:
            continue
        r = d.get("route") or {}
        stamp = d.get("realtime") if realtime else None
        platform = (d.get("realtime_platform") if realtime else None) or d.get("scheduled_platform") or {}
        line = str(r.get("designation") or r.get("name") or "")
        if truncate_line_after > 0:
            line = line[:truncate_line_after]
        departures.append(Departure(
            when=_local(stamp or d["scheduled"]), line=line, track=str(platform.get("designation") or ""),
            category=MODE_LETTER.get(str(r.get("transport_mode", "")).upper(), ""),
            to=truncate_destination(str(r.get("direction") or (r.get("destination") or {}).get("name", "")),
                                    truncate_after),
            route=route,
        ))
    return departures


def fetch_departures(url: str, route: int, realtime: bool, truncate_after: int,
                     truncate_line_after: int, provider: str = "resrobot") -> list[Departure]:
    data = json.loads(http_get(url))
    if provider == "trafiklab":
        return parse_realtime(data, route, realtime, truncate_after, truncate_line_after)
    return parse_departures(data, route, realtime, truncate_after, truncate_line_after)


class ResRobot(Widget):
    refresh_interval = 60.0  # re-check each minute: departed vehicles drop off, "5 min" counts down

    def __init__(
        self,
        zone: Zone,
        api_key: str = "",
        provider: str = "resrobot",        # or "trafiklab" (Trafiklab Realtime API)
        routes: list | None = None,       # [{from = "740…", to = "740…"}]; "to" is ResRobot-only
        lines: list | None = None,        # only these line numbers, e.g. ["4", "19"]
        destinations: list | None = None,  # only destinations containing any of these texts
        header: str = "",
        maximum_entries: int = 6,
        maximum_duration: int = 360,       # minutes ahead to ask for
        skip_minutes: int = 0,             # hide departures leaving within this many minutes
        truncate_after: int = 5,           # destination: cut at first space after N characters (0 = off)
        truncate_line_after: int = 5,      # line number: at most N characters (0 = off)
        show_track: bool = True,
        get_relative: int = 0,             # show "5 min"/"Nu" when fewer than N minutes left (0 = off)
        colored_icons: bool = False,
        icon_table: dict | None = None,
        color_table: dict | None = None,
        realtime: bool = True,
        fade: bool = True,
        fade_point: float = 0.25,
        update_interval: int = 300,        # seconds between fetches per route
        align: str | None = None,
        table_class: str = "small",        # text size
        column_widths: list | None = None, # minimum [time, icon, line, track] widths, CSS px
    ):
        super().__init__(zone)
        if provider not in PROVIDERS:
            raise ValueError(f"provider must be one of {PROVIDERS}, got {provider!r}")
        if not api_key or api_key.startswith("<"):
            which = "Trafiklab Realtime API" if provider == "trafiklab" else "Trafiklab ResRobot v2.1"
            raise ValueError(f"set api_key to your {which} key")
        routes = list(routes or [])
        if not routes or not all(isinstance(r, dict) and r.get("from") for r in routes):
            raise ValueError('add at least one route: [[zones.X.routes]] with from = "740…"')

        self.header = header
        self.provider = provider
        self.lines = {str(x) for x in lines} if lines else None
        self.destinations = [str(x).lower() for x in destinations] if destinations else None
        self.maximum_entries = int(maximum_entries)
        self.skip_minutes = int(skip_minutes)
        self.show_track = bool(show_track)
        self.get_relative = int(get_relative)
        self.colored_icons = bool(colored_icons)
        self.icon_table = {**ICON_TABLE, **(icon_table or {})}
        self.color_table = {**COLOR_TABLE, **(color_table or {})}
        self.fade = bool(fade)
        self.fade_point = float(fade_point)
        self.align = align or default_align(zone.col)
        self.table_class = table_class
        self.column_widths = [float(w) for w in (column_widths or [])] + [0.0] * 4

        self.pollers = []
        interval = interval_option("update_interval", update_interval)
        for i, route in enumerate(routes):
            url = build_url(api_key, str(route["from"]), str(route.get("to") or ""), int(maximum_duration), provider)
            fn = (lambda u=url, n=i: fetch_departures(u, n, bool(realtime), int(truncate_after),
                                                      int(truncate_line_after), provider))
            self.pollers.append(Poller(f"{provider} route {i + 1}", fn, interval).start())
        self._rows: tuple = ()

    # -- state ----------------------------------------------------------------

    def _wanted(self, dep: Departure) -> bool:
        if self.lines is not None and dep.line not in self.lines:
            return False
        if self.destinations is not None and not any(t in dep.to.lower() for t in self.destinations):
            return False
        return True

    def _time_text(self, dep: Departure, now: datetime) -> str:
        waiting = int((dep.when - now).total_seconds() // 60)  # moment diff(now, "minutes")
        if waiting < self.get_relative:
            return f"{waiting} {self.tr('MINUTES_SHORT')}" if waiting > 1 else self.tr("NOW")
        return dep.when.strftime("%H:%M")

    def update(self, now: float) -> bool:
        current = _now()
        cutoff = current + timedelta(minutes=self.skip_minutes)
        departures, loading, error = [], False, None
        for poller in self.pollers:
            _, data, err = poller.snapshot()
            if data is None:
                loading = loading or err is None
                error = error or err
                continue
            departures.extend(d for d in data if d.when >= cutoff and self._wanted(d))
        departures.sort(key=lambda d: (d.when, d.route))
        departures = departures[: self.maximum_entries]

        if departures:
            rows = tuple((self._time_text(d, current), d.category[:1], d.line, d.track, d.to) for d in departures)
        elif loading:
            rows = ("message", self.tr("DEPARTURES_LOADING"))
        elif error:
            rows = ("message", self.tr(error))
        else:
            rows = ()
        changed = rows != self._rows
        self._rows = rows
        return changed

    # -- layout / drawing ---------------------------------------------------------

    def _table(self, width: int | None = None):
        """Cells and column geometry. MMM-ResRobot.css: 10px right padding after time, line
        and track; the browser's 1px elsewhere. Cell text follows the region's alignment.
        If the table is wider than ``width``, destinations are shortened with an ellipsis."""
        t, cls = self.theme, self.table_class
        size = t.size(cls)
        cells = []
        for i, (when, kind, line, track, to) in enumerate(self._rows):
            o = fade_opacity(i, len(self._rows), self.fade, self.fade_point)
            icon_name = self.icon_table.get(kind)
            icon_color = pygame.Color(self.color_table[kind]) if (
                self.colored_icons and kind in self.color_table) else NORMAL
            cells.append((
                Text(when, size, fade(NORMAL, o)),
                Text(symbol_char(icon_name), size, fade(tuple(icon_color)[:3], o), FONT_AWESOME) if icon_name else None,
                Text(line, size, fade(NORMAL, o)),
                Text(track or " ", size, fade(NORMAL, o)) if self.show_track else None,
                Text(to, size, fade(NORMAL, o), REGULAR),
            ))
        p1, p10 = t.px(t.cell_padding), t.px(10)
        right_pad = [p10, p1, p10, p10, p1]
        keys = [k for k in range(5) if k != 3 or self.show_track]
        natural = {k: p1 + max((c[k].width for c in cells if c[k]), default=0) + right_pad[k] for k in keys}
        widths = {k: max(natural[k], t.px(self.column_widths[k]) if k < 4 and self.column_widths[k] else 0)
                  for k in keys}
        if width is not None and sum(widths.values()) > width:
            # Too wide for the zone: like a browser, let padded-out columns give way first...
            overflow = sum(widths.values()) - width
            for k in (2, 3, 1, 0):
                if k in widths and overflow > 0:
                    give = min(widths[k] - natural[k], overflow)
                    widths[k] -= give
                    overflow -= give
            # ...and only then shorten destinations with an ellipsis.
            if overflow > 0:
                widths[4] = max(p1 * 2, widths[4] - overflow)
                room = widths[4] - 2 * p1
                f = font(size, REGULAR)
                fitted = []
                for i, (c, row) in enumerate(zip(cells, self._rows)):
                    o = fade_opacity(i, len(self._rows), self.fade, self.fade_point)
                    fitted.append(c[:4] + (Text(_ellipsize(row[4], f, room), size, fade(NORMAL, o), REGULAR),))
                cells = fitted
        cols = []  # (k, content x, content width)
        x = 0
        for k in keys:
            cols.append((k, x + p1, widths[k] - p1 - right_pad[k]))
            x += widths[k]
        return cells, cols, x

    def _message(self) -> Text:
        return Text(self._rows[1], self.theme.size(self.table_class), DIMMED, LIGHT)

    def _credit(self) -> Text | None:
        if self.provider != "trafiklab":
            return None
        return Text(self.tr("TRAFIKLAB_CREDIT"), self.theme.size("xsmall"), DIMMED, LIGHT)

    def size(self, width: int) -> tuple[int, int] | None:
        t = self.theme
        if not self._rows:
            return self.with_header(0, 0)
        if self._rows[0] == "message":
            return self.with_header(self._message().width, t.line(self.table_class))
        cells, _, table_w = self._table(width)
        credit = self._credit()
        height = len(cells) * t.row(self.table_class) + (t.line("xsmall") if credit else 0)
        return self.with_header(max(table_w, credit.width if credit else 0), height)

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

        cells, cols, table_w = self._table(rect.width)
        y = self.begin(surface, rect, table_w)
        left = x_for(self.align, rect, table_w)
        row_h, pad, line_h = t.row(self.table_class), t.cell_padding * t.scale, t.line(self.table_class)
        for row in cells:
            base = row[0].baseline_in(y + pad, line_h)
            for k, x, width in cols:
                cell = row[k]
                if cell is None:
                    continue
                align = "center" if k == 1 else self.align  # icons centred, text like the region
                cell.draw(surface, x_for(align, pygame.Rect(left + x, 0, width, 0), cell.width), base)
            y += row_h

        credit = self._credit()  # CC-BY: credit Trafiklab on the display
        if credit:
            credit.draw(surface, x_for(self.align, pygame.Rect(left, 0, table_w, 0), credit.width),
                        credit.baseline_in(y, t.line("xsmall")))
