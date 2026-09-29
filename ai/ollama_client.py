"""
Backward-compatibility wrapper for legacy callers of ask_ai.
Delegates to the configured AI provider abstraction.
"""
from ai.providers import get_ai_provider
from config import OLLAMA_MODEL

MODEL = OLLAMA_MODEL


def ask_ai(prompt: str) -> str:
    """
    Backward-compatible entry point for asking the AI model.
    Routes to the configured active provider (Cloud or Ollama).
    """
    provider = get_ai_provider()
    return provider.ask(prompt)