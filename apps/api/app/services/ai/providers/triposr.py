"""TripoSR provider via Replicate - fast image-to-3D for papercraft."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

from app.config import settings
from app.schemas.model import Style
from app.services.ai.base import GenerationResult, ModelGeneratorProvider
from app.services.ai.http_utils import download_file, image_to_data_uri
from app.services.ai.prompt_builder import enhance_image_hint


class TripoSRProvider(ModelGeneratorProvider):
    """TripoSR on Replicate - image-to-3D only."""

    name = "triposr"

    @property
    def is_available(self) -> bool:
        return bool(settings.replicate_api_token and settings.triposr_replicate_version)

    @property
    def requires_async(self) -> bool:
        return True

    async def generate_from_text(
        self,
        prompt: str,
        style: Style,
        output_path: Path,
        *,
        on_progress: Callable[[int, str], None] | None = None,
    ) -> GenerationResult:
        """Reject text prompts because TripoSR is image-only."""
        raise RuntimeError(
            "TripoSR supports image-to-3D only. Configure Meshy or Replicate text generation."
        )

    async def generate_from_image(
        self,
        image_path: Path,
        style: Style,
        output_path: Path,
        hint: str | None = None,
        *,
        on_progress: Callable[[int, str], None] | None = None,
    ) -> GenerationResult:
        enhanced = enhance_image_hint(hint, style)
        if not self.is_available:
            raise RuntimeError(
                "TripoSR requires REPLICATE_API_TOKEN and TRIPOSR_REPLICATE_VERSION"
            )

        if on_progress:
            on_progress(5, "Submitting TripoSR prediction")

        data_uri = image_to_data_uri(image_path)
        mesh_url = await asyncio.to_thread(
            self._run_replicate_prediction,
            data_uri,
        )

        if on_progress:
            on_progress(90, "Downloading model")

        await download_file(mesh_url, output_path)
        if on_progress:
            on_progress(100, "Complete")

        return GenerationResult(
            model_path=output_path,
            provider=self.name,
            enhanced_prompt=enhanced,
            preview_image_path=image_path,
        )

    def _run_replicate_prediction(self, image_data_uri: str) -> str:
        try:
            import replicate
        except ImportError as exc:
            raise RuntimeError("Install replicate: pip install replicate") from exc

        client = replicate.Client(api_token=settings.replicate_api_token)
        output = client.run(
            settings.triposr_replicate_version,
            input={"image": image_data_uri},
        )
        return self._resolve_output_url(output)

    @staticmethod
    def _resolve_output_url(output: object) -> str:
        if isinstance(output, str):
            return output
        if isinstance(output, list) and output:
            first = output[0]
            if isinstance(first, str):
                return first
        if isinstance(output, dict):
            for key in ("mesh", "model", "glb", "output"):
                value = output.get(key)
                if isinstance(value, str):
                    return value
        raise RuntimeError("TripoSR returned an unexpected output format")
