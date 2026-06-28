"""Server-Sent Events helpers for job progress streams."""

from __future__ import annotations

import json
from typing import Any


def format_sse_data(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"


def format_sse_comment(text: str) -> str:
    return f": {text}\n\n"
