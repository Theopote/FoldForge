"""Offline mock provider — procedural text + heightmap image generation."""

from pathlib import Path

from app.schemas.model import Style
from app.services.ai.base import GenerationResult, ModelGeneratorProvider
from app.services.ai.heightmap import image_to_relief_mesh
from app.services.ai.prompt_builder import enhance_image_hint, enhance_text_prompt
from app.services.ai.procedural import generate_procedural_mesh


class MockModelProvider(ModelGeneratorProvider):
    """
    Local generation without external API keys.

    Text → keyword-based procedural meshes.
    Image → heightmap relief mesh.
    """

    name = "mock"

    async def generate_from_text(
        self,
        prompt: str,
        style: Style,
        output_path: Path,
    ) -> GenerationResult:
        enhanced = enhance_text_prompt(prompt, style)
        mesh = generate_procedural_mesh(enhanced, style)
        mesh.export(output_path)
        return GenerationResult(model_path=output_path, provider=self.name, enhanced_prompt=enhanced)

    async def generate_from_image(
        self,
        image_path: Path,
        style: Style,
        output_path: Path,
        hint: str | None = None,
    ) -> GenerationResult:
        enhanced = enhance_image_hint(hint, style)
        mesh = image_to_relief_mesh(image_path, style)
        mesh.export(output_path)
        return GenerationResult(
            model_path=output_path,
            provider=self.name,
            enhanced_prompt=enhanced,
            preview_image_path=image_path,
        )
