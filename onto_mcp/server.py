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
        # Initialize MCP server before starting HTTP server
        print(f"🚀 Starting MCP Server: {mcp.name}")
        print(f"📡 Transport: HTTP on port {PORT}")
        
        # Show available tools
        tools = mcp.get_tools()
        print(f"🛠️  Tools available: {len(tools)}")
        for tool in tools[:5]:  # Show first 5 tools
            print(f"   • {tool.name}")
        if len(tools) > 5:
            print(f"   ... and {len(tools) - 5} more")
        
        # Show available resources
        resources = mcp.get_resources()
        print(f"📁 Resources available: {len(resources)}")
        for resource in resources[:3]:  # Show first 3 resources
            print(f"   • {resource.uri}")
        if len(resources) > 3:
            print(f"   ... and {len(resources) - 3} more")
        
        print("=" * 50)
        uvicorn.run(mcp.http_app(), host="0.0.0.0", port=PORT)
    else:
        raise ValueError("MCP_TRANSPORT must be 'stdio' or 'http'")


if __name__ == "__main__":
    run()
