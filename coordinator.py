"""
Coordinator Agent — LangChain ReAct agent that orchestrates specialist tools.
"""

import json
import uuid
from typing import AsyncGenerator

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    SummarizationMiddleware,
    ToolErrorMiddleware,
    ModelRetryMiddleware,
    ToolCallLimitMiddleware,
)
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from memory.long_term import LongTermMemory


class Coordinator:
    def __init__(
        self,
        agent,
        llm: BaseChatModel,
        long_term: LongTermMemory,
    ):
        self.agent = agent
        self.llm = llm
        self.long_term = long_term
        self.pending_interrupts: dict[str, dict] = {}

    async def chat_stream(self, message: str, conversation_id: str | None = None) -> AsyncGenerator[str, None]:
        """Stream SSE events as the agent works."""
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        messages = []
        past = self.long_term.get_recent_conversations()
        if past:
            context = "Recent conversation history:\n" + "\n".join(
                f"- {m['role']}: {m['content']}" for m in past
            )
            messages.append(SystemMessage(content=context))
        messages.append(HumanMessage(content=message))

        config = {
            "configurable": {"thread_id": conversation_id},
        }

        yield self._sse({"type": "start", "conversation_id": conversation_id})

        full_response = ""

        async for msg, metadata in self.agent.astream(
            {"messages": messages}, config=config, stream_mode="messages"
        ):
            if not isinstance(msg, AIMessage):
                continue
            content = msg.content
            if isinstance(content, list):
                text = "".join(block.get("text", "") for block in content if isinstance(block, dict))
            else:
                text = content or ""
            if text:
                full_response += text
                yield self._sse({"type": "token", "content": text})

        self.long_term.save_conversation(
            conversation_id,
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": full_response},
            ],
        )

        yield self._sse({
            "type": "done",
            "conversation_id": conversation_id,
        })

    @staticmethod
    def _sse(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    async def handle_approval(self, action_id: str, decision_type: str, message: str | None = None, edited_args: dict | None = None) -> dict:
        """Resume the agent after a human decision (approve/reject/edit)."""
        pending = self.pending_interrupts.pop(action_id, None)
        if not pending:
            return {"error": "Action not found or already resolved"}

        conversation_id = pending["conversation_id"]
        config = {
            "configurable": {"thread_id": conversation_id},
        }

        if decision_type == "approve":
            decision = {"type": "approve"}
        elif decision_type == "reject":
            decision = {"type": "reject", "message": message or "Rejected by user."}
        elif decision_type == "edit":
            decision = {
                "type": "edit",
                "edited_action": {
                    "name": pending["tool_name"],
                    "args": edited_args or pending["args"],
                },
            }
        else:
            return {"error": f"Unknown decision type: {decision_type}"}

        result = await self.agent.ainvoke(
            Command(resume={"decisions": [decision]}),
            config=config,
        )

        response_messages = result.get("messages", [])
        final_response = ""
        for msg in reversed(response_messages):
            if isinstance(msg, AIMessage):
                text = msg.text
                if text.strip():
                    final_response = text
                    break

        return {
            "status": decision_type,
            "action_id": action_id,
            "response": final_response,
        }

    def list_pending(self) -> list[dict]:
        return [
            {
                "action_id": aid,
                "tool_name": info["tool_name"],
                "args": info["args"],
                "status": "pending",
                "created_at": info["created_at"],
            }
            for aid, info in self.pending_interrupts.items()
        ]


async def _tool_error_handler(err, req):
    return f"Tool '{req.tool_call.get('name', 'unknown')}' failed: {err}"


def build_coordinator(
    llm: BaseChatModel,
    tools: list[StructuredTool],
    config: dict,
) -> Coordinator:
    coord_config = config.get("coordinator", {})
    memory_config = config.get("memory", {})
    write_tool_names = config.get("hitl", {}).get("write_tools", [])
    system_prompt = coord_config.get("system_prompt", "")

    # HITL middleware — interrupts write tools for human approval
    interrupt_on = {}
    for name in write_tool_names:
        interrupt_on[name] = {"allowed_decisions": ["approve", "reject", "edit"]}

    stm_config = memory_config.get("short_term", {})
    window_size = stm_config.get("window_size", 10)
    max_iterations = coord_config.get("max_iterations", 10)

    middleware = [
        ModelRetryMiddleware(max_retries=3),
        ToolErrorMiddleware(
            aon_error=_tool_error_handler,
        ),
        ToolCallLimitMiddleware(run_limit=max_iterations * 2),
        SummarizationMiddleware(
            model=llm,
            trigger=("messages", window_size * 3),
            keep=("messages", window_size),
        ),
    ]
    #These are the tools that should stop and ask for human approval
    if interrupt_on:
        middleware.append(
            HumanInTheLoopMiddleware(interrupt_on=interrupt_on)
        )

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middleware,
        checkpointer=InMemorySaver(), # gives the agent a temporary place to save its current state so it can pause and continue later.
    )

    ltm_config = memory_config.get("long_term", {})
    long_term = LongTermMemory(
        db_path=ltm_config.get("db_path", "data/memory.db"),
    )

    return Coordinator(
        agent=agent,
        llm=llm,
        long_term=long_term,
    )
