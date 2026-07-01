"""AI instruction writer tests."""

from __future__ import annotations

import pytest

from app.schemas.model import Difficulty, PaperSize, ProjectSettings, Style
from app.services.instruction_generator import (
    _apply_ai_instructions,
    build_instruction_document,
    build_instruction_document_async,
)


@pytest.mark.asyncio
async def test_generate_ai_instructions_returns_none_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(settings, "claude_instructions_enabled", True)

    doc = await build_instruction_document_async(
        "Cube",
        ProjectSettings(),
        {"pieces": 6, "pages": 1, "craftability": 80, "level": "good"},
        [],
        pieces=[],
        pages=[],
    )

    static = build_instruction_document(
        "Cube",
        ProjectSettings(),
        {"pieces": 6, "pages": 1, "craftability": 80, "level": "good"},
        [],
        pieces=[],
        pages=[],
    )
    assert doc.sections == static.sections


def test_apply_ai_instructions_replaces_target_sections() -> None:
    static = build_instruction_document(
        "Fox",
        ProjectSettings(
            paperSize=PaperSize.A4,
            difficulty=Difficulty.EASY,
            style=Style.LOW_POLY,
        ),
        {"pieces": 8, "pages": 1, "craftability": 90, "level": "excellent"},
        [],
        pieces=[],
        pages=[],
    )

    updated = _apply_ai_instructions(
        static,
        {
            "assembly_steps_en": ["Step 1: cut ears", "Step 2: glue body"],
            "chinese_tips": ["提示一", "提示二", "提示三", "提示四"],
            "difficulty_note": "Great for beginners.",
        },
    )

    section_map = dict(updated.sections)
    assert section_map["Assembly steps"][0] == "📋 Great for beginners."
    assert section_map["Assembly steps"][1] == "Step 1: cut ears"
    assert section_map["中文提示"] == ("提示一", "提示二", "提示三", "提示四")


@pytest.mark.asyncio
async def test_generate_ai_instructions_uses_claude_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(settings, "claude_instructions_enabled", True)

    async def fake_complete(system: str, user: str, **kwargs: object) -> dict:
        _ = (system, user, kwargs)
        return {
            "assembly_steps_en": ["Step 1: fold base"],
            "chinese_tips": ["一", "二", "三", "四"],
            "difficulty_note": "Easy kit.",
        }

    monkeypatch.setattr(
        "app.services.ai.ai_instruction_writer.complete_json",
        fake_complete,
    )

    doc = await build_instruction_document_async(
        "House",
        ProjectSettings(),
        {"pieces": 4, "pages": 1, "craftability": 75, "level": "good"},
        [],
        pieces=[],
        pages=[],
    )

    section_map = dict(doc.sections)
    assert "Step 1: fold base" in section_map["Assembly steps"]
    assert section_map["中文提示"] == ("一", "二", "三", "四")
