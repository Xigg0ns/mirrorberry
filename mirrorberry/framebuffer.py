# SPDX-License-Identifier: GPL-3.0-or-later
"""Linux framebuffer output (/dev/fb0).

pygame still does all the drawing, on an ordinary in-memory surface. On each
present the pixels are converted to the framebuffer's format and copied into
/dev/fb0. No GPU, EGL or Mesa is involved, which makes this the most reliable
option on a Pi Zero W.

SDL is initialised with its "dummy" video driver purely so pygame's event
queue and timers keep working.
"""

from __future__ import annotations

import fcntl
import logging
import mmap
import os
import struct
from dataclasses import dataclass
from pathlib import Path

import pygame

from .config import DisplayConfig

log = logging.getLogger(__name__)

FBIOGET_VSCREENINFO = 0x4600
KDSETMODE = 0x4B3A
KD_TEXT = 0x00
KD_GRAPHICS = 0x01


@dataclass
class FbGeometry:
    width: int
    height: int
    bpp: int
    stride: int  # bytes per row, may include padding
    offset: int  # byte offset of the visible area (panning)
    masks: tuple[int, int, int, int]  # R, G, B, A


def read_geometry(fd: int, device: str) -> FbGeometry:
    """Ask the kernel for the framebuffer's resolution and pixel layout."""
    var = bytearray(160)  # struct fb_var_screeninfo
    fcntl.ioctl(fd, FBIOGET_VSCREENINFO, var)
    (xres, yres, _xvirt, _yvirt, xoff, yoff, bpp, _gray,
     r_off, r_len, _r_msb, g_off, g_len, _g_msb,
     b_off, b_len, _b_msb, a_off, a_len, _a_msb) = struct.unpack_from("20I", var)

    stride_file = Path("/sys/class/graphics") / Path(device).name / "stride"
    try:
        stride = int(stride_file.read_text().strip())
    except (OSError, ValueError):
        stride = xres * bpp // 8

    def mask(off: int, length: int) -> int:
        return ((1 << length) - 1) << off if length else 0

    return FbGeometry(
        width=xres,
        height=yres,
        bpp=bpp,
        stride=stride,
        offset=yoff * stride + xoff * bpp // 8,
        masks=(mask(r_off, r_len), mask(g_off, g_len), mask(b_off, b_len), mask(a_off, a_len)),
    )


class FramebufferDisplay:
    # SDL's dummy driver delivers no input, and its event wait polls every
    # millisecond, so the app sleeps with time.sleep() instead.
    has_events = False

    def __init__(self, cfg: DisplayConfig, device: str = "/dev/fb0",
                 geometry_reader=read_geometry):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.display.init()
        pygame.font.init()

        self.background = pygame.Color(cfg.background)
        self.rotation = cfg.rotation

        try:
            self._fd = os.open(device, os.O_RDWR)
        except OSError as exc:
            raise RuntimeError(
                f"Could not open {device}: {exc}\n"
                "  - Does it exist?  ls -l /dev/fb*\n"
                "  - Is the user in the 'video' group?  groups $USER"
            ) from exc

        g = self.geometry = geometry_reader(self._fd, device)
        log.info("Framebuffer %s: %sx%s, %s bpp, stride %s",
                 device, g.width, g.height, g.bpp, g.stride)

        flags = pygame.SRCALPHA if g.masks[3] else 0
        self._fb_surface = pygame.Surface((g.width, g.height), flags, g.bpp, g.masks)
        self._row_bytes = g.width * g.bpp // 8
        self._map = mmap.mmap(self._fd, g.offset + g.stride * g.height,
                              mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

        self._canvas = pygame.Surface(self.size)
        self._console_fd: int | None = None
        self._claim_console()

    # -- console ------------------------------------------------------------

    def _claim_console(self) -> None:
        """Stop the text console from drawing over us (cursor, login, kernel messages).

        Works when stdin is a virtual terminal we control, which is what the
        systemd unit sets up (TTYPath=/dev/tty1, StandardInput=tty).
        """
        try:
            tty = os.ttyname(0)
        except OSError:
            tty = None
        if not tty or not tty.startswith("/dev/tty") or not tty[8:].isdigit():
            log.info("Not running on a virtual terminal; the text console may show "
                     "through. Run via the systemd unit to prevent this.")
            return
        try:
            fcntl.ioctl(0, KDSETMODE, KD_GRAPHICS)
            self._console_fd = 0
            log.info("Switched %s to graphics mode", tty)
        except OSError as exc:
            log.warning("Could not switch %s to graphics mode: %s", tty, exc)

    def _release_console(self) -> None:
        if self._console_fd is not None:
            try:
                fcntl.ioctl(self._console_fd, KDSETMODE, KD_TEXT)
            except OSError:
                pass
            self._console_fd = None

    # -- Display interface --------------------------------------------------

    @property
    def size(self) -> tuple[int, int]:
        w, h = self.geometry.width, self.geometry.height
        return (h, w) if self.rotation in (90, 270) else (w, h)

    @property
    def canvas(self) -> pygame.Surface:
        return self._canvas

    def resync(self) -> None:
        pass  # the framebuffer never changes size under us

    def clear(self) -> None:
        self._canvas.fill(self.background)

    def present(self, rects: list[pygame.Rect] | None = None) -> None:
        """Copy the canvas to the framebuffer: everything, or just ``rects``."""
        if rects is None:
            src = self._canvas
            if self.rotation:
                src = pygame.transform.rotate(src, self.rotation)
            self._fb_surface.blit(src, (0, 0))  # converts to the fb pixel format
            self._copy_to_fb(self._fb_surface.get_rect())
            return

        canvas_rect = self._canvas.get_rect()
        for rect in rects:
            rect = rect.clip(canvas_rect)
            if not rect.width or not rect.height:
                continue
            src = self._canvas.subsurface(rect)
            if self.rotation:
                src = pygame.transform.rotate(src, self.rotation)
            phys = self._to_physical(rect)
            self._fb_surface.blit(src, phys.topleft)
            self._copy_to_fb(phys)

    def _to_physical(self, r: pygame.Rect) -> pygame.Rect:
        """Map a logical-canvas rect to framebuffer coordinates.

        pygame rotates counter-clockwise, so for 90 degrees a logical point
        (x, y) lands at (y, W - 1 - x), where W is the logical width.
        """
        w, h = self.size
        if self.rotation == 90:
            return pygame.Rect(r.y, w - r.right, r.height, r.width)
        if self.rotation == 180:
            return pygame.Rect(w - r.right, h - r.bottom, r.width, r.height)
        if self.rotation == 270:
            return pygame.Rect(h - r.bottom, r.x, r.height, r.width)
        return pygame.Rect(r)

    def _copy_to_fb(self, r: pygame.Rect) -> None:
        g = self.geometry
        px = g.bpp // 8
        pitch = self._fb_surface.get_pitch()
        pixels = memoryview(self._fb_surface.get_buffer())  # no copy
        try:
            if r.x == 0 and r.width == g.width and pitch == g.stride:
                # Whole rows, same layout: one contiguous copy.
                start = r.y * pitch
                length = r.height * pitch
                self._map[g.offset + start:g.offset + start + length] = pixels[start:start + length]
                return
            row = r.width * px
            for y in range(r.y, r.bottom):
                dst = g.offset + y * g.stride + r.x * px
                src = y * pitch + r.x * px
                self._map[dst:dst + row] = pixels[src:src + row]
        finally:
            pixels.release()

    def save(self, path: str) -> None:
        pygame.image.save(self._canvas, path)

    def close(self) -> None:
        self._release_console()
        try:
            self._map.close()
            os.close(self._fd)
        except (OSError, ValueError):
            pass
