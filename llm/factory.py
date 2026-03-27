"""Factory for LLM providers."""

from llm.base import LLMProvider
from llm.claude_provider import ClaudeProvider

_providers: dict[str, LLMProvider] = {}


def get_llm_provider(
    provider_type: str = "claude",
    model: str | None = None,
) -> LLMProvider:
    """
    Factory for LLM providers. Caches by provider type + model.

    Args:
        provider_type: Provider backend ("claude")
        model: Optional model override

    Returns:
        Cached LLMProvider instance
    """
    cache_key = f"{provider_type}:{model or 'default'}"
    if cache_key not in _providers:
        if provider_type == "claude":
            _providers[cache_key] = ClaudeProvider(model=model)
        else:
            raise ValueError(f"Unknown LLM provider: {provider_type}")
    return _providers[cache_key]
