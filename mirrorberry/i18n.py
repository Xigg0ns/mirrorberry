# SPDX-License-Identifier: GPL-3.0-or-later
"""Texts and date wording, matching MagicMirror (translations + moment.js).

Contains strings and rules from MagicMirror² (MIT, (c) Michael Teeuw) and
moment.js (MIT, (c) OpenJS Foundation and contributors); see THIRD_PARTY_NOTICES.md.

Strings come from MagicMirror's translations/{sv,en}.json and moment.js's
locale files, so a Swedish mirror reads "I morgon", "om 2 timmar",
"På fredag 14:00" exactly as MagicMirror does. Day and month *names* come
from the system locale ([general] locale in config.toml).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

STRINGS: dict[str, dict[str, str]] = {
    "sv": {
        "LOADING": "Laddar …",
        "TODAY": "I dag",
        "TOMORROW": "I morgon",
        "DAYAFTERTOMORROW": "I övermorgon",
        "RUNNING": "Slutar om {}",
        "EMPTY": "Inga kommande händelser.",
        "FEELS": "Känns som {}",
        "ERROR_NO_CONNECTION": "Ingen internetanslutning.",
        "ERROR_SERVER": "Serverfel. Försöker igen senare.",
        "ERROR_CLIENT": "Förfrågan misslyckades.",
        "ERROR_CONFIG": "Kontrollera inställningarna i config.toml.",
        "ERROR_UNAUTHORIZED": "Autentisering misslyckades.",
        "ERROR_RATE_LIMITED": "För många förfrågningar. Försöker igen senare.",
        # MMM-ResRobot
        "NOW": "Nu",
        "MINUTES_SHORT": "min",
        "DEPARTURES_LOADING": "Hämtar avgångar …",
        "TRAFIKLAB_CREDIT": "Data från Trafiklab.se",
        # MMM-Namnsdag
        "NAMEDAY_LOADING": "Hämtar dagens namn …",
        "NAMEDAY_ERROR": "Fel! Försöker igen om 5 min.",
        "NAMEDAY_EMPTY": "Ingen har namnsdag",
        # moment.js sv
        "LT": "%H:%M",
        "sameDay": "Idag {time}",
        "nextDay": "Imorgon {time}",
        "nextWeek": "På {weekday} {time}",
        "lastDay": "Igår {time}",
        "lastWeek": "I {weekday}s {time}",
        "future": "om {}",
        "past": "för {} sedan",
        "s": "några sekunder", "ss": "{} sekunder", "m": "en minut", "mm": "{} minuter",
        "h": "en timme", "hh": "{} timmar", "d": "en dag", "dd": "{} dagar",
        "M": "en månad", "MM": "{} månader", "y": "ett år", "yy": "{} år",
    },
    "en": {
        "LOADING": "Loading …",
        "TODAY": "Today",
        "TOMORROW": "Tomorrow",
        "DAYAFTERTOMORROW": "",  # MagicMirror has none for English: shows the weekday
        "RUNNING": "Ends in {}",
        "EMPTY": "No upcoming events.",
        "FEELS": "Feels like {}",
        "ERROR_NO_CONNECTION": "No internet connection.",
        "ERROR_SERVER": "Server error. Retrying later.",
        "ERROR_CLIENT": "Request failed.",
        "ERROR_CONFIG": "Check the settings in config.toml.",
        "ERROR_UNAUTHORIZED": "Authentication failed.",
        "ERROR_RATE_LIMITED": "Too many requests. Retrying later.",
        # MMM-ResRobot
        "NOW": "Now",
        "MINUTES_SHORT": "min",
        "DEPARTURES_LOADING": "Fetching departures …",
        "TRAFIKLAB_CREDIT": "Data from Trafiklab.se",
        # MMM-Namnsdag
        "NAMEDAY_LOADING": "Fetching today's names …",
        "NAMEDAY_ERROR": "Error! Retrying in 5 min.",
        "NAMEDAY_EMPTY": "No name day today",
        # moment.js en
        "LT": "%-I:%M %p",
        "sameDay": "Today at {time}",
        "nextDay": "Tomorrow at {time}",
        "nextWeek": "{weekday} at {time}",
        "lastDay": "Yesterday at {time}",
        "lastWeek": "Last {weekday} at {time}",
        "future": "in {}",
        "past": "{} ago",
        "s": "a few seconds", "ss": "{} seconds", "m": "a minute", "mm": "{} minutes",
        "h": "an hour", "hh": "{} hours", "d": "a day", "dd": "{} days",
        "M": "a month", "MM": "{} months", "y": "a year", "yy": "{} years",
    },
}

CARDINALS = {
    "sv": ["N", "NNO", "NO", "ONO", "Ö", "OSO", "SO", "SSO", "S", "SSV", "SV", "VSV", "V", "VNV", "NV", "NNV"],
    "en": ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"],
}


def language_for(locale_name: str, override: str = "") -> str:
    """'sv_SE.UTF-8' -> 'sv'. Unknown languages fall back to English."""
    lang = (override or locale_name.split("_")[0].split(".")[0]).lower()
    return lang if lang in STRINGS else "en"


def cap_first(text: str) -> str:
    return text[:1].upper() + text[1:]


def _js_round(x: float) -> int:
    """JavaScript's Math.round (halves round up), as moment.js uses."""
    return math.floor(x + 0.5)


class Translator:
    def __init__(self, language: str):
        self.language = language if language in STRINGS else "en"
        self.s = STRINGS[self.language]

    def __call__(self, key: str, *args) -> str:
        return self.s[key].format(*args)

    # -- small formatters -------------------------------------------------------

    def time(self, t: datetime) -> str:
        from .widgets.clock import format_time  # local import avoids a cycle
        return format_time(self.s["LT"], t)

    def cardinal(self, degrees: float) -> str:
        """Same 16 sectors as MagicMirror's cardinalWindDirection()."""
        return CARDINALS[self.language][int(((degrees % 360) + 11.25) // 22.5) % 16]

    def month_day(self, t: datetime) -> str:
        """moment's "MMM Do": 'okt 5:e' (sv) or 'Oct 5th' (en)."""
        month = t.strftime("%b").rstrip(".")
        n = t.day
        if self.language == "sv":
            suffix = ":e" if (n % 100) // 10 == 1 else (":a" if n % 10 in (1, 2) else ":e")
            return f"{month} {n}{suffix}"
        if (n % 100) // 10 == 1:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{month} {n}{suffix}"

    # -- moment.js humanize -----------------------------------------------------

    def duration(self, delta: timedelta) -> str:
        """moment.duration(...).humanize() without suffix, same thresholds."""
        ms = abs(delta.total_seconds()) * 1000
        seconds = _js_round(ms / 1000)
        minutes = _js_round(ms / 60_000)
        hours = _js_round(ms / 3_600_000)
        days_f = ms / 86_400_000
        days = _js_round(days_f)
        months = _js_round(days_f * 4800 / 146097)
        years = _js_round(days_f * 4800 / 146097 / 12)
        if seconds <= 44:
            key, n = "s", seconds
        elif seconds < 45:
            key, n = "ss", seconds
        elif minutes <= 1:
            key, n = "m", 1
        elif minutes < 45:
            key, n = "mm", minutes
        elif hours <= 1:
            key, n = "h", 1
        elif hours < 22:
            key, n = "hh", hours
        elif days <= 1:
            key, n = "d", 1
        elif days < 26:
            key, n = "dd", days
        elif months <= 1:
            key, n = "M", 1
        elif months < 11:
            key, n = "MM", months
        elif years <= 1:
            key, n = "y", 1
        else:
            key, n = "yy", years
        return self.s[key].format(n)

    def from_now(self, target: datetime, now: datetime) -> str:
        """moment(target).fromNow(): 'om 2 timmar' / 'in 2 hours'."""
        text = self.duration(target - now)
        return self.s["future" if target >= now else "past"].format(text)

    # -- moment.js calendar() ---------------------------------------------------

    @staticmethod
    def calendar_category(target: datetime, now: datetime) -> str:
        """Which calendar() format applies, measured from the start of today."""
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        diff = (target.replace(tzinfo=None) - start_of_today).total_seconds() / 86400
        if diff < -6:
            return "sameElse"
        if diff < -1:
            return "lastWeek"
        if diff < 0:
            return "lastDay"
        if diff < 1:
            return "sameDay"
        if diff < 2:
            return "nextDay"
        if diff < 7:
            return "nextWeek"
        return "sameElse"

    def calendar(self, target: datetime, now: datetime, same_else: str) -> str:
        """moment(target).calendar() with the locale's wording; ``same_else`` for far dates."""
        category = self.calendar_category(target, now)
        if category == "sameElse":
            return same_else
        return self.s[category].format(time=self.time(target), weekday=target.strftime("%A"))
