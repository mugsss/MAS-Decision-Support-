"""
YAML config loading with ${ENV_VAR} substitution.

Unset placeholders fall back to documented defaults rather than being left as
literals — otherwise a missing .env silently yields paths like "${MEMORY_DB_PATH}"
and SQLite creates a file by that name instead of failing.
"""

import os
import re
from pathlib import Path

import yaml

_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

DEFAULTS = {
    "FLEET_DB_PATH": "data/fleet.db",
    "MEMORY_DB_PATH": "data/memory.db",
    "CHROMA_PERSIST_DIR": "data/chroma",
    "PDM_DATA_PATH": "data/pdm_vehicles.json",
    "LOGS_DATA_PATH": "data/integration_logs.jsonl",
    "DOCS_DIR": "docs",
    "MCP_SERVER_PATH": "pdm_mcp/server.py",
}


def substitute_env(raw: str) -> str:
    """Replace ${VAR} with the environment value, else a known default."""

    def _replace(match: re.Match) -> str:
        var = match.group(1)
        value = os.getenv(var)
        if value is not None:
            return value
        if var in DEFAULTS:
            return DEFAULTS[var]
        raise KeyError(
            f"Config references ${{{var}}} but it is not set and has no default. "
            f"Add it to your .env file."
        )

    return _PLACEHOLDER.sub(_replace, raw)


def load_yaml_config(path: str) -> dict:
    """Load a YAML file with environment-variable substitution applied."""
    return yaml.safe_load(substitute_env(Path(path).read_text()))


def env_or_default(var: str) -> str:
    """Look up an environment variable, falling back to the same documented
    default used for ${VAR} substitution in YAML — the single source of truth
    for defaults, whether a caller reads them via YAML or os.getenv directly."""
    value = os.getenv(var)
    if value is not None:
        return value
    if var in DEFAULTS:
        return DEFAULTS[var]
    raise KeyError(f"{var} is not set and has no default. Add it to your .env file.")
