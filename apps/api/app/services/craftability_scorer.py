"""Simple craftability scoring for papercraft suitability."""

import trimesh

from app.models.geometry import LayoutPage, UnfoldPiece
from app.schemas.model import Difficulty
from app.services.unfolder import piece_bounds


def compute_craftability(
    mesh: trimesh.Trimesh,
    pieces: list[UnfoldPiece],
    pages: list[LayoutPage],
    difficulty: Difficulty,
    extra_warnings: list[str],
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

    if page_count > 6:
        score -= 15
        warnings.append("Template spans many pages — printing cost may be high.")
    elif page_count > 3:
        score -= 5

    small_pieces = 0
    for piece in pieces:
        min_x, min_y, max_x, max_y = piece_bounds(piece, include_tabs=True)
        min_dim = min(max_x - min_x, max_y - min_y)
        if min_dim < 12:
            small_pieces += 1

    if small_pieces > 0:
        penalty = min(20, small_pieces * 4)
        score -= penalty
        warnings.append("Some parts may be too small to cut by hand.")

    extents = mesh.bounding_box.extents
    thin_ratio = float(min(extents) / max(extents)) if max(extents) > 0 else 1.0
    if thin_ratio < 0.15:
        score -= 10
        warnings.append("The model has many thin structures. Consider Easy mode.")

    tab_count = sum(len(p.tabs) for p in pieces)
    if tab_count > piece_count * 6:
        score -= 8
        warnings.append("Glue tabs are densely packed — folding may be tricky.")

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
