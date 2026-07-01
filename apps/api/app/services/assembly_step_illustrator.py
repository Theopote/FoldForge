"""Render step-by-step assembly illustrations to PDF and SVG."""

from __future__ import annotations

from pathlib import Path

import svgwrite
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.models.geometry import Point2D, UnfoldPiece
from app.schemas.model import ProjectSettings
from app.services.assembly_step_planner import AssemblyStep, plan_assembly_steps
from app.services.instruction_graphics import (
    find_cut_line,
    find_shared_cut_line,
    map_points_to_box,
    piece_outline_points,
)


def draw_assembly_step_pages(
    pdf: canvas.Canvas,
    pieces: list[UnfoldPiece],
    settings: ProjectSettings,
) -> None:
    """Append illustrated assembly steps to an open instruction PDF canvas."""
    piece_by_id = {piece.id: piece for piece in pieces}
    steps = plan_assembly_steps(pieces, settings)
    if not steps:
        return

    page_width, page_height = pdf._pagesize  # type: ignore[attr-defined]
    margin_x = 18 * mm

    for step in steps:
        pdf.showPage()
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(margin_x, page_height - 18 * mm, f"Step {step.number} — {step.title}")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(margin_x, page_height - 26 * mm, step.detail)

        if step.kind == "overview":
            _draw_overview_step(pdf, piece_by_id, step, margin_x, page_height - 38 * mm)
        elif step.kind == "prepare":
            piece = piece_by_id[step.primary_piece_id]
            _draw_prepare_step(pdf, piece, margin_x, page_height - 42 * mm)
        elif step.kind == "join" and step.secondary_piece_id and step.tab and step.tab_owner_piece_id:
            _draw_join_step(
                pdf,
                piece_by_id[step.tab_owner_piece_id],
                piece_by_id[step.primary_piece_id],
                piece_by_id[step.secondary_piece_id],
                step.tab,
                margin_x,
                page_height - 42 * mm,
            )


def export_assembly_steps_svg(
    output_path: Path,
    pieces: list[UnfoldPiece],
    settings: ProjectSettings,
    project_name: str,
) -> Path:
    """Write a scrollable SVG with one illustrated step per row."""
    piece_by_id = {piece.id: piece for piece in pieces}
    steps = plan_assembly_steps(pieces, settings)
    step_height = 95.0
    width = 210.0
    height = max(step_height, len(steps) * step_height + 20.0)

    drawing = svgwrite.Drawing(
        str(output_path),
        size=(f"{width}mm", f"{height}mm"),
        viewBox=f"0 0 {width} {height}",
    )
    drawing.add(
        drawing.text(
            f"{project_name} — Assembly Steps",
            insert=(8, 10),
            fill="#334155",
            font_size="4mm",
            font_family="sans-serif",
            font_weight="bold",
        )
    )

    for index, step in enumerate(steps):
        y_offset = 16.0 + index * step_height
        group = drawing.g(id=f"step-{step.number}", class_="assembly-step")
        group.add(
            drawing.text(
                f"Step {step.number}: {step.title}",
                insert=(8, y_offset),
                fill="#0f172a",
                font_size="3.5mm",
                font_family="sans-serif",
                font_weight="bold",
            )
        )
        group.add(
            drawing.text(
                step.detail,
                insert=(8, y_offset + 5),
                fill="#475569",
                font_size="2.8mm",
                font_family="sans-serif",
            )
        )

        if step.kind == "overview":
            _draw_overview_step_svg(drawing, group, piece_by_id, step, 8, y_offset + 10)
        elif step.kind == "prepare":
            _draw_prepare_step_svg(
                drawing,
                group,
                piece_by_id[step.primary_piece_id],
                8,
                y_offset + 12,
            )
        elif step.kind == "join" and step.secondary_piece_id and step.tab and step.tab_owner_piece_id:
            _draw_join_step_svg(
                drawing,
                group,
                piece_by_id[step.tab_owner_piece_id],
                piece_by_id[step.primary_piece_id],
                piece_by_id[step.secondary_piece_id],
                step.tab,
                8,
                y_offset + 12,
            )

        drawing.add(group)

    drawing.save()
    return output_path


def _draw_overview_step(
    pdf: canvas.Canvas,
    piece_by_id: dict[str, UnfoldPiece],
    step: AssemblyStep,
    margin_x: float,
    top_y: float,
) -> None:
    cell = 34 * mm
    gap = 6 * mm
    cols = 4
    pieces = [piece_by_id[piece_id] for piece_id in step.assembled_piece_ids if piece_id in piece_by_id]

    for index, piece in enumerate(pieces[:12]):
        col = index % cols
        row = index // cols
        x = margin_x + col * (cell + gap)
        y = top_y - row * (cell + 10 * mm) - cell
        _draw_piece_shape(pdf, piece, x, y, cell, fill=(0.95, 0.96, 0.98))
        pdf.setFont("Helvetica", 7)
        pdf.drawCentredString(x + cell / 2, y - 4 * mm, f"Piece {piece.label}")


def _draw_prepare_step(pdf: canvas.Canvas, piece: UnfoldPiece, margin_x: float, top_y: float) -> None:
    size = 90 * mm
    x = margin_x + 20 * mm
    y = top_y - size
    _draw_piece_shape(pdf, piece, x, y, size, fill=(0.93, 0.96, 1.0))
    _draw_fold_lines(pdf, piece, x, y, size)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawCentredString(x + size / 2, y - 8 * mm, f"Piece {piece.label}")


def _draw_join_step(
    pdf: canvas.Canvas,
    tab_owner: UnfoldPiece,
    attaching: UnfoldPiece,
    target: UnfoldPiece,
    tab,
    margin_x: float,
    top_y: float,
) -> None:
    cell = 72 * mm
    gap = 24 * mm
    left_x = margin_x
    right_x = margin_x + cell + gap
    y = top_y - cell

    owner_piece = tab_owner
    other = target if attaching.id == tab_owner.id else attaching
    _draw_piece_shape(pdf, other, left_x, y, cell, fill=(0.93, 0.96, 1.0))
    _draw_piece_shape(pdf, attaching, right_x, y, cell, fill=(0.91, 0.97, 0.91))

    if tab_owner.id == attaching.id:
        _draw_tab_highlight(pdf, tab, right_x, y, cell)
        source_cut = find_cut_line(attaching, tab.edge_id)
        if source_cut is not None:
            _draw_edge_highlight(pdf, other, source_cut.start, source_cut.end, left_x, y, cell)
    else:
        _draw_tab_highlight(pdf, tab, left_x, y, cell)
        source_cut = find_cut_line(tab_owner, tab.edge_id)
        if source_cut is not None:
            _draw_edge_highlight(pdf, attaching, source_cut.start, source_cut.end, right_x, y, cell)

    arrow_y = y + cell / 2
    pdf.setStrokeColorRGB(0.91, 0.36, 0.29)
    pdf.setLineWidth(1.2)
    pdf.line(left_x + cell + 3 * mm, arrow_y, right_x - 3 * mm, arrow_y)
    pdf.line(right_x - 6 * mm, arrow_y + 2 * mm, right_x - 3 * mm, arrow_y)
    pdf.line(right_x - 6 * mm, arrow_y - 2 * mm, right_x - 3 * mm, arrow_y)

    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(left_x + cell / 2, y - 6 * mm, f"Piece {other.label}")
    pdf.drawCentredString(right_x + cell / 2, y - 6 * mm, f"Piece {attaching.label}")
    if tab.label:
        pdf.setFillColorRGB(0.91, 0.36, 0.29)
        pdf.drawCentredString(
            margin_x + cell + gap / 2 + cell / 2,
            arrow_y + 5 * mm,
            tab.label,
        )


def _draw_piece_shape(
    pdf: canvas.Canvas,
    piece: UnfoldPiece,
    x: float,
    y: float,
    size: float,
    *,
    fill: tuple[float, float, float],
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
    pdf.setFillColorRGB(*fill)
    pdf.setStrokeColorRGB(0.2, 0.24, 0.3)
    pdf.setLineWidth(0.35)
    pdf.drawPath(path, stroke=1, fill=1)


def _draw_fold_lines(pdf: canvas.Canvas, piece: UnfoldPiece, x: float, y: float, size: float) -> None:
    for fold in piece.fold_lines:
        color = (0.15, 0.39, 0.92) if fold.fold_type == "valley" else (0.86, 0.15, 0.15)
        pdf.setStrokeColorRGB(*color)
        pdf.setDash(2, 2)
        pdf.setLineWidth(0.25)
        start = _map_point(fold.start, piece, x, y, size)
        end = _map_point(fold.end, piece, x, y, size)
        pdf.line(start[0], start[1], end[0], end[1])
    pdf.setDash()


def _draw_tab_highlight(pdf: canvas.Canvas, tab, x: float, y: float, size: float) -> None:
    if len(tab.polygon) < 3:
        return
    points = map_points_to_box(tab.polygon, x, y, size, padding=0.86)
    path = pdf.beginPath()
    for index, (px, py) in enumerate(points):
        if index == 0:
            path.moveTo(px, py)
        else:
            path.lineTo(px, py)
    path.close()
    pdf.setFillColorRGB(0.98, 0.74, 0.38)
    pdf.setStrokeColorRGB(0.86, 0.45, 0.12)
    pdf.setLineWidth(0.4)
    pdf.drawPath(path, stroke=1, fill=1)


def _draw_edge_highlight(
    pdf: canvas.Canvas,
    piece: UnfoldPiece,
    start: Point2D,
    end: Point2D,
    x: float,
    y: float,
    size: float,
) -> None:
    p1 = _map_point(start, piece, x, y, size)
    p2 = _map_point(end, piece, x, y, size)
    pdf.setStrokeColorRGB(0.91, 0.36, 0.29)
    pdf.setLineWidth(1.4)
    pdf.line(p1[0], p1[1], p2[0], p2[1])


def _map_point(point: Point2D, piece: UnfoldPiece, x: float, y: float, size: float) -> tuple[float, float]:
    mapped = map_points_to_box(piece_outline_points(piece), x, y, size)
    outline = piece_outline_points(piece)
    for outline_point, mapped_point in zip(outline, mapped, strict=False):
        if outline_point.x == point.x and outline_point.y == point.y:
            return mapped_point
    all_points = map_points_to_box([point], x, y, size)
    return all_points[0] if all_points else (x, y)


def _draw_overview_step_svg(
    drawing: svgwrite.Drawing,
    group: svgwrite.container.Group,
    piece_by_id: dict[str, UnfoldPiece],
    step: AssemblyStep,
    x: float,
    y: float,
) -> None:
    cell = 28.0
    gap = 6.0
    pieces = [piece_by_id[piece_id] for piece_id in step.assembled_piece_ids if piece_id in piece_by_id]
    for index, piece in enumerate(pieces[:8]):
        col = index % 4
        row = index // 4
        px = x + col * (cell + gap)
        py = y + row * (cell + 8)
        _add_piece_polygon_svg(drawing, group, piece, px, py, cell, fill="#f1f5f9")


def _draw_prepare_step_svg(
    drawing: svgwrite.Drawing,
    group: svgwrite.container.Group,
    piece: UnfoldPiece,
    center_x: float,
    center_y: float,
) -> None:
    _add_piece_polygon_svg(drawing, group, piece, center_x - 35, center_y - 35, 70, fill="#dbeafe")
    for fold in piece.fold_lines:
        color = "#2563eb" if fold.fold_type == "valley" else "#dc2626"
        group.add(
            drawing.line(
                start=_svg_point(fold.start, piece, center_x - 35, center_y - 35, 70),
                end=_svg_point(fold.end, piece, center_x - 35, center_y - 35, 70),
                stroke=color,
                stroke_width=0.25,
                stroke_dasharray="2,1.5",
            )
        )


def _draw_join_step_svg(
    drawing: svgwrite.Drawing,
    group: svgwrite.container.Group,
    tab_owner: UnfoldPiece,
    attaching: UnfoldPiece,
    target: UnfoldPiece,
    tab,
    x: float,
    y: float,
) -> None:
    cell = 55.0
    gap = 18.0
    other = target if attaching.id == tab_owner.id else attaching
    _add_piece_polygon_svg(drawing, group, other, x, y, cell, fill="#dbeafe")
    _add_piece_polygon_svg(drawing, group, attaching, x + cell + gap, y, cell, fill="#dcfce7")
    if len(tab.polygon) >= 3:
        points = [
            _svg_point(point, tab_owner if tab_owner.id == attaching.id else attaching, x + cell + gap if tab_owner.id == attaching.id else x, y, cell)
            for point in tab.polygon
        ]
        group.add(
            drawing.polygon(
                points=points,
                fill="#fdba74",
                stroke="#ea580c",
                stroke_width=0.25,
            )
        )
    group.add(
        drawing.line(
            start=(x + cell + 2, y + cell / 2),
            end=(x + cell + gap - 2, y + cell / 2),
            stroke="#e85d4c",
            stroke_width=0.4,
        )
    )


def _add_piece_polygon_svg(
    drawing: svgwrite.Drawing,
    group: svgwrite.container.Group,
    piece: UnfoldPiece,
    x: float,
    y: float,
    size: float,
    *,
    fill: str,
) -> None:
    points = map_points_to_box(piece_outline_points(piece), x, y, size)
    if len(points) < 3:
        return
    group.add(
        drawing.polygon(
            points=points,
            fill=fill,
            stroke="#1f2937",
            stroke_width=0.25,
        )
    )


def _svg_point(point: Point2D, piece: UnfoldPiece, x: float, y: float, size: float) -> tuple[float, float]:
    return _map_point(point, piece, x, y, size)
