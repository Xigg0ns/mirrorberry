# SPDX-License-Identifier: GPL-3.0-or-later
"""Main loop and screen layout.

Layout works like MagicMirror's regions on the 3x3 grid: each zone holds a
stack of widgets, top to bottom, with a gap between them. A zone reaches down
over any empty zones below it, so a tall stack (clock + calendar) can use the
height of a whole column. Widgets in a zone share its width for their header
rules, like modules in a region.

Designed for a single-core 1 GHz ARMv6: the loop sleeps until a widget is
due and only repaints (and pushes to the screen) widgets that changed.
"""

from __future__ import annotations

import logging
import signal
import time
from dataclasses import dataclass, field

import pygame

from .config import Config
from .display import open_display
from .i18n import language_for
from .layout import Zone, compute_zone_rects
from .widgets import Widget, create_widget
from .widgets.errors import ConfigErrorWidget
from .widgets.style import Theme
from .widgets.text import fit_text

log = logging.getLogger(__name__)

DEFAULT_VALIGN = {0: "top", 1: "top", 2: "bottom"}  # by row, like MagicMirror's regions


@dataclass
class Slot:
    zone: Zone
    widget: Widget
    rect: pygame.Rect = field(default_factory=lambda: pygame.Rect(0, 0, 0, 0))
    next_update: float | None = 0.0  # monotonic time it's next due; None = never
    measured: object = False         # cached widget.size(); False = measure again


class App:
    def __init__(self, config: Config, headless: bool = False):
        self._t0 = time.monotonic()
        self._first_frame_logged = False
        self.config = config
        self.display = open_display(config.display, headless=headless)
        self.slots: list[Slot] = [
            Slot(zone, self._create(zone, zc.widget, zc.options))
            for zone, stack in config.zones.items() for zc in stack
        ]
        self.zone_rects: dict[Zone, pygame.Rect] = {}   # full zone area (after extension)
        self.content_rects: dict[Zone, pygame.Rect] = {}  # inside the zone padding
        self._dirty: set[int] = set()
        self._full_redraw = True
        self.running = False
        in_use = [f"{z.name}: {' + '.join(zc.widget for zc in s)}" for z, s in config.zones.items() if s]
        empty = [z.name for z, s in config.zones.items() if not s] + [z.name for z in Zone if z not in config.zones]
        log.info("Zones: %s; empty: %s", ", ".join(in_use) or "none", ", ".join(empty) or "none")
        self.relayout()

    # Kept for tools/tests that look up a zone's (first) widget.
    @property
    def widgets(self) -> dict[Zone, Widget]:
        out: dict[Zone, Widget] = {}
        for slot in self.slots:
            out.setdefault(slot.zone, slot.widget)
        return out

    @staticmethod
    def _create(zone: Zone, name: str, options: dict) -> Widget:
        """A widget with a bad setting shows the problem in its zone instead of stopping the app."""
        try:
            return create_widget(name, zone, options)
        except ValueError as exc:
            log.error("config.toml: %s", exc)
            return ConfigErrorWidget(zone, str(exc))

    # -- layout ---------------------------------------------------------------

    def _theme(self) -> Theme:
        scale = self.config.display.scale
        if scale == "auto":
            scale = min(self.display.size) / 1080
        th = self.config.theme
        base = Theme()
        return Theme(
            scale=float(scale),
            sizes={**base.sizes, **th.sizes},
            line_heights={**base.line_heights, **th.line_heights},
            letter_spacing={**base.letter_spacing, **th.letter_spacing},
            **{k: v for k, v in th.header.items()},
        )

    def relayout(self) -> None:
        theme = self._theme()
        language = language_for(self.config.locale, self.config.language)
        for slot in self.slots:
            slot.widget.theme, slot.widget.language = theme, language
        log.info("Theme scale %.2f, language %s", theme.scale, language)
        self.theme = theme

        lay = self.config.layout
        grid = compute_zone_rects(self.display.size, lay.column_weights, lay.row_weights,
                                  theme.px(lay.margin) if lay.margin else 0,
                                  theme.px(lay.gutter) if lay.gutter else 0)
        occupied = {slot.zone for slot in self.slots}
        self.zone_rects, self.content_rects = {}, {}
        for zone in occupied:
            rect = grid[zone].copy()
            # Reach down over empty zones in the same column.
            for row in range(zone.row + 1, 3):
                below = next(z for z in Zone if z.row == row and z.col == zone.col)
                if below in occupied:
                    break
                rect.union_ip(grid[below])
            self.zone_rects[zone] = rect
            pad = int(min(rect.width, rect.height) * lay.padding)
            self.content_rects[zone] = rect.inflate(-2 * pad, -2 * pad)
        for slot in self.slots:
            slot.measured = False  # zone widths may have changed
        self._full_redraw = True
        self._dirty = set(range(len(self.slots)))

    def _stack(self, zone: Zone, changed: set[int]) -> bool:
        """Position the widgets of one zone; True if any rect moved or resized.

        Only widgets in ``changed`` are measured again; the others keep their
        cached size (a ticking clock doesn't make the calendar re-measure).
        """
        area = self.content_rects[zone]
        indices = [i for i, s in enumerate(self.slots) if s.zone == zone]
        slots = [self.slots[i] for i in indices]
        if len(slots) == 1 and slots[0].widget.fills_zone:
            new = [self.zone_rects[zone]]
        else:
            sizes = []
            for i, slot in zip(indices, slots):
                if i in changed or slot.measured is False:
                    try:
                        slot.measured = slot.widget.size(area.width)
                    except Exception:
                        log.exception("Widget in %s failed to measure", zone.name)
                        slot.measured = None
                sizes.append(slot.measured)
            gap = self.theme.px(self.config.layout.stack_gap)
            fixed = sum(s[1] for s in sizes if s) + gap * (len(slots) - 1)
            flexible = sum(1 for s in sizes if s is None)
            flex_h = max(0, (area.height - fixed) // flexible) if flexible else 0
            total = fixed + flex_h * flexible
            if total > area.height:
                log.debug("%s: content (%d px) taller than the zone (%d px)", zone.name, total, area.height)
            valign = self.config.layout.valign.get(zone, DEFAULT_VALIGN[zone.row])
            if flexible or valign == "top":
                y = area.top
            elif valign == "center":
                y = area.top + (area.height - total) // 2
            else:
                y = area.bottom - total
            stack_w = max((s[0] for s in sizes if s), default=0)
            new = []
            for i, slot, s in zip(indices, slots, sizes):
                h = s[1] if s else flex_h
                new.append(pygame.Rect(area.left, y, area.width, h))
                width = min(stack_w, area.width)
                if slot.widget.stack_width != width:  # header rules follow the widest module
                    slot.widget.stack_width = width
                    self._dirty.add(i)
                y += h + gap
        changed = False
        for slot, rect in zip(slots, new):
            if slot.rect != rect:
                slot.rect, changed = rect, True
        return changed

    # -- drawing --------------------------------------------------------------

    def render(self) -> None:
        started = time.perf_counter()
        canvas = self.display.canvas
        full = self._full_redraw
        if full:
            self.display.clear()
            self._full_redraw = False

        drawn: list[pygame.Rect] = []
        # Widgets whose content changed may have changed size: restack their zones.
        for zone in {self.slots[i].zone for i in self._dirty}:
            if self._stack(zone, set(self._dirty)) and not full:
                canvas.fill(self.display.background, self.zone_rects[zone])
                drawn.append(self.zone_rects[zone])
                self._dirty |= {i for i, s in enumerate(self.slots) if s.zone == zone}

        for i in sorted(self._dirty):
            slot = self.slots[i]
            rect = slot.rect.clip(self.zone_rects[slot.zone])
            if rect.width <= 0 or rect.height <= 0:
                continue
            drawn.append(rect)
            canvas.set_clip(rect)
            try:
                slot.widget.draw(canvas, slot.rect)
            except Exception:
                # One broken widget must not take the whole mirror down.
                log.exception("Widget in %s failed to draw", slot.zone.name)
                self._draw_error(canvas, rect, slot.zone)
            finally:
                canvas.set_clip(None)

        self._dirty.clear()
        # Push only what changed, unless the whole screen was redrawn.
        self.display.present(None if full else drawn)
        log.debug("Rendered %s in %.0f ms", "full frame" if full else f"{len(drawn)} area(s)",
                  (time.perf_counter() - started) * 1000)
        if not self._first_frame_logged:
            log.info("First frame presented %.1f s after start", time.monotonic() - self._t0)
            self._first_frame_logged = True

    @staticmethod
    def _draw_error(canvas: pygame.Surface, rect: pygame.Rect, zone: Zone) -> None:
        canvas.fill((60, 0, 0), rect)
        msg = fit_text(f"{zone.name}: widget error, see log", int(rect.width * 0.9),
                       max(12, rect.height // 12), (255, 200, 200))
        canvas.blit(msg, msg.get_rect(center=rect.center))

    # -- updates / events ---------------------------------------------------

    def poll_widgets(self, now: float) -> None:
        for i, slot in enumerate(self.slots):
            due = slot.next_update
            if due is None or now < due:
                continue
            try:
                if slot.widget.update(now):
                    self._dirty.add(i)
            except Exception:
                log.exception("Widget in %s failed to update", slot.zone.name)
            # Schedule from the clock *after* the update, so its cost never shifts the next run.
            try:
                delay = slot.widget.next_update_in(time.time())
            except Exception:
                log.exception("Widget in %s failed to schedule", slot.zone.name)
                delay = slot.widget.refresh_interval
            slot.next_update = None if delay is None else time.monotonic() + max(0.0, delay)

    def _sleep_time(self, now: float) -> float:
        """Seconds until the next widget is due, capped at tick_ms."""
        cap = self.config.tick_ms / 1000
        pending = [s.next_update for s in self.slots if s.next_update is not None]
        if not pending:
            return cap
        return min(cap, max(0.0, min(pending) - now))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            self.display.resync()
            self.relayout()

    def _on_signal(self, signum, _frame) -> None:
        log.info("Received signal %s, shutting down", signum)
        self.running = False

    # -- entry points -------------------------------------------------------

    def run(self) -> None:
        signal.signal(signal.SIGTERM, self._on_signal)
        signal.signal(signal.SIGINT, self._on_signal)
        self.running = True
        log.info("MirrorBerry running with %d widgets", len(self.slots))
        try:
            self.poll_widgets(time.monotonic())
            self.render()  # show something immediately instead of after the first tick
            while self.running:
                # Sleep until the next widget is due (or tick_ms at most).
                timeout = self._sleep_time(time.monotonic())
                if self.display.has_events:
                    # event.wait(0) would mean "forever", so wait at least 1 ms
                    self.handle_event(pygame.event.wait(max(1, round(timeout * 1000))))
                    for event in pygame.event.get():
                        self.handle_event(event)
                elif timeout > 0:
                    time.sleep(timeout)
                self.poll_widgets(time.monotonic())
                if self._dirty or self._full_redraw:
                    self.render()
        finally:
            self.display.close()
            pygame.quit()

    def screenshot(self, path: str) -> None:
        """Render one frame and save it as an image (works without a screen)."""
        self.poll_widgets(time.monotonic())
        self.render()
        self.display.save(path)
        self.display.close()
        pygame.quit()
