"""
Shared helpers for running a specialist sub-agent and extracting its final answer.
"""

from langchain_core.messages import AIMessage, HumanMessage

from text_utils import message_text


def run_agent_sync(agent, query: str) -> str:
    """Invoke a compiled create_agent graph with a single user query and
    return the text of its last AI message."""
    result = agent.invoke({"messages": [HumanMessage(content=query)]})
    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage):
            text = message_text(msg.content)
            if text.strip():
                return text
    return "No response generated."
