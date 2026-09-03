"""
Code Assist Agent — answers AUTOSAR, ASPICE, ASIL questions via RAG.
A real create_agent loop over a `retrieve_docs` tool: the LLM can re-query
with different phrasing if the first retrieval looks insufficient. READ-ONLY.
"""

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from agents.agent_utils import run_agent_sync
from rag.retriever import RAGRetriever

CODE_ASSIST_SYSTEM_PROMPT = """You are an automotive software standards expert covering
AUTOSAR architecture, ASPICE process areas, ASIL/ISO 26262 functional safety, ECU flashing
procedures, CAN bus diagnostics, OTA updates, and related development standards.

Use the retrieve_docs tool to find relevant documentation before answering. If the first
retrieval doesn't clearly cover the question, try again with different search terms
(at most once more) before answering.

Answer using ONLY the retrieved context — never from general knowledge. If the context
doesn't contain enough information, say so clearly. Cite which document the information
comes from when possible."""

def build_code_assist_tool(llm: BaseChatModel, retriever: RAGRetriever):
    """Build the code-assist specialist agent and return the single tool the coordinator calls."""

    @tool
    def retrieve_docs(query: str) -> str:
        """Retrieve relevant automotive standards documentation chunks for a query.
        Returns the matched chunks with their source document name and relevance score."""
        docs, low_relevance = retriever.retrieve(query)
        if not docs:
            return "No relevant documents found."

        context_parts = []
        for doc in docs:
            source = doc.metadata.get("doc_name", "unknown")
            score = doc.metadata.get("relevance_score", 0)
            context_parts.append(f"[Source: {source}, relevance: {score:.2f}]\n{doc.page_content}")

        context = "\n\n---\n\n".join(context_parts)
        if low_relevance:
            context += (
                "\n\n[All results are below the relevance threshold — tell the user your "
                "answer may not fully address their question, or try a different query.]"
            )
        return context

    agent = create_agent(model=llm, tools=[retrieve_docs], system_prompt=CODE_ASSIST_SYSTEM_PROMPT)

    @tool
    def code_assist_agent(query: str, config: RunnableConfig) -> str:
        """Standards and compliance specialist — answers questions about AUTOSAR architecture,
        ASPICE process areas, ASIL/ISO 26262 functional safety, ECU flashing procedures,
        CAN bus diagnostics, OTA updates, and automotive software development standards.
        Pass a clear question about automotive standards or processes."""
        return run_agent_sync(agent, query, config=config)

    return code_assist_agent
