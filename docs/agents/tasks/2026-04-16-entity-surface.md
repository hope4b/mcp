# Task Note

## Task
- Short objective: Add the matrix-aligned entity MCP tools on top of Onto `saveEntity` and `saveEntityBatch`.
- Scope: Implement entity upsert/read/search/delete tools, keep batch create as a compatibility wrapper, and preserve explicit `meta_entity_id` semantics.
- Out of scope: Relations, fields, and diagrams.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `README.md`, `MCP_SETUP.md`
- Behavioral impact:
  - Added `save_entity`, `save_entities_batch`, `get_entity`, `search_entities`, `search_entities_with_related_meta`, and `delete_entity`.
  - Converted `create_entities_batch` into a compatibility wrapper over `save_entities_batch`.
  - `save_entity` and `save_entities_batch` no longer imply any hidden dedup or preflight lookup.
  - `meta_entity_id` remains an explicit caller-controlled part of the save payload, matching Onto reclassification/declassification behavior.
- Risks:
  - `save_entities_batch` currently formats returned entities from the `createdEntities` response slot; live API verification is still needed for mixed create/update batches.
  - `search_entities` and `search_entities_with_related_meta` assume list-shaped responses and flatten `entities` blocks from v2 results.

## Validation
- Commands run:
  - `python - <<import/introspection snippet>>`
  - `git diff -- onto_mcp/api_resources.py`
- Result:
  - `onto_mcp.api_resources` imports successfully.
  - New entity tools appear in the registered FastMCP tool list.
- Not run (and why):
  - Live Onto entity mutation/search smoke tests were not run in this step.

## Commit Description (English)
- Short commit description: add entity upsert and search MCP tools
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: relation/meta-relation tools, field tools, and diagram tools remain to close the matrix.
- Recommended next owner (area): Feature Agent / Data/API Agent
