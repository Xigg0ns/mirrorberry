# SPDX-License-Identifier: GPL-3.0-or-later
"""Run with:  python3 -m mirrorberry [--windowed] [--size 540x960] [--screenshot out.png]"""

from __future__ import annotations

import argparse
import locale
import logging
import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from .config import DEFAULT_CONFIG_PATH, load_config  # noqa: E402


def _parse_size(value: str) -> tuple[int, int]:
    try:
        w, h = (int(v) for v in value.lower().split("x"))
        return w, h
    except ValueError:
        raise argparse.ArgumentTypeError("size must look like 540x960") from None


def _apply_locale(name: str) -> None:
    """Day and month names in the configured language (falls back to the system's)."""
    log = logging.getLogger("mirrorberry")
    try:
        locale.setlocale(locale.LC_TIME, name)
        if name:
            log.info("Locale for dates: %s", name)
        return
    except locale.Error:
        log.warning(
            "Locale %s is not installed, using the system default. Install it with:\n"
            "  sudo sed -i 's/^# *%s/%s/' /etc/locale.gen && sudo locale-gen",
            name, name.replace(".", "\\."), name,
        )
    try:
        locale.setlocale(locale.LC_TIME, "")
    except locale.Error:
        pass


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="mirrorberry", description="MirrorBerry display")
    parser.add_argument("-c", "--config", type=Path, default=DEFAULT_CONFIG_PATH,
                        help="path to config.toml (default: %(default)s)")
    parser.add_argument("--windowed", action="store_true",
                        help="run in a window instead of fullscreen (for development)")
    parser.add_argument("--size", type=_parse_size, metavar="WxH",
                        help="window size, implies --windowed")
    parser.add_argument("--backend", choices=("auto", "fbdev", "sdl"),
                        help="override display.backend from config.toml")
    parser.add_argument("--screenshot", metavar="PNG",
                        help="render one frame to an image and exit (no screen needed)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    try:
        config = load_config(args.config)
    except ValueError as exc:
        logging.getLogger("mirrorberry").error("config.toml: %s", exc)
        raise SystemExit(1) from None

    _apply_locale(config.locale)
    if args.windowed or args.size or args.screenshot:
        config.display.fullscreen = False
    if args.size:
        config.display.window_size = args.size
    if args.backend:
        config.display.backend = args.backend

    from .app import App  # imported late so SDL env vars are set first

    try:
        if args.screenshot:
            App(config, headless=True).screenshot(args.screenshot)
        else:
            App(config).run()
    except (RuntimeError, ValueError) as exc:
        logging.getLogger("mirrorberry").error("%s", exc)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
