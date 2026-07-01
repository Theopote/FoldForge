"""Multi-turn prompt refinement using Claude."""

from __future__ import annotations

from app.config import settings
from app.schemas.model import Difficulty, Style
from app.services.ai.claude_client import claude_complete, is_available, parse_claude_json

_SYSTEM = """You are a papercraft design consultant for FoldForge.
Your job: turn a user's rough idea into an optimised Meshy AI prompt
that will produce a clean, low-polygon, fold-friendly 3D model.

Rules:
- Ask ONE clarifying question only if the input is genuinely ambiguous
  (under 5 words with no clear shape). Otherwise skip straight to the result.
- The enhanced prompt must be under 120 words and in English.
- Always output valid JSON only — no markdown, no preamble.
"""

_ENHANCE_TEMPLATE = """User's idea: "{prompt}"
Requested style: {style}
Target difficulty: {difficulty}

Return JSON:
{{
  "enhanced_prompt": "...",
  "recommended_style": "{style}",
  "recommended_difficulty": "{difficulty}",
  "tip": "One short tip for this model in Chinese (≤20 chars)"
}}

The enhanced_prompt should add: shape clarity, papercraft-friendliness,
low poly detail level, approximate face count target (easy=20-40 faces,
standard=40-100, advanced=100-200), and any structural simplifications
needed for folding."""


async def enhance_prompt(
    prompt: str,
    style: Style = Style.LOW_POLY,
    difficulty: Difficulty = Difficulty.STANDARD,
) -> dict[str, str]:
    """
    Returns enhanced_prompt, recommended_style, recommended_difficulty, tip.
    Raises RuntimeError if Claude is not available.
    """
    if not settings.claude_prompt_enhance_enabled or not is_available():
        raise RuntimeError("ANTHROPIC_API_KEY not configured.")

    user = _ENHANCE_TEMPLATE.format(
        prompt=prompt.strip(),
        style=style.value,
        difficulty=difficulty.value,
    )

    raw = await claude_complete(_SYSTEM, user, max_tokens=400, temperature=0.6)
    return parse_claude_json(raw.strip())
