"""Pipeline failures that should surface as client-visible errors."""

from __future__ import annotations

from dataclasses import dataclass


class UnfoldRepairError(Exception):
    """Unfold overlaps remain after auto-repair; export was blocked."""

    def __init__(self, message: str, *, warnings: list[str] | None = None) -> None:
        super().__init__(message)
        self.warnings = warnings or []


class JobCancelledError(Exception):
    """Process job was cancelled by the user."""


@dataclass(frozen=True)
class PieceTooLarge:
    """A papercraft piece cannot fit the printable area at uniform scale."""

    label: str
    width_mm: float
    height_mm: float
    paper_size: str
    usable_width_mm: float
    usable_height_mm: float
    suggested_target_height_mm: float | None = None

    def user_message(self) -> str:
        paper = self.paper_size
        if self.suggested_target_height_mm is not None:
            target = int(round(self.suggested_target_height_mm))
            return (
                f"Piece {self.label} is too large for {paper} "
                f"({self.usable_width_mm:.0f}×{self.usable_height_mm:.0f} mm printable). "
                f"Try A3, Easy mode, or reduce target height to around {target} mm."
            )
        return (
            f"Piece {self.label} is too large for {paper} "
            f"({self.usable_width_mm:.0f}×{self.usable_height_mm:.0f} mm printable). "
            "Try A3, Easy mode, or reduce target height."
        )


class LayoutFitError(Exception):
    """Layout cannot produce a safe printable template at uniform piece scale."""

    def __init__(
        self,
        message: str,
        *,
        pieces: list[PieceTooLarge] | None = None,
        suggestions: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.pieces = pieces or []
        self.suggestions = suggestions or []
        self.warnings = warnings or []

    @classmethod
    def from_oversize_pieces(
        cls,
        pieces: list[PieceTooLarge],
        *,
        extra_suggestions: list[str] | None = None,
    ) -> LayoutFitError:
        suggestions = [
            "Use a larger paper size (e.g. A3 instead of A4).",
            "Reduce target height so all pieces shrink uniformly.",
            "Switch to Easy mode to split the model into smaller patches.",
            "Simplify the source model or remove oversized details.",
        ]
        if extra_suggestions:
            suggestions.extend(extra_suggestions)
        warnings = [piece.user_message() for piece in pieces]
        summary = warnings[0] if len(warnings) == 1 else (
            f"{len(warnings)} piece(s) are too large for the selected paper."
        )
        return cls(summary, pieces=pieces, suggestions=suggestions, warnings=warnings)
