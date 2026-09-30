"""
Factory module for instantiating and caching AI providers.
Resolves providers based on AI_PROVIDER environment setting.
"""
import os
from typing import Optional, Dict
import logging
from ai.providers.base import BaseAIProvider
from ai.providers.cloud_provider import CloudAIProvider
from ai.providers.gemini_provider import GeminiCloudProvider
from ai.providers.ollama_provider import OllamaProvider
from ai.providers.mock_provider import MockAIProvider
from config import AI_PROVIDER

logger = logging.getLogger(__name__)

_PROVIDER_CACHE: Dict[str, BaseAIProvider] = {}


def get_ai_provider(provider_name: Optional[str] = None) -> BaseAIProvider:
    """
    Returns an instance of the configured AI provider.
    Supported provider names (case-insensitive):
    - "openai", "cloud", "groq", "openrouter": OpenAI-compatible cloud API
    - "gemini": Google Gemini REST API
    - "ollama": Local Ollama service
    - "mock": Mock provider for automated testing
    """
    target = (provider_name or os.getenv("AI_PROVIDER") or AI_PROVIDER or "openai").lower().strip()

    if target in _PROVIDER_CACHE:
        return _PROVIDER_CACHE[target]

    provider: BaseAIProvider
    if target in ("openai", "cloud", "groq", "openrouter"):
        provider = CloudAIProvider()
    elif target == "gemini":
        provider = GeminiCloudProvider()
    elif target == "ollama":
        provider = OllamaProvider()
    elif target == "mock":
        provider = MockAIProvider()
    else:
        logger.warning("Unknown AI_PROVIDER '%s'. Defaulting to CloudAIProvider.", target)
        provider = CloudAIProvider()

    _PROVIDER_CACHE[target] = provider
    return provider


def reset_provider_cache():
    """Clears the cached providers (useful for testing configuration changes)."""
    global _PROVIDER_CACHE
    _PROVIDER_CACHE.clear()
