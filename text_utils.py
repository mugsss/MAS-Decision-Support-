"""
Message content helpers.

langchain-core 1.x returns `AIMessage.content` as either a plain string or a
list of content blocks (e.g. [{"type": "text", "text": "..."}]). Everything that
treats model output as text must go through `message_text` first.
"""


def message_text(content) -> str:
    """Flatten LangChain message content into plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                # Skip non-text blocks (tool calls, thinking, images).
                if block.get("type") in (None, "text") and "text" in block:
                    parts.append(block["text"])
        return "".join(parts)
    return str(content)
