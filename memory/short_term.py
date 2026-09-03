"""
Short-term memory — conversation buffer with sliding window and summarization.
"""

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from text_utils import message_text


SUMMARY_PROMPT = """Summarize the following conversation concisely, preserving key facts,
decisions, vehicle IDs, ECU references, and any action items:

{conversation}

Summary:"""


class ShortTermMemory:
    def __init__(self, window_size: int = 10, summary_threshold_tokens: int = 3000):
        self.window_size = window_size
        self.summary_threshold_tokens = summary_threshold_tokens
        self.sessions: dict[str, list[BaseMessage]] = {}
        self.summaries: dict[str, str] = {}

    def get_messages(self, conversation_id: str) -> list[BaseMessage]:
        messages = self.sessions.get(conversation_id, [])
        result = []
        summary = self.summaries.get(conversation_id)
        if summary:
            result.append(SystemMessage(content=f"Previous conversation summary: {summary}"))
        result.extend(messages[-self.window_size :])
        return result

    def add_message(self, conversation_id: str, message: BaseMessage):
        if conversation_id not in self.sessions:
            self.sessions[conversation_id] = []
        self.sessions[conversation_id].append(message)

    def should_summarize(self, conversation_id: str) -> bool:
        messages = self.sessions.get(conversation_id, [])
        if len(messages) <= self.window_size:
            return False
        total_chars = sum(len(message_text(m.content)) for m in messages)
        estimated_tokens = total_chars // 4
        return estimated_tokens > self.summary_threshold_tokens

    async def maybe_summarize(self, conversation_id: str, llm: BaseChatModel):
        if not self.should_summarize(conversation_id):
            return

        messages = self.sessions[conversation_id]
        older = messages[: -self.window_size]

        conversation_text = "\n".join(
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {message_text(m.content)}"
            for m in older
        )

        existing_summary = self.summaries.get(conversation_id, "")
        if existing_summary:
            conversation_text = f"Previous summary: {existing_summary}\n\n{conversation_text}"

        response = await llm.ainvoke(
            [HumanMessage(content=SUMMARY_PROMPT.format(conversation=conversation_text))]
        )
        self.summaries[conversation_id] = message_text(response.content)
        self.sessions[conversation_id] = messages[-self.window_size :]

    def clear(self, conversation_id: str):
        self.sessions.pop(conversation_id, None)
        self.summaries.pop(conversation_id, None)
