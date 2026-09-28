# SPDX-License-Identifier: GPL-3.0-or-later
"""Configuration: built-in defaults, optionally overridden by config.toml."""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .layout import Zone

log = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.toml"

# Revision-1 debug palette: one distinct colour per zone.
DEFAULT_ZONE_COLORS: dict[Zone, str] = {
    Zone.TopLeft: "#E63946",
    Zone.TopCenter: "#F4A261",
    Zone.TopRight: "#E9C46A",
    Zone.CenterLeft: "#2A9D8F",
    Zone.Center: "#264653",
    Zone.CenterRight: "#8AB17D",
    Zone.BottomLeft: "#457B9D",
    Zone.BottomCenter: "#6D597A",
    Zone.BottomRight: "#B5838D",
}

VALID_ROTATIONS = (0, 90, 180, 270)


VALID_BACKENDS = ("auto", "fbdev", "sdl")


@dataclass
class DisplayConfig:
    backend: str = "auto"  # auto | fbdev | sdl
    fullscreen: bool = True
    window_size: tuple[int, int] = (540, 960)  # logical size in windowed mode
    rotation: int = 0  # degrees counter-clockwise, fullscreen only
    background: str = "#000000"
    scale: float | str = "auto"  # MagicMirror px -> screen px; auto = shorter side / 1080


@dataclass
class LayoutConfig:
    margin: float = 0               # outer screen margin, MagicMirror px (x scale)
    gutter: float = 0               # gap between zones, MagicMirror px (x scale)
    column_weights: tuple[float, float, float] = (1, 1, 1)
    row_weights: tuple[float, float, float] = (1, 1, 1)
    padding: float = 0.08           # inside each zone, fraction of its shorter side
    stack_gap: float = 30           # between widgets stacked in one zone (MagicMirror: 30px)
    valign: dict = field(default_factory=dict)  # Zone -> "top" | "center" | "bottom"


@dataclass
class ThemeConfig:
    sizes: dict = field(default_factory=dict)
    line_heights: dict = field(default_factory=dict)
    letter_spacing: dict = field(default_factory=dict)
    header: dict = field(default_factory=dict)  # header_size, header_line, ... cell_padding


@dataclass
class ZoneConfig:
    widget: str = "placeholder"
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    locale: str = ""  # e.g. "sv_SE.UTF-8"; "" = the system's default
    language: str = ""  # "sv" or "en"; "" = from the locale
    display: DisplayConfig = field(default_factory=DisplayConfig)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    tick_ms: int = 1000
    theme: ThemeConfig = field(default_factory=ThemeConfig)
    # Each zone holds a stack of widgets, top to bottom; an empty list = nothing there.
    zones: dict[Zone, list[ZoneConfig]] = field(default_factory=dict)


def _default_zones() -> dict[Zone, list[ZoneConfig]]:
    return {
        zone: [ZoneConfig("placeholder", {"color": DEFAULT_ZONE_COLORS[zone]})] for zone in Zone
    }


THEME_KEYS = ("header_size", "header_line", "header_padding", "header_rule", "header_margin", "cell_padding")
VALIGNS = ("top", "center", "bottom")


def load_config(path: Path | None = DEFAULT_CONFIG_PATH) -> Config:
    cfg = Config(zones=_default_zones())

    if path is None or not path.exists():
        log.warning("No config file at %s: showing placeholders. Copy config.example.toml "
                    "to config.toml to get started.", path)
        return cfg

    log.info("Loading config from %s", path)
    with path.open("rb") as fh:
        raw = tomllib.load(fh)

    general = raw.get("general", {})
    cfg.locale = str(general.get("locale", cfg.locale))
    cfg.language = str(general.get("language", cfg.language))

    d = raw.get("display", {})
    cfg.display = DisplayConfig(
        backend=str(d.get("backend", cfg.display.backend)),
        fullscreen=bool(d.get("fullscreen", cfg.display.fullscreen)),
        window_size=tuple(d.get("window_size", cfg.display.window_size)),
        rotation=int(d.get("rotation", cfg.display.rotation)),
        background=str(d.get("background", cfg.display.background)),
        scale=d.get("scale", cfg.display.scale),
    )
    if cfg.display.scale != "auto" and not (
            isinstance(cfg.display.scale, (int, float)) and cfg.display.scale > 0):
        raise ValueError('display.scale must be "auto" or a positive number')
    if cfg.display.backend not in VALID_BACKENDS:
        raise ValueError(f"display.backend must be one of {VALID_BACKENDS}")
    if cfg.display.rotation not in VALID_ROTATIONS:
        raise ValueError(f"display.rotation must be one of {VALID_ROTATIONS}")

    lay = raw.get("layout", {})
    valign = {}
    for name, value in lay.get("valign", {}).items():
        if value not in VALIGNS:
            raise ValueError(f"layout.valign.{name} must be one of {VALIGNS}")
        valign[Zone.from_name(name)] = value
    cfg.layout = LayoutConfig(
        margin=float(lay.get("margin", cfg.layout.margin)),
        gutter=float(lay.get("gutter", cfg.layout.gutter)),
        column_weights=tuple(lay.get("column_weights", cfg.layout.column_weights)),
        row_weights=tuple(lay.get("row_weights", cfg.layout.row_weights)),
        padding=float(lay.get("padding", cfg.layout.padding)),
        stack_gap=float(lay.get("stack_gap", cfg.layout.stack_gap)),
        valign=valign,
    )

    th = raw.get("theme", {})
    for key in th.get("sizes", {}):
        if key not in ("xsmall", "small", "medium", "large", "xlarge"):
            raise ValueError(f"theme.sizes: unknown class {key!r}")
    unknown = set(th) - {"sizes", "line_heights", "letter_spacing", *THEME_KEYS}
    if unknown:
        raise ValueError(f"theme: unknown setting(s) {', '.join(sorted(unknown))}")
    cfg.theme = ThemeConfig(
        sizes={k: float(v) for k, v in th.get("sizes", {}).items()},
        line_heights={k: float(v) for k, v in th.get("line_heights", {}).items()},
        letter_spacing={k: float(v) for k, v in th.get("letter_spacing", {}).items()},
        header={k: float(th[k]) for k in THEME_KEYS if k in th},
    )

    cfg.tick_ms = int(raw.get("loop", {}).get("tick_ms", cfg.tick_ms))

    # [zones.<Name>] holds one widget; [[zones.<Name>]] (repeated) stacks several.
    # "widget" picks the widget, everything else is passed to it as options.
    # Once config.toml defines any zones, zones it leaves out are empty.
    if "zones" in raw:
        cfg.zones = {zone: [] for zone in Zone}
    for name, entry in raw.get("zones", {}).items():
        zone = Zone.from_name(name)
        stack = []
        for table in (entry if isinstance(entry, list) else [entry]):
            table = dict(table)
            if not table:
                continue  # a bare [zones.X] header: nothing in this zone
            widget = table.pop("widget", "")  # missing: the zone shows an error saying so
            if widget == "empty":
                continue
            if widget == "placeholder":
                table.setdefault("color", DEFAULT_ZONE_COLORS[zone])
            stack.append(ZoneConfig(widget=widget, options=table))
        cfg.zones[zone] = stack

    return cfg
