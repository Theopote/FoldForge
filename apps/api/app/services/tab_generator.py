"""Generate paired glue tabs on shared seam edges."""

from __future__ import annotations

import math
from collections import defaultdict

from app.models.geometry import Point2D, Tab, UnfoldPiece

TAB_WIDTH_MM = 8.0
MIN_EDGE_LENGTH_MM = 6.0


def _edge_normal(start: Point2D, end: Point2D, sign: float = 1.0) -> tuple[float, float]:
    dx = end.x - start.x
    dy = end.y - start.y
    length = math.hypot(dx, dy)
    if length < 1e-8:
        return (0.0, sign)
    return (-dy / length * sign, dx / length * sign)


def _polygon_centroid(polygon: list[Point2D]) -> tuple[float, float]:
    if not polygon:
        return 0.0, 0.0
    return (
        sum(p.x for p in polygon) / len(polygon),
        sum(p.y for p in polygon) / len(polygon),
    )


def _outward_normal(piece: UnfoldPiece, start: Point2D, end: Point2D) -> tuple[float, float]:
    """Edge normal pointing away from the piece interior."""
    nx, ny = _edge_normal(start, end)
    cx, cy = _polygon_centroid(piece.polygon)
    mx = (start.x + end.x) * 0.5
    my = (start.y + end.y) * 0.5
    if (mx - cx) * nx + (my - cy) * ny < 0:
        nx, ny = -nx, -ny
    return nx, ny


def _tab_polygon(
    cut_start: Point2D,
    cut_end: Point2D,
    nx: float,
    ny: float,
) -> list[Point2D]:
    return [
        cut_start,
        cut_end,
        Point2D(cut_end.x + nx * TAB_WIDTH_MM, cut_end.y + ny * TAB_WIDTH_MM),
        Point2D(cut_start.x + nx * TAB_WIDTH_MM, cut_start.y + ny * TAB_WIDTH_MM),
    ]


def add_tabs_to_pieces(
    pieces: list[UnfoldPiece],
    add_tabs: bool,
    add_numbers: bool,
) -> list[UnfoldPiece]:
    """
    Add glue tabs with cross-piece pairing on shared 3D seam edges.

    Each shared seam gets one tab on the lexicographically smaller piece label;
    tabs are labeled with mate IDs (e.g. A1-B2).
    """
    if not add_tabs:
        return pieces

    edge_refs: dict[tuple[int, int], list[tuple[UnfoldPiece, int, object]]] = defaultdict(list)
    for piece in pieces:
        for index, cut in enumerate(piece.cut_lines):
            if cut.mesh_edge is not None:
                edge_refs[cut.mesh_edge].append((piece, index, cut))

    tab_assignments: dict[tuple[str, int], Tab] = {}
    tab_owner_piece: dict[tuple[int, int], str] = {}
    pair_counter = 0

    for mesh_edge, refs in edge_refs.items():
        if len(refs) < 2:
            continue

        refs_sorted = sorted(refs, key=lambda item: (item[0].label, item[1]))
        (piece_a, idx_a, cut_a) = refs_sorted[0]
        (piece_b, _idx_b, _cut_b) = refs_sorted[1]

        length = math.hypot(cut_a.end.x - cut_a.start.x, cut_a.end.y - cut_a.start.y)
        if length < MIN_EDGE_LENGTH_MM:
            continue

        pair_counter += 1
        label = f"{piece_a.label}{pair_counter}-{piece_b.label}{pair_counter}"
        nx, ny = _outward_normal(piece_a, cut_a.start, cut_a.end)
        tab_owner_piece[mesh_edge] = piece_a.id

        tab_assignments[(piece_a.id, idx_a)] = Tab(
            id=f"tab-{piece_a.label}-{idx_a}",
            edge_id=cut_a.id,
            polygon=_tab_polygon(cut_a.start, cut_a.end, nx, ny),
            target_piece_id=piece_b.id,
            label=label if add_numbers else "",
        )

    updated: list[UnfoldPiece] = []

    for piece in pieces:
        tabs: list[Tab] = []
        for index, cut in enumerate(piece.cut_lines):
            if cut.mesh_edge is not None and tab_owner_piece.get(cut.mesh_edge) != piece.id:
                if cut.mesh_edge in tab_owner_piece:
                    continue

            assigned = tab_assignments.get((piece.id, index))
            if assigned is not None:
                tabs.append(assigned)
                continue

            length = math.hypot(cut.end.x - cut.start.x, cut.end.y - cut.start.y)
            if length < MIN_EDGE_LENGTH_MM:
                continue

            nx, ny = _outward_normal(piece, cut.start, cut.end)
            tabs.append(
                Tab(
                    id=f"tab-{piece.label}-{index}",
                    edge_id=cut.id,
                    polygon=_tab_polygon(cut.start, cut.end, nx, ny),
                    target_piece_id="",
                    label=str(index + 1) if add_numbers else "",
                )
            )

        updated.append(
            UnfoldPiece(
                id=piece.id,
                face_ids=piece.face_ids,
                polygon=piece.polygon,
                fold_lines=piece.fold_lines,
                cut_lines=piece.cut_lines,
                tabs=tabs,
                label=piece.label,
                has_overlap=piece.has_overlap,
            )
        )

    return updated
