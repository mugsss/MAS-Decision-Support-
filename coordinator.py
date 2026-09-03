"""
Coordinator Agent — LangChain ReAct agent that orchestrates specialist tools.
"""

import uuid
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langchain.agents import create_agent

from config_loader import env_or_default
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from guardrails.input_guard import InputGuard
from guardrails.output_guard import OutputGuard
from observability.tracing import get_run_metadata
from text_utils import message_text


class Coordinator:
    def __init__(
        self,
        agent,
        llm: BaseChatModel,
        short_term: ShortTermMemory,
        long_term: LongTermMemory,
        input_guard: InputGuard,
        output_guard: OutputGuard,
    ):
        self.agent = agent
        self.llm = llm
        self.short_term = short_term
        self.long_term = long_term
        self.input_guard = input_guard
        self.output_guard = output_guard

    async def chat(self, message: str, conversation_id: str | None = None) -> dict[str, Any]:
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        is_safe, reason = self.input_guard.check(message)
        if not is_safe:
            return {
                "response": f"I can't process this request: {reason}",
                "conversation_id": conversation_id,
                "agents_used": [],
                "skills_used": [],
                "blocked": True,
                "block_reason": reason,
            }

        long_term_context = ""
        history = self.short_term.get_messages(conversation_id)
        if not history or len(history) <= 1:
            memories = self.long_term.retrieve_relevant(message)
            if memories:
                long_term_context = (
                    "Relevant context from past conversations:\n"
                    + "\n".join(f"- {m}" for m in memories)
                )

        self.short_term.add_message(conversation_id, HumanMessage(content=message))

        messages = []
        if long_term_context:
            messages.append(SystemMessage(content=long_term_context))
        messages.extend(self.short_term.get_messages(conversation_id))

        metadata = get_run_metadata(
            agent_name="coordinator",
            conversation_id=conversation_id,
        )

        result = await self.agent.ainvoke(
            {"messages": messages},
            config={"metadata": metadata},
        )

        response_messages = result.get("messages", [])
        final_response = ""
        agents_used = []

        for msg in response_messages:
            if isinstance(msg, AIMessage):
                text = message_text(msg.content)
                if text.strip():
                    final_response = text
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        agents_used.append(tc["name"])

        final_response = self.output_guard.sanitize(final_response)

        self.short_term.add_message(conversation_id, AIMessage(content=final_response))
        await self.short_term.maybe_summarize(conversation_id, self.llm)

        self.long_term.save_conversation(
            conversation_id,
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": final_response},
            ],
        )

        return {
            "response": final_response,
            "conversation_id": conversation_id,
            "agents_used": list(set(agents_used)),
            "skills_used": [a for a in agents_used if a in _SKILL_NAMES],
        }


_SKILL_NAMES = set()


def build_coordinator(
    llm: BaseChatModel,
    tools: list[StructuredTool],
    system_prompt: str,
    memory_config: dict,
    embeddings: Embeddings | None = None,
) -> Coordinator:
    from skills.loader import SkillsLoader
    global _SKILL_NAMES
    try:
        loader = SkillsLoader()
        config = loader.load()
        _SKILL_NAMES = set(config.keys())
    except Exception:
        pass

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    stm_config = memory_config.get("short_term", {})
    short_term = ShortTermMemory(
        window_size=stm_config.get("window_size", 10),
        summary_threshold_tokens=stm_config.get("summary_threshold_tokens", 3000),
    )

    ltm_config = memory_config.get("long_term", {})
    long_term = LongTermMemory(
        db_path=ltm_config.get("db_path", "data/memory.db"),
        chroma_dir=env_or_default("CHROMA_PERSIST_DIR"),
        collection_name=ltm_config.get("vectorstore", {}).get("collection", "conversation_memory"),
        embeddings=embeddings,
        top_k=ltm_config.get("vectorstore", {}).get("top_k", 3),
    )

    input_guard = InputGuard()
    output_guard = OutputGuard()

    return Coordinator(
        agent=agent,
        llm=llm,
        short_term=short_term,
        long_term=long_term,
        input_guard=input_guard,
        output_guard=output_guard,
    )
