# MCP existing-link representation runtime implementation

## Task
- Short objective: add the one approved `create_existing_link_representation`
  MCP wrapper and keep its Agent Contract/runtime guidance discoverable.
- Scope: exact wrapper, `diagram_write` registration, contract version/count,
  runtime/guide guidance, focused tests, and implementation evidence.
- Out of scope: backend changes, aliases, fallbacks, compatibility, alternate
  routes, relation selectors, QA, deploy, PR, merge, and Onto writes.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes
- Approved Change Spec, both completed review sections, MCP handoff, immutable
  backend result, and published backend controller read and hash-validated: yes
- Runtime base: `hope4b/mcp@576a3ba0846e670db5d4c94454c654c1e3e3f652`
- Backend dependency: `a4b-core@6a14fb7de36c1c5befbe54462ba0cc0738cfbd5d`

## Changes
- Files changed:
  - `onto_mcp/api_resources.py`
  - `onto_mcp/agent_contract.json`
  - `onto_mcp/agent_contract.py`
  - `docs/AGENT_ENTRY_GUIDE.md`
  - `tests/test_agent_contract.py`
  - `tests/test_create_existing_link_representation.py`
  - this task note
- Behavioral impact: one required five-string tool performs one POST to the
  canonical existing-link representation endpoint with the exact three-key
  camel-case body and formats the direct backend object with the approved text.
  Blank input and helper `RuntimeError` paths return only failure text. Runtime
  guidance requires `write_intent` and discloses that the backend may create the
  subject relation when absent.
- Agent Contract: version `2026-09-02.existing-link-representation`, 66 tools,
  one registration in `diagram_write`; guide markers agree.
- Risks: independent review and integrated QA remain required. The full local
  pytest command is environment-blocked in three pre-existing real FastMCP
  subprocess transport modules under Linux Python 3.14.4; see validation.

## Validation
- Commands run:
  - `PYTHONPATH=/tmp/mcp-existing-link-deps-345 python3 -m pytest tests/test_create_existing_link_representation.py`
  - `PYTHONPATH=/tmp/mcp-existing-link-deps-345 python3 -m pytest tests/test_agent_contract.py`
  - `timeout 240s env FASTMCP_CHECK_FOR_UPDATES=off PYTHONPATH=.:/tmp/mcp-existing-link-deps-345 python3 -m pytest`
  - `FASTMCP_CHECK_FOR_UPDATES=off PYTHONPATH=.:/tmp/mcp-existing-link-deps-345 python3 -m pytest --ignore=tests/test_memory_artifact_schema_transport.py --ignore=tests/test_realm_agent_admission_schema_transport.py --ignore=tests/test_realm_agent_admission_http_transport.py`
  - `PYTHONPYCACHEPREFIX=/tmp/mcp-existing-link-pycache PYTHONPATH=/tmp/mcp-existing-link-deps-345 python3 -m compileall onto_mcp`
  - `python3 -m json.tool onto_mcp/agent_contract.json`
  - `git diff --check`
  - `PYTHONPATH=/tmp/mcp-existing-link-deps-345 python3 -m black --workers 1 tests/test_create_existing_link_representation.py`
- Result:
  - focused tool: 5 passed, 13 subtests passed;
  - Agent Contract: 49 passed, 18 subtests passed;
  - full non-transport suite: 178 passed, 250 subtests passed;
  - compileall, JSON validation, and diff whitespace checks passed.
- Not run (and why): independent review, integrated/live QA, deploy, and PR are
  outside this implementation tract. The unfiltered 192-test pytest suite did
  not complete because the existing real FastMCP subprocess probes hang with
  the available Linux Python 3.14.4 environment, including the repository-
  evidenced FastMCP 3.4.5 / MCP SDK 1.29.0 / Pydantic 2.13.4 baseline. Python
  3.11 is unavailable and Docker daemon access is unavailable. No runtime or
  test was modified to conceal or bypass this environment limitation.

## Commit Description (English)
- Short commit description: Add existing-link representation MCP tool

## Handoff
- Remaining work: independent implementation review, then independently
  authorized backend/integrated QA against exact backend and MCP identities.
- Recommended next owner (area): resident `orchestrator` for routing.
