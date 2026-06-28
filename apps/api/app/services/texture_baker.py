"""Spike: bake source mesh surface color onto 2D unfold triangles."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh
from PIL import Image

from app.models.geometry import BakedTriangle, Point2D, UnfoldPiece
from app.services.seam_generator import EdgeDihedralData
from app.services.unfolder import compute_unfold_vertex_map


@dataclass(frozen=True)
class TextureBakeStats:
    pieces_with_color: int
    triangle_count: int
    used_vertex_colors: bool
    used_texture_map: bool
    used_face_color_cache: bool
    face_colors: dict[int, str]


def bake_piece_textures(
    mesh: trimesh.Trimesh,
    pieces: list[UnfoldPiece],
    dihedral: EdgeDihedralData,
    *,
    face_color_cache: dict[int, str] | None = None,
) -> tuple[list[UnfoldPiece], TextureBakeStats]:
    """
    Sample mesh surface color for each unfold face and attach SVG-ready triangles.

    Supports vertex colors and GLB/GLTF texture maps. Meshes without color data
    receive a neutral gray fill so ``colorMode=color`` still renders consistently.

    When ``face_color_cache`` is provided, mesh sampling is skipped for cached faces.
    """
    sampler = _MeshColorSampler(mesh) if face_color_cache is None else None
    pieces_with_color = 0
    triangle_count = 0
    used_face_color_cache = False
    face_colors: dict[int, str] = dict(face_color_cache or {})

    for piece in pieces:
        if not piece.face_ids:
            continue

        vertex_2d, _ = compute_unfold_vertex_map(mesh, piece.face_ids, dihedral)
        baked: list[BakedTriangle] = []

        for face_idx in piece.face_ids:
            triangle = _bake_face_triangle(
                mesh,
                face_idx,
                vertex_2d,
                sampler,
                face_color_cache=face_colors if face_color_cache is not None else None,
            )
            if triangle is not None:
                baked.append(triangle)
                face_colors[int(face_idx)] = triangle.fill
                if face_color_cache is not None and int(face_idx) in face_color_cache:
                    used_face_color_cache = True

        piece.baked_triangles = baked
        if baked:
            pieces_with_color += 1
            triangle_count += len(baked)

    return pieces, TextureBakeStats(
        pieces_with_color=pieces_with_color,
        triangle_count=triangle_count,
        used_vertex_colors=bool(sampler and sampler.used_vertex_colors),
        used_texture_map=bool(sampler and sampler.used_texture_map),
        used_face_color_cache=used_face_color_cache,
        face_colors=face_colors,
    )


def _bake_face_triangle(
    mesh: trimesh.Trimesh,
    face_idx: int,
    vertex_2d: dict[int, Point2D],
    sampler: "_MeshColorSampler | None",
    *,
    face_color_cache: dict[int, str] | None = None,
) -> BakedTriangle | None:
    face = mesh.faces[face_idx]
    points: list[Point2D] = []
    colors: list[tuple[int, int, int]] = []
    cached_fill = face_color_cache.get(int(face_idx)) if face_color_cache else None

    for vertex_idx in face:
        vi = int(vertex_idx)
        if vi not in vertex_2d:
            return None
        points.append(vertex_2d[vi])
        if cached_fill is None:
            if sampler is None:
                return None
            colors.append(sampler.color_at_vertex(vi, face_idx))

    if len(points) != 3:
        return None

    fill = cached_fill if cached_fill is not None else _rgb_to_hex(_average_rgb(colors))
    return BakedTriangle(a=points[0], b=points[1], c=points[2], fill=fill)


class _MeshColorSampler:
    """Resolve RGB samples from vertex colors or a texture map."""

    def __init__(self, mesh: trimesh.Trimesh) -> None:
        self._mesh = mesh
        self.used_vertex_colors = False
        self.used_texture_map = False
        self._vertex_colors = _read_vertex_colors(mesh)
        self._texture = _read_texture_sampler(mesh)
        if self._vertex_colors is not None:
            self.used_vertex_colors = True
        elif self._texture is not None:
            self.used_texture_map = True

    def color_at_vertex(self, vertex_idx: int, face_idx: int) -> tuple[int, int, int]:
        if self._vertex_colors is not None:
            rgba = self._vertex_colors[vertex_idx]
            return int(rgba[0]), int(rgba[1]), int(rgba[2])

        if self._texture is not None:
            uv, image = self._texture
            if vertex_idx < len(uv):
                u, v = float(uv[vertex_idx][0]), float(uv[vertex_idx][1])
                return _sample_texture_pixel(image, u, v)

        return _face_normal_tint(_face_normal(self._mesh, face_idx))


def _read_vertex_colors(mesh: trimesh.Trimesh) -> np.ndarray | None:
    visual = mesh.visual
    colors = getattr(visual, "vertex_colors", None)
    if colors is None or len(colors) != len(mesh.vertices):
        return None
    arr = np.asarray(colors)
    if arr.ndim != 2 or arr.shape[1] < 3:
        return None
    if np.max(arr) <= 1.0:
        arr = (arr[:, :4] if arr.shape[1] >= 4 else np.column_stack([arr, np.ones(len(arr))])) * 255.0
    return arr.astype(np.uint8)


def _read_texture_sampler(mesh: trimesh.Trimesh) -> tuple[np.ndarray, Image.Image] | None:
    visual = mesh.visual
    material = getattr(visual, "material", None)
    image = getattr(material, "image", None) if material is not None else None
    uv = getattr(visual, "uv", None)
    if image is None or uv is None or len(uv) != len(mesh.vertices):
        return None
    if isinstance(image, Image.Image):
        return np.asarray(uv, dtype=np.float64), image.convert("RGB")
    return None


def _sample_texture_pixel(image: Image.Image, u: float, v: float) -> tuple[int, int, int]:
    u = u % 1.0
    v = v % 1.0
    x = min(image.width - 1, max(0, int(round(u * (image.width - 1)))))
    y = min(image.height - 1, max(0, int(round((1.0 - v) * (image.height - 1)))))
    r, g, b = image.getpixel((x, y))
    return int(r), int(g), int(b)


def _face_normal(mesh: trimesh.Trimesh, face_idx: int) -> np.ndarray:
    vertices = mesh.vertices[mesh.faces[face_idx]]
    edge_a = vertices[1] - vertices[0]
    edge_b = vertices[2] - vertices[0]
    normal = np.cross(edge_a, edge_b)
    length = float(np.linalg.norm(normal))
    if length < 1e-12:
        return np.array([0.0, 0.0, 1.0])
    return normal / length


def _face_normal_tint(normal: np.ndarray) -> tuple[int, int, int]:
    """Neutral fallback when no mesh color data exists."""
    r = int(np.clip((normal[0] * 0.5 + 0.5) * 220 + 20, 0, 255))
    g = int(np.clip((normal[1] * 0.5 + 0.5) * 220 + 20, 0, 255))
    b = int(np.clip((normal[2] * 0.5 + 0.5) * 220 + 20, 0, 255))
    return r, g, b


def _average_rgb(colors: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    if not colors:
        return 180, 180, 180
    r = sum(color[0] for color in colors) // len(colors)
    g = sum(color[1] for color in colors) // len(colors)
    b = sum(color[2] for color in colors) // len(colors)
    return r, g, b


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
