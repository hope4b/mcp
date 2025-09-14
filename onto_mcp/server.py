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
        import importlib.metadata
        
        # Get version
        try:
            version = importlib.metadata.version("onto-mcp-server")
        except:
            version = "unknown"
        
        print(f"🚀 Starting MCP Server: {mcp.name} v{version}", file=sys.stderr)
        print(f"📡 Transport: HTTP on port {PORT}", file=sys.stderr)
        
        # Try to get tools and resources info
        try:
            # Debug: Show all available methods
            print(f"🔍 Debug: MCP object type: {type(mcp)}", file=sys.stderr)
            print(f"🔍 Debug: Available methods: {[m for m in dir(mcp) if not m.startswith('_')][:10]}", file=sys.stderr)
            
            # Try different methods to get tools
            tools = None
            tool_names = []
            
            # Method 1: list_tools
            if hasattr(mcp, 'list_tools'):
                try:
                    tools = mcp.list_tools()
                    print(f"🔍 Debug: list_tools() returned: {type(tools)}", file=sys.stderr)
                except Exception as e:
                    print(f"🔍 Debug: list_tools() error: {e}", file=sys.stderr)
            
            # Method 2: _tools attribute
            if not tools and hasattr(mcp, '_tools'):
                try:
                    tools = mcp._tools
                    print(f"🔍 Debug: _tools attribute: {type(tools)} = {tools}", file=sys.stderr)
                except Exception as e:
                    print(f"🔍 Debug: _tools error: {e}", file=sys.stderr)
            
            # Method 3: Try to get from resources module directly
            if not tools:
                try:
                    from . import resources
                    # Look for tool functions in the module
                    tool_functions = [name for name in dir(resources) if not name.startswith('_') and callable(getattr(resources, name))]
                    if tool_functions:
                        tool_names = [name for name in tool_functions if name not in ['mcp', 'keycloak_auth', '_get_valid_token', '_get_user_spaces_data']]
                        print(f"🔍 Debug: Found {len(tool_names)} tool functions in resources module", file=sys.stderr)
                except Exception as e:
                    print(f"🔍 Debug: resources module error: {e}", file=sys.stderr)
            
            # Process tools
            if tools:
                if isinstance(tools, dict):
                    tool_names = list(tools.keys())
                elif isinstance(tools, list):
                    tool_names = [getattr(tool, 'name', str(tool)) for tool in tools]
                else:
                    tool_names = [str(tool) for tool in tools]
            
            if tool_names:
                print(f"🛠️  Tools available: {len(tool_names)}", file=sys.stderr)
                for tool_name in tool_names[:5]:
                    print(f"   • {tool_name}", file=sys.stderr)
                if len(tool_names) > 5:
                    print(f"   ... and {len(tool_names) - 5} more", file=sys.stderr)
            else:
                print("🛠️  Tools: Available (MCP server initialized)", file=sys.stderr)
            
            # Try different methods to get resources
            resources = None
            resource_uris = []
            
            # Method 1: list_resources
            if hasattr(mcp, 'list_resources'):
                try:
                    resources = mcp.list_resources()
                    print(f"🔍 Debug: list_resources() returned: {type(resources)}", file=sys.stderr)
                except Exception as e:
                    print(f"🔍 Debug: list_resources() error: {e}", file=sys.stderr)
            
            # Method 2: _resources attribute
            if not resources and hasattr(mcp, '_resources'):
                try:
                    resources = mcp._resources
                    print(f"🔍 Debug: _resources attribute: {type(resources)} = {resources}", file=sys.stderr)
                except Exception as e:
                    print(f"🔍 Debug: _resources error: {e}", file=sys.stderr)
            
            # Process resources
            if resources:
                if isinstance(resources, dict):
                    resource_uris = list(resources.keys())
                elif isinstance(resources, list):
                    resource_uris = [getattr(resource, 'uri', str(resource)) for resource in resources]
                else:
                    resource_uris = [str(resource) for resource in resources]
            
            if resource_uris:
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
