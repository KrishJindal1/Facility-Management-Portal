"""
Automated AI Provider & Cloud Abstraction Test Suite.
Verifies Phase 5 requirements:
1. Provider abstraction (CloudAIProvider, GeminiCloudProvider, OllamaProvider, MockAIProvider).
2. Dynamic configuration via AI_PROVIDER and environment variables.
3. Missing API-key behavior (graceful offline notice).
4. API failure behavior (HTTP 401 unauthorized, HTTP 429 rate limit, timeout, connection errors).
5. Verification that secrets are never hardcoded or stored in source code.
6. Chatbot interface and prompts preservation.
"""
import unittest
from unittest.mock import patch, MagicMock
import requests
from ai.chatbot import ask_chatbot
from ai.providers.base import BaseAIProvider
from ai.providers.cloud_provider import CloudAIProvider
from ai.providers.gemini_provider import GeminiCloudProvider
from ai.providers.ollama_provider import OllamaProvider
from ai.providers.mock_provider import MockAIProvider
from ai.providers.factory import get_ai_provider, reset_provider_cache


class TestAIProviderArchitecture(unittest.TestCase):

    def setUp(self):
        reset_provider_cache()

    def tearDown(self):
        reset_provider_cache()

    def test_01_greetings_handled_without_api_call(self):
        """Chatbot responds to greetings immediately without triggering external API calls."""
        for greeting in ("hi", "hello", "hey", "good morning"):
            response = ask_chatbot(greeting)
            self.assertIn("Welcome to HomeDesk", response)
            self.assertIn("Cook services", response)

    def test_02_missing_api_key_graceful_handling(self):
        """When AI_API_KEY is missing or empty, cloud provider returns a friendly offline message."""
        provider = CloudAIProvider(api_key="")
        is_ready, msg = provider.is_configured()
        self.assertFalse(is_ready)
        self.assertIn("missing", msg.lower())

        response = provider.ask("How much does a cook cost?")
        self.assertIn("AI Assistant Offline", response)
        self.assertIn("AI_API_KEY", response)

    def test_03_cloud_provider_success(self):
        """Simulates successful cloud API chat completion response."""
        provider = CloudAIProvider(api_key="test-dummy-key-not-real")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "A full-time cook in Mumbai typically ranges from ₹14,000 to ₹18,000 per month.",
                    }
                }
            ]
        }

        with patch("requests.post", return_value=mock_resp) as mock_post:
            reply = provider.ask("What is the cook price in Mumbai?", system_prompt="System instructions")
            self.assertIn("₹14,000", reply)
            mock_post.assert_called_once()
            # Verify authorization header is sent
            headers_sent = mock_post.call_args[1]["headers"]
            self.assertEqual(headers_sent["Authorization"], "Bearer test-dummy-key-not-real")

    def test_04_cloud_provider_auth_failure_401(self):
        """HTTP 401 Unauthorized returns a clear, non-crashing authentication error message."""
        provider = CloudAIProvider(api_key="invalid-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized: Invalid API key"

        with patch("requests.post", return_value=mock_resp):
            reply = provider.ask("Hello?")
            self.assertIn("Authentication Error", reply)
            self.assertIn("AI_API_KEY", reply)
            # Ensure raw secret is not dumped
            self.assertNotIn("invalid-key", reply)

    def test_05_cloud_provider_rate_limit_429(self):
        """HTTP 429 Rate Limit returns a friendly retry notification."""
        provider = CloudAIProvider(api_key="test-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Rate limit reached"

        with patch("requests.post", return_value=mock_resp):
            reply = provider.ask("Hello?")
            self.assertIn("Rate Limit Exceeded", reply)

    def test_06_cloud_provider_timeout_handling(self):
        """Timeout exceptions are caught and reported cleanly."""
        provider = CloudAIProvider(api_key="test-key", timeout=1)

        with patch("requests.post", side_effect=requests.exceptions.Timeout("Read timeout")):
            reply = provider.ask("Hello?")
            self.assertIn("Request Timed Out", reply)

    def test_07_cloud_provider_connection_error_handling(self):
        """Network/Connection failures are caught and reported gracefully."""
        provider = CloudAIProvider(api_key="test-key")

        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("DNS failure")):
            reply = provider.ask("Hello?")
            self.assertIn("Connection Error", reply)

    def test_08_gemini_provider_behavior(self):
        """Google Gemini cloud provider handles missing key and successful generation."""
        # 1. Missing key
        gemini = GeminiCloudProvider(api_key="")
        self.assertFalse(gemini.is_configured()[0])
        self.assertIn("AI Assistant Offline", gemini.ask("Test"))

        # 2. Successful generation
        gemini_ready = GeminiCloudProvider(api_key="test-gemini-key")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Gemini response: Security guards operate 12-hour shifts."}]
                    }
                }
            ]
        }

        with patch("requests.post", return_value=mock_resp):
            answer = gemini_ready.ask("What are guard shifts?", system_prompt="Knowledge")
            self.assertIn("12-hour shifts", answer)

    def test_09_ollama_provider_unreachable_notice(self):
        """When Ollama is not running (e.g. on Render), returns cloud switch instructions."""
        ollama = OllamaProvider(host="http://localhost:99999")

        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Refused")):
            reply = ollama.ask("Question?")
            self.assertIn("Ollama Unavailable", reply)
            self.assertIn("AI_PROVIDER=openai", reply)
            self.assertIn("Render", reply)

    def test_10_provider_factory_resolution(self):
        """Factory correctly resolves requested providers."""
        openai_p = get_ai_provider("openai")
        self.assertIsInstance(openai_p, CloudAIProvider)

        groq_p = get_ai_provider("groq")
        self.assertIsInstance(groq_p, CloudAIProvider)

        gemini_p = get_ai_provider("gemini")
        self.assertIsInstance(gemini_p, GeminiCloudProvider)

        ollama_p = get_ai_provider("ollama")
        self.assertIsInstance(ollama_p, OllamaProvider)

        mock_p = get_ai_provider("mock")
        self.assertIsInstance(mock_p, MockAIProvider)

    def test_11_no_hardcoded_secrets_in_source_tree(self):
        """Verifies that no real API keys are hardcoded in the codebase."""
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent

        forbidden_patterns = [
            "sk-" + "proj-",
            "AIza" + "Sy",
            "gsk" + "_",
        ]

        # Scan application source files (excluding .venv and tests)
        for py_file in root.glob("**/*.py"):
            file_str = str(py_file)
            if ".venv" in file_str or "tests" in file_str:
                continue
            text = py_file.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                self.assertNotIn(
                    pattern,
                    text,
                    f"Possible hardcoded secret pattern '{pattern}' found in {py_file}!",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
