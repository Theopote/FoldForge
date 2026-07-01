"""Use Claude to write personalized assembly instructions from pipeline geometry."""

from __future__ import annotations

import json

from app.config import settings as app_settings
from app.models.geometry import LayoutPage, UnfoldPiece
from app.schemas.model import ProjectSettings
from app.services.llm import complete_json, is_llm_available
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

_SYSTEM = """You are an expert papercraft instructor writing clear, friendly assembly
guides for FoldForge paper models. You write in both English and Chinese.
Be specific to the model described — never use generic filler text.
Keep each point concise (one sentence). Output only the JSON asked for."""


def _build_context(
    project_name: str,
    settings: ProjectSettings,
    stats: dict[str, int | str],
    warnings: list[str],
    pieces: list[UnfoldPiece],
    pages: list[LayoutPage],
) -> str:
    ordered = sorted(pieces, key=lambda piece: (-len(piece.face_ids), piece.label))
    piece_summaries = [
        {
            "label": piece.label,
            "faces": len(piece.face_ids),
            "folds": len(piece.fold_lines),
            "tabs": len(piece.tabs),
        }
        for piece in ordered[:20]
    ]

    return json.dumps(
        {
            "project_name": project_name,
            "difficulty": settings.difficulty.value,
            "style": settings.style.value,
            "paper_size": settings.paper_size.value,
            "add_tabs": settings.add_tabs,
            "color_mode": settings.color_mode.value,
            "craftability_score": stats.get("craftability"),
            "craftability_level": stats.get("level"),
            "total_pieces": stats.get("pieces"),
            "total_pages": stats.get("pages"),
            "warnings": warnings[:5],
            "pieces": piece_summaries,
        },
        ensure_ascii=False,
        indent=2,
    )


_USER_TEMPLATE = """Here is a FoldForge papercraft model's data:

{context}

Write personalized assembly instructions for this specific model.

Return ONLY valid JSON with this exact structure (no markdown, no preamble):
{{
  "assembly_steps_en": [
    "Step 1: ...",
    "Step 2: ..."
  ],
  "chinese_tips": [
    "中文提示 1",
    "中文提示 2",
    "中文提示 3",
    "中文提示 4"
  ],
  "difficulty_note": "One sentence noting difficulty and who it suits."
}}

Rules:
- assembly_steps_en: 5-7 steps specific to this model (mention actual piece count, difficulty, tabs if present)
- chinese_tips: exactly 4 tips in Chinese, specific to this model
- Mention the craftability score and what it means for this model
- If warnings exist, address them in the steps
"""


async def generate_ai_instructions(
    project_name: str,
    settings: ProjectSettings,
    stats: dict[str, int | str],
    warnings: list[str],
    pieces: list[UnfoldPiece],
    pages: list[LayoutPage],
) -> dict[str, list[str] | str] | None:
    """
    Call Claude to generate personalised instructions.
    Returns None if Claude is not configured or on error (caller uses fallback).
    """
    if not app_settings.claude_instructions_enabled or not is_llm_available():
        return None

    context = _build_context(project_name, settings, stats, warnings, pieces, pages)
    user_prompt = _USER_TEMPLATE.format(context=context)

    try:
        return await complete_json(_SYSTEM, user_prompt, max_tokens=800, temperature=0.5)
    except Exception as exc:
        logger.warning("LLM instruction generation failed: %s", exc)
        return None
