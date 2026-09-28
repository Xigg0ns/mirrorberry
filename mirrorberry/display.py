# SPDX-License-Identifier: GPL-3.0-or-later
"""Screen setup.

Two backends share one small interface (size, canvas, clear, present, close):

* ``fbdev``: draws in memory and copies pixels to /dev/fb0. No GPU involved.
  The default on a console-only Pi, see framebuffer.py.
* ``sdl``:   lets SDL own the screen: a normal window on a PC, or KMS/DRM
  (GPU/EGL) on a Pi.

Everything is drawn on a *logical* canvas. When the physical screen is mounted
sideways, the canvas is rotated once per frame just before it's shown.
"""

from __future__ import annotations

import logging
import os

import pygame

from .config import DisplayConfig

log = logging.getLogger(__name__)


class SDLDisplay:
    has_events = True  # window / keyboard events arrive through SDL

    def __init__(self, cfg: DisplayConfig, headless: bool = False):
        self.cfg = cfg
        self.background = pygame.Color(cfg.background)

        if headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
        elif cfg.fullscreen and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            # Console-only Pi: go straight to the framebuffer via KMS/DRM.
            os.environ.setdefault("SDL_VIDEODRIVER", "kmsdrm")

        try:
            pygame.display.init()
        except pygame.error as exc:
            raise RuntimeError(self._kms_hint(exc)) from exc
        pygame.font.init()
        log.info("SDL video driver: %s", pygame.display.get_driver())

        # Rotation only applies to the real screen; a dev window shows the
        # layout upright so it's easy to read.
        self.rotation = cfg.rotation if (cfg.fullscreen and not headless) else 0

        if cfg.fullscreen and not headless:
            try:
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            except pygame.error as exc:
                raise RuntimeError(self._kms_hint(exc)) from exc
            pygame.mouse.set_visible(False)
        else:
            self.screen = pygame.display.set_mode(cfg.window_size, pygame.RESIZABLE)
            pygame.display.set_caption("MirrorBerry")

        self._canvas: pygame.Surface | None = None
        self.resync()

    @staticmethod
    def _kms_hint(exc: Exception) -> str:
        driver = os.environ.get("SDL_VIDEODRIVER", "auto")
        msg = f"Could not open the display (SDL driver: {driver}): {exc}"
        if driver == "kmsdrm":
            msg += (
                "\n  KMS/DRM checklist:"
                "\n  - EGL/GLES runtime installed?  sudo apt install -y libegl1 libgles2"
                "\n  - GPU driver enabled?  'dtoverlay=vc4-kms-v3d' in /boot/firmware/config.txt"
                "\n  - /dev/dri/card* present and user in the 'video' and 'render' groups?"
                "\n  - Nothing else (a desktop, another MirrorBerry) already owns the screen?"
            )
        return msg

    @property
    def size(self) -> tuple[int, int]:
        """Logical (upright) size that the layout is computed against."""
        w, h = self.screen.get_size()
        return (h, w) if self.rotation in (90, 270) else (w, h)

    @property
    def canvas(self) -> pygame.Surface:
        """Surface to draw on. Without rotation this is the screen itself."""
        return self._canvas if self._canvas is not None else self.screen

    def resync(self) -> None:
        """Rebuild the canvas after start-up or a window resize."""
        self.screen = pygame.display.get_surface()
        # SDL's KMS/DRM backend recreates its EGL surface on the first present
        # after a mode set, discarding that frame. Games redraw constantly and
        # never notice; we draw once, so present the next frame twice.
        self._settle = True
        if self.rotation:
            self._canvas = pygame.Surface(self.size, 0, self.screen)
        else:
            self._canvas = None
        log.info("Screen %sx%s, logical %sx%s, rotation %s",
                 *self.screen.get_size(), *self.size, self.rotation)

    def clear(self) -> None:
        self.canvas.fill(self.background)

    def present(self, rects: list[pygame.Rect] | None = None) -> None:
        if rects is not None and self._canvas is None and not self._settle:
            pygame.display.update(rects)
            return
        if self._canvas is not None:
            # Multiples of 90 take pygame's fast lossless path.
            self.screen.blit(pygame.transform.rotate(self._canvas, self.rotation), (0, 0))
        pygame.display.flip()
        if self._settle:
            pygame.display.flip()
            self._settle = False

    def save(self, path: str) -> None:
        pygame.image.save(self.canvas, path)

    def close(self) -> None:
        pass


def _has_desktop() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def open_display(cfg: DisplayConfig, headless: bool = False):
    """Pick and open the display backend for this environment."""
    backend = cfg.backend
    if headless or not cfg.fullscreen:
        backend = "sdl"
    elif backend == "auto":
        backend = "fbdev" if (not _has_desktop() and os.path.exists("/dev/fb0")) else "sdl"

    log.info("Display backend: %s", backend)
    if backend == "fbdev":
        from .framebuffer import FramebufferDisplay
        return FramebufferDisplay(cfg)
    return SDLDisplay(cfg, headless=headless)
