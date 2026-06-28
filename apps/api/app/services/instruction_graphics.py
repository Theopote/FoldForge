"""Shared 2D drawing helpers for instruction illustrations."""

from __future__ import annotations

from app.models.geometry import Point2D, UnfoldPiece


def piece_outline_points(piece: UnfoldPiece) -> list[Point2D]:
    if piece.cut_outline and len(piece.cut_outline) >= 3:
        return piece.cut_outline
    return piece.polygon


def piece_bounds(points: list[Point2D]) -> tuple[float, float, float, float]:
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def map_points_to_box(
    points: list[Point2D],
    x: float,
    y: float,
    size: float,
    *,
    padding: float = 0.86,
) -> list[tuple[float, float]]:
    if len(points) < 3:
        return []

    min_x, min_y, max_x, max_y = piece_bounds(points)
    width = max(max_x - min_x, 1e-6)
    height = max(max_y - min_y, 1e-6)
    scale = min(size / width, size / height) * padding
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0

    return [
        (x + size / 2 + (point.x - center_x) * scale, y + size / 2 + (point.y - center_y) * scale)
        for point in points
    ]


def find_cut_line(piece: UnfoldPiece, edge_id: str):
    for cut in piece.cut_lines:
        if cut.id == edge_id:
            return cut
    return None


def find_shared_cut_line(target: UnfoldPiece, mesh_edge: tuple[int, int] | None):
    if mesh_edge is None:
        return None
    key = tuple(sorted(mesh_edge))
    for cut in target.cut_lines:
        if cut.mesh_edge is not None and tuple(sorted(cut.mesh_edge)) == key:
            return cut
    return None
