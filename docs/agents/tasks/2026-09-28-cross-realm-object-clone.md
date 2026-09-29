# Cross-realm object clone implementation

## Task
- Short objective: expose the accepted cross-realm clone contract through MCP.
- Scope: MCP write tool, read-only timeout recovery, routing and tests.
- Out of scope: backend implementation, idempotency keys, blind POST retry, merge and PROD.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes
- Feature: https://internal.ontonet.ru/ru/context/000ba00a-00a0-0a00-a000-000a0a0a0aa3/entity/8d28b580-7f8b-4d53-861e-887e6f3b033a
- Accepted Change Spec: `256406d1-1c8d-4e06-88e9-417b8c0f5ff6`

## Changes
- Files changed:
  - `onto_mcp/realm_object_clone.py`
  - `onto_mcp/api_resources.py`
  - `onto_mcp/agent_contract.json`
  - `onto_mcp/agent_contract.py`
  - `docs/AGENT_ENTRY_GUIDE.md`
  - `tests/test_clone_object_to_realm.py`
  - `tests/test_agent_contract.py`
  - `tests/test_server_runtime.py`
  - `tests/test_http_onto_api_key_passthrough.py`
  - `tests/conftest.py`
  - `tests/test_memory_artifact_schema_transport.py`
  - `tests/test_memory_artifact_tools.py`
  - `tests/test_realm_agent_admission_schema_transport.py`
  - `docs/agents/tasks/2026-09-28-cross-realm-object-clone.md`
- Behavioral impact: one POST per write invocation and one read-only result lookup after an ambiguous timeout.
- Risks: the accepted concurrent-duplicate window remains; found=false never authorizes a blind POST retry.

## Validation
- Commands run:
  - `/usr/bin/env FASTMCP_CHECK_FOR_UPDATES=off PYTHONPATH=/home/ubuntu/git/onto/_platform/agent-runtime/.runtime/feature-worktrees/256406d1-1c8d-4e06-88e9-417b8c0f5ff6/mcp /home/ubuntu/git/onto/_platform/qa/mcp-feature-venv/bin/python -m compileall -q onto_mcp`
  - `/usr/bin/env FASTMCP_CHECK_FOR_UPDATES=off PYTHONPATH=/home/ubuntu/git/onto/_platform/agent-runtime/.runtime/feature-worktrees/256406d1-1c8d-4e06-88e9-417b8c0f5ff6/mcp /home/ubuntu/git/onto/_platform/qa/mcp-feature-venv/bin/python -m pytest tests/test_clone_object_to_realm.py tests/test_agent_contract.py tests/test_server_runtime.py tests/test_http_onto_api_key_passthrough.py`
  - `docker run --rm ... python:3.12-slim sh -lc 'python -m pip install --disable-pip-version-check -q -r requirements.txt && python -m pytest -q && python -m compileall -q onto_mcp'`
- Result:
  - passed (`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`)
  - passed (`ab8beb22456ee85c03554f447c842e5666f9195364f046ff4345f77596e213cc`)
  - canonical-like clean Python 3.12 environment: `249 passed`, compileall passed.
- PREPROD recovery: canonical run `36587217154` exposed that collection order let
  legacy offline tests replace the declared `requests` dependency globally.
  `tests/conftest.py` now loads the real declared dependencies before collection;
  the subprocess transport probe receives the repository import path, the HTTP
  exception fixture uses the public `requests` constructor, and the pre-existing
  tool-count assertion includes the two accepted clone tools. No product exception
  handling or timeout semantics were changed.
- Not run (and why): live PREPROD smoke waits for the explicit owner PREPROD gate.

## Commit Description (English)
- Short commit description: Add safe cross-realm object clone MCP tools

## Handoff
- Remaining work: independent review, PR creation and owner-approved PREPROD manual testing.
- Recommended next owner (area): feature owner for manual acceptance.

Commit description (EN): Add safe cross-realm object clone MCP tools
