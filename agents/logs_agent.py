"""
Logs Agent — analyzes diagnostic/integration JSONL logs for error patterns,
failure rates, DTC codes, CAN bus errors. READ-ONLY.

A real create_agent loop: the LLM picks which analysis tool(s) to call based
on the question, instead of a hand-written keyword dispatcher.
"""

import json
from collections import Counter
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from agents.agent_utils import run_agent_sync

LOGS_PATH = Path(__file__).parent.parent / "data" / "integration_logs.jsonl"

LOGS_SYSTEM_PROMPT = """You are a diagnostics specialist for automotive integration logs.
Use the tools available to analyze DTC codes, CAN bus errors, error/critical entries,
recurring patterns, or per-vehicle summaries. Pick whichever tool(s) best answer the
question — call more than one if the question spans several angles. Answer concisely
based only on the tool output."""


def _load_logs() -> list[dict]:
    logs = []
    with open(LOGS_PATH) as f:
        for line in f:
            if line.strip():
                logs.append(json.loads(line))
    return logs


@tool
def analyze_dtcs() -> str:
    """Frequency of DTC (Diagnostic Trouble Code) occurrences, overall and by ECU."""
    logs = _load_logs()
    dtc_logs = [l for l in logs if "dtc_code" in l]
    if not dtc_logs:
        return "No DTC codes found in the logs."

    dtc_counts = Counter(l["dtc_code"] for l in dtc_logs)
    dtc_by_ecu = Counter(f"{l['dtc_code']} on {l['ecu_type']}" for l in dtc_logs)

    lines = ["## DTC Analysis", f"Total DTC entries: {len(dtc_logs)}", "", "### Top DTCs by frequency:"]
    for dtc, count in dtc_counts.most_common(10):
        lines.append(f"- {dtc}: {count} occurrences")
    lines.append("")
    lines.append("### DTC-ECU combinations:")
    for combo, count in dtc_by_ecu.most_common(10):
        lines.append(f"- {combo}: {count}")
    return "\n".join(lines)


@tool
def analyze_can_errors() -> str:
    """Frequency of CAN bus errors (bus-off, stuff error, CRC error, etc.), overall and by ECU."""
    logs = _load_logs()
    can_logs = [l for l in logs if "can_error" in l]
    if not can_logs:
        return "No CAN bus errors found in the logs."

    error_counts = Counter(l["can_error"] for l in can_logs)
    by_ecu = Counter(f"{l['can_error']} on {l['ecu_type']}" for l in can_logs)

    lines = ["## CAN Bus Error Analysis", f"Total CAN errors: {len(can_logs)}", "", "### By error type:"]
    for err, count in error_counts.most_common():
        lines.append(f"- {err}: {count}")
    lines.append("")
    lines.append("### By ECU:")
    for combo, count in by_ecu.most_common(10):
        lines.append(f"- {combo}: {count}")
    return "\n".join(lines)


@tool
def analyze_errors() -> str:
    """Breakdown of ERROR/CRITICAL severity log entries by severity, ECU, and source."""
    logs = _load_logs()
    error_logs = [l for l in logs if l["severity"] in ("ERROR", "CRITICAL")]
    if not error_logs:
        return "No errors found in the logs."

    by_severity = Counter(l["severity"] for l in error_logs)
    by_ecu = Counter(l["ecu_type"] for l in error_logs)
    by_source = Counter(l["source"] for l in error_logs)

    lines = [
        "## Error Analysis",
        f"Total error/critical entries: {len(error_logs)}",
        "",
        "### By severity:",
    ]
    for sev, count in by_severity.most_common():
        lines.append(f"- {sev}: {count}")
    lines.append("")
    lines.append("### Top ECUs with errors:")
    for ecu, count in by_ecu.most_common(5):
        lines.append(f"- {ecu}: {count}")
    lines.append("")
    lines.append("### By source:")
    for src, count in by_source.most_common():
        lines.append(f"- {src}: {count}")
    return "\n".join(lines)


@tool
def analyze_patterns() -> str:
    """Recurring/frequent patterns: error distribution by hour, and ECUs that tend to
    fail together on the same vehicle (co-failure patterns)."""
    logs = _load_logs()
    error_logs = [l for l in logs if l["severity"] in ("ERROR", "CRITICAL")]
    by_hour = Counter()
    for l in error_logs:
        hour = l["timestamp"][11:13]
        by_hour[hour] += 1

    ecu_pairs = Counter()
    by_vehicle = {}
    for l in error_logs:
        vid = l["vehicle_id"]
        by_vehicle.setdefault(vid, set()).add(l["ecu_type"])
    for vid, ecus in by_vehicle.items():
        ecus_list = sorted(ecus)
        for i in range(len(ecus_list)):
            for j in range(i + 1, len(ecus_list)):
                ecu_pairs[(ecus_list[i], ecus_list[j])] += 1

    lines = ["## Pattern Analysis", "", "### Error distribution by hour:"]
    for hour in sorted(by_hour.keys()):
        lines.append(f"- {hour}:00 — {by_hour[hour]} errors")
    lines.append("")
    lines.append("### ECU co-failure patterns:")
    for (e1, e2), count in ecu_pairs.most_common(5):
        lines.append(f"- {e1} + {e2}: {count} vehicles with co-occurring errors")
    return "\n".join(lines)


@tool
def summarize_logs(vehicle_id: str | None = None) -> str:
    """Overall log summary (counts by severity, ECU, and source). Pass vehicle_id
    to scope the summary to a single vehicle (e.g. VIN-0001-TEST)."""
    logs = _load_logs()
    if vehicle_id:
        logs = [l for l in logs if l["vehicle_id"] == vehicle_id]
        if not logs:
            return f"No logs found for vehicle {vehicle_id}."

    by_sev = Counter(l["severity"] for l in logs)
    by_ecu = Counter(l["ecu_type"] for l in logs)
    by_source = Counter(l["source"] for l in logs)

    lines = [
        "## Log Summary",
        f"Total entries: {len(logs)}",
        "",
        "### By severity:",
    ]
    for sev in ["CRITICAL", "ERROR", "WARNING", "INFO"]:
        lines.append(f"- {sev}: {by_sev.get(sev, 0)}")
    lines.append("")
    lines.append("### Top ECUs by log volume:")
    for ecu, count in by_ecu.most_common(5):
        lines.append(f"- {ecu}: {count}")
    lines.append("")
    lines.append("### By source:")
    for src, count in by_source.most_common():
        lines.append(f"- {src}: {count}")
    return "\n".join(lines)


LOGS_TOOLS = [analyze_dtcs, analyze_can_errors, analyze_errors, analyze_patterns, summarize_logs]


def build_logs_tool(llm: BaseChatModel):
    """Build the logs specialist agent and return the single tool the coordinator calls."""
    agent = create_agent(model=llm, tools=LOGS_TOOLS, system_prompt=LOGS_SYSTEM_PROMPT)

    @tool
    def logs_agent(query: str, config: RunnableConfig) -> str:
        """Diagnostics specialist — analyzes integration JSONL logs for error patterns,
        failure rates, DTC codes, and CAN bus errors. Pass a natural-language query
        about log analysis, error patterns, DTC frequencies, or specific vehicle/ECU diagnostics."""
        return run_agent_sync(agent, query, config=config)

    return logs_agent
