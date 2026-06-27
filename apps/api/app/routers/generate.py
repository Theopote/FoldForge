"""AI text/image → 3D model generation endpoints."""

from pathlib import Path

import aiofiles
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.schemas.generate import AiProviderInfo, GenerateFromTextRequest, GenerateModelResponse
from app.schemas.model import ProjectStatus, SourceType, Style
from app.services.ai.registry import get_model_provider, list_providers
from app.services.project_store import project_store
from app.utils.file_utils import build_storage_url, generate_project_id

router = APIRouter()

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@router.get("/ai/providers", response_model=list[AiProviderInfo])
async def get_ai_providers() -> list[AiProviderInfo]:
    """List available AI generation providers and which is active."""
    return [AiProviderInfo(**item) for item in list_providers()]


@router.post("/generate-from-text", response_model=GenerateModelResponse)
async def generate_from_text(request: GenerateFromTextRequest) -> GenerateModelResponse:
    """
    Generate a papercraft-friendly 3D model from a text description.

    Uses the configured AI provider (mock offline, Replicate when token set).
    """
    provider = get_model_provider()
    project_id = generate_project_id()
    output_path = settings.uploads_dir / f"{project_id}.glb"

    result = await provider.generate_from_text(
        prompt=request.prompt,
        style=request.style,
        output_path=output_path,
    )

    if not result.model_path.exists():
        raise HTTPException(status_code=500, detail="Model generation failed.")

    name = request.name or _name_from_prompt(request.prompt)
    source_url = build_storage_url(Path("uploads") / output_path.name)

    project_store.create(
        project_id=project_id,
        name=name,
        source_type=SourceType.TEXT_TO_3D,
        source_file_url=source_url,
        status=ProjectStatus.UPLOADED,
        source_prompt=request.prompt,
        ai_provider=result.provider,
        enhanced_prompt=result.enhanced_prompt,
    )

    return GenerateModelResponse(
        projectId=project_id,
        sourceType=SourceType.TEXT_TO_3D,
        sourceFileUrl=source_url,
        sourcePrompt=request.prompt,
        aiProvider=result.provider,
        enhancedPrompt=result.enhanced_prompt,
        status=ProjectStatus.UPLOADED,
    )


@router.post("/generate-from-image", response_model=GenerateModelResponse)
async def generate_from_image(
    file: UploadFile = File(...),
    style: Style = Form(default=Style.LOW_POLY),
    hint: str | None = Form(default=None),
    name: str | None = Form(default=None),
) -> GenerateModelResponse:
    """
    Generate a 3D model from a reference image (photo, sketch, screenshot).

    Saves the reference image and produces a GLB mesh for the papercraft pipeline.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Image filename is required.")

    extension = Path(file.filename).suffix.lower()
    if extension not in IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(IMAGE_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Unsupported image type. Allowed: {allowed}")

    content = await file.read()
    max_bytes = settings.max_image_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large. Maximum is {settings.max_image_size_mb} MB.",
        )

    project_id = generate_project_id()
    image_path = settings.uploads_dir / f"{project_id}_ref{extension}"
    output_path = settings.uploads_dir / f"{project_id}.glb"

    async with aiofiles.open(image_path, "wb") as output:
        await output.write(content)

    provider = get_model_provider()
    result = await provider.generate_from_image(
        image_path=image_path,
        style=style,
        output_path=output_path,
        hint=hint,
    )

    if not result.model_path.exists():
        raise HTTPException(status_code=500, detail="Model generation failed.")

    source_url = build_storage_url(Path("uploads") / output_path.name)
    image_url = build_storage_url(Path("uploads") / image_path.name)
    project_name = name or Path(file.filename).stem

    project_store.create(
        project_id=project_id,
        name=project_name,
        source_type=SourceType.IMAGE_TO_3D,
        source_file_url=source_url,
        status=ProjectStatus.UPLOADED,
        source_image_url=image_url,
        source_prompt=hint,
        ai_provider=result.provider,
        enhanced_prompt=result.enhanced_prompt,
    )

    return GenerateModelResponse(
        projectId=project_id,
        sourceType=SourceType.IMAGE_TO_3D,
        sourceFileUrl=source_url,
        sourceImageUrl=image_url,
        sourcePrompt=hint,
        aiProvider=result.provider,
        enhancedPrompt=result.enhanced_prompt,
        status=ProjectStatus.UPLOADED,
    )


def _name_from_prompt(prompt: str) -> str:
    """Derive a short project name from the user prompt."""
    cleaned = prompt.strip()[:48]
    return cleaned if cleaned else "AI Model"
