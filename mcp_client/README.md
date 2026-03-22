# MCP Client

The MCP client connects to an MCP server and provides a high-level API for interacting with its capabilities.

## What it does

1. **Connects** — Spawns the MCP server as a subprocess (stdio transport)
2. **Discovers** — Calls `list_tools()`, `list_resources()`, `list_prompts()` to learn what the server offers
3. **Bridges to Claude** — Registers MCP tools as Anthropic tool-use tools
4. **Agentic loop** — When Claude wants to use a tool, the client calls the MCP server and feeds the result back

## The Agentic Tool-Use Loop

```
User message
    │
    ▼
Claude API (with tools)
    │
    ├── stop_reason = "end_turn" → return response
    │
    └── stop_reason = "tool_use" → for each tool_use block:
            │
            ▼
        MCP Client calls session.call_tool(name, args)
            │
            ▼
        MCP Server executes and returns result
            │
            ▼
        Add tool_result to conversation
            │
            ▼
        Loop back to Claude API ──▶ (repeat until "end_turn")
```

## Usage

```python
from mcp_client.client import MCPClient

client = MCPClient()

async with client.connect("mcp_server/server.py") as c:
    # List capabilities
    tools = c.get_tools()
    resources = c.get_resources()

    # Call a tool directly
    result = await c.call_tool("calculator", {"operation": "add", "a": 1, "b": 2})

    # Chat with Claude (tools are used automatically)
    reply, history = await c.chat("What's the weather in Tokyo?")
```
