"""
MCP client — uses langchain-mcp-adapters to connect to the local MCP server
and return LangChain tools.
"""

import sys
from pathlib import Path

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient


class MCPClient:
    def __init__(self, server_script: str):
        self.server_script = str(Path(server_script).resolve())
        self._client: MultiServerMCPClient | None = None
        self._tools: list[BaseTool] = []

    async def start(self):
        self._client = MultiServerMCPClient({
            "pdm": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [self.server_script],
            }
        })
        self._tools = await self._client.get_tools()

    async def stop(self):
        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass

    def get_langchain_tools(self) -> list[BaseTool]:
        return self._tools
