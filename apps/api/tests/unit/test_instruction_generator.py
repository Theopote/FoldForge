"""Assembly instruction generator tests."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from app.models.geometry import CutLine, FoldLine, LayoutPage, PlacedPiece, Point2D, Tab, UnfoldPiece
from app.schemas.model import ColorMode, Difficulty, PaperSize, ProjectSettings, Style
from app.services.instruction_generator import generate_instructions
from app.services.instructions_pdf_exporter import export_instructions_pdf
from app.services.papercraft_pipeline import run_pipeline


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


def _sample_pages(pieces: list[UnfoldPiece]) -> list[LayoutPage]:
    return [
        LayoutPage(
            index=0,
            width_mm=210,
            height_mm=297,
            placed_pieces=[
                PlacedPiece(piece=pieces[0], offset_x=10, offset_y=10, page_index=0),
                PlacedPiece(piece=pieces[1], offset_x=60, offset_y=10, page_index=0),
            ],
        )
    ]


def test_generate_instructions_includes_piece_inventory_and_tab_pairings() -> None:
    pieces = _sample_pieces()
    pages = _sample_pages(pieces)
    settings = ProjectSettings(addTabs=True, addNumbers=True)
    text = generate_instructions(
        "Demo",
        settings,
        {"faces": 8, "pieces": 2, "pages": 1, "craftability": 80, "level": "good"},
        [],
        pieces=pieces,
        pages=pages,
    )

    assert "Piece inventory" in text
    assert "Piece A (piece-a)" in text
    assert "page 1" in text
    assert "Suggested assembly order" in text
    assert "1. Piece A" in text
    assert "Glue tab pairings" in text
    assert "A1-B1" in text
    assert "piece B" in text
    assert "中文提示" in text


def test_generate_instructions_includes_color_mode_guidance() -> None:
    pieces = _sample_pieces()
    text = generate_instructions(
        "Color Demo",
        ProjectSettings(colorMode=ColorMode.COLOR),
        {"faces": 4, "pieces": 2, "pages": 1, "craftability": 75, "level": "fair"},
        [],
        pieces=pieces,
    )

    assert "Color mode: print on white cardstock" in text
    assert "Color mode: color fills" in text
    assert "彩色模式请用白卡纸打印" in text


def test_export_instructions_pdf_writes_valid_pdf(tmp_path: Path) -> None:
    pieces = _sample_pieces()
    pdf_path = tmp_path / "instructions.pdf"
    export_instructions_pdf(
        pdf_path,
        "Demo",
        ProjectSettings(),
        {"faces": 4, "pieces": 2, "pages": 1, "craftability": 70, "level": "fair"},
        ["Test warning"],
        pieces=pieces,
        pages=_sample_pages(pieces),
    )

    header = pdf_path.read_bytes()[:4]
    assert header == b"%PDF"
    assert pdf_path.stat().st_size > 400


def test_export_instructions_pdf_bytesio() -> None:
    buffer = BytesIO()
    export_instructions_pdf(
        buffer,
        "Demo",
        ProjectSettings(),
        {"faces": 4, "pieces": 2, "pages": 1, "craftability": 70, "level": "fair"},
        [],
        pieces=_sample_pieces(),
    )
    assert buffer.getvalue()[:4] == b"%PDF"


def test_export_instructions_pdf_includes_piece_reference_page(tmp_path: Path) -> None:
    pieces = _sample_pieces()
    minimal_pdf = tmp_path / "minimal.pdf"
    full_pdf = tmp_path / "full.pdf"

    export_instructions_pdf(
        minimal_pdf,
        "Demo",
        ProjectSettings(),
        {"faces": 4, "pieces": 2, "pages": 1, "craftability": 70, "level": "fair"},
        [],
    )
    export_instructions_pdf(
        full_pdf,
        "Demo",
        ProjectSettings(),
        {"faces": 4, "pieces": 2, "pages": 1, "craftability": 70, "level": "fair"},
        [],
        pieces=pieces,
        pages=_sample_pages(pieces),
    )

    assert full_pdf.stat().st_size > minimal_pdf.stat().st_size


def test_export_instruction_files_writes_standalone_exports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import settings
    from app.services.instruction_export import export_instruction_files

    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()
    monkeypatch.setattr(settings, "exports_dir", exports_dir)

    txt_path, pdf_path = export_instruction_files(
        exports_dir,
        "demo-project",
        "Demo",
        ProjectSettings(addTabs=True),
        {"faces": 4, "pieces": 2, "pages": 1, "craftability": 70, "level": "fair"},
        [],
        pieces=_sample_pieces(),
        pages=_sample_pages(_sample_pieces()),
    )

    assert txt_path.name == "demo-project.instructions.txt"
    assert pdf_path.name == "demo-project.instructions.pdf"
    assert "Piece inventory" in txt_path.read_text(encoding="utf-8")
    assert pdf_path.read_bytes()[:4] == b"%PDF"


def test_pipeline_zip_contains_instructions_pdf(
    test_env: Path,
    fixtures_dir: Path,
    fast_layout,
) -> None:
    from app.config import settings as app_settings

    source = fixtures_dir / "cube.stl"
    run_pipeline(
        project_id="instruction_zip",
        source_path=source,
        project_name="Instruction Cube",
        settings=ProjectSettings(
            paperSize=PaperSize.A4,
            difficulty=Difficulty.EASY,
            style=Style.LOW_POLY,
            targetHeightMm=80.0,
            addTabs=True,
            addNumbers=True,
        ),
        source_original_path=source,
    )

    import zipfile

    zip_path = app_settings.exports_dir / "instruction_zip.zip"
    txt_path = app_settings.exports_dir / "instruction_zip.instructions.txt"
    pdf_path = app_settings.exports_dir / "instruction_zip.instructions.pdf"
    assert txt_path.exists()
    assert pdf_path.exists()
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        assert "instructions.pdf" in names
        assert archive.read("instructions.pdf")[:4] == b"%PDF"
        instructions = archive.read("instructions.txt").decode("utf-8")
        assert "Piece inventory" in instructions
        assert "Suggested assembly order" in instructions
