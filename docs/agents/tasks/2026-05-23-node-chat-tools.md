## Task
- Short objective: Expose Onto object/node chat read and append endpoints through MCP tools.
- Scope: Add `get_node_chat_messages` and `create_node_chat_message` over the confirmed node chat endpoints.
- Out of scope: Assistant chat endpoints, fallback paths, and paginated node-chat endpoints.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `tests/test_node_chat_tools.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`
- Behavioral impact: MCP clients can now read and append object/node chat messages attached to a specific node in a realm.
- Risks: Live backend smoke was not run in this pass; wrapper tests cover exact endpoint mapping and validation.

## Validation
- Commands run: `python -m unittest tests.test_node_chat_tools`; `python -m unittest discover -s tests -p "test_*.py"`; syntax parse with `PYTHONDONTWRITEBYTECODE=1`; `git diff --check`
- Result: Targeted and full unit test discovery passed; syntax parse passed; diff check passed with line-ending warnings only.
- Not run (and why): `python -m compileall onto_mcp` was not run because this workspace has an existing `.pyc` write-permission issue; syntax parse was used instead.

## Commit Description (English)
- Short commit description: Add MCP node chat tools.

## Handoff
- Remaining work: Run live smoke against a temporary realm/node when a backend test fixture is available.
- Recommended next owner (area): QA/Reviewer Agent
