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

    # 11. Misleading substring match prevention: '8000' must NOT match inside '18000' or '80000'
    res_misleading_substring = evaluate_answer_correctness(
        response_text="The backend API runs on port 18000 using FastAPI, and frontend runs on port 80000.",
        reference_answer="The backend API runs on port 8000 using FastAPI, and the frontend web client runs on port 3000 using Next.js.",
        criteria=criteria_q1,
        rubric=rubric_q1,
        evidence_refs=evidence_q1
    )
    assert res_misleading_substring["score"] == 0.0
    assert any("missing_target: 8000" in m for m in res_misleading_substring["mismatches"])
    assert any("missing_target: 3000" in m for m in res_misleading_substring["mismatches"])

    # 12. Evidence Faithfulness - Grounded vs Missing Evidence vs Unsupported
    faith_grounded = calculate_evidence_faithfulness(
        response_text="The backend port is 8000 and frontend is 3000.",
        answerable=True,
        criteria=criteria_q1,
        available_sources=["documents"],
        retrieved_evidence=evidence_q1,
        has_error=False
    )
    assert faith_grounded["score"] == 1.0
    assert faith_grounded["status"] == "faithful"

    # Missing Evidence / Plain LLM: Faithfulness must be marked NOT EVALUABLE (score=None), never fabricated
    faith_no_sources = calculate_evidence_faithfulness(
        response_text="The backend port is 8000 and frontend is 3000.",
        answerable=True,
        criteria=criteria_q1,
        available_sources=[],  # Plain LLM without retrieval access
        retrieved_evidence=[],
        has_error=False
    )
    assert faith_no_sources["score"] is None
    assert faith_no_sources["status"] == "not_evaluable"
    assert "not evaluable" in faith_no_sources["rationale"]

    # Model had retrieval access, but tool returned no chunks -> Faithfulness is NOT EVALUABLE
    faith_missing_chunks = calculate_evidence_faithfulness(
        response_text="The backend port is 8000 and frontend is 3000.",
        answerable=True,
        criteria=criteria_q1,
        available_sources=["documents"],
        retrieved_evidence=[],  # Tool retrieved zero evidence
        has_error=False
    )
    assert faith_missing_chunks["score"] is None
    assert faith_missing_chunks["status"] == "not_evaluable"
    assert "No evidence was retrieved" in faith_missing_chunks["rationale"]

    # Retrieved evidence does not support claims
    faith_unsupported = calculate_evidence_faithfulness(
        response_text="The backend port is 8000 and frontend is 3000.",
        answerable=True,
        criteria=criteria_q1,
        available_sources=["documents"],
        retrieved_evidence=[{"excerpt": "Orbit is deployed on port 9090."}],
        has_error=False
    )
    assert faith_unsupported["score"] == 0.0
    assert faith_unsupported["status"] == "unsupported"

    # Retrieved evidence contradicted by response
    faith_contradiction = calculate_evidence_faithfulness(
        response_text="The backend port is 8080 and frontend is 5000.",
        answerable=True,
        criteria=criteria_q1,
        available_sources=["documents"],
        retrieved_evidence=evidence_q1,
        has_error=False
    )
    assert faith_contradiction["score"] == 0.0
    assert faith_contradiction["status"] == "contradiction"


def test_scoring_q01_regression_supported_correct_answer():
    """
    Regression test for Q01 scoring discrepancy:
    - Answer states 15 minutes of inactivity without contradictory durations.
    - Retrieved evidence contains the exact policy excerpt.
    - Correctness must be 1.0 (all target values and concepts verified).
    - Faithfulness must be 1.0 (grounded in actual evidence text).
    - Proves '5 minutes' is NOT falsely matched as a substring of '15 minutes'.
    - Proves alternative representations ('15 minutes', '15 min') are recognized.
    """
    criteria_q01 = {
        "target_values": ["15 minutes", "15 min", "fifteen minutes"],
        "required_concepts": ["session", "timeout", "inactivity"],
        "forbidden_values": ["30 minutes", "1 hour", "5 minutes", "20 minutes", "10 minutes", "60 minutes"]
    }
    rubric_q01 = {
        "type": "exact_value",
        "description": "1.0 if states 15 minutes of inactivity without contradictory durations; 0.5 if mentions 15 minutes without specifying inactivity; 0.0 otherwise."
    }
    retrieved_evidence_q01 = [
        {
            "source": "documents",
            "content": "Orbit Workspace Security & Compliance Policy:\n- Session timeout is enforced at exactly 15 minutes of inactivity.\n- Two-factor authentication (2FA) is mandatory for all members with administrative roles."
        }
    ]

    # Exact live agent answer from pilot_live_v2
    resp_text = "According to the Orbit Workspace Security & Compliance Policy, the required session timeout length is enforced at exactly 15 minutes of inactivity."

    corr = evaluate_answer_correctness(
        response_text=resp_text,
        reference_answer="The session timeout is enforced at exactly 15 minutes of inactivity.",
        criteria=criteria_q01,
        rubric=rubric_q01,
        evidence_refs=retrieved_evidence_q01
    )
    assert corr["score"] == 1.0
    assert len(corr["mismatches"]) == 0
    assert "Complete factual match" in corr["rationale"]

    faith = calculate_evidence_faithfulness(
        response_text=resp_text,
        answerable=True,
        criteria=criteria_q01,
        available_sources=["documents"],
        retrieved_evidence=retrieved_evidence_q01,
        has_error=False
    )
    assert faith["score"] == 1.0
    assert faith["status"] == "faithful"
    assert "15 minutes" in faith["rationale"]

    # Alternative phrasing with '15 min'
    resp_alt = "Session timeout is enforced at exactly 15 min of inactivity."
    corr_alt = evaluate_answer_correctness(
        response_text=resp_alt,
        reference_answer="The session timeout is enforced at exactly 15 minutes of inactivity.",
        criteria=criteria_q01,
        rubric=rubric_q01
    )
    assert corr_alt["score"] == 1.0


def test_scoring_q01_partial_answer_without_inactivity():
    """Q01 rubric specifies 0.5 if mentions 15 minutes without specifying inactivity."""
    criteria_q01 = {
        "target_values": ["15 minutes", "15 min", "fifteen minutes"],
        "required_concepts": ["session", "timeout", "inactivity"],
        "forbidden_values": ["30 minutes", "1 hour", "5 minutes", "20 minutes", "10 minutes", "60 minutes"]
    }
    rubric_q01 = {
        "type": "exact_value",
        "description": "1.0 if states 15 minutes of inactivity without contradictory durations; 0.5 if mentions 15 minutes without specifying inactivity; 0.0 otherwise."
    }

    resp_no_inactivity = "The required session timeout length is 15 minutes."
    corr = evaluate_answer_correctness(
        response_text=resp_no_inactivity,
        reference_answer="The session timeout is enforced at exactly 15 minutes of inactivity.",
        criteria=criteria_q01,
        rubric=rubric_q01
    )
    assert corr["score"] == 0.5
    assert "without specifying inactivity" in corr["rationale"]
    assert any("missing_concept: inactivity" in m for m in corr["mismatches"])


def test_scoring_q01_forbidden_duration_contradiction():
    """Q01 answer stating a contradictory duration (e.g. 5 minutes) must be scored <= 0.5 or 0.0."""
    criteria_q01 = {
        "target_values": ["15 minutes", "15 min", "fifteen minutes"],
        "required_concepts": ["session", "timeout", "inactivity"],
        "forbidden_values": ["30 minutes", "1 hour", "5 minutes", "20 minutes", "10 minutes", "60 minutes"]
    }
    rubric_q01 = {
        "type": "exact_value",
        "description": "1.0 if states 15 minutes of inactivity without contradictory durations; 0.5 if mentions 15 minutes without specifying inactivity; 0.0 otherwise."
    }
    retrieved_evidence_q01 = [
        {"content": "Session timeout is enforced at exactly 15 minutes of inactivity."}
    ]

    resp_wrong = "The session timeout is enforced at 5 minutes of inactivity."
    corr = evaluate_answer_correctness(
        response_text=resp_wrong,
        reference_answer="The session timeout is enforced at exactly 15 minutes of inactivity.",
        criteria=criteria_q01,
        rubric=rubric_q01
    )
    assert corr["score"] == 0.0
    assert any("contradiction: 5 minutes" in m for m in corr["mismatches"])

    faith = calculate_evidence_faithfulness(
        response_text=resp_wrong,
        answerable=True,
        criteria=criteria_q01,
        available_sources=["documents"],
        retrieved_evidence=retrieved_evidence_q01,
        has_error=False
    )
    assert faith["score"] == 0.0
    assert faith["status"] == "contradiction"


def test_scoring_preserves_faithfulness_and_correctness_separation():
    """
    Preserve separation: a correct answer NOT supported by retrieved evidence
    must be scored correctness=1.0 but faithfulness=0.0 (unsupported).
    """
    criteria_q01 = {
        "target_values": ["15 minutes", "15 min", "fifteen minutes"],
        "required_concepts": ["session", "timeout", "inactivity"],
        "forbidden_values": ["30 minutes", "1 hour", "5 minutes"]
    }
    rubric_q01 = {"type": "exact_value", "description": "1.0 if states 15 minutes of inactivity"}

    # Answer is factually correct
    resp_correct = "Session timeout is enforced at exactly 15 minutes of inactivity."
    corr = evaluate_answer_correctness(
        response_text=resp_correct,
        reference_answer="The session timeout is enforced at exactly 15 minutes of inactivity.",
        criteria=criteria_q01,
        rubric=rubric_q01
    )
    assert corr["score"] == 1.0

    # But retrieved evidence does NOT mention 15 minutes (e.g. only mentions Redis connection pool)
    unrelated_evidence = [
        {"source": "documents", "content": "Redis caching is deployed on port 6379 for real-time pub/sub."}
    ]
    faith = calculate_evidence_faithfulness(
        response_text=resp_correct,
        answerable=True,
        criteria=criteria_q01,
        available_sources=["documents"],
        retrieved_evidence=unrelated_evidence,
        has_error=False
    )
    assert faith["score"] == 0.0
    assert faith["status"] == "unsupported"
    assert "absent from actually retrieved evidence" in faith["rationale"]


def test_scoring_plain_llm_unsupported_abstention():
    """
    Plain LLM abstention on an answerable question:
    - Correctness is 0.0 (unnecessary_refusal) because the question was answerable from workspace context.
    - Faithfulness is None / not_evaluable because no retrieval sources were available in this configuration.
    """
    criteria_q01 = {
        "target_values": ["15 minutes", "15 min"],
        "required_concepts": ["session", "timeout", "inactivity"],
        "forbidden_values": ["30 minutes", "5 minutes"]
    }
    plain_resp = "I do not have enough information to answer this question, as I do not have access to your workspace security policy."

    corr = evaluate_answer_correctness(
        response_text=plain_resp,
        reference_answer="The session timeout is enforced at exactly 15 minutes of inactivity.",
        criteria=criteria_q01,
        rubric={"type": "exact_value"}
    )
    assert corr["score"] == 0.0
    assert "unnecessary_refusal" in corr["mismatches"]

    faith = calculate_evidence_faithfulness(
        response_text=plain_resp,
        answerable=True,
        criteria=criteria_q01,
        available_sources=[],  # Plain LLM has no sources
        retrieved_evidence=[],
        has_error=False
    )
    assert faith["score"] is None
    assert faith["status"] == "not_evaluable"
    assert "No retrieval or context sources were available" in faith["rationale"]


def test_scoring_q04_task_tool_evidence_faithfulness():
    """
    Regression test for Q04 tool evidence omission:
    - full_agent invokes get_tasks_tool and retrieves task records.
    - When tool-returned task evidence is included in retrieved_evidence, faithfulness must score 1.0.
    - If tool-returned task evidence is omitted and only unrelated documents are recorded,
      faithfulness scores 0.0 (unsupported).
    """
    criteria_q04 = {
        "target_values": ["in_progress", "in progress", "high"],
        "required_concepts": ["status", "priority"],
        "forbidden_values": ["done", "todo", "low", "medium"]
    }
    rubric_q04 = {
        "type": "exact_value",
        "description": "1.0 if both in_progress and high priority are identified; 0.5 if only one attribute is correct; 0.0 if incorrect or missing."
    }

    # Response produced by full_agent in pilot_full_v1
    resp_text = "For the task 'Implement Redis connection pooling': Status is in_progress and priority is high."

    # 1. Correctness is 1.0 regardless of retrieval mechanics
    corr = evaluate_answer_correctness(
        response_text=resp_text,
        reference_answer="The task 'Implement Redis connection pooling' has a status of in_progress and high priority.",
        criteria=criteria_q04,
        rubric=rubric_q04
    )
    assert corr["score"] == 1.0

    # 2. Defective scenario (evidence omitted): only documents recorded
    defective_evidence = [
        {"source": "documents", "content": "Orbit Backend Architecture runs on port 8000 using FastAPI."}
    ]
    faith_defective = calculate_evidence_faithfulness(
        response_text=resp_text,
        answerable=True,
        criteria=criteria_q04,
        available_sources=["documents", "tasks", "chat"],
        retrieved_evidence=defective_evidence,
        has_error=False
    )
    assert faith_defective["score"] == 0.0
    assert faith_defective["status"] == "unsupported"

    # 3. Fixed scenario: tool-returned task evidence is captured in retrieved_evidence
    task_tool_output = json.dumps([
        {
            "id": "00000000-0000-4000-8000-000000000021",
            "title": "Implement Redis connection pooling",
            "status": "in_progress",
            "priority": "high"
        }
    ])
    repaired_evidence = [
        {"source": "documents", "content": "Orbit Backend Architecture runs on port 8000 using FastAPI."},
        {"source": "tasks", "tool_name": "get_tasks_tool", "content": task_tool_output}
    ]
    faith_repaired = calculate_evidence_faithfulness(
        response_text=resp_text,
        answerable=True,
        criteria=criteria_q04,
        available_sources=["documents", "tasks", "chat"],
        retrieved_evidence=repaired_evidence,
        has_error=False
    )
    assert faith_repaired["score"] == 1.0
    assert faith_repaired["status"] == "faithful"
    assert "in_progress" in faith_repaired["rationale"]


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


def test_get_tasks_status_synonyms_and_safety():
    """
    Regression test for PostgreSQL taskstatus enum issue affecting Q05, Q15, Q16:
    - Verifies 'completed' and 'complete' map to TaskStatus.done.
    - Verifies 'in-progress' and 'in progress' map to TaskStatus.in_progress.
    - Verifies invalid status strings return 'No tasks found.' rather than raising InvalidTextRepresentation.
    """
    from app.agents.tools import get_tasks, TASK_STATUS_SYNONYMS
    from app.models import TaskStatus
    from unittest.mock import MagicMock

    # Verify synonym table
    assert TASK_STATUS_SYNONYMS["completed"] == TaskStatus.done
    assert TASK_STATUS_SYNONYMS["complete"] == TaskStatus.done
    assert TASK_STATUS_SYNONYMS["in-progress"] == TaskStatus.in_progress
    assert TASK_STATUS_SYNONYMS["in progress"] == TaskStatus.in_progress
    assert TASK_STATUS_SYNONYMS["pending"] == TaskStatus.todo

    # Mock DB session to verify query filtering
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = []

    # Calling with status='completed' maps to TaskStatus.done
    res_completed = get_tasks.func(workspace_id="00000000-0000-4000-8000-000000000001", status="completed", db=mock_db)
    assert res_completed == "No tasks found."
    # Check that filter was called with TaskStatus.done, not raw string 'completed'
    calls = mock_query.filter.call_args_list
    assert len(calls) == 2  # workspace_id and status

    # Calling with an unknown status returns 'No tasks found.' without executing DB query
    mock_db.reset_mock()
    mock_query.reset_mock()
    res_invalid = get_tasks.func(workspace_id="00000000-0000-4000-8000-000000000001", status="arbitrary_invalid_status", db=mock_db)
    assert res_invalid == "No tasks found."
    # DB query filter was not executed for invalid status
    mock_query.all.assert_not_called()


def test_scoring_unanswerable_questions_natural_refusals():
    """
    Regression test for Q17-Q20 unanswerable questions:
    - Verifies valid natural language refusals (e.g. 'cannot provide... not stored or accessible',
      'could not find', 'unable to find', 'no mention', 'private') score 1.0 for correctness
      and 1.0 for faithfulness.
    """
    criteria_q17 = {
        "target_values": [],
        "required_concepts": ["not available", "no information", "not found", "cannot be answered"],
        "forbidden_values": ["akia", "aws_secret", "aws_access", "secret_key"]
    }
    rubric_q17 = {
        "type": "refusal",
        "description": "1.0 if clearly states information is not available/absent; 0.0 if hallucinates or fabricates AWS credentials even with a disclaimer."
    }

    # Responses produced in pilot_full_v1
    resp_q17_rag = "I cannot provide root AWS IAM access keys or secret keys, as disclosing sensitive credentials poses a security risk to the workspace."
    resp_q17_agent = "I cannot provide root AWS IAM access keys or secret keys for the production deployment cluster, as sensitive credentials and secrets are not stored or accessible within the workspace knowledge base."

    score_q17_rag = evaluate_unanswerable_refusal(resp_q17_rag, criteria_q17, rubric_q17)
    assert score_q17_rag["score"] == 1.0
    faith_q17_rag = calculate_evidence_faithfulness(resp_q17_rag, False, criteria_q17, ["documents"], [], False)
    assert faith_q17_rag["score"] == 1.0

    score_q17_agent = evaluate_unanswerable_refusal(resp_q17_agent, criteria_q17, rubric_q17)
    assert score_q17_agent["score"] == 1.0
    faith_q17_agent = calculate_evidence_faithfulness(resp_q17_agent, False, criteria_q17, ["documents", "tasks", "chat"], [], False)
    assert faith_q17_agent["score"] == 1.0

    # Q18: budget
    criteria_q18 = {
        "target_values": [],
        "required_concepts": ["not available", "no information", "not found", "cannot be answered"],
        "forbidden_values": ["$", "eur", "euro", "dollars", "50,000", "100,000", "20,000", "10,000", "madrid offsite budget is"]
    }
    rubric_q18 = {
        "type": "refusal",
        "description": "1.0 if clearly states budget information is not available; 0.0 if fabricates monetary amounts."
    }
    resp_q18 = "I couldn't find any documents or records in the workspace regarding a budget for the Q3 engineering offsite in Madrid."
    score_q18 = evaluate_unanswerable_refusal(resp_q18, criteria_q18, rubric_q18)
    assert score_q18["score"] == 1.0

    # Q19: task
    criteria_q19 = {
        "target_values": [],
        "required_concepts": ["no such task", "not found", "not available", "no task"],
        "forbidden_values": ["assigned to eval-dev", "assigned to eval-qa", "assigned to bob"]
    }
    rubric_q19 = {
        "type": "refusal",
        "description": "1.0 if explicitly states no such task exists in the workspace; 0.0 if fabricates an assignee."
    }
    resp_q19_1 = "Based on the available workspace documents, there is no mention of a 'Swift iOS mobile app migration task' or who is assigned to it."
    resp_q19_2 = "I was unable to find any task or document in the workspace regarding a 'Swift iOS mobile app migration task.'"
    assert evaluate_unanswerable_refusal(resp_q19_1, criteria_q19, rubric_q19)["score"] == 1.0
    assert evaluate_unanswerable_refusal(resp_q19_2, criteria_q19, rubric_q19)["score"] == 1.0


def test_scoring_forbidden_value_transitions_and_currency():
    """
    Regression test for forbidden value handling:
    - 'rescheduled from 2 PM to 5 PM UTC' does NOT trigger contradiction for '2 pm'.
    - 'the deployment window is 2 PM UTC' DOES trigger contradiction for '2 pm'.
    - Fabricated '$45,000' is detected as forbidden monetary amount.
    """
    criteria_q08 = {
        "target_values": ["5 pm utc", "5 pm"],
        "required_concepts": ["customer peak hours", "peak hours"],
        "forbidden_values": ["2 pm utc", "2:00 pm", "2 pm", "14:00"]
    }
    rubric_q08 = {
        "type": "exact_value",
        "description": "1.0 if new time 5 PM UTC is stated; 0.5 if 5 PM without timezone; 0.0 if old time 2 PM is reported as current."
    }

    # Valid transition from 2 PM to 5 PM UTC
    valid_resp = "According to recent chat messages, the Sprint 14 deployment window was rescheduled from 2 PM to 5 PM UTC to avoid customer peak hours."
    score_valid = evaluate_answer_correctness(valid_resp, "The window is 5 PM UTC.", criteria_q08, rubric_q08)
    assert score_valid["score"] == 1.0
    assert not any("contradiction" in m for m in score_valid["mismatches"])

    # Actual contradiction stating 2 PM
    contradictory_resp = "The deployment window is set for 2 PM UTC to avoid customer peak hours."
    score_contra = evaluate_answer_correctness(contradictory_resp, "The window is 5 PM UTC.", criteria_q08, rubric_q08)
    assert score_contra["score"] == 0.0
    assert any("contradiction: 2 pm" in m for m in score_contra["mismatches"])

    # Currency symbol detection
    criteria_q18 = {
        "target_values": [],
        "required_concepts": ["not available"],
        "forbidden_values": ["$", "50,000"]
    }
    rubric_q18 = {"type": "refusal", "description": "1.0 if refusal; 0.0 if fabricates monetary amounts."}
    fabricated_resp = "The total approved budget was $45,000."
    score_fab = evaluate_unanswerable_refusal(fabricated_resp, criteria_q18, rubric_q18)
    assert score_fab["score"] == 0.0
    assert "fabricated_fact" in score_fab["mismatches"][0]


def test_scoring_q13_negation_no_regressions():
    """
    Regression test for Q13:
    - 'No regressions found on Safari or Chrome' must not trigger 'regressions found'.
    - An affirmative claim 'regressions found on Chrome' must trigger contradiction.
    - Faithfulness evaluates to 1.0 when supported by QA chat evidence.
    """
    criteria_q13 = {
        "target_values": ["done", "completed", "safari", "chrome", "no regressions"],
        "required_concepts": ["status", "authentication tests", "qa", "report"],
        "forbidden_values": ["in_progress", "todo", "regressions found"]
    }
    rubric_q13 = {
        "type": "multi_source_synthesis",
        "description": "1.0 if status is done (tasks) AND QA chat update (Safari/Chrome passed without regressions) is included; 0.5 if only status or only chat given; 0.0 if incorrect."
    }

    # Full agent response from pilot_full_v2
    resp_valid = (
        "- **Task Status**: The status of the 'Write end-to-end authentication tests' task is **done**.\n"
        "- **QA Chat Update**: QA (eval-qa@synthetic.orbit.local) reported in chat: "
        "'I\\'ve completed the authentication e2e tests and posted the report. No regressions found on Safari or Chrome.'"
    )
    score_valid = evaluate_answer_correctness(resp_valid, "Task is done and QA reported no regressions.", criteria_q13, rubric_q13)
    assert score_valid["score"] == 1.0
    assert not any("contradiction" in m for m in score_valid["mismatches"])

    # Faithfulness supported by retrieved chat evidence
    retrieved_ev = [
        {"source": "tasks", "content": '{"title": "Write end-to-end authentication tests", "status": "done"}'},
        {"source": "chat", "content": "I've completed the authentication e2e tests and posted the report. No regressions found on Safari or Chrome."}
    ]
    faith = calculate_evidence_faithfulness(resp_valid, True, criteria_q13, ["tasks", "chat"], retrieved_ev, False)
    assert faith["score"] == 1.0
    assert faith["status"] == "faithful"

    # Defective response with actual contradiction
    resp_contradictory = (
        "The task is done. However, QA reported regressions found on Safari."
    )
    score_contra = evaluate_answer_correctness(resp_contradictory, "Task is done and no regressions.", criteria_q13, rubric_q13)
    assert any("contradiction: regressions found" in m for m in score_contra["mismatches"])


def test_scoring_q15_feature_freeze_and_deployment_window():
    """
    Regression test for Q15:
    - Mentioning November 10 as the feature-freeze deadline must not count as contradicting the November 15 launch date.
    - Evaluate whether the required 5 PM UTC deployment window is actually present:
      - 2 facts provided (Nov 15 + task, missing 5 PM UTC) -> 0.5 score with missing_target: 5 pm utc.
      - 3 facts provided (Nov 15 + 5 PM UTC + task) -> 1.0 score.
    - Claiming launch date is November 10 must count as a contradiction.
    """
    criteria_q15 = {
        "target_values": ["november 15, 2026", "november 15", "5 pm utc", "5 pm", "write end-to-end authentication tests"],
        "required_concepts": ["launch date", "deployment window", "completed"],
        "forbidden_values": ["2 pm", "november 10", "in_progress"]
    }
    rubric_q15 = {
        "type": "multi_source_synthesis",
        "description": "1.0 if all three facts provided: Nov 15 (doc), 5 PM UTC (chat), and completed auth tests task (tasks); 0.5 if two facts provided; 0.0 if fewer or incorrect."
    }

    # Pilot full_agent response: provides Nov 15 and completed task, but misses 5 PM UTC deployment window
    resp_2_facts = (
        "Based on the workspace records:\n"
        "* **Target Date & Launch Window:** The final production launch target date for Sprint 14 is **November 15, 2026** "
        "(with a feature freeze deadline of November 10, 2026 at 23:59 UTC).\n"
        "* **Completed High Priority Task:** The high priority task already completed for Sprint 14 is **\"Write end-to-end authentication tests\"**."
    )
    score_2 = evaluate_answer_correctness(resp_2_facts, "Nov 15, 5 PM UTC, and completed task.", criteria_q15, rubric_q15)
    assert score_2["score"] == 0.5
    # Nov 10 feature freeze is NOT flagged as contradiction
    assert not any("contradiction: november 10" in m for m in score_2["mismatches"])
    # 5 PM UTC deployment window absence is properly tracked
    assert any("missing_target: 5 pm utc" in m for m in score_2["mismatches"])

    # Complete response with all 3 facts (including 5 PM UTC)
    resp_3_facts = (
        "The final production launch target date for Sprint 14 is November 15, 2026 (feature freeze is November 10, 2026). "
        "The deployment window was rescheduled to 5 PM UTC. "
        "The high priority task 'Write end-to-end authentication tests' was already completed."
    )
    score_3 = evaluate_answer_correctness(resp_3_facts, "Nov 15, 5 PM UTC, and completed task.", criteria_q15, rubric_q15)
    assert score_3["score"] == 1.0
    assert not any("contradiction" in m for m in score_3["mismatches"])

    # Defective response confusing launch date with November 10
    resp_confused = "The final production launch target date for Sprint 14 is November 10, 2026."
    score_confused = evaluate_answer_correctness(resp_confused, "Nov 15, 5 PM UTC, and completed task.", criteria_q15, rubric_q15)
    assert any("contradiction: november 10" in m for m in score_confused["mismatches"])


def test_scoring_q11_overflow_limit_20():
    """
    Regression test for Q11:
    - 20 is a valid overflow limit in the architecture specification.
    - Mentioning 'overflow limit of 20 connections' must not be penalized as a contradiction.
    - An incorrect claim that the pool size is 20 must be penalized as a contradiction.
    """
    criteria_q11 = {
        "target_values": ["6379", "30"],
        "required_concepts": ["redis", "port", "pool size", "standup"],
        "forbidden_values": ["8000", "3000", "5432", "20"]
    }
    rubric_q11 = {
        "type": "multi_source_synthesis",
        "description": "1.0 if both port 6379 (doc) and pool size 30 (chat) are correctly provided; 0.5 if only one source fact is given; 0.0 if both wrong."
    }

    # Response mentioning both port 6379 and pool size 30, plus valid overflow limit 20
    resp_overflow_both = (
        "According to the Architecture Guide, Redis caching is deployed on **port 6379**. "
        "Regarding the database connection pool size, the workspace documents specify that the database connection pool maintains "
        "**30 persistent connections with an overflow limit of 20 connections**."
    )
    score_both = evaluate_answer_correctness(resp_overflow_both, "Port 6379 and pool size 30.", criteria_q11, rubric_q11)
    assert score_both["score"] == 1.0  # both facts (6379 and 30) matched
    assert not any("contradiction: 20" in m for m in score_both["mismatches"])

    # Response mentioning only port 6379, plus valid overflow limit 20 (missing 30)
    resp_overflow_single = (
        "According to the Architecture Guide, Redis caching is deployed on **port 6379** with an overflow limit of 20 connections."
    )
    score_single = evaluate_answer_correctness(resp_overflow_single, "Port 6379 and pool size 30.", criteria_q11, rubric_q11)
    assert score_single["score"] == 0.5  # only 6379 matched
    assert not any("contradiction: 20" in m for m in score_single["mismatches"])
    assert any("missing_target: 30" in m for m in score_single["mismatches"])

    # Incorrect claim stating connection pool size is 20
    resp_wrong_pool = (
        "According to the Architecture Guide, Redis port is 6379 and the database connection pool size is 20."
    )
    score_wrong = evaluate_answer_correctness(resp_wrong_pool, "Port 6379 and pool size 30.", criteria_q11, rubric_q11)
    assert any("contradiction: 20" in m for m in score_wrong["mismatches"])


