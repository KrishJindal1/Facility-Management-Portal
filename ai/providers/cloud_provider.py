"""
Cloud AI Provider implementing OpenAI-compatible Chat Completions API.
Supports OpenAI, Groq, OpenRouter, Together AI, and other OpenAI-standard endpoints.
Reads credentials strictly from environment variables.
"""
from typing import Optional, Tuple
import logging
import requests
from ai.providers.base import BaseAIProvider
from config import (
    AI_API_KEY,
    AI_MODEL,
    AI_API_BASE_URL,
    AI_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


class CloudAIProvider(BaseAIProvider):
    """OpenAI-compatible cloud AI provider using direct HTTP requests."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self._api_key = api_key or AI_API_KEY
        self._model = model or AI_MODEL or "gpt-4o-mini"
        self._base_url = (base_url or AI_API_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self._timeout = timeout or AI_TIMEOUT_SECONDS or 30

    @property
    def name(self) -> str:
        return "cloud_openai_compatible"

    def is_configured(self) -> Tuple[bool, str]:
        if not self._api_key or not self._api_key.strip():
            return False, "AI_API_KEY environment variable is missing or empty."
        return True, "Cloud AI provider configured."

    def ask(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Sends chat completion request to the OpenAI-compatible endpoint.
        Gracefully handles errors, timeouts, and missing API keys.
        """
        configured, msg = self.is_configured()
        if not configured:
            logger.warning("Cloud AI request skipped: %s", msg)
            return (
                "⚠️ **AI Assistant Offline**\n\n"
                "The cloud AI assistant is currently not configured because no API key was found.\n\n"
                "To enable the AI chatbot on Render or locally, please set the `AI_API_KEY` "
                "environment variable with your provider API key."
            )

        endpoint = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key.strip()}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.3,
        }

        try:
            logger.info("Sending chat completion to %s (model: %s)", endpoint, self._model)
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self._timeout,
            )

            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    return choices[0]["message"].get("content", "").strip()
                return "The AI returned an empty response. Please rephrase your question."

            elif response.status_code == 401:
                logger.error("Cloud AI authentication failed (HTTP 401).")
                return (
                    "⚠️ **Authentication Error**\n\n"
                    "The configured AI API key was rejected by the cloud provider. "
                    "Please verify your `AI_API_KEY` in environment variables."
                )

            elif response.status_code == 429:
                logger.warning("Cloud AI rate limit / quota exceeded (HTTP 429).")
                return (
                    "⏳ **Rate Limit Exceeded**\n\n"
                    "The AI service is experiencing high demand or account quota is exhausted. "
                    "Please try again in a few moments."
                )

            elif response.status_code >= 500:
                logger.error("Cloud AI server error (HTTP %s).", response.status_code)
                return (
                    "⚠️ **AI Provider Temporary Error**\n\n"
                    f"The cloud AI service returned a server error (HTTP {response.status_code}). "
                    "Please try again later."
                )

            else:
                logger.error("Unexpected Cloud AI error (HTTP %s): %s", response.status_code, response.text[:200])
                return (
                    "⚠️ **AI Communication Error**\n\n"
                    f"Unable to process request (HTTP {response.status_code}). Please try again."
                )

        except requests.exceptions.Timeout:
            logger.warning("Cloud AI request timed out after %s seconds.", self._timeout)
            return (
                "⏱️ **Request Timed Out**\n\n"
                "The AI assistant took too long to respond. Please try again."
            )

        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to cloud AI endpoint: %s", self._base_url)
            return (
                "🔌 **Connection Error**\n\n"
                "Could not establish a connection to the cloud AI service. "
                "Please verify network connectivity."
            )

        except Exception as exc:
            logger.error("Unexpected error in CloudAIProvider: %s", exc)
            return (
                "⚠️ **Service Error**\n\n"
                "An unexpected error occurred while communicating with the AI service. "
                "Please try again."
            )
