"""Texture baking spike tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import trimesh

from app.models.geometry import BakedTriangle, LayoutPage, PlacedPiece, Point2D, UnfoldPiece
from app.schemas.model import ColorMode, PaperSize, ProjectSettings
from app.services.seam_generator import compute_edge_dihedral_angles, select_seams, split_into_patches
from app.services.pdf_exporter import export_pdf, _hex_to_rgb01
from app.services.svg_exporter import export_svg
from app.services.texture_baker import bake_piece_textures
from app.services.unfold_repair import unfold_with_auto_repair
from app.services.unfolder import compute_unfold_vertex_map, translate_piece
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
    assert "layer-baked" in text
    assert "layer-lines" in text


def test_pdf_color_mode_renders_baked_fills(tmp_path: Path) -> None:
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

    color_path = tmp_path / "color.pdf"
    line_path = tmp_path / "line.pdf"
    export_pdf(
        [page],
        color_path,
        "Color Spike",
        ProjectSettings(colorMode=ColorMode.COLOR, paperSize=PaperSize.A4),
    )
    export_pdf(
        [page],
        line_path,
        "Color Spike",
        ProjectSettings(colorMode=ColorMode.LINE_ART, paperSize=PaperSize.A4),
    )

    color_bytes = color_path.read_bytes()
    line_bytes = line_path.read_bytes()
    assert color_bytes[:4] == b"%PDF"
    assert b"ca .92" in color_bytes
    assert b"ca .92" not in line_bytes
    assert len(color_bytes) > len(line_bytes)


def test_hex_to_rgb01_parses_baked_fill() -> None:
    assert _hex_to_rgb01("#4caf50") == (
        76 / 255.0,
        175 / 255.0,
        80 / 255.0,
    )


def test_bake_reuses_cached_vertex_map(monkeypatch: pytest.MonkeyPatch) -> None:
    mesh = _colored_box()
    dihedral = compute_edge_dihedral_angles(mesh)
    result = unfold_with_auto_repair(mesh, Difficulty.EASY, block_export_on_failure=False)

    assert result.pieces
    assert result.pieces[0].vertex_map

    calls = {"count": 0}
    original = compute_unfold_vertex_map

    def counting(*args, **kwargs):
        calls["count"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(
        "app.services.texture_baker.compute_unfold_vertex_map",
        counting,
    )

    _, stats = bake_piece_textures(mesh, result.pieces, dihedral)

    assert calls["count"] == 0
    assert stats.used_vertex_map_cache is True


def test_translate_piece_moves_baked_triangles() -> None:
    triangle = BakedTriangle(
        a=Point2D(0, 0),
        b=Point2D(10, 0),
        c=Point2D(5, 8),
        fill="#112233",
    )
    piece = UnfoldPiece(
        id="piece-move",
        face_ids=[0],
        polygon=[Point2D(0, 0), Point2D(10, 0), Point2D(5, 8)],
        baked_triangles=[triangle],
    )

    moved = translate_piece(piece, 12.5, 3.0)
    baked = moved.baked_triangles[0]

    assert baked.a.x == 12.5 and baked.a.y == 3.0
    assert baked.b.x == 22.5 and baked.b.y == 3.0
    assert baked.c.x == 17.5 and baked.c.y == 11.0
    assert baked.fill == "#112233"
