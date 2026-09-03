"""
Shared helpers for running a specialist sub-agent and extracting its final answer.
"""

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from text_utils import message_text


def run_agent_sync(agent, query: str, config: RunnableConfig | None = None) -> str:
    """Invoke a compiled create_agent graph with a single user query and
    return the text of its last AI message.

    Pass through the caller's RunnableConfig (if any) so callbacks —
    e.g. the coordinator's tool-call tracker — see this sub-agent's own
    tool calls too, not just the outer specialist call."""
    result = agent.invoke({"messages": [HumanMessage(content=query)]}, config=config)
    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage):
            text = message_text(msg.content)
            if text.strip():
                return text
    return "No response generated."
