# Task Note

## Task
- Short objective: Add a read-only MCP tool for relation-template discovery through the new backend contract.
- Scope: Implement `search_relation_templates`, validate its input, cover accepted body shapes with tests, and update tool documentation.
- Out of scope: Any create/update/delete relation-template behavior changes and any backend contract changes.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `.gitignore`, `onto_mcp/api_resources.py`, `tests/test_search_relation_templates.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`
- Behavioral impact:
- Added read-only tool `search_relation_templates(realm_id, relation_type_name="", meta_ids=None)`.
- MCP now supports relation-template discovery by relation name, by relation name plus one/two participant template ids, and by one/two participant template ids without a relation name.
- Invalid discovery requests are rejected before any backend call when filters are missing or `meta_ids` length is not `1..2`.
- Repository test discovery is now consistent with `pyproject.toml` because `tests/` is no longer ignored.
- Risks:
- Live backend smoke verification is still needed to confirm whether any useful relation-template fields are omitted from the human-readable MCP summary.

## Validation
- Commands run:
- `python -m unittest tests.test_search_relation_templates`
- `python -m compileall onto_mcp`
- Result:
- Unit tests cover all acceptance-path input shapes and local validation paths.
- Package compile check passed for `onto_mcp`.
- Not run (and why):
- Live Onto API smoke checks were not run because this task used local wrapper tests only.

## Commit Description (English)
- Short commit description: add relation-template discovery MCP tool
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: run a live smoke check against a real Onto backend and confirm whether the summary should expose any extra relation-template fields.
- Recommended next owner (area): Feature Agent / QA-Reviewer Agent
