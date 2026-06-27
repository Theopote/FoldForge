"""SVG export for printable unfold templates."""

from pathlib import Path

import svgwrite

from app.models.geometry import LayoutPage, PlacedPiece
from app.schemas.model import ProjectSettings


def export_svg(
    pages: list[LayoutPage],
    output_path: Path,
    project_name: str,
    settings: ProjectSettings,
) -> Path:
    """Write a multi-page SVG document with cut, fold, tab, and label layers."""
    if not pages:
        raise ValueError("No pages to export.")

    page_gap = 20.0
    total_width = max(p.width_mm for p in pages)
    total_height = sum(p.height_mm + page_gap for p in pages) - page_gap

    drawing = svgwrite.Drawing(
        str(output_path),
        size=(f"{total_width}mm", f"{total_height}mm"),
        viewBox=f"0 0 {total_width} {total_height}",
    )

    y_offset = 0.0
    for page in pages:
        _draw_page(drawing, page, y_offset, project_name, settings)
        y_offset += page.height_mm + page_gap

    drawing.save()
    return output_path


def _draw_page(
    drawing: svgwrite.Drawing,
    page: LayoutPage,
    y_offset: float,
    project_name: str,
    settings: ProjectSettings,
) -> None:
    page_group = drawing.g(id=f"page-{page.index + 1}")

    page_group.add(
        drawing.rect(
            insert=(0, y_offset),
            size=(page.width_mm, page.height_mm),
            fill="white",
            stroke="#94a3b8",
            stroke_width=0.3,
        )
    )

    page_group.add(
        drawing.text(
            f"{project_name} — Page {page.index + 1}",
            insert=(5, y_offset + 6),
            fill="#64748b",
            font_size="3mm",
            font_family="sans-serif",
        )
    )

    for placed in page.placed_pieces:
        _draw_piece(page_group, drawing, placed, page.height_mm, y_offset, settings)

    drawing.add(page_group)


def _svg_y(page_height_mm: float, y_offset: float, y_mm: float) -> float:
    return y_offset + page_height_mm - y_mm


def _draw_piece(
    group: svgwrite.container.Group,
    drawing: svgwrite.Drawing,
    placed: PlacedPiece,
    page_height_mm: float,
    y_offset: float,
    settings: ProjectSettings,
) -> None:
    piece = placed.piece
    piece_group = drawing.g(id=piece.id)

    if settings.add_cut_lines:
        for cut in piece.cut_lines:
            piece_group.add(
                drawing.line(
                    start=(
                        cut.start.x,
                        _svg_y(page_height_mm, y_offset, cut.start.y),
                    ),
                    end=(
                        cut.end.x,
                        _svg_y(page_height_mm, y_offset, cut.end.y),
                    ),
                    stroke="#111827",
                    stroke_width=0.35,
                )
            )

    if settings.add_fold_lines:
        for fold in piece.fold_lines:
            dash = "2,1.5" if fold.fold_type == "valley" else "4,1.5"
            color = "#2563eb" if fold.fold_type == "valley" else "#dc2626"
            piece_group.add(
                drawing.line(
                    start=(
                        fold.start.x,
                        _svg_y(page_height_mm, y_offset, fold.start.y),
                    ),
                    end=(
                        fold.end.x,
                        _svg_y(page_height_mm, y_offset, fold.end.y),
                    ),
                    stroke=color,
                    stroke_width=0.25,
                    stroke_dasharray=dash,
                )
            )

    if settings.add_tabs:
        for tab in piece.tabs:
            points = [
                (p.x, _svg_y(page_height_mm, y_offset, p.y))
                for p in tab.polygon
            ]
            piece_group.add(
                drawing.polygon(
                    points=points,
                    fill="#f1f5f9",
                    stroke="#64748b",
                    stroke_width=0.2,
                )
            )
            if settings.add_numbers and tab.label:
                cx = sum(p[0] for p in points) / len(points)
                cy = sum(p[1] for p in points) / len(points)
                piece_group.add(
                    drawing.text(
                        tab.label,
                        insert=(cx, cy),
                        fill="#475569",
                        font_size="2.5mm",
                        font_family="sans-serif",
                        text_anchor="middle",
                    )
                )

    if settings.add_numbers and piece.label:
        cx = sum(p.x for p in piece.polygon) / max(len(piece.polygon), 1)
        cy = sum(p.y for p in piece.polygon) / max(len(piece.polygon), 1)
        piece_group.add(
            drawing.text(
                piece.label,
                insert=(cx, _svg_y(page_height_mm, y_offset, cy)),
                fill="#e85d4c",
                font_size="5mm",
                font_family="sans-serif",
                font_weight="bold",
                text_anchor="middle",
            )
        )

    group.add(piece_group)
