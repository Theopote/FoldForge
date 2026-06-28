"""Cooperative cancellation checks for long-running pipeline stages."""

from __future__ import annotations

from typing import Protocol

from app.services.pipeline_errors import JobCancelledError


class CancelCheck(Protocol):
    def __call__(self) -> bool: ...


def check_cancelled(cancel_check: CancelCheck | None) -> None:
    if cancel_check is not None and cancel_check():
        raise JobCancelledError("Processing cancelled.")
