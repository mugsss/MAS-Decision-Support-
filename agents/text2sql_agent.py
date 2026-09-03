"""
Text2SQL Agent — NL → SQL against SQLite fleet DB. READ-ONLY.
A real create_agent loop over get_schema/run_sql_query: the LLM can see a
validation or execution error and retry with corrected SQL instead of failing once.
"""

import sqlite3

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from agents.agent_utils import run_agent_sync
from guardrails.output_guard import OutputGuard

PLATFORMS = ["MQB-Evo", "MEB", "PPE", "SSP"]
TEST_TYPES = ["flash_test", "integration_test", "regression_test", "e2e_test", "smoke_test"]
TEST_RESULTS = ["pass", "fail", "blocked", "skipped"]
DEFECT_SEVERITIES = ["critical", "major", "minor", "trivial"]
DEFECT_STATUSES = ["open", "in_progress", "resolved", "closed"]

SCHEMA_INFO = f"""Tables in the fleet database:

vehicles(vehicle_id TEXT PK, platform TEXT, model_year INT, project_code TEXT, ecu_count INT, created_at TEXT)
integration_runs(run_id TEXT PK, vehicle_id TEXT FK, run_type TEXT, started_at TEXT, finished_at TEXT, status TEXT, total_tests INT, passed INT, failed INT, blocked INT)
test_results(test_id TEXT PK, run_id TEXT FK, test_name TEXT, test_type TEXT, result TEXT, duration_ms INT, ecu_type TEXT, error_message TEXT, executed_at TEXT)
defects(defect_id TEXT PK, vehicle_id TEXT FK, title TEXT, description TEXT, severity TEXT, status TEXT, ecu_type TEXT, dtc_code TEXT, created_at TEXT, updated_at TEXT)

Valid values:
- platform: {", ".join(PLATFORMS)}
- run_type / test_type: {", ".join(TEST_TYPES)}
- result: {", ".join(TEST_RESULTS)}
- defect severity: {", ".join(DEFECT_SEVERITIES)}
- defect status: {", ".join(DEFECT_STATUSES)}
"""

TEXT2SQL_SYSTEM_PROMPT = """You are a SQL expert for the automotive fleet database.
Call get_schema first if you need the table layout or valid column values, then call
run_sql_query with a single SQLite SELECT statement to answer the question.

Rules:
- Only SELECT statements — no other statement type is permitted
- Use proper SQLite syntax
- Use LIMIT when the result set could be large (default LIMIT 20)
- For counts and aggregations, use appropriate GROUP BY
- Date columns are ISO format strings — use string comparison for date filters
- Only use the exact valid values listed by get_schema for platform, test_type,
  result, severity, and status columns

If run_sql_query returns an error, fix the SQL and retry (at most twice) before
telling the user the query could not be answered. Present the final results clearly."""

def build_text2sql_tool(llm: BaseChatModel, db_path: str):
    """Build the text2sql specialist agent and return the single tool the coordinator calls."""
    output_guard = OutputGuard()

    @tool
    def get_schema() -> str:
        """Return the fleet database table layout and the valid values for
        enum-like columns (platform, test_type, result, severity, status)."""
        return SCHEMA_INFO

    @tool
    def run_sql_query(sql: str) -> str:
        """Execute a single read-only SQLite SELECT statement against the fleet
        database and return the results as a table. Returns an error message
        (not an exception) if the SQL is invalid or unsafe, so it can be corrected."""
        query_sql = sql.strip().strip("`").strip()
        if query_sql.lower().startswith("sql"):
            query_sql = query_sql[3:].strip()

        is_safe, reason = output_guard.validate_sql(query_sql)
        if not is_safe:
            return f"SQL validation failed: {reason}\nGenerated SQL: {query_sql}"

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.execute(query_sql)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []
            conn.close()

            if not rows:
                return f"Query returned no results.\nSQL: {query_sql}"

            result_lines = [f"SQL: {query_sql}", f"Results ({len(rows)} rows):", ""]
            result_lines.append(" | ".join(columns))
            result_lines.append("-" * (len(" | ".join(columns))))
            for row in rows[:20]:
                result_lines.append(" | ".join(str(row[c]) for c in columns))

            if len(rows) > 20:
                result_lines.append(f"... and {len(rows) - 20} more rows")

            return "\n".join(result_lines)

        except Exception as e:
            return f"SQL execution error: {e}\nSQL: {query_sql}"

    agent = create_agent(
        model=llm, tools=[get_schema, run_sql_query], system_prompt=TEXT2SQL_SYSTEM_PROMPT
    )

    @tool
    def text2sql_agent(query: str, config: RunnableConfig) -> str:
        """Fleet analytics specialist — translates natural-language questions into SQL
        queries against the fleet database. Covers vehicles, integration runs, test results,
        and defects. Pass a clear analytical question about fleet data."""
        return run_agent_sync(agent, query, config=config)

    return text2sql_agent
