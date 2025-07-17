from __future__ import annotations

import os

from .resources import mcp


def run() -> None:
    """Entry-point for both CLI and servers."""
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run()
    elif transport == "http":
        import uvicorn
        uvicorn.run(mcp.asgi_app(), host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
    else:
        raise ValueError("MCP_TRANSPORT must be 'stdio' or 'http'")


if __name__ == "__main__":
    run()
