# MCP End-to-End Flow: Deep Dive Documentation

This document explains **how MCP (Model Context Protocol) works end-to-end** in this demo project, what each component does, and how MCP compares to other approaches like RAG.

---

## Table of Contents

1. [What is MCP?](#what-is-mcp)
2. [End-to-End Flow (Step by Step)](#end-to-end-flow-step-by-step)
3. [What the MCP Server Does](#what-the-mcp-server-does)
4. [What the MCP Client Does](#what-the-mcp-client-does)
5. [The Agentic Tool-Use Loop](#the-agentic-tool-use-loop)
6. [How the Pieces Connect](#how-the-pieces-connect)
7. [MCP vs RAG — Key Differences](#mcp-vs-rag--key-differences)
8. [MCP vs Function Calling — Key Differences](#mcp-vs-function-calling--key-differences)
9. [MCP vs LangChain / Agent Frameworks](#mcp-vs-langchain--agent-frameworks)
10. [When to Use What](#when-to-use-what)
11. [Glossary](#glossary)

---

## What is MCP?

**MCP (Model Context Protocol)** is an open standard created by Anthropic that defines how AI applications connect to external tools, data sources, and prompt templates. Think of it as **"USB-C for AI"** — a universal plug that lets any AI model talk to any data source or tool.

Before MCP, every AI integration was custom-built:
```
App A → custom code → Database
App B → different custom code → Same Database
App C → yet another approach → Same Database
```

With MCP, there's one standard protocol:
```
App A ──┐
App B ──┤── MCP Protocol ──→ MCP Server → Database
App C ──┘
```

### The Three Primitives

MCP defines three types of capabilities a server can expose:

| Primitive     | Who Initiates    | Purpose                                | Analogy                    |
|--------------|------------------|----------------------------------------|----------------------------|
| **Tools**     | The LLM decides  | Functions the AI can call              | "API endpoints for the AI" |
| **Resources** | The client/user  | Read-only data accessible by URI       | "Files the AI can read"    |
| **Prompts**   | The client/user  | Reusable prompt templates              | "Saved macros/shortcuts"   |

---

## End-to-End Flow (Step by Step)

Here's exactly what happens when a user asks **"What's the weather in Tokyo?"**:

### Phase 1: User to Backend

```
User types message in React UI
        │
        ▼
React calls POST /api/chat { message: "What's the weather in Tokyo?" }
        │
        ▼  (Vite proxy forwards /api/* to FastAPI on port 8000)
        │
FastAPI receives the request in backend/app.py → chat() endpoint
```

**What happens in code:**

- `frontend/src/components/ChatPanel.jsx` captures user input
- `frontend/src/lib/api.js` → `sendMessage()` sends HTTP POST to `/api/chat`
- Vite dev server proxies the request to `http://127.0.0.1:8000`
- `backend/app.py` → `chat()` endpoint receives it

### Phase 2: Backend to Claude (via MCP Client)

```
FastAPI calls mcp_client.chat(user_message, conversation_history)
        │
        ▼
MCP Client builds the request:
  - System prompt (describes available resources & prompts)
  - Conversation history (previous messages)
  - Tool definitions (converted from MCP format → Anthropic format)
  - User's new message
        │
        ▼
MCP Client sends everything to Claude API via anthropic.messages.create()
```

**What happens in code** (`mcp_client/client.py`):

```python
# MCP tools get converted to Anthropic tool format:
anthropic_tools = [
    {
        "name": tool.name,              # e.g., "get_weather"
        "description": tool.description, # e.g., "Get current weather..."
        "input_schema": tool.inputSchema # e.g., { "city": { "type": "string" } }
    }
    for tool in self._tools
]

# Then sent to Claude:
response = self.anthropic.messages.create(
    model="claude-sonnet-4-20250514",
    tools=anthropic_tools,       # ← MCP tools registered here
    messages=conversation_history,
    system=system_prompt,
)
```

### Phase 3: Claude Decides to Use a Tool

```
Claude analyzes the message and available tools
        │
        ▼
Claude returns: stop_reason="tool_use"
  content: [
    { type: "tool_use", name: "get_weather", input: { city: "Tokyo" } }
  ]
```

Claude does NOT execute the tool itself — it just says **"I want to call this tool with these arguments."** The client must actually execute it.

### Phase 4: MCP Client Calls MCP Server

```
MCP Client receives tool_use from Claude
        │
        ▼
MCP Client calls: session.call_tool("get_weather", { city: "Tokyo" })
        │
        ▼  (JSON-RPC message sent over stdin to the server subprocess)
        │
MCP Server receives the request
        │
        ▼
MCP Server executes the tool handler → _handle_weather({ city: "Tokyo" })
        │
        ▼
MCP Server returns the result over stdout:
  "Weather in Tokyo:\n  Temperature: 28°C\n  Condition: Sunny\n  Humidity: 55%"
```

**What happens in code** (`mcp_server/server.py`):

```python
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "get_weather":
        city = arguments["city"].lower()
        w = WEATHER_DATA[city]  # Look up from in-memory data
        return [TextContent(type="text", text=f"Weather in {city.title()}: ...")]
```

### Phase 5: Result Back to Claude

```
MCP Client receives the tool result from MCP Server
        │
        ▼
MCP Client adds tool_result to conversation:
  { role: "user", content: [{ type: "tool_result", tool_use_id: "...", content: "Weather in Tokyo:..." }] }
        │
        ▼
MCP Client sends updated conversation back to Claude API
        │
        ▼
Claude generates a natural language response:
  "The weather in Tokyo is currently sunny with a temperature of 28°C and 55% humidity."
```

### Phase 6: Response Back to User

```
Claude returns: stop_reason="end_turn"
  content: [{ type: "text", text: "The weather in Tokyo is currently sunny..." }]
        │
        ▼
MCP Client extracts the text and returns it to FastAPI
        │
        ▼
FastAPI returns JSON: { reply: "The weather in Tokyo...", tools_used: ["get_weather"] }
        │
        ▼
React receives the response and renders it in the chat panel
  (with a "get_weather" badge showing which tool was used)
```

### Complete Flow Diagram

```
┌─────────┐     HTTP      ┌─────────┐   Anthropic API   ┌─────────┐
│  React  │ ──────────▶   │ FastAPI  │  ──────────────▶  │  Claude │
│  UI     │ ◀──────────   │ Backend  │  ◀──────────────  │  API    │
└─────────┘               └────┬─────┘                   └─────────┘
                               │                              │
                               │ uses                         │ returns
                               ▼                              │ tool_use
                          ┌─────────┐                         │
                          │  MCP    │                         │
                          │ Client  │ ◀───────────────────────┘
                          └────┬────┘
                               │ stdio (JSON-RPC)
                               ▼
                          ┌─────────┐
                          │  MCP    │
                          │ Server  │ → executes tools, reads resources
                          └─────────┘
```

---

## What the MCP Server Does

The MCP Server (`mcp_server/server.py`) is a **standalone process** that exposes capabilities via the MCP protocol. It does NOT know about Claude, the frontend, or the backend — it just responds to MCP requests.

### Responsibilities

| Responsibility          | How                                              |
|------------------------|--------------------------------------------------|
| Declare available tools | `@app.list_tools()` returns tool schemas          |
| Execute tool calls      | `@app.call_tool()` runs the actual logic          |
| Declare resources       | `@app.list_resources()` returns resource URIs     |
| Serve resource content  | `@app.read_resource()` returns data for a URI     |
| Declare prompts         | `@app.list_prompts()` returns prompt templates    |
| Render prompts          | `@app.get_prompt()` fills in template arguments   |

### Transport

The server uses **stdio transport** — it reads JSON-RPC messages from stdin and writes responses to stdout. The MCP Client spawns it as a subprocess:

```
MCP Client                              MCP Server (subprocess)
    │                                        │
    │── stdin:  {"method":"tools/list"} ──▶  │
    │◀─ stdout: {"result":[...tools...]} ──  │
    │                                        │
    │── stdin:  {"method":"tools/call",  ──▶ │
    │           "params":{"name":"calc"}}     │
    │◀─ stdout: {"result":"6 * 7 = 42"} ──  │
```

### What the server does NOT do

- Does NOT call Claude or any LLM
- Does NOT know about HTTP or REST
- Does NOT manage conversation history
- Does NOT decide when to use tools (that's Claude's job)

---

## What the MCP Client Does

The MCP Client (`mcp_client/client.py`) is the **bridge** between the AI (Claude) and the MCP Server. It has two jobs:

### Job 1: Manage the MCP Server Connection

```python
# Spawn server as subprocess and establish session
async with client.connect("mcp_server/server.py") as c:
    # Protocol handshake happens automatically
    # Capabilities are discovered:
    #   - 4 tools (calculator, get_weather, manage_notes, get_datetime)
    #   - 4 resources (server-info, cities, notes)
    #   - 3 prompts (summarize, code-review, explain-concept)
```

### Job 2: Run the Agentic Tool-Use Loop

This is the core intelligence — the client orchestrates a **loop** between Claude and the MCP Server:

```python
while True:
    # 1. Send conversation to Claude (with tools)
    response = anthropic.messages.create(tools=mcp_tools, messages=history)

    # 2. Check: did Claude want to use a tool?
    if response.stop_reason == "tool_use":
        # 3. YES → Execute tool via MCP Server
        for tool_call in response.tool_use_blocks:
            result = await session.call_tool(tool_call.name, tool_call.input)
            # 4. Add result to conversation
            history.append(tool_result)
        # 5. Loop back to step 1 (Claude may want another tool)
    else:
        # 6. NO → Claude is done, return the final text
        return response.text
```

This loop can execute **multiple tool calls** in sequence. For example:
- "Compare the weather in Tokyo and London" → Claude calls `get_weather` twice
- "Create a note with today's date" → Claude calls `get_datetime`, then `manage_notes`

---

## The Agentic Tool-Use Loop

This is the most important concept. Here's the loop visualized:

```
                    ┌──────────────────────────────┐
                    │                              │
                    ▼                              │
        ┌───────────────────┐                     │
        │  Send messages +   │                     │
        │  tools to Claude   │                     │
        └────────┬──────────┘                     │
                 │                                │
                 ▼                                │
        ┌───────────────────┐     YES             │
        │ stop_reason ==     │ ─────────▶ Execute tool(s)
        │ "tool_use" ?       │            via MCP Server
        └────────┬──────────┘            │
                 │ NO                     │ Add tool_result
                 ▼                        │ to conversation
        ┌───────────────────┐            │
        │  Return final      │            │
        │  text response     │ ◀──────────┘
        └───────────────────┘   (loop back)
```

### Why is this "agentic"?

Because **Claude decides** what to do. The client doesn't hardcode "if user says weather, call weather tool." Instead:

1. Claude sees the available tools and their descriptions
2. Claude understands the user's intent from natural language
3. Claude autonomously picks which tool(s) to call and with what arguments
4. Claude can chain multiple tools together to answer complex questions

---

## How the Pieces Connect

### Startup Sequence

```
1. FastAPI starts → lifespan() begins
2. MCPClient() is created
3. client.connect("mcp_server/server.py") spawns the server as a subprocess
4. MCP protocol handshake (initialize)
5. Client discovers: list_tools(), list_resources(), list_prompts()
6. FastAPI is now ready to accept requests
```

### Data Flow for Each Request Type

**Chat (AI-powered):**
```
React → POST /api/chat → FastAPI → MCPClient.chat()
  → Claude API (with tools) → [tool_use loop] → MCP Server
  → final response → FastAPI → React
```

**Direct Tool Call (bypass AI):**
```
React → POST /api/tools/calculator → FastAPI → MCPClient.call_tool()
  → MCP Server → result → FastAPI → React
```

**Read Resource:**
```
React → GET /api/resources/memo://server-info → FastAPI → MCPClient.read_resource()
  → MCP Server → content → FastAPI → React
```

**Get Prompt:**
```
React → POST /api/prompts/summarize → FastAPI → MCPClient.get_prompt()
  → MCP Server → rendered messages → FastAPI → React
```

---

## MCP vs RAG — Key Differences

RAG (Retrieval-Augmented Generation) and MCP solve **different problems**. They are complementary, not competing.

### RAG: "Give the AI knowledge"

```
User question → Embed → Search vector DB → Retrieve chunks → Stuff into prompt → LLM → Answer

┌────────────┐    ┌──────────────┐    ┌─────────┐
│ User query  │──▶│ Vector DB     │──▶│  LLM    │
│             │    │ (embeddings) │    │ + chunks│──▶ Answer
└────────────┘    └──────────────┘    └─────────┘
```

- **Purpose:** Give the LLM access to your private data/documents
- **Direction:** Data flows INTO the prompt BEFORE the LLM generates
- **When it runs:** Before LLM inference (pre-processing)
- **What the LLM sees:** Retrieved text chunks in its context window
- **The LLM's role:** Answer based on provided context

### MCP: "Give the AI abilities"

```
User question → LLM decides → Call tool → Get result → LLM responds

┌────────────┐    ┌─────────┐    ┌──────────────┐
│ User query  │──▶│  LLM    │──▶│ MCP Server    │
│             │    │ (thinks)│◀──│ (tools/data)  │──▶ Answer
└────────────┘    └─────────┘    └──────────────┘
```

- **Purpose:** Give the LLM the ability to DO things and ACCESS live data
- **Direction:** LLM decides what data to fetch and when
- **When it runs:** During/after LLM inference (the LLM triggers it)
- **What the LLM sees:** Tool descriptions, then tool results
- **The LLM's role:** Decide which tools to use, interpret results

### Side-by-Side Comparison

| Aspect                | RAG                                    | MCP                                     |
|-----------------------|----------------------------------------|-----------------------------------------|
| **Core purpose**      | Knowledge retrieval                    | Tool execution + data access            |
| **Data flow**         | Data → Prompt → LLM                   | LLM → Tool call → Result → LLM         |
| **Who decides what?** | Developer configures retrieval         | LLM autonomously picks tools            |
| **Data freshness**    | As fresh as your index                 | Real-time (calls live systems)          |
| **Can take actions?** | No (read-only)                         | Yes (create, update, delete, compute)   |
| **Standardized?**     | No (many custom implementations)       | Yes (MCP is an open protocol)           |
| **Scope**             | Text search over documents             | Any capability: APIs, DBs, calculations |
| **Complexity**        | Embedding + vector DB + chunking       | Server + client + tool definitions      |
| **Best for**          | "Answer from these documents"          | "Do things and access live systems"     |

### When to use RAG vs MCP

| Scenario                                          | Use        |
|---------------------------------------------------|------------|
| "Answer questions from our 10,000 PDF documents"  | **RAG**    |
| "Look up the current stock price"                 | **MCP**    |
| "Search our knowledge base for similar issues"    | **RAG**    |
| "Create a Jira ticket and assign it to Bob"       | **MCP**    |
| "What does our policy say about refunds?"         | **RAG**    |
| "Calculate the compound interest on this loan"    | **MCP**    |
| "Find relevant code examples in our codebase"     | **RAG**    |
| "Run the test suite and report results"           | **MCP**    |
| "Answer from docs AND take actions"               | **Both!**  |

### Using RAG + MCP Together

They combine naturally. For example, a customer support bot could:

1. **RAG** → Search knowledge base for relevant articles
2. **MCP Tool** → Look up the customer's order status in the live database
3. **MCP Tool** → Create a support ticket if needed
4. **LLM** → Compose a response using knowledge base info + live order data

```
User: "Where's my order #12345?"

RAG: Retrieves shipping FAQ from knowledge base
MCP: Calls get_order_status(order_id="12345") → "Shipped, arriving March 25"
MCP: Calls get_tracking_link(order_id="12345") → "https://track.example.com/..."

LLM: "Your order #12345 has shipped and is expected to arrive on March 25.
      You can track it here: https://track.example.com/...
      Per our shipping policy, most orders arrive within 3-5 business days."
```

---

## MCP vs Function Calling — Key Differences

MCP tools are built ON TOP of function calling. Here's how they relate:

### Function Calling (Anthropic/OpenAI native)

```python
# Tools are defined inline in your application code
response = anthropic.messages.create(
    tools=[{
        "name": "get_weather",
        "description": "...",
        "input_schema": { ... }
    }],
    messages=[...],
)

# You handle tool execution yourself
if response.stop_reason == "tool_use":
    # YOUR code decides how to execute
    result = your_custom_weather_function(args)
```

- Tools are hardcoded in your app
- Execution logic lives in your app
- Every app reimplements the same tools
- No standard for tool discovery

### MCP (standardized protocol)

```python
# Tools are defined in a separate MCP server
# Client discovers them dynamically
tools = await session.list_tools()  # Server tells you what's available

# Execution is delegated to the server
result = await session.call_tool("get_weather", args)  # Server runs it
```

- Tools live in a **reusable server** (separate process)
- Any client can connect and use them
- Tools are **discovered at runtime**, not hardcoded
- One server can serve many apps

### Key insight

**MCP doesn't replace function calling — it standardizes and decouples it.**

```
Without MCP:  App ←→ [hardcoded tool logic] ←→ External systems
With MCP:     App ←→ MCP Client ←→ MCP Server ←→ External systems
                                     (reusable)
```

---

## MCP vs LangChain / Agent Frameworks

| Aspect              | LangChain / Frameworks           | MCP                                |
|---------------------|----------------------------------|------------------------------------|
| **What it is**      | Application framework (library)  | Communication protocol (standard)  |
| **Scope**           | Full app: chains, memory, agents | Just the tool/data connection layer|
| **Tool definition** | In your app code                 | In a separate, reusable server     |
| **Interoperability**| Tied to the framework            | Any client can talk to any server  |
| **Transport**       | In-process function calls        | stdio, HTTP/SSE (cross-process)    |
| **Ecosystem**       | Framework-specific plugins       | Universal MCP servers              |

**They work together:** You can use MCP servers as tool providers inside LangChain agents.

---

## When to Use What

```
"I need to answer questions from documents"
  → Use RAG

"I need the AI to call APIs and do things"
  → Use MCP (or function calling for simple cases)

"I need reusable tools that multiple apps can share"
  → Use MCP (that's exactly what it's for)

"I need a quick one-off tool integration"
  → Use function calling directly

"I need a full agent with memory, chains, and complex logic"
  → Use an agent framework (LangChain, CrewAI, etc.)
  → Use MCP for the tool layer underneath

"I need all of the above"
  → RAG for knowledge + MCP for tools + framework for orchestration
```

---

## Glossary

| Term                  | Definition                                                                              |
|-----------------------|-----------------------------------------------------------------------------------------|
| **MCP**               | Model Context Protocol — open standard for connecting AI to external tools and data     |
| **MCP Server**        | A process that exposes tools, resources, and/or prompts via the MCP protocol            |
| **MCP Client**        | A process that connects to an MCP server to use its capabilities                        |
| **Tool**              | A function the LLM can decide to call (e.g., calculator, API call)                      |
| **Resource**          | Read-only data exposed by a server via URI (e.g., `memo://server-info`)                 |
| **Prompt**            | A reusable message template with arguments (e.g., `summarize(text, style)`)             |
| **stdio transport**   | Communication via stdin/stdout — server runs as a subprocess of the client               |
| **SSE transport**     | Communication via HTTP Server-Sent Events — for remote servers                           |
| **Tool-use loop**     | The cycle: LLM requests tool → client executes → result sent back → LLM continues       |
| **JSON-RPC**          | The message format MCP uses over its transports (method, params, result)                 |
| **RAG**               | Retrieval-Augmented Generation — embedding + search to add knowledge to LLM prompts     |
| **Function calling**  | LLM capability to output structured tool calls (MCP builds on top of this)              |
| **Agentic**           | The LLM autonomously decides what actions to take rather than following hardcoded rules  |
