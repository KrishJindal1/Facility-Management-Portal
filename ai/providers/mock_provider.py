"""
Mock AI Provider for testing and offline validation.
Allows deterministic testing of UI, failure modes, and chatbot behaviors without external API calls.
"""
from typing import Optional, Tuple
from ai.providers.base import BaseAIProvider


class MockAIProvider(BaseAIProvider):
    """Mock provider for automated testing and test suites."""

    def __init__(
        self,
        default_response: Optional[str] = None,
        simulate_error: Optional[str] = None,
    ):
        self._default_response = (
            default_response
            or "This is a mock AI response from HomeDesk Facility Management assistant."
        )
        self._simulate_error = simulate_error

    @property
    def name(self) -> str:
        return "mock"

    def is_configured(self) -> Tuple[bool, str]:
        if self._simulate_error == "missing_key":
            return False, "Mock error: Missing API key"
        return True, "Mock provider ready"

    def set_simulation(self, error_type: Optional[str] = None):
        self._simulate_error = error_type

    def ask(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if self._simulate_error == "missing_key":
            return (
                "⚠️ **AI Assistant Offline**\n\n"
                "The cloud AI assistant is currently not configured because no API key was found.\n\n"
                "To enable the AI chatbot on Render or locally, please set the `AI_API_KEY` "
                "environment variable with your provider API key."
            )
        elif self._simulate_error == "unauthorized":
            return (
                "⚠️ **Authentication Error**\n\n"
                "The configured AI API key was rejected by the cloud provider. "
                "Please verify your `AI_API_KEY` in environment variables."
            )
        elif self._simulate_error == "rate_limit":
            return (
                "⏳ **Rate Limit Exceeded**\n\n"
                "The AI service is experiencing high demand or account quota is exhausted. "
                "Please try again in a few moments."
            )
        elif self._simulate_error == "timeout":
            return (
                "⏱️ **Request Timed Out**\n\n"
                "The AI assistant took too long to respond. Please try again."
            )
        elif self._simulate_error == "connection_error":
            return (
                "🔌 **Connection Error**\n\n"
                "Could not establish a connection to the cloud AI service. "
                "Please verify network connectivity."
            )

        return f"Echo: Based on the knowledge base, for question '{prompt[:40]}...': {self._default_response}"
