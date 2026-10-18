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
    temperature: float = 0.3
) -> BaseChatModel:
    """
    Factory function to return the configured LLM (Google Gemini or Local Ollama/Llama).
    Resolves preferences from:
    1. Given Workspace instance
    2. Workspace record looked up by workspace_id
    3. Global environment variables (LLM_PROVIDER, GEMINI_MODEL, OLLAMA_MODEL, OLLAMA_BASE_URL)
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

    # Determine provider and model
    provider = getattr(ws, "ai_provider", None) or os.getenv("LLM_PROVIDER", "gemini")
    provider = provider.strip().lower()

    if provider in ["ollama", "local", "llama"]:
        model = getattr(ws, "ai_model", None)
        if not model or "gemini" in model:
            model = os.getenv("OLLAMA_MODEL", "llama3.2")

        base_url = getattr(ws, "ai_ollama_url", None) or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        base_url = base_url.rstrip("/")

        # Auto-detect installed models in Ollama to avoid 404 'model not found'
        try:
            import requests
            tag_resp = requests.get(f"{base_url}/api/tags", timeout=1.5)
            if tag_resp.status_code == 200:
                installed = [m.get("name") for m in tag_resp.json().get("models", [])]
                if installed and model not in installed:
                    base_req = model.split(":")[0].split(".")[0].lower()
                    matched = next((m for m in installed if base_req in m.lower()), None)
                    if matched:
                        print(f"[AI ENGINE] Notice: Model '{model}' not found in Ollama. Auto-resolved to installed '{matched}'.", flush=True)
                        model = matched
                    else:
                        print(f"[AI ENGINE] Notice: Model '{model}' not found in Ollama. Falling back to '{installed[0]}'.", flush=True)
                        model = installed[0]
        except Exception as tag_err:
            logger.debug(f"Could not query Ollama tags: {tag_err}")

        print(f"\n[AI ENGINE] ==> Active Provider: LOCAL OLLAMA | Model: '{model}' | URL: {base_url}\n", flush=True)
        logger.info(f"Using Local Ollama LLM: model={model}, base_url={base_url}")

        # 1. Try langchain_ollama
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(model=model, base_url=base_url, temperature=temperature)
        except ImportError:
            pass

        # 2. Try langchain_community ChatOllama
        try:
            from langchain_community.chat_models import ChatOllama
            return ChatOllama(model=model, base_url=base_url, temperature=temperature)
        except ImportError:
            pass

        # 3. Try langchain_openai pointing to Ollama's native /v1 endpoint
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                base_url=f"{base_url}/v1",
                api_key="ollama",
                model=model,
                temperature=temperature
            )
        except Exception as e:
            logger.warning(f"Failed to initialize ChatOpenAI against Ollama: {e}")

        # 4. Fallback lightweight wrapper using requests
        from .ollama_fallback import OllamaChatFallback
        return OllamaChatFallback(model=model, base_url=base_url, temperature=temperature)

    else:
        # Default: Google Gemini Cloud
        model = getattr(ws, "ai_model", None)
        if not model or "gemini" not in model:
            model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        api_key = os.getenv("GEMINI_API_KEY")
        print(f"\n[AI ENGINE] ==> Active Provider: GOOGLE GEMINI (Cloud) | Model: '{model}'\n", flush=True)
        logger.info(f"Using Google Gemini LLM: model={model}")

        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature
        )
