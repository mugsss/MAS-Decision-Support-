"""
LLM provider factory — builds chat models and embeddings from configuration.

Keeps the rest of the system model-agnostic: every module depends on the
LangChain BaseChatModel / Embeddings interfaces, never on a concrete provider.
Swap providers by editing the `llm:` block in agents.yaml.
"""

import os

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from config_loader import load_yaml_config

GOOGLE_PROVIDERS = {"google_genai", "google", "gemini"}
DEFAULT_GOOGLE_EMBEDDING = "models/gemini-embedding-001"


def load_llm_config(agents_yaml: str = "agents.yaml") -> dict:
    """Read the `llm:` block from agents.yaml with ${ENV_VAR} substitution."""
    return load_yaml_config(agents_yaml).get("llm", {})


def _build_rate_limiter(config: dict):
    """Throttle client-side to stay under free-tier RPM.

    One chat turn costs several calls (ReAct loop + Text2SQL/RAG sub-chains +
    summarization), so without this a single question can trip a 429.
    """
    rpm = config.get("requests_per_minute")
    if not rpm:
        return None
    from langchain_core.rate_limiters import InMemoryRateLimiter

    return InMemoryRateLimiter(
        requests_per_second=rpm / 60.0,
        check_every_n_seconds=0.1,
        max_bucket_size=max(1, int(rpm / 6)),
    )


def _require_google_key() -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your "
            "key from https://aistudio.google.com/apikey"
        )
    return api_key


def build_chat_model(config: dict) -> BaseChatModel:
    provider = config.get("provider", "google_genai").lower()
    model = config.get("model")
    temperature = config.get("temperature", 0.1)

    if provider in GOOGLE_PROVIDERS:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=_require_google_key(),
            max_retries=config.get("max_retries", 3),
            rate_limiter=_build_rate_limiter(config),
        )

    raise ValueError(
        f"Unsupported LLM provider: {provider!r}. Supported: google_genai."
    )


def build_embeddings(config: dict) -> Embeddings:
    provider = config.get("provider", "google_genai").lower()
    model = config.get("embedding_model")

    if provider in GOOGLE_PROVIDERS:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=model or DEFAULT_GOOGLE_EMBEDDING,
            google_api_key=_require_google_key(),
        )

    raise ValueError(
        f"Unsupported embedding provider: {provider!r}. Supported: google_genai."
    )
