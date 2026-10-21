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
import re


def sanitize_secret(text: Optional[str]) -> Optional[str]:
    """Sanitize API keys, tokens, and DB passwords from log strings and error messages."""
    if not text:
        return text
    text = re.sub(r"AIza[A-Za-z0-9_-]{30,45}", "[REDACTED_API_KEY]", text)
    text = re.sub(r"Bearer\s+[A-Za-z0-9_.-]+", "Bearer [REDACTED_TOKEN]", text)
    text = re.sub(r"postgresql://([^:]+):([^@]+)@", r"postgresql://\1:[REDACTED_PASSWORD]@", text)
    return text


from langchain_core.runnables import Runnable
from langchain_core.messages import AIMessage


class MockEvaluationLLM(Runnable):
    """Mock LLM for offline tests and smoke checks without external API dependencies."""
    def __init__(self, model_name: str = "mock-eval-model"):
        self.model_name = model_name
        self.model = model_name

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


def validate_environment(mock_mode: bool = False) -> None:
    """Ensure necessary environment variables and dependencies exist."""
    if mock_mode:
        return

    gemini_key = os.getenv("GEMINI_API_KEY")
    db_url = os.getenv("DATABASE_URL")
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if not db_url:
        raise RuntimeError("DATABASE_URL environment variable is missing. Evaluation runner cannot access workspace data.")

    if provider == "gemini" and not gemini_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is missing. Set GEMINI_API_KEY or run with --mock-llm for offline testing.")


def load_dataset(file_path: Path) -> List[Dict[str, Any]]:
    """Load and validate question dataset."""
    if not file_path.exists():
        raise FileNotFoundError(f"Questions dataset not found at {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    if not questions:
        raise ValueError(f"No questions found in dataset file: {file_path}")

    for idx, q in enumerate(questions):
        for field in ["id", "question", "category", "required_sources", "reference_answer", "answerable"]:
            if field not in q:
                raise ValueError(f"Question at index {idx} ({q.get('id', 'unknown')}) missing required field: '{field}'")

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
    user_email: Optional[str] = None
) -> Path:
    """Main evaluation runner loop."""
    validate_environment(mock_mode=mock_mode)

    questions = load_dataset(questions_file)
    if limit is not None and limit > 0:
        questions = questions[:limit]

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    run_id = run_id or f"run_{timestamp}_{uuid.uuid4().hex[:6]}"
    output_file = output_dir / f"{run_id}.jsonl"

    target_ws = workspace_id or str(SYNTHETIC_WORKSPACE_ID)
    target_uid = user_id or str(SYNTHETIC_DEV1_ID)
    target_email = user_email or "eval-dev1@synthetic.orbit.local"

    llm_instance = MockEvaluationLLM() if mock_mode else None
    model_name = "mock-eval-model" if mock_mode else os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    print(f"\n=======================================================")
    print(f" ORBIT RESEARCH EVALUATION RUNNER")
    print(f" Run ID       : {run_id}")
    print(f" Mode         : {'OFFLINE (Mock LLM)' if mock_mode else 'LIVE (' + model_name + ')'}")
    print(f" Configurations: {', '.join(configs)}")
    print(f" Questions    : {len(questions)} items")
    print(f" Output File  : {output_file}")
    print(f" Workspace ID : {target_ws}")
    print(f"=======================================================\n")

    total_attempts = len(questions) * len(configs)
    current_attempt = 0

    with open(output_file, "a", encoding="utf-8") as out_fp:
        for q in questions:
            q_id = q["id"]
            q_text = q["question"]
            category = q["category"]
            req_sources = q["required_sources"]
            ref_ans = q["reference_answer"]
            answerable = q["answerable"]
            evidence_refs = q.get("evidence_references", [])

            for cfg_name in configs:
                current_attempt += 1
                progress = f"[{current_attempt}/{total_attempts}]"
                print(f"{progress} {q_id} | {cfg_name:14s} ... ", end="", flush=True)

                eval_result = await execute_evaluation_configuration(
                    config_name=cfg_name,
                    question=q_text,
                    workspace_id=target_ws,
                    user_id=target_uid,
                    user_email=target_email,
                    llm=llm_instance
                )

                sanitized_error = sanitize_secret(eval_result.get("error"))
                exec_status = "failed" if sanitized_error else eval_result.get("execution_status", "success")

                record = {
                    "run_id": run_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "question_id": q_id,
                    "question": q_text,
                    "category": category,
                    "required_sources": req_sources,
                    "answerable": answerable,
                    "reference_answer": ref_ans,
                    "evidence_references": evidence_refs,
                    "evaluation_criteria": q.get("evaluation_criteria", {}),
                    "rubric": q.get("rubric", {}),
                    "configuration": cfg_name,
                    "configured_model": eval_result.get("configured_model", model_name),
                    "resolved_model": eval_result.get("resolved_model", model_name),
                    "model_parameters": eval_result.get("model_parameters", {}),
                    "provider": eval_result.get("provider", "gemini"),
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

    print(f"\nEvaluation run finished successfully!")
    print(f"Results recorded at: {output_file}")
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

    args = parser.parse_args()

    selected_configs = [c.strip() for c in args.configs.split(",") if c.strip()]
    for c in selected_configs:
        if c not in CONFIGURATION_NAMES:
            print(f"Error: Unknown configuration '{c}'. Must be in {CONFIGURATION_NAMES}")
            sys.exit(1)

    asyncio.run(run_evaluation(
        configs=selected_configs,
        questions_file=Path(args.questions_file),
        output_dir=Path(args.output_dir),
        limit=args.limit,
        run_id=args.run_id,
        mock_mode=args.mock_llm,
        workspace_id=args.workspace_id
    ))


if __name__ == "__main__":
    main()
