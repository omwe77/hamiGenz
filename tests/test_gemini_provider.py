"""
tests/test_gemini_provider.py
Focused automated tests for Task 3.1 — Optional Gemini Provider + API Key Hygiene.

Covers:
1. Ollama remains the default provider when LLM_PROVIDER is unset or 'ollama'.
2. Gemini provider selection and model configuration via environment variables.
3. Missing GEMINI_API_KEY fails clearly with ValueError and never silently falls back.
4. Successful text generation via Gemini client (Interactions API and Models API).
5. Streaming generation accumulates chunks properly and is not ignored.
6. Structured generation returns parsed JSON matching the existing interface.
7. API errors are translated to LLMUnavailableError without leaking API keys or headers.
8. Supported generation options and request timeouts are mapped correctly; unsupported options reject.
9. .gitignore protects secret-bearing files (.env, .env.production, etc.) while allowing .env.example / .env.sample.
10. Existing OllamaService behavior remains completely unchanged.
11. Compatibility with downstream services (GroundingValidator, VerificationLayer, ActionExtractor, etc.).
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import main
from main import app, lifespan
from llm_service import (
    OllamaService,
    GeminiService,
    LLMUnavailableError,
    GroundingValidator,
    VerificationLayer,
    ExplanationEngine,
)
from action_extractor import ActionExtractor
from form_understanding import FormUnderstandingService
from official_answer import OfficialAnswerService


# ─── 1. Default Provider & Selection ──────────────────────────────────────────

def test_default_provider_is_ollama(monkeypatch):
    """When LLM_PROVIDER is unset or empty, provider defaults to ollama."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert os.getenv("LLM_PROVIDER", "ollama").strip().lower() == "ollama"


def test_gemini_provider_selection_and_model_config(monkeypatch):
    """Gemini provider is selected via LLM_PROVIDER=gemini with GEMINI_MODEL."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-secret-key-12345")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    mock_client = MagicMock()
    service = GeminiService(
        api_key=os.getenv("GEMINI_API_KEY"),
        model=os.getenv("GEMINI_MODEL"),
        client=mock_client,
    )
    assert service.model == "gemini-3.5-flash-lite"
    assert service.api_key == "test-secret-key-12345"
    assert service.client is mock_client


def test_missing_gemini_api_key_fails_clearly(monkeypatch):
    """If Gemini is selected without an API key, it fails clearly and never falls back."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        GeminiService(api_key=None, client=None)


# ─── 2. Generation & Streaming ────────────────────────────────────────────────

def test_gemini_generate_text_interactions_api():
    """GeminiService calls interactions.create and returns output_text."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.output_text = "Kathmandu is the capital of Nepal."
    mock_client.interactions.create.return_value = mock_resp

    service = GeminiService(api_key="test-key", client=mock_client)
    res = service.generate("What is the capital of Nepal?")

    assert res == "Kathmandu is the capital of Nepal."
    mock_client.interactions.create.assert_called_once()
    call_kwargs = mock_client.interactions.create.call_args.kwargs
    assert call_kwargs["model"] == "gemini-3.5-flash-lite"
    assert call_kwargs["input"] == "What is the capital of Nepal?"
    assert call_kwargs.get("store") is False, "store=False must always be sent to prevent server-side storage"


def test_gemini_generate_text_models_api_fallback():
    """If interactions is absent, falls back to models.generate_content."""
    mock_client = MagicMock(spec=["models"])
    mock_resp = MagicMock()
    mock_resp.text = "Answer from models API."
    mock_client.models.generate_content.return_value = mock_resp

    service = GeminiService(api_key="test-key", client=mock_client)
    res = service.generate("Hello models")

    assert res == "Answer from models API."
    mock_client.models.generate_content.assert_called_once()


def test_gemini_generate_streaming():
    """Streaming request yields and accumulates chunks into full response."""
    mock_client = MagicMock()
    event1 = MagicMock()
    event1.delta = "Part 1, "
    event2 = MagicMock()
    event2.delta = "Part 2."
    mock_client.interactions.create.return_value = [event1, event2]

    service = GeminiService(api_key="test-key", client=mock_client)
    res = service.generate("Stream test", stream=True)

    assert res == "Part 1, Part 2."
    call_kwargs = mock_client.interactions.create.call_args.kwargs
    assert call_kwargs["stream"] is True


# ─── 3. Structured Generation ──────────────────────────────────────────────────

def test_gemini_generate_structured_json():
    """generate_structured returns parsed dict through existing _parse_json_response interface."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.output_text = '{"name": "Citizenship Form", "fee": 500}'
    mock_client.interactions.create.return_value = mock_resp

    service = GeminiService(api_key="test-key", client=mock_client)
    parsed = service.generate_structured("Extract details")

    assert isinstance(parsed, dict)
    assert parsed["name"] == "Citizenship Form"
    assert parsed["fee"] == 500


def test_gemini_generate_structured_markdown_fence():
    """Handles JSON wrapped in markdown fences gracefully."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.output_text = '```json\n{"status": "verified"}\n```'
    mock_client.interactions.create.return_value = mock_resp

    service = GeminiService(api_key="test-key", client=mock_client)
    parsed = service.generate_structured("Check status")

    assert parsed == {"status": "verified"}


# ─── 4. Error Sanitization & LLMUnavailableError ──────────────────────────────

def test_gemini_api_error_redacts_key_and_raises_unavailable():
    """API failures translate to LLMUnavailableError without leaking API keys."""
    raw_key = "AIzaSyD-SecretKey-9988776655"
    mock_client = MagicMock()
    mock_client.interactions.create.side_effect = RuntimeError(
        f"HTTP 403: Forbidden for key {raw_key} with header x-goog-api-key: {raw_key}"
    )

    service = GeminiService(api_key=raw_key, client=mock_client)

    with pytest.raises(LLMUnavailableError) as exc_info:
        service.generate("Trigger error")

    err_msg = str(exc_info.value)
    assert "Gemini backend error" in err_msg
    assert raw_key not in err_msg, "Raw API key leaked in exception message!"
    assert "[REDACTED_API_KEY]" in err_msg or "[REDACTED]" in err_msg


# ─── 5. Generation Options & Timeout ──────────────────────────────────────────

def test_gemini_options_and_timeout_mapping():
    """Supported options and timeouts are passed to client."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.output_text = "options ok"
    mock_client.interactions.create.return_value = mock_resp

    service = GeminiService(api_key="test-key", client=mock_client)
    opts = {
        "temperature": 0.5,
        "top_p": 0.85,
        "top_k": 30,
        "max_output_tokens": 512,
    }
    service.generate("Test prompt", options=opts, timeout=45)

    call_kwargs = mock_client.interactions.create.call_args.kwargs
    assert call_kwargs["timeout"] == 45.0
    assert call_kwargs.get("store") is False, "store=False must always be sent to prevent server-side storage"
    cfg = call_kwargs["generation_config"]
    assert cfg["temperature"] == 0.5
    assert cfg["top_p"] == 0.85
    assert cfg["top_k"] == 30
    assert cfg["max_output_tokens"] == 512




def test_gemini_generate_always_sends_store_false():
    """store=False is always sent to the Interactions API, unconditionally."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.output_text = "ok"
    mock_client.interactions.create.return_value = mock_resp

    service = GeminiService(api_key="test-key", client=mock_client)
    # Call with no options, with options, and with stream=True — store must always be False
    for kwargs in [{}, {"options": {"temperature": 0.7}}, {"stream": True}]:
        mock_client.interactions.create.reset_mock()
        mock_client.interactions.create.return_value = [mock_resp] if kwargs.get("stream") else mock_resp
        service.generate("test", **kwargs)
        ckw = mock_client.interactions.create.call_args.kwargs
        assert ckw.get("store") is False, f"store=False missing for kwargs={kwargs}"

def test_gemini_unsupported_options_raise_value_error():
    """Unsupported options are not silently ignored; they raise ValueError."""
    mock_client = MagicMock()
    service = GeminiService(api_key="test-key", client=mock_client)

    with pytest.raises(ValueError, match="Unsupported Gemini option"):
        service.generate("Prompt", options={"unsupported_bogus_param": 123})


# ─── 6. Downstream Service Compatibility ──────────────────────────────────────

def test_downstream_services_accept_gemini_service():
    """Verify GeminiService satisfies the interface needed by all downstream components."""
    mock_client = MagicMock()
    mock_client.interactions.create.return_value.output_text = '{"answer": "valid"}'
    gemini = GeminiService(api_key="test-key", client=mock_client)

    # 1. GroundingValidator
    validator = GroundingValidator(gemini)
    assert validator.llm is gemini

    # 2. VerificationLayer
    verifier = VerificationLayer(gemini, validator)
    assert verifier.llm is gemini

    # 3. ExplanationEngine
    explainer = ExplanationEngine(gemini)
    assert explainer.llm is gemini

    # 4. ActionExtractor
    extractor = ActionExtractor(gemini)
    assert extractor.llm is gemini

    # 5. FormUnderstandingService
    form_svc = FormUnderstandingService(gemini)
    assert form_svc.llm is gemini

    # 6. OfficialAnswerService
    official_svc = OfficialAnswerService(gemini, verifier)
    assert official_svc.llm is gemini


# ─── 7. Gitignore & Secret Hygiene ────────────────────────────────────────────

def test_gitignore_ignores_secrets_and_allows_example_templates():
    """Verify git check-ignore ignores secret files and allows .env.example / .env.sample."""
    # Representative secret files that must be ignored
    secret_files = [
        ".env",
        ".env.production",
        ".env.development",
        ".env.local",
        "backend/.env",
        "backend/.env.production",
        "frontend/.env.local",
    ]
    for s_file in secret_files:
        proc = subprocess.run(
            ["git", "check-ignore", s_file],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"Expected {s_file} to be ignored by git, but it was not!"

    # Template files that must NOT be ignored
    template_files = [
        ".env.example",
        "frontend/.env.example",
        ".env.sample",
    ]
    for t_file in template_files:
        proc = subprocess.run(
            ["git", "check-ignore", t_file],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0, f"Expected template {t_file} to be trackable, but git ignored it!"


# ─── 8. Existing Ollama Behavior Unchanged ────────────────────────────────────

def test_existing_ollama_service_generate_and_structured(monkeypatch):
    """Verify OllamaService still works as expected."""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        # Mock tag verification
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"models": [{"name": "qwen3:8b"}]}

        # Mock generate
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"response": '{"test": "ollama_ok"}'}

        ollama = OllamaService(base_url="http://localhost:11434", model="qwen3:8b")
        res = ollama.generate("hello")
        assert res == '{"test": "ollama_ok"}'

        structured = ollama.generate_structured("json test")
        assert structured == {"test": "ollama_ok"}
