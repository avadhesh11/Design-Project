import os
import sys
import json
import uuid
import time
import asyncio
import argparse
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure backend root is on Python path
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = CURRENT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from evaluation.configs import (
    CONFIGURATION_NAMES,
    CONFIG_DEFINITIONS,
    execute_evaluation_configuration
)
from evaluation.seed_synthetic_workspace import (
    SYNTHETIC_WORKSPACE_ID,
    SYNTHETIC_DEV1_ID
)
from evaluation.scheduler import generate_evaluation_schedule, VALID_SCHEDULE_STRATEGIES
import re


def sanitize_secret(text: Optional[str]) -> Optional[str]:
    """Sanitize API keys, tokens, and DB passwords from log strings and error messages."""
    if not text:
        return text
    text = re.sub(r"AIza[A-Za-z0-9_-]{30,45}", "[REDACTED_API_KEY]", text)
    text = re.sub(r"Bearer\s+[A-Za-z0-9_.-]+", "Bearer [REDACTED_TOKEN]", text)
    text = re.sub(r"postgresql://([^:]+):([^@]+)@", r"postgresql://\1:[REDACTED_PASSWORD]@", text)
    return text


def get_git_commit() -> Optional[str]:
    """Retrieve current Git commit SHA safely if git is available."""
    try:
        import subprocess
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(BACKEND_ROOT),
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None


from langchain_core.runnables import Runnable
from langchain_core.messages import AIMessage


class MockEvaluationLLM(Runnable):
    """Mock LLM for offline tests and smoke checks without external API dependencies."""
    def __init__(self, model_name: str = "mock-eval-model", temperature: float = 0.3):
        self.model_name = model_name
        self.model = model_name
        self.temperature = temperature

    def _generate_response(self, messages: Any) -> AIMessage:
        query_text = ""
        msg_list = messages
        if isinstance(messages, dict):
            msg_list = messages.get("messages", [])
        for m in (msg_list if isinstance(msg_list, list) else []):
            content = getattr(m, "content", "")
            if isinstance(content, str):
                query_text += " " + content
            elif isinstance(content, list):
                for p in content:
                    query_text += " " + str(p)

        if "port" in query_text.lower():
            text = "The backend API runs on port 8000 using FastAPI and the frontend web client on port 3000 using Next.js."
        elif "timeout" in query_text.lower():
            text = "The session timeout is enforced at exactly 15 minutes of inactivity."
        elif "freeze" in query_text.lower():
            text = "The feature freeze deadline is November 10, 2026 at 23:59 UTC."
        elif "aws" in query_text.lower() or "madrid" in query_text.lower() or "budget" in query_text.lower():
            text = "This information is not available in the workspace documents or tasks."
        else:
            text = "Synthetic offline evaluation answer for research verification."

        msg = AIMessage(content=text)
        msg.usage_metadata = {"input_tokens": 42, "output_tokens": 18, "total_tokens": 60}
        msg.response_metadata = {"token_usage": msg.usage_metadata}
        return msg

    def invoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> Any:
        return self._generate_response(input)

    async def ainvoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> Any:
        return self._generate_response(input)

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        return self


def validate_environment(mock_mode: bool = False, provider: str = "gemini") -> None:
    """Ensure necessary environment variables and dependencies exist."""
    if mock_mode:
        return

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL environment variable is missing. Evaluation runner cannot access workspace data.")

    p_norm = provider.strip().lower()
    if p_norm == "gemini":
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is missing. Set GEMINI_API_KEY or run with --mock-llm for offline testing.")


def load_dataset(file_path: Path) -> List[Dict[str, Any]]:
    """Load and validate question dataset schema."""
    if not file_path.exists():
        raise FileNotFoundError(f"Questions dataset not found at {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict) or "questions" not in data:
        raise ValueError(f"Dataset root must be an object with a 'questions' array: {file_path}")

    questions = data.get("questions", [])
    if not isinstance(questions, list) or not questions:
        raise ValueError(f"No questions found in dataset file: {file_path}")

    for idx, q in enumerate(questions):
        for field in ["id", "question", "category", "required_sources", "reference_answer", "answerable"]:
            if field not in q:
                raise ValueError(f"Question at index {idx} ({q.get('id', 'unknown')}) missing required field: '{field}'")

        cat = q["category"]
        if cat not in ["single_source", "multi_source", "unanswerable"]:
            raise ValueError(f"Question {q.get('id')} has invalid category '{cat}'. Must be one of single_source, multi_source, unanswerable.")

        if not q["answerable"]:
            if cat != "unanswerable":
                raise ValueError(f"Question {q.get('id')} marked unanswerable but category is '{cat}'")
            if q["required_sources"]:
                raise ValueError(f"Unanswerable question {q.get('id')} must have empty required_sources.")

        if "evaluation_criteria" in q and not isinstance(q["evaluation_criteria"], dict):
            raise ValueError(f"Question {q.get('id')} 'evaluation_criteria' must be a dictionary.")

        if "rubric" in q:
            if not isinstance(q["rubric"], dict) or "type" not in q["rubric"]:
                raise ValueError(f"Question {q.get('id')} 'rubric' must be a dictionary with a 'type' field.")

    return questions


async def run_evaluation(
    configs: List[str],
    questions_file: Path,
    output_dir: Path,
    limit: Optional[int] = None,
    run_id: Optional[str] = None,
    mock_mode: bool = False,
    workspace_id: Optional[str] = None,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.3,
    num_ctx: int = 8192,
    schedule_strategy: str = "sequential",
    seed: Optional[int] = None
) -> Path:
    """Main evaluation runner loop."""
    active_provider = (provider or os.getenv("LLM_PROVIDER", "gemini")).strip().lower()
    if mock_mode:
        active_provider = "mock"
    elif active_provider not in ["gemini", "ollama"]:
        raise ValueError(f"Unsupported provider: '{active_provider}'. Supported providers are: 'gemini', 'ollama'.")

    if temperature < 0.0 or temperature > 2.0:
        raise ValueError(f"Invalid temperature {temperature}. Must be between 0.0 and 2.0.")

    if num_ctx < 512 or num_ctx > 131072:
        raise ValueError(f"Invalid context window size {num_ctx}. Must be between 512 and 131072.")

    validate_environment(mock_mode=mock_mode, provider=active_provider)

    questions = load_dataset(questions_file)
    if limit is not None and limit > 0:
        questions = questions[:limit]

    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = datetime.now(UTC)
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    run_id = run_id or f"run_{timestamp}_{uuid.uuid4().hex[:6]}"
    output_file = output_dir / f"{run_id}.jsonl"

    target_ws = workspace_id or str(SYNTHETIC_WORKSPACE_ID)
    target_uid = user_id or str(SYNTHETIC_DEV1_ID)
    target_email = user_email or "eval-dev1@synthetic.orbit.local"

    if mock_mode:
        model_name = model or "mock-eval-model"
        llm_instance = MockEvaluationLLM(model_name=model_name, temperature=temperature)
    else:
        from app.utils.llm_factory import get_chat_llm
        llm_instance = get_chat_llm(
            workspace_id=target_ws,
            temperature=temperature,
            provider=active_provider,
            model=model,
            base_url=base_url if active_provider == "ollama" else None,
            num_ctx=num_ctx if active_provider == "ollama" else None
        )
        model_name = getattr(llm_instance, "model", None) or getattr(llm_instance, "model_name", None) or model or "unknown"

    scheduled_attempts = generate_evaluation_schedule(
        questions=questions,
        configs=configs,
        schedule_strategy=schedule_strategy,
        seed=seed
    )
    total_attempts = len(scheduled_attempts)

    print(f"\n=======================================================")
    print(f" ORBIT RESEARCH EVALUATION RUNNER")
    print(f" Run ID       : {run_id}")
    print(f" Mode         : {'OFFLINE (Mock LLM)' if mock_mode else 'LIVE (' + active_provider + ' / ' + model_name + ')'}")
    print(f" Provider     : {active_provider}")
    print(f" Model        : {model_name}")
    print(f" Temperature  : {temperature}")
    if active_provider == "ollama":
        print(f" Num Context  : {num_ctx}")
        if base_url:
            print(f" Base URL     : {base_url}")
    print(f" Schedule     : {schedule_strategy}{' (seed=' + str(seed) + ')' if seed is not None else ''}")
    print(f" Configurations: {', '.join(configs)}")
    print(f" Questions    : {len(questions)} items ({total_attempts} attempts)")
    print(f" Output File  : {output_file}")
    print(f" Workspace ID : {target_ws}")
    print(f"=======================================================\n")

    successful_count = 0
    failed_count = 0

    with open(output_file, "a", encoding="utf-8") as out_fp:
        for attempt in scheduled_attempts:
            q = attempt["question"]
            q_id = attempt["question_id"]
            cfg_name = attempt["configuration"]
            current_attempt = attempt["attempt_index"]

            progress = f"[{current_attempt}/{total_attempts}]"
            print(f"{progress} {q_id} | {cfg_name:14s} ... ", end="", flush=True)

            eval_result = await execute_evaluation_configuration(
                config_name=cfg_name,
                question=q["question"],
                workspace_id=target_ws,
                user_id=target_uid,
                user_email=target_email,
                llm=llm_instance
            )

            sanitized_error = sanitize_secret(eval_result.get("error"))
            exec_status = "failed" if sanitized_error else eval_result.get("execution_status", "success")

            if sanitized_error:
                failed_count += 1
            else:
                successful_count += 1

            record = {
                "run_id": run_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "question_id": q_id,
                "question": q["question"],
                "category": q["category"],
                "required_sources": q["required_sources"],
                "answerable": q["answerable"],
                "reference_answer": q["reference_answer"],
                "evidence_references": q.get("evidence_references", []),
                "evaluation_criteria": q.get("evaluation_criteria", {}),
                "rubric": q.get("rubric", {}),
                "configuration": cfg_name,
                "configured_model": eval_result.get("configured_model", model or model_name),
                "resolved_model": eval_result.get("resolved_model", model_name),
                "model_parameters": eval_result.get("model_parameters", {}),
                "provider": eval_result.get("provider", active_provider),
                "available_sources": eval_result.get("available_sources", []),
                "execution_status": exec_status,
                "response": eval_result.get("response", ""),
                "tools_used": eval_result.get("tools_used", []),
                "retrieved_evidence": eval_result.get("retrieved_evidence", []),
                "latency_ms": eval_result.get("latency_ms"),
                "token_usage": eval_result.get("token_usage"),
                "error": sanitized_error
            }

            out_fp.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_fp.flush()

            if sanitized_error:
                print(f"FAILED ({eval_result.get('latency_ms')}ms) -> {sanitized_error}")
            else:
                tools_str = f"tools={len(eval_result.get('tools_used', []))}"
                print(f"DONE ({eval_result.get('latency_ms')}ms, {tools_str})")

    end_time = datetime.now(UTC)
    duration_s = (end_time - start_time).total_seconds()

    # Record run-level provenance metadata
    meta_file = output_dir / f"meta_{run_id}.json"
    with open(meta_file, "w", encoding="utf-8") as mf:
        json.dump({
            "run_id": run_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration_s, 2),
            "provider": active_provider,
            "configured_model": model,
            "resolved_model": model_name,
            "temperature": temperature,
            "num_ctx": num_ctx if active_provider == "ollama" else None,
            "base_url": base_url if active_provider == "ollama" else None,
            "schedule_strategy": schedule_strategy,
            "seed": seed,
            "configurations": configs,
            "questions_file": str(questions_file),
            "questions_count": len(questions),
            "total_attempts": total_attempts,
            "successful_attempts": successful_count,
            "failed_attempts": failed_count,
            "git_commit": get_git_commit()
        }, mf, indent=2)

    print(f"\nEvaluation run finished successfully!")
    print(f"Results recorded at: {output_file}")
    print(f"Run provenance metadata at: {meta_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Orbit Research Evaluation Runner")
    parser.add_argument(
        "--configs", "-c",
        type=str,
        default="plain_llm,rag_docs_only,full_agent",
        help="Comma-separated list of configurations to run"
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=None,
        help="Limit number of questions to evaluate (e.g. 5 for smoke test)"
    )
    parser.add_argument(
        "--questions-file", "-q",
        type=str,
        default=str(CURRENT_DIR / "questions.json"),
        help="Path to questions JSON file"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=str(CURRENT_DIR / "results"),
        help="Directory where result JSONL files will be saved"
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Custom run ID"
    )
    parser.add_argument(
        "--mock-llm",
        action="store_true",
        help="Run evaluation using Mock LLM for offline tests and sanity checking"
    )
    parser.add_argument(
        "--workspace-id",
        type=str,
        default=None,
        help="Workspace ID to target (defaults to synthetic workspace)"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        help="Model provider: 'gemini' or 'ollama' (defaults to LLM_PROVIDER env or gemini)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model identifier or Ollama model tag (e.g. 'llama3.2:3b', 'gemini-3.5-flash-lite')"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Local Ollama endpoint URL (defaults to http://localhost:11434)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="Sampling temperature (default: 0.3)"
    )
    parser.add_argument(
        "--num-ctx",
        type=int,
        default=8192,
        help="Context window size in tokens for local models (default: 8192)"
    )
    parser.add_argument(
        "--schedule",
        type=str,
        choices=VALID_SCHEDULE_STRATEGIES,
        default="sequential",
        help="Execution ordering: 'sequential', 'by_question', 'by_configuration', 'randomized'"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible randomized execution order"
    )

    args = parser.parse_args()

    selected_configs = [c.strip() for c in args.configs.split(",") if c.strip()]
    for c in selected_configs:
        if c not in CONFIGURATION_NAMES:
            print(f"Error: Unknown configuration '{c}'. Must be in {CONFIGURATION_NAMES}")
            sys.exit(1)

    if args.temperature < 0.0 or args.temperature > 2.0:
        print(f"Error: Invalid temperature {args.temperature}. Must be between 0.0 and 2.0.")
        sys.exit(1)

    if args.num_ctx < 512 or args.num_ctx > 131072:
        print(f"Error: Invalid context size {args.num_ctx}. Must be between 512 and 131072.")
        sys.exit(1)

    if args.schedule == "randomized" and args.seed is None:
        print("Error: --seed must be specified when using --schedule randomized.")
        sys.exit(1)

    asyncio.run(run_evaluation(
        configs=selected_configs,
        questions_file=Path(args.questions_file),
        output_dir=Path(args.output_dir),
        limit=args.limit,
        run_id=args.run_id,
        mock_mode=args.mock_llm,
        workspace_id=args.workspace_id,
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        temperature=args.temperature,
        num_ctx=args.num_ctx,
        schedule_strategy=args.schedule,
        seed=args.seed
    ))



if __name__ == "__main__":
    main()
