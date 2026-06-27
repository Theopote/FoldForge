"""Quick test for mock AI generation."""

import asyncio
from pathlib import Path

from app.config import settings
from app.schemas.model import Style
from app.services.ai.providers.mock import MockModelProvider


async def main() -> None:
    provider = MockModelProvider()
    output = settings.uploads_dir / "test_phase2.glb"
    result = await provider.generate_from_text(
        "low poly cat",
        Style.LOW_POLY,
        output,
    )
    print("provider:", result.provider)
    print("exists:", result.model_path.exists())
    print("prompt:", result.enhanced_prompt[:60] if result.enhanced_prompt else "")


if __name__ == "__main__":
    asyncio.run(main())
