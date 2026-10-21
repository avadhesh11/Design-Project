import time
from typing import Optional, Any
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.agent import EvaluationConfig, run_agent
from app.utils.llm_factory import get_chat_llm

CONFIGURATION_NAMES = ["plain_llm", "rag_docs_only", "full_agent"]

CONFIG_DEFINITIONS = {
    "plain_llm": {
        "name": "plain_llm",
        "description": "Plain LLM baseline without workspace documents, tasks, chat history, or tools.",
        "type": "direct_chat",
        "has_tools": False,
        "has_documents": False,
        "has_tasks": False,
        "has_chat": False,
    },
    "rag_docs_only": {
        "name": "rag_docs_only",
        "description": "Documents-only RAG enabling document retrieval and pre-injection; task and chat tools disabled.",
        "type": "react_agent",
        "has_tools": True,
        "has_documents": True,
        "has_tasks": False,
        "has_chat": False,
        "eval_config": EvaluationConfig(
            documents=True,
            tasks=False,
            chat=False,
            preinject_documents=True,
            allow_admin_actions=False
        ),
    },
    "full_agent": {
        "name": "full_agent",
        "description": "Full Orbit agent with documents, tasks, and team chat read tools enabled; admin action tools disabled.",
        "type": "react_agent",
        "has_tools": True,
        "has_documents": True,
        "has_tasks": True,
        "has_chat": True,
        "eval_config": EvaluationConfig(
            documents=True,
            tasks=True,
            chat=True,
            preinject_documents=True,
            allow_admin_actions=False
        ),
    },
}


async def run_plain_llm_execution(
    question: str,
    workspace_id: str,
    llm: Optional[Any] = None
) -> dict:
    """Execute the Plain LLM baseline without any tools, RAG, or workspace context."""
    if llm is None:
        llm = get_chat_llm(workspace_id=workspace_id, temperature=0.3)

    minimal_instruction = (
        "You are an AI assistant. Answer the user's question accurately based only on your knowledge. "
        "If you do not know the answer or lack sufficient information, state clearly that you do not have enough information."
    )

    messages = [
        SystemMessage(content=minimal_instruction),
        HumanMessage(content=question)
    ]

    response = await llm.ainvoke(messages)
    raw_content = response.content
    if isinstance(raw_content, list):
        resp_text = "".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in raw_content
        )
    else:
        resp_text = str(raw_content or "")

    token_usage = None
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        token_usage = dict(response.usage_metadata)
    elif hasattr(response, "response_metadata") and isinstance(response.response_metadata, dict):
        token_usage = response.response_metadata.get("token_usage") or response.response_metadata.get("usage")

    return {
        "response": resp_text,
        "tools_used": [],
        "role": "model",
        "is_admin": False,
        "token_usage": token_usage
    }


async def execute_evaluation_configuration(
    config_name: str,
    question: str,
    workspace_id: str,
    user_id: str,
    user_email: str,
    llm: Optional[Any] = None
) -> dict:
    """
    Unified entrypoint to invoke any of the three evaluation configurations:
    - plain_llm
    - rag_docs_only
    - full_agent
    """
    if config_name not in CONFIG_DEFINITIONS:
        raise ValueError(f"Unknown configuration '{config_name}'. Must be one of {CONFIGURATION_NAMES}")

    start_time = time.perf_counter()
    error_message = None
    result = None

    try:
        if config_name == "plain_llm":
            result = await run_plain_llm_execution(
                question=question,
                workspace_id=workspace_id,
                llm=llm
            )
        else:
            config_meta = CONFIG_DEFINITIONS[config_name]
            eval_config = config_meta["eval_config"]

            result = await run_agent(
                message=question,
                workspace_id=workspace_id,
                user_id=user_id,
                user_email=user_email,
                is_admin=False,
                history=[],
                eval_config=eval_config,
                llm_override=llm
            )
    except Exception as e:
        error_message = str(e)
        result = {
            "response": f"Evaluation error: {error_message}",
            "tools_used": [],
            "role": "model",
            "is_admin": False,
            "token_usage": None
        }

    elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    return {
        "configuration": config_name,
        "question": question,
        "response": result.get("response", ""),
        "tools_used": result.get("tools_used", []),
        "token_usage": result.get("token_usage"),
        "latency_ms": elapsed_ms,
        "error": error_message
    }
