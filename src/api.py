# -*- coding: utf-8 -*-
"""FastAPI backend with SSE streaming.

Exposes the Agent Loop as an API endpoint.
Frontend connects via SSE (Server-Sent Events) for real-time display.

SSE vs WebSocket:
  - SSE: one-way (server -> client), simpler, auto-reconnect
  - WebSocket: two-way, more complex
  - We use SSE because the model only streams output to frontend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import json
import os
import asyncio

from .agent.loop import AgentLoop
from .session.store import create_session, write_message, read_session, list_sessions

load_dotenv()

app = FastAPI(title="Stock Agent API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance (initialized on startup)
agent = None


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


@app.on_event("startup")
async def startup():
    global agent
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    base_url = os.environ.get("BASE_URL")
    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    if not api_key:
        raise ValueError("Please set ANTHROPIC_API_KEY")
    agent = AgentLoop(api_key=api_key, model=model, base_url=base_url)
    print(f"Agent initialized: model={model}, base_url={base_url}")


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """SSE streaming chat endpoint.

    Returns a streaming response with SSE events:
      data: {"type":"round_start","round":1}
      data: {"type":"text","content":"..."}
      data: {"type":"tool_use","name":"stock_quote","input":{...}}
      data: {"type":"tool_result","name":"stock_quote","content":"..."}
      data: {"type":"final_response","content":"..."}
      data: [DONE]
    """
    global agent
    session_id = request.session_id or create_session()
    write_message(session_id, {"role": "user", "content": request.message})

    async def event_generator():
        try:
            async for event in agent.run_sse(request.message):
                yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"

                # Record final response to session
                if event.get("type") == "final_response":
                    write_message(session_id, {"role": "assistant", "content": event["content"]})

            # Send session_id in the final event
            yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/sessions")
async def get_sessions():
    """List all sessions (for sidebar display)."""
    sessions = list_sessions()
    return sessions


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get full session history."""
    messages = read_session(session_id)
    return {"session_id": session_id, "messages": messages}


@app.post("/api/sessions")
async def create_new_session():
    """Create a new empty session."""
    session_id = create_session()
    return {"session_id": session_id}


@app.get("/api/health")
async def health():
    return {"status": "ok", "agent_initialized": agent is not None}