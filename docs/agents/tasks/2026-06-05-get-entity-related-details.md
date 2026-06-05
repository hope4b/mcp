# Get Entity Related Details

## Task
- Short objective: Expose actual related entity details in `get_entity` when `related_entities=true`.
- Scope: MCP `get_entity` text response formatting.
- Out of scope: backend API changes, new MCP tools, relation traversal beyond the backend payload.

## Context Used
- AGENTS.md read: yes.
- PROJECT_CONTEXT.md read: yes.
- ARCHITECTURE_MAP.md read: yes.

## Changes
- Files changed:
  - `onto_mcp/api_resources.py`
  - `tests/test_get_entity_related_entities.py`
- Behavioral impact: `get_entity(..., related_entities=true)` now prints each related entity id/name and available relation metadata instead of only the related entity count.
- Risks: no known open risk after live STDIO validation; future backend payload changes could still require formatter adjustment.

## Validation
- Commands run:
  - `python -m unittest tests.test_get_entity_related_entities`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - `python -c "from pathlib import Path; import ast; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in Path('onto_mcp').glob('*.py')]; print('syntax ok')"`
- Live STDIO smoke:
  - realm: `000ba00a-00a0-0a00-a000-000a0a0a0aa3`
  - entity: `123e2296-a62a-41bf-936e-1a12da6ce44b`
  - result: `Related entities: 7` plus related entity names, uuids, relation names, directions, and template info were visible in the MCP response.
- Result: all local commands passed; live STDIO smoke passed.
- Not run (and why): `python -m compileall onto_mcp` failed because the existing `onto_mcp/__pycache__` path denied `.pyc` writes; syntax was validated with `ast.parse` instead.

## Commit Description (English)
- Short commit description: Expose related entity details in get_entity.
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: none for this defect before commit/PR.
- Recommended next owner (area): Feature Agent.
