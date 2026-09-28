# SPDX-License-Identifier: GPL-3.0-or-later
"""Background fetching for widgets that need the network.

A Poller runs a function in a daemon thread every ``interval`` seconds and
keeps the last good result, so the display never waits on the network and
keeps showing data through short outages. Widgets poll ``version`` to see
when something new arrived. Pollers are shared by key, so e.g. a current-
weather and a forecast widget for the same place make one request.
"""

from __future__ import annotations

import logging
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from . import __version__

MIN_INTERVAL = 60  # seconds; anything shorter is almost certainly minutes typed as seconds


def interval_option(name: str, value) -> float:
    """A fetch interval from config.toml, in seconds (at least a minute, to spare the APIs)."""
    seconds = float(value)
    if seconds < MIN_INTERVAL:
        raise ValueError(f"{name} is in seconds and must be at least {MIN_INTERVAL} (got {seconds:g})")
    return seconds

log = logging.getLogger(__name__)

USER_AGENT = f"MirrorBerry/{__version__} (Raspberry Pi smart mirror)"


def http_get(url: str, timeout: float = 30) -> bytes:
    if url.startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


class AuthError(Exception):
    """The service rejected our credentials (API key)."""


def error_kind(exc: BaseException) -> str:
    """Map an exception to one of MagicMirror's error messages."""
    if isinstance(exc, AuthError):
        return "ERROR_UNAUTHORIZED"
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code in (401, 403):
            return "ERROR_UNAUTHORIZED"
        if exc.code == 429:
            return "ERROR_RATE_LIMITED"
        return "ERROR_SERVER" if exc.code >= 500 else "ERROR_CLIENT"
    if isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError, OSError)):
        return "ERROR_NO_CONNECTION"
    return "ERROR_CLIENT"


class Poller:
    _shared: dict[str, "Poller"] = {}
    _shared_lock = threading.Lock()

    def __init__(self, name: str, fn: Callable[[], Any], interval: float, retry: float = 60):
        self.name = name
        self.fn = fn
        self.interval = interval
        self.retry = retry
        self.data: Any = None
        self.error: str | None = None  # error kind while there is no good data
        self.version = 0
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._last_refresh = 0.0
        self._thread: threading.Thread | None = None

    @classmethod
    def shared(cls, key: str, name: str, fn: Callable[[], Any], interval: float) -> "Poller":
        with cls._shared_lock:
            poller = cls._shared.get(key)
            if poller is None:
                poller = cls._shared[key] = cls(name, fn, interval)
            else:
                poller.interval = min(poller.interval, interval)
            return poller

    def start(self) -> "Poller":
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name=f"poll-{self.name}", daemon=True)
            self._thread.start()
        return self

    def refresh(self, min_gap: float = 60) -> None:
        """Fetch again now instead of waiting for the interval (at most once per ``min_gap``)."""
        if time.monotonic() - self._last_refresh >= min_gap:
            self._last_refresh = time.monotonic()
            self._wake.set()

    def snapshot(self) -> tuple[int, Any, str | None]:
        with self._lock:
            return self.version, self.data, self.error

    def _run(self) -> None:
        failures = 0
        while True:
            started = time.monotonic()
            try:
                data = self.fn()
            except Exception as exc:  # network, parsing, anything: keep running
                failures += 1
                delay = min(self.interval, self.retry * 2 ** (failures - 1))
                log.warning("%s: update failed (%s: %s); retrying in %.0f s",
                            self.name, type(exc).__name__, exc, delay)
                with self._lock:
                    if self.data is None:
                        self.error = error_kind(exc)
                        self.version += 1
            else:
                failures = 0
                delay = self.interval
                log.info("%s: updated in %.1f s", self.name, time.monotonic() - started)
                with self._lock:
                    self.data, self.error = data, None
                    self.version += 1
            self._wake.wait(delay)
            self._wake.clear()
