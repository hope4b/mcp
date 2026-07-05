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
  - `tests/test_http_onto_api_key_passthrough.py`
  - `tests/test_memory_artifact_tools.py`
- Behavioral impact:
  - Registered MCP tools are wrapped with a `60s` end-to-end tool-level timeout while preserving function signatures for FastMCP.
  - Tool-level timeout execution now preserves the current `contextvars` context when moving work into the timeout worker thread, so HTTP MCP tool calls keep access to the caller-provided `X-Onto-Api-Key` request header.
  - Timeout output is structured and MCP-visible, with `tool_name`, `timeout_ms`, `backend_request_sent`, `backend_response_received`, and a correlation id.
  - Backend `UNKNOWN_AGENT_PRINCIPAL` responses are surfaced as validation-style MCP errors preserving `code`, `field`, `value`, and `message`.
  - Existing MemoryArtifact pagination wrapper behavior remains canonical `first` as skip/start and `offset` as page size.
- Risks:
  - Thread-based timeout cannot forcibly stop a Python function already blocked in a worker thread, but the MCP tool call returns a structured timeout envelope to the caller.
  - Deployed HTTP MCP smoke is still required after delivery/deploy gates open.

## Validation
- Commands run:
  - `python3 -m unittest tests.test_http_onto_api_key_passthrough`
  - `python3 -m unittest tests.test_memory_artifact_tools`
  - `python3 -m unittest discover -s tests -p "test_*.py"`
  - `python3 -m compileall onto_mcp`
  - `git diff --check`
- Result:
  - Focused HTTP API-key passthrough tests passed: `4 tests`.
  - Focused MemoryArtifact tests passed: `14 tests`.
  - Full unittest discovery passed: `67 tests`.
  - `compileall` passed.
  - `git diff --check` passed.
- Not run (and why):
  - Live HTTP MCP smoke was not run; deploy/runtime gate is separate.

## Commit Description (English)
- Short commit description: Preserve HTTP request context in MCP timeout wrapper
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Delivery evidence: PR `https://github.com/hope4b/mcp/pull/10`, commit `435b9f670a65b4cd4a87bdc9949062126e288143`, preprod deploy run `https://github.com/hope4b/mcp-server/actions/runs/28756524613` passed with `mcp_ref=435b9f670a65b4cd4a87bdc9949062126e288143`.
- Deployed HTTP MCP smoke: initialize and tools/list passed; `tools_count=61`; required MemoryArtifact tools were present.
- Blocker root cause: PR `#10` moved tool execution into a timeout worker thread without copying the FastMCP HTTP request `contextvars` context, so `get_http_request()` could not see caller-provided `X-Onto-Api-Key` inside tool execution.
- Local fix: timeout wrapper now runs the tool inside `contextvars.copy_context()` in the worker thread, with regression coverage proving passthrough survives the wrapper.
- Remaining work: Commit/push the fix, redeploy PR `#10` to preprod, then rerun MemoryArtifact validation/pagination smoke.
- Recommended next owner (area): Orchestrator / MCP QA after backend QA route is opened.
