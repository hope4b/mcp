# Add Existing Nodes To Diagram MCP Tool

## Task
- Short objective: Add `add_existing_nodes_to_diagram` for placing existing Onto nodes on a diagram as visual representations.
- Scope: MCP wrapper, validation, output formatting, tests, and tool documentation.
- Out of scope: Creating objects, creating diagram links, changing diagram metadata/tags, websocket/STOMP fallbacks, automatic batch splitting over 20 items.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `tests/test_add_existing_nodes_to_diagram.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`
- Behavioral impact: MCP exposes a new diagram tool over `POST /realm/{realmId}/diagram/v2/{diagramId}/representation/create/existing_nodes/batch`.
- Risks: Live backend smoke for the target EDREST diagram still needs to be run with a valid API key.

## Validation
- Commands run: `python -m unittest tests.test_add_existing_nodes_to_diagram`; `python -m unittest discover -s tests -p "test_*.py"`; syntax parse with `PYTHONDONTWRITEBYTECODE=1`; `python -m compileall onto_mcp`; `git diff --check`.
- Result: targeted tests passed, full unittest discovery passed, syntax parse passed, `compileall` passed after rerun outside sandbox following a pycache write `PermissionError`, diff check passed with standard LF -> CRLF warnings only.
- Not run (and why): live smoke not run during implementation; it requires the target backend/API key context.

## Commit Description (English)
- Short commit description: Add existing node diagram placement tool.
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: Run live smoke by placing `EDREST-REQ-001..005` on diagram `7fdd80aa-9bba-4fa6-9c93-f8e11dcef67b` and confirm `get_diagram` reports `Representations: 5`.
- Recommended next owner (area): QA/Reviewer Agent.
