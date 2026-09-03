"""
ToolCallTracker — a LangChain callback handler that records which tools ran
during one agent invocation, with their arguments and wall-clock duration.
Used to surface "agents/tools called" transparency in the API response.
"""

import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler


class ToolCallTracker(AsyncCallbackHandler):
    def __init__(self):
        self.calls: list[dict] = []
        self._starts: dict[UUID, dict] = {}

    async def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._starts[run_id] = {
            "tool": serialized.get("name", "unknown"),
            "args": inputs if inputs is not None else input_str,
            "started_at": time.perf_counter(),
        }

    async def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        start = self._starts.pop(run_id, None)
        if start is None:
            return
        self.calls.append({
            "tool": start["tool"],
            "args": start["args"],
            "duration_seconds": round(time.perf_counter() - start["started_at"], 3),
            "error": None,
        })

    async def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        start = self._starts.pop(run_id, None)
        if start is None:
            return
        self.calls.append({
            "tool": start["tool"],
            "args": start["args"],
            "duration_seconds": round(time.perf_counter() - start["started_at"], 3),
            "error": str(error),
        })
