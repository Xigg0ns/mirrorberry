# SPDX-License-Identifier: GPL-3.0-or-later
"""Sunrise and sunset: a port of suncalc 2.x getTimes(), as MagicMirror uses.

SMHI's forecast has no sunrise/sunset, so MagicMirror computes them with the
suncalc library; this is the same algorithm, so day/night icons and the
sunrise/sunset line match MagicMirror to the second.
(suncalc: BSD-2-Clause, (c) Volodymyr Agafonkin; see THIRD_PARTY_NOTICES.md.)
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

RAD = math.pi / 180
DAY_S = 86400
J1970 = 2440588
J2000 = 2451545
J0 = 0.0009
SUNRISE_ANGLE = -0.833  # degrees: refraction + the sun's radius


def _js_round(x: float) -> int:
    return math.floor(x + 0.5)


def _to_days(t: datetime) -> float:
    return t.timestamp() / DAY_S - 0.5 + J1970 - J2000


def _from_julian(j: float) -> datetime:
    return datetime.fromtimestamp((j + 0.5 - J1970) * DAY_S, tz=timezone.utc)


def _delta_t(d: float) -> float:
    """Seconds between terrestrial and universal time (only the years we need)."""
    y = 2000 + d / 365.2425
    if y < 2005:
        t = y - 2000
        return 63.86 + t * (0.3345 + t * (-0.060374 + t * (0.0017275 + t * (651814e-9 + t * 2373599e-11))))
    if y < 2050:
        t = y - 2000
        return 62.92 + t * (0.32217 + t * 0.005589)
    t = (y - 1820) / 100
    return -20 + 32 * t * t - 0.5628 * (2150 - y)


def _to_days_tt(d: float) -> float:
    return d + _delta_t(d) / 86400


def _sidereal_time(d: float, lw: float) -> float:
    return RAD * (280.46061837 + 360.98564736629 * d) - lw


def _altitude(h: float, phi: float, dec: float) -> float:
    return math.asin(math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(h))


def _sun_coords(d: float) -> tuple[float, float]:
    """Right ascension and declination."""
    t = d / 36525
    l0 = RAD * (280.46646 + t * (36000.76983 + t * 3032e-7))
    m = RAD * (357.52911 + t * (35999.05029 - t * 1537e-7))
    sin_m, cos_m = math.sin(m), math.cos(m)
    c = RAD * ((1.914602 - t * (0.004817 + t * 14e-6)) * sin_m
               + (0.019993 - 101e-6 * t) * 2 * sin_m * cos_m
               + 289e-6 * sin_m * (3 - 4 * sin_m * sin_m))
    om = RAD * (125.04 - 1934.136 * t)
    lon = l0 + c - RAD * (0.00569 + 0.00478 * math.sin(om))
    e = RAD * (23.439291 - t * (0.0130042 + t * (16e-8 - t * 504e-9))) + RAD * 0.00256 * math.cos(om)
    return math.atan2(math.cos(e) * math.sin(lon), math.cos(lon)), math.asin(math.sin(e) * math.sin(lon))


def _wrap_pi(a: float) -> float:
    return a - 2 * math.pi * _js_round(a / (2 * math.pi))


def _solar_transit(dt: float, lw: float) -> float:
    for _ in range(3):
        h = _wrap_pi(_sidereal_time(dt, lw) - _sun_coords(_to_days_tt(dt))[0])
        dt -= h / (2 * math.pi)
    return dt


def _set_j(h0: float, dt: float, sign: int, lw: float, phi: float, dec: float) -> float | None:
    cos_h0 = (math.sin(h0) - math.sin(phi) * math.sin(dec)) / (math.cos(phi) * math.cos(dec))
    if cos_h0 < -1 or cos_h0 > 1:
        return None  # midnight sun / polar night
    d = dt + sign * math.acos(cos_h0) / (2 * math.pi)
    for _ in range(2):
        ra, c_dec = _sun_coords(_to_days_tt(d))
        h = _wrap_pi(_sidereal_time(d, lw) - ra)
        alt = _altitude(h, phi, c_dec)
        sin_h = math.cos(phi) * math.cos(c_dec) * math.sin(h)
        if abs(sin_h) < 1e-6:
            break
        d += (alt - h0) / (2 * math.pi * sin_h)
    return d


def sun_times(when: datetime, lat: float, lon: float) -> tuple[datetime | None, datetime | None]:
    """(sunrise, sunset) around the solar noon nearest ``when``, in UTC.

    None for either means the sun doesn't cross the horizon that day.
    """
    lw = RAD * -lon
    phi = RAD * lat
    dt = _solar_transit(_js_round(_to_days(when) - J0 - lw / (2 * math.pi)) + J0 + lw / (2 * math.pi), lw)
    dec = _sun_coords(_to_days_tt(dt))[1]
    h0 = SUNRISE_ANGLE * RAD
    rise, sset = _set_j(h0, dt, -1, lw, phi, dec), _set_j(h0, dt, 1, lw, phi, dec)
    return (_from_julian(rise + J2000) if rise is not None else None,
            _from_julian(sset + J2000) if sset is not None else None)


def is_daytime(when: datetime, sunrise: datetime | None, sunset: datetime | None) -> bool:
    """MagicMirror's isDayTime(): daytime if unknown."""
    if sunrise is None or sunset is None:
        return True
    return sunrise <= when < sunset
