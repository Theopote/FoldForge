"""Parse structured JSON from LLM text output."""

from __future__ import annotations

import json
from typing import Any


def parse_llm_json(raw: str) -> dict[str, Any]:
    """Parse JSON from model output, stripping optional markdown fences."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    return json.loads(cleaned)
