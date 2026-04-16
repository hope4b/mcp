# Task Note

## Task
- Short objective: Add the matrix-aligned relation and meta-relation MCP tools.
- Scope: Implement create/update/delete tools for entity relations and template/meta relations.
- Out of scope: Field and diagram tools.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `README.md`, `MCP_SETUP.md`
- Behavioral impact:
  - Added `create_relation`, `update_relation`, and `delete_relation`.
  - Added `create_meta_relation`, `update_meta_relation`, and `delete_meta_relation`.
  - Relation payloads now map directly onto Onto `EntityRelationDefinition` and `MetaRelationDefinition`.
- Risks:
  - Live verification is still needed to confirm whether `additionalProperties` is accepted as-is for entity relations.
  - Cardinality defaults for meta relations are conservative (`0..1`) and may need adjustment by callers for richer models.

## Validation
- Commands run:
  - `python - <<import/introspection snippet>>`
  - `git diff -- onto_mcp/api_resources.py`
- Result:
  - `onto_mcp.api_resources` imports successfully.
  - Relation tools appear in the registered FastMCP tool list.
- Not run (and why):
  - Live Onto relation mutation smoke tests were not run in this step.

## Commit Description (English)
- Short commit description: add relation and meta-relation MCP tools
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: field tools and diagram tools remain to close the matrix.
- Recommended next owner (area): Feature Agent / Data/API Agent
