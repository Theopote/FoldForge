"""Persist user-editable seam sets per project."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import settings as app_settings

SEAM_SET_VERSION = 1


def seam_set_path(project_id: str) -> Path:
    return app_settings.cache_dir / f"{project_id}.seamset.json"


def parse_mesh_edge(raw: str) -> tuple[int, int]:
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) != 2:
        raise ValueError(f"Invalid mesh edge: {raw!r}")
    v0, v1 = int(parts[0]), int(parts[1])
    return (v0, v1) if v0 <= v1 else (v1, v0)


def format_mesh_edge(edge: tuple[int, int]) -> str:
    return f"{edge[0]},{edge[1]}"


def format_seam_list(seams: set[tuple[int, int]]) -> list[str]:
    return [format_mesh_edge(edge) for edge in sorted(seams)]


def load_seam_set(project_id: str) -> set[tuple[int, int]] | None:
    path = seam_set_path(project_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw_edges = payload.get("seams", [])
        return {parse_mesh_edge(str(item)) for item in raw_edges}
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def save_seam_set(project_id: str, seams: set[tuple[int, int]]) -> Path:
    app_settings.cache_dir.mkdir(parents=True, exist_ok=True)
    path = seam_set_path(project_id)
    payload = {
        "version": SEAM_SET_VERSION,
        "seams": format_seam_list(seams),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
