"""Unit and integration tests verifying environment variable defaults and isolated .env loading."""
import os
import sys
from pathlib import Path

_BACKEND = os.path.dirname(os.path.dirname(__file__))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from config import load_environment


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


def test_load_environment_reads_unset_var(tmp_path, monkeypatch):
    """Integration: Isolated temporary .env supplies a previously unset config variable."""
    test_key = "TEST_HAMIGENZ_UNSET_VAR"
    test_val = "isolated_nepal_civic_value"

    # Ensure clean starting state
    monkeypatch.delenv(test_key, raising=False)
    assert os.getenv(test_key) is None

    # Write a temporary .env file
    env_file = tmp_path / ".env"
    env_file.write_text(f"{test_key}={test_val}\n", encoding="utf-8")

    # Load via application's loading mechanism
    loaded = load_environment(dotenv_path=env_file)
    assert loaded is True
    assert os.getenv(test_key) == test_val


def test_load_environment_preserves_precedence(tmp_path, monkeypatch):
    """Integration: Existing environment variables take precedence by default (override=False)."""
    test_key = "TEST_HAMIGENZ_PRECEDENCE_VAR"
    pre_existing_val = "system_level_precedence"
    dotenv_val = "dotenv_level_ignored"

    # Pre-set in environment
    monkeypatch.setenv(test_key, pre_existing_val)

    # Write conflicting value in temporary .env file
    env_file = tmp_path / ".env"
    env_file.write_text(f"{test_key}={dotenv_val}\n", encoding="utf-8")

    # Load without override
    loaded = load_environment(dotenv_path=env_file, override=False)
    assert loaded is True
    assert os.getenv(test_key) == pre_existing_val


def test_load_environment_supports_explicit_override(tmp_path, monkeypatch):
    """Integration: When override=True is specified, .env takes precedence."""
    test_key = "TEST_HAMIGENZ_OVERRIDE_VAR"
    pre_existing_val = "initial_val"
    dotenv_val = "overridden_val"

    monkeypatch.setenv(test_key, pre_existing_val)

    env_file = tmp_path / ".env"
    env_file.write_text(f"{test_key}={dotenv_val}\n", encoding="utf-8")

    loaded = load_environment(dotenv_path=env_file, override=True)
    assert loaded is True
    assert os.getenv(test_key) == dotenv_val


def test_load_environment_nonexistent_file():
    """Verify loading from a non-existent path safely returns False without raising."""
    loaded = load_environment(dotenv_path=Path("/nonexistent/path/.env.missing"))
    assert loaded is False
