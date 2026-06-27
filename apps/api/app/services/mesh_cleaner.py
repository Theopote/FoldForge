"""Mesh cleaning and validation."""

import trimesh


def clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """
    Clean mesh topology: merge vertices, remove degenerate faces, fix normals.

    Returns a new mesh instance safe for downstream processing.
    """
    cleaned = mesh.copy()
    cleaned.merge_vertices()
    cleaned.remove_duplicate_faces()
    cleaned.remove_degenerate_faces()
    cleaned.remove_unreferenced_vertices()
    cleaned.fix_normals()

    if len(cleaned.faces) == 0:
        raise ValueError("Mesh has no valid faces after cleaning.")

    return cleaned


def mesh_quality_issues(mesh: trimesh.Trimesh) -> list[str]:
    """Detect common mesh issues for craftability warnings."""
    warnings: list[str] = []

    if not mesh.is_watertight:
        warnings.append("Model is not watertight — some folds may be inaccurate.")

    if not mesh.is_winding_consistent:
        warnings.append("Inconsistent face winding detected.")

    edges = mesh.edges_unique
    edge_faces = mesh.edges_unique_faces
    non_manifold = sum(1 for faces in edge_faces if len(faces) > 2)
    if non_manifold > 0:
        warnings.append(f"Found {non_manifold} non-manifold edges.")

    return warnings
