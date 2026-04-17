"""Caseware Cloud MCP Proxy — connects to the remote Caseware Cloud MCP server as a client.

Acts as an MCP client that discovers and forwards tool calls to the remote
Caseware Cloud MCP server via Streamable HTTP (with SSE fallback).
"""

import asyncio
import logging
from typing import Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.sse import sse_client
from mcp.types import Tool, CallToolResult

logger = logging.getLogger(__name__)


class CloudProxy:
    """Manages the MCP client connection to Caseware Cloud.

    Runs the transport + session in a background task so the async context
    managers stay alive for the lifetime of the proxy.
    """

    def __init__(self, url: str, bearer_token: str) -> None:
        self._url = url
        if bearer_token.lower().startswith("bearer "):
            bearer_token = bearer_token[7:].strip()
        self._bearer_token = bearer_token
        self._session: Optional[ClientSession] = None
        self._tools: list[Tool] = []
        self._tool_names: set[str] = set()
        self._connected = False
        self._shutdown_event: Optional[asyncio.Event] = None
        self._bg_task: Optional[asyncio.Task] = None
        self._ready_event: Optional[asyncio.Event] = None
        self._connect_error: Optional[Exception] = None

    @property
    def connected(self) -> bool:
        """Check if proxy is connected AND the background task is still running."""
        if not self._connected:
            return False
        if self._bg_task and self._bg_task.done():
            # Background task has died — update state
            self._connected = False
            self._session = None
            return False
        return True

    @property
    def tools(self) -> list[Tool]:
        return self._tools

    def has_tool(self, name: str) -> bool:
        return name in self._tool_names

    async def connect(self) -> None:
        """Start the background connection task and wait until ready."""
        self._shutdown_event = asyncio.Event()
        self._ready_event = asyncio.Event()
        self._connect_error = None

        self._bg_task = asyncio.create_task(self._run_streamable_http())

        # Wait for connection to be established or fail
        await self._ready_event.wait()

        if self._connect_error:
            raise self._connect_error

    async def reconnect(self, max_attempts: int = 3) -> bool:
        """Attempt to re-establish the connection with exponential backoff.

        Returns True if reconnection succeeded, False otherwise.
        """
        # Clean up old task if it exists
        if self._bg_task and not self._bg_task.done():
            self._shutdown_event.set()
            try:
                await asyncio.wait_for(self._bg_task, timeout=5.0)
            except (asyncio.TimeoutError, Exception):
                self._bg_task.cancel()

        delays = [1, 2, 4]  # exponential backoff seconds
        for attempt in range(max_attempts):
            logger.info("Reconnection attempt %d/%d", attempt + 1, max_attempts)
            try:
                await self.connect()
                logger.info("Reconnected to Caseware Cloud successfully")
                return True
            except Exception as e:
                logger.warning("Reconnection attempt %d failed: %s", attempt + 1, e)
                if attempt < max_attempts - 1:
                    await asyncio.sleep(delays[attempt])

        logger.error("All %d reconnection attempts failed", max_attempts)
        return False

    async def _run_streamable_http(self) -> None:
        """Run the Streamable HTTP transport in a long-lived task."""
        headers = {"Authorization": f"Bearer {self._bearer_token}"}
        try:
            async with streamablehttp_client(self._url, headers=headers, timeout=60.0) as (
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    self._session = session
                    await session.initialize()

                    # Discover tools (activation not needed — all tools are
                    # exposed automatically by the Caseware Cloud MCP server)
                    await self._discover_tools()

                    self._connected = True
                    logger.info(
                        "Connected to Caseware Cloud MCP server — %d tools available",
                        len(self._tools),
                    )

                    # Signal that we're ready
                    self._ready_event.set()

                    # Keep alive until shutdown is requested
                    await self._shutdown_event.wait()

        except Exception as e:
            logger.error("Streamable HTTP connection failed: %s", e)
            self._connect_error = ConnectionError(
                f"Could not connect to Caseware Cloud MCP server at {self._url}: {e}"
            )
            self._ready_event.set()
        finally:
            self._session = None
            self._connected = False

    async def _discover_tools(self) -> None:
        """Discover tools from the remote server and cache them."""
        result = await self._session.list_tools()
        self._tools = list(result.tools)
        self._tool_names = {t.name for t in self._tools}

    async def call_tool(self, name: str, arguments: dict) -> CallToolResult:
        """Forward a tool call to the remote Caseware Cloud MCP server."""
        if not self._session:
            raise RuntimeError("CloudProxy is not connected")
        return await self._session.call_tool(name, arguments)

    async def disconnect(self) -> None:
        """Signal shutdown and wait for the background task to finish."""
        if self._shutdown_event:
            self._shutdown_event.set()
        if self._bg_task:
            try:
                await asyncio.wait_for(self._bg_task, timeout=10.0)
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning("Error during disconnect: %s", e)
                self._bg_task.cancel()
        self._tools = []
        self._tool_names = set()
        self._connected = False
