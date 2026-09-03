"""
AgentFactory — YAML-driven instantiation of agents, tools, skills, and the Coordinator.
"""

from pathlib import Path

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from config_loader import load_yaml_config, env_or_default
from llm_provider import build_chat_model, build_embeddings
from mcp.client import MCPClient
from rag.retriever import RAGRetriever
from agents.pdm_agent import build_pdm_tool
from agents.logs_agent import build_logs_tool
from agents.text2sql_agent import build_text2sql_tool
from agents.code_assist_agent import build_code_assist_tool
from agents.write_tools import build_write_tools
from hitl.approval import PendingActionsStore, wrap_write_tools
from skills.loader import SkillsLoader
from observability.tracing import setup_tracing
from coordinator import build_coordinator


class AgentFactory:
    def __init__(
        self,
        agents_yaml: str = "agents.yaml",
        skills_yaml: str = "skills.yaml",
        env_file: str = ".env",
    ):
        if Path(env_file).exists():
            load_dotenv(env_file)

        self.config = load_yaml_config(agents_yaml)

        self.skills_yaml = skills_yaml
        self.llm: BaseChatModel | None = None
        self.embeddings: Embeddings | None = None
        self.mcp_client: MCPClient | None = None
        self.approval_store: PendingActionsStore | None = None
        self.all_tools = []
        self.tool_map: dict = {}
        self.raw_write_tools: dict = {}

    def build(self):
        setup_tracing()
        self._build_llm()
        self._build_approval_store()
        self._build_agents()
        self._build_skills()
        coordinator = self._build_coordinator()
        return coordinator

    def _build_llm(self):
        llm_config = self.config["llm"]
        self.llm = build_chat_model(llm_config)
        self.embeddings = build_embeddings(llm_config)

    def _build_approval_store(self):
        hitl_config = self.config.get("hitl", {})
        db_path = hitl_config.get("db_path", env_or_default("MEMORY_DB_PATH"))
        self.approval_store = PendingActionsStore(db_path)

    def _build_agents(self):
        agents_config = self.config.get("agents", {})
        write_tool_names = self.config.get("hitl", {}).get("write_tools", [])

        # PDM Agent (MCP)
        pdm_config = agents_config.get("pdm", {})
        if pdm_config.get("type") == "mcp":
            server_path = pdm_config.get("mcp_server", "mcp/server.py")
            self.mcp_client = MCPClient(server_path)
            self.mcp_client.start()
            mcp_write = pdm_config.get("write_tools", [])
            self.mcp_client.set_write_tools(mcp_write)

            mcp_tools = self.mcp_client.get_langchain_tools()
            # Keep unwrapped references so approved actions can actually execute.
            for t in mcp_tools:
                if t.name in write_tool_names:
                    self.raw_write_tools[t.name] = t

            mcp_tools = wrap_write_tools(mcp_tools, write_tool_names, self.approval_store)

            pdm_name = pdm_config.get("name", "niki")
            pdm_tool = build_pdm_tool(self.llm, mcp_tools, name=pdm_name)
            self.all_tools.append(pdm_tool)
            self.tool_map[pdm_name] = pdm_tool

        # Logs Agent
        logs_tool = build_logs_tool(self.llm)
        self.all_tools.append(logs_tool)
        self.tool_map[logs_tool.name] = logs_tool

        # Text2SQL Agent
        sql_config = agents_config.get("text2sql", {})
        db_path = sql_config.get("db_path", env_or_default("FLEET_DB_PATH"))
        text2sql_tool = build_text2sql_tool(self.llm, db_path)
        self.all_tools.append(text2sql_tool)
        self.tool_map[text2sql_tool.name] = text2sql_tool

        # Code Assist Agent
        ca_config = agents_config.get("code_assist", {})
        retriever_config = ca_config.get("retriever", {})
        retriever = RAGRetriever(
            persist_dir=env_or_default("CHROMA_PERSIST_DIR"),
            collection_name=retriever_config.get("collection", "automotive_docs"),
            embeddings=self.embeddings,
            top_k=retriever_config.get("top_k", 3),
            relevance_threshold=retriever_config.get("relevance_threshold", 0.3),
        )
        code_assist_tool = build_code_assist_tool(self.llm, retriever)
        self.all_tools.append(code_assist_tool)
        self.tool_map[code_assist_tool.name] = code_assist_tool

        # Write tools (standalone, HITL-gated)
        self._build_write_tools(write_tool_names)

    def _build_write_tools(self, write_tool_names: list[str]):
        write_tools = build_write_tools()
        for t in write_tools:
            self.raw_write_tools[t.name] = t

        wrapped = wrap_write_tools(write_tools, write_tool_names, self.approval_store)
        for t in wrapped:
            self.all_tools.append(t)
            self.tool_map[t.name] = t

    def _build_skills(self):
        loader = SkillsLoader(self.skills_yaml)
        loader.load()
        skill_tools = loader.build_skill_tools(self.llm, self.tool_map)
        for st in skill_tools:
            self.all_tools.append(st)
            self.tool_map[st.name] = st

    def _build_coordinator(self):
        coord_config = self.config.get("coordinator", {})
        memory_config = self.config.get("memory", {})
        return build_coordinator(
            llm=self.llm,
            tools=self.all_tools,
            system_prompt=coord_config.get("system_prompt", ""),
            memory_config=memory_config,
            embeddings=self.embeddings,
        )

    def get_approval_store(self) -> PendingActionsStore:
        return self.approval_store

    def get_executable_tool(self, tool_name: str):
        """Return the unwrapped tool for executing an approved action."""
        return self.raw_write_tools.get(tool_name)

    def shutdown(self):
        if self.mcp_client:
            self.mcp_client.stop()
        if self.approval_store:
            self.approval_store.close()
