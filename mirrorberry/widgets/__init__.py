# SPDX-License-Identifier: GPL-3.0-or-later
"""Widget registry. Add new widgets here so config.toml can refer to them by name."""

from __future__ import annotations

from ..layout import Zone
from .base import Widget
from .calendar import Calendar
from .clock import Clock
from .namnsdag import Namnsdag
from .placeholder import Placeholder
from .resrobot import ResRobot
from .weather import Weather

REGISTRY: dict[str, type[Widget]] = {
    "calendar": Calendar,
    "clock": Clock,
    "namnsdag": Namnsdag,
    "placeholder": Placeholder,
    "resrobot": ResRobot,
    "weather": Weather,
}


def create_widget(name: str, zone: Zone, options: dict) -> Widget:
    if not name:
        raise ValueError(
            f'Zone {zone.name}: no widget set. Add widget = "..." to [zones.{zone.name}], '
            f'or delete the section to leave the zone empty.'
        )
    try:
        cls = REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"Zone {zone.name}: unknown widget {name!r}. Known: {', '.join(REGISTRY)}"
        ) from None
    try:
        return cls(zone, **options)
    except TypeError as exc:  # usually a misspelt option in config.toml
        raise ValueError(f"Zone {zone.name}: bad option for widget {name!r}: {exc}") from None
    except ValueError as exc:
        raise ValueError(f"Zone {zone.name}, widget {name!r}: {exc}") from None


__all__ = ["REGISTRY", "Widget", "create_widget"]
