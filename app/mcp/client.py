"""
MCP Client — communicates with an external MCP server or exposes local tools
following the Model Context Protocol spec.
"""
import httpx
from typing import Any
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class MCPClient:
    """Thin client for calling an external MCP-compatible tool server."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.mcp_server_url

    async def list_tools(self) -> list[dict]:
        async with httpx.AsyncClient() as http:
            resp = await http.get(f"{self.base_url}/tools")
            resp.raise_for_status()
            return resp.json()

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict:
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.post(
                f"{self.base_url}/tools/{tool_name}",
                json={"arguments": arguments},
            )
            resp.raise_for_status()
            return resp.json()


mcp_client = MCPClient()
