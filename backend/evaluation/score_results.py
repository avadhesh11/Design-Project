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

RUBRIC_VERSION = "2.2-deterministic-audited"

REFUSAL_SIGNALS = [
    "not available",
    "no information",
    "not provided",
    "cannot be answered",
    "not found",
    "does not contain",
    "do not contain",
    "does not mention",
    "do not mention",
    "does not specify",
    "do not specify",
    "not specified",
    "does not provide",
    "do not provide",
    "not mentioned",
    "lack sufficient",
    "no such task",
    "not listed",
    "unknown",
    "do not have enough information",
    "no relevant information",
    "not found in the workspace",
    "no record",
    "no records",
    "insufficient evidence",
    "not documented",
    "i do not have access",
    "do not have access",
    "does not have access",
    "cannot provide",
    "can't provide",
    "could not find",
    "couldn't find",
    "unable to find",
    "cannot find",
    "can't find",
    "no mention",
    "not stored",
    "not accessible",
    "no task",
    "no tasks",
    "no document",
    "no documents",
    "no evidence"
]


def load_dataset_lookup(questions_file: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Load questions.json into a dictionary keyed by question_id for metadata enrichment."""
    q_file = questions_file or (CURRENT_DIR / "questions.json")
    if not q_file.exists():
        return {}
    try:
        with open(q_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {q["id"]: q for q in data.get("questions", [])}
    except Exception:
        return {}


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
        return " ".join(parts)
    if isinstance(val, dict):
        return json.dumps(val)
    return str(val)


import re

NUM_WORDS = {'15': 'fifteen', '30': 'thirty', '12': 'twelve', '1': 'one', '2': 'two', '5': 'five'}

ABBREVIATIONS = {
    r'\bmin\b': 'minutes',
    r'\bnov\b': 'november',
    r'\bdec\b': 'december',
    r'\bsec\b': 'seconds',
    r'\bhr\b': 'hours',
    r'\bhrs\b': 'hours',
    r':00\b': '',
    r'\butc\b': '',
    r'\bam\b': '',
    r'\bpm\b': '',
}


def _contains_fact(target: str, text: str) -> bool:
    """
    Check if target fact is contained in text, using word boundaries for tokens, numbers,
    and multi-word phrases to prevent misleading substring matches
    (e.g. '5 minutes' matching inside '15 minutes', or '8000' matching inside '18000').
    """
    target_clean = target.strip().lower()
    text_clean = text.lower()
    if not target_clean:
        return False
    # Use word boundary or delimiter lookaround to prevent substring false positives
    # while allowing Markdown formatting (backticks, asterisks, underscores) and punctuation
    if target_clean in {"$", "€", "£", "¥"}:
        pattern = r"(?<![^\s`*_\'\"(\[{<])" + re.escape(target_clean) + r"(?=[\d\s]|$)"
    else:
        prefix = r"\b" if re.match(r"^\w", target_clean) else r"(?<![^\s`*_\'\"(\[{<])"
        suffix = r"\b" if re.search(r"\w$", target_clean) else r"(?![^\s`*_\'\"\)\]}>,.;:!?])"
        pattern = prefix + re.escape(target_clean) + suffix
    return bool(re.search(pattern, text_clean))


def _is_contradiction(fv: str, text: str) -> bool:
    """
    Check if a forbidden value is asserted as a factual claim/contradiction in text.
    Returns False if fv is not present or if all occurrences are in an explicit
    transitional/negated/explanatory context (e.g. 'rescheduled from 2 PM to 5 PM',
    'not 2 PM', 'instead of 2 PM', 'Feature Freeze Deadline: November 10').
    """
    target_clean = fv.strip().lower()
    text_clean = text.lower()
    if not target_clean or not _contains_fact(target_clean, text_clean):
        return False

    if target_clean in {"$", "€", "£", "¥"}:
        pattern = r"(?<![^\s`*_\'\"(\[{<])" + re.escape(target_clean) + r"(?=[\d\s]|$)"
    else:
        prefix = r"\b" if re.match(r"^\w", target_clean) else r"(?<![^\s`*_\'\"(\[{<])"
        suffix = r"\b" if re.search(r"\w$", target_clean) else r"(?![^\s`*_\'\"\)\]}>,.;:!?])"
        pattern = prefix + re.escape(target_clean) + suffix

    matches = list(re.finditer(pattern, text_clean))
    if not matches:
        return False

    for m in matches:
        start, end = m.start(), m.end()
        preceding = text_clean[max(0, start - 60):start]
        following = text_clean[end:min(len(text_clean), end + 60)]

        is_transitional = False
        if re.search(r"\b(?:moved|rescheduled|changed|shifted|delayed|pushed|updated)\s+from\s*[:\s*(`*_\'\"(\[{<]*$", preceding):
            is_transitional = True
        elif re.search(r"\bfrom\s*[:\s*(`*_\'\"(\[{<]*$", preceding) and re.search(r"^\s*[`*_\'\"\)\]}>,.;:!?]*\s*to\b", following):
            is_transitional = True
        elif re.search(r"\b(?:no|zero|without|not|never|neither|nor|none|n/a|isn't|wasn't|aren't|weren't|don't|didn't|doesn't|instead of|rather than|previously|originally)\s*(?:\w+\s+)?[:\s*(`*_\'\"(\[{<]*$", preceding):
            is_transitional = True
        elif re.search(r"^\s*[:=-]?\s*[`*_\'\"\)\]}>,.;:!?]*\s*(?:none|no|zero|0|false|nil|null)\b", following):
            is_transitional = True
        elif re.search(r"\bfeature freeze(?:\s+(?:deadline|date))?(?:\s+(?:is|of|on|at|set for))?[:\s*(`*_\'\"(\[{<]+$", preceding):
            is_transitional = True
        elif re.search(r"\boverflow(?:\s+(?:limit|connections?))?(?:\s+(?:is|of|to|at))?[:\s*(`*_\'\"(\[{<]+$", preceding):
            is_transitional = True

        if not is_transitional:
            return True

    return False


def _normalize_synonym(s: str) -> str:
    s = s.lower().strip()
    s = s.replace('_', ' ').replace(',', '')
    for pat, rep in ABBREVIATIONS.items():
        s = re.sub(pat, rep, s)
    words = s.split()
    norm_words = []
    for w in words:
        if w in NUM_WORDS:
            norm_words.append(NUM_WORDS[w])
        else:
            norm_words.append(w)
    return ' '.join(norm_words).strip()


def _are_target_synonyms(a: str, b: str) -> bool:
    s1 = a.lower().strip()
    s2 = b.lower().strip()
    if s1 == s2:
        return True
    n1 = _normalize_synonym(s1)
    n2 = _normalize_synonym(s2)
    if n1 == n2:
        return True
    w1 = set(n1.split())
    w2 = set(n2.split())
    if w1 == w2:
        return True
    if len(w1) >= 2 and len(w2) >= 2 and (w1.issubset(w2) or w2.issubset(w1)):
        return True
    if (s1 == 'latency' and s2 == 'query latency') or (s2 == 'latency' and s1 == 'query latency'):
        return True
    if ({'done', 'completed'} & w1) and ({'done', 'completed'} & w2):
        return True
    if ('17:00' in a and ('5' in b or 'five' in b)) or ('17:00' in b and ('5' in a or 'five' in a)):
        return True
    return False


def group_target_values(targets: List[str]) -> List[List[str]]:
    """
    Group target values into clusters of synonymous or alternative expressions
    (e.g. ['15 minutes', '15 min', 'fifteen minutes'] forms one group).
    """
    groups: List[List[str]] = []
    for t in targets:
        placed = False
        for g in groups:
            if any(_are_target_synonyms(t, existing) for existing in g):
                g.append(t)
                placed = True
                break
        if not placed:
            groups.append([t])
    return groups


def evaluate_unanswerable_refusal(
    response_text: str,
    criteria: Dict[str, Any],
    rubric: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deterministic scoring for unanswerable questions:
    - 1.0: Valid refusal identifying lack of workspace evidence, with NO forbidden fabricated facts.
    - 0.0: Failed refusal or fabricated facts (even if accompanied by a disclaimer).
    """
    lower = response_text.lower().strip()
    forbidden_values = criteria.get("forbidden_values", [])

    # Check for fabricated forbidden values (e.g. AWS access keys, €45,000, Madrid team member)
    detected_fabricated = [fv for fv in forbidden_values if _is_contradiction(fv, lower)]
    if detected_fabricated:
        return {
            "score": 0.0,
            "rationale": f"Fabricated facts detected despite question being unanswerable: {detected_fabricated}",
            "mismatches": [f"fabricated_fact: {fv}" for fv in detected_fabricated]
        }

    # Check for valid refusal signals or required refusal concepts
    # Also support semantically equivalent plural/singular variations (e.g. 'do not contain' / 'does not contain')
    req_concepts = criteria.get("required_concepts", [])
    expanded_concepts = set(req_concepts)
    for rc in req_concepts:
        if rc.startswith("does not "):
            expanded_concepts.add(rc.replace("does not ", "do not "))
        elif rc.startswith("do not "):
            expanded_concepts.add(rc.replace("do not ", "does not "))

    has_refusal = (
        any(sig in lower for sig in REFUSAL_SIGNALS) or
        any(_contains_fact(rc, lower) for rc in expanded_concepts)
    )
    if has_refusal:
        return {
            "score": 1.0,
            "rationale": "Valid refusal: correctly identified insufficient workspace information without hallucinating forbidden facts",
            "mismatches": []
        }

    # Missing refusal signal
    return {
        "score": 0.0,
        "rationale": "Failed refusal: did not acknowledge lack of information for unanswerable question",
        "mismatches": ["missing_refusal_signal"]
    }


def evaluate_answer_correctness(
    response_text: str,
    reference_answer: str,
    criteria: Dict[str, Any],
    rubric: Dict[str, Any],
    evidence_refs: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Transparent, deterministic factual scoring rubric for answerable questions:
    - 1.0: Full factual match of all required target values/attributes and key concepts, no contradictions.
    - 0.5: Partial factual match (e.g. some target attributes matched) or partial match with minor contradiction.
    - 0.0: Incorrect values, missing critical facts, or contradictions.

    Limitations:
    Evaluates presence of factual tokens, numbers, and absence of known contradictions.
    Does not evaluate deep semantic syntax or stylistic quality.
    """
    lower_resp = response_text.lower().strip()
    target_values = criteria.get("target_values", [])
    required_concepts = criteria.get("required_concepts", [])
    forbidden_values = criteria.get("forbidden_values", [])
    rubric_desc = rubric.get("description", "").lower() if rubric else ""

    target_groups = group_target_values(target_values)
    matched_groups = [g for g in target_groups if any(_contains_fact(tv, lower_resp) for tv in g)]

    # 1. Check for unnecessary refusal on answerable question
    has_refusal = any(sig in lower_resp for sig in REFUSAL_SIGNALS)
    if has_refusal and len(matched_groups) == 0:
        return {
            "score": 0.0,
            "rationale": "Unnecessary refusal: question is answerable from workspace context but model refused",
            "mismatches": ["unnecessary_refusal"]
        }

    # 2. Check for contradictions / forbidden incorrect values
    detected_contradictions = [fv for fv in forbidden_values if _is_contradiction(fv, lower_resp)]
    mismatches = [f"contradiction: {fv}" for fv in detected_contradictions]

    # 3. Check target values and concepts
    target_ratio = len(matched_groups) / len(target_groups) if target_groups else 1.0
    matched_concepts = [c for c in required_concepts if _contains_fact(c, lower_resp)]
    concept_ratio = len(matched_concepts) / len(required_concepts) if required_concepts else 1.0

    for g in target_groups:
        if g not in matched_groups:
            mismatches.append(f"missing_target: {g[0]}")

    # 4. Rubric decision
    if detected_contradictions:
        if target_ratio >= 0.5 and len(detected_contradictions) == 1:
            return {
                "score": 0.5,
                "rationale": f"Partial match with contradiction: matched {len(matched_groups)}/{len(target_groups)} targets but contained contradiction ({detected_contradictions})",
                "mismatches": mismatches
            }
        else:
            return {
                "score": 0.0,
                "rationale": f"Incorrect due to contradictory facts: {detected_contradictions}",
                "mismatches": mismatches
            }

    if not target_values:
        # Fallback to token overlap if no target values defined
        lower_ref = reference_answer.lower()
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "to", "in", "on", "at", "by", "for", "with", "and", "or", "of", "that", "this"}
        ref_words = [w.strip() for w in lower_ref.split() if len(w.strip()) > 2 and w.strip() not in stopwords]
        if not ref_words:
            return {"score": 1.0 if lower_ref in lower_resp else 0.0, "rationale": "Exact match fallback", "mismatches": []}
        match_c = sum(1 for w in ref_words if _contains_fact(w, lower_resp))
        ratio = match_c / len(ref_words)
        if ratio >= 0.65:
            return {"score": 1.0, "rationale": f"Factual overlap {ratio:.2f}", "mismatches": []}
        elif ratio >= 0.35:
            return {"score": 0.5, "rationale": f"Partial factual overlap {ratio:.2f}", "mismatches": ["low_overlap"]}
        return {"score": 0.0, "rationale": f"Insufficient overlap {ratio:.2f}", "mismatches": ["insufficient_overlap"]}

    # Specific rubric clause check: e.g. "without specifying inactivity" -> requires inactivity for 1.0
    if "without specifying inactivity" in rubric_desc and not _contains_fact("inactivity", lower_resp):
        return {
            "score": 0.5,
            "rationale": "Partial factual match: stated duration without specifying inactivity as required by rubric",
            "mismatches": ["missing_concept: inactivity"]
        }

    if target_ratio == 1.0 and concept_ratio >= 0.5:
        matched_targets_display = [g[0] for g in matched_groups]
        return {
            "score": 1.0,
            "rationale": f"Complete factual match: all target values ({matched_targets_display}) and key concepts verified",
            "mismatches": []
        }
    elif target_ratio >= 0.5 or (target_ratio > 0 and concept_ratio >= 0.5):
        return {
            "score": 0.5,
            "rationale": f"Partial factual match: matched {len(matched_groups)}/{len(target_groups)} targets and {len(matched_concepts)}/{len(required_concepts)} concepts",
            "mismatches": mismatches
        }
    else:
        missing_targets_display = [g[0] for g in target_groups if g not in matched_groups]
        return {
            "score": 0.0,
            "rationale": f"Incorrect: failed to match required target values ({missing_targets_display})",
            "mismatches": mismatches
        }


def calculate_evidence_faithfulness(
    response_text: str,
    answerable: bool,
    criteria: Dict[str, Any],
    available_sources: List[str],
    retrieved_evidence: List[Dict[str, Any]],
    has_error: bool
) -> Dict[str, Any]:
    """
    Evaluates evidence faithfulness:
    - Assesses whether factual claims in the response are grounded in the evidence ACTUALLY retrieved or supplied.
    - NEVER substitutes expected benchmark evidence for evidence actually retrieved or supplied to the model.
    - If grounding evidence is unavailable, marks faithfulness as NOT EVALUABLE (score=None) and explains why.
    - Keeps correctness separate from faithfulness.
    - Distinguishes missing evidence from contradictions/unfaithful claims.
    """
    if has_error:
        return {
            "score": None,
            "status": "not_evaluable",
            "rationale": "Execution error; no model response to evaluate faithfulness"
        }

    if not answerable:
        # For unanswerable questions: if model refused without fabricating forbidden facts, it faithfully reflects lack of workspace evidence
        lower = response_text.lower()
        forbidden_values = criteria.get("forbidden_values", [])
        if any(_is_contradiction(fv, lower) for fv in forbidden_values):
            return {
                "score": 0.0,
                "status": "unfaithful",
                "rationale": "Fabricated unsupported claims on an unanswerable question"
            }
        has_refusal = (
            any(sig in lower for sig in REFUSAL_SIGNALS) or
            any(_contains_fact(rc, lower) for rc in criteria.get("required_concepts", []))
        )
        if has_refusal:
            return {
                "score": 1.0,
                "status": "faithful",
                "rationale": "Faithfully acknowledged lack of workspace evidence"
            }
        return {
            "score": 0.0,
            "status": "unfaithful",
            "rationale": "Did not faithfully refuse unanswerable question"
        }

    # Configuration has no source access (e.g. plain_llm)
    if not available_sources:
        return {
            "score": None,
            "status": "not_evaluable",
            "rationale": "No retrieval or context sources were available to the model in this configuration (faithfulness is not evaluable)"
        }

    # Model had source access, but no evidence was actually retrieved or supplied
    if not retrieved_evidence:
        return {
            "score": None,
            "status": "not_evaluable",
            "rationale": "No evidence was retrieved or supplied by tools for this attempt (faithfulness is not evaluable)"
        }

    # Aggregate text ONLY from actually retrieved or supplied evidence
    evidence_corpus = []
    for ev in retrieved_evidence:
        if isinstance(ev, dict):
            text = ev.get("excerpt", "") or ev.get("content", "") or ev.get("snippet", "")
            if text:
                evidence_corpus.append(text)
        elif isinstance(ev, str):
            evidence_corpus.append(ev)

    actual_evidence_text = " ".join(evidence_corpus).lower()
    if not actual_evidence_text.strip():
        return {
            "score": None,
            "status": "not_evaluable",
            "rationale": "Retrieved evidence contained no textual content"
        }

    lower_resp = response_text.lower()
    target_values = criteria.get("target_values", [])
    forbidden_values = criteria.get("forbidden_values", [])

    # Check if response directly contradicts the retrieved evidence with forbidden values
    detected_forbidden = [fv for fv in forbidden_values if _is_contradiction(fv, lower_resp)]
    if detected_forbidden:
        return {
            "score": 0.0,
            "status": "contradiction",
            "rationale": f"Response contradicts retrieved evidence with forbidden values: {detected_forbidden}"
        }

    target_groups = group_target_values(target_values)
    resp_groups = [g for g in target_groups if any(_contains_fact(tv, lower_resp) for tv in g)]
    if resp_groups:
        grounded_groups = [g for g in resp_groups if any(_contains_fact(tv, actual_evidence_text) for tv in g)]
        if len(grounded_groups) == len(resp_groups):
            grounded_names = [g[0] for g in grounded_groups]
            return {
                "score": 1.0,
                "status": "faithful",
                "rationale": f"All stated factual targets ({grounded_names}) are grounded in retrieved evidence"
            }
        elif len(grounded_groups) > 0:
            return {
                "score": 0.5,
                "status": "partially_faithful",
                "rationale": f"Partially grounded: {len(grounded_groups)}/{len(resp_groups)} stated targets found in retrieved evidence"
            }
        else:
            resp_names = [g[0] for g in resp_groups]
            return {
                "score": 0.0,
                "status": "unsupported",
                "rationale": f"Stated targets ({resp_names}) are absent from actually retrieved evidence"
            }

    return {
        "score": 0.5,
        "status": "partially_faithful",
        "rationale": "Response contains general statements without explicit grounded targets"
    }


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


def score_results(
    input_file: Path,
    output_dir: Optional[Path] = None,
    questions_file: Optional[Path] = None,
    report_name: Optional[str] = None
) -> Dict[str, Any]:
    """Score evaluation results from a JSONL file using deterministic rubrics."""
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

    dataset_lookup = load_dataset_lookup(questions_file)
    run_id = records[0].get("run_id", "unknown_run")
    report_id = report_name or run_id
    output_dir = output_dir or (CURRENT_DIR / "reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    scored_records = []
    grouped_by_config: Dict[str, List[Dict[str, Any]]] = {}
    grouped_by_config_and_cat: Dict[tuple, List[Dict[str, Any]]] = {}

    for r in records:
        q_id = r["question_id"]
        # Enrich from questions.json if missing from record
        dataset_meta = dataset_lookup.get(q_id, {})
        criteria = r.get("evaluation_criteria") or dataset_meta.get("evaluation_criteria", {})
        rubric = r.get("rubric") or dataset_meta.get("rubric", {})
        ref_ans = r.get("reference_answer") or dataset_meta.get("reference_answer", "")
        answerable = r.get("answerable") if "answerable" in r else dataset_meta.get("answerable", True)
        evidence_refs = r.get("evidence_references") or dataset_meta.get("evidence_references", [])

        ans = _to_text_string(r.get("response", ""))
        cfg = r.get("configuration", "unknown")
        cat = r.get("category", dataset_meta.get("category", "unknown"))
        has_error = bool(r.get("error")) or (r.get("execution_status") == "failed")
        available_sources = r.get("available_sources", [])
        retrieved_evidence = r.get("retrieved_evidence", [])

        if has_error:
            correctness = {
                "score": 0.0,
                "rationale": f"Execution failed: {r.get('error')}",
                "mismatches": ["execution_error"]
            }
            faithfulness = {
                "score": None,
                "status": "not_evaluable",
                "rationale": "Execution error; faithfulness cannot be evaluated"
            }
        elif not answerable:
            correctness = evaluate_unanswerable_refusal(ans, criteria, rubric)
            faithfulness = calculate_evidence_faithfulness(
                ans, answerable, criteria, available_sources, retrieved_evidence, has_error
            )
        else:
            correctness = evaluate_answer_correctness(ans, ref_ans, criteria, rubric, evidence_refs)
            faithfulness = calculate_evidence_faithfulness(
                ans, answerable, criteria, available_sources, retrieved_evidence, has_error
            )

        scored_item = dict(r)
        scored_item["rubric_version"] = RUBRIC_VERSION
        scored_item["score_correctness"] = correctness["score"]
        scored_item["scoring_rationale"] = correctness["rationale"]
        scored_item["mismatches"] = correctness.get("mismatches", [])
        scored_item["score_faithfulness"] = faithfulness["score"]
        scored_item["faithfulness_status"] = faithfulness.get("status", "evaluable")
        scored_item["faithfulness_rationale"] = faithfulness["rationale"]

        scored_records.append(scored_item)
        grouped_by_config.setdefault(cfg, []).append(scored_item)
        grouped_by_config_and_cat.setdefault((cfg, cat), []).append(scored_item)

    # Aggregate summaries
    def _aggregate_group(items: List[Dict[str, Any]], cfg_name: str, cat_name: str) -> Dict[str, Any]:
        total_attempts = len(items)
        successful_items = [it for it in items if not it.get("error") and it.get("execution_status") != "failed"]
        failed_items = [it for it in items if it.get("error") or it.get("execution_status") == "failed"]

        coverage = round(len(successful_items) / total_attempts, 4) if total_attempts else 0.0
        error_rate = round(len(failed_items) / total_attempts, 4) if total_attempts else 0.0

        all_correctness = [it["score_correctness"] for it in items]
        succ_correctness = [it["score_correctness"] for it in successful_items]
        partial_credits = sum(1 for it in items if it["score_correctness"] == 0.5)

        all_faithfulness = [it["score_faithfulness"] for it in items if it.get("score_faithfulness") is not None]
        succ_faithfulness = [it["score_faithfulness"] for it in successful_items if it.get("score_faithfulness") is not None]

        succ_latencies = [it["latency_ms"] for it in successful_items if it.get("latency_ms") is not None]
        fail_latencies = [it["latency_ms"] for it in failed_items if it.get("latency_ms") is not None]

        succ_lat_stats = compute_stats(succ_latencies)
        fail_lat_stats = compute_stats(fail_latencies)

        token_counts = []
        for it in successful_items:
            t_use = it.get("token_usage")
            if isinstance(t_use, dict):
                total_t = t_use.get("total_tokens") or t_use.get("total_token_count")
                if total_t is not None:
                    token_counts.append(total_t)
        tok_stats = compute_stats(token_counts) if token_counts else None

        mean_corr_all = round(sum(all_correctness) / len(all_correctness), 4) if all_correctness else 0.0
        mean_corr_succ = round(sum(succ_correctness) / len(succ_correctness), 4) if succ_correctness else 0.0

        mean_faith_all = round(sum(all_faithfulness) / len(all_faithfulness), 4) if all_faithfulness else None
        mean_faith_succ = round(sum(succ_faithfulness) / len(succ_faithfulness), 4) if succ_faithfulness else None

        return {
            "run_id": run_id,
            "rubric_version": RUBRIC_VERSION,
            "configuration": cfg_name,
            "category": cat_name,
            "total_attempted": total_attempts,
            "successful_attempts": len(successful_items),
            "failed_attempts": len(failed_items),
            "coverage": coverage,
            "error_rate": error_rate,
            "mean_correctness_all": mean_corr_all,
            "mean_correctness_successful": mean_corr_succ,
            "partial_credit_count": partial_credits,
            "mean_faithfulness_all": mean_faith_all,
            "mean_faithfulness_successful": mean_faith_succ,
            "mean_latency_ms": succ_lat_stats["mean"],
            "median_latency_ms": succ_lat_stats["median"],
            "stddev_latency_ms": succ_lat_stats["stddev"],
            "mean_latency_failed_ms": fail_lat_stats["mean"],
            "mean_tokens": tok_stats["mean"] if tok_stats else None
        }

    summary_rows = []
    for cfg, items in grouped_by_config.items():
        summary_rows.append(_aggregate_group(items, cfg, "ALL"))

    for (cfg, cat), items in grouped_by_config_and_cat.items():
        summary_rows.append(_aggregate_group(items, cfg, cat))

    # Print summary table
    print("\n" + "=" * 105)
    print(f" ORBIT EVALUATION SCORING REPORT (Run ID: {run_id} | Rubric: {RUBRIC_VERSION})")
    print("=" * 105)
    headers = ["Configuration", "Category", "Attempts", "Succ", "Fail", "Corr(All)", "Corr(Succ)", "Faith(Succ)", "Latency(ms)"]
    print(f"{headers[0]:15s} | {headers[1]:15s} | {headers[2]:8s} | {headers[3]:4s} | {headers[4]:4s} | {headers[5]:9s} | {headers[6]:10s} | {headers[7]:11s} | {headers[8]:11s}")
    print("-" * 105)
    for row in summary_rows:
        lat_str = f"{row['mean_latency_ms']}ms" if row['mean_latency_ms'] is not None else "N/A"
        faith_str = f"{row['mean_faithfulness_successful']:11.2f}" if row['mean_faithfulness_successful'] is not None else f"{'N/A':>11s}"
        print(f"{row['configuration']:15s} | {row['category']:15s} | {row['total_attempted']:8d} | {row['successful_attempts']:4d} | {row['failed_attempts']:4d} | {row['mean_correctness_all']:9.2f} | {row['mean_correctness_successful']:10.2f} | {faith_str} | {lat_str:11s}")

    # Export to CSV
    csv_file = output_dir / f"summary_{report_id}.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    # Export scored JSON
    scored_json_file = output_dir / f"scored_{report_id}.json"
    with open(scored_json_file, "w", encoding="utf-8") as fp:
        json.dump({
            "run_id": run_id,
            "report_id": report_id,
            "rubric_version": RUBRIC_VERSION,
            "summary": summary_rows,
            "scored_records": scored_records
        }, fp, indent=2, ensure_ascii=False)

    print("\n" + "=" * 105)
    print(f" Summary CSV exported to  : {csv_file}")
    print(f" Detailed JSON exported to: {scored_json_file}")
    print("=" * 105 + "\n")

    return {
        "run_id": run_id,
        "report_id": report_id,
        "rubric_version": RUBRIC_VERSION,
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
    parser.add_argument(
        "--questions-file", "--dataset", "-q",
        type=str,
        dest="questions_file",
        default=str(CURRENT_DIR / "questions.json"),
        help="Path to questions.json for criteria and rubric enrichment (alias: --dataset)"
    )
    parser.add_argument(
        "--report-name", "-r",
        type=str,
        default=None,
        help="Custom report identifier for output filenames (summary_<name>.csv, scored_<name>.json)"
    )

    args = parser.parse_args()
    score_results(Path(args.input_file), Path(args.output_dir), Path(args.questions_file), args.report_name)


if __name__ == "__main__":
    main()
