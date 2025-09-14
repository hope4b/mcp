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
        
        # Show available tools (using internal _tools if available)
        if hasattr(mcp, '_tools'):
            tools = mcp._tools
            print(f"🛠️  Tools available: {len(tools)}")
            for tool_name in list(tools.keys())[:5]:  # Show first 5 tools
                print(f"   • {tool_name}")
            if len(tools) > 5:
                print(f"   ... and {len(tools) - 5} more")
        else:
            print("🛠️  Tools: Available (count unknown)")
        
        # Show available resources (using internal _resources if available)
        if hasattr(mcp, '_resources'):
            resources = mcp._resources
            print(f"📁 Resources available: {len(resources)}")
            for resource_uri in list(resources.keys())[:3]:  # Show first 3 resources
                print(f"   • {resource_uri}")
            if len(resources) > 3:
                print(f"   ... and {len(resources) - 3} more")
        else:
            print("📁 Resources: Available (count unknown)")
        
        print("=" * 50)
        uvicorn.run(mcp.http_app(), host="0.0.0.0", port=PORT)
    else:
        raise ValueError("MCP_TRANSPORT must be 'stdio' or 'http'")


if __name__ == "__main__":
    run()
