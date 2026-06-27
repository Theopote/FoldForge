"""Provider registry — select AI backend from configuration."""

from app.config import settings
from app.services.ai.base import ModelGeneratorProvider
from app.services.ai.providers.mock import MockModelProvider
from app.services.ai.providers.replicate import ReplicateModelProvider

_PROVIDERS: dict[str, type[ModelGeneratorProvider]] = {
    "mock": MockModelProvider,
    "replicate": ReplicateModelProvider,
}


def get_model_provider() -> ModelGeneratorProvider:
    """
    Return the configured model generation provider.

    Uses `replicate` when selected and token is present; otherwise mock.
    """
    provider_name = settings.ai_provider.lower()

    if provider_name == "replicate":
        provider = ReplicateModelProvider()
        if provider.is_available:
            return provider

    return MockModelProvider()


def list_providers() -> list[dict[str, str | bool]]:
    """Return provider status for the /api/ai/providers endpoint."""
    active = get_model_provider()
    return [
        {
            "name": name,
            "active": active.name == name,
            "available": cls().is_available if name != "mock" else True,
        }
        for name, cls in _PROVIDERS.items()
    ]
