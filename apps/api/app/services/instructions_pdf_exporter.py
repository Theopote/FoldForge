"""Export assembly instructions as a printable PDF."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

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
from app.services.instruction_pdf_layout import instruction_page_size
from app.services.pdf_fonts import instruction_font_for, wrap_instruction_line


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
    page_size = instruction_page_size(settings)
    pdf = canvas.Canvas(
        str(output) if isinstance(output, Path) else output,
        pagesize=page_size,
    )
    page_width, page_height = page_size
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

    def draw_wrapped_lines(
        text: str,
        *,
        font_size: int,
        weight: str = "regular",
        indent: float = 0,
        line_spacing: float = 1.0,
    ) -> None:
        nonlocal y
        font_name = instruction_font_for(text, weight=weight)
        pdf.setFont(font_name, font_size)
        for line in wrap_instruction_line(text, font_name, font_size, max_width - indent):
            ensure_space()
            pdf.drawString(margin_x + indent, y, line)
            y -= line_height * line_spacing

    title_font = instruction_font_for(document.title, weight="bold")
    pdf.setFont(title_font, 14)
    for line in wrap_instruction_line(document.title, title_font, 14, max_width):
        ensure_space()
        pdf.drawString(margin_x, y, line)
        y -= line_height * 1.4

    generated_line = f"Generated: {document.generated}"
    draw_wrapped_lines(generated_line, font_size=9)
    y -= line_height

    for title, body in document.sections:
        ensure_space(3)
        title_font = instruction_font_for(title, weight="bold")
        pdf.setFont(title_font, 11)
        pdf.drawString(margin_x, y, title)
        y -= line_height * 1.3

        for entry in body:
            draw_wrapped_lines(
                f"• {entry}",
                font_size=9,
                indent=4 * mm,
            )
        y -= line_height * 0.6

    ensure_space(3)
    footer = "FoldForge / 纸模工坊 — Turn imagination into printable paper models."
    footer_font = instruction_font_for(footer, weight="italic")
    pdf.setFont(footer_font, 8)
    pdf.drawString(margin_x, y, footer)

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
    page_width, page_height = _canvas_page_size(pdf)
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


def _canvas_page_size(pdf: canvas.Canvas) -> tuple[float, float]:
    return pdf._pagesize  # type: ignore[attr-defined]
