import json
import uuid
import requests
from typing import Any, List, Optional, Sequence
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatResult, ChatGeneration


class OllamaChatFallback(BaseChatModel):
    """Fallback Ollama chat model using direct HTTP requests when langchain-ollama is not installed."""
    model: str = "llama3.2"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.3
    num_ctx: int = 8192
    bound_tools: Optional[List[dict]] = None

    @property
    def _llm_type(self) -> str:
        return "ollama-direct"

    def bind_tools(
        self,
        tools: Sequence[Any],
        **kwargs: Any
    ) -> "OllamaChatFallback":
        """Bind tools to the Ollama chat model using OpenAI-compatible schema."""
        from langchain_core.utils.function_calling import convert_to_openai_tool
        formatted = [convert_to_openai_tool(t) for t in tools]
        return OllamaChatFallback(
            model=self.model,
            base_url=self.base_url,
            temperature=self.temperature,
            num_ctx=self.num_ctx,
            bound_tools=formatted
        )

    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        payload_messages = []
        for m in messages:
            if isinstance(m, SystemMessage):
                payload_messages.append({"role": "system", "content": m.content})
            elif isinstance(m, HumanMessage):
                payload_messages.append({"role": "user", "content": m.content})
            elif isinstance(m, ToolMessage):
                payload_messages.append({"role": "tool", "content": str(m.content)})
            elif isinstance(m, AIMessage):
                entry = {"role": "assistant", "content": m.content or ""}
                if getattr(m, "tool_calls", None):
                    formatted_tc = []
                    for tc in m.tool_calls:
                        raw_args = tc.get("args", {})
                        if isinstance(raw_args, dict):
                            parsed_args = raw_args
                        elif isinstance(raw_args, str):
                            try:
                                parsed_args = json.loads(raw_args)
                                if not isinstance(parsed_args, dict):
                                    parsed_args = {}
                            except Exception:
                                parsed_args = {}
                        else:
                            parsed_args = {}
                        formatted_tc.append({
                            "id": tc.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": parsed_args
                            }
                        })
                    entry["tool_calls"] = formatted_tc
                payload_messages.append(entry)
            else:
                payload_messages.append({"role": "user", "content": str(getattr(m, "content", m))})
        return payload_messages

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> ChatResult:
        options = {"temperature": self.temperature}
        if self.num_ctx is not None:
            options["num_ctx"] = self.num_ctx

        payload = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "stream": False,
            "options": options
        }
        if self.bound_tools:
            payload["tools"] = self.bound_tools
        if stop:
            payload["options"]["stop"] = stop

        resp = requests.post(
            f"{self.base_url.rstrip('/')}/api/chat",
            json=payload,
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        msg_data = data.get("message", {})
        content = msg_data.get("content", "")

        raw_tc = msg_data.get("tool_calls", [])
        tool_calls = []
        for tc in raw_tc:
            func = tc.get("function", {})
            args = func.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    pass
            tool_calls.append({
                "name": func.get("name", ""),
                "args": args if isinstance(args, dict) else {},
                "id": tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
            })

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content, tool_calls=tool_calls if tool_calls else []))])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> ChatResult:
        # Run synchronous call in thread pool for async compatibility
        import asyncio
        return await asyncio.to_thread(self._generate, messages, stop, run_manager, **kwargs)

