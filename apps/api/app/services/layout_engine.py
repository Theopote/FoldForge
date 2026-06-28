"""Layout unfolded pieces with Shapely collision-aware 2D nesting."""

from __future__ import annotations

from dataclasses import dataclass, field

from shapely.geometry import Polygon, box
from shapely.strtree import STRtree

from app.models.geometry import LayoutPage, PlacedPiece, UnfoldPiece
from app.schemas.model import PaperSize
from app.services.nfp_packing import nfp_placement_candidates
from app.services.unfolder import (
    piece_bounds,
    piece_polygon_area,
    piece_to_shapely,
    rotate_piece,
    translate_piece,
)

PAPER_SIZES_MM: dict[PaperSize, tuple[float, float]] = {
    PaperSize.A4: (210.0, 297.0),
    PaperSize.A3: (297.0, 420.0),
    PaperSize.LETTER: (215.9, 279.4),
}

MARGIN_MM = 10.0
DEFAULT_GAP_MM = 8.0
COLLISION_EPS_MM2 = 0.25
PLACEMENT_STEP_MM = 4.0


@dataclass
class LayoutIssueReport:
    has_overlaps: bool = False
    overlap_count: int = 0
    oversize_piece_labels: list[str] = field(default_factory=list)
    overflow_count: int = 0

    @property
    def scaled_piece_labels(self) -> list[str]:
        """Legacy alias — oversize pieces are never scaled down."""
        return self.oversize_piece_labels


def find_pieces_too_large_for_paper(
    pieces: list[UnfoldPiece],
    paper_size: PaperSize,
    *,
    target_height_mm: float | None = None,
) -> list:
    """Return pieces whose minimum rotated bbox exceeds the printable area."""
    from app.services.pipeline_errors import PieceTooLarge

    page_width, page_height = PAPER_SIZES_MM[paper_size]
    usable_w = page_width - 2 * MARGIN_MM
    usable_h = page_height - 2 * MARGIN_MM
    oversize: list[PieceTooLarge] = []

    for piece in pieces:
        if _piece_fits_paper(piece, usable_w, usable_h):
            continue

        label = piece.label or piece.id
        min_w, min_h = _smallest_rotated_bbox_mm(piece)
        suggested = None
        if target_height_mm is not None and min_w > 0 and min_h > 0:
            scale = min(usable_w / min_w, usable_h / min_h) * 0.95
            suggested = max(20.0, target_height_mm * scale)

        oversize.append(
            PieceTooLarge(
                label=label,
                width_mm=round(min_w, 1),
                height_mm=round(min_h, 1),
                paper_size=paper_size.value,
                usable_width_mm=round(usable_w, 1),
                usable_height_mm=round(usable_h, 1),
                suggested_target_height_mm=round(suggested, 1) if suggested else None,
            )
        )

    return oversize


def _piece_fits_paper(piece: UnfoldPiece, usable_w: float, usable_h: float) -> bool:
    for rotation in range(4):
        normalized = _normalize_to_origin(rotate_piece(piece, rotation))
        min_x, min_y, max_x, max_y = piece_bounds(normalized, include_tabs=True)
        width = max_x - min_x
        height = max_y - min_y
        if width <= usable_w and height <= usable_h:
            return True
    return False


def _smallest_rotated_bbox_mm(piece: UnfoldPiece) -> tuple[float, float]:
    """Dimensions of the most compact rotation (for error reporting)."""
    best_w = 0.0
    best_h = 0.0
    best_area = float("inf")
    for rotation in range(4):
        normalized = _normalize_to_origin(rotate_piece(piece, rotation))
        min_x, min_y, max_x, max_y = piece_bounds(normalized, include_tabs=True)
        width = max_x - min_x
        height = max_y - min_y
        area = width * height
        if area < best_area:
            best_area = area
            best_w = width
            best_h = height
    return best_w, best_h


def detect_layout_issues(pages: list[LayoutPage]) -> LayoutIssueReport:
    """Find page overlaps, printable-area overflows, and oversize pieces."""
    overlap_count = 0
    overflow_count = 0
    oversize_labels: list[str] = []

    for page in pages:
        usable_w = page.width_mm - 2 * MARGIN_MM
        usable_h = page.height_mm - 2 * MARGIN_MM
        usable_box = box(MARGIN_MM, MARGIN_MM, MARGIN_MM + usable_w, MARGIN_MM + usable_h)
        polys: list[Polygon] = []

        for placed in page.placed_pieces:
            piece = placed.piece
            poly = piece_to_shapely(piece, include_tabs=True, gap_buffer=0.0)
            if poly.is_empty:
                continue

            if not _fits_usable(poly, usable_box):
                overflow_count += 1
                label = piece.label or piece.id
                if label not in oversize_labels:
                    oversize_labels.append(label)

            polys.append(poly)

        if len(polys) < 2:
            continue

        tree = STRtree(polys)
        page_overlap = False
        for index, poly in enumerate(polys):
            for other_idx in tree.query(poly):
                j = int(other_idx)
                if j <= index:
                    continue
                other = polys[j]
                if not poly.intersects(other):
                    continue
                if poly.touches(other):
                    continue
                if poly.intersection(other).area > COLLISION_EPS_MM2:
                    page_overlap = True
                    break
            if page_overlap:
                break

        if page_overlap:
            overlap_count += 1

    return LayoutIssueReport(
        has_overlaps=overlap_count > 0,
        overlap_count=overlap_count,
        oversize_piece_labels=oversize_labels,
        overflow_count=overflow_count,
    )


def layout_pieces(
    pieces: list[UnfoldPiece],
    paper_size: PaperSize,
    *,
    gap_mm: float = DEFAULT_GAP_MM,
) -> list[LayoutPage]:
    """
    Pack pieces using bottom-left nesting with Shapely collision detection.

    Tries 0°/90°/180°/270° rotations and prefers adding pages.
    Individual pieces are never scaled — papercraft parts must stay at uniform scale.
    """
    page_width, page_height = PAPER_SIZES_MM[paper_size]
    usable_w = page_width - 2 * MARGIN_MM
    usable_h = page_height - 2 * MARGIN_MM
    usable_box = box(MARGIN_MM, MARGIN_MM, MARGIN_MM + usable_w, MARGIN_MM + usable_h)

    sorted_pieces = sorted(
        pieces,
        key=lambda p: piece_polygon_area(p) or _bbox_area(p),
        reverse=True,
    )

    pages: list[LayoutPage] = [
        LayoutPage(index=0, width_mm=page_width, height_mm=page_height, placed_pieces=[]),
    ]

    for piece in sorted_pieces:
        _place_piece_nesting(
            piece,
            pages,
            usable_box,
            usable_w,
            usable_h,
            page_width,
            page_height,
            gap_mm=gap_mm,
        )

    pages = [page for page in pages if page.placed_pieces]

    for index, page in enumerate(pages):
        page.index = index

    return pages


def _place_piece_nesting(
    piece: UnfoldPiece,
    pages: list[LayoutPage],
    usable_box: Polygon,
    usable_w: float,
    usable_h: float,
    page_width: float,
    page_height: float,
    *,
    gap_mm: float,
) -> None:
    for page in pages:
        placement = _find_placement_on_page(
            piece, page, usable_box, usable_w, usable_h, gap_mm=gap_mm
        )
        if placement is not None:
            normalized, _rotation, x, y = placement
            placed_piece = translate_piece(normalized, x, y)
            page.placed_pieces.append(
                PlacedPiece(piece=placed_piece, offset_x=x, offset_y=y, page_index=page.index),
            )
            return

    new_page = LayoutPage(
        index=len(pages),
        width_mm=page_width,
        height_mm=page_height,
        placed_pieces=[],
    )
    pages.append(new_page)
    placement = _find_placement_on_page(
        piece, new_page, usable_box, usable_w, usable_h, gap_mm=gap_mm
    )
    if placement is not None:
        normalized, _rotation, x, y = placement
        placed_piece = translate_piece(normalized, x, y)
        new_page.placed_pieces.append(
            PlacedPiece(piece=placed_piece, offset_x=x, offset_y=y, page_index=new_page.index),
        )
        return

    # Printable area too small at uniform scale — skip; layout_with_repair will fail safely.


def _find_placement_on_page(
    piece: UnfoldPiece,
    page: LayoutPage,
    usable_box: Polygon,
    usable_w: float,
    usable_h: float,
    *,
    gap_mm: float,
) -> tuple[UnfoldPiece, int, float, float] | None:
    placed_polys: list[Polygon] = []
    for placed in page.placed_pieces:
        poly = piece_to_shapely(placed.piece, include_tabs=True, gap_buffer=gap_mm * 0.35)
        if not poly.is_empty:
            placed_polys.append(poly)

    tree = STRtree(placed_polys) if placed_polys else None
    candidates = _candidate_positions(placed_polys, usable_w, usable_h, gap_mm=gap_mm)

    best: tuple[float, UnfoldPiece, int, float, float] | None = None

    for rotation in range(4):
        normalized = _normalize_to_origin(rotate_piece(piece, rotation))
        min_x, min_y, max_x, max_y = piece_bounds(normalized, include_tabs=True)
        width = max_x - min_x
        height = max_y - min_y
        if width > usable_w or height > usable_h:
            continue

        trial_poly_norm = piece_to_shapely(normalized, include_tabs=True, gap_buffer=0.0)
        nfp_candidates = nfp_placement_candidates(placed_polys, trial_poly_norm)
        rotation_candidates = _candidates_for_piece(candidates, nfp_candidates)

        for cx, cy in rotation_candidates:
            x = cx - min_x
            y = cy - min_y
            trial = translate_piece(normalized, x, y)
            trial_poly = piece_to_shapely(trial, include_tabs=True, gap_buffer=0.0)
            if trial_poly.is_empty:
                continue
            if not _fits_usable(trial_poly, usable_box):
                continue
            if tree is not None and _collides(trial_poly, placed_polys, tree):
                continue

            score = y * 10000 + x
            if best is None or score < best[0]:
                best = (score, normalized, rotation, x, y)

    if best is None:
        return None
    _, normalized, rotation, x, y = best
    return normalized, rotation, x, y


def _fits_usable(trial: Polygon, usable_box: Polygon) -> bool:
    if not usable_box.intersects(trial):
        return False
    overflow = trial.difference(usable_box).area
    return overflow <= COLLISION_EPS_MM2


def _collides(trial: Polygon, placed: list[Polygon], tree: STRtree) -> bool:
    for idx in tree.query(trial):
        other = placed[int(idx)]
        if not trial.intersects(other):
            continue
        if trial.touches(other):
            continue
        if trial.intersection(other).area > COLLISION_EPS_MM2:
            return True
    return False


def _candidate_positions(
    placed: list[Polygon],
    usable_w: float,
    usable_h: float,
    *,
    gap_mm: float,
) -> list[tuple[float, float]]:
    """Bottom-left candidate anchors from page origin and placed piece corners."""
    xs = {MARGIN_MM}
    ys = {MARGIN_MM}

    for poly in placed:
        minx, miny, maxx, maxy = poly.bounds
        xs.update((minx, maxx + gap_mm))
        ys.update((miny, maxy + gap_mm))

    xs = sorted(x for x in xs if MARGIN_MM <= x <= MARGIN_MM + usable_w)
    ys = sorted(y for y in ys if MARGIN_MM <= y <= MARGIN_MM + usable_h)

    if not xs:
        xs = [MARGIN_MM]
    if not ys:
        ys = [MARGIN_MM]

    candidates: list[tuple[float, float]] = []
    for y in ys:
        for x in xs:
            candidates.append((x, y))

    candidates.sort(key=lambda pos: (pos[1], pos[0]))
    return candidates


def _candidates_for_piece(
    base_candidates: list[tuple[float, float]],
    nfp_candidates: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Merge bottom-left and NFP reference-corner candidates."""
    merged: set[tuple[float, float]] = set(base_candidates)
    for x, y in nfp_candidates:
        merged.add((round(x, 2), round(y, 2)))
    merged.add((MARGIN_MM, MARGIN_MM))
    return sorted(merged, key=lambda pos: (pos[1], pos[0]))


def _bbox_area(piece: UnfoldPiece) -> float:
    min_x, min_y, max_x, max_y = piece_bounds(piece, include_tabs=True)
    return max(0.0, (max_x - min_x) * (max_y - min_y))


def _normalize_to_origin(piece: UnfoldPiece) -> UnfoldPiece:
    min_x, min_y, _, _ = piece_bounds(piece, include_tabs=True)
    return translate_piece(piece, -min_x, -min_y)
