# Task Note

## Task
- Short objective: Add an MCP tool that explains Onto in the style of the canonical `about.md`.
- Scope: runtime tool surface and packaged editorial text.
- Out of scope: dynamic documentation retrieval and multilingual variants.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/about_content.py`, `onto_mcp/api_resources.py`, `README.md`, `MCP_SETUP.md`
- Behavioral impact: MCP now exposes `about_onto(focus="")` returning a Russian overview of Onto and focused topic variants.
- Risks: content is static and must be updated manually if the canonical editorial source changes.

## Validation
- Commands run: FastMCP tool introspection for `onto_mcp.api_resources`
- Result: `about_onto` is present in the registered tool set.
- Not run (and why): no end-to-end Onto API validation required because the tool does not call the API.

## Commit Description (English)
- Short commit description: add static Onto overview tool
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: decide whether the editorial text should remain packaged static content or move to a broader docs packaging flow.
- Recommended next owner (area): Feature Agent
