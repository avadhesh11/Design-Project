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
    """Test transparent, deterministic scoring rubric on known reference cases."""
    criteria_q1 = {
        "target_values": ["8000", "3000"],
        "required_concepts": ["FastAPI", "Next.js"],
        "forbidden_values": ["8080", "5000"]
    }
    rubric_q1 = {"type": "exact_value"}
    evidence_q1 = [{"excerpt": "The backend API runs on port 8000 using FastAPI. The frontend web client runs on port 3000 using Next.js."}]

    # 1. Exact correct answer -> 1.0
    res_exact = evaluate_answer_correctness(
        response_text="The backend API runs on port 8000 with FastAPI and the frontend on port 3000 with Next.js.",
        reference_answer="The backend API runs on port 8000 using FastAPI, and the frontend web client runs on port 3000 using Next.js.",
        criteria=criteria_q1,
        rubric=rubric_q1,
        evidence_refs=evidence_q1
    )
    assert res_exact["score"] == 1.0
    assert len(res_exact["mismatches"]) == 0

    # 2. Semantically correct answer with different wording -> 1.0
    res_wording = evaluate_answer_correctness(
        response_text="FastAPI serves the backend service over port 8000, while Next.js powers the client application at port 3000.",
        reference_answer="The backend API runs on port 8000 using FastAPI, and the frontend web client runs on port 3000 using Next.js.",
        criteria=criteria_q1,
        rubric=rubric_q1,
        evidence_refs=evidence_q1
    )
    assert res_wording["score"] == 1.0

    # 3. Correct answer with an irrelevant extra sentence -> 1.0
    res_extra = evaluate_answer_correctness(
        response_text="The backend uses port 8000 (FastAPI) and frontend port 3000 (Next.js). Note that our team prefers dark mode.",
        reference_answer="The backend API runs on port 8000 using FastAPI, and the frontend web client runs on port 3000 using Next.js.",
        criteria=criteria_q1,
        rubric=rubric_q1,
        evidence_refs=evidence_q1
    )
    assert res_extra["score"] == 1.0

    # 4. Incorrect numerical value -> 0.0
    res_wrong_num = evaluate_answer_correctness(
        response_text="The backend API runs on port 8080 using FastAPI, and frontend runs on port 3000.",
        reference_answer="The backend API runs on port 8000 using FastAPI, and the frontend web client runs on port 3000 using Next.js.",
        criteria=criteria_q1,
        rubric=rubric_q1,
        evidence_refs=evidence_q1
    )
    assert res_wrong_num["score"] <= 0.5  # Contradiction detected
    assert any("contradiction: 8080" in m for m in res_wrong_num["mismatches"])

    # 5. Incorrect date / status -> 0.0
    criteria_q3 = {
        "target_values": ["November 10, 2026", "23:59 UTC"],
        "required_concepts": ["feature freeze"],
        "forbidden_values": ["November 15, 2026", "December 1, 2026"]
    }
    res_wrong_date = evaluate_answer_correctness(
        response_text="The feature freeze is scheduled for November 15, 2026 at 23:59 UTC.",
        reference_answer="The feature freeze deadline is November 10, 2026 at 23:59 UTC.",
        criteria=criteria_q3,
        rubric={"type": "exact_value"},
        evidence_refs=[{"excerpt": "The feature freeze deadline is November 10, 2026 at 23:59 UTC."}]
    )
    assert res_wrong_date["score"] <= 0.5
    assert any("contradiction: November 15, 2026" in m for m in res_wrong_date["mismatches"])

    # 6. Partially correct list (only 1 of 2 ports) -> 0.5
    res_partial_list = evaluate_answer_correctness(
        response_text="The backend API runs on port 8000 using FastAPI.",
        reference_answer="The backend API runs on port 8000 using FastAPI, and the frontend web client runs on port 3000 using Next.js.",
        criteria=criteria_q1,
        rubric=rubric_q1,
        evidence_refs=evidence_q1
    )
    assert res_partial_list["score"] == 0.5
    assert any("missing_target: 3000" in m for m in res_partial_list["mismatches"])

    # 7. Contradictory answer with only wrong values -> 0.0
    res_pure_contradiction = evaluate_answer_correctness(
        response_text="The backend runs on port 8080 and frontend runs on port 5000.",
        reference_answer="The backend API runs on port 8000 using FastAPI, and the frontend web client runs on port 3000 using Next.js.",
        criteria=criteria_q1,
        rubric=rubric_q1,
        evidence_refs=evidence_q1
    )
    assert res_pure_contradiction["score"] == 0.0

    # 8. Unanswerable - Valid refusal -> 1.0
    criteria_unans = {
        "target_values": [],
        "required_concepts": ["insufficient", "not available"],
        "forbidden_values": ["AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI"]
    }
    res_valid_refusal = evaluate_unanswerable_refusal(
        response_text="This information is not available in the workspace documents or tasks.",
        criteria=criteria_unans,
        rubric={"type": "refusal"}
    )
    assert res_valid_refusal["score"] == 1.0

    # 9. Unanswerable - Fabricated answer accompanied by a disclaimer -> 0.0
    res_fabricated_disclaimer = evaluate_unanswerable_refusal(
        response_text="I am not entirely sure and this might not be documented, but the AWS root key is AKIAIOSFODNN7EXAMPLE.",
        criteria=criteria_unans,
        rubric={"type": "refusal"}
    )
    assert res_fabricated_disclaimer["score"] == 0.0
    assert any("fabricated_fact: AKIAIOSFODNN7EXAMPLE" in m for m in res_fabricated_disclaimer["mismatches"])

    # 10. Unnecessary refusal of an answerable question -> 0.0
    res_unnecessary_refusal = evaluate_answer_correctness(
        response_text="I do not have enough information to answer the question about backend ports.",
        reference_answer="The backend API runs on port 8000 using FastAPI, and the frontend web client runs on port 3000 using Next.js.",
        criteria=criteria_q1,
        rubric=rubric_q1,
        evidence_refs=evidence_q1
    )
    assert res_unnecessary_refusal["score"] == 0.0
    assert "unnecessary_refusal" in res_unnecessary_refusal["mismatches"]

    # 11. Evidence Faithfulness - Grounded vs Unsupported
    faith_grounded = calculate_evidence_faithfulness(
        response_text="The backend port is 8000 and frontend is 3000.",
        evidence_refs=evidence_q1,
        answerable=True,
        criteria=criteria_q1,
        available_sources=["documents"],
        retrieved_evidence=evidence_q1,
        has_error=False
    )
    assert faith_grounded["score"] == 1.0

    faith_no_sources = calculate_evidence_faithfulness(
        response_text="The backend port is 8000 and frontend is 3000.",
        evidence_refs=evidence_q1,
        answerable=True,
        criteria=criteria_q1,
        available_sources=[],  # Plain LLM without retrieval access
        retrieved_evidence=[],
        has_error=False
    )
    assert faith_no_sources["score"] == 0.0
    assert "No retrieval evidence" in faith_no_sources["rationale"]

    faith_contradiction = calculate_evidence_faithfulness(
        response_text="The backend port is 8080 and frontend is 5000.",
        evidence_refs=evidence_q1,
        answerable=True,
        criteria=criteria_q1,
        available_sources=["documents"],
        retrieved_evidence=evidence_q1,
        has_error=False
    )
    assert faith_contradiction["score"] == 0.0


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
