from __future__ import annotations

from .resources import mcp
from .settings import MCP_TRANSPORT, PORT
from .utils import safe_print


def run() -> None:
    """Entry-point for both CLI (stdio) and HTTP server."""
    if MCP_TRANSPORT == "stdio":
        safe_print("[server] Onto MCP Server starting (stdio transport)")
        mcp.run()
    elif MCP_TRANSPORT == "http":
        safe_print(f"[server] Onto MCP Server vOAUTH starting on port {PORT} (http transport)")
        import uvicorn
        uvicorn.run(mcp.http_app(), host="0.0.0.0", port=PORT)
    else:
        raise ValueError("MCP_TRANSPORT must be 'stdio' or 'http'")


if __name__ == "__main__":
    run()
