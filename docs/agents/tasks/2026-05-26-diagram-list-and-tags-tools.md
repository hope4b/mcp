## Task
- Short objective: Add MCP tools for diagram discovery, context tag discovery, context tag creation from an existing object, and explicit diagram tag add/remove operations.
- Scope: `search_diagrams`, `search_context_tags`, `create_context_tag_from_object`, `add_diagram_tag`, `remove_diagram_tag`.
- Out of scope: Backend changes, alternate/fallback endpoints, all-page auto-fetch loops, assistant/object chat endpoints.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `tests/test_diagram_list_and_tags_tools.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`
- Behavioral impact: MCP clients can now list/filter diagrams, search context tags, mark an existing entity as a context tag, and add/remove diagram tags with read-modify-write semantics that preserve current tags and diagram metadata.
- Risks: Live backend smoke was not run in this pass; wrapper tests cover endpoint mapping, validation, and read-modify-write payloads.

## Validation
- Commands run: `python -m unittest tests.test_diagram_list_and_tags_tools`; `python -m unittest discover -s tests -p "test_*.py"`; syntax parse with `PYTHONDONTWRITEBYTECODE=1`; `git diff --check`
- Result: Targeted tests passed, full unittest discovery passed, syntax parse passed, diff check passed with line-ending warnings only.
- Not run (and why): Live smoke was not run because no agreed temporary realm/object/diagram fixture was provided in this turn.

## Commit Description (English)
- Short commit description: Add diagram discovery and tag tools.

## Handoff
- Remaining work: Run live smoke with a temporary realm/object/diagram fixture.
- Recommended next owner (area): QA/Reviewer Agent
