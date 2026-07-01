"""AI seam advisor tests."""

from __future__ import annotations

import json

import pytest
import trimesh

from app.config import settings
from app.schemas.model import Difficulty
from app.services.ai.ai_seam_advisor import _describe_mesh, generate_seam_hints
from app.services.seam_generator import compute_edge_dihedral_angles


def test_describe_mesh_handles_empty_pieces() -> None:
    mesh = trimesh.creation.box()
    dihedral = compute_edge_dihedral_angles(mesh)
    payload = json.loads(_describe_mesh(mesh, [], dihedral, "cube"))

    assert payload["total_faces"] == len(mesh.faces)
    assert payload["total_pieces"] == 0
    assert payload["pieces"] == []


@pytest.mark.asyncio
async def test_generate_seam_hints_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "claude_seam_advisor_enabled", False)
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")

    mesh = trimesh.creation.box()
    dihedral = compute_edge_dihedral_angles(mesh)
    result = await generate_seam_hints(mesh, [], dihedral, Difficulty.STANDARD, "cube")

    assert result is None


@pytest.mark.asyncio
async def test_generate_seam_hints_parses_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "claude_seam_advisor_enabled", True)
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")

    async def fake_complete(system: str, user: str, **kwargs: object) -> dict:
        _ = (system, user, kwargs)
        return {
            "model_interpretation": "A simple cube model",
            "structural_notes": "Six flat faces",
            "suggestions": [],
            "assembly_order_hint": "先粘底部",
        }

    monkeypatch.setattr(
        "app.services.ai.ai_seam_advisor.complete_json",
        fake_complete,
    )

    mesh = trimesh.creation.box()
    dihedral = compute_edge_dihedral_angles(mesh)
    result = await generate_seam_hints(mesh, [], dihedral, Difficulty.STANDARD, "cube")

    assert result is not None
    assert result["model_interpretation"] == "A simple cube model"
    assert result["assembly_order_hint"] == "先粘底部"
