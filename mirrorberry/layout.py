# SPDX-License-Identifier: GPL-3.0-or-later
"""The 3x3 zone grid.

Zones are addressed by name (TopLeft ... BottomRight). Geometry is computed
from the logical screen size plus relative column/row weights, so the grid
adapts to any resolution or orientation without code changes.
"""

from __future__ import annotations

from enum import Enum
from itertools import accumulate
from typing import Sequence

import pygame


class Zone(Enum):
    """Nine screen regions. The value is (row, column)."""

    TopLeft = (0, 0)
    TopCenter = (0, 1)
    TopRight = (0, 2)
    CenterLeft = (1, 0)
    Center = (1, 1)
    CenterRight = (1, 2)
    BottomLeft = (2, 0)
    BottomCenter = (2, 1)
    BottomRight = (2, 2)

    @property
    def row(self) -> int:
        return self.value[0]

    @property
    def col(self) -> int:
        return self.value[1]

    @classmethod
    def from_name(cls, name: str) -> "Zone":
        try:
            return cls[name]
        except KeyError:
            valid = ", ".join(z.name for z in cls)
            raise ValueError(f"Unknown zone {name!r}. Valid zones: {valid}") from None


def _split(total: int, weights: Sequence[float]) -> list[int]:
    """Divide `total` pixels by `weights`, keeping the sum exact."""
    weight_sum = sum(weights)
    sizes = [int(total * w / weight_sum) for w in weights]
    sizes[-1] += total - sum(sizes)  # rounding leftovers go to the last track
    return sizes


def _offsets(start: int, sizes: Sequence[int], gutter: int) -> list[int]:
    """Start coordinate of each track, given sizes and the gap between them."""
    return [start + o for o in accumulate((s + gutter for s in sizes[:-1]), initial=0)]


def compute_zone_rects(
    size: tuple[int, int],
    column_weights: Sequence[float] = (1, 1, 1),
    row_weights: Sequence[float] = (1, 1, 1),
    margin: int = 0,
    gutter: int = 0,
) -> dict[Zone, pygame.Rect]:
    """Return the pixel rectangle for every zone.

    A weight of 0 collapses that column/row (its zones get zero width/height),
    which is handy for layouts that don't use the side columns.
    """
    for label, weights in (("column_weights", column_weights), ("row_weights", row_weights)):
        if len(weights) != 3:
            raise ValueError(f"{label} needs exactly 3 values, got {len(weights)}")
        if any(w < 0 for w in weights) or sum(weights) <= 0:
            raise ValueError(f"{label} must be non-negative with a positive sum")

    width, height = size
    inner_w = width - 2 * margin - 2 * gutter
    inner_h = height - 2 * margin - 2 * gutter
    if inner_w <= 0 or inner_h <= 0:
        raise ValueError(f"margin/gutter leave no room on a {width}x{height} screen")

    col_w = _split(inner_w, column_weights)
    row_h = _split(inner_h, row_weights)
    col_x = _offsets(margin, col_w, gutter)
    row_y = _offsets(margin, row_h, gutter)

    return {
        zone: pygame.Rect(col_x[zone.col], row_y[zone.row], col_w[zone.col], row_h[zone.row])
        for zone in Zone
    }
