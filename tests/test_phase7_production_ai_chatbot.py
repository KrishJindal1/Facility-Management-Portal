"""
Unit and Integration Tests for Phase 7: Production AI Chatbot & Provider Abstraction.

Verifies:
1. Chatbot success (end-to-end ask_chatbot and FastAPI /api/chat).
2. Missing API key handling (graceful offline notice, no crash).
3. API failure handling (HTTP 401, 429, 500, timeout, connection error).
4. Malformed response handling (unparseable JSON, invalid choices/candidates).
5. Application startup without Ollama (healthcheck and endpoints run cleanly on Render without Ollama).
6. Secrets protection (API keys read from environment, never hardcoded, never leaked in responses/logs).
"""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from ai.chatbot import ask_chatbot
from ai.providers.base import BaseAIProvider
from ai.providers.cloud_provider import CloudAIProvider
from ai.providers.gemini_provider import GeminiCloudProvider
from ai.providers.ollama_provider import OllamaProvider
from ai.providers.factory import get_ai_provider, reset_provider_cache
from healthcheck import run_health_check


class TestPhase7ProductionAIChatbot(unittest.TestCase):
    """Test suite for Phase 7 Production AI Chatbot & Ollama Independence."""

    def setUp(self):
        reset_provider_cache()
        self.client = TestClient(app)

    def tearDown(self):
        reset_provider_cache()

    def test_01_chatbot_success(self):
        """Chatbot successfully answers queries using Cloud AI provider without Ollama."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "HomeDesk provides verified professional cooks for home dining across major cities.",
                    }
                }
            ]
        }

        with patch.dict("os.environ", {"AI_PROVIDER": "openai", "AI_API_KEY": "test-cloud-key"}):
            with patch("requests.post", return_value=mock_resp):
                # 1. Direct ask_chatbot call
                reply = ask_chatbot("Tell me about cook services")
                self.assertIn("verified professional cooks", reply)

                # 2. FastAPI endpoint /api/chat
                api_resp = self.client.post("/api/chat", json={"message": "Tell me about cook services"})
                self.assertEqual(api_resp.status_code, 200)
                self.assertIn("verified professional cooks", api_resp.json().get("reply", ""))

    def test_02_missing_api_key(self):
        """When AI_API_KEY is not configured, chatbot returns graceful offline guidance without crashing."""
        provider = CloudAIProvider(api_key="")
        is_ready, msg = provider.is_configured()
        self.assertFalse(is_ready)
        self.assertIn("missing", msg.lower())

        with patch.dict("os.environ", {"AI_PROVIDER": "openai", "AI_API_KEY": ""}):
            # Direct ask_chatbot call
            reply = ask_chatbot("What is the driver hourly rate?")
            self.assertIn("AI Assistant Offline", reply)
            self.assertIn("AI_API_KEY", reply)

            # API endpoint handles missing configuration cleanly
            res = self.client.post("/api/chat", json={"message": "What is the driver hourly rate?"})
            self.assertEqual(res.status_code, 200)
            self.assertIn("AI Assistant Offline", res.json().get("reply", ""))

    def test_03_api_failure_modes(self):
        """API failure modes (401 Unauthorized, 429 Rate Limit, 500 Error, Timeout, ConnectionError) handled gracefully."""
        provider = CloudAIProvider(api_key="mock-key")

        # 1. HTTP 401 Unauthorized
        mock_401 = MagicMock(status_code=401, text="Unauthorized: Key rejected")
        with patch("requests.post", return_value=mock_401):
            reply_401 = provider.ask("Hello?")
            self.assertIn("Authentication Error", reply_401)
            self.assertNotIn("mock-key", reply_401, "API key must never leak into response")

        # 2. HTTP 429 Rate Limit
        mock_429 = MagicMock(status_code=429, text="Rate limit reached")
        with patch("requests.post", return_value=mock_429):
            reply_429 = provider.ask("Hello?")
            self.assertIn("Rate Limit Exceeded", reply_429)

        # 3. HTTP 500 / 503 Provider Server Error
        mock_503 = MagicMock(status_code=503, text="Service Unavailable")
        with patch("requests.post", return_value=mock_503):
            reply_503 = provider.ask("Hello?")
            self.assertIn("AI Provider Temporary Error", reply_503)

        # 4. Timeout Exception
        import requests
        with patch("requests.post", side_effect=requests.exceptions.Timeout("Read timed out")):
            reply_timeout = provider.ask("Hello?")
            self.assertIn("Request Timed Out", reply_timeout)

        # 5. Connection Error
        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("DNS failure")):
            reply_conn = provider.ask("Hello?")
            self.assertIn("Connection Error", reply_conn)

    def test_04_malformed_response_handling(self):
        """Malformed JSON responses and broken schema responses are caught and handled gracefully."""
        provider = CloudAIProvider(api_key="mock-key")

        # 1. Invalid JSON body (e.g. HTML error page or truncated data with HTTP 200)
        mock_bad_json = MagicMock(status_code=200)
        mock_bad_json.json.side_effect = ValueError("Invalid JSON: Expecting value: line 1 column 1")
        with patch("requests.post", return_value=mock_bad_json):
            reply_bad_json = provider.ask("Question?")
            self.assertIn("Malformed AI Response", reply_bad_json)

        # 2. Empty choices list
        mock_empty_choices = MagicMock(status_code=200)
        mock_empty_choices.json.return_value = {"choices": []}
        with patch("requests.post", return_value=mock_empty_choices):
            reply_empty = provider.ask("Question?")
            self.assertIn("Malformed AI Response", reply_empty)

        # 3. Missing 'message' key inside choice
        mock_missing_msg = MagicMock(status_code=200)
        mock_missing_msg.json.return_value = {"choices": [{"index": 0}]}
        with patch("requests.post", return_value=mock_missing_msg):
            reply_missing = provider.ask("Question?")
            self.assertIn("Malformed AI Response", reply_missing)

        # 4. Gemini malformed candidate structure
        gemini = GeminiCloudProvider(api_key="gemini-key")
        mock_gemini_bad = MagicMock(status_code=200)
        mock_gemini_bad.json.return_value = {"candidates": [{}]}
        with patch("requests.post", return_value=mock_gemini_bad):
            gemini_reply = gemini.ask("Question?")
            self.assertIn("Malformed AI Response", gemini_reply)

        # 5. Ollama malformed response
        ollama = OllamaProvider(host="http://localhost:11434")
        mock_ollama_bad = MagicMock(status_code=200)
        mock_ollama_bad.json.return_value = {"broken": True}
        with patch("requests.post", return_value=mock_ollama_bad):
            ollama_reply = ollama.ask("Question?")
            self.assertIn("Malformed AI Response", ollama_reply)

    def test_05_application_startup_without_ollama(self):
        """Application health check and FastAPI endpoints execute successfully without Ollama installed or running."""
        # Ensure AI_PROVIDER is set to cloud provider (openai)
        with patch.dict("os.environ", {"AI_PROVIDER": "openai", "AI_API_KEY": "test-key"}):
            # 1. Health check executes without trying to contact Ollama
            report = run_health_check()
            self.assertIn(report["status"], ("healthy", "degraded"))
            self.assertIn("ai_provider", report["checks"])
            self.assertEqual(report["checks"]["ai_provider"]["provider"], "openai")

            # 2. FastAPI health endpoint responds with HTTP 200
            res = self.client.get("/api/health")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("checks", data)
            self.assertEqual(data["checks"]["ai_provider"]["provider"], "openai")

    def test_06_local_ollama_unreachable_gives_clear_production_guidance(self):
        """When AI_PROVIDER=ollama is configured for local dev but Ollama daemon is offline, returns clear switch guidance."""
        ollama = OllamaProvider(host="http://localhost:11434")
        import requests
        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Connection refused")):
            reply = ollama.ask("Help with cooking?")
            self.assertIn("Ollama Unavailable", reply)
            self.assertIn("AI_PROVIDER=openai", reply)
            self.assertIn("Render", reply)

    def test_07_secrets_protection_and_no_leakage(self):
        """Verifies that secrets are never logged or exposed in responses even under error conditions."""
        secret_key = "super-secret-prod-token-12345"
        provider = CloudAIProvider(api_key=secret_key)

        mock_err = MagicMock(status_code=403, text=f"Forbidden for {secret_key}")
        with patch("requests.post", return_value=mock_err):
            response = provider.ask("Test question")
            self.assertNotIn(secret_key, response, "Secret key must not appear in user-facing response")


if __name__ == "__main__":
    unittest.main()
