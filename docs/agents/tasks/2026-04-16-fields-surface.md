## Task
- Short objective: Add the matrix-aligned fields MCP tools for entities and templates.
- Scope: `onto_mcp/api_resources.py`, operator docs, QA catalog, agent coordination files.
- Out of scope: diagram tools, live preprod QA, any extra semantic wrappers for field subtypes.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`, `docs/agents/DECISIONS.md`
- Behavioral impact: MCP runtime now exposes canonical field mutation tools for entity fields and template fields, with `metaFieldUuid` kept as the domain signal for template-derived entity fields, both save paths aligned to the confirmed `/fields` endpoints plus raw list payloads, field ids generated client-side when omitted, and `T_STRING` injected internally instead of required from callers.
- Risks: Delete query parameter naming differs between entity fields (`fieldsUuids`) and template fields (`fieldsIds`) and still needs live QA confirmation.

## Validation
- Commands run: import/introspection smoke for `onto_mcp.api_resources`
- Result: `onto_mcp.api_resources` imports successfully with dummy env values, and the new fields tools are registered in `FastMCP`.
- Not run (and why): live Onto API QA was not run here because it requires preprod calls and test data.

## Commit Description (English)
- Short commit description: add fields MCP surface and document unified entity field semantics
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: Run QA for the new fields tools, then implement the remaining diagram tools.
- Recommended next owner (area): QA/Reviewer Agent, then Feature/Data/API Agent for diagrams.
