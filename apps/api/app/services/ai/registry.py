"""Provider registry - select AI backend from configuration."""

from app.config import settings
from app.services.ai.base import ModelGeneratorProvider
from app.services.ai.providers.meshy import MeshyProvider
from app.services.ai.providers.mock import MockModelProvider
from app.services.ai.providers.replicate import ReplicateModelProvider
from app.services.ai.providers.triposr import TripoSRProvider

_PROVIDERS: dict[str, type[ModelGeneratorProvider]] = {
    "mock": MockModelProvider,
    "meshy": MeshyProvider,
    "triposr": TripoSRProvider,
    "replicate": ReplicateModelProvider,
}


def _instantiate(name: str) -> ModelGeneratorProvider:
    cls = _PROVIDERS.get(name, MockModelProvider)
    return cls()


def resolve_provider_name(modality: str = "any") -> str:
    """
    Resolve configured provider name.

    `auto` picks the best available production provider, else mock.
    """
    configured = settings.ai_provider.lower()
    if configured != "auto":
        return configured

    if modality == "text":
        candidates = ("meshy", "replicate")
    elif modality == "image":
        candidates = ("meshy", "triposr", "replicate")
    else:
        candidates = ("meshy", "triposr", "replicate")

    for candidate in candidates:
        provider = _instantiate(candidate)
        configured, text, image, _reason = _provider_capabilities(candidate)
        supports_modality = (
            modality == "any"
            or (modality == "text" and text)
            or (modality == "image" and image)
        )
        if provider.is_available and configured and supports_modality:
            return candidate
    return "mock"


def get_model_provider(modality: str = "any") -> ModelGeneratorProvider:
    """Return the configured model generation provider instance."""
    name = resolve_provider_name(modality)
    provider = _instantiate(name)
    return provider


def get_provider_by_name(name: str) -> ModelGeneratorProvider:
    """Return a provider instance by explicit name."""
    provider = _instantiate(name)
    return provider


def should_use_async_queue(provider: ModelGeneratorProvider) -> bool:
    """Whether generation should run in the background job queue."""
    if provider.name == "mock":
        return settings.ai_async_for_mock
    return provider.requires_async


def list_providers() -> list[dict[str, str | bool]]:
    """Return provider status for the /api/ai/providers endpoint."""
    active_name = resolve_provider_name()
    active = get_model_provider()
    items: list[dict[str, str | bool]] = []

    for name in ("mock", "meshy", "triposr", "replicate"):
        provider = _instantiate(name)
        configured, text, image, reason = _provider_capabilities(name)
        items.append(
            {
                "name": name,
                "active": active.name == name or (active_name == name),
                "available": provider.is_available if name != "mock" else True,
                "configured": configured,
                "text": text,
                "image": image,
                "reason": reason or "",
                "async": should_use_async_queue(provider),
            }
        )

    items.append(
        {
            "name": "auto",
            "active": settings.ai_provider.lower() == "auto",
            "available": True,
            "configured": True,
            "text": True,
            "image": True,
            "reason": f"Resolved to {active.name}",
            "async": should_use_async_queue(active),
        }
    )
    return items


def _provider_capabilities(name: str) -> tuple[bool, bool, bool, str | None]:
    if name == "mock":
        return True, True, True, "Offline procedural fallback"
    if name == "meshy":
        configured = bool(settings.meshy_api_key)
        return (
            configured,
            configured,
            configured,
            None if configured else "Set MESHY_API_KEY",
        )
    if name == "triposr":
        configured = bool(
            settings.replicate_api_token and settings.triposr_replicate_version
        )
        missing = []
        if not settings.replicate_api_token:
            missing.append("REPLICATE_API_TOKEN")
        if not settings.triposr_replicate_version:
            missing.append("TRIPOSR_REPLICATE_VERSION")
        return (
            configured,
            False,
            configured,
            None if configured else f"Set {', '.join(missing)}",
        )
    if name == "replicate":
        has_token = bool(settings.replicate_api_token)
        text = bool(has_token and settings.replicate_text_model)
        image = bool(has_token and settings.replicate_image_model)
        missing = []
        if not has_token:
            missing.append("REPLICATE_API_TOKEN")
        if has_token and not settings.replicate_text_model:
            missing.append("REPLICATE_TEXT_MODEL")
        if has_token and not settings.replicate_image_model:
            missing.append("REPLICATE_IMAGE_MODEL")
        return (
            text or image,
            text,
            image,
            None if text or image else f"Set {', '.join(missing)}",
        )
    return False, False, False, "Unknown provider"
