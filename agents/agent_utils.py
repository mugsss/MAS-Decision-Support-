"""
Shared helpers for running a specialist sub-agent and extracting its final answer.
"""

import asyncio

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig


def _extract_response(result: dict) -> str:
    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage):
            if msg.text.strip():
                return msg.text
    return "No response generated."


def run_agent_sync(agent, query: str, config: RunnableConfig | None = None) -> str:
    result = agent.invoke({"messages": [HumanMessage(content=query)]}, config=config)
    return _extract_response(result)


async def run_agent_async(agent, query: str, config: RunnableConfig | None = None) -> str:
    result = await agent.ainvoke({"messages": [HumanMessage(content=query)]}, config=config)
    return _extract_response(result)
