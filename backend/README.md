# FastAPI Backend

The backend is a REST API that bridges the React frontend to the MCP system.

## Lifecycle

1. On startup, it creates an `MCPClient` and connects to the MCP server
2. The MCP server runs as a child process for the entire app lifetime
3. All REST endpoints delegate to the MCP client
4. On shutdown, the connection is cleanly closed

## Endpoints

| Method | Path                   | Purpose                              |
|--------|------------------------|--------------------------------------|
| POST   | `/api/chat`            | Send message → Claude with MCP tools |
| GET    | `/api/tools`           | List all MCP tools                   |
| POST   | `/api/tools/{name}`    | Call a tool directly (bypass LLM)    |
| GET    | `/api/resources`       | List all MCP resources               |
| GET    | `/api/resources/{uri}` | Read a resource by URI               |
| GET    | `/api/prompts`         | List all MCP prompt templates        |
| POST   | `/api/prompts/{name}`  | Render a prompt with arguments       |
| DELETE | `/api/sessions/{id}`   | Clear a chat session                 |
| GET    | `/api/health`          | Health check + capability counts     |

## Running

```bash
# From project root
make backend

# Or directly
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs
