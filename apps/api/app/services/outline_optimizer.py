"""Boolean union of piece body + tabs into a unified cut outline."""

from __future__ import annotations

from shapely.geometry import Polygon
from shapely.ops import unary_union

from app.models.geometry import Point2D, UnfoldPiece


def _to_valid_polygon(points: list[Point2D]) -> Polygon | None:
    if len(points) < 3:
        return None
    try:
        poly = Polygon([p.as_tuple() for p in points])
        if poly.is_empty or not poly.is_valid:
            cleaned = poly.buffer(0)
            if cleaned.is_empty:
                return None
            if cleaned.geom_type == "Polygon":
                return cleaned
            if cleaned.geom_type == "MultiPolygon":
                return max(cleaned.geoms, key=lambda geom: geom.area)
            return None
        return poly
    except Exception:
        return None


def _extract_exterior(polygon) -> list[Point2D]:
    if polygon.is_empty:
        return []

    if polygon.geom_type == "Polygon":
        return [Point2D(float(x), float(y)) for x, y in polygon.exterior.coords]

    if polygon.geom_type == "MultiPolygon":
        largest = max(polygon.geoms, key=lambda geom: geom.area)
        return [Point2D(float(x), float(y)) for x, y in largest.exterior.coords]

    return []


def optimize_piece_cut_outline(piece: UnfoldPiece, *, simplify_mm: float = 0.15) -> UnfoldPiece:
    """
    Merge piece body and glue tabs via boolean union into one cut contour.

    Stores the result in `cut_outline` for export/layout; original polygon and tab
    polygons are preserved for fold lines and labels.
    """
    parts: list[Polygon] = []

    body = _to_valid_polygon(piece.polygon)
    if body is not None:
        parts.append(body)

    for tab in piece.tabs:
        tab_poly = _to_valid_polygon(tab.polygon)
        if tab_poly is not None:
            parts.append(tab_poly)

    if not parts:
        return piece

    merged = unary_union(parts).buffer(0)
    if simplify_mm > 0 and not merged.is_empty:
        merged = merged.simplify(simplify_mm, preserve_topology=True).buffer(0)

    cut_outline = _extract_exterior(merged)
    if len(cut_outline) < 3:
        return piece

    return UnfoldPiece(
        id=piece.id,
        face_ids=piece.face_ids,
        polygon=piece.polygon,
        tabs=piece.tabs,
        fold_lines=piece.fold_lines,
        cut_lines=piece.cut_lines,
        label=piece.label,
        has_overlap=piece.has_overlap,
        cut_outline=cut_outline,
    )


def optimize_pieces_cut_outlines(pieces: list[UnfoldPiece]) -> list[UnfoldPiece]:
    """Apply boolean cut-outline optimization to all pieces."""
    return [optimize_piece_cut_outline(piece) for piece in pieces]
