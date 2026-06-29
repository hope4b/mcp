# Field Value Entity Search

## Task
- Short objective: Add MCP support for finding entities by template field values and route agents to it through `how_to_use_onto_mcp`.
- Scope: Read-only MCP tool, `get_entity` field-value presentation, agent contract/how-to routing, tests, and documentation.
- Out of scope: Field writes, relation search changes, backend contract changes, and fallback endpoints.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `onto_mcp/agent_contract.py`, `onto_mcp/agent_contract.json`, `tests/test_search_entities_by_fields.py`, `tests/test_agent_contract.py`, `README.md`, `MCP_SETUP.md`, `docs/AGENT_ENTRY_GUIDE.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`
- Behavioral impact: Added `search_entities_by_fields` over `POST /realm/{realmId}/entity/find/v2` with `metaFieldFilters`; `get_entity` now renders returned field values when present.
- Risks: Live backend field payloads may include additional field properties not rendered; this tool requires callers to know or discover `field_id`.

## Validation
- Commands run: `python -m unittest tests.test_search_entities_by_fields`; `python -m unittest tests.test_agent_contract`; `python -m unittest discover -s tests -p "test_*.py"`; syntax parse with `PYTHONDONTWRITEBYTECODE=1`; `python -X pycache_prefix=$env:TEMP\onto_mcp_compile_cache -m compileall onto_mcp`; `git diff --check`.
- Result: focused wrapper tests passed, agent contract tests passed, full unittest discovery passed `59 tests`, syntax parse passed, compileall passed, diff check passed with standard LF -> CRLF warnings only.
- Not run (and why): live MCP smoke not run during implementation; unit tests validate wrapper mapping and how-to routing.

## Commit Description (English)
- Short commit description: Add field-value entity search tool.
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: Optional live smoke with a known template field such as INN/OGRN on preprod/prod.
- Recommended next owner (area): QA/Reviewer Agent.
