# Task Note

## Task
- Short objective: Add the first matrix-aligned realm and template MCP tools on top of the Onto API key runtime.
- Scope: Implement realm update/delete and template upsert/read/list/delete/link tools; keep template creation as a compatibility wrapper.
- Out of scope: Entity, relation, field, and diagram tool implementation.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `README.md`, `MCP_SETUP.md`
- Behavioral impact:
  - Added `update_realm` and `delete_realm`.
  - Added `save_template`, `get_template`, `list_templates`, `delete_template`, and `link_template_to_parents`.
  - Converted `create_template` into a compatibility wrapper over `save_template`.
  - Added query-parameter support to the shared Onto HTTP helper.
- Risks:
  - `list_templates` depends on caller-provided `class_name` semantics from Onto.
  - Template and realm mutation responses are normalized into human-readable summaries; some response payload details remain hidden.

## Validation
- Commands run:
  - `python - <<import/introspection snippet>>`
  - `git diff -- onto_mcp/api_resources.py`
- Result:
  - `onto_mcp.api_resources` imports successfully.
  - New tools appear in the registered FastMCP tool list.
- Not run (and why):
  - Live Onto mutation smoke tests were not run because no write verification was requested in this step.

## Commit Description (English)
- Short commit description: add realm and template MCP tools aligned to operation matrix
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: implement entity-layer tools next, then relations, fields, and diagrams.
- Recommended next owner (area): Feature Agent / Data/API Agent
