"""Use Claude to provide semantic seam suggestions from mesh topology."""

from __future__ import annotations

import json

import numpy as np
import trimesh

from app.config import settings
from app.models.geometry import UnfoldPiece
from app.schemas.model import Difficulty
from app.services.llm import complete_json, is_llm_available
from app.services.seam_generator import EdgeDihedralData
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

_SYSTEM = """You are a papercraft model designer reviewing a 3D mesh for cutting seams.
You understand how meshes unfold into flat paper pieces.
Give practical, specific advice a hobbyist can act on.
Output only valid JSON — no markdown, no extra text."""


def _describe_mesh(
    mesh: trimesh.Trimesh,
    pieces: list[UnfoldPiece],
    dihedral: EdgeDihedralData,
    prompt_hint: str | None,
) -> str:
    piece_stats = []
    for piece in sorted(pieces, key=lambda item: -len(item.face_ids))[:15]:
        face_normals = mesh.face_normals[piece.face_ids]
        normal_variance = float(np.std(face_normals, axis=0).mean())
        piece_stats.append(
            {
                "label": piece.label,
                "face_count": len(piece.face_ids),
                "has_overlap": piece.has_overlap,
                "normal_variance": round(normal_variance, 3),
                "tab_count": len(piece.tabs),
            }
        )

    sharp_edges = [
        {
            "edge": list(edge),
            "angle_deg": round(float(np.degrees(angle)), 1),
        }
        for edge, angle in list(dihedral.unsigned.items())[:30]
        if angle > np.radians(45)
    ]

    return json.dumps(
        {
            "model_hint": prompt_hint or "Unknown model",
            "total_faces": len(mesh.faces),
            "total_pieces": len(pieces),
            "overlapping_pieces": [piece.label for piece in pieces if piece.has_overlap],
            "pieces": piece_stats,
            "sharp_edge_sample": sharp_edges[:15],
        },
        ensure_ascii=False,
        indent=2,
    )


_USER_TEMPLATE = """This is a papercraft model mesh data:

{context}

Based on the model's apparent structure (hint: "{hint}"), answer:
1. Which pieces likely represent major structural parts (body, head, limbs)?
2. Are there seam placements that look geometrically unnatural for this model?
3. What 2-3 specific seam changes would improve the final assembled appearance?

Return ONLY JSON:
{{
  "model_interpretation": "One sentence describing what this model appears to be",
  "structural_notes": "One sentence about the overall piece structure",
  "suggestions": [
    {{
      "action": "split",
      "piece_labels": ["A", "B"],
      "reason": "Specific reason referencing the model's anatomy/structure"
    }}
  ],
  "assembly_order_hint": "Natural build order for this model type (Chinese OK)"
}}

Keep each suggestion reason under 20 words. Max 3 suggestions."""


async def generate_seam_hints(
    mesh: trimesh.Trimesh,
    pieces: list[UnfoldPiece],
    dihedral: EdgeDihedralData,
    difficulty: Difficulty,
    prompt_hint: str | None = None,
) -> dict | None:
    """
    Returns AI seam hints or None if Claude unavailable / on error.
    Called after geometric seam selection — provides semantic overlay only.
    """
    if not settings.claude_seam_advisor_enabled or not is_llm_available():
        return None

    _ = difficulty
    context = _describe_mesh(mesh, pieces, dihedral, prompt_hint)
    user = _USER_TEMPLATE.format(
        context=context,
        hint=prompt_hint or "no hint provided",
    )

    try:
        return await complete_json(_SYSTEM, user, max_tokens=500, temperature=0.4)
    except Exception as exc:
        logger.warning("LLM seam advisor failed: %s", exc)
        return None
