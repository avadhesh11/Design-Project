"""
Deterministic scheduling helper for Orbit evaluation runner.
Supports sequential, by-question (interleaved), by-configuration, and seeded reproducible ordering.
"""
import random
from typing import List, Dict, Any, Optional


VALID_SCHEDULE_STRATEGIES = ["sequential", "by_question", "by_configuration", "randomized"]


def generate_evaluation_schedule(
    questions: List[Dict[str, Any]],
    configs: List[str],
    schedule_strategy: str = "sequential",
    seed: Optional[int] = None,
    models: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Generate an ordered, deterministic schedule of evaluation attempts.

    Args:
        questions: List of question specification dictionaries.
        configs: List of configuration names (e.g. ['plain_llm', 'rag_docs_only', 'full_agent']).
        schedule_strategy: One of 'sequential', 'by_question', 'by_configuration', 'randomized'.
        seed: Random seed required when schedule_strategy is 'randomized'.
        models: Optional list of model specification dictionaries. If None, treats as single-model.

    Returns:
        List of scheduled attempt dictionaries containing question, configuration, model, and metadata.
    """
    if schedule_strategy not in VALID_SCHEDULE_STRATEGIES:
        raise ValueError(
            f"Invalid schedule strategy '{schedule_strategy}'. "
            f"Must be one of {VALID_SCHEDULE_STRATEGIES}."
        )

    model_list = models if models else [None]
    scheduled: List[Dict[str, Any]] = []

    if schedule_strategy in ["sequential", "by_question"]:
        # Interleaved by question: evaluate all configs/models for question Q before moving to Q+1
        for q in questions:
            for m in model_list:
                for c in configs:
                    scheduled.append({
                        "question": q,
                        "question_id": q.get("id"),
                        "configuration": c,
                        "model": m
                    })

    elif schedule_strategy == "by_configuration":
        # Grouped by configuration: run all questions for Config 1, then Config 2, etc.
        for c in configs:
            for m in model_list:
                for q in questions:
                    scheduled.append({
                        "question": q,
                        "question_id": q.get("id"),
                        "configuration": c,
                        "model": m
                    })

    elif schedule_strategy == "randomized":
        if seed is None:
            raise ValueError("A random seed must be provided when using 'randomized' schedule strategy.")
        # Start with standard interleaved order then deterministically shuffle with seed
        for q in questions:
            for m in model_list:
                for c in configs:
                    scheduled.append({
                        "question": q,
                        "question_id": q.get("id"),
                        "configuration": c,
                        "model": m
                    })
        rng = random.Random(seed)
        rng.shuffle(scheduled)

    # Attach deterministic attempt indices
    total = len(scheduled)
    for idx, item in enumerate(scheduled, start=1):
        item["attempt_index"] = idx
        item["total_attempts"] = total
        item["schedule_strategy"] = schedule_strategy

    return scheduled
