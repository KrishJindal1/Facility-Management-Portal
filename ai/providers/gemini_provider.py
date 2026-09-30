"""
Cloud AI Provider implementing Google Gemini REST API.
Reads credentials strictly from environment variables.
"""
from typing import Optional, Tuple
import logging
import os
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
        self._api_key = (
            api_key
            if api_key is not None
            else (
                os.getenv("AI_API_KEY")
                or os.getenv("GEMINI_API_KEY")
                or AI_API_KEY
            )
        )
        self._model = model or os.getenv("AI_MODEL") or AI_MODEL or "gemini-1.5-flash"
        self._timeout = timeout or int(os.getenv("AI_TIMEOUT_SECONDS", str(AI_TIMEOUT_SECONDS or 30)))

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
                try:
                    data = response.json()
                except Exception as json_err:
                    logger.error("Failed to parse JSON response from Gemini API: %s", json_err)
                    return (
                        "⚠️ **Malformed AI Response**\n\n"
                        "Received an unparseable response from the Gemini API. "
                        "Please try again."
                    )

                if not isinstance(data, dict):
                    return (
                        "⚠️ **Malformed AI Response**\n\n"
                        "Received an unexpected response structure from the Gemini API. "
                        "Please try again."
                    )

                candidates = data.get("candidates")
                if not isinstance(candidates, list) or not candidates:
                    return (
                        "⚠️ **Malformed AI Response**\n\n"
                        "The Gemini API returned an empty or malformed candidate set. "
                        "Please try again."
                    )

                first_candidate = candidates[0]
                if not isinstance(first_candidate, dict):
                    return (
                        "⚠️ **Malformed AI Response**\n\n"
                        "The Gemini API returned an invalid candidate format. "
                        "Please try again."
                    )

                content_obj = first_candidate.get("content")
                if not isinstance(content_obj, dict):
                    return (
                        "⚠️ **Malformed AI Response**\n\n"
                        "The Gemini API response missing content structure. "
                        "Please try again."
                    )

                parts = content_obj.get("parts")
                if not isinstance(parts, list) or not parts or not isinstance(parts[0], dict):
                    return (
                        "⚠️ **Malformed AI Response**\n\n"
                        "The Gemini API response missing parts structure. "
                        "Please try again."
                    )

                text = parts[0].get("text")
                if text is None or not str(text).strip():
                    return "The AI returned an empty response. Please rephrase your question."

                return str(text).strip()

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
