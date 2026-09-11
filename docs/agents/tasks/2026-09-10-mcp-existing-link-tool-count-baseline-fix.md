# MCP existing-link tool-count baseline fix

## Task
- Short objective: correct the stale realm-agent admission schema-transport
  expected MCP tool count from 65 to the canonical 66-tool baseline.
- Scope: one assertion in
  `tests/test_realm_agent_admission_schema_transport.py`, this task note,
  manifest validation, commit, and push on the existing feature branch.
- Out of scope: runtime behavior, tool schemas, Agent Contract or guidance,
  dependencies, deployment, merge, independent review, QA verdicts, realm or
  subject changes, memory, and object-chat writes.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes
- Process source: `onto-docs/main@8ef5d21cdb3844c3410caaf953e73c44784e3b10`.
- Manifest source:
  `onto-docs/docs/mcp-existing-link-representation-spec@b4d140df0f21d919d979d4af4a3c72fd72922ed5`.
- Manifest: `2026-09-10-mcp-existing-link-tool-count-baseline-fix-v1`.
- Runtime initial identity:
  `feat/mcp-existing-link-representation@5f55e84995d84752f6937e25b77126e7da32a248`.
- Accepted/current governance: Constitution
  `b826563c-f1ab-47ec-a994-0dfe86662833`, registry
  `b466b73f-bed0-4683-bcda-e38f367bafb9`, and `mcp-owner` charter
  `656fdd41-a025-4f1e-8e44-b804c0657a0a`; resident validation was
  `valid_active_resident` with `boot_allowed=true`.
- Approved Change Spec, MCP implementation handoff, prior implementation
  result, prior independent review, canonical Agent Contract, regression
  baseline, authorized stale test, and prior runtime note were read from their
  exact manifest-bound refs and hashes.

## Changes
- Files changed:
  - `tests/test_realm_agent_admission_schema_transport.py`
  - this task note
- Behavioral impact: none. The transport regression now expects the existing
  canonical 66-tool surface that already includes
  `create_existing_link_representation`.
- Contract impact: none; runtime, tool schemas, registration, Agent Contract,
  generated guidance, and dependencies are unchanged.
- Risks: independent review and QA remain separate. This narrow correction
  changes only the expected count and does not add transport behavior.

## Validation
- Commands run:
  - `python -m pytest tests/test_realm_agent_admission_schema_transport.py`
  - `python3 -m pytest tests/test_realm_agent_admission_schema_transport.py`
  - `FASTMCP_CHECK_FOR_UPDATES=off PYTHONPATH=.:/tmp/mcp-existing-link-deps-345 python3 -m pytest tests/test_realm_agent_admission_schema_transport.py`
  - `FASTMCP_CHECK_FOR_UPDATES=off PYTHONPATH=.:/tmp/mcp-existing-link-deps-345 python3 -m pytest tests/test_agent_contract.py`
  - `timeout 90s env FASTMCP_CHECK_FOR_UPDATES=off PYTHONPATH=.:/tmp/mcp-existing-link-deps-345 python3 -m pytest`
  - `FASTMCP_CHECK_FOR_UPDATES=off PYTHONPATH=.:/tmp/mcp-existing-link-deps-345 python3 -m pytest --ignore=tests/test_memory_artifact_schema_transport.py --ignore=tests/test_realm_agent_admission_schema_transport.py --ignore=tests/test_realm_agent_admission_http_transport.py`
  - `PYTHONPYCACHEPREFIX=/tmp/mcp-tool-count-pycache PYTHONPATH=/tmp/mcp-existing-link-deps-345 python3 -m compileall onto_mcp`
  - static JSON/source alignment check for canonical count 66
  - `git diff --check`
- Result:
  - Agent Contract suite passed: 49 tests and 18 subtests;
  - full non-transport suite passed: 178 tests and 250 subtests;
  - compileall, static 66-count alignment, and diff whitespace checks passed;
  - the bare manifest command could not start because `python` is unavailable;
  - system `python3` collected the focused module but its subprocess failed
    because FastMCP is not installed globally;
  - with the existing repository-recorded isolated FastMCP 3.4.5 / Pydantic
    2.13.4 baseline, both the focused module and unfiltered 192-test suite
    reached the pre-existing real FastMCP subprocess transport boundary and
    stalled under Linux Python 3.14.4; the focused run was interrupted after
    observation and the unfiltered suite ended at the recorded 90-second
    timeout. No focused or unfiltered pass is claimed.
- Not run (and why): deploy, merge, independent review, QA, and remote/live
  verification are outside this runtime-only tract. No dependency or runtime
  change was made to bypass the documented transport-environment limitation.

## Commit Description (English)
- Short commit description: Fix MCP tool-count test baseline

## Handoff
- Remaining work: independent review remains required before any deploy retry;
  no deploy or merge authority is included here.
- Recommended next owner (area): resident `orchestrator` for exact commit/push
  identity intake and independent review routing.
