"""Build and write instruction bundle files for ZIP and standalone export."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from app.models.geometry import LayoutPage, UnfoldPiece
from app.schemas.model import ProjectSettings
from app.services.assembly_step_illustrator import export_assembly_steps_svg
from app.services.instruction_generator import build_instruction_document, format_instruction_text
from app.services.instructions_pdf_exporter import render_instruction_pdf


def build_instruction_bundle(
    project_name: str,
    settings: ProjectSettings,
    stats: dict[str, int | str],
    warnings: list[str],
    *,
    pieces: list[UnfoldPiece] | None = None,
    pages: list[LayoutPage] | None = None,
) -> tuple[str, bytes]:
    """Return plain-text instructions and PDF bytes from the same document."""
    document = build_instruction_document(
        project_name,
        settings,
        stats,
        warnings,
        pieces=pieces,
        pages=pages,
    )
    txt = format_instruction_text(document)
    pdf_buffer = BytesIO()
    render_instruction_pdf(
        pdf_buffer,
        document,
        settings=settings,
        pieces=pieces,
        pages=pages,
    )
    return txt, pdf_buffer.getvalue()


def export_instruction_files(
    exports_dir: Path,
    project_id: str,
    project_name: str,
    settings: ProjectSettings,
    stats: dict[str, int | str],
    warnings: list[str],
    *,
    pieces: list[UnfoldPiece] | None = None,
    pages: list[LayoutPage] | None = None,
) -> tuple[Path, Path, Path | None]:
    """Write instruction exports under exports dir (txt, pdf, optional steps SVG)."""
    txt, pdf_bytes = build_instruction_bundle(
        project_name,
        settings,
        stats,
        warnings,
        pieces=pieces,
        pages=pages,
    )
    txt_path = exports_dir / f"{project_id}.instructions.txt"
    pdf_path = exports_dir / f"{project_id}.instructions.pdf"
    txt_path.write_text(txt, encoding="utf-8")
    pdf_path.write_bytes(pdf_bytes)

    svg_path: Path | None = None
    if pieces:
        svg_path = exports_dir / f"{project_id}.assembly-steps.svg"
        export_assembly_steps_svg(svg_path, pieces, settings, project_name)

    return txt_path, pdf_path, svg_path
