"""Re-unfold and re-export after manual seam edits (skip mesh clean/simplify)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.config import settings as app_settings
from app.models.geometry import PipelineResult
from app.schemas.model import ColorMode, ProjectSettings
from app.services.cancel import CancelCheck, check_cancelled
from app.services.craftability_scorer import compute_craftability
from app.services.layout_repair import (
    collect_layout_warnings,
    ensure_layout_exportable,
    layout_with_repair,
)
from app.services.material_cache import apply_color_mode_to_cached_pieces, save_material_cache
from app.services.mesh_cleaner import mesh_quality_issues
from app.services.model_loader import load_mesh
from app.services.outline_optimizer import optimize_pieces_cut_outlines
from app.services.pdf_exporter import export_pdf
from app.services.seam_generator import compute_edge_dihedral_angles
from app.services.seam_manifest import export_seam_manifest
from app.services.seam_store import load_seam_set, save_seam_set
from app.services.svg_exporter import export_svg
from app.services.tab_generator import add_tabs_to_pieces
from app.services.texture_baker import bake_piece_textures
from app.services.unfold_repair import collect_unfold_warnings, unfold_with_custom_seams
from app.services.zip_exporter import export_zip
from app.utils.file_utils import build_storage_url

ProgressCallback = Callable[[int, str], None]


def run_seam_reflow_pipeline(
    project_id: str,
    processed_mesh_path: Path,
    project_name: str,
    settings: ProjectSettings,
    *,
    on_progress: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> PipelineResult:
    """Re-unfold from stored seams using the already-processed mesh GLB."""
    def report(progress: int, message: str) -> None:
        check_cancelled(cancel_check)
        if on_progress is not None:
            on_progress(progress, message)

    report(10, "Loading processed mesh")
    mesh = load_mesh(processed_mesh_path)
    dihedral = compute_edge_dihedral_angles(mesh)

    seams = load_seam_set(project_id)
    if seams is None:
        raise ValueError("No seam set stored for this project.")

    report(35, "Re-unfolding with custom seams")
    unfold_result = unfold_with_custom_seams(
        mesh,
        seams,
        settings.difficulty,
        dihedral=dihedral,
        cancel_check=cancel_check,
    )
    pieces = unfold_result.pieces
    unfold_warnings = collect_unfold_warnings(pieces, unfold_result.messages)
    save_seam_set(project_id, unfold_result.seams)

    face_colors: dict[int, str] = {}
    if settings.color_mode == ColorMode.COLOR:
        report(48, "Baking surface colors")
        pieces, bake_stats = bake_piece_textures(mesh, pieces, dihedral)
        face_colors = bake_stats.face_colors
    else:
        apply_color_mode_to_cached_pieces(pieces, settings, None)

    report(55, "Adding tabs and cut lines")
    pieces = add_tabs_to_pieces(
        pieces,
        add_tabs=settings.add_tabs,
        add_numbers=settings.add_numbers,
    )
    if settings.add_tabs:
        pieces = optimize_pieces_cut_outlines(pieces)

    save_material_cache(
        project_id,
        source_path=processed_mesh_path,
        settings=settings,
        pieces=pieces,
        face_colors=face_colors,
    )

    report(70, "Laying out pages")
    layout_result = layout_with_repair(
        pieces,
        settings.paper_size,
        target_height_mm=settings.target_height_mm,
        cancel_check=cancel_check,
    )
    ensure_layout_exportable(layout_result)
    pages = layout_result.pages
    layout_warnings = collect_layout_warnings(layout_result)

    report(85, "Exporting templates")
    svg_path = app_settings.exports_dir / f"{project_id}.svg"
    pdf_path = app_settings.exports_dir / f"{project_id}.pdf"
    export_svg(pages, svg_path, project_name, settings)
    export_pdf(pages, pdf_path, project_name, settings)
    export_seam_manifest(
        app_settings.exports_dir / f"{project_id}.seams.json",
        pieces,
        dihedral,
        mesh=mesh,
        active_seams=load_seam_set(project_id) or unfold_result.seams,
        difficulty=settings.difficulty,
    )

    craft_score, craft_level, craft_warnings = compute_craftability(
        mesh,
        pieces,
        pages,
        settings.difficulty,
        mesh_quality_issues(mesh) + unfold_warnings + layout_warnings,
        layout_has_overlaps=layout_result.has_overlaps,
        layout_oversize_labels=layout_result.oversize_piece_labels,
    )

    zip_path = app_settings.exports_dir / f"{project_id}.zip"
    zip_files: dict[str, Path] = {
        "unfold.pdf": pdf_path,
        "unfold.svg": svg_path,
        "model.glb": processed_mesh_path,
    }
    export_zip(
        zip_path,
        project_name,
        zip_files,
        stats={
            "faces": len(mesh.faces),
            "pieces": len(pieces),
            "pages": len(pages),
            "craftability": craft_score,
            "level": craft_level,
        },
        warnings=craft_warnings,
        settings=settings,
        pieces=pieces,
        pages=pages,
    )

    report(100, "Complete")

    return PipelineResult(
        processed_mesh_path=build_storage_url(Path("processed") / processed_mesh_path.name),
        svg_path=build_storage_url(Path("exports") / svg_path.name),
        pdf_path=build_storage_url(Path("exports") / pdf_path.name),
        zip_path=build_storage_url(Path("exports") / zip_path.name),
        pieces=pieces,
        pages=pages,
        face_count=len(mesh.faces),
        difficulty_score=_difficulty_score(len(mesh.faces), len(pieces), len(pages)),
        craftability_score=craft_score,
        craftability_level=craft_level,
        warnings=craft_warnings,
        export_blocked=unfold_result.export_blocked,
        has_unfold_overlap=unfold_result.has_unfold_overlap,
    )


def _difficulty_score(faces: int, pieces: int, pages: int) -> int:
    score = 0.0
    score += min(40, faces / 20)
    score += min(30, pieces * 2)
    score += min(30, pages * 5)
    return int(min(100, round(score)))
