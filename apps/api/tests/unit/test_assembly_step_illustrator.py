"""Assembly step planner and illustration tests."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from app.models.geometry import CutLine, FoldLine, Point2D, Tab, UnfoldPiece
from app.schemas.model import ProjectSettings
from app.services.assembly_step_illustrator import (
    draw_assembly_step_pages,
    export_assembly_steps_svg,
)
from app.services.assembly_step_planner import plan_assembly_steps
from app.services.instruction_generator import generate_instructions
from app.services.instructions_pdf_exporter import render_instruction_pdf
from app.services.instruction_generator import build_instruction_document


def _sample_pieces() -> list[UnfoldPiece]:
    piece_a = UnfoldPiece(
        id="piece-a",
        face_ids=[0, 1, 2],
        polygon=[Point2D(0, 0), Point2D(40, 0), Point2D(40, 40), Point2D(0, 40)],
        label="A",
        fold_lines=[
            FoldLine(
                id="fold-a",
                start=Point2D(0, 0),
                end=Point2D(40, 0),
                fold_type="valley",
            )
        ],
        cut_lines=[
            CutLine(
                id="cut-a",
                start=Point2D(40, 0),
                end=Point2D(40, 40),
                mesh_edge=(0, 1),
            )
        ],
        tabs=[
            Tab(
                id="tab-a",
                edge_id="cut-a",
                polygon=[Point2D(40, 0), Point2D(48, 0), Point2D(48, 8), Point2D(40, 8)],
                target_piece_id="piece-b",
                label="A1-B1",
            )
        ],
    )
    piece_b = UnfoldPiece(
        id="piece-b",
        face_ids=[0],
        polygon=[Point2D(0, 0), Point2D(20, 0), Point2D(10, 20)],
        label="B",
        cut_lines=[
            CutLine(
                id="cut-b",
                start=Point2D(0, 0),
                end=Point2D(20, 0),
                mesh_edge=(0, 1),
            )
        ],
    )
    return [piece_a, piece_b]


def test_plan_assembly_steps_includes_overview_prepare_and_join() -> None:
    pieces = _sample_pieces()
    settings = ProjectSettings(addTabs=True)
    steps = plan_assembly_steps(pieces, settings)

    assert len(steps) >= 3
    assert steps[0].kind == "overview"
    assert any(step.kind == "prepare" for step in steps)
    assert any(step.kind == "join" for step in steps)
    join = next(step for step in steps if step.kind == "join")
    assert join.tab is not None
    assert join.tab.label == "A1-B1"


def test_generate_instructions_includes_illustrated_steps_section() -> None:
    text = generate_instructions(
        "Demo",
        ProjectSettings(addTabs=True),
        {"faces": 4, "pieces": 2, "pages": 1, "craftability": 70, "level": "fair"},
        [],
        pieces=_sample_pieces(),
    )

    assert "Illustrated assembly steps" in text
    assert "Step 1:" in text
    assert "Pre-fold piece A" in text


def test_export_assembly_steps_svg_writes_valid_svg(tmp_path: Path) -> None:
    svg_path = tmp_path / "steps.svg"
    export_assembly_steps_svg(
        svg_path,
        _sample_pieces(),
        ProjectSettings(addTabs=True),
        "Demo",
    )

    content = svg_path.read_text(encoding="utf-8")
    assert content.startswith("<?xml") or content.startswith("<svg")
    assert "assembly-step" in content
    assert "Step 1:" in content


def test_draw_assembly_step_pages_appends_pdf_pages() -> None:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.drawString(20, 800, "Cover")
    draw_assembly_step_pages(pdf, _sample_pieces(), ProjectSettings(addTabs=True))
    pdf.save()

    assert buffer.getvalue()[:4] == b"%PDF"
    assert len(buffer.getvalue()) > 800


def test_render_instruction_pdf_includes_step_pages() -> None:
    document = build_instruction_document(
        "Demo",
        ProjectSettings(addTabs=True),
        {"faces": 4, "pieces": 2, "pages": 1, "craftability": 70, "level": "fair"},
        [],
        pieces=_sample_pieces(),
    )
    minimal = BytesIO()
    render_instruction_pdf(minimal, document)
    full = BytesIO()
    render_instruction_pdf(
        full,
        document,
        settings=ProjectSettings(addTabs=True),
        pieces=_sample_pieces(),
    )

    assert len(full.getvalue()) > len(minimal.getvalue())


def test_export_instruction_files_writes_assembly_steps_svg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import settings
    from app.services.instruction_export import export_instruction_files

    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()
    monkeypatch.setattr(settings, "exports_dir", exports_dir)

    txt_path, pdf_path, svg_path = export_instruction_files(
        exports_dir,
        "demo-project",
        "Demo",
        ProjectSettings(addTabs=True),
        {"faces": 4, "pieces": 2, "pages": 1, "craftability": 70, "level": "fair"},
        [],
        pieces=_sample_pieces(),
    )

    assert txt_path.exists()
    assert pdf_path.exists()
    assert svg_path is not None
    assert svg_path.name == "demo-project.assembly-steps.svg"
    assert svg_path.exists()
    assert "Step" in svg_path.read_text(encoding="utf-8")
