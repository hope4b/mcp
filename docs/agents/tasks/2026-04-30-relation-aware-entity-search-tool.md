# Task Note

## Task
- Short objective: Add a read-only MCP tool for relation-aware entity search.
- Scope: `onto_mcp/api_resources.py`, tests, public tool documentation.
- Out of scope: Backend API changes, multi-hop graph search, direction-aware public semantics, business projections.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `tests/test_search_entities_by_relations.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`
- Behavioral impact: Added `search_entities_by_relations` over `POST /realm/{realmId}/entity/search` with local validation and snake_case-to-camelCase body mapping.
- Risks: Live backend smoke was not run in this task; implementation is covered by wrapper-level unit tests.

## Validation
- Commands run: `python -m unittest tests.test_search_entities_by_relations`; `python -m unittest discover -s tests -p "test_*.py"`; `python -m compileall onto_mcp`
- Result: passed
- Not run (and why): Live Onto smoke was not run because no target realm/API key was provided for this implementation pass.

## Commit Description (English)
- Short commit description: add relation-aware entity search MCP tool
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: Run live smoke against Onto for root-only, single-predicate, multi-predicate, and invalid-shape cases.
- Recommended next owner (area): QA/Reviewer Agent
