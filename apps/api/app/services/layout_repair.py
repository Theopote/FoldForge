"""Layout packing with retry when pieces overlap on the page."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.geometry import LayoutPage, UnfoldPiece
from app.schemas.model import PaperSize
from app.services.layout_engine import detect_layout_issues, layout_pieces

MAX_LAYOUT_REPAIR_ITERATIONS = 4
GAP_MM_SEQUENCE = (8.0, 10.0, 12.0, 14.0)


@dataclass
class LayoutRepairResult:
    pages: list[LayoutPage]
    messages: list[str] = field(default_factory=list)
    has_overlaps: bool = False
    scaled_piece_labels: list[str] = field(default_factory=list)


def layout_with_repair(
    pieces: list[UnfoldPiece],
    paper_size: PaperSize,
) -> LayoutRepairResult:
    """
    Pack pieces onto pages, retrying with wider gaps when overlaps are detected.

    Tries progressively larger piece spacing before accepting a flawed layout.
    """
    messages: list[str] = []
    last_pages: list[LayoutPage] = []
    last_issues = detect_layout_issues([])

    for attempt, gap_mm in enumerate(GAP_MM_SEQUENCE[:MAX_LAYOUT_REPAIR_ITERATIONS]):
        pages = layout_pieces(pieces, paper_size, gap_mm=gap_mm)
        issues = detect_layout_issues(pages)
        last_pages = pages
        last_issues = issues

        if not issues.has_overlaps and not issues.scaled_piece_labels:
            if attempt > 0:
                messages.append(
                    f"Layout auto-repair resolved page overlaps (gap {gap_mm:.0f} mm)."
                )
            return LayoutRepairResult(
                pages=pages,
                messages=messages,
                has_overlaps=False,
                scaled_piece_labels=[],
            )

    overlap_msg = (
        "Pieces overlap on the printed page — cut lines may be unusable."
        if last_issues.has_overlaps
        else ""
    )
    scaled_msg = (
        f"Piece(s) {', '.join(last_issues.scaled_piece_labels)} were scaled down to fit."
        if last_issues.scaled_piece_labels
        else ""
    )
    detail = " ".join(part for part in (overlap_msg, scaled_msg) if part)
    if detail:
        messages.append(detail)

    return LayoutRepairResult(
        pages=last_pages,
        messages=messages,
        has_overlaps=last_issues.has_overlaps,
        scaled_piece_labels=last_issues.scaled_piece_labels,
    )


def collect_layout_warnings(result: LayoutRepairResult) -> list[str]:
    """Turn layout repair metadata into user-facing warnings."""
    return list(result.messages)
