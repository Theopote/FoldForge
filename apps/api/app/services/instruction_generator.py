"""Plain-text assembly instructions for export bundles."""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.model import PaperSize, ProjectSettings

PAPER_RECOMMENDATIONS: dict[PaperSize, str] = {
    PaperSize.A4: "A4 (210 × 297 mm) cardstock, 200–250 gsm",
    PaperSize.A3: "A3 (297 × 420 mm) cardstock, 200–250 gsm",
    PaperSize.LETTER: "US Letter (8.5 × 11 in) cardstock, 200–250 gsm",
}


def generate_instructions(
    project_name: str,
    settings: ProjectSettings,
    stats: dict[str, int | str],
    warnings: list[str],
) -> str:
    """Build detailed instructions.txt for the ZIP bundle."""
    paper = PAPER_RECOMMENDATIONS.get(settings.paper_size, str(settings.paper_size))
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"FoldForge Assembly Instructions — {project_name}",
        "=" * 56,
        "",
        f"Generated: {generated}",
        "",
        "Recommended materials",
        f"  • Paper: {paper}",
        "  • Tools: sharp craft knife, metal ruler, cutting mat, bone folder, PVA glue",
        "",
        "Print settings",
        "  • Print unfold.pdf at 100% scale — do NOT use 'Fit to page'",
        "  • Verify the 50 mm scale check line on page 1 with a ruler",
        "  • Use borderless printing only if your printer maintains true scale",
        "  • Print a test page on plain paper first if unsure",
        "",
        "Cutting & scoring",
        "  • Cut along solid black lines (see legend on page 1)",
        "  • Score mountain folds (red dashed) from the back when possible",
        "  • Score valley folds (blue dashed) from the front",
        "  • Glue tabs are shaded areas — apply glue to the tab, not the face",
        "",
        "Assembly",
        "  1. Cut out all numbered pieces",
        "  2. Pre-fold all scored lines before gluing",
        "  3. Match numbered tabs to matching edges (A↔A, B↔B, …)",
        "  4. Glue one seam at a time; hold until set",
        "  5. Work from larger structural pieces to smaller details",
        "",
        "Kit stats",
        f"  • Faces in model: {stats.get('faces', '—')}",
        f"  • Paper pieces: {stats.get('pieces', '—')}",
        f"  • Printed pages: {stats.get('pages', '—')}",
        f"  • Craftability: {stats.get('craftability', '—')}/100 ({stats.get('level', '—')})",
        "",
        "Files in this ZIP",
        "  • unfold.pdf  — primary print template",
        "  • unfold.svg  — editable vector template",
        "  • model.glb   — low-poly reference model",
        "  • README.txt  — quick reference summary",
        "",
    ]

    if warnings:
        lines.extend(["Important notes", *[f"  • {warning}" for warning in warnings], ""])

    lines.extend(
        [
            "—",
            "FoldForge / 纸模工坊 — Turn imagination into printable paper models.",
        ]
    )
    return "\n".join(lines)
