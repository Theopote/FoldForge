"""Plain-text and PDF assembly instructions for export bundles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.geometry import LayoutPage, UnfoldPiece
from app.schemas.model import ColorMode, PaperSize, ProjectSettings
from app.services.assembly_step_planner import format_assembly_step_lines, plan_assembly_steps

PAPER_RECOMMENDATIONS: dict[PaperSize, str] = {
    PaperSize.A4: "A4 (210 × 297 mm) cardstock, 200–250 gsm",
    PaperSize.A3: "A3 (297 × 420 mm) cardstock, 200–250 gsm",
    PaperSize.LETTER: "US Letter (8.5 × 11 in) cardstock, 200–250 gsm",
}


@dataclass(frozen=True)
class InstructionDocument:
    title: str
    generated: str
    sections: tuple[tuple[str, tuple[str, ...]], ...]


def build_instruction_document(
    project_name: str,
    settings: ProjectSettings,
    stats: dict[str, int | str],
    warnings: list[str],
    pieces: list[UnfoldPiece] | None = None,
    pages: list[LayoutPage] | None = None,
) -> InstructionDocument:
    """Collect all instruction sections from project metadata and geometry."""
    paper = PAPER_RECOMMENDATIONS.get(settings.paper_size, str(settings.paper_size))
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    piece_list = pieces or []
    page_by_piece = _piece_page_map(pages or [])

    sections: list[tuple[str, tuple[str, ...]]] = [
        (
            "Recommended materials",
            (
                f"Paper: {paper}",
                "Tools: sharp craft knife, metal ruler, cutting mat, bone folder, PVA glue",
                "Optional: tweezers, clothespins, low-tack tape for dry-fitting seams",
            ),
        ),
    ]

    print_lines = [
        "Print unfold.pdf at 100% scale — do NOT use 'Fit to page'",
        "Verify the 50 mm scale check line on page 1 with a ruler",
        "Use borderless printing only if your printer maintains true scale",
        "Print a test page on plain paper first if unsure",
    ]
    if settings.color_mode == ColorMode.COLOR:
        print_lines.extend(
            [
                "Color mode: print on white cardstock for best surface color fidelity",
                "Use a color laser or inkjet profile suited to heavy paper",
                "Allow ink to dry fully before scoring folds (avoid smearing fills)",
                "The baked color layer sits under cut/fold lines in unfold.pdf",
            ]
        )
    sections.append(("Print settings", tuple(print_lines)))

    cut_lines = [
        "Cut along solid black lines (see legend on page 1)",
        "Score mountain folds (red dashed) from the back when possible",
        "Score valley folds (blue dashed) from the front",
    ]
    if settings.add_tabs:
        cut_lines.append("Glue tabs are shaded areas — apply glue to the tab, not the printed face")
    sections.append(("Cutting & scoring", tuple(cut_lines)))

    if piece_list:
        inventory = _format_piece_inventory(piece_list, page_by_piece)
        if inventory:
            sections.append(("Piece inventory", tuple(inventory)))

        order = _format_assembly_order(piece_list)
        if order:
            sections.append(("Suggested assembly order", tuple(order)))

        if settings.add_tabs:
            pairings = _format_tab_pairings(piece_list)
            if pairings:
                sections.append(("Glue tab pairings", tuple(pairings)))

        illustrated_steps = format_assembly_step_lines(plan_assembly_steps(piece_list, settings))
        if illustrated_steps:
            sections.append(("Illustrated assembly steps", tuple(illustrated_steps)))

    assembly_steps = [
        "Cut out every piece listed above (check page numbers before printing extras)",
        "Pre-fold all scored lines before gluing",
    ]
    if settings.add_tabs and settings.add_numbers:
        assembly_steps.append("Match tab labels to the pairing table (e.g. A1-B1 joins piece A to B)")
    elif settings.add_tabs:
        assembly_steps.append("Glue each tab to the matching outer edge on the adjacent piece")
    else:
        assembly_steps.append("Align shared edges and glue seams where tabs would normally attach")
    assembly_steps.extend(
        [
            "Glue one seam at a time; hold until the adhesive sets",
            "Build larger structural pieces first, then attach smaller details",
            "Use model.glb as a 3D reference while assembling",
        ]
    )
    sections.append(("Assembly steps", tuple(assembly_steps)))

    sections.append(
        (
            "Kit stats",
            (
                f"Faces in model: {stats.get('faces', '—')}",
                f"Paper pieces: {stats.get('pieces', '—')}",
                f"Printed pages: {stats.get('pages', '—')}",
                f"Craftability: {stats.get('craftability', '—')}/100 ({stats.get('level', '—')})",
                f"Color mode: {'color fills' if settings.color_mode == ColorMode.COLOR else 'line art'}",
            ),
        )
    )

    file_lines = [
        "unfold.pdf — primary print template",
        "unfold.svg — editable vector template",
        "instructions.pdf — this guide with piece reference and step illustrations (PDF)",
        "instructions.txt — this guide (plain text)",
        "assembly-steps.svg — step-by-step assembly illustrations (vector)",
        "model.glb — low-poly reference model",
        "README.txt — quick reference summary",
    ]
    sections.append(("Files in this ZIP", tuple(file_lines)))

    if warnings:
        sections.append(("Important notes", tuple(warnings)))

    sections.append(
        (
            "中文提示",
            (
                "以 100% 比例打印 unfold.pdf，并用第 1 页的 50 mm 刻度线校准尺寸",
                "实线裁切、虚线压痕（红=山折、蓝=谷折），胶舌区域涂胶粘合",
                "按「Suggested assembly order」从大到小组装；对照「Glue tab pairings」匹配编号",
                "彩色模式请用白卡纸打印，待油墨干燥后再压痕折叠",
            ),
        )
    )

    return InstructionDocument(
        title=f"FoldForge Assembly Instructions — {project_name}",
        generated=generated,
        sections=tuple(sections),
    )


async def build_instruction_document_async(
    project_name: str,
    settings: ProjectSettings,
    stats: dict[str, int | str],
    warnings: list[str],
    pieces: list[UnfoldPiece] | None = None,
    pages: list[LayoutPage] | None = None,
) -> InstructionDocument:
    """Async version: attempts Claude-enhanced instructions, falls back to static."""
    doc = build_instruction_document(
        project_name,
        settings,
        stats,
        warnings,
        pieces=pieces,
        pages=pages,
    )

    from app.config import settings as app_settings

    if not app_settings.claude_instructions_enabled:
        return doc

    from app.services.ai.ai_instruction_writer import generate_ai_instructions

    ai = await generate_ai_instructions(
        project_name,
        settings,
        stats,
        warnings,
        pieces or [],
        pages or [],
    )
    if ai is None:
        return doc

    return _apply_ai_instructions(doc, ai)


def _apply_ai_instructions(
    doc: InstructionDocument,
    ai: dict,
) -> InstructionDocument:
    """Replace the two rule-based sections with Claude's output."""
    new_sections: list[tuple[str, tuple[str, ...]]] = []

    for title, body in doc.sections:
        if title == "Assembly steps" and ai.get("assembly_steps_en"):
            steps = [str(step) for step in ai["assembly_steps_en"]]
            difficulty_note = ai.get("difficulty_note")
            if difficulty_note:
                steps.insert(0, f"📋 {difficulty_note}")
            new_sections.append(("Assembly steps", tuple(steps)))
        elif title == "中文提示" and ai.get("chinese_tips"):
            new_sections.append(
                ("中文提示", tuple(str(tip) for tip in ai["chinese_tips"]))
            )
        else:
            new_sections.append((title, body))

    return InstructionDocument(
        title=doc.title,
        generated=doc.generated,
        sections=tuple(new_sections),
    )


def generate_instructions(
    project_name: str,
    settings: ProjectSettings,
    stats: dict[str, int | str],
    warnings: list[str],
    *,
    pieces: list[UnfoldPiece] | None = None,
    pages: list[LayoutPage] | None = None,
) -> str:
    """Build detailed instructions.txt for the ZIP bundle."""
    document = build_instruction_document(
        project_name,
        settings,
        stats,
        warnings,
        pieces=pieces,
        pages=pages,
    )
    return format_instruction_text(document)


def format_instruction_text(document: InstructionDocument) -> str:
    lines = [
        document.title,
        "=" * min(56, len(document.title)),
        "",
        f"Generated: {document.generated}",
        "",
    ]
    for title, body in document.sections:
        lines.append(title)
        lines.extend(f"  • {line}" for line in body)
        lines.append("")

    lines.extend(
        [
            "—",
            "FoldForge / 纸模工坊 — Turn imagination into printable paper models.",
        ]
    )
    return "\n".join(lines)


def _piece_page_map(pages: list[LayoutPage]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for page in pages:
        for placed in page.placed_pieces:
            mapping[placed.piece.id] = page.index + 1
    return mapping


def _format_piece_inventory(
    pieces: list[UnfoldPiece],
    page_by_piece: dict[str, int],
) -> list[str]:
    lines: list[str] = []
    for piece in sorted(pieces, key=lambda item: item.label):
        page = page_by_piece.get(piece.id)
        page_text = f"page {page}" if page is not None else "page —"
        tab_count = len(piece.tabs)
        lines.append(
            f"Piece {piece.label} ({piece.id}) — "
            f"{len(piece.face_ids)} faces, "
            f"{len(piece.fold_lines)} folds, "
            f"{len(piece.cut_lines)} cut edges, "
            f"{tab_count} tab(s) — {page_text}"
        )
    return lines


def _format_assembly_order(pieces: list[UnfoldPiece]) -> list[str]:
    ordered = sorted(
        pieces,
        key=lambda piece: (-len(piece.face_ids), -len(piece.polygon), piece.label),
    )
    return [
        f"{index}. Piece {piece.label} — {len(piece.face_ids)} faces"
        for index, piece in enumerate(ordered, start=1)
    ]


def _format_tab_pairings(pieces: list[UnfoldPiece]) -> list[str]:
    id_to_label = {piece.id: piece.label for piece in pieces}
    lines: list[str] = []

    for piece in sorted(pieces, key=lambda item: item.label):
        for tab in piece.tabs:
            target = id_to_label.get(tab.target_piece_id, tab.target_piece_id)
            label = tab.label or f"{piece.label}→{target}"
            lines.append(
                f"{label}: tab on piece {piece.label} glues to outer edge on piece {target}"
            )

    if not lines:
        lines.append("No numbered glue tabs on this template (tabs disabled or edges too short).")
    return lines
