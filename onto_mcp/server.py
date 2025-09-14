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
        import asyncio
        
        # Show MCP server info BEFORE starting uvicorn (use stderr to avoid uvicorn interference)
        import sys
        print(f"🚀 Starting MCP Server: {mcp.name}", file=sys.stderr)
        print(f"📡 Transport: HTTP on port {PORT}", file=sys.stderr)
        
        # Try to get tools and resources info
        try:
            # Check if we can access tools
            if hasattr(mcp, '_tools') and mcp._tools:
                tools = mcp._tools
                print(f"🛠️  Tools available: {len(tools)}", file=sys.stderr)
                for tool_name in list(tools.keys())[:5]:
                    print(f"   • {tool_name}", file=sys.stderr)
                if len(tools) > 5:
                    print(f"   ... and {len(tools) - 5} more", file=sys.stderr)
            else:
                print("🛠️  Tools: Available (MCP server initialized)", file=sys.stderr)
            
            # Check if we can access resources
            if hasattr(mcp, '_resources') and mcp._resources:
                resources = mcp._resources
                print(f"📁 Resources available: {len(resources)}", file=sys.stderr)
                for resource_uri in list(resources.keys())[:3]:
                    print(f"   • {resource_uri}", file=sys.stderr)
                if len(resources) > 3:
                    print(f"   ... and {len(resources) - 3} more", file=sys.stderr)
            else:
                print("📁 Resources: Available (MCP server initialized)", file=sys.stderr)
                
        except Exception as e:
            print("🛠️  Tools: Available (MCP server initialized)", file=sys.stderr)
            print("📁 Resources: Available (MCP server initialized)", file=sys.stderr)
        
        print("=" * 50, file=sys.stderr)
        print("🔧 Starting HTTP server...", file=sys.stderr)
        
        # Force flush both stdout and stderr
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Start server
        uvicorn.run(mcp.http_app(), host="0.0.0.0", port=PORT)
    else:
        raise ValueError("MCP_TRANSPORT must be 'stdio' or 'http'")


if __name__ == "__main__":
    run()
