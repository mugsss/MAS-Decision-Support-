"""
LLM provider — builds the Google Gemini chat model and embedding model.
"""

import os

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings


def load_llm_config(agents_yaml: str = "agents.yaml") -> dict:
    from config_loader import load_yaml_config
    return load_yaml_config(agents_yaml).get("llm", {})


def _get_api_key() -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Add it to your .env file "
            "(get a key at https://aistudio.google.com/apikey)"
        )
    return api_key


def build_chat_model(config: dict) -> BaseChatModel:
    return ChatGoogleGenerativeAI(
        model=config.get("model"),
        temperature=config.get("temperature", 0.1),
        google_api_key=_get_api_key(),
        max_retries=config.get("max_retries", 3),
    )


def build_embeddings(config: dict) -> Embeddings:
    return GoogleGenerativeAIEmbeddings(
        model=config.get("embedding_model", "models/gemini-embedding-001"),
        google_api_key=_get_api_key(),
    )
