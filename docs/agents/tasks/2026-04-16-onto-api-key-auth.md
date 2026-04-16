# Task Note

## Task
- Short objective: Replace user login/password authentication with configuration-based Onto API key access.
- Scope: runtime MCP surface, server wiring, runtime settings, and minimal documentation alignment.
- Out of scope: full deletion of all legacy Keycloak modules from the repository and live verification against the real Onto API.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `onto_mcp/server.py`, `onto_mcp/settings.py`, `onto_mcp/__init__.py`, `.env.example`, `README.md`, `MCP_SETUP.md`
- Behavioral impact: active MCP server now exposes Onto tools through `ONTO_API_KEY`; login/password auth tools are no longer part of the runtime MCP surface.
- Risks: live Onto API behavior still needs validation with a real API key.

## Validation
- Commands run: `python -c "import onto_mcp.server; print('import-ok')"`, `python -c "from onto_mcp.server import run; print('server-module-ok')"`, FastMCP tool introspection for `onto_mcp.api_resources`
- Result: server imports cleanly; tool registry contains only Onto operations plus session-state helpers.
- Not run (and why): live Onto API calls were not executed because no real API key was used in this session.

## Commit Description (English)
- Short commit description: switch runtime MCP access from Keycloak auth to Onto API key
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: run live Onto API smoke checks and tighten error handling once real API responses are observed.
- Recommended next owner (area): Platform/Infra Agent plus Feature Agent
