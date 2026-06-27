"""No-Fit Polygon helpers for irregular 2D nesting."""

from __future__ import annotations

from shapely.affinity import scale, translate
from shapely.geometry import Polygon
from shapely.ops import unary_union


def reflect_at_origin(polygon: Polygon) -> Polygon:
    """Reflect polygon through the origin (for Minkowski difference)."""
    reflected = scale(polygon, xfact=-1.0, yfact=-1.0, origin=(0.0, 0.0))
    if reflected.is_empty:
        return polygon
    return reflected


def minkowski_sum_convex(base: Polygon, shape: Polygon) -> Polygon:
    """
    Minkowski sum of two convex polygons.

    base + shape = union of shape translated to each vertex of base.
    """
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


def no_fit_polygon(stationary: Polygon, orbiting: Polygon) -> Polygon:
    """
    Compute an NFP approximation via convex-hull Minkowski sum.

    NFP(A, B) = A ⊕ (-B). Using convex hulls is conservative but fast for
    papercraft pieces with moderate concavity.
    """
    if stationary.is_empty or orbiting.is_empty:
        return Polygon()

    base = stationary.convex_hull
    reflected = reflect_at_origin(orbiting.convex_hull)
    return minkowski_sum_convex(base, reflected)


def nfp_reference_point(polygon: Polygon) -> tuple[float, float]:
    """Bottom-left reference corner used when orbiting a piece."""
    minx, miny, _, _ = polygon.bounds
    return minx, miny


def nfp_placement_candidates(
    stationary_polygons: list[Polygon],
    orbiting_polygon: Polygon,
    *,
    edge_step_mm: float = 6.0,
) -> list[tuple[float, float]]:
    """
    Generate candidate reference-point positions from NFP boundaries.

    Each returned (x, y) is where the orbiting piece's bottom-left corner
    can sit adjacent to existing pieces without overlap (before fine collision).
    """
    ref_x, ref_y = nfp_reference_point(orbiting_polygon)
    orbiting_at_origin = translate(orbiting_polygon, xoff=-ref_x, yoff=-ref_y)

    candidates: set[tuple[float, float]] = set()

    for stationary in stationary_polygons:
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
                x0, y0 = coords[i]
                x1, y1 = coords[i + 1]
                length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
                steps = max(1, int(length / edge_step_mm))
                for step in range(steps + 1):
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
    """Place orbiting polygon so its reference corner sits at candidate."""
    dx = candidate_x - ref_x
    dy = candidate_y - ref_y
    return translate(orbiting_polygon, xoff=dx, yoff=dy)
