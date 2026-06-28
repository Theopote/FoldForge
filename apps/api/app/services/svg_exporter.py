"""SVG export for printable unfold templates."""

from pathlib import Path

import svgwrite

from app.models.geometry import LayoutPage, PlacedPiece, UnfoldPiece
from app.schemas.model import ColorMode, ProjectSettings
from app.services.export_annotations import draw_svg_page_annotations


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

    draw_svg_page_annotations(
        drawing,
        page_group,
        page_width_mm=page.width_mm,
        page_height_mm=page.height_mm,
        y_offset=y_offset,
        settings=settings,
        show_legend=page.index == 0,
    )

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
    piece_group_kwargs: dict[str, str] = {"id": piece.id}
    if piece.has_overlap:
        piece_group_kwargs["class_"] = "piece-has-overlap"
    piece_group = drawing.g(**piece_group_kwargs)
    baked_layer = drawing.g(class_="layer-baked")
    lines_layer = drawing.g(class_="layer-lines")

    if settings.color_mode == ColorMode.COLOR and piece.baked_triangles:
        for triangle in piece.baked_triangles:
            points = [
                (triangle.a.x, _svg_y(page_height_mm, y_offset, triangle.a.y)),
                (triangle.b.x, _svg_y(page_height_mm, y_offset, triangle.b.y)),
                (triangle.c.x, _svg_y(page_height_mm, y_offset, triangle.c.y)),
            ]
            baked_layer.add(
                drawing.polygon(
                    points=points,
                    fill=triangle.fill,
                    stroke="none",
                    fill_opacity=0.92,
                )
            )

    if settings.add_cut_lines:
        if piece.cut_outline and len(piece.cut_outline) >= 3:
            points = [
                (p.x, _svg_y(page_height_mm, y_offset, p.y))
                for p in piece.cut_outline
            ]
            lines_layer.add(
                drawing.polygon(
                    points=points,
                    fill="none",
                    stroke="#111827",
                    stroke_width=0.35,
                )
            )
        else:
            for cut in piece.cut_lines:
                lines_layer.add(
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
            lines_layer.add(
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

    if settings.add_tabs and not piece.cut_outline:
        for tab in piece.tabs:
            points = [
                (p.x, _svg_y(page_height_mm, y_offset, p.y))
                for p in tab.polygon
            ]
            lines_layer.add(
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
                lines_layer.add(
                    drawing.text(
                        tab.label,
                        insert=(cx, cy),
                        fill="#475569",
                        font_size="2.5mm",
                        font_family="sans-serif",
                        text_anchor="middle",
                    )
                )

    if settings.add_tabs and piece.cut_outline:
        for tab in piece.tabs:
            if not tab.label:
                continue
            if tab.polygon:
                cx = sum(p.x for p in tab.polygon) / len(tab.polygon)
                cy = sum(p.y for p in tab.polygon) / len(tab.polygon)
            elif piece.cut_outline:
                cx = sum(p.x for p in piece.cut_outline) / len(piece.cut_outline)
                cy = sum(p.y for p in piece.cut_outline) / len(piece.cut_outline)
            else:
                continue
            if settings.add_numbers:
                lines_layer.add(
                    drawing.text(
                        tab.label,
                        insert=(cx, _svg_y(page_height_mm, y_offset, cy)),
                        fill="#475569",
                        font_size="2.5mm",
                        font_family="sans-serif",
                        text_anchor="middle",
                    )
                )

    if settings.add_numbers and piece.label:
        cx = sum(p.x for p in piece.polygon) / max(len(piece.polygon), 1)
        cy = sum(p.y for p in piece.polygon) / max(len(piece.polygon), 1)
        lines_layer.add(
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

    piece_group.add(baked_layer)
    piece_group.add(lines_layer)
    if settings.add_cut_lines or settings.add_fold_lines:
        piece_group.add(
            _draw_seam_hit_targets(
                drawing,
                piece,
                page_height_mm,
                y_offset,
                include_cuts=settings.add_cut_lines,
                include_folds=settings.add_fold_lines,
            )
        )
    group.add(piece_group)


def _mesh_edge_data(edge: tuple[int, int] | None) -> dict[str, str]:
    if edge is None:
        return {}
    v0, v1 = edge
    if v0 <= v1:
        return {"data-mesh-edge": f"{v0},{v1}"}
    return {"data-mesh-edge": f"{v1},{v0}"}


def _draw_seam_hit_targets(
    drawing: svgwrite.Drawing,
    piece: UnfoldPiece,
    page_height_mm: float,
    y_offset: float,
    *,
    include_cuts: bool,
    include_folds: bool,
) -> svgwrite.container.Group:
    """Invisible wide strokes for Studio seam inspector hit-testing."""
    seams_layer = drawing.g(class_="layer-seams")

    if include_cuts:
        for cut in piece.cut_lines:
            _add_seam_hit_line(
                drawing,
                seams_layer,
                start=(cut.start.x, _svg_y(page_height_mm, y_offset, cut.start.y)),
                end=(cut.end.x, _svg_y(page_height_mm, y_offset, cut.end.y)),
                stroke_width=2.5,
                class_name="seam-edge seam-cut",
                attrs={
                    "data-piece-id": piece.id,
                    "data-piece-label": piece.label,
                    "data-line-id": cut.id,
                    "data-edge-kind": "cut",
                    **_mesh_edge_data(cut.mesh_edge),
                },
            )

    if include_folds:
        for fold in piece.fold_lines:
            _add_seam_hit_line(
                drawing,
                seams_layer,
                start=(fold.start.x, _svg_y(page_height_mm, y_offset, fold.start.y)),
                end=(fold.end.x, _svg_y(page_height_mm, y_offset, fold.end.y)),
                stroke_width=2.0,
                class_name="seam-edge seam-fold",
                attrs={
                    "data-piece-id": piece.id,
                    "data-piece-label": piece.label,
                    "data-line-id": fold.id,
                    "data-edge-kind": "fold",
                    "data-fold-type": fold.fold_type,
                    **_mesh_edge_data(fold.mesh_edge),
                },
            )

    return seams_layer


def _seam_line_id(
    edge_kind: str,
    piece_label: str,
    mesh_edge: tuple[int, int] | None,
    fold_type: str | None = None,
) -> str:
    if mesh_edge is None:
        return f"seam-{edge_kind}-{piece_label}-unknown"
    v0, v1 = mesh_edge
    base = f"seam-{edge_kind}-{piece_label}-{v0}-{v1}"
    if fold_type:
        return f"{base}-{fold_type}"
    return base


def _add_seam_hit_line(
    drawing: svgwrite.Drawing,
    group: svgwrite.container.Group,
    *,
    start: tuple[float, float],
    end: tuple[float, float],
    stroke_width: float,
    class_name: str,
    attrs: dict[str, str],
) -> None:
    mesh_edge_raw = attrs.get("data-mesh-edge", "")
    mesh_edge: tuple[int, int] | None = None
    if mesh_edge_raw:
        parts = mesh_edge_raw.split(",")
        if len(parts) == 2:
            mesh_edge = (int(parts[0]), int(parts[1]))

    line = drawing.line(
        start=start,
        end=end,
        stroke="#000000",
        stroke_width=stroke_width,
        stroke_opacity=0,
        class_=class_name,
        id=_seam_line_id(
            attrs.get("data-edge-kind", "cut"),
            attrs.get("data-piece-label", ""),
            mesh_edge,
            attrs.get("data-fold-type") or None,
        ),
    )
    group.add(line)
