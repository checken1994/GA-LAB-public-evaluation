"""SCP MCP server package.

A minimal, self-implemented MCP-compatible JSON-RPC 2.0 server over stdio
(line-delimited) that exposes the Hands tools through the same capability PEP
path as the /v3/hands HTTP routes. Stdio only — the server never opens a
network port.
"""
from scp.mcp_server.server import MCP_SERVER_VERSION, McpStdioServer, main

__all__ = ["MCP_SERVER_VERSION", "McpStdioServer", "main"]
