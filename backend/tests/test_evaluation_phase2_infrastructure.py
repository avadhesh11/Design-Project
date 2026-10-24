import os
import json
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import requests

from evaluation.configs import get_llm_metadata, execute_evaluation_configuration
from evaluation.run_evaluation import (
    load_dataset,
    run_evaluation,
    validate_environment,
    MockEvaluationLLM
)
from evaluation.scheduler import generate_evaluation_schedule, VALID_SCHEDULE_STRATEGIES
from app.utils.llm_factory import get_chat_llm
from app.utils.ollama_fallback import OllamaChatFallback


def test_default_gemini_selection_and_no_num_ctx(monkeypatch):
    """1. Existing default invocation selects Gemini and does not pass num_ctx."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key_for_test")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")

    llm = get_chat_llm(temperature=0.3)
    meta = get_llm_metadata(llm)

    assert meta["provider"] == "gemini"
    assert "gemini" in meta["resolved_model"].lower()
    assert meta["temperature"] == 0.3
    # Gemini must not have num_ctx in parameters
    assert "num_ctx" not in meta["parameters"]


def test_explicit_ollama_receives_all_parameters(monkeypatch):
    """2 & 3. Ollama receives explicit model tag, base_url, temperature, and num_ctx=8192."""
    mock_tags = MagicMock()
    mock_tags.status_code = 200
    mock_tags.json.return_value = {"models": [{"name": "llama3.2:3b"}]}

    with patch("requests.get", return_value=mock_tags):
        llm = get_chat_llm(
            provider="ollama",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
            temperature=0.7,
            num_ctx=8192
        )

    assert isinstance(llm, OllamaChatFallback)
    assert llm.model == "llama3.2:3b"
    assert llm.base_url == "http://localhost:11434"
    assert llm.temperature == 0.7
    assert llm.num_ctx == 8192

    meta = get_llm_metadata(llm)
    assert meta["provider"] == "ollama"
    assert meta["resolved_model"] == "llama3.2:3b"
    assert meta["parameters"]["num_ctx"] == 8192
    assert meta["parameters"]["temperature"] == 0.7


def test_gemini_ignores_ollama_context_parameters(monkeypatch):
    """4. Gemini does not receive Ollama-specific context parameters."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key_for_test")

    llm = get_chat_llm(provider="gemini", model="gemini-2.5-flash", num_ctx=8192)
    meta = get_llm_metadata(llm)

    assert meta["provider"] == "gemini"
    assert "num_ctx" not in meta["parameters"]


def test_invalid_parameters_rejected():
    """5. Invalid provider, temperature, and context window values are rejected."""
    # Invalid provider
    with pytest.raises(ValueError, match="Unsupported provider"):
        get_chat_llm(provider="unsupported_engine")

    # Invalid temperatures
    with pytest.raises(ValueError, match="Invalid temperature"):
        get_chat_llm(provider="gemini", temperature=-0.1)

    with pytest.raises(ValueError, match="Invalid temperature"):
        get_chat_llm(provider="gemini", temperature=2.5)

    # Invalid context window sizes
    with pytest.raises(ValueError, match="Invalid context window size"):
        get_chat_llm(provider="ollama", num_ctx=128)

    with pytest.raises(ValueError, match="Invalid context window size"):
        get_chat_llm(provider="ollama", num_ctx=200000)


def test_mock_mode_without_credentials_or_ollama():
    """6. Mock mode runs without a live Ollama server or external API credentials."""
    # validate_environment must succeed without error in mock mode even with empty env
    with patch.dict(os.environ, {}, clear=True):
        validate_environment(mock_mode=True, provider="gemini")
        validate_environment(mock_mode=True, provider="ollama")

    mock_llm = MockEvaluationLLM(model_name="mock-test", temperature=0.3)
    meta = get_llm_metadata(mock_llm)
    assert meta["provider"] == "mock"
    assert meta["resolved_model"] == "mock-test"


def test_ollama_unavailable_or_missing_model_clear_error():
    """7. Missing Ollama service or model produces a clear error and does not silently switch."""
    # 7a. Ollama service unavailable
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        with pytest.raises(RuntimeError, match="Ollama service is unavailable"):
            get_chat_llm(provider="ollama", model="llama3.2:3b")

    # 7b. Model not found in Ollama installed tags: must error, NEVER silently switch models
    mock_tags = MagicMock()
    mock_tags.status_code = 200
    mock_tags.json.return_value = {"models": [{"name": "qwen2.5:7b"}, {"name": "mistral:7b"}]}

    with patch("requests.get", return_value=mock_tags):
        with pytest.raises(RuntimeError, match="not found in Ollama"):
            get_chat_llm(provider="ollama", model="llama3.2:3b")


def test_provenance_and_backward_compatible_records():
    """8 & 9. Run-level and attempt metadata recorded with all fields and no leaked secrets."""
    async def _test():
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            dataset_path = Path(__file__).resolve().parent.parent / "evaluation" / "questions.json"
            output_dir = tmp_path / "results"

            output_file = await run_evaluation(
                configs=["plain_llm", "rag_docs_only"],
                questions_file=dataset_path,
                output_dir=output_dir,
                limit=1,
                run_id="test_provenance_run",
                mock_mode=True,
                temperature=0.3,
                schedule_strategy="sequential"
            )

            assert output_file.exists()
            meta_file = output_dir / "meta_test_provenance_run.json"
            assert meta_file.exists()

            with open(meta_file, "r", encoding="utf-8") as mf:
                meta = json.load(mf)

            # Check run-level provenance
            assert meta["run_id"] == "test_provenance_run"
            assert meta["provider"] == "mock"
            assert meta["temperature"] == 0.3
            assert meta["total_attempts"] == 2
            assert meta["successful_attempts"] == 2
            assert "start_time" in meta
            assert "end_time" in meta
            assert "duration_seconds" in meta
            assert "git_commit" in meta

            # Check attempt-level fields for backward compatibility
            with open(output_file, "r", encoding="utf-8") as f:
                records = [json.loads(line) for line in f if line.strip()]

            assert len(records) == 2
            required_fields = [
                "run_id", "timestamp", "question_id", "question", "category",
                "required_sources", "answerable", "reference_answer", "evidence_references",
                "evaluation_criteria", "rubric", "configuration", "configured_model",
                "resolved_model", "model_parameters", "provider", "available_sources",
                "execution_status", "response", "tools_used", "retrieved_evidence",
                "latency_ms", "token_usage", "error"
            ]
            for r in records:
                for field in required_fields:
                    assert field in r, f"Missing required field: '{field}'"
                assert r["execution_status"] == "success"
                assert "temperature" in r["model_parameters"]

    asyncio.run(_test())


def test_deterministic_scheduling_strategies():
    """10. Interleaving is deterministic and preserves questions/configs."""
    mock_questions = [
        {"id": "Q01", "category": "single_source"},
        {"id": "Q02", "category": "multi_source"}
    ]
    configs = ["plain_llm", "rag_docs_only", "full_agent"]

    # 1. Sequential / by_question: Interleaved by question (Q1/C1, Q1/C2, Q1/C3, Q2/C1, Q2/C2, Q2/C3)
    sched_seq = generate_evaluation_schedule(mock_questions, configs, schedule_strategy="sequential")
    assert len(sched_seq) == 6
    expected_seq_pairs = [
        ("Q01", "plain_llm"), ("Q01", "rag_docs_only"), ("Q01", "full_agent"),
        ("Q02", "plain_llm"), ("Q02", "rag_docs_only"), ("Q02", "full_agent")
    ]
    actual_seq_pairs = [(item["question_id"], item["configuration"]) for item in sched_seq]
    assert actual_seq_pairs == expected_seq_pairs

    # 2. By configuration: Grouped by config (C1/Q1, C1/Q2, C2/Q1, C2/Q2, C3/Q1, C3/Q2)
    sched_cfg = generate_evaluation_schedule(mock_questions, configs, schedule_strategy="by_configuration")
    expected_cfg_pairs = [
        ("Q01", "plain_llm"), ("Q02", "plain_llm"),
        ("Q01", "rag_docs_only"), ("Q02", "rag_docs_only"),
        ("Q01", "full_agent"), ("Q02", "full_agent")
    ]
    actual_cfg_pairs = [(item["question_id"], item["configuration"]) for item in sched_cfg]
    assert actual_cfg_pairs == expected_cfg_pairs

    # 3. Randomized with seed: reproducible
    sched_rand1 = generate_evaluation_schedule(mock_questions, configs, schedule_strategy="randomized", seed=42)
    sched_rand2 = generate_evaluation_schedule(mock_questions, configs, schedule_strategy="randomized", seed=42)
    sched_rand_diff = generate_evaluation_schedule(mock_questions, configs, schedule_strategy="randomized", seed=999)

    order1 = [(it["question_id"], it["configuration"]) for it in sched_rand1]
    order2 = [(it["question_id"], it["configuration"]) for it in sched_rand2]
    order_diff = [(it["question_id"], it["configuration"]) for it in sched_rand_diff]

    assert order1 == order2
    assert order1 != order_diff

    # Randomized without seed must raise ValueError
    with pytest.raises(ValueError, match="random seed must be provided"):
        generate_evaluation_schedule(mock_questions, configs, schedule_strategy="randomized", seed=None)


def test_custom_dataset_schema_validation(tmp_path):
    """11. A custom dataset path is schema-validated with informative errors."""
    # Valid custom dataset
    valid_data = {
        "questions": [
            {
                "id": "T01",
                "question": "What is the test question?",
                "category": "single_source",
                "required_sources": ["documents"],
                "reference_answer": "Test answer.",
                "answerable": True,
                "evidence_references": []
            }
        ]
    }
    valid_file = tmp_path / "valid_questions.json"
    with open(valid_file, "w", encoding="utf-8") as f:
        json.dump(valid_data, f)

    loaded = load_dataset(valid_file)
    assert len(loaded) == 1
    assert loaded[0]["id"] == "T01"

    # Missing required field
    invalid_data = {
        "questions": [
            {
                "id": "T02",
                "question": "Missing category",
                "required_sources": [],
                "reference_answer": "Test.",
                "answerable": True
            }
        ]
    }
    invalid_file = tmp_path / "invalid_questions.json"
    with open(invalid_file, "w", encoding="utf-8") as f:
        json.dump(invalid_data, f)

    with pytest.raises(ValueError, match="missing required field"):
        load_dataset(invalid_file)

    # Invalid category
    bad_cat_data = {
        "questions": [
            {
                "id": "T03",
                "question": "Bad category",
                "category": "not_a_valid_category",
                "required_sources": [],
                "reference_answer": "Test.",
                "answerable": True
            }
        ]
    }
    bad_cat_file = tmp_path / "bad_cat_questions.json"
    with open(bad_cat_file, "w", encoding="utf-8") as f:
        json.dump(bad_cat_data, f)

    with pytest.raises(ValueError, match="invalid category"):
        load_dataset(bad_cat_file)


def test_ollama_fallback_bind_tools_and_messages():
    """12. OllamaChatFallback tool binding and message conversion."""
    fallback = OllamaChatFallback(model="llama3.2:3b", base_url="http://localhost:11434")

    # Mock tool
    def mock_search(query: str) -> str:
        """Search tool."""
        return "result"

    bound = fallback.bind_tools([mock_search])
    assert isinstance(bound, OllamaChatFallback)
    assert bound.bound_tools is not None
    assert len(bound.bound_tools) == 1
    assert bound.bound_tools[0]["function"]["name"] == "mock_search"
