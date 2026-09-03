"""
FastAPI app — API layer for the Automotive MAS.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent_factory import AgentFactory

load_dotenv()

factory: AgentFactory | None = None
coordinator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global factory, coordinator
    factory = AgentFactory()
    coordinator = factory.build()
    yield
    if factory:
        factory.shutdown()


app = FastAPI(
    title="Automotive MAS — Decision Support",
    description="Multi-agent system for automotive software integration decision support",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)


# --- Request / Response models ---

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    agents_used: list[str]
    skills_used: list[str]
    blocked: bool = False
    block_reason: str | None = None


class ApprovalRequest(BaseModel):
    reason: str | None = None


# --- Endpoints ---

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if coordinator is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    result = await coordinator.chat(
        message=request.message,
        conversation_id=request.conversation_id,
    )
    return ChatResponse(**result)


@app.get("/api/actions/pending")
async def list_pending_actions():
    if factory is None:
        raise HTTPException(status_code=503, detail="System not initialized")
    store = factory.get_approval_store()
    return {"actions": store.list_pending()}


@app.post("/api/actions/{action_id}/approve")
async def approve_action(action_id: str):
    if factory is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    store = factory.get_approval_store()
    action = store.approve(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found or already resolved")

    tool_name = action["tool_name"]
    args = action["args"]

    # Use the UNWRAPPED tool — the version in tool_map is approval-gated and
    # would simply re-queue the action instead of executing it.
    executable = factory.get_executable_tool(tool_name)
    if executable is None:
        return {
            "status": "approved",
            "action_id": action_id,
            "note": f"No executable tool registered for '{tool_name}'",
        }

    try:
        result = executable.invoke(args)
        store.set_result(action_id, result)
        return {"status": "approved", "action_id": action_id, "result": result}
    except Exception as e:
        store.set_result(action_id, {"error": str(e)})
        return {"status": "error", "action_id": action_id, "error": str(e)}


@app.post("/api/actions/{action_id}/reject")
async def reject_action(action_id: str, request: ApprovalRequest | None = None):
    if factory is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    store = factory.get_approval_store()
    reason = request.reason if request else ""
    success = store.reject(action_id, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Action not found or already resolved")
    return {"status": "rejected", "action_id": action_id, "reason": reason}


@app.get("/api/conversations/{conversation_id}/memory")
async def get_conversation_memory(conversation_id: str):
    if coordinator is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    messages = coordinator.long_term.get_conversation(conversation_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    memories = coordinator.long_term.retrieve_relevant(
        " ".join(m.get("content", "") for m in messages[:3])
    )
    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "related_memories": memories,
    }


@app.get("/api/traces/{run_id}")
async def get_trace(run_id: str):
    langsmith_project = os.getenv("LANGCHAIN_PROJECT", "automotive-mas")
    return {
        "run_id": run_id,
        "langsmith_url": f"https://smith.langchain.com/o/default/projects/p/{langsmith_project}/r/{run_id}",
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "agents": ["niki (PDM)", "logs_agent", "text2sql_agent", "code_assist_agent"],
        "mcp_server": factory.mcp_client is not None if factory else False,
    }


# --- React frontend ---------------------------------------------------------
# Mounted last so it never shadows an /api route. Built with:
#   cd frontend && npm install && npm run build
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    @app.get("/")
    async def frontend_missing():
        return {
            "message": "Frontend not built. Run: cd frontend && npm install && npm run build",
            "api_docs": "/docs",
        }


if __name__ == "__main__":
    import uvicorn

    print("\n  API running at http://localhost:8000\n")
    # 127.0.0.1 binds locally only. Use 0.0.0.0 to expose on your network —
    # note 0.0.0.0 is a bind address, not a URL you can open in a browser.
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
