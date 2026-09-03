"""
Human-in-the-loop approval system for write actions.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Callable

from langchain_core.tools import StructuredTool


class PendingActionsStore:
    def __init__(self, db_path: str = "data/memory.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)

    def create(self, tool_name: str, args: dict) -> str:
        action_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            """INSERT INTO pending_actions
               (action_id, tool_name, args_json, status, created_at)
               VALUES (?, ?, ?, 'pending', ?)""",
            (action_id, tool_name, json.dumps(args), now),
        )
        self.conn.commit()
        return action_id

    def list_pending(self) -> list[dict]:
        cur = self.conn.execute(
            "SELECT action_id, tool_name, args_json, status, created_at FROM pending_actions WHERE status = 'pending'"
        )
        return [
            {
                "action_id": row[0],
                "tool_name": row[1],
                "args": json.loads(row[2]),
                "status": row[3],
                "created_at": row[4],
            }
            for row in cur.fetchall()
        ]

    def approve(self, action_id: str) -> dict | None:
        cur = self.conn.execute(
            "SELECT tool_name, args_json FROM pending_actions WHERE action_id = ? AND status = 'pending'",
            (action_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "UPDATE pending_actions SET status = 'approved', resolved_at = ? WHERE action_id = ?",
            (now, action_id),
        )
        self.conn.commit()
        return {"tool_name": row[0], "args": json.loads(row[1])}

    def reject(self, action_id: str, reason: str = "") -> bool:
        now = datetime.utcnow().isoformat()
        result_json = json.dumps({"reason": reason}) if reason else None
        cur = self.conn.execute(
            "UPDATE pending_actions SET status = 'rejected', resolved_at = ?, result_json = ? WHERE action_id = ? AND status = 'pending'",
            (now, result_json, action_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def set_result(self, action_id: str, result: Any):
        self.conn.execute(
            "UPDATE pending_actions SET result_json = ? WHERE action_id = ?",
            (json.dumps(result, default=str), action_id),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


class HumanApprovalTool:
    def __init__(self, wrapped_tool: StructuredTool, store: PendingActionsStore):
        self.wrapped_tool = wrapped_tool
        self.store = store

    def as_tool(self) -> StructuredTool:
        original = self.wrapped_tool

        def approval_fn(**kwargs) -> str:
            action_id = self.store.create(original.name, kwargs)
            args_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
            return (
                f"Action requires human approval.\n"
                f"Action ID: {action_id}\n"
                f"Tool: {original.name}({args_str})\n"
                f"Status: PENDING — awaiting approval via /api/actions/{action_id}/approve"
            )

        return StructuredTool(
            name=original.name,
            description=f"[REQUIRES APPROVAL] {original.description}",
            func=approval_fn,
            args_schema=original.args_schema,
        )


def wrap_write_tools(
    tools: list[StructuredTool],
    write_tool_names: list[str],
    store: PendingActionsStore,
) -> list[StructuredTool]:
    result = []
    for tool in tools:
        if tool.name in write_tool_names:
            result.append(HumanApprovalTool(tool, store).as_tool())
        else:
            result.append(tool)
    return result
