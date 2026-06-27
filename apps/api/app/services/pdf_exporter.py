"""Export layout pages to PDF via ReportLab."""

from pathlib import Path

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.models.geometry import LayoutPage, PlacedPiece
from app.schemas.model import ProjectSettings


def export_pdf(
    pages: list[LayoutPage],
    output_path: Path,
    project_name: str,
    settings: ProjectSettings,
) -> Path:
    """Generate a multi-page PDF matching the SVG layout."""
    if not pages:
        raise ValueError("No pages to export.")

    first = pages[0]
    pdf = canvas.Canvas(
        str(output_path),
        pagesize=(first.width_mm * mm, first.height_mm * mm),
    )

    for page in pages:
        pdf.setPageSize((page.width_mm * mm, page.height_mm * mm))
        _draw_page_pdf(pdf, page, project_name, settings)
        pdf.showPage()

    pdf.save()
    return output_path


def _draw_page_pdf(
    pdf: canvas.Canvas,
    page: LayoutPage,
    project_name: str,
    settings: ProjectSettings,
) -> None:
    width = page.width_mm * mm
    height = page.height_mm * mm

    pdf.setStrokeColorRGB(0.58, 0.64, 0.72)
    pdf.setLineWidth(0.5)
    pdf.rect(0, 0, width, height, stroke=1, fill=0)

    pdf.setFillColorRGB(0.39, 0.45, 0.55)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(5 * mm, height - 8 * mm, f"{project_name} — Page {page.index + 1}")

    for placed in page.placed_pieces:
        _draw_piece_pdf(pdf, placed, page.height_mm, settings)


def _pdf_y(page_height_mm: float, y_mm: float) -> float:
    return page_height_mm * mm - y_mm * mm


def _draw_piece_pdf(
    pdf: canvas.Canvas,
    placed: PlacedPiece,
    page_height_mm: float,
    settings: ProjectSettings,
) -> None:
    piece = placed.piece

    if settings.add_cut_lines:
        pdf.setStrokeColorRGB(0.07, 0.09, 0.15)
        pdf.setLineWidth(0.4)
        pdf.setDash()
        if piece.cut_outline and len(piece.cut_outline) >= 3:
            path = pdf.beginPath()
            path.moveTo(
                piece.cut_outline[0].x * mm,
                _pdf_y(page_height_mm, piece.cut_outline[0].y),
            )
            for point in piece.cut_outline[1:]:
                path.lineTo(point.x * mm, _pdf_y(page_height_mm, point.y))
            path.close()
            pdf.drawPath(path, stroke=1, fill=0)
        else:
            for cut in piece.cut_lines:
                pdf.line(
                    cut.start.x * mm,
                    _pdf_y(page_height_mm, cut.start.y),
                    cut.end.x * mm,
                    _pdf_y(page_height_mm, cut.end.y),
                )

    if settings.add_fold_lines:
        for fold in piece.fold_lines:
            if fold.fold_type == "valley":
                pdf.setStrokeColorRGB(0.15, 0.39, 0.92)
                pdf.setDash(2, 2)
            else:
                pdf.setStrokeColorRGB(0.86, 0.15, 0.15)
                pdf.setDash(4, 2)
            pdf.setLineWidth(0.3)
            pdf.line(
                fold.start.x * mm,
                _pdf_y(page_height_mm, fold.start.y),
                fold.end.x * mm,
                _pdf_y(page_height_mm, fold.end.y),
            )

    if settings.add_tabs and not piece.cut_outline:
        pdf.setDash()
        for tab in piece.tabs:
            if len(tab.polygon) < 3:
                continue
            path = pdf.beginPath()
            path.moveTo(tab.polygon[0].x * mm, _pdf_y(page_height_mm, tab.polygon[0].y))
            for point in tab.polygon[1:]:
                path.lineTo(point.x * mm, _pdf_y(page_height_mm, point.y))
            path.close()
            pdf.setFillColorRGB(0.95, 0.96, 0.98)
            pdf.setStrokeColorRGB(0.39, 0.45, 0.55)
            pdf.drawPath(path, stroke=1, fill=1)

            if settings.add_numbers and tab.label:
                cx = sum(p.x for p in tab.polygon) / len(tab.polygon)
                cy = sum(p.y for p in tab.polygon) / len(tab.polygon)
                pdf.setFillColorRGB(0.28, 0.33, 0.41)
                pdf.setFont("Helvetica", 6)
                pdf.drawCentredString(cx * mm, _pdf_y(page_height_mm, cy), tab.label)

    if settings.add_tabs and piece.cut_outline:
        pdf.setDash()
        for tab in piece.tabs:
            if not settings.add_numbers or not tab.label:
                continue
            if tab.polygon:
                cx = sum(p.x for p in tab.polygon) / len(tab.polygon)
                cy = sum(p.y for p in tab.polygon) / len(tab.polygon)
            else:
                cx = sum(p.x for p in piece.cut_outline) / len(piece.cut_outline)
                cy = sum(p.y for p in piece.cut_outline) / len(piece.cut_outline)
            pdf.setFillColorRGB(0.28, 0.33, 0.41)
            pdf.setFont("Helvetica", 6)
            pdf.drawCentredString(cx * mm, _pdf_y(page_height_mm, cy), tab.label)

    if settings.add_numbers and piece.label:
        cx = sum(p.x for p in piece.polygon) / max(len(piece.polygon), 1)
        cy = sum(p.y for p in piece.polygon) / max(len(piece.polygon), 1)
        pdf.setFillColorRGB(0.91, 0.36, 0.29)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(cx * mm, _pdf_y(page_height_mm, cy), piece.label)
