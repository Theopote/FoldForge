"""Generate glue tabs on piece boundary edges."""

import math

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


def add_tabs_to_pieces(
    pieces: list[UnfoldPiece],
    add_tabs: bool,
    add_numbers: bool,
) -> list[UnfoldPiece]:
    """
    Add glue tabs along cut-line edges and optional matching labels.

    MVP: tabs on all cut lines with sufficient length, labeled for manual matching.
    """
    if not add_tabs:
        return pieces

    updated: list[UnfoldPiece] = []

    for piece in pieces:
        tabs: list[Tab] = []
        for index, cut in enumerate(piece.cut_lines):
            length = math.hypot(cut.end.x - cut.start.x, cut.end.y - cut.start.y)
            if length < MIN_EDGE_LENGTH_MM:
                continue

            nx, ny = _edge_normal(cut.start, cut.end)
            tab_polygon = [
                cut.start,
                cut.end,
                Point2D(cut.end.x + nx * TAB_WIDTH_MM, cut.end.y + ny * TAB_WIDTH_MM),
                Point2D(cut.start.x + nx * TAB_WIDTH_MM, cut.start.y + ny * TAB_WIDTH_MM),
            ]

            label = str(index + 1) if add_numbers else ""
            tabs.append(
                Tab(
                    id=f"tab-{piece.label}-{index}",
                    edge_id=cut.id,
                    polygon=tab_polygon,
                    target_piece_id="",
                    label=label,
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
