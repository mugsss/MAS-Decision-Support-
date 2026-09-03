"""
Standalone write tools — not tied to any specialist, HITL-gated by AgentFactory
via hitl.approval.wrap_write_tools before being handed to the coordinator.
"""

import sqlite3
import uuid
from datetime import datetime

from langchain_core.tools import StructuredTool

from config_loader import env_or_default


def _create_defect(vehicle_id: str, description: str, severity: str) -> str:
    """Create a new defect record in the fleet database."""
    db_path = env_or_default("FLEET_DB_PATH")
    conn = sqlite3.connect(db_path)
    defect_id = f"DEF-{uuid.uuid4().hex[:5].upper()}"
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO defects (defect_id, vehicle_id, title, description, severity, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'open', ?, ?)",
        (defect_id, vehicle_id, description[:100], description, severity, now, now),
    )
    conn.commit()
    conn.close()
    return f"Defect {defect_id} created for vehicle {vehicle_id} with severity {severity}."


def _flag_log_entry(log_id: str, flag_type: str, note: str) -> str:
    """Flag a log entry as a known issue or for follow-up."""
    return f"Log entry {log_id} flagged as '{flag_type}': {note}"


def build_write_tools() -> list[StructuredTool]:
    """Standalone write-action tools, unwrapped (no approval gating applied yet)."""
    return [
        StructuredTool.from_function(
            func=_create_defect,
            name="create_defect",
            description="[REQUIRES APPROVAL] Create a new defect record in the fleet database.",
        ),
        StructuredTool.from_function(
            func=_flag_log_entry,
            name="flag_log_entry",
            description="[REQUIRES APPROVAL] Flag a log entry as a known issue or for follow-up.",
        ),
    ]
