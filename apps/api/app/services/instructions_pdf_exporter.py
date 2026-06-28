"""Export assembly instructions as a printable PDF."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.models.geometry import LayoutPage, UnfoldPiece
from app.schemas.model import ProjectSettings
from app.services.assembly_step_illustrator import draw_assembly_step_pages
from app.services.instruction_generator import (
    InstructionDocument,
    build_instruction_document,
    _piece_page_map,
)
from app.services.instruction_graphics import map_points_to_box, piece_outline_points


def export_instructions_pdf(
    output_path: Path | BytesIO,
    project_name: str,
    settings: ProjectSettings,
    stats: dict[str, int | str],
    warnings: list[str],
    *,
    pieces: list[UnfoldPiece] | None = None,
    pages: list[LayoutPage] | None = None,
) -> Path | BytesIO:
    """Write a multi-page instruction booklet matching instructions.txt content."""
    document = build_instruction_document(
        project_name,
        settings,
        stats,
        warnings,
        pieces=pieces,
        pages=pages,
    )
    render_instruction_pdf(
        output_path,
        document,
        settings=settings,
        pieces=pieces,
        pages=pages,
    )
    return output_path


def render_instruction_pdf(
    output: Path | BytesIO,
    document: InstructionDocument,
    *,
    settings: ProjectSettings | None = None,
    pieces: list[UnfoldPiece] | None = None,
    pages: list[LayoutPage] | None = None,
) -> None:
    pdf = canvas.Canvas(str(output) if isinstance(output, Path) else output, pagesize=A4)
    page_width, page_height = A4
    margin_x = 18 * mm
    margin_top = 20 * mm
    margin_bottom = 18 * mm
    line_height = 4.2 * mm
    max_width = page_width - (2 * margin_x)

    y = page_height - margin_top

    def new_page() -> None:
        nonlocal y
        pdf.showPage()
        y = page_height - margin_top

    def ensure_space(lines_needed: int = 2) -> None:
        nonlocal y
        if y - (lines_needed * line_height) < margin_bottom:
            new_page()

    pdf.setFont("Helvetica-Bold", 14)
    for line in _wrap_line(document.title, "Helvetica-Bold", 14, max_width):
        ensure_space()
        pdf.drawString(margin_x, y, line)
        y -= line_height * 1.4

    pdf.setFont("Helvetica", 9)
    ensure_space()
    pdf.drawString(margin_x, y, f"Generated: {document.generated}")
    y -= line_height * 2

    for title, body in document.sections:
        ensure_space(3)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(margin_x, y, title)
        y -= line_height * 1.3

        pdf.setFont("Helvetica", 9)
        for entry in body:
            wrapped = _wrap_line(f"• {entry}", "Helvetica", 9, max_width - 4 * mm)
            for index, line in enumerate(wrapped):
                ensure_space()
                pdf.drawString(margin_x + (4 * mm if index > 0 else 0), y, line)
                y -= line_height
        y -= line_height * 0.6

    ensure_space(3)
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawString(
        margin_x,
        y,
        "FoldForge / 纸模工坊 — Turn imagination into printable paper models.",
    )

    if pieces:
        _draw_piece_reference_pages(
            pdf,
            pieces,
            _piece_page_map(pages or []),
        )
        if settings is not None:
            draw_assembly_step_pages(pdf, pieces, settings)

    pdf.save()


def _draw_piece_reference_pages(
    pdf: canvas.Canvas,
    pieces: list[UnfoldPiece],
    page_by_piece: dict[str, int],
) -> None:
    sorted_pieces = sorted(pieces, key=lambda piece: piece.label)
    cols = 3
    rows = 2
    per_page = cols * rows
    cell = 52 * mm
    gap_x = 10 * mm
    gap_y = 22 * mm
    margin_x = 18 * mm
    page_width, page_height = A4
    grid_top = page_height - 28 * mm

    for batch_start in range(0, len(sorted_pieces), per_page):
        pdf.showPage()
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(margin_x, page_height - 18 * mm, "Piece reference")

        batch = sorted_pieces[batch_start : batch_start + per_page]
        for index, piece in enumerate(batch):
            col = index % cols
            row = index // cols
            x = margin_x + col * (cell + gap_x)
            y = grid_top - row * (cell + gap_y) - cell
            _draw_piece_thumbnail(pdf, x, y, cell, piece)

            page_num = page_by_piece.get(piece.id)
            subtitle = f"Piece {piece.label}"
            if page_num is not None:
                subtitle += f" · page {page_num}"
            pdf.setFont("Helvetica", 8)
            pdf.drawCentredString(x + cell / 2, y - 5 * mm, subtitle)


def _draw_piece_thumbnail(
    pdf: canvas.Canvas,
    x: float,
    y: float,
    size: float,
    piece: UnfoldPiece,
) -> None:
    points = map_points_to_box(piece_outline_points(piece), x, y, size)
    if len(points) < 3:
        return

    path = pdf.beginPath()
    for index, (px, py) in enumerate(points):
        if index == 0:
            path.moveTo(px, py)
        else:
            path.lineTo(px, py)
    path.close()

    pdf.setFillColorRGB(0.95, 0.96, 0.98)
    pdf.setStrokeColorRGB(0.2, 0.24, 0.3)
    pdf.setLineWidth(0.35)
    pdf.drawPath(path, stroke=1, fill=1)


def _wrap_line(text: str, font_name: str, font_size: int, max_width: float) -> list[str]:
    from reportlab.pdfbase.pdfmetrics import stringWidth

    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines
