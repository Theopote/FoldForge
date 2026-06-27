"""Approximate 2D unfolding of mesh patches."""

import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

from app.models.geometry import CutLine, FoldLine, Point2D, Tab, UnfoldPiece


def _normalize(v: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(v))
    if length < 1e-12:
        return v
    return v / length


def _project_to_plane(
    point: np.ndarray,
    origin: np.ndarray,
    axis_u: np.ndarray,
    axis_w: np.ndarray,
) -> Point2D:
    delta = point - origin
    return Point2D(
        x=float(np.dot(delta, axis_u)),
        y=float(np.dot(delta, axis_w)),
    )


def _face_local_basis(mesh: trimesh.Trimesh, face_idx: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    face = mesh.faces[face_idx]
    v0 = mesh.vertices[face[0]]
    v1 = mesh.vertices[face[1]]
    v2 = mesh.vertices[face[2]]

    axis_u = _normalize(v1 - v0)
    normal = _normalize(np.cross(v1 - v0, v2 - v0))
    axis_w = _normalize(np.cross(normal, axis_u))
    return v0, axis_u, axis_w


def _rotate_point_to_edge(
    point: np.ndarray,
    edge_a: np.ndarray,
    edge_b: np.ndarray,
    target_a_2d: Point2D,
    target_b_2d: Point2D,
) -> Point2D:
    """
    Rotate a 3D point into the 2D plane defined by placing edge on target 2D edge.
    """
    edge_vec_3d = edge_b - edge_a
    edge_len = float(np.linalg.norm(edge_vec_3d))
    if edge_len < 1e-12:
        return Point2D(target_a_2d.x, target_a_2d.y)

    target_vec = np.array(
        [target_b_2d.x - target_a_2d.x, target_b_2d.y - target_a_2d.y],
        dtype=np.float64,
    )
    target_len = float(np.linalg.norm(target_vec))
    if target_len < 1e-12:
        return Point2D(target_a_2d.x, target_a_2d.y)

    # Local 3D frame on edge
    t = _normalize(edge_vec_3d)
    arbitrary = np.array([1.0, 0.0, 0.0]) if abs(t[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    n = _normalize(np.cross(t, arbitrary))
    b = _normalize(np.cross(t, n))

    local = point - edge_a
    local_x = float(np.dot(local, t))
    local_y = float(np.dot(local, b))

    # Target 2D frame
    t2 = target_vec / target_len
    n2 = np.array([-t2[1], t2[0]])

    result = np.array([target_a_2d.x, target_a_2d.y]) + local_x * t2 + local_y * n2
    return Point2D(float(result[0]), float(result[1]))


def unfold_patch(
    mesh: trimesh.Trimesh,
    face_indices: list[int],
    piece_label: str,
    dihedral_angles: dict[tuple[int, int], float],
) -> UnfoldPiece:
    """
    Unfold a connected face patch into 2D using incremental face placement.

    Interior edges become fold lines; boundary edges become cut lines.
    """
    if not face_indices:
        raise ValueError("Patch has no faces.")

    patch_set = set(face_indices)
    vertex_2d: dict[int, Point2D] = {}
    placed_faces: set[int] = set()

    root = face_indices[0]
    origin, axis_u, axis_w = _face_local_basis(mesh, root)

    for vertex_idx in mesh.faces[root]:
        vertex_2d[int(vertex_idx)] = _project_to_plane(
            mesh.vertices[int(vertex_idx)],
            origin,
            axis_u,
            axis_w,
        )
    placed_faces.add(root)

    queue = [root]
    adjacency = {
        (int(f1), int(f2)): (int(v0), int(v1))
        for (f1, f2), (v0, v1) in zip(mesh.face_adjacency, mesh.face_adjacency_edges)
    }

    while queue:
        current = queue.pop(0)
        for (f1, f2), (v0, v1) in adjacency.items():
            if f1 != current and f2 != current:
                continue
            neighbor = f2 if f1 == current else f1
            if neighbor in placed_faces or neighbor not in patch_set:
                continue

            edge_a, edge_b = v0, v1
            if edge_a not in vertex_2d or edge_b not in vertex_2d:
                continue

            for vertex_idx in mesh.faces[neighbor]:
                vi = int(vertex_idx)
                if vi in vertex_2d:
                    continue
                vertex_2d[vi] = _rotate_point_to_edge(
                    mesh.vertices[vi],
                    mesh.vertices[edge_a],
                    mesh.vertices[edge_b],
                    vertex_2d[edge_a],
                    vertex_2d[edge_b],
                )

            placed_faces.add(neighbor)
            queue.append(neighbor)

    # Build piece outline from union of face triangles
    triangles: list[Polygon] = []
    for face_idx in face_indices:
        face = mesh.faces[face_idx]
        pts = [vertex_2d[int(v)].as_tuple() for v in face]
        if len(pts) >= 3:
            try:
                triangles.append(Polygon(pts))
            except Exception:
                continue

    if triangles:
        merged = unary_union(triangles)
        if merged.geom_type == "Polygon":
            outline = list(merged.exterior.coords)
        else:
            outline = list(merged.convex_hull.exterior.coords)
    else:
        outline = [p.as_tuple() for p in vertex_2d.values()]

    polygon = [Point2D(x=float(x), y=float(y)) for x, y in outline]

    fold_lines: list[FoldLine] = []
    cut_lines: list[CutLine] = []

    for (f1, f2), (v0, v1) in zip(mesh.face_adjacency, mesh.face_adjacency_edges):
        if f1 not in patch_set and f2 not in patch_set:
            continue

        key = (v0, v1) if v0 < v1 else (v1, v0)
        if v0 not in vertex_2d or v1 not in vertex_2d:
            continue

        start = vertex_2d[v0]
        end = vertex_2d[v1]

        if f1 in patch_set and f2 in patch_set:
            angle = dihedral_angles.get(key, 0.0)
            fold_type = "mountain" if angle > 0.6 else "valley"
            fold_lines.append(
                FoldLine(
                    id=f"fold-{piece_label}-{len(fold_lines)}",
                    start=start,
                    end=end,
                    fold_type=fold_type,
                )
            )
        elif f1 in patch_set or f2 in patch_set:
            cut_lines.append(
                CutLine(
                    id=f"cut-{piece_label}-{len(cut_lines)}",
                    start=start,
                    end=end,
                )
            )

    return UnfoldPiece(
        id=f"piece-{piece_label}",
        face_ids=list(face_indices),
        polygon=polygon,
        fold_lines=fold_lines,
        cut_lines=cut_lines,
        label=piece_label,
    )


def unfold_mesh(
    mesh: trimesh.Trimesh,
    patches: list[list[int]],
) -> list[UnfoldPiece]:
    """Unfold all patches into 2D pieces with labels A, B, C, ..."""
    dihedral = {}
    for face_pair, edge_verts in zip(mesh.face_adjacency, mesh.face_adjacency_edges):
        f1, f2 = int(face_pair[0]), int(face_pair[1])
        v0, v1 = int(edge_verts[0]), int(edge_verts[1])
        key = (v0, v1) if v0 < v1 else (v1, v0)
        n1 = mesh.face_normals[f1]
        n2 = mesh.face_normals[f2]
        dot = float(np.clip(np.dot(n1, n2), -1.0, 1.0))
        dihedral[key] = float(np.arccos(dot))

    pieces: list[UnfoldPiece] = []
    for index, patch in enumerate(patches):
        label = _piece_label(index)
        pieces.append(unfold_patch(mesh, patch, label, dihedral))

    return pieces


def _piece_label(index: int) -> str:
    """Generate piece labels: A, B, ... Z, AA, AB, ..."""
    label = ""
    n = index
    while True:
        label = chr(ord("A") + n % 26) + label
        n //= 26
        if n == 0:
            break
        n -= 1
    return label


def piece_bounds(piece: UnfoldPiece) -> tuple[float, float, float, float]:
    """Return min_x, min_y, max_x, max_y for a piece."""
    xs = [p.x for p in piece.polygon]
    ys = [p.y for p in piece.polygon]
    return min(xs), min(ys), max(xs), max(ys)


def translate_piece(piece: UnfoldPiece, dx: float, dy: float) -> UnfoldPiece:
    """Return a copy of piece with all coordinates translated."""
    return UnfoldPiece(
        id=piece.id,
        face_ids=piece.face_ids,
        label=piece.label,
        polygon=[Point2D(p.x + dx, p.y + dy) for p in piece.polygon],
        tabs=[
            Tab(
                id=tab.id,
                edge_id=tab.edge_id,
                target_piece_id=tab.target_piece_id,
                label=tab.label,
                polygon=[Point2D(p.x + dx, p.y + dy) for p in tab.polygon],
            )
            for tab in piece.tabs
        ],
        fold_lines=[
            FoldLine(
                id=line.id,
                fold_type=line.fold_type,
                start=Point2D(line.start.x + dx, line.start.y + dy),
                end=Point2D(line.end.x + dx, line.end.y + dy),
            )
            for line in piece.fold_lines
        ],
        cut_lines=[
            CutLine(
                id=line.id,
                start=Point2D(line.start.x + dx, line.start.y + dy),
                end=Point2D(line.end.x + dx, line.end.y + dy),
            )
            for line in piece.cut_lines
        ],
    )
