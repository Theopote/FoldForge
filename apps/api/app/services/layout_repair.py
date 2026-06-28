"""Layout packing with retry when pieces overlap on the page."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.geometry import LayoutPage, UnfoldPiece
from app.schemas.model import PaperSize
from app.services.cancel import CancelCheck, check_cancelled
from app.services.layout_engine import (
    detect_layout_issues,
    find_pieces_too_large_for_paper,
    layout_pieces,
)
from app.services.pipeline_errors import LayoutFitError, PieceTooLarge

MAX_LAYOUT_REPAIR_ITERATIONS = 4
GAP_MM_SEQUENCE = (8.0, 10.0, 12.0, 14.0)


@dataclass
class LayoutRepairResult:
    pages: list[LayoutPage]
    messages: list[str] = field(default_factory=list)
    has_overlaps: bool = False
    oversize_piece_labels: list[str] = field(default_factory=list)
    oversize_pieces: list[PieceTooLarge] = field(default_factory=list)
    export_blocked: bool = False
    suggestions: list[str] = field(default_factory=list)

    @property
    def scaled_piece_labels(self) -> list[str]:
        """Legacy alias — pieces are never individually scaled."""
        return self.oversize_piece_labels


def layout_with_repair(
    pieces: list[UnfoldPiece],
    paper_size: PaperSize,
    *,
    target_height_mm: float | None = None,
    cancel_check: CancelCheck | None = None,
) -> LayoutRepairResult:
    """
    Pack pieces onto pages, retrying with wider gaps when overlaps are detected.

    Never scales individual pieces. Oversize or overlapping layouts block export.
    """
    oversize_pieces = find_pieces_too_large_for_paper(
        pieces,
        paper_size,
        target_height_mm=target_height_mm,
    )
    if oversize_pieces:
        error = LayoutFitError.from_oversize_pieces(oversize_pieces)
        return LayoutRepairResult(
            pages=[],
            messages=error.warnings,
            has_overlaps=False,
            oversize_piece_labels=[piece.label for piece in oversize_pieces],
            oversize_pieces=oversize_pieces,
            export_blocked=True,
            suggestions=error.suggestions,
        )

    messages: list[str] = []
    last_pages: list[LayoutPage] = []
    last_issues = detect_layout_issues([])

    for attempt, gap_mm in enumerate(GAP_MM_SEQUENCE[:MAX_LAYOUT_REPAIR_ITERATIONS]):
        check_cancelled(cancel_check)
        layout = layout_pieces(pieces, paper_size, gap_mm=gap_mm, cancel_check=cancel_check)
        if layout.unplaced_pieces:
            labels = [piece.label or piece.id for piece in layout.unplaced_pieces]
            label_text = ", ".join(labels)
            return LayoutRepairResult(
                pages=layout.pages,
                messages=[
                    f"Could not place piece(s) {label_text} on the page — "
                    "layout export blocked."
                ],
                export_blocked=True,
                suggestions=[
                    "Use a larger paper size (e.g. A3 instead of A4).",
                    "Reduce target height so all pieces shrink uniformly.",
                    "Switch to Easy mode to split the model into smaller patches.",
                ],
            )

        pages = layout.pages
        issues = detect_layout_issues(pages)
        last_pages = pages
        last_issues = issues

        if not issues.has_overlaps and not issues.oversize_piece_labels:
            if attempt > 0:
                messages.append(
                    f"Layout auto-repair resolved page overlaps (gap {gap_mm:.0f} mm)."
                )
            return LayoutRepairResult(
                pages=pages,
                messages=messages,
                has_overlaps=False,
                oversize_piece_labels=[],
            )

    overlap_msg = (
        "Pieces overlap on the printed page — cut lines may be unusable."
        if last_issues.has_overlaps
        else ""
    )
    oversize_msg = (
        f"Piece(s) {', '.join(last_issues.oversize_piece_labels)} exceed the printable area — "
        "reduce target height, use larger paper (e.g. A3), or try Easy mode."
        if last_issues.oversize_piece_labels
        else ""
    )
    detail = " ".join(part for part in (overlap_msg, oversize_msg) if part)
    if detail:
        messages.append(detail)

    suggestions = [
        "Use a larger paper size (e.g. A3 instead of A4).",
        "Reduce target height so all pieces shrink uniformly.",
        "Switch to Easy mode to split the model into smaller patches.",
    ]

    return LayoutRepairResult(
        pages=last_pages,
        messages=messages,
        has_overlaps=last_issues.has_overlaps,
        oversize_piece_labels=last_issues.oversize_piece_labels,
        export_blocked=True,
        suggestions=suggestions,
    )


def collect_layout_warnings(result: LayoutRepairResult) -> list[str]:
    """Turn layout repair metadata into user-facing warnings."""
    return list(result.messages)


def ensure_layout_exportable(result: LayoutRepairResult) -> None:
    """Raise LayoutFitError when the layout is not safe to export."""
    if result.oversize_pieces:
        raise LayoutFitError.from_oversize_pieces(result.oversize_pieces)

    if result.export_blocked or result.has_overlaps:
        warnings = list(result.messages)
        if result.has_overlaps:
            raise LayoutFitError(
                warnings[0]
                if warnings
                else "Pieces overlap on the printed page — export blocked.",
                suggestions=result.suggestions,
                warnings=warnings,
            )
        raise LayoutFitError(
            warnings[0]
            if warnings
            else "Layout could not produce a safe printable template.",
            suggestions=result.suggestions,
            warnings=warnings,
        )
