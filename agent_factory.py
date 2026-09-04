"""
AgentFactory — YAML-driven instantiation of agents, tools, skills, and the Coordinator.
"""

from pathlib import Path

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from config_loader import load_yaml_config, env_or_default
from llm_provider import build_chat_model, build_embeddings
from pdm_mcp.client import MCPClient
from rag.retriever import RAGRetriever
from agents.pdm_agent import build_pdm_tool
from agents.logs_agent import build_logs_tool
from agents.text2sql_agent import build_text2sql_tool
from agents.code_assist_agent import build_code_assist_tool
from agents.write_tools import build_write_tools
from coordinator import build_coordinator


class AgentFactory:
    def __init__(
        self,
        agents_yaml: str = "agents.yaml",
        env_file: str = ".env",
    ):
        if Path(env_file).exists():
            load_dotenv(env_file)

        self.config = load_yaml_config(agents_yaml)
        self.llm: BaseChatModel | None = None
        self.embeddings: Embeddings | None = None
        self.mcp_client: MCPClient | None = None
        self.all_tools: list[BaseTool] = []
        self.tool_map: dict[str, BaseTool] = {}

    async def build(self):
        self._build_llm()
        await self._build_agents()
        return build_coordinator(
            llm=self.llm,
            tools=self.all_tools,
            config=self.config,
        )

    def _register_tool(self, tool: BaseTool):
        self.all_tools.append(tool)
        self.tool_map[tool.name] = tool

    def _build_llm(self):
        llm_config = self.config["llm"]
        self.llm = build_chat_model(llm_config)
        self.embeddings = build_embeddings(llm_config)

    async def _build_agents(self):
        agents_config = self.config.get("agents", {})

        # PDM Agent (MCP)
        pdm_config = agents_config.get("pdm", {})
        if pdm_config.get("type") == "mcp":
            server_path = pdm_config.get("mcp_server", "pdm_mcp/server.py")
            self.mcp_client = MCPClient(server_path)
            await self.mcp_client.start()
            mcp_tools = self.mcp_client.get_langchain_tools()
            self._register_tool(build_pdm_tool(self.llm, mcp_tools, name=pdm_config.get("name", "niki")))

        # Logs Agent
        self._register_tool(build_logs_tool(self.llm))

        # Text2SQL Agent
        sql_config = agents_config.get("text2sql", {})
        db_path = sql_config.get("db_path", env_or_default("FLEET_DB_PATH"))
        self._register_tool(build_text2sql_tool(self.llm, db_path))

        # Code Assist Agent (RAG)
        ca_config = agents_config.get("code_assist", {})
        retriever_config = ca_config.get("retriever", {})
        retriever = RAGRetriever(
            persist_dir=env_or_default("CHROMA_PERSIST_DIR"),
            collection_name=retriever_config.get("collection", "automotive_docs"),
            embeddings=self.embeddings,
            top_k=retriever_config.get("top_k", 3),
            relevance_threshold=retriever_config.get("relevance_threshold", 0.3),
        )
        self._register_tool(build_code_assist_tool(self.llm, retriever))

        # Standalone write tools (HITL gated by middleware in coordinator)
        for t in build_write_tools():
            self._register_tool(t)

    async def shutdown(self):
        if self.mcp_client:
            await self.mcp_client.stop()
