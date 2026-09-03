# Multi-Agent System Decision-Support in Automotive Engineering

A multi-agent decision-support system for automotive software integration:
a ReAct **Coordinator** delegates to four read-only specialist agents, with
human-in-the-loop approval gating every write action.

## Architecture

**Agent-as-tools with ReAct orchestration.** The Coordinator is the only agent
that sees conversation history. Each specialist is a LangChain tool receiving a
self-contained sub-query — no history, no access to other agents' outputs.

| Agent | Role | Data source |
|-------|------|-------------|
| `niki` (PDM) | Vehicle configs, ECU assignments, part numbers, SW versions | Local MCP server (JSON-RPC 2.0 over stdio) |
| `logs_agent` | Error patterns, failure rates, DTC codes, CAN bus errors | `data/integration_logs.jsonl` |
| `text2sql_agent` | Fleet analytics via NL → SQL | `data/fleet.db` (SQLite) |
| `code_assist_agent` | AUTOSAR / ASPICE / ASIL questions via RAG | ChromaDB over `docs/` |

**Skills** (`skills.yaml`) are reusable prompt+tool bundles registered as
top-level tools that compose across specialists — e.g. `vehicle_health_check`
uses both PDM and Text2SQL.

## Setup

```bash
pip install -r requirements.txt

cp .env.example .env          # then add your GOOGLE_API_KEY
python setup_data.py          # generate synthetic data (deterministic, seed=42)
python rag/indexer.py         # build the ChromaDB index

cd frontend && npm install && npm run build && cd ..

python main.py                # → http://localhost:8000
```

Open **http://localhost:8000** for the chat UI.

### Running without the HTTP layer

The multi-agent system does not depend on FastAPI — the coordinator runs
in-process. `cli.py` is a direct entry point, useful for quick testing and for
scripted evaluation runs:

```bash
python cli.py                              # interactive
python cli.py "how many open defects?"     # single question
python cli.py --file questions.txt         # batch
```

FastAPI earns its place only for HTTP consumers: the React UI, and approving
actions over REST. In the interactive CLI, `/pending`, `/approve <id>` and
`/reject <id>` cover the HITL flow locally instead.

Note that guardrails and memory live in the `Coordinator` wrapper, not in the
LangGraph agent. Calling the underlying agent's `.invoke()` directly bypasses
injection detection, PII redaction, and both memory tiers — go through
`Coordinator.chat()` to keep them.

### Frontend

A React app (Vite) in `frontend/`. It shows which specialist answered each
question and surfaces pending write actions with approve/reject controls, so the
orchestration and the HITL gate are both visible during a demo.

FastAPI serves the built app from `frontend/dist` at `/`, mounted after the API
routes so it never shadows `/api/*`.

For frontend development with hot reload, run the backend and Vite separately —
the dev server proxies `/api` to port 8000:

```bash
python main.py                 # terminal 1 — backend on :8000
cd frontend && npm run dev      # terminal 2 — UI on :5173
```

Get a free Gemini API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

### Free-tier quota

Gemini's free tier caps requests **per model per day**. One question costs
several calls (planner loop + specialist sub-chain + summarization), so model
choice matters:

- `gemini-3.5-flash` — stronger, but only **20 requests/day** free
- `gemini-3.1-flash-lite` — the configured default, much larger daily allowance

`agents.yaml` also sets `requests_per_minute` for client-side throttling. That
guards the per-minute limit; the per-day cap is a hard ceiling no throttle can
avoid. Raise or remove both on a paid plan.

### Swapping the LLM

Everything depends only on the LangChain `BaseChatModel` / `Embeddings`
interfaces, so providers swap in one place — the `llm:` block of `agents.yaml`.

## API

| Endpoint | Purpose |
|----------|---------|
| `POST /api/chat` | Run the Coordinator |
| `GET /api/actions/pending` | List pending HITL actions |
| `POST /api/actions/{id}/approve` | Approve and execute |
| `POST /api/actions/{id}/reject` | Reject with optional reason |
| `GET /api/conversations/{id}/memory` | Conversation + extracted memories |
| `GET /api/traces/{run_id}` | LangSmith run link |
| `GET /api/health` | Health check |

## Human-in-the-loop

All four specialists are read-only. Write tools (`create_defect`,
`update_sw_version`, `flag_log_entry`) are wrapped in `HumanApprovalTool`, which
intercepts the call, stores it in `pending_actions`, and returns an action ID
instead of executing. The Coordinator acknowledges the pending state and keeps
answering. Approval executes the *unwrapped* tool via `/api/actions/{id}/approve`.

## Memory

- **Short-term** — sliding window of the last 10 messages per `conversation_id`; older turns are summarized once they exceed ~3000 tokens.
- **Long-term** — conversations persisted to SQLite; facts extracted by an LLM call and embedded into ChromaDB. On a new conversation, the top-3 relevant memories are injected into the Coordinator's system prompt.

## Guardrails

- **Input** — length limit, prompt-injection patterns, topic scoping (rejects before any LLM call is made)
- **Output** — PII redaction, SQL validation (SELECT-only, single statement), low-relevance RAG warnings

## Project layout

```
agents.yaml / skills.yaml   YAML-driven configuration
frontend/                   React (Vite) chat UI
llm_provider.py             Provider factory (chat models + embeddings)
config_loader.py            YAML loading with ${ENV_VAR} substitution
agent_factory.py            Builds agents, tools, skills, Coordinator
coordinator.py              ReAct agent + memory + guardrail wiring
main.py                     FastAPI app (HTTP layer — optional)
cli.py                      Direct entry point, no HTTP
agents/                     Four specialists
mcp/                        MCP server + client
rag/                        Indexer + retriever
memory/                     Short-term + long-term
guardrails/                 Input + output
hitl/                       Approval tool + pending store
skills/                     skills.yaml loader
observability/              LangSmith + OTel
setup_data.py               Synthetic data generator
```

## Notes

Data is synthetic and generated deterministically (`seed=42`): 10 PDM vehicles,
200 log entries, a 500-vehicle fleet DB, and 15 standards documents for RAG.
`setup_data.py` is safe to re-run — it rebuilds the identical dataset.
