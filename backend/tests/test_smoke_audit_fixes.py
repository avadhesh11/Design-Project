"""
Regression tests for Phase 3 smoke-test audit fixes:
1. Scorer matching robustness for target values with punctuation/markdown (e.g. `/api/v2`, ``/api/v2``, `**/api/v2**`).
2. Full-agent task retrieval guideline and tool invocation for Q53.
3. Unanswerable question factual grounding guideline and refusal scoring for Q85.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from langchain_core.messages import AIMessage, ToolMessage

from evaluation.score_results import (
    _contains_fact,
    _is_contradiction,
    evaluate_answer_correctness,
    evaluate_unanswerable_refusal,
    calculate_evidence_faithfulness
)
from app.agents.agent import run_agent, EvaluationConfig, get_agent_tools


# ===========================================================================
# 1. Scorer Robustness Tests (Issue 1 - Q21)
# ===========================================================================

def test_contains_fact_markdown_and_punctuation():
    target = "/api/v2"

    # Plain match
    assert _contains_fact(target, "The API uses /api/v2 endpoints.") is True
    # Markdown inline code (backticks)
    assert _contains_fact(target, "clients should use the `/api/v2` prefix for REST endpoints.") is True
    # Markdown bold (asterisks)
    assert _contains_fact(target, "clients should use the **/api/v2** prefix for REST endpoints.") is True
    # Markdown bold-italic
    assert _contains_fact(target, "clients should use ***/api/v2*** prefix.") is True
    # Quotes and brackets
    assert _contains_fact(target, "prefix is '/api/v2'.") is True
    assert _contains_fact(target, "prefix is \"/api/v2\".") is True
    assert _contains_fact(target, "see (/api/v2) documentation.") is True
    assert _contains_fact(target, "see [/api/v2] endpoint.") is True

    # Negative / non-matching cases
    assert _contains_fact(target, "clients should use /api/v1.") is False
    assert _contains_fact(target, "prefix is /api/v20.") is False
    assert _contains_fact(target, "unrelated text without the prefix.") is False


def test_is_contradiction_markdown_and_punctuation():
    forbidden = "/api/v1"
    # Contradiction asserted plain
    assert _is_contradiction(forbidden, "Clients must use /api/v1.") is True
    # Contradiction asserted in backticks
    assert _is_contradiction(forbidden, "Clients must use `/api/v1`.") is True
    # Contradiction asserted in bold
    assert _is_contradiction(forbidden, "Clients must use **/api/v1**.") is True
    # Negated / transitional context (not a contradiction)
    assert _is_contradiction(forbidden, "Clients must use /api/v2, not `/api/v1`.") is False
    assert _is_contradiction(forbidden, "Do not use /api/v1.") is False


def test_q21_evaluation_scoring_with_markdown_responses():
    criteria = {
        "target_values": ["/api/v2"],
        "required_concepts": ["api", "prefix"],
        "forbidden_values": ["/api/v1"]
    }
    rubric = {"type": "exact_value", "description": "Must state /api/v2; penalize contradictory values."}
    ref_ans = "The Orbit API uses REST endpoints under the /api/v2 prefix."

    # Backtick response (from Gemini rag_docs_only)
    resp_backticks = "Based on the Orbit Architecture Specification, clients should use the `/api/v2` prefix for REST endpoints."
    eval_backticks = evaluate_answer_correctness(resp_backticks, ref_ans, criteria, rubric)
    assert eval_backticks["score"] == 1.0, f"Failed: {eval_backticks['rationale']}"
    assert not eval_backticks["mismatches"]

    # Bold response (from Gemini full_agent)
    resp_bold = "Based on the Orbit Architecture Specification, clients should use the **/api/v2** prefix for REST endpoints."
    eval_bold = evaluate_answer_correctness(resp_bold, ref_ans, criteria, rubric)
    assert eval_bold["score"] == 1.0, f"Failed: {eval_bold['rationale']}"
    assert not eval_bold["mismatches"]

    # Faithfulness scoring with markdown
    doc_evidence = [{
        "source": "documents",
        "content": "The Orbit API uses REST endpoints under the /api/v2 prefix."
    }]
    faith_backticks = calculate_evidence_faithfulness(
        response_text=resp_backticks,
        answerable=True,
        criteria=criteria,
        available_sources=["documents"],
        retrieved_evidence=doc_evidence,
        has_error=False
    )
    assert faith_backticks["score"] == 1.0
    assert faith_backticks["status"] == "faithful"


# ===========================================================================
# 2. Full-Agent Task Retrieval Prompting & Execution (Issue 2 - Q53)
# ===========================================================================

def test_agent_prompt_includes_task_guideline_for_full_agent():
    async def _test():
        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [MagicMock(content="Mock response", name=None)]
        })

        # 1. Full agent (tasks=True) must have task_guideline
        with patch("app.rag.vector_store.search_similar", return_value=[]), \
             patch("app.agents.agent.create_react_agent", return_value=mock_agent) as mock_create_agent:

            config_full = EvaluationConfig(documents=True, tasks=True, chat=True, preinject_documents=True)
            await run_agent(
                message="When is Priya's document export task due?",
                workspace_id="00000000-0000-4000-8000-000000000003",
                user_id="user-1",
                user_email="dev@orbit.local",
                is_admin=False,
                eval_config=config_full,
                llm_override=MagicMock()
            )
            passed_prompt = mock_create_agent.call_args[1]["prompt"]
            assert "Task Due Dates & Tracker Records:" in passed_prompt
            assert "get_tasks is the authoritative source for actual task dates and statuses" in passed_prompt

        # 2. RAG docs only (tasks=False) must NOT have task_guideline
        with patch("app.rag.vector_store.search_similar", return_value=[]), \
             patch("app.agents.agent.create_react_agent", return_value=mock_agent) as mock_create_agent:

            config_rag = EvaluationConfig(documents=True, tasks=False, chat=False, preinject_documents=True)
            await run_agent(
                message="When is Priya's document export task due?",
                workspace_id="00000000-0000-4000-8000-000000000003",
                user_id="user-1",
                user_email="dev@orbit.local",
                is_admin=False,
                eval_config=config_rag,
                llm_override=MagicMock()
            )
            passed_prompt = mock_create_agent.call_args[1]["prompt"]
            assert "Task Due Dates & Tracker Records:" not in passed_prompt

    asyncio.run(_test())


def test_full_agent_q53_invokes_get_tasks_and_synthesizes_both_dates():
    async def _test():
        # Deterministic mock simulating tool invocation loop in create_react_agent:
        # Step 1: Model calls get_tasks
        # Step 2: Tool returns task record
        # Step 3: Model returns answer with both 11 November and 7 November
        task_output = (
            '[{"id": "50", "title": "Document export", "status": "in_progress", '
            '"due_date": "2026-11-07T00:00:00Z", "assigned_to": "priya"}]'
        )

        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[{"name": "get_tasks", "args": {}, "id": "call_1"}]
                ),
                ToolMessage(content=task_output, tool_call_id="call_1", name="get_tasks"),
                AIMessage(
                    content=(
                        "The Sprint 15 release candidate is planned for 11 November 2026, "
                        "and Priya's document export task is due on 7 November 2026."
                    )
                )
            ]
        })

        with patch("app.rag.vector_store.search_similar", return_value=[{
            "source_id": "doc3",
            "content": "Orbit Release Plan Sprint 15: The release candidate is planned for 11 November 2026."
        }]), patch("app.agents.agent.create_react_agent", return_value=mock_agent):

            config_full = EvaluationConfig(documents=True, tasks=True, chat=True, preinject_documents=True)
            result = await run_agent(
                message="When is the Sprint 15 release candidate planned, and what is the due date for Priya's document export task?",
                workspace_id="00000000-0000-4000-8000-000000000003",
                user_id="user-1",
                user_email="dev@orbit.local",
                is_admin=False,
                eval_config=config_full,
                llm_override=MagicMock()
            )

            assert "get_tasks" in result["tools_used"]
            assert "11 November 2026" in result["response"]
            assert "7 November 2026" in result["response"]

            # Score the synthesized output
            criteria = {
                "target_values": ["11 November 2026", "7 November 2026"],
                "required_concepts": ["release candidate", "export"],
                "forbidden_values": []
            }
            rubric = {"type": "multi_source_synthesis", "description": "Combine facts from both sources"}
            eval_q53 = evaluate_answer_correctness(
                result["response"],
                "The Sprint 15 release candidate is planned for 11 November 2026, and Priya's document export task is due on 7 November 2026.",
                criteria,
                rubric
            )
            assert eval_q53["score"] == 1.0

    asyncio.run(_test())


# ===========================================================================
# 3. Unanswerable Question Factual Grounding & Refusal (Issue 3 - Q85)
# ===========================================================================

def test_agent_prompt_includes_unanswerable_abstention_guideline():
    async def _test():
        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [MagicMock(content="Mock response", name=None)]
        })

        with patch("app.rag.vector_store.search_similar", return_value=[]), \
             patch("app.agents.agent.create_react_agent", return_value=mock_agent) as mock_create_agent:

            config_full = EvaluationConfig(documents=True, tasks=True, chat=True, preinject_documents=True)
            await run_agent(
                message="What exact date and time will the next major Orbit mobile app version be released?",
                workspace_id="00000000-0000-4000-8000-000000000003",
                user_id="user-1",
                user_email="dev@orbit.local",
                is_admin=False,
                eval_config=config_full,
                llm_override=MagicMock()
            )
            passed_prompt = mock_create_agent.call_args[1]["prompt"]
            assert "Factual Grounding & Unanswerable Questions:" in passed_prompt
            assert "a general web release date or a mobile layout styling fix must NEVER be treated as the release date of a dedicated mobile application" in passed_prompt

    asyncio.run(_test())


def test_q85_refusal_and_over_answering_scoring():
    criteria = {
        "target_values": [],
        "required_concepts": ["not available", "no information", "not found", "cannot be answered", "does not contain"],
        "forbidden_values": []
    }
    rubric = {"type": "refusal", "description": "Must clearly state that requested fact is unavailable."}

    # 1. Compliant abstention response
    proper_refusal = (
        "This information is not available in the workspace documents or tasks, "
        "as no release date or schedule for a dedicated Orbit mobile application is specified."
    )
    score_refusal = evaluate_unanswerable_refusal(proper_refusal, criteria, rubric)
    assert score_refusal["score"] == 1.0
    assert "Valid refusal" in score_refusal["rationale"]

    # 2. Over-answering / hallucination response (failing to refuse)
    hallucinated_answer = (
        "Based on the Orbit Release Plan Sprint 15, the target production launch date is 16 November 2026."
    )
    score_hallucination = evaluate_unanswerable_refusal(hallucinated_answer, criteria, rubric)
    assert score_hallucination["score"] == 0.0
    assert "Failed refusal" in score_hallucination["rationale"]


def test_plural_refusal_scoring_q93_and_q99():
    """
    Ensure semantically equivalent plural phrasings like 'documents and task records do not contain information'
    are accepted as valid refusals, while forbidden fabricated values still trigger 0.0.
    """
    criteria_q93 = {
        "target_values": [],
        "required_concepts": ["not available", "no information", "not found", "cannot be answered", "does not contain"],
        "forbidden_values": ["Alex Rivera", "David Kim"]
    }
    rubric = {"type": "refusal", "description": "Must clearly state that the requested fact is unavailable."}

    # 1. Exact Q93 response from live Gemini benchmark
    resp_q93 = "The available workspace documents and task records do not contain information regarding who is on call for the production API this weekend."
    eval_q93 = evaluate_unanswerable_refusal(resp_q93, criteria_q93, rubric)
    assert eval_q93["score"] == 1.0, f"Failed: {eval_q93['rationale']}"
    assert "Valid refusal" in eval_q93["rationale"]

    # 2. Exact Q99 response from live Gemini benchmark
    criteria_q99 = {
        "target_values": [],
        "required_concepts": ["not available", "no information", "not found", "cannot be answered", "does not contain"],
        "forbidden_values": ["Sarah Chen", "CEO"]
    }
    resp_q99 = "The available workspace documents and task tracker records do not contain information about who approved the final press release wording or when it was approved."
    eval_q99 = evaluate_unanswerable_refusal(resp_q99, criteria_q99, rubric)
    assert eval_q99["score"] == 1.0, f"Failed: {eval_q99['rationale']}"
    assert "Valid refusal" in eval_q99["rationale"]

    # 3. Plural phrasing with forbidden fabricated value MUST STILL FAIL (rubric integrity)
    resp_fabricated = "The available workspace documents and task records do not contain full details, but Alex Rivera is on call."
    eval_fab = evaluate_unanswerable_refusal(resp_fabricated, criteria_q93, rubric)
    assert eval_fab["score"] == 0.0
    assert "Fabricated facts detected" in eval_fab["rationale"]

    # 4. Other plural variations
    assert evaluate_unanswerable_refusal("Workspace records do not specify this detail.", criteria_q93, rubric)["score"] == 1.0
    assert evaluate_unanswerable_refusal("Existing documents do not provide this date.", criteria_q93, rubric)["score"] == 1.0
    assert evaluate_unanswerable_refusal("The tasks do not mention any on-call schedule.", criteria_q93, rubric)["score"] == 1.0
