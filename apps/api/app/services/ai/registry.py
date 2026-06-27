"""Provider registry — select AI backend from configuration."""

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


def resolve_provider_name() -> str:
    """
    Resolve configured provider name.

    `auto` picks the best available production provider, else mock.
    """
    configured = settings.ai_provider.lower()
    if configured != "auto":
        return configured

    for candidate in ("meshy", "triposr", "replicate"):
        provider = _instantiate(candidate)
        if provider.is_available:
            return candidate
    return "mock"


def get_model_provider() -> ModelGeneratorProvider:
    """Return the configured model generation provider instance."""
    name = resolve_provider_name()
    provider = _instantiate(name)
    if name != "mock" and not provider.is_available:
        return MockModelProvider()
    return provider


def get_provider_by_name(name: str) -> ModelGeneratorProvider:
    """Return a provider instance by explicit name."""
    provider = _instantiate(name)
    if name != "mock" and not provider.is_available:
        return MockModelProvider()
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
        items.append(
            {
                "name": name,
                "active": active.name == name or (active_name == name),
                "available": provider.is_available if name != "mock" else True,
                "async": should_use_async_queue(provider),
            }
        )

    items.append(
        {
            "name": "auto",
            "active": settings.ai_provider.lower() == "auto",
            "available": True,
            "async": should_use_async_queue(active),
        }
    )
    return items
