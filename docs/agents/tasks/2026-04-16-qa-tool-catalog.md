# Task Note

## Task
- Short objective: Produce a detachable QA-agent document describing the current MCP tool surface and implemented semantics.
- Scope: Document all currently registered tools, their logic, and QA-relevant behavioral notes.
- Out of scope: New tool implementation or matrix expansion.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `docs/income/QA_MCP_TOOL_CATALOG.md`
- Behavioral impact:
  - Added a standalone QA-agent-facing catalog of the current MCP tool surface.
  - Captured current semantics such as upsert behavior, wrapper tools, and known open questions.
- Risks:
  - The document is only as current as the runtime surface in `onto_mcp/api_resources.py`; future tool additions require manual sync.

## Validation
- Commands run:
  - `python - <<tool introspection snippet>>`
  - `rg -n \"@mcp.tool|def ...\" onto_mcp/api_resources.py`
- Result:
  - Confirmed the documented tool set matches the currently registered FastMCP tools.
- Not run (and why):
  - No live Onto API tests were needed because this task only produced detached documentation.

## Commit Description (English)
- Short commit description: add detached QA agent catalog for current MCP tools
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: Keep the QA catalog synchronized as fields and diagram tools are added.
- Recommended next owner (area): QA/Reviewer Agent / Feature Agent
