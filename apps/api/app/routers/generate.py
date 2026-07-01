"""AI text/image → 3D model generation endpoints."""

import io
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.schemas.generate import (
    AiProviderInfo,
    EnhancePromptRequest,
    EnhancePromptResponse,
    GenerateFromTextRequest,
    GenerateModelResponse,
    LlmProviderInfo,
)
from app.schemas.generation_job import GenerationJob, GenerationJobResponse, JobType
from app.schemas.job import JobStatus
from app.schemas.model import Difficulty, ProjectStatus, SourceType, Style
from app.services.ai.generation_queue import generation_queue
from app.services.ai.job_response import build_generation_job_response
from app.services.ai.job_store import generation_job_store
from app.services.ai.prompt_builder import enhance_text_prompt
from app.services.ai.rate_limit import enforce_ai_generation_rate_limit
from app.services.ai.registry import get_model_provider, list_providers, should_use_async_queue
from app.services.llm import list_llm_providers
from app.services.project_store import project_store
from app.utils.file_utils import build_storage_url, generate_project_id, read_upload_with_limit

router = APIRouter()

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@router.get("/ai/providers", response_model=list[AiProviderInfo])
async def get_ai_providers() -> list[AiProviderInfo]:
    """List available AI generation providers and which is active."""
    return [AiProviderInfo(**item) for item in list_providers()]


@router.get("/llm/providers", response_model=list[LlmProviderInfo])
async def get_llm_providers() -> list[LlmProviderInfo]:
    """List available LLM providers for instructions, prompt enhance, and seam advisor."""
    return [LlmProviderInfo(**item) for item in list_llm_providers()]


@router.post("/ai/enhance-prompt", response_model=EnhancePromptResponse)
async def enhance_prompt_endpoint(request: EnhancePromptRequest) -> EnhancePromptResponse:
    """
    Use Claude to refine a user's rough idea into an optimised Meshy prompt.
    Returns a static fallback when Claude is not configured.
    """
    from app.config import settings as app_settings
    from app.services.llm import is_llm_available

    if not app_settings.claude_prompt_enhance_enabled or not is_llm_available():
        enhanced = enhance_text_prompt(request.prompt, request.style)
        return EnhancePromptResponse(
            enhancedPrompt=enhanced,
            recommendedStyle=request.style,
            recommendedDifficulty=request.difficulty,
            tip="请先配置 LLM API Key（ANTHROPIC_API_KEY 或 OPENAI_API_KEY）以启用 AI 优化",
            available=False,
        )

    from app.services.ai.prompt_enhancer import enhance_prompt

    try:
        result = await enhance_prompt(
            request.prompt,
            request.style,
            request.difficulty,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Prompt enhancement failed: {exc}") from exc

    recommended_style = request.style
    style_value = result.get("recommended_style")
    if isinstance(style_value, str):
        try:
            recommended_style = Style(style_value)
        except ValueError:
            recommended_style = request.style

    recommended_difficulty = request.difficulty
    difficulty_value = result.get("recommended_difficulty")
    if isinstance(difficulty_value, str):
        try:
            recommended_difficulty = Difficulty(difficulty_value)
        except ValueError:
            recommended_difficulty = request.difficulty

    return EnhancePromptResponse(
        enhancedPrompt=str(result.get("enhanced_prompt", request.prompt)),
        recommendedStyle=recommended_style,
        recommendedDifficulty=recommended_difficulty,
        tip=str(result.get("tip", "")),
        available=True,
    )


@router.get("/generation-jobs/{job_id}", response_model=GenerationJobResponse)
async def get_generation_job(job_id: str) -> GenerationJobResponse:
    """Poll async generation job status and result URLs."""
    job = generation_job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found.")

    return build_generation_job_response(job)


@router.post("/generate-from-text", response_model=GenerateModelResponse)
async def generate_from_text(http_request: Request, request: GenerateFromTextRequest):
    """
    Generate a papercraft-friendly 3D model from a text description.

    Production providers (Meshy, TripoSR, Replicate) return 202 + jobId for polling.
    Mock runs synchronously unless AI_ASYNC_FOR_MOCK=true.
    """
    provider = get_model_provider("text")
    _ensure_provider_can_run(provider, "text")
    enforce_ai_generation_rate_limit(http_request, provider.name)
    project_id = generate_project_id()
    output_path = settings.uploads_dir / f"{project_id}.glb"
    name = request.name or _name_from_prompt(request.prompt)

    if should_use_async_queue(provider):
        return await _enqueue_text_job(
            project_id=project_id,
            name=name,
            prompt=request.prompt,
            style=request.style,
            output_path=output_path,
            provider_name=provider.name,
        )

    try:
        result = await provider.generate_from_text(
            prompt=request.prompt,
            style=request.style,
            output_path=output_path,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not result.model_path.exists():
        raise HTTPException(status_code=500, detail="Model generation failed.")

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
        async_mode=False,
    )


@router.post("/generate-from-image", response_model=GenerateModelResponse)
async def generate_from_image(
    http_request: Request,
    file: UploadFile = File(...),
    style: Style = Form(default=Style.LOW_POLY),
    hint: str | None = Form(default=None),
    name: str | None = Form(default=None),
):
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

    max_bytes = settings.max_image_size_mb * 1024 * 1024
    content = await read_upload_with_limit(
        file,
        max_bytes=max_bytes,
        empty_detail="Uploaded image file is empty.",
    )
    _validate_image_content(content)

    provider = get_model_provider("image")
    _ensure_provider_can_run(provider, "image")
    enforce_ai_generation_rate_limit(http_request, provider.name)

    project_id = generate_project_id()
    image_path = settings.uploads_dir / f"{project_id}_ref{extension}"
    output_path = settings.uploads_dir / f"{project_id}.glb"

    async with aiofiles.open(image_path, "wb") as output:
        await output.write(content)

    project_name = name or Path(file.filename).stem
    image_url = build_storage_url(Path("uploads") / image_path.name)

    if should_use_async_queue(provider):
        return await _enqueue_image_job(
            project_id=project_id,
            name=project_name,
            style=style,
            hint=hint,
            image_path=image_path,
            image_url=image_url,
            output_path=output_path,
            provider_name=provider.name,
        )

    try:
        result = await provider.generate_from_image(
            image_path=image_path,
            style=style,
            output_path=output_path,
            hint=hint,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not result.model_path.exists():
        raise HTTPException(status_code=500, detail="Model generation failed.")

    source_url = build_storage_url(Path("uploads") / output_path.name)

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
        async_mode=False,
    )


async def _enqueue_text_job(
    *,
    project_id: str,
    name: str,
    prompt: str,
    style: Style,
    output_path: Path,
    provider_name: str,
) -> JSONResponse:
    now = datetime.now(timezone.utc)
    job_id = generate_project_id()

    project_store.create(
        project_id=project_id,
        name=name,
        source_type=SourceType.TEXT_TO_3D,
        status=ProjectStatus.PROCESSING,
        source_prompt=prompt,
        ai_provider=provider_name,
    )

    job = GenerationJob(
        id=job_id,
        projectId=project_id,
        jobType=JobType.TEXT_TO_3D,
        provider=provider_name,
        prompt=prompt,
        style=style,
        output_path=str(output_path),
        createdAt=now,
        updatedAt=now,
    )
    generation_job_store.create(job)
    await generation_queue.enqueue(job_id)

    body = GenerateModelResponse(
        projectId=project_id,
        sourceType=SourceType.TEXT_TO_3D,
        sourcePrompt=prompt,
        aiProvider=provider_name,
        status=ProjectStatus.PROCESSING,
        jobId=job_id,
        async_mode=True,
        jobStatus=JobStatus.QUEUED,
        progress=0,
        message="Queued for generation",
    )
    return JSONResponse(status_code=202, content=body.model_dump(by_alias=True))


async def _enqueue_image_job(
    *,
    project_id: str,
    name: str,
    style: Style,
    hint: str | None,
    image_path: Path,
    image_url: str,
    output_path: Path,
    provider_name: str,
) -> JSONResponse:
    now = datetime.now(timezone.utc)
    job_id = generate_project_id()

    project_store.create(
        project_id=project_id,
        name=name,
        source_type=SourceType.IMAGE_TO_3D,
        status=ProjectStatus.PROCESSING,
        source_image_url=image_url,
        source_prompt=hint,
        ai_provider=provider_name,
    )

    job = GenerationJob(
        id=job_id,
        projectId=project_id,
        jobType=JobType.IMAGE_TO_3D,
        provider=provider_name,
        style=style,
        hint=hint,
        image_path=str(image_path),
        output_path=str(output_path),
        createdAt=now,
        updatedAt=now,
    )
    generation_job_store.create(job)
    await generation_queue.enqueue(job_id)

    body = GenerateModelResponse(
        projectId=project_id,
        sourceType=SourceType.IMAGE_TO_3D,
        sourceImageUrl=image_url,
        sourcePrompt=hint,
        aiProvider=provider_name,
        status=ProjectStatus.PROCESSING,
        jobId=job_id,
        async_mode=True,
        jobStatus=JobStatus.QUEUED,
        progress=0,
        message="Queued for generation",
    )
    return JSONResponse(status_code=202, content=body.model_dump(by_alias=True))


def _name_from_prompt(prompt: str) -> str:
    """Derive a short project name from the user prompt."""
    cleaned = prompt.strip()[:48]
    return cleaned if cleaned else "AI Model"


def _validate_image_content(content: bytes) -> None:
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Image content does not match a supported image format.",
        ) from exc


def _ensure_provider_can_run(provider, modality: str) -> None:
    if provider.name == "mock":
        return
    if provider.name == "triposr" and modality == "text":
        raise HTTPException(
            status_code=400,
            detail="TripoSR supports image-to-3D only. Configure Meshy or REPLICATE_TEXT_MODEL for text-to-3D.",
        )
    if provider.name == "replicate":
        missing = None
        if not settings.replicate_api_token:
            missing = "REPLICATE_API_TOKEN"
        elif modality == "text" and not settings.replicate_text_model:
            missing = "REPLICATE_TEXT_MODEL"
        elif modality == "image" and not settings.replicate_image_model:
            missing = "REPLICATE_IMAGE_MODEL"
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Replicate {modality}-to-3D requires {missing}.",
            )
    if provider.is_available:
        return
    raise HTTPException(
        status_code=400,
        detail=(
            f"AI provider '{provider.name}' is not configured for {modality}-to-3D. "
            "Check /api/ai/providers and apps/api/.env."
        ),
    )
