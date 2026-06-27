"""Convert reference images into relief meshes suitable for papercraft."""

from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageFilter

from app.schemas.model import Style


def image_to_relief_mesh(
    image_path: Path,
    style: Style,
    grid_size: int = 56,
) -> trimesh.Trimesh:
    """
    Build a heightmap relief mesh from an image.

    Works offline without external AI — good for silhouettes and photos.
    Real image-to-3D providers can replace this in production.
    """
    image = Image.open(image_path).convert("RGBA")
    image = _auto_crop_content(image)
    image = image.resize((grid_size, grid_size), Image.Resampling.LANCZOS)

    alpha = np.array(image.split()[-1], dtype=float) / 255.0
    gray = np.array(image.convert("L"), dtype=float) / 255.0
    height = gray * alpha

    height = _apply_style(height, style)
    height = _smooth_heightmap(height)

    return _heightmap_to_mesh(height, scale_xy=2.0, scale_z=_height_scale(style))


def _auto_crop_content(image: Image.Image, padding: int = 8) -> Image.Image:
    """Crop to non-transparent/non-white content bounding box."""
    arr = np.array(image.convert("RGBA"))
    alpha = arr[:, :, 3]
    rgb = arr[:, :, :3]
    mask = (alpha > 16) & (np.mean(rgb, axis=2) < 250)
    if not mask.any():
        return image

    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    top, bottom = max(0, rows[0] - padding), min(image.height, rows[-1] + padding)
    left, right = max(0, cols[0] - padding), min(image.width, cols[-1] + padding)
    return image.crop((left, top, right, bottom))


def _apply_style(height: np.ndarray, style: Style) -> np.ndarray:
    if style == Style.CUTE:
        return np.power(np.clip(height, 0, 1), 0.75)
    if style == Style.GEOMETRIC:
        levels = 5
        return np.round(height * levels) / levels
    return height


def _smooth_heightmap(height: np.ndarray) -> np.ndarray:
    img = Image.fromarray((height * 255).astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
    return np.array(img, dtype=float) / 255.0


def _height_scale(style: Style) -> float:
    if style == Style.CUTE:
        return 0.55
    if style == Style.GEOMETRIC:
        return 0.85
    return 0.7


def _heightmap_to_mesh(
    height: np.ndarray,
    scale_xy: float,
    scale_z: float,
) -> trimesh.Trimesh:
    """Triangulate a regular grid heightmap into a mesh."""
    rows, cols = height.shape
    xs = np.linspace(-scale_xy / 2, scale_xy / 2, cols)
    ys = np.linspace(-scale_xy / 2, scale_xy / 2, rows)
    grid_x, grid_y = np.meshgrid(xs, ys[::-1])

    vertices = np.column_stack([
        grid_x.ravel(),
        height.ravel() * scale_z,
        grid_y.ravel(),
    ])

    faces: list[list[int]] = []

    def vid(r: int, c: int) -> int:
        return r * cols + c

    for r in range(rows - 1):
        for c in range(cols - 1):
            if height[r, c] < 0.05 and height[r, c + 1] < 0.05 and height[r + 1, c] < 0.05:
                continue
            v0, v1, v2, v3 = vid(r, c), vid(r, c + 1), vid(r + 1, c), vid(r + 1, c + 1)
            faces.append([v0, v2, v1])
            faces.append([v1, v2, v3])

    mesh = trimesh.Trimesh(vertices=vertices, faces=np.array(faces))
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals()
    return mesh
