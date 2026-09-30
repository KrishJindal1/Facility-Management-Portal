"""
Local Ollama Provider for offline and local development.
Uses standard HTTP REST calls so the application does not depend on the Ollama daemon in cloud.
"""
from typing import Optional, Tuple
import logging
import requests
from ai.providers.base import BaseAIProvider
from config import OLLAMA_HOST, OLLAMA_MODEL

logger = logging.getLogger(__name__)


class OllamaProvider(BaseAIProvider):
    """Local Ollama AI provider for development environments."""

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 45,
    ):
        self._host = (host or OLLAMA_HOST or "http://localhost:11434").rstrip("/")
        self._model = model or OLLAMA_MODEL or "llama3.1:8b"
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "ollama"

    def is_configured(self) -> Tuple[bool, str]:
        try:
            res = requests.get(f"{self._host}/api/tags", timeout=2)
            if res.status_code == 200:
                return True, "Ollama service is reachable."
        except Exception:
            pass
        return False, f"Ollama daemon not reachable at {self._host}."

    def ask(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        endpoint = f"{self._host}/api/chat"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }

        try:
            logger.info("Sending request to local Ollama at %s (model: %s)", endpoint, self._model)
            response = requests.post(endpoint, json=payload, timeout=self._timeout)

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception as json_err:
                    logger.error("Failed to parse JSON response from Ollama: %s", json_err)
                    return (
                        "⚠️ **Malformed AI Response**\n\n"
                        "Received an unparseable response from the Ollama server. "
                        "Please try again."
                    )

                if not isinstance(data, dict):
                    return (
                        "⚠️ **Malformed AI Response**\n\n"
                        "Received an unexpected response structure from the Ollama server. "
                        "Please try again."
                    )

                msg = data.get("message")
                if not isinstance(msg, dict) or "content" not in msg:
                    return (
                        "⚠️ **Malformed AI Response**\n\n"
                        "Ollama response missing message content. "
                        "Please try again."
                    )

                content = msg.get("content")
                if content is None or not str(content).strip():
                    return "The AI returned an empty response. Please rephrase your question."

                return str(content).strip()
            else:
                return f"⚠️ **Ollama Error**: Server returned status code {response.status_code}."

        except requests.exceptions.ConnectionError:
            logger.warning("Could not connect to Ollama at %s", self._host)
            return (
                "🔌 **Ollama Unavailable**\n\n"
                f"Could not connect to the local Ollama server at `{self._host}`.\n\n"
                "• For **local development**: Please verify Ollama is running (`ollama serve`).\n"
                "• For **cloud deployment (Render)**: Set `AI_PROVIDER=openai` (or `gemini`) "
                "and set `AI_API_KEY` in environment variables."
            )

        except requests.exceptions.Timeout:
            return "⏱️ **Ollama Timed Out**: The local model took too long to respond."

        except Exception as exc:
            logger.error("Ollama request error: %s", exc)
            return f"⚠️ **Ollama Error**: {str(exc)}"
