from unittest.mock import MagicMock
from evaluation.configs import get_llm_metadata
from evaluation.run_evaluation import sanitize_secret, MockEvaluationLLM


def test_get_llm_metadata_from_mock():
    """Verify metadata extraction from MockEvaluationLLM."""
    mock_llm = MockEvaluationLLM(model_name="test-mock-3.5")
    meta = get_llm_metadata(mock_llm, configured_model="gemini-2.5-flash", provider="gemini")

    assert meta["resolved_model"] == "test-mock-3.5"
    assert meta["configured_model"] == "gemini-2.5-flash"
    assert meta["provider"] == "gemini"


def test_get_llm_metadata_from_langchain_object():
    """Verify metadata extraction from a LangChain chat model instance."""
    fake_llm = MagicMock()
    fake_llm.model = "gemini-2.5-flash"
    fake_llm.temperature = 0.2

    meta = get_llm_metadata(fake_llm, configured_model="gemini-2.5-flash", provider="gemini")
    assert meta["resolved_model"] == "gemini-2.5-flash"
    assert meta["configured_model"] == "gemini-2.5-flash"
    assert meta["parameters"]["temperature"] == 0.2


def test_get_llm_metadata_preserves_discrepancy():
    """
    Ensure the runner does not hide or overwrite a mismatch between
    what was requested in config and what the LLM provider instance resolved.
    """
    fake_llm = MagicMock()
    fake_llm.model = "gemini-2.5-pro"  # Different from configured!
    fake_llm.temperature = 0.0

    meta = get_llm_metadata(fake_llm, configured_model="gemini-2.5-flash", provider="gemini")
    assert meta["configured_model"] == "gemini-2.5-flash"
    assert meta["resolved_model"] == "gemini-2.5-pro"
    assert meta["configured_model"] != meta["resolved_model"]


def test_sanitize_secret_removes_sensitive_tokens():
    """Verify regex secret sanitization removes API keys, bearer tokens, and DB passwords."""
    raw_error = "Error connecting with AIzaSyD-761829034567890123456789012345 to postgresql://postgres:SecretPassword123@db.supabase.co:5432/postgres using Bearer eyJhbGciOiJIUzI1Ni.secret.token"
    sanitized = sanitize_secret(raw_error)

    assert "[REDACTED_API_KEY]" in sanitized
    assert "AIzaSyD" not in sanitized
    assert "[REDACTED_PASSWORD]" in sanitized
    assert "SecretPassword123" not in sanitized
    assert "[REDACTED_TOKEN]" in sanitized
    assert "eyJhbGciOiJIUzI1Ni" not in sanitized


def test_get_llm_metadata_missing_attributes_marked_unknown():
    """
    CRITICAL ATTRIBUTION TEST:
    When an LLM instance lacks model or temperature attributes,
    metadata MUST be recorded as unknown/None, never fabricated as verified runtime metadata.
    """
    uninstrumented_llm = object()  # Bare object with no model attributes
    meta = get_llm_metadata(uninstrumented_llm)

    assert meta["resolved_model"] == "unknown"
    assert meta["runtime_resolved_model"] is None
    assert meta["is_runtime_verified"] is False
    assert meta["temperature"] is None, "Must not fabricate a default temperature as verified runtime metadata"
    assert meta["parameters"]["temperature"] is None


def test_get_llm_metadata_distinguishes_sources():
    """Verify tracking of model_source across explicit config, DB, or env."""
    mock_llm = MockEvaluationLLM(model_name="gemini-2.5-flash")

    # Explicit config source
    meta_explicit = get_llm_metadata(mock_llm, configured_model="gemini-2.5-flash")
    assert meta_explicit["model_source"] == "explicit_config"
    assert meta_explicit["is_runtime_verified"] is True

