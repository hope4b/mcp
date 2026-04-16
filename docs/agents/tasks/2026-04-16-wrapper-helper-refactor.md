# Task Note

## Task
- Short objective: Fix MCP wrapper tools that were calling decorated `FunctionTool` objects at runtime.
- Scope: Move template and batch-entity shared logic into plain helper functions and rewire wrapper tools to those helpers.
- Out of scope: Broader refactor of all tool implementations.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`
- Behavioral impact:
  - `create_template` no longer calls a decorated `save_template` tool object.
  - `create_entities_batch` no longer calls a decorated `save_entities_batch` tool object.
  - Shared logic now lives in plain helpers, which keeps wrapper tools valid thin aliases.
- Risks:
  - Similar wrapper patterns should be avoided in future tool additions unless they go through plain helpers.

## Validation
- Commands run:
  - `python - <<import/introspection snippet>>`
  - `git diff -- onto_mcp/api_resources.py`
- Result:
  - `onto_mcp.api_resources` imports successfully.
  - All four affected tools remain registered in FastMCP.
- Not run (and why):
  - Live rerun of `create_template` and `create_entities_batch` was not performed in this step.

## Commit Description (English)
- Short commit description: fix wrapper tools by routing through plain helper functions
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: rerun QA on `create_template` and `create_entities_batch` runtime paths.
- Recommended next owner (area): QA/Reviewer Agent / Feature Agent
