# MCP post-merge transport tool-count fix

## Task
- Short objective: correct the stale transport-test tool-count expectation from 66 to the canonical merged count of 67.
- Scope: the single expectation in `tests/test_realm_agent_admission_schema_transport.py`, validation of canonical 67-tool alignment, and this task-local implementation note.
- Out of scope: runtime, schema, how-to, dependency, realm, subject, memory, object-chat or deploy behavior; dependency installation; independent review/QA; PR merge; and deployment.

## Context Used
- AGENTS.md read: yes, exact target ref from the immutable manifest.
- PROJECT_CONTEXT.md read: yes, exact target ref from the immutable manifest.
- ARCHITECTURE_MAP.md read: yes, exact target ref from the immutable manifest.
- Additional bootstrap: `docs/agents/ROLES.md`, `docs/agents/TEST_STRATEGY.md`, live accepted/current realm governance, MCP Owner bootstrap, task-manifest contract, and runtime receiver kernel.
- Manifest: `2026-09-10-mcp-post-merge-tool-count-fix-v1` at `onto-docs/docs/mcp-existing-link-representation-spec@2463df89c60f3e8d88fa56380ef22d0e651f2f8d`.
- Process source: `onto-docs/main@8ef5d21cdb3844c3410caaf953e73c44784e3b10`.
- Runtime target before the fix: `mcp/feat/mcp-existing-link-representation@28c2e723c5a866be6139ea5b7c3dce61c50dd63a`.

## Changes
- Files changed: `tests/test_realm_agent_admission_schema_transport.py` and this task note.
- Behavioral impact: none. The test now expects the canonical 67-tool transport surface already produced by the merged runtime.
- Risks: no runtime or public contract code changed; independent review remains required before any redeploy.

## Validation
- `python3 -m pytest tests/test_realm_agent_admission_schema_transport.py`: did not execute the five tests because the subprocess probe failed at import with `ModuleNotFoundError: No module named 'fastmcp'`; pytest reported five setup errors.
- Direct probe confirmation: `python3 tests/_realm_agent_admission_schema_transport_probe.py` failed at the declared `fastmcp` import, confirming dependency unavailability rather than a changed transport assertion result.
- Workflow-equivalent `python3 -m pytest`: not run because the declared runtime dependency `fastmcp` is unavailable in this environment; dependency installation was forbidden and was not attempted.
- Static canonical alignment: passed at 67 unique `@mcp.tool` registrations, 67 `tool_contract` entries, 67 unique family entries, equal name sets, and guide marker 67.
- `python3 -m compileall -q onto_mcp`: passed.
- `python3 -m json.tool onto_mcp/agent_contract.json`: passed.
- `git diff --check`: passed.
- Exact main ancestry and scoped-diff checks: passed; `9062e99a19032e0fcc5e48b8db8dbfaf18fee1f4` remains an ancestor and only the authorized test expectation plus this note changed.

## Commit Description (English)
- Short commit description: Update the post-merge transport tool-count expectation.

## Handoff
- Remaining work: independent review of this exact fix is required before any separately authorized redeploy. This implementation does not claim QA, deploy readiness, merge, release acceptance, or completion.
- Recommended next owner (area): `orchestrator` for independent-review routing.
