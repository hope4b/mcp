# Get Diagram Representation Details

## Task
- Short objective: Enrich `get_diagram` output with diagram representation details so diagram-gated agents can identify represented objects.
- Scope: Runtime-only MCP `get_diagram(realm_id, diagram_id)` summary formatting and focused tests.
- Out of scope: Database changes, backend changes, deploy repo changes, deploys, diagram mutations, alternate endpoints, transitional adapters, legacy paths, compatibility parsers, and marking the defect done.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes
- TEST_STRATEGY.md read: yes
- HANDOFF.md / WORKLOG.md read: yes
- Accepted MemoryArtifact read: yes, `09100d92-58d2-407f-a8bf-2f32982d9fe8` at `dev/bugs/mcp/get-diagram-representation-objects`
- Locked Onto anchor received: yes, object `c160d7ad-22ec-4e04-8b9d-6b8f328980b3`; substitution not allowed

## Changes
- Files changed: `onto_mcp/api_resources.py`, `tests/test_get_diagram.py`, `docs/agents/tasks/2026-07-06-get-diagram-representation-details.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`
- Behavioral impact: `get_diagram` still returns existing diagram metadata and counts, and now adds a `Representation details` section when the backend response contains representations. The section exposes representation id, node id, object name, representation type, classification, coordinates, size, and placement details when present.
- Risks: Live payload shape should be validated through a real MCP `get_diagram` call against diagram `8b344515-7eb0-42bf-b26e-139c3264cc20` with a valid API key before owner-facing remote verification or production claims.
- Onto milestone: `implementation_reported` was written to the locked defect object chat.

## Validation
- Commands run:
  - `python3 -m unittest tests.test_get_diagram`
  - `python3 -m unittest discover -s tests -p "test_*.py"`
  - `python3 -m compileall onto_mcp`
  - `git diff --check`
- Result: Focused test passed; full unittest discovery passed 68 tests; compileall passed; diff check passed.
- Not run (and why): Live MCP `get_diagram` smoke was not run because no valid API key/service execution route was provided in this implementation turn.

## Commit Description (English)
- Short commit description: Enrich get_diagram representation output.
- Required for code changes: assistant final response must end with `Commit description (EN): Enrich get_diagram representation output.`

## Handoff
- Remaining work: Publish via PR for human review, then run live MCP read of the known diagram with a valid API key to confirm represented defect object visibility. No commit, push, PR, or deploy was performed.
- Recommended next owner (area): MCP Owner / QA Reviewer for PR review and live read-only MCP validation.
