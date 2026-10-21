import os
import sys
import json
import csv
import math
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure backend root is on Python path
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = CURRENT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def evaluate_unanswerable_refusal(response_text: str) -> float:
    """
    Rubric for unanswerable questions:
    Returns 1.0 if the response correctly acknowledges lack of information / refuses hallucination.
    Returns 0.0 if the response attempts to fabricate false facts.
    """
    lower = response_text.lower()
    refusal_signals = [
        "not available",
        "no information",
        "not provided",
        "cannot be answered",
        "not found",
        "does not contain",
        "not mentioned",
        "lack sufficient",
        "no such task",
        "not listed",
        "private",
        "unknown",
        "do not have enough information",
        "no relevant information",
    ]
    if any(sig in lower for sig in refusal_signals):
        return 1.0

    # If the response is an error or short refusal
    if "error" in lower or len(lower.strip()) < 10:
        return 0.5

    return 0.0


def evaluate_answer_correctness(response_text: str, reference_answer: str, evidence_refs: List[Dict[str, Any]]) -> float:
    """
    Transparent scoring rubric for answerable questions based on key factual coverage.
    - 1.0: Full factual match
    - 0.5: Partial factual match
    - 0.0: Incorrect or missing critical facts
    """
    lower_resp = response_text.lower()
    lower_ref = reference_answer.lower()

    # Extract keywords/entities (excluding stopwords)
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "to", "in", "on", "at", "by", "for", "with", "about", "and", "or", "of", "that", "this", "from"}
    
    # Collect key terms from reference answer and evidence excerpts
    raw_terms = []
    for word in lower_ref.replace(",", " ").replace(".", " ").replace(":", " ").replace(";", " ").replace("(", " ").replace(")", " ").split():
        cleaned = word.strip()
        if len(cleaned) > 2 and cleaned not in stopwords:
            raw_terms.append(cleaned)

    for ev in evidence_refs:
        excerpt = ev.get("excerpt", "").lower()
        for word in excerpt.replace(",", " ").replace(".", " ").replace(":", " ").split():
            cleaned = word.strip()
            if len(cleaned) > 2 and cleaned not in stopwords:
                raw_terms.append(cleaned)

    unique_terms = list(dict.fromkeys(raw_terms))
    if not unique_terms:
        return 1.0 if lower_ref in lower_resp else 0.0

    matched_count = sum(1 for term in unique_terms if term in lower_resp)
    overlap_ratio = matched_count / len(unique_terms)

    if overlap_ratio >= 0.65:
        return 1.0
    elif overlap_ratio >= 0.35:
        return 0.5
    else:
        return 0.0


def calculate_evidence_faithfulness(response_text: str, evidence_refs: List[Dict[str, Any]], answerable: bool) -> float:
    """
    Measures evidence faithfulness: checks if the response reflects provided evidence
    without contradicting referenced excerpts.
    """
    if not answerable:
        # For unanswerable questions, refusal is completely faithful
        return evaluate_unanswerable_refusal(response_text)

    if not evidence_refs:
        return 1.0

    lower_resp = response_text.lower()
    matches = 0
    for ev in evidence_refs:
        excerpt = ev.get("excerpt", "").lower()
        # Check if excerpt fragment or key entity appears
        terms = [w.strip() for w in excerpt.split() if len(w.strip()) > 3]
        if any(t in lower_resp for t in terms):
            matches += 1

    return round(matches / len(evidence_refs), 2)


def compute_stats(values: List[float]) -> Dict[str, Optional[float]]:
    """Compute mean, median, min, max, and sample standard deviation."""
    if not values:
        return {"mean": None, "median": None, "min": None, "max": None, "stddev": None}

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mean_val = sum(sorted_vals) / n

    if n % 2 == 1:
        median_val = sorted_vals[n // 2]
    else:
        median_val = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0

    if n > 1:
        variance = sum((x - mean_val) ** 2 for x in sorted_vals) / (n - 1)
        stddev_val = math.sqrt(variance)
    else:
        stddev_val = 0.0

    return {
        "mean": round(mean_val, 2),
        "median": round(median_val, 2),
        "min": round(sorted_vals[0], 2),
        "max": round(sorted_vals[-1], 2),
        "stddev": round(stddev_val, 2)
    }


def _to_text_string(val: Any) -> str:
    """Safely convert any response type (str, list, dict) to a string."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        parts = []
        for p in val:
            if isinstance(p, dict):
                parts.append(p.get("text", "") or p.get("content", "") or str(p))
            else:
                parts.append(str(p))
        return "".join(parts)
    if isinstance(val, dict):
        return json.dumps(val)
    return str(val)


def score_results(input_file: Path, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Score evaluation results from a JSONL file."""
    if not input_file.exists():
        raise FileNotFoundError(f"Result file not found: {input_file}")

    records = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                records.append(json.loads(line_str))

    if not records:
        raise ValueError(f"No records found in {input_file}")

    run_id = records[0].get("run_id", "unknown_run")
    output_dir = output_dir or (CURRENT_DIR / "reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    scored_records = []
    grouped_by_config: Dict[str, List[Dict[str, Any]]] = {}
    grouped_by_config_and_cat: Dict[tuple, List[Dict[str, Any]]] = {}

    for r in records:
        q_text = r["question"]
        ref_ans = r["reference_answer"]
        ans = _to_text_string(r.get("response", ""))
        answerable = r.get("answerable", True)
        evidence_refs = r.get("evidence_references", [])
        cfg = r.get("configuration", "unknown")
        cat = r.get("category", "unknown")

        if not answerable:
            correctness = evaluate_unanswerable_refusal(ans)
        else:
            correctness = evaluate_answer_correctness(ans, ref_ans, evidence_refs)

        faithfulness = calculate_evidence_faithfulness(ans, evidence_refs, answerable)

        scored_item = dict(r)
        scored_item["score_correctness"] = correctness
        scored_item["score_faithfulness"] = faithfulness
        scored_records.append(scored_item)

        grouped_by_config.setdefault(cfg, []).append(scored_item)
        grouped_by_config_and_cat.setdefault((cfg, cat), []).append(scored_item)

    # Aggregate by configuration
    summary_rows = []
    print("\n" + "=" * 80)
    print(f" ORBIT EVALUATION SCORING REPORT (Run ID: {run_id})")
    print("=" * 80)

    for cfg, items in grouped_by_config.items():
        total_items = len(items)
        successful_items = [it for it in items if not it.get("error")]
        coverage = round(len(successful_items) / total_items, 4) if total_items else 0.0
        error_rate = round((total_items - len(successful_items)) / total_items, 4) if total_items else 0.0

        correctness_scores = [it["score_correctness"] for it in items]
        faithfulness_scores = [it["score_faithfulness"] for it in items]
        latencies = [it["latency_ms"] for it in items if it.get("latency_ms") is not None]

        token_counts = []
        for it in items:
            t_use = it.get("token_usage")
            if isinstance(t_use, dict):
                total_t = t_use.get("total_tokens") or t_use.get("total_token_count")
                if total_t is not None:
                    token_counts.append(total_t)

        lat_stats = compute_stats(latencies)
        tok_stats = compute_stats(token_counts) if token_counts else None

        mean_correctness = round(sum(correctness_scores) / len(correctness_scores), 4) if correctness_scores else 0.0
        mean_faithfulness = round(sum(faithfulness_scores) / len(faithfulness_scores), 4) if faithfulness_scores else 0.0

        summary_rows.append({
            "run_id": run_id,
            "configuration": cfg,
            "category": "ALL",
            "total_questions": total_items,
            "coverage": coverage,
            "error_rate": error_rate,
            "mean_correctness": mean_correctness,
            "mean_faithfulness": mean_faithfulness,
            "mean_latency_ms": lat_stats["mean"],
            "median_latency_ms": lat_stats["median"],
            "stddev_latency_ms": lat_stats["stddev"],
            "mean_tokens": tok_stats["mean"] if tok_stats else None
        })

    # Aggregate by configuration + category
    for (cfg, cat), items in grouped_by_config_and_cat.items():
        total_items = len(items)
        successful_items = [it for it in items if not it.get("error")]
        coverage = round(len(successful_items) / total_items, 4) if total_items else 0.0
        error_rate = round((total_items - len(successful_items)) / total_items, 4) if total_items else 0.0

        correctness_scores = [it["score_correctness"] for it in items]
        faithfulness_scores = [it["score_faithfulness"] for it in items]
        latencies = [it["latency_ms"] for it in items if it.get("latency_ms") is not None]

        lat_stats = compute_stats(latencies)
        mean_correctness = round(sum(correctness_scores) / len(correctness_scores), 4) if correctness_scores else 0.0
        mean_faithfulness = round(sum(faithfulness_scores) / len(faithfulness_scores), 4) if faithfulness_scores else 0.0

        summary_rows.append({
            "run_id": run_id,
            "configuration": cfg,
            "category": cat,
            "total_questions": total_items,
            "coverage": coverage,
            "error_rate": error_rate,
            "mean_correctness": mean_correctness,
            "mean_faithfulness": mean_faithfulness,
            "mean_latency_ms": lat_stats["mean"],
            "median_latency_ms": lat_stats["median"],
            "stddev_latency_ms": lat_stats["stddev"],
            "mean_tokens": None
        })

    # Print summary table
    headers = ["Configuration", "Category", "Questions", "Correctness", "Faithfulness", "Latency (ms)", "Errors"]
    print(f"\n{headers[0]:15s} | {headers[1]:15s} | {headers[2]:9s} | {headers[3]:11s} | {headers[4]:12s} | {headers[5]:12s} | {headers[6]:6s}")
    print("-" * 90)
    for row in summary_rows:
        lat_str = f"{row['mean_latency_ms']}ms" if row['mean_latency_ms'] is not None else "N/A"
        print(f"{row['configuration']:15s} | {row['category']:15s} | {row['total_questions']:9d} | {row['mean_correctness']:11.2f} | {row['mean_faithfulness']:12.2f} | {lat_str:12s} | {row['error_rate']:6.2f}")

    # Export to CSV
    csv_file = output_dir / f"summary_{run_id}.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    # Export scored JSON
    scored_json_file = output_dir / f"scored_{run_id}.json"
    with open(scored_json_file, "w", encoding="utf-8") as fp:
        json.dump({"run_id": run_id, "summary": summary_rows, "scored_records": scored_records}, fp, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print(f" Summary CSV exported to  : {csv_file}")
    print(f" Detailed JSON exported to: {scored_json_file}")
    print("=" * 80 + "\n")

    return {
        "run_id": run_id,
        "summary_csv": str(csv_file),
        "scored_json": str(scored_json_file),
        "summary": summary_rows
    }


def main():
    parser = argparse.ArgumentParser(description="Score Orbit Research Evaluation Results")
    parser.add_argument(
        "--input-file", "-i",
        type=str,
        required=True,
        help="Path to raw JSONL results file (e.g. results/run_xxx.jsonl)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=str(CURRENT_DIR / "reports"),
        help="Directory to save summary CSV and scored JSON reports"
    )

    args = parser.parse_args()
    score_results(Path(args.input_file), Path(args.output_dir))


if __name__ == "__main__":
    main()
