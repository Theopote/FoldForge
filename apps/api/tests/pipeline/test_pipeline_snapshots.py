"""Pipeline snapshot tests for committed mesh fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import settings
from tests.helpers.pipeline_assertions import (
    assert_pdf_export,
    assert_pipeline_snapshot,
    assert_svg_export,
    summarize_pipeline,
)

GOOD_FIXTURES = [
    "cube.stl",
    "low_poly_bunny.obj",
    "simple_house.glb",
    "thin_parts_model.obj",
]


@pytest.mark.parametrize("fixture_name", GOOD_FIXTURES)
def test_pipeline_snapshot(
    run_pipeline_sync,
    fixture_name: str,
    test_env: Path,
) -> None:
    stem = Path(fixture_name).stem
    project_id = f"snap_{stem[:8]}"
    result = run_pipeline_sync(
        fixture_name,
        project_id=project_id,
        project_name=f"Snapshot {stem}",
    )

    svg_path = settings.exports_dir / f"{project_id}.svg"
    pdf_path = settings.exports_dir / f"{project_id}.pdf"

    assert_svg_export(svg_path, project_name=f"Snapshot {stem}")
    assert_pdf_export(pdf_path)

    metrics = summarize_pipeline(result, svg_path=svg_path, pdf_path=pdf_path)
    assert metrics["pieces"] >= 1
    assert metrics["pages"] >= 1
    assert metrics["cut_lines"] >= 1
    assert metrics["piece_overlaps"] == 0

    assert_pipeline_snapshot(stem, metrics)


def test_bad_mesh_does_not_crash_pipeline(run_pipeline_sync) -> None:
    """Non-manifold / open meshes should fail gracefully or complete with warnings."""
    try:
        result = run_pipeline_sync(
            "non_manifold_bad_mesh.stl",
            project_id="snap_badmesh",
            project_name="Bad Mesh",
        )
    except Exception as exc:
        assert str(exc)
        return

    assert result.face_count >= 1
    assert len(result.warnings) >= 1
