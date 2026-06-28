"""Fast row layout for pipeline tests (avoids slow NFP nesting in CI)."""

from __future__ import annotations

from app.models.geometry import LayoutPage, PlacedPiece, UnfoldPiece
from app.schemas.model import PaperSize
from app.services.layout_engine import (
    MARGIN_MM,
    PAPER_SIZES_MM,
    find_pieces_too_large_for_paper,
    piece_bounds,
)


def layout_pieces_row(
    pieces: list[UnfoldPiece],
    paper_size: PaperSize,
    gap_mm: float = 8.0,
) -> list[LayoutPage]:
    """Place pieces left-to-right, top-to-bottom without NFP (test helper)."""
    if not pieces:
        return []

    if find_pieces_too_large_for_paper(pieces, paper_size):
        return []

    page_w, page_h = PAPER_SIZES_MM[paper_size]
    usable_w = page_w - 2 * MARGIN_MM
    usable_h = page_h - 2 * MARGIN_MM

    pages: list[LayoutPage] = []
    page_index = 0
    cursor_x = MARGIN_MM
    cursor_y = MARGIN_MM
    row_height = 0.0
    placed: list[PlacedPiece] = []

    def flush_page() -> None:
        nonlocal page_index, cursor_x, cursor_y, row_height, placed
        if placed:
            pages.append(
                LayoutPage(
                    index=page_index,
                    width_mm=page_w,
                    height_mm=page_h,
                    placed_pieces=placed,
                )
            )
            page_index += 1
            placed = []
            cursor_x = MARGIN_MM
            cursor_y = MARGIN_MM
            row_height = 0.0

    for piece in pieces:
        min_x, min_y, max_x, max_y = piece_bounds(piece, include_tabs=True)
        width = max_x - min_x
        height = max_y - min_y

        if width > usable_w or height > usable_h:
            continue

        if cursor_x + width > MARGIN_MM + usable_w and cursor_x > MARGIN_MM:
            cursor_x = MARGIN_MM
            cursor_y += row_height + gap_mm
            row_height = 0.0

        if cursor_y + height > MARGIN_MM + usable_h:
            flush_page()
            if height > usable_h:
                continue

        placed.append(
            PlacedPiece(
                piece=piece,
                offset_x=cursor_x - min_x,
                offset_y=cursor_y - min_y,
                page_index=page_index,
            )
        )
        cursor_x += width + gap_mm
        row_height = max(row_height, height)

    if placed:
        pages.append(
            LayoutPage(
                index=page_index,
                width_mm=page_w,
                height_mm=page_h,
                placed_pieces=placed,
            )
        )

    return pages
