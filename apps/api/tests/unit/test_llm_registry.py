"""LLM provider registry tests."""

from __future__ import annotations

import pytest

from app.config import settings
from app.services.llm.json_utils import parse_llm_json
from app.services.llm.registry import (
    get_llm_provider,
    is_llm_available,
    resolve_llm_provider_name,
)


def test_resolve_llm_provider_auto_prefers_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "auto")
    monkeypatch.setattr(settings, "anthropic_api_key", "anthropic-key")
    monkeypatch.setattr(settings, "openai_api_key", "openai-key")

    assert resolve_llm_provider_name() == "claude"


def test_resolve_llm_provider_auto_falls_back_to_openai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "llm_provider", "auto")
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(settings, "openai_api_key", "openai-key")

    assert resolve_llm_provider_name() == "openai"


def test_resolve_llm_provider_auto_uses_mock_without_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "llm_provider", "auto")
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(settings, "openai_api_key", None)

    assert resolve_llm_provider_name() == "mock"
    assert is_llm_available() is False


def test_explicit_openai_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "openai-key")

    provider = get_llm_provider()
    assert provider.name == "openai"
    assert provider.is_available is True
    assert is_llm_available() is True


def test_parse_llm_json_strips_markdown_fence() -> None:
    payload = parse_llm_json(
        """```json
        {"enhanced_prompt": "fox", "tip": "ok"}
        ```"""
    )
    assert payload["enhanced_prompt"] == "fox"
    assert payload["tip"] == "ok"
