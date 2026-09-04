"""
FastAPI app — API layer for the Automotive MAS.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent_factory import AgentFactory

load_dotenv()

factory: AgentFactory | None = None
coordinator = None

'''
Before the server starts accepting requests, build your entire agent system. 
When the server shuts down, clean it all up.
'''
@asynccontextmanager
async def lifespan(app: FastAPI):
    global factory, coordinator
    factory = AgentFactory()
    coordinator = await factory.build()
    yield #server is live and accepting requests
    if factory:
        await factory.shutdown()


app = FastAPI(
    title="Automotive MAS — Decision Support",
    description="Multi-agent system for automotive software integration decision support",
    version="1.0.0",
    lifespan=lifespan
)


# --- Request / Response models ---

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ApprovalRequest(BaseModel):
    decision: str = "approve"
    reason: str | None = None
    edited_args: dict | None = None


# --- Endpoints ---

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    if coordinator is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    return StreamingResponse(
        coordinator.chat_stream(
            message=request.message,
            conversation_id=request.conversation_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/api/actions/pending")
async def list_pending_actions():
    if coordinator is None:
        raise HTTPException(status_code=503, detail="System not initialized")
    return {"actions": coordinator.list_pending()}


@app.post("/api/actions/{action_id}/approve")
async def approve_action(action_id: str, request: ApprovalRequest | None = None):
    if coordinator is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    decision = request.decision if request else "approve"
    message = request.reason if request else None
    edited_args = request.edited_args if request else None

    result = await coordinator.handle_approval(
        action_id=action_id,
        decision_type=decision,
        message=message,
        edited_args=edited_args,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    result["result"] = result.get("response", "")
    return result


@app.post("/api/actions/{action_id}/reject")
async def reject_action(action_id: str, request: ApprovalRequest | None = None):
    if coordinator is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    reason = request.reason if request else "Rejected by user."

    result = await coordinator.handle_approval(
        action_id=action_id,
        decision_type="reject",
        message=reason,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/conversations/{conversation_id}/memory")
async def get_conversation_memory(conversation_id: str):
    if coordinator is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    messages = coordinator.long_term.get_conversation(conversation_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "conversation_id": conversation_id,
        "messages": messages,
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "agents": ["niki (PDM)", "logs_agent", "text2sql_agent", "code_assist_agent"],
        "mcp_server": factory.mcp_client is not None if factory else False,
    }


# --- React frontend ---------------------------------------------------------
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    @app.get("/")
    async def frontend_missing():
        return {
            "message": "Frontend not built. Run: cd frontend && npm install && npm run build",
        }


if __name__ == "__main__":
    import uvicorn

    print("\n  API running at http://localhost:8000\n")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
