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
            # Try different methods to get tools
            tools = None
            if hasattr(mcp, 'list_tools'):
                try:
                    tools = mcp.list_tools()
                except:
                    pass
            
            if not tools and hasattr(mcp, '_tools') and mcp._tools:
                tools = mcp._tools
            
            if tools:
                if isinstance(tools, dict):
                    tool_names = list(tools.keys())
                elif isinstance(tools, list):
                    tool_names = [getattr(tool, 'name', str(tool)) for tool in tools]
                else:
                    tool_names = [str(tool) for tool in tools]
                
                print(f"🛠️  Tools available: {len(tool_names)}", file=sys.stderr)
                for tool_name in tool_names[:5]:
                    print(f"   • {tool_name}", file=sys.stderr)
                if len(tool_names) > 5:
                    print(f"   ... and {len(tool_names) - 5} more", file=sys.stderr)
            else:
                print("🛠️  Tools: Available (MCP server initialized)", file=sys.stderr)
            
            # Try different methods to get resources
            resources = None
            if hasattr(mcp, 'list_resources'):
                try:
                    resources = mcp.list_resources()
                except:
                    pass
            
            if not resources and hasattr(mcp, '_resources') and mcp._resources:
                resources = mcp._resources
            
            if resources:
                if isinstance(resources, dict):
                    resource_uris = list(resources.keys())
                elif isinstance(resources, list):
                    resource_uris = [getattr(resource, 'uri', str(resource)) for resource in resources]
                else:
                    resource_uris = [str(resource) for resource in resources]
                
                print(f"📁 Resources available: {len(resource_uris)}", file=sys.stderr)
                for resource_uri in resource_uris[:3]:
                    print(f"   • {resource_uri}", file=sys.stderr)
                if len(resource_uris) > 3:
                    print(f"   ... and {len(resource_uris) - 3} more", file=sys.stderr)
            else:
                print("📁 Resources: Available (MCP server initialized)", file=sys.stderr)
                
        except Exception as e:
            print(f"🛠️  Tools: Available (MCP server initialized) - Error: {e}", file=sys.stderr)
            print(f"📁 Resources: Available (MCP server initialized) - Error: {e}", file=sys.stderr)
        
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
