## Task
- Short objective: Add the remaining diagram MCP tools and close the last uncovered matrix block.
- Scope: `onto_mcp/api_resources.py`, operator docs, QA catalog, agent coordination files.
- Out of scope: diagram node/link sub-tools, copy/star/export endpoints, live preprod QA.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`, `docs/agents/tasks/2026-04-17-diagram-surface.md`
- Behavioral impact: MCP runtime now exposes `create_diagram`, `get_diagram`, `update_diagram`, and `delete_diagram` over the confirmed Onto diagram v2 endpoints.
- Risks: `create_diagram` uses query params rather than JSON body, and tag updates still need live QA with real tag ids.

## Validation
- Commands run: import/introspection smoke for `onto_mcp.api_resources`
- Result: `onto_mcp.api_resources` imports successfully with dummy env values, and the diagram tools are registered in `FastMCP`.
- Not run (and why): live Onto API QA was not run here because it requires preprod calls and test data.

## Commit Description (English)
- Short commit description: add diagram MCP surface and close the remaining matrix gap
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: Run QA for the new diagram tools and then validate optional session-state HTTP behavior.
- Recommended next owner (area): QA/Reviewer Agent.
