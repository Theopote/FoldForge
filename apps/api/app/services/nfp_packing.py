"""No-Fit Polygon helpers — convex decomposition + irregular nesting."""

from __future__ import annotations

from shapely.affinity import scale, translate
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union


from app.services.cancel import CancelCheck, check_cancelled


def reflect_at_origin(polygon: Polygon) -> Polygon:
    """Reflect polygon through the origin (for Minkowski difference)."""
    reflected = scale(polygon, xfact=-1.0, yfact=-1.0, origin=(0.0, 0.0))
    if reflected.is_empty:
        return polygon
    return reflected


def minkowski_sum_convex(base: Polygon, shape: Polygon) -> Polygon:
    """Minkowski sum of two convex polygons."""
    if base.is_empty or shape.is_empty:
        return Polygon()

    parts: list[Polygon] = []
    for x, y in base.exterior.coords[:-1]:
        moved = translate(shape, xoff=x, yoff=y)
        if not moved.is_empty:
            parts.append(moved)

    if not parts:
        return Polygon()

    merged = unary_union(parts)
    if merged.geom_type == "Polygon":
        return merged
    if merged.geom_type == "MultiPolygon":
        return max(merged.geoms, key=lambda geom: geom.area)
    return merged.convex_hull


def _cross_z(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx


def _is_convex_ring(coords: list[tuple[float, float]]) -> bool:
    if len(coords) < 3:
        return True
    sign = 0
    n = len(coords)
    for i in range(n):
        x1, y1 = coords[i]
        x2, y2 = coords[(i + 1) % n]
        x3, y3 = coords[(i + 2) % n]
        cross = _cross_z(x2 - x1, y2 - y1, x3 - x2, y3 - y2)
        if abs(cross) < 1e-10:
            continue
        current = 1 if cross > 0 else -1
        if sign == 0:
            sign = current
        elif current != sign:
            return False
    return True


def _fan_triangulate(coords: list[tuple[float, float]]) -> list[Polygon]:
    """Fan triangulation from the first vertex."""
    if len(coords) < 3:
        return []
    anchor = coords[0]
    triangles: list[Polygon] = []
    for i in range(1, len(coords) - 1):
        tri = Polygon([anchor, coords[i], coords[i + 1]])
        if tri.is_valid and not tri.is_empty and tri.area > 1e-6:
            triangles.append(tri)
    return triangles


def _split_at_reflex_vertices(polygon: Polygon) -> list[Polygon]:
    """Split a simple polygon into convex parts at reflex vertices."""
    coords = list(polygon.exterior.coords[:-1])
    if len(coords) < 4:
        return [polygon] if polygon.is_valid and not polygon.is_empty else []

    n = len(coords)
    reflex_indices: list[int] = []
    area_sign = 1.0 if polygon.area >= 0 else -1.0

    for i in range(n):
        x0, y0 = coords[(i - 1) % n]
        x1, y1 = coords[i]
        x2, y2 = coords[(i + 1) % n]
        cross = _cross_z(x1 - x0, y1 - y0, x2 - x1, y2 - y1) * area_sign
        if cross < -1e-10:
            reflex_indices.append(i)

    if not reflex_indices:
        return [polygon]

    parts: list[Polygon] = []
    split_points = reflex_indices + [n]
    start = 0
    for split in split_points:
        segment = coords[start : split + 1]
        if len(segment) >= 3:
            try:
                part = Polygon(segment)
                if part.is_valid and not part.is_empty:
                    if _is_convex_ring(segment):
                        parts.append(part)
                    else:
                        parts.extend(_fan_triangulate(segment))
            except Exception:
                pass
        start = split

    tail = coords[start:] + [coords[0]]
    if len(tail) >= 3:
        try:
            part = Polygon(tail)
            if part.is_valid and not part.is_empty:
                if _is_convex_ring(tail):
                    parts.append(part)
                else:
                    parts.extend(_fan_triangulate(tail))
        except Exception:
            pass

    return parts if parts else _fan_triangulate(coords)


def decompose_to_convex_parts(polygon: Polygon) -> list[Polygon]:
    """
    Decompose a (possibly non-convex) polygon into convex pieces.

    Uses reflex-vertex splitting with fan-triangulation fallback.
    """
    if polygon.is_empty or not polygon.is_valid:
        cleaned = polygon.buffer(0)
        if cleaned.is_empty:
            return []
        if cleaned.geom_type == "Polygon":
            polygon = cleaned
        elif cleaned.geom_type == "MultiPolygon":
            parts: list[Polygon] = []
            for geom in cleaned.geoms:
                parts.extend(decompose_to_convex_parts(geom))
            return parts
        else:
            return []

    coords = list(polygon.exterior.coords[:-1])
    if len(coords) < 3:
        return []
    if len(coords) == 3:
        return [polygon]
    if _is_convex_ring(coords):
        return [polygon]

    parts = _split_at_reflex_vertices(polygon)
    if not parts:
        return _fan_triangulate(coords)
    return parts


def no_fit_polygon_convex(stationary: Polygon, orbiting: Polygon) -> Polygon:
    """NFP via convex hull Minkowski sum (fast conservative approximation)."""
    if stationary.is_empty or orbiting.is_empty:
        return Polygon()
    base = stationary.convex_hull
    reflected = reflect_at_origin(orbiting.convex_hull)
    return minkowski_sum_convex(base, reflected)


def no_fit_polygon(stationary: Polygon, orbiting: Polygon) -> Polygon | MultiPolygon:
    """
    Exact non-convex NFP via orbiting algorithm, with decomposition fallback.

    NFP(A, B) is the locus of reference-point positions where B touches A without overlap.
    """
    from app.services.nfp_orbiting import no_fit_polygon_exact

    return no_fit_polygon_exact(stationary, orbiting)


def nfp_reference_point(polygon: Polygon) -> tuple[float, float]:
    minx, miny, _, _ = polygon.bounds
    return minx, miny


def nfp_placement_candidates(
    stationary_polygons: list[Polygon],
    orbiting_polygon: Polygon,
    *,
    edge_step_mm: float = 6.0,
    cancel_check: CancelCheck | None = None,
) -> list[tuple[float, float]]:
    """Generate candidate reference-point positions from decomposed NFP boundaries."""
    ref_x, ref_y = nfp_reference_point(orbiting_polygon)
    orbiting_at_origin = translate(orbiting_polygon, xoff=-ref_x, yoff=-ref_y)

    candidates: set[tuple[float, float]] = set()

    for stationary in stationary_polygons:
        check_cancelled(cancel_check)
        if stationary.is_empty:
            continue

        nfp = no_fit_polygon(stationary, orbiting_at_origin)
        if nfp.is_empty:
            continue

        geoms = [nfp] if nfp.geom_type == "Polygon" else list(nfp.geoms)

        for geom in geoms:
            if geom.is_empty:
                continue
            coords = list(geom.exterior.coords)
            for x, y in coords:
                candidates.add((round(x, 2), round(y, 2)))

            for i in range(len(coords) - 1):
                check_cancelled(cancel_check)
                x0, y0 = coords[i]
                x1, y1 = coords[i + 1]
                length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
                steps = max(1, int(length / edge_step_mm))
                for step in range(steps + 1):
                    if step % 16 == 0:
                        check_cancelled(cancel_check)
                    t = step / steps
                    candidates.add((
                        round(x0 + (x1 - x0) * t, 2),
                        round(y0 + (y1 - y0) * t, 2),
                    ))

    return sorted(candidates, key=lambda pos: (pos[1], pos[0]))


def orbiting_polygon_at_reference(
    orbiting_polygon: Polygon,
    ref_x: float,
    ref_y: float,
    candidate_x: float,
    candidate_y: float,
) -> Polygon:
    dx = candidate_x - ref_x
    dy = candidate_y - ref_y
    return translate(orbiting_polygon, xoff=dx, yoff=dy)
