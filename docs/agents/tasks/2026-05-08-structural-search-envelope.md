## Task
- Short objective: Align MCP relation-aware entity search with the production-ready backend page envelope.
- Scope: `search_entities_by_relations` response parsing, pagination/sort request mapping, wrapper tests, and tool catalog docs.
- Out of scope: Backend controller changes and live data fixture creation.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `tests/test_search_entities_by_relations.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`
- Behavioral impact: `search_entities_by_relations` now unwraps `{items,total,first,offset}` responses, preserves old list responses, and exposes `include_descendants`, `first`, `offset`, and `sort`.
- Risks: Live HTTP smoke still requires an Onto API key source for the local backend.

## Validation
- Commands run: `python -m unittest tests.test_search_entities_by_relations`; `PYTHONDONTWRITEBYTECODE=1` syntax parse for `onto_mcp/*.py`; `git diff --check`
- Result: Targeted tests passed; syntax parse passed; diff check passed with line-ending warnings only.
- Not run (and why): `python -m compileall onto_mcp` failed because the existing `onto_mcp/__pycache__` refused `.pyc` writes with `PermissionError`.

## Commit Description (English)
- Short commit description: Support structural entity search page envelope in MCP.

## Handoff
- Remaining work: Run a live local backend smoke once an `X-API-Key` is available to the test process.
- Recommended next owner (area): QA/Reviewer Agent
