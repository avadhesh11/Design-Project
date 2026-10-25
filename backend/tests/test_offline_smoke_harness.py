import json
import asyncio
import socket
from pathlib import Path
import pytest

from evaluation.run_evaluation import run_evaluation, load_dataset
from evaluation.score_results import score_results, RUBRIC_VERSION
from evaluation.mock_offline_harness import (
    offline_evaluation_harness,
    SYNTHETIC_PHASE3_WORKSPACE_ID,
    OFFLINE_DOCUMENTS,
    OFFLINE_TASKS,
    OFFLINE_CHAT_MESSAGES
)

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = CURRENT_DIR.parent
EVAL_DIR = BACKEND_ROOT / "evaluation"
PHASE3_DATASET = EVAL_DIR / "questions_phase3_100.json"


def test_offline_harness_negative_guards():
    """Verify negative guards immediately block any attempted database or network socket access."""
    import app.database
    with offline_evaluation_harness(strict_negative_guards=True):
        # 1. Database access via SessionLocal must fail
        with pytest.raises(RuntimeError, match="Database access is strictly blocked"):
            app.database.SessionLocal()

        # 2. Network socket connection must fail
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(RuntimeError, match="Network access is strictly blocked"):
            s.connect(("8.8.8.8", 53))

    # After exiting harness, original functions are restored
    # (SessionLocal should not raise the blocked exception)
    try:
        db = app.database.SessionLocal()
        db.close()
    except RuntimeError as r_err:
        assert "Database access is strictly blocked" not in str(r_err)
    except Exception:
        # Connection failure is expected if db is down, but not our harness guard!
        pass


def test_offline_smoke_test_representative_questions(tmp_path):
    """
    Run a fully offline smoke test on a representative subset of questions:
    - Single-source (Q21)
    - Multi-source (Q53)
    - Unanswerable (Q85)
    across all three configurations: plain_llm, rag_docs_only, full_agent.
    """
    # Create mini dataset containing Q21, Q53, and Q85
    all_questions = load_dataset(PHASE3_DATASET)
    subset_ids = {"Q21", "Q53", "Q85"}
    subset_questions = [q for q in all_questions if q["id"] in subset_ids]
    assert len(subset_questions) == 3

    mini_dataset_file = tmp_path / "mini_questions.json"
    with open(mini_dataset_file, "w", encoding="utf-8") as f:
        json.dump({
            "version": "test-mini",
            "questions": subset_questions
        }, f, indent=2)

    output_dir = tmp_path / "results"
    report_dir = tmp_path / "reports"
    run_id = "offline_smoke_test_run"

    # Execute all 3 configurations: 3 configs x 3 questions = 9 attempts
    asyncio.run(run_evaluation(
        configs=["plain_llm", "rag_docs_only", "full_agent"],
        questions_file=mini_dataset_file,
        output_dir=output_dir,
        run_id=run_id,
        offline=True,
        workspace_id=SYNTHETIC_PHASE3_WORKSPACE_ID
    ))

    result_file = output_dir / f"{run_id}.jsonl"
    assert result_file.exists()

    with open(result_file, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    # 1. Verify attempt count
    assert len(records) == 9

    # 2. Verify all succeeded without errors
    for r in records:
        assert r["execution_status"] == "success"
        assert r["error"] is None
        assert r["provider"] == "mock"
        assert r["resolved_model"] == "mock-offline-llm"

    # 3. Verify permitted evidence sources per configuration
    for r in records:
        cfg = r["configuration"]
        sources = r["available_sources"]
        if cfg == "plain_llm":
            assert sources == [], "plain_llm must have empty available_sources"
            assert r["tools_used"] == []
        elif cfg == "rag_docs_only":
            assert sources == ["documents"], "rag_docs_only must only have documents"
        elif cfg == "full_agent":
            assert set(sources) == {"documents", "tasks", "chat"}, "full_agent must have all 3 sources"

    # 4. Verify unanswerable question refusal
    unans_records = [r for r in records if r["question_id"] == "Q85"]
    assert len(unans_records) == 3
    for r in unans_records:
        assert "not available" in r["response"].lower()

    # 5. Verify scoring works correctly with Rubric 2.1
    score_out = score_results(
        input_file=result_file,
        output_dir=report_dir,
        questions_file=mini_dataset_file,
        report_name="smoke_representative"
    )

    assert score_out["rubric_version"] == RUBRIC_VERSION
    assert Path(score_out["scored_json"]).exists()
    assert Path(score_out["summary_csv"]).exists()

    with open(score_out["scored_json"], "r", encoding="utf-8") as f:
        scored_data = json.load(f)

    scored_records = scored_data.get("scored_records", [])
    assert len(scored_records) == 9
    for sr in scored_records:
        assert sr["score_correctness"] == 1.0, f"Record {sr['question_id']} ({sr['configuration']}) failed scoring: {sr.get('scoring_rationale')}"
