# MCP Server

This project provides a minimal FastMCP server wrapping Onto resources.

## Usage

1. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Run in stdio mode:
   ```bash
   python -m onto_mcp.server
   ```
3. Run as HTTP server (port 8080 by default):
   ```bash
   MCP_TRANSPORT=http python -m onto_mcp.server
   ```
4. Docker (development):
   ```bash
   docker compose up --build
   ```

Environment variables (see `.env.example`) allow overriding `ONTO_API_BASE` and
server port.
