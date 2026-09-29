"""
Cloud AI Provider implementing Google Gemini REST API.
Reads credentials strictly from environment variables.
"""
from typing import Optional, Tuple
import logging
import requests
from ai.providers.base import BaseAIProvider
from config import AI_API_KEY, AI_MODEL, AI_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class GeminiCloudProvider(BaseAIProvider):
    """Google Gemini REST API cloud provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self._api_key = api_key or AI_API_KEY
        self._model = model or AI_MODEL or "gemini-1.5-flash"
        self._timeout = timeout or AI_TIMEOUT_SECONDS or 30

    @property
    def name(self) -> str:
        return "gemini"

    def is_configured(self) -> Tuple[bool, str]:
        if not self._api_key or not self._api_key.strip():
            return False, "GEMINI_API_KEY or AI_API_KEY environment variable is missing."
        return True, "Gemini provider configured."

    def ask(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        configured, msg = self.is_configured()
        if not configured:
            logger.warning("Gemini request skipped: %s", msg)
            return (
                "⚠️ **AI Assistant Offline**\n\n"
                "Google Gemini is not configured. Please set the `AI_API_KEY` (or `GEMINI_API_KEY`) "
                "environment variable."
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
        params = {"key": self._api_key.strip()}
        headers = {"Content-Type": "application/json"}

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
            }
        }
        if system_prompt:
            payload["system_instruction"] = {
                "parts": [{"text": system_prompt}]
            }

        try:
            logger.info("Sending request to Google Gemini API (model: %s)", self._model)
            response = requests.post(url, params=params, headers=headers, json=payload, timeout=self._timeout)

            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
                return "The AI returned an empty response. Please rephrase your question."

            elif response.status_code in (400, 403):
                logger.error("Gemini API key rejected or invalid request (HTTP %s).", response.status_code)
                return (
                    "⚠️ **Authentication Error**\n\n"
                    "The Gemini API key was rejected or invalid. "
                    "Please check your `AI_API_KEY` environment variable."
                )

            elif response.status_code == 429:
                return (
                    "⏳ **Rate Limit Exceeded**\n\n"
                    "Google Gemini API quota exceeded or rate limited. Please try again shortly."
                )

            else:
                return f"⚠️ **AI Error**: Gemini returned status code {response.status_code}."

        except requests.exceptions.Timeout:
            return "⏱️ **Request Timed Out**: Google Gemini took too long to respond. Please try again."

        except requests.exceptions.ConnectionError:
            return "🔌 **Connection Error**: Could not connect to Google Gemini API."

        except Exception as exc:
            logger.error("Gemini request exception: %s", exc)
            return "⚠️ **Service Error**: An unexpected error occurred while communicating with Gemini."
