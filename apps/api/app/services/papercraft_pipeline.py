"""Orchestrate the full papercraft generation pipeline."""

from pathlib import Path

from app.config import settings as app_settings
from app.models.geometry import PipelineResult
from app.schemas.model import ProjectSettings
from app.services.craftability_scorer import compute_craftability
from app.services.layout_engine import layout_pieces
from app.services.mesh_cleaner import clean_mesh, mesh_quality_issues
from app.services.mesh_simplifier import scale_to_target_height, simplify_mesh
from app.services.model_loader import load_mesh
from app.services.pdf_exporter import export_pdf
from app.services.seam_generator import compute_edge_dihedral_angles, select_seams, split_into_patches
from app.services.svg_exporter import export_svg
from app.services.outline_optimizer import optimize_pieces_cut_outlines
from app.services.tab_generator import add_tabs_to_pieces
from app.services.unfolder import detect_unfold_overlaps, unfold_mesh
from app.services.zip_exporter import export_zip
from app.utils.file_utils import build_storage_url


def run_pipeline(
    project_id: str,
    source_path: Path,
    project_name: str,
    settings: ProjectSettings,
    source_original_path: Path | None = None,
) -> PipelineResult:
    """
    Execute load → clean → simplify → seam → unfold → tabs → layout → export.

    Writes processed mesh, SVG, and PDF to storage and returns metadata.
    """
    mesh = load_mesh(source_path)
    quality_warnings = mesh_quality_issues(mesh)

    mesh = clean_mesh(mesh)
    mesh = scale_to_target_height(mesh, settings.target_height_mm)
    mesh = simplify_mesh(mesh, settings.difficulty, settings.style)

    dihedral = compute_edge_dihedral_angles(mesh)
    seams = select_seams(mesh, settings.difficulty, dihedral=dihedral)
    patches = split_into_patches(mesh, seams)
    pieces = unfold_mesh(mesh, patches, dihedral=dihedral)
    unfold_warnings = detect_unfold_overlaps(pieces)
    pieces = add_tabs_to_pieces(
        pieces,
        add_tabs=settings.add_tabs,
        add_numbers=settings.add_numbers,
    )
    if settings.add_tabs:
        pieces = optimize_pieces_cut_outlines(pieces)

    pages = layout_pieces(pieces, settings.paper_size)

    processed_path = app_settings.processed_dir / f"{project_id}.glb"
    mesh.export(processed_path)

    svg_path = app_settings.exports_dir / f"{project_id}.svg"
    pdf_path = app_settings.exports_dir / f"{project_id}.pdf"

    export_svg(pages, svg_path, project_name, settings)
    export_pdf(pages, pdf_path, project_name, settings)

    craft_score, craft_level, craft_warnings = compute_craftability(
        mesh,
        pieces,
        pages,
        settings.difficulty,
        quality_warnings + unfold_warnings,
    )

    zip_path = app_settings.exports_dir / f"{project_id}.zip"
    zip_files: dict[str, Path] = {
        "unfold.pdf": pdf_path,
        "unfold.svg": svg_path,
        "model.glb": processed_path,
    }
    if source_original_path and source_original_path.exists():
        zip_files[f"source{source_original_path.suffix.lower()}"] = source_original_path

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
    )

    difficulty_score = _difficulty_score(len(mesh.faces), len(pieces), len(pages))

    return PipelineResult(
        processed_mesh_path=build_storage_url(Path("processed") / processed_path.name),
        svg_path=build_storage_url(Path("exports") / svg_path.name),
        pdf_path=build_storage_url(Path("exports") / pdf_path.name),
        zip_path=build_storage_url(Path("exports") / zip_path.name),
        pieces=pieces,
        pages=pages,
        face_count=len(mesh.faces),
        difficulty_score=difficulty_score,
        craftability_score=craft_score,
        craftability_level=craft_level,
        warnings=craft_warnings,
    )


def _difficulty_score(faces: int, pieces: int, pages: int) -> int:
    """Heuristic build difficulty 0–100 (higher = harder)."""
    score = 0.0
    score += min(40, faces / 20)
    score += min(30, pieces * 2)
    score += min(30, pages * 5)
    return int(min(100, round(score)))
