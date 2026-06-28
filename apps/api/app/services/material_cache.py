"""Persist unfold geometry and per-face material colors for fast re-layout."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import settings as app_settings
from app.models.geometry import (
    BakedTriangle,
    CutLine,
    FoldLine,
    Point2D,
    Tab,
    UnfoldPiece,
)
from app.schemas.model import ColorMode, ProjectSettings

CACHE_VERSION = 1


@dataclass
class MaterialCache:
    version: int
    source_fingerprint: str
    geometry_settings_key: str
    color_mode: str
    pieces: list[dict[str, Any]]
    face_colors: dict[str, str] = field(default_factory=dict)

    def matches_geometry(self, source_fingerprint: str, geometry_settings_key: str) -> bool:
        return (
            self.version == CACHE_VERSION
            and self.source_fingerprint == source_fingerprint
            and self.geometry_settings_key == geometry_settings_key
        )


def geometry_settings_key(settings: ProjectSettings) -> str:
    """Settings that affect mesh processing, unfold, tabs, and labels."""
    return "|".join(
        [
            settings.difficulty.value,
            settings.style.value,
            f"{settings.target_height_mm:.3f}",
            "tabs" if settings.add_tabs else "notabs",
            "nums" if settings.add_numbers else "nonums",
        ]
    )


def compute_source_fingerprint(source_path: Path) -> str:
    digest = hashlib.sha256()
    with source_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_path(project_id: str) -> Path:
    return app_settings.cache_dir / f"{project_id}.material.json"


def load_material_cache(project_id: str) -> MaterialCache | None:
    if not app_settings.material_cache_enabled:
        return None

    path = cache_path(project_id)
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return MaterialCache(
            version=int(payload.get("version", 0)),
            source_fingerprint=str(payload["sourceFingerprint"]),
            geometry_settings_key=str(payload["geometrySettingsKey"]),
            color_mode=str(payload.get("colorMode", ColorMode.LINE_ART.value)),
            pieces=list(payload.get("pieces", [])),
            face_colors={
                str(key): str(value)
                for key, value in dict(payload.get("faceColors", {})).items()
            },
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def save_material_cache(
    project_id: str,
    *,
    source_path: Path,
    settings: ProjectSettings,
    pieces: list[UnfoldPiece],
    face_colors: dict[int, str] | None = None,
) -> None:
    if not app_settings.material_cache_enabled:
        return

    app_settings.cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": CACHE_VERSION,
        "sourceFingerprint": compute_source_fingerprint(source_path),
        "geometrySettingsKey": geometry_settings_key(settings),
        "colorMode": settings.color_mode.value,
        "pieces": [serialize_piece(piece) for piece in pieces],
        "faceColors": {
            str(face_idx): fill
            for face_idx, fill in sorted((face_colors or {}).items())
        },
    }
    cache_path(project_id).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def try_restore_geometry_cache(
    project_id: str,
    source_path: Path,
    settings: ProjectSettings,
) -> tuple[list[UnfoldPiece] | None, MaterialCache | None]:
    cache = load_material_cache(project_id)
    if cache is None:
        return None, None

    source_fp = compute_source_fingerprint(source_path)
    geom_key = geometry_settings_key(settings)
    if not cache.matches_geometry(source_fp, geom_key):
        return None, cache

    return deserialize_pieces(cache.pieces), cache


def face_color_cache_from_material(cache: MaterialCache | None) -> dict[int, str] | None:
    if cache is None or not cache.face_colors:
        return None
    return {int(face_idx): fill for face_idx, fill in cache.face_colors.items()}


def pieces_have_baked_color(pieces: list[UnfoldPiece]) -> bool:
    return any(piece.baked_triangles for piece in pieces)


def clear_baked_triangles(pieces: list[UnfoldPiece]) -> None:
    for piece in pieces:
        piece.baked_triangles = []


def apply_color_mode_to_cached_pieces(
    pieces: list[UnfoldPiece],
    settings: ProjectSettings,
    cache: MaterialCache | None,
) -> bool:
    """
    Adjust baked triangles on restored pieces for the requested color mode.

    Returns True when a color rebake is still required.
    """
    if settings.color_mode == ColorMode.LINE_ART:
        clear_baked_triangles(pieces)
        return False

    if pieces_have_baked_color(pieces):
        return False

    if cache is not None and cache.face_colors:
        return True

    return True


def serialize_piece(piece: UnfoldPiece) -> dict[str, Any]:
    return {
        "id": piece.id,
        "faceIds": piece.face_ids,
        "polygon": [_point_to_dict(point) for point in piece.polygon],
        "tabs": [
            {
                "id": tab.id,
                "edgeId": tab.edge_id,
                "polygon": [_point_to_dict(point) for point in tab.polygon],
                "targetPieceId": tab.target_piece_id,
                "label": tab.label,
            }
            for tab in piece.tabs
        ],
        "foldLines": [
            {
                "id": line.id,
                "start": _point_to_dict(line.start),
                "end": _point_to_dict(line.end),
                "foldType": line.fold_type,
            }
            for line in piece.fold_lines
        ],
        "cutLines": [
            {
                "id": line.id,
                "start": _point_to_dict(line.start),
                "end": _point_to_dict(line.end),
                "meshEdge": [int(v) for v in line.mesh_edge] if line.mesh_edge else None,
            }
            for line in piece.cut_lines
        ],
        "label": piece.label,
        "hasOverlap": piece.has_overlap,
        "cutOutline": (
            [_point_to_dict(point) for point in piece.cut_outline]
            if piece.cut_outline
            else None
        ),
        "bakedTriangles": [
            {
                "a": _point_to_dict(triangle.a),
                "b": _point_to_dict(triangle.b),
                "c": _point_to_dict(triangle.c),
                "fill": triangle.fill,
            }
            for triangle in piece.baked_triangles
        ],
    }


def deserialize_pieces(payload: list[dict[str, Any]]) -> list[UnfoldPiece]:
    return [deserialize_piece(item) for item in payload]


def deserialize_piece(payload: dict[str, Any]) -> UnfoldPiece:
    return UnfoldPiece(
        id=str(payload["id"]),
        face_ids=[int(face_id) for face_id in payload["faceIds"]],
        polygon=[_point_from_dict(item) for item in payload["polygon"]],
        tabs=[
            Tab(
                id=str(tab["id"]),
                edge_id=str(tab["edgeId"]),
                polygon=[_point_from_dict(point) for point in tab["polygon"]],
                target_piece_id=str(tab["targetPieceId"]),
                label=str(tab.get("label", "")),
            )
            for tab in payload.get("tabs", [])
        ],
        fold_lines=[
            FoldLine(
                id=str(line["id"]),
                start=_point_from_dict(line["start"]),
                end=_point_from_dict(line["end"]),
                fold_type=line["foldType"],
            )
            for line in payload.get("foldLines", [])
        ],
        cut_lines=[
            CutLine(
                id=str(line["id"]),
                start=_point_from_dict(line["start"]),
                end=_point_from_dict(line["end"]),
                mesh_edge=tuple(line["meshEdge"]) if line.get("meshEdge") else None,
            )
            for line in payload.get("cutLines", [])
        ],
        label=str(payload.get("label", "")),
        has_overlap=bool(payload.get("hasOverlap", False)),
        cut_outline=(
            [_point_from_dict(point) for point in payload["cutOutline"]]
            if payload.get("cutOutline")
            else None
        ),
        baked_triangles=[
            BakedTriangle(
                a=_point_from_dict(triangle["a"]),
                b=_point_from_dict(triangle["b"]),
                c=_point_from_dict(triangle["c"]),
                fill=str(triangle["fill"]),
            )
            for triangle in payload.get("bakedTriangles", [])
        ],
    )


def _point_to_dict(point: Point2D) -> dict[str, float]:
    return {"x": point.x, "y": point.y}


def _point_from_dict(payload: dict[str, float]) -> Point2D:
    return Point2D(x=float(payload["x"]), y=float(payload["y"]))
