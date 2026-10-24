import os
import logging
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from ..database import SessionLocal
from ..models import Workspace

logger = logging.getLogger(__name__)


def get_chat_llm(
    workspace: Optional[Workspace] = None,
    workspace_id: Optional[str] = None,
    db: Optional[any] = None,
    temperature: float = 0.3,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    num_ctx: Optional[int] = None
) -> BaseChatModel:
    """
    Factory function to return the configured LLM (Google Gemini or Local Ollama/Llama).
    Resolves preferences from:
    1. Explicit arguments (provider, model, base_url, temperature, num_ctx)
    2. Given Workspace instance
    3. Workspace record looked up by workspace_id
    4. Global environment variables (LLM_PROVIDER, GEMINI_MODEL, OLLAMA_MODEL, OLLAMA_BASE_URL, OLLAMA_NUM_CTX)
    """
    ws = workspace

    if not ws and workspace_id:
        created_session = False
        session = db
        if not session:
            session = SessionLocal()
            created_session = True
        try:
            ws = session.query(Workspace).filter(Workspace.id == workspace_id).first()
        except Exception as e:
            logger.warning(f"Could not load workspace for LLM resolution: {e}")
        finally:
            if created_session:
                session.close()

    # Determine provider
    if provider is not None:
        p_norm = provider.strip().lower()
        if p_norm not in ["gemini", "ollama", "local", "llama"]:
            raise ValueError(f"Unsupported provider: '{provider}'. Supported providers are: 'gemini', 'ollama'.")
    else:
        p_norm = (getattr(ws, "ai_provider", None) or os.getenv("LLM_PROVIDER", "gemini")).strip().lower()

    if temperature < 0.0 or temperature > 2.0:
        raise ValueError(f"Invalid temperature {temperature}. Must be between 0.0 and 2.0.")

    if num_ctx is not None:
        if not isinstance(num_ctx, int) or num_ctx < 512 or num_ctx > 131072:
            raise ValueError(f"Invalid context window size {num_ctx}. Must be an integer between 512 and 131072.")

    if p_norm in ["ollama", "local", "llama"]:
        resolved_model = model or getattr(ws, "ai_model", None)
        if not resolved_model or "gemini" in resolved_model:
            resolved_model = os.getenv("OLLAMA_MODEL", "llama3.2")

        resolved_base_url = base_url or getattr(ws, "ai_ollama_url", None) or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        resolved_base_url = resolved_base_url.rstrip("/")

        resolved_num_ctx = num_ctx if num_ctx is not None else int(os.getenv("OLLAMA_NUM_CTX", "8192"))

        # Verify Ollama service and model availability without silent switching
        try:
            import requests
            tag_resp = requests.get(f"{resolved_base_url}/api/tags", timeout=2.0)
            if tag_resp.status_code == 200:
                installed = [m.get("name") for m in tag_resp.json().get("models", [])]
                if installed:
                    if resolved_model in installed:
                        pass
                    elif f"{resolved_model}:latest" in installed:
                        resolved_model = f"{resolved_model}:latest"
                    elif any(m.startswith(f"{resolved_model}:") for m in installed):
                        matched = next(m for m in installed if m.startswith(f"{resolved_model}:"))
                        resolved_model = matched
                    else:
                        raise RuntimeError(
                            f"Configured model '{resolved_model}' not found in Ollama at {resolved_base_url}. "
                            f"Installed models: {installed}. Please run 'ollama pull {resolved_model}' first."
                        )
            else:
                logger.warning(f"Ollama returned status {tag_resp.status_code} at {resolved_base_url}/api/tags")
        except requests.exceptions.RequestException as net_err:
            if provider or os.getenv("LLM_PROVIDER") in ["ollama", "local", "llama"]:
                raise RuntimeError(
                    f"Ollama service is unavailable at {resolved_base_url}: {net_err}. "
                    f"Please ensure Ollama is running or use --mock-llm for offline testing."
                )
            logger.warning(f"Could not connect to Ollama at {resolved_base_url}: {net_err}")

        logger.info(f"Using Local Ollama LLM: model={resolved_model}, base_url={resolved_base_url}, num_ctx={resolved_num_ctx}")

        # 1. Try langchain_ollama
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(model=resolved_model, base_url=resolved_base_url, temperature=temperature, num_ctx=resolved_num_ctx)
        except ImportError:
            pass

        # 2. Try langchain_community ChatOllama
        try:
            from langchain_community.chat_models import ChatOllama
            return ChatOllama(model=resolved_model, base_url=resolved_base_url, temperature=temperature, num_ctx=resolved_num_ctx)
        except ImportError:
            pass

        # 3. Try langchain_openai pointing to Ollama's native /v1 endpoint
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                base_url=f"{resolved_base_url}/v1",
                api_key="ollama",
                model=resolved_model,
                temperature=temperature,
                model_kwargs={"options": {"num_ctx": resolved_num_ctx}}
            )
        except Exception as e:
            logger.debug(f"Failed to initialize ChatOpenAI against Ollama: {e}")

        # 4. Fallback lightweight wrapper using requests
        from .ollama_fallback import OllamaChatFallback
        return OllamaChatFallback(
            model=resolved_model,
            base_url=resolved_base_url,
            temperature=temperature,
            num_ctx=resolved_num_ctx
        )

    else:
        # Default: Google Gemini Cloud
        resolved_model = model or getattr(ws, "ai_model", None)
        if not resolved_model or "gemini" not in resolved_model:
            resolved_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

        api_key = os.getenv("GEMINI_API_KEY")
        logger.info(f"Using Google Gemini LLM: model={resolved_model}")

        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=resolved_model,
            google_api_key=api_key,
            temperature=temperature
        )

