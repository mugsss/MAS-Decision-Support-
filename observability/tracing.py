"""
Observability — LangSmith tracing + OpenTelemetry console fallback.
"""

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def setup_tracing():
    tracing_enabled = (
        os.getenv("LANGSMITH_TRACING", os.getenv("LANGCHAIN_TRACING_V2", "false")).lower() == "true"
    )

    if tracing_enabled:
        project = os.getenv("LANGSMITH_PROJECT", os.getenv("LANGCHAIN_PROJECT", "automotive-mas"))
        os.environ.setdefault("LANGCHAIN_PROJECT", project)
        print("[observability] LangSmith tracing enabled")
        print(f"[observability] Project: {project}")
        return {"backend": "langsmith"}

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            ConsoleSpanExporter,
            SimpleSpanProcessor,
        )

        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        print("[observability] OpenTelemetry console exporter enabled (LangSmith not configured)")
        return {"backend": "otel-console"}

    except ImportError:
        print("[observability] No tracing backend available (set LANGCHAIN_TRACING_V2=true for LangSmith)")
        return {"backend": "none"}


def get_run_metadata(
    agent_name: str | None = None,
    query_type: str | None = None,
    conversation_id: str | None = None,
    skill_name: str | None = None,
) -> dict:
    metadata = {}
    if agent_name:
        metadata["agent_name"] = agent_name
    if query_type:
        metadata["query_type"] = query_type
    if conversation_id:
        metadata["conversation_id"] = conversation_id
    if skill_name:
        metadata["skill_name"] = skill_name
    return metadata
