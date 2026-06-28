"""Shared print annotations: scale check and line-type legend."""

from __future__ import annotations

import svgwrite
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.schemas.model import ProjectSettings

SCALE_CHECK_MM = 50.0
LEGEND_TITLE = "Legend"


def draw_pdf_page_annotations(
    pdf: canvas.Canvas,
    *,
    page_width_mm: float,
    page_height_mm: float,
    settings: ProjectSettings,
    show_legend: bool,
) -> None:
    """Draw 50 mm scale check and optional legend on a PDF page."""
    _draw_pdf_scale_check(pdf, page_height_mm)
    if show_legend:
        _draw_pdf_legend(pdf, page_width_mm, page_height_mm, settings)


def _draw_pdf_scale_check(pdf: canvas.Canvas, page_height_mm: float) -> None:
    x0 = 12 * mm
    y0 = 8 * mm
    length = SCALE_CHECK_MM * mm

    pdf.setStrokeColorRGB(0.2, 0.24, 0.3)
    pdf.setLineWidth(0.6)
    pdf.setDash()
    pdf.line(x0, y0, x0 + length, y0)
    pdf.line(x0, y0 - 1.5 * mm, x0, y0 + 1.5 * mm)
    pdf.line(x0 + length, y0 - 1.5 * mm, x0 + length, y0 + 1.5 * mm)

    pdf.setFillColorRGB(0.28, 0.33, 0.41)
    pdf.setFont("Helvetica", 7)
    pdf.drawString(x0, y0 + 2.5 * mm, f"Scale check: {SCALE_CHECK_MM:.0f} mm (print at 100%)")


def _draw_pdf_legend(
    pdf: canvas.Canvas,
    page_width_mm: float,
    page_height_mm: float,
    settings: ProjectSettings,
) -> None:
    box_w = 58 * mm
    box_h = 24 * mm
    x0 = page_width_mm * mm - box_w - 10 * mm
    y0 = 8 * mm

    pdf.setStrokeColorRGB(0.75, 0.78, 0.82)
    pdf.setLineWidth(0.4)
    pdf.setDash()
    pdf.rect(x0, y0, box_w, box_h, stroke=1, fill=0)

    pdf.setFillColorRGB(0.28, 0.33, 0.41)
    pdf.setFont("Helvetica-Bold", 7)
    pdf.drawString(x0 + 3 * mm, y0 + box_h - 5 * mm, LEGEND_TITLE)

    line_y = y0 + box_h - 10 * mm
    row_gap = 4.5 * mm
    row = 0

    if settings.add_cut_lines:
        pdf.setStrokeColorRGB(0.07, 0.09, 0.15)
        pdf.setLineWidth(0.5)
        pdf.setDash()
        pdf.line(x0 + 3 * mm, line_y - row * row_gap, x0 + 14 * mm, line_y - row * row_gap)
        pdf.setFont("Helvetica", 6)
        pdf.drawString(x0 + 16 * mm, line_y - row * row_gap - 1.5 * mm, "Cut line")
        row += 1

    if settings.add_fold_lines:
        pdf.setStrokeColorRGB(0.86, 0.15, 0.15)
        pdf.setDash(4, 2)
        pdf.setLineWidth(0.35)
        pdf.line(x0 + 3 * mm, line_y - row * row_gap, x0 + 14 * mm, line_y - row * row_gap)
        pdf.setFont("Helvetica", 6)
        pdf.drawString(x0 + 16 * mm, line_y - row * row_gap - 1.5 * mm, "Mountain fold")
        row += 1

        pdf.setStrokeColorRGB(0.15, 0.39, 0.92)
        pdf.setDash(2, 2)
        pdf.line(x0 + 3 * mm, line_y - row * row_gap, x0 + 14 * mm, line_y - row * row_gap)
        pdf.drawString(x0 + 16 * mm, line_y - row * row_gap - 1.5 * mm, "Valley fold")
        row += 1

    if settings.add_tabs:
        pdf.setDash()
        pdf.setFillColorRGB(0.95, 0.96, 0.98)
        pdf.setStrokeColorRGB(0.39, 0.45, 0.55)
        pdf.rect(x0 + 3 * mm, line_y - row * row_gap - 1 * mm, 11 * mm, 2.5 * mm, stroke=1, fill=1)
        pdf.setFillColorRGB(0.28, 0.33, 0.41)
        pdf.drawString(x0 + 16 * mm, line_y - row * row_gap - 1.5 * mm, "Glue tab")


def draw_svg_page_annotations(
    drawing: svgwrite.Drawing,
    page_group: svgwrite.container.Group,
    *,
    page_width_mm: float,
    page_height_mm: float,
    y_offset: float,
    settings: ProjectSettings,
    show_legend: bool,
) -> None:
    """Draw scale check and optional legend on an SVG page."""
    _draw_svg_scale_check(drawing, page_group, page_height_mm, y_offset)
    if show_legend:
        _draw_svg_legend(
            drawing,
            page_group,
            page_width_mm=page_width_mm,
            page_height_mm=page_height_mm,
            y_offset=y_offset,
            settings=settings,
        )


def _svg_y(page_height_mm: float, y_offset: float, y_mm: float) -> float:
    return y_offset + page_height_mm - y_mm


def _draw_svg_scale_check(
    drawing: svgwrite.Drawing,
    page_group: svgwrite.container.Group,
    page_height_mm: float,
    y_offset: float,
) -> None:
    y_mm = 8.0
    y = _svg_y(page_height_mm, y_offset, y_mm)
    page_group.add(
        drawing.line(
            start=(12, y),
            end=(12 + SCALE_CHECK_MM, y),
            stroke="#334155",
            stroke_width=0.4,
        )
    )
    page_group.add(
        drawing.text(
            f"Scale check: {SCALE_CHECK_MM:.0f} mm (print at 100%)",
            insert=(12, y - 2),
            fill="#475569",
            font_size="2.2mm",
            font_family="sans-serif",
        )
    )


def _draw_svg_legend(
    drawing: svgwrite.Drawing,
    page_group: svgwrite.container.Group,
    *,
    page_width_mm: float,
    page_height_mm: float,
    y_offset: float,
    settings: ProjectSettings,
) -> None:
    box_w = 58.0
    box_h = 22.0
    x0 = page_width_mm - box_w - 10.0
    y_top_mm = 30.0
    y_top = _svg_y(page_height_mm, y_offset, y_top_mm)

    page_group.add(
        drawing.rect(
            insert=(x0, y_top - box_h),
            size=(box_w, box_h),
            fill="white",
            stroke="#cbd5e1",
            stroke_width=0.25,
        )
    )
    page_group.add(
        drawing.text(
            LEGEND_TITLE,
            insert=(x0 + 2, y_top - 4),
            fill="#334155",
            font_size="2.5mm",
            font_family="sans-serif",
            font_weight="bold",
        )
    )

    row = 0
    row_gap = 4.0

    def add_row(label: str, stroke: str, dash: str | None = None) -> None:
        nonlocal row
        y = y_top - 9 - row * row_gap
        page_group.add(
            drawing.line(
                start=(x0 + 2, y),
                end=(x0 + 12, y),
                stroke=stroke,
                stroke_width=0.3,
                **({"stroke_dasharray": dash} if dash else {}),
            )
        )
        page_group.add(
            drawing.text(
                label,
                insert=(x0 + 14, y + 0.8),
                fill="#475569",
                font_size="2mm",
                font_family="sans-serif",
            )
        )
        row += 1

    if settings.add_cut_lines:
        add_row("Cut line", "#111827")
    if settings.add_fold_lines:
        add_row("Mountain fold", "#dc2626", "4,1.5")
        add_row("Valley fold", "#2563eb", "2,1.5")
    if settings.add_tabs:
        page_group.add(
            drawing.rect(
                insert=(x0 + 2, y_top - 9 - row * row_gap - 1),
                size=(10, 2.5),
                fill="#f1f5f9",
                stroke="#64748b",
                stroke_width=0.2,
            )
        )
        page_group.add(
            drawing.text(
                "Glue tab",
                insert=(x0 + 14, y_top - 9 - row * row_gap + 0.5),
                fill="#475569",
                font_size="2mm",
                font_family="sans-serif",
            )
        )
