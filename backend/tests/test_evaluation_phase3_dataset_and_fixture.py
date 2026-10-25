import json
import uuid
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from evaluation.run_evaluation import load_dataset, run_evaluation
from evaluation.score_results import (
    evaluate_answer_correctness,
    evaluate_unanswerable_refusal,
    load_dataset_lookup,
    _contains_fact,
    RUBRIC_VERSION
)
from evaluation.seed_synthetic_workspace_phase3 import (
    SYNTHETIC_PHASE3_WORKSPACE_ID,
    clean_synthetic_workspace_phase3,
    seed_synthetic_workspace_phase3
)
from evaluation.seed_synthetic_workspace import SYNTHETIC_WORKSPACE_ID

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = CURRENT_DIR.parent
EVAL_DIR = BACKEND_ROOT / "evaluation"
BASELINE_DATASET = EVAL_DIR / "questions.json"
PHASE3_DATASET = EVAL_DIR / "questions_phase3_100.json"
DRAFT_DATASET = EVAL_DIR / "drafts" / "orbit_phase3_heldout_questions_Q21-Q100.json"
ORIGINAL_BACKUP = EVAL_DIR / "drafts" / "orbit_phase3_heldout_questions_Q21-Q100.original.json"


def test_immutable_backup_preserved():
    """Verify original downloaded draft is preserved under an immutable backup."""
    assert ORIGINAL_BACKUP.exists(), "Original draft backup must exist"
    assert ORIGINAL_BACKUP.stat().st_size > 0, "Original draft backup must not be empty"


def test_canonical_phase3_dataset_schema_and_counts():
    """Verify the canonical Phase 3 100-question dataset schema, allocation, and split."""
    assert PHASE3_DATASET.exists(), "Canonical Phase 3 dataset must exist"
    questions = load_dataset(PHASE3_DATASET)

    # Exactly 100 questions
    assert len(questions) == 100

    # Question IDs: Q01 to Q100 with no gaps or duplicates
    expected_ids = [f"Q{i:02d}" if i < 100 else f"Q{i}" for i in range(1, 101)]
    actual_ids = [q["id"] for q in questions]
    assert actual_ids == expected_ids

    # Distribution counts: 40 single-source, 40 multi-source, 20 unanswerable
    categories = [q["category"] for q in questions]
    assert categories.count("single_source") == 40
    assert categories.count("multi_source") == 40
    assert categories.count("unanswerable") == 20

    # Split integrity: Q01-Q20 matches baseline development/validation questions
    baseline_questions = load_dataset(BASELINE_DATASET)
    assert len(baseline_questions) == 20
    for idx in range(20):
        assert questions[idx]["id"] == baseline_questions[idx]["id"]
        assert questions[idx]["question"] == baseline_questions[idx]["question"]
        assert questions[idx]["category"] == baseline_questions[idx]["category"]
        assert questions[idx]["reference_answer"] == baseline_questions[idx]["reference_answer"]

    # Held-out split integrity: Q21-Q100
    heldout = questions[20:]
    assert len(heldout) == 80
    heldout_categories = [q["category"] for q in heldout]
    assert heldout_categories.count("single_source") == 32
    assert heldout_categories.count("multi_source") == 32
    assert heldout_categories.count("unanswerable") == 16


def test_category_cohort_boundaries_and_anti_naive_range_assumption():
    """
    Ensure category mapping is strictly determined by the 'category' field and never
    by naive question ID intervals.

    Regression Guard:
    - Baseline (Q01-Q20): contains 8 single_source (Q01-Q08), 8 multi_source (Q09-Q16), 4 unanswerable (Q17-Q20).
    - Held-out (Q21-Q100): contains 32 single_source (Q21-Q52), 32 multi_source (Q53-Q84), 16 unanswerable (Q85-Q100).
    - Prevents naive range bug where Q41-Q52 were assumed to be multi_source or Q81-Q84 were assumed unanswerable.
    """
    questions = load_dataset(PHASE3_DATASET)
    q_map = {q["id"]: q["category"] for q in questions}

    # Verify Baseline cohort mapping
    for i in range(1, 9):
        assert q_map[f"Q{i:02d}"] == "single_source"
    for i in range(9, 17):
        assert q_map[f"Q{i:02d}"] == "multi_source"
    for i in range(17, 21):
        assert q_map[f"Q{i:02d}"] == "unanswerable"

    # Verify Held-out cohort mapping
    for i in range(21, 53):
        assert q_map[f"Q{i:02d}"] == "single_source", f"Q{i:02d} must be single_source, got {q_map[f'Q{i:02d}']}"
    for i in range(53, 85):
        assert q_map[f"Q{i:02d}"] == "multi_source", f"Q{i:02d} must be multi_source, got {q_map[f'Q{i:02d}']}"
    for i in range(85, 101):
        qid = f"Q{i:02d}" if i < 100 else f"Q{i}"
        assert q_map[qid] == "unanswerable", f"{qid} must be unanswerable, got {q_map[qid]}"

    # Explicit anti-pattern assertions:
    assert q_map["Q41"] == "single_source", "Q41 is single_source, NOT multi_source"
    assert q_map["Q52"] == "single_source", "Q52 is single_source, NOT multi_source"
    assert q_map["Q81"] == "multi_source", "Q81 is multi_source, NOT unanswerable"
    assert q_map["Q84"] == "multi_source", "Q84 is multi_source, NOT unanswerable"
    assert q_map["Q85"] == "unanswerable", "Q85 is unanswerable"


def test_heldout_multi_source_cross_source_requirements():
    """Verify that every multi-source question genuinely requires >=2 distinct source types."""
    questions = load_dataset(PHASE3_DATASET)
    multi_source_q = [q for q in questions if q["category"] == "multi_source"]

    for q in multi_source_q:
        req_sources = q.get("required_sources", [])
        assert len(req_sources) >= 2, f"Multi-source question {q['id']} must require >=2 source types"

        # Check evidence references span at least two distinct source types
        ev_types = set()
        for ev in q.get("evidence_references", []):
            ev_types.add(ev.get("source"))

        assert len(ev_types) >= 2, (
            f"Question {q['id']} multi-source evidence references must span >=2 distinct source types, got {ev_types}"
        )


def test_flagged_questions_answer_leakage_repaired():
    """Verify answer leakage phrases are absent from Q61, Q72, and Q76 in canonical and draft datasets."""
    for dataset_path in [PHASE3_DATASET, DRAFT_DATASET]:
        questions = load_dataset(dataset_path)
        q_map = {q["id"]: q for q in questions}

        # Q61 must not leak 'confirmed'
        assert "Q61" in q_map
        assert "confirmed" not in q_map["Q61"]["question"].lower(), (
            f"Q61 in {dataset_path.name} leaks 'confirmed': {q_map['Q61']['question']}"
        )

        # Q72 must not leak 'Mateo'
        assert "Q72" in q_map
        assert "mateo" not in q_map["Q72"]["question"].lower(), (
            f"Q72 in {dataset_path.name} leaks 'Mateo': {q_map['Q72']['question']}"
        )

        # Q76 must not leak 'never be committed'
        assert "Q76" in q_map
        assert "never be committed" not in q_map["Q76"]["question"].lower(), (
            f"Q76 in {dataset_path.name} leaks 'never be committed': {q_map['Q76']['question']}"
        )


def test_flagged_multi_source_no_single_source_sufficiency():
    """Verify that no single source type alone contains all target facts for the repaired multi-source questions."""
    questions = load_dataset(PHASE3_DATASET)
    q_map = {q["id"]: q for q in questions}
    flagged_ids = ["Q53", "Q55", "Q58", "Q61", "Q62", "Q63", "Q68", "Q69", "Q72", "Q76", "Q78", "Q80", "Q81"]

    for qid in flagged_ids:
        q = q_map[qid]
        target_values = q.get("evaluation_criteria", {}).get("target_values", [])
        assert target_values, f"{qid} must have target_values"

        ev_by_source = {}
        for ev in q.get("evidence_references", []):
            src = ev.get("source")
            ev_by_source.setdefault(src, []).append(ev.get("excerpt", ""))

        assert len(ev_by_source) >= 2, f"{qid} must have evidence from >=2 distinct source types"

        # Check no single source type contains all target values
        for src, excerpts in ev_by_source.items():
            src_combined = " ".join(excerpts)
            matched = [tv for tv in target_values if _contains_fact(tv, src_combined)]
            assert len(matched) < len(target_values), (
                f"{qid}: source type '{src}' alone is sufficient (contains {matched}), violating multi-source requirement"
            )

        # Check combined evidence references across all sources DO contain all target values
        all_combined = " ".join(" ".join(excerpts) for excerpts in ev_by_source.values())
        matched_all = [tv for tv in target_values if _contains_fact(tv, all_combined)]
        assert len(matched_all) == len(target_values), (
            f"{qid}: combined evidence missing target values: {[tv for tv in target_values if tv not in matched_all]}"
        )


def test_evidence_references_resolve_to_fixture_records():
    """Verify that all evidence references in the held-out set resolve to real Phase 3 fixture records."""
    valid_documents = {
        "Architecture Specification",
        "Security Policy",
        "Release Plan Sprint 15"
    }
    valid_tasks = {
        "Document export", "Search relevance tuning", "Mobile navigation fixes",
        "Migration rehearsal", "P0/P1 defect triage", "Canary rollout checklist",
        "Audit log export review", "Service account rotation", "Status page separation check",
        "English retrieval test", "Request ID error test", "Session expiry regression test",
        "Quarterly access review", "Incident reporting drill", "Backup restore check",
        "Embedding pipeline monitor"
    }
    valid_chat_senders = {f"Team chat C{i:02d}" for i in range(1, 17)}

    questions = load_dataset(PHASE3_DATASET)
    held_out = questions[20:]

    for q in held_out:
        for ev in q.get("evidence_references", []):
            src = ev.get("source")
            assert src in {"documents", "tasks", "chat"}, f"Invalid source '{src}' in {q['id']}"
            assert ev.get("excerpt"), f"Missing excerpt in {q['id']} for source {src}"

            if src == "documents":
                doc_title = ev.get("document_title")
                assert doc_title in valid_documents, f"{q['id']} references unknown document '{doc_title}'"
            elif src == "tasks":
                task_title = ev.get("task_title")
                assert task_title in valid_tasks, f"{q['id']} references unknown task '{task_title}'"
            elif src == "chat":
                sender = ev.get("sender")
                assert sender in valid_chat_senders, f"{q['id']} references unknown chat sender '{sender}'"


def test_historical_artifacts_and_baseline_immutability():
    """Verify historical artifacts, baseline questions, and original draft backup are completely preserved."""
    # Baseline questions.json exists and has 20 questions
    assert BASELINE_DATASET.exists()
    baseline_q = load_dataset(BASELINE_DATASET)
    assert len(baseline_q) == 20

    # Original downloaded draft backup exists and is non-empty
    assert ORIGINAL_BACKUP.exists()
    assert ORIGINAL_BACKUP.stat().st_size > 0

    # Historical results and reports exist and are non-empty
    pilot_v1 = EVAL_DIR / "results" / "pilot_full_v1.jsonl"
    pilot_v2 = EVAL_DIR / "results" / "pilot_full_v2.jsonl"
    report_v2 = EVAL_DIR / "reports" / "scored_pilot_full_v2_audited.json"
    summary_v2 = EVAL_DIR / "reports" / "summary_pilot_full_v2_audited.csv"

    for hist_file in [pilot_v1, pilot_v2, report_v2, summary_v2]:
        assert hist_file.exists(), f"Historical file {hist_file} must exist"
        assert hist_file.stat().st_size > 0, f"Historical file {hist_file} must not be empty"


def test_unanswerable_refusal_rubric_and_criteria():
    """Verify unanswerable questions have valid refusal criteria and rubric structure."""
    questions = load_dataset(PHASE3_DATASET)
    unanswerable_q = [q for q in questions if q["category"] == "unanswerable"]
    assert len(unanswerable_q) == 20

    for q in unanswerable_q:
        assert q["answerable"] is False
        assert q["required_sources"] == []
        assert q["evidence_references"] == []

        crit = q.get("evaluation_criteria", {})
        rub = q.get("rubric", {})

        assert rub.get("type") == "refusal"

        # Valid refusal response must score 1.0
        standard_refusal = "This information is not available in the workspace documents, tasks, or chat messages."
        res = evaluate_unanswerable_refusal(standard_refusal, crit, rub)
        assert res["score"] == 1.0, f"Standard refusal failed on {q['id']}: {res}"

        # Fabricated forbidden facts must score 0.0
        forbidden = crit.get("forbidden_values", [])
        if forbidden:
            fabricated_resp = f"The value is definitely {forbidden[0]}."
            res_fab = evaluate_unanswerable_refusal(fabricated_resp, crit, rub)
            assert res_fab["score"] == 0.0, f"Fabrication should have been penalized on {q['id']}"


def test_scorer_compatibility_all_phase3_reference_answers():
    """Verify all 80 held-out reference answers score 1.0 with the Rubric 2.1 deterministic scorer."""
    questions = load_dataset(PHASE3_DATASET)
    held_out = questions[20:]
    assert len(held_out) == 80

    for q in held_out:
        ref_ans = q["reference_answer"]
        crit = q.get("evaluation_criteria", {})
        rub = q.get("rubric", {})
        if q["answerable"]:
            res = evaluate_answer_correctness(ref_ans, ref_ans, crit, rub)
        else:
            res = evaluate_unanswerable_refusal(ref_ans, crit, rub)

        assert res["score"] == 1.0, (
            f"Reference answer for {q['id']} failed self-scoring (score={res['score']}): "
            f"{res['rationale']}, mismatches={res.get('mismatches')}"
        )


def test_explicit_dataset_path_selection():
    """Verify both baseline and Phase 3 datasets can be explicitly selected and loaded."""
    q_base = load_dataset(BASELINE_DATASET)
    q_p3 = load_dataset(PHASE3_DATASET)

    assert len(q_base) == 20
    assert len(q_p3) == 100

    lookup_base = load_dataset_lookup(BASELINE_DATASET)
    lookup_p3 = load_dataset_lookup(PHASE3_DATASET)

    assert len(lookup_base) == 20
    assert len(lookup_p3) == 100
    assert "Q01" in lookup_base and "Q20" in lookup_base
    assert "Q21" in lookup_p3 and "Q100" in lookup_p3


@pytest.mark.skip(reason="Database mutation forbidden during offline Phase 3 dataset correction audit")
def test_phase3_fixture_seeding_and_isolation():
    """Verify Phase 3 synthetic fixture seeder is idempotent and isolates Workspace 3."""
    clean_res = clean_synthetic_workspace_phase3()
    assert isinstance(clean_res, dict)

    seed_res = seed_synthetic_workspace_phase3(skip_embeddings=True)
    assert seed_res["status"] == "success"
    assert seed_res["workspace_id"] == str(SYNTHETIC_PHASE3_WORKSPACE_ID)
    assert seed_res["documents_count"] == 3
    assert seed_res["tasks_count"] == 16
    assert seed_res["users_count"] == 6

    from app.database import SessionLocal
    from app.models import Workspace, Task, Document
    db = SessionLocal()
    try:
        ws1 = db.query(Workspace).filter(Workspace.id == SYNTHETIC_WORKSPACE_ID).first()
        t1_count = db.query(Task).filter(Task.workspace_id == SYNTHETIC_WORKSPACE_ID).count()
        d1_count = db.query(Document).filter(Document.workspace_id == SYNTHETIC_WORKSPACE_ID).count()
        assert ws1 is not None, "Workspace 1 must remain intact"
        assert t1_count == 4, "Workspace 1 tasks must not be affected"
        assert d1_count == 3, "Workspace 1 documents must not be affected"

        ws3 = db.query(Workspace).filter(Workspace.id == SYNTHETIC_PHASE3_WORKSPACE_ID).first()
        t3_count = db.query(Task).filter(Task.workspace_id == SYNTHETIC_PHASE3_WORKSPACE_ID).count()
        d3_count = db.query(Document).filter(Document.workspace_id == SYNTHETIC_PHASE3_WORKSPACE_ID).count()
        assert ws3 is not None, "Workspace 3 must exist"
        assert t3_count == 16, "Workspace 3 must have 16 tasks"
        assert d3_count == 3, "Workspace 3 must have 3 documents"
    finally:
        db.close()

    seed_res2 = seed_synthetic_workspace_phase3(skip_embeddings=True)
    assert seed_res2["status"] == "success"
    assert seed_res2["tasks_count"] == 16


def test_phase3_runner_and_scoring_smoke_test(tmp_path):
    """Run an isolated offline smoke test using offline harness on the canonical Phase 3 dataset."""
    import asyncio
    from evaluation.score_results import score_results

    output_dir = tmp_path / "results"
    report_dir = tmp_path / "reports"
    run_id = "smoke_phase3_test"

    asyncio.run(run_evaluation(
        configs=["plain_llm", "rag_docs_only", "full_agent"],
        questions_file=PHASE3_DATASET,
        output_dir=output_dir,
        limit=2,
        run_id=run_id,
        offline=True,
        workspace_id=str(SYNTHETIC_PHASE3_WORKSPACE_ID)
    ))

    result_file = output_dir / f"{run_id}.jsonl"
    assert result_file.exists(), "Evaluation result JSONL must exist"

    with open(result_file, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    assert len(records) == 6
    for r in records:
        assert r["run_id"] == run_id
        assert r["execution_status"] == "success"
        assert "retrieved_evidence" in r
        assert "tools_used" in r

    score_out = score_results(
        input_file=result_file,
        output_dir=report_dir,
        questions_file=PHASE3_DATASET,
        report_name="smoke_phase3"
    )

    assert score_out["rubric_version"] == RUBRIC_VERSION
    scored_json = Path(score_out["scored_json"])
    assert scored_json.exists()
