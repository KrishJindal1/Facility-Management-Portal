"""
Abstract base class for AI providers.
Defines the standard interface for all AI backends (Cloud APIs, Ollama, Mocks).
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple


class BaseAIProvider(ABC):
    """Abstract interface for AI chat generation."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier name of the provider."""
        pass

    @abstractmethod
    def ask(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Submits a prompt and returns the AI response string.
        Must handle errors gracefully and never raise unhandled exceptions.
        Must never leak credentials in responses or error logs.
        """
        pass

    @abstractmethod
    def is_configured(self) -> Tuple[bool, str]:
        """
        Checks if the provider has all required credentials and configuration.
        Returns (is_ready, message).
        """
        pass
