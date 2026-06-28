"""Pipeline failures that should surface as client-visible errors."""


class UnfoldRepairError(Exception):
    """Unfold overlaps remain after auto-repair; export was blocked."""

    def __init__(self, message: str, *, warnings: list[str] | None = None) -> None:
        super().__init__(message)
        self.warnings = warnings or []
