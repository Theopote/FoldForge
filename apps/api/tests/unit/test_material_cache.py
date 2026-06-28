"""Material cache persistence and pipeline fast-path tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import trimesh

from app.models.geometry import BakedTriangle, Point2D, UnfoldPiece
from app.schemas.model import ColorMode, Difficulty, PaperSize, ProjectSettings, Style
from app.services.material_cache import (
    compute_source_fingerprint,
    deserialize_pieces,
    geometry_settings_key,
    load_material_cache,
    save_material_cache,
    serialize_piece,
    try_restore_geometry_cache,
)
from app.services.papercraft_pipeline import run_pipeline
from app.services.seam_generator import compute_edge_dihedral_angles
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


def test_material_cache_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "cache_dir", tmp_path / "cache")
    monkeypatch.setattr(settings, "material_cache_enabled", True)

    piece = UnfoldPiece(
        id="piece-a",
        face_ids=[0, 1],
        polygon=[Point2D(0, 0), Point2D(10, 0), Point2D(10, 10)],
        label="A",
        baked_triangles=[
            BakedTriangle(
                a=Point2D(0, 0),
                b=Point2D(5, 0),
                c=Point2D(2, 4),
                fill="#aabbcc",
            )
        ],
    )
    source = tmp_path / "source.stl"
    _colored_box().export(source)

    settings_obj = ProjectSettings(
        paperSize=PaperSize.A4,
        difficulty=Difficulty.EASY,
        colorMode=ColorMode.COLOR,
    )
    save_material_cache(
        "project-1",
        source_path=source,
        settings=settings_obj,
        pieces=[piece],
        face_colors={0: "#aabbcc", 1: "#112233"},
    )

    loaded = load_material_cache("project-1")
    assert loaded is not None
    restored = deserialize_pieces(loaded.pieces)
    assert len(restored) == 1
    assert restored[0].id == "piece-a"
    assert restored[0].baked_triangles[0].fill == "#aabbcc"
    assert loaded.face_colors["0"] == "#aabbcc"

    cache_hit, _ = try_restore_geometry_cache("project-1", source, settings_obj)
    assert cache_hit is not None
    assert cache_hit[0].face_ids == [0, 1]


def test_material_cache_round_trip_preserves_vertex_map(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "cache_dir", tmp_path / "cache")
    monkeypatch.setattr(settings, "material_cache_enabled", True)

    mesh = _colored_box()
    result = unfold_with_auto_repair(mesh, Difficulty.EASY, block_export_on_failure=False)
    source = tmp_path / "source.stl"
    mesh.export(source)

    settings_obj = ProjectSettings(colorMode=ColorMode.COLOR, paperSize=PaperSize.A4)
    save_material_cache(
        "vertex-map-project",
        source_path=source,
        settings=settings_obj,
        pieces=result.pieces,
        face_colors={0: "#aabbcc"},
    )

    loaded = load_material_cache("vertex-map-project")
    assert loaded is not None
    restored = deserialize_pieces(loaded.pieces)
    assert restored[0].vertex_map


def test_face_color_cache_skips_mesh_sampling() -> None:
    mesh = _colored_box()
    dihedral = compute_edge_dihedral_angles(mesh)
    piece = UnfoldPiece(
        id="piece-a",
        face_ids=[0],
        polygon=[Point2D(0, 0), Point2D(10, 0), Point2D(10, 10)],
    )

    first_pass, first_stats = bake_piece_textures(mesh, [piece], dihedral)
    assert first_stats.used_vertex_colors is True
    assert first_stats.face_colors[0].startswith("#")

    second_piece = UnfoldPiece(
        id="piece-a",
        face_ids=[0],
        polygon=[Point2D(0, 0), Point2D(10, 0), Point2D(10, 10)],
    )
    second_pass, second_stats = bake_piece_textures(
        mesh,
        [second_piece],
        dihedral,
        face_color_cache=first_stats.face_colors,
    )

    assert second_stats.used_face_color_cache is True
    assert second_stats.used_vertex_colors is False
    assert second_pass[0].baked_triangles[0].fill == first_pass[0].baked_triangles[0].fill


def test_run_pipeline_reuses_geometry_cache_on_paper_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import settings as app_settings

    cache_dir = tmp_path / "cache"
    exports_dir = tmp_path / "exports"
    processed_dir = tmp_path / "processed"
    for directory in (cache_dir, exports_dir, processed_dir):
        directory.mkdir(parents=True)

    monkeypatch.setattr(app_settings, "cache_dir", cache_dir)
    monkeypatch.setattr(app_settings, "exports_dir", exports_dir)
    monkeypatch.setattr(app_settings, "processed_dir", processed_dir)
    monkeypatch.setattr(app_settings, "material_cache_enabled", True)

    source = tmp_path / "cube.stl"
    trimesh.creation.box(extents=(40.0, 40.0, 40.0)).export(source)

    unfold_calls = {"count": 0}
    original_unfold = unfold_with_auto_repair

    def counting_unfold(*args, **kwargs):
        unfold_calls["count"] += 1
        return original_unfold(*args, **kwargs)

    monkeypatch.setattr(
        "app.services.papercraft_pipeline.unfold_with_auto_repair",
        counting_unfold,
    )

    def fake_layout_with_repair(pieces, paper_size, **kwargs):
        from app.services.layout_engine import layout_pieces
        from app.services.layout_repair import LayoutRepairResult

        placement = layout_pieces(pieces, paper_size)
        return LayoutRepairResult(
            pages=placement.pages,
            has_overlaps=placement.issues.has_overlaps,
        )

    monkeypatch.setattr(
        "app.services.papercraft_pipeline.layout_with_repair",
        fake_layout_with_repair,
    )

    base_settings = ProjectSettings(
        paperSize=PaperSize.A4,
        difficulty=Difficulty.EASY,
        style=Style.LOW_POLY,
        targetHeightMm=40.0,
        addTabs=False,
        colorMode=ColorMode.LINE_ART,
    )

    run_pipeline(
        project_id="cache-project",
        source_path=source,
        project_name="Cache Test",
        settings=base_settings,
        source_original_path=source,
    )
    assert unfold_calls["count"] == 1

    relayout_settings = base_settings.model_copy(update={"paperSize": PaperSize.A3})
    run_pipeline(
        project_id="cache-project",
        source_path=source,
        project_name="Cache Test",
        settings=relayout_settings,
        source_original_path=source,
    )
    assert unfold_calls["count"] == 1


def test_serialize_piece_matches_deserialize() -> None:
    piece = UnfoldPiece(
        id="piece-b",
        face_ids=[3],
        polygon=[Point2D(1, 2), Point2D(3, 4), Point2D(5, 6)],
        label="B",
    )
    restored = deserialize_pieces([serialize_piece(piece)])[0]
    assert restored.id == piece.id
    assert restored.polygon[1].x == 3
    assert restored.label == "B"


def test_geometry_settings_key_changes_when_tabs_toggle() -> None:
    with_tabs = ProjectSettings(addTabs=True)
    without_tabs = ProjectSettings(addTabs=False)
    assert geometry_settings_key(with_tabs) != geometry_settings_key(without_tabs)


def test_source_fingerprint_changes_with_file_content(tmp_path: Path) -> None:
    first = tmp_path / "a.stl"
    second = tmp_path / "b.stl"
    trimesh.creation.box(extents=(10, 10, 10)).export(first)
    trimesh.creation.box(extents=(20, 20, 20)).export(second)
    assert compute_source_fingerprint(first) != compute_source_fingerprint(second)
