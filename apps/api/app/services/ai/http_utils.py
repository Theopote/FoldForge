"""Shared HTTP helpers for AI providers."""

from pathlib import Path

import httpx


async def download_file(url: str, destination: Path, timeout: float = 300.0) -> None:
    """Download a remote file to a local path."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        destination.write_bytes(response.content)


def image_to_data_uri(image_path: Path) -> str:
    """Encode a local image as a base64 data URI for Meshy/Replicate APIs."""
    import base64
    import mimetypes

    mime, _ = mimetypes.guess_type(image_path.name)
    mime = mime or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"
