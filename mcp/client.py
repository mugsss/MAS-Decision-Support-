"""
MCP client — spawns the local MCP server subprocess, discovers tools,
and wraps each as a LangChain StructuredTool.
"""

import json
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import create_model


class MCPClient:
    def __init__(self, server_script: str):
        self.server_script = str(Path(server_script).resolve())
        self.process: subprocess.Popen | None = None
        self._write_tools: set[str] = set()

    def start(self):
        self.process = subprocess.Popen(
            [sys.executable, self.server_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None

    def _send(self, request: dict) -> dict | None:
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise RuntimeError("MCP server not started")
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        if "id" not in request:
            return None
        line = self.process.stdout.readline()
        return json.loads(line)

    def list_tools(self) -> list[dict]:
        resp = self._send({
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
        })
        return resp["result"]["tools"]

    def call_tool(self, name: str, arguments: dict) -> str:
        resp = self._send({
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        if "error" in resp:
            return json.dumps(resp["error"])
        content = resp["result"]["content"]
        return content[0]["text"] if content else "{}"

    def set_write_tools(self, names: list[str]):
        self._write_tools = set(names)

    def is_write_tool(self, name: str) -> bool:
        return name in self._write_tools

    def get_langchain_tools(self) -> list[StructuredTool]:
        raw_tools = self.list_tools()
        lc_tools = []
        for tool_def in raw_tools:
            name = tool_def["name"]
            description = tool_def["description"]
            schema = tool_def.get("inputSchema", {})
            props = schema.get("properties", {})
            required = set(schema.get("required", []))

            fields: dict[str, Any] = {}
            for prop_name, prop_info in props.items():
                py_type = str
                default = ... if prop_name in required else None
                fields[prop_name] = (py_type, default)

            args_model = create_model(f"{name}_args", **fields) if fields else None

            def _make_fn(tool_name: str):
                def fn(**kwargs) -> str:
                    return self.call_tool(tool_name, kwargs)
                fn.__name__ = tool_name
                return fn

            tool = StructuredTool(
                name=name,
                description=description,
                func=_make_fn(name),
                args_schema=args_model,
            )
            lc_tools.append(tool)
        return lc_tools
