# Task
- Short objective: Implement MCP portion of MemoryArtifact boundary defect contract.
- Scope: MCP tool-level timeout envelope, backend validation error surfacing, and MemoryArtifact wrapper tests.
- Out of scope: Backend implementation, `mcp-server` deploy/config changes, hidden dedup/fallback/idempotency changes, production deploy.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed:
  - `onto_mcp/api_resources.py`
  - `tests/test_memory_artifact_tools.py`
- Behavioral impact:
  - Registered MCP tools are wrapped with a `60s` end-to-end tool-level timeout while preserving function signatures for FastMCP.
  - Timeout output is structured and MCP-visible, with `tool_name`, `timeout_ms`, `backend_request_sent`, `backend_response_received`, and a correlation id.
  - Backend `UNKNOWN_AGENT_PRINCIPAL` responses are surfaced as validation-style MCP errors preserving `code`, `field`, `value`, and `message`.
  - Existing MemoryArtifact pagination wrapper behavior remains canonical `first` as skip/start and `offset` as page size.
- Risks:
  - Thread-based timeout cannot forcibly stop a Python function already blocked in a worker thread, but the MCP tool call returns a structured timeout envelope to the caller.
  - Deployed HTTP MCP smoke is still required after delivery/deploy gates open.

## Validation
- Commands run:
  - `python3 -m unittest tests.test_memory_artifact_tools`
  - `python3 -m unittest discover -s tests -p "test_*.py"`
  - `python3 -m compileall onto_mcp`
  - `git -C mcp diff --check`
- Result:
  - Focused MemoryArtifact tests passed: `14 tests`.
  - Full unittest discovery passed: `66 tests`.
  - `compileall` passed.
  - `git diff --check` passed.
- Not run (and why):
  - Live HTTP MCP smoke was not run; deploy/runtime gate is separate.

## Commit Description (English)
- Short commit description: Add structured MCP timeout and MemoryArtifact validation errors
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: Commit/push/open PR, deploy selected `mcp` commit to preprod through `mcp-server`, then run deployed HTTP MCP smoke.
- Recommended next owner (area): Orchestrator / MCP QA after backend QA route is opened.
