import json
import tempfile
import asyncio
from pathlib import Path
import pytest

from evaluation.configs import CONFIGURATION_NAMES, CONFIG_DEFINITIONS, execute_evaluation_configuration
from evaluation.run_evaluation import load_dataset, run_evaluation, MockEvaluationLLM
from evaluation.score_results import (
    evaluate_unanswerable_refusal,
    evaluate_answer_correctness,
    calculate_evidence_faithfulness,
    compute_stats,
    score_results
)


def test_configuration_definitions():
    """Verify the three required evaluation configurations are defined with correct properties."""
    assert set(CONFIGURATION_NAMES) == {"plain_llm", "rag_docs_only", "full_agent"}

    # Plain LLM
    plain = CONFIG_DEFINITIONS["plain_llm"]
    assert plain["has_tools"] is False
    assert plain["has_documents"] is False
    assert plain["has_tasks"] is False
    assert plain["has_chat"] is False
    assert plain["type"] == "direct_chat"

    # Documents-only RAG
    rag = CONFIG_DEFINITIONS["rag_docs_only"]
    assert rag["has_tools"] is True
    assert rag["has_documents"] is True
    assert rag["has_tasks"] is False
    assert rag["has_chat"] is False
    assert rag["eval_config"].documents is True
    assert rag["eval_config"].tasks is False
    assert rag["eval_config"].chat is False
    assert rag["eval_config"].preinject_documents is True
    assert rag["eval_config"].allow_admin_actions is False

    # Full Orbit Agent
    agent = CONFIG_DEFINITIONS["full_agent"]
    assert agent["has_tools"] is True
    assert agent["has_documents"] is True
    assert agent["has_tasks"] is True
    assert agent["has_chat"] is True
    assert agent["eval_config"].documents is True
    assert agent["eval_config"].tasks is True
    assert agent["eval_config"].chat is True
    assert agent["eval_config"].preinject_documents is True
    assert agent["eval_config"].allow_admin_actions is False


def test_dataset_schema_and_allocation():
    """Verify the questions.json dataset schema, allocation, and field types."""
    dataset_path = Path(__file__).resolve().parent.parent / "evaluation" / "questions.json"
    questions = load_dataset(dataset_path)

    assert len(questions) == 20

    categories = [q["category"] for q in questions]
    assert categories.count("single_source") == 8
    assert categories.count("multi_source") == 8
    assert categories.count("unanswerable") == 4

    seen_ids = set()
    for q in questions:
        assert q["id"] not in seen_ids
        seen_ids.add(q["id"])
        assert isinstance(q["question"], str) and len(q["question"].strip()) > 0
        assert isinstance(q["category"], str)
        assert isinstance(q["required_sources"], list)
        assert isinstance(q["reference_answer"], str)
        assert isinstance(q["answerable"], bool)
        assert isinstance(q["evidence_references"], list)

        if not q["answerable"]:
            assert q["category"] == "unanswerable"
            assert q["required_sources"] == []


def test_scoring_rubric_on_known_cases():
    """Test transparent scoring rubric on known reference cases."""
    # 1. Answerable - Exact/high overlap -> 1.0
    res_high = evaluate_answer_correctness(
        response_text="The session timeout is enforced at exactly 15 minutes of inactivity.",
        reference_answer="The session timeout is enforced at exactly 15 minutes of inactivity.",
        evidence_refs=[{"excerpt": "Session timeout is enforced at exactly 15 minutes of inactivity."}]
    )
    assert res_high == 1.0

    # 2. Answerable - Partial overlap -> 0.5
    res_partial = evaluate_answer_correctness(
        response_text="Session timeout is roughly 15 minutes according to policy.",
        reference_answer="The session timeout is enforced at exactly 15 minutes of inactivity.",
        evidence_refs=[{"excerpt": "Session timeout is enforced at exactly 15 minutes of inactivity."}]
    )
    assert res_partial == 0.5

    # 3. Answerable - Completely wrong -> 0.0
    res_wrong = evaluate_answer_correctness(
        response_text="The database runs on port 5432 with default settings.",
        reference_answer="The session timeout is enforced at exactly 15 minutes of inactivity.",
        evidence_refs=[{"excerpt": "Session timeout is enforced at exactly 15 minutes of inactivity."}]
    )
    assert res_wrong == 0.0

    # 4. Unanswerable - Proper refusal -> 1.0
    refusal_score = evaluate_unanswerable_refusal("This information is not available in the workspace documents.")
    assert refusal_score == 1.0

    # 5. Unanswerable - Hallucinated fabrication -> 0.0
    hallucination_score = evaluate_unanswerable_refusal("The root AWS key is AKIAIOSFODNN7EXAMPLE and secret is wJalrXUtnFEMI.")
    assert hallucination_score == 0.0


def test_compute_stats():
    """Test statistics computation for latencies and token counts."""
    values = [100.0, 200.0, 300.0, 400.0, 500.0]
    stats = compute_stats(values)
    assert stats["mean"] == 300.0
    assert stats["median"] == 300.0
    assert stats["min"] == 100.0
    assert stats["max"] == 500.0
    assert stats["stddev"] > 0

    empty_stats = compute_stats([])
    assert empty_stats["mean"] is None


def test_runner_and_scoring_end_to_end_mock():
    """Execute end-to-end evaluation run and scoring with Mock LLM in a temporary directory."""
    async def _test():
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            dataset_path = Path(__file__).resolve().parent.parent / "evaluation" / "questions.json"
            output_dir = tmp_path / "results"
            reports_dir = tmp_path / "reports"

            # Run evaluation on first 2 questions for all 3 configurations
            output_file = await run_evaluation(
                configs=["plain_llm", "rag_docs_only", "full_agent"],
                questions_file=dataset_path,
                output_dir=output_dir,
                limit=2,
                mock_mode=True,
                workspace_id="00000000-0000-4000-8000-000000000001",
                user_id="00000000-0000-4000-8000-000000000003",
                user_email="eval-dev1@synthetic.orbit.local"
            )

            assert output_file.exists()

            # Verify JSONL lines count: 2 questions * 3 configs = 6 lines
            with open(output_file, "r", encoding="utf-8") as f:
                lines = [json.loads(line) for line in f if line.strip()]
            assert len(lines) == 6

            for record in lines:
                assert "run_id" in record
                assert "question_id" in record
                assert "configuration" in record
                assert "latency_ms" in record
                assert record["configuration"] in CONFIGURATION_NAMES

            # Run scoring on the output
            scoring_res = score_results(output_file, reports_dir)
            assert Path(scoring_res["summary_csv"]).exists()
            assert Path(scoring_res["scored_json"]).exists()
            assert len(scoring_res["summary"]) > 0

    asyncio.run(_test())
