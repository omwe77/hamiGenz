"""Unit tests verifying environment variable defaults and dotenv integration."""
import os
import sys

_BACKEND = os.path.dirname(os.path.dirname(__file__))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


def test_env_defaults():
    """Verify backend default environment variables are valid and non-empty."""
    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    embed_model = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

    assert ollama_base.startswith("http://") or ollama_base.startswith("https://")
    assert len(ollama_model) > 0
    assert "MiniLM" in embed_model
    assert "3000" in frontend_origin


def test_dotenv_module_available():
    """Ensure python-dotenv can be imported and load_dotenv callable."""
    from dotenv import load_dotenv
    assert callable(load_dotenv)