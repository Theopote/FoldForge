"""Meshy.ai production provider — text/image to 3D with polling."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

import httpx

from app.config import settings
from app.schemas.model import Style
from app.services.ai.base import GenerationResult, ModelGeneratorProvider
from app.services.ai.http_utils import download_file, image_to_data_uri
from app.services.ai.prompt_builder import enhance_image_hint, enhance_text_prompt

MESHY_BASE = "https://api.meshy.ai"


class MeshyProvider(ModelGeneratorProvider):
    """Meshy REST API — preview/low-poly geometry for papercraft."""

    name = "meshy"

    @property
    def is_available(self) -> bool:
        return bool(settings.meshy_api_key)

    @property
    def requires_async(self) -> bool:
        return True

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.meshy_api_key}",
            "Content-Type": "application/json",
        }

    async def generate_from_text(
        self,
        prompt: str,
        style: Style,
        output_path: Path,
        *,
        on_progress: Callable[[int, str], None] | None = None,
    ) -> GenerationResult:
        enhanced = enhance_text_prompt(prompt, style)
        if on_progress:
            on_progress(5, "Submitting Meshy text-to-3D preview task")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{MESHY_BASE}/openapi/v2/text-to-3d",
                headers=self._headers(),
                json={
                    "mode": "preview",
                    "prompt": enhanced[:600],
                    "model_type": "lowpoly",
                    "should_remesh": True,
                    "decimation_mode": 4,
                },
            )
            response.raise_for_status()
            task_id = response.json()["result"]

        if on_progress:
            on_progress(15, "Meshy generating geometry")

        task = await self._poll_text_task(task_id, on_progress=on_progress)
        glb_url = self._extract_glb_url(task)
        if on_progress:
            on_progress(90, "Downloading model")

        await download_file(glb_url, output_path)
        if on_progress:
            on_progress(100, "Complete")

        return GenerationResult(
            model_path=output_path,
            provider=self.name,
            enhanced_prompt=enhanced,
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
        data_uri = image_to_data_uri(image_path)
        if on_progress:
            on_progress(5, "Submitting Meshy image-to-3D task")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{MESHY_BASE}/openapi/v1/image-to-3d",
                headers=self._headers(),
                json={
                    "image_url": data_uri,
                    "model_type": "lowpoly",
                    "should_texture": False,
                    "target_formats": ["glb"],
                },
            )
            response.raise_for_status()
            task_id = response.json()["result"]

        if on_progress:
            on_progress(15, "Meshy generating geometry")

        task = await self._poll_image_task(task_id, on_progress=on_progress)
        glb_url = self._extract_glb_url(task)
        if on_progress:
            on_progress(90, "Downloading model")

        await download_file(glb_url, output_path)
        if on_progress:
            on_progress(100, "Complete")

        return GenerationResult(
            model_path=output_path,
            provider=self.name,
            enhanced_prompt=enhanced,
            preview_image_path=image_path,
        )

    async def _poll_text_task(
        self,
        task_id: str,
        *,
        on_progress: Callable[[int, str], None] | None = None,
    ) -> dict:
        return await self._poll_task(
            f"{MESHY_BASE}/openapi/v2/text-to-3d/{task_id}",
            on_progress=on_progress,
        )

    async def _poll_image_task(
        self,
        task_id: str,
        *,
        on_progress: Callable[[int, str], None] | None = None,
    ) -> dict:
        return await self._poll_task(
            f"{MESHY_BASE}/openapi/v1/image-to-3d/{task_id}",
            on_progress=on_progress,
        )

    async def _poll_task(
        self,
        url: str,
        *,
        on_progress: Callable[[int, str], None] | None = None,
    ) -> dict:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + settings.meshy_poll_timeout_sec
        async with httpx.AsyncClient(timeout=30.0) as client:
            while loop.time() < deadline:
                response = await client.get(url, headers=self._headers())
                response.raise_for_status()
                data = response.json()
                status = data.get("status", "PENDING")
                progress = int(data.get("progress", 0) or 0)

                if on_progress:
                    mapped = min(85, 15 + int(progress * 0.7))
                    on_progress(mapped, f"Meshy {status.lower()} ({progress}%)")

                if status == "SUCCEEDED":
                    return data
                if status in ("FAILED", "CANCELED"):
                    raise RuntimeError(
                        data.get("task_error", {}).get("message")
                        or f"Meshy task {status.lower()}"
                    )

                await asyncio.sleep(settings.meshy_poll_interval_sec)

        raise TimeoutError("Meshy generation timed out")

    @staticmethod
    def _extract_glb_url(task: dict) -> str:
        model_urls = task.get("model_urls") or {}
        if isinstance(model_urls, dict):
            glb = model_urls.get("glb")
            if glb:
                return glb
        raise RuntimeError("Meshy task succeeded but no GLB URL was returned")
