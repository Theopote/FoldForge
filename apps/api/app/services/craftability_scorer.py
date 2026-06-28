"""Simple craftability scoring for papercraft suitability."""

import trimesh

from app.models.geometry import LayoutPage, UnfoldPiece
from app.schemas.model import Difficulty
from app.services.unfolder import piece_bounds

MIN_PIECE_DIMENSION_MM = 12.0
MIN_TAB_WIDTH_MM = 5.0
MAX_PAGES_WARNING = 6
MAX_PAGES_SOFT = 3


def compute_craftability(
    mesh: trimesh.Trimesh,
    pieces: list[UnfoldPiece],
    pages: list[LayoutPage],
    difficulty: Difficulty,
    extra_warnings: list[str],
    *,
    layout_has_overlaps: bool = False,
    layout_scaled_labels: list[str] | None = None,
) -> tuple[int, str, list[str]]:
    """
    Compute a 0–100 craftability score with level and warnings.

    Higher is better for hand-cutting and assembly.
    """
    warnings = list(extra_warnings)
    score = 100.0

    face_count = len(mesh.faces)
    piece_count = len(pieces)
    page_count = len(pages)

    if face_count > 800:
        score -= 25
        warnings.append("Face count is very high — consider Easy mode.")
    elif face_count > 400:
        score -= 12

    if piece_count > 30:
        score -= 20
        warnings.append("Many separate pieces — assembly will take longer.")
    elif piece_count > 15:
        score -= 8

    if page_count > MAX_PAGES_WARNING:
        score -= 15
        warnings.append(
            f"Template spans {page_count} pages — printing and assembly will take longer."
        )
    elif page_count > MAX_PAGES_SOFT:
        score -= 5
        warnings.append(f"Template uses {page_count} pages — check paper supply before printing.")

    small_pieces = 0
    for piece in pieces:
        min_x, min_y, max_x, max_y = piece_bounds(piece, include_tabs=True)
        min_dim = min(max_x - min_x, max_y - min_y)
        if min_dim < MIN_PIECE_DIMENSION_MM:
            small_pieces += 1

    if small_pieces > 0:
        penalty = min(20, small_pieces * 4)
        score -= penalty
        warnings.append(
            f"{small_pieces} part(s) are smaller than {MIN_PIECE_DIMENSION_MM:.0f} mm — "
            "may be difficult to cut by hand."
        )

    small_tabs = 0
    for piece in pieces:
        for tab in piece.tabs:
            if len(tab.polygon) < 3:
                continue
            xs = [point.x for point in tab.polygon]
            ys = [point.y for point in tab.polygon]
            if min(max(xs) - min(xs), max(ys) - min(ys)) < MIN_TAB_WIDTH_MM:
                small_tabs += 1

    if small_tabs > 0:
        score -= min(15, small_tabs * 3)
        warnings.append(
            f"{small_tabs} glue tab(s) are narrower than {MIN_TAB_WIDTH_MM:.0f} mm — "
            "tabs may tear when folded."
        )

    extents = mesh.bounding_box.extents
    thin_ratio = float(min(extents) / max(extents)) if max(extents) > 0 else 1.0
    if thin_ratio < 0.15:
        score -= 10
        warnings.append("The model has many thin structures. Consider Easy mode.")

    tab_count = sum(len(p.tabs) for p in pieces)
    if tab_count > piece_count * 6:
        score -= 8
        warnings.append("Glue tabs are densely packed — folding may be tricky.")

    overlap_count = sum(1 for piece in pieces if piece.has_overlap)
    if overlap_count > 0:
        score -= min(45, overlap_count * 20)
        warnings.append(
            f"{overlap_count} piece(s) have unfold overlaps — "
            "the printed template may not fold correctly."
        )

    if layout_has_overlaps:
        score -= 25
        warnings.append(
            "Pieces overlap on the printed page — cut lines may be unusable."
        )

    scaled_labels = layout_scaled_labels or []
    if scaled_labels:
        score -= min(20, len(scaled_labels) * 8)

    if difficulty == Difficulty.ADVANCED and piece_count > 20:
        warnings.append("Advanced mode with many pieces — not ideal for beginners.")

    score = int(max(0, min(100, round(score))))

    if score >= 85:
        level = "excellent"
    elif score >= 70:
        level = "good"
    elif score >= 50:
        level = "fair"
    else:
        level = "poor"

    return score, level, warnings
