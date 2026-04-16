# Task Note

## Task
- Short objective: Make the MCP server importable/startable and align the exposed tool contract with implemented behavior.
- Scope: runtime settings validation timing, auth tool surface, documentation cleanup, and contract clarification.
- Out of scope: full network integration testing against Onto/Keycloak APIs and deeper refactoring of `onto_mcp/resources.py`.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/settings.py`, `onto_mcp/server.py`, `onto_mcp/resources.py`, `README.md`, `MCP_SETUP.md`
- Behavioral impact: package import no longer fails immediately without env vars; server validates config at runtime; auth tools now include manual token and OAuth helper flows.
- Risks: live API paths are still only verified structurally, not end-to-end against real Onto services in this task.

## Validation
- Commands run: `python -c "import onto_mcp.server; print('import-ok')"`, `python -c "from onto_mcp.server import run; print('server-module-ok')"`, FastMCP tool introspection via `await mcp.get_tools()`
- Result: imports succeeded; tool registry now includes `login_via_token`, `get_keycloak_auth_url`, and `exchange_auth_code`.
- Not run (and why): full API smoke tests were not run because network-backed auth and Onto endpoints were not exercised in this session.

## Commit Description (English)
- Short commit description: align MCP runtime configuration and auth tool contract
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: decide whether `saveOntoAIThreadID` and `getOntoAIThreadID` remain part of the public contract or move behind integration-specific documentation.
- Recommended next owner (area): Feature Agent plus Data/API Agent
