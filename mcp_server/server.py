"""
MCP Server - Demo server with tools, resources, and prompts.

This server demonstrates the three core MCP primitives:
  - Tools:     Functions the LLM can call (calculator, weather, notes)
  - Resources: Data the LLM can read (static content exposed via URI)
  - Prompts:   Reusable prompt templates the client can request
"""

import json
import logging
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
    Resource,
    Prompt,
    PromptArgument,
    PromptMessage,
    GetPromptResult,
    ResourceTemplate,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

# ---------------------------------------------------------------------------
# In-memory data stores (simulating real backends)
# ---------------------------------------------------------------------------

# Simple notes store
NOTES: dict[str, str] = {
    "welcome": "Welcome to the MCP demo! This is a sample note.",
    "todo": "1. Learn MCP\n2. Build a client\n3. Build a server",
}

# Fake weather data
WEATHER_DATA: dict[str, dict] = {
    "new york": {"temp_c": 22, "condition": "Partly Cloudy", "humidity": 65},
    "london": {"temp_c": 15, "condition": "Rainy", "humidity": 80},
    "tokyo": {"temp_c": 28, "condition": "Sunny", "humidity": 55},
    "sydney": {"temp_c": 19, "condition": "Windy", "humidity": 70},
    "paris": {"temp_c": 18, "condition": "Cloudy", "humidity": 72},
}

# ---------------------------------------------------------------------------
# Create the MCP server
# ---------------------------------------------------------------------------
app = Server("demo-mcp-server")


# ========================== TOOLS ==========================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Return the list of available tools."""
    return [
        Tool(
            name="calculator",
            description="Perform basic arithmetic operations (add, subtract, multiply, divide).",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide"],
                        "description": "The arithmetic operation to perform",
                    },
                    "a": {"type": "number", "description": "First operand"},
                    "b": {"type": "number", "description": "Second operand"},
                },
                "required": ["operation", "a", "b"],
            },
        ),
        Tool(
            name="get_weather",
            description="Get current weather for a city. Available cities: New York, London, Tokyo, Sydney, Paris.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name (e.g., 'New York', 'London')",
                    },
                },
                "required": ["city"],
            },
        ),
        Tool(
            name="manage_notes",
            description="Create, read, update, or delete notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "read", "update", "delete", "list"],
                        "description": "The action to perform on notes",
                    },
                    "title": {
                        "type": "string",
                        "description": "Note title (required for create/read/update/delete)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Note content (required for create/update)",
                    },
                },
                "required": ["action"],
            },
        ),
        Tool(
            name="get_datetime",
            description="Get the current date and time in various formats.",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["iso", "human", "date_only", "time_only"],
                        "description": "Output format (default: human)",
                    },
                },
                "required": [],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a tool and return the result."""
    logger.info(f"Tool called: {name} with args: {arguments}")

    if name == "calculator":
        return _handle_calculator(arguments)
    elif name == "get_weather":
        return _handle_weather(arguments)
    elif name == "manage_notes":
        return _handle_notes(arguments)
    elif name == "get_datetime":
        return _handle_datetime(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


def _handle_calculator(args: dict) -> list[TextContent]:
    op = args["operation"]
    a, b = args["a"], args["b"]
    if op == "add":
        result = a + b
    elif op == "subtract":
        result = a - b
    elif op == "multiply":
        result = a * b
    elif op == "divide":
        if b == 0:
            return [TextContent(type="text", text="Error: Division by zero")]
        result = a / b
    else:
        return [TextContent(type="text", text=f"Unknown operation: {op}")]
    return [TextContent(type="text", text=f"{a} {op} {b} = {result}")]


def _handle_weather(args: dict) -> list[TextContent]:
    city = args["city"].lower()
    if city not in WEATHER_DATA:
        available = ", ".join(c.title() for c in WEATHER_DATA)
        return [TextContent(type="text", text=f"City not found. Available: {available}")]
    w = WEATHER_DATA[city]
    text = (
        f"Weather in {city.title()}:\n"
        f"  Temperature: {w['temp_c']}°C\n"
        f"  Condition:   {w['condition']}\n"
        f"  Humidity:    {w['humidity']}%"
    )
    return [TextContent(type="text", text=text)]


def _handle_notes(args: dict) -> list[TextContent]:
    action = args["action"]

    if action == "list":
        if not NOTES:
            return [TextContent(type="text", text="No notes found.")]
        listing = "\n".join(f"- {title}" for title in NOTES)
        return [TextContent(type="text", text=f"Notes:\n{listing}")]

    title = args.get("title", "").strip()
    if not title and action != "list":
        return [TextContent(type="text", text="Error: 'title' is required.")]

    if action == "read":
        if title not in NOTES:
            return [TextContent(type="text", text=f"Note '{title}' not found.")]
        return [TextContent(type="text", text=f"**{title}**\n\n{NOTES[title]}")]

    elif action == "create":
        content = args.get("content", "")
        if title in NOTES:
            return [TextContent(type="text", text=f"Note '{title}' already exists. Use 'update' instead.")]
        NOTES[title] = content
        return [TextContent(type="text", text=f"Note '{title}' created.")]

    elif action == "update":
        content = args.get("content", "")
        if title not in NOTES:
            return [TextContent(type="text", text=f"Note '{title}' not found. Use 'create' instead.")]
        NOTES[title] = content
        return [TextContent(type="text", text=f"Note '{title}' updated.")]

    elif action == "delete":
        if title not in NOTES:
            return [TextContent(type="text", text=f"Note '{title}' not found.")]
        del NOTES[title]
        return [TextContent(type="text", text=f"Note '{title}' deleted.")]

    return [TextContent(type="text", text=f"Unknown action: {action}")]


def _handle_datetime(args: dict) -> list[TextContent]:
    fmt = args.get("format", "human")
    now = datetime.now()
    if fmt == "iso":
        text = now.isoformat()
    elif fmt == "date_only":
        text = now.strftime("%Y-%m-%d")
    elif fmt == "time_only":
        text = now.strftime("%H:%M:%S")
    else:
        text = now.strftime("%A, %B %d, %Y at %I:%M %p")
    return [TextContent(type="text", text=text)]


# ========================== RESOURCES ==========================

@app.list_resources()
async def list_resources() -> list[Resource]:
    """Return available resources."""
    resources = [
        Resource(
            uri="memo://server-info",
            name="Server Information",
            description="Information about this MCP demo server",
            mimeType="text/plain",
        ),
        Resource(
            uri="memo://available-cities",
            name="Available Cities",
            description="List of cities with weather data",
            mimeType="application/json",
        ),
    ]
    # Expose each note as a resource
    for title in NOTES:
        resources.append(
            Resource(
                uri=f"memo://notes/{title}",
                name=f"Note: {title}",
                description=f"User note titled '{title}'",
                mimeType="text/plain",
            )
        )
    return resources


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read a specific resource by URI."""
    logger.info(f"Resource read: {uri}")

    if uri == "memo://server-info":
        return (
            "MCP Demo Server v1.0\n"
            "====================\n"
            "This server provides:\n"
            "- Calculator tool (basic arithmetic)\n"
            "- Weather tool (5 cities)\n"
            "- Notes management tool (CRUD)\n"
            "- Date/time tool\n"
            "- Resources (server info, cities, notes)\n"
            "- Prompt templates (summarize, code-review, explain)"
        )

    if uri == "memo://available-cities":
        cities = {
            city.title(): data for city, data in WEATHER_DATA.items()
        }
        return json.dumps(cities, indent=2)

    if uri.startswith("memo://notes/"):
        title = uri.replace("memo://notes/", "")
        if title in NOTES:
            return NOTES[title]
        return f"Note '{title}' not found."

    return f"Unknown resource: {uri}"


# ========================== PROMPTS ==========================

@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    """Return available prompt templates."""
    return [
        Prompt(
            name="summarize",
            description="Summarize the given text concisely.",
            arguments=[
                PromptArgument(
                    name="text",
                    description="The text to summarize",
                    required=True,
                ),
                PromptArgument(
                    name="style",
                    description="Summary style: brief, detailed, or bullet-points",
                    required=False,
                ),
            ],
        ),
        Prompt(
            name="code-review",
            description="Review the given code and provide feedback.",
            arguments=[
                PromptArgument(
                    name="code",
                    description="The code to review",
                    required=True,
                ),
                PromptArgument(
                    name="language",
                    description="Programming language of the code",
                    required=False,
                ),
            ],
        ),
        Prompt(
            name="explain-concept",
            description="Explain a technical concept in simple terms.",
            arguments=[
                PromptArgument(
                    name="concept",
                    description="The concept to explain",
                    required=True,
                ),
                PromptArgument(
                    name="level",
                    description="Explanation level: beginner, intermediate, or advanced",
                    required=False,
                ),
            ],
        ),
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict | None = None) -> GetPromptResult:
    """Return a fully-rendered prompt."""
    args = arguments or {}
    logger.info(f"Prompt requested: {name} with args: {args}")

    if name == "summarize":
        style = args.get("style", "brief")
        text = args.get("text", "")
        return GetPromptResult(
            description="Summarize text",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"Please summarize the following text in a {style} style:\n\n{text}",
                    ),
                )
            ],
        )

    elif name == "code-review":
        code = args.get("code", "")
        language = args.get("language", "unknown")
        return GetPromptResult(
            description="Code review",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=(
                            f"Please review the following {language} code. "
                            f"Check for bugs, performance issues, and suggest improvements:\n\n"
                            f"```{language}\n{code}\n```"
                        ),
                    ),
                )
            ],
        )

    elif name == "explain-concept":
        concept = args.get("concept", "")
        level = args.get("level", "beginner")
        return GetPromptResult(
            description="Explain concept",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=(
                            f"Explain the concept of '{concept}' at a {level} level. "
                            f"Use simple analogies and examples where possible."
                        ),
                    ),
                )
            ],
        )

    raise ValueError(f"Unknown prompt: {name}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    """Run the MCP server via stdio transport."""
    logger.info("Starting MCP Demo Server...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
