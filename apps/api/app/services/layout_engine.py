"""Layout unfolded pieces onto printable paper pages."""

from app.models.geometry import LayoutPage, PlacedPiece, UnfoldPiece
from app.schemas.model import PaperSize
from app.services.unfolder import (
    piece_bounds,
    piece_polygon_area,
    rotate_piece_90,
    translate_piece,
)

PAPER_SIZES_MM: dict[PaperSize, tuple[float, float]] = {
    PaperSize.A4: (210.0, 297.0),
    PaperSize.A3: (297.0, 420.0),
    PaperSize.LETTER: (215.9, 279.4),
}

MARGIN_MM = 10.0
GAP_MM = 8.0


def layout_pieces(
    pieces: list[UnfoldPiece],
    paper_size: PaperSize,
) -> list[LayoutPage]:
    """
    Pack pieces onto pages using shelf rows with 0°/90° rotation.

    Uses tab-inclusive bounds and prefers adding pages over downscaling to
    preserve 1:1 mm scale from target height.
    """
    page_width, page_height = PAPER_SIZES_MM[paper_size]
    usable_w = page_width - 2 * MARGIN_MM
    usable_h = page_height - 2 * MARGIN_MM

    sorted_pieces = sorted(
        pieces,
        key=lambda p: piece_polygon_area(p) or _bbox_area(p),
        reverse=True,
    )

    pages: list[LayoutPage] = []
    current_page = LayoutPage(index=0, width_mm=page_width, height_mm=page_height, placed_pieces=[])
    cursor_x = MARGIN_MM
    cursor_y = MARGIN_MM
    row_height = 0.0

    for piece in sorted_pieces:
        normalized, width, height, scaled = _best_orientation(piece, usable_w, usable_h)

        if cursor_x + width > MARGIN_MM + usable_w:
            cursor_x = MARGIN_MM
            cursor_y += row_height + GAP_MM
            row_height = 0.0

        if cursor_y + height > MARGIN_MM + usable_h:
            pages.append(current_page)
            current_page = LayoutPage(
                index=len(pages),
                width_mm=page_width,
                height_mm=page_height,
                placed_pieces=[],
            )
            cursor_x = MARGIN_MM
            cursor_y = MARGIN_MM
            row_height = 0.0

            # Fresh page — retry without row constraints
            normalized, width, height, scaled = _best_orientation(piece, usable_w, usable_h)

            if height > usable_h or width > usable_w:
                normalized, width, height, scaled = _best_orientation(
                    piece,
                    usable_w,
                    usable_h,
                    allow_scale=True,
                )

        placed = translate_piece(normalized, cursor_x, cursor_y)
        current_page.placed_pieces.append(
            PlacedPiece(
                piece=placed,
                offset_x=cursor_x,
                offset_y=cursor_y,
                page_index=current_page.index,
            ),
        )

        cursor_x += width + GAP_MM
        row_height = max(row_height, height)

        if scaled:
            current_page.placed_pieces[-1].piece.id = f"{piece.id}-scaled"

    if current_page.placed_pieces or not pages:
        pages.append(current_page)

    for index, page in enumerate(pages):
        page.index = index

    return pages


def _bbox_area(piece: UnfoldPiece) -> float:
    min_x, min_y, max_x, max_y = piece_bounds(piece, include_tabs=True)
    return max(0.0, (max_x - min_x) * (max_y - min_y))


def _normalize_to_origin(piece: UnfoldPiece) -> UnfoldPiece:
    min_x, min_y, _, _ = piece_bounds(piece, include_tabs=True)
    return translate_piece(piece, -min_x, -min_y)


def _best_orientation(
    piece: UnfoldPiece,
    usable_w: float,
    usable_h: float,
    *,
    allow_scale: bool = False,
) -> tuple[UnfoldPiece, float, float, bool]:
    """
    Pick 0° or 90° rotation (and optional uniform scale) that fits usable area.

    Returns (piece, width, height, was_scaled).
    """
    candidates: list[tuple[UnfoldPiece, float, float]] = []

    for candidate in (piece, rotate_piece_90(piece)):
        normalized = _normalize_to_origin(candidate)
        min_x, min_y, max_x, max_y = piece_bounds(normalized, include_tabs=True)
        width = max_x - min_x
        height = max_y - min_y
        candidates.append((normalized, width, height))

    # Prefer orientations that fit without scaling
    fitting = [
        (normalized, width, height)
        for normalized, width, height in candidates
        if width <= usable_w and height <= usable_h
    ]

    if fitting:
        normalized, width, height = min(fitting, key=lambda item: item[2])
        return normalized, width, height, False

    if not allow_scale:
        normalized, width, height = min(candidates, key=lambda item: item[1] * item[2])
        return normalized, width, height, False

    normalized, width, height = min(candidates, key=lambda item: item[1] * item[2])
    scale = min(usable_w / width, usable_h / height) * 0.98
    scaled_piece = _scale_piece(normalized, scale)
    min_x, min_y, max_x, max_y = piece_bounds(scaled_piece, include_tabs=True)
    return scaled_piece, max_x - min_x, max_y - min_y, True


def _scale_piece(piece: UnfoldPiece, scale: float) -> UnfoldPiece:
    """Uniformly scale a piece around its origin."""
    from app.models.geometry import CutLine, FoldLine, Point2D, Tab

    def scale_point(p: Point2D) -> Point2D:
        return Point2D(p.x * scale, p.y * scale)

    return UnfoldPiece(
        id=piece.id,
        face_ids=piece.face_ids,
        label=piece.label,
        has_overlap=piece.has_overlap,
        polygon=[scale_point(p) for p in piece.polygon],
        tabs=[
            Tab(
                id=t.id,
                edge_id=t.edge_id,
                target_piece_id=t.target_piece_id,
                label=t.label,
                polygon=[scale_point(p) for p in t.polygon],
            )
            for t in piece.tabs
        ],
        fold_lines=[
            FoldLine(
                id=f.id,
                fold_type=f.fold_type,
                start=scale_point(f.start),
                end=scale_point(f.end),
            )
            for f in piece.fold_lines
        ],
        cut_lines=[
            CutLine(
                id=c.id,
                start=scale_point(c.start),
                end=scale_point(c.end),
            )
            for c in piece.cut_lines
        ],
    )
