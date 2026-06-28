"""Bundle export files into a downloadable ZIP kit."""

import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.model import ProjectSettings
from app.services.instruction_generator import generate_instructions


def export_zip(
    output_path: Path,
    project_name: str,
    files: dict[str, Path],
    stats: dict[str, int | str],
    warnings: list[str],
    settings: ProjectSettings | None = None,
) -> Path:
    """
    Create a ZIP archive containing templates, processed model, and instructions.

    `files` maps archive entry names to absolute filesystem paths.
    """
    settings_obj = settings or ProjectSettings()
    readme = _build_readme(project_name, stats, warnings)
    instructions = generate_instructions(project_name, settings_obj, stats, warnings)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", readme)
        archive.writestr("instructions.txt", instructions)

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
        "  unfold.pdf   — Print this file (100% scale, no fit-to-page)",
        "  unfold.svg   — Vector template for editing",
        "  instructions.txt — Detailed print & assembly guide",
        "  model.glb    — Processed low-poly reference model",
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
