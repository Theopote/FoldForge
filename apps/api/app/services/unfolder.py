"""Approximate 2D unfolding of mesh patches."""

from __future__ import annotations

import heapq

import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

from app.models.geometry import CutLine, FoldLine, Point2D, Tab, UnfoldPiece
from app.services.seam_generator import EdgeDihedralData, _edge_key, compute_edge_dihedral_angles

OVERLAP_AREA_THRESHOLD_MM2 = 0.5


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
    """Rotate a 3D point into the 2D plane defined by placing edge on target 2D edge."""
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

    t = _normalize(edge_vec_3d)
    arbitrary = np.array([1.0, 0.0, 0.0]) if abs(t[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    n = _normalize(np.cross(t, arbitrary))
    b = _normalize(np.cross(t, n))

    local = point - edge_a
    local_x = float(np.dot(local, t))
    local_y = float(np.dot(local, b))

    t2 = target_vec / target_len
    n2 = np.array([-t2[1], t2[0]])

    result = np.array([target_a_2d.x, target_a_2d.y]) + local_x * t2 + local_y * n2
    return Point2D(float(result[0]), float(result[1]))


def _build_face_adjacency(
    mesh: trimesh.Trimesh,
) -> dict[int, list[tuple[int, int, int]]]:
    """Map face index → list of (neighbor_face, v0, v1) shared-edge vertices."""
    adjacency: dict[int, list[tuple[int, int, int]]] = {i: [] for i in range(len(mesh.faces))}

    for face_pair, edge_verts in zip(mesh.face_adjacency, mesh.face_adjacency_edges):
        f1, f2 = int(face_pair[0]), int(face_pair[1])
        v0, v1 = int(edge_verts[0]), int(edge_verts[1])
        adjacency[f1].append((f2, v0, v1))
        adjacency[f2].append((f1, v0, v1))

    return adjacency


def _extract_outline_coords(merged) -> list[tuple[float, float]]:
    """Extract the best outer boundary from a Shapely union result."""
    if merged.is_empty:
        return []

    if merged.geom_type == "Polygon":
        return list(merged.exterior.coords)

    if merged.geom_type == "MultiPolygon":
        largest = max(merged.geoms, key=lambda geom: geom.area)
        return list(largest.exterior.coords)

    if merged.geom_type == "GeometryCollection":
        polygons = [geom for geom in merged.geoms if geom.geom_type == "Polygon" and not geom.is_empty]
        if polygons:
            largest = max(polygons, key=lambda geom: geom.area)
            return list(largest.exterior.coords)

    cleaned = merged.buffer(0)
    if not cleaned.is_empty and cleaned.geom_type in ("Polygon", "MultiPolygon"):
        return _extract_outline_coords(cleaned)

    return list(merged.convex_hull.exterior.coords)


def _face_polygon_2d(
    mesh: trimesh.Trimesh,
    face_idx: int,
    vertex_2d: dict[int, Point2D],
) -> Polygon | None:
    face = mesh.faces[face_idx]
    pts = [vertex_2d[int(v)].as_tuple() for v in face if int(v) in vertex_2d]
    if len(pts) < 3:
        return None
    try:
        poly = Polygon(pts)
        return poly if poly.is_valid and not poly.is_empty else None
    except Exception:
        return None


def _detect_face_overlap(new_face: Polygon, placed: list[Polygon]) -> bool:
    for existing in placed:
        if not new_face.intersects(existing):
            continue
        if new_face.touches(existing):
            continue
        intersection = new_face.intersection(existing)
        if intersection.area > OVERLAP_AREA_THRESHOLD_MM2:
            return True
    return False


def unfold_patch(
    mesh: trimesh.Trimesh,
    face_indices: list[int],
    piece_label: str,
    dihedral: EdgeDihedralData,
) -> UnfoldPiece:
    """
    Unfold a connected face patch into 2D using incremental face placement.

    Neighbors are placed in order of lowest dihedral (flattest joints first) to
    reduce cumulative folding error. Interior edges become fold lines; boundary
    edges become cut lines.
    """
    if not face_indices:
        raise ValueError("Patch has no faces.")

    patch_set = set(face_indices)
    vertex_2d: dict[int, Point2D] = {}
    placed_faces: set[int] = set()
    placed_triangles: list[Polygon] = []
    overlap_detected = False

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
    root_poly = _face_polygon_2d(mesh, root, vertex_2d)
    if root_poly is not None:
        placed_triangles.append(root_poly)

    adjacency = _build_face_adjacency(mesh)
    heap: list[tuple[float, int, int, int, int]] = []
    # (dihedral priority, current face, neighbor, v0, v1)

    def push_neighbors(current: int) -> None:
        for neighbor, v0, v1 in adjacency.get(current, []):
            if neighbor in placed_faces or neighbor not in patch_set:
                continue
            key = _edge_key(v0, v1)
            priority = dihedral.unsigned.get(key, 0.0)
            heapq.heappush(heap, (priority, current, neighbor, v0, v1))

    push_neighbors(root)

    while heap:
        _, current, neighbor, v0, v1 = heapq.heappop(heap)
        if neighbor in placed_faces:
            continue

        edge_a, edge_b = v0, v1
        if edge_a not in vertex_2d or edge_b not in vertex_2d:
            continue

        trial_2d = dict(vertex_2d)
        for vertex_idx in mesh.faces[neighbor]:
            vi = int(vertex_idx)
            if vi in trial_2d:
                continue
            trial_2d[vi] = _rotate_point_to_edge(
                mesh.vertices[vi],
                mesh.vertices[edge_a],
                mesh.vertices[edge_b],
                vertex_2d[edge_a],
                vertex_2d[edge_b],
            )

        trial_poly = _face_polygon_2d(mesh, neighbor, trial_2d)
        if trial_poly is not None and _detect_face_overlap(trial_poly, placed_triangles):
            # Retry with flipped edge orientation (mirror across shared edge)
            flipped = dict(vertex_2d)
            for vertex_idx in mesh.faces[neighbor]:
                vi = int(vertex_idx)
                if vi in flipped:
                    continue
                flipped[vi] = _rotate_point_to_edge(
                    mesh.vertices[vi],
                    mesh.vertices[edge_b],
                    mesh.vertices[edge_a],
                    vertex_2d[edge_b],
                    vertex_2d[edge_a],
                )
            flipped_poly = _face_polygon_2d(mesh, neighbor, flipped)
            if flipped_poly is not None and not _detect_face_overlap(flipped_poly, placed_triangles):
                trial_2d = flipped
                trial_poly = flipped_poly
            elif trial_poly is not None and _detect_face_overlap(trial_poly, placed_triangles):
                overlap_detected = True

        vertex_2d = trial_2d
        placed_faces.add(neighbor)
        if trial_poly is not None:
            placed_triangles.append(trial_poly)
        push_neighbors(neighbor)

    # Build piece outline from union of face triangles
    triangles: list[Polygon] = []
    for face_idx in face_indices:
        poly = _face_polygon_2d(mesh, face_idx, vertex_2d)
        if poly is not None:
            triangles.append(poly)

    if triangles:
        merged = unary_union(triangles)
        outline = _extract_outline_coords(merged)
    else:
        outline = [p.as_tuple() for p in vertex_2d.values()]

    polygon = [Point2D(x=float(x), y=float(y)) for x, y in outline]

    fold_lines: list[FoldLine] = []
    cut_lines: list[CutLine] = []

    for (f1, f2), (v0, v1) in zip(mesh.face_adjacency, mesh.face_adjacency_edges):
        if f1 not in patch_set and f2 not in patch_set:
            continue

        key = _edge_key(v0, v1)
        if v0 not in vertex_2d or v1 not in vertex_2d:
            continue

        start = vertex_2d[v0]
        end = vertex_2d[v1]

        if f1 in patch_set and f2 in patch_set:
            signed = dihedral.signed.get(key, 0.0)
            fold_type = "mountain" if signed >= 0 else "valley"
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
        has_overlap=overlap_detected,
    )


def unfold_mesh(
    mesh: trimesh.Trimesh,
    patches: list[list[int]],
    dihedral: EdgeDihedralData | None = None,
) -> list[UnfoldPiece]:
    """Unfold all patches into 2D pieces with labels A, B, C, ..."""
    data = dihedral or compute_edge_dihedral_angles(mesh)

    pieces: list[UnfoldPiece] = []
    for index, patch in enumerate(patches):
        label = _piece_label(index)
        pieces.append(unfold_patch(mesh, patch, label, data))

    return pieces


def detect_unfold_overlaps(pieces: list[UnfoldPiece]) -> list[str]:
    """Return warnings for pieces whose 2D unfold faces overlap."""
    warnings: list[str] = []
    for piece in pieces:
        if piece.has_overlap:
            warnings.append(
                f"Piece {piece.label} has overlapping folds — "
                "try Easy mode or a simpler model."
            )
    return warnings


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


def piece_bounds(
    piece: UnfoldPiece,
    *,
    include_tabs: bool = False,
) -> tuple[float, float, float, float]:
    """Return min_x, min_y, max_x, max_y for a piece (optionally including tabs)."""
    points = list(piece.polygon)
    if include_tabs:
        for tab in piece.tabs:
            points.extend(tab.polygon)

    if not points:
        return 0.0, 0.0, 0.0, 0.0

    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def piece_polygon_area(piece: UnfoldPiece) -> float:
    """Shoelace area of the piece outline in mm²."""
    if len(piece.polygon) < 3:
        return 0.0
    try:
        return float(Polygon([p.as_tuple() for p in piece.polygon]).area)
    except Exception:
        min_x, min_y, max_x, max_y = piece_bounds(piece)
        return max(0.0, (max_x - min_x) * (max_y - min_y))


def translate_piece(piece: UnfoldPiece, dx: float, dy: float) -> UnfoldPiece:
    """Return a copy of piece with all coordinates translated."""
    return UnfoldPiece(
        id=piece.id,
        face_ids=piece.face_ids,
        label=piece.label,
        has_overlap=piece.has_overlap,
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


def rotate_piece_90(piece: UnfoldPiece) -> UnfoldPiece:
    """Rotate piece 90° counter-clockwise around origin."""
    def rot(p: Point2D) -> Point2D:
        return Point2D(p.y, -p.x)

    return UnfoldPiece(
        id=piece.id,
        face_ids=piece.face_ids,
        label=piece.label,
        has_overlap=piece.has_overlap,
        polygon=[rot(p) for p in piece.polygon],
        tabs=[
            Tab(
                id=tab.id,
                edge_id=tab.edge_id,
                target_piece_id=tab.target_piece_id,
                label=tab.label,
                polygon=[rot(p) for p in tab.polygon],
            )
            for tab in piece.tabs
        ],
        fold_lines=[
            FoldLine(
                id=line.id,
                fold_type=line.fold_type,
                start=rot(line.start),
                end=rot(line.end),
            )
            for line in piece.fold_lines
        ],
        cut_lines=[
            CutLine(
                id=line.id,
                start=rot(line.start),
                end=rot(line.end),
            )
            for line in piece.cut_lines
        ],
    )
