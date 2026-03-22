"""
MCP Client - Connects to an MCP server and exposes its capabilities.

This client:
  1. Spawns the MCP server as a subprocess (stdio transport)
  2. Discovers available tools, resources, and prompts
  3. Provides methods to call tools, read resources, and get prompts
  4. Integrates with an LLM (Claude) to handle tool-use in a chat loop
"""

import json
import logging
from contextlib import asynccontextmanager

from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_client")


class MCPClient:
    """
    High-level MCP client that manages a session with an MCP server
    and integrates with Claude for AI-powered chat with tool use.
    """

    def __init__(self):
        self.session: ClientSession | None = None
        self._tools: list = []
        self._resources: list = []
        self._prompts: list = []
        self.anthropic = Anthropic()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def connect(self, server_script_path: str):
        """
        Connect to an MCP server by spawning it as a subprocess.

        Usage:
            async with client.connect("path/to/server.py") as client:
                tools = await client.list_tools()
        """
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session

                # Initialize the connection (protocol handshake)
                await session.initialize()
                logger.info("MCP session initialized")

                # Cache available capabilities
                await self._discover_capabilities()

                yield self

                self.session = None

    async def _discover_capabilities(self):
        """Discover and cache all server capabilities."""
        tools_result = await self.session.list_tools()
        self._tools = tools_result.tools
        logger.info(f"Discovered {len(self._tools)} tools")

        resources_result = await self.session.list_resources()
        self._resources = resources_result.resources
        logger.info(f"Discovered {len(self._resources)} resources")

        prompts_result = await self.session.list_prompts()
        self._prompts = prompts_result.prompts
        logger.info(f"Discovered {len(self._prompts)} prompts")

    # ------------------------------------------------------------------
    # Capability accessors
    # ------------------------------------------------------------------

    def get_tools(self) -> list[dict]:
        """Return tools as serializable dicts."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.inputSchema,
            }
            for t in self._tools
        ]

    def get_resources(self) -> list[dict]:
        """Return resources as serializable dicts."""
        return [
            {
                "uri": str(r.uri),
                "name": r.name,
                "description": r.description,
                "mimeType": r.mimeType,
            }
            for r in self._resources
        ]

    def get_prompts(self) -> list[dict]:
        """Return prompts as serializable dicts."""
        return [
            {
                "name": p.name,
                "description": p.description,
                "arguments": [
                    {
                        "name": a.name,
                        "description": a.description,
                        "required": a.required,
                    }
                    for a in (p.arguments or [])
                ],
            }
            for p in self._prompts
        ]

    # ------------------------------------------------------------------
    # Tool calling
    # ------------------------------------------------------------------

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call a tool on the server and return the text result."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        result = await self.session.call_tool(tool_name, arguments)
        # Collect all text content blocks
        texts = [c.text for c in result.content if hasattr(c, "text")]
        return "\n".join(texts)

    # ------------------------------------------------------------------
    # Resource reading
    # ------------------------------------------------------------------

    async def read_resource(self, uri: str) -> str:
        """Read a resource from the server."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        result = await self.session.read_resource(uri)
        # result.contents is a list of content items
        texts = []
        for item in result.contents:
            if hasattr(item, "text"):
                texts.append(item.text)
        return "\n".join(texts)

    # ------------------------------------------------------------------
    # Prompt retrieval
    # ------------------------------------------------------------------

    async def get_prompt(self, prompt_name: str, arguments: dict) -> list[dict]:
        """Get a rendered prompt from the server."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        result = await self.session.get_prompt(prompt_name, arguments)
        messages = []
        for msg in result.messages:
            content = msg.content
            if hasattr(content, "text"):
                messages.append({"role": msg.role, "content": content.text})
            else:
                messages.append({"role": msg.role, "content": str(content)})
        return messages

    # ------------------------------------------------------------------
    # Chat with Claude (tool-use loop)
    # ------------------------------------------------------------------

    async def chat(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
    ) -> tuple[str, list[dict]]:
        """
        Send a message to Claude with MCP tools available.

        Returns:
            (assistant_reply, updated_conversation_history)
        """
        if conversation_history is None:
            conversation_history = []

        # Add user message to history
        conversation_history.append({"role": "user", "content": user_message})

        # Convert MCP tools to Anthropic tool format
        anthropic_tools = [
            {
                "name": t.name,
                "description": t.description or "",
                "input_schema": t.inputSchema,
            }
            for t in self._tools
        ]

        # System prompt that describes available resources and prompts
        system = self._build_system_prompt()

        # Agentic tool-use loop
        while True:
            response = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system,
                tools=anthropic_tools,
                messages=conversation_history,
            )

            # Collect the assistant response
            assistant_content = response.content
            conversation_history.append(
                {"role": "assistant", "content": self._serialize_content(assistant_content)}
            )

            # Check if we need to handle tool calls
            if response.stop_reason == "tool_use":
                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        logger.info(f"Claude wants to call tool: {block.name}({block.input})")
                        result_text = await self.call_tool(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_text,
                            }
                        )
                # Add tool results to conversation
                conversation_history.append({"role": "user", "content": tool_results})
            else:
                # No more tool calls — extract final text
                final_text = ""
                for block in assistant_content:
                    if hasattr(block, "text"):
                        final_text += block.text
                return final_text, conversation_history

    def _build_system_prompt(self) -> str:
        """Build a system prompt that describes available MCP capabilities."""
        parts = [
            "You are a helpful assistant with access to various tools via MCP (Model Context Protocol).",
            "",
            "Available resources you can tell the user about:",
        ]
        for r in self._resources:
            parts.append(f"  - {r.name} ({r.uri}): {r.description}")

        parts.append("")
        parts.append("Available prompt templates:")
        for p in self._prompts:
            args = ", ".join(a.name for a in (p.arguments or []))
            parts.append(f"  - {p.name}({args}): {p.description}")

        parts.append("")
        parts.append(
            "Use the tools provided to help the user. "
            "Be concise and helpful in your responses."
        )
        return "\n".join(parts)

    @staticmethod
    def _serialize_content(content) -> list[dict]:
        """Serialize Anthropic content blocks to dicts for conversation history."""
        serialized = []
        for block in content:
            if block.type == "text":
                serialized.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                serialized.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
        return serialized
