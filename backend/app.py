"""
FastAPI Backend - REST API that bridges the React frontend to the MCP client.

Endpoints:
  POST /api/chat          - Send a message and get an AI response (with tool use)
  GET  /api/tools         - List available MCP tools
  GET  /api/resources     - List available MCP resources
  GET  /api/resources/{uri} - Read a specific resource
  GET  /api/prompts       - List available MCP prompt templates
  POST /api/prompts/{name} - Get a rendered prompt
  POST /api/tools/{name}  - Directly call a tool (bypass LLM)
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path so we can import mcp_client
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_client.client import MCPClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

mcp_client = MCPClient()
# Store conversations by session id
conversations: dict[str, list[dict]] = {}

# Path to the MCP server script
SERVER_SCRIPT = str(Path(__file__).resolve().parent.parent / "mcp_server" / "server.py")


# ---------------------------------------------------------------------------
# App lifecycle — start/stop MCP connection
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the MCP client connection across the app's lifetime."""
    logger.info(f"Connecting to MCP server: {SERVER_SCRIPT}")
    async with mcp_client.connect(SERVER_SCRIPT):
        logger.info("MCP client connected — server capabilities loaded")
        yield
    logger.info("MCP client disconnected")


app = FastAPI(
    title="MCP Client Demo API",
    description="REST API that integrates with an MCP server via the MCP client",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    tools_used: list[str] = []


class ToolCallRequest(BaseModel):
    arguments: dict


class PromptRequest(BaseModel):
    arguments: dict


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a chat message — Claude will use MCP tools as needed."""
    history = conversations.get(request.session_id)

    try:
        reply, updated_history = await mcp_client.chat(
            user_message=request.message,
            conversation_history=history,
        )
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=str(e))

    conversations[request.session_id] = updated_history

    # Extract which tools were used in this turn
    tools_used = []
    for msg in updated_history:
        if isinstance(msg.get("content"), list):
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tools_used.append(block["name"])

    return ChatResponse(
        reply=reply,
        session_id=request.session_id,
        tools_used=tools_used,
    )


# ---------------------------------------------------------------------------
# Tools endpoints
# ---------------------------------------------------------------------------

@app.get("/api/tools")
async def list_tools():
    """List all available MCP tools."""
    return {"tools": mcp_client.get_tools()}


@app.post("/api/tools/{tool_name}")
async def call_tool(tool_name: str, request: ToolCallRequest):
    """Directly call an MCP tool (bypassing the LLM)."""
    try:
        result = await mcp_client.call_tool(tool_name, request.arguments)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Resources endpoints
# ---------------------------------------------------------------------------

@app.get("/api/resources")
async def list_resources():
    """List all available MCP resources."""
    return {"resources": mcp_client.get_resources()}


@app.get("/api/resources/{uri:path}")
async def read_resource(uri: str):
    """Read an MCP resource by URI."""
    try:
        content = await mcp_client.read_resource(uri)
        return {"uri": uri, "content": content}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Prompts endpoints
# ---------------------------------------------------------------------------

@app.get("/api/prompts")
async def list_prompts():
    """List all available MCP prompt templates."""
    return {"prompts": mcp_client.get_prompts()}


@app.post("/api/prompts/{prompt_name}")
async def get_prompt(prompt_name: str, request: PromptRequest):
    """Get a rendered prompt template."""
    try:
        messages = await mcp_client.get_prompt(prompt_name, request.arguments)
        return {"prompt_name": prompt_name, "messages": messages}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

@app.delete("/api/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear conversation history for a session."""
    if session_id in conversations:
        del conversations[session_id]
    return {"message": f"Session '{session_id}' cleared"}


@app.get("/api/health")
async def health():
    """Health check."""
    return {
        "status": "ok",
        "mcp_connected": mcp_client.session is not None,
        "tools_count": len(mcp_client.get_tools()),
        "resources_count": len(mcp_client.get_resources()),
        "prompts_count": len(mcp_client.get_prompts()),
    }
