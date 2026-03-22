# MCP Client-Server Demo

A **complete end-to-end demo** of the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) — showing how an AI-powered chat app connects to external tools, data, and prompt templates through MCP.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                             │
│                                                                     │
│  ┌──────────────────────┐    ┌────────────────────────────────────┐ │
│  │     Chat Panel        │    │        MCP Explorer Panel          │ │
│  │                       │    │                                    │ │
│  │  User ←→ Claude       │    │  Browse & test:                   │ │
│  │  (with tool use)      │    │  • Tools (calculator, weather...) │ │
│  │                       │    │  • Resources (server info, notes) │ │
│  │                       │    │  • Prompts (summarize, review...) │ │
│  └──────────┬───────────┘    └──────────────┬─────────────────────┘ │
│             │ HTTP                           │ HTTP                   │
└─────────────┼───────────────────────────────┼───────────────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                                 │
│                                                                     │
│  REST API endpoints:                                                │
│    POST /api/chat           → AI chat with tool use                 │
│    GET  /api/tools          → List MCP tools                        │
│    POST /api/tools/:name    → Call a tool directly                  │
│    GET  /api/resources      → List MCP resources                    │
│    GET  /api/resources/:uri → Read a resource                       │
│    GET  /api/prompts        → List MCP prompts                      │
│    POST /api/prompts/:name  → Render a prompt template              │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    MCP CLIENT                                  │ │
│  │                                                                │ │
│  │  • Connects to MCP server via stdio transport                 │ │
│  │  • Discovers tools, resources, prompts                        │ │
│  │  • Integrates with Claude API for agentic tool-use loop       │ │
│  └───────────────────────┬────────────────────────────────────────┘ │
└──────────────────────────┼──────────────────────────────────────────┘
                           │ stdio (stdin/stdout)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     MCP SERVER                                      │
│                                                                     │
│  TOOLS (functions the LLM can call):                                │
│    • calculator      — add, subtract, multiply, divide              │
│    • get_weather     — weather for 5 cities                         │
│    • manage_notes    — CRUD operations on notes                     │
│    • get_datetime    — current date/time in various formats         │
│                                                                     │
│  RESOURCES (data the LLM can read):                                 │
│    • memo://server-info        — server description                 │
│    • memo://available-cities   — city weather data (JSON)           │
│    • memo://notes/{title}      — individual notes                   │
│                                                                     │
│  PROMPTS (reusable templates):                                      │
│    • summarize          — summarize text in various styles          │
│    • code-review        — review code for bugs & improvements       │
│    • explain-concept    — explain topics at different levels        │
└─────────────────────────────────────────────────────────────────────┘
```

## How MCP Works (End-to-End Flow)

```
1. User types: "What's the weather in Tokyo?"
              │
              ▼
2. Frontend sends POST /api/chat { message: "..." }
              │
              ▼
3. Backend's MCP Client sends message to Claude API
   with MCP tools registered as Anthropic tools
              │
              ▼
4. Claude decides to use the "get_weather" tool
   and responds with a tool_use block
              │
              ▼
5. MCP Client calls session.call_tool("get_weather", {city: "Tokyo"})
   which sends the request to the MCP Server over stdio
              │
              ▼
6. MCP Server executes the tool handler and returns the result
              │
              ▼
7. MCP Client sends the tool result back to Claude
              │
              ▼
8. Claude generates a natural language response using the tool result
              │
              ▼
9. Response flows back: Claude → MCP Client → FastAPI → Frontend
```

## The Three MCP Primitives

| Primitive    | Direction       | Description                              | Example                     |
|-------------|-----------------|------------------------------------------|-----------------------------|
| **Tools**    | LLM → Server   | Functions the LLM can invoke             | `calculator`, `get_weather` |
| **Resources**| Client → Server | Data/content the client can read         | `memo://server-info`        |
| **Prompts**  | Client → Server | Reusable prompt templates with arguments | `summarize(text, style)`    |

## Project Structure

```
mcp-client-demo/
├── mcp_server/              # MCP Server
│   ├── __init__.py
│   └── server.py            # Server with tools, resources, prompts
│
├── mcp_client/              # MCP Client library
│   ├── __init__.py
│   └── client.py            # Client with Claude integration
│
├── backend/                 # FastAPI backend
│   ├── __init__.py
│   └── app.py               # REST API bridging frontend ↔ MCP
│
├── frontend/                # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/          # shadcn/ui components
│   │   │   ├── ChatPanel.jsx
│   │   │   └── ExplorerPanel.jsx
│   │   ├── lib/
│   │   │   ├── api.js       # API client
│   │   │   └── utils.js     # Utility functions
│   │   ├── App.jsx          # Main app layout
│   │   ├── main.jsx         # Entry point
│   │   └── index.css        # Tailwind + shadcn theme
│   ├── package.json
│   └── vite.config.js
│
├── requirements.txt         # Python dependencies
├── Makefile                 # Easy commands
├── .env.example             # Environment template
└── README.md                # This file
```

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Anthropic API key** ([get one here](https://console.anthropic.com/))

### 1. Install dependencies

```bash
make install
```

Or manually:

```bash
# Python
pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

### 2. Set your API key

```bash
# Option A: Environment variable
export ANTHROPIC_API_KEY=your-key-here

# Option B: Copy and edit .env
cp .env.example .env
# Edit .env with your key
```

### 3. Run the application

Open **two terminals**:

```bash
# Terminal 1 — Backend (starts MCP server automatically)
make backend
```

```bash
# Terminal 2 — Frontend
make frontend
```

Then open **http://localhost:5173** in your browser.

## Usage Guide

### Chat Panel (Left)

The chat panel lets you interact with Claude. Claude has access to all MCP tools and will use them automatically:

- **"What's the weather in London?"** → Uses `get_weather` tool
- **"Calculate 123 * 456"** → Uses `calculator` tool
- **"Create a note called 'ideas' with some content"** → Uses `manage_notes` tool
- **"What time is it?"** → Uses `get_datetime` tool

Tool usage is shown as badges on assistant messages.

### MCP Explorer (Right)

Browse and directly test all three MCP primitives:

- **Tools tab** — See all available tools and click "Try" to call them with demo arguments
- **Resources tab** — See all resources and click "Read" to fetch their content
- **Prompts tab** — See all prompt templates and click "Try" to render them

## Key Concepts Demonstrated

1. **MCP Server** — How to define tools, resources, and prompts using the MCP SDK
2. **MCP Client** — How to connect to a server, discover capabilities, and call tools
3. **Stdio Transport** — Server runs as a subprocess, communicating via stdin/stdout
4. **LLM Integration** — Claude's tool-use capability paired with MCP tools
5. **Agentic Loop** — Client handles the tool_use → tool_result → response cycle
6. **REST Bridge** — FastAPI exposes MCP capabilities as a standard REST API

## API Reference

| Method | Endpoint               | Description                    |
|--------|------------------------|--------------------------------|
| POST   | `/api/chat`            | Chat with Claude (uses tools)  |
| GET    | `/api/tools`           | List available tools           |
| POST   | `/api/tools/:name`     | Call a tool directly           |
| GET    | `/api/resources`       | List available resources       |
| GET    | `/api/resources/:uri`  | Read a resource                |
| GET    | `/api/prompts`         | List available prompts         |
| POST   | `/api/prompts/:name`   | Render a prompt template       |
| DELETE | `/api/sessions/:id`    | Clear chat session             |
| GET    | `/api/health`          | Health check                   |

## Technology Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Frontend  | React 18, Tailwind CSS, shadcn/ui   |
| Backend   | Python, FastAPI, Uvicorn            |
| MCP       | MCP Python SDK                      |
| AI        | Claude (via Anthropic API)          |
| Transport | stdio (subprocess)                  |
| Build     | Vite (frontend), Make (orchestration)|
