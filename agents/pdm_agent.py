"""
PDM Agent (Niki) — vehicle configs, ECU assignments, part numbers, SW versions.
Tools are discovered dynamically from the MCP server and injected by AgentFactory.
"""

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool

from agents.agent_utils import run_agent_async

PDM_SYSTEM_PROMPT = """You are a PDM (Product Data Management) specialist for vehicle
configurations, ECU assignments, part numbers, and software versions.

Use the available tools to answer the question: get_vehicle_config, get_ecu_assignments,
search_parts, get_software_versions, and update_sw_version (a write action that requires
human approval — acknowledge the pending status if the tool reports one).

Call more than one tool if the question needs it. Answer concisely based on the tool output."""


def build_pdm_tool(llm: BaseChatModel, mcp_tools: list, name: str = "niki") -> BaseTool:
    """Build the PDM specialist agent and return the single tool the coordinator calls."""
    agent = create_agent(model=llm, tools=mcp_tools, system_prompt=PDM_SYSTEM_PROMPT)

    async def _niki(query: str, config: RunnableConfig) -> str:
        """PDM specialist — retrieves vehicle configurations, ECU assignments,
        part numbers, and software versions from the Product Data Management system.
        Pass a natural-language query describing what vehicle/ECU data you need.
        Available operations: get_vehicle_config, get_ecu_assignments, search_parts,
        get_software_versions, update_sw_version (requires approval)."""
        return await run_agent_async(agent, query, config=config)

    return tool(name)(_niki)
