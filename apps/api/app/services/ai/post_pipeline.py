"""Claude enhancements applied after the synchronous papercraft pipeline."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from app.config import settings
from app.models.geometry import PipelineResult
from app.schemas.model import ProjectSettings
from app.services.ai.ai_seam_advisor import generate_seam_hints
from app.services.instruction_export import refresh_instruction_exports_async
from app.services.model_loader import load_mesh
from app.services.seam_generator import compute_edge_dihedral_angles
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

ProgressCallback = Callable[[int, str], None]


async def apply_claude_post_pipeline_enhancements(
    *,
    project_id: str,
    project_name: str,
    project_settings: ProjectSettings,
    result: PipelineResult,
    source_prompt: str | None,
    on_progress: ProgressCallback | None = None,
) -> None:
    """Refresh instructions and seam manifest with optional Claude output."""
    stats = {
        "faces": result.face_count,
        "pieces": len(result.pieces),
        "pages": len(result.pages),
        "craftability": result.craftability_score,
        "level": result.craftability_level,
    }

    if settings.claude_instructions_enabled:
        try:
            if on_progress:
                on_progress(96, "Writing AI instructions")
            await refresh_instruction_exports_async(
                project_id=project_id,
                project_name=project_name,
                project_settings=project_settings,
                stats=stats,
                warnings=result.warnings,
                pieces=result.pieces,
                pages=result.pages,
            )
            if on_progress:
                on_progress(98, "AI instructions written")
        except Exception as exc:
            logger.warning("AI instructions failed, using static fallback: %s", exc)

    if settings.claude_seam_advisor_enabled:
        try:
            if on_progress:
                on_progress(99, "Writing AI seam hints")
            await enrich_seam_manifest_with_ai_hints(
                project_id=project_id,
                pieces=result.pieces,
                project_settings=project_settings,
                source_prompt=source_prompt,
            )
        except Exception as exc:
            logger.warning("AI seam hints failed: %s", exc)


async def enrich_seam_manifest_with_ai_hints(
    *,
    project_id: str,
    pieces: list,
    project_settings: ProjectSettings,
    source_prompt: str | None,
) -> None:
    manifest_path = settings.exports_dir / f"{project_id}.seams.json"
    if not manifest_path.exists():
        return

    processed_path = settings.processed_dir / f"{project_id}.glb"
    if not processed_path.exists():
        return

    mesh = load_mesh(processed_path)
    dihedral = compute_edge_dihedral_angles(mesh)
    ai_hints = await generate_seam_hints(
        mesh,
        pieces,
        dihedral,
        project_settings.difficulty,
        source_prompt,
    )
    if ai_hints is None:
        return

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    advisor = payload.get("advisor")
    if not isinstance(advisor, dict):
        advisor = {}
    advisor["aiHints"] = ai_hints
    payload["advisor"] = advisor
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
