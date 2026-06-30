"""Shared geometry helpers used by the papercraft pipeline."""

from typing import Sequence


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a numeric value to the given range."""
    return max(minimum, min(maximum, value))


def polygon_area(points: Sequence[tuple[float, float]]) -> float:
    """Compute signed polygon area using the shoelace formula."""
    if len(points) < 3:
        return 0.0

    area = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0
