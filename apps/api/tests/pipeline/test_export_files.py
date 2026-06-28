"""SVG and PDF export structure tests."""

from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.schemas.model import Difficulty, PaperSize, ProjectSettings, Style
from app.services.pdf_exporter import export_pdf
from app.services.papercraft_pipeline import run_pipeline
from tests.helpers.pipeline_assertions import assert_pdf_export, assert_svg_export


def test_export_files_from_cube_pipeline(run_pipeline_sync, fast_layout, test_env: Path) -> None:
    result = run_pipeline_sync(
        "cube.stl",
        project_id="export_cube",
        project_name="Cube Export",
    )

    svg_path = settings.exports_dir / "export_cube.svg"
    pdf_path = settings.exports_dir / "export_cube.pdf"
    zip_path = settings.exports_dir / "export_cube.zip"

    assert_svg_export(svg_path, project_name="Cube Export")
    assert_pdf_export(pdf_path)
    assert zip_path.exists() and zip_path.stat().st_size > 500

    svg_text = svg_path.read_text(encoding="utf-8")
    assert "Scale check" in svg_text
    assert "Legend" in svg_text
    assert 'stroke-dasharray="2,1"' in svg_text or "stroke-dasharray" in svg_text

    import zipfile

    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        assert "README.txt" in names
        assert "instructions.txt" in names
        assert "instructions.pdf" in names
        instructions = archive.read("instructions.txt").decode("utf-8")
        assert "Print settings" in instructions
        assert "50 mm scale check" in instructions
        assert "Piece inventory" in instructions
        assert "Illustrated assembly steps" in instructions
        assert "assembly-steps.svg" in names
        assert archive.read("instructions.pdf")[:4] == b"%PDF"
        steps_svg = archive.read("assembly-steps.svg").decode("utf-8")
        assert "Step 1:" in steps_svg

    assert result.craftability_score >= 0
    assert result.craftability_score <= 100


def test_pdf_page_size_matches_paper_setting(test_env: Path, fixtures_dir: Path, fast_layout) -> None:
    source = fixtures_dir / "cube.stl"
    settings_obj = ProjectSettings(
        paperSize=PaperSize.A4,
        difficulty=Difficulty.EASY,
        style=Style.LOW_POLY,
        targetHeightMm=80.0,
        addTabs=False,
        addNumbers=True,
        addFoldLines=True,
        addCutLines=True,
    )
    result = run_pipeline(
        project_id="pdf_a4",
        source_path=source,
        project_name="A4 Cube",
        settings=settings_obj,
        source_original_path=source,
    )
    pdf_path = settings.exports_dir / "pdf_a4.pdf"
    assert_pdf_export(pdf_path)
    assert len(result.pages) >= 1
    assert result.pages[0].width_mm > 200
    assert result.pages[0].height_mm > 280


def test_export_pdf_requires_pages(tmp_path: Path) -> None:
    settings_obj = ProjectSettings()
    try:
        export_pdf([], tmp_path / "empty.pdf", "Empty", settings_obj)
    except ValueError as exc:
        assert "No pages" in str(exc)
    else:
        raise AssertionError("Expected ValueError for empty pages")
