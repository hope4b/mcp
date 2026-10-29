# Task Note: canonical relation batch MCP adapter

## Task
- Objective: implement `implementation:mcp:0` for the approved batch-relations
  specification, bounded to this MCP repository and a local candidate commit.
- Locked anchor: realm `000ba00a-00a0-0a00-a000-000a0a0a0aa3`, Feature
  `9529e47d-064c-44bd-a039-08b4f552eb52`.
- No deployment, publication, merge, backend changes or functional QA execution.

## Context Used
- Required project read order completed: AGENTS.md, ROLES.md, PROJECT_CONTEXT.md,
  ARCHITECTURE_MAP.md and TEST_STRATEGY.md; task template and exact source files.
- Valid active/execution resident `mcp-owner`; authoritative supplied bootstrap:
  Constitution `b826563c-f1ab-47ec-a994-0dfe86662833`, Registry
  `4b2edeff-fe1c-4419-a607-22843ffe27d6`, Charter
  `656fdd41-a025-4f1e-8e44-b804c0657a0a`, all accepted/current.
  These governance documents were not reread from another source.
- Assignment: `../authority.json`, SHA256
  `33607e0578db6aa578295691434f0cd6b718618349e219e8e7d69744f7498b15`.
  Exact role/runtime operation, workspace, gates and output inspected. The
  controller owns private capability validation and result persistence.
- Process source: `63033a506e389f8c6b35d74c68339a7b244d4276`; exact supplied
  AGENTS.md, FEATURE_PIPELINE_RECEIVER.md and MCP_OWNER_BOOTSTRAP_TEMPLATE.md
  hashes/sizes verified. The explicitly typed native entry governs this run.
- All six assigned artifact-file hashes/sizes, reference identities and exact
  UTF-8 body hashes verified. Current package:
  `356a8f13-e6c9-4a8a-bf45-be8479ae6ab5`; original specification/start gate:
  `d5c14bb3-34b9-4715-aa18-b0271679e259`; technical revision:
  `593b2ccd-b893-49d9-9b55-df6a5c3128a3`.
- Original/effective base, attempt parent and assigned main are all
  `50d57adbd99d4f67f2ef8c2a52b6470c21a7a1a6`; starting tree
  `3b76bcaa243723cf7c12153f149d3e86ae9677f5` was clean. Main incorporation is
  unnecessary. The supplied backend repair is context, not an MCP repair task.

## Changes
- `onto_mcp/relation_batch.py`: closed output variants, complete ordered-result
  validation, fixed message/provenance allowlists for operation refusals,
  single canonical dispatch, 35-second deadline covering acquisition/parsing/
  validation, shared cancellation/terminal state and late-completion discard.
- `onto_mcp/api_resources.py`: register the raw-array tool, use the existing
  canonical credential transport, attach protocol cancellation and map the
  existing outer guard to batch uncertainty.
- Agent Contract and entry guide: add the tool exactly once, describe partial
  success, repeats, reverse duplicates and no automatic replay. Contract version
  and count assertions updated to the additive 70-tool surface.
- `tests/test_relation_batch.py`: component and real in-memory FastMCP cases for
  raw inputs, limits/refusals, complete/all-ERROR output, malformed result
  variants, credential context, total deadline phases, both outer-guard dispatch
  states, cancellation, late completion and existing single-relation regression.
- No alternate endpoint, item writer, per-item schema, pre-read or retry added.

## Validation and artifacts
- `python3 -m compileall -q onto_mcp tests/test_relation_batch.py`: passed.
- Initial dependency installation failed: default Python 3.14 lacked FastMCP;
  package-index DNS was unavailable. Initial pytest therefore exited at conftest
  with missing FastMCP (`/tmp/mcp-batch-16158580-tests.log`).
- Cached dependency distributions were made available only to a temporary Python
  3.12 venv. Observed versions: FastMCP 4.0.10 and Pydantic 2.13.5. Python 3.14
  could not load the cached CPython-3.12 extension; no dependency or application
  runtime requirements were changed to accommodate it.
- The initial real-client test hung and was interrupted; a bounded diagnostic
  exited 124. An empty independent FastMCP sync echo server also timed out.
  Evidence: `/tmp/mcp-batch-16158580-protocol-diagnostic.log`,
  `/tmp/mcp-batch-16158580-sync-probe.log`. A diagnostic timer let the unchanged
  adapter request finish, indicating lost event-loop worker wakeups locally.
- A local-only pytest plugin `/tmp/mcp_batch_local_wakeup.py` adds a periodic
  event-loop timer; it replaces no tool, Core sender, parser or result boundary
  and is not committed or required by production. Original failed checks remain
  evidence. This workaround does not establish controller execution or QA PASS.
- Final focused command:
  `PYTHONPATH=/tmp:. timeout 30 /tmp/mcp-batch-16158580-py312/bin/python -m pytest -p mcp_batch_local_wakeup tests/test_relation_batch.py tests/test_agent_contract.py -q`
  passed **120 tests** (one dependency warning); evidence:
  `/tmp/mcp-batch-16158580-final-focused.log`.
- Full-suite attempt and final diff checks are recorded below once observed.

## Handoff
- Next owner: independent MCP implementation reviewer, then QA-agent for the
  approved candidate/PREPROD cases and Orchestrator for routing.
- Register exact committed sources `tests/test_relation_batch.py`,
  `tests/test_agent_contract.py`, `tests/test_server_runtime.py` and
  `tests/test_http_onto_api_key_passthrough.py` for controller technical execution.
- Separate functional candidate and PREPROD QA remain mandatory. No current
  deployed composition, state persistence or PREPROD readiness is asserted.
- Risks: Core may continue after timeout; reverse duplicates remain possible;
  local timer-assisted results require reassessment by the registered executor.

## Commit Description (English)
Commit description (EN): Add the canonical relation batch MCP adapter.

### Final observed checks
- Full command:
  `PYTHONPATH=/tmp:. timeout 120 /tmp/mcp-batch-16158580-py312/bin/python -m pytest -p mcp_batch_local_wakeup -q`
  exited **124**, stopping in existing `test_http_onto_api_key_passthrough.py`
  after 13 completed cases in that file. It collected 328 cases and did not
  finish. Evidence: `/tmp/mcp-batch-16158580-full.log`. This is not a full-suite
  pass; the local asyncio.run timer does not cover every existing test runner.
- Optional Ruff invocation could not locate the cached package's executable
  (`RuffNotFound`); no lint pass is claimed.
- `git diff --check` passed. A static AST/JSON comparison found exactly 70
  registered tools, matching unique Agent Contract and family coverage.
- Temporary test/diagnostic commands were interrupted or bounded by timeout and
  all have stopped. Temporary venv, plugin and redacted logs remain under /tmp
  for evidence; no application or test data was deleted.
