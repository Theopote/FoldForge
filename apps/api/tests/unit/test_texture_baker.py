"""Texture baking spike tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

from app.models.geometry import BakedTriangle, LayoutPage, PlacedPiece, Point2D, UnfoldPiece
from app.schemas.model import ColorMode, PaperSize, ProjectSettings
from app.services.seam_generator import compute_edge_dihedral_angles, select_seams, split_into_patches
from app.services.svg_exporter import export_svg
from app.services.texture_baker import bake_piece_textures
from app.services.unfold_repair import unfold_with_auto_repair
from app.schemas.model import Difficulty


def _colored_box() -> trimesh.Trimesh:
    mesh = trimesh.creation.box(extents=(40.0, 40.0, 40.0))
    colors = np.zeros((len(mesh.vertices), 4), dtype=np.uint8)
    colors[:, 3] = 255
    colors[:, :3] = [190, 70, 70]
    colors[mesh.vertices[:, 2] > 0.0, :3] = [70, 110, 210]
    mesh.visual.vertex_colors = colors
    return mesh


def test_bake_piece_textures_from_vertex_colors() -> None:
    mesh = _colored_box()
    dihedral = compute_edge_dihedral_angles(mesh)
    piece = UnfoldPiece(
        id="piece-a",
        face_ids=[0],
        polygon=[Point2D(0, 0), Point2D(10, 0), Point2D(10, 10)],
        label="A",
    )

    baked_pieces, stats = bake_piece_textures(mesh, [piece], dihedral)

    assert stats.triangle_count == 1
    assert stats.used_vertex_colors is True
    assert len(baked_pieces[0].baked_triangles) == 1
    assert baked_pieces[0].baked_triangles[0].fill.startswith("#")


def test_unfold_pipeline_populates_baked_triangles_in_color_mode() -> None:
    mesh = _colored_box()
    result = unfold_with_auto_repair(mesh, Difficulty.EASY, block_export_on_failure=False)
    baked, stats = bake_piece_textures(mesh, result.pieces, compute_edge_dihedral_angles(mesh))

    assert stats.pieces_with_color == len(baked)
    assert stats.triangle_count > 0
    assert all(piece.baked_triangles for piece in baked)


def test_svg_color_mode_renders_baked_fills(tmp_path: Path) -> None:
    triangle = BakedTriangle(
        a=Point2D(10, 10),
        b=Point2D(40, 10),
        c=Point2D(25, 35),
        fill="#4caf50",
    )
    piece = UnfoldPiece(
        id="piece-color",
        face_ids=[0],
        polygon=[Point2D(10, 10), Point2D(40, 10), Point2D(25, 35)],
        label="A",
        baked_triangles=[triangle],
        cut_outline=[Point2D(10, 10), Point2D(40, 10), Point2D(25, 35)],
    )
    page = LayoutPage(
        index=0,
        width_mm=210,
        height_mm=297,
        placed_pieces=[PlacedPiece(piece=piece, offset_x=0, offset_y=0, page_index=0)],
    )
    settings = ProjectSettings(colorMode=ColorMode.COLOR, paperSize=PaperSize.A4)

    svg_path = tmp_path / "color.svg"
    export_svg([page], svg_path, "Color Spike", settings)

    text = svg_path.read_text(encoding="utf-8")
    assert 'fill="#4caf50"' in text
    assert "fill_opacity" in text or "opacity" in text
