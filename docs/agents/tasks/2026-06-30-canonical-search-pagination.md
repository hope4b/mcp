# Canonical Search Pagination

## Task
- Short objective: Unify MCP search/list pagination on `first=0`, `offset=100`.
- Scope: Public MCP search signatures, backend mapping, how-to routing hints, tests, and documentation.
- Out of scope: Backend endpoint changes and non-search mutation tools.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `onto_mcp/agent_contract.py`, `onto_mcp/agent_contract.json`, `tests/test_canonical_pagination.py`, `tests/test_diagram_list_and_tags_tools.py`, `README.md`, `MCP_SETUP.md`, `docs/AGENT_ENTRY_GUIDE.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`
- Behavioral impact: `search_objects`, `search_entities`, `search_entities_with_related_meta`, `search_diagrams`, and `search_context_tags` now expose canonical `first`/`offset` pagination. For page-based backend endpoints, MCP maps `first/offset` to `page/size`.
- Risks: Existing clients using old `offset/limit`, `page/size`, or `page_size` arguments must update to canonical pagination.

## Validation
- Commands run: `python -m unittest tests.test_canonical_pagination`; `python -m unittest tests.test_canonical_pagination tests.test_diagram_list_and_tags_tools tests.test_agent_contract tests.test_search_entities_by_fields`; `python -m unittest discover -s tests -p "test_*.py"`; syntax parse with `PYTHONDONTWRITEBYTECODE=1`; `python -X pycache_prefix=$env:TEMP\onto_mcp_compile_cache -m compileall onto_mcp`; `git diff --check`.
- Result: focused pagination tests passed, affected wrapper/how-to tests passed, full unittest discovery passed `63 tests`, syntax parse passed, compileall passed, diff check passed with standard LF -> CRLF warnings only.
- Not run (and why): live MCP smoke not run during implementation; unit tests validate mapping.

## Commit Description (English)
- Short commit description: Unify search pagination parameters.
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: Optional live smoke for representative search tools after deploy.
- Recommended next owner (area): QA/Reviewer Agent.
