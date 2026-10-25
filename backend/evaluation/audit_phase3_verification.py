import json
import csv
from pathlib import Path
from collections import Counter
import statistics

BASE_DIR = Path(__file__).resolve().parent

# 1. Load dataset
questions_path = BASE_DIR / "questions_phase3_100.json"
with open(questions_path, "r", encoding="utf-8") as f:
    q_data = json.load(f)
questions = q_data["questions"]
q_lookup = {q["id"]: q for q in questions}

print(f"Loaded {len(questions)} questions from {questions_path.name}")
print(f"Overall categories: {dict(Counter(q['category'] for q in questions))}")

baseline_qs = [q for q in questions if int(q["id"][1:]) <= 20]
heldout_qs = [q for q in questions if int(q["id"][1:]) >= 21]
print(f"Baseline (Q01-Q20) categories: {dict(Counter(q['category'] for q in baseline_qs))}")
print(f"Held-out (Q21-Q100) categories: {dict(Counter(q['category'] for q in heldout_qs))}")

# 2. Function to audit a model report
def audit_report(report_path, raw_path, meta_path):
    print(f"\n=======================================================")
    print(f" AUDITING: {report_path.name}")
    print(f"=======================================================")

    with open(report_path, "r", encoding="utf-8") as f:
        rep = json.load(f)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Count raw lines
    raw_lines = []
    with open(raw_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                raw_lines.append(json.loads(line))

    records = rep["scored_records"]
    print(f"Raw records count   : {len(raw_lines)}")
    print(f"Scored records count: {len(records)}")
    assert len(raw_lines) == 300, f"Expected 300 raw lines, got {len(raw_lines)}"
    assert len(records) == 300, f"Expected 300 scored records, got {len(records)}"

    rubric_ver = rep.get("rubric_version")
    print(f"Rubric Version      : {rubric_ver}")

    # Check question-config coverage
    q_cfg_pairs = [(r["question_id"], r["configuration"]) for r in records]
    pair_counts = Counter(q_cfg_pairs)
    assert len(pair_counts) == 300, "Duplicate or missing question/config pairs"
    for pair, cnt in pair_counts.items():
        assert cnt == 1, f"Pair {pair} has count {cnt}"

    # Check category consistency
    for r in records:
        qid = r["question_id"]
        expected_cat = q_lookup[qid]["category"]
        assert r["category"] == expected_cat, f"Category mismatch on {qid}: {r['category']} != {expected_cat}"

    # Verify execution status
    failed_execs = [r for r in records if r.get("error") or r.get("execution_status") == "failed"]
    print(f"Execution failures  : {len(failed_execs)}")

    # Calculate metrics by config and cohort/category
    configs = ["plain_llm", "rag_docs_only", "full_agent"]
    categories = ["single_source", "multi_source", "unanswerable"]

    results = {}
    for cfg in configs:
        cfg_recs = [r for r in records if r["configuration"] == cfg]
        
        # Overall
        corr_all = [r["score_correctness"] for r in cfg_recs]
        faith_eval = [r["score_faithfulness"] for r in cfg_recs if r.get("score_faithfulness") is not None]
        faith_all_eval = [r["score_faithfulness"] for r in cfg_recs] # may have None
        latencies = [r["latency_ms"] for r in cfg_recs if r.get("latency_ms") is not None]
        partial_credits = [r for r in cfg_recs if 0.0 < r["score_correctness"] < 1.0]

        results[cfg] = {
            "attempts": len(cfg_recs),
            "correctness": sum(corr_all) / len(corr_all),
            "partial_credit_count": len(partial_credits),
            "faithfulness_mean": sum(faith_eval) / len(faith_eval) if faith_eval else None,
            "faithfulness_denom": len(faith_eval),
            "faithfulness_none": len([r for r in cfg_recs if r.get("score_faithfulness") is None]),
            "latency_mean_ms": statistics.mean(latencies) if latencies else None,
            "latency_median_ms": statistics.median(latencies) if latencies else None,
            "categories": {},
            "baseline": {},
            "heldout": {}
        }

        # By Category (Full dataset)
        for cat in categories:
            cat_recs = [r for r in cfg_recs if r["category"] == cat]
            c_corr = [r["score_correctness"] for r in cat_recs]
            c_faith = [r["score_faithfulness"] for r in cat_recs if r.get("score_faithfulness") is not None]
            c_part = [r for r in cat_recs if 0.0 < r["score_correctness"] < 1.0]
            results[cfg]["categories"][cat] = {
                "attempts": len(cat_recs),
                "correctness": sum(c_corr) / len(c_corr),
                "partial_credit_count": len(c_part),
                "faithfulness_mean": sum(c_faith) / len(c_faith) if c_faith else None,
                "faithfulness_denom": len(c_faith)
            }

        # By Cohort: Baseline (Q01-Q20)
        base_recs = [r for r in cfg_recs if int(r["question_id"][1:]) <= 20]
        b_corr = [r["score_correctness"] for r in base_recs]
        b_faith = [r["score_faithfulness"] for r in base_recs if r.get("score_faithfulness") is not None]
        results[cfg]["baseline"]["ALL"] = {
            "attempts": len(base_recs),
            "correctness": sum(b_corr) / len(b_corr),
            "faithfulness_mean": sum(b_faith) / len(b_faith) if b_faith else None,
            "faithfulness_denom": len(b_faith)
        }
        for cat in categories:
            b_cat_recs = [r for r in base_recs if r["category"] == cat]
            bc_corr = [r["score_correctness"] for r in b_cat_recs]
            bc_faith = [r["score_faithfulness"] for r in b_cat_recs if r.get("score_faithfulness") is not None]
            results[cfg]["baseline"][cat] = {
                "attempts": len(b_cat_recs),
                "correctness": sum(bc_corr) / len(bc_corr) if bc_corr else None,
                "faithfulness_mean": sum(bc_faith) / len(bc_faith) if bc_faith else None,
                "faithfulness_denom": len(bc_faith)
            }

        # By Cohort: Held-out (Q21-Q100)
        held_recs = [r for r in cfg_recs if int(r["question_id"][1:]) >= 21]
        h_corr = [r["score_correctness"] for r in held_recs]
        h_faith = [r["score_faithfulness"] for r in held_recs if r.get("score_faithfulness") is not None]
        results[cfg]["heldout"]["ALL"] = {
            "attempts": len(held_recs),
            "correctness": sum(h_corr) / len(h_corr),
            "faithfulness_mean": sum(h_faith) / len(h_faith) if h_faith else None,
            "faithfulness_denom": len(h_faith)
        }
        for cat in categories:
            h_cat_recs = [r for r in held_recs if r["category"] == cat]
            hc_corr = [r["score_correctness"] for r in h_cat_recs]
            hc_faith = [r["score_faithfulness"] for r in h_cat_recs if r.get("score_faithfulness") is not None]
            results[cfg]["heldout"][cat] = {
                "attempts": len(h_cat_recs),
                "correctness": sum(hc_corr) / len(hc_corr) if hc_corr else None,
                "faithfulness_mean": sum(hc_faith) / len(hc_faith) if hc_faith else None,
                "faithfulness_denom": len(hc_faith)
            }

    return results

gemini_audit = audit_report(
    BASE_DIR / "reports/scored_phase3_benchmark_gemini_35_lite_20261025_165427_corrected.json",
    BASE_DIR / "results/phase3_benchmark_gemini_35_lite_20261025_165427.jsonl",
    BASE_DIR / "results/meta_phase3_benchmark_gemini_35_lite_20261025_165427.json"
)

llama_audit = audit_report(
    BASE_DIR / "reports/scored_phase3_benchmark_llama32_20261025_173645.json",
    BASE_DIR / "results/phase3_benchmark_llama32_20261025_173645.jsonl",
    BASE_DIR / "results/meta_phase3_benchmark_llama32_20261025_173645.json"
)

# Output summary comparison
print("\n" + "="*80)
print("AUDIT RECONCILIATION SUMMARY")
print("="*80)
for model_name, model_res in [("Gemini 3.5 Flash Lite", gemini_audit), ("Llama 3.2:latest", llama_audit)]:
    print(f"\n--- {model_name} ---")
    for cfg in ["plain_llm", "rag_docs_only", "full_agent"]:
        d = model_res[cfg]
        print(f"[{cfg}]")
        print(f"  Overall: Corr={d['correctness']:.4f} (partials={d['partial_credit_count']}), Faith={d['faithfulness_mean']:.4f} (denom={d['faithfulness_denom']}, none={d['faithfulness_none']}), Latency={d['latency_mean_ms']:.1f}ms (med={d['latency_median_ms']:.1f}ms)")
        print(f"  Categories (Full 100):")
        for cat, cd in d["categories"].items():
            f_str = f"{cd['faithfulness_mean']:.4f}" if cd['faithfulness_mean'] is not None else "N/A"
            print(f"    {cat:14s} (n={cd['attempts']}): Corr={cd['correctness']:.4f} (partials={cd['partial_credit_count']}), Faith={f_str} (denom={cd['faithfulness_denom']})")
        print(f"  Baseline (Q01-Q20): ALL Corr={d['baseline']['ALL']['correctness']:.4f}")
        for cat in ["single_source", "multi_source", "unanswerable"]:
            bcd = d["baseline"][cat]
            print(f"    {cat:14s} (n={bcd['attempts']}): Corr={bcd['correctness']:.4f}")
        print(f"  Held-out (Q21-Q100): ALL Corr={d['heldout']['ALL']['correctness']:.4f}")
        for cat in ["single_source", "multi_source", "unanswerable"]:
            hcd = d["heldout"][cat]
            print(f"    {cat:14s} (n={hcd['attempts']}): Corr={hcd['correctness']:.4f}")

# 3. Export CSV Reports
csv1_path = BASE_DIR / "reports/summary_phase3_final_audit_cohort_and_categories_20261025.csv"
csv1_rows = []
for m_name, m_data in [("gemini-3.5-flash-lite", gemini_audit), ("llama3.2:latest", llama_audit)]:
    for cfg in ["plain_llm", "rag_docs_only", "full_agent"]:
        d = m_data[cfg]
        # Full ALL
        csv1_rows.append({
            "model": m_name, "configuration": cfg, "cohort": "full_dataset_Q01-Q100", "category": "ALL",
            "total_attempted": d["attempts"], "successful_attempts": d["attempts"], "failed_attempts": 0,
            "mean_correctness": round(d["correctness"], 4), "partial_credit_count": d["partial_credit_count"],
            "mean_faithfulness": round(d["faithfulness_mean"], 4) if d["faithfulness_mean"] is not None else "N/A",
            "faithfulness_evaluable_count": d["faithfulness_denom"], "faithfulness_non_evaluable_count": d["faithfulness_none"],
            "mean_latency_ms": round(d["latency_mean_ms"], 2), "median_latency_ms": round(d["latency_median_ms"], 2)
        })
        # Full Categories
        for cat in ["single_source", "multi_source", "unanswerable"]:
            cd = d["categories"][cat]
            csv1_rows.append({
                "model": m_name, "configuration": cfg, "cohort": "full_dataset_Q01-Q100", "category": cat,
                "total_attempted": cd["attempts"], "successful_attempts": cd["attempts"], "failed_attempts": 0,
                "mean_correctness": round(cd["correctness"], 4), "partial_credit_count": cd["partial_credit_count"],
                "mean_faithfulness": round(cd["faithfulness_mean"], 4) if cd["faithfulness_mean"] is not None else "N/A",
                "faithfulness_evaluable_count": cd["faithfulness_denom"], "faithfulness_non_evaluable_count": cd["attempts"] - cd["faithfulness_denom"],
                "mean_latency_ms": "N/A", "median_latency_ms": "N/A"
            })
        # Baseline ALL and Categories
        b_all = d["baseline"]["ALL"]
        csv1_rows.append({
            "model": m_name, "configuration": cfg, "cohort": "baseline_Q01-Q20", "category": "ALL",
            "total_attempted": b_all["attempts"], "successful_attempts": b_all["attempts"], "failed_attempts": 0,
            "mean_correctness": round(b_all["correctness"], 4), "partial_credit_count": "N/A",
            "mean_faithfulness": round(b_all["faithfulness_mean"], 4) if b_all["faithfulness_mean"] is not None else "N/A",
            "faithfulness_evaluable_count": b_all["faithfulness_denom"], "faithfulness_non_evaluable_count": b_all["attempts"] - b_all["faithfulness_denom"],
            "mean_latency_ms": "N/A", "median_latency_ms": "N/A"
        })
        for cat in ["single_source", "multi_source", "unanswerable"]:
            bcd = d["baseline"][cat]
            csv1_rows.append({
                "model": m_name, "configuration": cfg, "cohort": "baseline_Q01-Q20", "category": cat,
                "total_attempted": bcd["attempts"], "successful_attempts": bcd["attempts"], "failed_attempts": 0,
                "mean_correctness": round(bcd["correctness"], 4), "partial_credit_count": "N/A",
                "mean_faithfulness": round(bcd["faithfulness_mean"], 4) if bcd["faithfulness_mean"] is not None else "N/A",
                "faithfulness_evaluable_count": bcd["faithfulness_denom"], "faithfulness_non_evaluable_count": bcd["attempts"] - bcd["faithfulness_denom"],
                "mean_latency_ms": "N/A", "median_latency_ms": "N/A"
            })
        # Held-out ALL and Categories
        h_all = d["heldout"]["ALL"]
        csv1_rows.append({
            "model": m_name, "configuration": cfg, "cohort": "heldout_Q21-Q100", "category": "ALL",
            "total_attempted": h_all["attempts"], "successful_attempts": h_all["attempts"], "failed_attempts": 0,
            "mean_correctness": round(h_all["correctness"], 4), "partial_credit_count": "N/A",
            "mean_faithfulness": round(h_all["faithfulness_mean"], 4) if h_all["faithfulness_mean"] is not None else "N/A",
            "faithfulness_evaluable_count": h_all["faithfulness_denom"], "faithfulness_non_evaluable_count": h_all["attempts"] - h_all["faithfulness_denom"],
            "mean_latency_ms": "N/A", "median_latency_ms": "N/A"
        })
        for cat in ["single_source", "multi_source", "unanswerable"]:
            hcd = d["heldout"][cat]
            csv1_rows.append({
                "model": m_name, "configuration": cfg, "cohort": "heldout_Q21-Q100", "category": cat,
                "total_attempted": hcd["attempts"], "successful_attempts": hcd["attempts"], "failed_attempts": 0,
                "mean_correctness": round(hcd["correctness"], 4), "partial_credit_count": "N/A",
                "mean_faithfulness": round(hcd["faithfulness_mean"], 4) if hcd["faithfulness_mean"] is not None else "N/A",
                "faithfulness_evaluable_count": hcd["faithfulness_denom"], "faithfulness_non_evaluable_count": hcd["attempts"] - hcd["faithfulness_denom"],
                "mean_latency_ms": "N/A", "median_latency_ms": "N/A"
            })

with open(csv1_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(csv1_rows[0].keys()))
    writer.writeheader()
    writer.writerows(csv1_rows)
print(f"\nWrote CSV 1: {csv1_path.name}")

# CSV 2: Comparison with deltas
csv2_path = BASE_DIR / "reports/summary_phase3_final_audit_model_comparison_20261025.csv"
comparison_rows = []

slices = [
    ("Overall (Q01-Q100)", lambda d: d["correctness"]),
    ("Single-Source (All 40)", lambda d: d["categories"]["single_source"]["correctness"]),
    ("Multi-Source (All 40)", lambda d: d["categories"]["multi_source"]["correctness"]),
    ("Unanswerable (All 20)", lambda d: d["categories"]["unanswerable"]["correctness"]),
    ("Baseline Cohort ALL (Q01-Q20, n=20)", lambda d: d["baseline"]["ALL"]["correctness"]),
    ("Baseline Single-Source (Q01-Q08, n=8)", lambda d: d["baseline"]["single_source"]["correctness"]),
    ("Baseline Multi-Source (Q09-Q16, n=8)", lambda d: d["baseline"]["multi_source"]["correctness"]),
    ("Baseline Unanswerable (Q17-Q20, n=4)", lambda d: d["baseline"]["unanswerable"]["correctness"]),
    ("Held-out Cohort ALL (Q21-Q100, n=80)", lambda d: d["heldout"]["ALL"]["correctness"]),
    ("Held-out Single-Source (Q21-Q52, n=32)", lambda d: d["heldout"]["single_source"]["correctness"]),
    ("Held-out Multi-Source (Q53-Q84, n=32)", lambda d: d["heldout"]["multi_source"]["correctness"]),
    ("Held-out Unanswerable (Q85-Q100, n=16)", lambda d: d["heldout"]["unanswerable"]["correctness"])
]

for label, getter in slices:
    g_plain = getter(gemini_audit["plain_llm"])
    g_rag = getter(gemini_audit["rag_docs_only"])
    g_agent = getter(gemini_audit["full_agent"])
    g_delta_rag = (g_rag - g_plain) * 100.0
    g_delta_agent = (g_agent - g_rag) * 100.0

    l_plain = getter(llama_audit["plain_llm"])
    l_rag = getter(llama_audit["rag_docs_only"])
    l_agent = getter(llama_audit["full_agent"])
    l_delta_rag = (l_rag - l_plain) * 100.0
    l_delta_agent = (l_agent - l_rag) * 100.0

    comparison_rows.append({
        "slice": label,
        "gemini_plain_llm": round(g_plain, 4),
        "gemini_rag_docs": round(g_rag, 4),
        "gemini_full_agent": round(g_agent, 4),
        "gemini_delta_rag_over_plain_pp": round(g_delta_rag, 2),
        "gemini_delta_agent_over_rag_pp": round(g_delta_agent, 2),
        "llama_plain_llm": round(l_plain, 4),
        "llama_rag_docs": round(l_rag, 4),
        "llama_full_agent": round(l_agent, 4),
        "llama_delta_rag_over_plain_pp": round(l_delta_rag, 2),
        "llama_delta_agent_over_rag_pp": round(l_delta_agent, 2)
    })

with open(csv2_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(comparison_rows[0].keys()))
    writer.writeheader()
    writer.writerows(comparison_rows)
print(f"Wrote CSV 2: {csv2_path.name}")
