import requests
from typing import Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, HumanMessage
from langchain_core.outputs import ChatResult, ChatGeneration


class OllamaChatFallback(BaseChatModel):
    """Fallback Ollama chat model using direct HTTP requests when langchain-ollama is not installed."""
    model: str = "llama3.2"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.3

    @property
    def _llm_type(self) -> str:
        return "ollama-direct"

    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        payload_messages = []
        for m in messages:
            if isinstance(m, SystemMessage):
                payload_messages.append({"role": "system", "content": m.content})
            elif isinstance(m, HumanMessage):
                payload_messages.append({"role": "user", "content": m.content})
            elif isinstance(m, AIMessage):
                payload_messages.append({"role": "assistant", "content": m.content})
            else:
                payload_messages.append({"role": "user", "content": str(m.content)})
        return payload_messages

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> ChatResult:
        payload = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "stream": False,
            "options": {"temperature": self.temperature}
        }
        if stop:
            payload["options"]["stop"] = stop

        resp = requests.post(
            f"{self.base_url.rstrip('/')}/api/chat",
            json=payload,
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

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
