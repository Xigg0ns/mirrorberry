# Development

## How it works

MirrorBerry is a single Python process built for a single-core 1 GHz ARMv6 CPU:

- **Drawing.** pygame draws into an in-memory surface. On a Pi the `fbdev`
  backend copies changed areas of it to `/dev/fb0` (converting to the
  framebuffer's pixel format and rotation); elsewhere SDL shows a window.
- **Main loop** (`app.py`). The loop sleeps until the next widget is due, calls
  `update()` on due widgets, and redraws only the widgets whose `update()`
  returned `True`. Updates are scheduled from the wall clock, so a 1-second clock
  runs just after each second ticks over and slow redraws can't make it drift.
- **Layout.** Zones hold stacks of widgets. Widgets report their size through
  `size()`, the app stacks them, extends zones over empty zones below, and
  restacks a zone when a widget's size changes. Measured sizes are cached, so a
  ticking clock doesn't make the calendar below it measure itself again.
- **Downloads** (`fetch.py`). A `Poller` runs a function in a background thread
  every interval, keeps the last good result when the network fails, and retries
  with a growing delay. Widgets read the latest result in `update()` and never
  wait for the network.
- **Look** (`widgets/style.py`). A `Theme` holds MagicMirror²'s size classes,
  scaled by `[display] scale`. `Text` places text in CSS-like line boxes, so
  vertical positions match a browser.

## Writing a widget

A widget is a `Widget` subclass in `mirrorberry/widgets/`. This one shows a line
of text downloaded from a URL, for example a note on your home server:

```python
"""Shows a line of text downloaded from a URL, e.g. a note on your home server."""

from __future__ import annotations

import pygame

from ..fetch import Poller, http_get, interval_option
from ..layout import Zone
from .base import Widget
from .style import BRIGHT, Text, default_align, x_for


class Message(Widget):
    refresh_interval = 60  # look for new data once a minute (the Poller does the downloading)

    def __init__(self, zone: Zone, url: str = "", header: str = "", update_interval: int = 600):
        super().__init__(zone)
        if not url:
            raise ValueError("set url")  # shown in the widget's zone
        self.header = header
        self.align = default_align(zone.col)
        self.poller = Poller(f"message {url}", lambda: http_get(url).decode().strip(),
                             interval_option("update_interval", update_interval)).start()
        self._seen = -1
        self._text = ""

    def update(self, now: float) -> bool:
        version, data, error = self.poller.snapshot()
        if version == self._seen:
            return False  # nothing new: no redraw
        self._seen = version
        self._text = data or self.tr("LOADING")
        return True

    def _line(self) -> Text:
        return Text(self._text, self.theme.size("medium"), BRIGHT)

    def size(self, width: int) -> tuple[int, int]:
        return self.with_header(self._line().width, self.theme.line("medium"))

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        line = self._line()
        y = self.begin(surface, rect, line.width)  # clears the rect, draws the header
        line.draw(surface, x_for(self.align, rect, line.width),
                  line.baseline_in(y, self.theme.line("medium")))
```

Register it in `mirrorberry/widgets/__init__.py`:

```python
from .message import Message

REGISTRY = {
    ...
    "message": Message,
}
```

and use it in `config.toml`; every key except `widget` is passed to `__init__`:

```toml
[zones.TopLeft]
widget = "message"
url    = "https://example.com/note.txt"
header = "Påminnelse"
```

The pieces:

- **`__init__(zone, **options)`.** Options come from `config.toml`. Raise
  `ValueError` for bad settings; the message is shown in the zone. A misspelt
  option name is reported the same way.
- **`refresh_interval` / `update(now)`.** Seconds between `update()` calls
  (`None` = never). Return `True` when the widget needs redrawing. Calls are
  aligned to the wall clock (a 60-second widget runs just after each minute);
  override `next_update_in(wall_time)` for other timing. To fetch early, call
  the Poller's `refresh()`, as the name-day widget does when the date changes.
- **`size(width)`.** `(width, height)` of the content, so the widget can be
  stacked. Return `None` to fill whatever space is left instead.
- **`draw(surface, rect)`.** Paint inside `rect`; drawing is clipped to it. Keep
  network calls out of here.
- **Helpers.** `self.theme` gives sizes (`size("small")`, `line("small")`,
  `px(10)`), `self.tr(...)` translated texts, `self.begin()` and
  `self.with_header()` handle the MagicMirror²-style header.
  `widgets/style.py` has the colours (`BRIGHT`, `NORMAL`, `DIMMED`), fonts and
  list fading.

`clock.py` is a compact example of a widget without downloads; `namnsdag.py` a
short one with downloads.

## Testing without a Pi

```bash
python3 -m mirrorberry --size 1280x720                     # live, in a window
python3 -m mirrorberry --screenshot out.png --size 1920x1080  # one frame to a file
python3 -m mirrorberry -v                                  # debug log with redraw times
```

`-c other.toml` runs with a different config file.

## Project structure

```
config.example.toml          example settings (copy to config.toml)
deploy/mirrorberry@.service  systemd unit
docs/                        documentation
mirrorberry/
  __main__.py                command line
  app.py                     main loop, zone stacking, redraws
  config.py                  loading and checking config.toml
  display.py                 backend selection, SDL window, rotation
  framebuffer.py             /dev/fb0 backend
  fetch.py                   background downloads (Poller)
  i18n.py                    Swedish and English texts, MagicMirror² date wording
  layout.py                  zones and grid geometry
  sun.py                     sunrise and sunset (port of suncalc)
  assets/fonts/              Font Awesome, Weather Icons and their licences
  widgets/
    __init__.py              widget registry
    base.py                  Widget base class
    style.py                 theme, colours, text, headers, fading
    text.py                  font loading and caching
    clock.py                 clock
    weather.py               SMHI / Open-Meteo weather and forecast
    calendar.py              iCal calendar
    resrobot.py              departures (ResRobot / Trafiklab Realtime)
    namnsdag.py              Swedish name days
    placeholder.py           coloured placeholder blocks
    errors.py                shown in a zone with a settings problem
```
