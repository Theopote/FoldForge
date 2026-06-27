"""Abstract interface for AI 3D model generation providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from app.schemas.model import Style


@dataclass
class GenerationResult:
    """Output of an AI model generation request."""

    model_path: Path
    provider: str
    enhanced_prompt: str | None = None
    preview_image_path: Path | None = None


class ModelGeneratorProvider(ABC):
    """Pluggable provider for text/image → 3D mesh generation."""

    name: str = "base"

    @abstractmethod
    async def generate_from_text(
        self,
        prompt: str,
        style: Style,
        output_path: Path,
    ) -> GenerationResult:
        """Generate a 3D model file from a text prompt."""

    @abstractmethod
    async def generate_from_image(
        self,
        image_path: Path,
        style: Style,
        output_path: Path,
        hint: str | None = None,
    ) -> GenerationResult:
        """Generate a 3D model file from a reference image."""

    @property
    def is_available(self) -> bool:
        """Whether this provider can accept requests right now."""
        return True
