"""
Central configuration module for HomeDesk Facility Management Portal.
Loads environment variables from .env file with fallback defaults.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Base Directory: Absolute path to the repository root
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file if present
load_dotenv(BASE_DIR / ".env")

# Application Environment
APP_ENV = os.getenv("APP_ENV", "development").lower()

# Server Configuration (Render injects PORT dynamically)
PORT = int(os.getenv("PORT", "8501"))
SERVER_ADDRESS = os.getenv("SERVER_ADDRESS", "0.0.0.0")

# Database Configuration
# Reads DATABASE_URL from environment. In development mode without PostgreSQL,
# defaults to a local SQLite database in data/ to preserve local execution.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{(BASE_DIR / 'data' / 'facility_management.db').resolve()}"

# Storage Configuration (Excel export / reporting)
_excel_path_env = os.getenv("EXCEL_FILE_PATH")
if _excel_path_env:
    _custom_excel = Path(_excel_path_env).expanduser()
    EXCEL_FILE = _custom_excel if _custom_excel.is_absolute() else (BASE_DIR / _custom_excel).resolve()
else:
    EXCEL_FILE = (BASE_DIR / "data" / "requirements.xlsx").resolve()

# Knowledge Base Directory
_knowledge_dir_env = os.getenv("KNOWLEDGE_DIR")
if _knowledge_dir_env:
    _custom_knowledge = Path(_knowledge_dir_env).expanduser()
    KNOWLEDGE_DIR = _custom_knowledge if _custom_knowledge.is_absolute() else (BASE_DIR / _custom_knowledge).resolve()
else:
    KNOWLEDGE_DIR = (BASE_DIR / "knowlegde").resolve()

# AI Provider Configuration
# Supported providers: "openai" (OpenAI-compatible cloud API e.g. OpenAI, Groq, OpenRouter), "gemini", "ollama"
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower().strip()
AI_API_KEY = (
    os.getenv("AI_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or os.getenv("GEMINI_API_KEY")
    or os.getenv("GROQ_API_KEY")
)
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1")
AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))

# Local Ollama Configuration (only used if AI_PROVIDER="ollama")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
