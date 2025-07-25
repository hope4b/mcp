from __future__ import annotations

# 'os' no longer needed after migrating to settings
from .resources import mcp
from .settings import MCP_TRANSPORT, PORT


def run() -> None:
    """Entry-point for both CLI and servers."""
    if MCP_TRANSPORT == "stdio":
        mcp.run()
    elif MCP_TRANSPORT == "http":
        import uvicorn
        uvicorn.run(mcp.asgi_app(), host="0.0.0.0", port=PORT)
    else:
        raise ValueError("MCP_TRANSPORT must be 'stdio' or 'http'")


if __name__ == "__main__":
    run()
