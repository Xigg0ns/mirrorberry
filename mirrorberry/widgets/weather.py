# SPDX-License-Identifier: GPL-3.0-or-later
"""Weather, like MagicMirror's default weather module.

Ported from MagicMirror² (MIT, (c) Michael Teeuw); see THIRD_PARTY_NOTICES.md.

Two data sources, both free without an API key:

* provider = "smhi":      SMHI's SNOW1gv1 point forecast (Sweden and the
                          Nordic area), processed exactly like MagicMirror's
                          smhi provider.
* provider = "openmeteo": Open-Meteo, worldwide.

Two layouts:

* type = "current":   wind + next sunrise/sunset, big icon and temperature,
                       "feels like" underneath.
* type = "forecast":  one row per day: day, icon, max, min, fading out.

Widgets for the same place and provider share one download.
"""

from __future__ import annotations

import json
import logging
import math
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pygame

from ..fetch import Poller, http_get, interval_option
from ..sun import is_daytime, sun_times
from ..layout import Zone
from .base import Widget
from .clock import format_time
from .style import (BRIGHT, DIMMED, LIGHT, NORMAL, REGULAR, WEATHER_ICONS, Text, default_align,
                    fade, fade_opacity, x_for)

log = logging.getLogger(__name__)


def _now() -> datetime:
    """Current local time (a function so tests can freeze it)."""
    return datetime.now().astimezone()

API = "https://api.open-meteo.com/v1/forecast"

# Weather Icons codepoints (erikflowers/weather-icons CSS)
ICONS = {
    "day-sunny": "\uf00d", "night-clear": "\uf02e", "day-cloudy": "\uf002", "night-alt-cloudy": "\uf086",
    "day-sunny-overcast": "\uf00c", "night-alt-partly-cloudy": "\uf081", "day-fog": "\uf003", "night-fog": "\uf04a",
    "day-sprinkle": "\uf00b", "night-sprinkle": "\uf039", "day-showers": "\uf009", "night-showers": "\uf037",
    "day-thunderstorm": "\uf010", "night-thunderstorm": "\uf03b", "day-rain-mix": "\uf006", "night-rain-mix": "\uf034",
    "snowflake-cold": "\uf076", "day-sleet": "\uf0b2", "night-sleet": "\uf0b3", "day-snow-wind": "\uf065",
    "night-snow-wind": "\uf066", "day-snow-thunderstorm": "\uf06b", "night-snow-thunderstorm": "\uf06c",
    "day-sleet-storm": "\uf068", "night-sleet-storm": "\uf069", "na": "\uf07b",
    "strong-wind": "\uf050", "sunrise": "\uf051", "sunset": "\uf052",
    # used by the SMHI mapping
    "night-partly-cloudy": "\uf083", "night-cloudy": "\uf031", "cloudy": "\uf013", "fog": "\uf014",
    "showers": "\uf01a", "thunderstorm": "\uf01e", "sleet": "\uf0b5", "snow": "\uf01b", "rain": "\uf019",
}

# WMO code -> (day icon, night icon); the same table as MagicMirror's openmeteo provider.
WMO_ICONS = {
    0: ("day-sunny", "night-clear"),
    1: ("day-cloudy", "night-alt-cloudy"), 2: ("day-cloudy", "night-alt-cloudy"),
    3: ("day-sunny-overcast", "night-alt-partly-cloudy"),
    45: ("day-fog", "night-fog"), 48: ("day-fog", "night-fog"),
    51: ("day-sprinkle", "night-sprinkle"), 61: ("day-sprinkle", "night-sprinkle"),
    80: ("day-sprinkle", "night-sprinkle"),
    53: ("day-showers", "night-showers"), 63: ("day-showers", "night-showers"),
    81: ("day-showers", "night-showers"),
    55: ("day-thunderstorm", "night-thunderstorm"), 65: ("day-thunderstorm", "night-thunderstorm"),
    82: ("day-thunderstorm", "night-thunderstorm"),
    66: ("day-rain-mix", "night-rain-mix"),
    56: ("snowflake-cold", "snowflake-cold"), 57: ("snowflake-cold", "snowflake-cold"),
    77: ("day-sleet", "night-sleet"),
    71: ("day-snow-wind", "night-snow-wind"), 73: ("day-snow-wind", "night-snow-wind"),
    75: ("day-snow-thunderstorm", "night-snow-thunderstorm"),
    67: ("day-snow-thunderstorm", "night-snow-thunderstorm"),
    85: ("day-rain-mix", "night-rain-mix"), 86: ("day-rain-mix", "night-rain-mix"),
    95: ("day-thunderstorm", "night-thunderstorm"),
    96: ("day-sleet", "night-sleet"), 99: ("day-sleet-storm", "night-sleet-storm"),
}


# SMHI symbol_code (1-27) -> (day icon, night icon); MagicMirror's smhi provider mapping.
SMHI_ICONS = {
    1: ("day-sunny", "night-clear"),
    2: ("day-sunny-overcast", "night-partly-cloudy"),
    3: ("day-cloudy", "night-cloudy"), 4: ("day-cloudy", "night-cloudy"),
    **{c: ("cloudy", "cloudy") for c in (5, 6)},
    7: ("fog", "fog"),
    **{c: ("showers", "showers") for c in (8, 9, 10)},
    **{c: ("thunderstorm", "thunderstorm") for c in (11, 21)},
    **{c: ("sleet", "sleet") for c in (12, 13, 14, 22, 23, 24)},
    **{c: ("snow", "snow") for c in (15, 16, 17, 25, 26, 27)},
    **{c: ("rain", "rain") for c in (18, 19, 20)},
}


def wmo_icon(code: int | None, is_day: bool = True) -> str:
    pair = WMO_ICONS.get(code if code is not None else -1)
    return pair[0 if is_day else 1] if pair else "na"


def smhi_icon(code: int | None, is_day: bool = True) -> str:
    pair = SMHI_ICONS.get(code if code is not None else -1)
    return pair[0 if is_day else 1] if pair else "na"


# -- data -------------------------------------------------------------------------

@dataclass(frozen=True)
class Day:
    date: datetime
    icon: str        # Weather Icons name, e.g. "day-cloudy"
    t_max: float | None
    t_min: float | None
    sunrise: datetime | None
    sunset: datetime | None


@dataclass(frozen=True)
class Report:
    time: datetime
    temperature: float | None
    feels_like: float | None
    icon: str
    wind_speed: float | None
    wind_direction: float | None
    days: tuple[Day, ...]


PROVIDERS = ("smhi", "openmeteo")


def build_url(provider: str, latitude: float, longitude: float, days: int = 7) -> str:
    if provider == "smhi":
        return ("https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/"
                f"geotype/point/lon/{longitude:.6f}/lat/{latitude:.6f}/data.json")
    params = {
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "current": "temperature_2m,apparent_temperature,weather_code,is_day,wind_speed_10m,wind_direction_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset",
        "timezone": "auto",
        "wind_speed_unit": "ms",
        "forecast_days": str(max(2, min(16, days))),
    }
    return f"{API}?{urllib.parse.urlencode(params, safe=',')}"


# -- Open-Meteo -------------------------------------------------------------------

def parse_openmeteo(data: dict) -> Report:
    """Open-Meteo JSON -> Report, with times as aware datetimes in the place's timezone."""
    tz = timezone(timedelta(seconds=int(data.get("utc_offset_seconds", 0))))

    def when(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value).replace(tzinfo=tz) if value else None

    cur = data["current"]
    daily = data.get("daily", {})
    columns = [daily.get(k, []) for k in ("time", "weather_code", "temperature_2m_max",
                                          "temperature_2m_min", "sunrise", "sunset")]
    days = tuple(
        Day(when(t), wmo_icon(code, True), tmax, tmin, when(rise), when(sset))
        for t, code, tmax, tmin, rise, sset in zip(*columns)
    )
    return Report(
        time=when(cur["time"]),
        temperature=cur.get("temperature_2m"),
        feels_like=cur.get("apparent_temperature"),
        icon=wmo_icon(cur.get("weather_code"), bool(cur.get("is_day", 1))),
        wind_speed=cur.get("wind_speed_10m"),
        wind_direction=cur.get("wind_direction_10m"),
        days=days,
    )


# -- SMHI (port of MagicMirror's providers/smhi.js, SNOW1gv1) ----------------------

def _smhi_value(entry: dict, name: str):
    """A parameter, or None if missing (SMHI marks missing values with 9999)."""
    value = entry.get("data", {}).get(name)
    return None if value is None or value == 9999 else value


def _smhi_feels_like(entry: dict) -> float | None:
    """Apparent temperature from temperature, humidity and wind, as MagicMirror computes it."""
    ta = _smhi_value(entry, "air_temperature")
    rh = _smhi_value(entry, "relative_humidity")
    ws = _smhi_value(entry, "wind_speed")
    if ta is None or rh is None or ws is None:
        return ta
    vapour = (rh / 100) * 6.105 * math.exp((17.27 * ta) / (237.7 + ta))
    return ta + 0.33 * vapour - 0.7 * ws - 4


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_smhi(data: dict, now: datetime, latitude: float, longitude: float) -> Report:
    series = data.get("timeSeries")
    if not isinstance(series, list) or not series:
        raise ValueError("SMHI response has no timeSeries")
    coords = (data.get("geometry") or {}).get("coordinates")
    if isinstance(coords, list) and len(coords) >= 2 and isinstance(coords[0], (int, float)):
        longitude, latitude = coords[0], coords[1]  # the grid point SMHI actually used

    def icon_at(entry: dict, t: datetime) -> str:
        rise, sset = sun_times(t, latitude, longitude)
        return smhi_icon(_smhi_value(entry, "symbol_code"), is_daytime(t, rise, sset))

    # Current: the forecast step closest to now.
    current = min(series, key=lambda e: abs((_utc(e["time"]) - now).total_seconds()))
    t_cur = _utc(current["time"])

    # Forecast: fill gaps to hourly steps (SMHI steps are 1, 3, 6 or 12 hours),
    # then group by local day: min/max temperature and the middle daytime symbol.
    hourly: list[tuple[datetime, dict]] = [(_utc(series[0]["time"]), series[0])]
    for prev, entry in zip(series, series[1:]):
        t_prev, t_next = _utc(prev["time"]), _utc(entry["time"])
        for j in range(1, int((t_next - t_prev).total_seconds() // 3600)):
            hourly.append((t_prev + timedelta(hours=j), prev))
        hourly.append((t_next, entry))

    groups: list[dict] = []
    for t, entry in hourly:
        local = t.astimezone()
        if not groups or groups[-1]["date"].date() != local.date():
            rise, sset = sun_times(t, latitude, longitude)
            groups.append({"date": local, "temps": [], "day_icons": [], "icon": "na",
                           "sunrise": rise, "sunset": sset})
        g = groups[-1]
        rise, sset = sun_times(t, latitude, longitude)
        icon = smhi_icon(_smhi_value(entry, "symbol_code"), is_daytime(t, rise, sset))
        if is_daytime(t, rise, sset):
            g["day_icons"].append(icon)
        g["icon"] = g["day_icons"][len(g["day_icons"]) // 2] if g["day_icons"] else icon
        temp = _smhi_value(entry, "air_temperature")
        if temp is not None:
            g["temps"].append(temp)

    days = tuple(
        Day(g["date"], g["icon"], max(g["temps"], default=None), min(g["temps"], default=None),
            g["sunrise"], g["sunset"])
        for g in groups
    )
    return Report(
        time=t_cur,
        temperature=_smhi_value(current, "air_temperature"),
        feels_like=_smhi_feels_like(current),
        icon=icon_at(current, t_cur),
        wind_speed=_smhi_value(current, "wind_speed"),
        wind_direction=_smhi_value(current, "wind_from_direction"),
        days=days,
    )


def fetch_report(url: str, provider: str, latitude: float, longitude: float) -> Report:
    data = json.loads(http_get(url))
    if provider == "smhi":
        return parse_smhi(data, _now(), latitude, longitude)
    return parse_openmeteo(data)


# -- widget -----------------------------------------------------------------------

class Weather(Widget):
    refresh_interval = 60.0  # re-check each minute: sunrise/sunset flips, "today" rolls over

    def __init__(
        self,
        zone: Zone,
        type: str = "current",           # "current" or "forecast"
        provider: str = "openmeteo",      # "smhi" (Sweden/Nordics) or "openmeteo" (worldwide)
        latitude: float | None = None,
        longitude: float | None = None,
        header: str = "",
        max_days: int = 5,                # forecast rows, including today
        ignore_today: bool = False,
        round_temp: bool = False,         # 12° instead of 12.3°
        decimal_symbol: str = ".",
        show_feels_like: bool = True,
        show_sun: bool = True,
        show_wind_direction: bool = True,
        colored: bool = False,            # forecast: red max, blue min
        capitalize_names: bool = False,   # "Tis" instead of "tis"
        fade: bool = True,
        fade_point: float = 0.25,
        update_interval: int = 600,       # seconds
        align: str | None = None,         # default follows the zone's column
        table_class: str = "small",       # forecast text size (MagicMirror's tableClass)
        forecast_date_format: str = "%a", # forecast day names after I dag / I morgon
        cell_padding: dict | None = None, # forecast column spacing overrides, see README
        temp_gap: float = 10,             # current: icon -> temperature (MagicMirror: flex gap 10px)
    ):
        super().__init__(zone)
        if type not in ("current", "forecast"):
            raise ValueError(f'type must be "current" or "forecast", got {type!r}')
        if provider not in PROVIDERS:
            raise ValueError(f"provider must be one of {PROVIDERS}, got {provider!r}")
        if latitude is None or longitude is None:
            raise ValueError("set latitude and longitude (decimal degrees)")
        self.type = type
        self.header = header
        self.max_days = int(max_days)
        self.ignore_today = bool(ignore_today)
        self.round_temp = bool(round_temp)
        self.decimal_symbol = decimal_symbol
        self.show_feels_like = bool(show_feels_like)
        self.show_sun = bool(show_sun)
        self.show_wind_direction = bool(show_wind_direction)
        self.colored = bool(colored)
        self.capitalize_names = bool(capitalize_names)
        self.fade = bool(fade)
        self.fade_point = float(fade_point)
        self.align = align or default_align(zone.col)
        self.table_class = table_class
        self.forecast_date_format = forecast_date_format
        # MagicMirror weather.css: .day {padding-right: 25px} .weather-icon {padding-right: 30px}
        # .min-temp {padding-left: 20px}; other sides get the browser's 1px.
        self.cells = {"day_right": 25, "icon_left": 1, "icon_right": 30, "max_left": 1,
                      "max_right": 1, "min_left": 20, **(cell_padding or {})}
        self.temp_gap = float(temp_gap)

        lat, lon = float(latitude), float(longitude)
        url = build_url(provider, lat, lon, self.max_days + 2)
        self.poller = Poller.shared(url, f"weather ({provider}) {lat},{lon}",
                                    lambda: fetch_report(url, provider, lat, lon),
                                    interval_option("update_interval", update_interval)).start()
        self._seen = -1
        self._report: Report | None = None
        self._error: str | None = None
        self._view: tuple = ()

    # -- state ----------------------------------------------------------------

    def update(self, now: float) -> bool:
        version, report, error = self.poller.snapshot()
        if version != self._seen:
            self._seen, self._report, self._error = version, report, error
        view = self._build_view(_now())
        changed = view != self._view
        self._view = view
        return changed

    def temp(self, value: float | None) -> str:
        """MagicMirror's roundValue + degree sign."""
        if value is None:
            return ""
        text = f"{value:.0f}" if self.round_temp else f"{value:.1f}"
        if text in ("-0", "-0.0"):
            text = text[1:]
        return text.replace(".", self.decimal_symbol) + "°"

    def _build_view(self, now: datetime) -> tuple:
        """Everything that's on screen, as plain values; a change means redraw."""
        r = self._report
        if r is None:
            return ("message", self.tr(self._error or "LOADING"))
        if self.type == "current":
            return self._current_view(r, now)
        return self._forecast_view(r, now)

    def _current_view(self, r: Report, now: datetime) -> tuple:
        wind = "" if r.wind_speed is None else str(round(r.wind_speed))
        direction = self.tr.cardinal(r.wind_direction) if (
            self.show_wind_direction and r.wind_direction is not None) else ""
        sun_icon = sun_time = ""
        if self.show_sun:
            # Next event: sunset while the sun is up, otherwise the next sunrise.
            events = [(d.sunrise, "sunrise") for d in r.days if d.sunrise] + \
                     [(d.sunset, "sunset") for d in r.days if d.sunset]
            upcoming = sorted((t, k) for t, k in events if t > now)
            if upcoming:
                t, kind = upcoming[0]
                sun_icon, sun_time = ICONS[kind], self.tr.time(t.astimezone())
        feels = self.tr("FEELS", self.temp(r.feels_like)) if (
            self.show_feels_like and r.feels_like is not None) else ""
        return ("current", wind, direction, sun_icon, sun_time,
                ICONS.get(r.icon, ICONS["na"]), self.temp(r.temperature), feels)

    def _forecast_view(self, r: Report, now: datetime) -> tuple:
        today = now.date()
        days = [d for d in r.days if d.date.astimezone().date() >= today]
        if self.ignore_today:
            days = [d for d in days if d.date.astimezone().date() > today]
        rows = []
        for i, d in enumerate(days[: self.max_days]):
            offset = (d.date.astimezone().date() - today).days
            if offset == 0:
                label = self.tr("TODAY")
            elif offset == 1:
                label = self.tr("TOMORROW")
            else:
                label = format_time(self.forecast_date_format, d.date, self.capitalize_names).rstrip(".")
            rows.append((label, ICONS.get(d.icon, ICONS["na"]), self.temp(d.t_max), self.temp(d.t_min)))
        return ("forecast", tuple(rows))

    # -- layout -----------------------------------------------------------------

    def _current_parts(self):
        """current.njk's lines: pieces separated by spaces, like the HTML's whitespace."""
        _, wind, direction, sun_icon, sun_time, icon, temp, feels = self._view
        t = self.theme
        med = t.size("medium")
        space = Text(" ", med, NORMAL).width
        line1: list = []  # (Text, raise_px) or (None, spacing)
        if wind:
            line1 += [(Text(ICONS["strong-wind"], med, DIMMED, WEATHER_ICONS), 0), (None, space),
                      (Text(wind, med, NORMAL), 0)]
            if direction:  # " <sup>S&nbsp;</sup>": half size, raised, trailing no-break space
                sup = round(med * 0.5)
                line1 += [(None, space), (Text(direction, sup, NORMAL), round(med * 0.33)),
                          (None, Text(" ", sup, NORMAL).width)]
        if sun_icon:
            if line1:
                line1.append((None, space))
            line1 += [(Text(sun_icon, med, DIMMED, WEATHER_ICONS), 0), (None, space),
                      (Text(sun_time, med, NORMAL), 0)]
        large = t.size("large")
        big_icon = Text(icon, round(large * 0.75), NORMAL, WEATHER_ICONS)
        big_temp = Text(temp, large, BRIGHT, LIGHT, t.spacing("large"))
        line3 = Text(feels, med, DIMMED) if feels else None
        return line1, big_icon, big_temp, line3

    def _current_size(self) -> tuple[float, float]:
        line1, big_icon, big_temp, line3 = self._current_parts()
        t = self.theme
        w1 = sum(item.width if item else value for item, value in line1)
        w2 = big_icon.width + t.px(self.temp_gap) + big_temp.width
        width = max(w1, w2, line3.width if line3 else 0)
        height = (t.line("medium") if line1 else 0) + t.line("large") + (t.line("medium") if line3 else 0)
        return width, height

    def _forecast_cells(self):
        rows = self._view[1]
        t, cls = self.theme, self.table_class
        size = t.size(cls)
        max_color = (0xFF, 0x8E, 0x99) if self.colored else BRIGHT
        min_color = (0xBC, 0xDD, 0xFF) if self.colored else NORMAL
        cells = []
        for i, (label, icon, t_max, t_min) in enumerate(rows):
            o = fade_opacity(i, len(rows), self.fade, self.fade_point)
            cells.append((
                Text(label, size, fade(NORMAL, o)),
                Text(icon, round(size * 0.75), fade(BRIGHT, o), WEATHER_ICONS),
                Text(t_max, size, fade(max_color, o)),
                Text(t_min, size, fade(min_color, o)),
            ))
        widths = [max((c[k].width for c in cells), default=0) for k in range(4)]
        c = {k: t.px(v) if v else 0 for k, v in self.cells.items()}
        # column start positions (content edges), relative to the table's left edge
        x_day = 0
        x_icon = widths[0] + c["day_right"] + c["icon_left"]
        x_max = x_icon + widths[1] + c["icon_right"] + c["max_left"]
        x_min = x_max + widths[2] + c["max_right"] + c["min_left"]
        table_w = x_min + widths[3]
        return cells, widths, (x_day, x_icon, x_max, x_min), table_w

    def size(self, width: int) -> tuple[int, int] | None:
        kind = self._view[0] if self._view else "message"
        if kind == "current":
            return self.with_header(*self._current_size())
        if kind == "forecast":
            cells, _, _, table_w = self._forecast_cells()
            return self.with_header(table_w, len(cells) * self.theme.row(self.table_class))
        text = Text(self._view[1] if self._view else "", self.theme.size("small"), DIMMED, LIGHT)
        return self.with_header(text.width, self.theme.line("small"))

    # -- drawing --------------------------------------------------------------

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        kind = self._view[0] if self._view else "message"
        if kind == "current":
            self._draw_current(surface, rect)
        elif kind == "forecast":
            self._draw_forecast(surface, rect)
        else:
            text = Text(self._view[1] if self._view else "", self.theme.size("small"), DIMMED, LIGHT)
            y = self.begin(surface, rect, text.width)
            text.draw(surface, x_for(self.align, rect, text.width), text.baseline_in(y, self.theme.line("small")))

    def _draw_current(self, surface, rect) -> None:
        line1, big_icon, big_temp, line3 = self._current_parts()
        t = self.theme
        width, _ = self._current_size()
        y = self.begin(surface, rect, width)
        med_lh = t.line("medium")

        if line1:
            base = Text("0", t.size("medium"), NORMAL).baseline_in(y, med_lh)
            w1 = sum(item.width if item else value for item, value in line1)
            x = x_for(self.align, rect, w1)
            for item, value in line1:
                if item is None:
                    x += value
                    continue
                item.draw(surface, x, base - value)
                x += item.width
            y += med_lh

        large_lh = t.line("large")
        base = big_temp.baseline_in(y, large_lh)
        gap = t.px(self.temp_gap)
        w2 = big_icon.width + gap + big_temp.width
        x = x_for(self.align, rect, w2)
        big_icon.draw(surface, x, base)
        big_temp.draw(surface, x + big_icon.width + gap, base)
        y += large_lh

        if line3:
            line3.draw(surface, x_for(self.align, rect, line3.width), line3.baseline_in(y, med_lh))

    def _draw_forecast(self, surface, rect) -> None:
        cells, widths, (x_day, x_icon, x_max, x_min), table_w = self._forecast_cells()
        t = self.theme
        y = self.begin(surface, rect, table_w)
        left = x_for(self.align, rect, table_w)
        row_h, pad = t.row(self.table_class), t.cell_padding * t.scale
        line_h = t.line(self.table_class)
        for day, icon, t_max, t_min in cells:
            base = day.baseline_in(y + pad, line_h)
            day.draw(surface, left + x_day, base)
            icon.draw(surface, left + x_icon + (widths[1] - icon.width) / 2, base)   # centred
            t_max.draw(surface, left + x_max + widths[2] - t_max.width, base)       # right-aligned
            t_min.draw(surface, left + x_min + widths[3] - t_min.width, base)
            y += row_h
