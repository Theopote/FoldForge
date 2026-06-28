"""Bundle export files into a downloadable ZIP kit."""

import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app.models.geometry import LayoutPage, UnfoldPiece
from app.schemas.model import ProjectSettings
from app.services.instruction_export import export_instruction_files


def export_zip(
    output_path: Path,
    project_name: str,
    files: dict[str, Path],
    stats: dict[str, int | str],
    warnings: list[str],
    settings: ProjectSettings | None = None,
    *,
    pieces: list[UnfoldPiece] | None = None,
    pages: list[LayoutPage] | None = None,
) -> Path:
    """
    Create a ZIP archive containing templates, processed model, and instructions.

    `files` maps archive entry names to absolute filesystem paths.
    """
    settings_obj = settings or ProjectSettings()
    readme = _build_readme(project_name, stats, warnings)
    project_id = output_path.stem
    txt_path, pdf_path, steps_svg_path = export_instruction_files(
        output_path.parent,
        project_id,
        project_name,
        settings_obj,
        stats,
        warnings,
        pieces=pieces,
        pages=pages,
    )
    instructions_txt = txt_path.read_text(encoding="utf-8")
    instructions_pdf = pdf_path.read_bytes()

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", readme)
        archive.writestr("instructions.txt", instructions_txt)
        archive.writestr("instructions.pdf", instructions_pdf)
        if steps_svg_path is not None and steps_svg_path.exists():
            archive.write(steps_svg_path, arcname="assembly-steps.svg")

        for entry_name, file_path in files.items():
            if file_path.exists():
                archive.write(file_path, arcname=entry_name)

    return output_path


def _build_readme(
    project_name: str,
    stats: dict[str, int | str],
    warnings: list[str],
) -> str:
    """Generate a plain-text assembly guide for the ZIP bundle."""
    lines = [
        f"FoldForge Papercraft Kit — {project_name}",
        "=" * 48,
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Contents:",
        "  unfold.pdf        — Print this file (100% scale, no fit-to-page)",
        "  unfold.svg        — Vector template for editing",
        "  instructions.pdf  — Detailed print & assembly guide (PDF)",
        "  instructions.txt  — Detailed print & assembly guide (text)",
        "  assembly-steps.svg — Step-by-step assembly illustrations",
        "  model.glb         — Processed low-poly reference model",
        "",
        "Stats:",
        f"  Faces:   {stats.get('faces', '—')}",
        f"  Pieces:  {stats.get('pieces', '—')}",
        f"  Pages:   {stats.get('pages', '—')}",
        f"  Craftability: {stats.get('craftability', '—')}/100 ({stats.get('level', '—')})",
        "",
        "How to build:",
        "  1. Print unfold.pdf at 100% scale on cardstock (200–250 gsm recommended)",
        "  2. Cut along solid black lines",
        "  3. Score along dashed fold lines (blue = valley, red = mountain)",
        "  4. Fold and glue tabs — match numbered edges",
        "  5. Assemble pieces following part labels (A, B, C…)",
        "",
    ]

    if warnings:
        lines.extend(["Notes:", *[f"  • {warning}" for warning in warnings], ""])

    lines.extend(
        [
            "—",
            "Made with FoldForge / 纸模工坊",
            "Turn imagination into printable paper models.",
        ]
    )

    return "\n".join(lines)
