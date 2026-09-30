"""
Cloud AI Provider implementing OpenAI-compatible Chat Completions API.
Supports OpenAI, Groq, OpenRouter, Together AI, and other OpenAI-standard endpoints.
Reads credentials strictly from environment variables.
"""
from typing import Optional, Tuple
import logging
import os
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
        self._api_key = (
            api_key
            if api_key is not None
            else (
                os.getenv("AI_API_KEY")
                or os.getenv("OPENAI_API_KEY")
                or os.getenv("GROQ_API_KEY")
                or AI_API_KEY
            )
        )
        self._model = model or os.getenv("AI_MODEL") or AI_MODEL or "gpt-4o-mini"
        self._base_url = (
            base_url
            or os.getenv("AI_API_BASE_URL")
            or AI_API_BASE_URL
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self._timeout = timeout or int(os.getenv("AI_TIMEOUT_SECONDS", str(AI_TIMEOUT_SECONDS or 30)))

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
                try:
                    data = response.json()
                except Exception as json_err:
                    logger.error("Failed to parse JSON response from Cloud AI: %s", json_err)
                    return (
                        "⚠️ **Malformed AI Response**\n\n"
                        "Received an unparseable response from the AI provider. "
                        "Please try again."
                    )

                if not isinstance(data, dict):
                    logger.error("Cloud AI response JSON is not a dictionary: %s", type(data))
                    return (
                        "⚠️ **Malformed AI Response**\n\n"
                        "Received an unexpected response structure from the AI provider. "
                        "Please try again."
                    )

                choices = data.get("choices")
                if not isinstance(choices, list) or not choices:
                    logger.warning("Cloud AI response has empty or invalid choices: %s", choices)
                    return (
                        "⚠️ **Malformed AI Response**\n\n"
                        "The AI provider returned an empty or malformed choice set. "
                        "Please try again."
                    )

                first_choice = choices[0]
                if not isinstance(first_choice, dict) or "message" not in first_choice:
                    logger.warning("Cloud AI response choice missing message: %s", first_choice)
                    return (
                        "⚠️ **Malformed AI Response**\n\n"
                        "The AI provider response missing message content. "
                        "Please try again."
                    )

                message = first_choice.get("message")
                if not isinstance(message, dict) or "content" not in message:
                    logger.warning("Cloud AI response message missing content: %s", message)
                    return (
                        "⚠️ **Malformed AI Response**\n\n"
                        "The AI provider response missing content field. "
                        "Please try again."
                    )

                content = message.get("content")
                if content is None or not str(content).strip():
                    return "The AI returned an empty response. Please rephrase your question."

                return str(content).strip()

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
