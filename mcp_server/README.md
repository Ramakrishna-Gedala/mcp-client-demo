# MCP Server

The MCP server exposes three types of capabilities to clients:

## Tools (LLM-callable functions)

| Tool           | Description                            | Parameters                         |
|----------------|----------------------------------------|------------------------------------|
| `calculator`   | Basic arithmetic (+, -, *, /)          | `operation`, `a`, `b`              |
| `get_weather`  | Weather for 5 cities                   | `city`                             |
| `manage_notes` | CRUD for in-memory notes               | `action`, `title?`, `content?`     |
| `get_datetime` | Current date/time in various formats   | `format?` (iso/human/date/time)    |

## Resources (readable data)

| URI                        | Description                |
|----------------------------|----------------------------|
| `memo://server-info`       | Server description text    |
| `memo://available-cities`  | City weather data (JSON)   |
| `memo://notes/{title}`     | Individual note content    |

## Prompts (reusable templates)

| Prompt            | Description                | Arguments                  |
|-------------------|----------------------------|----------------------------|
| `summarize`       | Summarize text             | `text*`, `style?`          |
| `code-review`     | Review code                | `code*`, `language?`       |
| `explain-concept` | Explain a technical topic  | `concept*`, `level?`       |

## How it works

The server uses **stdio transport** — it communicates via stdin/stdout. The MCP client spawns it as a subprocess and sends JSON-RPC messages over these streams.

```
MCP Client  ──stdin──▶  MCP Server
            ◀─stdout──
```

## Running standalone (for testing)

```bash
python -m mcp_server.server
```

This will start the server on stdio. You can test it with the MCP Inspector or any MCP client.
