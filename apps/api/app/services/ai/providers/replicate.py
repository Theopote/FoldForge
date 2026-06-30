"""Optional Replicate API provider for real text/image-to-3D models."""

import asyncio
import base64
from collections.abc import Callable
from pathlib import Path

import httpx

from app.config import settings
from app.schemas.model import Style
from app.services.ai.base import GenerationResult, ModelGeneratorProvider
from app.services.ai.prompt_builder import enhance_image_hint, enhance_text_prompt
from app.services.ai.providers.mock import MockModelProvider
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ReplicateModelProvider(ModelGeneratorProvider):
    """
    Replicate-hosted models when API token is configured.

    Provider fallback is opt-in; production AI failures should be visible.
    """

    name = "replicate"

    def __init__(self) -> None:
        self._fallback = MockModelProvider()

    @property
    def is_available(self) -> bool:
        return bool(
            settings.replicate_api_token
            and (settings.replicate_text_model or settings.replicate_image_model)
        )

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
        enhanced = enhance_text_prompt(prompt, style)
        if not settings.replicate_api_token or not settings.replicate_text_model:
            if settings.ai_allow_provider_fallback:
                return await self._fallback.generate_from_text(prompt, style, output_path)
            missing = (
                "REPLICATE_TEXT_MODEL"
                if settings.replicate_api_token
                else "REPLICATE_API_TOKEN"
            )
            raise RuntimeError(f"Replicate text generation requires {missing}.")

        try:
            await self._download_replicate_output(
                model=settings.replicate_text_model,
                input_payload={"prompt": enhanced},
                destination=output_path,
            )
            return GenerationResult(
                model_path=output_path,
                provider=self.name,
                enhanced_prompt=enhanced,
            )
        except Exception as exc:
            if not settings.ai_allow_provider_fallback:
                raise RuntimeError(f"Replicate text generation failed: {exc}") from exc
            logger.warning("Replicate text failed: %s; using mock fallback", exc)
            return await self._fallback.generate_from_text(prompt, style, output_path)

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
        if not settings.replicate_api_token or not settings.replicate_image_model:
            if settings.ai_allow_provider_fallback:
                return await self._fallback.generate_from_image(
                    image_path, style, output_path, hint
                )
            missing = (
                "REPLICATE_IMAGE_MODEL"
                if settings.replicate_api_token
                else "REPLICATE_API_TOKEN"
            )
            raise RuntimeError(f"Replicate image generation requires {missing}.")

        try:
            image_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
            suffix = image_path.suffix.lower().lstrip(".") or "png"
            await self._download_replicate_output(
                model=settings.replicate_image_model,
                input_payload={"image": f"data:image/{suffix};base64,{image_b64}"},
                destination=output_path,
            )
            return GenerationResult(
                model_path=output_path,
                provider=self.name,
                enhanced_prompt=enhanced,
                preview_image_path=image_path,
            )
        except Exception as exc:
            if not settings.ai_allow_provider_fallback:
                raise RuntimeError(f"Replicate image generation failed: {exc}") from exc
            logger.warning("Replicate image failed: %s; using mock fallback", exc)
            return await self._fallback.generate_from_image(
                image_path, style, output_path, hint
            )

    async def _download_replicate_output(
        self,
        model: str,
        input_payload: dict,
        destination: Path,
    ) -> None:
        """Run a Replicate prediction and download the resulting mesh."""
        headers = {
            "Authorization": f"Bearer {settings.replicate_api_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            create = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json={"version": model, "input": input_payload},
            )
            create.raise_for_status()
            prediction = create.json()
            poll_url = prediction["urls"]["get"]
            status = prediction.get("status")

            while status not in ("succeeded", "failed", "canceled"):
                await asyncio.sleep(2)
                poll = await client.get(poll_url, headers=headers)
                poll.raise_for_status()
                body = poll.json()
                status = body.get("status")
                if status == "succeeded":
                    prediction = body
                    break
                if status in ("failed", "canceled"):
                    raise RuntimeError(body.get("error", "Replicate prediction failed"))

            output_url = prediction.get("output")
            if isinstance(output_url, list):
                output_url = output_url[0]
            if not output_url:
                raise RuntimeError("Replicate returned no output URL")

            mesh_response = await client.get(output_url)
            mesh_response.raise_for_status()
            destination.write_bytes(mesh_response.content)
