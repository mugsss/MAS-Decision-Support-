"""
Text2SQL Agent — NL → SQL against SQLite fleet DB. READ-ONLY.
A real create_agent loop over get_schema/run_sql_query: the LLM can see a
validation or execution error and retry with corrected SQL instead of failing once.
"""

import re
import sqlite3

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from agents.agent_utils import run_agent_sync

_DANGEROUS_SQL = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

ENUM_COLUMNS = {
    "vehicles": {"platform": "platform"},
    "integration_runs": {"run_type": "run_type"},
    "test_results": {"test_type": "test_type", "result": "result"},
    "defects": {"severity": "severity", "status": "status"},
}

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
    @tool
    def get_schema() -> str:
        """Return the fleet database table layout and the valid values for
        enum-like columns (platform, test_type, result, severity, status)."""
        conn = sqlite3.connect(db_path)
        table_sql = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()

        lines = ["Tables in the fleet database:\n"]
        for name, ddl in table_sql:
            lines.append(ddl + "\n")

        lines.append("\nValid values (queried from database):")
        for table, columns in ENUM_COLUMNS.items():
            for label, col in columns.items():
                values = [
                    r[0] for r in conn.execute(
                        f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL ORDER BY {col}"
                    ).fetchall()
                ]
                lines.append(f"- {label}: {', '.join(str(v) for v in values)}")

        conn.close()
        return "\n".join(lines)

    @tool
    def run_sql_query(sql: str) -> str:
        """Execute a single read-only SQLite SELECT statement against the fleet
        database and return the results as a table. Returns an error message
        (not an exception) if the SQL is invalid or unsafe, so it can be corrected."""
        query_sql = sql.strip().strip("`").strip()
        if query_sql.lower().startswith("sql"):
            query_sql = query_sql[3:].strip()

        stripped = query_sql.rstrip(";").strip()
        if not stripped.upper().startswith("SELECT"):
            return f"SQL validation failed: Only SELECT statements are allowed.\nGenerated SQL: {query_sql}"
        if _DANGEROUS_SQL.search(stripped):
            return f"SQL validation failed: SQL contains disallowed keywords.\nGenerated SQL: {query_sql}"
        if ";" in stripped:
            return f"SQL validation failed: Multiple statements are not allowed.\nGenerated SQL: {query_sql}"

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
