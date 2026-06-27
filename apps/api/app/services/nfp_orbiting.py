"""Exact non-convex NFP via orbiting (sliding) algorithm."""

from __future__ import annotations

import math

from shapely.geometry import MultiPoint, Polygon
from shapely.ops import polygonize, unary_union
from shapely.prepared import prep

from app.services.nfp_packing import (
    _is_convex_ring,
    decompose_to_convex_parts,
    minkowski_sum_convex,
    reflect_at_origin,
)

TOUCH_EPS = 1e-4
OVERLAP_EPS = 1e-5


def _signed_area(ring: list[tuple[float, float]]) -> float:
    area = 0.0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        area += x0 * y1 - x1 * y0
    return area * 0.5


def _ensure_ccw_ring(polygon: Polygon) -> list[tuple[float, float]]:
    if polygon.is_empty:
        return []
    ring = [(float(x), float(y)) for x, y in polygon.exterior.coords[:-1]]
    if len(ring) < 3:
        return ring
    if _signed_area(ring) < 0:
        ring.reverse()
    return ring


def _translate_ring(ring: list[tuple[float, float]], tx: float, ty: float) -> list[tuple[float, float]]:
    return [(x + tx, y + ty) for x, y in ring]


def _ring_polygon(ring: list[tuple[float, float]]) -> Polygon:
    if len(ring) < 3:
        return Polygon()
    poly = Polygon(ring)
    if poly.is_valid and not poly.is_empty:
        return poly
    cleaned = poly.buffer(0)
    return cleaned if not cleaned.is_empty else Polygon()


def _is_valid_touch_placement(
    stationary: Polygon,
    b_ring: list[tuple[float, float]],
    tx: float,
    ty: float,
    *,
    prepared_stationary,
) -> bool:
    moved = _ring_polygon(_translate_ring(b_ring, tx, ty))
    if moved.is_empty:
        return False
    if prepared_stationary.intersects(moved):
        if stationary.intersection(moved).area > OVERLAP_EPS:
            return False
    return stationary.distance(moved) <= TOUCH_EPS


def _edge_edge_translations(
    a0: tuple[float, float],
    a1: tuple[float, float],
    b0: tuple[float, float],
    b1: tuple[float, float],
) -> list[tuple[float, float]]:
    """Translations where anti-parallel edges touch (sliding contacts)."""
    ax, ay = a1[0] - a0[0], a1[1] - a0[1]
    bx, by = b1[0] - b0[0], b1[1] - b0[1]
    la = math.hypot(ax, ay)
    lb = math.hypot(bx, by)
    if la < 1e-9 or lb < 1e-9:
        return []

    dot = (ax * bx + ay * by) / (la * lb)
    if dot > -0.85:
        return []

    translations: list[tuple[float, float]] = []
    for t in (0.0, 0.5, 1.0):
        px = a0[0] + ax * t
        py = a0[1] + ay * t
        translations.append((px - b0[0], py - b0[1]))
        translations.append((px - b1[0], py - b1[1]))
    return translations


def _collect_touch_translations(
    stationary: Polygon,
    a_ring: list[tuple[float, float]],
    b_ring: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    if stationary.is_empty:
        return []

    prepared = prep(stationary)
    candidates: set[tuple[float, float]] = set()

    for ax, ay in a_ring:
        for bx, by in b_ring:
            tx, ty = ax - bx, ay - by
            if _is_valid_touch_placement(stationary, b_ring, tx, ty, prepared_stationary=prepared):
                candidates.add((round(tx, 3), round(ty, 3)))

    n_a = len(a_ring)
    n_b = len(b_ring)
    for i in range(n_a):
        a0, a1 = a_ring[i], a_ring[(i + 1) % n_a]
        for j in range(n_b):
            b0, b1 = b_ring[j], b_ring[(j + 1) % n_b]
            for tx, ty in _edge_edge_translations(a0, a1, b0, b1):
                if _is_valid_touch_placement(stationary, b_ring, tx, ty, prepared_stationary=prepared):
                    candidates.add((round(tx, 3), round(ty, 3)))

    return list(candidates)


def _pick_start_translation(
    a_ring: list[tuple[float, float]],
    b_ring: list[tuple[float, float]],
    candidates: list[tuple[float, float]],
) -> tuple[float, float] | None:
    if not candidates:
        return None

    a_bottom = min(a_ring, key=lambda p: (p[1], p[0]))
    b_top = max(b_ring, key=lambda p: p[1])
    preferred = (round(a_bottom[0] - b_top[0], 3), round(a_bottom[1] - b_top[1], 3))

    if preferred in candidates:
        return preferred

    return min(candidates, key=lambda p: (p[1], p[0]))


def _angular_distance(ref: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    v1 = (a[0] - ref[0], a[1] - ref[1])
    v2 = (b[0] - ref[0], b[1] - ref[1])
    cross = v1[0] * v2[1] - v1[1] * v2[0]
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    return math.atan2(cross, dot)


def _orbiting_walk(
    stationary: Polygon,
    b_ring: list[tuple[float, float]],
    candidates: list[tuple[float, float]],
    start: tuple[float, float],
) -> list[tuple[float, float]]:
    """Walk touching placements counter-clockwise to trace NFP boundary."""
    if len(candidates) < 3:
        return candidates

    prepared = prep(stationary)
    remaining = set(candidates)
    path = [start]
    remaining.discard(start)
    current = start
    max_steps = min(len(candidates) * 2, 512)

    for _ in range(max_steps):
        neighbors = [
            point
            for point in remaining
            if _is_valid_touch_placement(
                stationary, b_ring, point[0], point[1], prepared_stationary=prepared,
            )
        ]
        if not neighbors:
            break

        prev = path[-2] if len(path) >= 2 else (current[0] - 1.0, current[1])
        next_point = max(
            neighbors,
            key=lambda p: _angular_distance(current, prev, p),
        )

        if len(path) > 2 and next_point == path[0]:
            break
        if next_point == current:
            break

        path.append(next_point)
        remaining.discard(next_point)
        current = next_point

    return path


def _polygon_from_orbit_path(path: list[tuple[float, float]]) -> Polygon:
    if len(path) < 3:
        return Polygon()

    try:
        poly = Polygon(path)
        if poly.is_valid and not poly.is_empty and poly.area > 1e-6:
            return poly
    except Exception:
        pass

    try:
        polys = list(polygonize(path))
        if polys:
            return max(polys, key=lambda geom: geom.area)
    except Exception:
        pass

    try:
        hull = MultiPoint(path).convex_hull
        if not hull.is_empty:
            return hull
    except Exception:
        pass

    return Polygon()


def _polygon_is_convex(polygon: Polygon) -> bool:
    if polygon.is_empty:
        return False
    coords = list(polygon.exterior.coords[:-1])
    return _is_convex_ring(coords)


def _nfp_convex_decomposition(stationary: Polygon, reflected: Polygon) -> Polygon:
    s_parts = decompose_to_convex_parts(stationary)
    b_parts = decompose_to_convex_parts(reflected)
    if not s_parts or not b_parts:
        return minkowski_sum_convex(stationary.convex_hull, reflected.convex_hull)

    parts: list[Polygon] = []
    for s_part in s_parts:
        for b_part in b_parts:
            nfp = minkowski_sum_convex(s_part.convex_hull, b_part.convex_hull)
            if not nfp.is_empty:
                parts.append(nfp)

    if not parts:
        return Polygon()

    merged = unary_union(parts)
    return merged.buffer(0) if not merged.is_empty else Polygon()


def no_fit_polygon_orbiting(stationary: Polygon, orbiting: Polygon) -> Polygon:
    """
    Compute NFP(A, B) by orbiting -B around A.

    B is reflected through the origin; returned NFP vertices are reference-point
    positions (where B's reference corner may sit tangent to A).
    """
    if stationary.is_empty or orbiting.is_empty:
        return Polygon()

    cleaned = stationary.buffer(0)
    if cleaned.is_empty:
        return Polygon()
    if cleaned.geom_type == "MultiPolygon":
        cleaned = max(cleaned.geoms, key=lambda geom: geom.area)
    stationary = cleaned

    a_ring = _ensure_ccw_ring(stationary)
    b_ring = _ensure_ccw_ring(reflect_at_origin(orbiting))
    if len(a_ring) < 3 or len(b_ring) < 3:
        return Polygon()

    candidates = _collect_touch_translations(stationary, a_ring, b_ring)
    if len(candidates) < 3:
        return Polygon()

    start = _pick_start_translation(a_ring, b_ring, candidates)
    if start is None:
        return Polygon()

    path = _orbiting_walk(stationary, b_ring, candidates, start)
    nfp = _polygon_from_orbit_path(path)
    if nfp.is_empty:
        return Polygon()
    return nfp if nfp.is_valid else nfp.buffer(0)


def no_fit_polygon_exact(stationary: Polygon, orbiting: Polygon) -> Polygon:
    """Exact NFP: convex Minkowski, non-convex orbiting, decomposition fallback."""
    if stationary.is_empty or orbiting.is_empty:
        return Polygon()

    reflected = reflect_at_origin(orbiting)
    stationary_convex = _polygon_is_convex(stationary)
    orbiting_convex = _polygon_is_convex(orbiting)

    if stationary_convex and orbiting_convex:
        return minkowski_sum_convex(stationary, reflected)

    if stationary_convex:
        return _nfp_convex_decomposition(stationary, reflected)

    orbiting_nfp = no_fit_polygon_orbiting(stationary, orbiting)
    if not orbiting_nfp.is_empty and orbiting_nfp.area > 1e-4:
        return orbiting_nfp

    return _nfp_convex_decomposition(stationary, reflected)
