import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.agents.agent import get_agent_tools, EvaluationConfig, run_agent


def test_get_agent_tools_with_evaluation_filtering():
    """Verify tool filtering under various EvaluationConfig settings."""
    workspace_id = "test-ws-id"
    user_id = "test-user-id"

    # 1. Documents only
    config_docs = EvaluationConfig(documents=True, tasks=False, chat=False, allow_admin_actions=False)
    tools_docs = get_agent_tools(is_admin=True, workspace_id=workspace_id, user_id=user_id, eval_config=config_docs)
    tool_names_docs = [t.name for t in tools_docs]
    assert tool_names_docs == ["search_workspace_tool"]

    # 2. Tasks only
    config_tasks = EvaluationConfig(documents=False, tasks=True, chat=False, allow_admin_actions=False)
    tools_tasks = get_agent_tools(is_admin=True, workspace_id=workspace_id, user_id=user_id, eval_config=config_tasks)
    tool_names_tasks = [t.name for t in tools_tasks]
    assert tool_names_tasks == ["get_tasks_tool"]

    # 3. Chat only
    config_chat = EvaluationConfig(documents=False, tasks=False, chat=True, allow_admin_actions=False)
    tools_chat = get_agent_tools(is_admin=True, workspace_id=workspace_id, user_id=user_id, eval_config=config_chat)
    tool_names_chat = [t.name for t in tools_chat]
    assert tool_names_chat == ["get_recent_chat_tool"]

    # 4. Full evaluation configuration: all 3 read tools, zero admin action tools
    config_full = EvaluationConfig(documents=True, tasks=True, chat=True, allow_admin_actions=False)
    tools_full = get_agent_tools(is_admin=True, workspace_id=workspace_id, user_id=user_id, eval_config=config_full)
    tool_names_full = [t.name for t in tools_full]
    assert set(tool_names_full) == {"search_workspace_tool", "get_tasks_tool", "get_recent_chat_tool"}
    # Verify no admin action tools are included
    for admin_tool in ["create_task_tool", "update_task_tool", "send_task_reminder_email_tool", "send_deadline_alert_email_tool", "send_important_info_email_tool"]:
        assert admin_tool not in tool_names_full


def test_get_agent_tools_production_default_behavior():
    """Verify production behavior is preserved when eval_config is None."""
    workspace_id = "test-ws-id"
    user_id = "test-user-id"

    # Member role: 3 read tools
    tools_member = get_agent_tools(is_admin=False, workspace_id=workspace_id, user_id=user_id, eval_config=None)
    names_member = [t.name for t in tools_member]
    assert set(names_member) == {"search_workspace_tool", "get_tasks_tool", "get_recent_chat_tool"}

    # Admin role: 3 read tools + 5 admin tools
    tools_admin = get_agent_tools(is_admin=True, workspace_id=workspace_id, user_id=user_id, eval_config=None)
    names_admin = [t.name for t in tools_admin]
    assert len(names_admin) == 8
    assert "create_task_tool" in names_admin
    assert "update_task_tool" in names_admin


import asyncio

def test_document_preinjection_enabled_and_disabled():
    """Verify pre-injection adds chunks when enabled, and omits them when disabled."""
    async def _test():
        fake_chunks = [
            {"content": "Orbit Architecture specifies backend port 8000."},
            {"content": "Redis pool size is 30 connections."}
        ]

        mock_llm = MagicMock()
        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [MagicMock(content="Synthetic agent answer", name=None)]
        })

        # Test Case A: Pre-injection enabled (documents=True, preinject_documents=True)
        with patch("app.rag.vector_store.search_similar", return_value=fake_chunks) as mock_search, \
             patch("app.agents.agent.create_react_agent", return_value=mock_agent) as mock_create_agent:

            config_enabled = EvaluationConfig(documents=True, tasks=True, chat=True, preinject_documents=True)
            await run_agent(
                message="What is the backend port?",
                workspace_id="ws-test",
                user_id="user-test",
                user_email="test@orbit.local",
                is_admin=False,
                eval_config=config_enabled,
                llm_override=mock_llm
            )

            mock_search.assert_called_once()
            passed_prompt = mock_create_agent.call_args[1]["prompt"]
            assert "Relevant Workspace Knowledge Base Documents:" in passed_prompt
            assert "Orbit Architecture specifies backend port 8000." in passed_prompt

        # Test Case B: Pre-injection disabled (preinject_documents=False)
        with patch("app.rag.vector_store.search_similar", return_value=fake_chunks) as mock_search, \
             patch("app.agents.agent.create_react_agent", return_value=mock_agent) as mock_create_agent:

            config_no_preinject = EvaluationConfig(documents=True, tasks=True, chat=True, preinject_documents=False)
            await run_agent(
                message="What is the backend port?",
                workspace_id="ws-test",
                user_id="user-test",
                user_email="test@orbit.local",
                is_admin=False,
                eval_config=config_no_preinject,
                llm_override=mock_llm
            )

            # search_similar must NOT be called when preinject_documents=False
            mock_search.assert_not_called()
            passed_prompt = mock_create_agent.call_args[1]["prompt"]
            assert "Relevant Workspace Knowledge Base Documents:" not in passed_prompt
            assert "Orbit Architecture specifies backend port 8000." not in passed_prompt

        # Test Case C: Documents completely disabled (documents=False)
        with patch("app.rag.vector_store.search_similar", return_value=fake_chunks) as mock_search, \
             patch("app.agents.agent.create_react_agent", return_value=mock_agent) as mock_create_agent:

            config_no_docs = EvaluationConfig(documents=False, tasks=True, chat=True, preinject_documents=True)
            await run_agent(
                message="What is the backend port?",
                workspace_id="ws-test",
                user_id="user-test",
                user_email="test@orbit.local",
                is_admin=False,
                eval_config=config_no_docs,
                llm_override=mock_llm
            )

            mock_search.assert_not_called()
            passed_prompt = mock_create_agent.call_args[1]["prompt"]
            assert "Relevant Workspace Knowledge Base Documents:" not in passed_prompt
            passed_tools = mock_create_agent.call_args[1]["tools"]
            assert "search_workspace_tool" not in [t.name for t in passed_tools]

    asyncio.run(_test())
